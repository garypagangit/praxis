"""Register both pilots and freeze input bundle before first model response."""
import hashlib,json,tarfile,datetime,py_compile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIVATE=Path('C:/w/vlm_pilots_20261002')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
    assert not (HERE/'FREEZE.json').exists()
    for p in HERE.glob('*.py'):py_compile.compile(str(p),doraise=True)
    registry=HERE.parent/'REGISTRY.json';r=json.loads(registry.read_text())
    for num,folder,title in [(98,'vlm_gate_20261002','Visual Host Windows as an Additional Warning-Gate Member'),(99,'vlm_stages_20261002','Visual Reconstruction of APT Stages and Transitions')]:
        ident=f'PX-{num:03d}';assert not any(e['id']==ident for e in r['experiments'])
        r['experiments'].append({'id':ident,'directory':folder,'title':title,'status':'REGISTERED_INPUTS_PREPARED_INFERENCE_PENDING',
            'protocol':folder+'/PROTOCOL.md','results':folder+'/FINDINGS.md','novelty':'UNCONFIRMED_LITERATURE_OVERLAP_FOUND',
            'scope':'Bounded exploratory pilot on exposed UNRAVELED data; not independent confirmation'})
    save(registry,r)
    with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
        a.add(HERE/'infer.py',arcname='infer.py')
        for p in sorted((PRIVATE/'inputs').iterdir()):a.add(p,arcname='inputs/'+p.name)
    s=json.loads(Path('C:/w/warning_control_20260930/settings.json').read_text())
    s['prefix']='praxis-next/vlm-pilots/20261002-attempt1/';s['usd_per_hour']=1.006
    s['rate_source']='AWS Pricing GetProducts verified 2026-10-02; Linux shared g5.xlarge us-east-1; effective 2026-09-01; not invoice'
    save(PRIVATE/'settings.json',s)
    paths=list(HERE.glob('*.py'))+[HERE/'cloud.sh',HERE/'PROTOCOL.md',HERE/'PREPARATION.json',HERE.parent/'vlm_stages_20261002/PROTOCOL.md']
    save(HERE/'FREEZE.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FROZEN_BEFORE_INFERENCE',
        'experiments':['PX-098','PX-099'],'model':'Qwen/Qwen2.5-VL-7B-Instruct','revision':'cc594898137f460bfe9f0759e9844b3ce807cfb5',
        'bundle_sha256':sha(PRIVATE/'bundle.tar.gz'),'bundle_bytes':(PRIVATE/'bundle.tar.gz').stat().st_size,
        'runtime_files':{str(p.relative_to(ROOT)):sha(p) for p in paths},'gpu_reserve_usd':2,
        'limitations':['PX099 pages truncated to first 144 five-minute bins and top eight hosts','8192 input-token cap; oversized text inputs skipped and reported','PX098 random sample has zero exfil-positive windows; no population attack recall estimate']})
    print('Registered PX-098 and PX-099; bundle frozen', (PRIVATE/'bundle.tar.gz').stat().st_size)
if __name__=='__main__':main()
