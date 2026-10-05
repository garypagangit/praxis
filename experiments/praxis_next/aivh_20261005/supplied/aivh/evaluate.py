"""Evaluation harness: random / LOLO / LOEO splits, timing-free ablation,
conformal gate coverage, bootstrap CIs. Produces the tables in EXPERIMENT.md.

Binary task by default: agent (positive) vs human (negative). Bots, when
present, are reported in a separate three-way block.
"""
from __future__ import annotations

import json
import numpy as np
from collections import defaultdict
from sklearn.metrics import roc_auc_score, average_precision_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold

from .features import to_matrix, feature_names
from .models import make_model
from .gate import ConformalGate, gate_report

POS = "agent"
NEG = "human"


def _bin(y):
    return np.array([1 if v == POS else 0 for v in y])


def _auroc_ci(y, scores, n_boot=1000, seed=0):
    rng = np.random.default_rng(seed)
    y, scores = np.asarray(y), np.asarray(scores)
    base = roc_auc_score(y, scores) if len(set(y)) > 1 else float("nan")
    boots = []
    idx = np.arange(len(y))
    for _ in range(n_boot):
        s = rng.choice(idx, len(idx), replace=True)
        if len(set(y[s])) < 2:
            continue
        boots.append(roc_auc_score(y[s], scores[s]))
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (float("nan"), float("nan")))
    return round(base, 4), round(lo, 4), round(hi, 4)


def _fit_predict(Xtr, ytr, Xte, kind):
    m = make_model(kind)
    m.fit(Xtr, ytr)
    classes = list(m.classes_)
    proba = m.predict_proba(Xte)
    pos_col = classes.index(POS)
    return m, proba, proba[:, pos_col], classes


def _metrics_block(ybin_te, pos_score, yte_pred=None):
    out = {}
    out["auroc"], out["auroc_lo"], out["auroc_hi"] = _auroc_ci(ybin_te, pos_score)
    out["auprc"] = round(average_precision_score(ybin_te, pos_score), 4) if len(set(ybin_te)) > 1 else None
    pred = (pos_score >= 0.5).astype(int)
    out["balanced_acc"] = round(balanced_accuracy_score(ybin_te, pred), 4)
    out["f1"] = round(f1_score(ybin_te, pred, zero_division=0), 4)
    out["n_test"] = int(len(ybin_te))
    out["n_pos"] = int(sum(ybin_te))
    return out


def run_random_kfold(sessions, kind="gbm", k=5, exclude_families=(), alpha=0.05, seed=0):
    sessions = [s for s in sessions if s.label in (POS, NEG)]
    X, y, groups, names = to_matrix(sessions, exclude_families)
    y = np.array(y)
    ybin = _bin(y)
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
    fold_metrics, gate_metrics = [], []
    for fold, (tr, te) in enumerate(skf.split(X, ybin)):
        # carve a calibration slice out of train for the gate
        rng = np.random.default_rng(seed + fold)
        tr = rng.permutation(tr)
        cut = int(len(tr) * 0.75)
        tr_fit, tr_cal = tr[:cut], tr[cut:]
        m, proba_te, pos_te, classes = _fit_predict(X[tr_fit], y[tr_fit], X[te], kind)
        fold_metrics.append(_metrics_block(ybin[te], pos_te))
        proba_cal = m.predict_proba(X[tr_cal])
        gate = ConformalGate(alpha=alpha).calibrate(proba_cal, y[tr_cal], classes)
        gate_metrics.append(gate_report(gate, proba_te, y[te]))
    return {"split": "random_kfold", "kind": kind, "k": k,
            "exclude_families": list(exclude_families),
            "folds": fold_metrics, "mean_auroc": round(np.nanmean([f["auroc"] for f in fold_metrics]), 4),
            "gate": gate_metrics,
            "gate_mean_coverage": round(np.mean([g["coverage"] for g in gate_metrics]), 4),
            "gate_mean_decided_error": round(np.mean([g["decided_error"] for g in gate_metrics]), 4),
            "n_features": len(names)}


def run_leave_one_group_out(sessions, group_key, kind="gbm", exclude_families=(), alpha=0.05, seed=0):
    """Hold out one agent group (LLM family or environment) at a time.

    The negative class (humans) has no counterpart group, so to keep every
    test fold two-class we split the negatives into disjoint per-fold slices:
    each held-out agent group is paired with its own held-out slice of humans
    for test, while the remaining humans stay in train. This keeps the shift
    on the *positive* side (unseen model / unseen environment) — the quantity
    RQ2/RQ3 are about — without leaking the same humans into train and test.
    """
    sessions = [s for s in sessions if s.label in (POS, NEG)]
    X, y, groups, names = to_matrix(sessions, exclude_families)
    y = np.array(y); ybin = _bin(y)
    g = np.array(groups[group_key])
    pos_idx = np.where(ybin == 1)[0]
    neg_idx = np.where(ybin == 0)[0]
    held = sorted(set(g[i] for i in pos_idx))                 # agent groups only
    # pre-partition negatives into len(held) disjoint slices
    rng = np.random.default_rng(seed)
    neg_perm = rng.permutation(neg_idx)
    neg_slices = {h: neg_perm[i::len(held)] for i, h in enumerate(held)} if held else {}
    results = []
    for h in held:
        te_pos = pos_idx[g[pos_idx] == h]
        te_neg = neg_slices[h]
        te = np.concatenate([te_pos, te_neg])
        tr_pos = pos_idx[g[pos_idx] != h]
        tr_neg = np.setdiff1d(neg_idx, te_neg, assume_unique=False)
        tr = np.concatenate([tr_pos, tr_neg])
        if len(te_pos) == 0 or len(te_neg) == 0 or len(set(y[tr])) < 2:
            continue
        tr = rng.permutation(tr)
        cut = int(len(tr) * 0.75)
        tr_fit, tr_cal = tr[:cut], tr[cut:]
        if len(set(y[tr_cal])) < 2:        # ensure calibration has both classes
            tr_fit, tr_cal = tr[: int(len(tr) * 0.6)], tr[int(len(tr) * 0.6):]
        m, proba_te, pos_te, classes = _fit_predict(X[tr_fit], y[tr_fit], X[te], kind)
        block = _metrics_block(ybin[te], pos_te)
        block["held_out"] = str(h)
        block["n_test_pos"] = int(len(te_pos))
        block["n_test_neg"] = int(len(te_neg))
        gate = ConformalGate(alpha=alpha).calibrate(m.predict_proba(X[tr_cal]), y[tr_cal], classes)
        block["gate"] = gate_report(gate, proba_te, y[te])
        results.append(block)
    valid = [r for r in results if not np.isnan(r["auroc"])]
    return {"split": f"leave_one_{group_key}_out", "kind": kind,
            "exclude_families": list(exclude_families),
            "held": results,
            "mean_auroc": round(np.nanmean([r["auroc"] for r in valid]), 4) if valid else None,
            "min_auroc": round(np.nanmin([r["auroc"] for r in valid]), 4) if valid else None}


def feature_importance(sessions, kind="gbm", exclude_families=(), seed=0, top=20):
    from sklearn.inspection import permutation_importance
    sessions = [s for s in sessions if s.label in (POS, NEG)]
    X, y, groups, names = to_matrix(sessions, exclude_families)
    y = np.array(y)
    m = make_model(kind); m.fit(X, y)
    r = permutation_importance(m, X, y, n_repeats=10, random_state=seed, scoring="roc_auc")
    order = np.argsort(r.importances_mean)[::-1][:top]
    return [{"feature": names[i], "importance": round(float(r.importances_mean[i]), 4),
             "std": round(float(r.importances_std[i]), 4)} for i in order]


def full_suite(sessions, out_dir, kind="gbm", alpha=0.05, seed=0):
    from pathlib import Path
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    report = {"meta": {"kind": kind, "alpha": alpha, "seed": seed,
                       "n_sessions": len(sessions),
                       "label_counts": dict(_counts(sessions))}}
    report["RQ1_random"] = run_random_kfold(sessions, kind, alpha=alpha, seed=seed)
    report["RQ4_timing_free"] = run_random_kfold(sessions, kind, exclude_families=("T",), alpha=alpha, seed=seed)
    report["RQ4_timing_only"] = run_random_kfold(sessions, kind, exclude_families=("C", "S", "E"), alpha=alpha, seed=seed)
    report["RQ2_LOLO"] = run_leave_one_group_out(sessions, "family", kind, alpha=alpha, seed=seed)
    report["RQ2_LOLO_timing_free"] = run_leave_one_group_out(sessions, "family", kind, exclude_families=("T",), alpha=alpha, seed=seed)
    report["RQ3_LOEO"] = run_leave_one_group_out(sessions, "environment", kind, alpha=alpha, seed=seed)
    try:
        report["feature_importance"] = feature_importance(sessions, kind, seed=seed)
    except Exception as e:
        report["feature_importance_error"] = str(e)
    (out / f"report_{kind}.json").write_text(json.dumps(report, indent=2))
    return report


def _counts(sessions):
    c = defaultdict(int)
    for s in sessions:
        c[s.label] += 1
    return c
