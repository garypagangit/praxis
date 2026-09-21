"""Finite, tie-preserving selection using only a declared selection partition."""
from __future__ import annotations

import numpy as np
from fractions import Fraction
from sklearn.metrics import average_precision_score, roc_auc_score


def frontier(scores, y, normal_index, lateral_index):
    scores, y = np.asarray(scores, dtype=float), np.asarray(y)
    if scores.ndim != 1 or scores.shape != y.shape or not len(y):
        raise ValueError("Scores and labels must be nonempty matching vectors")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Attack probabilities must be finite and within [0,1]")
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    ends = np.r_[np.flatnonzero(np.diff(sorted_scores)), len(y) - 1]
    normal, lateral = y[order] == normal_index, y[order] == lateral_index
    n, l = int(normal.sum()), int(lateral.sum())
    if not n or not l:
        raise ValueError("Selection requires both benign and lateral examples")
    return {"threshold": np.r_[-1.0, sorted_scores[ends]],
            "fp": np.r_[n, n - np.cumsum(normal)[ends]],
            "lateral_tp": np.r_[l, l - np.cumsum(lateral)[ends]],
            "benign_n": n, "lateral_n": l}


def eligible(f, reference_lateral_tp=None):
    # Integer comparisons preserve exact budgets at tied-score boundaries.
    keep = (f["fp"] * 100 <= f["benign_n"]) & (f["lateral_tp"] * 10 >= 9 * f["lateral_n"])
    if reference_lateral_tp is not None:
        keep &= 100 * (f["lateral_tp"] - reference_lateral_tp) >= -3 * f["lateral_n"]
    return np.flatnonzero(keep)


def select_policies(cells, y, normal_index, lateral_index):
    """Cells arrive in frozen model/scheme order. No verification data accepted."""
    if not cells or len({c["cell_id"] for c in cells}) != len(cells):
        raise ValueError("Missing or duplicate selection cells")
    fronts = [frontier(c["scores"], y, normal_index, lateral_index) for c in cells]
    options = [(k, int(i)) for k, f in enumerate(fronts) for i in eligible(f)]
    if not options:
        return {"status": "INFEASIBLE", "reason": "No control attains selection lateral recall >=90% and benign FPR <=1%", "choices": {}}
    ref_k, ref_i = min(options, key=lambda p: (-int(fronts[p[0]]["lateral_tp"][p[1]]), int(fronts[p[0]]["fp"][p[1]]), p[0], -float(fronts[p[0]]["threshold"][p[1]])))
    ref_tp = int(fronts[ref_k]["lateral_tp"][ref_i])
    valid = [(k, int(i)) for k, f in enumerate(fronts) for i in eligible(f, ref_tp)]
    candidate = min(valid, key=lambda p: (int(fronts[p[0]]["fp"][p[1]]), -int(fronts[p[0]]["lateral_tp"][p[1]]), p[0], -float(fronts[p[0]]["threshold"][p[1]])))
    local = [(ref_k, int(i)) for i in eligible(fronts[ref_k], ref_tp)]
    ablation = min(local, key=lambda p: (int(fronts[p[0]]["fp"][p[1]]), -int(fronts[p[0]]["lateral_tp"][p[1]]), -float(fronts[p[0]]["threshold"][p[1]])))
    def encode(pair):
        k, i = pair; f = fronts[k]
        return {"cell_id": cells[k]["cell_id"], "threshold": float(f["threshold"][i]),
                "selection_benign_fp": int(f["fp"][i]), "selection_lateral_tp": int(f["lateral_tp"][i]),
                "selection_benign_n": f["benign_n"], "selection_lateral_n": f["lateral_n"]}
    choices = {"reference": encode((ref_k, ref_i)), "candidate": encode(candidate), "threshold_only": encode(ablation)}
    return {"status": "SELECTED", "choices": choices,
            "candidate_equals_threshold_only": choices["candidate"] == choices["threshold_only"],
            "candidate_uses_reference_detector": choices["candidate"]["cell_id"] == choices["reference"]["cell_id"]}


def alert_metrics(y, scores, flags, classes, normal_index):
    y, scores, flags = np.asarray(y), np.asarray(scores), np.asarray(flags, dtype=bool)
    if y.shape != flags.shape or y.shape != scores.shape:
        raise ValueError("Metric arrays have different shapes")
    normal = y == normal_index; attack = ~normal
    fp, tp = int((normal & flags).sum()), int((attack & flags).sum())
    fn, tn = int((attack & ~flags).sum()), int((normal & ~flags).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / int(attack.sum()) if attack.any() else None
    return {"rows": len(y), "benign_n": int(normal.sum()), "attack_n": int(attack.sum()),
            "fp": fp, "tp": tp, "fn": fn, "tn": tn, "benign_fpr": fp / int(normal.sum()) if normal.any() else None,
            "attack_recall": recall, "attack_precision": precision,
            "attack_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            "alert_fraction": float(flags.mean()), "roc_auc": float(roc_auc_score(attack, scores)) if normal.any() and attack.any() else None,
            "average_precision": float(average_precision_score(attack, scores)) if attack.any() else None,
            "per_stage": {name: {"n": int((y == k).sum()), "detected": int(((y == k) & flags).sum()),
                                 "recall": float(flags[y == k].mean()) if (y == k).any() else None} for k, name in enumerate(classes) if k != normal_index}}


def point_gate(rows, expected):
    """Descriptive mean-seed screen; never an independent confirmation bound."""
    selected = [r for r in rows if r["selection_status"] == "SELECTED"]
    if len(rows) != expected:
        return {"status": "INCOMPLETE", "pairs": len(selected), "expected_pairs": expected}
    if len(selected) != expected:
        return {"status": "INFEASIBLE", "pairs": len(selected), "expected_pairs": expected,
                "reason": "All prespecified seeds must have a selected policy; no averaging only feasible survivors"}
    c = [r["partitions"]["verification"]["candidate"] for r in selected]
    b = [r["partitions"]["verification"]["reference"] for r in selected]
    cf = float(np.mean([x["benign_fpr"] for x in c])); bf = float(np.mean([x["benign_fpr"] for x in b]))
    cr = float(np.mean([x["per_stage"]["LateralMovement"]["recall"] for x in c])); br = float(np.mean([x["per_stage"]["LateralMovement"]["recall"] for x in b]))
    mean_f = lambda values: sum((Fraction(x["fp"], x["benign_n"]) for x in values), Fraction()) / len(values)
    mean_r = lambda values: sum((Fraction(x["per_stage"]["LateralMovement"]["detected"], x["per_stage"]["LateralMovement"]["n"]) for x in values), Fraction()) / len(values)
    exact_cf, exact_bf, exact_cr, exact_br = mean_f(c), mean_f(b), mean_r(c), mean_r(b)
    guards = {"false_alarm_reduction_at_least_20pct": exact_cf < Fraction(4, 5) * exact_bf,
              "lateral_loss_less_than_3pp": exact_cr - exact_br > -Fraction(3, 100),
              "lateral_recall_at_least_90pct": exact_cr >= Fraction(9, 10), "benign_fpr_at_most_1pct": exact_cf <= Fraction(1, 100)}
    return {"status": "DEVELOPMENT_PROMISING" if all(guards.values()) else "DEVELOPMENT_NEGATIVE",
            "pairs": len(selected), "expected_pairs": expected, "guards": guards,
            "candidate_mean_fpr": cf, "reference_mean_fpr": bf, "candidate_mean_lateral_recall": cr,
            "reference_mean_lateral_recall": br, "relative_fpr_reduction": 1 - cf / bf if bf else None,
            "candidate_worst_seed_fpr": max(x["benign_fpr"] for x in c),
            "candidate_worst_seed_lateral_recall": min(x["per_stage"]["LateralMovement"]["recall"] for x in c),
            "interpretation": "Mean-seed point estimates on an exposed-source verification partition; no confidence certificate, independent replication, or novelty claim"}
