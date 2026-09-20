"""Audit saved robustness outputs; only calibration model inference is allowed.

No fitting, tuning, test inference, source mutation, or human label adjudication.
The cached path is intended for large Casino corpora. An uncached small-corpus
path is supported when the current replay/runner bytes match its pre-fit receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

import joblib
import numpy as np
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)


class AuditFailure(ValueError):
    pass


def _require(condition, message):
    if not bool(condition):
        raise AuditFailure(message)


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _safe_name(value):
    _require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", value)
             and value not in {".", ".."}, "Unsafe artifact identifier")
    return value


def _target_labels(events, target):
    # Deliberately independent of the evaluated run.is_target function.
    return np.asarray([any(label == target or re.split(r"[.:]", label, maxsplit=1)[0] == target
                           for label in event["labels"]) for event in events], dtype=np.int8)


def _metrics(labels, scores, observed, threshold):
    predicted = (scores > threshold) & observed
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(labels, predicted, labels=[0, 1]).ravel())
    positive, negative = int(labels.sum()), len(labels) - int(labels.sum())
    return {"n": len(labels), "positive": positive, "negative": negative,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)) if positive else None,
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "negative_label_flag_rate": fp / negative if negative else None,
        "roc_auc": float(roc_auc_score(labels, scores)) if positive and negative else None,
        "average_precision": float(average_precision_score(labels, scores)) if positive else None,
        "observed_targets": int(observed.sum()), "observation_coverage": float(observed.mean()) if len(labels) else None,
        "unobserved_positive_targets": int(((labels == 1) & ~observed).sum())}


def _equal_metrics(reported, actual, scope):
    for key, value in actual.items():
        candidate = reported.get(key)
        if value is None or isinstance(value, int):
            _require(candidate == value, scope + ": count/undefined metric mismatch: " + key)
        else:
            _require(type(candidate) in (float, int) and math.isclose(candidate, value, rel_tol=1e-12, abs_tol=1e-12),
                     scope + ": continuous metric mismatch: " + key)


def _threshold(value):
    kind, threshold = value["threshold_kind"], value["threshold_value"]
    if kind == "finite":
        _require(type(threshold) in (float, int) and math.isfinite(threshold), "Invalid finite threshold")
        return float(threshold)
    _require(threshold is None and kind in {"positive_infinity", "negative_infinity"}, "Invalid threshold encoding")
    return math.inf if kind == "positive_infinity" else -math.inf


def _git_receipt(code_paths):
    root = Path(__file__).parents[3]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        matches = {}
        for name, path in code_paths.items():
            blob = subprocess.check_output(["git", "show", commit + ":" + path.relative_to(root).as_posix()], cwd=root, stderr=subprocess.DEVNULL)
            matches[name] = hashlib.sha256(blob).hexdigest() == _sha(path)
        return {"audit_time_head": commit, "current_code_equals_head": matches,
                "prefit_commit_attested": False,
                "note": "The original pre-fit receipt records code hashes, not a Git commit. This is an audit-time commit comparison only."}
    except (subprocess.SubprocessError, OSError, ValueError):
        return {"audit_time_head": None, "prefit_commit_attested": False,
                "note": "Git binding unavailable; original pre-fit/current source hash checks still apply."}


def _audit(run, events_path, manifest_path, feature_cache):
    result, receipt = _read(run / "RESULTS.json"), _read(run / "PRE_FIT_RECEIPT.json")
    source_manifest = _read(manifest_path)
    protocol = receipt["protocol"]
    _require(result["status"] == "COMPLETE" and receipt["frozen_before_fit"] is True, "Run is not complete/frozen")
    hashes = {}

    def bind(path, name, expected=None):
        digest = _sha(path)
        if expected is not None:
            _require(digest == expected, "Hash mismatch: " + name)
        hashes[name] = digest
        return digest

    bind(run / "RESULTS.json", "RESULTS.json")
    bind(run / "PRE_FIT_RECEIPT.json", "PRE_FIT_RECEIPT.json")
    event_sha = bind(events_path, "source_events", result["input_sha256"])
    bind(manifest_path, "source_manifest", result["manifest_sha256"])
    _require(receipt["input_sha256"] == event_sha == source_manifest["events_sha256"], "Source event hash chain mismatch")
    _require(receipt["protocol_sha256"] == result["protocol_sha256"], "Protocol hash chain mismatch")
    _require(set(result["targets"]) == set(protocol["datasets"][result["dataset"]]["targets"]), "Target roster differs from frozen protocol")
    here = Path(__file__).parent
    code_paths = {"run.py": here / "run.py", "replay.py": here / "replay.py",
                  "models.py": here.parent / "models.py", "feature_cache.py": here / "feature_cache.py",
                  "replay_fast.py": here / "replay_fast.py"}
    for name, expected in receipt["code_sha256"].items():
        _require(name in code_paths, "Unknown code file in pre-fit receipt")
        bind(code_paths[name], "code/" + name, expected)
    code_paths = {name: code_paths[name] for name in receipt["code_sha256"]}
    cache_manifest = None
    if feature_cache is not None:
        from .feature_cache import CachedReplay
        feature_cache = Path(feature_cache)
        if feature_cache.name == "MANIFEST.json":
            feature_cache = feature_cache.parent
        cache_sha = bind(feature_cache / "MANIFEST.json", "cache/MANIFEST.json", result["feature_cache_manifest_sha256"])
        _require(receipt["feature_cache_manifest_sha256"] == cache_sha, "Pre-fit cache binding mismatch")
        replay = CachedReplay(feature_cache, protocol, event_sha)
        cache_manifest = replay.manifest
        _require(cache_manifest["source_manifest_sha256"] == result["manifest_sha256"], "Cache source manifest mismatch")
        _require(cache_manifest["protocol_sha256"] == result["protocol_sha256"], "Cache raw protocol hash mismatch")
        bind(feature_cache / cache_manifest["targets_file"], "cache/TARGETS.jsonl", cache_manifest["targets_sha256"])
        for role, mapping in cache_manifest["role_mapping"].items():
            replay._checked_file(mapping["file"], mapping["sha256"])
            bind(feature_cache / mapping["file"], "cache/role_mapping/" + role, mapping["sha256"])
        for key, entry in cache_manifest["matrices"].items():
            for field in ("matrix", "observed"):
                replay._checked_file(entry[field], entry[field + "_sha256"])
                bind(feature_cache / entry[field], "cache/" + key + "/" + field, entry[field + "_sha256"])
        events, source_count = replay.events, replay.source_event_count
    else:
        _require("feature_cache_manifest_sha256" not in result, "Original run requires its bound feature cache")
        from .replay import Replay, load_events
        events = load_events(events_path)
        source_count = len(events)
        replay = Replay(events, protocol["history"]["seconds"], protocol["history"]["max_events"])
    eligible = np.asarray([i for i, event in enumerate(events) if event.get("target_eligible", True)], dtype=np.int64)
    split_indices = {role: np.asarray([i for i in eligible if events[i]["split"] == role], dtype=np.int64)
                     for role in ("fit", "development", "calibration", "test")}
    _require(source_count == result["events"] and len(eligible) == result["eligible_targets"], "Source/target counts mismatch")
    test_indices, calibration_indices = split_indices["test"], split_indices["calibration"]
    test_runs = np.asarray([events[i]["run_id"] for i in test_indices])
    expected_ids = np.asarray([events[i]["event_id"] for i in test_indices])
    _require(len(set(expected_ids)) == len(expected_ids), "Repeated target identity")
    bind(run / "PRIVATE_TARGET_ROSTER.npz", "PRIVATE_TARGET_ROSTER.npz")
    with np.load(run / "PRIVATE_TARGET_ROSTER.npz", allow_pickle=False) as saved:
        _require(np.array_equal(saved["event_ids"], expected_ids) and np.array_equal(saved["run_ids"], test_runs), "Saved target roster/order mismatch")
    del expected_ids
    conditions = {value["name"]: value for value in protocol["conditions"]}
    _require(len(conditions) == len(protocol["conditions"]), "Repeated frozen condition name")
    expected_grid = {(condition["name"], seed, arm) for condition in protocol["conditions"]
                     for seed in (protocol["seeds"] if condition["kind"] == "random" else protocol["seeds"][:1])
                     for arm in protocol["models"]}
    clean = protocol["conditions"][0]
    _require(clean["kind"] == "clean", "Frozen calibration condition is not clean")
    dimensions, fit_seed = protocol["text_features"]["hash_dimensions_per_block"], protocol["classifier"]["random_state"]
    calibration_features, observation_masks = {}, {}
    target_audits, fitted_model_paths, prediction_paths = [], [], []
    total_rows, metric_checks = 0, 0
    for target, record in result["targets"].items():
        _safe_name(target)
        labels = _target_labels(events, target)
        support = {role: {"n": len(idx), "positive": int(labels[idx].sum()), "negative": int(len(idx) - labels[idx].sum())}
                   for role, idx in split_indices.items()}
        _require(record["support"] == support, "Target support mismatch: " + target)
        supported = all(support[role]["positive"] and support[role]["negative"] for role in ("fit", "calibration", "test"))
        audited = {"target": target, "support": support, "status": record["status"], "calibration": [], "results": [], "full_delay_recovery": []}
        target_audits.append(audited)
        if not supported:
            _require(record["status"] == "UNSUPPORTED_BOTH_CLASSES_REQUIRED" and not record["models"] and not record["results"], "Unsupported target was fitted or reported as a scored failure")
            audited["interpretation"] = "Insufficient class support; no failed-method or zero-detection conclusion."
            continue
        _require(record["status"] == "COMPLETE" and set(record["models"]) == set(protocol["models"]), "Completed target model roster mismatch")
        ycal, ytest = labels[calibration_indices], labels[test_indices]
        thresholds = {}
        for arm, model_info in record["models"].items():
            _safe_name(arm)
            path = run / f"{target}_{arm}.joblib"
            bind(path, path.name, model_info["model_sha256"])
            fitted_model_paths.append(path)
            family = "entity_context" if arm == "context_dropout" else arm
            if family not in calibration_features:
                calibration_features[family] = replay.matrix(calibration_indices, clean, fit_seed, family, dimensions)
            matrix, observed = calibration_features[family]
            # These are locally generated models; the byte hash is checked
            # immediately before deserialization, and again after inference.
            _require(_sha(path) == model_info["model_sha256"], "Model changed before trusted local load")
            model = joblib.load(path)
            _require(set(model.classes_) == {0, 1}, "Saved model class orientation is invalid")
            scores = model.predict_proba(matrix)[:, list(model.classes_).index(1)]
            scores[~observed] = 0
            _require(np.isfinite(scores).all() and ((0 <= scores) & (scores <= 1)).all(), "Invalid derivative calibration scores")
            budget = Fraction(str(float(protocol["calibration"]["negative_label_fpr_budget"])))
            _require(0 <= budget <= 1, "Invalid frozen flag-rate budget")
            negative = np.sort(scores[ycal == 0])
            allowed = budget.numerator * len(negative) // budget.denominator
            index = len(negative) - allowed - 1
            derived = -math.inf if allowed == len(negative) else float(negative[index])
            original = _threshold(model_info["threshold"])
            _require(derived == original, "Frozen threshold failed independent exact rank reproduction: " + target + "/" + arm)
            thresholds[arm] = original
            counts = _metrics(ycal, scores, np.ones(len(ycal), dtype=bool), derived)
            confusion = {key: counts[key] for key in ("tp", "fp", "tn", "fn")}
            value = model_info["threshold"]
            _require(confusion == value["confusion"] and allowed == value["allowed_false_positives"], "Calibration confusion/budget mismatch")
            _require(value["n_rows"] == len(ycal) and value["n_attack"] == int(ycal.sum()) and value["n_benign"] == len(negative), "Calibration class support mismatch")
            _require(math.isclose(value["observed_recall"], counts["recall"], abs_tol=1e-12) and math.isclose(value["observed_fpr"], counts["negative_label_flag_rate"], abs_tol=1e-12), "Calibration rates mismatch")
            _require(_sha(path) == model_info["model_sha256"], "Saved model changed during audit")
            audited["calibration"].append({"arm": arm, "rows": len(ycal), "positive": int(ycal.sum()),
                "negative": len(negative), "allowed_negative_flags": allowed,
                "zero_based_negative_order_index": index if allowed < len(negative) else None,
                "threshold_kind": value["threshold_kind"], "threshold_value": value["threshold_value"],
                "exact_threshold_match": True, "confusion": confusion,
                "derivative_score_array_sha256": hashlib.sha256(scores.astype("<f8", copy=False).tobytes()).hexdigest(),
                "observed_mask_sha256": hashlib.sha256(observed.tobytes()).hexdigest(),
                "model_sha256_before_load": model_info["model_sha256"]})
            del model, scores
        seen, arrays = set(), {}
        for row in record["results"]:
            condition, seed, arm = row["condition"], row["seed"], row["arm"]
            _safe_name(condition)
            _require(type(seed) is int and (condition, seed, arm) in expected_grid, "Unknown result condition/seed/arm")
            key = (condition, seed, arm)
            _require(key not in seen, "Duplicate prediction result")
            seen.add(key)
            _require(row["deadline_seconds"] == conditions[condition].get("deadline", 0), "Decision deadline mismatch")
            path = run / f"PRIVATE_{target}_{arm}_{condition}_{seed}.npz"
            bind(path, path.name)
            prediction_paths.append(path)
            with np.load(path, allow_pickle=False) as saved:
                y, scores, observed = saved["y"].copy(), saved["score"].copy(), saved["observed"].copy()
            _require(y.shape == scores.shape == observed.shape == (len(ytest),) and np.array_equal(y, ytest), "Prediction labels/order/shape mismatch")
            _require(observed.dtype == np.bool_ and np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all(), "Invalid saved score/mask")
            _require(np.all(scores[~observed] == 0), "Unobserved targets have nonzero scores")
            family = "entity_context" if arm == "context_dropout" else arm
            mask_key = (condition, seed, family)
            if mask_key not in observation_masks:
                if cache_manifest is not None:
                    specification = {"role": "test", "family": family, "condition": conditions[condition], "seed": seed, "dimensions": dimensions}
                    matrix_key = hashlib.sha256(_canonical(specification).encode()).hexdigest()
                    entry = cache_manifest["matrices"][matrix_key]
                    mask = np.load(replay._checked_file(entry["observed"], entry["observed_sha256"]), allow_pickle=False)
                else:
                    matrix, mask = replay.matrix(test_indices, conditions[condition], seed, family, dimensions)
                    del matrix
                observation_masks[mask_key] = mask
            _require(np.array_equal(observed, observation_masks[mask_key]), "Saved observation mask differs from bound replay/cache")
            actual = {"condition": condition, "seed": seed, "arm": arm, "deadline_seconds": row["deadline_seconds"],
                      "fixed_0_5": _metrics(y, scores, observed, .5),
                      "calibrated": _metrics(y, scores, observed, thresholds[arm]), "by_run": {}}
            for mode in ("fixed_0_5", "calibrated"):
                _equal_metrics(row[mode], actual[mode], target + "/" + condition + "/" + arm)
                metric_checks += len(actual[mode])
            _require(set(row["by_run"]) == set(test_runs), "Per-run metric roster mismatch")
            for run_id in sorted(set(test_runs)):
                selected = test_runs == run_id
                actual["by_run"][run_id] = {"fixed_0_5": _metrics(y[selected], scores[selected], observed[selected], .5),
                    "calibrated": _metrics(y[selected], scores[selected], observed[selected], thresholds[arm])}
                for mode in ("fixed_0_5", "calibrated"):
                    _equal_metrics(row["by_run"][run_id][mode], actual["by_run"][run_id][mode], "Per-run metric")
                    metric_checks += len(actual["by_run"][run_id][mode])
            audited["results"].append(actual)
            arrays[key] = (scores, observed)
            total_rows += 1
        _require(seen == expected_grid, "Missing fixed condition/seed/model results")
        for condition in conditions.values():
            if condition["kind"] != "delay" or condition.get("deadline", 0) < condition["delay_seconds"]:
                continue
            for arm in protocol["models"]:
                clean_arrays = arrays[(clean["name"], protocol["seeds"][0], arm)]
                waited_arrays = arrays[(condition["name"], protocol["seeds"][0], arm)]
                equal = all(np.array_equal(a, b) for a, b in zip(clean_arrays, waited_arrays))
                _require(equal, "Full deterministic-delay recovery differs from clean control")
                audited["full_delay_recovery"].append({"condition": condition["name"], "arm": arm,
                    "scores_and_observation_masks_exactly_equal_clean": True,
                    "interpretation": "Expected buffering control by construction; not learned robustness"})
        del arrays
        print(json.dumps({"audited_target": target, "results": len(audited["results"]), "calibrations": len(audited["calibration"])}), flush=True)
    chronology = {"filesystem_order_consistent": None,
        "interpretation": "Local file times are supporting evidence, not independently attested execution timestamps."}
    if fitted_model_paths and prediction_paths:
        chronology["filesystem_order_consistent"] = ((run / "PRE_FIT_RECEIPT.json").stat().st_mtime
            <= min(path.stat().st_mtime for path in fitted_model_paths)
            <= max(path.stat().st_mtime for path in fitted_model_paths)
            <= min(path.stat().st_mtime for path in prediction_paths)
            <= (run / "RESULTS.json").stat().st_mtime)
    return {"status": "PASS", "audit_kind": "INDEPENDENT_AI_CODE_AND_SAVED_OUTPUT_AUDIT_NOT_HUMAN_REVIEW",
        "created_utc": datetime.now(timezone.utc).isoformat(), "auditor_sha256": _sha(Path(__file__)),
        "dataset": result["dataset"], "source_events": source_count, "eligible_targets": len(eligible),
        "test_targets": len(test_indices), "test_run_counts": dict(Counter(str(x) for x in test_runs)),
        "verified_result_rows": total_rows, "metric_scalar_comparisons": metric_checks,
        "hashes": hashes, "git": _git_receipt(code_paths), "chronology": chronology,
        "execution_scope": {"model_fit": False, "test_model_inference": False,
                            "saved_model_calibration_inference": True, "new_threshold_tuning": False},
        "method": "Independent sklearn/direct metric arithmetic and strict sorted-negative calibration ranks. Original feature implementation reused only for authorized calibration inference; bound cache masks used to verify test observation coverage.",
        "source_label_scope": "Target labels independently derived from source-bound eligible event metadata; no independent human adjudication of process/event labels or author rules.",
        "targets": target_audits,
        "limitations": [
            "Fixed0.5 and separately frozen calibration thresholds are different operating points; an advantage at one is not an advantage at every flag budget.",
            "An empirical calibration flag budget does not establish reliable population or operational false-alarm control under shift.",
            "Positive source events, runs and corruption seeds can be correlated; no independent campaign count or confidence claim.",
            "Runs without positive target labels have no evaluated positive-class capability; numerical F1=0 follows the upstream convention only.",
            "Completely unobserved targets remain in the denominator with score0/no alarm; their evaluator-known roster is not a deployment trigger.",
            "AIT singleton deletion often removes whole events. Casino negatives are other source-annotated techniques, not verified benign activity.",
            "Synthetic deterministic delays use source event clocks, not measured collection times; full recovery after the delay is expected by construction.",
            "The feature cache was separately qualified against Replay; this audit binds its artifacts but does not independently reimplement all feature semantics.",
            "This audit validates reported computation, not novel mechanism, larger-model need, or broad robustness/generalization."]}


def audit_results(run, events, manifest, output, feature_cache=None):
    run, events, manifest, output = map(Path, (run, events, manifest, output))
    if output.exists():
        raise FileExistsError("Refusing to overwrite audit evidence")
    output.mkdir(parents=True)
    try:
        result = _audit(run, events, manifest, feature_cache)
    except AuditFailure as error:
        result = {"status": "FAIL", "audit_kind": "AI_CODE_AUDIT", "issue": str(error)}
        (output / "AUDIT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (output / "AUDIT.md").write_text("# Robustness result audit\n\n**FAIL:** " + str(error) + "\n", encoding="utf-8")
        raise
    (output / "AUDIT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Independent robustness result audit", "", "**PASS** for saved-result computation and frozen calibration. This is an AI/code audit, not human label review or validation of novelty.", "",
        f"Dataset: **{result['dataset']}**. {result['source_events']:,} context/source events; {result['eligible_targets']:,} eligible targets; {result['test_targets']:,} fixed test targets. Verified {result['verified_result_rows']} condition/model results at both operating points, pooled and per run.", "",
        "## Checks", "", "- Streamed source hash, source manifest, original pre-fit code hashes, saved models, target roster and all used aggregate cache matrix/mask/row hashes verified.",
        "- Labels derived independently from eligible source-bound metadata; all prediction rows preserve their order and target denominator.",
        "- Confusion counts, precision/recall/F1, continuous-score ROC-AUC/AP, observation coverage and hidden-positive counts independently recomputed.",
        "- Saved models were loaded only after byte verification for calibration-only inference. Strict sorted-negative thresholds and calibration confusion counts reproduced exactly. No fitting, test inference or tuning.", "",
        "## Target support", "", "| Target | Status | Test positives | Test negatives | Verified result rows |", "|---|---|---:|---:|---:|"]
    for target in result["targets"]:
        support = target["support"]["test"]
        lines.append(f"| {target['target']} | {target['status']} | {support['positive']} | {support['negative']} | {len(target['results'])} |")
    lines += ["", "## Interpretation limits", ""] + ["- " + text for text in result["limitations"]]
    lines += ["", "The pre-fit receipt binds source bytes but does not attest a Git commit or independent timestamp. Audit-time Git comparison and filesystem chronology are reported explicitly in [AUDIT.json](AUDIT.json), alongside all recomputed results, source hashes, calibration checks and delay-control equality checks.", ""]
    (output / "AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--feature-cache", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit_results(args.run, args.events, args.manifest, args.output, args.feature_cache)
    print(json.dumps({"status": result["status"], "verified_results": result["verified_result_rows"]}), flush=True)


if __name__ == "__main__":
    main()
