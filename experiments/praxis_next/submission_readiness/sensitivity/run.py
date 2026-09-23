"""Frozen retrospective omission audit on public capture confusion tables only."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
PUBLIC=REPO/'experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis'
INPUT_NAMES=('CAPTURE_CONFUSIONS.json','PAIRED_RESULTS.json','MEANS.json','AUDIT.json',
             'PUBLICATION_AUDIT.json','PUBLIC_VERIFICATION.json','verify_public.py')
SOURCES=('ANALYSIS_PLAN.md','run.py','test_sensitivity.py')
NAMES=('Benign','OtherAttackStage','LateralMovement','DataExfiltration')
METRICS=('macro_f1','exfil_warning_recall','movement_exact_recall','benign_false_alert_rate',
         'exfil_to_benign_count','benign_false_alert_count')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def utc():return datetime.now(timezone.utc).isoformat()


def expected_specs():
    specs=[]
    for condition in ('clean','delayed_unavailable','wrong_host_history'):
        for budget in (1,2,3):
            for seed in (8101,8102,8103):
                p=f'seed_{seed}/{condition}_b{budget}_'
                specs.append(dict(study='PX081',contrast='harm_minus_entropy',condition=condition,budget=budget,
                    seed=seed,baseline=p+'entropy.npz',candidate=p+'harm.npz'))
    for seed in (20260923,20260924,20260925):
        for view in ('current','current_history'):
            specs.append(dict(study='PX082',contrast=view+'_mixed_minus_past',condition='common_anchor',budget=None,
                seed=seed,baseline=f'{seed}_{view}_past_only_anchor.npz',candidate=f'{seed}_{view}_time_mixed_anchor.npz'))
        specs.append(dict(study='PX082',contrast='chronological_history_minus_current',condition='common_anchor',budget=None,
            seed=seed,baseline=f'{seed}_current_past_only_anchor.npz',candidate=f'{seed}_current_history_past_only_anchor.npz'))
    return specs


def metrics(cm):
    cm=np.asarray(cm)
    if cm.shape!=(4,4) or not np.issubdtype(cm.dtype,np.integer) or (cm<0).any():
        raise ValueError('Expected four-class nonnegative integer confusion matrix')
    n=cm.sum(1);p=cm.sum(0);diag=cm.diagonal()
    macro=float(np.mean(2*diag/(n+p))) if np.all(n>0) else None
    return dict(macro_f1=macro,exfil_warning_recall=float(1-cm[3,0]/n[3]) if n[3] else None,
        movement_exact_recall=float(cm[2,2]/n[2]) if n[2] else None,
        benign_false_alert_rate=float(cm[0,1:].sum()/n[0]) if n[0] else None,
        exfil_to_benign_count=int(cm[3,0]),benign_false_alert_count=int(cm[0,1:].sum()))


def mean_metrics(points):
    if not points:raise ValueError('At least one declared seed is required')
    return {key:None if any(p[key] is None for p in points) else float(sum(p[key] for p in points)/len(points)) for key in METRICS}


def difference(before,after):
    return {k:None if before[k] is None or after[k] is None else float(after[k]-before[k]) for k in METRICS}


def direction(delta):
    f,w=delta['macro_f1'],delta['exfil_warning_recall']
    if f is None or w is None:return dict(f1_up_exfil_warning_down=None,f1_down_exfil_warning_up=None,sign_disagreement=None)
    first=bool(f>1e-12 and w < -1e-12);second=bool(f < -1e-12 and w>1e-12)
    return dict(f1_up_exfil_warning_down=first,f1_down_exfil_warning_up=second,sign_disagreement=first or second)


def summarize_pair(before,after):
    a,b=metrics(before),metrics(after);delta=difference(a,b)
    if not np.array_equal(np.sum(before,axis=1),np.sum(after,axis=1)):
        raise ValueError('Paired confusion tables have incompatible true-class supports')
    return dict(rows=int(np.sum(before)),class_support=np.sum(before,axis=1).tolist(),baseline=a,candidate=b,
                delta=delta,**direction(delta))


def signature(left,right,captures=(6,7,8,9,10)):
    payload={'class_order':list(NAMES),'capture_order':list(captures),
             'baseline':np.asarray(left).tolist(),'candidate':np.asarray(right).tolist()}
    return hashlib.sha256(json.dumps(payload,separators=(',',':'),sort_keys=True).encode()).hexdigest()


def identify(spec):
    return '|'.join(str(spec[k]) for k in ('study','contrast','condition','budget','seed'))


def groupkey(spec):return tuple(spec[k] for k in ('study','contrast','condition','budget'))


def independent_module():
    spec=importlib.util.spec_from_file_location('previous_public_verifier',PUBLIC/'verify_public.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def flatten_old(old):
    return {'macro_f1':old['macro_f1'],'exfil_warning_recall':old['stages']['DataExfiltration']['warning_recall'],
        'movement_exact_recall':old['stages']['LateralMovement']['exact_stage_recall'],
        'benign_false_alert_rate':old['benign_false_alert_rate'],'exfil_to_benign_count':old['stages']['DataExfiltration']['attack_to_benign_count'],
        'benign_false_alert_count':old['benign_false_alert_count']}


def inventory():
    entries=[{'path':(PUBLIC/name).relative_to(REPO).as_posix(),'sha256':sha(PUBLIC/name)} for name in INPUT_NAMES]
    previous=read(PUBLIC/'PUBLIC_VERIFICATION.json')
    for name in ('CAPTURE_CONFUSIONS.json','PAIRED_RESULTS.json','MEANS.json','AUDIT.json','PUBLICATION_AUDIT.json'):
        if sha(PUBLIC/name)!=previous['inputs_sha256'][name]:raise ValueError('Original public audit input changed: '+name)
    if sha(PUBLIC/'verify_public.py')!=previous['verifier_source_sha256']:raise ValueError('Independent verifier source changed')
    return entries


def freeze():
    if (HERE/'FREEZE.json').exists():raise ValueError('Do not overwrite an existing freeze')
    write(HERE/'INPUTS.json',{'status':'PUBLIC_INPUTS_ONLY','files':inventory()})
    write(HERE/'FREEZE.json',dict(status='RETROSPECTIVE_PLAN_FROZEN_BEFORE_OMISSION_RESULTS',utc=utc(),
        source_sha256={name:sha(HERE/name) for name in SOURCES},inputs_sha256=sha(HERE/'INPUTS.json'),
        paired_comparisons=36,capture_omissions=180,seed_omissions=36,independent_fits=0))
    print('Sensitivity source, plan, tests and input inventory ready for Git freeze; no actual omission metrics evaluated.')


def validate_freeze(commit):
    frozen=read(HERE/'FREEZE.json')
    for name,digest in frozen['source_sha256'].items():
        if sha(HERE/name)!=digest:raise ValueError('Frozen source changed: '+name)
    if sha(HERE/'INPUTS.json')!=frozen['inputs_sha256']:raise ValueError('Frozen input inventory changed')
    for name in (*SOURCES,'INPUTS.json','FREEZE.json'):
        path=HERE/name;rel=path.relative_to(REPO).as_posix()
        raw=subprocess.check_output(['git','show',f'{commit}:{rel}'],cwd=REPO)
        if hashlib.sha256(raw).hexdigest()!=sha(path):raise ValueError('Not identical to committed freeze: '+name)
    if inventory()!=read(HERE/'INPUTS.json')['files']:raise ValueError('Frozen public input bytes changed')


def csvfile(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='') as stream:
        out=csv.DictWriter(stream,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)


def flatten_rows(items,omission):
    rows=[]
    for item in items:
        spec=item['spec'];p=item['point'];common={k:spec[k] for k in ('study','contrast','condition','budget')}
        if omission=='omitted_capture':common['fitting_seed']=spec['seed']
        common[omission]=item[omission]
        if 'rows' in p:common.update(rows=p['rows'],class_support=json.dumps(p['class_support']))
        for metric in METRICS:
            rows.append({**common,'metric':metric,'baseline':p['baseline'][metric],'candidate':p['candidate'][metric],
                'delta':p['delta'][metric],'f1_up_exfil_warning_down':p['f1_up_exfil_warning_down'],
                'f1_down_exfil_warning_up':p['f1_down_exfil_warning_up'],'sign_disagreement':p['sign_disagreement']})
    return rows


def summarize_values(values):
    valid=[v for v in values if v is not None]
    return dict(minimum=min(valid) if valid else None,maximum=max(valid) if valid else None,
        defined=len(valid),undefined=len(values)-len(valid),positive=sum(v>1e-12 for v in valid),
        negative=sum(v < -1e-12 for v in valid),zero=sum(abs(v)<=1e-12 for v in valid))


def run(commit):
    if (HERE/'CAPTURE_OMISSIONS.json').exists():raise ValueError('Existing sensitivity outputs must not be overwritten')
    validate_freeze(commit);independent=independent_module()
    source=read(PUBLIC/'CAPTURE_CONFUSIONS.json');original=read(PUBLIC/'PAIRED_RESULTS.json')['results']
    independent.compare(source['ordered_captures'],[6,7,8,9,10]);independent.compare(source['native_class_order'],list(NAMES))
    independent.compare([i['spec'] for i in original],expected_specs())
    tables={key:np.asarray(value) for key,value in source['tables'].items()}
    if any(value.shape!=(5,4,4) or not np.issubdtype(value.dtype,np.integer) or (value<0).any() for value in tables.values()):
        raise ValueError('Invalid public source confusion table')
    captures=source['ordered_captures'];full=[];omissions=[];signatures={};checks=0
    for item in original:
        spec=item['spec'];left=tables[spec['study']+'/'+spec['baseline']];right=tables[spec['study']+'/'+spec['candidate']]
        if not np.array_equal(left.sum(2),right.sum(2)):raise ValueError('Capture/class support differs across methods')
        point=summarize_pair(left.sum(0),right.sum(0));full.append(dict(spec=spec,point=point))
        for side,cm in [('baseline',left.sum(0)),('candidate',right.sum(0))]:
            independent.compare(point[side],flatten_old(item['result'][side]),identify(spec)+' original '+side)
            independent.compare(point[side],flatten_old(independent.point_metrics(cm)),identify(spec)+' independent '+side);checks+=12
        for pos,cap in enumerate(captures):
            left_rest=left[np.arange(5)!=pos].sum(0);right_rest=right[np.arange(5)!=pos].sum(0)
            rest=summarize_pair(left_rest,right_rest)
            for side,cm in [('baseline',left_rest),('candidate',right_rest)]:
                independent.compare(rest[side],flatten_old(independent.point_metrics(cm)),identify(spec)+f' capture {cap} '+side);checks+=6
            omissions.append(dict(spec=spec,omitted_capture=cap,retained_captures=[c for c in captures if c!=cap],point=rest))
        if spec['study']=='PX081':
            sig=signature(left,right,captures)
            entry=signatures.setdefault(sig,dict(signature=sig,members=[],point=point))
            independent.compare(point,entry['point'],'aggregate-equivalent pair metrics')
            entry['members'].append(identify(spec))
    groups={}
    for item in full:groups.setdefault(groupkey(item['spec']),[]).append(item)
    seed_omissions=[];summaries=[];capture_means=[]
    original_means={groupkey(g):g for g in read(PUBLIC/'MEANS.json')['groups']}
    name_mapping={'macro_f1':'macro_f1','exfil_warning_recall':'DataExfiltration.warning_recall',
        'movement_exact_recall':'LateralMovement.exact_stage_recall','benign_false_alert_rate':'benign_false_alert_rate',
        'exfil_to_benign_count':'DataExfiltration.attack_to_benign_count','benign_false_alert_count':'benign_false_alert_count'}
    for key,items in groups.items():
        spec={k:v for k,v in zip(('study','contrast','condition','budget'),key)}
        seeds=sorted(i['spec']['seed'] for i in items)
        expected=[8101,8102,8103] if spec['study']=='PX081' else [20260923,20260924,20260925]
        independent.compare(seeds,expected,'complete fitting seeds')
        mean={side:mean_metrics([i['point'][side] for i in items]) for side in ('baseline','candidate','delta')}
        for side in mean:
            independent.compare(mean[side],{k:original_means[key]['means'][side][v] for k,v in name_mapping.items()},'original seed means');checks+=6
        mean.update(direction(mean['delta']))
        group_seed=[];group_capture=[]
        for excluded in seeds:
            remaining=[i for i in items if i['spec']['seed']!=excluded]
            p={side:mean_metrics([i['point'][side] for i in remaining]) for side in ('baseline','candidate','delta')}
            # A second direct arithmetic route checks paired means without pooling rows.
            independent.compare(p['delta'],difference(p['baseline'],p['candidate']),'seed omission paired mean');checks+=6
            p.update(direction(p['delta']))
            record=dict(spec=spec,omitted_seed=excluded,retained_seeds=[s for s in seeds if s!=excluded],point=p)
            seed_omissions.append(record);group_seed.append(record)
        for excluded in captures:
            remaining=[i for i in omissions if groupkey(i['spec'])==key and i['omitted_capture']==excluded]
            if len(remaining)!=3:raise ValueError('Missing capture omission seed')
            p={side:mean_metrics([i['point'][side] for i in remaining]) for side in ('baseline','candidate','delta')}
            independent.compare(p['delta'],difference(p['baseline'],p['candidate']),'capture omission paired mean');checks+=6
            p.update(direction(p['delta']))
            record=dict(spec=spec,omitted_capture=excluded,seeds=seeds,point=p)
            capture_means.append(record);group_capture.append(record)
        summaries.append(dict(spec=spec,seeds=seeds,full_three_seed_mean=mean,
            capture_omission_mean_ranges={k:summarize_values([i['point']['delta'][k] for i in group_capture]) for k in METRICS},
            seed_omission_mean_ranges={k:summarize_values([i['point']['delta'][k] for i in group_seed]) for k in METRICS},
            capture_omission_f1_up_exfil_warning_down=[i['point']['f1_up_exfil_warning_down'] for i in group_capture],
            seed_omission_f1_up_exfil_warning_down=[i['point']['f1_up_exfil_warning_down'] for i in group_seed]))
    equivalent=[]
    for value in signatures.values():
        equivalent.append({**value,'size':len(value['members'])})
    original81=[i for i in full if i['spec']['study']=='PX081']
    eq_summary=dict(interpretation='Aggregate-equivalent ordered confusion contrasts; neither identical predictions nor independent replications',
        original_pairs=len(original81),original_f1_up_exfil_warning_down=sum(i['point']['f1_up_exfil_warning_down'] for i in original81),
        aggregate_equivalent_classes=len(equivalent),classes_f1_up_exfil_warning_down=sum(i['point']['f1_up_exfil_warning_down'] for i in equivalent),
        repeated_classes=sum(i['size']>1 for i in equivalent),classes=equivalent)
    write(HERE/'FULL_POINTS.json',{'status':'RETROSPECTIVE','comparisons':full})
    write(HERE/'CAPTURE_OMISSIONS.json',{'status':'RETROSPECTIVE_FIXED_PREDICTIONS','comparisons':omissions})
    write(HERE/'SEED_OMISSIONS.json',{'status':'ARITHMETIC_MEANS_NOT_POOLED_FLOWS','groups':seed_omissions})
    write(HERE/'CAPTURE_OMISSION_MEANS.json',{'status':'ARITHMETIC_THREE_SEED_POINT_MEANS','groups':capture_means})
    write(HERE/'SUMMARY.json',{'interpretation':'Finite observed omission ranges, not confidence intervals','groups':summaries})
    write(HERE/'AGGREGATE_EQUIVALENCE.json',eq_summary)
    csvfile(HERE/'CAPTURE_OMISSIONS.csv',flatten_rows(omissions,'omitted_capture'))
    csvfile(HERE/'SEED_OMISSIONS.csv',flatten_rows(seed_omissions,'omitted_seed'))
    if (len(omissions),len(seed_omissions),len(capture_means),len(summaries))!=(180,36,60,12):raise ValueError('Incomplete analysis scope')
    outputs=('FULL_POINTS.json','CAPTURE_OMISSIONS.json','SEED_OMISSIONS.json','CAPTURE_OMISSION_MEANS.json',
             'SUMMARY.json','AGGREGATE_EQUIVALENCE.json','CAPTURE_OMISSIONS.csv','SEED_OMISSIONS.csv')
    write(HERE/'AUDIT.json',dict(status='PASS',utc=utc(),freeze_commit=commit,freeze_sha256=sha(HERE/'FREEZE.json'),
        input_manifest_sha256=sha(HERE/'INPUTS.json'),source_sha256=sha(__file__),public_only=True,private_files_opened=0,new_fits=0,
        full_pairs=36,capture_omission_pairs=180,seed_omission_means=36,capture_omission_seed_means=60,
        scalar_crosschecks=checks,independent_formula_source_sha256=sha(PUBLIC/'verify_public.py'),
        outputs_sha256={name:sha(HERE/name) for name in outputs},
        scope='Confusion arithmetic and fixed prediction sensitivity, not refitting or independent campaign validation'))
    print(json.dumps({'status':'PASS','capture_omissions':180,'seed_omissions':36,'scalar_checks':checks,
        'original_pairs':eq_summary['original_pairs'],'original_reversals':eq_summary['original_f1_up_exfil_warning_down'],
        'aggregate_equivalent_classes':eq_summary['aggregate_equivalent_classes'],
        'class_reversals':eq_summary['classes_f1_up_exfil_warning_down']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('freeze','run'));parser.add_argument('--commit')
    args=parser.parse_args()
    if args.action=='freeze':freeze()
    else:
        if not args.commit:parser.error('--commit is required for actual computation')
        run(args.commit)
