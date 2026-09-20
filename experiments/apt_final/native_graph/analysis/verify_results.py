"""Independently audit saved native-pilot evidence without rerunning or tuning models.

This post-run helper is deliberately outside the frozen executable inventory.
It reads arrays with allow_pickle=False and verifies checkpoint bytes by hash;
it never deserializes model checkpoints or claims a second inference run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np


FIXED = ("mlp", "gin", "isolation_forest", "type_rarity")
SELECTORS = ("quality_gate", "confidence_selector")
ARMS = FIXED + SELECTORS


class AuditFailure(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise AuditFailure(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def close(actual, expected, label):
    if isinstance(expected, dict):
        need(isinstance(actual, dict) and set(actual) == set(expected), label + " keys differ")
        for key, value in expected.items():
            close(actual[key], value, label + "." + key)
    elif expected is None:
        need(actual is None, label + " must be null")
    elif isinstance(expected, (int, str, bool)):
        need(actual == expected, label + " mismatch")
    else:
        need(actual is not None and math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-12), label + " mismatch")


def average_precision(y, scores):
    """Non-interpolated AP using precision at each distinct score threshold."""
    positive = int(np.count_nonzero(y))
    if not positive:
        return None
    order = np.argsort(-scores, kind="stable")
    ranked_y, ranked_score = y[order], scores[order]
    ends = np.r_[np.flatnonzero(np.diff(ranked_score)), len(scores) - 1]
    true_at = np.cumsum(ranked_y, dtype=np.int64)[ends]
    added_true = np.diff(np.r_[0, true_at])
    precision_at = true_at / (ends + 1)
    return float(np.sum(added_true * precision_at) / positive)


def metrics(y, score, prediction):
    need(y.ndim == score.ndim == prediction.ndim == 1 and len(y) == len(score) == len(prediction), "Metric shapes differ")
    need(np.all(np.isfinite(score)), "Nonfinite score")
    need(set(np.unique(y)) <= {0, 1} and set(np.unique(prediction)) <= {0, 1}, "Nonbinary labels/predictions")
    truth, pred = y.astype(bool), prediction.astype(bool)
    tp, fp = int(np.sum(truth & pred)), int(np.sum(~truth & pred))
    tn, fn = int(np.sum(~truth & ~pred)), int(np.sum(truth & ~pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    return {"n": len(y), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "false_positive_rate": fp / (fp + tn) if fp + tn else None,
            "false_positives_per_10000_benign_nodes": 10000 * fp / (fp + tn) if fp + tn else None,
            "average_precision": average_precision(y, score),
            "accuracy": (tp + tn) / len(y) if len(y) else None,
            "predicted_positive": tp + fp}


def error_changes(y, candidate, reference):
    cc, rc = candidate == y, reference == y
    return {"corrected_errors": int(np.sum(cc & ~rc)),
            "introduced_errors": int(np.sum(~cc & rc)),
            "both_wrong": int(np.sum(~cc & ~rc))}


def calibrated_margin(calibration, scores, alpha):
    need(calibration.ndim == scores.ndim == 1 and len(calibration) > 0, "Invalid calibration shapes")
    need(np.all(np.isfinite(calibration)) and np.all(np.isfinite(scores)), "Nonfinite calibration/score")
    ordered = np.sort(calibration.astype(np.float64))
    less = np.searchsorted(ordered, scores.astype(np.float64), side="left")
    probability = (len(ordered) - less + 1) / (len(ordered) + 1)
    return np.log(alpha / probability)


def load_arrays(path):
    with np.load(path, allow_pickle=False) as values:
        return {name: values[name] for name in values.files}


def verify_sources(config_path, data_dir, registration_path, repo):
    config, registration, manifest = read(config_path), read(registration_path), read(data_dir / "MANIFEST.json")
    need(config["scope"] == registration["scope"] == "DEVELOPMENT_ONLY", "Wrong registration scope")
    need(registration["status"] == "FROZEN_NATIVE_GRAPH_PILOT", "Wrong registration status")
    need(digest(config_path) == registration["config_sha256"], "Config differs from registration")
    need(digest(data_dir / "MANIFEST.json") == registration["data_manifest_sha256"], "Data manifest differs from registration")
    need(manifest["status"] == "STATIC_DEVELOPMENT_ONLY", "Data manifest scope changed")
    for rel, expected in registration["code_hashes"].items():
        path = (repo / rel).resolve()
        need(path.is_relative_to(repo), "Escaping source path")
        need(digest(path) == expected, "Registered source changed: " + rel)
        committed = subprocess.check_output(["git", "show", registration["git_commit"] + ":" + rel], cwd=repo)
        need(hashlib.sha256(committed).hexdigest() == expected, "Committed source differs: " + rel)
    actual = {p.relative_to(data_dir).as_posix(): digest(p) for p in data_dir.rglob("*.npz")}
    need(actual == registration["data_files"], "Normalized data differs from registration")
    return config, registration, manifest


def expected_scenarios(config, graph):
    n, edges = len(graph["y"]), len(graph["src"])
    def entry(name, rate, seed, keep):
        src, dst = graph["src"][keep], graph["dst"][keep]
        degree = np.bincount(src, minlength=n) + np.bincount(dst, minlength=n)
        return {"name": name, "drop_rate": float(rate), "mask_seed": seed,
                "observed_edges": len(src), "isolated_nodes": int(np.sum(degree == 0)),
                "degree": degree, "input_mask_sha256": hashlib.sha256(keep.tobytes()).hexdigest()}
    yield entry("clean", 0.0, None, np.ones(edges, dtype=bool))
    for seed in config["mask_seeds"]:
        uniform = np.random.Generator(np.random.PCG64(seed)).random(edges)
        for rate in config["drop_rates"]:
            if rate:
                yield entry(f"drop_{rate:g}_mask_{seed}", rate, seed, uniform >= rate)


def audit_dataset(output, dataset, config, registration, registration_path, data_dir, manifest):
    results = read(output / "RESULTS.json")
    run_status = read(output / "RUN_STATUS.json")
    freeze = read(output / "FIT_FREEZE.json")
    for source in (results, run_status):
        need(source["status"] == "COMPLETE_DEVELOPMENT_ONLY", dataset + " is incomplete")
        need(source["scope"] == "DEVELOPMENT_ONLY" and source["dataset"] == dataset, "Result scope/dataset mismatch")
        need(source["registration_sha256"] == digest(registration_path), "Result registration hash mismatch")
        need(source["registration_git_commit"] == registration["git_commit"], "Result source commit mismatch")
        need(source["config_sha256"] == registration["config_sha256"], "Result config hash mismatch")
        need(source["data_manifest_sha256"] == registration["data_manifest_sha256"], "Result data hash mismatch")
        if source["device_requested"] == "cuda":
            need(source["device_actual"] == "cuda" and source["gpu_qualification"]["status"] == "PASS", "Requested GPU qualification did not pass")
    need(results["fit_freeze_sha256"] == digest(output / "FIT_FREEZE.json"), "Fit freeze hash mismatch")
    need(freeze["status"] == "FITTED_BEFORE_EVALUATION_LABEL_ACCESS" and freeze["fit_labels_used"] is False, "Wrong fitting declaration")
    for key in ("train_graphs", "calibration_graph", "seeds"):
        need(freeze[key] == config[key], "Fit split/seed differs: " + key)
    need(results["fit_records"] == freeze["fit_records"], "Fit reports changed after freeze")
    private = output / "private"
    inventory = {p.name: digest(p) for p in private.iterdir() if p.is_file()}
    need(inventory == results["private_artifact_sha256"], "Private artifact hash inventory mismatch")
    expected_fit = {"PREPROCESSING.npz"}
    for seed in config["seeds"]:
        expected_fit.update({f"mlp_{seed}.pt", f"gin_{seed}.pt", f"isolation_forest_{seed}.joblib", f"calibration_{seed}.npz"})
    need(set(freeze["artifacts"]) == expected_fit, "Fit artifact inventory incomplete or unexpected")
    for name, expected in freeze["artifacts"].items():
        need(inventory.get(name) == expected, "Fitted artifact changed: " + name)
    spec = next(d for d in manifest["datasets"] if d["dataset"] == dataset)
    paths = {Path(g["npz"]).stem: data_dir / g["npz"] for g in spec["graphs"]}
    graph = load_arrays(paths[config["evaluation_graph"]])
    y = graph["y"]
    calibration_graph = load_arrays(paths[config["calibration_graph"]])
    calibration_degree = np.bincount(calibration_graph["src"], minlength=len(calibration_graph["y"])) + np.bincount(calibration_graph["dst"], minlength=len(calibration_graph["y"]))
    calibrations, fit_records = {}, {x["seed"]: x for x in freeze["fit_records"]}
    need(len(fit_records) == len(config["seeds"]) == len(freeze["fit_records"]), "Fit seed records duplicated or missing")
    for seed in config["seeds"]:
        scores = load_arrays(private / f"calibration_{seed}.npz")
        need(set(scores) == set(FIXED), "Calibration arm inventory differs")
        need(all(len(v) == len(calibration_degree) for v in scores.values()), "Calibration count differs from held-out graph")
        calibrations[seed] = scores
        margins = {a: calibrated_margin(v, v, config["calibration_fpr"]) for a, v in scores.items()}
        margins["quality_gate"] = np.where(calibration_degree >= config["gate_min_degree"], margins["gin"], margins["mlp"])
        margins["confidence_selector"] = np.where(np.abs(margins["gin"]) >= np.abs(margins["mlp"]), margins["gin"], margins["mlp"])
        for arm in ARMS:
            close(fit_records[seed]["calibration"][arm]["achieved_clean_benign_fpr"], float(np.mean(margins[arm] >= 0)), "Calibration FPR " + arm)
        for arm in ("mlp", "gin"):
            need(len(fit_records[seed]["fit"][arm]["epoch_mean_loss"]) == config["epochs"], "Epoch count mismatch")
    indexed = {(r["seed"], r["name"]): r for r in results["records"]}
    need(len(indexed) == len(results["records"]), "Duplicate result seed/scenario")
    checked, prediction_files, unique_inputs = [], set(), {}
    for scenario in expected_scenarios(config, graph):
        for seed in config["seeds"]:
            key = (seed, scenario["name"])
            need(key in indexed, "Missing seed/scenario: " + repr(key))
            record = indexed.pop(key)
            for field in ("name", "mask_seed", "drop_rate", "observed_edges", "isolated_nodes"):
                close(record[field], scenario[field], "Scenario " + field)
            name = f"predictions_{seed}_{scenario['name']}.npz"
            prediction_files.add(name)
            arrays = load_arrays(private / name)
            expected_keys = {"y", "degree", *("margin_" + a for a in ARMS), *("score_" + a for a in FIXED)}
            need(set(arrays) == expected_keys, "Prediction array inventory differs")
            need(np.array_equal(arrays["y"], y), "Saved labels differ from registered evaluation rows")
            need(np.array_equal(arrays["degree"], scenario["degree"]), "Saved degree differs from independently reconstructed mask")
            margins = {arm: calibrated_margin(calibrations[seed][arm], arrays["score_" + arm], config["calibration_fpr"]) for arm in FIXED}
            quality_gin = scenario["degree"] >= config["gate_min_degree"]
            confidence_gin = np.abs(margins["gin"]) >= np.abs(margins["mlp"])
            margins["quality_gate"] = np.where(quality_gin, margins["gin"], margins["mlp"])
            margins["confidence_selector"] = np.where(confidence_gin, margins["gin"], margins["mlp"])
            recomputed, predictions = {}, {}
            need(set(record["metrics"]) == set(ARMS), "Metric arm inventory differs")
            for arm in ARMS:
                need(arrays["margin_" + arm].shape == y.shape and np.allclose(arrays["margin_" + arm], margins[arm], rtol=1e-12, atol=1e-12), "Saved calibrated/routed margin differs: " + arm)
                predictions[arm] = margins[arm] >= 0
                recomputed[arm] = metrics(y, arrays.get("score_" + arm, margins[arm]), predictions[arm])
                close(record["metrics"][arm], recomputed[arm], "Metrics " + arm)
            changes = {arm: {ref: error_changes(y, predictions[arm], predictions[ref]) for ref in FIXED} for arm in SELECTORS}
            close(record["error_changes"], changes, "Corrected/introduced errors")
            close(record["routing"], {"quality_graph_fraction": float(np.mean(quality_gin)), "confidence_graph_fraction": float(np.mean(confidence_gin))}, "Routing")
            close(record["oracle_mlp_gin_accuracy_descriptive"], float(np.mean((predictions["mlp"] == y) | (predictions["gin"] == y))), "Descriptive accuracy oracle")
            equivalence_key = (seed, scenario["input_mask_sha256"])
            prediction_hash = hashlib.sha256()
            for field in sorted(arrays):
                prediction_hash.update(field.encode()); prediction_hash.update(arrays[field].tobytes())
            signature = prediction_hash.hexdigest()
            duplicate_of = unique_inputs.get(equivalence_key)
            if duplicate_of:
                need(duplicate_of[1] == signature, "Identical model/input produced unequal saved predictions")
            else:
                unique_inputs[equivalence_key] = (scenario["name"], signature)
            comparisons = {}
            for ref in ("gin", "mlp", "isolation_forest"):
                comparisons[ref] = {**changes["quality_gate"][ref],
                    **{"delta_" + m: recomputed["quality_gate"][m] - recomputed[ref][m]
                       for m in ("f1", "recall", "precision", "false_positive_rate", "average_precision")}}
            checked.append({"seed": seed, "scenario": scenario["name"], "drop_rate": scenario["drop_rate"],
                "mask_seed": scenario["mask_seed"], "observed_edges": scenario["observed_edges"],
                "input_mask_sha256": scenario["input_mask_sha256"],
                "duplicate_input_of": duplicate_of[0] if duplicate_of else None,
                "metrics": recomputed, "quality_gate_vs_fixed": comparisons})
    need(not indexed, "Unexpected result scenarios")
    need(set(inventory) == expected_fit | prediction_files, "Unexpected or missing private artifacts")
    summaries = []
    need(len(results["descriptive_summary"]) == len(config["drop_rates"]) * len(ARMS), "Unexpected descriptive summary count")
    for rate in config["drop_rates"]:
        members = [r for r in checked if r["drop_rate"] == rate]
        unique = [r for r in members if r["duplicate_input_of"] is None]
        need(unique, "No unique input/model combinations")
        for arm in ARMS:
            summary = {"drop_rate": rate, "arm": arm, "descriptive_runs": len(members)}
            for metric in ("f1", "precision", "recall", "false_positive_rate", "average_precision", "accuracy"):
                values = [r["metrics"][arm][metric] for r in members]
                summary[metric] = {"mean": float(np.mean(values)), "min": min(values), "max": max(values)}
            saved = [s for s in results["descriptive_summary"] if s["drop_rate"] == rate and s["arm"] == arm]
            need(len(saved) == 1, "Missing/duplicate summary")
            close(saved[0], summary, "Descriptive summary")
            summaries.append({**summary, "unique_model_input_combinations": len(unique),
                "duplicate_mask_evaluations": len(members) - len(unique)})
    return {"dataset": dataset, "status": "PASS_SAVED_EVIDENCE_AUDIT", "n_evaluation_nodes": len(y),
        "device_actual": results["device_actual"], "gpu_qualification": results["gpu_qualification"],
        "n_malicious_annotations": int(np.sum(y)), "records_checked": len(checked),
        "unique_model_input_combinations": len(unique_inputs), "duplicate_mask_evaluations": len(checked) - len(unique_inputs),
        "private_artifacts_hash_checked": len(inventory), "fit_artifacts_hash_checked": len(expected_fit),
        "results_sha256": digest(output / "RESULTS.json"), "fit_freeze_sha256": digest(output / "FIT_FREEZE.json"),
        "summaries": summaries, "conditions": checked}


def audit(outputs, data_dir, config_path, registration_path, repo):
    config, registration, manifest = verify_sources(config_path, data_dir, registration_path, repo)
    report = {"status": "PASS_SAVED_EVIDENCE_AUDIT", "scope": "DEVELOPMENT_ONLY",
        "created_utc": datetime.now(timezone.utc).isoformat(), "auditor_sha256": digest(Path(__file__)),
        "registration_sha256": digest(registration_path), "source_commit": registration["git_commit"],
        "config_sha256": digest(config_path), "data_manifest_sha256": digest(data_dir / "MANIFEST.json"),
        "verification": "Independent metric/AP/error and mask/degree/routing recalculation; file-hash binding of fitting artifacts.",
        "limitations": ["Checkpoint bytes were hash-verified; models were not deserialized or inference-rerun.",
            "Stored freeze declarations and source ordering are checked; JSON receipts alone do not externally attest wall-clock label-access order.",
            "Two 100%-removal masks describe the same empty-edge graph; duplicate evaluations are not independent evidence.",
            "Seeds and nodes do not establish independent campaign replication or production performance."],
        "datasets": []}
    for dataset in config["datasets"]:
        report["datasets"].append(audit_dataset(outputs / dataset, dataset, config, registration, registration_path, data_dir, manifest))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[4]
    try:
        result = audit(args.outputs.resolve(), args.data_dir.resolve(), args.config.resolve(), args.registration.resolve(), repo)
    except Exception as error:
        result = {"status": "FAIL_SAVED_EVIDENCE_AUDIT", "error_type": type(error).__name__, "reason": str(error),
                  "auditor_sha256": digest(Path(__file__))}
        code = 1
    else:
        code = 0
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "report": str(args.report),
                      "datasets_checked": len(result.get("datasets", []))}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
