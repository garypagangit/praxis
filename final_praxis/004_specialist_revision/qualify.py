"""Official four-issue SWE-bench BASE/GOLD qualification; no model requests."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, runpy, subprocess, sys, urllib.request
from pathlib import Path

DATASET='princeton-nlp/SWE-bench_Verified'
REVISION='c104f840cc67f8b6eec6f759ebc8b2693d585d4a'

def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FinalPraxis004'}),timeout=60) as response:return response.read(4_000_000)
def comment_patch(source):
    return ('diff --git a/sympy/__init__.py b/sympy/__init__.py\n--- a/sympy/__init__.py\n+++ b/sympy/__init__.py\n'
        '@@ -1 +1,2 @@\n+# Final Praxis004: semantics-preserving BASE qualification control.\n '+source.splitlines()[0]+'\n')

def prepare(out):
    if (out/'manifest.json').exists():
        manifest=json.loads((out/'manifest.json').read_text())
        for rel,expected in manifest['input_hashes'].items():
            if sha((out/rel).read_bytes())!=expected:raise RuntimeError('Frozen input changed: '+rel)
        return manifest
    from datasets import load_dataset
    import swebench
    rows=load_dataset(DATASET,revision=REVISION,split='test')
    chosen=sorted([r for r in rows if r['repo']=='sympy/sympy'],key=lambda r:r['instance_id'])[:4]
    if len(chosen)!=4:raise RuntimeError('Exactly four deterministic issues required')
    out.mkdir(parents=True,exist_ok=True);evaluation=out/'evaluator_only';evaluation.mkdir(exist_ok=True)
    write(evaluation/'instances.json',chosen)
    predictions={'base':[],'gold':[]};sources=[]
    for row in chosen:
        url='https://raw.githubusercontent.com/sympy/sympy/'+row['base_commit']+'/sympy/__init__.py'
        raw=fetch(url);patch=comment_patch(raw.decode())
        sources.append({'instance_id':row['instance_id'],'url':url,'source_sha256':sha(raw),'base_patch_sha256':sha(patch.encode())})
        for arm,change in [('base',patch),('gold',row['patch'])]:
            predictions[arm].append({'instance_id':row['instance_id'],'model_name_or_path':'praxis004_'+arm,'model_patch':change})
    for arm,values in predictions.items():
        (evaluation/(arm+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in values),encoding='utf-8')
    public=[{k:r[k] for k in ['instance_id','repo','base_commit','problem_statement']} for r in chosen]
    write(out/'public_instances.json',public)
    package=Path(swebench.__file__).resolve().parent
    package_hashes={p.relative_to(package).as_posix():sha(p.read_bytes()) for p in package.rglob('*.py')}
    files=['evaluator_only/instances.json','evaluator_only/base.jsonl','evaluator_only/gold.jsonl','public_instances.json']
    manifest={'study':'FinalPraxis004','stage':'BASE_GOLD_qualification','dataset':DATASET,'dataset_revision':REVISION,
        'instance_ids':[r['instance_id'] for r in chosen],'sources':sources,'python':sys.version,
        'swebench':importlib.metadata.version('swebench'),'package_source_hashes':package_hashes,
        'preregistration_sha256':os.environ['PRAXIS_PREREG_SHA256'],'docker_host':os.environ['DOCKER_HOST'],
        'input_hashes':{rel:sha((out/rel).read_bytes()) for rel in files}}
    write(out/'manifest.json',manifest);return manifest

def worker(out,arm):
    import docker.models.containers
    original=docker.models.containers.ContainerCollection.create
    def restricted(self,*args,**kwargs):
        if kwargs.get('privileged') or kwargs.get('mounts') or kwargs.get('volumes'):raise RuntimeError('Unsafe container configuration')
        kwargs.pop('network_mode',None);kwargs.pop('network',None)
        kwargs.update(network_disabled=True,mem_limit=8*1024**3,nano_cpus=2_000_000_000,pids_limit=512,
            privileged=False,cap_drop=['ALL'],security_opt=['no-new-privileges:true'])
        return original(self,*args,**kwargs)
    docker.models.containers.ContainerCollection.create=restricted
    manifest=json.loads((out/'manifest.json').read_text())
    sys.argv=['swebench.harness.run_evaluation','--dataset_name',str(out/'evaluator_only/instances.json'),
        '--predictions_path',str(out/'evaluator_only'/f'{arm}.jsonl'),'--instance_ids',*manifest['instance_ids'],
        '--max_workers','1','--run_id','fp004_qualification_'+arm,'--timeout','900','--namespace','swebench']
    os.chdir(out);runpy.run_module('swebench.harness.run_evaluation',run_name='__main__')

def collect(out,arm,ids):
    found={};reports=[]
    for path in out.rglob('report.json'):
        if 'fp004_qualification_'+arm not in str(path):continue
        data=json.loads(path.read_text());reports.append({'path':str(path.relative_to(out)),'sha256':sha(path.read_bytes())})
        for iid in ids:
            if isinstance(data.get(iid),dict):found[iid]=data[iid]
    return {'arm':arm,'reports':reports,'issues':[{'instance_id':iid,'official_record':found.get(iid),
        'resolved':found.get(iid,{}).get('resolved'),'report_present':iid in found} for iid in ids]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--worker',choices=['base','gold']);a=p.parse_args()
    out=a.output.resolve()
    if a.worker:worker(out,a.worker);return
    if importlib.metadata.version('swebench')!='4.1.0':raise RuntimeError('Pinned evaluator required')
    if not os.environ.get('DOCKER_HOST'):raise RuntimeError('Explicit Docker host required')
    prereg=Path(os.environ['PRAXIS_PREREG_PATH'])
    if sha(prereg.read_bytes())!=os.environ['PRAXIS_PREREG_SHA256']:raise RuntimeError('Preregistration hash mismatch')
    manifest=prepare(out);print(json.dumps({'prepared':manifest['instance_ids'],'revision':REVISION}),flush=True)
    summaries=[]
    for arm in ['base','gold']:
        receipt=out/(arm+'_process.json')
        if not receipt.exists():
            command=[sys.executable,str(Path(__file__).resolve()),'--output',str(out),'--worker',arm]
            with (out/(arm+'_stdout.log')).open('w') as log:
                try:
                    run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=7800,check=False)
                    result={'returncode':run.returncode,'command':command}
                except subprocess.TimeoutExpired:result={'returncode':None,'timeout':True,'command':command}
            write(receipt,result)
        summary=collect(out,arm,manifest['instance_ids']);summary['process']=json.loads(receipt.read_text())
        write(out/(arm+'_summary.json'),summary);summaries.append(summary)
        print(json.dumps({'arm':arm,'reports':len(summary['reports']),'returncode':summary['process']['returncode']}),flush=True)
    qualified=all(r['resolved'] is False for r in summaries[0]['issues']) and all(r['resolved'] is True for r in summaries[1]['issues'])
    result={'stage':'official_BASE_GOLD_qualification','model_calls':0,'qualified':qualified,'arms':summaries,
        'interpretation':'Benchmark/environment controls only; no model or defense efficacy claim.'}
    write(out/'qualification_summary.json',result)
    if not qualified:raise SystemExit(3)

if __name__=='__main__':main()
