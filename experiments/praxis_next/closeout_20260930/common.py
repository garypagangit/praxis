import hashlib,importlib.util,json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
INPUT=Path('C:/w/warning_control_20260930/input')
OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
OUT=Path('C:/w/warning_closeout_20260930')
spec=importlib.util.spec_from_file_location('warning_core',HERE.parent/'warning_control_20260930/common.py')
wc=importlib.util.module_from_spec(spec);spec.loader.exec_module(wc)
STAGES=wc.STAGES
save=wc.save
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify():
    f=json.loads((HERE/'FREEZE.json').read_text())
    for name,h in f['code'].items():assert sha(HERE/name)==h,name
    for name,h in f['inputs'].items():assert sha(name)==h,name
    OUT.mkdir(exist_ok=True)
def identities():return dict(np.load(INPUT/'calibration_identity.npz')),dict(np.load(INPUT/'test_identity.npz'))
def inputs(seed):return dict(np.load(INPUT/f'calibration_{seed}_clean.npz')),dict(np.load(INPUT/f'test_{seed}_clean.npz'))
def policy_prob(inp,policy):return wc.replay(inp,policy,2)[0]
def stage_threshold(p,y,alpha,scope):
    score=1-p[:,0].astype(float);counts=np.bincount(y,minlength=4)
    ts={STAGES[k]:wc.threshold(score[y==k],alpha) for k in [1,2,3]}
    keys=[STAGES[k] for k in [1,2,3] if counts[k] or scope=='all_stages_fail_closed']
    return min((ts[k] for k in keys),default=0.),counts.tolist()
def finite(p):assert np.isfinite(p).all() and (p>=0).all() and (p<=1).all() and np.allclose(p.sum(1),1,atol=1e-6)
def freeze():
    files=[INPUT/(split+'_identity.npz') for split in ['calibration','test']]
    files += [INPUT/f'{split}_{s}_clean.npz' for split in ['calibration','test'] for s in [8101,8102,8103]]
    files += [OLD/f'seed_{s}/oof_training.npz' for s in [8101,8102,8103]]
    files += [HERE.parent/'warning_control_20260930/common.py']
    assert not (HERE/'FREEZE.json').exists()
    save(HERE/'FREEZE.json',{'status':'EXPLORATORY_PRE_RUN_FREEZE','code':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.md']},'inputs':{str(p):sha(p) for p in files},'new_fit_cap':6,'new_paid_allocation':False})
if __name__=='__main__':freeze()
