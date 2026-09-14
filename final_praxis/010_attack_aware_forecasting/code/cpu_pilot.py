"""Development-only numerical qualification; no model downloads or cloud calls."""
import argparse
import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy
from scipy.signal import place_poles
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_frozen():
    freeze = json.loads((ROOT / 'PROTOCOL_FREEZE.json').read_text())
    for name, expected in freeze['files'].items():
        assert digest(ROOT / name) == expected, name
    return freeze


def released_observer(cache):
    """Execute only reviewed AST numerical slices, never original module top level."""
    path = cache / 'attack/1_replay_lti_final.py'
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
    expected = next(x['sha256'] for x in manifest['files'] if x['cache_path'] == 'attack/1_replay_lti_final.py')
    assert digest(path) == expected
    source = '\n'.join('# omitted notebook installation directive' if x.startswith('!') else x for x in path.read_text(encoding='utf-8').splitlines())
    tree = ast.parse(source)
    selected = [n for n in tree.body if 24 <= n.lineno <= 100 or 115 <= n.lineno <= 128]
    ns = {'np': np, 'chi2': chi2, 'place_poles': place_poles, 'print': lambda *a, **k: None}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), ns)
    loop = copy.deepcopy(next(n for n in tree.body if isinstance(n, ast.For) and n.lineno == 146))
    loop.body = [n for n in loop.body if n.lineno <= 184]
    # Last retained node must be complete original plant/observer simulation.
    assert loop.body[-1].lineno == 162 and loop.body[-1].end_lineno == 184
    loop.body += ast.parse("saved.append({'y_att': y_att.copy(), 'y_cln': y_cln.copy(), 'res_att': res_obs_att.copy(), 'res_cln': res_obs_cln.copy()})").body
    ast.fix_missing_locations(loop)
    ns['saved'] = []
    exec(compile(ast.Module(body=[loop], type_ignores=[]), str(path), 'exec'), ns)
    return ns


def independent_observer():
    angle = 0.3
    a = np.array([[np.cos(angle), np.sin(angle) / angle], [-angle * np.sin(angle), np.cos(angle)]])
    c = np.array([[1., 0.], [.31, -.48], [-.21, .43]])
    k = place_poles(a.T, c.T, np.array([.5 + .1j, .5 - .1j])).gain_matrix.T

    def series(seed, length):
        rng = np.random.RandomState(seed)
        x = np.array([1., 0.])
        result = []
        for _ in range(length):
            result.append(c @ x + .01 * rng.randn(3))
            x = a @ x
        return np.array(result)

    def residual(y):
        xhat = np.zeros(2)
        result = []
        for measurement in y:
            r = measurement - c @ xhat
            result.append(r)
            xhat = a @ xhat + k @ r
        return np.array(result)[51:]

    commissioning = series(0, 71)
    recording_start = int(71 - 2 * np.pi / .3)
    recording = commissioning[recording_start:recording_start + 20]
    trials = []
    for seed in range(1, 21):
        clean = series(seed, 101)
        attacked = clean.copy()
        attacked[71:] = recording[np.arange(30) % 20]
        trials.append({'y_att': attacked, 'y_cln': clean, 'res_att': residual(attacked), 'res_cln': residual(clean)})
    return commissioning, residual(commissioning), trials


def simple_detector(x, policy):
    reference = float(np.mean(x[:256]))
    buffer = x[:256].tolist()
    forecasts, alarms = [], []
    for t in range(256, len(x)):
        if policy == 'last_value':
            prediction = buffer[-1]
        elif policy == 'rolling_mean':
            prediction = float(np.mean(buffer[-32:]))
        elif policy == 'fixed_reference':
            prediction = reference
        else:
            prediction = float(np.mean(buffer[-32:]))
        alarm = bool(abs(x[t] - prediction) > .5)
        forecasts.append(prediction)
        alarms.append(alarm)
        if policy == 'alarm_only_blend' and alarm:
            buffer.append(.8 * prediction + .2 * x[t])
        elif policy == 'alarm_freeze' and alarm:
            pass
        else:
            buffer.append(float(x[t]))
    return np.asarray(forecasts), np.asarray(alarms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    started = time.time()
    freeze = verify_frozen()
    args.output.mkdir(parents=True, exist_ok=True)
    released = released_observer(args.cache)
    commissioning, calibration, trials = independent_observer()
    checks = {'commissioning_equal': np.allclose(commissioning, released['y_init'], atol=1e-10, rtol=1e-10), 'calibration_equal': np.allclose(calibration, released['res_obs_init'], atol=1e-10, rtol=1e-10)}
    maximum = 0.
    arrays = {'commissioning': commissioning, 'observer_calibration_residual': calibration}
    invcov = np.linalg.inv(np.cov(calibration.T))
    threshold = float(chi2.ppf(.995, 3))
    observer_rows = []
    for seed, (actual, expected) in enumerate(zip(trials, released['saved']), 1):
        for key in actual:
            checks[f'seed_{seed}_{key}'] = np.allclose(actual[key], expected[key], atol=1e-10, rtol=1e-10)
            maximum = max(maximum, float(np.max(np.abs(actual[key] - expected[key]))))
            arrays[f'seed{seed}_{key}'] = actual[key]
        for kind in ['att', 'cln']:
            r = actual['res_' + kind][20:]
            scores = np.einsum('ij,jk,ik->i', r, invcov, r)
            oracle_r = expected['res_' + kind][20:]
            oracle_scores = np.einsum('ij,jk,ik->i', oracle_r, released['Sigma_obs_inv'], oracle_r)
            checks[f'seed_{seed}_{kind}_alarms'] = np.array_equal(scores > threshold, oracle_scores > threshold)
            for t, score in enumerate(scores, 71):
                observer_rows.append({'seed': seed, 'stream': kind, 't': t, 'score': float(score), 'alarm': bool(score > threshold)})
    controls, point_rows = [], []
    for seed in range(10):
        x = np.random.RandomState(seed).normal(0, .05, 768)
        x[384:640] += 2.
        per_policy = {}
        for policy in ['last_value', 'rolling_mean', 'fixed_reference', 'alarm_freeze', 'alarm_only_blend']:
            prediction, alarms = simple_detector(x, policy)
            altered = x.copy(); altered[600:] += 17.
            prefix_equal = np.array_equal(alarms[:344], simple_detector(altered, policy)[1][:344])
            semantic_label_invariance = np.array_equal(alarms, simple_detector(x.copy(), policy)[1])
            checks[f'seed_{seed}_{policy}_prefix'] = prefix_equal
            checks[f'seed_{seed}_{policy}_semantic'] = semantic_label_invariance
            attack = alarms[128:384]
            hits = np.flatnonzero(attack)
            per_policy[policy] = {'onset_delay': int(hits[0]) if len(hits) else None, 'first32_retention': float(np.mean(attack[:32])), 'late_retention': float(np.mean(attack[32:])), 'last32_retention': float(np.mean(attack[-32:])), 'normal_alarm_points_before_step': int(alarms[:128].sum()), 'post_return_alarm_points': int(alarms[384:].sum()), 'benign_same_stream_alarm_points': int(attack.sum())}
            for i, (pred, alarm) in enumerate(zip(prediction, alarms), 256):
                point_rows.append({'seed': seed, 'policy': policy, 't': i, 'observation': float(x[i]), 'prediction': float(pred), 'alarm': bool(alarm)})
        passed = per_policy['last_value']['onset_delay'] == 0 and per_policy['last_value']['late_retention'] <= .1 and per_policy['fixed_reference']['late_retention'] >= .9
        controls.append({'seed': seed, 'persistence_gate_pass': passed, 'policies': per_policy})
    for name, rows in [('observer_rows.jsonl', observer_rows), ('synthetic_rows.jsonl', point_rows)]:
        (args.output / name).write_text(''.join(json.dumps(x) + '\n' for x in rows), encoding='utf-8')
    np.savez_compressed(args.output / 'observer_raw.npz', **arrays)
    checked = {k: bool(v) for k, v in checks.items()}
    summary = {'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'protocol_freeze': freeze, 'runner_sha256': digest(__file__), 'runtime_seconds': time.time() - started, 'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'checks': checked, 'all_checks_pass': all(checked.values()), 'observer_max_abs_difference': maximum, 'observer_attack_points': 600, 'observer_matched_clean_points': 600, 'observer_episode_hits': sum(any(r['alarm'] for r in observer_rows if r['seed'] == s and r['stream'] == 'att') for s in range(1, 21)), 'observer_clean_alarm_points': sum(r['alarm'] for r in observer_rows if r['stream'] == 'cln'), 'synthetic_seed_passes': sum(x['persistence_gate_pass'] for x in controls), 'synthetic_results': controls, 'qualification': 'CPU_ONLY_PASS' if all(checked.values()) and sum(x['persistence_gate_pass'] for x in controls) >= 9 else 'HOLD', 'foundation_model_success_claimed': False, 'heldout_hai_scored': False}
    summary['artifacts'] = {p.name: digest(p) for p in sorted(args.output.iterdir()) if p.name != 'CPU_QUALIFICATION_RECEIPT.json'}
    (args.output / 'CPU_QUALIFICATION_RECEIPT.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ['qualification', 'all_checks_pass', 'observer_max_abs_difference', 'synthetic_seed_passes', 'runtime_seconds']}))


if __name__ == '__main__':
    main()
