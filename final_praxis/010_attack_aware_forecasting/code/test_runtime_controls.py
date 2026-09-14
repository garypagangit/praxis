"""Synthetic/source integration controls only; no pretrained weights or inference."""
import argparse
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types

import numpy as np
import torch

from gpu_qualification import check_assets, load_granite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check_assets(args.cache)
    checks = {}
    ns = {'np': np, 'torch': torch}
    path = args.cache / 'granite/notebooks/hfdemo/adaptive_conformal_tsad/utils.py'
    fn = next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n, ast.FunctionDef) and n.name == 'create_rolling_forecast_contexts')
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), ns)
    original = np.arange(256, dtype=float)
    changed = original.copy(); changed[170:] += 10000
    for mode in ['fixed', 'expanding']:
        windows = ns['create_rolling_forecast_contexts'](original, 90, 15, 128, mode, return_type='numpy')
        alternate = ns['create_rolling_forecast_contexts'](changed, 90, 15, 128, mode, return_type='numpy')
        checks[mode + '_origins'] = len(windows['end_idx']) == 167 and windows['end_idx'][0] == 89
        checks[mode + '_all_past_only'] = all(ctx[-1] == end and ctx.max() == end for ctx, end in zip(windows['past_values'], windows['end_idx']))
        checks[mode + '_future_ground_truth_alignment'] = all(np.array_equal(y[:n], np.arange(end + 1, end + n + 1)) for y, n, end in zip(windows['future_values'], windows['n_gt_valid'], windows['end_idx']))
        checks[mode + '_future_suffix_no_prefix_context_change'] = all(np.array_equal(a, b) for a, b, end in zip(windows['past_values'], alternate['past_values'], windows['end_idx']) if end < 170)
        checks[mode + '_all_future_missing_last'] = np.isnan(windows['future_values'][-1]).all()
    w1 = load_granite(args.cache)
    values = np.zeros((160, 3, 1))
    for row in range(160):
        values[row, :, 0] = np.arange(row, row + 3)
    aligned = w1.PostHocProbabilisticProcessor().forecast_horizon_aggregation(values, None)
    checks['horizon_alignment_matches_timestamp'] = all(np.array_equal(aligned[i, :min(3, i + 1), 0], np.full(min(3, i + 1), i)) for i in range(160))
    # The same known-length score stream with changed future suffix must preserve scored prefix.
    rng = np.random.RandomState(42)
    scores = rng.normal(size=(160, 1, 1)); future = scores.copy(); future[140:] += 100.
    kwargs = dict(significance_level=.1, forecast_steps=1, n_epochs=1, n_batch_update=10, prior_past_weights_value='proximity', aggregation_forecast_horizon='Cauchy', aggregation_features='Cauchy')
    torch.manual_seed(42)
    p1 = w1.get_forecast_conformal_adaptive_online_score({'y_pred': np.zeros_like(scores), 'y_true': scores}, **kwargs)
    torch.manual_seed(42)
    p2 = w1.get_forecast_conformal_adaptive_online_score({'y_pred': np.zeros_like(scores), 'y_true': future}, **kwargs)
    checks['w1acas_future_suffix_prefix_score_invariance'] = np.allclose(p1[20:140], p2[20:140], rtol=1e-10, atol=1e-10)
    checks['w1acas_synthetic_pvalues_finite'] = np.isfinite(p1).all()
    checks['w1acas_synthetic_pvalues_bounds'] = np.all((p1 >= 0) & (p1 <= 1))
    # Only import package definitions; never instantiate/load a model.
    sys.path.insert(0, str(args.cache / 'timesfm_full/src'))
    import timesfm
    from timesfm3 import TimesFM3Evaluator, ModelConfig
    checks['official_timesfm25_api_imports'] = hasattr(timesfm, 'TimesFM_2p5_200M_torch')
    checks['official_timesfm3_api_imports'] = callable(TimesFM3Evaluator) and ModelConfig(device='cuda').device == 'cuda'
    # Synthetic API fixture exercises the full original source slicing/bookkeeping;
    # its made-up forecasts are discarded and are never a model efficacy result.
    import gpu_qualification as worker
    real_module = sys.modules['timesfm']
    real_verify = worker.verify_model
    class FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()
        def compile(self, *args, **kwargs):
            pass
        def forecast(self, horizon, inputs):
            return np.asarray([[np.asarray(x)[-1]] for x in inputs]), None
    sys.modules['timesfm'] = types.SimpleNamespace(TimesFM_2p5_200M_torch=FakeModel, ForecastConfig=lambda **k: k)
    worker.verify_model = lambda *args: Path('synthetic_no_weights')
    try:
        with tempfile.TemporaryDirectory(prefix='runtime_fixture_', dir=args.cache) as directory:
            with contextlib.redirect_stdout(io.StringIO()):
                synthetic = worker.original25(args.cache, Path(directory), {})
            actions = [json.loads(line) for line in (Path(directory) / 'interventions.jsonl').read_text().splitlines()]
            checks['mock_source_execution_accounting'] = synthetic['implementation_gate_pass'] and synthetic['intervention_steps'] == 8000
            checks['mock_no_oracle_gate_on_deployable'] = all(r['oracle_onset_eligible'] is None for r in actions if r['policy'] != 'historical_oracle_blend')
            checks['mock_original_gate_preserved'] = all(r['oracle_onset_eligible'] == (r['t'] >= 71) for r in actions if r['policy'] == 'historical_oracle_blend' and r['stream'] == 'att')
            checks['mock_observed_admission_exact'] = all(r['admitted'] == r['observation'] for r in actions if r['action'] == 'observed')
            checks['mock_blend_admission_exact'] = all(np.allclose(r['admitted'], .8 * np.asarray(r['prediction']) + .2 * np.asarray(r['observation']), atol=1e-12, rtol=1e-12) for r in actions if r['action'] == 'blend')
            checks['mock_frozen_admission_absent'] = all(r['admitted'] is None for r in actions if r['action'] == 'freeze')
    finally:
        sys.modules['timesfm'] = real_module
        worker.verify_model = real_verify
    result = {'checks': {k: bool(v) for k, v in checks.items()}, 'all_pass': all(checks.values()), 'controls': len(checks), 'pretrained_model_loads': 0, 'inference_calls': 0, 'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'runner_sha256': hashlib.sha256(Path(__file__).with_name('gpu_qualification.py').read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    assert result['all_pass']


if __name__ == '__main__':
    main()
