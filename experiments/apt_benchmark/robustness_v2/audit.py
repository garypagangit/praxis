"""Independently audit saved v2 scores; permit calibration-only model inference.

No fitting, tuning, or test-model inference. This is a calculation/provenance
audit, not human source-label adjudication or external scientific confirmation.
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

import joblib
import numpy as np
from scipy import sparse
from sklearn.metrics import average_precision_score, roc_auc_score


class AuditFailure(ValueError):
    pass


def require(value, message):
    if not bool(value):
        raise AuditFailure(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def safe_name(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", value)
            and value not in {".", ".."}, "Unsafe artifact identifier")
    return value


def target_labels(events, target):
    # Independent of the runner's label parser.
    return np.asarray([any(label == target or re.split(r"[.:]", label, maxsplit=1)[0] == target
                           for label in e["labels"]) for e in events], dtype=np.int8)


def validate_arrays(y, score, observed, expected_y):
    require(y.shape == score.shape == observed.shape == expected_y.shape,
            "Prediction array shape/order mismatch")
    require(np.array_equal(y, expected_y), "Saved labels differ from source-bound targets")
    require(observed.dtype == np.bool_, "Observation mask is not boolean")
    require(np.isfinite(score).all() and ((0 <= score) & (score <= 1)).all(), "Invalid saved score")
    require(np.all(score[~observed] == 0), "Unobserved target has nonzero score")


def metrics(y, score, observed, threshold):
    y = np.asarray(y, dtype=bool)
    prediction = (score > threshold) & observed
    tp = int(np.count_nonzero(prediction & y))
    fp = int(np.count_nonzero(prediction & ~y))
    fn = int(np.count_nonzero(~prediction & y))
    tn = int(np.count_nonzero(~prediction & ~y))
    positive, negative = tp + fn, fp + tn
    return {"n": len(y), "positive": positive, "negative": negative,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / positive if positive else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            "negative_label_flag_rate": fp / negative if negative else None,
            "roc_auc": float(roc_auc_score(y, score)) if positive and negative else None,
            "average_precision": float(average_precision_score(y, score)) if positive else None,
            "observed_targets": int(observed.sum()),
            "observation_coverage": float(observed.mean()) if len(y) else None,
            "unobserved_positive_targets": int(np.count_nonzero(y & ~observed))}


def compare_metrics(reported, actual, scope):
    for name, value in actual.items():
        require(name in reported, scope + ": missing metric " + name)
        candidate = reported[name]
        if value is None or type(value) is int:
            require(candidate == value, scope + ": count/undefined mismatch " + name)
        else:
            require(type(candidate) in (int, float) and math.isclose(candidate, value, rel_tol=1e-12, abs_tol=1e-12),
                    scope + ": numeric mismatch " + name)


def decode_threshold(value):
    kind, number = value.get("threshold_kind"), value.get("threshold_value")
    if kind == "finite":
        require(type(number) in (int, float) and math.isfinite(number), "Invalid finite threshold")
        return float(number)
    require(kind in {"positive_infinity", "negative_infinity"} and number is None, "Invalid infinite threshold")
    return math.inf if kind == "positive_infinity" else -math.inf


def audit_threshold(y, score, budget, reported):
    """Derive the exact strict threshold independently from sorted negatives."""
    fraction = Fraction(str(float(budget)))
    require(0 <= fraction <= 1, "Invalid calibration budget")
    negatives = np.sort(score[y == 0])
    positive = int(np.count_nonzero(y))
    require(positive and len(negatives), "Calibration requires both source classes")
    allowed = len(negatives) * fraction.numerator // fraction.denominator
    rank = len(negatives) - allowed - 1
    expected = -math.inf if allowed == len(negatives) else float(negatives[rank])
    require(decode_threshold(reported) == expected, "Threshold differs from independent negative-score rank")
    # The existing threshold selector computes its diagnostic confusion from
    # scores alone, which already force unobserved scores to zero.
    counts = metrics(y, score, np.ones(len(y), dtype=bool), expected)
    require(reported["confusion"] == {k: counts[k] for k in ("tp", "fp", "tn", "fn")}, "Calibration confusion mismatch")
    require(reported["allowed_false_positives"] == allowed, "Calibration allowed-flag count mismatch")
    require(reported["n_rows"] == len(y) and reported["n_attack"] == positive
            and reported["n_benign"] == len(negatives), "Calibration support mismatch")
    require(math.isclose(reported["observed_recall"], counts["recall"], abs_tol=1e-12)
            and math.isclose(reported["observed_fpr"], counts["negative_label_flag_rate"], abs_tol=1e-12), "Calibration rate mismatch")
    require(reported["max_fpr"] == float(budget), "Calibration budget differs from protocol")
    return {"threshold_kind": reported["threshold_kind"], "threshold_value": reported["threshold_value"],
            "negative_order_index": rank if rank >= 0 else None, "allowed_negative_flags": allowed,
            "confusion": reported["confusion"], "exact_threshold_match": True}, expected


def expected_grid(protocol):
    conditions = protocol["conditions"]
    require(len({c["name"] for c in conditions}) == len(conditions), "Duplicate protocol condition")
    require(len(set(protocol["models"])) == len(protocol["models"]), "Duplicate protocol model")
    return {(c["name"], seed, arm) for c in conditions
            for seed in (protocol["seeds"] if c["kind"] == "random" else protocol["seeds"][:1])
            for arm in protocol["models"]}


def observed_states(matrix, dimensions):
    bits = matrix[:, [2 * dimensions + 2, 2 * dimensions + 3]].toarray()
    require(np.isin(bits, [0, 1]).all(), "Route features are not binary observed-presence indicators")
    return bits[:, 0].astype(np.int8) + 2 * bits[:, 1].astype(np.int8)


def route_counts(matrix, observed, dimensions):
    states = observed_states(matrix, dimensions)
    return {str(state): int(np.count_nonzero((states == state) & observed)) for state in range(4)}


def audit_primary_screen(record, protocol):
    """Only call after every individual result metric has been reproduced."""
    spec = protocol["primary_comparison"]
    selectors = {"command_records_absent_f1_delta_min": ("command_records_absent", "f1"),
                 "command_records_absent_recall_delta_min": ("command_records_absent", "recall"),
                 "command_records_absent_flag_rate_delta_max": ("command_records_absent", "negative_label_flag_rate"),
                 "clean_f1_delta_min": ("clean", "f1"), "random_50_mean_f1_delta_min": ("random_50", "f1")}
    require(set(selectors) == set(spec["per_target_gates"]), "Unknown primary screening gate")
    values = {}
    for name, (condition, metric) in selectors.items():
        means = []
        for arm in (spec["candidate"], spec["baseline"]):
            data = [r[spec["point"]][metric] for r in record["results"] if r["arm"] == arm and r["condition"] == condition]
            require(data and all(v is not None and math.isfinite(v) for v in data), "Missing/undefined primary screening data")
            means.append(math.fsum(data) / len(data))
        delta, limit = means[0] - means[1], spec["per_target_gates"][name]
        passed = delta <= limit + 1e-12 if name.endswith("_max") else delta >= limit - 1e-12
        values[name] = {"delta": delta, "limit": limit, "passed": passed}
        reported = record["primary_screen"]["checks"][name]
        require(math.isclose(reported["delta"], delta, rel_tol=1e-12, abs_tol=1e-12)
                and reported["limit"] == limit and reported["passed"] is passed, "Primary screening check mismatch: " + name)
    status = "PASS" if all(v["passed"] for v in values.values()) else "FAIL"
    require(record["primary_screen"]["status"] == status, "Primary screening status mismatch")
    return {"status": status, "checks": values, "interpretation": "Independently reproduced descriptive gates; no population guarantee"}


def resolve_code(name):
    root = Path(__file__).resolve().parents[3]
    if "/" in name or "\\" in name:
        candidate = (root / name).resolve()
        require(candidate.is_relative_to(root) and candidate.is_file(), "Unresolved pre-fit code path")
        return candidate
    here = Path(__file__).parent
    aliases = {"run.py": here / "run.py", "feature_cache.py": here / "feature_cache.py",
               "replay.py": here.parent / "robustness" / "replay.py",
               "replay_fast.py": here.parent / "robustness" / "replay_fast.py",
               "models.py": here.parent / "models.py", "audit.py": Path(__file__)}
    require(name in aliases, "Unknown pre-fit code alias")
    return aliases[name]


def _audit(run, events_path, manifest_path, feature_cache, protocol_path, calibration_inference):
    result, receipt, manifest = read(run / "RESULTS.json"), read(run / "PRE_FIT_RECEIPT.json"), read(manifest_path)
    protocol = receipt["protocol"]
    require(result["status"] == "COMPLETE" and receipt["frozen_before_fit"] is True, "Run is not complete/frozen")
    hashes, bound_local = {}, {}

    def bind(path, name, expected=None):
        digest = sha(path)
        require(expected is None or digest == expected, "Hash mismatch: " + name)
        hashes[name] = digest
        return digest

    bind(run / "RESULTS.json", "RESULTS.json")
    bind(run / "PRE_FIT_RECEIPT.json", "PRE_FIT_RECEIPT.json")
    event_sha = bind(events_path, "source_events", result["input_sha256"])
    source_manifest_sha = bind(manifest_path, "source_manifest", result["manifest_sha256"])
    require(receipt["input_sha256"] == event_sha == manifest["events_sha256"], "Source hash chain mismatch")
    if "manifest_sha256" in receipt:
        require(receipt["manifest_sha256"] == source_manifest_sha, "Pre-fit source manifest mismatch")
    require(receipt["protocol_sha256"] == result["protocol_sha256"], "Protocol hash chain mismatch")
    protocol_path = Path(protocol_path) if protocol_path else run / "PROTOCOL.json"
    if not protocol_path.is_file():
        protocol_path = Path(__file__).with_name("protocol.json")
    require(protocol_path.is_file(), "Raw frozen protocol required; supply --protocol")
    bind(protocol_path, "protocol", result["protocol_sha256"])
    require(canonical(read(protocol_path)) == canonical(protocol), "Embedded protocol differs from frozen bytes")
    require(bool(receipt["code_sha256"]), "Missing pre-fit code bindings")
    for name, expected in receipt["code_sha256"].items():
        path = resolve_code(name)
        bind(path, "code/" + name, expected)
        bound_local[path] = expected
    require(set(result["targets"]) == set(protocol["datasets"][result["dataset"]]["targets"]), "Target roster differs from protocol")

    cache_manifest = None
    if feature_cache is not None:
        from .feature_cache import CachedReplay
        cache_root = Path(feature_cache)
        if cache_root.name == "MANIFEST.json":
            cache_root = cache_root.parent
        cache_sha = bind(cache_root / "MANIFEST.json", "cache/MANIFEST.json", result["feature_cache_manifest_sha256"])
        require(receipt["feature_cache_manifest_sha256"] == cache_sha, "Pre-fit cache hash mismatch")
        replay = CachedReplay(cache_root, protocol, event_sha)
        cache_manifest = replay.manifest
        require(cache_manifest["source_manifest_sha256"] == source_manifest_sha, "Cache source manifest mismatch")
        require(cache_manifest["protocol_sha256"] == result["protocol_sha256"], "Cache raw protocol mismatch")
        bind(replay._checked_file(cache_manifest["targets_file"], cache_manifest["targets_sha256"]), "cache/targets", cache_manifest["targets_sha256"])
        for role, entry in cache_manifest["role_mapping"].items():
            bind(replay._checked_file(entry["file"], entry["sha256"]), "cache/rows/" + role, entry["sha256"])
        for key, entry in cache_manifest["matrices"].items():
            for field in ("matrix", "observed"):
                bind(replay._checked_file(entry[field], entry[field + "_sha256"]), "cache/" + key + "/" + field, entry[field + "_sha256"])
        events, source_count = replay.events, replay.source_event_count
    else:
        require("feature_cache_manifest_sha256" not in result, "Original cache is required")
        from ..robustness.replay import Replay, load_events
        events = load_events(events_path)
        source_count = len(events)
        replay = Replay(events, protocol["history"]["seconds"], protocol["history"]["max_events"])
    eligible = np.asarray([i for i, e in enumerate(events) if e.get("target_eligible", True)], dtype=np.int64)
    indices = {role: np.asarray([i for i in eligible if events[i]["split"] == role], dtype=np.int64)
               for role in ("fit", "development", "calibration", "test")}
    require(source_count == result["events"] and len(eligible) == result["eligible_targets"], "Input/target count mismatch")
    require(len({events[i]["event_id"] for i in eligible}) == len(eligible), "Duplicate eligible identity")
    run_roles = {}
    for i in eligible:
        run_roles.setdefault(events[i]["run_id"], set()).add(events[i]["split"])
    require(all(len(x) == 1 for x in run_roles.values()), "Execution crosses splits")
    test_idx, cal_idx = indices["test"], indices["calibration"]
    test_runs = np.asarray([events[i]["run_id"] for i in test_idx])
    bind(run / "PRIVATE_TARGET_ROSTER.npz", "PRIVATE_TARGET_ROSTER.npz")
    with np.load(run / "PRIVATE_TARGET_ROSTER.npz", allow_pickle=False) as saved:
        require(np.array_equal(saved["event_ids"], [events[i]["event_id"] for i in test_idx])
                and np.array_equal(saved["run_ids"], test_runs), "Saved test roster differs from source order")
    grid = expected_grid(protocol)
    conditions = {c["name"]: c for c in protocol["conditions"]}
    clean = protocol["conditions"][0]
    require(clean["kind"] == "clean", "Calibration view is not clean")
    seed, dimensions = protocol["classifier"]["random_state"], protocol["text_features"]["hash_dimensions_per_block"]
    cal_features, masks, routes, audits = {}, {}, {}, []
    rows_checked = 0
    for target, record in result["targets"].items():
        safe_name(target)
        labels = target_labels(events, target)
        support = {role: {"n": len(idx), "positive": int(labels[idx].sum()), "negative": int(len(idx) - labels[idx].sum())}
                   for role, idx in indices.items()}
        require(record["support"] == support, "Source support mismatch: " + target)
        audited = {"target": target, "status": record["status"], "support": support, "calibration": [], "verified_results": 0, "delay_controls": []}
        audits.append(audited)
        supported = all(support[s]["positive"] and support[s]["negative"] for s in ("fit", "calibration", "test"))
        if not supported:
            require(record["status"] == "UNSUPPORTED_BOTH_CLASSES_REQUIRED" and not record["models"] and not record["results"], "Unsupported target has fitted outputs")
            continue
        require(record["status"] == "COMPLETE" and set(record["models"]) == set(protocol["models"]), "Model roster mismatch")
        ycal, ytest = labels[cal_idx], labels[test_idx]
        thresholds = {}
        for arm, info in record["models"].items():
            safe_name(arm)
            family = protocol["arms"][arm]["family"]
            model_path = run / f"{target}_{arm}.joblib"
            bind(model_path, model_path.name, info["model_sha256"])
            bound_local[model_path] = info["model_sha256"]
            if family not in cal_features:
                cal_features[family] = replay.matrix(cal_idx, clean, seed, family, dimensions)
            X, expected_observed = cal_features[family]
            if "calibration_observed_route_counts" in info:
                require(info["calibration_observed_route_counts"] == route_counts(X, expected_observed, dimensions), "Calibration route counts mismatch")
            cal_path = run / f"PRIVATE_CAL_{target}_{arm}.npz"
            bind(cal_path, cal_path.name)
            with np.load(cal_path, allow_pickle=False) as saved:
                y, score, observed = saved["y"].copy(), saved["score"].copy(), saved["observed"].copy()
            validate_arrays(y, score, observed, ycal)
            require(np.array_equal(observed, expected_observed), "Saved calibration visibility differs from replay")
            if calibration_inference:
                from .run import predict_bundle
                require(sha(model_path) == info["model_sha256"], "Model changed before trusted load")
                bundle = joblib.load(model_path)
                inferred = predict_bundle(bundle, X, observed, dimensions)
                # Runner may return score plus routing diagnostics.
                if isinstance(inferred, tuple):
                    inferred = inferred[0]
                require(np.array_equal(np.asarray(inferred), score), "Calibration-only model inference differs from saved scores")
                del bundle, inferred
            checked, thresholds[arm] = audit_threshold(y, score, protocol["calibration"]["negative_label_fpr_budget"], info["threshold"])
            audited["calibration"].append({"arm": arm, "rows": len(y), **checked, "saved_model_scores_reproduced": bool(calibration_inference)})
        seen, arrays = set(), {}
        for row in record["results"]:
            name, row_seed, arm = row["condition"], row["seed"], row["arm"]
            safe_name(name)
            key = (name, row_seed, arm)
            require(type(row_seed) is int and key in grid and key not in seen, "Unexpected/duplicate result row")
            seen.add(key)
            condition = conditions[name]
            require(row["deadline_seconds"] == condition.get("deadline", 0), "Result deadline differs from protocol")
            prediction_path = run / f"PRIVATE_{target}_{arm}_{name}_{row_seed}.npz"
            bind(prediction_path, prediction_path.name)
            with np.load(prediction_path, allow_pickle=False) as saved:
                y, score, observed = saved["y"].copy(), saved["score"].copy(), saved["observed"].copy()
            validate_arrays(y, score, observed, ytest)
            family = protocol["arms"][arm]["family"]
            mask_key = (name, row_seed, family)
            if mask_key not in masks:
                if cache_manifest is not None:
                    spec = {"role": "test", "family": family, "condition": condition, "seed": row_seed, "dimensions": dimensions}
                    entry = cache_manifest["matrices"][hashlib.sha256(canonical(spec).encode()).hexdigest()]
                    masks[mask_key] = np.load(replay._checked_file(entry["observed"], entry["observed_sha256"]), allow_pickle=False)
                    test_matrix = sparse.load_npz(replay._checked_file(entry["matrix"], entry["matrix_sha256"]))
                else:
                    test_matrix, masks[mask_key] = replay.matrix(test_idx, condition, row_seed, family, dimensions)
                routes[mask_key] = route_counts(test_matrix, masks[mask_key], dimensions)
                del test_matrix
            require(np.array_equal(observed, masks[mask_key]), "Saved test visibility differs from bound replay/cache")
            if "observed_route_counts" in row or "primary_comparison" in protocol:
                require(row.get("observed_route_counts") == routes[mask_key], "Test observed-route counts mismatch")
            for mode, threshold in (("fixed_0_5", .5), ("calibrated", thresholds[arm])):
                compare_metrics(row[mode], metrics(y, score, observed, threshold), target + "/" + name + "/" + arm)
            require(set(row["by_run"]) == set(test_runs), "Per-execution result roster mismatch")
            for run_id in sorted(set(test_runs)):
                selected = test_runs == run_id
                for mode, threshold in (("fixed_0_5", .5), ("calibrated", thresholds[arm])):
                    compare_metrics(row["by_run"][run_id][mode], metrics(y[selected], score[selected], observed[selected], threshold), "Execution " + run_id)
            arrays[key] = (score, observed)
            audited["verified_results"] += 1
            rows_checked += 1
        require(seen == grid, "Incomplete frozen result grid")
        if "primary_comparison" in protocol:
            audited["primary_screen"] = audit_primary_screen(record, protocol)
        for condition in conditions.values():
            if condition["kind"] == "delay" and condition.get("deadline", 0) >= condition["delay_seconds"]:
                for arm in protocol["models"]:
                    require(all(np.array_equal(a, b) for a, b in zip(arrays[(clean["name"], protocol["seeds"][0], arm)],
                            arrays[(condition["name"], protocol["seeds"][0], arm)])), "Full-delay control differs from clean")
                    audited["delay_controls"].append({"condition": condition["name"], "arm": arm, "exactly_clean": True})
        print(json.dumps({"audited_target": target, "verified_rows": audited["verified_results"]}), flush=True)
    for path, expected in bound_local.items():
        require(sha(path) == expected, "Bound code/model changed during audit")
    return {"status": "PASS", "created_utc": datetime.now(timezone.utc).isoformat(), "auditor_sha256": sha(__file__),
            "audit_kind": "INDEPENDENT_AI_CODE_AND_SAVED_OUTPUT_AUDIT_NOT_HUMAN_REVIEW", "dataset": result["dataset"],
            "source_events": source_count, "eligible_targets": len(eligible), "test_targets": len(test_idx),
            "test_run_counts": dict(Counter(str(x) for x in test_runs)), "verified_result_rows": rows_checked,
            "verified_calibration_thresholds": sum(len(t["calibration"]) for t in audits), "targets": audits, "hashes": hashes,
            "execution_scope": {"model_fit": False, "test_model_inference": False, "saved_model_calibration_inference": calibration_inference, "new_threshold_tuning": False},
            "limitations": ["Computational audit only; author labels are not independently human-adjudicated.",
                "Feature replay/cache semantics are reused; artifact hashes and coverage are verified, not a second complete feature implementation.",
                "Previously inspected AIT/Casino runs are development data, not external confirmation.",
                "Other-label flags are not independently established benign alarms or host-hour rates.",
                "Calibration budgets and descriptive gates do not imply population guarantees.",
                "Synthetic delay recovery is expected buffering behavior, not a learned-method success.",
                "Receipt hashes bind source bytes; they do not independently attest execution time."]}


def audit(run, events, manifest, output, feature_cache=None, protocol=None, calibration_inference=True):
    run, events, manifest, output = map(Path, (run, events, manifest, output))
    output.mkdir(parents=True, exist_ok=False)
    try:
        result = _audit(run, events, manifest, feature_cache, protocol, calibration_inference)
    except (AuditFailure, ValueError, KeyError, OSError) as error:
        result = {"status": "FAIL", "audit_kind": "AI_CODE_AUDIT", "issue": str(error)}
        (output / "AUDIT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (output / "AUDIT.md").write_text("# V2 calculation audit\n\n**FAIL:** " + str(error) + "\n", encoding="utf-8")
        raise
    (output / "AUDIT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Independent v2 calculation audit", "", "**PASS** for saved computations, source bindings, and calibration thresholds. This is an AI/code audit, not human label review or external confirmation.", "",
             f"Dataset: **{result['dataset']}**. Verified {result['verified_result_rows']} condition/model results, pooled and per execution, at both operating points; {result['verified_calibration_thresholds']} calibration thresholds.", "",
             "- Checked source/code/model/cache hashes and saved target identity/order.",
             "- Independently recomputed confusion counts, precision, recall, F1, ROC-AUC, AP, and observation coverage.",
             "- Independently derived strict sorted-negative calibration thresholds from saved clean calibration scores.",
             "- Saved-model calibration-only inference: " + str(calibration_inference) + ". No fitting, tuning, or test-model inference.", "", "## Limits", ""]
    lines.extend("- " + value for value in result["limitations"])
    (output / "AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "events", "manifest", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--feature-cache", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--skip-calibration-inference", action="store_true")
    args = parser.parse_args()
    result = audit(args.run, args.events, args.manifest, args.output, args.feature_cache, args.protocol, not args.skip_calibration_inference)
    print(json.dumps({"status": result["status"], "verified_results": result["verified_result_rows"]}), flush=True)


if __name__ == "__main__":
    main()
