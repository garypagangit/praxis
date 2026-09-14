"""Pinned original-model reproduction and TimesFM3 development feasibility.

Run each mode in a fresh process. No arbitrary remote model code, no cloud API.
All model weights must already be downloaded by prepare_assets.py --models.
"""
import argparse
import ast
import copy
import datetime
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
import types
import traceback
import zipfile

import numpy as np
import pandas as pd
import torch
from scipy.signal import place_poles
from scipy.stats import chi2

from cpu_pilot import digest, verify_frozen

ROOT = Path(__file__).resolve().parents[1]


def check_assets(cache):
    m = json.loads((ROOT / 'RUNTIME_ASSET_MANIFEST.json').read_text())
    for x in m['files']:
        assert digest(cache / x['cache_path']) == x['sha256'], x['cache_path']
    with zipfile.ZipFile(cache / 'timesfm_source.zip') as archive:
        expected_python = set()
        for entry in archive.infolist():
            parts = Path(entry.filename).parts[1:]
            if parts and not entry.is_dir():
                extracted = cache / 'timesfm_full' / Path(*parts)
                assert extracted.read_bytes() == archive.read(entry), str(extracted)
                if extracted.suffix == '.py':
                    expected_python.add(extracted.relative_to(cache / 'timesfm_full').as_posix())
        actual_python = {p.relative_to(cache / 'timesfm_full').as_posix() for p in (cache / 'timesfm_full').rglob('*.py')}
        assert actual_python == expected_python, 'Unexpected/stale Python files in extracted source'
    return m


def verify_model(cache, repo, manifest):
    info = manifest['models'][repo]
    directory = cache / 'models' / repo.split('/')[-1]
    for item in info['files']:
        if item['rfilename'].startswith('.'):
            continue
        if 'lfs' in item:
            assert digest(directory / item['rfilename']) == item['lfs']['sha256']
        else:
            data = (directory / item['rfilename']).read_bytes()
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert blob == item['blobId'], item['rfilename']
    return directory


def original25(cache, out, manifest):
    sys.path.insert(0, str(cache / 'timesfm_full/src'))
    import timesfm
    weights = verify_model(cache, 'google/timesfm-2.5-200m-pytorch', manifest)
    load_started = time.perf_counter()
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(str(weights), local_files_only=True)
    model.compile(timesfm.ForecastConfig(max_context=512, max_horizon=1, normalize_inputs=True))
    load_seconds = time.perf_counter() - load_started
    inference_started = time.perf_counter()
    path = cache / 'attack/1_replay_lti_final.py'
    source = '\n'.join('# omitted install directive' if x.startswith('!') else x for x in path.read_text(encoding='utf-8').splitlines())
    tree = ast.parse(source)
    selected = [copy.deepcopy(n) for n in tree.body if 24 <= n.lineno <= 239]
    loop = next(n for n in selected if isinstance(n, ast.For) and n.lineno == 146)
    forecast_loop = next(n for n in loop.body if isinstance(n, ast.For) and n.lineno == 191)
    forecast_loop.body += ast.parse("""
interventions.append({'policy': 'historical_oracle_blend', 'seed': trial + 1, 'stream': 'att', 't': t, 'alarm': bool(chi2_now > threshold), 'oracle_onset_eligible': bool(t >= attack_start), 'action': 'blend' if chi2_now > threshold and t >= attack_start else 'observed', 'observation': y_att[t].tolist(), 'prediction': y_hat.tolist(), 'admitted': y_buffer[t].tolist()})
clean_score = res_fm_cln[online_t] @ Sigma_fm_inv @ res_fm_cln[online_t]
interventions.append({'policy': 'historical_oracle_blend', 'seed': trial + 1, 'stream': 'cln', 't': t, 'alarm': bool(clean_score > threshold), 'oracle_onset_eligible': False, 'action': 'observed', 'observation': y_cln[t].tolist(), 'prediction': pf_cln[:, 0].tolist(), 'admitted': y_cln[t].tolist()})
""").body
    loop.body += ast.parse("saved_trials.append({'y_att': y_att.copy(), 'y_cln': y_cln.copy(), 'res_fm_att': res_fm_att.copy(), 'res_fm_cln': res_fm_cln.copy(), 'buffer': y_buffer.copy()})").body
    ast.fix_missing_locations(loop)
    ns = {'np': np, 'chi2': chi2, 'place_poles': place_poles, 'model': model, 'saved_trials': [], 'interventions': []}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), ns)
    rows = []
    arrays = {'fm_calibration_residuals': ns['res_fm_init'], 'fm_covariance': ns['Sigma_fm']}
    for seed, trial in enumerate(ns['saved_trials'], 1):
        for key, value in trial.items():
            arrays[f'seed{seed}_{key}'] = value
        for kind in ['att', 'cln']:
            scores = ns[f'chi2_fm_{kind}_trials'][seed - 1]
            for t, score in enumerate(scores, 71):
                rows.append({'policy': 'historical_oracle_blend', 'seed': seed, 'stream': kind, 't': t, 'score': float(score), 'alarm': bool(score > ns['threshold'])})
    # Same trials/threshold/covariance; all deployable updates depend only on current alarm.
    for policy in ['rolling', 'alarm_only_blend', 'literal_freeze']:
        for seed, trial in enumerate(ns['saved_trials'], 1):
            for kind in ['att', 'cln']:
                y = trial['y_' + kind]
                context = [row.copy() for row in y[:51]]
                for t in range(51, 101):
                    batch = np.asarray(context[-50:])
                    pf, _ = model.forecast(horizon=1, inputs=[batch[:, c] for c in range(3)])
                    prediction = pf[:, 0]
                    residual = y[t] - prediction
                    score = float(residual @ ns['Sigma_fm_inv'] @ residual)
                    alarm = bool(score > ns['threshold'])
                    assert np.isfinite(score)
                    if t >= 71:
                        rows.append({'policy': policy, 'seed': seed, 'stream': kind, 't': t, 'score': score, 'alarm': alarm})
                    if policy == 'literal_freeze' and alarm:
                        action, admitted = 'freeze', None
                    elif policy == 'alarm_only_blend' and alarm:
                        action, admitted = 'blend', .8 * prediction + .2 * y[t]
                        context.append(admitted)
                    else:
                        action, admitted = 'observed', y[t].copy()
                        context.append(admitted)
                    ns['interventions'].append({'policy': policy, 'seed': seed, 'stream': kind, 't': t, 'alarm': alarm, 'oracle_onset_eligible': None, 'action': action, 'observation': y[t].tolist(), 'prediction': prediction.tolist(), 'admitted': None if admitted is None else admitted.tolist()})
            print(f'{policy} seed {seed}/20 complete', flush=True)
    (out / 'pointwise.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    (out / 'interventions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in ns['interventions']), encoding='utf-8')
    np.savez_compressed(out / 'historical_raw.npz', **arrays)
    comparisons = []
    for policy in ['historical_oracle_blend', 'rolling', 'alarm_only_blend', 'literal_freeze']:
        attack = [r for r in rows if r['policy'] == policy and r['stream'] == 'att']
        clean = [r for r in rows if r['policy'] == policy and r['stream'] == 'cln']
        assert len(attack) == len(clean) == 600
        comparisons.append({'policy': policy, 'attack_points': 600, 'clean_points': 600, 'detected_episodes': sum(any(r['alarm'] for r in attack if r['seed'] == s) for s in range(1, 21)), 'episode_denominator': 20, 'alarm_attack_points': sum(r['alarm'] for r in attack), 'alarm_clean_points': sum(r['alarm'] for r in clean)})
    finite_covariance = bool(np.isfinite(ns['Sigma_fm']).all())
    finite_statistics = all(np.isfinite(r['score']) for r in rows) and all(np.isfinite(a).all() for a in arrays.values())
    unique_complete_rows = len({(r['policy'], r['seed'], r['stream'], r['t']) for r in rows}) == len(rows) == 4800
    unique_complete_interventions = len({(r['policy'], r['seed'], r['stream'], r['t']) for r in ns['interventions']}) == len(ns['interventions']) == 8000
    return {'implementation_complete': True, 'implementation_gate_pass': bool(finite_covariance and finite_statistics and unique_complete_rows and unique_complete_interventions), 'model_initialization_seconds': load_seconds, 'inference_and_bookkeeping_seconds_including_lazy_jit': time.perf_counter() - inference_started, 'comparisons': comparisons, 'historical_oracle_attack_onset': True, 'covariance_finite': finite_covariance, 'historical_statistics_finite': bool(finite_statistics), 'unique_complete_rows': unique_complete_rows, 'unique_complete_interventions': unique_complete_interventions, 'intervention_steps': len(ns['interventions']), 'novel_method_tested': False}


def new3(cache, out, manifest):
    sys.path.insert(0, str(cache / 'timesfm_full/src'))
    from timesfm3 import TimesFM3Evaluator, ModelConfig
    weights = verify_model(cache, 'google/timesfm-3.0-pytorch', manifest)
    config = ModelConfig(checkpoint_path=str(weights / 'model.safetensors'), per_core_batch_size=1, device='cuda', local_files_only=True)
    load_started = time.perf_counter()
    model = TimesFM3Evaluator(config)
    load_seconds = time.perf_counter() - load_started
    inference_started = time.perf_counter()
    t = np.arange(128, dtype=np.float32)
    context = np.stack([np.sin(t / 10), np.cos(t / 10), np.sin(t / 10) * .5]).astype(np.float32)
    options = dict(horizon=1, return_quantiles=True, use_symmetric_averaging=False, make_positive=False, sort_quantiles=True, use_znorm=False)
    def predict(ctx):
        return list(model.predict_batch([ctx], **options))[0]
    first = predict(context)
    timing, repeats = [], []
    for _ in range(5):
        torch.cuda.synchronize(); start = time.perf_counter(); result = predict(context); torch.cuda.synchronize()
        assert np.isfinite(result.forecast).all() and np.isfinite(result.quantiles).all(), 'Nonfinite repeated forecast'
        timing.append(time.perf_counter() - start)
        repeats.append(float(np.max(np.abs(result.forecast - first.forecast))))
    assert first.forecast.shape == (3, 1) and first.quantiles.shape == (3, 1, 9)
    # Fixed development-only probe: seed0, noisy step in all3 channels; no threshold tuning.
    x = np.random.RandomState(0).normal(0, .05, (768, 3)).astype(np.float32)
    x[384:640] += 2
    rows = []
    for t in range(256, 768):
        forecast = predict(x[t - 128:t].T).forecast[:, 0]
        residual = np.abs(x[t] - forecast)
        rows.append({'t': t, 'max_abs_residual': float(np.max(residual)), 'alarm': bool(np.max(residual) > .5), 'forecast': forecast.tolist()})
    (out / 'development_probe.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    peak = torch.cuda.max_memory_allocated() / 1024**3
    finite = bool(np.isfinite(first.forecast).all() and np.isfinite(first.quantiles).all() and all(np.isfinite(r['max_abs_residual']) for r in rows))
    feasible = finite and max(repeats) <= 1e-5 and np.median(timing) < 5 and peak < 20
    attack_hits = [r['t'] - 384 for r in rows if 384 <= r['t'] < 640 and r['alarm']]
    quiet_return = [r['t'] - 640 for r in rows if r['t'] >= 640 and not r['alarm']]
    return {'implementation_complete': True, 'feasibility_pass': bool(feasible), 'model_initialization_seconds': load_seconds, 'inference_and_bookkeeping_seconds': time.perf_counter() - inference_started, 'all_forecasts_finite': finite, 'max_repeat_abs_difference': max(repeats), 'median_batch_latency_seconds': float(np.median(timing)), 'peak_allocated_gib': peak, 'forecast_shape': list(first.forecast.shape), 'quantile_shape': list(first.quantiles.shape), 'development_only': True, 'step_onset_delay': min(attack_hits) if attack_hits else None, 'step_first32_alarm_fraction': np.mean([r['alarm'] for r in rows if 384 <= r['t'] < 416]).item(), 'step_late_alarm_fraction': np.mean([r['alarm'] for r in rows if 416 <= r['t'] < 640]).item(), 'step_last32_alarm_fraction': np.mean([r['alarm'] for r in rows if 608 <= r['t'] < 640]).item(), 'step_full_retention': len(attack_hits) / 256, 'post_return_alarm_points': sum(r['alarm'] for r in rows if r['t'] >= 640), 'post_return_first_quiet_point_delay': min(quiet_return) if quiet_return else None, 'novel_defense_efficacy_claimed': False}


def load_granite(cache):
    """Load the original five reviewed toolkit modules, bypassing unrelated package imports."""
    for name, path in [('tsfm_public', cache / 'granite/tsfm_public'), ('tsfm_public.toolkit', cache / 'granite/tsfm_public/toolkit')]:
        package = types.ModuleType(name); package.__path__ = [str(path)]; sys.modules[name] = package
    return importlib.import_module('tsfm_public.toolkit.w1acas')


def calibration(cache, out, manifest):
    from chronos import BaseChronosPipeline
    weights = verify_model(cache, 'amazon/chronos-bolt-small', manifest)
    module = load_granite(cache)
    epoch_probe = module.AdaptiveWeightedConformalScoreWrapper(false_alarm=.01, window_size=115, weighting='uniform', weighting_params={'n_epochs': 1, 'n_batch_update': 10})
    effective_epochs = int(epoch_probe.weighting_params['epochs'])
    assert effective_epochs == 2, 'Pinned source epoch mismatch changed; see amendment A1'
    del epoch_probe
    ns = {'np': np, 'torch': torch}
    path = cache / 'granite/notebooks/hfdemo/adaptive_conformal_tsad/utils.py'
    fn = next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n, ast.FunctionDef) and n.name == 'create_rolling_forecast_contexts')
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), ns)
    path = cache / 'tsbad/Datasets/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv'
    df = pd.read_csv(path)
    assert not df.isna().any().any(), 'Preserve missing rows; original dropna requires amendment if present'
    values = df.iloc[:, 0].to_numpy(dtype=float)
    windows = ns['create_rolling_forecast_contexts'](values, context_length=90, prediction_length=15, max_context=2048, mode='expanding', return_type='torch')
    # Alignment controls use synthetic indices, not model outcomes.
    indexed = ns['create_rolling_forecast_contexts'](np.arange(256), 90, 15, 2048, 'expanding', return_type='numpy')
    assert all(c[-1] == e and np.all(y[:n] == np.arange(e + 1, e + n + 1)) for c, e, y, n in zip(indexed['past_values'], indexed['end_idx'], indexed['future_values'], indexed['n_gt_valid']))
    load_started = time.perf_counter()
    model = BaseChronosPipeline.from_pretrained(str(weights), device_map='cuda', torch_dtype=torch.bfloat16, local_files_only=True)
    load_seconds = time.perf_counter() - load_started
    forecast_started = time.perf_counter()
    batches, repeat_difference = [], None
    for start in range(0, len(windows['past_values']), 128):
        inputs = windows['past_values'][start:start + 128]
        _, forecast = model.predict_quantiles(inputs=inputs, prediction_length=15, quantile_levels=[.5])
        if start == 0:
            _, repeated = model.predict_quantiles(inputs=inputs, prediction_length=15, quantile_levels=[.5])
            repeat_difference = float(torch.max(torch.abs(repeated - forecast)).item())
        batches.append(forecast.cpu().numpy())
        print(f'Chronos forecasts {min(start + 128, len(windows["past_values"]))}/{len(windows["past_values"])}', flush=True)
    y_pred = np.concatenate(batches)[..., None]
    y_true = windows['future_values'].numpy()[..., None]
    assert np.isnan(y_true[-1]).all()
    forecasts = {'y_pred': y_pred[:-1], 'y_true': y_true[:-1]}
    assert np.isfinite(forecasts['y_pred']).all()
    np.savez_compressed(out / 'forecasts.npz', **forecasts)
    forecast_seconds = time.perf_counter() - forecast_started
    calibration_started = time.perf_counter()
    pvalues = module.get_forecast_conformal_adaptive_online_score(forecasts, significance_level=.01, aggregation_forecast_horizon='Cauchy', nonconformity_score='absolute_error', forecast_steps=15, aggregation_features='Cauchy', n_epochs=1, n_batch_update=10, lr=.001, prior_past_weights_value='proximity', return_weights=False, align_forecast=True)
    assert len(pvalues) == len(values) - 90
    aligned = np.ones(len(values)); aligned[90:] = pvalues; aligned[:1007] = 1
    assert np.isfinite(aligned[1007:]).all()
    predictions = aligned < .01
    labels = df['Label'].to_numpy(dtype=int)
    assert set(np.unique(labels)).issubset({0, 1})
    assert np.all((aligned[1007:] >= 0) & (aligned[1007:] <= 1))
    rows = [{'t': i, 'pvalue': float(aligned[i]), 'scored': i >= 1007, 'alarm': bool(predictions[i]), 'label': int(labels[i])} for i in range(len(values))]
    (out / 'pointwise.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    scored = np.arange(len(values)) >= 1007
    return {'implementation_complete': True, 'implementation_gate_pass': repeat_difference <= 1e-5, 'model_initialization_seconds': load_seconds, 'forecast_and_bookkeeping_seconds': forecast_seconds, 'calibration_and_scoring_seconds': time.perf_counter() - calibration_started, 'requested_n_epochs': 1, 'effective_epochs': effective_epochs, 'upstream_epoch_parameter_mismatch_preserved': True, 'dataset_rows': len(values), 'context_rows': 90, 'original_train_boundary': 1007, 'scored_positions': int(scored.sum()), 'assigned_forecast_origins': len(y_pred), 'all_future_missing_origin_excluded': 1, 'forecast_boundary_missing_targets': int(np.isnan(forecasts['y_true']).sum()), 'forecast_values_finite': True, 'scored_pvalues_finite': True, 'max_repeat_abs_difference': repeat_difference, 'true_positive_points': int(np.sum(predictions & (labels == 1) & scored)), 'false_positive_points': int(np.sum(predictions & (labels == 0) & scored)), 'anomaly_points': int(np.sum((labels == 1) & scored)), 'normal_points': int(np.sum((labels == 0) & scored)), 'aggregate_paper_replication_claimed': False, 'dataset_all_development': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['original25', 'new3', 'calibration'], required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError('Use a fresh or empty output directory; preserve prior attempt receipts')
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
    freeze = verify_frozen()
    runtime_freeze = json.loads((ROOT / 'RUNTIME_FREEZE.json').read_text())
    for name, expected in runtime_freeze['files'].items():
        assert digest(ROOT / name) == expected, name
    manifest = check_assets(args.cache)
    assert torch.cuda.is_available(), 'This GPU protocol requires CUDA; do not substitute CPU silently'
    torch.set_num_threads(4); torch.manual_seed(42); np.random.seed(42); random.seed(42)
    torch.cuda.reset_peak_memory_stats()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        result = globals()[args.mode](args.cache, args.output, manifest)
    except Exception as exc:
        failure = {'mode': args.mode, 'qualification_gate': 'HOLD', 'implementation_complete': False, 'exception_type': type(exc).__name__, 'exception_message': str(exc), 'traceback': traceback.format_exc(), 'runtime_seconds': time.time() - started, 'runner_sha256': digest(__file__), 'heldout_hai_scored': False}
        (args.output / 'FAILED_QUALIFICATION_RECEIPT.json').write_text(json.dumps(failure, indent=2) + '\n', encoding='utf-8')
        raise
    gate = result['feasibility_pass'] if args.mode == 'new3' else result['implementation_gate_pass']
    result['qualification_gate'] = 'PASS' if gate else 'HOLD'
    result.update({'mode': args.mode, 'protocol_freeze': freeze, 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'runtime_seconds': time.time() - started, 'python': platform.python_version(), 'torch': torch.__version__, 'numpy': np.__version__, 'device': torch.cuda.get_device_name(), 'peak_allocated_gib': torch.cuda.max_memory_allocated() / 1024**3, 'runner_sha256': digest(__file__), 'heldout_hai_scored': False})
    result['artifacts'] = {p.name: digest(p) for p in args.output.iterdir() if p.name != 'QUALIFICATION_RECEIPT.json'}
    (args.output / 'QUALIFICATION_RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
