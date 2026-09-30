"""Validate prior calibration decisions and freeze a private cloud payload."""
import hashlib,json,tarfile
from pathlib import Path
import numpy as np
from common import replay,save

HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/warning_control_20260930')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    data=PRIVATE/'input';checks=0
    ci=np.load(data/'calibration_identity.npz');ti=np.load(data/'test_identity.npz')
    assert not np.intersect1d(ci['event_hash'],ti['event_hash']).size
    assert ci['end'].max()<ti['start'].min()
    for path in data.glob('*_8*.npz'):
        probs=np.load(path)['probabilities']
        assert np.all(np.isfinite(probs)) and np.all(probs>=0) and np.all(probs<=1) and np.allclose(probs.sum(2),1,atol=1e-6)
    for s in [8101,8102,8103]:
        for c in ['clean','delayed_unavailable','wrong_host_history']:
            inp=dict(np.load(data/f'calibration_{s}_{c}.npz'))
            for b in [1,2,3]:
                prior=np.load(f'C:/w/praxis_fixes_20260930/seed_{s}/calibration_{c}_b{b}.npz')
                for p in ['entropy','harm']:
                    prob,_,_=replay(inp,p,b)
                    assert np.array_equal(prob.argmax(1),prior[p]),(s,c,b,p)
                    checks+=1
    save(PRIVATE/'CALIBRATION_COMPATIBILITY.json',{'passed':True,'checks':checks,'note':'Prior LabelEncoder was serialized with sklearn 1.7.2; preparation loaded under 1.9.0. All prior entropy/harm calibration hard decisions match; cloud uses only numpy, not serialized estimators.'})
    paths={p.name:p for p in [HERE/'run.py',HERE/'common.py',HERE/'PROTOCOL.md']}
    paths.update({'input/'+p.name:p for p in data.glob('*') if p.is_file()})
    manifest={k:sha(p) for k,p in paths.items()};save(PRIVATE/'CONTENTS.json',manifest)
    with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz',compresslevel=1) as a:
        for k,p in paths.items():a.add(p,arcname=k)
        a.add(PRIVATE/'CONTENTS.json',arcname='CONTENTS.json')
    runtime={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.sh','.md']}
    freeze={'batch':'PX-085--087','bundle_sha256':sha(PRIVATE/'bundle.tar.gz'),'bundle_bytes':(PRIVATE/'bundle.tar.gz').stat().st_size,'runtime_files':runtime,'input_hashes':manifest,'calibration_compatibility_checks':checks,'preparation_checks':json.loads((data/'PREPARATION.json').read_text())['checks'],'status':'EXPLORATORY_FROZEN_BEFORE_CLOUD_REPLAY','workers':2,'cloud_allocation_max_seconds':2700,'planning_reserve_usd':2}
    save(HERE/'FREEZE.json',freeze);print(json.dumps({'bytes':freeze['bundle_bytes'],'checks':checks,'sha256':freeze['bundle_sha256']}))
if __name__=='__main__':main()
