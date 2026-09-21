"""Independently audit saved Sandworm transfer artifacts, without model imports or fits."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np

SEEDS=list(range(20260921,20260931))
MODELS=['selected_gbdt','tabicl_v2']
CLASSES=['DataExfiltration','InitialCompromise','LateralMovement','NormalTraffic','Pivoting','Reconnaissance']
PROTOCOL_SHA='ef42dd21680a2d0f9843ba439c3889a8e8804a183346c4d0adc2bacf01b5cfd8'
E1_PROTOCOL_SHA='9d4c69f9ab8af48dae44aae6c237a25cedc56a1f50eff819513fa2e9beb7c687'
CHECKPOINT_SHA='bdc7dbd5e4ff21f8f0456fcf90c6b7cdf72dbea960f2d05b19bec19f9b3d4ed0'
RUNNER_SHA='e80e27c2747ab212853008eff596eb2fb2119b6ee6adcea4b2a27a7c030cce5f'
PROCEDURES={'Normal':2054,'PHP_insecure_intrusion':16,'smb_intrusion':8,'rdp_intrusion':7,'ssh_intrusion':5,'remote_system_discovery':1}


def require(condition,message):
    if not condition:raise ValueError(message)


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def value_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def compare(actual,expected,path='value'):
    if isinstance(expected,dict):
        require(isinstance(actual,dict) and set(actual)==set(expected),path+' keys differ')
        for key,value in expected.items():compare(actual[key],value,path+'/'+str(key))
    elif isinstance(expected,list):
        require(isinstance(actual,list) and len(actual)==len(expected),path+' length differs')
        for index,value in enumerate(expected):compare(actual[index],value,path+'/'+str(index))
    elif isinstance(expected,float):
        require(isinstance(actual,(int,float)) and np.isfinite(actual) and np.isclose(actual,expected,rtol=0,atol=1e-10),path+' numeric value differs')
    else:require(actual==expected,path+' differs')


def verify_files(folder,hashes,names):
    require(set(hashes)==set(names),'File receipt roster differs')
    for name in names:require(digest(folder/name)==hashes[name],'Artifact hash mismatch: '+name)


def ranking_metrics(y,score,weights):
    """Weighted pair-count ROC-AUC and grouped-threshold AP, including score ties."""
    unique,inverse=np.unique(score,return_inverse=True)
    positive=np.bincount(inverse,weights=weights*y,minlength=len(unique))
    negative=np.bincount(inverse,weights=weights*(1-y),minlength=len(unique))
    p,n=positive.sum(),negative.sum();require(p>0 and n>0,'Both target labels required')
    auc=float(np.sum(positive*(np.cumsum(negative)-negative+0.5*negative))/(p*n))
    true_positive=np.cumsum(positive[::-1]);seen=np.cumsum((positive+negative)[::-1])
    ap=float(np.sum((positive[::-1]/p)*(true_positive/seen)))
    return auc,ap


def recompute_metrics(probabilities,classes,target,weights,*,decision_threshold=None):
    p=np.asarray(probabilities);y=np.asarray(target['y_binary']);weights=np.asarray(weights)
    require(p.shape==(len(y),len(classes)) and np.isfinite(p).all(),'Probability shape/nonfinite failure')
    require(np.all((p>=0)&(p<=1)) and np.allclose(p.sum(1),1,rtol=0,atol=1e-6),'Probability simplex failure')
    require(set(np.unique(y))=={0,1} and np.issubdtype(y.dtype,np.integer),'Invalid binary target')
    require(weights.shape==y.shape and np.issubdtype(weights.dtype,np.integer) and np.all(weights>0),'Invalid multiplicities')
    normal=list(classes).index('NormalTraffic');score=1-p[:,normal]
    guess=(np.argmax(p,axis=1)!=normal).astype(int) if decision_threshold is None else (score>decision_threshold).astype(int)
    count=lambda truth,pred:int(weights[(y==truth)&(guess==pred)].sum())
    tn,fp,fn,tp=count(0,0),count(0,1),count(1,0),count(1,1)
    f1=lambda correct:2*correct/(2*correct+fp+fn) if 2*correct+fp+fn else 0.0
    auc,ap=ranking_metrics(y,score,weights)
    procedures={}
    for name in sorted(set(target['procedure_labels'][y==1].tolist())):
        mask=(target['procedure_labels']==name)&(y==1);total=int(weights[mask].sum());detected=int(weights[mask&(guess==1)].sum())
        procedures[name]={'attack_rows':total,'detected':detected,'missed':total-detected,'recall':detected/total,'unique_query_rows':int(mask.sum())}
    return {'unique_query_rows':len(y),'represented_rows':int(weights.sum()),'confusion_matrix_normal_attack':[[tn,fp],[fn,tp]],
            'normal_rows':tn+fp,'attack_rows':tp+fn,'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,
            'attack_precision':tp/(tp+fp) if tp+fp else 0.0,'attack_recall':tp/(tp+fn),'normal_false_positive_rate':fp/(tn+fp),
            'attack_f1':f1(tp),'binary_macro_f1':(f1(tp)+f1(tn))/2,'accuracy':(tn+tp)/int(weights.sum()),
            'roc_auc':auc,'average_precision':ap,'per_procedure_attack_recall':procedures,
            'decision_rule':'Source six-class argmax is not NormalTraffic' if decision_threshold is None else '1 minus NormalTraffic probability strictly exceeds the source-only1%tail threshold',
            'ranking_score':'1 minus source NormalTraffic probability'}


def summary(values):
    require(bool(values),'Cannot summarize absent seeds')
    return {'mean':float(np.mean(values)),'min':float(min(values)),'max':float(max(values)),'seed_count':len(values)}


def always_normal_reference(normal,attack):
    return {'normal_rows':normal,'attack_rows':attack,'accuracy':normal/(normal+attack),
            'binary_macro_f1':normal/(2*normal+attack),'attack_recall':0.0,'attack_f1':0.0,
            'normal_false_positive_rate':0.0,'confusion_matrix_normal_attack':[[normal,0],[attack,0]],
            'attack_average_precision_prevalence_reference':attack/(normal+attack),
            'constant_ranking_roc_auc_reference':0.5}


def aggregate_verified(cells,seeds):
    lookup={(cell['model'],cell['seed']):cell for cell in cells}
    require(len(lookup)==len(cells) and set(lookup)=={(m,s) for m in MODELS for s in seeds},'Incomplete or duplicate cell roster')
    models={};pairs=[]
    metrics=['binary_macro_f1','attack_f1','attack_precision','attack_recall','normal_false_positive_rate','roc_auc','average_precision','true_positive','false_positive','true_negative','false_negative']
    for model in MODELS:
        views={}
        for view in ['deduplicated_primary','raw_flow_sensitivity']:
            rows=[lookup[(model,seed)]['metrics'][view] for seed in seeds]
            values={name:summary([row[name] for row in rows]) for name in metrics}
            values.update(same_target_normal_rows=rows[0]['normal_rows'],same_target_attack_rows=rows[0]['attack_rows'])
            values['per_procedure']={name:{'same_target_attack_rows':rows[0]['per_procedure_attack_recall'][name]['attack_rows'],
                                         **{metric:summary([row['per_procedure_attack_recall'][name][metric] for row in rows]) for metric in ['recall','detected','missed']}}
                                     for name in rows[0]['per_procedure_attack_recall']}
            views[view]=values
        models[model]={'seeds':seeds,'views':views}
    for seed in seeds:
        a,b=lookup[('tabicl_v2',seed)],lookup[('selected_gbdt',seed)]
        pair={'seed':seed,'selected_original_tree':b['actual_model']}
        for output,key in [('binary_macro_f1_delta','binary_macro_f1'),('attack_f1_delta','attack_f1'),('attack_recall_delta','attack_recall'),('normal_fpr_delta','normal_false_positive_rate')]:
            pair[output]=a['metrics']['deduplicated_primary'][key]-b['metrics']['deduplicated_primary'][key]
        pair['raw_flow_sensitivity_deltas']={key:a['metrics']['raw_flow_sensitivity'][key]-b['metrics']['raw_flow_sensitivity'][key] for key in ['binary_macro_f1','attack_f1','attack_recall','normal_false_positive_rate']}
        pairs.append(pair)
    return models,pairs,float(np.mean([p['binary_macro_f1_delta'] for p in pairs]))


def support(source,seed):
    generator=np.random.default_rng(seed);indices=[]
    for label in range(len(source['classes'])):
        pool=np.flatnonzero((source['split']==0)&(source['y']==label))
        ordered=pool[np.argsort(source['group_sha256'][pool],kind='stable')]
        require(len(ordered)>=32,'Source support insufficient')
        indices.extend(generator.choice(ordered,32,replace=False).tolist())
    return np.asarray(indices,dtype=np.int64)


def median_statistics(source,indices):
    values=source['X'][indices]
    return np.asarray([float(np.median(column[np.isfinite(column)])) if np.isfinite(column).any() else 0.0 for column in values.T])


def validate_prediction_arrays(saved,source,target,indices):
    checks={'source_classes':source['classes'],'target_y_binary':target['y_binary'],'target_procedure_labels':target['procedure_labels'],
            'target_fingerprints':target['group_sha256'],'target_raw_to_unique':target['raw_to_unique'],
            'selected_fit_indices':indices,'selected_fit_fingerprints':source['group_sha256'][indices]}
    require(set(saved)==set(checks)|{'target_probabilities','imputer_statistics'},'Prediction archive roster differs')
    for name,expected in checks.items():require(np.array_equal(saved[name],expected),'Prediction binding differs: '+name)
    require(saved['imputer_statistics'].shape==(source['X'].shape[1],) and np.allclose(saved['imputer_statistics'],median_statistics(source,indices),rtol=0,atol=1e-12),'Source-only imputer medians differ')


def cv_choice(cell,original):
    cv=cell['inner_cv'];grid=original['model_grids'][cell['model']]
    require(len(cv['candidates'])==len(grid),'Original CV roster differs');means=[]
    for candidate,params in zip(cv['candidates'],grid):
        scores=np.asarray(candidate['fold_macro_f1']);require(scores.shape==(3,) and np.isfinite(scores).all() and np.all((scores>=0)&(scores<=1)),'Invalid source CV folds')
        compare(candidate['parameters'],params,'CV parameters');mean=float(scores.mean());compare(candidate['mean_macro_f1'],mean,'CV mean');means.append(mean)
    winner=int(np.argmax(means));require(cv['selected_candidate_index']==winner,'Original CV winner differs')
    compare(cv['selected_parameters'],grid[winner],'Selected source params');compare(cv['selected_mean_macro_f1'],means[winner],'Selected CV score')
    require(cv['selection_data']=='selected fit support only','Original selection role differs')
    return means[winner]


def audit_source_baselines(root,source,original,e1_path,batch_code):
    prefit=read(root/'PREFIT_RECEIPT.json');execution=prefit['execution'];binding=value_hash(execution)
    require(prefit['execution_binding']==binding,'Source prefit binding differs')
    common={'data_sha256':original['data_npz_sha256'],'manifest_sha256':original['manifest_sha256'],'protocol_sha256':digest(e1_path),
            'code_sha256':{name:digest(batch_code/name) for name in ['run_e1.py','model_backend.py','requirementsfoundation.txt','requirements_baselines.txt']}}
    for key,value in common.items():compare(execution[key],value,'Source '+key)
    require(set(execution['models'])=={'random_forest','xgboost','lightgbm'},'Source baseline roster differs')
    require(set(execution['supports'])=={str(s) for s in SEEDS},'Source support roster differs')
    selections={};evidence={'prefit_receipt_sha256':digest(root/'PREFIT_RECEIPT.json'),'execution_binding':binding,'versions':execution['versions'],'cells':{}}
    for seed in SEEDS:
        indices=support(source,seed);selection_support={'indices':indices.tolist(),'fingerprints':source['group_sha256'][indices].tolist()}
        compare(execution['supports'][str(seed)],selection_support,'Source support')
        comparison=value_hash({**common,'seed':seed,'support':selection_support});candidates={}
        for model in ['random_forest','xgboost','lightgbm']:
            folder=root/'cells'/model/str(seed);marker=read(folder/'COMPLETE.json');cell=read(folder/'CELL.json')
            require(marker['execution_binding']==binding and marker['comparison_binding']==comparison,'Source marker binding differs')
            verify_files(folder,marker['file_sha256'],['CELL.json','PREDICTIONS.npz'])
            require(cell['model']==model and cell['seed']==seed and cell['execution_binding']==binding and cell['comparison_binding']==comparison,'Source cell identity differs')
            compare(cell['common_binding'],common,'Source common');require(cell['prefit_receipt_sha256']==evidence['prefit_receipt_sha256'],'Source receipt differs')
            require(cell['selected_fit_fingerprints_sha256']==value_hash(selection_support['fingerprints']),'Source support hash differs')
            with np.load(folder/'PREDICTIONS.npz',allow_pickle=False) as z:
                require(np.array_equal(z['selected_fit_indices'],indices) and np.array_equal(z['selected_fit_fingerprints'],source['group_sha256'][indices]) and np.array_equal(z['classes'],source['classes']),'Original prediction support differs')
                require(np.allclose(z['imputer_statistics'],median_statistics(source,indices),rtol=0,atol=1e-12),'Original imputer differs')
            if model!='random_forest':candidates[model]=(cv_choice(cell,original),cell['inner_cv']['selected_parameters'])
            else:require(cell['inner_cv'] is None,'Unexpected RF tuning')
            evidence['cells'][f'{model}/{seed}']={name:digest(folder/name) for name in ['CELL.json','PREDICTIONS.npz','COMPLETE.json']}
        winner='xgboost' if candidates['xgboost'][0]>=candidates['lightgbm'][0] else 'lightgbm'
        selections[str(seed)]={'selected_tree':winner,'selected_parameters':candidates[winner][1],
                              'cv_scores':{name:item[0] for name,item in candidates.items()},'support':selection_support}
    return selections,evidence


def source_threshold_diagnostic(foundation_root,baseline_root,source_data,e1_path,source,target,selections,run):
    expected=[str(seed) for seed in SEEDS]
    available=[] if foundation_root is None else [str(seed) for seed in SEEDS if (foundation_root/'cells'/'tabicl_v2'/str(seed)/'COMPLETE.json').exists()]
    pending={'status':'PENDING_MATCHING_FULL_SOURCE_CALIBRATION','available_full_source_tabicl_cells':len(available),
             'required_full_source_tabicl_cells':10,'missing_seeds':[int(s) for s in expected if s not in available],
             'reason':'Primary transfer is complete. The separately predeclared source1%tail diagnostic requires all ten matching original full source-calibration prediction cells; no missing cells are inferred or refitted.'}
    if len(available)!=10:return pending
    from ..tabular_batch.analyze_e1 import analyze
    source_audit=analyze(source_data,e1_path,[baseline_root,foundation_root])
    require(source_audit['audit_status']=='PASS','Full source calibration audit failed')
    audited={(cell['model'],cell['seed']) for cell in source_audit['cells']}
    require(all(('tabicl_v2',seed) in audited for seed in SEEDS),'Source foundation roster incomplete after audit')
    normal=CLASSES.index('NormalTraffic');weights=np.bincount(target['raw_to_unique'],minlength=len(target['X']))
    rows=[];receipts={};source_count=29929;rank=int(np.ceil(.99*(source_count+1)))
    for seed in SEEDS:
        selection=selections[str(seed)];indices=np.asarray(selection['support']['indices'])
        for model in MODELS:
            source_model=selection['selected_tree'] if model=='selected_gbdt' else model
            folder=(baseline_root if model=='selected_gbdt' else foundation_root)/'cells'/source_model/str(seed)
            cell=read(folder/'CELL.json')
            with np.load(folder/'PREDICTIONS.npz',allow_pickle=False) as z:
                require(np.array_equal(z['selected_fit_indices'],indices),'Calibration support differs')
                require(np.allclose(z['imputer_statistics'],median_statistics(source,indices),rtol=0,atol=1e-12),'Calibration imputer differs')
                calibration_y=z['calibration_y'];calibration_probabilities=z['calibration_probabilities']
            require(int((calibration_y==normal).sum())==source_count,'Source-normal calibration count differs')
            if model=='tabicl_v2':
                backend=cell['backend_receipt'];settings=backend['constructor_settings']
                require(backend['checkpoint']['sha256']==CHECKPOINT_SHA and backend['fixed_feasibility_ensemble']==4 and cell['actual_device']=='cpu','Calibration foundation configuration differs')
                require(settings['n_estimators']==4 and settings['n_jobs']==1 and settings['random_state']==seed,'Calibration constructor differs')
            scores=1-calibration_probabilities[calibration_y==normal,normal]
            threshold=float(np.sort(scores)[rank-1]);source_fp=int((scores>threshold).sum())
            target_folder=run/'cells'/model/str(seed)
            with np.load(target_folder/'PREDICTIONS.npz',allow_pickle=False) as z:probabilities=z['target_probabilities']
            metrics={view:recompute_metrics(probabilities,CLASSES,target,w,decision_threshold=threshold)
                     for view,w in [('deduplicated_primary',np.ones(len(target['X']),dtype=int)),('raw_flow_sensitivity',weights)]}
            rows.append({'model':model,'actual_model':source_model,'seed':seed,'source_normal_calibration_count':source_count,
                         'threshold_rank_one_based':rank,'threshold':threshold,'source_calibration_false_positives':source_fp,
                         'source_calibration_false_positive_rate':source_fp/source_count,'metrics':metrics})
            receipts[f'{source_model}/{seed}']={name:digest(folder/name) for name in ['CELL.json','PREDICTIONS.npz','COMPLETE.json']}
    models,pairs,mean_delta=aggregate_verified(rows,SEEDS)
    return {'status':'COMPLETE_AUDITED','source_calibration_analysis_value_sha256':value_hash(source_audit),
            'source_calibration_auditor_sha256':digest(Path(__file__).parent.parent/'tabular_batch'/'analyze_e1.py'),
            'source_foundation_prefit_sha256':digest(foundation_root/'PREFIT_RECEIPT.json'),'source_calibration_cell_hashes':receipts,
            'source_normal_calibration_count_per_seed_model':source_count,'threshold_rank_one_based':rank,'strict_greater_than':True,
            'source_target_fpr':.01,'target_labels_used_to_select_threshold':0,'model_summaries':models,'pairs':pairs,
            'mean_binary_macro_f1_delta':mean_delta,'per_seed':rows,
            'interpretation':'Secondary predeclared source-normal operating point;29,929 extra source labels per model/seed. Under target shift its actual false-positive rate can exceed1%. Primary argmax comparison is unchanged. Seeds reuse one capture.'}


def audit(run,source_data,target_data,protocol_path,e1_path,baseline_root,checkpoint,output,*,source_foundation_run=None):
    require(not output.exists() or not any(output.iterdir()),'Audit output must be fresh; preserve previous receipts')
    require((run/'COMPLETE.json').exists(),'Transfer run is incomplete; audit only final immutable artifacts')
    protocol=read(protocol_path);original=read(e1_path)
    require(digest(protocol_path)==PROTOCOL_SHA and digest(e1_path)==E1_PROTOCOL_SHA,'Frozen protocol bytes differ')
    source_data=source_data/'DATA.npz' if source_data.is_dir() else source_data
    target_data=target_data/'DATA.npz' if target_data.is_dir() else target_data
    source_manifest=source_data.with_name('MANIFEST.json');target_manifest=target_data.with_name('MANIFEST.json')
    for path,key in [(source_data,'source_data_npz_sha256'),(source_manifest,'source_manifest_sha256'),(target_data,'target_data_npz_sha256'),(target_manifest,'target_manifest_sha256')]:
        require(digest(path)==protocol[key],'Data/provenance binding differs: '+key)
    with np.load(source_data,allow_pickle=False) as z:source={k:z[k] for k in z.files}
    with np.load(target_data,allow_pickle=False) as z:target={k:z[k] for k in z.files}
    require(source['classes'].tolist()==CLASSES and np.array_equal(np.unique(source['y']),np.arange(6)),'Source class ordering differs')
    require(source['X'].shape==(153919,73) and len(set(source['group_sha256']))==153919 and set(np.unique(source['split']))=={0,1,2},'Source split contract differs')
    require(not np.isinf(source['X']).any() and target['X'].shape==(2091,73) and np.isfinite(target['X']).all(),'Feature shape/finite contract differs')
    require(np.array_equal(source['feature_names'],target['feature_names']),'Feature order differs')
    observed=dict(zip(*np.unique(target['procedure_labels'],return_counts=True)));compare({k:int(v) for k,v in observed.items()},PROCEDURES,'Target procedure counts')
    require(np.array_equal(target['y_binary'],(target['procedure_labels']!='Normal').astype(int)),'Binary labels differ')
    require(np.array_equal(target['group_sha256'],np.sort(np.unique(target['group_sha256']))) and not set(target['group_sha256']).intersection(source['group_sha256']),'Target duplicate/overlap contract differs')
    for row,fingerprint in zip(target['X'],target['group_sha256']):require(hashlib.sha256(np.asarray(row,dtype='<f8').tobytes()).hexdigest()==fingerprint,'Target feature fingerprint differs')
    mapping=target['raw_to_unique'];require(mapping.shape==(2133,) and np.issubdtype(mapping.dtype,np.integer) and np.all((mapping>=0)&(mapping<2091)),'Raw mapping invalid')
    weights=np.bincount(mapping,minlength=2091);require(np.all(weights>0) and int(target['y_binary'][mapping].sum())==37,'Raw multiplicities differ')
    module=Path(__file__).parent;batch=module.parent/'tabular_batch';manifest=read(target_manifest)
    require(manifest['adapter_sha256']==digest(module/'prepare_sandworm.py') and manifest['target_data_npz_sha256']==digest(target_data),'Adapter manifest binding differs')
    require(manifest['source_data_npz_sha256']==digest(source_data) and manifest['source_manifest_sha256']==digest(source_manifest),'Target source contract differs')
    require(read(source_manifest)['data_npz_sha256']==digest(source_data),'Source manifest binding differs')
    selections,source_evidence=audit_source_baselines(baseline_root,source,original,e1_path,batch)
    prefit=read(run/'PREFIT_RECEIPT.json');execution=prefit['execution'];binding=value_hash(execution);prefit_sha=digest(run/'PREFIT_RECEIPT.json')
    require(prefit['execution_binding']==binding and prefit['transfer_fits_started'] is False,'Transfer prefit differs')
    expected_code={'run_sandworm_transfer.py':digest(module/'run_sandworm_transfer.py'),**{'tabular_batch/'+name:digest(batch/name) for name in ['run_e1.py','analyze_e1.py','model_backend.py','requirementsfoundation.txt','requirements_baselines.txt']}}
    require(expected_code['run_sandworm_transfer.py']==RUNNER_SHA,'Frozen scientific runner changed')
    compare(execution['code_sha256'],expected_code,'Frozen source hashes');compare(execution['source_selections'],selections,'Source selection');compare(execution['source_baseline_evidence'],source_evidence,'Source evidence')
    require(execution['models']==MODELS and execution['device']=='cpu' and execution['cpu_threads']==4 and execution['classes']==CLASSES,'Execution settings differ')
    require(execution['target_training_labels_used']==0 and execution['target_calibration_labels_used']==0,'Target training/calibration declared')
    require(execution['target_query_fingerprints']==target['group_sha256'].tolist() and execution['target_raw_mapping_sha256']==value_hash(mapping.tolist()),'Query context differs')
    require(execution['protocol_sha256']==PROTOCOL_SHA and execution['e1_protocol_sha256']==E1_PROTOCOL_SHA,'Execution protocol differs')
    for key in ['source_data_npz_sha256','source_manifest_sha256','target_data_npz_sha256','target_manifest_sha256']:require(execution[key]==protocol[key],'Execution input differs')
    checkpoint_receipt=execution['foundation_checkpoint'];require(checkpoint_receipt['sha256']==CHECKPOINT_SHA and digest(checkpoint)==CHECKPOINT_SHA,'Checkpoint bytes differ')
    require(checkpoint.stat().st_size==checkpoint_receipt['size_bytes']==110368038 and checkpoint_receipt['package_version']=='2.2.0','Checkpoint metadata differs')
    for name in ['numpy','scipy','scikit-learn','pandas','xgboost','lightgbm']:require(execution['versions'][name]==source_evidence['versions'][name],'Source/target runtime mismatch')
    common={key:execution[key] for key in ['source_data_npz_sha256','source_manifest_sha256','target_data_npz_sha256','target_manifest_sha256','e1_protocol_sha256','protocol_sha256','code_sha256','foundation_checkpoint']}
    marker=read(run/'COMPLETE.json');require(marker['execution_binding']==binding,'Final marker binding differs')
    verify_files(run,marker['artifact_sha256'],['PREFIT_RECEIPT.json','RESULTS.json'])
    expected_roster={f'{m}/{s}' for s in SEEDS for m in MODELS};require(set(marker['cell_complete_sha256'])==expected_roster,'Final cell roster incomplete')
    cells=[];hashes={}
    for seed in SEEDS:
        selection=selections[str(seed)];indices=np.asarray(selection['support']['indices']);comparison=value_hash({**common,'seed':seed,'source_selection':selection})
        for model in MODELS:
            key=f'{model}/{seed}';folder=run/'cells'/model/str(seed)
            require(digest(folder/'COMPLETE.json')==marker['cell_complete_sha256'][key],'Cell completion receipt changed')
            complete=read(folder/'COMPLETE.json');cell=read(folder/'CELL.json');started=read(folder/'STARTED.json')
            require(complete['execution_binding']==binding and complete['comparison_binding']==comparison,'Cell marker binding differs')
            verify_files(folder,complete['file_sha256'],['CELL.json','PREDICTIONS.npz'])
            require(cell['execution_binding']==binding and cell['comparison_binding']==comparison and cell['seed']==seed and cell['model']==model,'Cell identity differs')
            compare(cell['common_binding'],common,'Cell common binding');require(cell['prefit_receipt_sha256']==prefit_sha and cell['started_receipt_sha256']==digest(folder/'STARTED.json'),'Cell receipt linkage differs')
            require(started['execution_binding']==binding and started['comparison_binding']==comparison and started['prefit_receipt_sha256']==prefit_sha,'Start binding differs')
            require(datetime.fromisoformat(prefit['created_utc'])<=datetime.fromisoformat(started['created_utc'])<=datetime.fromisoformat(cell['completed_utc']),'Execution ordering differs')
            require(cell['selected_fit_fingerprints_sha256']==value_hash(selection['support']['fingerprints']),'Fit fingerprint binding differs')
            require(cell['source_fit_rows']==192 and cell['source_fit_labels_per_class']==32 and cell['target_fit_rows']==cell['target_calibration_rows']==0 and cell['new_hyperparameter_search'] is False,'Fit role/budget differs')
            compare(cell['source_tree_selection'],{k:selection[k] for k in ['selected_tree','selected_parameters','cv_scores']},'Cell source tree selection')
            require(cell['device']=='cpu' and cell['versions']==execution['versions'],'Cell environment differs')
            require(all(np.isfinite(v) and v>=0 for v in cell['timing_seconds'].values()),'Invalid execution timing')
            require(cell['prediction_sha256']==digest(folder/'PREDICTIONS.npz'),'Cell prediction hash differs')
            if model=='selected_gbdt':require(cell['actual_model']==selection['selected_tree'] and cell['backend_receipt'] is None,'Selected comparator differs')
            else:
                backend=cell['backend_receipt'];settings=backend['constructor_settings']
                require(cell['actual_model']==model and backend['model_id']==model and backend['checkpoint']==checkpoint_receipt and backend['checkpoint_verified'] is True,'Foundation checkpoint receipt differs')
                expected_settings={'allow_auto_download':False,'checkpoint_version':checkpoint_receipt['filename'],'batch_size':1,'kv_cache':False,'use_amp':False,'use_fa3':False,'offload_mode':'auto','n_jobs':1,'verbose':False,'n_estimators':4,'random_state':seed,'device':'cpu'}
                compare({k:v for k,v in settings.items() if k!='model_path'},expected_settings,'Foundation settings')
                require(Path(settings['model_path']).resolve()==checkpoint.resolve(),'Foundation cache linkage differs')
                require(backend['device']['selected_device']=='cpu' and backend['device']['requested_device']=='cpu' and backend['fixed_feasibility_ensemble']==4 and backend['tuned'] is False and backend['fitted'] is True and backend['runtime_compatibility_tested'] is True,'Foundation runtime declaration differs')
                require(backend['environment']['tabicl']=='2.2.0','Foundation package differs')
            with np.load(folder/'PREDICTIONS.npz',allow_pickle=False) as z:saved={k:z[k] for k in z.files}
            validate_prediction_arrays(saved,source,target,indices)
            metrics={view:recompute_metrics(saved['target_probabilities'],CLASSES,target,w) for view,w in [('deduplicated_primary',np.ones(2091,dtype=int)),('raw_flow_sensitivity',weights)]}
            compare(cell['metrics'],metrics,'Independently recomputed metrics')
            cells.append({'model':model,'actual_model':cell['actual_model'],'seed':seed,'metrics':metrics,'comparison_binding':comparison})
            hashes[key]={name:digest(folder/name) for name in ['STARTED.json','CELL.json','PREDICTIONS.npz','COMPLETE.json']}
    models,pairs,mean_delta=aggregate_verified(cells,SEEDS);reported=read(run/'RESULTS.json')
    require(reported['status']=='COMPLETE' and reported['completed_cells']==reported['required_cells']==20 and reported['paired_seeds']==10,'Reported completion differs')
    require(reported['execution_binding']==binding and reported['prefit_receipt_sha256']==prefit_sha and reported['protocol_sha256']==PROTOCOL_SHA,'Results receipt binding differs')
    require(len(reported['cells'])==20,'Results cell count differs')
    for actual,reported_cell in zip(cells,reported['cells']):
        compare(reported_cell,read(run/'cells'/actual['model']/str(actual['seed'])/'CELL.json'),'Results contains altered cell')
    compare(reported['model_summaries'],models,'Aggregate model summaries');compare(reported['paired_differences'],pairs,'Aggregate paired differences');compare(reported['mean_binary_macro_f1_delta'],mean_delta,'Aggregate mean delta')
    require(reported['decision']=='DESCRIPTIVE_ONLY_NO_PASS_GATE' and reported['target_training_labels_used']==reported['target_calibration_labels_used']==0,'Reported policy differs')
    result={'schema_version':1,'experiment':'SANDWORM_BINARY_TRANSFER','audit_status':'PASS','run_status':'COMPLETE','all_cells_complete':True,
            'verified_cells':20,'paired_seed_count':10,'model_summaries':models,'pairs':pairs,'mean_binary_macro_f1_delta':mean_delta,'per_seed':cells,
            'target_counts':{'unique_rows':2091,'normal_rows':2054,'attack_rows':37,'raw_rows':2133,'procedures':PROCEDURES},
            'execution_binding':binding,'protocol_sha256':PROTOCOL_SHA,'e1_protocol_sha256':E1_PROTOCOL_SHA,'code_sha256':expected_code,
            'frozen_scientific_source_commit':'e49bba6f54f1f2684395ba273c4fa27482e7320f',
            'source_data_npz_sha256':digest(source_data),'source_manifest_sha256':digest(source_manifest),'target_data_npz_sha256':digest(target_data),'target_manifest_sha256':digest(target_manifest),
            'foundation_checkpoint':checkpoint_receipt,'runtime_versions':execution['versions'],'source_baseline_evidence':source_evidence,
            'artifact_hashes':{name:digest(run/name) for name in ['PREFIT_RECEIPT.json','RESULTS.json','COMPLETE.json']},'cell_artifact_hashes':hashes,
            'audit_code_sha256':digest(Path(__file__)),'audited_utc':datetime.now(timezone.utc).isoformat(),'no_refitting_or_inference_performed_by_audit':True,
            'checks':['Frozen input/protocol/source/checkpoint bytes','All source supports and original CV comparator choice','Source-only imputer medians','All20 complete receipt chains and query mappings','Independent weighted confusion/F1, tie-aware ROC-AUC and average precision','All per-procedure counts and20-cell aggregate/paired summaries'],
            'source_threshold_diagnostic':source_threshold_diagnostic(source_foundation_run,baseline_root,source_data,e1_path,source,target,selections,run),
            'always_normal_descriptive_reference':{'label':'Always-normal arithmetic context, not a fitted model, comparison arm or new success gate',
                                                   'added_after_initial_partial_results_for_interpretation':True,
                                                   'views':{'deduplicated_primary':always_normal_reference(2054,37),'raw_flow_sensitivity':always_normal_reference(2096,37)},
                                                   'interpretation':'High accuracy or a binary macro-F1 near0.496 can occur while detecting no attacks. Average-precision prevalence is the constant-score reference. Relative improvement over a poor tree comparator does not establish useful operational detection.'},
            'decision':'DESCRIPTIVE_ONLY_NO_PASS_GATE','interpretation':'One independent target capture with37 author-labeled attack flows; repeated source-fitting seeds are dependent. This does not validate SCVIC six-stage gains, rare-stage protection, missing-log resilience or operational readiness.',
            'raw_flow_sensitivity_notice':'Raw counts reweight fixed unique-query predictions; no duplicated-query inference was performed.'}
    output.mkdir(parents=True,exist_ok=True);(output/'TRANSFER_SUMMARY.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'audit_status':'PASS','all_cells_complete':True,'verified_cells':20,'mean_binary_macro_f1_delta':mean_delta}))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','source-data','target-data','protocol','e1-protocol','source-baselines','checkpoint','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--source-foundation-run',type=Path)
    args=parser.parse_args();audit(args.run,args.source_data,args.target_data,args.protocol,args.e1_protocol,args.source_baselines,args.checkpoint,args.output,source_foundation_run=args.source_foundation_run)
