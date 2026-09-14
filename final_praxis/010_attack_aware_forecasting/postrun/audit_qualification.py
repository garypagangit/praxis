"""Read-only accounting audit of Q1 artifacts; no model/optimization/cloud calls.

This checks file/source identity, complete assigned rows, reproduced metrics,
intervention arithmetic and target alignment. It does not rerun the forecasters
or the W1ACAS optimizer and cannot recreate an absent author environment.
"""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    p = argparse.ArgumentParser()
    for name in ['original25', 'new3', 'calibration']:
        p.add_argument('--' + name, type=Path)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    checks, missing, receipts = {}, [], {}

    def check(name, value):
        checks[name] = bool(value)

    freeze = json.loads((ROOT / 'RUNTIME_FREEZE.json').read_text())
    expected_runner = freeze['files']['code/gpu_qualification.py']
    for mode in ['original25', 'new3', 'calibration']:
        directory = getattr(args, mode)
        if directory is None or not (directory / 'QUALIFICATION_RECEIPT.json').exists():
            if directory is not None and (directory / 'FAILED_QUALIFICATION_RECEIPT.json').exists():
                check(mode + '_failed_attempt_present', False)
            missing.append(mode)
            continue
        result = json.loads((directory / 'QUALIFICATION_RECEIPT.json').read_text())
        receipts[mode] = {'sha256': sha(directory / 'QUALIFICATION_RECEIPT.json'), 'declared_gate': result.get('qualification_gate')}
        check(mode + '_runner_identity', result['runner_sha256'] == expected_runner)
        check(mode + '_no_failed_receipt_same_attempt', not (directory / 'FAILED_QUALIFICATION_RECEIPT.json').exists())
        check(mode + '_mode_identity', result['mode'] == mode)
        check(mode + '_no_hai_heldout', result['heldout_hai_scored'] is False)
        check(mode + '_worker_gate_pass', result['qualification_gate'] == 'PASS')
        for name, expected in result['artifacts'].items():
            target = (directory / name).resolve()
            check(mode + '_safe_path_' + name, target.is_relative_to(directory.resolve()))
            check(mode + '_artifact_hash_' + name, target.is_file() and sha(target) == expected)
        if mode == 'original25':
            rows = read_rows(directory / 'pointwise.jsonl')
            actions = read_rows(directory / 'interventions.jsonl')
            policies = ['historical_oracle_blend', 'rolling', 'alarm_only_blend', 'literal_freeze']
            key = lambda r: (r['policy'], r['seed'], r['stream'], r['t'])
            expected = {(policy, seed, stream, t) for policy in policies for seed in range(1, 21) for stream in ['att', 'cln'] for t in range(71, 101)}
            all_expected = {(policy, seed, stream, t) for policy in policies for seed in range(1, 21) for stream in ['att', 'cln'] for t in range(51, 101)}
            check('original_endpoint_universe_4800', len(rows) == len({key(r) for r in rows}) == 4800 and {key(r) for r in rows} == expected)
            check('original_intervention_universe_8000', len(actions) == len({key(r) for r in actions}) == 8000 and {key(r) for r in actions} == all_expected)
            raw = np.load(directory / 'historical_raw.npz', allow_pickle=False)
            covariance = raw['fm_covariance']; inv = np.linalg.inv(covariance)
            check('original_covariance_matches_calibration', np.allclose(covariance, np.cov(raw['fm_calibration_residuals'].T), atol=1e-12, rtol=1e-12))
            check('original_raw_all_finite', all(np.isfinite(raw[k]).all() for k in raw.files))
            endpoints = {key(r): r for r in rows}
            threshold = 12.838156466598647  # scipy chi2.ppf(.995,3), checked below via each score/alarm margin
            from scipy.stats import chi2
            threshold = float(chi2.ppf(.995, 3))
            action_ok, score_ok, causal_gate = True, True, True
            for row in actions:
                observation, prediction = np.asarray(row['observation']), np.asarray(row['prediction'])
                residual = observation - prediction
                score = float(residual @ inv @ residual)
                score_ok &= np.isfinite(score) and bool(score > threshold) == row['alarm']
                if row['t'] >= 71:
                    endpoint = endpoints[key(row)]
                    score_ok &= np.isclose(score, endpoint['score'], atol=1e-9, rtol=1e-9) and endpoint['alarm'] == row['alarm']
                if row['policy'] == 'historical_oracle_blend':
                    eligible = row['stream'] == 'att' and row['t'] >= 71
                    expected_action = 'blend' if eligible and row['alarm'] else 'observed'
                    causal_gate &= row['oracle_onset_eligible'] == eligible
                else:
                    expected_action = 'freeze' if row['policy'] == 'literal_freeze' and row['alarm'] else 'blend' if row['policy'] == 'alarm_only_blend' and row['alarm'] else 'observed'
                    causal_gate &= row['oracle_onset_eligible'] is None
                action_ok &= row['action'] == expected_action
                if expected_action == 'freeze':
                    action_ok &= row['admitted'] is None
                else:
                    admitted = .8 * prediction + .2 * observation if expected_action == 'blend' else observation
                    action_ok &= np.allclose(row['admitted'], admitted, atol=1e-10, rtol=1e-10)
            check('original_every_intervention_arithmetic', action_ok)
            check('original_every_residual_score_alarm', score_ok)
            check('original_oracle_vs_deployable_gate_distinction', causal_gate)
            for item in result['comparisons']:
                attack = [r for r in rows if r['policy'] == item['policy'] and r['stream'] == 'att']
                clean = [r for r in rows if r['policy'] == item['policy'] and r['stream'] == 'cln']
                measured = {'attack_points': len(attack), 'clean_points': len(clean), 'episode_denominator': 20, 'detected_episodes': sum(any(r['alarm'] for r in attack if r['seed'] == seed) for seed in range(1, 21)), 'alarm_attack_points': sum(r['alarm'] for r in attack), 'alarm_clean_points': sum(r['alarm'] for r in clean)}
                check('original_comparison_' + item['policy'], all(item[k] == v for k, v in measured.items()))
        elif mode == 'new3':
            rows = read_rows(directory / 'development_probe.jsonl')
            check('new3_probe512_complete', [r['t'] for r in rows] == list(range(256, 768)))
            x = np.random.RandomState(0).normal(0, .05, (768, 3)).astype(np.float32); x[384:640] += 2
            check('new3_probe_residuals_recomputed', all(np.asarray(r['forecast']).shape == (3,) and np.isclose(np.max(np.abs(x[r['t']] - np.asarray(r['forecast'], dtype=np.float32))), r['max_abs_residual'], atol=1e-7, rtol=1e-7) and bool(r['max_abs_residual'] > .5) == r['alarm'] for r in rows))
            attack = [r for r in rows if 384 <= r['t'] < 640]
            hits = [r['t'] - 384 for r in attack if r['alarm']]
            metrics = {'step_onset_delay': min(hits) if hits else None, 'step_full_retention': len(hits) / 256, 'step_first32_alarm_fraction': np.mean([r['alarm'] for r in attack[:32]]), 'step_last32_alarm_fraction': np.mean([r['alarm'] for r in attack[-32:]]), 'step_late_alarm_fraction': np.mean([r['alarm'] for r in attack[32:]]), 'post_return_alarm_points': sum(r['alarm'] for r in rows if r['t'] >= 640)}
            check('new3_all_reported_probe_metrics', all(result[k] == v for k, v in metrics.items()))
            check('new3_actual_operational_limits', result['all_forecasts_finite'] and result['max_repeat_abs_difference'] <= 1e-5 and result['median_batch_latency_seconds'] < 5 and result['peak_allocated_gib'] < 20)
        else:
            rows = read_rows(directory / 'pointwise.jsonl')
            path = args.cache / 'tsbad/Datasets/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv'
            check('calibration_dataset_identity', sha(path) == 'e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584')
            with path.open(newline='') as f:
                source = list(csv.reader(f))
            values = np.array([float(r[0]) for r in source[1:]], dtype=np.float32)
            labels = [int(float(r[-1])) for r in source[1:]]
            check('calibration_all4031_rows', [r['t'] for r in rows] == list(range(4031)))
            check('calibration_scored_boundary_fixed', all(r['scored'] == (r['t'] >= 1007) for r in rows))
            check('calibration_labels_identity', [r['label'] for r in rows] == labels)
            check('calibration_fixed_threshold', all(np.isfinite(r['pvalue']) and 0 <= r['pvalue'] <= 1 and r['alarm'] == (r['pvalue'] < .01) for r in rows))
            forecasts = np.load(directory / 'forecasts.npz', allow_pickle=False)
            check('calibration_forecast_shape_finite', forecasts['y_pred'].shape == forecasts['y_true'].shape == (3941, 15, 1) and np.isfinite(forecasts['y_pred']).all())
            alignment = True
            for i, target in enumerate(forecasts['y_true'][:, :, 0], 90):
                expected = np.full(15, np.nan, dtype=np.float32); n = min(15, len(values) - i); expected[:n] = values[i:i + n]
                alignment &= np.array_equal(expected, target, equal_nan=True)
            check('calibration_every_target_origin_alignment', alignment)
            scored = [r for r in rows if r['scored']]
            metrics = {'scored_positions': len(scored), 'true_positive_points': sum(r['alarm'] and r['label'] == 1 for r in scored), 'false_positive_points': sum(r['alarm'] and r['label'] == 0 for r in scored), 'anomaly_points': sum(r['label'] == 1 for r in scored), 'normal_points': sum(r['label'] == 0 for r in scored), 'requested_n_epochs': 1, 'effective_epochs': 2}
            check('calibration_metrics_from_all_rows', all(result[k] == v for k, v in metrics.items()))
    failures = [k for k, v in checks.items() if not v]
    output = {'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_sha256': sha(Path(__file__)), 'checks': checks, 'checks_passed': sum(checks.values()), 'checks_total': len(checks), 'failures': failures, 'missing_modes': missing, 'receipts': receipts, 'disposition': 'HOLD' if failures else 'PENDING' if missing else 'PASS_ACCOUNTING', 'scope': 'Raw-row metric/intervention/target accounting; no forecast or W1ACAS optimization reexecution.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: output[k] for k in ['disposition', 'checks_passed', 'checks_total', 'missing_modes', 'failures']}))


if __name__ == '__main__':
    main()
