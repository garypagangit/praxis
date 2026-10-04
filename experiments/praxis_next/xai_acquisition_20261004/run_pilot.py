import argparse, json, time, platform
from pathlib import Path
import numpy as np
import lightgbm as lgb

def explain(model,X,p):
    out=np.empty((len(X),10),np.float32); pe=ae=0.
    for lo in range(0,len(X),20000):
        sl=slice(lo,min(lo+20000,len(X))); x=X[sl]
        pr=model.predict(x,num_threads=2)
        pe=max(pe,float(np.max(np.abs(pr-p[sl]))))
        c=np.asarray(model.predict(x,pred_contrib=True,num_threads=2)).reshape(len(x),3,11)
        z=c[:,2]-c[:,0]
        raw=model.predict(x,raw_score=True,num_threads=2)
        ae=max(ae,float(np.max(np.abs(z.sum(1)-(raw[:,2]-raw[:,0])))))
        out[sl]=z[:,:10]
    assert pe<1e-5 and ae<1e-7,(pe,ae)
    return out,{'probability_error':pe,'additivity_error':ae}

def designs(X,p,sv,rng):
    raw=np.column_stack([X,p]); shuffled=sv[rng.permutation(len(sv))]
    return {'RAW':raw,'RAW_PADDED':np.column_stack([raw,np.zeros_like(sv)]),
            'XAI':np.column_stack([raw,sv]),'SHUFFLED':np.column_stack([raw,shuffled]),
            'SHAP_ONLY':np.column_stack([p,sv])}

def run(data,out,seeds):
    out.mkdir(parents=True,exist_ok=True); results=[]; audits=[]; timings=[]
    for seed in seeds:
        tick=time.monotonic(); tr=np.load(data/f'train_{seed}.npz'); sv=np.empty_like(tr['X'])
        for fold in range(1,6):
            ix=np.flatnonzero(tr['fold']==fold)
            model=lgb.Booster(model_file=str(data/f'model_{seed}_{fold}.txt'))
            sv[ix],audit=explain(model,tr['X'][ix],tr['p0'][ix]); audits.append({'seed':seed,'split':f'fold{fold}',**audit})
        target=np.where(tr['y']==2,4.,np.where(tr['y']==1,1.,-1.))*(tr['p1'].argmax(1)!=0)
        mats=designs(tr['X'],tr['p0'],sv,np.random.default_rng(seed+17000))
        models={}
        for method,x in mats.items():
            model=lgb.LGBMRegressor(n_estimators=100,num_leaves=9,learning_rate=.05,min_child_samples=30,reg_lambda=1,n_jobs=2,random_state=seed,verbosity=-1,deterministic=True,force_col_wise=True)
            model.fit(x,target); models[method]=model
            model.booster_.save_model(str(out/f'selector_{seed}_{method}.txt'))
        print('FITTED',seed,'target counts',dict(zip(*np.unique(target,return_counts=True))),flush=True)
        for name in ['wilson','harrison']:
            d=np.load(data/f'eval_{name}.npz'); pr=np.load(data/f'pred_{seed}_{name}.npz')
            X,y,case,ep=d['X'],d['y'],d['case'],d['episode']; nc=int(case.max())+1
            p0,p1=pr['p0'],pr['p1']; w0=p0.argmax(1)!=0; w1=p1.argmax(1)!=0
            base=np.zeros(nc,bool); np.logical_or.at(base,case,w0)
            after=np.zeros(nc,bool); np.logical_or.at(after,case,w1)
            exfil=np.zeros(nc,bool); np.logical_or.at(exfil,case,y==2)
            attack=np.zeros(nc,bool); np.logical_or.at(attack,case,y!=0)
            ew=np.zeros(nc,np.int64); np.add.at(ew,case,(y==2)&w1)
            end=np.full(nc,np.inf); np.minimum.at(end,case,d['end'])
            eligible=np.flatnonzero(~base)
            base_ep=np.unique(ep[w0&(ep>=0)])
            full_ep=np.unique(ep[(w0|w1)&(ep>=0)])
            scores={'UNCERTAINTY':np.zeros(nc),'RANDOM':np.random.default_rng(seed+9000).random(nc),'CHRONOLOGICAL':-end}
            np.maximum.at(scores['UNCERTAINTY'],case,1-p0[:,0])
            # Explanations calculated only for eligible cases: no new source values enter.
            ix=np.flatnonzero(~base[case]); model=lgb.Booster(model_file=str(data/f'model_{seed}_final.txt'))
            ev,audit=explain(model,X[ix],p0[ix]); audits.append({'seed':seed,'split':name,**audit})
            for method,mat in designs(X[ix],p0[ix],ev,np.random.default_rng(seed+27000)).items():
                score=np.full(nc,-np.inf); np.maximum.at(score,case[ix],models[method].predict(mat))
                scores[method]=score
            saved={'case':np.arange(nc),'base':base,'history_warn':after,'exfil':exfil,'attack':attack,'history_exfil_warn_rows':ew}
            for method,score in scores.items():
                order=eligible[np.lexsort((eligible,-score[eligible]))]; saved['order_'+method]=order
                for budget in [10,50,200]:
                    selected=order[:budget]; query=np.zeros(nc,bool);query[selected]=True
                    nw=after&query; rowwarn=w0|(query[case]&w1)
                    ep_after=np.unique(ep[rowwarn&(ep>=0)])
                    r={'seed':seed,'execution':name,'method':method,'budget':budget,'queries':len(selected),
                       'new_warning_cases':int(nw.sum()),'new_exfil_cases':int((nw&exfil).sum()),
                       'new_benign_only_cases':int((nw&~attack).sum()),
                       'new_other_attack_cases':int((nw&attack&~exfil).sum()),
                       'new_exfil_warn_rows':int(((~w0)&w1&query[case]&(y==2)).sum()),
                       'episode_total':int(np.unique(ep[ep>=0]).size),'baseline_episode_coverage':len(base_ep),
                       'episode_coverage':len(ep_after),'episodes_recovered':int(len(np.setdiff1d(ep_after,base_ep))),
                       'full_history_episode_coverage':len(full_ep),'eligible_cases':len(eligible),
                       'baseline_exfil_warn_rows':int((w0&(y==2)).sum()),'total_exfil_rows':int((y==2).sum())}
                    results.append(r)
            np.savez_compressed(out/f'cases_{seed}_{name}.npz',**saved)
            print('EVAL',seed,name,'episodes',len(base_ep),len(full_ep),'eligible',len(eligible),flush=True)
        timings.append({'seed':seed,'seconds':time.monotonic()-tick})
        (out/'RESULTS.json').write_text(json.dumps(results,indent=2))
        (out/'CHECKS.json').write_text(json.dumps(audits,indent=2))
    import csv
    with (out/'RESULTS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    (out/'ENVIRONMENT.json').write_text(json.dumps({'python':platform.python_version(),'numpy':np.__version__,'lightgbm':lgb.__version__,'timings':timings},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--seeds',type=int,nargs='+',default=[8101,8102,8103]);a=ap.parse_args();run(a.data,a.out,a.seeds)
