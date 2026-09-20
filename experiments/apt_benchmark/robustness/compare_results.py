"""Summarize frozen robustness outputs without fitting or model inference.

Each dataset/target/condition stays separate. Repeated corruption masks describe
perturbation variability; they are not independent campaigns or confidence
intervals. This is an aggregate report, not an independent prediction audit.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean


ARMS = ("generic_event", "semantic_event", "entity_context", "context_dropout")
MODES = ("fixed_0_5", "calibrated")
METRICS = ("f1", "precision", "recall", "negative_label_flag_rate", "observation_coverage",
           "roc_auc", "average_precision")
PAIRS = (("entity_context", "semantic_event"), ("context_dropout", "entity_context"))
OVERVIEW = ("clean", "random_50", "support_burst_60", "command_records_absent")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _support(row: dict) -> dict:
    names = ("n", "positive", "negative")
    if any(type(row.get(name)) is not int or row[name] < 0 for name in names):
        raise ValueError("Nonnegative integer support counts required")
    if row["positive"] + row["negative"] != row["n"]:
        raise ValueError("Positive and negative support must sum to n")
    return {name: row[name] for name in names}


def _validate_metrics(row: dict) -> None:
    support = _support(row)
    for name in ("tp", "fp", "tn", "fn", "observed_targets", "unobserved_positive_targets"):
        if type(row.get(name)) is not int or row[name] < 0:
            raise ValueError("Nonnegative integer confusion/observation counts required")
    if (row["tp"] + row["fn"] != support["positive"]
            or row["fp"] + row["tn"] != support["negative"]
            or row["observed_targets"] > support["n"]
            or row["unobserved_positive_targets"] > support["positive"]):
        raise ValueError("Confusion or observation counts disagree with support")
    for name in METRICS:
        value = row.get(name)
        if value is not None and (type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError("Metrics must be finite rates or explicit null")


def _value(row: dict, metric: str):
    # Upstream may use numerical F1=0 for an absent positive class. Do not
    # interpret that convention as measured positive-class capability.
    if metric in {"f1", "precision", "recall", "average_precision"} and not row["positive"]:
        return None
    if metric in {"negative_label_flag_rate", "roc_auc"} and not row["negative"]:
        return None
    if metric == "roc_auc" and not row["positive"]:
        return None
    return row[metric]


def _summary(values: list) -> dict:
    defined = [float(value) for value in values if value is not None]
    complete = len(defined) == len(values) and bool(values)
    return {"mean": fmean(defined) if complete else None,
            "min": min(defined) if complete else None,
            "max": max(defined) if complete else None,
            "defined_repeats": len(defined), "total_repeats": len(values),
            "undefined_reason": None if complete else "UNSUPPORTED_CLASS_OR_UNDEFINED_INPUT_METRIC",
            "uncertainty": "Descriptive corruption-seed range; not a confidence interval"}


def _mean_metrics(rows: list[dict]) -> dict:
    return {metric: _summary([_value(row, metric) for row in rows]) for metric in METRICS}


def _paired(left: list[dict], right: list[dict], seeds: list[int]) -> dict:
    if len(left) != len(right) or len(left) != len(seeds):
        raise ValueError("A paired comparison needs the same seed roster")
    result = {}
    for metric in METRICS:
        differences = []
        for a, b in zip(left, right):
            if _support(a) != _support(b):
                raise ValueError("Paired methods have different evaluation denominators")
            av, bv = _value(a, metric), _value(b, metric)
            differences.append(None if av is None or bv is None else av - bv)
        result[metric] = {**_summary(differences),
                          "per_seed": [{"seed": seed, "difference": difference}
                                       for seed, difference in zip(seeds, differences)]}
    return result


def _dataset_scope(dataset: str, frozen_protocol: dict | None) -> dict:
    details = (frozen_protocol or {}).get("datasets", {}).get(dataset, {})
    if dataset == "ait":
        label_status = "Author rule annotations on audit fragments, unioned into events. Previously exposed development runs; other-label negatives are not independently adjudicated benign activity."
        unit = "Audit event grouped by run/host/epoch/serial"
        limitations = ["Audit-only positives in this pilot concern escalation, not complete kill-chain coverage.",
                       "Most AIT events are singletons; random fragment loss commonly removes entire target events."]
    elif dataset == "casino":
        label_status = "Source process-technique annotations. Targets are annotation-onset proxies and negatives are other annotated techniques; not benign detection or independently verified action onset."
        unit = "First observed audit event per annotated process-technique and host; overlapping labels unioned"
        limitations = ["Inherited process labels need not establish a malicious action in each event.",
                       "Repeated actors/recipes and correlated events limit independent transfer claims."]
    else:
        label_status = "Source-defined labels; no independent analyst adjudication or benignness is inferred by this helper."
        unit = "See frozen input protocol"
        limitations = ["Dataset semantics require source-specific interpretation."]
    return {"dataset": dataset, "frozen_dataset_definition": details,
            "prediction_unit": details.get("prediction_unit", unit),
            "label_status": label_status, "limitations": limitations}


def _compare_target(target: str, record: dict, protocol: dict | None) -> dict:
    support = record["support"]
    for counts in support.values():
        _support(counts)
    output = {"target": target, "status": record["status"], "split_support": support,
              "test_run_support": {}, "conditions": [], "calibration": {}}
    if record["status"] != "COMPLETE":
        if record.get("results"):
            raise ValueError("Incomplete target has scored results; refusing partial summary")
        output["interpretation"] = "Target unsupported/incomplete; no model capability or zero-score failure is inferred."
        return output
    if set(record["models"]) != set(ARMS):
        raise ValueError("Completed target must contain all four fixed arms")
    output["calibration"] = {arm: record["models"][arm]["threshold"] for arm in ARMS}
    grouped = defaultdict(dict)
    run_support = None
    for row in record["results"]:
        condition, arm, seed = row["condition"], row["arm"], row["seed"]
        if arm not in ARMS or type(seed) is not int:
            raise ValueError("Unknown model arm or invalid seed")
        if (arm, seed) in grouped[condition]:
            raise ValueError("Duplicate arm/condition/seed result")
        for mode in MODES:
            _validate_metrics(row[mode])
            if _support(row[mode]) != support["test"]:
                raise ValueError("Condition changes the fixed target roster")
        current_support = {}
        for run_id, run_row in row["by_run"].items():
            for mode in MODES:
                _validate_metrics(run_row[mode])
            counts = _support(run_row["fixed_0_5"])
            if counts != _support(run_row["calibrated"]):
                raise ValueError("Operating points change per-run support")
            current_support[run_id] = counts
        if not current_support or {key: sum(value[key] for value in current_support.values())
                                   for key in ("n", "positive", "negative")} != support["test"]:
            raise ValueError("Per-run supports do not sum to pooled target support")
        if run_support is not None and current_support != run_support:
            raise ValueError("Conditions/arms change run support")
        run_support = current_support
        grouped[condition][(arm, seed)] = row
    if not grouped:
        raise ValueError("Completed target has no results")
    expected_conditions = {c["name"]: c for c in protocol["conditions"]} if protocol else None
    if expected_conditions is not None and set(grouped) != set(expected_conditions):
        raise ValueError("Results do not cover the frozen condition roster")
    output["test_run_support"] = run_support
    for condition, rows in grouped.items():
        seeds = sorted({seed for _, seed in rows})
        if set(rows) != {(arm, seed) for arm in ARMS for seed in seeds}:
            raise ValueError("Methods lack identical paired seed coverage")
        if expected_conditions is not None:
            definition = expected_conditions[condition]
            expected_seeds = protocol["seeds"] if definition["kind"] == "random" else protocol["seeds"][:1]
            if seeds != sorted(expected_seeds):
                raise ValueError("Results differ from frozen corruption seeds")
        deadlines = {row["deadline_seconds"] for row in rows.values()}
        if len(deadlines) != 1:
            raise ValueError("Condition does not use a shared deadline")
        entry = {"condition": condition, "deadline_seconds": next(iter(deadlines)),
                 "seeds": seeds, "perturbation_repeats": len(seeds), "arms": {}, "paired_changes": {}}
        for arm in ARMS:
            arm_rows = [rows[(arm, seed)] for seed in seeds]
            entry["arms"][arm] = {mode: _mean_metrics([row[mode] for row in arm_rows]) for mode in MODES}
            entry["arms"][arm]["per_run"] = {
                run_id: {mode: _mean_metrics([row["by_run"][run_id][mode] for row in arm_rows]) for mode in MODES}
                for run_id in sorted(run_support)}
            entry["arms"][arm]["zero_predicted_positive_repeats"] = {
                mode: sum(row[mode]["tp"] + row[mode]["fp"] == 0 for row in arm_rows) for mode in MODES}
        for left, right in PAIRS:
            name = left + "_minus_" + right
            paired = {mode: _paired([rows[(left, seed)][mode] for seed in seeds],
                                   [rows[(right, seed)][mode] for seed in seeds], seeds) for mode in MODES}
            paired["per_run"] = {
                run_id: {mode: _paired([rows[(left, seed)]["by_run"][run_id][mode] for seed in seeds],
                                      [rows[(right, seed)]["by_run"][run_id][mode] for seed in seeds], seeds)
                         for mode in MODES} for run_id in sorted(run_support)}
            entry["paired_changes"][name] = paired
        output["conditions"].append(entry)
    return output


def _format(value, signed=False) -> str:
    return "undefined" if value is None else (f"{value:+.4f}" if signed else f"{value:.4f}")


def _markdown(result: dict) -> str:
    lines = ["# Missing/delayed-log development comparisons", "",
        "Datasets and target labels remain separate. Values are means across the fixed corruption seeds within each condition; ranges in JSON describe mask variability, not independent replication or confidence intervals.", "",
        "Both decision rules are shown: fixed score > 0.5, and each model's separately frozen clean-calibration threshold. Completely unobserved targets remain in the denominator and receive no alarm.", ""]
    for dataset in result["datasets"]:
        lines += [f"## {dataset['dataset']}", "", dataset["scope"]["label_status"], ""]
        for target in dataset["targets"]:
            counts = target["split_support"]["test"]
            lines += [f"### {target['target']}", "", f"Status: **{target['status']}**. Test support: {counts['n']:,} events, {counts['positive']:,} positives, {counts['negative']:,} other-label negatives.", ""]
            if target["status"] != "COMPLETE":
                lines += [target["interpretation"], ""]
                continue
            lines += ["Per-run support: " + "; ".join(f"{run}: {c['positive']} positive / {c['negative']} negative" for run, c in sorted(target["test_run_support"].items())) + ".", "",
                "Preselected overview below; **all conditions, precision, recall, negative-label flag rates, coverage and paired per-run differences** appear in COMPARISONS.json.", "",
                "| Condition | Decision | Generic F1 | Semantic F1 | Context F1 | Dropout F1 | Context − semantic | Dropout − context | Coverage |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
            lookup = {entry["condition"]: entry for entry in target["conditions"]}
            for condition in OVERVIEW:
                if condition not in lookup:
                    continue
                entry = lookup[condition]
                for mode in MODES:
                    scores = [_format(entry["arms"][arm][mode]["f1"]["mean"]) for arm in ARMS]
                    deltas = [_format(entry["paired_changes"][left + "_minus_" + right][mode]["f1"]["mean"], True) for left, right in PAIRS]
                    coverages = [entry["arms"][arm][mode]["observation_coverage"]["mean"] for arm in ARMS]
                    coverage = _format(coverages[0]) if len(set(coverages)) == 1 else "see JSON"
                    label = "0.5" if mode == "fixed_0_5" else "calibrated"
                    lines.append("| " + " | ".join([condition, label] + scores + deltas + [coverage]) + " |")
            lines += ["", "A positive F1 difference is descriptive, not an automatic win: check its recall/flag-rate tradeoff and each run. F1/recall comparisons for a run with no positive target labels are undefined, not evidence of successful detection.", ""]
    lines += ["## Interpretation limits", "",
        "- The calibration budget is an empirical calibration-set operating point; it does not guarantee a population or deployment false-alarm rate. Other-label negatives have different meanings across datasets.",
        "- Small positive counts, correlated events and shared recipes limit conclusions. Three removal seeds are not three independently trained models or attack campaigns.",
        "- Random record loss often hides whole AIT singleton events. The evaluator's known target roster is not a deployed mechanism for detecting invisible events.",
        "- A recent-support burst is a target-relative stress test; record-type removal is not a whole-sensor outage. Native arrival times are not measured.",
        "- Recovery once waiting reaches the injected deterministic delay is guaranteed by construction. It is a buffering control with a latency cost, not a learned robustness success.",
        "- No dataset/label pooling, winner selection, significance claim, larger-model recommendation or novelty claim is produced here.",
        "- This helper summarizes supplied frozen aggregate results; it does not independently audit predictions or rerun models.", ""]
    return "\n".join(lines)


def build_comparisons(result_paths: list[Path], output_dir: Path) -> dict:
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite a comparison report")
    if not result_paths:
        raise ValueError("At least one completed result is required")
    datasets, seen = [], set()
    for result_path in map(Path, result_paths):
        source = json.loads(result_path.read_text(encoding="utf-8"))
        if source.get("status") != "COMPLETE":
            raise ValueError("Only completed result artifacts can be summarized")
        dataset = source["dataset"]
        if dataset in seen:
            raise ValueError("Duplicate dataset input would silently pool separate runs")
        seen.add(dataset)
        receipt_path = result_path.with_name("PRE_FIT_RECEIPT.json")
        protocol = None
        provenance = {"result_sha256": _sha(result_path),
                      "input_events_sha256": source["input_sha256"],
                      "manifest_sha256": source["manifest_sha256"],
                      "protocol_sha256": source["protocol_sha256"],
                      "frozen_condition_grid_checked": False}
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt["input_sha256"] != source["input_sha256"] or receipt["protocol_sha256"] != source["protocol_sha256"]:
                raise ValueError("Adjacent frozen receipt disagrees with result")
            protocol = receipt["protocol"]
            provenance.update(prefit_receipt_sha256=_sha(receipt_path), frozen_condition_grid_checked=True)
        datasets.append({"dataset": dataset, "provenance": provenance,
                         "scope": _dataset_scope(dataset, protocol),
                         "targets": [_compare_target(target, record, protocol) for target, record in source["targets"].items()]})
    result = {"status": "COMPLETE_DESCRIPTIVE_COMPARISON", "schema_version": "robustness-comparison-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(), "generator_sha256": _sha(Path(__file__)),
        "aggregation": "Arithmetic means across identical fixed corruption seeds within each dataset/target/condition; paired differences use matching seeds and denominators",
        "metric_direction": {"f1": "higher", "precision": "higher", "recall": "higher", "negative_label_flag_rate": "lower", "observation_coverage": "higher"},
        "undefined_policy": "No positive labels: F1/precision/recall/AP and their paired changes are null. No negatives: negative-label flag rate is null. Means require every repeat to be defined; no silent defined-only averaging.",
        "zero_prediction_precision": "With positive support but zero predicted positives, retain upstream precision=0 convention and count affected repeats.",
        "no_model_fitting_or_inference": True, "population_confidence_intervals": False,
        "no_cross_dataset_or_cross_target_pooling": True, "datasets": datasets}
    output_dir.mkdir(parents=True)
    (output_dir / "COMPARISONS.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output_dir / "COMPARISONS.md").write_text(_markdown(result), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build_comparisons(args.result, args.output)
    print(json.dumps({"status": result["status"], "datasets": [d["dataset"] for d in result["datasets"]]}))


if __name__ == "__main__":
    main()
