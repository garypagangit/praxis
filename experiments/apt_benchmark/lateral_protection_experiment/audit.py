"""Independently verify saved lateral-protection evidence without model replay.

Scientific selection and metric functions are deliberately not imported. Hash
checks establish which saved artifacts were examined, not that training itself
was independently rerun or that exposed flows are independent confirmation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def value_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def compare(actual, reported, location="root"):
    if isinstance(actual, dict):
        require(isinstance(reported, dict) and actual.keys() == reported.keys(), f"{location}: keys differ")
        for key in actual:
            compare(actual[key], reported[key], f"{location}.{key}")
    elif isinstance(actual, list):
        require(isinstance(reported, list) and len(actual) == len(reported), f"{location}: list differs")
        for i, (a, b) in enumerate(zip(actual, reported)):
            compare(a, b, f"{location}[{i}]")
    elif isinstance(actual, float):
        require(not isinstance(reported, bool) and isinstance(reported, (int, float))
                and np.isfinite(reported) and np.isclose(actual, reported, rtol=0, atol=1e-10), f"{location}: numeric mismatch")
    else:
        require(actual == reported and (not isinstance(actual, bool) or isinstance(reported, bool)), f"{location}: value mismatch")


def check_probabilities(prob, y, n_classes):
    prob, y = np.asarray(prob), np.asarray(y)
    require(y.ndim == 1 and y.dtype.kind in "iu" and len(y) > 0, "Invalid probability labels")
    require(np.all((y >= 0) & (y < n_classes)), "Out-of-range class label")
    require(prob.shape == (len(y), n_classes) and np.isfinite(prob).all(), "Probability shape/nonfinite mismatch")
    require(np.all((prob >= 0) & (prob <= 1)) and np.allclose(prob.sum(axis=1), 1, rtol=0, atol=1e-5), "Invalid probability distribution")
    return prob


def selection_options(scores, labels, normal, lateral):
    """Count score bins instead of using the runner's sorted-row frontier."""
    scores, labels = np.asarray(scores, dtype=float), np.asarray(labels)
    require(scores.ndim == 1 and scores.shape == labels.shape and len(scores) > 0, "Invalid score/label vectors")
    require(np.isfinite(scores).all() and np.all((scores >= 0) & (scores <= 1)), "Invalid attack scores")
    n, l = int(np.count_nonzero(labels == normal)), int(np.count_nonzero(labels == lateral))
    require(n > 0 and l > 0, "Selection requires normal and lateral support")
    values, inverse = np.unique(scores, return_inverse=True)
    normal_bins = np.bincount(inverse[labels == normal], minlength=len(values))
    lateral_bins = np.bincount(inverse[labels == lateral], minlength=len(values))
    fp = np.r_[n, n - np.cumsum(normal_bins)]
    tp = np.r_[l, l - np.cumsum(lateral_bins)]
    return [(float(t), int(a), int(b), n, l) for t, a, b in zip(np.r_[-1.0, values], fp, tp)]


def independent_selection(cells, labels, normal, lateral):
    require(cells and len({c["cell_id"] for c in cells}) == len(cells), "Missing/duplicate selection cells")
    options = []
    for order, cell in enumerate(cells):
        for t, fp, tp, n, l in selection_options(cell["scores"], labels, normal, lateral):
            if 100 * fp <= n and 10 * tp >= 9 * l:
                options.append((order, t, fp, tp, n, l))
    if not options:
        return {"status": "INFEASIBLE", "reason": "No control attains selection lateral recall >=90% and benign FPR <=1%", "choices": {}}
    reference = min(options, key=lambda p: (-p[3], p[2], p[0], -p[1]))
    eligible = [p for p in options if 100 * (p[3] - reference[3]) >= -3 * p[5]]
    candidate = min(eligible, key=lambda p: (p[2], -p[3], p[0], -p[1]))
    threshold_only = min((p for p in eligible if p[0] == reference[0]), key=lambda p: (p[2], -p[3], -p[1]))
    def record(p):
        k, t, fp, tp, n, l = p
        return {"cell_id": cells[k]["cell_id"], "threshold": t, "selection_benign_fp": fp,
                "selection_lateral_tp": tp, "selection_benign_n": n, "selection_lateral_n": l}
    choices = {"reference": record(reference), "candidate": record(candidate), "threshold_only": record(threshold_only)}
    return {"status": "SELECTED", "choices": choices,
            "candidate_equals_threshold_only": choices["candidate"] == choices["threshold_only"],
            "candidate_uses_reference_detector": candidate[0] == reference[0]}


def metrics(labels, scores, flags, classes, normal):
    labels, scores, flags = np.asarray(labels), np.asarray(scores), np.asarray(flags)
    require(labels.ndim == 1 and scores.shape == labels.shape and flags.shape == labels.shape, "Metric shape mismatch")
    require(flags.dtype == bool and np.isfinite(scores).all(), "Invalid metric flags/scores")
    benign = labels == normal
    truth = ~benign
    # Binary confusion counts built independently from 2x2 bincount.
    tn, fp, fn, tp = map(int, np.bincount(2 * truth.astype(int) + flags.astype(int), minlength=4))
    n, a = tn + fp, fn + tp
    return {"rows": len(labels), "benign_n": n, "attack_n": a, "fp": fp, "tp": tp, "fn": fn, "tn": tn,
            "benign_fpr": fp / n if n else None, "attack_recall": tp / a if a else None,
            "attack_precision": tp / (tp + fp) if tp + fp else 0.0,
            "attack_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            "alert_fraction": (tp + fp) / len(labels),
            "roc_auc": float(roc_auc_score(truth, scores)) if n and a else None,
            "average_precision": float(average_precision_score(truth, scores)) if a else None,
            "per_stage": {name: {"n": int(np.count_nonzero(labels == k)),
                "detected": int(np.count_nonzero(flags & (labels == k))),
                "recall": float(np.count_nonzero(flags & (labels == k)) / np.count_nonzero(labels == k)) if np.any(labels == k) else None}
                for k, name in enumerate(classes) if k != normal}}


def independent_gate(rows, expected):
    selected = [row for row in rows if row["selection_status"] == "SELECTED"]
    if len(rows) != expected:
        return {"status": "INCOMPLETE", "pairs": len(selected), "expected_pairs": expected}
    if len(selected) != expected:
        return {"status": "INFEASIBLE", "pairs": len(selected), "expected_pairs": expected,
                "reason": "All prespecified seeds must have a selected policy; no averaging only feasible survivors"}
    candidates = [r["partitions"]["verification"]["candidate"] for r in rows]
    references = [r["partitions"]["verification"]["reference"] for r in rows]
    mean = lambda items: sum(items) / len(items)
    cf, rf = [mean([r["benign_fpr"] for r in values]) for values in [candidates, references]]
    cr, rr = [mean([r["per_stage"]["LateralMovement"]["recall"] for r in values]) for values in [candidates, references]]
    def exact_rates(records, stage=False):
        if stage:
            return sum((Fraction(r["per_stage"]["LateralMovement"]["detected"], r["per_stage"]["LateralMovement"]["n"]) for r in records), Fraction()) / len(records)
        return sum((Fraction(r["fp"], r["benign_n"]) for r in records), Fraction()) / len(records)
    ecf, erf = exact_rates(candidates), exact_rates(references)
    ecr, err = exact_rates(candidates, True), exact_rates(references, True)
    guards = {"false_alarm_reduction_at_least_20pct": ecf < Fraction(4, 5) * erf,
              "lateral_loss_less_than_3pp": ecr - err > Fraction(-3, 100),
              "lateral_recall_at_least_90pct": ecr >= Fraction(9, 10), "benign_fpr_at_most_1pct": ecf <= Fraction(1, 100)}
    return {"status": "DEVELOPMENT_PROMISING" if all(guards.values()) else "DEVELOPMENT_NEGATIVE",
            "pairs": expected, "expected_pairs": expected, "guards": guards,
            "candidate_mean_fpr": cf, "reference_mean_fpr": rf, "candidate_mean_lateral_recall": cr,
            "reference_mean_lateral_recall": rr, "relative_fpr_reduction": 1 - cf / rf if rf else None,
            "candidate_worst_seed_fpr": max(c["benign_fpr"] for c in candidates),
            "candidate_worst_seed_lateral_recall": min(c["per_stage"]["LateralMovement"]["recall"] for c in candidates),
            "interpretation": "Mean-seed point estimates on an exposed-source verification partition; no confidence certificate, independent replication, or novelty claim"}


def weights(labels, scheme, classes, lateral):
    labels = np.asarray(labels)
    counts = np.bincount(labels, minlength=classes)
    require(np.all(counts > 0), "Missing fitting class")
    require(scheme in {"natural", "balanced", "lateral2", "lateral4"}, "Unknown weight scheme")
    multipliers = np.ones(classes)
    if scheme != "natural":
        multipliers = len(labels) / (classes * counts.astype(float))
        multipliers[lateral] *= {"balanced": 1, "lateral2": 2, "lateral4": 4}[scheme]
    result = multipliers[labels]
    result /= result.mean()
    return result


def weight_summary(labels, scheme, classes, lateral):
    vector = weights(labels, scheme, classes, lateral)
    return {"rows": len(labels), "class_counts": np.bincount(labels, minlength=classes).tolist(),
            "class_weight_sums": np.bincount(labels, weights=vector, minlength=classes).tolist(),
            "mean": float(vector.mean()), "minimum": float(vector.min()), "maximum": float(vector.max()),
            "vector_sha256": value_hash(vector.tolist())}


def imputer_statistics(features):
    features = np.asarray(features, dtype=np.float64)
    expected = np.zeros(features.shape[1])
    present = ~np.isnan(features).all(axis=0)
    expected[present] = np.nanmedian(features[:, present], axis=0)
    return expected.tolist()


def check_cv(metadata, grid, X, y, seed, model, scheme, classes, normal, lateral, threads):
    expected = {"model": model, "seed": seed, "n_classes": classes, "normal_index": normal,
        "lateral_index": lateral, "weight_scheme": scheme,
        "weight_normalization": "mean_one_within_each_fold_training_partition_and_final_support",
        "n_splits": 3, "shuffle": True, "split_random_state": seed,
        "metric": "unweighted_macro_f1_all_declared_classes_argmax",
        "tie_policy": "first_candidate_in_declared_grid_order", "selection_data": "supplied_fitting_support_only",
        "actual_device": "cpu", "cpu_threads": threads}
    for key, value in expected.items():
        compare(value, metadata.get(key), f"CV.{key}")
    require(len(metadata["candidates"]) == len(grid), "CV candidate roster mismatch")
    means = []
    for parameters, entry in zip(grid, metadata["candidates"]):
        compare(parameters, entry["parameters"], "CV parameters")
        scores = np.asarray(entry["fold_macro_f1"], dtype=float)
        require(scores.shape == (3,) and np.isfinite(scores).all() and np.all((scores >= 0) & (scores <= 1)), "Invalid CV score")
        means.append(float(scores.mean()))
        compare(means[-1], entry["mean_macro_f1"], "CV mean")
    winner = int(np.argmax(means))
    require(metadata["selected_candidate_index"] == winner, "Wrong CV winner")
    compare(grid[winner], metadata["selected_parameters"], "CV chosen parameters")
    compare(means[winner], metadata["selected_mean_macro_f1"], "CV chosen score")
    folds = list(StratifiedKFold(3, shuffle=True, random_state=seed).split(np.zeros((len(y), 1)), y))
    require(len(metadata["folds"]) == len(folds), "CV fold roster mismatch")
    for (train, validation), saved in zip(folds, metadata["folds"]):
        compare({"train_support_positions": train.tolist(), "validation_support_positions": validation.tolist(),
                 "training_weights": weight_summary(y[train], scheme, classes, lateral),
                 "imputer_statistics": imputer_statistics(X[train])}, saved, "CV fold")
    compare(weight_summary(y, scheme, classes, lateral), metadata["final_training_weights"], "Final weights")


SOURCE_FILES = ["experiments/apt_benchmark/lateral_protection_experiment/" + p for p in
                ["run.py", "backend.py", "selection.py", "specification.py", "__init__.py"]] + [
                "experiments/apt_benchmark/tabular_batch/run_e1.py",
                "experiments/apt_benchmark/tabular_batch/model_backend.py",
                "experiments/apt_benchmark/tabular_followup/run_strong_baselines.py"]
REPO = Path(__file__).resolve().parents[3]


def reconstruct_support(data, budget, seed):
    require(budget in (32, 128, 512, 1024), "Unsupported support budget")
    rng, chosen = np.random.default_rng(seed), []
    for k in range(len(data["classes"])):
        pool = np.flatnonzero((data["split"] == 0) & (data["y"] == k))
        pool = pool[np.argsort(data["group_sha256"][pool], kind="stable")]
        require(len(pool) >= 32, "Insufficient attack fitting rows")
        chosen.extend(rng.choice(pool, size=32, replace=False).tolist())
    normal = data["classes"].tolist().index("NormalTraffic")
    existing = set(chosen)
    pool = [int(i) for i in np.flatnonzero((data["split"] == 0) & (data["y"] == normal)) if int(i) not in existing]
    require(len(pool) >= budget - 32, "Insufficient normal fitting rows")
    def key(i):
        return hashlib.sha256(f"STRONG_BASELINES_BENIGN_20260921|{seed}|{data['group_sha256'][i]}".encode("ascii")).digest()
    return np.asarray(chosen + sorted(pool, key=key)[:budget - 32], dtype=np.int64)


def reconstruct_partitions(data, tag):
    first, second = [], []
    for k in range(len(data["classes"])):
        indices = np.flatnonzero((data["split"] == 1) & (data["y"] == k)).tolist()
        ranked = sorted(indices, key=lambda i: hashlib.sha256(f"{tag}|{data['group_sha256'][i]}".encode("ascii")).digest())
        cut = len(ranked) // 2
        first += ranked[:cut]
        second += ranked[cut:]
    result = {"selection": np.asarray(first, dtype=np.int64), "verification": np.asarray(second, dtype=np.int64),
              "test": np.flatnonzero(data["split"] == 2)}
    sets = [set(v.tolist()) for v in result.values()]
    require(all(not (sets[i] & sets[j]) for i in range(3) for j in range(i)), "Evaluation partitions overlap")
    require(sets[0] | sets[1] == set(np.flatnonzero(data["split"] == 1).tolist()), "Calibration partition dropped rows")
    return result


def roster(data, indices):
    return {"indices": indices.tolist(), "fingerprints": data["group_sha256"][indices].tolist(),
            "class_counts": np.bincount(data["y"][indices], minlength=len(data["classes"])).tolist()}


def load_bound_input(data_path, protocol):
    data_path = Path(data_path)
    if data_path.is_dir():
        data_path /= "DATA.npz"
    require(file_hash(data_path) == protocol["data_npz_sha256"], "Prepared input hash mismatch")
    manifest_path = data_path.with_name("MANIFEST.json")
    require(file_hash(manifest_path) == protocol["manifest_sha256"], "Manifest hash mismatch")
    require(read_json(manifest_path)["data_npz_sha256"] == protocol["data_npz_sha256"], "Manifest input binding mismatch")
    with np.load(data_path, allow_pickle=False) as z:
        data = {k: z[k] for k in z.files}
    require({"X", "y", "split", "group_sha256", "classes", "feature_names"} <= data.keys(), "Missing input arrays")
    require(data["X"].ndim == 2 and all(len(data[k]) == len(data["X"]) for k in ("y", "split", "group_sha256")), "Input row dimensions differ")
    require(data["X"].shape[1] == len(data["feature_names"]), "Feature schema differs")
    require(not np.isinf(data["X"]).any() and data["y"].dtype.kind in "iu", "Invalid input values")
    require(np.array_equal(np.unique(data["y"]), np.arange(len(data["classes"]))), "Input label encoding differs")
    require(set(np.unique(data["split"])) == {0, 1, 2}, "Unexpected original split")
    require(len(np.unique(data["group_sha256"])) == len(data["y"]), "Duplicate prepared fingerprint")
    return data


def check_protocol(protocol):
    require(protocol.get("status") == "FROZEN_BEFORE_NEW_MODEL_FITS" and protocol.get("study_kind") == "exposed_source_development", "Protocol is not frozen development")
    require(protocol["models"] == ["xgboost", "lightgbm"] and protocol["schemes"] == ["natural", "balanced", "lateral2", "lateral4"], "Model/scheme roster differs")
    require(protocol["samples_per_attack_class"] == 32 and protocol["n_splits"] == 3 and protocol["cpu_threads"] == 4, "Fitting constants differ")
    expected = [{"budget": 1024, "seed": s} for s in range(20260921, 20260931)] + [
        {"budget": b, "seed": s} for b in (32, 128, 512) for s in range(20260921, 20260924)]
    require(protocol["groups"] == expected, "Registered group roster differs")
    require(protocol["partition_tag"] == "LATERAL_SELECTION_20260921", "Partition salt differs")
    require(protocol["verification_gate"] == {"all_10_primary_seeds_feasible": True,
        "mean_seed_fpr_relative_reduction_strictly_greater": .2, "mean_seed_lateral_loss_strictly_less_than": .03,
        "mean_seed_lateral_recall_min": .9, "mean_seed_fpr_max": .01}, "Gate constants differ")
    forbidden = {"class_weight", "sample_weight", "scale_pos_weight", "is_unbalance", "unbalance"}
    for model in protocol["models"]:
        require(protocol["model_grids"][model], "Empty model grid")
        for params in protocol["model_grids"][model]:
            require(not (set(params) & forbidden), "Grid silently overrides sample weighting")


def verify_files(folder, records, expected):
    require(set(records) == set(expected), "Artifact receipt roster differs")
    for name, digest in records.items():
        require(file_hash(Path(folder) / name) == digest, f"Artifact hash mismatch: {name}")


def stamp(record):
    return datetime.fromisoformat(record["created_utc"].replace("Z", "+00:00"))


def packet(path, data, indices, prefix="", keys=None):
    with np.load(path, allow_pickle=False) as archive:
        if keys is not None:
            require(set(archive.files) == set(keys), "Prediction packet keys differ")
        require(np.array_equal(archive["classes"], data["classes"]), "Prediction class order differs")
        require(np.array_equal(archive[prefix + "indices"], indices), "Prediction query indices differ")
        require(np.array_equal(archive[prefix + "fingerprints"], data["group_sha256"][indices]), "Prediction query fingerprints differ")
        require(np.array_equal(archive[prefix + "y"], data["y"][indices]), "Prediction truth labels differ")
        return check_probabilities(archive[prefix + "probabilities"], data["y"][indices], len(data["classes"]))


def classification_metrics(y, p, classes):
    guess = p.argmax(axis=1)
    n_classes = len(classes)
    matrix = np.bincount(n_classes * y + guess, minlength=n_classes ** 2).reshape(n_classes, n_classes)
    stages = {}
    for k, name in enumerate(classes):
        tp, support, predicted = int(matrix[k, k]), int(matrix[k].sum()), int(matrix[:, k].sum())
        truth = y == k
        stages[name] = {"precision": tp / predicted if predicted else 0., "recall": tp / support if support else 0.,
            "f1": 2 * tp / (support + predicted) if support + predicted else 0., "support": support,
            "roc_auc_ovr": float(roc_auc_score(truth, p[:, k])) if truth.any() and (~truth).any() else None,
            "average_precision_ovr": float(average_precision_score(truth, p[:, k])) if truth.any() else None}
    aucs, aps = [v["roc_auc_ovr"] for v in stages.values()], [v["average_precision_ovr"] for v in stages.values()]
    return {"n": len(y), "accuracy": float(np.trace(matrix) / len(y)),
        "macro_f1": sum(v["f1"] for v in stages.values()) / n_classes,
        "roc_auc_ovr_macro": sum(aucs) / n_classes if all(v is not None for v in aucs) else None,
        "average_precision_ovr_macro": sum(aps) / n_classes if all(v is not None for v in aps) else None,
        "classes": classes, "confusion_matrix": matrix.tolist(), "per_stage": stages}


def check_group(data, protocol, receipt, run, group, parts):
    budget, seed = group["budget"], group["seed"]
    group_dir = run / "groups" / str(budget) / str(seed)
    saved_result = read_json(group_dir / "RESULT.json")
    lock_path = group_dir / "SELECTION_LOCK.json"
    lock, lock_sha = read_json(lock_path), file_hash(lock_path)
    binding = receipt["execution_binding"]
    classes = data["classes"].tolist()
    normal, lateral = classes.index("NormalTraffic"), classes.index("LateralMovement")
    fit = reconstruct_support(data, budget, seed)
    cells, fit_hashes, cell_hashes = [], {}, {}
    for model in protocol["models"]:
        for scheme in protocol["schemes"]:
            cell_id = f"{model}/{scheme}"
            folder = run / "cells" / str(budget) / str(seed) / model / scheme
            started, fitted, fit_complete = [read_json(folder / name) for name in ["STARTED.json", "FITTED.json", "FIT_COMPLETE.json"]]
            for obj in (started, fitted):
                for name, expected in [("budget", budget), ("seed", seed), ("cell_id", cell_id), ("execution_binding", binding)]:
                    require(obj.get(name) == expected, "Fitted cell identity/binding mismatch")
            require(fit_complete["execution_binding"] == binding, "Fit completion binding differs")
            verify_files(folder, fit_complete["files"], ["STARTED.json", "MODEL.joblib", "SELECTION.npz", "FITTED.json"])
            require(fitted["model_sha256"] == file_hash(folder / "MODEL.joblib") and fitted["selection_sha256"] == file_hash(folder / "SELECTION.npz"), "Fitted artifact hash differs")
            require(fitted["support_sha256"] == value_hash(fit.tolist()), "Fitting support hash differs")
            compare(imputer_statistics(data["X"][fit]), fitted["imputer_statistics"], "Final imputer")
            check_cv(fitted["cv_metadata"], protocol["model_grids"][model], data["X"][fit], data["y"][fit], seed,
                     model, scheme, len(classes), normal, lateral, protocol["cpu_threads"])
            compare(receipt["fixed"]["versions"], fitted["cv_metadata"]["versions"], "Fit versions")
            require(all(isinstance(v, (int, float)) and np.isfinite(v) and v >= 0 for v in fitted["timing_seconds"].values()), "Invalid timing record")
            require(stamp(receipt) <= stamp(started) <= stamp(fitted) <= stamp(fit_complete) <= stamp(lock), "Fit/selection-lock receipt order differs")
            selection = packet(folder / "SELECTION.npz", data, parts["selection"], keys=["probabilities", "y", "indices", "fingerprints", "classes"])
            fit_hashes[cell_id] = file_hash(folder / "FIT_COMPLETE.json")
            evaluation_start, cell, complete = [read_json(folder / name) for name in ["EVALUATION_STARTED.json", "CELL.json", "COMPLETE.json"]]
            for obj in (evaluation_start, cell, complete):
                require(obj["execution_binding"] == binding and obj["selection_lock_sha256"] == lock_sha, "Evaluation selection-lock binding differs")
            require(cell["cell_id"] == cell_id and cell["budget"] == budget and cell["seed"] == seed, "Evaluation identity differs")
            require(stamp(lock) <= stamp(evaluation_start) <= stamp(cell) <= stamp(complete), "Verification was recorded before its selection lock")
            verify_files(folder, complete["files"], ["CELL.json", "EVALUATION.npz", "EVALUATION_STARTED.json", "FIT_COMPLETE.json"])
            evaluation = {}
            for part in ("verification", "test"):
                p = packet(folder / "EVALUATION.npz", data, parts[part], part + "_",
                    keys=["classes"] + [k + "_" + name for k in ["verification", "test"] for name in ["probabilities", "y", "indices", "fingerprints"]])
                evaluation[part] = p
                y, scores = data["y"][parts[part]], 1 - p[:, normal]
                compare({"classification": classification_metrics(y, p, classes),
                         "argmax_alert": metrics(y, scores, p.argmax(1) != normal, classes, normal)}, cell["metrics"][part], f"Cell {cell_id}/{part}")
            cell_hashes[cell_id] = file_hash(folder / "COMPLETE.json")
            cells.append({"cell_id": cell_id, "scores": 1 - selection[:, normal], "fit": fitted, "evaluation": evaluation})
    choice = independent_selection(cells, data["y"][parts["selection"]], normal, lateral)
    natural = [c for c in cells if c["cell_id"].endswith("/natural")]
    cvbest = min(enumerate(natural), key=lambda kv: (-kv[1]["fit"]["cv_metadata"]["selected_mean_macro_f1"], kv[0]))[1]
    normal_scores = cvbest["scores"][data["y"][parts["selection"]] == normal]
    values = np.unique(normal_scores)
    # Ascending benign order statistic with exact strict-greater tie handling.
    counts = np.searchsorted(np.sort(normal_scores), values, side="right")
    threshold = next(float(v) for v, cleared in zip(values, counts) if 100 * (len(normal_scores) - int(cleared)) <= len(normal_scores))
    controls = {"cv_natural_argmax": {"cell_id": cvbest["cell_id"], "rule": "argmax"},
                "cv_natural_benign_threshold": {"cell_id": cvbest["cell_id"], "rule": "threshold", "threshold": threshold}}
    expected_lock = {"execution_binding": binding, "budget": budget, "seed": seed, **choice,
                     "controls": controls, "fit_complete_sha256": fit_hashes}
    compare(expected_lock, {k: v for k, v in lock.items() if k != "created_utc"}, "Selection lock")
    by_id = {c["cell_id"]: c for c in cells}
    policy_metrics = {part: {} for part in ("verification", "test")}
    for name, policy in {**choice["choices"], **controls}.items():
        for part in policy_metrics:
            p = by_id[policy["cell_id"]]["evaluation"][part]
            y, scores = data["y"][parts[part]], 1 - p[:, normal]
            flags = p.argmax(1) != normal if policy.get("rule") == "argmax" else scores > policy["threshold"]
            policy_metrics[part][name] = metrics(y, scores, flags, classes, normal)
    result = {"execution_binding": binding, "budget": budget, "seed": seed, "selection_status": choice["status"],
              "selection_lock_sha256": lock_sha, "selection": choice, "controls": controls,
              "partitions": policy_metrics, "cell_complete_sha256": cell_hashes}
    compare(result, saved_result, f"Group {budget}/{seed}")
    return result


def audit_run(data_path, protocol_path, run):
    protocol_path, run = Path(protocol_path), Path(run)
    protocol = read_json(protocol_path)
    check_protocol(protocol)
    data = load_bound_input(data_path, protocol)
    require(file_hash(REPO / "experiments/apt_benchmark/tabular_batch/protocol.json") == protocol["e1_protocol_sha256"], "Original protocol binding differs")
    receipt_path = run / "PREFIT_RECEIPT.json"
    receipt = read_json(receipt_path)
    parts = reconstruct_partitions(data, protocol["partition_tag"])
    fixed = receipt["fixed"]
    expected = {"schema_version": 1, "protocol_sha256": file_hash(protocol_path),
                "data_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
                "source_hashes": {name: file_hash(REPO / name) for name in SOURCE_FILES},
                "versions": fixed["versions"], "classes": data["classes"].tolist(), "feature_names": data["feature_names"].tolist(),
                "partitions": {name: roster(data, rows) for name, rows in parts.items()},
                "groups": [{**g, **roster(data, reconstruct_support(data, g["budget"], g["seed"]))} for g in protocol["groups"]]}
    compare(expected, fixed, "Prefit fixed fields")
    require(value_hash(fixed) == receipt["execution_binding"], "Prefit execution digest differs")
    rows, missing, group_hashes = [], [], {}
    for group in protocol["groups"]:
        path = run / "groups" / str(group["budget"]) / str(group["seed"]) / "RESULT.json"
        if path.exists():
            rows.append(check_group(data, protocol, receipt, run, group, parts))
            group_hashes[f"{group['budget']}/{group['seed']}"] = file_hash(path)
        else:
            missing.append(group)
    expected_summary = {"execution_binding": receipt["execution_binding"], "completed_groups": len(rows),
        "required_groups": len(protocol["groups"]), "completed_cells": 8 * len(rows), "required_cells": 8 * len(protocol["groups"]),
        "status": "INCOMPLETE" if missing else "COMPLETE", "primary_gate": independent_gate([r for r in rows if r["budget"] == 1024], 10),
        "secondary_gates": {str(b): independent_gate([r for r in rows if r["budget"] == b], 3) for b in (32, 128, 512)}, "groups": rows}
    artifacts = {"PREFIT_RECEIPT.json": file_hash(receipt_path)}
    summary_path = run / "SUMMARY.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        compare(expected_summary, {k: v for k, v in summary.items() if k != "created_utc"}, "Global summary")
        artifacts["SUMMARY.json"] = file_hash(summary_path)
    else:
        require(missing, "Completed run lacks final summary")
    return {"audit_status": "PASS", "run_status": expected_summary["status"],
            "experiment": protocol["experiment"], "execution_binding": receipt["execution_binding"],
            "completed_groups": len(rows), "required_groups": len(protocol["groups"]),
            "audited_cells": 8 * len(rows), "required_cells": 8 * len(protocol["groups"]),
            "missing_groups": missing, "primary_gate": expected_summary["primary_gate"],
            "secondary_gates": expected_summary["secondary_gates"], "artifact_hashes": artifacts,
            "group_result_hashes": group_hashes, "protocol_sha256": file_hash(protocol_path),
            "audit_source_sha256": file_hash(__file__),
            "checks": ["Input, protocol, code, model and receipt hashes", "Independent support, partition and label rosters",
                "Fitting-only CV arithmetic, fold weights and imputation statistics", "Selection precedes verification receipt chain",
                "Independent score-bin threshold/tie reconstruction including threshold-only ablation",
                "All saved predictions and classification/alert/stage metrics", "All-seed completeness and exact rational development guards"],
            "limitations": ["No model fitting or inference was replayed; CV fold scores are checked arithmetically, not recomputed from unsaved fold predictions.",
                "Receipt ordering and frozen code support the recorded execution path; they do not establish human blindness or independent confirmation.",
                "Previously exposed source flows and repeated fitting seeds do not provide independent-incident or deployment guarantees."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "AUDIT.json"
    require(not target.exists(), "Audit output already exists; use a fresh audit directory")
    try:
        result = audit_run(args.data, args.protocol, args.run)
    except Exception as exc:
        result = {"audit_status": "FAIL", "run_status": "NOT_VERIFIED", "error_type": type(exc).__name__,
                  "error": str(exc), "audit_source_sha256": file_hash(__file__)}
        target.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        raise
    result["audited_utc"] = datetime.now(timezone.utc).isoformat()
    target.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("audit_status", "run_status", "audited_cells", "primary_gate")}, sort_keys=True))


if __name__ == "__main__":
    main()
