"""Aggregate v2 comparisons and exact v1 baseline-replication diagnostics.

No fitting or inference. Paired run votes average matched corruption seeds
first, so each positive-bearing run supplies one descriptive vote per metric.
Private predictions are read only for replication checks and are not copied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import fmean
from zipfile import BadZipFile

import numpy as np

from ..robustness import compare_results as frozen_summary

METRICS = frozen_summary.METRICS
POINTS = frozen_summary.MODES
BASELINE = "random_dropout"
REPLICATION_ARMS = {"semantic_event": "semantic_event", "entity_context": "entity_context",
                    "random_dropout": "context_dropout"}
LOWER_IS_BETTER = {"negative_label_flag_rate"}
TIE_TOLERANCE = 1e-12


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _mean(values):
    return fmean(values) if values and all(value is not None for value in values) else None


def _load_run(path, allow_legacy_receipt=False):
    path = Path(path)
    result_path, receipt_path = path / "RESULTS.json", path / "PRE_FIT_RECEIPT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if result.get("status") != "COMPLETE":
        raise ValueError("Only completed runs can be compared")
    for field in ("input_sha256", "manifest_sha256", "protocol_sha256"):
        if field == "manifest_sha256" and field not in receipt and allow_legacy_receipt:
            if not isinstance(result.get(field), str):
                raise ValueError("Legacy result lacks source manifest hash")
            continue
        if result.get(field) != receipt.get(field) or not isinstance(result.get(field), str):
            raise ValueError("Frozen receipt disagrees with result provenance")
    protocol = receipt["protocol"]
    if not isinstance(protocol.get("models"), list) or len(set(protocol["models"])) != len(protocol["models"]):
        raise ValueError("Invalid frozen model roster")
    if set(result["targets"]) != set(protocol["datasets"][result["dataset"]]["targets"]):
        raise ValueError("Results differ from frozen target roster")
    return result, protocol, {"results_sha256": _sha(result_path), "prefit_receipt_sha256": _sha(receipt_path),
                              "input_sha256": result["input_sha256"], "manifest_sha256": result["manifest_sha256"],
                              "protocol_sha256": result["protocol_sha256"],
                              "source_manifest_in_prefit_receipt": "manifest_sha256" in receipt}


def _index_target(record, protocol):
    for support in record["support"].values():
        frozen_summary._support(support)
    if record["status"] != "COMPLETE":
        if record.get("results"):
            raise ValueError("Unsupported/incomplete target contains scored rows")
        return {}, {}
    arms = protocol["models"]
    if set(record["models"]) != set(arms):
        raise ValueError("Completed target lacks the frozen model roster")
    conditions = {c["name"]: c for c in protocol["conditions"]}
    if len(conditions) != len(protocol["conditions"]):
        raise ValueError("Duplicate frozen condition names")
    expected = {(arm, name, seed) for arm in arms for name, condition in conditions.items()
                for seed in (protocol["seeds"] if condition["kind"] == "random" else protocol["seeds"][:1])}
    indexed, run_support = {}, None
    for row in record["results"]:
        key = (row["arm"], row["condition"], row["seed"])
        if key in indexed or key not in expected:
            raise ValueError("Duplicate or unexpected model/condition/seed row")
        if row["deadline_seconds"] != conditions[row["condition"]].get("deadline", 0):
            raise ValueError("Results change the common decision deadline")
        for point in POINTS:
            frozen_summary._validate_metrics(row[point])
            if frozen_summary._support(row[point]) != record["support"]["test"]:
                raise ValueError("Result changes the eligible test denominator")
        current = {}
        for run, metrics in row["by_run"].items():
            for point in POINTS:
                frozen_summary._validate_metrics(metrics[point])
            counts = frozen_summary._support(metrics[POINTS[0]])
            if counts != frozen_summary._support(metrics[POINTS[1]]):
                raise ValueError("Operating point changes run support")
            current[run] = counts
        if not current or {key: sum(row[key] for row in current.values()) for key in ("n", "positive", "negative")} != record["support"]["test"]:
            raise ValueError("Per-run denominators do not sum to target support")
        if run_support is not None and current != run_support:
            raise ValueError("Conditions or methods change the per-run roster")
        run_support = current
        indexed[key] = row
    if set(indexed) != expected:
        raise ValueError("Completed target has missing frozen comparisons")
    return indexed, run_support


def _paired_runs(rows, baseline_rows, run_support, point, metric):
    differences = []
    eligible = [run for run, support in run_support.items() if support["positive"] > 0]
    for run in eligible:
        per_seed = []
        for left, right in zip(rows, baseline_rows):
            a = frozen_summary._value(left["by_run"][run][point], metric)
            b = frozen_summary._value(right["by_run"][run][point], metric)
            per_seed.append(None if a is None or b is None else a - b)
        differences.append(_mean(per_seed))
    defined = [value for value in differences if value is not None]
    directed = [-value if metric in LOWER_IS_BETTER else value for value in defined]
    return {"wins": sum(value > TIE_TOLERANCE for value in directed),
            "ties": sum(abs(value) <= TIE_TOLERANCE for value in directed),
            "losses": sum(value < -TIE_TOLERANCE for value in directed),
            "undefined": len(differences) - len(defined),
            "mean_delta": _mean(differences)}


def _target_summary(target, record, protocol):
    indexed, run_support = _index_target(record, protocol)
    result = {"status": record["status"], "support": record["support"],
              "primary_screen": record.get("primary_screen"), "conditions": {}}
    if not indexed:
        result["interpretation"] = "Unsupported target; no detection capability or zero-score failure inferred."
        return result
    if BASELINE not in protocol["models"]:
        raise ValueError("Frozen v2 protocol lacks random_dropout baseline")
    result["positive_bearing_test_runs"] = sum(row["positive"] > 0 for row in run_support.values())
    result["excluded_zero_positive_test_runs"] = sum(row["positive"] == 0 for row in run_support.values())
    result["calibration_thresholds"] = {arm: record["models"][arm]["threshold"] for arm in protocol["models"]}
    for condition in protocol["conditions"]:
        name = condition["name"]
        seeds = protocol["seeds"] if condition["kind"] == "random" else protocol["seeds"][:1]
        baseline_rows = [indexed[(BASELINE, name, seed)] for seed in seeds]
        summary = {"seeds": seeds, "deadline_seconds": condition.get("deadline", 0), "arms": {}}
        for arm in protocol["models"]:
            rows = [indexed[(arm, name, seed)] for seed in seeds]
            summary["arms"][arm] = {}
            for point in POINTS:
                means, deltas, paired = {}, {}, {}
                for metric in METRICS:
                    means[metric] = _mean([frozen_summary._value(row[point], metric) for row in rows])
                    per_seed = []
                    for left, right in zip(rows, baseline_rows):
                        a, b = frozen_summary._value(left[point], metric), frozen_summary._value(right[point], metric)
                        per_seed.append(None if a is None or b is None else a - b)
                    deltas[metric] = _mean(per_seed)
                    paired[metric] = _paired_runs(rows, baseline_rows, run_support, point, metric)
                summary["arms"][arm][point] = {"mean": means, "delta_vs_random_dropout": deltas,
                                               "paired_positive_runs": paired}
        result["conditions"][name] = summary
    return result


def _npz_equal(left_path, right_path, keys):
    """Return aggregate diagnostics only; never return private row values."""
    left_path, right_path = Path(left_path), Path(right_path)
    try:
        with np.load(left_path, allow_pickle=False) as left, np.load(right_path, allow_pickle=False) as right:
            if set(left.files) != set(keys) or set(right.files) != set(keys):
                return {"equal": False, "reason": "NPZ_KEY_SET_DIFFERS"}
            matches = {key: left[key].dtype == right[key].dtype and np.array_equal(left[key], right[key]) for key in keys}
            return {"equal": all(matches.values()), "fields_equal": matches,
                    "left_sha256": _sha(left_path), "right_sha256": _sha(right_path)}
    except (OSError, ValueError, EOFError, KeyError, BadZipFile):
        return {"equal": False, "reason": "MISSING_OR_INVALID_PRIVATE_NPZ"}


def _replication(v2_path, v2, v2_protocol, v1_path):
    if v1_path is None:
        return {"status": "NOT_REQUESTED", "interpretation": "No v1 run supplied; baseline replication not assessed."}
    prediction_hashes = []
    report = {"status": "FAIL", "checks": 0, "passed": 0, "failures": [],
              "targets": {}, "arm_mapping": REPLICATION_ARMS, "no_model_refitting_or_inference": True}

    def check(name, passed, details=None):
        report["checks"] += 1
        report["passed"] += int(bool(passed))
        if not passed:
            report["failures"].append({"check": name, **(details or {})})

    try:
        v1, old_protocol, provenance = _load_run(v1_path, allow_legacy_receipt=True)
    except (OSError, ValueError, KeyError):
        check("completed_v1_input", False, {"reason": "MISSING_INVALID_OR_INCOMPLETE_V1_RUN"})
        return report
    report["v1_provenance"] = provenance
    same_source = all(v2.get(key) == v1.get(key) for key in ("dataset", "input_sha256", "manifest_sha256"))
    check("same_dataset_and_frozen_source", same_source)
    if not same_source:
        return report
    roster = _npz_equal(Path(v2_path) / "PRIVATE_TARGET_ROSTER.npz", Path(v1_path) / "PRIVATE_TARGET_ROSTER.npz", ("event_ids", "run_ids"))
    check("exact_test_roster", roster["equal"], roster)
    report["target_roster"] = roster
    old_conditions = {condition["name"]: condition for condition in old_protocol["conditions"]}
    common = [condition["name"] for condition in v2_protocol["conditions"] if condition["name"] in old_conditions]
    check("nonempty_common_condition_grid", bool(common))
    report["common_conditions"] = common
    for condition in v2_protocol["conditions"]:
        if condition["name"] in old_conditions:
            check("identical_condition:" + condition["name"], _canonical(condition) == _canonical(old_conditions[condition["name"]]))
    for target, record in v2["targets"].items():
        old = v1["targets"].get(target)
        if old is None:
            check("target_present:" + target, False)
            continue
        if record["status"] != "COMPLETE" or old["status"] != "COMPLETE":
            report["targets"][target] = {"status": "UNSUPPORTED", "v2_status": record["status"], "v1_status": old["status"]}
            check("same_target_qualification:" + target, record["status"] == old["status"])
            continue
        try:
            new_index, _ = _index_target(record, v2_protocol)
            old_index, _ = _index_target(old, old_protocol)
        except ValueError:
            check("complete_target_grid:" + target, False)
            continue
        local = {"status": "PASS", "prediction_files_checked": 0, "prediction_files_equal": 0,
                 "thresholds_checked": 0, "thresholds_equal": 0, "aggregate_rows_equal": 0}
        failures_before = len(report["failures"])
        for arm, old_arm in REPLICATION_ARMS.items():
            threshold_equal = (arm in record["models"] and old_arm in old["models"]
                               and _canonical(record["models"][arm]["threshold"]) == _canonical(old["models"][old_arm]["threshold"]))
            local["thresholds_checked"] += 1
            local["thresholds_equal"] += int(threshold_equal)
            check(f"threshold:{target}:{arm}", threshold_equal)
            matching = [key for key in new_index if key[0] == arm and key[1] in common]
            for _, condition, seed in matching:
                key = (old_arm, condition, seed)
                if key not in old_index:
                    check(f"matching_v1_seed:{target}:{arm}:{condition}:{seed}", False)
                    continue
                comparison = _npz_equal(Path(v2_path) / f"PRIVATE_{target}_{arm}_{condition}_{seed}.npz",
                                        Path(v1_path) / f"PRIVATE_{target}_{old_arm}_{condition}_{seed}.npz", ("y", "score", "observed"))
                prediction_hashes.append({"target": target, "arm": arm, "condition": condition, "seed": seed,
                                          "v2_sha256": comparison.get("left_sha256"),
                                          "v1_sha256": comparison.get("right_sha256")})
                local["prediction_files_checked"] += 1
                local["prediction_files_equal"] += int(comparison["equal"])
                check(f"exact_predictions:{target}:{arm}:{condition}:{seed}", comparison["equal"], comparison)
                left, right = new_index[(arm, condition, seed)], old_index[key]
                metrics_equal = all(_canonical(left[point]) == _canonical(right[point]) for point in (*POINTS, "by_run"))
                local["aggregate_rows_equal"] += int(metrics_equal)
                check(f"exact_aggregate_metrics:{target}:{arm}:{condition}:{seed}", metrics_equal)
        local["status"] = "PASS" if len(report["failures"]) == failures_before else "FAIL"
        report["targets"][target] = local
    report["status"] = "PASS" if not report["failures"] else "FAIL"
    report["prediction_hash_inventory_sha256"] = hashlib.sha256(_canonical(prediction_hashes).encode("utf-8")).hexdigest()
    report["prediction_hash_inventory_entries"] = len(prediction_hashes)
    report["interpretation"] = "Numerically exact array values and dtypes, threshold objects, and supplied aggregate metrics on common conditions. This is replication evidence, not an independent label or full prediction audit."
    return report


def _format(value, signed=False):
    return "undefined" if value is None else (f"{value:+.4f}" if signed else f"{value:.4f}")


def _markdown(report):
    lines = [f"# {report['dataset']}: structured-loss comparisons", "",
             "All changes compare against random-record-dropout training. Both operating points remain separate; each arm retains its frozen clean-calibration threshold.", "",
             f"Baseline replication: **{report['baseline_replication']['status']}**.", "",
             "Each positive-bearing test run supplies one win/tie/loss vote after averaging matched corruption seeds. Runs with no positive examples are excluded from these votes; their negatives remain in pooled metrics. These votes are descriptive, not independent significance tests.", ""]
    for target, result in report["targets"].items():
        lines += [f"## {target}", "", f"Status: **{result['status']}**.", ""]
        if result["status"] != "COMPLETE":
            lines += [result["interpretation"], ""]
            continue
        lines += [f"Positive-bearing runs: {result['positive_bearing_test_runs']}; excluded zero-positive runs: {result['excluded_zero_positive_test_runs']}.", ""]
        for point in POINTS:
            lines += [f"### {'Fixed score > 0.5' if point == 'fixed_0_5' else 'Frozen calibration threshold'}", "",
                      "| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |",
                      "|---|---|---:|---:|---:|---:|---:|"]
            for condition, details in result["conditions"].items():
                for arm, arms in details["arms"].items():
                    values = arms[point]
                    paired, changes = values["paired_positive_runs"]["f1"], values["delta_vs_random_dropout"]
                    vote = f"{paired['wins']}/{paired['ties']}/{paired['losses']}"
                    if paired["undefined"]:
                        vote += f" ({paired['undefined']} undefined)"
                    lines.append("| " + " | ".join([condition, arm, _format(values["mean"]["f1"]),
                        _format(changes["f1"], True), _format(changes["recall"], True),
                        _format(changes["negative_label_flag_rate"], True), vote]) + " |")
            lines.append("")
    replication = report["baseline_replication"]
    if replication.get("failures"):
        lines += ["## Baseline replication discrepancies", "",
                  "Differences are retained as diagnostic failures; the v2 experimental results remain available.", ""]
        lines.extend("- " + failure["check"] + (": " + failure["reason"] if "reason" in failure else "") for failure in replication["failures"])
        lines.append("")
    lines += ["## Limits", "",
              "- Pooled means average the fixed corruption seeds; masks are not independent attacks or independently fitted models.",
              "- Undefined class-dependent metrics stay null; averages require all seed values to be defined.",
              "- Other-label flag rates do not measure independently verified benign false alarms.",
              "- Higher F1 may reflect fewer false flags or different recall. Primary gates and both operating points must remain visible.",
              "- This report performs no fitting or inference and publishes no prediction arrays. It does not establish novelty or deployment guarantees.", ""]
    return "\n".join(lines)


def compare(v2_run, output, v1_run=None):
    output, v2_run = Path(output), Path(v2_run)
    if output.exists():
        raise FileExistsError("Refusing to overwrite comparison evidence")
    result, protocol, provenance = _load_run(v2_run)
    report = {"status": "COMPLETE_DESCRIPTIVE_COMPARISON", "schema_version": "robustness-v2-comparison-v1",
              "created_utc": datetime.now(timezone.utc).isoformat(), "dataset": result["dataset"],
              "generator_sha256": _sha(Path(__file__)), "summary_helper_sha256": _sha(Path(frozen_summary.__file__)),
              "v2_provenance": provenance, "baseline_arm": BASELINE,
              "aggregation": "Equal-weight matched-seed means within each target/condition; no dataset or target pooling",
              "paired_run_policy": "Average paired seed deltas within each positive-bearing run, then count one vote per run separately per operating point; zero-positive runs excluded",
              "metric_direction": {metric: "lower" if metric in LOWER_IS_BETTER else "higher" for metric in METRICS},
              "tie_tolerance": TIE_TOLERANCE, "population_confidence_intervals": False,
              "targets": {target: _target_summary(target, record, protocol) for target, record in result["targets"].items()},
              "baseline_replication": _replication(v2_run, result, protocol, Path(v1_run) if v1_run else None)}
    # Bind both source result/receipt bytes throughout comparison generation.
    if _sha(v2_run / "RESULTS.json") != provenance["results_sha256"] or _sha(v2_run / "PRE_FIT_RECEIPT.json") != provenance["prefit_receipt_sha256"]:
        raise ValueError("Source results or frozen receipt changed during comparison")
    old_provenance = report["baseline_replication"].get("v1_provenance")
    if old_provenance and (_sha(Path(v1_run) / "RESULTS.json") != old_provenance["results_sha256"]
            or _sha(Path(v1_run) / "PRE_FIT_RECEIPT.json") != old_provenance["prefit_receipt_sha256"]):
        raise ValueError("V1 result or frozen receipt changed during comparison")
    output.mkdir(parents=True, exist_ok=False)
    (output / "COMPARISONS.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "COMPARISONS.md").write_text(_markdown(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2-run", required=True, type=Path)
    parser.add_argument("--v1-run", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(args.v2_run, args.output, args.v1_run)
    print(json.dumps({"status": result["status"], "dataset": result["dataset"],
                      "baseline_replication": result["baseline_replication"]["status"]}), flush=True)


if __name__ == "__main__":
    main()
