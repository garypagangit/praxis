"""Frozen structured-loss controls, with private predictions and audit receipts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time
import warnings

import joblib
import numpy as np
from scipy import sparse
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from ..models import calibration_threshold, resolve_threshold
from ..robustness.replay import load_events
from ..robustness.replay_fast import FastReplay
from ..robustness.run import sha256, save_json, is_target, summarize


def route_states(X, dimensions):
    """Route solely from visible current-event record types in feature metadata."""
    values = X[:, [2 * dimensions + 2, 2 * dimensions + 3]].toarray()
    return (values[:, 0] > 0).astype(np.int8) + 2 * (values[:, 1] > 0).astype(np.int8)


def _scores(model, X):
    return model.predict_proba(X)[:, list(model.classes_).index(1)].copy()


def predict_bundle(bundle, X, observed, dimensions):
    observed = np.asarray(observed, dtype=bool)
    if bundle['kind'] == 'single':
        scores = _scores(bundle['model'], X)
    elif bundle['kind'] == 'observed_router':
        scores = _scores(bundle['base'], X)
        states = route_states(X, dimensions)
        for state, expert in bundle['experts'].items():
            mask = (states == int(state)) & observed
            if mask.any():
                scores[mask] = _scores(expert, X[mask])
    else:
        raise ValueError('Unknown bundle kind')
    scores[~observed] = 0
    return scores


def fit_lr(X, y, protocol, weights=None):
    model = LogisticRegression(**{k: v for k, v in protocol['classifier'].items() if k != 'type'})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model.fit(X, y, sample_weight=weights)
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise RuntimeError('Nonconverged fit; no result permitted')
    return model


def fit_router(X, y, observed, underlying_ids, base_model, protocol, view_count, dimensions):
    states = route_states(X, dimensions)
    observed = np.asarray(observed, dtype=bool)
    underlying_ids = np.asarray(underlying_ids)
    experts, support = {}, {}
    for state in range(4):
        mask = (states == state) & observed
        positive = len(np.unique(underlying_ids[mask & (y == 1)]))
        negative = len(np.unique(underlying_ids[mask & (y == 0)]))
        enough = (positive >= protocol['router']['minimum_unique_positive_targets']
                  and negative >= protocol['router']['minimum_unique_negative_targets'])
        support[str(state)] = {'unique_positive': positive, 'unique_negative': negative,
                               'observed_augmented_rows': int(mask.sum()),
                               'uses_expert': enough,
                               'fallback_reason': None if enough else 'Insufficient unique observed fit targets'}
        if enough:
            experts[state] = fit_lr(X[mask], y[mask], protocol, np.full(int(mask.sum()), 1 / view_count))
    return {'kind': 'observed_router', 'base': base_model, 'experts': experts, 'route_support': support}


def primary_screen(record, protocol):
    if record['status'] != 'COMPLETE':
        return {'status': 'UNSUPPORTED'}
    spec = protocol['primary_comparison']
    def mean(arm, condition, metric):
        return float(np.mean([r[spec['point']][metric] for r in record['results']
                              if r['arm'] == arm and r['condition'] == condition]))
    def delta(condition, metric):
        return mean(spec['candidate'], condition, metric) - mean(spec['baseline'], condition, metric)
    values = {
        'command_records_absent_f1_delta_min': delta('command_records_absent', 'f1'),
        'command_records_absent_recall_delta_min': delta('command_records_absent', 'recall'),
        'command_records_absent_flag_rate_delta_max': delta('command_records_absent', 'negative_label_flag_rate'),
        'clean_f1_delta_min': delta('clean', 'f1'),
        'random_50_mean_f1_delta_min': delta('random_50', 'f1'),
    }
    checks = {k: {'delta': v, 'limit': spec['per_target_gates'][k],
                  'passed': bool(v <= spec['per_target_gates'][k] + 1e-12 if k.endswith('_max')
                                 else v >= spec['per_target_gates'][k] - 1e-12)} for k, v in values.items()}
    return {'status': 'PASS' if all(c['passed'] for c in checks.values()) else 'FAIL',
            'checks': checks, 'interpretation': spec['interpretation']}


def report(result):
    lines = [f"# {result['dataset']}: structured-record-loss controls", '',
             'Existing-method feasibility experiment. Labels identify a source technique versus other annotated techniques, not verified benign activity.', '',
             f"Context events: {result['events']:,}; eligible targets: {result['eligible_targets']:,}.", '',
             'Clean-calibration thresholds are frozen across test conditions. Random conditions average three perturbation seeds; other conditions have one deterministic view.', '']
    for target, record in result['targets'].items():
        lines += [f'## {target}', '', f"Status: {record['status']}. Primary screening: **{record['primary_screen']['status']}**.", '',
                  f"Support: `{json.dumps(record['support'], sort_keys=True)}`", '']
        if record['status'] != 'COMPLETE':
            continue
        lines += ['| Condition | Arm | Calibrated F1 | Recall | Other-label flag rate | F1 at0.5 |',
                  '|---|---|---:|---:|---:|---:|']
        groups = {}
        for row in record['results']:
            groups.setdefault((row['condition'], row['arm']), []).append(row)
        for (condition, arm), rows in groups.items():
            vals = [np.mean([r[point][key] for r in rows]) for point, key in
                    [('calibrated', 'f1'), ('calibrated', 'recall'), ('calibrated', 'negative_label_flag_rate'), ('fixed_0_5', 'f1')]]
            lines.append(f'| {condition} | {arm} | ' + ' | '.join(f'{v:.4f}' for v in vals) + ' |')
        lines += ['', 'Primary gates: `' + json.dumps(record['primary_screen']['checks'], sort_keys=True) + '`', '']
    lines += ['## Interpretation limits', '',
              '- AIT and Casino are already exposed development sources. No significance or population guarantee follows from passing descriptive gates.',
              '- CAM-LDS, if qualified, uses a family-held-out interval-state proxy. It is not directly comparable to Casino annotation-onset targets or AIT rule labels.',
              '- Router specialists use more parameters than one logistic regression; fit support counts unique underlying observed targets.',
              '- Record-type removal is a synthetic log stress test, not a measured sensor outage. Waiting out injected delay restores clean evidence by construction.',
              '- Invisible targets remain in denominators and get no alarm. The offline target roster is not a deployable detector trigger.',
              '- Source labels, dependent events, small positive counts, recipe overlap and dataset shift limit generalization.',
              '- No novel algorithm, complete APT detection, or improved real-world benign false-alarm rate is established.']
    return '\n'.join(lines) + '\n'


def run(events_path, manifest_path, dataset, output, protocol_path, feature_cache=None):
    start = time.perf_counter()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads(Path(protocol_path).read_text(encoding='utf-8'))
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    input_hash = sha256(events_path)
    if manifest.get('events_sha256') != input_hash:
        raise ValueError('Source manifest does not bind event corpus')
    if feature_cache:
        from .feature_cache import CachedReplay
        feature_cache = Path(feature_cache)
        if feature_cache.is_file():
            feature_cache = feature_cache.parent
        replay = CachedReplay(feature_cache, protocol, input_hash)
        if replay.manifest['source_manifest_sha256'] != sha256(manifest_path):
            raise ValueError('Cache source manifest mismatch')
        events, source_event_count = replay.events, replay.source_event_count
    else:
        events = load_events(events_path)
        replay = FastReplay(events, protocol['history']['seconds'], protocol['history']['max_events'])
        source_event_count = len(events)
    eligible = np.asarray([i for i, e in enumerate(events) if e.get('target_eligible', True)], dtype=int)
    indices = {role: np.asarray([i for i in eligible if events[i]['split'] == role], dtype=int)
               for role in ('fit', 'development', 'calibration', 'test')}
    conditions = {c['name']: c for c in protocol['conditions']}
    seed = protocol['classifier']['random_state']
    aug_seed = protocol['dropout_training']['seed']
    dimensions = protocol['text_features']['hash_dimensions_per_block']
    repo = Path(__file__).resolve().parents[3]
    code_files = [Path(__file__), Path(__file__).with_name('feature_cache.py'),
                  *[repo / 'experiments/apt_benchmark/robustness' / name for name in
                    ('run.py', 'replay.py', 'replay_fast.py', 'feature_cache.py')],
                  repo / 'experiments/apt_benchmark/models.py']
    result = {'status': 'RUNNING', 'dataset': dataset, 'events': source_event_count,
              'eligible_targets': len(eligible), 'input_sha256': input_hash,
              'manifest_sha256': sha256(manifest_path), 'protocol_sha256': sha256(protocol_path),
              'python': platform.python_version(), 'sklearn': sklearn.__version__, 'targets': {},
              'no_population_guarantee': True, 'private_manifest_status': manifest.get('status', 'See source manifest')}
    receipt = {'frozen_before_fit': True, 'created_utc': datetime.now(timezone.utc).isoformat(),
               'input_sha256': input_hash, 'manifest_sha256': result['manifest_sha256'],
               'protocol': protocol, 'protocol_sha256': result['protocol_sha256'],
               'protocol_file': 'PROTOCOL.json',
               'code_sha256': {p.relative_to(repo).as_posix(): sha256(p) for p in code_files}}
    try:
        receipt['git_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        receipt['git_commit'] = None
    if feature_cache:
        result['feature_cache_manifest_sha256'] = sha256(Path(feature_cache) / 'MANIFEST.json')
        receipt['feature_cache_manifest_sha256'] = result['feature_cache_manifest_sha256']
    shutil.copyfile(protocol_path, output / 'PROTOCOL.json')
    save_json(output / 'PRE_FIT_RECEIPT.json', receipt)
    save_json(output / 'RESULTS.partial.json', result)
    # Cache only fit and calibration views; no target values enter features.
    matrices = {}
    def matrix(role, family, view):
        key = role, family, view
        if key not in matrices:
            matrices[key] = replay.matrix(indices[role], conditions[view], seed if view == 'clean' else aug_seed, family, dimensions)
        return matrices[key]
    fitted = {}
    for target in protocol['datasets'][dataset]['targets']:
        y_all = np.asarray([is_target(e['labels'], target) for e in events], dtype=np.int8)
        support = {role: {'n': len(idx), 'positive': int(y_all[idx].sum()),
                          'negative': int(len(idx) - y_all[idx].sum())} for role, idx in indices.items()}
        record = {'status': 'RUNNING', 'support': support, 'models': {}, 'results': []}
        result['targets'][target] = record
        if any(not support[r]['positive'] or not support[r]['negative'] for r in ('fit', 'calibration', 'test')):
            record['status'] = 'UNSUPPORTED_BOTH_CLASSES_REQUIRED'
            continue
        for arm in protocol['models']:
            arm_spec = protocol['arms'][arm]
            family, views = arm_spec['family'], arm_spec['views']
            fit_start = time.perf_counter()
            fit_views = [matrix('fit', family, view) for view in views]
            X = sparse.vstack([v[0] for v in fit_views], format='csr') if len(views) > 1 else fit_views[0][0]
            y = np.tile(y_all[indices['fit']], len(views))
            observed = np.concatenate([v[1] for v in fit_views])
            if arm == 'observed_router':
                bundle = fit_router(X, y, observed, np.tile(indices['fit'], len(views)),
                                    fitted[(target, 'mixed_dropout')][0]['model'], protocol, len(views), dimensions)
                states = route_states(X, dimensions)
                ids = np.tile(indices['fit'], len(views))
                for state in range(4):
                    selected = (states == state) & observed
                    bundle['route_support'][str(state)]['positive_runs'] = len({events[i]['run_id'] for i in ids[selected & (y == 1)]})
                    bundle['route_support'][str(state)]['negative_runs'] = len({events[i]['run_id'] for i in ids[selected & (y == 0)]})
                models = [bundle['base'], *bundle['experts'].values()]
            else:
                weights = np.full(len(y), 1 / len(views)) if len(views) > 1 else None
                bundle = {'kind': 'single', 'model': fit_lr(X, y, protocol, weights)}
                models = [bundle['model']]
            fit_seconds = time.perf_counter() - fit_start
            Xcal, observed_cal = matrix('calibration', family, 'clean')
            scores_cal = predict_bundle(bundle, Xcal, observed_cal, dimensions)
            ycal = y_all[indices['calibration']]
            threshold = calibration_threshold(ycal, scores_cal, protocol['calibration']['negative_label_fpr_budget'])
            model_path = output / f'{target}_{arm}.joblib'
            joblib.dump(bundle, model_path)
            record['models'][arm] = {'threshold': threshold, 'fit_seconds': fit_seconds,
                                      'model_sha256': sha256(model_path), 'training_rows': len(y),
                                      'parameter_count': sum(m.coef_.size + m.intercept_.size for m in models),
                                      'route_support': bundle.get('route_support')}
            cal_states = route_states(Xcal, dimensions)
            record['models'][arm]['calibration_observed_route_counts'] = {str(s): int(((cal_states == s) & observed_cal).sum()) for s in range(4)}
            np.savez_compressed(output / f'PRIVATE_CAL_{target}_{arm}.npz', y=ycal, score=scores_cal, observed=observed_cal)
            fitted[(target, arm)] = bundle, resolve_threshold(threshold)
            print(f'fit {dataset} {target} {arm}: {len(y)} rows', flush=True)
        record['status'] = 'FITTED'
    del matrices
    test_idx = indices['test']
    test_runs = np.asarray([events[i]['run_id'] for i in test_idx])
    np.savez_compressed(output / 'PRIVATE_TARGET_ROSTER.npz', event_ids=np.asarray([events[i]['event_id'] for i in test_idx]), run_ids=test_runs)
    for condition in protocol['conditions'] if fitted else []:
        for corruption_seed in protocol['seeds'] if condition['kind'] == 'random' else [protocol['seeds'][0]]:
            for family in ('semantic_event', 'entity_context'):
                Xtest, observed = replay.matrix(test_idx, condition, corruption_seed, family, dimensions)
                states = route_states(Xtest, dimensions)
                for target, record in result['targets'].items():
                    if record['status'] != 'FITTED':
                        continue
                    labels = np.asarray([is_target(events[i]['labels'], target) for i in test_idx], dtype=np.int8)
                    for arm in [a for a in protocol['models'] if protocol['arms'][a]['family'] == family]:
                        bundle, threshold = fitted[(target, arm)]
                        scores = predict_bundle(bundle, Xtest, observed, dimensions)
                        row = {'condition': condition['name'], 'seed': corruption_seed, 'arm': arm,
                               'deadline_seconds': condition.get('deadline', 0),
                               'fixed_0_5': summarize(labels, scores, observed, .5),
                               'calibrated': summarize(labels, scores, observed, threshold), 'by_run': {},
                               'observed_route_counts': {str(s): int(((states == s) & observed).sum()) for s in range(4)}}
                        for run_id in sorted(set(test_runs)):
                            mask = test_runs == run_id
                            row['by_run'][run_id] = {'fixed_0_5': summarize(labels[mask], scores[mask], observed[mask], .5),
                                                    'calibrated': summarize(labels[mask], scores[mask], observed[mask], threshold)}
                        record['results'].append(row)
                        np.savez_compressed(output / f"PRIVATE_{target}_{arm}_{condition['name']}_{corruption_seed}.npz", y=labels, score=scores, observed=observed)
            print(f"scored {dataset} {condition['name']} seed {corruption_seed}", flush=True)
        save_json(output / 'RESULTS.partial.json', result)
    for record in result['targets'].values():
        if record['status'] == 'FITTED':
            record['status'] = 'COMPLETE'
        record['primary_screen'] = primary_screen(record, protocol)
    if (sha256(events_path) != input_hash or sha256(manifest_path) != result['manifest_sha256']
            or sha256(protocol_path) != result['protocol_sha256']
            or any(sha256(repo / p) != digest for p, digest in receipt['code_sha256'].items())
            or (feature_cache and sha256(feature_cache / 'MANIFEST.json') != result['feature_cache_manifest_sha256'])):
        raise ValueError('Frozen inputs or implementation changed during run; no completed result permitted')
    result['status'] = 'COMPLETE'
    result['runtime_seconds'] = time.perf_counter() - start
    save_json(output / 'RESULTS.json', result)
    (output / 'REPORT.md').write_text(report(result), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'dataset': dataset, 'runtime_seconds': result['runtime_seconds']}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('events', 'manifest', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--dataset', choices=('ait', 'casino', 'camlds'), required=True)
    parser.add_argument('--protocol', type=Path, default=Path(__file__).with_name('protocol.json'))
    parser.add_argument('--feature-cache', type=Path)
    args = parser.parse_args()
    run(args.events, args.manifest, args.dataset, args.output, args.protocol, args.feature_cache)
