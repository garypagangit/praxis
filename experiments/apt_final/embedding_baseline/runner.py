"""Frozen-encoder scoring comparison; all fitting uses training/benign calibration."""
from __future__ import annotations
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
import torch
import sklearn
from ..native_graph import pilot as old
from .engine import load_frozen_checkpoint, extract_embeddings, qualify_device
from .scoring import ExactKNN, sample_bank_indices
from .provenance import verify_registration, read, digest

NEW_ARMS = ('local_knn', 'mlp_knn', 'gin_knn')
PRIOR_ARMS = ('mlp', 'gin', 'isolation_forest', 'type_rarity', 'quality_gate', 'confidence_selector')


def emit(stage, **fields):
    print(json.dumps({'stage': stage, **fields}), flush=True)


def features_from(path, node_types, relations, mean, scale, keep=None):
    graph = old.load_graph(path)
    raw, degree, src, dst = old.observed_features(graph, node_types, relations, keep)
    return old.scale_features(raw, mean, scale), degree, src, dst


def representations(models, features, src, dst, device, config):
    values, timings = {'local_knn': features}, {}
    for arm, model in models.items():
        values[arm + '_knn'], timings[arm] = extract_embeddings(
            model, features, src, dst, device, config['embedding_batch_size'])
    return values, timings


def score_representations(values, detectors, config, query_path):
    scores, timings, evidence = {}, {}, {}
    for arm in NEW_ARMS:
        if config['deduplicate_queries']:
            unique, inverse = np.unique(values[arm], axis=0, return_inverse=True)
        else:
            unique, inverse = values[arm], np.arange(len(values[arm]))
        values_unique, timing = detectors[arm].score(unique, config['query_chunk_size'], False)
        scores[arm] = values_unique[inverse]
        timings[arm] = {**timing, 'original_query_rows': len(values[arm]),
                        'unique_queries_saved': len(unique),
                        'query_deduplication_applied_before_search': config['deduplicate_queries']}
        evidence[arm + '_unique'] = unique
        evidence[arm + '_inverse'] = inverse
    np.savez_compressed(query_path, **evidence)
    return scores, timings


def fit_all(config, paths, prior, private, spec, device):
    with np.load(prior / 'private/PREPROCESSING.npz', allow_pickle=False) as prep:
        mean, scale = prep['mean'].copy(), prep['scale'].copy()
    if not np.all(np.isfinite(mean)) or not np.all(np.isfinite(scale)) or np.any(scale <= 0):
        raise ValueError('Invalid frozen preprocessing')
    nt, nr = int(spec['metadata']['node_feature_dim']), int(spec['metadata']['edge_feature_dim'])
    prior_result = read(prior / 'RESULTS.json')
    prior_freeze = read(prior / 'FIT_FREEZE.json')
    if prior_result['fit_freeze_sha256'] != digest(prior / 'FIT_FREEZE.json'):
        raise ValueError('Predecessor freeze hash mismatch')
    if prior_freeze['train_graphs'] != config['train_graphs'] or prior_freeze['calibration_graph'] != config['calibration_graph']:
        raise ValueError('Predecessor split differs')
    sizes = {name: len(old.load_graph(paths[name])['node_type']) for name in config['train_graphs']}
    fitted, fit_records = [], []
    for seed in config['seeds']:
        emit('bank_and_calibration', dataset=spec['dataset'], seed=seed)
        models, checkpoint_receipts = {}, {}
        for arm in ('mlp', 'gin'):
            name = f'{arm}_{seed}.pt'
            models[arm], checkpoint_receipts[arm] = load_frozen_checkpoint(
                prior / 'private' / name, prior_freeze['artifacts'][name],
                expected_arm=arm, expected_seed=seed, expected_input_dim=len(mean))
        selected = sample_bank_indices(sizes, config['bank_size'], seed + config['bank_seed_offset'])
        np.savez_compressed(private / f'bank_indices_{seed}.npz', **selected)
        bank = {arm: [] for arm in NEW_ARMS}
        for name in sorted(selected):
            features, _, src, dst = features_from(paths[name], nt, nr, mean, scale)
            values, _ = representations(models, features, src, dst, device, config)
            for arm in NEW_ARMS:
                bank[arm].append(values[arm][selected[name]])
            del features, values, src, dst
        detectors = {arm: ExactKNN(np.concatenate(bank[arm]), config['neighbors'], config['scale_floor'])
                     for arm in NEW_ARMS}
        bank_evidence = {arm + '_' + field: array for arm, detector in detectors.items()
                         for field, array in detector.artifact_arrays().items()}
        np.savez_compressed(private / f'bank_{seed}.npz', **bank_evidence)
        features, degree, src, dst = features_from(paths[config['calibration_graph']], nt, nr, mean, scale)
        values, extraction = representations(models, features, src, dst, device, config)
        calibration, scoring = score_representations(values, detectors, config,
                                                      private / f'calibration_queries_{seed}.npz')
        np.savez_compressed(private / f'calibration_{seed}.npz', **calibration)
        margins = {arm: old.margin_from_calibration(calibration[arm], calibration[arm], config['calibration_fpr'])[0]
                   for arm in NEW_ARMS}
        quality, _ = old.quality_selector(degree, margins['gin_knn'], margins['mlp_knn'], config['gate_min_degree'])
        confidence, _ = old.confidence_selector(margins['gin_knn'], margins['mlp_knn'])
        margins.update(quality_gate=quality, confidence_selector=confidence)
        fit_records.append({'seed': seed, 'checkpoints': checkpoint_receipts,
                            'bank_graph_rows': {name: len(idx) for name, idx in selected.items()},
                            'bank': {arm: d.fit_metadata for arm, d in detectors.items()},
                            'calibration_fpr': {arm: float(np.mean(m >= 0)) for arm, m in margins.items()},
                            'calibration_extraction': extraction, 'calibration_scoring': scoring})
        fitted.append((seed, models, detectors, calibration))
        del values, features, degree, src, dst, bank, bank_evidence
    return fitted, fit_records, mean, scale


def summarize(records, config):
    summary = []
    for rate in config['drop_rates']:
        matches = [r for r in records if r['drop_rate'] == rate]
        for arm in matches[0]['metrics']:
            fields = {}
            for name in ('precision', 'recall', 'f1', 'false_positive_rate', 'average_precision'):
                values = [r['metrics'][arm][name] for r in matches]
                fields[name] = {'mean': float(np.mean(values)), 'min': float(min(values)), 'max': float(max(values))}
            summary.append({'drop_rate': rate, 'arm': arm, 'descriptive_runs': len(matches), **fields})
    return summary


def development_decision(records, config):
    clean = [r for r in records if r['drop_rate'] == 0]
    best_prior_f1 = max(float(np.mean([r['metrics']['prior_' + arm]['f1'] for r in clean]))
                        for arm in ('mlp', 'gin', 'isolation_forest', 'type_rarity'))
    arms = {}
    for arm in NEW_ARMS:
        ready = all(r['metrics'][arm]['recall'] >= config['readiness_min_recall'] and
                    r['metrics'][arm]['false_positive_rate'] <= config['readiness_max_fpr'] for r in clean)
        mean_f1 = float(np.mean([r['metrics'][arm]['f1'] for r in clean]))
        arms[arm] = {'detector_ready_all_seeds': ready, 'mean_clean_f1': mean_f1,
                     'f1_change_vs_best_prior_fixed_mean': mean_f1 - best_prior_f1,
                     'positive_scoring_screen': ready and mean_f1 - best_prior_f1 >= config['minimum_mean_f1_improvement']}
    return {'scope': 'PROSPECTIVE_DEVELOPMENT_SCREEN_ONLY', 'best_prior_fixed_mean_f1': best_prior_f1,
            'arms': arms, 'confirmation_or_novelty_established': False}


def run(config_path, data_dir, prior_dir, dataset, output, device_name, registration_path):
    registration = verify_registration(config_path, data_dir, registration_path, prior_dir)
    config = read(config_path)
    if dataset not in config['datasets']:
        raise ValueError('Dataset not registered')
    output, data_dir, prior = Path(output), Path(data_dir), Path(prior_dir) / dataset
    if output.exists():
        raise FileExistsError('Preserve prior evidence; output must be new')
    spec, paths = old.load_dataset_spec(data_dir, dataset, config)
    old.configure_reproducibility(config['cpu_threads'])
    device = old.select_device(device_name)
    qualification = qualify_device(device)
    output.mkdir(parents=True)
    private = output / 'private'
    private.mkdir()
    started = time.perf_counter()
    status = {'status': 'RUNNING', 'scope': 'POST_RESULT_DEVELOPMENT', 'dataset': dataset,
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'registration_sha256': digest(registration_path), 'source_commit': registration['git_commit'],
              'config_sha256': digest(config_path), 'data_manifest_sha256': digest(data_dir / 'MANIFEST.json'),
              'prior_results_sha256': digest(prior / 'RESULTS.json'), 'gpu_qualification': qualification,
              'device_actual': str(device), 'knn_device': 'cpu', 'encoder_weights_retrained': False,
              'test_outcomes_previously_inspected': True,
              'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                           'torch': torch.__version__, 'sklearn': sklearn.__version__}}
    old.write_json(output / 'RUN_STATUS.json', status)
    fitted, fit_records, mean, scale = fit_all(config, paths, prior, private, spec, device)
    freeze = {'status': 'BANKS_AND_CALIBRATION_FROZEN_BEFORE_THIS_RUN_EVALUATION_LABEL_ACCESS',
              'prior_test_label_exposure_acknowledged': True, 'fit_labels_used': False,
              'train_graphs': config['train_graphs'], 'calibration_graph': config['calibration_graph'],
              'seeds': config['seeds'], 'fit_records': fit_records,
              'artifacts': {p.name: digest(p) for p in private.iterdir() if p.is_file()}}
    old.write_json(output / 'FIT_FREEZE.json', freeze)
    with np.load(paths[config['evaluation_graph']], allow_pickle=False) as arrays:
        y = np.asarray(arrays['y'], dtype=np.int8)
    graph = old.load_graph(paths[config['evaluation_graph']])
    nt, nr = int(spec['metadata']['node_feature_dim']), int(spec['metadata']['edge_feature_dim'])
    previous = read(prior / 'RESULTS.json')
    prior_audit = read(Path(prior_dir) / 'INDEPENDENT_RESULT_AUDIT.json')
    audit_conditions = next(d['conditions'] for d in prior_audit['datasets'] if d['dataset'] == dataset)
    records = []
    for scenario, keep in old.scenario_masks(len(graph['src']), config['drop_rates'], config['mask_seeds']):
        features, degree, src, dst = features_from(paths[config['evaluation_graph']], nt, nr, mean, scale, keep)
        mask = np.ones(len(graph['src']), dtype=bool) if keep is None else keep
        mask_sha = hashlib.sha256(mask.tobytes()).hexdigest()
        for seed, models, detectors, calibration in fitted:
            audited = [r for r in audit_conditions if r['seed'] == seed and r['scenario'] == scenario['name']]
            if len(audited) != 1 or audited[0]['input_mask_sha256'] != mask_sha:
                raise ValueError('Removal mask differs from the audited predecessor condition')
            emit('evaluate', dataset=dataset, seed=seed, **scenario)
            values, extraction = representations(models, features, src, dst, device, config)
            scores, scoring = score_representations(values, detectors, config,
                private / f"queries_{seed}_{scenario['name']}.npz")
            del values
            margins = {arm: old.margin_from_calibration(calibration[arm], scores[arm], config['calibration_fpr'])[0]
                       for arm in NEW_ARMS}
            quality, _ = old.quality_selector(degree, margins['gin_knn'], margins['mlp_knn'], config['gate_min_degree'])
            confidence, _ = old.confidence_selector(margins['gin_knn'], margins['mlp_knn'])
            margins.update(quality_gate=quality, confidence_selector=confidence)
            scores.update(quality_gate=quality, confidence_selector=confidence)
            pred_name = f"predictions_{seed}_{scenario['name']}.npz"
            with np.load(prior / 'private' / pred_name, allow_pickle=False) as saved:
                if not np.array_equal(y, saved['y']) or not np.array_equal(degree, saved['degree']):
                    raise ValueError('Predecessor predictions do not describe same entities and graph condition')
                for arm in PRIOR_ARMS:
                    margins['prior_' + arm] = saved['margin_' + arm].copy()
                    score_key = 'score_' + arm if 'score_' + arm in saved.files else 'margin_' + arm
                    scores['prior_' + arm] = saved[score_key].copy()
            metrics = {arm: old.binary_metrics(y, scores[arm], margin >= 0) for arm, margin in margins.items()}
            old_matches = [r for r in previous['records'] if r['seed'] == seed and r['name'] == scenario['name']]
            if len(old_matches) != 1 or any(metrics['prior_' + a] != old_matches[0]['metrics'][a] for a in PRIOR_ARMS):
                raise ValueError('Predecessor aggregate metrics failed exact replay')
            references = ['prior_' + a for a in ('mlp', 'gin', 'isolation_forest', 'type_rarity')] + list(NEW_ARMS)
            changes = {arm: {ref: old.error_changes(y, margins[arm] >= 0, margins[ref] >= 0)
                             for ref in references if ref != arm}
                       for arm in (*NEW_ARMS, 'quality_gate', 'confidence_selector')}
            mlp, gin = margins['mlp_knn'] >= 0, margins['gin_knn'] >= 0
            record = {'seed': seed, **scenario, 'observed_edges': len(src),
                      'mask_sha256': mask_sha,
                      'metrics': metrics, 'error_changes': changes, 'extraction': extraction, 'scoring': scoring,
                      'complementarity': {'mlp_only_malicious_entities': int(np.sum((y == 1) & mlp & ~gin)),
                                          'gin_only_malicious_entities': int(np.sum((y == 1) & gin & ~mlp)),
                                          'union_malicious_entities': int(np.sum((y == 1) & (mlp | gin)))}}
            records.append(record)
            np.savez_compressed(private / pred_name, y=y, degree=degree,
                **{'score_' + arm: value for arm, value in scores.items()},
                **{'margin_' + arm: value for arm, value in margins.items()})
            old.write_json(output / 'RESULTS.partial.json', {**status, 'status': 'PARTIAL_DEVELOPMENT_ONLY',
                'records': records, 'fit_freeze_sha256': digest(output / 'FIT_FREEZE.json')})
    result = {**status, 'status': 'COMPLETE_DEVELOPMENT_ONLY', 'elapsed_seconds': time.perf_counter() - started,
              'fit_records': fit_records, 'fit_freeze_sha256': digest(output / 'FIT_FREEZE.json'),
              'records': records, 'descriptive_summary': summarize(records, config),
              'development_decision': development_decision(records, config),
              'private_artifact_sha256': {p.name: digest(p) for p in private.iterdir() if p.is_file()}}
    old.write_json(output / 'RESULTS.json', result)
    old.write_json(output / 'RUN_STATUS.json', {**status, 'status': result['status'], 'elapsed_seconds': result['elapsed_seconds']})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'data-dir', 'prior-dir', 'dataset', 'output', 'registration'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    args = parser.parse_args()
    result = run(args.config, args.data_dir, args.prior_dir, args.dataset, args.output, args.device, args.registration)
    emit('complete', dataset=args.dataset, elapsed_seconds=result['elapsed_seconds'])
