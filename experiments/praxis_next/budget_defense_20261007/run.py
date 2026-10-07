"""Frozen label-free fusion replay; labels enter only metric evaluation."""
import argparse, hashlib, json, pathlib
import numpy as np
from scipy.stats import rankdata
HERE=pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def policies(scores):
    a=np.stack([rankdata(s,method='average')/len(s) for s in scores])
    return dict(zip(['local','mlp','gin'],scores)) | {'mean':a.mean(0),'minimum':a.min(0),'maximum':a.max(0),'median':np.median(a,axis=0),'local_mlp':a[:2].mean(0),'gin_local':a[[0,2]].mean(0),'gin_mlp':a[1:].mean(0)}
def measure(s,y,f):
    n=len(y); b=int(np.ceil(n*f)); boundary=np.partition(s,n-b)[n-b]
    above=s>boundary; ties=s==boundary
    na=int(above.sum()); nt=int(ties.sum()); ta=int(y[above].sum()); tt=int(y[ties].sum()); need=b-na
    expected=ta+need*tt/nt; lo=ta+max(0,need-(nt-tt)); hi=ta+min(need,tt)
    return dict(n=n,positives=int(y.sum()),budget_fraction=f,budget=b,above=na,ties=nt,above_tp=ta,tie_tp=tt,needed=need,expected_tp=expected,min_tp=lo,max_tp=hi,precision=expected/b,recall=expected/y.sum(),random_precision=float(y.mean()))
def main(root):
    rows=[]; sources={}
    for ds in ['cadets','theia']:
        report=json.loads((root/ds/'RESULTS.json').read_text())
        for seed in [101,211,307]:
            for view in ['clean','drop_0.5_mask_20260920']:
                p=root/ds/'private'/f'predictions_{seed}_{view}.npz'
                digest=sha(p); assert digest==report['private_artifact_sha256'][p.name]; sources[ds+'/'+p.name]=digest
                z=np.load(p); y=z['y']; scores=[z['score_'+m+'_knn'] for m in ['local','mlp','gin']]
                assert set(np.unique(y))=={0,1} and all(np.isfinite(s).all() for s in scores)
                for name,s in policies(scores).items():
                    for f in [.001,.005,.01,.02,.05]: rows.append(dict(dataset=ds,seed=seed,view=view,policy=name,**measure(s,y,f)))
                print(ds,seed,view,flush=True)
    result=dict(scope='Exploratory saved-score replay; no new fitting',sources=sources,code_sha256=sha(pathlib.Path(__file__)),protocol_sha256=sha(HERE/'PROTOCOL.txt'),rows=rows)
    (HERE/'RESULTS.json').write_text(json.dumps(result,indent=2))
    summary=[]
    for ds in ['cadets','theia']:
        for name in policies([np.arange(2)]*3):
            r={v:[x['precision'] for x in rows if x['dataset']==ds and x['policy']==name and x['view']==v and x['budget_fraction']==.01] for v in ['clean','drop_0.5_mask_20260920']}
            summary.append(dict(dataset=ds,policy=name,clean=float(np.mean(r['clean'])),loss=float(np.mean(r['drop_0.5_mask_20260920'])),clean_range=[min(r['clean']),max(r['clean'])],loss_range=[min(r['drop_0.5_mask_20260920']),max(r['drop_0.5_mask_20260920'])]))
    (HERE/'SUMMARY.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--scores',type=pathlib.Path,required=True); main(p.parse_args().scores)
