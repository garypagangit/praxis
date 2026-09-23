"""Frozen Casino-trained score policy; no native classifier retraining."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import confusion_matrix,precision_recall_fscore_support,average_precision_score,roc_auc_score

ROOT=Path(__file__).resolve().parent
SOURCE=Path('C:/w/apt_benchmark_data_20260920/robustness_v2')
DATASETS={'casino':'casino_features','camlds':'camlds_features_masked_v2'}
TARGET='T1105'
ARMS=['current','context','fixed_fusion','confidence_gate','ordinary_gate','target_cost_gate','mixed_dropout']
PARAMS={'alpha':10.,'solver':'svd','fit_intercept':True}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def label(labels,target):return any(s==target or s.split(':',1)[0].split('.',1)[0]==target for s in labels)

def qualify():
    bindings={};summaries={};checked=0
    def bind(p,expected=None):
        actual=sha(p)
        if expected is not None and actual!=expected:raise ValueError('Changed source: '+str(p))
        bindings[p.relative_to(SOURCE).as_posix()]=actual
    for dataset,cache_name in DATASETS.items():
        run=SOURCE/(dataset+'_run1');cache=SOURCE/cache_name;ap=SOURCE/(dataset+'_audit')/'AUDIT.json'
        a=json.loads(ap.read_text());r=json.loads((run/'RESULTS.json').read_text());m=json.loads((cache/'MANIFEST.json').read_text())
        if a['status']!='PASS':raise ValueError('Original audit missing')
        bind(ap);bind(run/'RESULTS.json',a['hashes']['RESULTS.json']);bind(run/'PRE_FIT_RECEIPT.json',a['hashes']['PRE_FIT_RECEIPT.json'])
        bind(cache/'MANIFEST.json',r['feature_cache_manifest_sha256']);bind(cache/m['targets_file'],m['targets_sha256'])
        if m['events_sha256']!=r['input_sha256']:raise ValueError('Input lineage mismatch')
        t=[json.loads(line) for line in (cache/m['targets_file']).read_text().splitlines()]
        ix={}
        for split,v in m['role_mapping'].items():
            bind(cache/v['file'],v['sha256']);ix[split]=np.load(cache/v['file'],allow_pickle=False)
        roster=np.load(run/'PRIVATE_TARGET_ROSTER.npz',allow_pickle=False);bind(run/'PRIVATE_TARGET_ROSTER.npz')
        for key,field in [('event_ids','event_id'),('run_ids','run_id')]:
            if not np.array_equal(roster[key],np.asarray([t[i][field] for i in ix['test']])):raise ValueError('Roster/order mismatch')
        calids={t[i]['event_id'] for i in ix['calibration']};testids=set(roster['event_ids'])
        calruns={t[i]['run_id'] for i in ix['calibration']};testruns=set(roster['run_ids'])
        if calids&testids or calruns&testruns or len(testids)!=len(ix['test']):raise ValueError('Identity/split overlap')
        count=0
        for target in r['targets']:
            arms=['semantic_event','entity_context']+(['mixed_dropout'] if target==TARGET else [])
            for split in ['calibration','test']:
                expected=np.asarray([label(t[i]['labels'],target) for i in ix[split]])
                for arm in arms:
                    paths=[run/f'PRIVATE_CAL_{target}_{arm}.npz'] if split=='calibration' else sorted(run.glob(f'PRIVATE_{target}_{arm}_*.npz'))
                    for p in paths:
                        bind(p,a['hashes'][p.name]);z=np.load(p,allow_pickle=False)
                        if not np.array_equal(z['y'],expected):raise ValueError('Probability/source label mismatch')
                        if len(z['score'])!=len(expected) or not np.isfinite(z['score']).all() or np.any(z['score'][~z['observed']]!=0):raise ValueError('Invalid scores or invisible alarms')
                        count+=1
        checked+=count
        summaries[dataset]={'support':r['targets'][TARGET]['support'],'calibration_runs':len(calruns),'test_runs':len(testruns),
            'qualified_prediction_files':count,'event_id_overlap':0,'run_id_overlap':0,'unique_test_event_ids':len(testids),
            'source_events_sha256':r['input_sha256'],'cache':cache_name,'ordering':m['ordering']}
    if checked!=220:raise ValueError('Qualification inventory changed')
    return {'status':'QUALIFIED_CACHED_SCORE_POLICY_DEVELOPMENT','prediction_files':checked,'datasets':summaries,'sources':bindings,
            'limits':'Ordering is bound through the original frozen runner/cache roster and prior audit hashes; this does not independently verify attack truth or make old test outcomes untouched.'}

def binding():
    return {'files':{p.name:sha(p) for p in [ROOT/'PROTOCOL.md',ROOT/'run.py',ROOT/'test_policy.py',ROOT/'INPUTS.json']},'ridge':PARAMS,'target':TARGET,'arms':ARMS}

def features(c,h,oc,oh):
    cc=np.maximum(c,1-c);ch=np.maximum(h,1-h)
    return np.column_stack([c,h,h-c,np.abs(h-c),cc,ch,np.abs(c-.5),np.abs(h-.5),oc,oh,(c>.5)!=(h>.5),c*h])

def target(y,c,h,cost):return np.where(y==1,cost,1.)*(((h>.5)!=y).astype(float)-((c>.5)!=y).astype(float))

def metric(y,score,threshold=.5):
    pred=score>threshold;cm=confusion_matrix(y,pred,labels=[0,1]);p,r,f,_=precision_recall_fscore_support(y,pred,labels=[1],zero_division=0)
    return {'rows':len(y),'positive':int(np.sum(y)),'confusion':cm.tolist(),'precision':float(p[0]),'recall':float(r[0]),'f1':float(f[0]),
        'ap':float(average_precision_score(y,score)) if np.any(y) else None,'roc_auc':float(roc_auc_score(y,score)) if len(np.unique(y))==2 else None,
        'other_label_flags':int(cm[0,1]),'other_label_flag_rate':float(cm[0,1]/cm[0].sum()) if cm[0].sum() else None,
        'target_cost_error':float(np.mean(np.where(y==1,4.,1.)*(pred!=y)))}

def score_arms(c,h,oc,oh,mixed,ordinary,cost):
    x=features(c,h,oc,oh);og=ordinary.predict(x);cg=cost.predict(x)
    masks={'confidence_gate':np.maximum(h,1-h)>np.maximum(c,1-c),'ordinary_gate':og<0,'target_cost_gate':cg<0}
    out={'current':c.copy(),'context':h.copy(),'fixed_fusion':(c+h)/2,'mixed_dropout':mixed.copy(),
         **{k:np.where(v,h,c) for k,v in masks.items()}}
    for v in out.values():v[~(oc|oh)]=0
    return out,masks,og,cg

def run(output,freeze_commit):
    f=json.loads((ROOT/'FREEZE.json').read_text());inputs=json.loads((ROOT/'INPUTS.json').read_text())
    if f['binding']!=binding():raise ValueError('Frozen source changed')
    if qualify()!=inputs:raise ValueError('Qualified inputs changed')
    if output.exists() and any(output.iterdir()):raise ValueError('Fresh output required')
    output.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    write(output/'STARTED.json',{'utc':utc(),'binding':binding(),'freeze_commit':freeze_commit,'versions':{k:importlib.metadata.version(k) for k in ['numpy','scikit-learn']},'aws_used':False})
    source=SOURCE/'casino_run1';a=np.load(source/f'PRIVATE_CAL_{TARGET}_semantic_event.npz');b=np.load(source/f'PRIVATE_CAL_{TARGET}_entity_context.npz')
    if not np.array_equal(a['y'],b['y']):raise ValueError('Training label alignment')
    x=features(a['score'],b['score'],a['observed'],b['observed']);y=a['y'];ordinary=Ridge(**PARAMS);cost=Ridge(**PARAMS)
    t1=target(y,a['score'],b['score'],1);t4=target(y,a['score'],b['score'],4)
    ordinary.fit(x,t1);cost.fit(x,t4)
    joblib.dump(ordinary,output/'ordinary.joblib');joblib.dump(cost,output/'target_cost.joblib')
    np.savez_compressed(output/'TRAIN.npz',X=x,y=y,ordinary_target=t1,cost_target=t4)
    results=[];native=[]
    for dataset in DATASETS:
        root=SOURCE/(dataset+'_run1');receipt=json.loads((root/'RESULTS.json').read_text());record=receipt['targets'][TARGET]
        roster=np.load(root/'PRIVATE_TARGET_ROSTER.npz',allow_pickle=False);directory=output/dataset;directory.mkdir()
        grid=[(r['condition'],r['seed']) for r in record['results'] if r['arm']=='semantic_event']
        if len(grid)!=21 or len(set(grid))!=21:raise ValueError('Original grid changed')
        for condition,seed in grid:
            z={arm:np.load(root/f'PRIVATE_{TARGET}_{arm}_{condition}_{seed}.npz',allow_pickle=False) for arm in ['semantic_event','entity_context','mixed_dropout']}
            y=z['semantic_event']['y'];c=z['semantic_event']['score'];h=z['entity_context']['score'];oc=z['semantic_event']['observed'];oh=z['entity_context']['observed']
            if not all(np.array_equal(y,v['y']) for v in z.values()):raise ValueError('Evaluation alignment')
            probs,masks,os,cs=score_arms(c,h,oc,oh,z['mixed_dropout']['score'],ordinary,cost)
            np.savez_compressed(directory/f'{condition}_{seed}.npz',y=y,**probs,ordinary_gate_score=os,target_cost_gate_score=cs,observed=oc|oh)
            for arm,score in probs.items():
                row={'dataset':dataset,'condition':condition,'perturbation_seed':seed,'arm':arm,**metric(y,score)}
                row['by_run']={str(r):metric(y[roster['run_ids']==r],score[roster['run_ids']==r]) for r in np.unique(roster['run_ids'])}
                if arm in masks:row['context_selected_fraction']=float(masks[arm].mean())
                results.append(row)
            for source_arm in z:
                threshold=record['models'][source_arm]['threshold']['threshold_value']
                native.append({'dataset':dataset,'condition':condition,'perturbation_seed':seed,'arm':source_arm,'threshold':threshold,
                    'original_calibration_status':record['models'][source_arm]['threshold']['status'],**metric(y,z[source_arm]['score'],threshold)})
        print('COMPLETE '+dataset,flush=True)
    write(output/'METRICS.json',results);write(output/'ORIGINAL_THRESHOLD_CONTROLS.json',native)
    write(output/'COMPLETE.json',{'utc':utc(),'fits':2,'native_classifier_fits':0,'fit_dataset':'casino','fit_split':'clean calibration','fit_rows':len(x),
        'prediction_tables':len(results),'evaluation_views_per_dataset':21,'target':TARGET,'runtime_seconds':time.perf_counter()-started,'aws_used':False,
        'scope':'Already exposed native task-recognition development; transferred selector only, not movement/exfiltration detection or native-model transfer.'})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['freeze','run']);ap.add_argument('--output',type=Path);ap.add_argument('--freeze-commit');a=ap.parse_args()
    if a.command=='freeze':
        write(ROOT/'INPUTS.json',qualify());write(ROOT/'FREEZE.json',{'frozen_utc':utc(),'binding':binding()})
    else:
        if not a.output or not a.freeze_commit:ap.error('run requires output and freeze-commit')
        run(a.output,a.freeze_commit)
