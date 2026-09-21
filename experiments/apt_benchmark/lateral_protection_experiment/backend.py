"""Fit-only weighted tree selection for the lateral-protection experiment.

The caller supplies fitting rows only. This module has no calibration/test input,
dataset path, output writer, or threshold-selection logic. Every CV fold computes
its imputer and normalized weights using that fold's training labels/features.
"""
from __future__ import annotations

import copy
import json
from numbers import Integral
import time
from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits

from ..tabular_batch.run_e1 import canonical_hash, package_versions
from ..tabular_followup.run_strong_baselines import make_tree


MODELS = ("xgboost", "lightgbm")
WEIGHT_SCHEMES = ("natural", "balanced", "lateral2", "lateral4")
N_SPLITS = 3
_RESERVED = {
    "class_weight", "sample_weight", "scale_pos_weight", "is_unbalance", "unbalance",
    "random_state", "seed", "random_seed", "n_jobs", "nthread", "nthreads", "num_threads",
    "device", "device_type", "tree_method", "objective", "num_class", "num_classes",
    "eval_metric", "verbosity", "deterministic", "force_col_wise",
}


def _integer(value: Any, name: str, *, minimum: int, maximum: int | None = None) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer.")
    result = int(value)
    if result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f"{name} is outside the permitted range.")
    return result


def _labels(y: Any, n_classes: int) -> np.ndarray:
    values = np.asarray(y)
    if values.ndim != 1 or not len(values) or values.dtype.kind not in "iu":
        raise ValueError("Labels must be a nonempty one-dimensional integer array.")
    if not np.array_equal(np.unique(values), np.arange(n_classes)):
        raise ValueError("Every declared class must occur, with labels 0 through n_classes-1.")
    return values.astype(np.int64, copy=False)


def validate_weight_vector(weights: Any, n_rows: int) -> np.ndarray:
    """Reject malformed, nonpositive, nonfinite, or non-normalized weights."""
    raw = np.asarray(weights)
    if raw.dtype.kind not in "iuf" or raw.ndim != 1 or len(raw) != n_rows or not len(raw):
        raise ValueError("Weights must be a numeric vector with one value per fitting row.")
    values = raw.astype(np.float64, copy=False)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("All training weights must be finite and strictly positive.")
    if not np.isclose(values.mean(), 1.0, rtol=0, atol=1e-12):
        raise ValueError("Training weights must have mean one.")
    return values


def training_weights(y: Any, scheme: str, n_classes: int, lateral_index: int) -> np.ndarray:
    """Compute equal-class mass, optionally emphasizing lateral movement.

    Balanced weights are n / (K * class_count). Lateral multipliers apply after
    balancing; every scheme is then normalized to mean one over these rows.
    Missing classes are rejected rather than silently changing the estimand.
    """
    n_classes = _integer(n_classes, "n_classes", minimum=2)
    lateral_index = _integer(lateral_index, "lateral_index", minimum=0, maximum=n_classes - 1)
    labels = _labels(y, n_classes)
    if scheme not in WEIGHT_SCHEMES:
        raise ValueError("Unknown weight scheme.")
    counts = np.bincount(labels, minlength=n_classes)
    weights = np.ones(len(labels), dtype=np.float64)
    if scheme != "natural":
        weights = len(labels) / (n_classes * counts[labels].astype(np.float64))
        multiplier = {"balanced": 1.0, "lateral2": 2.0, "lateral4": 4.0}[scheme]
        weights[labels == lateral_index] *= multiplier
    weights /= weights.mean()
    return validate_weight_vector(weights, len(labels))


def _grid(grid: Any) -> list[dict[str, Any]]:
    if not isinstance(grid, (list, tuple)) or not grid:
        raise ValueError("The declared grid must contain at least one parameter dictionary.")
    result = []
    for parameters in grid:
        if not isinstance(parameters, dict) or not all(isinstance(key, str) for key in parameters):
            raise ValueError("Every grid candidate must be a dictionary with string keys.")
        forbidden = {key for key in parameters if key.lower().split("__")[-1] in _RESERVED}
        if forbidden:
            raise ValueError("Grid cannot override weights or fixed runtime/model settings: " + ", ".join(sorted(forbidden)))
        try:
            json.dumps(parameters, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Grid values must be finite JSON-compatible parameters.") from exc
        result.append(copy.deepcopy(parameters))
    return result


def _weight_summary(y: np.ndarray, weights: np.ndarray, n_classes: int) -> dict[str, Any]:
    weights = validate_weight_vector(weights, len(y))
    return {
        "rows": len(y), "class_counts": np.bincount(y, minlength=n_classes).tolist(),
        "class_weight_sums": np.bincount(y, weights=weights, minlength=n_classes).tolist(),
        "mean": float(weights.mean()), "minimum": float(weights.min()), "maximum": float(weights.max()),
        "vector_sha256": canonical_hash(weights.tolist()),
    }


def _probabilities(classifier: Any, X: np.ndarray, n_classes: int) -> np.ndarray:
    if not np.array_equal(np.asarray(classifier.classes_), np.arange(n_classes)):
        raise ValueError("Classifier probability columns do not match the fixed class order.")
    values = np.asarray(classifier.predict_proba(X), dtype=np.float64)
    if values.shape != (len(X), n_classes) or not np.isfinite(values).all():
        raise ValueError("Invalid validation probability dimensions or nonfinite values.")
    if (values < -1e-7).any() or (values > 1 + 1e-7).any() or not np.allclose(values.sum(axis=1), 1, rtol=0, atol=1e-5):
        raise ValueError("Validation probabilities must form distributions.")
    return values


def validate_cv_metadata(metadata: dict[str, Any], grid: Any) -> None:
    """Check fixed CV scoring, candidate means, and first-on-tie selection.

    This validates the stored arithmetic/selection contract, not a replay of
    model fitting; independent prediction auditing remains the caller's task.
    """
    candidates = _grid(grid)
    if metadata.get("n_splits") != N_SPLITS or metadata.get("metric") != "unweighted_macro_f1_all_declared_classes_argmax":
        raise ValueError("Unexpected weighted-CV scoring contract.")
    records = metadata.get("candidates")
    if not isinstance(records, list) or len(records) != len(candidates):
        raise ValueError("CV candidate roster differs from the declared grid.")
    means = []
    for expected, record in zip(candidates, records):
        if record.get("parameters") != expected:
            raise ValueError("CV candidate parameters changed.")
        scores = np.asarray(record.get("fold_macro_f1"), dtype=float)
        if scores.shape != (N_SPLITS,) or not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
            raise ValueError("Expected three finite macro-F1 scores between zero and one.")
        score = float(scores.mean())
        reported = record.get("mean_macro_f1")
        if not isinstance(reported, (int, float)) or not np.isclose(reported, score, rtol=0, atol=1e-12):
            raise ValueError("CV mean does not match the fold scores.")
        means.append(score)
    winner = int(np.argmax(means))
    if (type(metadata.get("selected_candidate_index")) is not int
            or metadata["selected_candidate_index"] != winner
            or metadata.get("selected_parameters") != candidates[winner]
            or not np.isclose(metadata.get("selected_mean_macro_f1", np.nan), means[winner], rtol=0, atol=1e-12)):
        raise ValueError("CV winner differs from maximum mean score with first-on-tie selection.")


def fit_model(model: str, X_fit: Any, y_fit: Any, seed: int, grid: Any,
              weight_scheme: str, normal_index: int, lateral_index: int, n_classes: int,
              threads: int = 4) -> tuple[Any, SimpleImputer, dict[str, Any], dict[str, float]]:
    """Tune on three fitting-only folds, then refit on the full supplied support.

    Validation macro-F1 is unweighted across all declared classes. No downstream
    attack score, operating point, calibration label, or final-test outcome is
    available to this routine. Returned timing values are seconds on the CPU.
    """
    total_start = time.perf_counter()
    if model not in MODELS:
        raise ValueError("Weighted backend supports xgboost and lightgbm only.")
    n_classes = _integer(n_classes, "n_classes", minimum=2)
    seed = _integer(seed, "seed", minimum=0, maximum=2**32 - 1)
    threads = _integer(threads, "threads", minimum=1)
    normal_index = _integer(normal_index, "normal_index", minimum=0, maximum=n_classes - 1)
    lateral_index = _integer(lateral_index, "lateral_index", minimum=0, maximum=n_classes - 1)
    if normal_index == lateral_index:
        raise ValueError("Normal and lateral class indices must differ.")
    y = _labels(y_fit, n_classes)
    X = np.asarray(X_fit)
    if X.dtype.kind not in "biuf" or X.ndim != 2 or X.shape[0] != len(y) or X.shape[1] < 1:
        raise ValueError("Fitting features must be a numeric matrix aligned with the labels.")
    X = X.astype(np.float64, copy=False)
    if np.isinf(X).any():
        raise ValueError("Fitting features may contain NaN, but not infinity.")
    if np.bincount(y, minlength=n_classes).min() < N_SPLITS:
        raise ValueError("Each fitting class requires at least three rows for stratified CV.")
    candidates = _grid(grid)
    final_weights = training_weights(y, weight_scheme, n_classes, lateral_index)
    # Validate even when the weight implementation is replaced in an integration.
    final_weights = validate_weight_vector(final_weights, len(y))
    folds = list(StratifiedKFold(N_SPLITS, shuffle=True, random_state=seed).split(X, y))
    versions = package_versions()
    fold_metadata = []
    scored_candidates = []
    with threadpool_limits(limits=threads):
        cv_start = time.perf_counter()
        for candidate_index, parameters in enumerate(candidates):
            scores = []
            for train, validation in folds:
                imputer = SimpleImputer(strategy="median", keep_empty_features=True)
                train_features = imputer.fit_transform(X[train])
                validation_features = imputer.transform(X[validation])
                weights = validate_weight_vector(training_weights(y[train], weight_scheme, n_classes, lateral_index), len(train))
                classifier = make_tree(model, seed, copy.deepcopy(parameters), n_classes, threads)
                classifier.fit(train_features, y[train], sample_weight=weights)
                probabilities = _probabilities(classifier, validation_features, n_classes)
                scores.append(float(f1_score(y[validation], probabilities.argmax(axis=1), labels=np.arange(n_classes),
                                             average="macro", zero_division=0)))
                if candidate_index == 0:
                    fold_metadata.append({
                        "train_support_positions": train.tolist(), "validation_support_positions": validation.tolist(),
                        "training_weights": _weight_summary(y[train], weights, n_classes),
                        "imputer_statistics": imputer.statistics_.tolist(),
                    })
            scored_candidates.append({"parameters": copy.deepcopy(parameters), "fold_macro_f1": scores,
                                      "mean_macro_f1": float(np.mean(scores))})
        cv_seconds = time.perf_counter() - cv_start
        winner = max(range(len(scored_candidates)), key=lambda index: scored_candidates[index]["mean_macro_f1"])
        metadata = {
            "model": model, "seed": seed, "n_classes": n_classes, "normal_index": normal_index,
            "lateral_index": lateral_index, "weight_scheme": weight_scheme,
            "weight_normalization": "mean_one_within_each_fold_training_partition_and_final_support",
            "n_splits": N_SPLITS, "shuffle": True, "split_random_state": seed,
            "metric": "unweighted_macro_f1_all_declared_classes_argmax",
            "tie_policy": "first_candidate_in_declared_grid_order",
            "selection_data": "supplied_fitting_support_only",
            "selected_candidate_index": winner, "selected_parameters": copy.deepcopy(candidates[winner]),
            "selected_mean_macro_f1": scored_candidates[winner]["mean_macro_f1"],
            "candidates": scored_candidates, "folds": fold_metadata,
            "final_training_weights": _weight_summary(y, final_weights, n_classes),
            "versions": versions, "actual_device": "cpu", "cpu_threads": threads,
        }
        validate_cv_metadata(metadata, candidates)
        final_start = time.perf_counter()
        imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        classifier = make_tree(model, seed, copy.deepcopy(candidates[winner]), n_classes, threads)
        classifier.fit(imputer.fit_transform(X), y, sample_weight=final_weights)
        final_seconds = time.perf_counter() - final_start
        if not np.array_equal(classifier.classes_, np.arange(n_classes)):
            raise ValueError("Final fitted class order differs from the declared labels.")
    timing = {"inner_cv": cv_seconds, "final_fit_including_imputer": final_seconds,
              "total_fit_and_tuning": time.perf_counter() - total_start}
    return classifier, imputer, metadata, timing
