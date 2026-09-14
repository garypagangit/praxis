"""Post-run independent 010 result audit; no model or cloud calls.

This version covers the released TimesFM3 result only. It deliberately leaves
original25/calibration pending, even if other files appear. Source archival
occurred after the model run and initial review; it is not a protocol freeze.
AI-assisted implementation; requires NumPy and the standard library.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(source, cloud_results, source_review):
    source, cloud = Path(source), Path(cloud_results)
    data = cloud / 'new3'
    report = json.loads((data / 'QUALIFICATION_RECEIPT.json').read_text())
    rows = [json.loads(line) for line in (data / 'development_probe.jsonl').read_text().splitlines()]
    freeze = json.loads((source / 'RUNTIME_FREEZE.json').read_text())
    assets = json.loads((source / 'RUNTIME_ASSET_MANIFEST.json').read_text())
    prepared = json.loads((cloud / 'ASSET_RECEIPT_MODELS.json').read_text())
    controls = json.loads((cloud / 'RUNTIME_CONTROLS_CLOUD.json').read_text())
    checks = []

    def check(name, valid, detail=None):
        checks.append({'check': name, 'passed': bool(valid), 'detail': detail})

    for name, expected in freeze['files'].items():
        check('runtime_freeze:' + name, sha(source / name) == expected)
    check('worker_identity', report['runner_sha256'] == sha(source / 'code/gpu_qualification.py'))
    check('protocol_freeze_equal', report['protocol_freeze'] == json.loads((source / 'PROTOCOL_FREEZE.json').read_text()))
    check('artifact_hash', report['artifacts'] == {'development_probe.jsonl': sha(data / 'development_probe.jsonl')})
    check('setup_exit_zero', (cloud / 'SETUP_EXIT.txt').read_text().strip() == '0')
    check('new3_exit_zero', (cloud / 'NEW3_EXIT.txt').read_text().strip() == '0')
    check('completed_mode', report['mode'] == 'new3' and report['implementation_complete'] is True and
          report['qualification_gate'] == 'PASS' and report['feasibility_pass'] is True)
    check('declared_scope', report['development_only'] is True and report['heldout_hai_scored'] is False and
          report['novel_defense_efficacy_claimed'] is False)
    check('raw_universe', len(rows) == 512 and [r['t'] for r in rows] == list(range(256, 768)))
    check('cloud_controls_all22', controls['controls'] == len(controls['checks']) == 22 and
          controls['all_pass'] is True and all(v is True for v in controls['checks'].values()) and
          controls['pretrained_model_loads'] == controls['inference_calls'] == 0)
    check('cloud_control_source_hashes', controls['runner_sha256'] == report['runner_sha256'] and
          controls['test_source_sha256'] == sha(source / 'code/test_runtime_controls.py'))
    by_url = {record['url']: record for record in prepared['files']}
    expected_urls = set()
    for record in assets['files']:
        expected_urls.add(record['url'])
        actual = by_url.get(record['url'], {})
        check('prepared_source:' + record['cache_path'], actual.get('sha256') == record['sha256'] and
              actual.get('bytes') == record['bytes'])
    for repo, info in assets['models'].items():
        for item in info['files']:
            if item['rfilename'].startswith('.'):
                continue
            url = f"https://huggingface.co/{repo}/resolve/{info['revision']}/{item['rfilename']}"
            expected_urls.add(url)
            actual = by_url.get(url, {})
            check('model_asset_present:' + repo + '/' + item['rfilename'], bool(actual) and actual['bytes'] == item['size'])
            if 'lfs' in item:
                check('model_weight_sha:' + repo, actual.get('sha256') == item['lfs']['sha256'])
    check('asset_inventory_exact', len(prepared['files']) == len(by_url) == len(expected_urls) and set(by_url) == expected_urls)

    # Only regenerate the frozen numeric input; forecasts come from saved rows.
    stream = np.random.RandomState(0).normal(0, .05, (768, 3)).astype(np.float32)
    stream[384:640] += 2
    max_difference = 0.0
    for row in rows:
        forecast = np.asarray(row['forecast'], dtype=np.float32)
        check('forecast_shape_finite:' + str(row['t']), forecast.shape == (3,) and np.isfinite(forecast).all())
        residual = float(np.max(np.abs(stream[row['t']] - forecast)))
        difference = abs(residual - row['max_abs_residual'])
        max_difference = max(max_difference, difference)
        check('residual_and_alarm:' + str(row['t']), difference == 0 and type(row['alarm']) is bool and
              row['alarm'] == (residual > .5))

    def rate(start, end):
        return sum(r['alarm'] for r in rows if start <= r['t'] < end) / (end - start)

    hits = [r['t'] - 384 for r in rows if 384 <= r['t'] < 640 and r['alarm']]
    quiet = [r['t'] - 640 for r in rows if r['t'] >= 640 and not r['alarm']]
    metrics = {
        'step_onset_delay': min(hits) if hits else None,
        'step_first32_alarm_fraction': rate(384, 416),
        'step_late_alarm_fraction': rate(416, 640),
        'step_last32_alarm_fraction': rate(608, 640),
        'step_full_retention': rate(384, 640),
        'post_return_alarm_points': sum(r['alarm'] for r in rows if r['t'] >= 640),
        'post_return_first_quiet_point_delay': min(quiet) if quiet else None,
    }
    for key, value in metrics.items():
        check('reported_metric:' + key, report[key] == value)
    finite = all(math.isfinite(r['max_abs_residual']) and all(math.isfinite(v) for v in r['forecast']) for r in rows)
    gate = (finite and report['all_forecasts_finite'] is True and report['max_repeat_abs_difference'] <= 1e-5 and
            report['median_batch_latency_seconds'] < 5 and report['peak_allocated_gib'] < 20)
    check('operational_gate_arithmetic', gate == report['feasibility_pass'] and
          report['forecast_shape'] == [3, 1] and report['quantile_shape'] == [3, 1, 9] and report['device'] == 'NVIDIA A10G')
    numeric_fields = ['max_repeat_abs_difference', 'median_batch_latency_seconds', 'peak_allocated_gib',
                      'runtime_seconds', 'model_initialization_seconds', 'inference_and_bookkeeping_seconds']
    check('finite_reported_runtime_values', all(math.isfinite(report[k]) and report[k] >= 0 for k in numeric_fields))
    check('mode_timeout_not_exceeded', report['runtime_seconds'] < 1500)
    check('timing_components_fit_total', report['model_initialization_seconds'] +
          report['inference_and_bookkeeping_seconds'] <= report['runtime_seconds'] + 1e-6)
    passed = all(check['passed'] for check in checks)
    return {
        'status': 'PARTIAL_VERIFIED_NEW3_ONLY' if passed else 'FAIL',
        'reviewed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'overall_010_qualification': 'PENDING',
        'reviewer': 'oracle_contract, independent of 010 worker author',
        'method': 'Independent stdlib/NumPy reconstruction of fixed inputs, residuals, alarms and summary accounting. No worker or model import.',
        'source_review_receipt_sha256': sha(source_review),
        'runtime_freeze_sha256': sha(source / 'RUNTIME_FREEZE.json'),
        'worker_sha256': report['runner_sha256'],
        'modes': {
            'new3': {
                'status': 'PASS_BOUNDED_OPERATIONAL_QUALIFICATION' if passed else 'FAIL',
                'results_receipt_sha256': sha(data / 'QUALIFICATION_RECEIPT.json'),
                'probe_rows_sha256': sha(data / 'development_probe.jsonl'),
                'rows_verified': len(rows),
                'maximum_independently_recomputed_residual_difference': max_difference,
                'metrics_recomputed_from_rows': metrics,
                'extra_descriptive_counts': {
                    'pre_step_clean_alarms': sum(r['alarm'] for r in rows if r['t'] < 384),
                    'pre_step_clean_points': 128, 'attack_alarm_points': len(hits), 'attack_points': 256,
                    'late_attack_alarm_points': sum(r['alarm'] for r in rows if 416 <= r['t'] < 640),
                    'late_attack_points': 224, 'post_return_points': 128},
                'reported_operational_metrics': {k: report[k] for k in numeric_fields + ['forecast_shape', 'quantile_shape']},
                'operational_metric_evidence_boundary': 'Individual latency samples, repeated forecast arrays, quantile arrays and allocator traces were not archived. Their reported gate arithmetic/source binding is checked; measurements are not independently regenerated from probe rows.',
                'interpretation': 'Actual pinned TimesFM3 is operational on the recorded A10G. The fixed step alarms initially but only at 3 of 256 attack-period points and none of 224 late points. This is a single synthetic development stream, not a successful defense or HAI efficacy test.'},
            'original25': {'status': 'PENDING', 'reason': 'This archived audit version covers only the released new3 results.'},
            'calibration': {'status': 'PENDING', 'reason': 'This archived audit version covers only the released new3 results.'}},
        'checks_total': len(checks), 'checks_passed': sum(c['passed'] for c in checks),
        'checks_failed': sum(not c['passed'] for c in checks), 'checks': checks,
        'setup_receipts': {name: sha(cloud / name) for name in [
            'ASSET_RECEIPT_MODELS.json', 'RUNTIME_CONTROLS_CLOUD.json', 'DATA_ACCESSIBILITY.json',
            'PIP_FREEZE.txt', 'SETUP_EXIT.txt', 'NEW3_EXIT.txt']},
        'scope_limits': ['The 512 probe positions are not independent attack episodes.',
                         'The 22 source/synthetic/mock controls are not model outcomes.',
                         'Asset receipt identities were checked; cloud weight bytes were not downloaded or independently rehashed.',
                         'Original25/calibration remain pending in this audit version. A1 preserves requested 1/effective 2 calibration epochs.',
                         'Full campaign cost and stopped-host verification belong to root closeout.'],
        'new_defense_validated': False, 'novelty_established': False,
        'reviewer_model_calls': 0, 'reviewer_cloud_calls': 0,
        'frozen_source_or_raw_results_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cloud-results', type=Path, required=True)
    parser.add_argument('--source-review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.source, args.cloud_results, args.source_review)
    except Exception as exc:
        result = {'status': 'FAIL', 'overall_010_qualification': 'PENDING',
                  'error_type': type(exc).__name__, 'error': str(exc),
                  'scope': 'Audit incomplete; no PASS inferred from missing or malformed input.'}
    result.update(audit_source_sha256=sha(__file__), audit_source_archived_after_model_runs=True,
                  audit_source_frozen_before_model_runs=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'checks_total', 'checks_failed') if k in result}))
    raise SystemExit(0 if result['status'] == 'PARTIAL_VERIFIED_NEW3_ONLY' else 1)


if __name__ == '__main__':
    main()
