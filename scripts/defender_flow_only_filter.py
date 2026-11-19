"""Compare matched flow-only models before and after a UDP port filter."""

import argparse
import json
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded
import defender_sequence_tuning as sequence
import defender_flow_ablation as ablation
import defender_flow_filter as flow_filter
import defender_visibility_audit as audit


def aligned_rows(original, filtered):
    def index(rows):
        result = {(row["session"], row["window"]): row for row in rows}
        if len(result) != len(rows):
            raise ValueError("Duplicate window keys")
        return result

    before, after = index(original), index(filtered)
    if set(before) != set(after):
        raise ValueError("Original and filtered windows differ")
    for key, row in before.items():
        changed = after[key]
        if set(row) != set(changed):
            raise ValueError("Original and filtered columns differ")
        for column in set(row) - set(flow_filter.FLOW_COLUMNS):
            if row[column] != changed[column]:
                raise ValueError(f"Non-flow field changed: {column}")
        for column in flow_filter.FLOW_COLUMNS:
            if not 0 <= int(changed[column]) <= int(row[column]):
                raise ValueError(f"Invalid filtered flow count: {column}")
        for candidate in (row, changed):
            if sum(int(candidate[f"bin_flow_{i}"]) for i in range(6)) != int(candidate["flow_records"]):
                raise ValueError("Flow bins do not sum to flow records")
    return [after[(row["session"], row["window"])] for row in original]


def run(experiment, filtered_output, visibility_output, output):
    experiment, filtered_output, visibility_output = (
        experiment.resolve(), filtered_output.resolve(), visibility_output.resolve()
    )
    output = expanded.safe_output(output, experiment, filtered_output)
    output = expanded.safe_output(output, visibility_output, visibility_output)
    own_hash = base.sha256(Path(__file__).resolve())
    helpers = audit.source_hashes()
    filter_hash = base.sha256(Path(flow_filter.__file__).resolve())
    audit_hash = base.sha256(Path(audit.__file__).resolve())
    _, groups, labels, sessions, _, provenance = sequence.prepare(experiment)
    filtered_manifest_path = filtered_output / "extraction.json"
    filtered_manifest = json.loads(filtered_manifest_path.read_text(encoding="utf-8"))
    filtered_path = filtered_output / "filtered_windows30.csv"
    visibility_manifest_path = visibility_output / "extraction.json"
    visibility_manifest = json.loads(visibility_manifest_path.read_text(encoding="utf-8"))
    visibility_path = visibility_output / "results.json"
    visibility = json.loads(visibility_path.read_text(encoding="utf-8"))
    if (filtered_manifest["script_sha256"] != filter_hash
            or filtered_manifest["provenance"] != provenance
            or filtered_manifest["port_filter"] != [41641, 3478]
            or filtered_manifest["filtered_features_sha256"] != base.sha256(filtered_path)
            or visibility_manifest["script_sha256"] != audit_hash
            or visibility_manifest["helper_sha256"] != helpers
            or visibility_manifest["provenance"] != provenance
            or visibility["provenance"] != provenance):
        raise ValueError("A prior experiment, its features, or its code changed")
    original_rows = base.rows(experiment / "windows30.csv")
    filtered_rows = aligned_rows(original_rows, base.rows(filtered_path))
    original = expanded.aggregate(original_rows, 30)
    filtered = expanded.aggregate(filtered_rows, 30)
    keys = lambda rows: [(r["session"], r["window"], r["label"]) for r in rows]
    if keys(original) != keys(filtered):
        raise ValueError("Aggregated windows are not aligned")
    if (groups.tolist() != [row["session"] for row in original]
            or labels.tolist() != [int(row["label"] == "ai") for row in original]):
        raise ValueError("Baseline session predictions are misaligned")
    true_ai = tuple(s for s in sessions if labels[groups == s][0] == 1)
    score, predictions, _ = expanded.model_score(original, audit.FLOW_COLUMNS, true_ai, "xgboost", False)
    baseline = visibility["results"]["attack_flow_only"]
    if (predictions.tolist() != baseline["predictions"]
            or abs(score - baseline["macro_f1"]) > 1e-12):
        raise ValueError("Unfiltered flow-only baseline did not reproduce")
    result, filtered_labels, filtered_groups, filtered_sessions = audit.evaluate_one(filtered, audit.FLOW_COLUMNS)
    if (filtered_labels.tolist() != labels.tolist() or filtered_groups.tolist() != groups.tolist()
            or filtered_sessions != sessions):
        raise ValueError("Filtered predictions are misaligned")
    result["delta_from_flow_baseline"] = result["macro_f1"] - score
    result["paired_interval"] = ablation.paired_interval(
        labels, groups, sessions, predictions, np.array(result["predictions"])
    )
    if (base.sha256(Path(__file__).resolve()) != own_hash or audit.source_hashes() != helpers
            or base.sha256(Path(flow_filter.__file__).resolve()) != filter_hash
            or base.sha256(Path(audit.__file__).resolve()) != audit_hash):
        raise ValueError("Code changed during evaluation")
    output.mkdir(parents=True)
    document = {
        "exploratory": True, "script_sha256": own_hash, "provenance": provenance,
        "filter_manifest_sha256": base.sha256(filtered_manifest_path),
        "visibility_manifest_sha256": base.sha256(visibility_manifest_path),
        "visibility_results_sha256": base.sha256(visibility_path),
        "baseline": baseline, "filtered": result,
    }
    (output / "results.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    low, high = result["paired_interval"]
    lines = [
        "# Port-filtered flow-only sensitivity", "",
        "**Exploratory; no benign-traffic evaluation or independent validation.**",
        "Same 1,225 30-second attack windows and nine sessions. UDP records with either "
        "source or destination port 41641 or 3478 were excluded before rebuilding flow features.",
        "", "| Model | Macro-F1 | AI recall | Human attack FPR | Session accuracy | Raw p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, value in (("Unfiltered flow-only", baseline), ("Port-filtered flow-only", result)):
        lines.append(f"| {name} | {value['macro_f1']:.3f} | {value['ai_recall']:.3f} | "
                     f"{value['human_attack_window_fpr']:.3f} | {value['session_accuracy']:.3f} | "
                     f"{value['raw_p']:.4f} |")
    lines += [
        "", f"Change from flow-only baseline: {result['delta_from_flow_baseline']:+.3f} "
        f"(95% paired fixed-prediction session interval {low:+.3f} to {high:+.3f}).",
        "The filtered model refits all 126 session-label assignments. Its raw p-value tests "
        "label association, not the difference between models, and is not corrected for earlier exploration.",
        "The filter was chosen after inspecting the data, can remove unrelated traffic, and cannot "
        "identify a process or rule out other environment-related signals.",
    ]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Filtered flow-only F1 {result['macro_f1']:.3f}, raw p {result['raw_p']:.4f}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--filtered-output", type=Path, required=True)
    parser.add_argument("--visibility-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.experiment, args.filtered_output, args.visibility_output, args.output)
