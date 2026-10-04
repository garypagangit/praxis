from pathlib import Path
import numpy as np, json, hashlib, joblib, shutil, tarfile
HERE=Path(__file__).parent
DATA=Path('C:/w/campaign_validation_20260928')
PRIVATE=Path('C:/w/px107_aws_pilot'); PRIVATE.mkdir(exist_ok=True)
IN=PRIVATE/'input'; IN.mkdir(exist_ok=True)
names=['santos','fox','wardbeck','russellmitchell','shaw','wheeler']
ds={n:dict(np.load(DATA/f'prepared/{n}.npz')) for n in names[1:]+['wilson','harrison']}
sizes=[len(ds[n]['y']) for n in names[1:]]
starts=np.r_[0,np.cumsum(sizes)]
for seed in [8101,8102,8103]:
    o=np.load(DATA/f'predictions/s{seed}_development_oof.npz')
    assert np.array_equal(o['y'],np.concatenate([ds[n]['y'] for n in names[1:]]))
    eligible=np.flatnonzero(o['p0'].argmax(1)==0)
    idx=np.sort(np.random.default_rng(107000+seed).choice(eligible,min(50000,len(eligible)),replace=False))
    X=np.concatenate([ds[n]['current'] for n in names[1:]])[idx]
    fold=np.searchsorted(starts[1:],idx,side='right')+1
    np.savez_compressed(IN/f'train_{seed}.npz',X=X,y=o['y'][idx],p0=o['p0'][idx],p1=o['p1'][idx],fold=fold,row=idx)
    for k in range(1,6):
        joblib.load(DATA/f'models/s{seed}_fold{k}_state0.joblib').booster_.save_model(str(IN/f'model_{seed}_{k}.txt'))
    joblib.load(DATA/f'models/s{seed}_final_state0.joblib').booster_.save_model(str(IN/f'model_{seed}_final.txt'))
    for n in ['wilson','harrison']:
        pr=np.load(DATA/f'predictions/s{seed}_{n}.npz'); d=ds[n]
        assert np.array_equal(pr['y'],d['y']) and np.array_equal(pr['key'],d['key'])
        np.savez_compressed(IN/f'pred_{seed}_{n}.npz',p0=pr['p0'],p1=pr['p1'])
for n in ['wilson','harrison']:
    d=ds[n]; m=np.load(f'C:/w/px094_soc_workload_20261001/{n}_meta.npz')
    assert np.array_equal(d['key'],m['key'])
    tags=np.array([f'{a}|{b}|{int(t//300)}' for a,b,t in zip(m['src'],m['dst'],d['end'])])
    _,case=np.unique(tags,return_inverse=True)
    episode=np.full(len(case),-1,np.int32); nextid=0
    ex=np.flatnonzero(d['y']==2)
    pairs=np.char.add(np.char.add(m['src'][ex],'|'),m['dst'][ex])
    for pair in np.unique(pairs):
        ids=ex[pairs==pair]; ids=ids[np.argsort(d['start'][ids],kind='stable')]
        cuts=np.r_[True,np.diff(d['start'][ids])>1800]
        eid=np.cumsum(cuts)-1+nextid; episode[ids]=eid; nextid=int(eid.max())+1
    np.savez_compressed(IN/f'eval_{n}.npz',X=d['current'],y=d['y'],case=case,episode=episode,key=d['key'],end=d['end'])
source={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(IN.iterdir())}
(HERE/'INPUTS.json').write_text(json.dumps(source,indent=2))
print(json.dumps({'files':len(source),'input_bytes':sum(p.stat().st_size for p in IN.iterdir())}))
