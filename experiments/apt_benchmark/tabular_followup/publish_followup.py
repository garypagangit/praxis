"""Publish aggregate evidence only after every required followup audit passes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re

SEEDS = set(range(20260921, 20260931))
E1_MODELS = {"random_forest", "xgboost", "lightgbm", "tabicl_v2", "tabpfn_2_5_synthetic"}
TREE_MODELS = {"random_forest", "xgboost", "lightgbm"}
CONDITIONS = {"equal_32_per_class", "abundant_benign_1024"}
PUBLIC_FILES = {"REPORT.md", "E1_ANALYSIS.json", "COMPARISONS.json", "GATE_AGGREGATE.json", "GATE_AUDIT.json", "TRANSFER_SUMMARY.json", "PUBLICATION.json"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pct(value):
    return "not available" if value is None else f"{100 * value:.2f}%"


def points(value):
    return "not available" if value is None else f"{100 * value:+.2f} percentage points"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close_values(left, right):
    """Float arithmetic may differ; counts, statuses, keys and order must match."""
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(close_values(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(close_values(a, b) for a, b in zip(left, right))
    if type(left) is float and type(right) is float:
        return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=0, abs_tol=1e-10)
    return type(left) is type(right) and left == right


def roster(rows, fields):
    keys = [tuple(row[field] for field in fields) for row in rows]
    require(len(keys) == len(set(keys)), "Duplicate publication cell or seed")
    return set(keys)


def aggregate_only(value):
    private_keys = {"x", "y", "test_y", "calibration_y", "y_binary", "raw_to_unique", "group_sha256",
                    "selected_fit_indices", "selected_fit_fingerprints", "target_fingerprints", "test_indices",
                    "calibration_indices", "target_query_fingerprints", "indices", "fingerprints", "probabilities",
                    "target_probabilities", "test_probabilities", "calibration_probabilities", "routing_flags",
                    "input_runs", "model_path", "path"}
    if isinstance(value, dict):
        require(not private_keys.intersection(key.lower() for key in value), "Row-level data or private path field cannot be published")
        for item in value.values():
            aggregate_only(item)
    elif isinstance(value, list):
        require(len(value) <= 2048, "Unexpected row-length array in aggregate publication")
        for item in value:
            aggregate_only(item)
    elif isinstance(value, str):
        require(not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]|\\\\[^\\]|^/(?:home|Users|w|mnt|tmp)/", value), "Private absolute path cannot be published")


def verify(e1, comparisons, gate, gate_audit):
    if e1.get("audit_status") != "PASS" or not e1.get("all_registered_cells_complete") or e1.get("completed_cell_count") != 50:
        raise ValueError("All 50 audited original E1 cells are required for final publication")
    if comparisons.get("audit_status") != "PASS" or not comparisons.get("strong_batch_complete") or comparisons.get("complete_strong_cells") != 60:
        raise ValueError("All 60 audited stronger-control cells are required")
    if gate_audit.get("audit_status") != "PASS" or gate_audit.get("run_status") != "COMPLETE" or gate_audit.get("audited_pair_count") != 10:
        raise ValueError("Ten independently audited review pairs are required")
    if gate.get("missing_pairs") != [] or gate["primary"]["paired_seed_count"] != 10 or not close_values(gate["primary"], gate_audit["primary"]):
        raise ValueError("Gate audit and recorded outcomes disagree")
    require(roster(e1["cells"], ["model", "seed"]) == {(model, seed) for model in E1_MODELS for seed in SEEDS}, "Original E1 cell roster is incomplete")
    require(roster(comparisons["cells"], ["condition", "model", "seed"]) == {(condition, model, seed) for condition in CONDITIONS for model in TREE_MODELS for seed in SEEDS}, "Stronger-control cell roster is incomplete")
    require(roster(gate["rows"], ["seed"]) == {(seed,) for seed in SEEDS}, "Review seed roster is incomplete")
    require(e1.get("missing_registered_cells") == [] and e1["primary"]["matched_seed_count"] == e1["primary"]["expected_seed_count"] == 10 and e1["primary"]["all_ten_registered_seeds_present"] is True, "Original paired E1 gate is incomplete")
    require(all(e1["primary"][name]["status"] in {"PASS", "FAIL"} for name in ["e1", "e4"]), "Original development decision is incomplete")
    require(comparisons.get("expected_strong_cells") == 60 and comparisons.get("full_e1_completed_cells") == 50 and close_values(comparisons["full_e1_primary"], e1["primary"]), "Comparisons refer to another or incomplete E1 analysis")
    for condition in CONDITIONS:
        result = comparisons["comparisons"][condition]
        require(result["matched_seeds"] == 10 and roster(result["pairs"], ["seed"]) == {(seed,) for seed in SEEDS}, "Stronger comparison pairs are incomplete")
        expected_status = {"PASS", "FAIL"} if condition == "equal_32_per_class" else {"DESCRIPTIVE_UNEQUAL_LABEL_BUDGET"}
        require(result["status"] in expected_status, "Invalid stronger comparison interpretation")
    require(gate["primary"]["required_paired_seeds"] == 10 and gate["primary"]["status"] in {"DEVELOPMENT_PROMISING", "DEVELOPMENT_NEGATIVE"}, "Review decision is incomplete")


def verify_transfer(transfer, e1):
    require(transfer.get("audit_status") == "PASS" and transfer.get("all_cells_complete") is True and transfer.get("run_status") == "COMPLETE" and transfer.get("verified_cells") == 20 and transfer.get("paired_seed_count") == 10, "External summary requires all twenty audited cells and ten pairs")
    require(roster(transfer["per_seed"], ["model", "seed"]) == {(model, seed) for model in ["selected_gbdt", "tabicl_v2"] for seed in SEEDS}, "External model/seed roster is incomplete")
    require(transfer.get("decision") == "DESCRIPTIVE_ONLY_NO_PASS_GATE", "External comparison must remain descriptive")
    for external, original in [("source_data_npz_sha256", "data_sha256"), ("source_manifest_sha256", "manifest_sha256"), ("e1_protocol_sha256", "protocol_sha256")]:
        require(transfer[external] == e1["common_binding"][original], "External summary used different source evidence")


def verify_sources(final_root, values, transfer=None):
    source = Path(__file__).parent
    batch = source.parent / "tabular_batch"
    original, strong_protocol = read(batch / "protocol.json"), read(source / "protocol_strong_baselines.json")
    e1, comparison, gate, gate_audit = (values[name] for name in ["E1_ANALYSIS.json", "COMPARISONS.json", "GATE_AGGREGATE.json", "GATE_AUDIT.json"])
    expected = {"data_sha256": original["data_npz_sha256"], "manifest_sha256": original["manifest_sha256"], "protocol_sha256": sha(batch / "protocol.json"),
                "code_sha256": {name: sha(batch / name) for name in ["run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt"]}}
    require(e1["common_binding"] == expected, "Original scientific source or input binding changed")
    require(comparison["protocol_sha256"] == sha(source / "protocol_strong_baselines.json") and comparison["auditor_sha256"] == sha(source / "audit_comparisons.py"), "Stronger comparison audit/source binding changed")
    require(strong_protocol["data_npz_sha256"] == expected["data_sha256"] and strong_protocol["e1_protocol_sha256"] == expected["protocol_sha256"], "Stronger protocol uses different source data")
    require(gate["policy_protocol_sha256"] == gate_audit["protocol_sha256"] == sha(source / "protocol_rare_stage_gate.json"), "Gate protocol binding changed")
    require(gate_audit["runner_sha256"] == sha(source / "run_rare_stage_gate.py") and gate_audit["audit_source_sha256"] == sha(source / "audit_rare_stage_gate.py"), "Gate runner/auditor changed")
    expected_artifacts = {"AGGREGATE.json", "PREFIT_RECEIPT.json", "COMPLETE.json", "SOURCE_ANALYSIS.json", "ROUTING_PRIVATE.npz"}
    require(set(gate_audit["artifact_hashes"]) == expected_artifacts, "Gate audit artifact roster changed")
    for name, digest in gate_audit["artifact_hashes"].items():
        require(sha(final_root / "gate" / name) == digest, "Gate artifact changed after independent audit")
    require(close_values(read(final_root / "gate/SOURCE_ANALYSIS.json"), e1), "Gate and publication use different E1 evidence")
    if transfer is not None:
        require(transfer["protocol_sha256"] == sha(source / "protocol_sandworm_transfer.json") and transfer["audit_code_sha256"] == sha(source / "audit_sandworm_transfer.py"), "External protocol/auditor binding changed")


def report(e1, comparison, gate, transfer=None, *, documentation_base="../../tabular_followup"):
    eq = comparison["comparisons"]["equal_32_per_class"]
    lines = ["# Reliable APT recognition with limited labeled data: followup results", "",
        f"**Execution complete:** 50 original model/seed cells, 60 stronger-tree cells, and ten rare-stage review comparisons were audited. The original TabICL development gate is **{e1['primary']['e1']['status']}**; the stronger equal-label comparison is **{eq['status']}**; the rare-stage review policy is **{gate['primary']['status']}**.", "",
        "These are development findings on the same feature-deduplicated SCVIC author-training split. Completion and arithmetic verification do not establish a novel method, independent attack-campaign generalization, or reliable deployment.", "",
        "## Full original comparison", "",
        "Unlike the earlier weighted prescreen, these models were evaluated on every one of the 30,787 development-test flows. Each used the same 32 fitting labels per class (192 total) across ten matched fitting seeds. Seeds reuse the same test flows and are not independent incidents.", "",
        "| Model | Mean full-test macro-F1 |", "|---|---:|"]
    for name, item in e1["model_summaries"].items():
        lines.append(f"| {name} | {pct(item['macro_f1']['mean'])} |")
    lines += ["", "Macro-F1 gives all six classes equal weight; it is not accuracy. Boosted-tree hyperparameters and comparator families were selected using fitting-only cross-validation, never test outcomes. The foundation candidates were fixed in advance.", "",
        f"The original paired TabICL macro-F1 difference is {points(e1['primary']['e1']['mean_paired_macro_f1_delta']['mean'])}. Full uncertainty-set E4 result: **{e1['primary']['e4']['status']}**. [Full E1/E4 evidence](E1_ANALYSIS.json).", "",
        "## Stronger controls and additional normal examples", "",
        "The new tree search used 12 XGBoost, 12 LightGBM, and six Random Forest settings in training-only three-fold cross-validation. No extra validation labels were used.", "",
        "| Fitting condition | Tree family | Mean full-test macro-F1 | Normal false-alarm rate |", "|---|---|---:|---:|"]
    for condition, models in comparison["model_summaries"].items():
        for name, item in models.items():
            lines.append(f"| {condition} | {name} | {pct(item['macro_f1']['mean'])} | {pct(item['normal_fpr']['mean'])} |")
    lines += ["", f"At the same 192-label budget, TabICL's mean difference versus the wider-CV-selected boosted tree was {points(eq['mean_macro_f1_delta'])}. Both rare-stage recall guards remain part of the decision.", "",
        "The abundant-normal condition used 1,024 normal labels and the same 160 attack labels, totaling 1,184. Its comparison with a 192-label foundation model is an explicitly unequal-budget deployment challenge, not a fair model-family ranking. [All controls and paired comparisons](COMPARISONS.json).", "",
        "## Rare-stage review experiment", "",
        "The fixed policy allocated a nominal 0.5% benign tail to a general attack score and 0.5% to a rare-stage rescue score combining TabICL and the original training-CV-selected tree. Both thresholds used source benign calibration examples only. The policy had to beat both fixed single-model controls, protect every attack stage, and remain at or below 1.5% observed normal-traffic routing in every seed.", "",
        f"Decision: **{gate['primary']['status']}**. Mean changes in minimum initial-compromise/exfiltration routing recall: " + "; ".join(f"{name}: {points(value)}" for name, value in gate["primary"]["mean_minimum_rare_recall_deltas"].items()) + ".", "",
        "Sending a flow to review is not correct stage identification or successful human correction. No human review was performed. The proposed rule needs 29,929 known-normal calibration examples beyond the 192 fitting labels; the conformal controls use all 30,782 calibration labels. At nominal 95% class-conditional coverage, the 14 initial-compromise calibration cases force that stage into every set, making this policy's review mapping route every flow.", "",
        "[Policy results](GATE_AGGREGATE.json) and [independent calculation audit](GATE_AUDIT.json).", "",
        "## Independent evidence and praxis decision", ""]
    if transfer:
        lines += ["A separate Sandworm transfer check is documented in [external evidence](TRANSFER_SUMMARY.json). Its 37 attack flows use procedure labels, with no exfiltration class. It tests fresh binary transfer only and cannot validate the rare-stage protection claim.", ""]
    else:
        lines += [f"The SCVIC author holdout remains unavailable. A small author-released Sandworm capture was separately qualified for binary transfer; see the [qualification record]({documentation_base}/HOLDOUT_QUALIFICATION.md). This is not an all-stage confirmation dataset.", ""]
    lines += [f"Direct prior work already covers these combinations, including tree-to-foundation rescue, few-label adaptation, cross-dataset transfer, and conformal prediction. This review policy is a development adaptation tested under rare-stage and false-alert constraints; there is no first-method claim. A defensible praxis contribution still requires a specific positive benefit and independent evidence with the relevant attack-stage labels. See the [novelty review and publication-status distinctions]({documentation_base}/NOVELTY_POSITION.md) and [method boundaries]({documentation_base}/RARE_STAGE_DESIGN.md).", "",
        "Remaining limits: only 15 initial-compromise and 106 exfiltration development-test examples; correlated flows and fitting seeds; fixed dataset label interpretation; no analyst workload study; no missing-log, early-warning, actor-attribution, or unknown-stage guarantee. All outcomes, including failed gates, are retained.", ""]
    return "\n".join(lines)


def publish(final_root, output, transfer_summary=None):
    paths = {"E1_ANALYSIS.json": final_root / "e1/ANALYSIS.json", "COMPARISONS.json": final_root / "COMPARISONS.json",
             "GATE_AGGREGATE.json": final_root / "gate/AGGREGATE.json", "GATE_AUDIT.json": final_root / "gate_audit/AUDIT.json"}
    values = {name: read(path) for name, path in paths.items()}
    verify(*(values[name] for name in paths))
    transfer = read(transfer_summary) if transfer_summary is not None else None
    if transfer is not None:
        verify_transfer(transfer, values["E1_ANALYSIS.json"])
    verify_sources(final_root, values, transfer)
    for value in [*values.values(), *([transfer] if transfer is not None else [])]:
        aggregate_only(value)
    if output.exists():
        require(all(path.name in PUBLIC_FILES and path.is_file() and not path.is_symlink() for path in output.iterdir()), "Unexpected file in aggregate publication directory")
        require(transfer is not None or not (output / "TRANSFER_SUMMARY.json").exists(), "Preserve the existing optional transfer publication; provide its audited summary")
    documentation_base = Path(os.path.relpath(Path(__file__).parent, output)).as_posix()
    for name in ["HOLDOUT_QUALIFICATION.md", "RARE_STAGE_DESIGN.md", "NOVELTY_POSITION.md"]:
        require((Path(__file__).parent / name).is_file(), "Publication documentation link target is missing")
    output.mkdir(parents=True, exist_ok=True)
    for name, value in values.items():
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    if transfer is not None:
        (output / "TRANSFER_SUMMARY.json").write_text(json.dumps(transfer, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (output / "REPORT.md").write_text(report(*[values[name] for name in list(paths)[:3]], transfer=transfer, documentation_base=documentation_base), encoding="utf-8")
    artifact_names = [*paths, "REPORT.md", *(["TRANSFER_SUMMARY.json"] if transfer is not None else [])]
    receipt = {"status": "COMPLETE_AUDITED", "published_utc": datetime.now(timezone.utc).isoformat(),
               "publisher_sha256": sha(__file__), "source_sha256": {**{name: sha(path) for name, path in paths.items()}, **({"TRANSFER_SUMMARY.json": sha(transfer_summary)} if transfer is not None else {})},
               "artifact_sha256": {name: sha(output / name) for name in artifact_names},
               "no_raw_or_row_level_data_published": True, "scientific_outcomes_may_be_negative": True}
    (output / "PUBLICATION.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--transfer-summary", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.final_root, args.output, args.transfer_summary)))
