"""Bounded exact full-reference scoring and training-only resource qualification."""
from __future__ import annotations

import math
import time

import numpy as np
import torch
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.neighbors import NearestNeighbors


class ResourceDeadline(RuntimeError):
    pass


def synchronize(device):
    if torch.device(device).type == "cuda":
        torch.cuda.synchronize(device)


def author_standardize(raw):
    """Preserve float32 author mean/std and division; fail instead of adding a floor."""
    raw = np.asarray(raw)
    if raw.dtype != np.float32 or raw.ndim != 2 or not len(raw) or not np.isfinite(raw).all():
        raise ValueError("Expected finite nonempty float32 author embeddings")
    mean, scale = raw.mean(axis=0), raw.std(axis=0)
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("SOURCE_NUMERICAL_HOLD: zero or nonfinite author embedding std")
    scaled = (raw - mean) / scale
    if not np.isfinite(scaled).all():
        raise ValueError("SOURCE_NUMERICAL_HOLD: nonfinite standardized embeddings")
    return scaled, mean, scale


class ExactFullReferenceKNN:
    """Every bank row retained, float64 direct Euclidean cdist, bounded tiles.

    Direct differences avoid cancellation in squared-norm matrix identities.
    Duplicate reference rows retain their multiplicity, including self matches.
    """
    def __init__(self, bank, k, device="cuda:0", query_batch_size=128, reference_batch_size=16384):
        bank = np.asarray(bank)
        if bank.ndim != 2 or not np.isfinite(bank).all() or not 1 <= k <= len(bank):
            raise ValueError("Invalid finite reference bank or k")
        if query_batch_size < 1 or reference_batch_size < 1:
            raise ValueError("Chunk sizes must be positive")
        self.device = torch.device(device)
        self.k = int(k)
        self.query_batch_size = int(query_batch_size)
        self.reference_batch_size = int(reference_batch_size)
        self.bank = torch.as_tensor(np.ascontiguousarray(bank), dtype=torch.float64, device=self.device)
        synchronize(self.device)

    def score(self, queries, check_budget=lambda: None):
        queries = np.asarray(queries)
        if queries.ndim != 2 or queries.shape[1] != self.bank.shape[1] or not np.isfinite(queries).all():
            raise ValueError("Invalid query matrix")
        started = time.perf_counter()
        output = np.empty(len(queries), dtype=np.float64)
        with torch.no_grad():
            for offset in range(0, len(queries), self.query_batch_size):
                check_budget()
                query = torch.as_tensor(np.ascontiguousarray(queries[offset:offset + self.query_batch_size]),
                                        dtype=torch.float64, device=self.device)
                best = torch.empty((len(query), 0), dtype=torch.float64, device=self.device)
                for reference_offset in range(0, len(self.bank), self.reference_batch_size):
                    check_budget()
                    reference = self.bank[reference_offset:reference_offset + self.reference_batch_size]
                    distances = torch.cdist(query, reference, p=2, compute_mode="donot_use_mm_for_euclid_dist")
                    combined = torch.cat((best, distances), dim=1)
                    best = torch.topk(combined, min(self.k, combined.shape[1]), largest=False,
                                      sorted=False, dim=1).values
                output[offset:offset + len(query)] = best.mean(dim=1).cpu().numpy()
        synchronize(self.device)
        return output, {"seconds": time.perf_counter() - started, "query_rows": len(queries),
                        "reference_rows": len(self.bank), "k": self.k, "dimension": self.bank.shape[1],
                        "reference_sampling": False, "reference_duplicates_preserved": True,
                        "search": "exact", "distance": "direct_float64_euclidean",
                        "query_batch_size": self.query_batch_size,
                        "reference_batch_size": self.reference_batch_size, "device": str(self.device)}


def numerical_check(bank, queries, k, device, settings):
    bank64, query64 = np.asarray(bank, dtype=np.float64), np.asarray(queries, dtype=np.float64)
    # Small qualification arrays only: direct independent differences, no norm identity.
    direct = np.sqrt(np.sum((query64[:, None, :] - bank64[None, :, :]) ** 2, axis=2))
    reference = np.sort(direct, axis=1)[:, :k].mean(axis=1)
    sklearn = NearestNeighbors(n_neighbors=k, algorithm="brute", metric="euclidean", n_jobs=1)
    sklearn.fit(bank64)
    sklearn_reference = sklearn.kneighbors(query64, return_distance=True)[0].mean(axis=1)
    scorer = ExactFullReferenceKNN(bank, k, device, settings["query_batch_size"], settings["reference_batch_size"])
    actual, timing = scorer.score(queries)
    if not np.allclose(actual, reference, rtol=settings["numerical_rtol"], atol=settings["numerical_atol"]):
        raise RuntimeError("Exact kNN disagrees with independent direct-distance qualification")
    return {"status": "PASS", "reference_rows": len(bank), "queries": len(queries), "k": k,
            "max_absolute_error": float(np.max(np.abs(actual - reference))),
            "decisive_oracle": "NumPy float64 direct differences and exhaustive sort",
            "sklearn_max_absolute_discrepancy_from_direct": float(np.max(np.abs(sklearn_reference - reference))),
            "sklearn_comparison_is_diagnostic": True,
            "rtol": settings["numerical_rtol"], "atol": settings["numerical_atol"], "timing": timing}


def synthetic_numerical_check(device, settings):
    rng = np.random.default_rng(90210)
    bank = rng.normal(size=(37, 64))
    bank[:24] = bank[0]  # More duplicates than k: exact zero distances must remain zero.
    query = np.concatenate((bank[:10], rng.normal(size=(7, 64))))
    return numerical_check(bank, query, 10, device, settings)


def resource_estimate(*, epoch_seconds, embedding_seconds, test_embedding_seconds,
                      query_seconds, sample_queries, reference_rows, test_rows,
                      serialization_seconds, index_seconds, remaining_seconds, resources, epochs=50):
    values = (epoch_seconds, embedding_seconds, test_embedding_seconds, query_seconds,
              serialization_seconds, index_seconds, remaining_seconds)
    if any(not math.isfinite(v) or v < 0 for v in values) or sample_queries < 1:
        raise ValueError("Invalid resource measurements")
    normalizer_rows = min(50000, reference_rows)
    per_query = query_seconds / sample_queries
    components = {"remaining_training": epoch_seconds * (epochs - 1),
                  "final_training_embeddings": embedding_seconds,
                  "evaluation_embeddings": test_embedding_seconds,
                  "full_reference_normalizer": per_query * normalizer_rows,
                  "full_evaluation_scoring": per_query * test_rows,
                  "reference_transfer": index_seconds,
                  "artifact_serialization": serialization_seconds * (1 + test_rows / reference_rows)}
    predicted = sum(components.values()) * resources["estimate_multiplier"] + resources["safety_seconds"]
    return {"status": "PASS" if predicted <= remaining_seconds else "NOT_RUN_RESOURCE_HOLD",
            "remaining_seconds": remaining_seconds, "predicted_remaining_seconds": predicted,
            "components_seconds_before_multiplier": components,
            "estimate_multiplier": resources["estimate_multiplier"], "safety_seconds": resources["safety_seconds"],
            "measured_full_epoch_seconds": epoch_seconds, "measured_sample_queries": sample_queries,
            "measured_sample_seconds": query_seconds, "normalizer_queries": normalizer_rows,
            "planned_evaluation_queries": test_rows, "reference_rows": reference_rows,
            "reference_sampling": False, "qualification_uses_evaluation_arrays_or_labels": False,
            "estimate_is_not_runtime_guarantee": True}


def confusion(y, score, threshold):
    predicted = np.asarray(score) >= threshold
    positive = np.asarray(y) == 1
    tp, fp = int(np.count_nonzero(predicted & positive)), int(np.count_nonzero(predicted & ~positive))
    fn, tn = int(np.count_nonzero(~predicted & positive)), int(np.count_nonzero(~predicted & ~positive))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall,
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "threshold": float(threshold), "threshold_uses_test_labels": True, "deployment_readiness": False}


def oracle_metrics(y, scores, recall_target):
    y, scores = np.asarray(y), np.asarray(scores)
    if y.ndim != 1 or scores.shape != y.shape or not np.isfinite(scores).all() or set(np.unique(y)) != {0, 1} or not 0 < recall_target <= 1:
        raise ValueError("Oracle metrics need finite scores and both binary classes")
    precision, recall, thresholds = precision_recall_curve(y, scores)
    author_index = -1
    for index in range(len(recall)):
        if recall[index] < recall_target:
            author_index = index - 1
            break
    if not len(thresholds) or not 0 <= author_index < len(thresholds):
        raise ValueError("SOURCE_NUMERICAL_HOLD: undefined author threshold endpoint")
    f1 = 2 * precision * recall / (recall + precision + 1e-9)
    maximum_index = int(np.argmax(f1[:-1]))
    return {"auroc": float(roc_auc_score(y, scores)), "average_precision": float(average_precision_score(y, scores)),
            "author_recall_rule": {**confusion(y, scores, thresholds[author_index]),
                                   "target_recall": recall_target, "threshold_index": author_index,
                                   "selection_rule": "last author precision-recall threshold before recall falls below target"},
            "supplemental_max_f1_oracle": {**confusion(y, scores, thresholds[maximum_index]),
                                           "threshold_index": maximum_index},
            "all_threshold_metrics_label_selected": True, "novelty_claimed": False,
            "operational_threshold_evaluated": False}
