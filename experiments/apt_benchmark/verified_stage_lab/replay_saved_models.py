"""Read-only independent saved-model inference replay. Never calls fit()."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import warnings

import joblib
import numpy as np
from lightgbm import LGBMClassifier
from threadpoolctl import threadpool_limits

REPOSITORY = Path('C:/w/apt_benchmark_20260920')
PRIVATE = Path('C:/w/apt_benchmark_data_20260920/verified_stage_lab_v1')
sys.path.insert(0, str(REPOSITORY))
from experiments.apt_benchmark.verified_stage_lab.features import views, CONDITIONS


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def main():
    output = PRIVATE / 'replay' / 'INFERENCE_REPLAY.json'
    require(not output.exists(), 'Fresh replay artifact required')
    began = time.perf_counter()
    protocol_path = REPOSITORY / 'experiments/apt_benchmark/verified_stage_lab/protocol.json'
    science = protocol_path.parent
    protocol = read(protocol_path)
    run, prepared = PRIVATE / 'run', PRIVATE / 'prepared'
    started, complete, summary = (read(run / name) for name in ('STARTED.json', 'COMPLETE.json', 'SUMMARY.json'))
    prep = read(prepared / 'PREPARATION.json')
    source_hashes = protocol['source_bindings']
    for name, value in source_hashes.items():
        require(digest(science / name) == value, 'Frozen scientific source changed: ' + name)
    require(complete == {'summary_sha256': digest(run / 'SUMMARY.json'), 'started_sha256': digest(run / 'STARTED.json')}, 'Root completion binding')
    require(started['protocol_sha256'] == digest(protocol_path) == prep['protocol_sha256'], 'Protocol binding')
    require(started['prepared_sha256'] == digest(prepared / 'DATA.npz') == prep['data_sha256'], 'Prepared array binding')
    require(started['preparation_sha256'] == digest(prepared / 'PREPARATION.json'), 'Preparation receipt binding')
    require(summary['receipt']['models_fitted'] == 21, 'Expected complete 21-model roster')
    versions = {name: importlib.metadata.version(name) for name in ('numpy', 'lightgbm', 'scikit-learn', 'joblib')}
    require(versions == started['environment']['packages'], 'Inference package versions changed')
    require(protocol['seeds'] == [20260922, 20260923, 20260924], 'Frozen seeds')
    require(protocol['conditions'] == list(CONDITIONS), 'Frozen feature conditions')
    d = load_arrays(prepared / 'DATA.npz')
    fit = np.flatnonzero((d['split'] == 0) & d['linked'])
    cal = np.flatnonzero((d['split'] == 1) & d['linked'])
    groups = {'linked': np.flatnonzero((d['split'] == 2) & d['linked']),
              'crossed': np.flatnonzero((d['split'] == 2) & ~d['linked']),
              'factorial_all': np.flatnonzero(d['split'] == 2)}
    matrices = {condition: views(d, condition) for condition in CONDITIONS}
    require(len(fit) == 288 and len(cal) == 96, 'Frozen fit/calibration support')
    require({name: len(indexes) for name, indexes in groups.items()} == {'linked': 192, 'crossed': 576, 'factorial_all': 768}, 'Frozen test populations')
    models, arrays_checked, rows_checked, maximum_error, all_exact = [], 0, 0, 0., True
    warnings.filterwarnings('ignore', message='X does not have valid feature names, but LGBMClassifier was fitted with feature names')
    for seed in protocol['seeds']:
        directory = run / str(seed)
        receipt = read(directory / 'COMPLETE.json')['files']
        expected_files = {'PREDICTIONS.npz', 'METRICS.json'} | {arm + '.joblib' for arm in protocol['arms']}
        require(set(receipt) == expected_files, 'Seed artifact roster')
        for name, value in receipt.items():
            require(digest(directory / name) == value, 'Seed artifact changed: ' + name)
        saved = load_arrays(directory / 'PREDICTIONS.npz')
        require(np.array_equal(saved['fit_indices'], fit) and np.array_equal(saved['cal_indices'], cal), 'Saved fit/calibration roster')
        for population, indexes in groups.items():
            require(np.array_equal(saved[population + '_indices'], indexes), 'Saved population roster')
        for arm in protocol['arms']:
            model = joblib.load(directory / (arm + '.joblib'))
            # Instantiating an unfitted parameter template does not train a model.
            expected_parameters = LGBMClassifier(**protocol['parameters'], random_state=seed,
                                                n_jobs=4, deterministic=True, force_col_wise=True,
                                                verbosity=-1).get_params(deep=True)
            require(model.get_params(deep=True) == expected_parameters, 'Frozen model parameters: ' + arm)
            require(np.array_equal(model.classes_, np.arange(4)), 'Model class order: ' + arm)
            expected_features = matrices['clean'][arm].shape[1]
            require(model.n_features_in_ == expected_features == model.booster_.num_feature(), 'Model feature count: ' + arm)
            comparisons = [(arm + '__cal', matrices['clean'][arm][cal])]
            for condition in CONDITIONS:
                for population, indexes in groups.items():
                    comparisons.append((f'{arm}__{condition}__{population}', matrices[condition][arm][indexes]))
            model_rows, model_maximum, model_exact = 0, 0., True
            for name, matrix in comparisons:
                require(matrix.shape[1] == expected_features, 'Condition changed feature dimensions')
                actual = model.predict_proba(matrix)
                expected = saved[name]
                require(actual.shape == expected.shape == (len(matrix), 4), 'Prediction shape: ' + name)
                require(np.isfinite(actual).all() and np.all((actual >= 0) & (actual <= 1)), 'Prediction range: ' + name)
                require(np.allclose(actual.sum(axis=1), 1, rtol=0, atol=1e-12), 'Prediction normalization: ' + name)
                difference = float(np.max(np.abs(actual - expected))) if len(actual) else 0.
                exact = bool(np.array_equal(actual, expected))
                require(difference <= 1e-12, 'Inference replay mismatch: ' + name)
                arrays_checked += 1; rows_checked += len(matrix); model_rows += len(matrix)
                maximum_error = max(maximum_error, difference); model_maximum = max(model_maximum, difference)
                all_exact &= exact; model_exact &= exact
            models.append({'seed': seed, 'arm': arm, 'model_sha256': receipt[arm + '.joblib'],
                           'predictions_sha256': receipt['PREDICTIONS.npz'], 'feature_count': expected_features,
                           'parameters_match_frozen_source_and_protocol': True,
                           'class_order': [0, 1, 2, 3], 'n_estimators_requested': model.get_params()['n_estimators'],
                           'iterations_stored': model.booster_.current_iteration(), 'trees_stored': model.booster_.num_trees(),
                           'probability_arrays_replayed': len(comparisons), 'probability_rows_replayed': model_rows,
                           'all_probabilities_bitwise_equal': model_exact, 'maximum_absolute_difference': model_maximum})
    require(len(models) == 21 and arrays_checked == 336, 'Complete inference roster')
    for name, value in source_hashes.items():
        require(digest(science / name) == value, 'Scientific source changed during replay')
    result = {'replay_status': 'PASS', 'run_status': 'COMPLETE',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'replay_source_sha256': digest(__file__),
              'protocol_sha256': digest(protocol_path), 'scientific_source_hashes': source_hashes,
              'prepared_data_sha256': digest(prepared / 'DATA.npz'),
              'artifact_hashes': {name: digest(run / name) for name in ('SUMMARY.json', 'STARTED.json', 'COMPLETE.json')},
              'environment_package_versions': versions, 'model_count': len(models),
              'probability_arrays_replayed': arrays_checked, 'probability_rows_replayed': rows_checked,
              'absolute_tolerance': 1e-12, 'maximum_absolute_difference': maximum_error,
              'all_probabilities_bitwise_equal': all_exact, 'model_details': models,
              'elapsed_seconds': time.perf_counter() - began, 'model_fits_performed': 0,
              'scientific_outputs_modified': False, 'cloud_compute_started': False,
              'limitations': ['Reproduces inference from the frozen prepared feature arrays and frozen views function; independent raw feature reconstruction is a separate audit.',
                              'Repeated population/condition prediction rows are not additional independent observations.',
                              'Consistency of stored model predictions does not establish label validity, external performance or novelty.']}
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('replay_status', 'model_count', 'probability_arrays_replayed', 'probability_rows_replayed', 'all_probabilities_bitwise_equal', 'maximum_absolute_difference', 'elapsed_seconds')}))


if __name__ == '__main__':
    with threadpool_limits(limits=4):
        main()
