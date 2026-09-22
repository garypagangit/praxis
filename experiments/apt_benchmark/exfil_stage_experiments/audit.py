"""Independent saved-output audit. Never imports the runner or loads models."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def compare(actual, expected, location='root'):
    """Exact structure/counts, small numerical tolerance for independent metrics."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), location + ': keys')
        for key in expected:
            compare(actual[key], expected[key], location + '.' + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), location + ': list')
        for i, value in enumerate(expected):
            compare(actual[i], value, f'{location}[{i}]')
    elif isinstance(expected, (float, np.floating)):
        require(isinstance(actual, (int, float)) and math.isfinite(actual)
                and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-11), location + ': numerical value')
    else:
        require(actual == expected, location + ': value')


def verify_hashes(folder, entries, expected_names):
    require(set(entries) == set(expected_names), 'artifact roster differs')
    for name, checksum in entries.items():
        require(Path(name).name == name, 'unsafe artifact name')
        require(digest(Path(folder) / name) == checksum, 'artifact hash mismatch: ' + name)


def probability(values, rows, columns=None):
    values = np.asarray(values)
    shape = (rows,) if columns is None else (rows, columns)
    require(values.shape == shape, 'probability shape')
    require(np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all(), 'probability range')
    if columns is not None:
        require(np.allclose(values.sum(axis=1), 1, rtol=1e-6, atol=1e-6), 'probability row sums')


def best_f1_threshold(labels, scores):
    """Independent grouped-count frontier; integer cross-products resolve ties."""
    labels, scores = np.asarray(labels, dtype=bool), np.asarray(scores, dtype=float)
    unique, inverse = np.unique(scores, return_inverse=True)
    positives = np.bincount(inverse, weights=labels, minlength=len(unique)).astype(np.int64)
    totals = np.bincount(inverse, minlength=len(unique))
    tp, fp, total_positive = int(labels.sum()), int((~labels).sum()), int(labels.sum())
    best_t, best_num, best_den = -1., 2 * tp, 2 * tp + fp
    if not best_den:
        best_den = 1
    for threshold, hit, total in zip(unique, positives, totals):
        tp -= int(hit)
        fp -= int(total - hit)
        numerator, denominator = 2 * tp, 2 * tp + fp + total_positive - tp
        denominator = denominator or 1
        if numerator * best_den >= best_num * denominator:
            best_t, best_num, best_den = float(threshold), numerator, denominator
    return best_t


def tail_threshold(scores, budget):
    scores = np.asarray(scores, dtype=float)
    require(len(scores) > 0 and np.isfinite(scores).all(), 'invalid calibration scores')
    allowed = int(Decimal(str(budget)) * len(scores))
    require(0 <= allowed < len(scores), 'invalid tail budget')
    return float(np.sort(scores)[::-1][allowed])


def binary_counts(y, scores, threshold, classes):
    flags = scores > threshold
    counts = np.bincount(y[flags], minlength=6)
    supports = np.bincount(y, minlength=6)
    tp, fp = int(counts[0]), int(counts[1:].sum())
    fn, tn = int(supports[0]) - tp, int(supports[1:].sum()) - fp
    return {'threshold': threshold, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': tp / (tp + fp) if tp + fp else 0., 'recall': tp / (tp + fn),
            'f1': 2 * tp / (2 * tp + fp + fn), 'non_exfil_fpr': fp / (fp + tn),
            'normal_fp': int(counts[3]), 'normal_fpr': float(counts[3] / supports[3]),
            'alert_count': int(counts.sum()),
            'flag_counts_by_true_stage': dict(zip(classes, map(int, counts)))}


def exfil_metrics(ycal, ytest, cal, test, classes, budgets):
    threshold = best_f1_threshold(ycal == 0, cal)
    result = {'average_precision': float(average_precision_score(ytest == 0, test)),
              'roc_auc': float(roc_auc_score(ytest == 0, test)),
              'calibration_f1_threshold': binary_counts(ytest, test, threshold, classes)}
    for key, mask, field in [('normal_budget_thresholds', ycal == 3, 'calibration_normal_fpr'),
                             ('non_exfil_budget_thresholds', ycal != 0, 'calibration_non_exfil_fpr')]:
        result[key] = {}
        for budget in budgets:
            t = tail_threshold(cal[mask], budget)
            result[key][str(budget)] = {field: float(np.count_nonzero(cal[mask] > t) / mask.sum()),
                                       **binary_counts(ytest, test, t, classes)}
    return result


def stage_metrics(y, scores, classes):
    predicted = scores.argmax(axis=1)
    matrix = np.bincount(y * 6 + predicted, minlength=36).reshape(6, 6)
    supports, assigned = matrix.sum(axis=1), matrix.sum(axis=0)
    diagonal = np.diag(matrix)
    per_stage = {}
    for k, name in enumerate(classes):
        per_stage[name] = {'precision': float(diagonal[k] / assigned[k]) if assigned[k] else 0.,
                          'recall': float(diagonal[k] / supports[k]),
                          'f1': float(2 * diagonal[k] / (supports[k] + assigned[k])),
                          'support': int(supports[k]),
                          'average_precision': float(average_precision_score(y == k, scores[:, k])),
                          'roc_auc': float(roc_auc_score(y == k, scores[:, k])),
                          'any_attack_recall': float((supports[k] - matrix[k, 3]) / supports[k])}
    return {'macro_f1': float(np.mean([v['f1'] for v in per_stage.values()])),
            'accuracy': float(diagonal.sum() / len(y)),
            'normal_fpr_any_attack': float((supports[3] - matrix[3, 3]) / supports[3]),
            'any_attack_recall': float((supports.sum() - supports[3] - matrix[:, 3].sum() + matrix[3, 3]) / (supports.sum() - supports[3])),
            'confusion_matrix': matrix.tolist(), 'per_stage': per_stage}


def normalized(values):
    totals = values.sum(axis=1)
    result = np.full_like(values, 1 / values.shape[1])
    nonzero = totals > 0
    result[nonzero] = values[nonzero] / totals[nonzero, None]
    return result


def matching_array(actual, expected, name):
    require(actual.shape == expected.shape and np.allclose(actual, expected, atol=1e-10, rtol=1e-8), 'array mismatch: ' + name)


def audit(run, data_path, protocol_path):
    run, data_path, protocol_path = Path(run), Path(data_path), Path(protocol_path)
    spec, started, summary, complete = read(protocol_path), read(run / 'STARTED.json'), read(run / 'SUMMARY.json'), read(run / 'COMPLETE.json')
    classes, seeds, families = spec['classes'], spec['seeds'], spec['models']
    require(classes == ['DataExfiltration', 'InitialCompromise', 'LateralMovement', 'NormalTraffic', 'Pivoting', 'Reconnaissance'], 'class semantics')
    require(digest(data_path) == spec['data_sha256'] == started['data_sha256'], 'data hash')
    require(digest(protocol_path) == started['protocol_sha256'], 'protocol hash')
    require(digest(Path(__file__).with_name('run.py')) == started['runner_sha256'], 'runner hash')
    require(digest(run / 'SUMMARY.json') == complete['summary_sha256'], 'summary hash')
    require(digest(run / 'STARTED.json') == complete['started_sha256'], 'started hash')
    for key, value in started.items():
        compare(summary['receipt'][key], value, 'summary.receipt.' + key)
    require(summary['interpretation'] == spec['evaluation_status'], 'scope binding')
    with np.load(data_path, allow_pickle=False) as z:
        data = {k: z[k] for k in ['y', 'split', 'classes', 'group_sha256']}
    require(data['classes'].tolist() == classes, 'input class order')
    require(len(np.unique(data['group_sha256'])) == len(data['y']), 'duplicate input groups')
    cal_indices, test_indices = np.flatnonzero(data['split'] == 1), np.flatnonzero(data['split'] == 2)
    ycal, ytest = data['y'][cal_indices], data['y'][test_indices]
    for name, y in [('calibration_counts', ycal), ('test_counts', ytest)]:
        compare(started[name], dict(zip(classes, map(int, np.bincount(y, minlength=6)))), name)
    require([m['seed'] for m in summary['seeds']] == seeds, 'summary seed roster')
    base_names = [f'{view}__{family}__{task}' for view in ['raw', 'engineered'] for family in families
                  for task in (['general', 'binary_0'] if view == 'raw' else ['general'] + [f'binary_{k}' for k in range(6)])]
    standard = [f'{view}_general_{f}' for view in ['raw', 'engineered'] for f in families]
    exfil_names = standard + [f'{view}_specialist_{f}' for view in ['raw', 'engineered'] for f in families] + [
        'engineered_general_average', 'engineered_specialist_average', 'engineered_fixed_fusion',
        'engineered_general_learned', 'engineered_learned_fusion']
    stage_names = standard + ['engineered_general_average', 'engineered_specialist_average', 'engineered_fixed_fusion',
        'engineered_selected_specialists', 'engineered_general_learned', 'engineered_specialist_learned', 'engineered_learned_fusion']
    models = [k + '.joblib' for k in base_names] + ['exfil__' + n + '.joblib' for n in ['engineered_general_learned', 'engineered_learned_fusion']] + [
        'stage__' + n + '.joblib' for n in ['engineered_general_learned', 'engineered_specialist_learned', 'engineered_learned_fusion']]
    seed_checks = []
    for seed, saved_metrics in zip(seeds, summary['seeds']):
        folder = run / str(seed)
        receipt, metrics, folds = read(folder / 'COMPLETE.json'), read(folder / 'METRICS.json'), read(folder / 'FOLDS.json')
        require(receipt['seed'] == seed, 'seed receipt')
        verify_hashes(folder, receipt['files'], ['PREDICTIONS.npz', 'METRICS.json', 'FOLDS.json'])
        verify_hashes(folder / 'models', receipt['models'], models)
        compare(saved_metrics, metrics, f'summary.seed.{seed}')
        with np.load(folder / 'PREDICTIONS.npz', allow_pickle=False) as z:
            packet = {k: z[k] for k in z.files}
        fit = []
        for k, name in enumerate(classes):
            pool = np.flatnonzero((data['split'] == 0) & (data['y'] == k))
            ranked = sorted(pool, key=lambda idx: hashlib.sha256(f"EXFIL_STAGE_V1|{seed}|{data['group_sha256'][idx]}".encode('ascii')).digest())
            n = spec['fit_budget']['NormalTraffic'] if name == 'NormalTraffic' else spec['fit_budget']['each_attack_stage']
            fit.extend(ranked[:n])
        fit = np.asarray(fit, dtype=np.int64)
        require(len(np.unique(fit)) == len(fit), 'duplicate fitting identities')
        for key, expected in [('fit_indices', fit), ('fit_y', data['y'][fit]), ('cal_indices', cal_indices), ('cal_y', ycal), ('test_indices', test_indices), ('test_y', ytest)]:
            require(np.array_equal(packet[key], expected), 'input identity mismatch: ' + key)
        expected_folds = np.full(len(fit), -1, dtype=int)
        for k, (_, held) in enumerate(StratifiedKFold(3, shuffle=True, random_state=seed).split(np.zeros(len(fit)), data['y'][fit])):
            expected_folds[held] = k
        require(np.array_equal(packet['fold_ids'], expected_folds), 'OOF fold membership')
        require(set(folds) == set(base_names), 'fold model roster')
        for base in base_names:
            expected_meta = [{'fold': k, 'train_rows': int((expected_folds != k).sum()), 'validation_rows': int((expected_folds == k).sum()),
                              'train_local_indices': np.flatnonzero(expected_folds != k).tolist(),
                              'validation_local_indices': np.flatnonzero(expected_folds == k).tolist()} for k in range(3)]
            compare(folds[base], expected_meta, 'OOF metadata.' + base)
            for split, n in [('oof', len(fit)), ('cal', len(ycal)), ('test', len(ytest))]:
                probability(packet[f'base::{base}::{split}'], n, 6 if base.endswith('__general') else None)
        expected_keys = {'fit_indices', 'fit_y', 'fold_ids', 'cal_indices', 'test_indices', 'cal_y', 'test_y'}
        expected_keys.update(f'base::{base}::{split}' for base in base_names for split in ['oof', 'cal', 'test'])
        for task, names in [('exfil', exfil_names), ('stage', stage_names)]:
            for name in names:
                for split, n in [('cal', len(ycal)), ('test', len(ytest))]:
                    key = f'{task}::{name}::{split}'; expected_keys.add(key)
                    probability(packet[key], n, 6 if task == 'stage' else None)
        require(set(packet) == expected_keys, 'prediction packet roster')
        selection = []
        for k, name in enumerate(classes):
            aps = [float(average_precision_score(data['y'][fit] == k, packet[f'base::engineered__{f}__binary_{k}::oof'])) for f in families]
            selection.append({'class': name, 'family_index': int(np.argmax(aps)), 'candidate_oof_ap': aps})
        compare(metrics['stage_family_selection'], selection, 'OOF expert selection')
        for split in ['cal', 'test']:
            for view in ['raw', 'engineered']:
                for family in families:
                    g = packet[f'base::{view}__{family}__general::{split}']
                    matching_array(packet[f'stage::{view}_general_{family}::{split}'], g, 'general alias')
                    matching_array(packet[f'exfil::{view}_general_{family}::{split}'], g[:, 0], 'general exfil alias')
                    matching_array(packet[f'exfil::{view}_specialist_{family}::{split}'], packet[f'base::{view}__{family}__binary_0::{split}'], 'specialist reuse')
            gs = [packet[f'base::engineered__{f}__general::{split}'] for f in families]
            ss = [np.column_stack([packet[f'base::engineered__{f}__binary_{k}::{split}'] for k in range(6)]) for f in families]
            fixed_stage = {'engineered_general_average': np.mean(gs, axis=0),
                           'engineered_specialist_average': np.mean([normalized(x) for x in ss], axis=0),
                           'engineered_fixed_fusion': np.mean(gs + [normalized(x) for x in ss], axis=0),
                           'engineered_selected_specialists': normalized(np.column_stack([ss[c['family_index']][:, k] for k, c in enumerate(selection)]))}
            fixed_exfil = {'engineered_general_average': np.mean([x[:, 0] for x in gs], axis=0),
                           'engineered_specialist_average': np.mean([x[:, 0] for x in ss], axis=0),
                           'engineered_fixed_fusion': np.mean([x[:, 0] for x in gs + ss], axis=0)}
            for task, arms in [('stage', fixed_stage), ('exfil', fixed_exfil)]:
                for name, value in arms.items():
                    matching_array(packet[f'{task}::{name}::{split}'], value, task + '.' + name)
        expected_metrics = {'seed': seed, 'fit_counts': dict(zip(classes, map(int, np.bincount(data['y'][fit], minlength=6)))),
                            'stage_family_selection': selection, 'base_fit_count': len(base_names) * 4,
                            'final_base_models': len(base_names), 'fusion_fit_count': 5,
                            'exfil': {name: exfil_metrics(ycal, ytest, packet[f'exfil::{name}::cal'], packet[f'exfil::{name}::test'], classes, spec['descriptive_fpr_design_budgets']) for name in exfil_names},
                            'stage': {name: stage_metrics(ytest, packet[f'stage::{name}::test'], classes) for name in stage_names}}
        compare(metrics, expected_metrics, f'metrics.{seed}')
        seed_checks.append({'seed': seed, 'complete_sha256': digest(folder / 'COMPLETE.json'),
                            'artifact_hashes': receipt['files'], 'model_hashes': receipt['models'],
                            'fit_rows': len(fit), 'OOF_folds': 3, 'base_models': len(base_names),
                            'exfil_arms_recomputed': len(exfil_names), 'stage_arms_recomputed': len(stage_names)})
    for key, value in [('final_base_models', len(base_names) * len(seeds)), ('base_fits_including_crossfit', 4 * len(base_names) * len(seeds)), ('fusion_fits', 5 * len(seeds))]:
        require(summary['receipt'][key] == value, 'fit accounting: ' + key)
    require(digest(run / 'SUMMARY.json') == complete['summary_sha256'], 'outputs changed during audit')
    return {'audit_status': 'PASS', 'run_status': 'COMPLETE', 'audited_utc': datetime.now(timezone.utc).isoformat(),
            'artifact_hashes': {name: digest(run / name) for name in ['SUMMARY.json', 'STARTED.json', 'COMPLETE.json']},
            'data_sha256': digest(data_path), 'protocol_sha256': digest(protocol_path),
            'runner_sha256': started['runner_sha256'], 'audit_sha256': digest(__file__),
            'seeds': seed_checks, 'completed_seeds': len(seeds), 'final_base_models': len(base_names) * len(seeds),
            'metrics_recomputed': len(seeds) * (len(exfil_names) + len(stage_names)),
            'checks': ['input and source/protocol hashes', 'complete artifact/model rosters and hashes',
                       'deterministic supports and disjoint original partitions', 'OOF fold identity and held-row exclusion metadata',
                       'probability dimensions/ranges/class order', 'OOF stage-family selection and fixed-fusion arithmetic',
                       'independent exact F1 frontier and strict tied tail thresholds', 'all ranking/classification/count metrics',
                       'summary copies and fit accounting'],
            'limitations': ['No model fitting, inference, deserialization or independent replay of base/learned predictions.',
                            'OOF and model provenance bind reviewed source and saved metadata; discarded fold models were not replayed.',
                            'Source labels and feature semantics were not independently adjudicated.',
                            'PASS concerns saved-output integrity; it does not establish a positive effect, novelty or independent-incident validity.']}


def main():
    parser = argparse.ArgumentParser()
    for key in ['run', 'data', 'protocol', 'output']:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'audit output must be fresh')
    try:
        result = audit(args.run, args.data, args.protocol)
    except Exception as error:
        result = {'audit_status': 'FAIL', 'run_status': 'NOT_VERIFIED', 'error_type': type(error).__name__, 'error': str(error),
                  'audited_utc': datetime.now(timezone.utc).isoformat(), 'audit_sha256': digest(__file__)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k in ['audit_status', 'run_status', 'completed_seeds', 'metrics_recomputed', 'error']}))
    if result['audit_status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
