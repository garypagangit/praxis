"""Render a separate praxis decision report only from completed audited evidence.

No fitting, inference, threshold selection, scientific modification, or Git action.
Existing coordinator/publication files are read only. All output is aggregate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from . import publish_followup as pub
from ..tabular_batch.audit_e3 import compare

FINAL_ARTIFACTS = {"e1/ANALYSIS.json", "e1/REPORT.md", "COMPARISONS.json", "gate/AGGREGATE.json", "gate/COMPLETE.json", "gate_audit/AUDIT.json", "external/TRANSFER_SUMMARY.json"}
OUTPUT_FILES = {"REPORT.md", "DECISION_EVIDENCE.json", "PUBLICATION.json"}
POLICIES = ("candidate", "single_tabicl", "single_tree", "two_channel_tabicl_only")


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values and all(v is not None for v in values) else None


def verify_manifest(root):
    manifest = pub.read(root / "RESULT_MANIFEST.json")
    pub.require(manifest.get("status") == "COMPLETE_AUDITED", "Final manifest is not complete and audited")
    for name, count in (("full_e1_cells", 50), ("strong_cells", 60), ("review_gate_pairs", 10), ("external_cells", 20)):
        pub.require(type(manifest.get(name)) is int and manifest[name] == count, "Incomplete manifest count: " + name)
    pub.require(manifest.get("no_model_fitting_or_inference_performed") is True, "Unexpected finalization scope")
    pub.require(set(manifest["artifact_sha256"]) == FINAL_ARTIFACTS, "Unexpected final artifact roster")
    for name, claimed in manifest["artifact_sha256"].items():
        path = root / name
        pub.require(path.is_file() and not path.is_symlink() and pub.sha(path) == claimed, "Final artifact changed: " + name)
    pub.require(pub.sha(root / "STARTUP_RECEIPT.json") == manifest["startup_receipt_sha256"], "Startup receipt changed")
    return manifest


def selected_tree_tradeoffs(comparison):
    result = {}
    for condition in ("equal_32_per_class", "abundant_benign_1024"):
        rows = []
        for seed in sorted(pub.SEEDS):
            options = {cell["model"]: cell for cell in comparison["cells"] if cell["condition"] == condition and cell["seed"] == seed and cell["model"] in ("xgboost", "lightgbm")}
            pub.require(set(options) == {"xgboost", "lightgbm"}, "Missing stronger tree pair")
            selected = max((options["xgboost"], options["lightgbm"]), key=lambda cell: cell["cv_macro_f1"])
            metrics = selected["metrics"]; classes = metrics["classes"]; matrix = metrics["confusion_matrix"]
            normal = classes.index("NormalTraffic"); attack = [k for k in range(len(classes)) if k != normal]
            support = [sum(row) for row in matrix]
            pub.require(all(n > 0 for n in support), "Unsupported stage in stronger comparison")
            rows.append({"seed": seed, "selected_model": selected["model"], "macro_f1": metrics["macro_f1"],
                         "normal_fpr": (support[normal] - matrix[normal][normal]) / support[normal],
                         "binary_attack_recall": sum(support[k] - matrix[k][normal] for k in attack) / sum(support[k] for k in attack),
                         "binary_detection_by_stage": {classes[k]: (support[k] - matrix[k][normal]) / support[k] for k in attack},
                         "exact_stage_recall": {classes[k]: matrix[k][k] / support[k] for k in attack}})
        averages = {key: mean(row[key] for row in rows) for key in ("macro_f1", "normal_fpr", "binary_attack_recall")}
        for key in ("binary_detection_by_stage", "exact_stage_recall"):
            averages[key] = {name: mean(row[key][name] for row in rows) for name in rows[0][key]}
        result[condition] = {"mean": averages, "per_seed": rows, "seeds": len(rows)}
    return result


def verify_benign_context(folder, comparison):
    receipt = pub.read(folder / "PUBLICATION.json")
    pub.require(receipt.get("status") == "DESCRIPTIVE_UNEQUAL_LABEL_BUDGET", "Unexpected benign-control interpretation")
    pub.require(set(receipt["artifact_sha256"]) == {"REPORT.md", "SUMMARY.json", "AUDIT.json"}, "Benign-context artifact roster differs")
    for name, claimed in receipt["artifact_sha256"].items():
        pub.require(pub.sha(folder / name) == claimed, "Benign-context artifact changed: " + name)
    old_audit, summary = pub.read(folder / "AUDIT.json"), pub.read(folder / "SUMMARY.json")
    pub.require(old_audit["audit_status"] == summary["audit_status"] == "PASS" and old_audit["complete_strong_cells"] == summary["strong_cells"] == 60, "Benign controls are not fully audited")
    pub.require(receipt["source_audit_sha256"] == summary["source_audit_sha256"] == pub.sha(folder / "AUDIT.json"), "Benign audit binding differs")
    key = lambda cell: (cell["condition"], cell["model"], cell["seed"])
    old = {key(cell): cell["prediction_sha256"] for cell in old_audit["cells"]}
    current = {key(cell): cell["prediction_sha256"] for cell in comparison["cells"]}
    pub.require(old == current and len(current) == 60, "Benign context used different tree predictions")
    derived = selected_tree_tradeoffs(comparison)
    compare(derived, summary["models"]["cv_selected_gbdt"], "independently recomputed benign tradeoff")
    return derived, {name: pub.sha(folder / name) for name in ("PUBLICATION.json", "SUMMARY.json", "AUDIT.json", "REPORT.md")}


def review_summary(gate):
    result = {}
    for policy in POLICIES:
        metrics = [row["policies"][policy] for row in gate["rows"]]
        rare = {}
        for stage in ("InitialCompromise", "DataExfiltration"):
            supports = {item["per_stage"][stage]["support"] for item in metrics}
            pub.require(len(supports) == 1, "Review stage denominator changed across seeds")
            rare[stage] = {"same_test_support": next(iter(supports)),
                           "mean_routed_count": mean(item["per_stage"][stage]["routed"] for item in metrics),
                           "mean_routing_recall": mean(item["per_stage"][stage]["routing_fraction"] for item in metrics)}
        result[policy] = {"rare_stages": rare,
                          **{"mean_" + field: mean(item[field] for item in metrics) for field in ("reviewed", "review_fraction", "review_queue_attack_precision", "benign_fpr", "attack_routing_recall")},
                          "maximum_seed_benign_fpr": max(item["benign_fpr"] for item in metrics)}
    return result


def verify_external_diagnostic(transfer):
    diagnostic = transfer.get("source_threshold_diagnostic", {})
    pub.require(diagnostic.get("status") == "COMPLETE_AUDITED", "External source-threshold diagnostic incomplete")
    pub.require(len(diagnostic.get("pairs", [])) == 10 and len(diagnostic.get("per_seed", [])) == 20, "External diagnostic pair/cell roster incomplete")
    pub.require(pub.roster(diagnostic["pairs"], ["seed"]) == {(seed,) for seed in pub.SEEDS}, "External diagnostic seed pairs differ")
    pub.require(pub.roster(diagnostic["per_seed"], ["model", "seed"]) == {(model, seed) for model in ("tabicl_v2", "selected_gbdt") for seed in pub.SEEDS}, "External diagnostic roster differs")


def load_evidence(final_root, benign_folder):
    verify_manifest(final_root)
    paths = {"E1_ANALYSIS.json": final_root / "e1/ANALYSIS.json", "COMPARISONS.json": final_root / "COMPARISONS.json",
             "GATE_AGGREGATE.json": final_root / "gate/AGGREGATE.json", "GATE_AUDIT.json": final_root / "gate_audit/AUDIT.json"}
    values = {name: pub.read(path) for name, path in paths.items()}
    e1, comparisons, gate, gate_audit = values.values()
    transfer = pub.read(final_root / "external/TRANSFER_SUMMARY.json")
    pub.verify(e1, comparisons, gate, gate_audit)
    pub.verify_transfer(transfer, e1)
    pub.verify_sources(final_root, values, transfer)
    verify_external_diagnostic(transfer)
    tradeoff, context_hashes = verify_benign_context(benign_folder, comparisons)
    policies = review_summary(gate)
    evidence = {"status": "COMPLETE_AUDITED_DECISION_REPORT", "source_result_manifest_sha256": pub.sha(final_root / "RESULT_MANIFEST.json"),
                "source_artifact_sha256": {**{name: pub.sha(path) for name, path in paths.items()}, "TRANSFER_SUMMARY.json": pub.sha(final_root / "external/TRANSFER_SUMMARY.json")},
                "benign_context_hashes": context_hashes, "completed_counts": {"original_cells": 50, "strong_cells": 60, "review_pairs": 10, "external_cells": 20},
                "registered_decisions": {"original_e1": e1["primary"]["e1"]["status"], "original_e4": e1["primary"]["e4"]["status"],
                                         "strong_equal_label": comparisons["comparisons"]["equal_32_per_class"]["status"], "review_policy": gate["primary"]["status"]},
                "review_primary": gate["primary"], "review_absolute_metrics": policies, "selected_tree_label_tradeoff": tradeoff,
                "novelty_established": False, "independent_attack_stage_validation": False,
                "new_success_criteria_applied": False, "human_review_performed": False}
    for value in (evidence, e1, comparisons, gate, gate_audit, transfer): pub.aggregate_only(value)
    return evidence, e1, comparisons, gate, transfer


def render(evidence, e1, comparisons, gate, transfer, *, docs="../../tabular_followup", benign_report="../strong_benign_controls_v1/REPORT.md"):
    decisions = evidence["registered_decisions"]
    positive_review = decisions["review_policy"] == "DEVELOPMENT_PROMISING"
    strong_positive = decisions["strong_equal_label"] == "PASS"
    lines = ["# Final praxis decision: rare-stage protection and limited-label APT recognition", "",
             "All required evidence is complete and audited: 50 original model runs, 60 stronger-control runs, ten review-policy pairs, and 20 external-transfer runs including the source-threshold diagnostic. Completion does not establish a novel method or deployment readiness.", "",
             "## What remains worth pursuing", "",
             ("The review policy met its frozen development criteria and is a candidate for independent validation with attack-stage labels." if positive_review else "The review policy did not meet its frozen development criteria; this completed experiment does not support advancing that policy as a demonstrated improvement."), "",
             ("The TabICL comparison also passed the stronger equal-label control gate, preserving a candidate classification benefit for independent replication." if strong_positive else "The TabICL comparison did not clear the stronger equal-label control gate; the original comparison alone does not establish a benefit over those stronger controls."), "",
             "**No algorithmic novelty or independent attack-stage validation is established.** A positive development gate identifies work worth validating; it is not a completed novel praxis claim. The Sandworm experiment tests binary transfer on one capture and cannot validate the proposed InitialCompromise/Exfiltration protection.", "",
             "| Frozen decision | Completed outcome |", "|---|---|"]
    labels = {"original_e1": "Original classification comparison", "original_e4": "Original uncertainty-set comparison", "strong_equal_label": "Stronger comparison at the same 192 labels", "review_policy": "Rare-stage review policy"}
    lines += [f"| {labels[key]} | {value} |" for key, value in decisions.items()]
    lines += ["", "Each outcome retains its original criterion. No new success threshold or combined score was introduced for this report.", "",
              "## Rare-stage protection: exact criteria and absolute cost", "",
              "The frozen gate requires all three conditions: (1) at least **+5 percentage points** in the mean paired difference of each seed's minimum InitialCompromise/Exfiltration routing recall, against **both** fixed single-model controls; (2) no more than **5 percentage points of mean recall loss for any attack stage**, against either control; and (3) normal-flow routing at or below **1.5% in every seed**. The rule therefore permits a limited average loss in an individual stage; it does not require every stage or seed to improve.", "",
              "The two candidate channels each use a nominal 0.5% source-normal tail. Each fixed single-model control uses 1%. These calibration targets are distinct from the measured 1.5% per-seed development gate and provide no arbitrary-shift guarantee.", "",
              "| Routing policy | Initial recall (mean routed/15) | Exfiltration recall (mean routed/106) | Queue attack precision | Mean reviewed flows | Review workload | Mean normal FPR | Maximum seed normal FPR |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    policy_labels = {"candidate": "Two-model review policy", "single_tabicl": "Fixed TabICL control", "single_tree": "Fixed source-CV-selected tree control", "two_channel_tabicl_only": "TabICL-only rescue ablation"}
    for name, item in evidence["review_absolute_metrics"].items():
        initial, exfil = (item["rare_stages"][stage] for stage in ("InitialCompromise", "DataExfiltration"))
        lines.append(f"| {policy_labels[name]} | {pub.pct(initial['mean_routing_recall'])} ({initial['mean_routed_count']:.2f}/{initial['same_test_support']}) | {pub.pct(exfil['mean_routing_recall'])} ({exfil['mean_routed_count']:.2f}/{exfil['same_test_support']}) | {pub.pct(item['mean_review_queue_attack_precision'])} | {item['mean_reviewed']:.1f} | {pub.pct(item['mean_review_fraction'])} | {pub.pct(item['mean_benign_fpr'])} | {pub.pct(item['maximum_seed_benign_fpr'])} |")
    lines += ["", "Recall here means reaching the review queue. Queue precision means the fraction of reviewed flows that are any attack; this binary gate does not output a stage-classification precision. Correct stage identification and successful analyst adjudication were not measured by the routing experiment. Counts are means over repeated fits on the same cases, not additional independent attacks.", "",
              "The candidate needs 29,929 known-normal calibration labels beyond its shared 192 fitting labels; conformal controls use all 30,782 calibration labels. Only nominal **95% class-conditional (Mondrian) LAC** is forced to include InitialCompromise for every input with these 14 rare calibration cases, making the specified protective mapping review every flow. This is not a claim that 90% Mondrian or all conformal methods review everything.", "",
              "## Original models and the stronger benign-label challenge", "",
              "| Original model | Full-test macro-F1 |", "|---|---:|"]
    for name, summary in e1["model_summaries"].items(): lines.append(f"| {name} | {summary['macro_f1']['mean']:.4f} |")
    lines += ["", "| Stronger tree family | Macro-F1: 192 labels | Macro-F1: 1,184 labels |", "|---|---:|---:|"]
    for name in sorted(pub.TREE_MODELS):
        a, b = (comparisons["model_summaries"][condition][name]["macro_f1"]["mean"] for condition in ("equal_32_per_class", "abundant_benign_1024"))
        lines.append(f"| {name} | {a:.4f} | {b:.4f} |")
    a, b = (evidence["selected_tree_label_tradeoff"][condition]["mean"] for condition in ("equal_32_per_class", "abundant_benign_1024"))
    lines += ["", f"For the fitting-CV-selected boosted tree, adding 992 normal examples changed macro-F1 from **{a['macro_f1']:.4f} to {b['macro_f1']:.4f}** and normal false alarms from **{pub.pct(a['normal_fpr'])} to {pub.pct(b['normal_fpr'])}**. The same 160 attack fitting labels were retained; total fitting labels rose from 192 to 1,184.", "",
              f"The detection cost matters: pooled attack detection changed **{pub.pct(a['binary_attack_recall'])} to {pub.pct(b['binary_attack_recall'])}**; lateral-movement detection as any attack changed **{pub.pct(a['binary_detection_by_stage']['LateralMovement'])} to {pub.pct(b['binary_detection_by_stage']['LateralMovement'])}**. These are binary detection rates, distinct from correctly identifying the stage. More benign labels improved an established baseline with a security tradeoff; the unequal-label condition is not a fair model-family victory or a new algorithm.", "",
              "This comparison does **not establish tree architecture superiority**: the foundation models received 192 fitting labels while the abundant-benign trees received 1,184. No matched abundant-benign foundation-model arm was run. Isolating an architecture effect would require the same label budget and fitting data.", "",
              f"The [independently audited benign-control report]({benign_report}) documents all stage tradeoffs. Its tree predictions are hash-matched to this final comparison. The abundant-benign models were not the models evaluated in Sandworm transfer.", "",
              "## External binary transfer: separate operating points", "", *pub.transfer_report(transfer),
              "## Limits of the praxis claim", "",
              f"The [novelty review]({docs}/NOVELTY_POSITION.md), [focused benign-label novelty note]({docs}/BENIGN_LABEL_NOVELTY_NOTE.md), and [frozen method design]({docs}/RARE_STAGE_DESIGN.md) document relevant overlap and distinguish publication status. Conditional candidacy above follows the registered development gates only. A defensible new contribution still needs a clearly distinct mechanism or applied finding and independent evidence for the relevant attack stages.", "",
              "These results do not establish early warning, actor attribution, robustness to missing or delayed logs, or unknown-stage protection. Fifteen InitialCompromise cases and 106 Exfiltration cases are reused across fitting seeds; no independent-incident confidence claim follows. The official SCVIC author holdout remains unavailable.", "",
              "[Decision evidence and source hashes](DECISION_EVIDENCE.json). No new model fit, inference, threshold search, or human review was performed to create this report.", ""]
    return "\n".join(lines)


def generate(final_root, output, benign_folder):
    final_root, output, benign_folder = map(lambda p: Path(p).resolve(), (final_root, output, benign_folder))
    pub.require(output != final_root and not output.is_relative_to(final_root), "Keep decision publication separate from private final evidence")
    pub.require(output.name == "tabular_followup_decision_v1", "Use the separate tabular_followup_decision_v1 output directory")
    if output.exists(): pub.require(all(p.name in OUTPUT_FILES and p.is_file() and not p.is_symlink() for p in output.iterdir()), "Existing decision output has unowned files")
    evidence, e1, comparisons, gate, transfer = load_evidence(final_root, benign_folder)
    here = Path(__file__).parent
    for name in ("NOVELTY_POSITION.md", "BENIGN_LABEL_NOVELTY_NOTE.md", "RARE_STAGE_DESIGN.md"):
        pub.require((here / name).is_file(), "Missing report documentation: " + name)
    docs = Path(os.path.relpath(here, output)).as_posix()
    benign_report = Path(os.path.relpath(benign_folder / "REPORT.md", output)).as_posix()
    report = render(evidence, e1, comparisons, gate, transfer, docs=docs, benign_report=benign_report)
    pub.aggregate_only(report); pub.aggregate_only(evidence)
    output.mkdir(parents=True, exist_ok=True)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    (output / "DECISION_EVIDENCE.json").write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    receipt = {"status": "COMPLETE_AUDITED_DECISION_REPORT", "created_utc": datetime.now(timezone.utc).isoformat(),
               "generator_sha256": pub.sha(Path(__file__)), "source_result_manifest_sha256": evidence["source_result_manifest_sha256"],
               "artifact_sha256": {name: pub.sha(output / name) for name in ("REPORT.md", "DECISION_EVIDENCE.json")}, "no_raw_or_private_paths_published": True}
    (output / "PUBLICATION.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benign-controls", type=Path, default=Path(__file__).parent.parent / "results/strong_benign_controls_v1")
    args = parser.parse_args()
    print(json.dumps(generate(args.final_root, args.output, args.benign_controls)))
