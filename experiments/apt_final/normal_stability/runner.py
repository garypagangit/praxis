"""Complete the fixed normal-stability family, then replay exposed attack data."""
from __future__ import annotations
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import numpy as np
import torch
from ..native_graph import pilot as old
from ..embedding_baseline.scoring import ExactKNN
from .engine import train_and_cache, load_fold, cache_graph
from .provenance import verify_registration, read, digest
from .scoring import select_fit_rows, build_view_banks, pool_calibration, empirical_tail_margin


def emit(stage, **fields):
    print(json.dumps({'stage':stage, **fields}), flush=True)


def write(path, record):
    temporary = Path(path).with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        return {name:saved[name].copy() for name in saved.files}


def inventory(root):
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def dataset_paths(data_dir, dataset):
    manifest = read(data_dir/'MANIFEST.json')
    matches = [s for s in manifest['datasets'] if s['dataset']==dataset]
    if len(matches)!=1:
        raise ValueError('Missing or duplicate dataset')
    spec=matches[0]
    paths={Path(g['npz']).stem:data_dir/g['npz'] for g in spec['graphs']}
    return spec,paths


def cache_paths(root, manifest):
    return {name:{condition:root/entry['cache_npz'] for condition,entry in views.items()}
            for name,views in manifest['caches'].items()}


def key(reference, arm, role, condition):
    return '__'.join([reference,arm,role,condition])


def query_scores(detectors, cache, role, condition, config):
    result, timing = {}, {}
    for reference, models in detectors.items():
        for arm, detector in models.items():
            name=key(reference,arm,role,condition)
            result[name],timing[name]=detector.score(cache[arm+'_unique'],config['query_chunk_size'],False)
    return result,timing


def expanded(scores, cache, reference, arm, role, condition):
    return scores[key(reference,arm,role,condition)][cache[arm+'_inverse']]


def calibration_scores(scores, calibration_cache, reference, arm, mode):
    clean=expanded(scores,calibration_cache['clean'],reference,arm,'calibration','clean')
    if mode=='clean': return clean
    if mode!='pooled': raise ValueError('Unknown calibration strategy')
    masked=expanded(scores,calibration_cache['masked'],reference,arm,'calibration','masked')
    return pool_calibration(clean,masked)


def normal_metrics(margin, node_type):
    predicted=margin>=0
    return {'n':len(predicted),'alerts':int(predicted.sum()),'false_positive_rate':float(predicted.mean()),
            'by_node_type':{str(int(t)):{'n':int(np.sum(node_type==t)),
                            'alerts':int(predicted[node_type==t].sum()),
                            'false_positive_rate':float(predicted[node_type==t].mean())}
                            for t in np.unique(node_type)}}


def identity(dataset, fold, encoder_seed, bank_seed, strategy, arm, condition, config):
    return {'dataset':dataset,'fold':fold,'encoder_seed':encoder_seed,'bank_seed':bank_seed,
            'strategy':strategy,'representation':arm,'condition':condition,
            'duplicate_of_encoder_seed':config['encoder_seeds'][0] if arm=='local_knn' and encoder_seed!=config['encoder_seeds'][0] else None}


def build_reference_state(banks, metadata, config):
    state={}
    for name in ('bank_row_graph','bank_row_id','pooled_is_masked'):
        state[name]=np.asarray(metadata[name])
    detectors={}
    for reference, representations in banks.items():
        detectors[reference]={}
        for arm,values in representations.items():
            detector=ExactKNN(values,config['neighbors'],config['scale_floor'])
            detectors[reference][arm]=detector
            state.update({reference+'__'+arm+'__'+field:value for field,value in detector.artifact_arrays().items()})
    return state,detectors


def restore_detectors(state, config):
    result={}
    for reference in ('clean','pooled'):
        result[reference]={}
        for arm in config['representations']:
            prefix=reference+'__'+arm+'__'
            detector=ExactKNN(state[prefix+'bank_raw'],config['neighbors'],config['scale_floor'])
            for field,value in detector.artifact_arrays().items():
                if not np.array_equal(value,state[prefix+field]):
                    raise ValueError('Reference state changed while reconstructing exact search')
            result[reference][arm]=detector
    return result


def unique_records(records):
    return [r for r in records if r['duplicate_of_encoder_seed'] is None]


def verify_duplicates(records):
    first={}
    for r in records:
        index=tuple(r[k] for k in ('dataset','fold','bank_seed','strategy','representation','condition'))
        if r['representation']!='local_knn': continue
        if index not in first:
            if r['duplicate_of_encoder_seed'] is not None: raise ValueError('Missing original local-feature result')
            first[index]=r['metrics']
        elif r['duplicate_of_encoder_seed'] is None or first[index]!=r['metrics']:
            raise ValueError('Local-feature duplicate has changed metrics')


def decide(normal, attack, config, baselines):
    normal,attack=unique_records(normal),unique_records(attack)
    result={'scope':'FIXED_DEVELOPMENT_FAMILY','datasets':{},'general_ready_candidates':[],
            'positive_repair_candidates':[],'novelty_established':False,'confirmation':False}
    for dataset in config['datasets']:
        strongest_clean_masked=max(float(np.mean([r['metrics']['f1'] for r in attack if
            r['dataset']==dataset and r['strategy']=='clean' and r['representation']==a and r['condition']=='masked']))
            for a in config['representations'])
        candidates={}
        for strategy in config['strategies']:
            for arm in config['representations']:
                n=[r for r in normal if r['dataset']==dataset and r['strategy']==strategy and r['representation']==arm]
                a=[r for r in attack if r['dataset']==dataset and r['strategy']==strategy and r['representation']==arm]
                normal_ready=all(r['metrics']['false_positive_rate']<=config['readiness_max_fpr'] for r in n)
                detection_ready=all(r['metrics']['false_positive_rate']<=config['readiness_max_fpr'] and
                    r['metrics']['recall']>=config['readiness_min_recall'] for r in a)
                clean_f1=float(np.mean([r['metrics']['f1'] for r in a if r['condition']=='clean']))
                masked_f1=float(np.mean([r['metrics']['f1'] for r in a if r['condition']=='masked']))
                historical_gain=clean_f1-baselines['records'][dataset]['original_best_fixed_mean_clean_f1']
                repair_gain=masked_f1-strongest_clean_masked
                candidates[strategy+'/'+arm]={'normal_ready':normal_ready,'detector_ready':detection_ready,
                    'ready':normal_ready and detection_ready,
                    'normal_worst_fpr':max(r['metrics']['false_positive_rate'] for r in n),
                    'attack_worst_fpr':max(r['metrics']['false_positive_rate'] for r in a),
                    'attack_min_recall':min(r['metrics']['recall'] for r in a),
                    'mean_clean_f1':clean_f1,'mean_masked_f1':masked_f1,
                    'historical_mean_clean_f1_gain':historical_gain,
                    'masked_f1_gain_vs_strongest_clean_strategy':repair_gain,
                    'positive_repair':strategy!='clean' and normal_ready and detection_ready and
                        historical_gain>=config['minimum_mean_f1_improvement'] and
                        repair_gain>=config['minimum_mean_f1_improvement'],
                    'unique_normal_cases':len(n),'unique_attack_cases':len(a)}
        result['datasets'][dataset]={'candidates':candidates,'strongest_clean_strategy_mean_masked_f1':strongest_clean_masked}
    for name in result['datasets'][config['datasets'][0]]['candidates']:
        if all(result['datasets'][d]['candidates'][name]['ready'] for d in config['datasets']):
            result['general_ready_candidates'].append(name)
        if all(result['datasets'][d]['candidates'][name]['positive_repair'] for d in config['datasets']):
            result['positive_repair_candidates'].append(name)
    result['status']='READY_CANDIDATE_REQUIRES_CONFIRMATION' if result['general_ready_candidates'] else 'NO_GO_FIXED_REPAIR_FAMILY'
    return result


def run(config_path,data_dir,output,registration_path,device_name):
    config_path,data_dir,output=map(Path,(config_path,data_dir,output))
    registration=verify_registration(config_path,data_dir,registration_path)
    config=read(config_path)
    if (output/'private').exists() or (output/'NORMAL_FREEZE.json').exists() or (output/'RESULTS.json').exists():
        raise FileExistsError('Scientific output must be new; preserve previous evidence')
    output.mkdir(parents=True,exist_ok=True)
    private=output/'private'; private.mkdir()
    old.configure_reproducibility(config['cpu_threads'])
    device=old.select_device(device_name)
    baseline=read(config_path.with_name('PINNED_BASELINES.json'))
    started=time.perf_counter()
    status={'scope':'POST_RESULT_DEVELOPMENT','status':'NORMAL_PHASE_RUNNING',
            'started_utc':datetime.now(timezone.utc).isoformat(),'source_commit':registration['git_commit'],
            'registration_sha256':digest(registration_path),'config_sha256':digest(config_path),
            'data_manifest_sha256':digest(data_dir/'MANIFEST.json'),'device':str(device),
            'knn_device':'cpu','test_labels_accessed':False}
    normal=[]; folds=[]
    write(output/'RUN_STATUS.json',status)
    for dataset in config['datasets']:
        spec,paths=dataset_paths(data_dir,dataset)
        nt,nr=spec['metadata']['node_feature_dim'],spec['metadata']['edge_feature_dim']
        sizes={name:len(old.load_graph(paths[name])['node_type']) for name in ('train0','train1','train2','train3')}
        for fold in config['folds']:
            for encoder_seed in config['encoder_seeds']:
                emit('normal_fold_fit',dataset=dataset,fold=fold['name'],encoder_seed=encoder_seed)
                root=private/dataset/fold['name']/f'encoder_{encoder_seed}'
                manifest=train_and_cache(paths,fold['fit'],{'calibration':fold['calibration'],
                    'normal_validation':fold['validation']},nt,nr,config,encoder_seed,device,root)
                cp=cache_paths(root,manifest)
                calibration_cache={c:arrays(cp[fold['calibration']][c]) for c in config['conditions']}
                validation_cache={c:arrays(cp[fold['validation']][c]) for c in config['conditions']}
                bank_receipts=[]
                for bank_seed in config['bank_seeds']:
                    emit('normal_reference',dataset=dataset,fold=fold['name'],encoder_seed=encoder_seed,bank_seed=bank_seed)
                    row_map=select_fit_rows(sizes,fold['fit'],fold['calibration'],fold['validation'],config['bank_size'],bank_seed)
                    banks,metadata=build_view_banks({g:cp[g] for g in fold['fit']},row_map,bank_seed)
                    bank_root=root/f'bank_{bank_seed}';bank_root.mkdir()
                    state,detectors=build_reference_state(banks,metadata,config)
                    np.savez_compressed(bank_root/'REFERENCE_STATE.npz',**state)
                    np.savez_compressed(bank_root/'ROW_SELECTION.npz',**row_map)
                    scores,timings={},{}
                    for role,role_cache in [('calibration',calibration_cache),('normal_validation',validation_cache)]:
                        for condition,cache in role_cache.items():
                            found,timing=query_scores(detectors,cache,role,condition,config)
                            scores.update(found);timings.update(timing)
                    np.savez_compressed(bank_root/'NORMAL_SCORES.npz',**scores)
                    cal_rates={}
                    for strategy,settings in config['strategies'].items():
                        for arm in config['representations']:
                            cal=calibration_scores(scores,calibration_cache,settings['reference'],arm,settings['calibration'])
                            cal_margin,_=empirical_tail_margin(cal,cal,config['calibration_fpr'])
                            cal_rates[strategy+'/'+arm]=float(np.mean(cal_margin>=0))
                            for condition,cache in validation_cache.items():
                                query=expanded(scores,cache,settings['reference'],arm,'normal_validation',condition)
                                margin,_=empirical_tail_margin(cal,query,config['calibration_fpr'])
                                normal.append({**identity(dataset,fold['name'],encoder_seed,bank_seed,strategy,arm,condition,config),
                                    'metrics':normal_metrics(margin,cache['node_type'])})
                    serial_metadata={k:v for k,v in metadata.items() if not isinstance(v,np.ndarray)}
                    receipt={'bank_seed':bank_seed,'selection':serial_metadata,'calibration_achieved_fpr':cal_rates,
                             'scoring':timings,'artifacts':inventory(bank_root),'target_labels_used':False}
                    write(bank_root/'FIT_RECEIPT.json',receipt)
                    bank_receipts.append({'bank_seed':bank_seed,'receipt_sha256':digest(bank_root/'FIT_RECEIPT.json')})
                    del state,detectors,banks,scores
                    write(output/'NORMAL_RESULTS.partial.json',{**status,'records':normal,'completed_encoder_folds':len(folds)})
                folds.append({'dataset':dataset,'fold':fold,'encoder_seed':encoder_seed,
                    'directory':root.relative_to(private).as_posix(),'manifest_sha256':digest(root/'MANIFEST.json'),
                    'fit_freeze_sha256':manifest['fit_freeze_sha256'],'banks':bank_receipts})
                del calibration_cache,validation_cache
    verify_duplicates(normal)
    expected=len(config['datasets'])*len(config['folds'])*len(config['encoder_seeds'])*len(config['bank_seeds'])*len(config['strategies'])*len(config['representations'])*len(config['conditions'])
    if len(normal)!=expected: raise ValueError('Normal experiment inventory incomplete')
    normal_report={**status,'status':'NORMAL_PHASE_COMPLETE','records':normal,
                   'unique_records':len(unique_records(normal)),'folds':folds,
                   'elapsed_seconds':time.perf_counter()-started}
    write(output/'NORMAL_RESULTS.json',normal_report)
    freeze={'status':'ALL_NORMAL_FITTING_AND_CALIBRATION_FROZEN_BEFORE_TEST_LABEL_ACCESS',
            'created_utc':datetime.now(timezone.utc).isoformat(),'previous_test_exposure_acknowledged':True,
            'normal_results_sha256':digest(output/'NORMAL_RESULTS.json'),'private_files':inventory(private),
            'folds':folds,'test_labels_accessed_this_run':False}
    write(output/'NORMAL_FREEZE.json',freeze)
    freeze_sha=digest(output/'NORMAL_FREEZE.json')
    normal_seconds=time.perf_counter()-started
    emit('normal_phase_complete',records=len(normal),unique_records=len(unique_records(normal)),elapsed_seconds=normal_seconds)
    status.update(status='ATTACK_REPLAY_RUNNING',test_labels_accessed=True,normal_freeze_sha256=freeze_sha)
    write(output/'RUN_STATUS.json',status)
    attack=[]
    for dataset in config['datasets']:
        spec,paths=dataset_paths(data_dir,dataset)
        with np.load(paths[config['evaluation_graph']],allow_pickle=False) as saved:
            y=saved['y'].astype(np.int8)
        if set(np.unique(y))!={0,1}: raise ValueError('Attack replay requires both benchmark labels')
        for fold in config['folds']:
            for encoder_seed in config['encoder_seeds']:
                emit('attack_fold_replay',dataset=dataset,fold=fold['name'],encoder_seed=encoder_seed)
                root=private/dataset/fold['name']/f'encoder_{encoder_seed}'
                entry=next(f for f in folds if f['dataset']==dataset and f['fold']['name']==fold['name'] and f['encoder_seed']==encoder_seed)
                if digest(root/'MANIFEST.json')!=entry['manifest_sha256']: raise ValueError('Fold manifest changed')
                manifest=read(root/'MANIFEST.json');cp=cache_paths(root,manifest)
                models,mean,scale,_=load_fold(root,device,expected_freeze_sha256=entry['fit_freeze_sha256'])
                test_caches={};test_entries={}
                for condition in config['conditions']:
                    target=root/'attack'/condition
                    receipt=cache_graph(paths[config['evaluation_graph']],models,mean,scale,
                        spec['metadata']['node_feature_dim'],spec['metadata']['edge_feature_dim'],device,target,
                        batch_size=config['embedding_batch_size'],condition=condition,graph_name=config['evaluation_graph'],
                        mask_seed=config['mask_seeds'][config['evaluation_graph']],expected_source_sha256=digest(paths[config['evaluation_graph']]))
                    test_caches[condition]=arrays(target/receipt['cache_npz']);test_entries[condition]=receipt
                write(root/'ATTACK_CACHES.json',test_entries)
                calibration_cache={c:arrays(cp[fold['calibration']][c]) for c in config['conditions']}
                for bank_seed in config['bank_seeds']:
                    bank_root=root/f'bank_{bank_seed}'
                    for filename in ('REFERENCE_STATE.npz','NORMAL_SCORES.npz'):
                        relative=(bank_root/filename).relative_to(private).as_posix()
                        if digest(bank_root/filename)!=freeze['private_files'][relative]: raise ValueError('Fitted score state changed')
                    detectors=restore_detectors(arrays(bank_root/'REFERENCE_STATE.npz'),config)
                    normal_scores=arrays(bank_root/'NORMAL_SCORES.npz')
                    scores,timings={},{}
                    for condition,cache in test_caches.items():
                        found,timing=query_scores(detectors,cache,'attack',condition,config)
                        scores.update(found);timings.update(timing)
                    np.savez_compressed(bank_root/'ATTACK_SCORES.npz',**scores)
                    write(bank_root/'ATTACK_TIMING.json',timings)
                    for strategy,settings in config['strategies'].items():
                        for arm in config['representations']:
                            cal=calibration_scores(normal_scores,calibration_cache,settings['reference'],arm,settings['calibration'])
                            for condition,cache in test_caches.items():
                                query=expanded(scores,cache,settings['reference'],arm,'attack',condition)
                                margin,_=empirical_tail_margin(cal,query,config['calibration_fpr'])
                                attack.append({**identity(dataset,fold['name'],encoder_seed,bank_seed,strategy,arm,condition,config),
                                               'metrics':old.binary_metrics(y,query,margin>=0)})
                    del detectors,scores,normal_scores
                for model in models.values():model.cpu()
                del models,test_caches,calibration_cache
                write(output/'ATTACK_RESULTS.partial.json',{**status,'records':attack})
    if len(attack)!=expected or digest(output/'NORMAL_FREEZE.json')!=freeze_sha:
        raise ValueError('Incomplete attack inventory or changed normal freeze')
    verify_duplicates(attack)
    for rel,sha in freeze['private_files'].items():
        if digest(private/rel)!=sha:raise ValueError('A normal-phase artifact changed during attack replay')
    result={**status,'status':'COMPLETE_FIXED_FAMILY_DEVELOPMENT','elapsed_seconds':time.perf_counter()-started,
            'normal_phase_seconds':normal_seconds,'normal_records':normal,'attack_records':attack,
            'logged_records_per_phase':expected,'unique_records_per_phase':len(unique_records(attack)),
            'decision':decide(normal,attack,config,baseline),'private_artifacts':inventory(private),
            'previous_results_modified':False,'normal_freeze_sha256':freeze_sha}
    write(output/'RESULTS.json',result)
    write(output/'RUN_STATUS.json',{**status,'status':result['status'],'elapsed_seconds':result['elapsed_seconds']})
    emit('complete',decision=result['decision']['status'],elapsed_seconds=result['elapsed_seconds'])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ('config','data-dir','output','registration'):parser.add_argument('--'+field,required=True)
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=parser.parse_args()
    run(args.config,args.data_dir,args.output,args.registration,args.device)
