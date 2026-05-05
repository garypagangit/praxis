from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve


def router_entropy(gates: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    probs = np.clip(np.asarray(gates, dtype=float), eps, 1.0)
    return -np.sum(probs * np.log(probs), axis=1)


def fpr_at_recall(y_true_binary: np.ndarray, scores: np.ndarray, target_recall: float = 0.95) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true_binary, scores)
    if len(thresholds) == 0:
        return float("nan")
    candidate_indexes = np.where(recall[:-1] >= target_recall)[0]
    if len(candidate_indexes) == 0:
        return 1.0
    threshold = thresholds[candidate_indexes[-1]]
    predictions = scores >= threshold
    negatives = y_true_binary == 0
    false_positives = np.logical_and(predictions, negatives).sum()
    total_negatives = negatives.sum()
    return float(false_positives / total_negatives) if total_negatives else float("nan")


def classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    class_ids = sorted(np.unique(np.concatenate([y_true, y_pred])).tolist())
    names = labels or [str(item) for item in class_ids]

    per_class = f1_score(y_true, y_pred, labels=class_ids, average=None, zero_division=0)
    output: dict[str, Any] = {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "per_class_f1": {names[class_id] if class_id < len(names) else str(class_id): float(value) for class_id, value in zip(class_ids, per_class)},
        "per_class_support": {
            names[class_id] if class_id < len(names) else str(class_id): int((y_true == class_id).sum())
            for class_id in class_ids
        },
        "per_class_predicted": {
            names[class_id] if class_id < len(names) else str(class_id): int((y_pred == class_id).sum())
            for class_id in class_ids
        },
    }

    if y_proba is not None:
        y_proba = np.asarray(y_proba)
        auprc = {}
        for class_id in class_ids:
            if class_id >= y_proba.shape[1]:
                continue
            binary = (y_true == class_id).astype(int)
            if binary.sum() == 0:
                score = float("nan")
            else:
                score = float(average_precision_score(binary, y_proba[:, class_id]))
            class_name = names[class_id] if class_id < len(names) else str(class_id)
            auprc[class_name] = score
        output["per_class_auprc"] = auprc
    return output


def bootstrap_mean_ci(values: np.ndarray, seed: int, n_resamples: int = 10000, alpha: float = 0.05) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return {"mean": float("nan"), "low": float("nan"), "high": float("nan")}
    samples = rng.choice(values, size=(n_resamples, len(values)), replace=True).mean(axis=1)
    return {
        "mean": float(values.mean()),
        "low": float(np.quantile(samples, alpha / 2)),
        "high": float(np.quantile(samples, 1 - alpha / 2)),
    }


def paired_bootstrap_pvalue(
    baseline_scores: np.ndarray,
    treatment_scores: np.ndarray,
    seed: int,
    n_resamples: int = 10000,
) -> dict[str, float]:
    baseline_scores = np.asarray(baseline_scores, dtype=float)
    treatment_scores = np.asarray(treatment_scores, dtype=float)
    if baseline_scores.shape != treatment_scores.shape:
        raise ValueError("Paired bootstrap requires equal-shaped score arrays.")
    rng = np.random.default_rng(seed)
    n = len(baseline_scores)
    deltas = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        deltas.append(float(treatment_scores[idx].mean() - baseline_scores[idx].mean()))
    deltas_array = np.asarray(deltas)
    observed = float(treatment_scores.mean() - baseline_scores.mean())
    p_value = float((deltas_array <= 0).mean())
    return {
        "observed_delta": observed,
        "p_value_one_sided_treatment_gt_baseline": p_value,
        "ci_low": float(np.quantile(deltas_array, 0.025)),
        "ci_high": float(np.quantile(deltas_array, 0.975)),
    }
