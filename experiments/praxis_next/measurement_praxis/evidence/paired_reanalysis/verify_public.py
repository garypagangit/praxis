"""Public-only arithmetic verifier. Requires Python and NumPy; no project imports.

Run: python verify_public.py
Optionally save a NEW receipt: python verify_public.py --receipt PUBLIC_VERIFICATION.json

Confusion tables suffice for paired capture-bootstrap metrics, but cannot prove
raw-row identity, author-label correctness or model-fitting provenance. Those
claims remain covered only by the earlier private-input audit and source record.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

NAMES = ('Benign', 'OtherAttackStage', 'LateralMovement', 'DataExfiltration')
FILES = ('CAPTURE_CONFUSIONS.json', 'CAPTURE_DRAWS.json', 'PAIRED_RESULTS.json',
         'MEANS.json', 'DIRECTION_COUNTS.json', 'AUDIT.json', 'PUBLICATION_AUDIT.json')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def compare(got, expected, path='root'):
    """Strict structure/types with tolerant arithmetic comparison for reals."""
    if isinstance(expected, dict):
        if not isinstance(got, dict) or set(got) != set(expected):
            raise ValueError(f'{path}: different object keys')
        for key in expected:compare(got[key], expected[key], path+'.'+key)
    elif isinstance(expected, (list, tuple)):
        if not isinstance(got, list) or len(got) != len(expected):
            raise ValueError(f'{path}: different sequence lengths/types')
        for i,(a,b) in enumerate(zip(got,expected)):compare(a,b,f'{path}[{i}]')
    elif expected is None or isinstance(expected, (str,bool)):
        if got != expected or type(got) is not type(expected):
            raise ValueError(f'{path}: {got!r} != {expected!r}')
    elif isinstance(expected, (int,np.integer)):
        if isinstance(got,bool) or not isinstance(got,(int,float)) or got != expected:
            raise ValueError(f'{path}: {got!r} != {expected!r}')
    elif not isinstance(got,(int,float)) or isinstance(got,bool) or not np.isclose(got,expected,rtol=1e-10,atol=1e-12):
        raise ValueError(f'{path}: {got!r} != {expected!r}')


def point_metrics(cm):
    """Derive every published scalar/count directly from a 4 x 4 table."""
    cm=np.asarray(cm,dtype=np.int64)
    support=cm.sum(axis=1); called=cm.sum(axis=0)
    classes={};stages={}
    for k,name in enumerate(NAMES):
        true_n=int(support[k]);pred_n=int(called[k]);correct=int(cm[k,k])
        classes[name]={'native_label':k,'support':true_n,'predicted_count':pred_n,'correct_count':correct,
            'exact_stage_recall':correct/true_n if true_n else None,
            'precision':correct/pred_n if pred_n else None,
            'f1':2*correct/(true_n+pred_n) if true_n else None}
        if k:
            missed=int(cm[k,0]);wrong=int(sum(cm[k,j] for j in range(1,4) if j!=k))
            if missed+wrong+correct!=true_n:raise ValueError('Error destinations do not partition support')
            stages[name]={**classes[name],'warning_count':true_n-missed,
                'warning_recall':(true_n-missed)/true_n if true_n else None,
                'attack_to_benign_count':missed,'wrong_attack_stage_count':wrong}
    absent=[name for name in NAMES if classes[name]['support']==0]
    normal=int(support[0]);false=int(sum(cm[0,1:]))
    return {'rows':int(cm.sum()),'label_order':[0,1,2,3],
        'label_mapping':[{'native_label':k,'name':n} for k,n in enumerate(NAMES)],'benign_label':0,
        'confusion':cm.tolist(),'macro_f1':None if absent else sum(v['f1'] for v in classes.values())/4,
        'macro_f1_unsupported_classes':absent,'classes':classes,'stages':stages,
        'attack_to_benign_count':sum(v['attack_to_benign_count'] for v in stages.values()),
        'wrong_attack_stage_count':sum(v['wrong_attack_stage_count'] for v in stages.values()),
        'benign_support':normal,'benign_false_alert_count':false,'benign_false_alert_rate':false/normal if normal else None}


def quantities(cms):
    """All paired-interval quantities, vectorized over independent draws."""
    cms=np.asarray(cms,dtype=float)
    if cms.ndim==2:cms=cms[None,...]
    actual=cms.sum(axis=2);predicted=cms.sum(axis=1);correct=np.stack([cms[:,i,i] for i in range(4)],axis=1)
    with np.errstate(divide='ignore',invalid='ignore'):
        scores=2*correct/(actual+predicted)
        scores[actual==0]=np.nan
        exact=correct/actual
        warned=cms[:,:,1:].sum(axis=2)/actual
        fpr=cms[:,0,1:].sum(axis=1)/actual[:,0]
    missed=cms[:,1:,0].sum(axis=1)
    wrong=sum(cms[:,i,j] for i in range(1,4) for j in range(1,4) if i!=j)
    values={'macro_f1':scores.mean(axis=1),'benign_false_alert_rate':fpr,
        'benign_false_alert_count':cms[:,0,1:].sum(axis=1),'attack_to_benign_count':missed,'wrong_attack_stage_count':wrong}
    for k,name in enumerate(NAMES[1:],1):
        values[name+'.exact_stage_recall']=exact[:,k]
        values[name+'.warning_recall']=warned[:,k]
        values[name+'.stage_f1']=scores[:,k]
        values[name+'.attack_to_benign_count']=cms[:,k,0]
        values[name+'.wrong_attack_stage_count']=sum(cms[:,k,j] for j in range(1,4) if j!=k)
    return values


def bounds(values):
    valid=np.asarray(values)[np.isfinite(values)]
    if len(valid)>=2:
        low,high=(float(v) for v in np.quantile(valid,[.025,.975],method='linear'))
    else:low=high=None
    missing=len(values)-len(valid)
    return dict(lower=low,upper=high,confidence=.95,valid_replicates=int(len(valid)),
        undefined_replicates=int(missing),conditional_on_required_label_support=bool(missing),
        status='INSUFFICIENT_DEFINED_REPLICATES' if len(valid)<2 else 'SUPPORT_CONDITIONAL' if missing else 'COMPLETE')


def insert(obj,key,value):
    if '.' in key:
        stage,metric=key.split('.')
        obj.setdefault('stages',{}).setdefault(stage,{})['delta_'+metric]=value
    else:obj['delta_'+key]=value


def make_expected_specs():
    specs=[]
    for condition in ('clean','delayed_unavailable','wrong_host_history'):
        for budget in (1,2,3):
            for seed in (8101,8102,8103):
                path=f'seed_{seed}/{condition}_b{budget}_'
                specs.append(dict(study='PX081',contrast='harm_minus_entropy',condition=condition,budget=budget,seed=seed,
                                  baseline=path+'entropy.npz',candidate=path+'harm.npz'))
    for seed in (20260923,20260924,20260925):
        for view in ('current','current_history'):
            specs.append(dict(study='PX082',contrast=view+'_mixed_minus_past',condition='common_anchor',budget=None,seed=seed,
                baseline=f'{seed}_{view}_past_only_anchor.npz',candidate=f'{seed}_{view}_time_mixed_anchor.npz'))
        specs.append(dict(study='PX082',contrast='chronological_history_minus_current',condition='common_anchor',budget=None,seed=seed,
            baseline=f'{seed}_current_past_only_anchor.npz',candidate=f'{seed}_current_history_past_only_anchor.npz'))
    return specs


def verify(directory):
    directory=Path(directory)
    inputs={name:load(directory/name) for name in FILES}
    # Bind to pre-existing audit receipts; do not rewrite their hashes or outputs.
    for receipt in ('AUDIT.json','PUBLICATION_AUDIT.json'):
        for name,expected in inputs[receipt]['outputs_sha256'].items():
            if digest(directory/name)!=expected:raise ValueError('Previous receipt hash mismatch: '+name)
    if inputs['PUBLICATION_AUDIT.json']['arithmetic_audit_sha256']!=digest(directory/'AUDIT.json'):
        raise ValueError('Original audit linkage mismatch')
    sufficient=inputs['CAPTURE_CONFUSIONS.json'];plan=inputs['CAPTURE_DRAWS.json']
    compare(sufficient['ordered_captures'],[6,7,8,9,10],'captures')
    compare(sufficient['native_class_order'],list(NAMES),'schema')
    compare(plan['ordered_captures'],[6,7,8,9,10],'plan captures')
    compare(plan['seed'],20260923,'bootstrap seed');compare(plan['replicates'],2000,'draw count')
    groups=sufficient['ordered_captures'];draws=plan['draws']
    original=np.random.default_rng(20260923).integers(0,5,size=(2000,5))
    regenerated=[[groups[index] for index in row] for row in original]
    compare(draws,regenerated,'regenerated capture draws')
    drawhash=hashlib.sha256(json.dumps(draws,separators=(',',':'),sort_keys=True).encode()).hexdigest()
    compare(plan['draws_sha256'],drawhash,'capture draw hash')
    compare(inputs['AUDIT.json']['shared_capture_draws_sha256'],drawhash,'audited draw hash')
    weights=np.array([[row.count(group) for group in groups] for row in draws],dtype=np.int64)
    tables={}
    for key,raw in sufficient['tables'].items():
        array=np.asarray(raw)
        if array.shape!=(5,4,4) or not np.issubdtype(array.dtype,np.integer) or (array<0).any():
            raise ValueError('Malformed public confusion count table: '+key)
        tables[key]=array
    saved=inputs['PAIRED_RESULTS.json']
    compare(saved['comparison_count'],36,'comparison count');compare(saved['status'],'RETROSPECTIVE','analysis status')
    compare([r['spec'] for r in saved['results']],make_expected_specs(),'complete contrast inventory')
    computed=[];used=set();interval_checks=0
    for entry in saved['results']:
        spec=entry['spec'];published=entry['result'];points=[];boot=[];arrays=[]
        for side in ('baseline','candidate'):
            key=spec['study']+'/'+spec[side];used.add(key);array=tables[key];arrays.append(array)
            compare(published[side],point_metrics(array.sum(axis=0)),key+' point metrics')
            points.append({key:float(value[0]) for key,value in quantities(array.sum(axis=0)).items()})
            resampled=np.zeros((2000,4,4),dtype=np.int64)
            for group in range(5):resampled+=weights[:,group,None,None]*array[group]
            boot.append(quantities(resampled))
        # Aggregates retain stage support within every capture; identical truth
        # marginals are necessary, but cannot establish individual-row pairing.
        compare(arrays[0].sum(axis=2).tolist(),arrays[1].sum(axis=2).tolist(),'paired capture-stage supports')
        expected_delta={};expected_intervals={}
        flat_delta={key:points[1][key]-value for key,value in points[0].items()}
        for key,value in flat_delta.items():
            insert(expected_delta,key,value)
            insert(expected_intervals,key,bounds(boot[1][key]-boot[0][key]));interval_checks+=1
        for stage in NAMES[1:]:
            fdelta=flat_delta['macro_f1'];wdelta=flat_delta[stage+'.warning_recall']
            updown=bool(fdelta>1e-12 and wdelta < -1e-12)
            downup=bool(fdelta < -1e-12 and wdelta>1e-12)
            expected_delta['stages'][stage].update(macro_f1_up_warning_down=updown,macro_f1_down_warning_up=downup,
                                                   macro_f1_warning_sign_reversal=updown or downup)
        compare(published['paired_deltas'],expected_delta,'all paired differences')
        compare(published['bootstrap']['intervals'],expected_intervals,'all paired intervals')
        compare(published['bootstrap']['replicates'],2000,'per-comparison draw count')
        compare(published['bootstrap']['seed'],20260923,'per-comparison draw seed')
        compare(published['bootstrap']['group_count'],5,'per-comparison group count')
        compare(published['bootstrap']['paired_draws_sha256'],inputs['AUDIT.json']['row_bound_plan_sha256'][spec['study']],'row-bound plan receipt')
        computed.append(dict(spec=spec,points=points,delta=flat_delta,stage_deltas=expected_delta['stages'],
            intervals=expected_intervals,rows=int(arrays[0].sum()),support=arrays[0].sum(axis=(0,2)).tolist()))
    compare(sorted(used),sorted(tables),'no unused/missing public prediction tables')
    grouping={}
    for item in computed:
        spec=item['spec'];key=tuple(spec[k] for k in ('study','contrast','condition','budget'))
        grouping.setdefault(key,[]).append(item)
    means=[]
    for key,items in grouping.items():
        study,contrast,condition,budget=key
        seeds=[8101,8102,8103] if study=='PX081' else [20260923,20260924,20260925]
        compare(sorted(i['spec']['seed'] for i in items),seeds,'three fitting seeds')
        mean_values={side:{metric:sum(i['points'][s][metric] for i in items)/3 for metric in items[0]['points'][s]}
            for s,side in enumerate(('baseline','candidate'))}
        mean_values['delta']={metric:sum(i['delta'][metric] for i in items)/3 for metric in items[0]['delta']}
        stages={}
        for k,stage in enumerate(NAMES[1:],1):
            stages[stage]={'support':items[0]['support'][k],
                'macro_f1_up_warning_down_seeds':sum(i['stage_deltas'][stage]['macro_f1_up_warning_down'] for i in items),
                'macro_f1_down_warning_up_seeds':sum(i['stage_deltas'][stage]['macro_f1_down_warning_up'] for i in items),
                'warning_down_seeds':sum(i['delta'][stage+'.warning_recall'] < -1e-12 for i in items),
                'warning_up_seeds':sum(i['delta'][stage+'.warning_recall'] > 1e-12 for i in items)}
        means.append(dict(study=study,contrast=contrast,condition=condition,budget=budget,seeds=seeds,rows=items[0]['rows'],means=mean_values,stages=stages))
    compare(inputs['MEANS.json'],{'status':'THREE_SEED_POINT_MEANS_ONLY_NO_POOLED_CI','groups':means},'all seed means')
    direction_counts={}
    for study in ('PX081','PX082'):
        direction_counts[study]={};items=[i for i in computed if i['spec']['study']==study]
        for stage in NAMES[1:]:
            direction_counts[study][stage]={
                'comparisons':len(items),
                'macro_up_warning_down':sum(i['stage_deltas'][stage]['macro_f1_up_warning_down'] for i in items),
                'macro_down_warning_up':sum(i['stage_deltas'][stage]['macro_f1_down_warning_up'] for i in items),
                'warning_delta_interval_entirely_below_zero':sum(i['intervals']['stages'][stage]['delta_warning_recall']['upper']<0 for i in items),
                'macro_interval_positive_and_warning_interval_negative':sum(i['intervals']['delta_macro_f1']['lower']>0 and
                    i['intervals']['stages'][stage]['delta_warning_recall']['upper']<0 for i in items)}
    compare(inputs['DIRECTION_COUNTS.json'],direction_counts,'all direction counts')
    return dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),verifier_source_sha256=digest(__file__),
        inputs_sha256={name:digest(directory/name) for name in FILES},private_files_opened=0,project_analysis_modules_imported=0,
        source_fits=0,public_prediction_tables=len(tables),paired_comparisons=len(computed),
        independently_recomputed_metric_intervals=interval_checks,three_seed_mean_groups=len(means),
        capture_draws_regenerated=2000,capture_count=5,stage_direction_summaries=6,
        original_receipt_hash_bindings_verified=True,
        unverified_from_public_aggregates=['Original individual-row identities and pairing','Original probability-to-hard-label conversion',
            'Ground-truth author-label validity','Model-fitting provenance beyond linked receipts','Independence or generalization across campaigns'],
        interpretation='Public aggregate arithmetic verification; this does not convert five fragments into independent campaigns')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--receipt',type=Path)
    args=parser.parse_args()
    if args.receipt and args.receipt.exists():raise ValueError('Refusing to overwrite an existing receipt')
    receipt=verify(args.directory)
    encoded=json.dumps(receipt,indent=2,allow_nan=False)+'\n'
    if args.receipt:args.receipt.write_text(encoded,encoding='utf-8')
    print(encoded)
