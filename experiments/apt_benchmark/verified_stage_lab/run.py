"""Prespecified workflow-predictability and history-mismatch experiment."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
import warnings
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score,average_precision_score,confusion_matrix,precision_recall_fscore_support,roc_auc_score
from threadpoolctl import threadpool_limits
from .features import build,views,CONDITIONS,KINDS,CURRENT_NAMES,HISTORY_NAMES

SEEDS=(20260922,20260923,20260924)
ARMS=('current','current_roles','current_history','current_roles_history','current_roles_wrong_history','history_only','timing_diagnostic')
PARAMS={'n_estimators':100,'num_leaves':7,'max_depth':3,'learning_rate':.05,'min_child_samples':5,'reg_lambda':1.}
CLASSES=('Neither','RemoteAction','FileTransfer','Both')
warnings.filterwarnings('ignore', message='X does not have valid feature names, but LGBMClassifier was fitted with feature names')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def jsonl(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines()]
def arrays(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def now():return datetime.now(timezone.utc).isoformat()
def fresh(path):
    if path.exists() and any(path.iterdir()):raise ValueError('Fresh directory required')
    path.mkdir(parents=True,exist_ok=True)


def freeze(path):
    if path.exists():raise ValueError('Existing protocol')
    folder=Path(__file__).parent
    files=['collector.py','features.py','run.py','DESIGN.md']
    spec={'created_utc':now(),'status':'FROZEN_BEFORE_COLLECTION_AND_FITS','source_bindings':{name:sha(folder/name) for name in files},
          'collection':{'seed':20260922,'blocks':48,'reps':1,'transactions_per_block':48,'expected_current_transactions':2304,'workers':3},
          'fit_blocks':list(range(24)),'calibration_blocks':list(range(24,32)),'test_blocks':list(range(32,48)),
          'fit_population':'prior_mask == requested_mask only; deliberate workflow correspondence',
          'test_populations':['linked: prior_mask==requested_mask','crossed: prior_mask!=requested_mask','factorial_all: every test transaction; contains the other two groups, not an independent additional sample'],
          'labels':'Four completed-outcome masks verified from worker artifacts; not requests or malicious intent',
          'seeds':list(SEEDS),'arms':list(ARMS),'parameters':PARAMS,'conditions':list(CONDITIONS),
          'history':'Same-episode prior events; eventtime and controller arrival strictly before current start. Wrong control uses snapshot from an earlier completed episode with a different source in the same block.',
          'primary_features':list(CURRENT_NAMES)+list(HISTORY_NAMES),'roles':'Three static logical process role tags; test permutation is a metadata counterfactual, not a new enterprise deployment',
          'timing':'Excluded from six main arms; separate timing_diagnostic only',
          'rule':'If status200, infer preceding completed remote_job/file_write bits; otherwise neither. This exposes programmed workflow predictability and is not a detector of intent.',
          'intent_twins':'Counterfactual policy interpretations of identical test observations; no extra physical executions or independent samples. Hidden-policy opposite labels bound deterministic classification accuracy at 50%.',
          'interpretation':'An engineered mechanism/stress test on one OS with three loopback processes. Linked subset intentionally encodes workflow correspondence. No APT, operational theft, independent campaign, novel algorithm or early warning claim.'}
    write(path,spec)


def verify(protocol):
    spec=read(protocol)
    for name,digest in spec['source_bindings'].items():
        if sha(Path(__file__).parent/name)!=digest:raise ValueError('Frozen source changed: '+name)
    return spec


def prepare(protocol,collection,output):
    spec=verify(protocol);fresh(output)
    receipt=read(collection/'COLLECT_RECEIPT.json')
    if read(collection/'COMPLETE.json')['receipt_sha256']!=sha(collection/'COLLECT_RECEIPT.json'):raise ValueError('Collection completion binding')
    if receipt['source_sha256']!=spec['source_bindings']['collector.py'] or receipt['completed_episodes']!=2304:raise ValueError('Frozen collection roster')
    for name,digest in receipt['artifact_hashes'].items():
        if sha(collection/name)!=digest:raise ValueError('Collection artifact changed')
    d=build(jsonl(collection/'FLOW.jsonl'),jsonl(collection/'TELEMETRY.jsonl'))
    truth={t['episode']:t for t in jsonl(collection/'TRUTH.jsonl')}
    if set(d['episode'])!=set(truth):raise ValueError('Truth/flow identity mismatch')
    d['y']=np.asarray([truth[e]['completed_mask'] for e in d['episode']]);d['prior_mask']=np.asarray([truth[e]['prior_mask'] for e in d['episode']]);d['requested_mask']=np.asarray([truth[e]['requested_mask'] for e in d['episode']])
    d['linked']=d['prior_mask']==d['requested_mask'];d['split']=np.where(d['block']<24,0,np.where(d['block']<32,1,2))
    np.savez_compressed(output/'DATA.npz',**d)
    counts={}
    for split,name in enumerate(('fit','calibration','test')):
        counts[name]={}
        for linked,pop in ((True,'linked'),(False,'crossed')):
            at=(d['split']==split)&(d['linked']==linked)
            counts[name][pop]={'rows':int(at.sum()),'outcomes':dict(zip(CLASSES,np.bincount(d['y'][at],minlength=4).tolist()))}
    write(output/'PREPARATION.json',{'created_utc':now(),'protocol_sha256':sha(protocol),'collection_root':str(collection.resolve()),'collection_receipt_sha256':sha(collection/'COLLECT_RECEIPT.json'),'data_sha256':sha(output/'DATA.npz'),'counts':counts})
    print(json.dumps(counts),flush=True)


def score(y,p):
    pred=p.argmax(axis=1);precision,recall,f1,support=precision_recall_fscore_support(y,pred,labels=np.arange(4),zero_division=0)
    result={'rows':len(y),'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1.mean()),'confusion':confusion_matrix(y,pred,labels=np.arange(4)).tolist(),
            'per_class':{name:{'precision':float(precision[i]),'recall':float(recall[i]),'f1':float(f1[i]),'support':int(support[i])} for i,name in enumerate(CLASSES)},'outcomes':{}}
    for bit,name in ((1,'remote'),(2,'transfer')):
        truth=(y&bit)>0;flags=(pred&bit)>0;s=p[:,[k for k in range(4) if k&bit]].sum(axis=1)
        tp=int(np.sum(truth&flags));fp=int(np.sum(~truth&flags));fn=int(np.sum(truth&~flags))
        result['outcomes'][name]={'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else 0.,'recall':tp/(tp+fn) if tp+fn else None,
            'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,'ap':float(average_precision_score(truth,s)) if truth.any() else None,
            'roc_auc':float(roc_auc_score(truth,s)) if truth.any() and (~truth).any() else None}
    return result


def rule(d,condition):
    h=d[condition+'__history'];c=d[condition+'__current']
    remote=h[:,3*KINDS.index('remote_job')+1]>0;transfer=h[:,3*KINDS.index('file_write')+1]>0
    predicted=(remote.astype(int)+2*transfer.astype(int))*(c[:,2]>0)
    return np.eye(4)[predicted]


def fit(protocol,prepared,output):
    spec=verify(protocol);fresh(output)
    prep=read(prepared/'PREPARATION.json')
    if prep['protocol_sha256']!=sha(protocol) or prep['data_sha256']!=sha(prepared/'DATA.npz'):raise ValueError('Preparation binding')
    d=arrays(prepared/'DATA.npz');fit=np.flatnonzero((d['split']==0)&d['linked']);cal=np.flatnonzero((d['split']==1)&d['linked'])
    groups={name:np.flatnonzero((d['split']==2)&(d['linked']==linked)) for name,linked in (('linked',True),('crossed',False))}
    groups['factorial_all']=np.flatnonzero(d['split']==2)
    receipt={'started_utc':now(),'protocol_sha256':sha(protocol),'prepared_sha256':sha(prepared/'DATA.npz'),'preparation_sha256':sha(prepared/'PREPARATION.json'),'cloud_compute_started':False,
             'environment':{'python':platform.python_version(),'platform':platform.platform(),'packages':{name:importlib.metadata.version(name) for name in ('numpy','lightgbm','scikit-learn','joblib')}}}
    write(output/'STARTED.json',receipt);clock=time.perf_counter();results=[]
    train_views=views(d,'clean')
    for seed in SEEDS:
        cell=output/str(seed);cell.mkdir();saved={'fit_indices':fit,'cal_indices':cal,**{name+'_indices':idx for name,idx in groups.items()}}
        out={}
        for arm in ARMS:
            model=LGBMClassifier(**PARAMS,random_state=seed,n_jobs=4,deterministic=True,force_col_wise=True,verbosity=-1)
            model.fit(train_views[arm][fit],d['y'][fit])
            if not np.array_equal(model.classes_,np.arange(4)):raise ValueError('Unsupported fitting class')
            joblib.dump(model,cell/(arm+'.joblib'),compress=3);out[arm]={}
            saved[arm+'__cal']=model.predict_proba(train_views[arm][cal])
            for condition in CONDITIONS:
                matrix=views(d,condition)[arm];out[arm][condition]={}
                for population,idx in groups.items():
                    p=model.predict_proba(matrix[idx]);saved[f'{arm}__{condition}__{population}']=p
                    out[arm][condition][population]={'all':score(d['y'][idx],p),'status200_only':score(d['y'][idx][d['clean__current'][idx,2]>0],p[d['clean__current'][idx,2]>0])}
            print(f'FIT {seed} {arm}',flush=True)
        comparisons={}
        for name in ('majority','prior_evidence_rule'):
            comparisons[name]={}
            for condition in CONDITIONS:
                p=np.eye(4)[np.full(len(d['y']),np.bincount(d['y'][fit],minlength=4).argmax())] if name=='majority' else rule(d,condition)
                comparisons[name][condition]={population:{'all':score(d['y'][idx],p[idx]),'status200_only':score(d['y'][idx][d['clean__current'][idx,2]>0],p[idx][d['clean__current'][idx,2]>0])} for population,idx in groups.items()}
        # Exactly the same technical observations receive opposite hidden-policy
        # interpretations. They are a counterfactual diagnostic, not more runs.
        twins={}
        for arm in ARMS:
            twins[arm]={}
            for population,idx in groups.items():
                eligible=d['y'][idx]!=0;p=saved[f'{arm}__clean__{population}'][eligible];flags=p.argmax(axis=1)!=0
                predicted=np.repeat(flags,2);truth=np.tile([False,True],len(flags));scores=np.repeat(1-p[:,0],2)
                twins[arm][population]={'underlying_completed_operations':int(eligible.sum()),'counterfactual_rows':2*int(eligible.sum()),'accuracy':float(np.mean(predicted==truth)),
                                      'roc_auc':float(roc_auc_score(truth,scores)),'policy_context_supplied':False,'separate_physical_executions':False}
        result={'seed':seed,'arms':out,'comparators':comparisons,'hidden_policy_twins':twins}
        np.savez_compressed(cell/'PREDICTIONS.npz',**saved);write(cell/'METRICS.json',result)
        write(cell/'COMPLETE.json',{'files':{p.name:sha(p) for p in cell.iterdir() if p.is_file()}});results.append(result)
    receipt.update({'completed_utc':now(),'elapsed_seconds':time.perf_counter()-clock,'models_fitted':len(SEEDS)*len(ARMS)})
    write(output/'SUMMARY.json',{'receipt':receipt,'preparation':prep,'seeds':results})
    write(output/'COMPLETE.json',{'summary_sha256':sha(output/'SUMMARY.json'),'started_sha256':sha(output/'STARTED.json')})
    print(json.dumps(receipt),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','prepare','fit']);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--collection',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args()
    with threadpool_limits(limits=4):
        if args.mode=='freeze':freeze(args.protocol)
        elif args.mode=='prepare':prepare(args.protocol,args.collection,args.output)
        else:fit(args.protocol,args.prepared,args.output)
if __name__=='__main__':main()
