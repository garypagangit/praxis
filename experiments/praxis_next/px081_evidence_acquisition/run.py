"""PX-081: frozen offline evidence-acquisition development replay."""
from __future__ import annotations
import argparse, hashlib, json, time, warnings
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, average_precision_score, roc_auc_score

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
DEFAULT_OUTPUT = Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
SEEDS = (8101,8102,8103)
POLICIES = ('none','roles_first','history_first','random','entropy','harm')
CONDITIONS = ('clean','delayed_unavailable','wrong_host_history')
CLASSES = ('benign','other_attack','movement','exfiltration')
COST = np.array([1.,2.]); NOMINAL = np.array([.25,.75]); WEIGHTS = np.array([1.,1.,4.,4.])
TRANSITIONS = ((0,0),(0,1),(1,1),(2,0))

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()

def write(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def utc(): return datetime.now(timezone.utc).isoformat()

def entropy(p): return -np.sum(p*np.log(np.maximum(p,1e-15)),axis=1)

def stage_loss(y,p): return WEIGHTS[y]*(np.argmax(p,axis=1)!=y)

def subset_x(data,idx,state,wrong=False):
    xs=[data['current'][idx].astype(np.float32)]
    if state&1: xs.append(data['roles'][idx].astype(np.float32))
    if state&2: xs.append(data['wrong_history' if wrong else 'history'][idx].astype(np.float32))
    return np.concatenate(xs,axis=1)

def observed_x(data,idx,state,probs,wrong=False):
    return np.concatenate([subset_x(data,idx,state,wrong),probs.astype(np.float32)],axis=1)

def capped(indices,y,seed):
    rng=np.random.default_rng(seed); selected=[]
    for cls,cap in enumerate((12000,4000,4000,4000)):
        ids=indices[y[indices]==cls]
        selected.extend(rng.choice(ids,min(len(ids),cap),replace=False))
    return np.sort(np.asarray(selected,dtype=np.int64))

def classifier(seed):
    return LGBMClassifier(n_estimators=150,num_leaves=15,learning_rate=.05,min_child_samples=10,
        reg_lambda=1.,n_jobs=2,random_state=seed,verbosity=-1)

def regressor(seed):
    return LGBMRegressor(n_estimators=100,num_leaves=9,learning_rate=.05,min_child_samples=20,
        reg_lambda=1.,n_jobs=2,random_state=seed,verbosity=-1)

def predict(model,x):
    out=np.zeros((len(x),4),dtype=np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning); p=model.predict_proba(x)
    out[:,model.classes_.astype(int)]=p
    return out

def schedule(keys,seed,condition):
    # Schedule draws depend on event hash, seed and channel, never labels.
    n=len(keys); u=np.empty((n,2,2)); order=np.empty((n,2))
    for i,key in enumerate(keys):
        for channel in range(2):
            b=hashlib.sha256(f'PX081|{seed}|{key}|{channel}'.encode()).digest()
            u[i,channel,0]=int.from_bytes(b[:8],'big')/2**64
            u[i,channel,1]=int.from_bytes(b[8:16],'big')/2**64
            order[i,channel]=int.from_bytes(b[16:24],'big')/2**64
    if condition=='delayed_unavailable':
        available=u[:,:,0]<np.array([.8,.65])
        extra=np.where(u[:,:,1]<.6,0.,np.where(u[:,:,1]<.85,.5,1.5))
        delays=NOMINAL+extra
    else:
        available=np.ones((n,2),dtype=bool); delays=np.broadcast_to(NOMINAL,(n,2)).copy()
    return available,delays,order

def replay(policy,gains,available,delays,random_order,budget,condition,deadline=1.):
    """No feature values, labels, unacquired probabilities or future draws feed selection.

    Realized availability/delay is inspected only after a channel is chosen.
    """
    n=len(available); state=np.zeros(n,dtype=np.uint8); attempted=np.zeros(n,dtype=np.uint8)
    spent=np.zeros(n,dtype=np.float32); elapsed=np.zeros(n,dtype=np.float32)
    actions=np.full((n,2),-1,dtype=np.int8)
    success_prior=np.array([.8,.65]) if condition=='delayed_unavailable' else np.ones(2)
    for step in range(2):
        eligible=np.stack([((attempted&(1<<g))==0)&(spent+COST[g]<=budget)&
            (elapsed+NOMINAL[g]<=deadline+1e-7) for g in range(2)],axis=1)
        if policy=='none': scores=np.full((n,2),-np.inf)
        elif policy=='roles_first': scores=np.broadcast_to([2.,1.],(n,2)).copy()
        elif policy=='history_first': scores=np.broadcast_to([1.,2.],(n,2)).copy()
        elif policy=='random': scores=random_order.copy()
        else:
            scores=np.stack([gains[policy][state,np.arange(n),g] for g in range(2)],axis=1)
            scores=scores*success_prior/COST
        scores=np.where(eligible,scores,-np.inf)
        chosen=np.argmax(scores,axis=1); best=np.max(scores,axis=1)
        ids=np.flatnonzero(np.isfinite(best)&(best>0))
        if not len(ids): break
        g=chosen[ids]; actions[ids,step]=g; attempted[ids]|=(1<<g).astype(np.uint8)
        spent[ids]+=COST[g]; elapsed[ids]+=delays[ids,g]
        arrived=available[ids,g]&(elapsed[ids]<=deadline+1e-7)
        state[ids[arrived]]|=(1<<g[arrived]).astype(np.uint8)
    return dict(state=state,attempted=attempted,spent=spent,elapsed=elapsed,actions=actions)

def metrics(y,p,trace):
    pred=np.argmax(p,axis=1); cm=confusion_matrix(y,pred,labels=np.arange(4))
    prec,rec,f1,_=precision_recall_fscore_support(y,pred,labels=np.arange(4),zero_division=0)
    out={'n':len(y),'confusion':cm.tolist(),'macro_f1':float(f1.mean()),'errors':int((pred!=y).sum()),
         'weighted_error_total':float(stage_loss(y,p).sum()),'benign_false_alerts':int(cm[0,1:].sum()),
         'movement_missed':int(cm[2].sum()-cm[2,2]),'exfiltration_missed':int(cm[3].sum()-cm[3,3]),
         'movement_as_exfiltration':int(cm[2,3]),'mean_spend':float(trace['spent'].mean()),
         'mean_elapsed':float(trace['elapsed'].mean()),'query_rate':float((trace['attempted']>0).mean()),
         'mean_queries':float(((trace['actions']>=0).sum(axis=1)).mean()),
         'mean_delivered':float(((trace['state']&1)>0).mean()+((trace['state']&2)>0).mean())}
    for c,name in enumerate(CLASSES):
        binary=y==c
        out[name]={'support':int(binary.sum()),'precision':float(prec[c]),'recall':float(rec[c]),'f1':float(f1[c]),
             'ap':float(average_precision_score(binary,p[:,c])) if binary.any() and (~binary).any() else None,
             'roc_auc':float(roc_auc_score(binary,p[:,c])) if binary.any() and (~binary).any() else None}
    return out

def freeze(input_path):
    sources={p.name:sha(p) for p in [HERE/'run.py',HERE/'audit.py',HERE/'test_px081.py',HERE/'PROTOCOL.md']}
    receipt={'experiment':'PX-081','frozen_at':utc(),'status':'FROZEN_BEFORE_FITS',
             'input_sha256':sha(input_path),'source_sha256':sources,'seeds':list(SEEDS),
             'classes':list(CLASSES),'stage_error_weights':WEIGHTS.tolist(),'costs':COST.tolist(),
             'nominal_delays':NOMINAL.tolist(),'deadline':1.,'budgets':[1,2,3],
             'conditions':list(CONDITIONS),'policies':list(POLICIES),'compute':'CPU LightGBM; AWS if available'}
    path=HERE/'FREEZE.json'
    if path.exists(): raise RuntimeError('Existing freeze must not be overwritten')
    write(path,receipt); print(json.dumps(receipt,indent=2),flush=True)

def run(input_path,out):
    started=utc(); timer=time.monotonic(); frozen=json.loads((HERE/'FREEZE.json').read_text())
    assert sha(input_path)==frozen['input_sha256']
    for name,digest in frozen['source_sha256'].items(): assert sha(HERE/name)==digest,name
    out.mkdir(parents=True,exist_ok=True)
    if (out/'RUN_RECEIPT.json').exists(): raise RuntimeError('Refuse to overwrite completed run')
    d=dict(np.load(input_path,allow_pickle=False)); y=d['y']; cap=d['capture']; split=d['split']
    assert np.max(d['end'][split==0])<np.min(d['start'][split==1])
    assert np.max(d['end'][split==1])<np.min(d['start'][split==2])
    assert np.all((d['latest_history_end']<d['start'])|(d['latest_history_end']<0))
    assert np.all((d['latest_wrong_history_end']<d['start'])|(d['latest_wrong_history_end']<0))
    train=np.flatnonzero(split==0); test=np.flatnonzero(split==2); oof=np.flatnonzero((cap>=1)&(cap<=4))
    np.savez_compressed(out/'evaluation_identity.npz',y=y[test],capture=cap[test],event_hash=d['group_sha256'][test])
    rows=[]; strata=[]; fit_log=[]
    for seed in SEEDS:
        print(f'Seed {seed}: forward OOF classifiers',flush=True)
        seedout=out/f'seed_{seed}'; seedout.mkdir(exist_ok=True)
        oofprob=np.zeros((4,len(y),4),dtype=np.float32)
        for validcapture in (1,2,3,4):
            base=np.flatnonzero(cap<validcapture); valid=np.flatnonzero(cap==validcapture)
            assert np.max(d['end'][base])<np.min(d['start'][valid])
            selected=capped(base,y,seed+validcapture)
            fit_log.append({'seed':seed,'kind':'forward_oof','fit_captures':list(range(validcapture)),
                'evaluation_capture':validcapture,'fit_n':len(selected),'evaluation_n':len(valid),
                'fit_class_counts':np.bincount(y[selected],minlength=4).tolist()})
            for state in range(4):
                model=classifier(seed); model.fit(subset_x(d,selected,state),y[selected])
                oofprob[state,valid]=predict(model,subset_x(d,valid,state))
        print(f'Seed {seed}: selectors and final classifiers',flush=True)
        selection=capped(oof,y,seed+100); selectors={}
        for state,channel in TRANSITIONS:
            targetstate=state|(1<<channel); before=oofprob[state,selection]; after=oofprob[targetstate,selection]
            x=observed_x(d,selection,state,before)
            for method,target in [('harm',stage_loss(y[selection],before)-stage_loss(y[selection],after)),
                                  ('entropy',entropy(before)-entropy(after))]:
                model=regressor(seed); model.fit(x,target); selectors[method,state,channel]=model
        np.savez_compressed(seedout/'oof_training.npz',indices=selection,y=y[selection],capture=cap[selection],
            probabilities=oofprob[:,selection],selection_event_hash=d['group_sha256'][selection])
        final={}; fitidx=capped(train,y,seed)
        for state in range(4):
            model=classifier(seed); model.fit(subset_x(d,fitidx,state),y[fitidx]); final[state]=model
        joblib.dump({'classifiers':final,'selectors':selectors,'fit_indices':fitidx},seedout/'models.joblib',compress=3)
        for condition in CONDITIONS:
            print(f'Seed {seed}: replay {condition}',flush=True)
            wrong=condition=='wrong_host_history'
            probs=np.stack([predict(final[s],subset_x(d,test,s,wrong)) for s in range(4)])
            gains={method:np.full((4,len(test),2),-np.inf,dtype=np.float32) for method in ('entropy','harm')}
            for state,channel in TRANSITIONS:
                x=observed_x(d,test,state,probs[state],wrong)
                for method in gains:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore',UserWarning)
                        gains[method][state,:,channel]=selectors[method,state,channel].predict(x)
            available,delays,order=schedule(d['group_sha256'][test],seed,condition)
            np.savez_compressed(seedout/f'{condition}_inputs.npz',probabilities=probs,available=available,
                delays=delays,random_order=order,harm_gains=gains['harm'],entropy_gains=gains['entropy'])
            for budget in (1,2,3):
                for policy in POLICIES:
                    trace=replay(policy,gains,available,delays,order,budget,condition)
                    p=probs[trace['state'],np.arange(len(test))]
                    np.savez_compressed(seedout/f'{condition}_b{budget}_{policy}.npz',probabilities=p,**trace)
                    metadata={'seed':seed,'condition':condition,'budget':budget,'policy':policy,'reference_only':False}
                    rows.append({**metadata,**metrics(y[test],p,trace)})
                    for c in np.unique(cap[test]):
                        mask=cap[test]==c
                        strata.append({**metadata,'capture':int(c),**metrics(y[test][mask],p[mask],{k:v[mask] for k,v in trace.items()})})
            trace=dict(state=np.full(len(test),3,dtype=np.uint8),attempted=np.full(len(test),3,dtype=np.uint8),
                spent=np.full(len(test),3.,dtype=np.float32),elapsed=np.zeros(len(test),dtype=np.float32),
                actions=np.broadcast_to([0,1],(len(test),2)).copy())
            rows.append({'seed':seed,'condition':condition,'budget':None,'policy':'full_context_reference','reference_only':True,
                **metrics(y[test],probs[3],trace)})
            write(HERE/'RESULTS.json',rows); write(HERE/'CAPTURE_RESULTS.json',strata)
    write(out/'FIT_LOG.json',fit_log)
    write(HERE/'FIT_LOG.json',fit_log)
    receipt={'experiment':'PX-081','started':started,'completed':utc(),'wall_seconds':time.monotonic()-timer,
        'compute':'local CPU','input_sha256':sha(input_path),'freeze_sha256':sha(HERE/'FREEZE.json'),
        'fit_n':len(train),'calibration_n_unused':int((split==1).sum()),'evaluation_n':len(test),
        'evaluation_class_counts':np.bincount(y[test],minlength=4).tolist(),
        'classifier_fits':60,'regressor_fits':24,'result_rows':len(rows),'capture_result_rows':len(strata),
        'prediction_files':len(list(out.rglob('*.npz'))),'simulated_acquisition':True,'independent_campaigns':1,
        'private_output':str(out),'public_hashes':{p.name:sha(p) for p in [HERE/'RESULTS.json',HERE/'CAPTURE_RESULTS.json',HERE/'FIT_LOG.json']}}
    write(out/'RUN_RECEIPT.json',receipt); write(HERE/'RUN_RECEIPT.json',receipt)
    print(json.dumps(receipt,indent=2),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('action',choices=['freeze','run']); a.add_argument('--input',type=Path,default=DEFAULT_INPUT)
    a.add_argument('--output',type=Path,default=DEFAULT_OUTPUT); args=a.parse_args()
    freeze(args.input) if args.action=='freeze' else run(args.input,args.output)
