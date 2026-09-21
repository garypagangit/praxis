"""Independently audit saved E1 predictions and describe E1/E4 pilot outcomes.

No classifier is fitted. CPU/GPU runs can be combined only when every input,
protocol, support set, class order and completed-cell binding agrees. Repeated
seeds share one test set; this module deliberately produces no significance CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

try:
    from .conformal import evaluate_lac
except ImportError:
    from conformal import evaluate_lac

NOTICE = ('Descriptive within-training development results. Fitting seeds share one '
          'test set and are not independent incidents. No significance, temporal, '
          'population-coverage or unseen-stage risk guarantee is established.')
COMMON_KEYS = ('data_sha256','manifest_sha256','protocol_sha256','code_sha256')


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def value_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def require(condition,message):
    if not condition:
        raise ValueError(message)


def probabilities(prob, labels, n_classes):
    prob=np.asarray(prob)
    labels=np.asarray(labels)
    require(prob.shape==(len(labels),n_classes),'Probability shape mismatch')
    require(labels.ndim==1 and np.issubdtype(labels.dtype,np.integer),'Class IDs must be integers')
    require(np.all((labels>=0)&(labels<n_classes)),'Class ID outside declared classes')
    require(np.isfinite(prob).all(),'Nonfinite probabilities')
    require(np.all((prob>=0)&(prob<=1)),'Probabilities outside [0,1]')
    require(np.allclose(prob.sum(axis=1),1,rtol=0,atol=1e-6),'Probability rows do not sum to one')
    return prob,labels


def recompute_metrics(labels,prob,class_names):
    prob,labels=probabilities(prob,labels,len(class_names))
    require(len(labels)>0,'Empty evaluation partition')
    guess=prob.argmax(axis=1)
    matrix=np.zeros((len(class_names),len(class_names)),dtype=np.int64)
    np.add.at(matrix,(labels,guess),1)
    stage={}
    for k,name in enumerate(class_names):
        tp=int(matrix[k,k]); support=int(matrix[k].sum()); predicted=int(matrix[:,k].sum())
        precision=tp/predicted if predicted else 0.0
        recall=tp/support if support else 0.0
        f1=2*tp/(support+predicted) if support+predicted else 0.0
        truth=labels==k
        auc=float(roc_auc_score(truth,prob[:,k])) if truth.any() and (~truth).any() else None
        ap=float(average_precision_score(truth,prob[:,k])) if truth.any() else None
        stage[name]={'precision':precision,'recall':recall,'f1':f1,'support':support,
                     'true_positive':tp,'false_positive':predicted-tp,'false_negative':support-tp,
                     'roc_auc_ovr':auc,'average_precision_ovr':ap}
    aucs=[v['roc_auc_ovr'] for v in stage.values()]
    aps=[v['average_precision_ovr'] for v in stage.values()]
    return {'n':len(labels),'accuracy':float(np.trace(matrix)/len(labels)),
            'macro_f1':float(np.mean([v['f1'] for v in stage.values()])),
            'roc_auc_ovr_macro':float(np.mean(aucs)) if all(v is not None for v in aucs) else None,
            'average_precision_ovr_macro':float(np.mean(aps)) if all(v is not None for v in aps) else None,
            'classes':list(class_names),'confusion_matrix':matrix.tolist(),'per_stage':stage}


def check_reported_metrics(reported,actual):
    for key in ['n','classes','confusion_matrix']:
        require(reported.get(key)==actual[key],f'Reported {key} does not match saved predictions')
    for key in ['accuracy','macro_f1','roc_auc_ovr_macro','average_precision_ovr_macro']:
        a,b=reported.get(key),actual[key]
        require((a is None and b is None) or (a is not None and b is not None and np.isclose(a,b,rtol=0,atol=1e-10)),f'Reported {key} disagrees')
    for name,values in actual['per_stage'].items():
        for key in ['precision','recall','f1','support','roc_auc_ovr','average_precision_ovr']:
            a,b=reported['per_stage'][name].get(key),values[key]
            require((a is None and b is None) or (a is not None and b is not None and np.isclose(a,b,rtol=0,atol=1e-10)),f'Reported {name}/{key} disagrees')


def fit_support(data,seed,budget):
    rng=np.random.default_rng(seed)
    rows=[]
    for k in range(len(data['classes'])):
        candidates=np.flatnonzero((data['split']==0)&(data['y']==k))
        candidates=candidates[np.argsort(data['group_sha256'][candidates],kind='stable')]
        require(len(candidates)>=budget,'Unsupported class budget')
        rows.extend(rng.choice(candidates,size=budget,replace=False).tolist())
    return np.asarray(rows,dtype=np.int64)


def validate_cv(cell,protocol):
    if cell['model'] not in ('xgboost','lightgbm'):
        require(cell.get('inner_cv') is None,'Unexpected inner CV on fixed model')
        return None
    cv=cell['inner_cv']; candidates=cv['candidates'];grid=protocol['model_grids'][cell['model']]
    require(len(candidates)==len(grid),'CV candidate count differs from protocol')
    means=[]
    for candidate,params in zip(candidates,grid):
        scores=np.asarray(candidate['fold_macro_f1'],dtype=float)
        require(scores.shape==(protocol['n_splits'],) and np.isfinite(scores).all() and np.all((scores>=0)&(scores<=1)),'Invalid fold scores')
        require(candidate['parameters']==params,'CV grid differs from protocol')
        require(np.isclose(candidate['mean_macro_f1'],scores.mean(),rtol=0,atol=1e-12),'CV mean inconsistent with folds')
        means.append(float(scores.mean()))
    winner=int(np.argmax(means))
    require(cv['selected_candidate_index']==winner and cv['selected_parameters']==grid[winner],'CV selected wrong candidate')
    require(np.isclose(cv['selected_mean_macro_f1'],means[winner],rtol=0,atol=1e-12),'Wrong selected CV score')
    require(cv['selection_data']=='selected fit support only','Selection used unqualified data')
    return means[winner]


def summarize(values):
    values=[float(v) for v in values if v is not None]
    return {'mean':float(np.mean(values)),'min':min(values),'max':max(values),'seed_count':len(values)} if values else {'mean':None,'min':None,'max':None,'seed_count':0}


def lac_result(cell,nominal=.9,method='marginal'):
    return next(e['metrics'] for e in cell['e4']['evaluations'] if e['nominal_coverage']==nominal and e['method']==method)


def compare_primary(cells,protocol):
    grouped={}
    for cell in cells:
        grouped.setdefault(cell['seed'],{})[cell['model']]=cell
    rows=[]
    risky=protocol['e1_development_gate']['high_risk_classes']
    for seed in protocol['seeds']:
        available=grouped.get(seed,{})
        if not {'tabicl_v2','xgboost','lightgbm'}<=available.keys():
            continue
        baseline=max([available['xgboost'],available['lightgbm']],key=lambda c:c['inner_cv_selected_macro_f1'])
        candidate=available['tabicl_v2']
        recall_delta={name:candidate['test_metrics']['per_stage'][name]['recall']-baseline['test_metrics']['per_stage'][name]['recall'] for name in risky}
        cm,bm=lac_result(candidate),lac_result(baseline)
        delta=candidate['test_metrics']['macro_f1']-baseline['test_metrics']['macro_f1']
        e1_gate=protocol['e1_development_gate'];e4_gate=protocol['e4']['development_gate']
        seed_e1={'macro_f1_gain':delta>=e1_gate['macro_f1_delta_min'],
                 **{f'{name}_recall':v>=e1_gate['mean_recall_delta_min'] for name,v in recall_delta.items()}}
        seed_e4={'set_size':cm['mean_set_size']<=e4_gate['candidate_to_comparator_mean_set_size_max']*bm['mean_set_size'],
                 'pooled_coverage':cm['coverage']>=e4_gate['observed_pooled_coverage_min'],
                 'every_class_coverage':all(c['coverage'] is not None and c['coverage']>=e4_gate['observed_per_class_coverage_min'] for c in cm['per_class'])}
        rows.append({'seed':seed,'comparator_selected_on_inner_cv':baseline['model'],
                     'candidate_macro_f1':candidate['test_metrics']['macro_f1'],
                     'comparator_macro_f1':baseline['test_metrics']['macro_f1'],
                     'delta_macro_f1':delta,'e1_per_seed_guards':seed_e1,'e4_per_seed_guards':seed_e4,
                     'high_risk_recall_deltas':recall_delta,
                     'e4_marginal90':{'candidate_mean_set_size':cm['mean_set_size'],'comparator_mean_set_size':bm['mean_set_size'],
                                     'candidate_coverage':cm['coverage'],'comparator_coverage':bm['coverage'],
                                     'candidate_covered':cm['covered'],'comparator_covered':bm['covered'],'test_count':cm['count'],
                                     'candidate_per_class':cm['per_class'],'comparator_per_class':bm['per_class']}})
    complete=len(rows)==len(protocol['seeds']) and len(protocol['seeds'])==10
    delta=summarize([r['delta_macro_f1'] for r in rows])
    recall={name:summarize([r['high_risk_recall_deltas'][name] for r in rows]) for name in risky}
    guards={'macro_f1_gain':delta['mean'] is not None and delta['mean']>=protocol['e1_development_gate']['macro_f1_delta_min'],
            **{f'{name}_recall':s['mean'] is not None and s['mean']>=protocol['e1_development_gate']['mean_recall_delta_min'] for name,s in recall.items()}}
    e1={'status':'PASS' if complete and all(guards.values()) else ('FAIL' if complete else 'INCOMPLETE'),
        'guards':guards,'mean_paired_macro_f1_delta':delta,'high_risk_recall_deltas':recall}
    cm=summarize([r['e4_marginal90']['candidate_mean_set_size'] for r in rows])
    bm=summarize([r['e4_marginal90']['comparator_mean_set_size'] for r in rows])
    coverage=summarize([r['e4_marginal90']['candidate_coverage'] for r in rows])
    class_coverage={}
    if rows:
        for i,c in enumerate(rows[0]['e4_marginal90']['candidate_per_class']):
            class_coverage[c['class_label']]=summarize([r['e4_marginal90']['candidate_per_class'][i]['coverage'] for r in rows])
    thresholds=protocol['e4']['development_gate']
    e4guards={'set_size':cm['mean'] is not None and cm['mean']<=thresholds['candidate_to_comparator_mean_set_size_max']*bm['mean'],
              'pooled_coverage':coverage['mean'] is not None and coverage['mean']>=thresholds['observed_pooled_coverage_min'],
              'every_class_coverage':bool(class_coverage) and all(s['mean'] is not None and s['mean']>=thresholds['observed_per_class_coverage_min'] for s in class_coverage.values())}
    e4={'status':'PASS' if complete and all(e4guards.values()) else ('FAIL' if complete else 'INCOMPLETE'),
        'primary_method':'marginal LAC at nominal 90%','guards':e4guards,'candidate_mean_set_size':cm,
        'comparator_mean_set_size':bm,'candidate_pooled_coverage':coverage,'candidate_per_class_coverage':class_coverage,
        'candidate_to_comparator_ratio_of_mean_set_sizes':cm['mean']/bm['mean'] if bm['mean'] else None}
    return {'expected_seed_count':len(protocol['seeds']),'matched_seed_count':len(rows),
            'all_ten_registered_seeds_present':complete,'gbdt_tie_policy':'xgboost first',
            'per_seed':rows,'e1':e1,'e4':e4,'interpretation':NOTICE}


def aggregate_models(cells):
    output={}
    for model in sorted({c['model'] for c in cells}):
        selected=[c for c in cells if c['model']==model]
        summary={'seeds':[c['seed'] for c in selected],
                 'macro_f1':summarize([c['test_metrics']['macro_f1'] for c in selected]),
                 'roc_auc_ovr_macro':summarize([c['test_metrics']['roc_auc_ovr_macro'] for c in selected]),
                 'average_precision_ovr_macro':summarize([c['test_metrics']['average_precision_ovr_macro'] for c in selected]),
                 'per_stage':{},'e4':[]}
        for name in selected[0]['test_metrics']['classes']:
            summary['per_stage'][name]={key:summarize([c['test_metrics']['per_stage'][name][key] for c in selected]) for key in ['precision','recall','f1','roc_auc_ovr','average_precision_ovr']}
            summary['per_stage'][name]['same_test_support']=selected[0]['test_metrics']['per_stage'][name]['support']
        for nominal in [.9,.95]:
            for method in ['marginal','mondrian']:
                evaluations=[lac_result(c,nominal,method) for c in selected]
                summary['e4'].append({'nominal_coverage':nominal,'method':method,
                    **{key:summarize([v[key] for v in evaluations]) for key in ['coverage','mean_set_size','empty_fraction','full_fraction','singleton_fraction','singleton_accuracy']},
                    'per_class':{name:summarize([v['per_class'][i]['coverage'] for v in evaluations]) for i,name in enumerate(selected[0]['test_metrics']['classes'])}})
        output[model]=summary
    return output


def analyze(data_path,protocol_path,run_roots):
    data_path=Path(data_path);protocol_path=Path(protocol_path)
    if data_path.is_dir():data_path=data_path/'DATA.npz'
    protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
    require(protocol.get('experiment')=='E1','Not an E1 protocol')
    require(file_hash(data_path)==protocol['data_npz_sha256'],'Frozen data digest mismatch')
    require(file_hash(data_path.with_name('MANIFEST.json'))==protocol['manifest_sha256'],'Frozen manifest digest mismatch')
    with np.load(data_path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
    require(len(set(data['group_sha256'].tolist()))==len(data['y']),'Repeated prepared feature groups')
    class_names=data['classes'].tolist()
    require(len(set(class_names))==len(class_names),'Duplicate class names')
    expected_common={'data_sha256':protocol['data_npz_sha256'],'manifest_sha256':protocol['manifest_sha256'],'protocol_sha256':file_hash(protocol_path)}
    common_reference=None;cells=[];seen=set();incomplete=[]
    for root in map(Path,run_roots):
        prefit_path=root/'PREFIT_RECEIPT.json'
        prefit=json.loads(prefit_path.read_text(encoding='utf-8'));execution=prefit['execution']
        require(value_hash(execution)==prefit['execution_binding'],'Invalid prefit execution binding')
        common={key:execution[key] for key in COMMON_KEYS}
        require(all(common[key]==v for key,v in expected_common.items()),'Run input/protocol binding mismatch')
        require(common_reference is None or common==common_reference,'Cannot combine runs with differing source/input/protocol bindings')
        common_reference=common
        require(set(execution['models'])<=set(protocol['models']),'Unregistered run model')
        require(set(execution['supports'])=={str(s) for s in protocol['seeds']},'Prefit seed roster mismatch')
        for seed in protocol['seeds']:
            fit=fit_support(data,seed,protocol['samples_per_class'])
            support={'indices':fit.tolist(),'fingerprints':data['group_sha256'][fit].tolist()}
            require(execution['supports'][str(seed)]==support,'Prefit support differs from deterministic selection')
            binding=value_hash({**common,'seed':seed,'support':support})
            for model in execution['models']:
                cell_dir=root/'cells'/model/str(seed)
                if not (cell_dir/'COMPLETE.json').exists():
                    incomplete.append({'model':model,'seed':seed});continue
                require((model,seed) not in seen,'Duplicate completed model/seed across run roots')
                seen.add((model,seed))
                complete=json.loads((cell_dir/'COMPLETE.json').read_text(encoding='utf-8'))
                require(complete['execution_binding']==prefit['execution_binding'] and complete['comparison_binding']==binding,'Completed cell binding mismatch')
                require(set(complete['file_sha256'])=={'CELL.json','PREDICTIONS.npz'},'Incomplete artifact hash roster')
                for name,digest in complete['file_sha256'].items():require(file_hash(cell_dir/name)==digest,'Cell file digest mismatch')
                cell=json.loads((cell_dir/'CELL.json').read_text(encoding='utf-8'))
                require(cell['model']==model and cell['seed']==seed,'Cell model/seed mismatch')
                require(cell['execution_binding']==prefit['execution_binding'] and cell['comparison_binding']==binding and cell['common_binding']==common,'Cell binding disagrees')
                require(cell['prefit_receipt_sha256']==file_hash(prefit_path),'Prefit receipt changed after fit')
                require(cell['prediction_sha256']==complete['file_sha256']['PREDICTIONS.npz'],'Prediction receipt mismatch')
                require(cell['selected_fit_fingerprints_sha256']==value_hash(support['fingerprints']),'Support fingerprint digest mismatch')
                require(cell['samples_per_class']==protocol['samples_per_class'] and cell['selected_fit_rows']==len(fit),'Fit budget metadata mismatch')
                with np.load(cell_dir/'PREDICTIONS.npz',allow_pickle=False) as z:p={k:z[k] for k in z.files}
                require(np.array_equal(p['classes'],data['classes']),'Probability class order mismatch')
                require(np.array_equal(p['selected_fit_indices'],fit) and np.array_equal(p['selected_fit_fingerprints'],data['group_sha256'][fit]),'Prediction support mismatch')
                metrics={}
                for partition,code in [('calibration',1),('test',2)]:
                    ids=np.flatnonzero(data['split']==code)
                    require(np.array_equal(p[partition+'_indices'],ids),'Prediction rows or order mismatch')
                    require(np.array_equal(p[partition+'_y'],data['y'][ids]),'Prediction labels differ from frozen input')
                    metrics[partition]=recompute_metrics(p[partition+'_y'],p[partition+'_probabilities'],class_names)
                    check_reported_metrics(cell['metrics'][partition],metrics[partition])
                conformal=evaluate_lac(p['calibration_probabilities'],data['classes'][p['calibration_y']],p['test_probabilities'],data['classes'][p['test_y']],class_labels=class_names)
                cells.append({'model':model,'seed':seed,'comparison_binding':binding,'actual_device':cell['actual_device'],
                    'inner_cv_selected_macro_f1':validate_cv(cell,protocol),'inner_cv':cell['inner_cv'],
                    'test_metrics':metrics['test'],'calibration_metrics':metrics['calibration'],'e4':conformal,
                    'timing_seconds':cell['timing_seconds'],'versions':cell['versions'],'prediction_sha256':cell['prediction_sha256']})
    cells.sort(key=lambda c:(c['seed'],c['model']))
    missing=[{'model':m,'seed':s} for m in protocol['models'] for s in protocol['seeds'] if (m,s) not in seen]
    return {'schema_version':1,'audit_status':'PASS','audit_scope':'Input, protocol, support, cell bytes, prediction labels/probabilities, inner-CV arithmetic and independently recomputed metrics',
            'completed_cell_count':len(cells),'missing_registered_cells':missing,'uncompleted_run_cells':incomplete,
            'all_registered_cells_complete':not missing,'common_binding':common_reference,'cells':cells,
            'model_summaries':aggregate_models(cells),'primary':compare_primary(cells,protocol),
            'interpretation':NOTICE,'timing_notice':'Device-specific diagnostic timings only; combining CPU/GPU timings cannot establish E2 throughput superiority.'}


def report_markdown(result):
    p=result['primary']
    lines=['# Few-label APT development pilot: independent analysis','',NOTICE,'',
           f"Audited completed cells: **{result['completed_cell_count']}**. Missing registered cells: **{len(result['missing_registered_cells'])}**.",'',
           f"E1 descriptive gate: **{p['e1']['status']}**. E4 descriptive gate: **{p['e4']['status']}**.",'',
           '| Model | Seeds | Mean macro F1 | Minimum | Maximum |','|---|---:|---:|---:|---:|']
    for model,m in result['model_summaries'].items():
        f=m['macro_f1'];lines.append(f"| {model} | {f['seed_count']} | {f['mean']:.6f} | {f['min']:.6f} | {f['max']:.6f} |")
    lines+=['','The comparator is selected separately for each fitting seed using only inner-CV macro F1; ties choose XGBoost. Test performance does not select the comparator.','',
            f"Matched primary seeds: {p['matched_seed_count']}/{p['expected_seed_count']}. Mean paired macro-F1 delta: {p['e1']['mean_paired_macro_f1_delta']['mean']}.",'',
            f"E1 guards: `{json.dumps(p['e1']['guards'],sort_keys=True)}`.",'',
            f"E4 guards: `{json.dumps(p['e4']['guards'],sort_keys=True)}`. Ratio of mean set sizes: {p['e4']['candidate_to_comparator_ratio_of_mean_set_sizes']}.",'',
            'Per-stage support, precision, recall, F1, one-vs-rest ROC-AUC/AP, confusion matrices, all LAC levels/methods, exact coverage counts, and every gate guard are retained in ANALYSIS.json.','',
            'InitialCompromise has only 15 development-test examples. Reported seed ranges describe training-subsample sensitivity, not independent replication. No confidence interval or significance claim is attached.','',result['timing_notice'],'']
    return '\n'.join(lines)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--run',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):raise FileExistsError('Use a fresh analysis output directory')
    result=analyze(args.data,args.protocol,args.run)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'ANALYSIS.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False),encoding='utf-8')
    (args.output/'REPORT.md').write_text(report_markdown(result),encoding='utf-8')
    print(json.dumps({'audit_status':result['audit_status'],'cells':result['completed_cell_count'],'e1':result['primary']['e1']['status'],'e4':result['primary']['e4']['status']}))
