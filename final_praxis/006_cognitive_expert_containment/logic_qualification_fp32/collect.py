"""Collect private cloud receipts and independently audit a terminal run locally."""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, subprocess, sys, time
import shutil
from pathlib import Path
import boto3
from botocore.config import Config

HERE=Path(__file__).resolve().parent
BUCKET='praxis-garypagan-272615233626-us-east-1'
TERMINAL={'COMPLETED','FAILED','STOPPED','TIMED_OUT'}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8');temp.replace(path)

class PendingCollection(RuntimeError):
    """A terminal prefix is not yet a stable, complete result snapshot."""


def remaining_pause(deadline, seconds=30):
    remaining=deadline-time.monotonic()
    if remaining<=0: raise TimeoutError('Collector deadline reached; cloud watchdog remains independent')
    time.sleep(min(seconds,remaining))


def inventory(client,prefix,out):
    objects=[]
    for page in client.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=prefix):
        for obj in page.get('Contents',[]):
            name=obj['Key'][len(prefix):]
            if name.startswith('outputs/') or name in ('cloud_status.json','driver.log','launch_receipt.json','bundle_manifest.json'):
                path=(out/name).resolve()
                if not path.is_relative_to(out.resolve()): raise ValueError('Unsafe result path')
                if obj['Size']>100_000_000: raise ValueError('Unexpected result object size')
                objects.append({'name':name,'size':obj['Size'],'etag':obj['ETag']})
    if len(objects)>5000 or sum(o['size'] for o in objects)>1_000_000_000:
        raise ValueError('Unexpected result inventory exceeds collection bound')
    return sorted(objects,key=lambda o:o['name'])


def get_status(client,prefix,run_id):
    response=client.get_object(Bucket=BUCKET,Key=prefix+'cloud_status.json')
    body=response['Body']
    try: raw=body.read(1_000_001)
    finally: body.close()
    if len(raw)>1_000_000: raise ValueError('Unexpected status size')
    status=json.loads(raw)
    if status.get('run_id')!=run_id: raise ValueError('Cloud status belongs to another run')
    return status,response['ETag']


def download_snapshot(client,prefix,objects,out):
    def download(item):
        name=item['name'];path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix(path.suffix+'.download-part')
        response=client.get_object(Bucket=BUCKET,Key=prefix+name,IfMatch=item['etag'])
        body=response['Body'];total=0
        try:
            with temporary.open('wb') as stream:
                while True:
                    chunk=body.read(1024*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>item['size']: raise PendingCollection('Object grew during collection')
                    stream.write(chunk)
        finally: body.close()
        if total!=item['size']: raise PendingCollection('Object size changed during collection')
        temporary.replace(path)
        return {'key':prefix+name,'file':name,'bytes':total,'sha256':digest(path),'etag':item['etag']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(download,objects))


def collect(run_id,out,wait=False,deadline=None):
    if not re.fullmatch(r'fp006-logic-[0-9a-f]{10}',run_id): raise ValueError('Invalid run identifier')
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    identity=out/'collector_identity.json'
    if identity.exists():
        if json.loads(identity.read_text()).get('run_id')!=run_id: raise ValueError('Output directory belongs to another run')
    elif (out/'outputs').exists():
        raise ValueError('Existing output directory lacks a collector run identity')
    else: write(identity,{'run_id':run_id})
    prefix='final-praxis/20260912/runs/'+run_id+'/'
    client=boto3.Session(profile_name='praxis-build',region_name='us-east-1').client('s3',config=Config(connect_timeout=10,read_timeout=30,retries={'max_attempts':2}))
    deadline=deadline if deadline is not None else time.monotonic()+12*3600
    # Terminal status is written before final sync. Require two matching inventories,
    # then an ETag-bound download, then one unchanged post-download snapshot.
    while True:
        if time.monotonic()>=deadline: raise TimeoutError('Collector deadline reached; no final result published')
        try:
            status,etag=get_status(client,prefix,run_id)
            print(json.dumps({'run_id':run_id,'state':status['state'],'updated_utc':status['updated_utc'],'elapsed_seconds':status['elapsed_seconds']}),flush=True)
            if status['state'] not in TERMINAL:
                if not wait: return status
                remaining_pause(deadline);continue
            before=inventory(client,prefix,out)
            remaining_pause(deadline)
            confirmed,confirmed_etag=get_status(client,prefix,run_id)
            stable=inventory(client,prefix,out)
            if confirmed_etag!=etag or confirmed['state']!=status['state'] or stable!=before:
                raise PendingCollection('Terminal status or inventory is still changing')
            required={'bundle_manifest.json','launch_receipt.json','cloud_status.json'}
            if status['state']=='COMPLETED':
                required|={'outputs/generation_complete.json','outputs/pilot_completion.json',
                           'outputs/test_completion.json','outputs/technical.json'}
            if not required.issubset({o['name'] for o in stable}):
                raise PendingCollection('Final artifacts have not arrived')
            receipts=download_snapshot(client,prefix,stable,out)
            final,final_etag=get_status(client,prefix,run_id)
            if final_etag!=etag or inventory(client,prefix,out)!=stable:
                raise PendingCollection('Artifacts changed during collection; retrying a complete snapshot')
            manifest=json.loads((out/'bundle_manifest.json').read_text())
            launch=json.loads((out/'launch_receipt.json').read_text())
            if not isinstance(manifest.get('commit'),str) or manifest['commit'][:10]!=run_id.removeprefix('fp006-logic-'):
                raise ValueError('Manifest commit does not identify requested run')
            if launch.get('run_id')!=run_id or launch.get('git_commit')!=manifest['commit']:
                raise ValueError('Launch receipt identity mismatch')
            study_prefix='code/final_praxis/006_cognitive_expert_containment/logic_qualification_fp32/'
            for name in ('audit.py','protocol.json','data.json','PREREGISTRATION.md'):
                if digest(HERE/name)!=manifest['files'][study_prefix+name]:
                    raise ValueError('Local audit inputs differ from frozen cloud bundle: '+name)
            if final.get('preregistration_sha256')!=digest(HERE/'PREREGISTRATION.md'):
                raise ValueError('Cloud preregistration identity mismatch')
            local_cells={p.relative_to(out).as_posix() for p in (out/'outputs/cells').glob('*.json')}
            remote_cells={o['name'] for o in stable if o['name'].startswith('outputs/cells/') and o['name'].endswith('.json')}
            if local_cells!=remote_cells: raise ValueError('Local cells contain artifacts outside the stable remote snapshot')
            result=subprocess.run([sys.executable,str(HERE/'audit.py'),'--run-dir',str(out/'outputs'),'--data',str(HERE/'data.json'),
                '--protocol',str(HERE/'protocol.json'),'--technical',str(out/'outputs/technical.json'),
                '--report-dir',str(out/'independent_audit')],check=False,timeout=120)
            audit=json.loads((out/'independent_audit/audit.json').read_text())
            if final['state']=='COMPLETED' and (audit.get('status')!='COMPLETE' or audit.get('validated_unique_cells')!=816):
                raise PendingCollection('Cloud completed but independent full-cohort audit is incomplete or invalid')
            receipt={'run_id':run_id,'source_commit':manifest['commit'],'source_prefix':'s3://'+BUCKET+'/'+prefix,
                'cloud_state':final['state'],'cloud_status_etag':final_etag,'stable_inventory_verified':True,
                'independent_audit_exitcode':result.returncode,'files':receipts}
            write(out/'collection_receipt.json',receipt)
            return receipt
        except (ValueError,KeyError) as error:
            # Frozen identity/schema mismatches are not network failures and are never retried away.
            raise
        except Exception as error:
            print(json.dumps({'event':'COLLECTION_RETRY','error_type':type(error).__name__,'detail':str(error)[:200]}),flush=True)
            if not wait or time.monotonic()>=deadline: raise
            remaining_pause(deadline,60)


def semantic_audit(value):
    """Compare substantive results while retaining the original audit timestamp."""
    result=json.loads(json.dumps(value))
    result.pop('audit_utc',None)
    for item in result.get('input_receipts',[]):
        name=item.get('file','').replace('\\','/')
        if name.startswith('/') or re.match(r'^[A-Za-z]:/',name):
            item['file']=name.rsplit('/',1)[-1]
    return result


def publish_completion(out,receipt,deadline=None):
    """Publish only this run's derived review and provenance to its existing branch."""
    deadline=deadline if deadline is not None else time.monotonic()+12*3600
    if receipt.get('cloud_state') not in TERMINAL or receipt.get('stable_inventory_verified') is not True:
        raise ValueError('Only a stable terminal cloud run may publish its final review')
    root=HERE.parents[2];branch='Final-Praxis-006-Cognitive-Expert-Containment'
    def git(*args): return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
    if git('branch','--show-current')!=branch: raise ValueError('Unexpected publication branch')
    relative=HERE.relative_to(root).as_posix()
    targets=[relative+'/completed/RESULTS.md',relative+'/completed/AUDIT.json',relative+'/completed/ARTIFACTS.json',relative+'/STATUS.md']
    staged=set(filter(None,git('diff','--cached','--name-only').splitlines()))
    if staged-set(targets): raise ValueError('Unrelated staged edits; final audit preserved locally')
    if not (out/'independent_audit/audit.json').is_file(): raise ValueError('Independent audit missing')
    result=json.loads((out/'independent_audit/audit.json').read_text())
    if receipt['cloud_state']=='COMPLETED':
        if result.get('status')!='COMPLETE' or result.get('validated_unique_cells')!=816 or result.get('all_technical_checks') is not True or receipt.get('independent_audit_exitcode')!=0:
            raise ValueError('A completed cloud run requires all 816 cells and technical validity')
    else:
        qualification=result.get('qualification',{})
        if qualification.get('passed') is not False or qualification.get('decision')!='DO_NOT_ADVANCE_CURRENT_QUALIFICATION':
            raise ValueError('A failed or interrupted cloud run can never publish a passing qualification')
        if result.get('status') not in ('COMPLETE','PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY') or receipt.get('independent_audit_exitcode') not in (0,2):
            raise ValueError('Failed-run publication requires a valid negative or incomplete audit')
    if result['protocol_sha256']!=digest(HERE/'protocol.json'): raise ValueError('Audit protocol mismatch')
    destination=HERE/'completed';destination.mkdir(exist_ok=True)
    audit_path=destination/'AUDIT.json'
    artifacts_path=destination/'ARTIFACTS.json'
    if artifacts_path.exists() and json.loads(artifacts_path.read_text()).get('run_id')!=receipt['run_id']:
        raise ValueError('Existing completion belongs to another run')
    if audit_path.exists():
        if not artifacts_path.exists(): raise ValueError('Existing audit has no run provenance')
        existing=json.loads(audit_path.read_text())
        if semantic_audit(existing)!=semantic_audit(result):
            raise ValueError('Existing completion differs substantively; inspect instead of overwriting')
        # Preserve original audit timestamp and artifact provenance on push retries.
    else:
        write(artifacts_path,receipt)
        shutil.copyfile(out/'independent_audit/audit.json',audit_path)
    shutil.copyfile(out/'independent_audit/RESULTS.md',destination/'RESULTS.md')
    (HERE/'STATUS.md').write_text('# Logic qualification: final automated review\n\n'
        +'Run `'+receipt['run_id']+'` ended with cloud state **'+receipt['cloud_state']+'**. '
        +'The independently recomputed review is **'+result['qualification']['decision']+'**.\n\n'
        +'**Cohort status:** '+result['status']+'. **Validated cells:** '+str(result['validated_unique_cells'])+'/816.\n\n'
        +('The final review preserves the failed or interrupted experiment; it does not qualify this study for continuation. The `completed/` folder denotes a completed review, not a completed experiment.\n\n' if receipt['cloud_state']!='COMPLETED' else '')
        +'Read [completed/RESULTS.md](completed/RESULTS.md) for all arm scores, uncertainty, integrity checks and continuation criteria. '
        +'[completed/ARTIFACTS.json](completed/ARTIFACTS.json) preserves source pins and private artifact hashes.\n\n'
        +'This is a useful-specialist prerequisite, with no novel containment or primary-Praxis selection claim. '
        +'The cloud supervisor requests early shutdown after its final upload; its external eight-hour stop watchdog remains a backstop.\n',encoding='utf-8')
    subprocess.run(['git','add','--',*targets],cwd=root,check=True)
    if git('diff','--cached','--name-only','--',*targets):
        subprocess.run(['git','commit','-m','Record automated MiCRo logic qualification results','--',*targets],cwd=root,check=True)
    for attempt in range(30):
        if time.monotonic()>=deadline: raise TimeoutError('Collector publication deadline reached; local commit is preserved')
        try:
            pushed=subprocess.run(['git','push','origin',branch],cwd=root,check=False,timeout=min(120,max(1,deadline-time.monotonic())))
        except subprocess.TimeoutExpired:
            pushed=subprocess.CompletedProcess(['git','push'],124)
        if pushed.returncode==0: break
        if attempt==29: raise RuntimeError('Git push unavailable; committed final audit is preserved locally')
        print(json.dumps({'event':'PUBLICATION_CONNECTION_RETRY','attempt':attempt+1}),flush=True)
        remaining_pause(deadline,60)
    write(out/'publication_receipt.json',{'branch':branch,'commit':git('rev-parse','HEAD'),'run_id':receipt['run_id']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--out',required=True,type=Path);p.add_argument('--wait',action='store_true');p.add_argument('--publish',action='store_true')
    a=p.parse_args();deadline=time.monotonic()+12*3600
    receipt=collect(a.run_id,a.out.resolve(),a.wait,deadline)
    if a.publish and 'files' in receipt: publish_completion(a.out.resolve(),receipt,deadline)
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'},default=str))
