"""One predetermined deployment fit using only the frozen 2,500-row old pilot."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from apply_deployment import load_helper, score_records

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'cti_checker_pilot_20260918'


def hash_object(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_json_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    outputs = ['deployment.joblib', 'DEPLOYMENT_METADATA.json',
               'deployment_calibration_predictions.jsonl', 'DEPLOYMENT_VERIFICATION.json']
    for name in outputs:
        if (ROOT / name).exists():
            raise FileExistsError(f'Refusing to overwrite deployment export: {name}')
    start = time.perf_counter()
    helper = load_helper()
    frozen = json.loads((OLD / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in frozen['sha256'].items():
        if helper.sha(OLD / name) != digest:
            raise ValueError(f'Old pilot freeze changed: {name}')
    data, eligible, groups, base, evidence = helper.load_data()
    split_rows = json.loads((OLD / 'SPLITS.json').read_text(encoding='utf-8'))
    assert [r['id'] for r in split_rows] == [r['id'] for r in data]
    assert [r['source_group'] for r in split_rows] == list(groups)
    folds = np.asarray([r['fold'] for r in split_rows])
    train = np.flatnonzero(folds != 0)
    calibration = np.flatnonzero(folds == 0)
    assert len(train) == 2000 and len(calibration) == 500
    assert set(folds) == {0, 1, 2, 3, 4}
    train_groups = sorted(set(groups[train]))
    cal_groups = sorted(set(groups[calibration]))
    assert not set(train_groups) & set(cal_groups)
    qmap = helper.verified_scores('data.jsonl', 'relevance_scores.jsonl', 'relevance_metadata.json', data)
    option_data = helper.rows(OLD / 'data_relevance_options.jsonl')
    assert [r['id'] for r in option_data] == [r['id'] for r in data]
    for original, projected in zip(data, option_data):
        assert projected['question'] == helper.question_text(original)
        assert projected['evidence'] == original['evidence']
    omap = helper.verified_scores('data_relevance_options.jsonl', 'relevance_options_scores.jsonl',
                                 'relevance_options_metadata.json', option_data)
    texts = [helper.question_text(row) for row in data]
    dictionaries = [helper.features(row, qmap[row['id']]['logits']) for row in data]
    names = list(dictionaries[0])
    assert len(names) == 38 and all(list(d) == names for d in dictionaries)
    dense = np.asarray([[d[n] for n in names] for d in dictionaries], dtype=float)
    assert np.isfinite(dense).all()
    delta = evidence - base
    target = delta.mean(axis=1)
    vectors = helper.vectorizers()
    xtrain = sparse.hstack([v.fit_transform([texts[i] for i in train]) for v in vectors], format='csr')
    xcal = sparse.hstack([v.transform([texts[i] for i in calibration]) for v in vectors], format='csr')
    scaler = StandardScaler().fit(dense[train])
    ztrain = sparse.hstack([xtrain, sparse.csr_matrix(scaler.transform(dense[train]))], format='csr')
    zcal = sparse.hstack([xcal, sparse.csr_matrix(scaler.transform(dense[calibration]))], format='csr')
    estimators = {
        'source_classifier': LogisticRegression(C=1, class_weight='balanced', max_iter=2000,
                                                 random_state=helper.SEED),
        'question_utility': Ridge(alpha=10, solver='lsqr'),
        'evidence_utility': Ridge(alpha=10, solver='lsqr'),
    }
    fit_seconds = {}
    for name, estimator in estimators.items():
        t0 = time.perf_counter()
        estimator.fit(ztrain if name == 'evidence_utility' else xtrain,
                      eligible[train] if name == 'source_classifier' else target[train])
        fit_seconds[name] = time.perf_counter() - t0
    scores = {
        'relevance': dense[calibration, names.index('relevance_max')],
        'relevance_options': np.asarray([max(omap[data[i]['id']]['logits']) for i in calibration]),
        'source_classifier': estimators['source_classifier'].predict_proba(xcal)[:, 1],
        'question_utility': estimators['question_utility'].predict(xcal),
        'evidence_utility': estimators['evidence_utility'].predict(zcal),
    }
    thresholds, threshold_details, metrics = {}, {}, {}
    for name, values in scores.items():
        cutoff, detail = helper.threshold(values, delta[calibration], eligible[calibration])
        thresholds[name] = cutoff
        threshold_details[name] = detail
        use = values >= cutoff
        outcomes = base[calibration] + use[:, None] * delta[calibration]
        metrics[name] = {'n': len(calibration), 'evidence_use_n': int(use.sum()),
            'evidence_use_pct': float(100 * use.mean()),
            'models': {model: {'correct': int(outcomes[:, j].sum()),
                'accuracy_pct': float(100 * outcomes[:, j].mean()),
                'delta_vs_vanilla_pp': float(100 * (outcomes[:, j] - base[calibration, j]).mean())}
                for j, model in enumerate(helper.MODELS)}}
    bundle = {'schema_version': 1, 'helper_sha256': helper.sha(OLD / 'run_pilot.py'),
        'feature_names': names, 'vectorizers': vectors, 'scaler': scaler, **estimators,
        'thresholds': thresholds, 'models': helper.MODELS, 'seed': helper.SEED,
        'training_policy': 'SPLITS fold 0 calibration; folds 1-4 train; no new-data access',
        'minilm_model_id': 'cross-encoder/ms-marco-MiniLM-L6-v2',
        'minilm_revision': '233902d25c440f23af6f7d6e94d2946bac0bee0a'}
    with (ROOT / 'deployment.joblib').open('xb') as stream:
        joblib.dump(bundle, stream, compress=3)
    # Only old calibration records enter export verification, explicitly projected.
    safe = [{'id': data[i]['id'], 'question': data[i]['question'], 'options': data[i]['options'],
             'evidence': [{k: e[k] for k in ('text', 'kind', 'score') if k in e}
                          for e in data[i]['evidence']]} for i in calibration]
    qs = [{'id': r['id'], 'logits': qmap[r['id']]['logits']} for r in safe]
    os = [{'id': r['id'], 'logits': omap[r['id']]['logits']} for r in safe]
    loaded_predictions = score_records(ROOT / 'deployment.joblib', safe, qs, os)
    repeated_predictions = score_records(ROOT / 'deployment.joblib', safe, qs, os)
    assert loaded_predictions == repeated_predictions
    max_error = 0.0
    for i, result in enumerate(loaded_predictions):
        assert result['id'] == safe[i]['id']
        for name, values in scores.items():
            max_error = max(max_error, abs(result['scores'][name] - float(values[i])))
            assert np.isclose(result['scores'][name], values[i], rtol=0, atol=1e-12)
            assert result['use_evidence'][name] == bool(values[i] >= thresholds[name])
    with (ROOT / 'deployment_calibration_predictions.jsonl').open('x', encoding='utf-8') as stream:
        for row in loaded_predictions:
            stream.write(json.dumps(row, allow_nan=False) + '\n')
    input_names = ['FREEZE.json', 'SPLITS.json', 'data.jsonl', 'data_relevance_options.jsonl',
                   'relevance_scores.jsonl', 'relevance_options_scores.jsonl',
                   'relevance_metadata.json', 'relevance_options_metadata.json', 'run_pilot.py']
    train_ids = [data[i]['id'] for i in train]
    cal_ids = [data[i]['id'] for i in calibration]
    metadata = {'status': 'FROZEN_DEPLOYMENT_OLD_DATA_ONLY',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'fit_rule': bundle['training_policy'], 'fit_count_per_estimator': 1,
        'no_new_dataset_or_outcomes_read': True,
        'selection': 'Predetermined split, no best-fold selection and no hyperparameter tuning',
        'train_n': len(train_ids), 'calibration_n': len(cal_ids),
        'training_ids': train_ids, 'calibration_ids': cal_ids,
        'training_ids_sha256': hash_object(train_ids), 'calibration_ids_sha256': hash_object(cal_ids),
        'training_source_groups': train_groups, 'calibration_source_groups': cal_groups,
        'training_source_groups_sha256': hash_object(train_groups),
        'calibration_source_groups_sha256': hash_object(cal_groups),
        'source_group_overlap': 0, 'feature_names': names,
        'threshold_calibration': threshold_details, 'calibration_metrics': metrics,
        'calibration_metrics_are_not_test_results': True,
        'input_sha256': {name: helper.sha(OLD / name) for name in input_names},
        'code_sha256': {name: helper.sha(ROOT / name) for name in ('train_deployment.py', 'apply_deployment.py')},
        'bundle_sha256': helper.sha(ROOT / 'deployment.joblib'),
        'calibration_predictions_sha256': helper.sha(ROOT / 'deployment_calibration_predictions.jsonl'),
        'estimator_fit_seconds': fit_seconds, 'total_export_seconds': time.perf_counter() - start,
        'python': sys.version,
        'versions': {name: importlib.metadata.version(name) for name in
                     ('numpy', 'scipy', 'scikit-learn', 'joblib', 'threadpoolctl')}}
    write_json_new(ROOT / 'DEPLOYMENT_METADATA.json', metadata)
    verification = {'status': 'PASS', 'records': len(calibration),
        'checked_data': 'Old fold-0 calibration only; no fresh test data',
        'serialized_roundtrip_matches_in_memory_scores_and_decisions': True,
        'repeated_loaded_predictions_identical': True, 'maximum_score_absolute_error': max_error,
        'frozen_old_files_unchanged': all(helper.sha(OLD / name) == digest
                                         for name, digest in frozen['sha256'].items()),
        'bundle_sha256': helper.sha(ROOT / 'deployment.joblib'),
        'metadata_sha256': helper.sha(ROOT / 'DEPLOYMENT_METADATA.json')}
    assert verification['frozen_old_files_unchanged']
    write_json_new(ROOT / 'DEPLOYMENT_VERIFICATION.json', verification)
    print(json.dumps({'status': metadata['status'], 'train_n': len(train), 'calibration_n': len(calibration),
                      'threshold_calibration': threshold_details, 'verification': verification}, indent=2))


if __name__ == '__main__':
    with threadpool_limits(limits=4):
        main()
