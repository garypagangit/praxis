"""Fixed-configuration, cross-fitted specialist/feature pilot.

Existing SCVIC partitions have been exposed in earlier studies. This is a new
development comparison, never an untouched test or incident-level replication.
No calibration or test row enters a fitted base or fusion model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, roc_auc_score)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits


DATA_SHA = "8e8a7474d4db03b78977a3c6a48be083d60d7648dd7548788037db721e80e565"
CLASSES = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]
SEEDS = [20260922, 20260923, 20260924]
PARAMETERS = {
    "xgboost": {"n_estimators": 300, "max_depth": 3, "learning_rate": .05, "reg_lambda": 1.0},
    "lightgbm": {"n_estimators": 300, "num_leaves": 15, "learning_rate": .05, "min_child_samples": 5, "reg_lambda": 1.0},
}
BUDGETS = [0.001, 0.005, 0.01, 0.02]
DERIVED = ["log_total_bytes", "log_total_packets", "log_duration_raw",
           "forward_byte_fraction", "forward_packet_fraction", "byte_asymmetry",
           "packet_asymmetry", "log_byte_direction_ratio", "log_packet_direction_ratio",
           "forward_bytes_per_packet", "backward_bytes_per_packet", "mean_packet_direction_ratio",
           "flow_iat_cv", "forward_iat_cv", "backward_iat_cv", "packet_length_cv",
           "active_cv", "byte_packet_fraction_difference"]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def utc():
    return datetime.now(timezone.utc).isoformat()


def protocol():
    return {
        "study": "Exfiltration attribution and stage-expert fusion", "version": 1,
        "status": "FROZEN_BEFORE_THIS_PILOT_FITS", "seeds": SEEDS, "data_sha256": DATA_SHA,
        "classes": CLASSES, "fit_budget": {"NormalTraffic": 1024, "each_attack_stage": 32},
        "fit_sampling": "Hash EXFIL_STAGE_V1|seed|feature_group per class, original fit pool only",
        "crossfit_folds": 3, "model_parameters": PARAMETERS, "class_weight": None,
        "models": ["xgboost", "lightgbm"], "threads": 4,
        "feature_views": ["raw_73", "raw_plus_18_derived"], "derived_features": DERIVED,
        "fusion": "Unweighted fixed averages and L2 logistic regression C=1 trained on strictly out-of-fold clipped logit scores; no hyperparameter tuning",
        "stage_family_selection": "Per class, highest fit-OOF average precision, ties xgboost; only used in a fixed selector arm, never to train learned fusion",
        "threshold_selection": "Original calibration only: maximize exfil F1; ties higher threshold. Also empirical tail thresholds separately on normal and all non-exfil rows with strict score>threshold",
        "descriptive_fpr_design_budgets": BUDGETS,
        "primary_exfil_endpoint": "Test exfil-vs-all average precision; exact-exfil F1/precision/recall and false positives by true stage at calibration-selected threshold",
        "primary_stage_endpoint": "Six-class macro-F1 and each stage F1/AP/recall/precision; binary any-attack detection reported separately",
        "comparisons": ["features: engineered minus raw within same model/task", "specialization: exfil specialist minus general exfil score with same model/features", "fusion: learned/fixed fusion versus engineered general models, their average, and OOF learned general-only fusion"],
        "success_policy": "Report all directions and stage costs; no arbitrary 90% recall floor or pass/fail improvement magnitude",
        "evaluation_status": "Previously exposed SCVIC development partitions; fitting seeds are not independent attacks",
        "not_measured": ["early detection", "temporal progression reconstruction", "unseen campaign generalization", "missing logs", "new algorithm novelty"],
    }


def engineered(X, names):
    """Deterministic row-local re-encodings; direction is flow-forward, NOT egress."""
    names = list(names)
    def v(name):
        # Missingness propagates into derived values, then fold-local imputation.
        return np.maximum(np.asarray(X[:, names.index(name)], dtype=float), 0)
    bf, bb = v("Total Length of Fwd Packet"), v("Total Length of Bwd Packet")
    pf, pb = v("Total Fwd Packet"), v("Total Bwd packets")
    b, p = bf + bb, pf + pb
    fb, fp = bf / (1 + b), pf / (1 + p)
    out = [np.log1p(b), np.log1p(p), np.log1p(v("Flow Duration")), fb, fp,
           (bf - bb) / (1 + b), (pf - pb) / (1 + p),
           np.log1p(bf) - np.log1p(bb), np.log1p(pf) - np.log1p(pb),
           bf / (1 + pf), bb / (1 + pb), (1 + bf / (1 + pf)) / (1 + bb / (1 + pb)),
           v("Flow IAT Std") / (1 + v("Flow IAT Mean")),
           v("Fwd IAT Std") / (1 + v("Fwd IAT Mean")),
           v("Bwd IAT Std") / (1 + v("Bwd IAT Mean")),
           v("Packet Length Std") / (1 + v("Packet Length Mean")),
           v("Active Std") / (1 + v("Active Mean")), fb - fp]
    result = np.column_stack([X, *out])
    if np.isinf(result).any():
        raise ValueError("Infinite derived features")
    return result


def supports(data, seed):
    indices = []
    for label, name in enumerate(CLASSES):
        pool = np.flatnonzero((data["split"] == 0) & (data["y"] == label))
        order = sorted(pool, key=lambda i: hashlib.sha256(f"EXFIL_STAGE_V1|{seed}|{data['group_sha256'][i]}".encode("ascii")).digest())
        count = 1024 if name == "NormalTraffic" else 32
        if len(order) < count:
            raise ValueError("Insufficient fitting examples")
        indices.extend(order[:count])
    return np.asarray(indices, dtype=np.int64)


def make_model(family, seed):
    settings = dict(PARAMETERS[family], random_state=seed, n_jobs=4)
    if family == "xgboost":
        from xgboost import XGBClassifier
        classifier = XGBClassifier(**settings, tree_method="hist", device="cpu")
    else:
        from lightgbm import LGBMClassifier
        classifier = LGBMClassifier(**settings, verbosity=-1, deterministic=True, force_col_wise=True)
    return Pipeline([("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("classifier", classifier)])


def crossfit(family, X, y, fold_ids, seed, Xcal, Xtest):
    n_classes = len(np.unique(y))
    oof = np.full((len(y), n_classes), np.nan)
    folds = []
    for fold in range(3):
        train, validation = np.flatnonzero(fold_ids != fold), np.flatnonzero(fold_ids == fold)
        if set(np.unique(y[train])) != set(range(n_classes)):
            raise ValueError("A fitting fold lacks a class")
        fitted = make_model(family, seed).fit(X[train], y[train])
        oof[validation] = fitted.predict_proba(X[validation])
        folds.append({"fold": fold, "train_rows": len(train), "validation_rows": len(validation),
                      "train_local_indices": train.tolist(), "validation_local_indices": validation.tolist()})
    fitted = make_model(family, seed).fit(X, y)
    if not np.isfinite(oof).all():
        raise ValueError("OOF predictions incomplete")
    return {"oof": oof, "cal": fitted.predict_proba(Xcal), "test": fitted.predict_proba(Xtest)}, fitted, folds


def logits(values):
    p = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(p) - np.log1p(-p)


def learned_fusion(parts, y, binary=False):
    model = LogisticRegression(C=1, max_iter=3000, solver="lbfgs", random_state=0)
    model.fit(np.column_stack([logits(part["oof"]) for part in parts]), y)
    scores = {split: model.predict_proba(np.column_stack([logits(part[split]) for part in parts])) for split in ("cal", "test")}
    if binary:
        scores = {split: p[:, 1] for split, p in scores.items()}
    return scores, model


def normalize(p):
    sums = p.sum(axis=1, keepdims=True)
    return np.divide(p, sums, out=np.full_like(p, 1 / p.shape[1]), where=sums > 0)


def threshold_f1(y, score):
    """Find score>threshold frontier with tied scores kept together."""
    y, score = np.asarray(y, dtype=bool), np.asarray(score, dtype=float)
    order = np.argsort(score, kind="stable")
    s, truth = score[order], y[order]
    ends = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]
    tp = np.r_[truth.sum(), truth.sum() - np.cumsum(truth)[ends]]
    fp = np.r_[(~truth).sum(), (~truth).sum() - np.cumsum(~truth)[ends]]
    thresholds = np.r_[-1.0, s[ends]]
    denom = 2 * tp + fp + truth.sum() - tp
    f1 = np.divide(2 * tp, denom, out=np.zeros_like(denom, dtype=float), where=denom != 0)
    winner = np.flatnonzero(f1 == f1.max())[-1]
    return float(thresholds[winner])


def threshold_budget(normal_scores, budget):
    """Empirical calibration budget only; not a population guarantee."""
    if not 0 <= budget < 1:
        raise ValueError("Invalid budget")
    scores = np.sort(np.asarray(normal_scores, dtype=float))
    if not len(scores) or not np.isfinite(scores).all():
        raise ValueError("Invalid normal scores")
    allowed = int(np.floor(budget * len(scores)))
    return float(scores[len(scores) - allowed - 1])


def binary_metrics(y, score, threshold, positive=0):
    truth, flags = y == positive, score > threshold
    tp, fp = int((truth & flags).sum()), int((~truth & flags).sum())
    fn, tn = int((truth & ~flags).sum()), int((~truth & ~flags).sum())
    normal = y == CLASSES.index("NormalTraffic")
    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else 0., "recall": tp / (tp + fn),
            "f1": 2 * tp / (2 * tp + fp + fn), "non_exfil_fpr": fp / (fp + tn), "normal_fp": int((normal & flags).sum()),
            "normal_fpr": float(flags[normal].mean()), "alert_count": int(flags.sum()),
            "flag_counts_by_true_stage": {name: int((flags & (y == i)).sum()) for i, name in enumerate(CLASSES)}}


def exfil_metrics(ycal, ytest, cal, test):
    selected = threshold_f1(ycal == 0, cal)
    return {"average_precision": float(average_precision_score(ytest == 0, test)),
            "roc_auc": float(roc_auc_score(ytest == 0, test)),
            "calibration_f1_threshold": binary_metrics(ytest, test, selected),
            "normal_budget_thresholds": {str(b): {"calibration_normal_fpr": float(np.mean(cal[ycal == 3] > threshold_budget(cal[ycal == 3], b))),
                **binary_metrics(ytest, test, threshold_budget(cal[ycal == 3], b))} for b in BUDGETS},
            "non_exfil_budget_thresholds": {str(b): {"calibration_non_exfil_fpr": float(np.mean(cal[ycal != 0] > threshold_budget(cal[ycal != 0], b))),
                **binary_metrics(ytest, test, threshold_budget(cal[ycal != 0], b))} for b in BUDGETS}}


def stage_metrics(y, scores):
    predicted = scores.argmax(axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(y, predicted, labels=np.arange(6), zero_division=0)
    normal = y == 3
    return {"macro_f1": float(f1_score(y, predicted, average="macro")),
            "accuracy": float(np.mean(predicted == y)), "normal_fpr_any_attack": float(np.mean(predicted[normal] != 3)),
            "any_attack_recall": float(np.mean(predicted[~normal] != 3)),
            "confusion_matrix": confusion_matrix(y, predicted, labels=np.arange(6)).tolist(),
            "per_stage": {name: {"precision": float(precision[k]), "recall": float(recall[k]), "f1": float(f1[k]),
                                  "support": int(support[k]), "average_precision": float(average_precision_score(y == k, scores[:, k])),
                                  "roc_auc": float(roc_auc_score(y == k, scores[:, k])),
                                  "any_attack_recall": float(np.mean(predicted[y == k] != 3))} for k, name in enumerate(CLASSES)}}


def run(data_path, protocol_path, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be fresh; preserve partial/completed runs")
    spec = json.loads(protocol_path.read_text(encoding="utf-8"))
    if spec != protocol() or sha(data_path) != DATA_SHA:
        raise ValueError("Protocol or data binding mismatch")
    output.mkdir(parents=True, exist_ok=True)
    with np.load(data_path, allow_pickle=False) as source:
        data = {key: source[key] for key in source.files}
    if data["classes"].tolist() != CLASSES or data["X"].shape[1] != 73:
        raise ValueError("Unexpected classes/features")
    if len(np.unique(data["group_sha256"])) != len(data["y"]):
        raise ValueError("Duplicate feature groups")
    if not np.array_equal(np.unique(data["split"]), [0, 1, 2]) or np.isinf(data["X"]).any():
        raise ValueError("Invalid split/features")
    cal_idx, test_idx = np.flatnonzero(data["split"] == 1), np.flatnonzero(data["split"] == 2)
    ycal, ytest = data["y"][cal_idx], data["y"][test_idx]
    views = {"raw": data["X"], "engineered": engineered(data["X"], data["feature_names"])}
    receipt = {"started_utc": utc(), "data_sha256": sha(data_path), "protocol_sha256": sha(protocol_path), "runner_sha256": sha(__file__),
               "packages": {p: importlib.metadata.version(p) for p in ["numpy", "scikit-learn", "xgboost", "lightgbm", "scipy"]},
               "calibration_counts": dict(zip(CLASSES, np.bincount(ycal).tolist())), "test_counts": dict(zip(CLASSES, np.bincount(ytest).tolist())),
               "hardware": "CPU, four threads; no AWS instance started"}
    write_json(output / "STARTED.json", receipt)
    summaries = []
    start = time.perf_counter()
    for seed in SEEDS:
        folder = output / str(seed)
        folder.mkdir()
        model_dir = folder / "models"
        model_dir.mkdir()
        fit = supports(data, seed)
        yfit = data["y"][fit]
        fold_ids = np.full(len(fit), -1, dtype=np.int16)
        for k, (_, validation) in enumerate(StratifiedKFold(3, shuffle=True, random_state=seed).split(np.zeros(len(fit)), yfit)):
            fold_ids[validation] = k
        base, fold_metadata = {}, {}
        for view, X in views.items():
            tasks = ["general", "binary_0"] if view == "raw" else ["general", *[f"binary_{k}" for k in range(6)]]
            for family in PARAMETERS:
                for task in tasks:
                    label = None if task == "general" else int(task.split("_")[1])
                    target = yfit if label is None else (yfit == label).astype(int)
                    key = f"{view}__{family}__{task}"
                    print(f"FIT {seed} {key}", flush=True)
                    predictions, fitted, fold_info = crossfit(family, X[fit], target, fold_ids, seed, X[cal_idx], X[test_idx])
                    base[key] = predictions if label is None else {split: p[:, 1] for split, p in predictions.items()}
                    fold_metadata[key] = fold_info
                    joblib.dump(fitted, model_dir / f"{key}.joblib", compress=3)
        saved = {"fit_indices": fit, "fit_y": yfit, "fold_ids": fold_ids, "cal_indices": cal_idx, "test_indices": test_idx,
                 "cal_y": ycal, "test_y": ytest}
        for key, preds in base.items():
            for split, scores in preds.items():
                saved[f"base::{key}::{split}"] = scores
        exfil_arms, stage_arms = {}, {}
        for view in views:
            for family in PARAMETERS:
                g = base[f"{view}__{family}__general"]
                exfil_arms[f"{view}_general_{family}"] = {s: p[:, 0] for s, p in g.items()}
                stage_arms[f"{view}_general_{family}"] = g
                exfil_arms[f"{view}_specialist_{family}"] = base[f"{view}__{family}__binary_0"]
        generals = [base[f"engineered__{f}__general"] for f in PARAMETERS]
        specialists = [{s: np.column_stack([base[f"engineered__{f}__binary_{k}"][s] for k in range(6)]) for s in ["oof", "cal", "test"]} for f in PARAMETERS]
        gx = [{s: p[:, 0] for s, p in g.items()} for g in generals]
        sx = [{s: p[:, 0] for s, p in g.items()} for g in specialists]
        average = lambda parts: {s: np.mean([p[s] for p in parts], axis=0) for s in ("oof", "cal", "test")}
        exfil_arms["engineered_general_average"] = average(gx)
        exfil_arms["engineered_specialist_average"] = average(sx)
        exfil_arms["engineered_fixed_fusion"] = average(gx + sx)
        for name, parts in [("engineered_general_learned", gx), ("engineered_learned_fusion", gx + sx)]:
            scores, model = learned_fusion(parts, (yfit == 0).astype(int), binary=True)
            exfil_arms[name] = scores
            joblib.dump(model, model_dir / f"exfil__{name}.joblib")
        stage_arms["engineered_general_average"] = average(generals)
        normalized_specialists = [{s: normalize(p) for s, p in part.items()} for part in specialists]
        stage_arms["engineered_specialist_average"] = average(normalized_specialists)
        stage_arms["engineered_fixed_fusion"] = average(generals + normalized_specialists)
        choice = []
        for k in range(6):
            candidate_ap = [float(average_precision_score(yfit == k, p["oof"][:, k])) for p in specialists]
            choice.append({"class": CLASSES[k], "family_index": int(np.argmax(candidate_ap)), "candidate_oof_ap": candidate_ap})
        stage_arms["engineered_selected_specialists"] = {s: normalize(np.column_stack([specialists[c["family_index"]][s][:, k] for k, c in enumerate(choice)])) for s in ["cal", "test"]}
        for name, parts in [("engineered_general_learned", generals), ("engineered_specialist_learned", specialists), ("engineered_learned_fusion", generals + specialists)]:
            scores, model = learned_fusion(parts, yfit)
            stage_arms[name] = scores
            joblib.dump(model, model_dir / f"stage__{name}.joblib")
        metrics = {"seed": seed, "fit_counts": dict(zip(CLASSES, np.bincount(yfit).tolist())), "stage_family_selection": choice,
                   "base_fit_count": len(base) * 4, "final_base_models": len(base), "fusion_fit_count": 5,
                   "exfil": {name: exfil_metrics(ycal, ytest, scores["cal"], scores["test"]) for name, scores in exfil_arms.items()},
                   "stage": {name: stage_metrics(ytest, scores["test"]) for name, scores in stage_arms.items()}}
        for task, arms in [("exfil", exfil_arms), ("stage", stage_arms)]:
            for name, scores in arms.items():
                for split in ("cal", "test"):
                    saved[f"{task}::{name}::{split}"] = scores[split]
        np.savez_compressed(folder / "PREDICTIONS.npz", **saved)
        write_json(folder / "METRICS.json", metrics)
        write_json(folder / "FOLDS.json", fold_metadata)
        write_json(folder / "COMPLETE.json", {"seed": seed, "completed_utc": utc(), "files": {p.name: sha(p) for p in [folder / "PREDICTIONS.npz", folder / "METRICS.json", folder / "FOLDS.json"]},
                                                "models": {p.name: sha(p) for p in model_dir.glob("*.joblib")}})
        summaries.append(metrics)
        print(f"COMPLETE seed={seed} seconds={time.perf_counter()-start:.1f}", flush=True)
    receipt.update({"completed_utc": utc(), "elapsed_seconds": time.perf_counter() - start,
                    "final_base_models": sum(x["final_base_models"] for x in summaries),
                    "base_fits_including_crossfit": sum(x["base_fit_count"] for x in summaries),
                    "fusion_fits": 15})
    write_json(output / "SUMMARY.json", {"receipt": receipt, "seeds": summaries, "interpretation": spec["evaluation_status"]})
    write_json(output / "COMPLETE.json", {"summary_sha256": sha(output / "SUMMARY.json"), "started_sha256": sha(output / "STARTED.json"), "completed_utc": utc()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-protocol", action="store_true")
    args = parser.parse_args()
    if args.write_protocol:
        if args.protocol.exists():
            raise ValueError("Refusing to replace existing protocol")
        write_json(args.protocol, protocol())
    else:
        with threadpool_limits(limits=4):
            run(args.data, args.protocol, args.output)


if __name__ == "__main__":
    main()
