"""Synthetic artifact controls; no model calls and no real experiment results."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    runner = ROOT / 'postrun/audit_qualification.py'
    freeze = json.loads((ROOT / 'RUNTIME_FREEZE.json').read_text())
    checks = {}
    with tempfile.TemporaryDirectory(prefix='SYNTHETIC_AUDITOR_', dir=args.cache) as directory:
        base = Path(directory); mode = base / 'new3'; mode.mkdir()
        x = np.random.RandomState(0).normal(0, .05, (768, 3)).astype(np.float32); x[384:640] += 2
        rows = [{'t': t, 'forecast': [0., 0., 0.], 'max_abs_residual': float(np.max(np.abs(x[t]))), 'alarm': bool(np.max(np.abs(x[t])) > .5)} for t in range(256, 768)]
        raw = mode / 'development_probe.jsonl'
        raw.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        receipt = {'synthetic_fixture_only': True, 'mode': 'new3', 'runner_sha256': freeze['files']['code/gpu_qualification.py'], 'qualification_gate': 'PASS', 'heldout_hai_scored': False, 'artifacts': {'development_probe.jsonl': hashlib.sha256(raw.read_bytes()).hexdigest()}, 'step_onset_delay': 0, 'step_full_retention': 1., 'step_first32_alarm_fraction': 1., 'step_last32_alarm_fraction': 1., 'step_late_alarm_fraction': 1., 'post_return_alarm_points': 0, 'all_forecasts_finite': True, 'max_repeat_abs_difference': 0., 'median_batch_latency_seconds': .1, 'peak_allocated_gib': 1.}
        record = mode / 'QUALIFICATION_RECEIPT.json'
        def audit(tag, with_mode=True, original25=None):
            record.write_text(json.dumps(receipt), encoding='utf-8')
            output = base / (tag + '.json')
            cmd = [sys.executable, str(runner), '--cache', str(args.cache), '--output', str(output)]
            if with_mode:
                cmd += ['--new3', str(mode)]
            if original25 is not None:
                cmd += ['--original25', str(original25)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return json.loads(output.read_text())
        r = audit('missing', False)
        checks['missing_modes_never_pass'] = r['disposition'] == 'PENDING' and len(r['missing_modes']) == 3
        r = audit('valid_subset')
        checks['valid_synthetic_subset_accounted'] = r['disposition'] == 'PENDING' and not r['failures'] and r['checks_total'] > 0
        receipt['step_full_retention'] = .5
        r = audit('incorrect_metric')
        checks['incorrect_metric_held'] = r['disposition'] == 'HOLD' and 'new3_all_reported_probe_metrics' in r['failures']
        receipt['step_full_retention'] = 1.; receipt['runner_sha256'] = '0' * 64
        r = audit('wrong_worker')
        checks['wrong_worker_held'] = r['disposition'] == 'HOLD' and 'new3_runner_identity' in r['failures']
        receipt['runner_sha256'] = freeze['files']['code/gpu_qualification.py']
        (mode / 'FAILED_QUALIFICATION_RECEIPT.json').write_text('{}')
        r = audit('stale_pass')
        checks['stale_success_with_failure_held'] = r['disposition'] == 'HOLD' and 'new3_no_failed_receipt_same_attempt' in r['failures']
        (mode / 'FAILED_QUALIFICATION_RECEIPT.json').unlink()
        # A full synthetic source execution validates the independent 8,000-action
        # arithmetic auditor without loading the original model's weights.
        sys.path.insert(0, str(ROOT / 'code'))
        import gpu_qualification as worker
        class FakeModel:
            @classmethod
            def from_pretrained(cls, *a, **k): return cls()
            def compile(self, *a, **k): pass
            def forecast(self, horizon, inputs): return np.array([[np.asarray(x)[-1]] for x in inputs], dtype=np.float32), None
        previous_module = sys.modules.get('timesfm')
        previous_verify = worker.verify_model
        sys.modules['timesfm'] = types.SimpleNamespace(TimesFM_2p5_200M_torch=FakeModel, ForecastConfig=lambda **k: k)
        worker.verify_model = lambda *a: Path('synthetic_no_weights')
        original_dir = base / 'original25'; original_dir.mkdir()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                original = worker.original25(args.cache, original_dir, {})
        finally:
            worker.verify_model = previous_verify
            if previous_module is None: sys.modules.pop('timesfm', None)
            else: sys.modules['timesfm'] = previous_module
        original.update({'synthetic_fixture_only': True, 'mode': 'original25', 'runner_sha256': freeze['files']['code/gpu_qualification.py'], 'qualification_gate': 'PASS', 'heldout_hai_scored': False, 'artifacts': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in original_dir.iterdir()}})
        original_receipt = original_dir / 'QUALIFICATION_RECEIPT.json'
        original_receipt.write_text(json.dumps(original), encoding='utf-8')
        r = audit('original_arithmetic', original25=original_dir)
        checks['full_original_mock_arithmetic_audited'] = r['disposition'] == 'PENDING' and not r['failures'] and r['checks'].get('original_every_intervention_arithmetic') and r['checks'].get('original_every_residual_score_alarm')
        checks['float32_source_predictions_preserved'] = r['checks'].get('original_prediction_values_exact_float32') is True
        # Float32 multiplication must occur before float64 observation addition.
        # Deliberately inject the old float64 replay into a real mock blend row.
        actions_path = original_dir / 'interventions.jsonl'
        original_actions_bytes = actions_path.read_bytes()
        action_rows = [json.loads(line) for line in original_actions_bytes.splitlines()]
        changed = False
        for action in action_rows:
            if action['action'] != 'blend': continue
            wrong = .8 * np.asarray(action['prediction'], dtype=np.float64) + .2 * np.asarray(action['observation'], dtype=np.float64)
            if not np.allclose(wrong, action['admitted'], atol=1e-10, rtol=1e-10):
                action['admitted'] = wrong.tolist(); changed = True; break
        checks['fixture_exposes_original_float64_rounding_bug'] = changed
        actions_path.write_bytes((''.join(json.dumps(row) + '\n' for row in action_rows)).encode())
        original['artifacts']['interventions.jsonl'] = hashlib.sha256(actions_path.read_bytes()).hexdigest()
        original_receipt.write_text(json.dumps(original), encoding='utf-8')
        r = audit('float64_admission_corruption', original25=original_dir)
        checks['float64_blend_corruption_held_at_original_tolerance'] = r['disposition'] == 'HOLD' and 'original_every_intervention_arithmetic' in r['failures']
        actions_path.write_bytes(original_actions_bytes)
        original['artifacts']['interventions.jsonl'] = hashlib.sha256(original_actions_bytes).hexdigest()
        # Direct fixture distinguishes source expressions even when their
        # float64 observation-term difference is below the audit tolerance.
        import importlib.util
        spec = importlib.util.spec_from_file_location('auditor_synthetic_test', runner)
        auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
        pred = np.array([.12345679, 1.2345679, -3.1415927], dtype=np.float32)
        obs = np.array([1.234567890123, -6.712345678901, 8.123456789012], dtype=np.float64)
        historical = .8 * pred + (1 - .8) * obs
        deployable = .8 * pred + .2 * obs
        checks['source_policy_weights_and_operator_order_exact'] = not np.array_equal(historical, deployable) and np.array_equal(auditor.replay_admitted('historical_oracle_blend', 'blend', obs, pred), historical) and np.array_equal(auditor.replay_admitted('alarm_only_blend', 'blend', obs, pred), deployable)
        original['comparisons'][0]['detected_episodes'] = -1
        original_receipt.write_text(json.dumps(original), encoding='utf-8')
        r = audit('original_wrong_count', original25=original_dir)
        checks['original_wrong_numerator_held'] = r['disposition'] == 'HOLD' and 'original_comparison_historical_oracle_blend' in r['failures']
    result = {'synthetic_artifacts_only': True, 'checks': checks, 'all_pass': all(checks.values()), 'auditor_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(), 'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'model_inference_calls': 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result)); assert result['all_pass']


if __name__ == '__main__':
    main()
