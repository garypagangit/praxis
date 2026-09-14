"""Postrun independent saved-result extension for 010 original25/calibration.

This reviewer code was written after original25 completed, not frozen before
model execution. It does not import the worker, Torch, or a model/calibrator.
The archived v1 audit and its evidence boundaries are retained unchanged.
Requires NumPy, SciPy and the standard library. No network operations.
"""
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import chi2

from audit_010_results_independent import audit as audit_new3, sha

POLICIES = ('historical_oracle_blend', 'rolling', 'alarm_only_blend', 'literal_freeze')
NAB_SHA = 'e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584'
ATOL, RTOL = 1e-10, 1e-10


class Checks:
    def __init__(self):
        self.items = []

    def check(self, name, valid, detail=None):
        self.items.append({'check': name, 'passed': bool(valid), 'detail': detail})

    @property
    def passed(self):
        return all(c['passed'] for c in self.items)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def close(left, right):
    a, b = np.asarray(left), np.asarray(right)
    return a.shape == b.shape and bool(np.isfinite(a).all() and np.isfinite(b).all()
                                      and np.allclose(a, b, atol=ATOL, rtol=RTOL))


def indexed(rows, expected, checks, label):
    keys = [(r['policy'], r['seed'], r['stream'], r['t']) for r in rows]
    valid = len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
    checks.check(label + ':exact_assignment_universe', valid, {'rows': len(rows), 'expected': len(expected)})
    if not valid:
        raise ValueError(label + ' has missing, duplicate or unexpected assignments')
    return dict(zip(keys, rows))


def seeded_clean(seed, n):
    rng = np.random.RandomState(seed)
    angle = .3
    transition = np.array([[np.cos(angle), np.sin(angle) / angle],
                           [-np.sin(angle) * angle, np.cos(angle)]])
    observation = np.array([[1., 0.], [.31, -.48], [-.21, .43]])
    state = np.array([1., 0.])
    result = np.empty((n, 3), dtype=np.float64)
    for t in range(n):
        result[t] = observation @ state + .01 * rng.randn(3)
        state = transition @ state
    return result


def expected_action(policy, stream, t, alarm, observation, prediction):
    """Preserve float32 multiply BEFORE adding float64 observations.

    Historical source computes the second coefficient as 1 - .8; the worker's
    deployable blend uses literal .2. They can differ at the last float64 bit.
    """
    observation = np.asarray(observation, dtype=np.float64)
    prediction = np.asarray(prediction, dtype=np.float32)
    if policy == 'historical_oracle_blend':
        oracle = bool(t >= 71) if stream == 'att' else False
        if stream == 'att' and oracle and alarm:
            return oracle, 'blend', .8 * prediction + (1 - .8) * observation
        return oracle, 'observed', observation
    if policy == 'literal_freeze' and alarm:
        return None, 'freeze', None
    if policy == 'alarm_only_blend' and alarm:
        return None, 'blend', .8 * prediction + .2 * observation
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    return None, 'observed', observation


def admission_equal(recorded, expected):
    if expected is None:
        return recorded is None
    return recorded is not None and np.array_equal(np.asarray(recorded, dtype=np.float64), expected)


def comparison_counts(pointwise):
    output = []
    for policy in POLICIES:
        attack = [r for r in pointwise if r['policy'] == policy and r['stream'] == 'att']
        clean = [r for r in pointwise if r['policy'] == policy and r['stream'] == 'cln']
        output.append({'policy': policy, 'attack_points': len(attack), 'clean_points': len(clean),
                       'detected_episodes': len({r['seed'] for r in attack if r['alarm']}),
                       'episode_denominator': len({r['seed'] for r in attack}),
                       'alarm_attack_points': sum(r['alarm'] for r in attack),
                       'alarm_clean_points': sum(r['alarm'] for r in clean)})
    return output


def common(source, cloud, mode, expected_artifacts, checks):
    directory = cloud / mode
    receipt = read_json(directory / 'QUALIFICATION_RECEIPT.json')
    checks.check(mode + ':no_failure_receipt', not (directory / 'FAILED_QUALIFICATION_RECEIPT.json').exists())
    checks.check(mode + ':worker_identity', receipt['runner_sha256'] == sha(source / 'code/gpu_qualification.py'))
    checks.check(mode + ':protocol_identity', receipt['protocol_freeze'] == read_json(source / 'PROTOCOL_FREEZE.json'))
    actual_artifacts = {p.name: sha(p) for p in directory.iterdir() if p.is_file() and p.name != 'QUALIFICATION_RECEIPT.json'}
    checks.check(mode + ':artifacts_exact_hashes', set(actual_artifacts) == set(expected_artifacts)
                 and receipt['artifacts'] == actual_artifacts)
    checks.check(mode + ':complete_correct_mode', receipt['mode'] == mode and receipt['implementation_complete'] is True)
    checks.check(mode + ':exit_zero', (cloud / (mode.upper() + '_EXIT.txt')).read_text().strip() == '0')
    checks.check(mode + ':heldout_not_scored', receipt['heldout_hai_scored'] is False)
    checks.check(mode + ':hardware', receipt['device'] == 'NVIDIA A10G')
    checks.check(mode + ':runtime_finite_and_bounded', math.isfinite(receipt['runtime_seconds'])
                 and 0 < receipt['runtime_seconds'] < 2400)
    checks.check(mode + ':memory_measurement_finite', math.isfinite(receipt['peak_allocated_gib'])
                 and 0 <= receipt['peak_allocated_gib'] < 24)
    return directory, receipt, actual_artifacts


def audit_original25(source, cloud):
    checks = Checks()
    directory, receipt, artifacts = common(source, cloud, 'original25',
                                            ['pointwise.jsonl', 'interventions.jsonl', 'historical_raw.npz'], checks)
    pointwise = read_rows(directory / 'pointwise.jsonl')
    interventions = read_rows(directory / 'interventions.jsonl')
    expected = {(p, s, k, t) for p in POLICIES for s in range(1, 21) for k in ('att', 'cln') for t in range(71, 101)}
    points = indexed(pointwise, expected, checks, 'original25:pointwise')
    expected = {(p, s, k, t) for p in POLICIES for s in range(1, 21) for k in ('att', 'cln') for t in range(51, 101)}
    steps = indexed(interventions, expected, checks, 'original25:interventions')
    with np.load(directory / 'historical_raw.npz', allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    expected_keys = {'fm_calibration_residuals', 'fm_covariance'} | {
        f'seed{s}_{name}' for s in range(1, 21) for name in ('y_att', 'y_cln', 'res_fm_att', 'res_fm_cln', 'buffer')}
    checks.check('original25:npz_exact_keys', set(arrays) == expected_keys)
    checks.check('original25:all_arrays_finite', all(np.isfinite(a).all() for a in arrays.values()))
    checks.check('original25:calibration_shapes', arrays['fm_calibration_residuals'].shape == (20, 3)
                 and arrays['fm_covariance'].shape == (3, 3))
    covariance = np.cov(arrays['fm_calibration_residuals'].T)
    checks.check('original25:covariance_recomputed', close(covariance, arrays['fm_covariance']))
    inverse = np.linalg.inv(covariance)
    checks.check('original25:covariance_positive_definite', bool(np.linalg.eigvalsh(covariance).min() > 0))
    threshold = float(chi2.ppf(.995, 3))
    commissioning = seeded_clean(0, 71)
    replay_start = int(71 - 2 * np.pi / .3)
    recording = commissioning[replay_start:replay_start + 20]
    for seed in range(1, 21):
        clean = seeded_clean(seed, 101)
        attacked = clean.copy()
        attacked[71:] = recording[np.arange(30) % 20]
        checks.check(f'original25:seeded_inputs:{seed}', close(clean, arrays[f'seed{seed}_y_cln'])
                     and close(attacked, arrays[f'seed{seed}_y_att']))
        checks.check(f'original25:historical_shapes:{seed}', all(arrays[f'seed{seed}_{key}'].shape == shape for key, shape in
                     [('y_att', (101, 3)), ('y_cln', (101, 3)), ('buffer', (101, 3)), ('res_fm_att', (50, 3)), ('res_fm_cln', (50, 3))]))
        checks.check(f'original25:initial_buffer:{seed}', np.array_equal(arrays[f'seed{seed}_buffer'][:51], attacked[:51]))
    max_score_error = 0.0
    action_counts = {}
    for key, step in steps.items():
        policy, seed, stream, t = key
        observation = arrays[f'seed{seed}_y_{stream}'][t]
        raw_prediction = np.asarray(step['prediction'], dtype=np.float64)
        prediction = raw_prediction.astype(np.float32)
        prediction_ok = prediction.shape == (3,) and np.isfinite(prediction).all() and np.array_equal(raw_prediction, prediction.astype(np.float64))
        residual = observation - prediction
        score = float(residual @ inverse @ residual)
        alarm = bool(score > threshold)
        oracle, action, admitted = expected_action(policy, stream, t, alarm, observation, prediction)
        evidence_valid = prediction_ok and np.array_equal(observation, np.asarray(step['observation']))
        decision_valid = type(step['alarm']) is bool and step['alarm'] == alarm and step['oracle_onset_eligible'] is oracle
        admission_valid = step['action'] == action and admission_equal(step['admitted'], admitted)
        checks.check('original25:step:' + ':'.join(map(str, key)), evidence_valid and decision_valid and admission_valid,
                     None if evidence_valid and decision_valid and admission_valid else {'evidence': bool(evidence_valid), 'decision': bool(decision_valid), 'admission': bool(admission_valid)})
        group = policy + ':' + stream + ':' + action
        action_counts[group] = action_counts.get(group, 0) + 1
        if t >= 71:
            point = points[key]
            max_score_error = max(max_score_error, abs(score - point['score']))
            checks.check('original25:score:' + ':'.join(map(str, key)), math.isfinite(point['score'])
                         and math.isclose(score, point['score'], abs_tol=ATOL, rel_tol=RTOL)
                         and type(point['alarm']) is bool and point['alarm'] == alarm)
        if policy == 'historical_oracle_blend':
            valid = np.array_equal(residual, arrays[f'seed{seed}_res_fm_{stream}'][t - 51])
            if stream == 'att':
                valid = valid and admission_equal(arrays[f'seed{seed}_buffer'][t], admitted)
            checks.check('original25:historical_saved:' + ':'.join(map(str, key)), valid)
    counts = comparison_counts(pointwise)
    checks.check('original25:summary_counts_exact', receipt['comparisons'] == counts)
    required_flags = ('implementation_gate_pass', 'covariance_finite', 'historical_statistics_finite',
                      'unique_complete_rows', 'unique_complete_interventions', 'historical_oracle_attack_onset')
    checks.check('original25:reported_gate_fields', all(receipt[k] is True for k in required_flags)
                 and receipt['qualification_gate'] == 'PASS' and receipt['intervention_steps'] == 8000
                 and receipt['novel_method_tested'] is False)
    timing_keys = ['model_initialization_seconds', 'inference_and_bookkeeping_seconds_including_lazy_jit']
    checks.check('original25:timing_components', all(math.isfinite(receipt[k]) and receipt[k] >= 0 for k in timing_keys)
                 and sum(receipt[k] for k in timing_keys) <= receipt['runtime_seconds'] + 1e-6)
    return {'status': 'PASS_BOUNDED_REPRODUCTION' if checks.passed else 'FAIL',
            'results_receipt_sha256': sha(directory / 'QUALIFICATION_RECEIPT.json'), 'artifacts': artifacts,
            'pointwise_rows_verified': len(pointwise), 'intervention_rows_verified': len(interventions),
            'metrics_recomputed_from_rows': counts, 'action_counts_all_50_online_positions': action_counts,
            'threshold_independently_computed': threshold, 'maximum_score_absolute_difference': max_score_error,
            'review_numerical_tolerance': {'abs': ATOL, 'rel': RTOL, 'admission': 'exact mixed precision'},
            'runtime_seconds_reported': receipt['runtime_seconds'],
            'interpretation': 'These are 20 source-defined synthetic replay trials with matched clean streams. The historical arm uses known attack onset; deployable arms do not. Episode detection, point retention and false alarms are distinct. No new defense, heldout HAI efficacy, statistical superiority or successful transfer is established.',
            'limits': ['Forecasts and commissioning residuals are archived model outputs, not independently regenerated model predictions.',
                       'Saved actions, admissions, scores, labels and summary counts are independently reconciled; the actual forecast input tensor at each call is not archived.',
                       'Covariance estimated from one shared 20-point clean calibration window; repeated points/trials share that calibration and replay recording.',
                       'Resource measurements are receipt values checked for arithmetic/finite bounds, not regenerated allocator or timing traces.']}, checks.items


def expected_truth(values):
    values = np.asarray(values, dtype=np.float32)
    target = np.full((len(values) - 90, 15, 1), np.nan, dtype=np.float32)
    for row, origin in enumerate(range(89, len(values) - 1)):
        count = min(15, len(values) - origin - 1)
        target[row, :count, 0] = values[origin + 1:origin + count + 1]
    return target


def calibration_counts(rows):
    scored = [r for r in rows if r['scored']]
    return {'scored_positions': len(scored),
            'true_positive_points': sum(r['alarm'] and r['label'] == 1 for r in scored),
            'false_positive_points': sum(r['alarm'] and r['label'] == 0 for r in scored),
            'anomaly_points': sum(r['label'] == 1 for r in scored),
            'normal_points': sum(r['label'] == 0 for r in scored)}


def audit_calibration(source, cloud, nab_data):
    checks = Checks()
    directory, receipt, artifacts = common(source, cloud, 'calibration', ['forecasts.npz', 'pointwise.jsonl'], checks)
    checks.check('calibration:public_data_pin', sha(nab_data) == NAB_SHA)
    with Path(nab_data).open(newline='', encoding='utf-8-sig') as handle:
        raw = list(csv.DictReader(handle))
    values = np.asarray([float(r['Data']) for r in raw], dtype=np.float64)
    labels = np.asarray([int(r['Label']) for r in raw], dtype=int)
    checks.check('calibration:public_data_shape_finite_binary', len(values) == 4031 and np.isfinite(values).all()
                 and set(labels).issubset({0, 1}))
    with np.load(directory / 'forecasts.npz', allow_pickle=False) as archive:
        checks.check('calibration:npz_exact_keys', set(archive.files) == {'y_pred', 'y_true'})
        prediction, target = archive['y_pred'], archive['y_true']
    expected = expected_truth(values)
    checks.check('calibration:forecast_shapes', target.shape == prediction.shape == (3941, 15, 1))
    checks.check('calibration:forecast_finite', np.isfinite(prediction).all())
    checks.check('calibration:truth_alignment_exact', np.array_equal(target, expected, equal_nan=True))
    checks.check('calibration:truth_dtype', target.dtype == np.dtype('float32'))
    checks.check('calibration:future_missing_exact', np.isnan(target).sum() == 105 and not np.isnan(target).all(axis=(1, 2)).any())
    rows = read_rows(directory / 'pointwise.jsonl')
    checks.check('calibration:exact_rows', len(rows) == 4031 and [r['t'] for r in rows] == list(range(4031)))
    for row in rows:
        t = row['t']
        p = row['pvalue']
        checks.check(f'calibration:point:{t}', math.isfinite(p) and 0 <= p <= 1 and row['label'] == int(labels[t])
                     and type(row['scored']) is bool and row['scored'] == (t >= 1007)
                     and type(row['alarm']) is bool and row['alarm'] == (p < .01)
                     and (t >= 1007 or p == 1))
    counts = calibration_counts(rows)
    checks.check('calibration:summary_counts', all(receipt[k] == v for k, v in counts.items()))
    expected_fields = {'dataset_rows': 4031, 'context_rows': 90, 'original_train_boundary': 1007,
                       'assigned_forecast_origins': 3942, 'all_future_missing_origin_excluded': 1,
                       'forecast_boundary_missing_targets': 105, 'requested_n_epochs': 1, 'effective_epochs': 2}
    checks.check('calibration:assignment_and_effective_parameters', all(receipt[k] == v for k, v in expected_fields.items()))
    checks.check('calibration:scope_and_finite_flags', receipt['upstream_epoch_parameter_mismatch_preserved'] is True
                 and receipt['forecast_values_finite'] is True and receipt['scored_pvalues_finite'] is True
                 and receipt['aggregate_paper_replication_claimed'] is False and receipt['dataset_all_development'] is True)
    repeat = receipt['max_repeat_abs_difference']
    checks.check('calibration:reported_operational_gate', math.isfinite(repeat) and 0 <= repeat <= 1e-5
                 and receipt['implementation_gate_pass'] is True and receipt['qualification_gate'] == 'PASS')
    timing_keys = ['model_initialization_seconds', 'forecast_and_bookkeeping_seconds', 'calibration_and_scoring_seconds']
    checks.check('calibration:timing_components', all(math.isfinite(receipt[k]) and receipt[k] >= 0 for k in timing_keys)
                 and sum(receipt[k] for k in timing_keys) <= receipt['runtime_seconds'] + 1e-6)
    return {'status': 'PASS_BOUNDED_ALIGNMENT_AND_ACCOUNTING' if checks.passed else 'FAIL',
            'results_receipt_sha256': sha(directory / 'QUALIFICATION_RECEIPT.json'), 'artifacts': artifacts,
            'public_data_sha256': sha(nab_data), 'rows_verified': len(rows),
            'forecast_tensor_shape': list(prediction.shape), 'missing_future_targets': int(np.isnan(target).sum()),
            'metrics_recomputed_from_rows': counts, 'effective_epochs': 2, 'requested_n_epochs': 1,
            'runtime_seconds_reported': receipt['runtime_seconds'],
            'interpretation': 'One designated public NAB development series qualifies Chronos/W1ACAS execution and alignment. Requested n_epochs=1 is an upstream parameter mismatch; effective epochs=2 is preserved under A1. Point detection counts are descriptive, not new-method efficacy, independent attack episodes, or a replication of aggregate benchmark results.',
            'limits': ['Archived W1ACAS p-values are checked for labels, scoring masks, range, thresholds and summary consistency; they are not numerically recomputed by this auditor.',
                       'Chronos forecasts and unarchived repeated-batch forecasts are not regenerated; repeat determinism is a reported operational measurement.',
                       'Source review addresses chronological ordering, but this result audit cannot reconstruct unarchived internal optimizer states.',
                       'This single NAB series is entirely development data; no HAI or independent test split was scored.']}, checks.items


def audit(source, cloud, source_review, modes, nab_data=None):
    source, cloud = Path(source), Path(cloud)
    if not modes or not set(modes).issubset({'new3', 'original25', 'calibration'}) or len(set(modes)) != len(modes):
        raise ValueError('Explicit distinct released modes required')
    initial = audit_new3(source, cloud, source_review)
    if 'new3' not in modes:
        raise ValueError('Extension retains prior new3 audit; include new3 in released modes')
    report = dict(initial)
    report['reviewed_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['modes'] = dict(initial['modes'])
    checks = list(initial['checks'])
    for mode in ('original25', 'calibration'):
        if mode not in modes:
            report['modes'][mode] = {'status': 'PENDING', 'reason': 'Mode not explicitly released to this audit invocation.'}
            continue
        if mode == 'original25':
            result, extra = audit_original25(source, cloud)
        else:
            if nab_data is None:
                raise ValueError('--nab-data required for released calibration audit')
            result, extra = audit_calibration(source, cloud, Path(nab_data))
        report['modes'][mode] = result
        checks.extend(extra)
    passed = all(c['passed'] for c in checks)
    complete = set(modes) == {'new3', 'original25', 'calibration'}
    report.update(status=('PASS_ALL_RELEASED_GPU_MODES' if complete else 'PARTIAL_VERIFIED_RELEASED_MODES') if passed else 'FAIL',
                  overall_010_qualification='GPU_COMPONENTS_VERIFIED_ROOT_CPU_AND_CLOSEOUT_REQUIRED' if complete and passed else 'PENDING',
                  checks=checks, checks_total=len(checks), checks_passed=sum(c['passed'] for c in checks),
                  checks_failed=sum(not c['passed'] for c in checks), released_modes=modes,
                  method='Independent postrun NumPy/SciPy saved-result reconstruction; no model, worker, upstream calibrator or cloud execution.',
                  audit_extension_source_sha256=sha(__file__),
                  prior_new3_audit_source_sha256=sha(Path(__file__).with_name('audit_010_results_independent.py')),
                  audit_source_frozen_before_model_runs=False, audit_source_archived_after_original25_model_run=True)
    report['scope_limits'] = [s for s in initial['scope_limits'] if not s.startswith('Original25/calibration')]
    report['scope_limits'] += ['Any unreleased mode is pending, not a zero outcome or successful qualification.',
                              'No favorable detection or novelty gate is inferred from operational PASS. Calibration preserves A1 requested 1/effective 2 epochs.']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cloud-results', type=Path, required=True)
    parser.add_argument('--source-review', type=Path, required=True)
    parser.add_argument('--modes', required=True, help='Comma-separated explicitly released modes, including new3')
    parser.add_argument('--nab-data', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.source, args.cloud_results, args.source_review, args.modes.split(','), args.nab_data)
    except Exception as exc:
        result = {'status': 'FAIL', 'overall_010_qualification': 'PENDING',
                  'error_type': type(exc).__name__, 'error': str(exc),
                  'scope': 'Missing/malformed input or incomplete audit cannot pass.'}
    result.update(audit_source_sha256=sha(__file__), audit_source_frozen_before_model_runs=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'checks_total', 'checks_failed', 'error') if k in result}))
    raise SystemExit(1 if result['status'] == 'FAIL' else 0)


if __name__ == '__main__':
    main()
