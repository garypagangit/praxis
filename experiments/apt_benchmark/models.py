"""Fixed CPU binary baselines and empirical, calibration-only thresholds.

Features and split provenance are the caller's responsibility. Larger scores
mean class 1 (malicious). Thresholds use strict score > threshold. A measured
calibration false-positive rate is not a population guarantee under drift or
dependence, irrespective of the number of available rows.
"""
from __future__ import annotations

from fractions import Fraction
import math
from numbers import Real

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MODEL_SPECS = {
    'dummy_prior': {'estimator': 'DummyClassifier', 'parameters': {'strategy': 'prior'},
                    'imputer': 'median_keep_empty_features', 'scaler': None},
    'logistic_regression': {'estimator': 'LogisticRegression',
                            'parameters': {'max_iter': 1000, 'class_weight': 'balanced'},
                            'imputer': 'median_keep_empty_features', 'scaler': 'StandardScaler'},
    'random_forest': {'estimator': 'RandomForestClassifier',
                      'parameters': {'n_estimators': 150, 'max_depth': 14,
                                     'min_samples_leaf': 5, 'class_weight': 'balanced', 'n_jobs': 2},
                      'imputer': 'median_keep_empty_features', 'scaler': None},
    'hist_gradient_boosting': {'estimator': 'HistGradientBoostingClassifier',
                               'parameters': {'max_iter': 100, 'max_leaf_nodes': 15,
                                              'l2_regularization': 1, 'early_stopping': False},
                               'imputer': 'median_keep_empty_features', 'scaler': None},
}


def build_binary_model(name, seed=20260920):
    """Return an unfitted, fixed-parameter sklearn Pipeline.

    The imputer and optional scaler are fitted only by Pipeline.fit on the
    caller's fit partition. No calibration/test statistics are used here.
    """
    if not isinstance(name, str):
        raise ValueError('Model name must be a string')
    name = name.replace('-', '_')
    if name not in MODEL_SPECS:
        raise ValueError('Unknown model: ' + name)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Seed must be an integer in [0, 2**32)')
    constructors = {'dummy_prior': DummyClassifier, 'logistic_regression': LogisticRegression,
                    'random_forest': RandomForestClassifier,
                    'hist_gradient_boosting': HistGradientBoostingClassifier}
    estimator = constructors[name](**MODEL_SPECS[name]['parameters'], random_state=seed)
    steps = [('imputer', SimpleImputer(strategy='median', keep_empty_features=True))]
    if name == 'logistic_regression':
        steps.append(('scaler', StandardScaler()))
    steps.append(('classifier', estimator))
    return Pipeline(steps)


def score_binary(model, X):
    """Return class-1 probability; never assume it is predict_proba column 1.

    A fitted one-class dummy is supported: class 0 yields all zero and class 1
    all one. This does not make its training/evaluation split qualified.
    """
    classes = np.asarray(model.classes_)
    if (classes.ndim != 1 or len(classes) not in (1, 2)
            or len(np.unique(classes)) != len(classes) or not np.isin(classes, [0, 1]).all()):
        raise ValueError('Fitted model classes must be numeric binary labels 0/1')
    probabilities = np.asarray(model.predict_proba(X), dtype=float)
    if (probabilities.ndim != 2 or probabilities.shape[1] != len(classes)
            or not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or (probabilities > 1).any()
            or not np.allclose(probabilities.sum(axis=1), 1, rtol=1e-7, atol=1e-9)):
        raise ValueError('Model must return finite normalized binary probabilities')
    matches = np.flatnonzero(classes == 1)
    return probabilities[:, matches[0]].copy() if len(matches) else np.zeros(len(probabilities))


def resolve_threshold(result):
    """Decode the JSON-safe threshold fields for internal comparison only."""
    kind, value = result.get('threshold_kind'), result.get('threshold_value')
    if kind == 'finite':
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError('Finite threshold requires a finite number')
        return float(value)
    if kind not in ('positive_infinity', 'negative_infinity') or value is not None:
        raise ValueError('Invalid threshold encoding')
    return math.inf if kind == 'positive_infinity' else -math.inf


def calibration_threshold(y, scores, max_fpr=0.01):
    """Maximize observed attack recall subject to an empirical event-FPR cap.

    Pick the lowest feasible strict threshold; ties remain unsuppressed by an
    arbitrary epsilon. This also deterministically resolves equal-recall
    candidates toward the more permissive feasible threshold. With n negative
    labels and k=floor(max_fpr*n), the threshold is negative_score[n-k-1]
    (ascending), or -infinity for k=n. This benign order statistic maximizes
    recall for every set of positive scores by monotonicity.

    Missing either class returns explicit no-alarm (+infinity), with undefined
    recall/FPR where appropriate. Low benign count is flagged when one false
    event already exceeds the budget; the zero-observed-FP option remains a
    computable exploratory threshold. Rows are not asserted independent.
    """
    labels = np.asarray(y)
    values = np.asarray(scores, dtype=float)
    if (labels.ndim != 1 or values.ndim != 1 or len(labels) != len(values)
            or not np.isin(labels, [0, 1]).all() or not np.isfinite(values).all()):
        raise ValueError('Equal-length known binary labels and finite scores are required')
    if (isinstance(max_fpr, (bool, np.bool_)) or not isinstance(max_fpr, Real)
            or not math.isfinite(max_fpr) or not 0 <= max_fpr <= 1):
        raise ValueError('max_fpr must be finite and in [0, 1]')
    labels = labels.astype(bool)
    n_attack, n_benign = int(labels.sum()), int((~labels).sum())
    budget = Fraction(str(float(max_fpr)))
    allowed = (budget.numerator * n_benign) // budget.denominator
    minimum_support = math.ceil(1 / budget) if budget > 0 else None
    low_support = minimum_support is not None and n_benign < minimum_support
    if not n_attack or not n_benign:
        threshold = math.inf
        status = ('EMPTY_CALIBRATION' if not len(labels) else
                  'NO_ATTACK_CALIBRATION' if not n_attack else 'NO_BENIGN_CALIBRATION')
    elif allowed == n_benign:
        threshold = -math.inf
        status = 'LOW_BENIGN_RESOLUTION' if low_support else 'EMPIRICAL_CALIBRATION_ONLY'
    else:
        threshold = float(np.sort(values[~labels])[n_benign - allowed - 1])
        status = 'LOW_BENIGN_RESOLUTION' if low_support else 'EMPIRICAL_CALIBRATION_ONLY'
    pred = values > threshold
    tp, fp = int((pred & labels).sum()), int((pred & ~labels).sum())
    kind = 'positive_infinity' if threshold == math.inf else 'negative_infinity' if threshold == -math.inf else 'finite'
    return {
        'status': status, 'threshold_kind': kind,
        'threshold_value': threshold if math.isfinite(threshold) else None,
        'decision_rule': 'class_1_score > threshold', 'max_fpr': float(max_fpr),
        'n_rows': len(labels), 'n_attack': n_attack, 'n_benign': n_benign,
        'allowed_false_positives': allowed,
        'confusion': {'tp': tp, 'fp': fp, 'tn': n_benign - fp, 'fn': n_attack - tp},
        'observed_recall': tp / n_attack if n_attack else None,
        'observed_fpr': fp / n_benign if n_benign else None,
        'both_classes_present': bool(n_attack and n_benign),
        'minimum_benign_count_for_one_false_event_within_budget': minimum_support,
        'insufficient_benign_resolution': low_support,
        'population_fpr_guarantee': False,
        'selection': 'Lowest feasible strict threshold; calibration data only',
        'limitations': ['Empirical event FPR, not a population guarantee or host-hour alarm rate',
                        'Dependent rows and distribution shift are not corrected by this selector',
                        'One-row budget resolution is not a confidence or power calculation'],
    }
