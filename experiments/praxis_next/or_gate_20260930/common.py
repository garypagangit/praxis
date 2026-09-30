import hashlib,json,importlib.util,platform
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/px092_or_gate_20260930')
OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
AIT=Path('C:/w/campaign_validation_20260928')
AE=HERE.parent/'campaign_validation_20260928/evidence'
PX=HERE.parent/'px081_evidence_acquisition'
SEEDS=list(range(8101,8111));CONDS=['clean','delayed_unavailable','wrong_host_history']
NAMES=['benign','other_attack','movement','exfiltration']
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def pxmodule():
    spec=importlib.util.spec_from_file_location('px081_original',PX/'run.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def decisions(p):
    p=np.asarray(p,dtype=np.float64);assert np.isfinite(p).all() and (p>=0).all() and np.allclose(p.sum(2),1,atol=1e-6)
    single=p.argmax(2);warning=single!=0
    stage=1+(p[:,:,1:]*warning[:,:,None]).sum(0).argmax(1)
    return np.where(warning.any(0),stage,0).astype(np.int8),p.mean(0).argmax(1).astype(np.int8),single.astype(np.int8)
def metrics(y,pred,k):
    cm=np.bincount(y.astype(int)*k+pred,minlength=k*k).reshape(k,k);sup=cm.sum(1);den=sup+cm.sum(0)
    out={'n':len(y),'confusion':cm.tolist(),'macro_f1':float(np.divide(2*np.diag(cm),den,out=np.zeros(k),where=den>0).mean()),'false_alerts':int(cm[0,1:].sum()),'benign_fpr':float(cm[0,1:].sum()/sup[0]) if sup[0] else None}
    names=NAMES if k==4 else ['benign','other_attack','exfiltration']
    for i,n in enumerate(names[1:],1):out[n]={'support':int(sup[i]),'missed':int(cm[i,0]),'warning_recall':float(1-cm[i,0]/sup[i]) if sup[i] else None,'exact_recall':float(cm[i,i]/sup[i]) if sup[i] else None}
    return out
def verify():
    f=json.loads((HERE/'FREEZE.json').read_text());import lightgbm
    assert lightgbm.__version__==f['lightgbm_version']
    for p,h in f['files'].items():assert sha(p)==h,p
    return f
def freeze():
    import lightgbm
    assert not (HERE/'FREEZE.json').exists()
    old=json.loads((OLD/'ARTIFACT_HASHES.json').read_text());files=[DATA,OLD/'evaluation_identity.npz',OLD/'ARTIFACT_HASHES.json',PX/'run.py',PX/'FREEZE.json',AE/'ARTIFACTS.json',AE/'FREEZE.json']
    assert sha(DATA)==json.loads((PX/'FREEZE.json').read_text())['input_sha256']
    paths=[OLD/'evaluation_identity.npz']+[OLD/f'seed_{s}/{c}_inputs.npz' for s in SEEDS[:3] for c in CONDS]
    for p in paths:
        key=str(p.relative_to(OLD));assert sha(p)==old[key],key
    files+=paths
    aman={Path(a['path']):a['sha256'] for a in json.loads((AE/'ARTIFACTS.json').read_text())};af=json.loads((AE/'FREEZE.json').read_text())
    for ex in ['wilson','harrison']:
        p=AIT/f'prepared/{ex}.npz';assert sha(p)==af['prepared_files'][ex];files.append(p)
        for s in SEEDS[:3]:
            p=AIT/f'predictions/s{s}_{ex}.npz';assert sha(p)==aman[p];files.append(p)
    files+=list(HERE.glob('*.py'))+list(HERE.glob('*.md'))
    from datetime import datetime,timezone
    save(HERE/'FREEZE.json',{'experiment':'PX-092','status':'FROZEN_BEFORE_EXECUTION','utc':datetime.now(timezone.utc).isoformat(),'lightgbm_version':lightgbm.__version__,'python':platform.python_version(),'new_final_fits':7,'new_oof_fits':0,'shared_schedule_seed':8101,'new_seed_fallback':'current_8101','files':{str(p):sha(p) for p in dict.fromkeys(files)}})
    PRIVATE.mkdir(exist_ok=True);print('FREEZE created',flush=True)
if __name__=='__main__':freeze()
