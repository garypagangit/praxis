"""PX-082 fixed split-sensitivity measurement. No tuning or winner selection."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
NAMES = ['Benign', 'OtherAttackStage', 'LateralMovement', 'DataExfiltration']

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def write(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def utc(): return datetime.now(timezone.utc).isoformat()

def bindings():
    return {p.name:sha(p) for p in [HERE/'protocol.json',HERE/'run.py',HERE/'test_audit.py']}

def anchor_rows(d):
    rows=[]
    for capture in np.unique(d['capture'][d['split']==2]):
        for k in range(4):
            ix=np.flatnonzero((d['split']==2)&(d['capture']==capture)&(d['y']==k))
            ix=ix[np.argsort(d['group_sha256'][ix],kind='stable')]
            rows.extend(ix[:(len(ix)+1)//2])
    return np.sort(np.asarray(rows,dtype=np.int64))

def fingerprints(x):
    # Qualified finite float64 arrays. Normalize signed zeros before byte hashing.
    a=np.asarray(x,dtype='<f8').copy(); a[a==0]=0
    return np.asarray([hashlib.sha256(row.tobytes()).hexdigest() for row in a])

def sample(d,pool,counts,seed):
    rows=[]
    for k,n in enumerate(counts):
        ix=pool[d['y'][pool]==k]
        if len(ix)<n: raise ValueError('Insufficient matched class support')
        keys=[hashlib.sha256(f'PX082|{seed}|{d["group_sha256"][i]}'.encode()).digest() for i in ix]
        rows.extend(ix[np.argsort(keys)[:n]])
    return np.asarray(rows,dtype=np.int64)

def metric(y,p):
    pred=p.argmax(1)
    pr,re,f,s=precision_recall_fscore_support(y,pred,labels=np.arange(4),zero_division=0)
    normal=(y==0); movement=(y==2)
    return {'rows':len(y),'macro_f1':float(f.mean()),'normal_false_attacks':int(np.sum(normal&(pred!=0))),
            'normal_false_attack_rate':float(np.mean(pred[normal]!=0)) if normal.any() else None,
            'movement_any_attack_recall':float(np.mean(pred[movement]!=0)) if movement.any() else None,
            'confusion':confusion_matrix(y,pred,labels=np.arange(4)).tolist(),
            'per_class':{name:{'support':int(s[k]),'precision':float(pr[k]),'recall':float(re[k]),'f1':float(f[k]),
                'ap':float(average_precision_score(y==k,p[:,k])) if np.any(y==k) else None,
                'roc_auc':float(roc_auc_score(y==k,p[:,k])) if len(np.unique(y==k))==2 else None} for k,name in enumerate(NAMES)}}

def macro_from_confusion(cm):
    den=cm.sum(0)+cm.sum(1)
    return float(np.divide(2*np.diag(cm),den,out=np.zeros(4),where=den>0).mean())

def paired_bootstrap(y,pa,pb,captures,seed):
    groups=np.unique(captures)
    ac=np.asarray([confusion_matrix(y[captures==g],pa[captures==g].argmax(1),labels=np.arange(4)) for g in groups])
    bc=np.asarray([confusion_matrix(y[captures==g],pb[captures==g].argmax(1),labels=np.arange(4)) for g in groups])
    rng=np.random.default_rng(seed); diffs=[]
    for _ in range(1000):
        take=rng.integers(0,len(groups),len(groups))
        diffs.append(macro_from_confusion(bc[take].sum(0))-macro_from_confusion(ac[take].sum(0)))
    return {'difference_mixed_minus_past':macro_from_confusion(bc.sum(0))-macro_from_confusion(ac.sum(0)),
            'conditional_capture_bootstrap_95_interval':np.quantile(diffs,[.025,.975]).tolist(),
            'capture_count':len(groups),'bootstrap_draws':1000,'independent_campaign_interval':False}

def run(data,out,commit):
    protocol=json.loads((HERE/'protocol.json').read_text(encoding='utf-8'))
    frozen=json.loads((HERE/'FREEZE.json').read_text(encoding='utf-8'))
    if frozen['source']!=bindings(): raise ValueError('Source changed after freeze')
    if sha(data)!=protocol['data_sha256']: raise ValueError('Input hash mismatch')
    if out.exists() and any(out.iterdir()): raise ValueError('Fresh output directory required')
    out.mkdir(parents=True,exist_ok=True); started=time.perf_counter()
    write(out/'STARTED.json',{'utc':utc(),'commit':commit,'source':bindings(),'data_sha256':sha(data),
        'compute':'local CPU','aws_used':False,'versions':{p:importlib.metadata.version(p) for p in ['numpy','lightgbm','scikit-learn']}})
    with np.load(data,allow_pickle=False) as z: d={k:z[k] for k in z.files}
    anchor=anchor_rows(d); fp=fingerprints(d['current'])
    overlaps=np.isin(fp,fp[anchor]); is_anchor=np.zeros(len(fp),dtype=bool);is_anchor[anchor]=True
    past=np.flatnonzero((d['split']==0)&~overlaps)
    mixed=np.flatnonzero((d['split']!=1)&~is_anchor&~overlaps)
    counts=np.minimum(np.minimum(np.bincount(d['y'][past],minlength=4),np.bincount(d['y'][mixed],minlength=4)),[20000,5000,5000,5000])
    if np.any(counts<2): raise ValueError('Insufficient class support after anchor fingerprint purge')
    if not d['end'][past].max()<d['start'][anchor].min(): raise ValueError('Past chronology invalid')
    np.savez_compressed(out/'DESIGN.npz',anchor=anchor,past_pool=past,mixed_pool=mixed,counts=counts)
    design={'rows':len(fp),'anchor_counts':np.bincount(d['y'][anchor],minlength=4).tolist(),'matched_fit_counts':counts.tolist(),
        'past_pool_before_purge':int(np.sum(d['split']==0)),'past_pool_after_purge':len(past),
        'mixed_pool_after_purge':len(mixed),'unique_current_fingerprints':len(np.unique(fp)),
        'anchor_fingerprint_train_overlap_after_purge':0,'anchor_capture_counts':{str(c):int(np.sum(d['capture'][anchor]==c)) for c in np.unique(d['capture'][anchor])}}
    write(out/'DESIGN.json',design)
    results=[]; paired=[]
    for seed in protocol['seeds']:
        random_pool,random_test=train_test_split(np.arange(len(fp)),test_size=.55,random_state=seed,stratify=d['y'])
        for view in protocol['views']:
            x=d['current'] if view=='current' else np.column_stack([d['current'],d['history']])
            ps={}
            for arm,pool,test in [('past_only_anchor',past,anchor),('time_mixed_anchor',mixed,anchor),('conventional_random',random_pool,random_test)]:
                fit=sample(d,pool,counts,seed)
                if len(np.intersect1d(fit,test)): raise ValueError('Row split overlap')
                params={k:v for k,v in protocol['model'].items() if k!='name'}
                model=LGBMClassifier(**params,random_state=seed,verbosity=-1,deterministic=True,force_col_wise=True)
                t=time.perf_counter();model.fit(x[fit],d['y'][fit]);p=model.predict_proba(x[test]);elapsed=time.perf_counter()-t
                if not np.array_equal(model.classes_,np.arange(4)): raise ValueError('Class ordering')
                prefix=f'{seed}_{view}_{arm}'
                np.savez_compressed(out/(prefix+'.npz'),fit=fit,test=test,y=d['y'][test],p=p,capture=d['capture'][test])
                r={'seed':seed,'view':view,'arm':arm,'seconds':elapsed,**metric(d['y'][test],p),
                   'train_counts':np.bincount(d['y'][fit],minlength=4).tolist(),
                   'test_rows_with_current_fingerprint_in_training':int(np.isin(fp[test],fp[fit]).sum()),
                   'training_rows_ending_after_first_test_start':int(np.sum(d['end'][fit]>=d['start'][test].min())),
                   'chronological_all_fit_before_test':bool(d['end'][fit].max()<d['start'][test].min())}
                results.append(r); ps[arm]=p
                print(json.dumps({k:r[k] for k in ['seed','view','arm','macro_f1','seconds']}),flush=True)
            paired.append({'seed':seed,'view':view,**paired_bootstrap(d['y'][anchor],ps['past_only_anchor'],ps['time_mixed_anchor'],d['capture'][anchor],seed)})
    write(out/'METRICS.json',results);write(out/'PAIRED.json',paired)
    files={p.name:sha(p) for p in out.glob('*.npz')}
    write(out/'COMPLETE.json',{'utc':utc(),'fits':len(results),'seconds':time.perf_counter()-started,'source':bindings(),'files':files,'aws_used':False})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['freeze','run']);ap.add_argument('--data',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--commit')
    a=ap.parse_args()
    if a.command=='freeze':write(HERE/'FREEZE.json',{'utc':utc(),'source':bindings()})
    else:
        if not all([a.data,a.out,a.commit]):ap.error('run requires data, out, commit')
        with threadpool_limits(limits=2):run(a.data,a.out,a.commit)
