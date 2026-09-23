"""Frozen retrospective paired reanalysis. Reads predictions; never fits models."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
from experiments.praxis_next.d1_benchmark_audit.paired_metrics import (
    LabelSchema, PredictionBatch, make_group_bootstrap_plan, paired_comparison,
)

PRIVATE = Path('C:/w/apt_benchmark_data_20260920')
DATA = PRIVATE / 'host_history_exfil_v1/prepared/DATA.npz'
PX081 = PRIVATE / 'praxis_next/px081'
PX082 = PRIVATE / 'praxis_next/px082/run_v1'
PUBLIC081 = REPO / 'experiments/praxis_next/px081_evidence_acquisition'
PUBLIC082 = REPO / 'experiments/praxis_next/px082_temporal_audit'
LIBRARY = REPO / 'experiments/praxis_next/d1_benchmark_audit/paired_metrics.py'
DATA_SHA = 'b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14'
NAMES = ('Benign', 'OtherAttackStage', 'LateralMovement', 'DataExfiltration')
SCHEMA = LabelSchema(dict(enumerate(NAMES)), benign_label=0)
SEEDS = {'PX081': (8101, 8102, 8103), 'PX082': (20260923, 20260924, 20260925)}
CONDITIONS = ('clean', 'delayed_unavailable', 'wrong_host_history')
BOOT_SEED = 20260923
BOOT_N = 2000
SOURCE_FILES = ('ANALYSIS_PLAN.md', 'reanalysis.py', 'test_reanalysis.py')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            digest.update(block)
    return digest.hexdigest()


def objsha(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def contrasts():
    output = []
    for condition in CONDITIONS:
        for budget in (1, 2, 3):
            for seed in SEEDS['PX081']:
                stem = f'seed_{seed}/{condition}_b{budget}_'
                output.append(dict(study='PX081', contrast='harm_minus_entropy', condition=condition,
                    budget=budget, seed=seed, baseline=stem+'entropy.npz', candidate=stem+'harm.npz'))
    for seed in SEEDS['PX082']:
        for view in ('current', 'current_history'):
            output.append(dict(study='PX082', contrast=f'{view}_mixed_minus_past', condition='common_anchor',
                budget=None, seed=seed, baseline=f'{seed}_{view}_past_only_anchor.npz',
                candidate=f'{seed}_{view}_time_mixed_anchor.npz'))
        output.append(dict(study='PX082', contrast='chronological_history_minus_current', condition='common_anchor',
            budget=None, seed=seed, baseline=f'{seed}_current_past_only_anchor.npz',
            candidate=f'{seed}_current_history_past_only_anchor.npz'))
    return output


def validate_probabilities(p, rows):
    p = np.asarray(p)
    if p.shape != (rows, 4) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('Expected finite nonnegative native four-column probabilities')
    if not np.allclose(p.sum(axis=1), 1., rtol=1e-6, atol=1e-6):
        raise ValueError('Probability rows do not sum to one')
    return p.argmax(axis=1)


def require_equal(actual, expected, description):
    if not np.array_equal(actual, expected):
        raise ValueError('Identity mismatch: ' + description)


def source_identities():
    # Load only identity/label/group arrays, not model features.
    with np.load(DATA, allow_pickle=False) as z:
        data = {key: z[key] for key in ('y', 'split', 'capture', 'group_sha256')}
    later = np.flatnonzero(data['split'] == 2)
    with np.load(PX081/'evaluation_identity.npz', allow_pickle=False) as z:
        require_equal(z['y'], data['y'][later], 'PX081 truth')
        require_equal(z['capture'], data['capture'][later], 'PX081 capture')
        require_equal(z['event_hash'], data['group_sha256'][later], 'PX081 event order')
    with np.load(PX082/'DESIGN.npz', allow_pickle=False) as z:
        anchor = z['anchor']
    if anchor.ndim != 1 or not np.issubdtype(anchor.dtype, np.integer):
        raise ValueError('Anchor indices must be a native integer vector')
    if len(np.unique(anchor)) != len(anchor) or not np.isin(anchor, later).all():
        raise ValueError('Anchor must contain unique original later rows')
    cohorts = {}
    for name, indices in [('PX081', later), ('PX082', anchor)]:
        rows, truth, groups = (data[key][indices] for key in ('group_sha256', 'y', 'capture'))
        if len(np.unique(rows)) != len(rows) or set(np.unique(truth)) != set(range(4)):
            raise ValueError('Unique event IDs and all native classes are required')
        cohorts[name] = dict(indices=indices, rows=rows, truth=truth, groups=groups)
    return cohorts


def inventories():
    """Hash inputs and verify old receipts without evaluating probabilities."""
    if sha(DATA) != DATA_SHA:
        raise ValueError('Prepared source data hash differs')
    audit081 = read(PUBLIC081/'AUDIT.json')
    if sha(PX081/'ARTIFACT_HASHES.json') != audit081['artifact_manifest_sha256']:
        raise ValueError('PX081 original artifact manifest changed')
    manifest081 = {name.replace('\\', '/'): digest for name, digest in read(PX081/'ARTIFACT_HASHES.json').items()}
    complete082 = read(PUBLIC082/'COMPLETE.json')
    if sha(PX082/'COMPLETE.json') != sha(PUBLIC082/'COMPLETE.json'):
        raise ValueError('PX082 original completion receipts differ')
    records = []
    for study, root, manifest, extras in [('PX081', PX081, manifest081, ['evaluation_identity.npz']),
            ('PX082', PX082, complete082['files'], ['DESIGN.npz'])]:
        files = sorted(set(extras + [c[side] for c in contrasts() if c['study'] == study for side in ('baseline','candidate')]))
        for name in files:
            digest = sha(root/name)
            if digest != manifest[name]:
                raise ValueError(f'Original prediction hash mismatch: {study}/{name}')
            records.append(dict(study=study, file=name, bytes=(root/name).stat().st_size, sha256=digest))
    receipt_paths = [PUBLIC081/'RUN_RECEIPT.json', PUBLIC081/'AUDIT.json', PUBLIC081/'FREEZE.json',
                     PX081/'ARTIFACT_HASHES.json', PUBLIC082/'COMPLETE.json', PUBLIC082/'STARTED.json',
                     PUBLIC082/'protocol.json', PUBLIC082/'AUDIT.json']
    return dict(data_sha256=DATA_SHA, private_input_roots={'PX081':str(PX081),'PX082':str(PX082)},
                files=records, original_receipts=[{'path':str(p),'sha256':sha(p)} for p in receipt_paths])


def freeze():
    if (HERE/'FREEZE.json').exists():
        raise ValueError('Freeze already exists; do not overwrite')
    inputs = inventories()
    cohorts = source_identities()
    inputs['identity_qualification'] = {name:{'rows':len(c['truth']), 'groups':np.unique(c['groups']).tolist(),
        'class_counts':np.bincount(c['truth'], minlength=4).tolist(), 'unique_event_ids':True,
        'original_identity_alignment':True} for name,c in cohorts.items()}
    write(HERE/'INPUTS.json', inputs)
    write(HERE/'FREEZE.json', dict(status='RETROSPECTIVE_ANALYSIS_FROZEN_BEFORE_COMPLETE_REANALYSIS',
        utc=datetime.now(timezone.utc).isoformat(), source_sha256={name:sha(HERE/name) for name in SOURCE_FILES},
        inputs_sha256=sha(HERE/'INPUTS.json'), metric_library_sha256=sha(LIBRARY),
        contrasts=len(contrasts()), bootstrap_draws=BOOT_N, bootstrap_seed=BOOT_SEED))
    print(json.dumps({'freeze_ready':True,'prediction_files':len(inputs['files'])-2,'comparisons':36}))


def verify_frozen(commit):
    frozen = read(HERE/'FREEZE.json')
    for name, digest in frozen['source_sha256'].items():
        if sha(HERE/name) != digest:
            raise ValueError('Frozen source changed: '+name)
    if sha(LIBRARY) != frozen['metric_library_sha256'] or sha(HERE/'INPUTS.json') != frozen['inputs_sha256']:
        raise ValueError('Metric library or input inventory changed')
    # Git bytes are checked as well as the in-file receipt; no shell interpolation.
    for path in [HERE/name for name in (*SOURCE_FILES, 'INPUTS.json', 'FREEZE.json')] + [LIBRARY]:
        relative = path.relative_to(REPO).as_posix()
        committed = subprocess.check_output(['git','show',f'{commit}:{relative}'], cwd=REPO)
        if hashlib.sha256(committed).hexdigest() != sha(path):
            raise ValueError('Git freeze byte mismatch: '+relative)
    previous = read(HERE/'INPUTS.json')
    fresh = inventories()
    for key in fresh:
        if fresh[key] != previous[key]:
            raise ValueError('Input inventory mismatch: '+key)
    return frozen


def load_prediction(study, file, cohort):
    root = PX081 if study == 'PX081' else PX082
    with np.load(root/file, allow_pickle=False) as z:
        if study == 'PX082':
            for field, expected in [('test',cohort['indices']),('y',cohort['truth']),('capture',cohort['groups'])]:
                require_equal(z[field], expected, f'{file}/{field}')
        return validate_probabilities(z['probabilities' if study == 'PX081' else 'p'], len(cohort['truth']))


def interval(values):
    values = np.asarray([np.nan if v is None else v for v in values], dtype=float)
    good = values[np.isfinite(values)]
    bounds = np.quantile(good, [.025,.975], method='linear').tolist() if len(good)>=2 else [None,None]
    return dict(lower=bounds[0],upper=bounds[1],confidence=.95,valid_replicates=int(len(good)),
        undefined_replicates=int(len(values)-len(good)),conditional_on_required_label_support=len(good)<len(values),
        status='INSUFFICIENT_DEFINED_REPLICATES' if len(good)<2 else 'SUPPORT_CONDITIONAL' if len(good)<len(values) else 'COMPLETE')


def capture_confusions(truth, pred, groups, ordered_groups):
    output = np.zeros((len(ordered_groups),4,4), dtype=np.int64)
    for i,group in enumerate(ordered_groups):
        mask = groups == group
        np.add.at(output[i], (truth[mask],pred[mask]), 1)
    return output


def independent_quantities(cms):
    """Vectorized arithmetic audit, independent of D1 metric implementation."""
    cms=np.asarray(cms, dtype=np.float64)
    support=cms.sum(axis=-1); called=cms.sum(axis=-2)
    tp=np.diagonal(cms, axis1=-2, axis2=-1)
    with np.errstate(divide='ignore',invalid='ignore'):
        f1=2*tp/(support+called)
        f1=np.where(support>0,f1,np.nan)
        exact=tp/support
        warning=(support-cms[..., :,0])/support
        fpr=(support[...,0]-cms[...,0,0])/support[...,0]
    out={'macro_f1':np.mean(f1,axis=-1),'benign_false_alert_rate':fpr,
         'benign_false_alert_count':support[...,0]-cms[...,0,0],
         'attack_to_benign_count':cms[...,1:,0].sum(axis=-1),
         'wrong_attack_stage_count':(support[...,1:]-cms[...,1:,0]-tp[...,1:]).sum(axis=-1)}
    for i,name in enumerate(NAMES[1:],1):
        for key,value in [('exact_stage_recall',exact[...,i]),('warning_recall',warning[...,i]),
                          ('stage_f1',f1[...,i]),('attack_to_benign_count',cms[...,i,0]),
                          ('wrong_attack_stage_count',support[...,i]-cms[...,i,0]-tp[...,i])]:
            out[name+'.'+key]=value
    return out


def flat_points(result, side):
    m=result[side]
    out={key:m[key] for key in ('macro_f1','benign_false_alert_rate','benign_false_alert_count',
                                'attack_to_benign_count','wrong_attack_stage_count')}
    for name,stage in m['stages'].items():
        for key in ('exact_stage_recall','warning_recall','attack_to_benign_count','wrong_attack_stage_count'):
            out[name+'.'+key]=stage[key]
        out[name+'.stage_f1']=stage['f1']
    return out


def interval_key(key):
    if '.' not in key:
        return ('delta_'+key,)
    name,metric=key.split('.')
    return ('stages',name,'delta_'+metric)


def nested_get(obj,path):
    for key in path:obj=obj[key]
    return obj


def nested_set(obj,path,value):
    for key in path[:-1]:obj=obj.setdefault(key,{})
    obj[path[-1]]=value


def audit_and_extend(result, left_cm, right_cm, weights):
    """Recompute every point/CI; add count intervals absent from D1 output."""
    before=independent_quantities(left_cm.sum(axis=0)); after=independent_quantities(right_cm.sum(axis=0))
    sampled_before=independent_quantities(np.einsum('bg,gij->bij',weights,left_cm))
    sampled_after=independent_quantities(np.einsum('bg,gij->bij',weights,right_cm))
    points_a=flat_points(result,'baseline'); points_b=flat_points(result,'candidate')
    intervals=result['bootstrap']['intervals']
    for key in before:
        for observed,expected in [(points_a[key],before[key]),(points_b[key],after[key])]:
            if not np.isclose(observed,expected,rtol=1e-12,atol=1e-12):
                raise ValueError('Independent point audit failed: '+key)
        path=interval_key(key)
        expected_interval=interval(sampled_after[key]-sampled_before[key])
        try:
            actual_interval=nested_get(intervals,path)
        except KeyError:
            nested_set(intervals,path,expected_interval)
        else:
            for field in ('lower','upper'):
                av,ev=actual_interval[field],expected_interval[field]
                if not ((av is None and ev is None) or (av is not None and ev is not None and np.isclose(av,ev,rtol=1e-10,atol=1e-12))):
                    raise ValueError('Independent percentile audit failed: '+key)
            for field in ('valid_replicates','undefined_replicates','conditional_on_required_label_support','status'):
                if actual_interval[field]!=expected_interval[field]:raise ValueError('Support audit failed: '+key)
        expected_delta=float(after[key]-before[key])
        try:
            actual_delta=nested_get(result['paired_deltas'],path)
        except KeyError:
            nested_set(result['paired_deltas'],path,expected_delta)
        else:
            if not np.isclose(actual_delta,expected_delta,rtol=1e-12,atol=1e-12):
                raise ValueError('Independent paired difference failed: '+key)
    return len(before)


def aggregate(results):
    groups={}
    for item in results:
        s=item['spec'];key=(s['study'],s['contrast'],s['condition'],s['budget'])
        groups.setdefault(key,[]).append(item)
    out=[]
    for key,items in groups.items():
        study,contrast,condition,budget=key
        if sorted(i['spec']['seed'] for i in items)!=list(SEEDS[study]):
            raise ValueError('Aggregation requires exactly three distinct registered seeds')
        record=dict(study=study,contrast=contrast,condition=condition,budget=budget,seeds=list(SEEDS[study]),
                    rows=items[0]['result']['baseline']['rows'],means={},stages={})
        for side in ('baseline','candidate'):
            flattened=[flat_points(i['result'],side) for i in items]
            record['means'][side]={metric:float(np.mean([r[metric] for r in flattened])) for metric in flattened[0]}
        record['means']['delta']={k:record['means']['candidate'][k]-v for k,v in record['means']['baseline'].items()}
        for name in NAMES[1:]:
            stage_values=[i['result']['paired_deltas']['stages'][name] for i in items]
            record['stages'][name]={'support':items[0]['result']['baseline']['stages'][name]['support'],
                'macro_f1_up_warning_down_seeds':sum(v['macro_f1_up_warning_down'] for v in stage_values),
                'macro_f1_down_warning_up_seeds':sum(v['macro_f1_down_warning_up'] for v in stage_values),
                'warning_down_seeds':sum(v['delta_warning_recall'] < -1e-12 for v in stage_values),
                'warning_up_seeds':sum(v['delta_warning_recall'] > 1e-12 for v in stage_values)}
        out.append(record)
    return out


def csv_write(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def tabular_outputs(results,means):
    rows=[]
    for item in results:
        r=item['result'];spec=item['spec']
        for metric,before in flat_points(r,'baseline').items():
            path=interval_key(metric);bounds=nested_get(r['bootstrap']['intervals'],path)
            rows.append({**{k:spec[k] for k in ('study','contrast','condition','budget','seed')},'metric':metric,
                         'baseline':before,'candidate':flat_points(r,'candidate')[metric],
                         'delta':nested_get(r['paired_deltas'],path),**bounds})
    csv_write(HERE/'PAIRED_METRICS.csv',rows)
    rows=[]
    for r in means:
        for metric,before in r['means']['baseline'].items():
            rows.append({**{k:r[k] for k in ('study','contrast','condition','budget','rows')},'metric':metric,
                         'baseline_mean':before,'candidate_mean':r['means']['candidate'][metric],
                         'delta_mean':r['means']['delta'][metric],'seed_count':3})
    csv_write(HERE/'MEANS.csv',rows)


def run(commit):
    if (HERE/'PAIRED_RESULTS.json').exists():raise ValueError('Results already exist; do not silently overwrite')
    frozen=verify_frozen(commit)
    cohorts=source_identities(); plans={}; draw_lists=[]
    for study,c in cohorts.items():
        plans[study]=make_group_bootstrap_plan(c['rows'],c['groups'],group_unit='capture fragment within one UNRAVELED campaign',
                                              n_resamples=BOOT_N,seed=BOOT_SEED)
        draw_lists.append(plans[study].draws)
    if draw_lists[0]!=draw_lists[1]:raise ValueError('Cross-cohort capture multiplicities differ')
    ordered_groups=list(dict.fromkeys(cohorts['PX081']['groups'].tolist()))
    draws=[list(d) for d in draw_lists[0]]
    weights=np.asarray([[draw.count(g) for g in ordered_groups] for draw in draws],dtype=np.int64)
    write(HERE/'CAPTURE_DRAWS.json',dict(seed=BOOT_SEED,replicates=BOOT_N,ordered_captures=ordered_groups,
        draws_sha256=objsha(draws),draws=draws,interpretation='Shared capture fragments, not independent campaigns'))
    cache={};results=[];statistics={};checks=0
    for spec in contrasts():
        study=spec['study'];c=cohorts[study];preds=[]
        for side in ('baseline','candidate'):
            key=(study,spec[side])
            if key not in cache:cache[key]=load_prediction(study,spec[side],c)
            pred=cache[key];preds.append(pred)
            if '/'.join(key) not in statistics:
                statistics['/'.join(key)]=capture_confusions(c['truth'],pred,c['groups'],ordered_groups).tolist()
        batches=[PredictionBatch(c['rows'],c['truth'],pred,SCHEMA,c['groups']) for pred in preds]
        result=paired_comparison(*batches,bootstrap=plans[study])
        checks+=audit_and_extend(result,np.asarray(statistics[study+'/'+spec['baseline']]),
                                np.asarray(statistics[study+'/'+spec['candidate']]),weights)
        results.append(dict(spec=spec,result=result))
        print(json.dumps({'completed':len(results),'study':study,'contrast':spec['contrast'],'seed':spec['seed']}),flush=True)
    means=aggregate(results)
    write(HERE/'PAIRED_RESULTS.json',dict(status='RETROSPECTIVE',comparison_count=len(results),results=results))
    write(HERE/'MEANS.json',dict(status='THREE_SEED_POINT_MEANS_ONLY_NO_POOLED_CI',groups=means))
    write(HERE/'CAPTURE_CONFUSIONS.json',dict(ordered_captures=ordered_groups,native_class_order=list(NAMES),tables=statistics))
    tabular_outputs(results,means)
    plan_hashes={study:next(i['result']['bootstrap']['paired_draws_sha256'] for i in results if i['spec']['study']==study) for study in cohorts}
    for study in cohorts:
        if {i['result']['bootstrap']['paired_draws_sha256'] for i in results if i['spec']['study']==study}!={plan_hashes[study]}:
            raise ValueError('A comparison or seed used different cohort bootstrap draws')
    output_files=('PAIRED_RESULTS.json','MEANS.json','CAPTURE_CONFUSIONS.json','CAPTURE_DRAWS.json','PAIRED_METRICS.csv','MEANS.csv')
    receipt=dict(status='PASS',analysis_status='RETROSPECTIVE',utc=datetime.now(timezone.utc).isoformat(),freeze_commit=commit,
        freeze_sha256=sha(HERE/'FREEZE.json'),input_inventory_sha256=sha(HERE/'INPUTS.json'),metric_library_sha256=frozen['metric_library_sha256'],
        prediction_files_verified=len(cache),paired_comparisons=len(results),three_seed_mean_groups=len(means),
        independently_checked_point_and_interval_quantities=checks,bootstrap_draws_per_comparison=BOOT_N,
        shared_capture_draws_sha256=objsha(draws),row_bound_plan_sha256=plan_hashes,
        raw_predictions_exported=False,new_fits=0,compute='local CPU arithmetic only',
        scope='Recomputation and identity/hash audit; not human label validation or independent-campaign inference',
        outputs_sha256={name:sha(HERE/name) for name in output_files})
    write(HERE/'AUDIT.json',receipt)
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('freeze','run'));ap.add_argument('--commit')
    args=ap.parse_args()
    if args.action=='freeze':freeze()
    else:
        if not args.commit:ap.error('run requires parent-provided --commit')
        run(args.commit)
