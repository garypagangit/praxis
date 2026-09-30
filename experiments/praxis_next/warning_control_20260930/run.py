"""Parallel AWS replay of PX-085/086/087. Every arm is retained."""
import argparse, concurrent.futures, json, os, platform, time
from pathlib import Path
import numpy as np
from common import *

POLICIES=['none','roles_first','history_first','entropy','harm','roles_stop50','roles_stop90']
def policy_run(inp,policy,budget):
    stop={'roles_stop50':.5,'roles_stop90':.9}.get(policy)
    return replay(inp,'roles_first' if stop is not None else policy,budget,stop)

def task(params):
    data,out,seed,condition=params;data=Path(data);out=Path(out)
    cal=dict(np.load(data/f'calibration_{seed}_{condition}.npz'));test=dict(np.load(data/f'test_{seed}_{condition}.npz'))
    cid=np.load(data/'calibration_identity.npz');tid=np.load(data/'test_identity.npz');cy=cid['y'];y=tid['y'];cap=tid['capture']
    baselines=[];controlled=[];decomp=[]
    for budget in [1,2,3]:
        reach=reachable(test,budget);warn=test['probabilities'].argmax(2)>0;any_reach=(warn&reach).any(0)
        for policy in POLICIES:
            cp,_,_=policy_run(cal,policy,budget);p,spent,state=policy_run(test,policy,budget)
            assert np.all(reach[state,np.arange(len(y))])
            meta={'seed':seed,'condition':condition,'budget':budget,'policy':policy}
            pred=p.argmax(1);baselines.append({**meta,**metrics(y,pred,spent)})
            controlled.extend(gates(cp,cy,p,y,spent,meta,cap))
            if policy=='harm':
                for k in [1,2,3]:
                    miss=(y==k)&(pred==0);r=miss&any_reach;u=miss&~any_reach
                    assert int(r.sum()+u.sum())==int(miss.sum())
                    decomp.append({**meta,'stage':STAGES[k],'missed':int(miss.sum()),'policy_recoverable':int(r.sum()),'unrecoverable_by_reachable_fitted_experts':int(u.sum()),'all_four_experts_miss':int(((y==k)&~warn.any(0)).sum())})
    dest=out/f'{seed}_{condition}.json';save(dest,{'baselines':baselines,'controlled':controlled,'decomposition':decomp,'worker_pid':os.getpid()})
    return {'job':dest.name,'baseline_rows':len(baselines),'controlled_rows':len(controlled),'pid':os.getpid()}

def ensembles(data,out):
    cid=np.load(data/'calibration_identity.npz');tid=np.load(data/'test_identity.npz');cy=cid['y'];y=tid['y'];cap=tid['capture']
    rows=[];controlled=[];ds=[]
    for condition in ['clean','delayed_unavailable','wrong_host_history']:
        cal=[dict(np.load(data/f'calibration_{s}_{condition}.npz')) for s in [8101,8102,8103]]
        test=[dict(np.load(data/f'test_{s}_{condition}.npz')) for s in [8101,8102,8103]]
        # Same evidence states, all three models. State availability is isolated from this diagnostic.
        for state in range(4):
            cp=np.mean(np.stack([z['probabilities'][state] for z in cal]).astype(np.float64),axis=0)
            stack=np.stack([z['probabilities'][state] for z in test]);p=np.mean(stack.astype(np.float64),axis=0)
            pred=p.argmax(1);sw=stack.argmax(2)>0;union=sw.any(0)
            up=pred.copy();up[union&(up==0)]=1+p[union&(up==0),1:].argmax(1)
            assert np.all((up>0)>=sw)
            spent=np.full(len(y),float(bool(state&1)+2*bool(state&2)))
            meta={'seed':'mean_of_8101_8102_8103','condition':condition,'budget':None,'policy':f'state_{state}_mean','evidence_state':state,'reference_only':condition=='delayed_unavailable','model_evaluations_per_row':3}
            rows.append({**meta,**metrics(y,pred,spent)})
            rows.append({**meta,'policy':f'state_{state}_warning_union',**metrics(y,up,spent)})
            controlled.extend(gates(cp,cy,p,y,spent,meta,cap))
            for k in [1,2,3]:
                stage=y==k
                ds.append({'condition':condition,'state':state,'stage':STAGES[k],
                  'single_seed_misses':[int((stage&~s).sum()) for s in sw],
                  'mean_misses':int((stage&(pred==0)).sum()),'union_misses':int((stage&~union).sum()),
                  'mean_loses_any_seed_warning':int((stage&union&(pred==0)).sum())})
    save(out/'ENSEMBLES.json',{'baselines':rows,'controlled':controlled,'diagnostics':ds,
         'limitation':'same-state ensemble diagnostic; not a free combination of differently acquired evidence; compute cost triples'})

def self_test():
    # A real counterexample to the proposed probability-mean guarantee.
    p=np.array([[.49,.51,0,0],[.99,.01,0,0],[.99,.01,0,0]])
    assert p[0].argmax()!=0 and p.mean(0).argmax()==0
    # Cheapest-first can spend 1 on gain .1 and lose access to cost-2 gain 1 at budget 2.
    assert .1<1 and 1+2>2
    # Exact finite rank check over every leave-one-out exchangeable position; includes ties.
    checks=2
    for scores in [np.linspace(0,1,101), np.repeat([0.,.1,.8,1.],[20,30,20,31])]:
        for alpha in ALPHAS:
            misses=[scores[i]<threshold(np.delete(scores,i),alpha) for i in range(len(scores))]
            assert np.mean(misses)<=alpha+1e-12;checks+=1
    assert threshold([], .05)==0 and threshold([.9],.05)==0;checks+=1
    cp=np.array([[.99,.01,0,0],[.4,.6,0,0]])
    for t in [0,.1,1]: assert np.all(apply_gate(cp,t)[cp.argmax(1)>0]>0);checks+=1
    return checks

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--workers',type=int,default=2);ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
    checks=self_test()
    if a.self_test:print(json.dumps({'passed':True,'checks':checks}));return
    assert 1<=a.workers<=2
    if a.out.exists():raise RuntimeError('Refuse existing output directory')
    a.out.mkdir(parents=True);start=time.monotonic()
    jobs=[(str(a.data),str(a.out),s,c) for s in [8101,8102,8103] for c in ['clean','delayed_unavailable','wrong_host_history']]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        receipts=list(pool.map(task,jobs))
    ensembles(a.data,a.out)
    save(a.out/'COMPLETE.json',{'passed':True,'jobs':receipts,'self_test_checks':checks,'parallel_workers':a.workers,'wall_seconds':time.monotonic()-start,'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),'new_model_fits':0,'gpu_used':False,'data_scope':'previously exposed UNRAVELED development campaign; no independent replication'})
    print(json.dumps({'complete':True,'seconds':time.monotonic()-start,'jobs':len(jobs)}),flush=True)
if __name__=='__main__':main()
