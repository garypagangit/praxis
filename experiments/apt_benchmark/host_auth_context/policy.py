"""Fixed comparison of independent stage flags and review-only abstention."""
from __future__ import annotations

import numpy as np
from ..host_history_exfil.run import alert_metrics, f1_threshold

BUDGETS = (.001, .005, .01, .02)
MIN_NEGATIVE = 100
MIN_POSITIVE = 20


def tail_cut(negative_scores, budget):
    scores = np.sort(np.asarray(negative_scores))
    if not len(scores):
        raise ValueError("No calibration negatives")
    allowed = int(np.floor(budget * len(scores)))
    return float(scores[len(scores) - allowed - 1])


def decisions(y, base_prediction, exfil, unsupported):
    """Do not score two labels as a resolved correct stage."""
    y, base_prediction = np.asarray(y), np.asarray(base_prediction)
    exfil, unsupported = np.asarray(exfil, bool), np.asarray(unsupported, bool)
    movement = base_prediction == 2
    both = movement & exfil
    review_union = (base_prediction != 0) | exfil
    unresolved = both | (exfil & unsupported)
    auto_exfil = exfil & ~movement & ~unsupported
    out = {"exfil_flag": alert_metrics(y, exfil), "automatic_exfil": alert_metrics(y, auto_exfil),
           "review_union_count": int(review_union.sum()),
           "review_union_benign_count": int(np.sum(review_union & (y == 0))),
           "baseline_review_count": int(np.sum(base_prediction != 0)),
           "additional_review_count": int(np.sum(exfil & (base_prediction == 0))),
           "retained_baseline_alerts": bool(np.all(review_union[base_prediction != 0])),
           "by_true_class": {}}
    for k, name in enumerate(["Benign", "OtherAttackStage", "LateralMovement", "DataExfiltration"]):
        mask = y == k
        out["by_true_class"][name] = {"support": int(mask.sum()), "movement_flag": int(np.sum(mask & movement)),
            "exfil_flag": int(np.sum(mask & exfil)), "both_flags": int(np.sum(mask & both)),
            "unsupported_exfil_review": int(np.sum(mask & exfil & unsupported)), "unresolved_review": int(np.sum(mask & unresolved)),
            "resolved_movement_only": int(np.sum(mask & movement & ~exfil)), "resolved_exfil_only": int(np.sum(mask & auto_exfil)),
            "any_review": int(np.sum(mask & review_union)), "neither_target_flag": int(np.sum(mask & ~movement & ~exfil))}
    return out


def evaluate(y_cal, cal_score, cal_role, y_test, test_score, test_role, base_prediction):
    """No test truth enters threshold or role-support construction."""
    supports = {str(r): {"positive": int(np.sum((cal_role == r) & (y_cal == 3))),
                         "negative": int(np.sum((cal_role == r) & (y_cal != 3)))} for r in range(16)}
    unsupported = np.array([supports[str(r)]["positive"] < MIN_POSITIVE or supports[str(r)]["negative"] < MIN_NEGATIVE for r in test_role])
    out = {"calibration_role_support": supports, "policies": {}}
    settings = [("calibration_f1", None)] + [(f"tail_{b:g}", b) for b in BUDGETS]
    for name, budget in settings:
        cut = f1_threshold(y_cal == 3, cal_score) if budget is None else tail_cut(cal_score[y_cal != 3], budget)
        variants = {"global": np.full(len(test_score), cut)}
        role_cuts = {}
        if budget is not None:
            for r in range(16):
                neg = (cal_role == r) & (y_cal != 3)
                role_cuts[str(r)] = tail_cut(cal_score[neg], budget) if neg.sum() >= MIN_NEGATIVE else cut
            variants["role_tail"] = np.asarray([role_cuts[str(r)] for r in test_role])
        for variant, cuts in variants.items():
            flags = test_score > cuts
            out["policies"][f"{name}__{variant}"] = {"global_cut": cut, "role_cuts": role_cuts if variant == "role_tail" else {},
                "global_calibration_nonexfil_rate": float(np.mean(cal_score[y_cal != 3] > cut)),
                "all_test": decisions(y_test, base_prediction, flags, unsupported),
                "role_strata": {str(r): decisions(y_test[test_role == r], base_prediction[test_role == r], flags[test_role == r], unsupported[test_role == r]) for r in np.unique(test_role)}}
    return out
