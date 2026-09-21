"""Frozen, family-separated retrospective window diagnostic; private predictions."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
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
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def select_review(rows, scores, fraction, known_only=False):
    """Review budget is per run. Labels are never consulted in full-grid selection."""
    selected = np.zeros(len(rows), dtype=bool)
    for run in sorted({r['run_id'] for r in rows}):
        candidates = [i for i, r in enumerate(rows) if r['run_id'] == run
                      and (not known_only or r['label'] >= 0)]
        order = sorted(candidates, key=lambda i: (-float(scores[i]), hashlib.sha256(
            ('window-diagnostic-v1:' + rows[i]['window_id']).encode()).hexdigest()))
        selected[order[:math.ceil(fraction * len(candidates))]] = True
    return selected


def summarize(rows, scores, fraction):
    labels = np.array([r['label'] for r in rows])
    selected = select_review(rows, scores, fraction)
    known_selected = select_review(rows, scores, fraction, known_only=True)
    pos, neg, known = labels == 1, labels == 0, labels >= 0
    tp = int((selected & pos).sum())
    other = int((selected & neg).sum())
    unknown = int((selected & ~known).sum())
    budget = int(selected.sum())
    expected_tp = 0.0
    for run in sorted({r['run_id'] for r in rows}):
        idx = np.array([r['run_id'] == run for r in rows])
        expected_tp += int((idx & pos).sum()) * math.ceil(fraction * int(idx.sum())) / int(idx.sum())
    ktp = int((known_selected & pos).sum())
    kfp = int((known_selected & neg).sum())
    kfn = int(pos.sum()) - ktp
    kprecision = ktp / (ktp + kfp) if ktp + kfp else 0.0
    krecall = ktp / int(pos.sum()) if pos.any() else 0.0
    positive_steps = {s for r in rows for s in r['positive_source_step_ids']}
    selected_steps = {s for i, r in enumerate(rows) if selected[i] for s in r['positive_source_step_ids']}
    return {
        'windows': len(rows), 'positive': int(pos.sum()), 'other_annotated': int(neg.sum()),
        'unknown': int((~known).sum()), 'reviewed': budget, 'selected_target': tp,
        'selected_other': other, 'selected_unknown': unknown,
        'recall': tp / int(pos.sum()) if pos.any() else None,
        'chance_recall': expected_tp / int(pos.sum()) if pos.any() else None,
        'confirmed_positive_yield_lower_bound': tp / budget if budget else 0.0,
        'possible_positive_yield_upper_bound': (tp + unknown) / budget if budget else 0.0,
        'unknown_selected_fraction': unknown / budget if budget else 0.0,
        'known_average_precision': float(average_precision_score(labels[known], scores[known])) if pos.any() and neg.any() else None,
        'known_roc_auc': float(roc_auc_score(labels[known], scores[known])) if pos.any() and neg.any() else None,
        'known_prevalence': float(pos.sum() / known.sum()) if known.any() else None,
        'known_only_budget': {'reviewed': int(known_selected.sum()), 'tp': ktp, 'fp': kfp, 'fn': kfn,
            'precision': kprecision, 'recall': krecall,
            'f1': 2 * ktp / (2 * ktp + kfp + kfn) if 2 * ktp + kfp + kfn else 0.0},
        'represented_source_intervals': len(positive_steps),
        'source_intervals_touched_by_review': len(selected_steps),
        'source_interval_touch_recall': len(selected_steps) / len(positive_steps) if positive_steps else None
    }


def compute_gates(records, protocol):
    def rows(arm, condition):
        return {r['family']: r['metrics'] for r in records if r['arm'] == arm and r['condition'] == condition}
    def macro(arm, condition):
        return float(np.mean([r['recall'] for r in rows(arm, condition).values()]))
    spec = protocol['gates']
    primary = spec['primary_arm']
    clean = rows(primary, 'clean')
    m = macro(primary, 'clean')
    chance = float(np.mean([r['chance_recall'] for r in clean.values()]))
    n_above = sum(r['recall'] > r['chance_recall'] for r in clean.values())
    useful = spec['clean_useful_signal']
    delta = [clean[f]['recall'] - rows('first_lr', 'clean')[f]['recall'] for f in clean]
    pooling = spec['pooling_benefit']
    simple_delta = m - macro('transfer_rule', 'clean')
    loss_delta = m - macro(primary, 'command_absent')
    checks = {
        'clean_useful_signal': {'passed': bool(m >= useful['macro_recall_min'] and m >= useful['chance_multiplier_min'] * chance
            and n_above >= useful['families_above_chance_min']), 'macro_recall': m, 'macro_chance_recall': chance, 'families_above_chance': n_above},
        'pooling_benefit': {'passed': bool(np.mean(delta) >= pooling['macro_recall_delta_min'] and sum(d > 0 for d in delta) >= pooling['families_improved_min']
            and min(delta) >= pooling['worst_family_delta_min']), 'macro_delta': float(np.mean(delta)), 'families_improved': sum(d > 0 for d in delta), 'worst_family_delta': min(delta)},
        'simple_control_value': {'passed': bool(simple_delta >= spec['simple_control_value']['macro_recall_delta_min']), 'macro_delta': simple_delta},
        'loss_gap': {'present': bool(loss_delta >= spec['loss_gap']['clean_minus_command_absent_macro_recall_min']), 'macro_clean_minus_loss_recall': loss_delta},
        'activity_count_clean_recall_delta': m - macro('activity_count', 'clean'),
        'novel_method_validated': False
    }
    if not checks['clean_useful_signal']['passed']:
        checks['decision'] = 'RETIRE_PRIMARY_POOLED_LR_FORMULATION; inspect secondary controls as disclosed developmental diagnostics only'
    elif checks['loss_gap']['present']:
        checks['decision'] = 'CLEAN_SIGNAL_WITH_LOSS_GAP; qualify surviving additional sources before a new recovery experiment'
    else:
        checks['decision'] = 'CLEAN_SIGNAL_WITHOUT_LARGE_COMMAND_LOSS_GAP; no demonstrated need for a recovery mechanism under this stress'
    return checks


def run(cache, protocol_path, output):
    if output.exists():
        raise ValueError('Immutable run output must not already exist')
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    manifest = json.loads((cache / 'MANIFEST.json').read_text(encoding='utf-8'))
    rows = json.loads((cache / 'metadata.json').read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('Expected metadata list')
    required = ['metadata.json', *[f'{view}_{condition}.npz' for view in ('first', 'pooled') for condition in protocol['conditions']],
                *[f'rules_{condition}.npy' for condition in protocol['conditions']]]
    hashes = {name: digest(cache / name) for name in required}
    if manifest['protocol_sha256'] != digest(protocol_path):
        raise ValueError('Cache protocol hash mismatch')
    if any(hashes[name] != manifest['artifacts'][name]['sha256'] for name in required):
        raise ValueError('Cache artifact hash mismatch')
    feature_path = Path(__file__).with_name('features.py')
    adapter_path = Path(__file__).parents[1] / 'camlds' / 'events.py'
    if (digest(feature_path) != manifest['code_sha256']['features.py']
            or digest(adapter_path) != manifest['code_sha256']['camlds/events.py']):
        raise ValueError('Feature preparation code changed')
    families = np.array([r['family'] for r in rows])
    labels = np.array([r['label'] for r in rows])
    if sorted(set(families)) != protocol['families'] or len({r['window_id'] for r in rows}) != len(rows):
        raise ValueError('Unexpected family roster or duplicate windows')
    matrices = {(view, cond): sparse.load_npz(cache / f'{view}_{cond}.npz') for view in ('first', 'pooled') for cond in protocol['conditions']}
    if any(X.shape != (len(rows), 8200) or not np.isfinite(X.data).all() for X in matrices.values()):
        raise ValueError('Feature dimensions or finiteness invalid')
    output.mkdir(parents=True)
    repo = Path(__file__).resolve().parents[3]
    source_files = [Path(__file__), Path(__file__).with_name('features.py'), protocol_path]
    receipt = {'created_utc': datetime.now(timezone.utc).isoformat(), 'frozen_before_fit': True,
        'protocol_sha256': digest(protocol_path), 'feature_manifest_sha256': digest(cache / 'MANIFEST.json'),
        'cache_artifact_sha256': hashes, 'code_sha256': {p.relative_to(repo).as_posix(): digest(p) for p in source_files},
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        'python': platform.python_version(), 'sklearn': sklearn.__version__,
        'development_only': True, 'models_fit': 0}
    save(output / 'PRE_FIT_RECEIPT.json', receipt)
    shutil.copyfile(protocol_path, output / 'PROTOCOL.json')
    save(output / 'FEATURE_MANIFEST.json', manifest)
    shutil.copyfile(cache / 'metadata.json', output / 'metadata.json')
    scores = {}
    fits = []
    for arm in protocol['arms']:
        for condition in protocol['conditions']:
            if arm == 'transfer_rule':
                scores[(arm, condition)] = np.load(cache / f'rules_{condition}.npy').astype(float)
            elif arm == 'activity_count':
                scores[(arm, condition)] = matrices[('pooled', condition)][:, 8192].toarray().ravel()
            else:
                scores[(arm, condition)] = np.full(len(rows), np.nan)
    with threadpool_limits(limits=2):
        for family in protocol['families']:
            train = (families != family) & (labels >= 0)
            test = families == family
            if set(labels[train]) != {0, 1} or set(labels[test & (labels >= 0)]) != {0, 1}:
                raise ValueError('Unsupported family fold')
            for arm in ('first_lr', 'pooled_lr', 'pooled_extra_trees'):
                view = 'first' if arm == 'first_lr' else 'pooled'
                model = ExtraTreesClassifier(**protocol['extra_trees']) if arm == 'pooled_extra_trees' else LogisticRegression(**protocol['logistic_regression'])
                start = time.perf_counter()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    model.fit(matrices[(view, 'clean')][train], labels[train])
                if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                    raise RuntimeError('Nonconverged fit; no result permitted')
                model_path = output / f'model_{family}_{arm}.joblib'
                joblib.dump(model, model_path)
                id_hash = lambda mask: hashlib.sha256(json.dumps([r['window_id'] for i, r in enumerate(rows) if mask[i]],
                    separators=(',', ':')).encode()).hexdigest()
                fits.append({'heldout_family': family, 'arm': arm, 'train_windows': int(train.sum()),
                    'train_positive': int((train & (labels == 1)).sum()), 'test_windows': int(test.sum()),
                    'train_families': sorted(set(families[train])), 'train_window_ids_sha256': id_hash(train),
                    'test_window_ids_sha256': id_hash(test), 'model_sha256': digest(model_path),
                    'fit_and_save_seconds': time.perf_counter() - start, 'warnings': [str(w.message) for w in caught]})
                for condition in protocol['conditions']:
                    scores[(arm, condition)][test] = model.predict_proba(matrices[(view, condition)][test])[:, list(model.classes_).index(1)]
                print(json.dumps(fits[-1]), flush=True)
    records, run_records = [], []
    prediction_arrays = {'label': labels, 'family': families}
    for (arm, condition), values in scores.items():
        if not np.isfinite(values).all():
            raise ValueError('Unscored or nonfinite predictions')
        prediction_arrays[f'{arm}__{condition}'] = values
        prediction_arrays[f'{arm}__{condition}__selected'] = select_review(rows, values, protocol['review_fraction'])
        for family in protocol['families']:
            idx = np.flatnonzero(families == family)
            records.append({'arm': arm, 'condition': condition, 'family': family,
                'metrics': summarize([rows[i] for i in idx], values[idx], protocol['review_fraction'])})
        for run_id in sorted({r['run_id'] for r in rows}):
            idx = np.array([i for i, r in enumerate(rows) if r['run_id'] == run_id])
            run_records.append({'arm': arm, 'condition': condition, 'run_id': run_id, 'family': rows[idx[0]]['family'],
                'metrics': summarize([rows[i] for i in idx], values[idx], protocol['review_fraction'])})
    np.savez_compressed(output / 'predictions.npz', **prediction_arrays)
    macro = []
    for arm in protocol['arms']:
        for condition in protocol['conditions']:
            selected = [r['metrics'] for r in records if r['arm'] == arm and r['condition'] == condition]
            keys = ['recall', 'chance_recall', 'confirmed_positive_yield_lower_bound', 'unknown_selected_fraction', 'known_average_precision', 'known_roc_auc', 'known_prevalence', 'source_interval_touch_recall']
            macro.append({'arm': arm, 'condition': condition, **{k: float(np.mean([r[k] for r in selected])) for k in keys},
                'known_only_f1': float(np.mean([r['known_only_budget']['f1'] for r in selected]))})
    result = {'status': 'COMPLETE_DEVELOPMENT_DIAGNOSTIC', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'protocol_sha256': digest(protocol_path), 'pre_fit_receipt_sha256': digest(output / 'PRE_FIT_RECEIPT.json'),
        'predictions_sha256': digest(output / 'predictions.npz'), 'models_fit': len(fits), 'family_condition_arm_rows': len(records),
        'fits': fits, 'macro_family_results': macro, 'family_results': records, 'run_results': run_records,
        'gates': compute_gates(records, protocol), 'novel_method_validated': False, 'independent_confirmation': False}
    save(output / 'RESULTS.json', result)
    print(json.dumps({'status': result['status'], 'gates': result['gates']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.cache, args.protocol, args.output)
