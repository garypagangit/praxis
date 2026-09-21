"""LAC prediction sets for a frozen classifier's saved probabilities.

This module fits no classifier and chooses no model or operating point. It
implements the usual marginal and class-conditional (Mondrian) score quantiles.
Outputs describe empirical coverage; the code does not certify exchangeability,
independent flow groups, temporal generalization, or unseen-attack risk.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import math
from typing import Any, Sequence

import numpy as np


EMPIRICAL_NOTICE = (
    "Empirical coverage and set efficiency only. No coverage or attack-miss "
    "guarantee is claimed for dependent flows, group splits, temporal shift, "
    "or unseen stages."
)


def _probabilities(values: Any, n_classes: int | None = None) -> np.ndarray:
    probabilities = np.asarray(values, dtype=float)
    if probabilities.ndim != 2 or probabilities.shape[1] == 0:
        raise ValueError("Probabilities must have shape (n_examples, n_classes>0).")
    if n_classes is not None and probabilities.shape[1] != n_classes:
        raise ValueError("Probability columns do not match the calibration classes.")
    if not np.all(np.isfinite(probabilities)):
        raise ValueError("Probabilities must be finite.")
    if np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Probabilities must lie in [0, 1].")
    if not np.allclose(probabilities.sum(axis=1), 1.0, rtol=0, atol=1e-6):
        raise ValueError("Every probability row must sum to one.")
    return probabilities


def _class_labels(values: Sequence[Any] | None, count: int) -> tuple[Any, ...]:
    labels = tuple(range(count)) if values is None else tuple(
        value.item() if isinstance(value, np.generic) else value for value in values
    )
    if len(labels) != count:
        raise ValueError("class_labels must list every probability column in order.")
    if any(not isinstance(label, (str, int, float, bool)) for label in labels):
        raise ValueError("Class labels must be JSON-compatible scalar values.")
    if any(isinstance(label, float) and not math.isfinite(label) for label in labels):
        raise ValueError("Class labels must be finite.")
    if len(set(labels)) != len(labels):
        raise ValueError("Class labels must be unique.")
    return labels


def _label_indices(values: Sequence[Any], labels: tuple[Any, ...], count: int) -> np.ndarray:
    observed = np.asarray(values, dtype=object)
    if observed.ndim != 1 or len(observed) != count:
        raise ValueError("Labels must be one-dimensional and match the row count.")
    lookup = {label: index for index, label in enumerate(labels)}
    try:
        return np.asarray([lookup[label] for label in observed], dtype=int)
    except (KeyError, TypeError) as error:
        raise ValueError("An observed label has no declared probability column.") from error


def finite_sample_quantile(scores: Sequence[float], alpha: float) -> float:
    """Return sorted_scores[ceil((n+1)*(1-alpha))-1], or +inf if unavailable.

    Decimal arithmetic avoids floating-point rounding a mathematically integral
    rank upward. Alpha is interpreted as the decimal value provided by caller.
    No interpolation or replacement by the largest observed score is used.
    """
    alpha = float(alpha)
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and strictly between zero and one.")
    values = np.asarray(scores, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("Calibration scores must be a finite one-dimensional array.")
    if np.any((values < 0) | (values > 1)):
        raise ValueError("LAC calibration scores must lie in [0, 1].")
    rank = int((Decimal(len(values) + 1) * (1 - Decimal(str(alpha)))).to_integral_value(
        rounding=ROUND_CEILING
    ))
    if rank > len(values):
        return math.inf
    return float(np.partition(values, rank - 1)[rank - 1])


@dataclass(frozen=True)
class LACCalibration:
    """Frozen quantiles; class_labels defines the order of every probability matrix."""

    method: str
    alpha: float
    class_labels: tuple[Any, ...]
    thresholds: tuple[float, ...]
    calibration_count: int
    calibration_class_counts: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe metadata: a null threshold means positive infinity."""
        return {
            "method": self.method,
            "score": "1 - probability_of_candidate_class",
            "alpha": self.alpha,
            "nominal_coverage": float(Decimal(1) - Decimal(str(self.alpha))),
            "class_labels": list(self.class_labels),
            "thresholds": [None if math.isinf(q) else q for q in self.thresholds],
            "threshold_infinite": [math.isinf(q) for q in self.thresholds],
            "threshold_null_means": "positive_infinity_include_candidate_class",
            "calibration_count": self.calibration_count,
            "calibration_class_counts": list(self.calibration_class_counts),
            "interpretation": EMPIRICAL_NOTICE,
        }


def fit_lac(
    calibration_probabilities: Any,
    calibration_labels: Sequence[Any],
    *,
    alpha: float = 0.1,
    method: str = "marginal",
    class_labels: Sequence[Any] | None = None,
) -> LACCalibration:
    """Calibrate LAC scores globally or separately within each true class.

    Unsupported or undersized Mondrian classes get +inf and are always included.
    If no global calibration scores exist, marginal calibration is also vacuous.
    This function never inspects test labels or fits a probability model.
    """
    if method not in ("marginal", "mondrian"):
        raise ValueError("method must be 'marginal' or 'mondrian'.")
    probabilities = _probabilities(calibration_probabilities)
    labels = _class_labels(class_labels, probabilities.shape[1])
    indices = _label_indices(calibration_labels, labels, len(probabilities))
    scores = 1 - probabilities[np.arange(len(indices)), indices]
    counts = tuple(int(np.count_nonzero(indices == index)) for index in range(len(labels)))
    if method == "marginal":
        quantile = finite_sample_quantile(scores, alpha)
        thresholds = (quantile,) * len(labels)
    else:
        thresholds = tuple(finite_sample_quantile(scores[indices == index], alpha)
                           for index in range(len(labels)))
    return LACCalibration(method, float(alpha), labels, thresholds, len(scores), counts)


def predict_sets(probabilities: Any, calibration: LACCalibration) -> np.ndarray:
    """Return a boolean candidate-label matrix, retaining empty and full sets."""
    observed = _probabilities(probabilities, len(calibration.class_labels))
    thresholds = np.asarray(calibration.thresholds, dtype=float)
    if thresholds.shape != (len(calibration.class_labels),) or np.any(np.isnan(thresholds)):
        raise ValueError("Calibration thresholds are invalid.")
    if np.any(thresholds < 0) or np.any(np.isneginf(thresholds)):
        raise ValueError("Calibration thresholds cannot be negative.")
    return (1 - observed) <= thresholds[np.newaxis, :]


def evaluate_sets(
    prediction_sets: Any,
    true_labels: Sequence[Any],
    *,
    class_labels: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Describe coverage and utility without treating rows as independent trials."""
    sets = np.asarray(prediction_sets)
    if sets.ndim != 2 or sets.shape[1] == 0 or sets.dtype != np.dtype(bool):
        raise ValueError("prediction_sets must be a boolean (n_examples, n_classes>0) matrix.")
    labels = _class_labels(class_labels, sets.shape[1])
    indices = _label_indices(true_labels, labels, len(sets))
    covered = sets[np.arange(len(sets)), indices]
    sizes = sets.sum(axis=1)
    singleton = sizes == 1
    count = len(sets)
    singleton_count = int(np.count_nonzero(singleton))
    singleton_correct = int(np.count_nonzero(covered & singleton))
    per_class = []
    for index, label in enumerate(labels):
        mask = indices == index
        denominator = int(np.count_nonzero(mask))
        numerator = int(np.count_nonzero(covered & mask))
        per_class.append({"class_index": index, "class_label": label,
                          "count": denominator, "covered": numerator,
                          "coverage": numerator / denominator if denominator else None})
    empty_count = int(np.count_nonzero(sizes == 0))
    full_count = int(np.count_nonzero(sizes == len(labels)))
    return {
        "count": count,
        "n_classes": len(labels),
        "covered": int(np.count_nonzero(covered)),
        "coverage": float(np.mean(covered)) if count else None,
        "mean_set_size": float(np.mean(sizes)) if count else None,
        "median_set_size": float(np.median(sizes)) if count else None,
        "empty_count": empty_count,
        "empty_fraction": empty_count / count if count else None,
        "full_count": full_count,
        "full_fraction": full_count / count if count else None,
        "singleton_count": singleton_count,
        "singleton_fraction": singleton_count / count if count else None,
        "singleton_correct": singleton_correct,
        "singleton_accuracy": singleton_correct / singleton_count if singleton_count else None,
        "per_class": per_class,
        "interpretation": EMPIRICAL_NOTICE,
    }


def evaluate_lac(
    calibration_probabilities: Any,
    calibration_labels: Sequence[Any],
    test_probabilities: Any,
    test_labels: Sequence[Any],
    *,
    class_labels: Sequence[Any] | None = None,
    nominal_coverages: Sequence[float] = (0.9, 0.95),
) -> dict[str, Any]:
    """Evaluate the prespecified nominal levels and both methods on saved scores.

    Test labels are passed only to evaluate_sets after prediction sets are built.
    Each entry is descriptive; this function does not select a winning method.
    """
    calibration_probabilities = _probabilities(calibration_probabilities)
    labels = _class_labels(class_labels, calibration_probabilities.shape[1])
    test_probabilities = _probabilities(test_probabilities, len(labels))
    evaluations = []
    for nominal in nominal_coverages:
        nominal = float(nominal)
        if not math.isfinite(nominal) or not 0 < nominal < 1:
            raise ValueError("Nominal coverage must be finite and strictly between zero and one.")
        alpha = float(Decimal(1) - Decimal(str(nominal)))
        for method in ("marginal", "mondrian"):
            calibration = fit_lac(calibration_probabilities, calibration_labels,
                                  alpha=alpha, method=method, class_labels=labels)
            sets = predict_sets(test_probabilities, calibration)
            evaluations.append({"nominal_coverage": nominal, "method": method,
                                "calibration": calibration.to_dict(),
                                "metrics": evaluate_sets(sets, test_labels, class_labels=labels)})
    return {"class_labels": list(labels), "evaluations": evaluations,
            "interpretation": EMPIRICAL_NOTICE}
