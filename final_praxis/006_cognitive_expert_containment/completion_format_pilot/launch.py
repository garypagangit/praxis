"""Build the committed study, install an AWS stop watchdog, then launch detached."""
from __future__ import annotations
import argparse, hashlib, json, shlex, subprocess, sys, time, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SHARED=ROOT/'final_praxis/shared_20260912'
sys.path.insert(0,str(SHARED));sys.path.insert(0,str(HERE))
import cloud_control as cloud
from model_loader import verify_bundle

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,default=str)+'\n',encoding='utf-8')

def build(artifacts, directory):
    verify_bundle(artifacts/'source')
    subprocess.run([sys.executable,str(HERE/'run_study.py'),'--out',str(directory/'preflight'),'--artifacts',str(artifacts),'--preflight-only'],check=True,capture_output=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(HERE),'-p','test_*.py'],check=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    changed=subprocess.check_output(['git','status','--porcelain','--',str(HERE),str(SHARED/'supervisor.py')],cwd=ROOT,text=True)
    if changed.strip(): raise ValueError('Study/runtime must be committed before bundling')
    run_id='fp006-format-'+commit[:10]
    archive=directory/(run_id+'.zip')
    if archive.exists(): raise ValueError('Bundle already exists; inspect saved launch before retrying')
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    study_prefix=HERE.relative_to(ROOT).as_posix()+'/'
    files={('code/'+name):(ROOT/name) for name in tracked if name.startswith(study_prefix)}
    files['code/final_praxis/shared_20260912/supervisor.py']=SHARED/'supervisor.py'
    for part in ('source','tokenizer'):
        for path in (artifacts/part).rglob('*'):
            if path.is_file(): files['artifacts/'+path.relative_to(artifacts).as_posix()]=path
    manifest={}
    for name,path in files.items():
        if path.is_symlink() or path.stat().st_size>25_000_000 or '__pycache__' in path.parts: raise ValueError('Invalid source bundle file')
        manifest[name]=sha(path)
    directory.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
        for name,path in sorted(files.items()): bundle.write(path,name)
        bundle.writestr('bundle_manifest.json',json.dumps({'commit':commit,'files':manifest},indent=2))
    return {'run_id':run_id,'git_commit':commit,'archive':str(archive),'archive_sha256':sha(archive),
            'bundle_key':cloud.PREFIX+'bundles/'+archive.name,'prereg_sha256':sha(HERE/'PREREGISTRATION.md'),
            'protocol_sha256':sha(HERE/'protocol.json'),'instance':cloud.HOSTS['005'],'runtime_hours':2,'total_usd_cap':15}

def deploy_script(plan):
    # Only validated hexadecimal commit/run/hash values enter shell strings.
    run_id=plan['run_id'];runroot='/mnt/praxis-20260912-005/'+run_id
    metadata=json.dumps({**plan,'runroot':runroot,'bucket':cloud.BUCKET})
    return '''set -eu
scratch=/mnt/praxis-20260912-005
mountpoint -q "$scratch"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,json,shutil,zipfile
from pathlib import Path
meta=json.loads('''+repr(metadata)+''')
root=Path(meta['runroot'])
if root.exists(): raise RuntimeError('Existing remote run: inspect before duplicate launch')
if shutil.disk_usage(root.parent).free < 30*1024**3: raise RuntimeError('Need30GiB free scratch for bounded setup')
root.mkdir()
archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file(meta['bucket'],meta['bundle_key'],str(archive))
if hashlib.sha256(archive.read_bytes()).hexdigest()!=meta['archive_sha256']: raise RuntimeError('Archive hash mismatch')
with zipfile.ZipFile(archive) as z:
    if not all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist()): raise RuntimeError('Unsafe archive path')
    z.extractall(root)
manifest=json.loads((root/'bundle_manifest.json').read_text())
for name,expected in manifest['files'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected: raise RuntimeError('Extracted hash mismatch: '+name)
(root/'launch_receipt.json').write_text(json.dumps(meta,indent=2)+'\\n')
PY
systemd-run --unit='''+shlex.quote(run_id)+''' --property=RuntimeMaxSec=6600 --property=WorkingDirectory='''+shlex.quote(runroot)+''' --setenv=PYTHONUNBUFFERED=1 /bin/bash '''+shlex.quote(runroot+'/code/final_praxis/006_cognitive_expert_containment/completion_format_pilot/cloud_entry.sh')+' '+shlex.quote(runroot)+' '+shlex.quote(plan['prereg_sha256'])+'''
systemctl is-active '''+shlex.quote(run_id)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--execution-dir',type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args();directory=a.execution_dir.resolve()
    plan=build(a.artifacts.resolve(),directory);write(directory/'launch_plan.json',plan)
    script=directory/'deploy.sh';script.write_text(deploy_script(plan),encoding='utf-8')
    if not a.execute: print(json.dumps({'status':'BUILT_NOT_STARTED',**plan}));return
    cloud.transfer('upload',plan['archive'],plan['bundle_key'])
    cloud.start('005',HERE/'PREREGISTRATION.md',2)
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        info=cloud.client('ssm').describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[plan['instance']]}])['InstanceInformationList']
        if any(row['PingStatus']=='Online' for row in info): break
        time.sleep(15)
    else:
        cloud.client('ec2').stop_instances(InstanceIds=[plan['instance']]);raise TimeoutError('SSM unavailable; stopped host')
    command=cloud.client('ssm').send_command(InstanceIds=[plan['instance']],DocumentName='AWS-RunShellScript',
        Parameters={'commands':[script.read_text()],'executionTimeout':['600']},TimeoutSeconds=120,
        Comment='Authorized option006 completion format pilot',OutputS3BucketName=cloud.BUCKET,OutputS3KeyPrefix=cloud.PREFIX+'ssm')
    plan['command_id']=command['Command']['CommandId'];write(directory/'launch_receipt.json',plan)
    print(json.dumps({'status':'DEPLOYMENT_SUBMITTED',**plan}),flush=True)
    deadline=time.monotonic()+660
    while time.monotonic()<deadline:
        try:
            invocation=cloud.client('ssm').get_command_invocation(CommandId=plan['command_id'],InstanceId=plan['instance'])
        except cloud.client('ssm').exceptions.InvocationDoesNotExist:
            time.sleep(5);continue
        if invocation['Status'] in ('Pending','InProgress','Delayed'):
            time.sleep(5);continue
        write(directory/'deployment_result.json',invocation)
        if invocation['Status']!='Success':
            cloud.client('ec2').stop_instances(InstanceIds=[plan['instance']])
            raise RuntimeError('Deployment failed; host stopped. Inspect deployment_result.json')
        # A briefly active systemd unit alone does not establish supervisor startup.
        heartbeat_deadline=time.monotonic()+180
        s3=cloud.client('s3')
        while time.monotonic()<heartbeat_deadline:
            try:
                response=s3.get_object(Bucket=cloud.BUCKET,Key=cloud.PREFIX+'runs/'+plan['run_id']+'/cloud_status.json')
                status=json.loads(response['Body'].read())
                if status.get('run_id')!=plan['run_id'] or status.get('preregistration_sha256')!=plan['prereg_sha256']:
                    raise ValueError('Supervisor heartbeat identity mismatch')
                write(directory/'initial_supervisor_status.json',status)
                print(json.dumps({'status':'SUPERVISOR_HEARTBEAT_VERIFIED','run_id':plan['run_id'],'state':status['state']}),flush=True)
                return
            except s3.exceptions.NoSuchKey:
                time.sleep(10)
        cloud.client('ec2').stop_instances(InstanceIds=[plan['instance']])
        raise RuntimeError('Supervisor heartbeat missing after deployment; requested host stop')
    raise TimeoutError('Deployment status unknown; watchdog remains active, inspect SSM before retrying')

if __name__=='__main__': main()
