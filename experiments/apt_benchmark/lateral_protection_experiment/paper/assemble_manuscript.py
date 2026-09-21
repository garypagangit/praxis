"""Assemble the completed, audited negative-feasibility praxis manuscript.

Reads published aggregates only. No models, predictions, or raw flows are loaded.
The manuscript is deliberately scoped to this experiment's INFEASIBLE primary
outcome; changed scientific outcomes require a new reviewed interpretation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from statistics import fmean


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = HERE.parents[3]
CLASSES = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]
STAGES = [x for x in CLASSES if x != "NormalTraffic"]
SHORT = {"DataExfiltration": "Exfiltration", "InitialCompromise": "Initial", "LateralMovement": "Lateral",
         "Pivoting": "Pivoting", "Reconnaissance": "Reconnaissance", "NormalTraffic": "Normal"}
POLICIES = ["reference", "candidate", "threshold_only", "cv_natural_argmax", "cv_natural_benign_threshold"]
NAMES = {"reference": "Lateral-sensitive reference", "candidate": "Constrained candidate", "threshold_only": "Threshold-only ablation",
         "cv_natural_argmax": "Natural tree, argmax", "cv_natural_benign_threshold": "Natural tree, source-normal 1% threshold"}
SCHEMES = ["natural", "balanced", "lateral2", "lateral4"]
MODELS = ["xgboost", "lightgbm"]
METRICS = ["benign_fpr", "fp", "tp", "attack_recall", "attack_precision", "attack_f1", "roc_auc", "average_precision", "alert_fraction"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same(a, b, label="Value"):
    """Exact structure and discrete values; tolerate numerical aggregation roundoff."""
    if isinstance(a, dict):
        require(isinstance(b, dict) and set(a) == set(b), label + " keys differ")
        for key in a:
            same(a[key], b[key], label + "/" + key)
    elif isinstance(a, list):
        require(isinstance(b, list) and len(a) == len(b), label + " list differs")
        for i, (left, right) in enumerate(zip(a, b)):
            same(left, right, label + "/" + str(i))
    elif type(a) is float or type(b) is float:
        require(isinstance(a, (int, float)) and not isinstance(a, bool)
                and isinstance(b, (int, float)) and not isinstance(b, bool)
                and math.isfinite(a) and math.isfinite(b)
                and math.isclose(a, b, rel_tol=0, abs_tol=1e-10), label + " numeric value differs")
    else:
        require(type(a) is type(b) and a == b, label + " differs")


def table(header, rows):
    require(2 <= len(header) <= 6, "Document tables must have two through six columns")
    all_rows = [header, ["---"] * len(header), *rows]
    require(all(len(row) == len(header) for row in all_rows), "Table columns differ")
    return "\n".join("| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in row) + " |" for row in all_rows)


def pct(value, digits=3):
    return "Not estimable" if value is None else f"{100 * value:.{digits}f}%"


def number(value, digits=4):
    return "Not estimable" if value is None else f"{value:.{digits}f}"


def policy_means(rows, partition):
    out = {}
    for name in POLICIES:
        selected = [r["partitions"][partition][name] for r in rows if name in r["partitions"][partition]]
        if not selected:
            continue
        out[name] = {"pairs": len(selected), "seeds": [r["seed"] for r in rows if name in r["partitions"][partition]],
                     **{key: fmean(x[key] for x in selected) for key in METRICS},
                     "stage_recall": {stage: fmean(x["per_stage"][stage]["recall"] for x in selected) for stage in STAGES},
                     "stage_detected": {stage: fmean(x["per_stage"][stage]["detected"] for x in selected) for stage in STAGES},
                     "worst_lateral_recall": min(x["per_stage"]["LateralMovement"]["recall"] for x in selected),
                     "worst_benign_fpr": max(x["benign_fpr"] for x in selected)}
    return out


def validate_package(results, diagnostic_path, validation_path):
    results = Path(results).resolve()
    require(results.is_relative_to(REPO), "Read a public repository aggregate directory, not private run files")
    publication = read(results / "PUBLICATION.json")
    required = {"EVIDENCE.json", "SUMMARY.json", "CELL_METRICS.json", "AUDIT.json", "EXTERNAL_RESULT.json", "EXTERNAL_AUDIT.json"}
    require(required <= set(publication["files"]), "Publication manifest lacks required complete evidence")
    for name, expected in publication["files"].items():
        path = (results / name).resolve()
        require(path.is_relative_to(results) and path.is_file(), "Unsafe or missing published artifact")
        require(digest(path) == expected, "Published artifact hash changed: " + name)
    evidence, summary, cells, audit = [read(results / name) for name in ["EVIDENCE.json", "SUMMARY.json", "CELL_METRICS.json", "AUDIT.json"]]
    require(evidence["status"] == "AUDITED_COMPLETE_DEVELOPMENT_STUDY", "Evidence is not completed and audited")
    require(summary["status"] == audit["run_status"] == "COMPLETE" and audit["audit_status"] == "PASS", "Source audit/completion failed")
    require(summary["completed_groups"] == summary["required_groups"] == audit["completed_groups"] == audit["required_groups"] == 19,
            "Expected all 19 registered groups")
    require(summary["completed_cells"] == summary["required_cells"] == audit["audited_cells"] == audit["required_cells"] == len(cells) == 152,
            "Expected all 152 registered final model cells")
    require(not audit["missing_groups"], "Independent audit reports missing groups")
    binding = evidence["execution_binding"]
    require(binding == summary["execution_binding"] == audit["execution_binding"] == publication["source_execution_binding"], "Mixed source bindings")
    require(audit["artifact_hashes"]["SUMMARY.json"] == digest(results / "SUMMARY.json"), "Summary differs from independent audit")
    same(evidence["primary_gate"], summary["primary_gate"], "Evidence primary gate")
    same(summary["primary_gate"], audit["primary_gate"], "Audited primary gate")
    same(evidence["secondary_gates"], summary["secondary_gates"], "Secondary gates")
    same(summary["secondary_gates"], audit["secondary_gates"], "Audited secondary gates")
    require(summary["primary_gate"]["status"] == "INFEASIBLE", "This manuscript interpretation requires the audited INFEASIBLE primary result")
    protocol = read(EXPERIMENT / "protocol.json")
    require(digest(EXPERIMENT / "protocol.json") == evidence["protocol_sha256"] == audit["protocol_sha256"], "Protocol binding changed")
    groups = {(r["budget"], r["seed"]): r for r in summary["groups"]}
    expected = {(g["budget"], g["seed"]) for g in protocol["groups"]}
    require(len(groups) == len(summary["groups"]) == 19 and set(groups) == expected, "Group roster is not the protocol roster")
    cell_map = {(c["budget"], c["seed"], c["cell_id"]): c for c in cells}
    expected_cells = {(b, s, m + "/" + w) for b, s in expected for m in MODELS for w in SCHEMES}
    require(len(cell_map) == 152 and set(cell_map) == expected_cells, "Duplicate or missing published cells")
    for key, cell in cell_map.items():
        group = groups[key[:2]]
        require(cell["execution_binding"] == binding and cell["selection_lock_sha256"] == group["selection_lock_sha256"], "Cell selection binding differs")
        for part in ["verification", "test"]:
            cls = cell["metrics"][part]["classification"]
            require(cls["classes"] == CLASSES, "Class-column order differs")
            require(cls["n"] == sum(evidence["label_ledger"][part]["class_counts"]), "Cell metric denominator differs")
    for budget in [1024, 32, 128, 512]:
        rows = [groups[k] for k in sorted(groups) if k[0] == budget]
        for part in ["verification", "test"]:
            same(policy_means(rows, part), evidence["aggregates"][str(budget)][part], "Policy aggregate")
        selected = [r for r in rows if r["selection_status"] == "SELECTED"]
        for part in ["verification", "test"]:
            same(policy_means(selected, part), evidence["matched_feasible_aggregates"][str(budget)][part], "Matched feasible aggregate")
        require(all(r["selection_status"] in {"SELECTED", "INFEASIBLE"} for r in rows), "Unknown completed selection status")
        for row in rows:
            choices = row["selection"]["choices"]
            require(set(choices) == ({"reference", "candidate", "threshold_only"} if row["selection_status"] == "SELECTED" else set()), "Incomplete or invented constrained policy roster")
            for part in ["verification", "test"]:
                require(set(row["partitions"][part]) == set(choices) | {"cv_natural_argmax", "cv_natural_benign_threshold"}, "Unexpected evaluated policy")
        decisions = evidence["policy_selections"][str(budget)]
        same(decisions, {"feasible_groups": len(selected), "required_groups": len(rows),
             "candidate_equals_threshold_only": sum(bool(r["selection"].get("candidate_equals_threshold_only")) for r in rows),
             "candidate_cells": dict(Counter(r["selection"]["choices"]["candidate"]["cell_id"] for r in selected)),
             "reference_cells": dict(Counter(r["selection"]["choices"]["reference"]["cell_id"] for r in selected))}, "Selection summary")
    external, external_audit = read(results / "EXTERNAL_RESULT.json"), read(results / "EXTERNAL_AUDIT.json")
    same(external, evidence["external"], "External evidence")
    same(external_audit, evidence["external_audit"], "External audit evidence")
    require(external["status"] == external_audit["run_status"] == "COMPLETE_LIMITED_EXTERNAL_STRESS"
            and external_audit["audit_status"] == "PASS", "External stress is not complete and audited")
    require(external_audit["artifact_hashes"]["RESULT.json"] == digest(results / "EXTERNAL_RESULT.json"), "External result changed after audit")
    require(external["protocol"]["source_execution_binding"] == binding, "External result uses another source execution")
    require(external["source_selection_status"] == groups[(1024, 20260921)]["selection_status"] == "INFEASIBLE", "External controls-only interpretation is not supported")
    require(external["source_seed"] == 20260921 and external["source_budget"] == 1024, "External source support differs")
    require(set(external["metrics"]) == {"cv_natural_argmax", "cv_natural_benign_threshold"}, "External policy roster is not controls-only")
    require(external["benign_n"] == 100000 and external["lateral_n"] == 4, "External stress scope differs from reviewed interpretation")
    preparation = read(EXPERIMENT / "dedale/STRESS_PREPARATION_RECEIPT.json")
    require(preparation["data_npz_sha256"] == external["protocol"]["data_sha256"] == external_audit["target_data_sha256"], "External prepared data binding differs")
    require(preparation["documented_lateral_executions"] == preparation["independent_campaigns"] == 1, "External independent-unit count changed")
    validation = read(validation_path)
    require(validation["status"] == "PASS" and validation["test_count"] > 0, "Software validation receipt is not passing")
    for relative, expected_hash in validation["test_files"].items():
        path = (REPO / relative).resolve()
        require(path.is_relative_to(REPO) and digest(path) == expected_hash, "Software test source changed since validation")
    diagnostics = None
    if diagnostic_path is not None:
        diagnostics = read(diagnostic_path)
        require(diagnostics["status"] == "COMPLETE_POSTHOC_DESCRIPTIVE" and diagnostics["execution_binding"] == binding,
                "Diagnostics are incomplete or use another source")
        require(diagnostics["completed_groups"] == 19 and diagnostics["completed_cells"] == 152, "Diagnostics omit registered cells")
        require(diagnostics["protocol_sha256"] == evidence["protocol_sha256"], "Diagnostics protocol changed")
        require(diagnostics["input_artifact_hashes"]["SUMMARY.json"] == digest(results / "SUMMARY.json")
                and diagnostics["source_audit_sha256"] == digest(results / "AUDIT.json"), "Diagnostics do not bind completed audited source")
        require({(g["budget"], g["seed"]) for g in diagnostics["groups"]} == expected and len(diagnostics["groups"]) == 19,
                "Diagnostics group roster differs")
        for row in diagnostics["groups"]:
            group = groups[(row["budget"], row["seed"])]
            require(row["locked_selection_status"] == group["selection_status"], "Diagnostics contradict selection locks")
    return evidence, summary, cells, audit, external, validation, diagnostics, protocol


def extract(text, begin, end):
    require(text.count(begin) == text.count(end) == 1, "Draft section boundary missing or repeated")
    return text.split(begin, 1)[1].split(end, 1)[0]


def replace_section(text, begin, end, replacement):
    require(text.count(begin) == text.count(end) == 1, "Draft subsection boundary missing or repeated")
    return text.split(begin, 1)[0] + replacement.rstrip() + "\n\n" + end + text.split(end, 1)[1]


def operating_table(aggregates):
    return table(["Policy", "Seeds", "Mean benign FP", "Benign FPR", "Mean lateral detected", "Lateral recall"],
        [[NAMES[name], m["pairs"], number(m["fp"], 1), pct(m["benign_fpr"]), number(m["stage_detected"]["LateralMovement"], 1),
          pct(m["stage_recall"]["LateralMovement"])] for name, m in aggregates.items()])


def binary_table(aggregates):
    return table(["Policy", "Seeds", "Attack precision", "Attack recall", "Binary attack F1", "All-flow alert rate"],
        [[NAMES[name], m["pairs"], pct(m["attack_precision"]), pct(m["attack_recall"]), number(m["attack_f1"]), pct(m["alert_fraction"])]
         for name, m in aggregates.items()])


def ranking_table(aggregates):
    return table(["Policy", "Seeds", "Binary attack ROC-AUC", "Binary attack AP"],
        [[NAMES[name], m["pairs"], number(m["roc_auc"]), number(m["average_precision"])] for name, m in aggregates.items()])


def stage_table(aggregates):
    return table(["Policy (seed count)", *[SHORT[s] for s in STAGES]],
        [[f"{NAMES[name]} (n={m['pairs']})", *[pct(m["stage_recall"][stage]) for stage in STAGES]] for name, m in aggregates.items()])


def seed_sets(aggregates):
    return "\n".join(f"- {NAMES[name]}: seeds " + ", ".join(map(str, m["seeds"])) + "." for name, m in aggregates.items())


def feasible_tradeoff(e):
    """Describe the matched feasible subset without replacing the primary gate."""
    means = e["matched_feasible_aggregates"]["1024"]["verification"]
    if "candidate" not in means:
        return "No primary seed supplied a selected candidate, so no matched candidate/reference verification tradeoff was estimable."
    candidate, reference = means["candidate"], means["reference"]
    require(candidate["seeds"] == reference["seeds"], "Tradeoff requires matched feasible seed sets")
    if reference["benign_fpr"] > 0:
        reduction = 100 * (1 - candidate["benign_fpr"] / reference["benign_fpr"])
        false_alarms = (f"false alarms fell {reduction:.1f}% relative to the reference" if reduction >= 0
                       else f"false alarms increased {-reduction:.1f}% relative to the reference")
    else:
        false_alarms = "relative false-alarm reduction was undefined because the reference false-positive rate was zero"
    reference_recall = reference["stage_recall"]["LateralMovement"]
    candidate_recall = candidate["stage_recall"]["LateralMovement"]
    change = "fell" if candidate_recall < reference_recall else "rose" if candidate_recall > reference_recall else "remained unchanged"
    movement = (f"lateral detection {change} from {pct(reference_recall, 1)} to {pct(candidate_recall, 1)}" if change != "remained unchanged"
                else f"lateral detection remained {pct(candidate_recall, 1)}")
    loss = 100 * (reference_recall - candidate_recall)
    requirements = []
    if candidate_recall < .9:
        requirements.append("candidate recall was below the 90% verification floor")
    if loss >= 3:
        requirements.append(f"the {loss:.2f}-percentage-point recall loss did not satisfy the less-than-three-point requirement")
    text = f"Among the {candidate['pairs']} seeds with a selected policy, {false_alarms}, while {movement}."
    if requirements:
        text += " In that subset, " + ", and ".join(requirements) + "."
    return text + " This is a descriptive result conditional on feasible selection; it does not replace or redefine the failed all-ten-seed primary requirement."


def seed_table(rows, partition="verification"):
    def count(row, policy):
        m = row["partitions"][partition].get(policy)
        if m is None:
            return "Not selected"
        return f"{m['fp']:,} / {m['per_stage']['LateralMovement']['detected']}"
    return table(["Seed", "Selection status", "Reference FP / lateral TP", "Candidate FP / lateral TP", "Same as threshold-only?"],
        [[r["seed"], r["selection_status"], count(r, "reference"), count(r, "candidate"),
          ("Yes" if r["selection"]["candidate_equals_threshold_only"] else "No") if r["selection_status"] == "SELECTED" else "No candidate"] for r in rows])


def classification_rows(cells, partition="verification"):
    rows = []
    for model in MODELS:
        for scheme in SCHEMES:
            name = model + "/" + scheme
            subset = [c["metrics"][partition]["classification"] for c in cells if c["budget"] == 1024 and c["cell_id"] == name]
            require(len(subset) == 10, "Classification table requires all ten registered fitting seeds")
            rows.append([name, 10, number(fmean(x["macro_f1"] for x in subset)), number(fmean(x["roc_auc_ovr_macro"] for x in subset)),
                         number(fmean(x["average_precision_ovr_macro"] for x in subset)), pct(fmean(x["per_stage"]["LateralMovement"]["recall"] for x in subset))])
    return rows


def chapter_four(e, summary, cells, diagnostics, link):
    primary = sorted((g for g in summary["groups"] if g["budget"] == 1024), key=lambda x: x["seed"])
    feasible = [r for r in primary if r["selection_status"] == "SELECTED"]
    failures = [str(r["seed"]) for r in primary if r["selection_status"] == "INFEASIBLE"]
    means = e["aggregates"]["1024"]["verification"]
    lines = ["# Chapter 4. Results", "", "## 4.1 Completion, audit, and primary decision", "",
        f"All **{summary['completed_cells']} final model cells and {summary['completed_groups']} registered groups completed**. The independent source consistency audit passed. "
        f"The primary scientific decision was **{summary['primary_gate']['status']}**: only {len(feasible)} of ten primary fitting seeds produced a feasible reference policy. "
        "The all-ten-feasible prerequisite was therefore unmet. A passing software or artifact audit is not a passing scientific hypothesis.", "",
        "Here, independent audit means a separately implemented software and calculation check. It was not human review, external peer review, independent relabeling, or a model refit.", "",
        "Infeasible primary seeds were: **" + ", ".join(failures) + "**. In each, no threshold on any of the eight final CV-selected family/weighting detectors simultaneously met the selection requirements of at least 90% lateral recall and at most 1% benign FPR. "
        "This statement does not cover discarded CV hyperparameter models, other learning algorithms, or every possible detector.", "",
        "## 4.2 Every primary fitting seed", "",
        "Counts below are on the same verification partition: 14,965 benign flows and 72 lateral flows. Unselected policies have no verification result; their values are not zero.", "",
        seed_table(primary), "", "![Each of ten primary fitting seeds on the same exposed verification partition: 14,965 unique benign feature groups and 72 lateral groups. Natural argmax and source-normal threshold controls appear for every seed; a missing candidate diamond means source selection was infeasible. Dashed lines mark 1% benign FPR and 90% lateral recall. No confidence intervals are implied.](figures/primary_seeds.png)", "",
        "## 4.3 Operating outcomes and the feasible-subset boundary", "",
        "The conventional controls were evaluated in all ten seeds. Reference, candidate, and threshold-only rows include only seeds where a reference existed. "
        "Their denominators are explicit below. A favorable conditional mean cannot replace the all-ten-seed primary endpoint, and rows with different seed counts are not matched comparisons.", "",
        operating_table(means), "", seed_sets(means), "", binary_table(means), "", ranking_table(means), "",
        "Binary attack F1 treats any non-normal label as an attack. Its ROC-AUC and average precision use the continuous score `1 - pNormal`, independently of the displayed threshold. "
        "These differ from six-class macro-F1 and macro one-versus-rest ranking scores. Mean precision is the mean of seed precisions, not a ratio of mean counts. Decimal counts represent repeated-fit means, not fractional observations.", ""]
    if feasible:
        lines += [f"### Matched description restricted to the {len(feasible)} feasible seeds", "",
                  "All five policies in the following table use exactly the same feasible seed subset. This conditional comparison remains descriptive and cannot demonstrate reliability over the full registered support roster.", "",
                  "Matched seed roster: " + ", ".join(str(r["seed"]) for r in feasible) + ".", "",
                  operating_table(e["matched_feasible_aggregates"]["1024"]["verification"]), "", feasible_tradeoff(e), ""]
    lines += ["## 4.4 Other attack stages", "",
        "Entries count any alert on a true stage-labeled flow, rather than an exact-stage label. Verification denominators are exfiltration 53, initial compromise 7, lateral movement 72, pivoting 212, and reconnaissance 83. "
        "The initial-compromise count is especially small. No unreported stage is presumed protected.", "", stage_table(means), "",
        "## 4.5 Threshold-only ablation and selected detectors", ""]
    equal = e["policy_selections"]["1024"]["candidate_equals_threshold_only"]
    lines += [f"Among {len(feasible)} feasible primary seeds, the candidate was identical to the threshold-only ablation in **{equal}**. "
        "Identity means the saved policy choice, threshold, and selection counts match. This is not an extra success criterion, and a different detector does not itself establish an improvement.", ""]
    if feasible:
        ablation_rows = []
        for row in feasible:
            choices = row["selection"]["choices"]; m = row["partitions"]["verification"]
            ablation_rows.append([row["seed"], choices["reference"]["cell_id"], choices["candidate"]["cell_id"],
                "Yes" if row["selection"]["candidate_equals_threshold_only"] else "No",
                m["candidate"]["fp"] - m["threshold_only"]["fp"],
                m["candidate"]["per_stage"]["LateralMovement"]["detected"] - m["threshold_only"]["per_stage"]["LateralMovement"]["detected"]])
        lines += [table(["Seed", "Reference detector", "Candidate detector", "Identical ablation?", "Candidate minus ablation FP", "Candidate minus ablation lateral TP"], ablation_rows), ""]
    lines += ["Whenever a reference existed, it was itself an eligible candidate and threshold-only option. Therefore selection FPR satisfied candidate ≤ threshold-only ≤ reference by construction. "
        "A selection-side reduction is an optimization consequence; the locked verification counts above determine whether it persisted. No policy was changed after observing those counts.", "",
        "## 4.6 Secondary normal-label budgets", "",
        table(["Normal fitting labels", "Total fitting labels", "Feasible / registered seeds", "Declared secondary decision"],
            [[b, b + 160, f"{e['policy_selections'][str(b)]['feasible_groups']}/3", summary["secondary_gates"][str(b)]["status"]] for b in [32, 128, 512]]), "",
        "![Argmax classifier tradeoffs at normal fitting budgets 32, 128, 512, and 1,024, always averaging the same first three seeds. Separate XGBoost and LightGBM panels show natural, balanced, lateral2, and lateral4 weighting; larger circles mark budget 32, squares mark 1,024, and the connected intermediate points mark 128 and 512 in order. All points use the same exposed verification sample, with 14,965 unique benign groups and 72 lateral groups per seed. These are individual classifiers, not selected constrained candidates; no confidence intervals are shown.](figures/budget_tradeoff.png)", ""]
    for b in [32, 128, 512]:
        rows = sorted((g for g in summary["groups"] if g["budget"] == b), key=lambda x: x["seed"])
        lines += [f"### {b} normal fitting examples", "", seed_table(rows), "",
                  operating_table(e["aggregates"][str(b)]["verification"]), "", seed_sets(e["aggregates"][str(b)]["verification"]), ""]
    lines += ["These budgets used only the first three registered seeds and nested supports. Their screens are secondary development descriptions; no favorable budget was promoted to replace the failed primary requirement.", "",
        "## 4.7 Classification of all six classes", "",
        "The following means include all ten primary fits for every family/weighting cell, regardless of policy feasibility. They describe each classifier's argmax output. "
        "Macro-F1 includes normal traffic; a larger value is not proof that the alert policy meets the lateral constraint. Appendix E reports every class separately.", "",
        table(["Model / weights", "Fits", "Six-class macro-F1", "Macro OvR AUC", "Macro OvR AP", "Exact lateral-stage recall"], classification_rows(cells)), "",
        "## 4.8 Previously exposed original test", "",
        "The same locked choices were also evaluated on the original 30,787-row development test. It includes 29,929 benign and 144 lateral flows. "
        "These descriptive outcomes neither select thresholds nor rescue the verification gate, and this split is not the author's independent test artifact.", "",
        operating_table(e["aggregates"]["1024"]["test"]), "", stage_table(e["aggregates"]["1024"]["test"]), ""]
    if diagnostics is not None:
        lines += ["## 4.9 Posthoc selection-frontier diagnostics", "",
            "After completing the frozen experiment, saved selection probabilities were examined to describe the attainable tradeoff within the eight final fitted detectors per seed. "
            "All tied score cutoffs were retained. No new policy, threshold, model fit, or success gate resulted. These are selection-data descriptions, not held-out performance estimates.", ""]
        rows = []
        for r in diagnostics["groups"]:
            if r["budget"] != 1024:
                continue
            f = r["frontiers"]["all_fit_library"]
            rows.append([r["seed"], r["locked_selection_status"],
                pct(f["maximum_lateral_recall_at_fpr_at_most_1pct"]["lateral_recall"]),
                pct(f["minimum_fpr_for_lateral_recall_at_least_90pct"]["benign_fpr"])])
        lines += [table(["Seed", "Locked status", "Maximum selection lateral recall at ≤1% FPR", "Minimum selection FPR at ≥90% lateral recall"], rows), "",
                  "The limits apply only to the saved CV-selected model/weighting cells, not to every hyperparameter configuration considered during fitting or to all possible solutions.", ""]
    else:
        lines += ["## 4.9 Diagnostic scope", "", "No optional posthoc frontier artifact was incorporated in this manuscript. The original locked outcomes and gate remain the complete basis of the primary conclusion.", ""]
    ext = e["external"]
    lines += ["## 4.10 DEDALE external stress: conventional controls only", "",
        f"The fixed source seed was {ext['source_seed']}, at {ext['source_budget']} normal fitting examples. Its source selection was **INFEASIBLE**. "
        "Accordingly, no candidate, reference, or threshold-only candidate was available for external testing. The prespecified fallback was to evaluate the two already locked natural-tree controls without target fitting, calibration, or threshold selection.", "",
        "The target consisted of 100,000 deterministically sampled unique benign feature groups and all four lateral groups from one documented PrintNightmare execution on DEDALE day 17. "
        "All four lateral groups came from the same execution; they are not four independent attacks. Other attack stages were excluded by the frozen stress scope.", ""]
    rows = []
    for name in ["cv_natural_argmax", "cv_natural_benign_threshold"]:
        m = ext["metrics"][name]; lm = m["per_stage"]["LateralMovement"]
        rows.append([NAMES[name], f"{m['fp']:,}/{m['benign_n']:,}", pct(m["benign_fpr"]), f"{lm['detected']}/{lm['n']}", pct(lm["recall"]), number(m["attack_f1"] )])
    lines += [table(["Source-locked control", "Benign false alerts", "Benign FPR", "Lateral detected", "Lateral recall", "Sample attack F1"], rows), "",
        table(["Source-locked control", "Sample attack precision", "Binary ROC-AUC", "Sample average precision"],
              [[NAMES[name], pct(m["attack_precision"]), number(m["roc_auc"]), number(m["average_precision"])] for name, m in ext["metrics"].items()]), "",
        "![DEDALE controls-only external stress for fixed source seed 20260921: false benign alerts among 100,000 sampled unique normal groups and lateral detections among four unique lateral flows. All four lateral flows belong to one execution. The source candidate was infeasible and is absent; no confidence intervals or incident-level recall estimates are shown.](figures/external_stress.png)", "",
        "The source-normal 1% label names its source calibration rule; it is not a 1% target guarantee. In a multiclass model it also need not be a stricter decision rule than argmax. "
        "The larger alert count on DEDALE must therefore be reported rather than described as successful suppression. Precision, F1, and average precision describe this deliberately selected sample; they are not deployment-prevalence estimates. "
        "Detecting one of four flows does not mean the entire incident was missed; a single flow could alert on that execution. Even four-of-four detections cannot establish protection across independent executions or a three-point noninferiority margin.", "",
        "The external consistency audit passed. That audit reconstructs saved counts and provenance; it does not independently replay the attack, adjudicate the author's labels, or prove matching feature-extractor settings. "
        "This completed stress test supplies no external validation of a constrained candidate, because no such candidate was selected for the fixed source seed.", "",
        f"Complete numerical aggregates and provenance are available in [EVIDENCE.json]({link('EVIDENCE.json')}), [SUMMARY.json]({link('SUMMARY.json')}), "
        f"[CELL_METRICS.json]({link('CELL_METRICS.json')}), [source audit]({link('AUDIT.json')}), and [external audit]({link('EXTERNAL_AUDIT.json')}).", ""]
    return "\n".join(lines)


def chapter_five(e, summary):
    decisions = e["policy_selections"]["1024"]
    n, identical = decisions["feasible_groups"], decisions["candidate_equals_threshold_only"]
    natural = e["external"]["metrics"]["cv_natural_argmax"]
    threshold = e["external"]["metrics"]["cv_natural_benign_threshold"]
    return f"""# Chapter 5. Discussion and conclusion

## 5.1 What the completed experiment established

The declared protection procedure did not meet its primary development requirement. Only {n} of ten primary seeds produced a feasible reference from the eight final CV-selected detectors, so the all-ten-seed prerequisite failed. This is a completed **negative feasibility result for the tested procedure**, not an unfinished model run and not an assertion that lateral-protection research is impossible. The artifact and metric audits passed, which supports the consistency of that recorded result.

The boundary matters: fitting CV selected one hyperparameter configuration for each of two families and four weighting schemes. Selection examined thresholds on those eight detectors. It did not optimize the downstream constraint over every discarded configuration or every possible algorithm. Macro-F1-selected hyperparameters may not produce the strongest constrained frontier. A future objective-aligned search is a separate experiment, with equal search access for its controls and a new untouched evaluation, not a retroactive repair of this result.

## 5.2 Why conditional means do not overturn infeasibility

The feasible subset answers what happened when this library supplied a qualifying source reference. It does not answer whether the process reliably qualifies across the registered supports. Reporting only successful selections would discard the very failures the primary rule was designed to retain. The conventional controls' ten-seed means and the constrained policies' {n}-seed means also have different fitting-support denominators; the matched subset table limits this comparison explicitly.

{feasible_tradeoff(e)}

Within selection data, candidate FPR could not exceed the threshold-only value, which could not exceed reference FPR, because the reference itself remained an available option. Those inequalities are consequences of selection. Only the locked verification results can show persistence outside the optimizing partition, and even those are exposed-source development evidence.

## 5.3 What the ablation and other stages contribute

The candidate was identical to the threshold-only policy in {identical} of {n} feasible primary seeds. The recorded count and paired verification differences determine how much the broader detector search added in those cases. A different selected model is not sufficient evidence of benefit. Likewise, a higher six-class macro-F1 or binary ROC-AUC cannot compensate for a failed lateral requirement at the operating threshold.

Stage-specific tables reveal whether a quieter policy trades away initial compromise, exfiltration, pivoting, or reconnaissance. These outcomes were retained regardless of feasibility. With seven initial-compromise verification flows and 72 lateral flows, numerical changes can reflect very few observations; the study supplies neither an all-stage safety guarantee nor a population confidence certificate.

## 5.4 What the external stress means

The fixed source seed was infeasible, so DEDALE tested conventional controls only. The natural argmax control generated {natural['fp']:,} false alerts among {natural['benign_n']:,} sampled benign groups and detected {natural['per_stage']['LateralMovement']['detected']} of four lateral groups. The source-normal threshold generated {threshold['fp']:,} false alerts and detected {threshold['per_stage']['LateralMovement']['detected']} of four. These results expose the operating-cost tradeoff under source-to-target shift. They do not demonstrate successful external protection by the unavailable candidate.

The four lateral groups belong to one documented execution. Detecting one of four flows is not evidence that the whole incident was missed, just as detecting four does not represent four independent successful attack detections. The author labels used scheduled action times with a three-minute margin, host pairs, and ports; these were not four independent manual adjudications, and the metric audit did not independently relabel them. Sampling 100,000 benign feature groups changes the evaluated prevalence, and deduplication changes the unit from raw flows to unique predictor rows. FPR and raw lateral counts remain useful descriptions, while precision/F1 cannot be extrapolated to a live stream. The source extractor revision also remains unqualified, so the stress includes possible extraction differences alongside network and attack differences.

## 5.5 Novelty and contribution

The literature already supplies benign-support expansion, class weighting, constrained error objectives, and validation-selected thresholds. Singhal and Kumar (2026) directly combine cost-sensitive training with a miss-constrained operating point in cybersecurity. Tian and Feng (2025), Tong et al. (2018), and Angelopoulos et al. (2025) provide established error-control foundations under their stated assumptions. This study neither invents those components nor establishes a new proven algorithm.

Its completed contribution is a bounded empirical account: a motivating normal-data tradeoff was turned into a matched-support, locked-selection test; infeasible supports were retained; threshold-only controls limited attribution; labels and software evidence were accounted for; and a recent external dataset was qualified for the narrower stress it could support. The result identifies a failure boundary for this concrete procedure. Whether that is sufficient for a particular institution's praxis requirements is an academic assessment, not a claim established by an automated experiment.

## 5.6 Threats to validity

**Prior exposure and adaptation.** The source question arose after previous SCVIC results were examined. A later source freeze prevents new outcome-driven changes to this run, but does not convert those data into untouched confirmation. Both halves of the old calibration partition and the original descriptive test retain this history.

**Dependence and sample size.** Exact-feature deduplication removes one form of overlap, not incident, host, temporal, or near-duplicate dependence. Ten fitting seeds reuse the same verification observations. They describe sensitivity to fitting support; they do not provide ten independent deployments or justify a narrow incident-level confidence interval.

**Finite methods and budget.** Only two tree families, four weighting schemes, fixed grids, and scarce fitting attack supports were tested. More normal examples change coverage, sample size, relative weights, absolute summed loss weight, and possibly the selected hyperparameters. Balanced mean-one weighting fixes relative class mass, not every other statistical or regularization effect. The study does not isolate a unique causal mechanism.

**Information and measurement.** Fitting supports contain 160 attack labels per fit, but selection, verification, test labeling, and the larger known-label pool supply additional information. An alert on a stage-labeled flow is not a completed analyst investigation, actor attribution, or proof of early warning. The study measured no analyst time, production outcome, missing-log robustness, or automatic suppression safety.

**Comparator and literature limits.** The experiment evaluated empirical weighted-tree and threshold policies, not a fully instantiated confidence-controlled NP algorithm. The bounded review of the closest Sysmon application used its abstract and metadata; it did not establish omissions in its full methods. These limits rule out broad novelty or certification claims.

## 5.7 Practical next study

The next defensible study needs new attack executions with legitimate remote-administration background, an agreed operational loss margin, and controls allowed the same search and label information. Appendix D specifies a concrete prospective design. The present results do not justify selecting a better-looking source seed, relaxing the 90%/1% requirements, or retuning on DEDALE and presenting the revision as confirmation.

Until a revised method is independently evaluated, an organization should treat this work as research evidence for shadow evaluation. No production detector was certified or authorized for suppression. Lower alert volume remains an incomplete success measure when the hidden cost is missed lateral activity.

## 5.8 Final conclusion

This completed study found that the declared tree-weighting and constrained-threshold procedure was not reliably feasible across the registered source fitting supports. The all-ten-seed development requirement failed, and the fixed external seed supplied no constrained candidate to test. Conventional controls on DEDALE showed a substantial false-alarm/detection tradeoff on one lateral execution. The evidence supports a reproducible negative feasibility finding and a focused next research question. It does **not** establish a successful lateral-protection solution, a new algorithm, or deployment readiness.
"""


def appendices(e, cells, validation, results, diagnostics, diagnostic_path, validation_path, link):
    ledger = e["label_ledger"]
    runtime = e.get("fit_tuning_elapsed_seconds_sum")
    require(runtime is not None and math.isfinite(runtime), "Elapsed fitting-time aggregate missing")
    lines = ["# Appendix A. Software and execution accounting", "",
        f"The recorded validation receipt reports **{validation['test_count']} passing software tests** in {validation['elapsed_seconds']:.3f} seconds, recorded at {validation['recorded_utc']}. "
        "These synthetic and artifact-tampering checks test software behavior; they do not demonstrate model effectiveness, independent attack truth, or a human audit. "
        "The assembler verifies that the referenced test-source hashes still match the receipt.", "",
        table(["Package", "Recorded version"], [[name, version] for name, version in sorted(e["software_versions"].items())]), "",
        f"The sum of per-cell fit-and-tuning elapsed times was **{runtime:,.1f} seconds**. The two workers could overlap, so this is neither CPU-core seconds nor the total batch wall time. "
        "Inference latency was not benchmarked. Foundation packages present in the environment do not imply that a foundation model was fitted in this tree experiment.", "",
        "# Appendix B. Full label ledger", "",
        table(["Normal fitting budget", "Attack fitting labels per fit", "Total fitting labels per fit"],
              [[b, ledger["per_fit_attack"], ledger["per_fit_total"][str(b)]] for b in [32, 128, 512, 1024]]), "",
        table(["Partition", "All labels", "Normal labels", "Attack labels", "Lateral labels"],
              [[part.capitalize(), sum(ledger[part]["class_counts"]), ledger[part]["class_counts"][3],
                sum(ledger[part]["class_counts"]) - ledger[part]["class_counts"][3], ledger[part]["class_counts"][2]]
               for part in ["selection", "verification", "test"]]), "",
        f"There were {ledger['unique_fitting_rows_across_registered_groups']:,} unique fitting rows across the registered groups. "
        f"The available labeled fit pool contained {ledger['available_labeled_fit_pool_rows']:,} rows, within {ledger['total_prepared_labeled_rows']:,} prepared labeled rows. "
        "Supports overlap across seeds and budgets; adding per-fit counts would overstate unique labels. Conversely, reporting only one support's count would understate label access used for stratification, selection, and assessment. No low acquisition-cost claim follows from the allocated fitting budget.", "",
        "# Appendix C. Evidence and provenance", "",
        table(["Binding", "Value"], [["Source freeze Git revision", e["source_freeze_git_head"]],
              ["Source execution binding", e["execution_binding"]], ["Source protocol SHA-256", e["protocol_sha256"]],
              ["Software validation SHA-256", digest(validation_path)], ["Optional frontier diagnostics SHA-256", digest(diagnostic_path) if diagnostic_path else "Not included"]]), "",
        table(["Published artifact", "SHA-256"], [[f"[{name}]({link(name)})", digest(results / name)] for name in
              ["EVIDENCE.json", "SUMMARY.json", "CELL_METRICS.json", "AUDIT.json", "EXTERNAL_RESULT.json", "EXTERNAL_AUDIT.json", "PUBLICATION.json"]]), "",
        "The source audit independently reconstructs support/partition rosters, fold-weight and imputer metadata, threshold/tie choices, saved prediction metrics, and exact decision arithmetic. "
        "It does not retrain the models or recompute unsaved inner-fold predictions. Receipt order documents the execution path, not independent human blindness. "
        "The external audit checks saved target predictions and source/target bindings; it does not replay the attack or rebuild author labels from raw evidence. "
        "The optional posthoc frontier description, when included, binds the complete source audit and does not modify the frozen experiment.", "",
        "# Appendix D. Concrete prospective confirmation design", "",
        "This appendix specifies future work; none of its new data collections or confirmation claims was completed by this experiment.", "",
        "## D.1 Independent collection and decision units", "",
        "Generate or obtain separate lateral-movement executions with contemporaneous legitimate administration. Predeclare hosts, credentials, remote-management tools, collection settings, and execution/campaign identifiers. "
        "Keep repeated interfaces and correlated flows from the same execution together. Separate whole execution/campaign groups into fitting, selection, one locked verification, and untouched confirmation blocks; reserve a later period or different network for confirmation. "
        "A benchmark containing one campaign cannot establish a many-incident claim merely by slicing its flows.", "",
        "## D.2 Fair comparisons and a single locked choice", "",
        "Use the same attack identities, benign-label cap, candidate-search access, and permitted selection/calibration labels for all comparators. Include a strong natural tree, balanced and lateral-weighted trees, "
        "a threshold-only control, and an established constrained/NP procedure with its actual assumptions and implementation. If the proposed rule is equivalent to a comparator, collapse the duplicate arm. "
        "A new search that tunes hyperparameters for the downstream constrained frontier must be declared before new outcomes, with identical access for controls. Do not reuse the present exposed verification data as independent confirmation.", "",
        "## D.3 Prespecified requirements and adequate evidence", "",
        "For each independent incident/campaign with suitable denominators, calculate lateral detection and normal FPR; compare candidate/reference on the same eligible groups and report equal-group means plus pooled flow counts. "
        "Before confirmation, lock the grouping, interval construction, handling of absent-stage groups, minimum group/sample adequacy, and multiplicity procedure. "
        "A future joint criterion may require a one-sided 95% upper bound for `F_candidate - 0.8 × F_reference` below zero, a lower bound for `R_candidate - R_reference` above `-0.03`, "
        "a lower bound for candidate lateral recall at least 0.90, and an upper bound for candidate FPR at most 0.01. These remain proposed engineering requirements, not clinical or industry standards. "
        "Plan sample size with realistic paired discordance and clustering before collecting confirmation outcomes. If independent groups cannot support those bounds, report insufficient confirmation evidence rather than treating individual flows or seeds as independent.", "",
        "## D.4 Failure handling and operational evaluation", "",
        "Accept or reject the single locked choice once. Do not search for a fallback after viewing confirmation labels. Report every other stage and every infeasible support, charge all known-normal and attack labels, "
        "and distinguish source-only transfer from target-assisted calibration. Only after independent validation should shadow evaluation measure incident aggregation, analyst burden, and missed activity under a prospectively defined workflow. "
        "Any production decision requires evidence and review specific to that environment; the current experiment supplies no automatic suppression authorization.", "",
        "# Appendix E. Exact-stage classification for every primary final cell", "",
        "All entries below average ten argmax classifiers on the common verification partition. Precision/recall/F1 concern the named exact class; AUC and AP are one-versus-rest. "
        "They are different from the alert-policy detection metrics in Chapter 4. All weighting cells remain visible, including those that did not yield a feasible policy. Confusion matrices are retained in the linked CELL_METRICS artifact.", ""]
    for model in MODELS:
        for scheme in SCHEMES:
            name = model + "/" + scheme
            subset = [c["metrics"]["verification"]["classification"] for c in cells if c["budget"] == 1024 and c["cell_id"] == name]
            rows = []
            for stage in CLASSES:
                m = [s["per_stage"][stage] for s in subset]
                rows.append([stage, pct(fmean(x["precision"] for x in m)), pct(fmean(x["recall"] for x in m)),
                             number(fmean(x["f1"] for x in m)), number(fmean(x["roc_auc_ovr"] for x in m)), number(fmean(x["average_precision_ovr"] for x in m))])
            lines += ["## " + name, "", table(["Class", "Exact precision", "Exact recall", "Exact F1", "OvR AUC", "OvR AP"], rows), ""]
    return "\n".join(lines)


def assemble(results, output, draft=None, diagnostics=None, validation=None):
    results, output = Path(results).resolve(), Path(output).resolve()
    draft = Path(draft or HERE / "DRAFT_EMPIRICAL_PRAXIS.md").resolve()
    validation = Path(validation or EXPERIMENT / "SOFTWARE_VALIDATION.json").resolve()
    require(output.parent == HERE and output != draft and output.suffix == ".md", "Write a separate manuscript Markdown file in the paper directory")
    require(not output.exists(), "Preserve existing manuscript; use a new output filename for a revised assembly")
    if diagnostics is None and (results / "DIAGNOSTICS.json").is_file():
        diagnostics = results / "DIAGNOSTICS.json"
    if diagnostics is not None:
        diagnostics = Path(diagnostics).resolve()
    for figure in ["budget_tradeoff.png", "primary_seeds.png", "external_stress.png"]:
        require((output.parent / "figures" / figure).is_file(), "Generate required figure before assembly: " + figure)
    e, s, cells, audit, ext, software, diag, protocol = validate_package(results, diagnostics, validation)
    original = draft.read_text(encoding="utf-8")
    link = lambda name: Path(os.path.relpath(results / name, output.parent)).as_posix()
    count = e["policy_selections"]["1024"]["feasible_groups"]
    argmax, threshold = ext["metrics"]["cv_natural_argmax"], ext["metrics"]["cv_natural_benign_threshold"]
    abstract = f"""# Reducing False Alarms While Preserving Lateral-Movement Detection

## A negative feasibility study of training emphasis and alert selection with scarce attack fitting labels

**Completed empirical manuscript.** Evidence publication: {e['created_utc']}. Source scientific decision: **INFEASIBLE**. Source and external consistency audits: **PASS**.

**Study boundary:** This is a completed negative feasibility study on previously examined source data, with a controls-only external stress test. It establishes neither a successful new protection algorithm nor independent confirmation of deployment reliability.

## Abstract

Reducing false alarms can hide attack behavior that resembles normal activity. This praxis evaluated whether conventional tree weighting and constrained threshold selection could reduce false alarms while limiting missed lateral movement under a fixed attack fitting budget. The source study completed 152 final models across 19 support groups. Its primary condition used 1,024 benign and 160 attack fitting examples, two boosted-tree families, four weighting schemes, and ten fitting seeds. Fitting-only cross-validation selected each cell's hyperparameters; separate source partitions selected and verified locked policies. The primary decision was **INFEASIBLE**: only {count} of ten primary seeds supplied a detector/threshold pair satisfying the selection requirements of at least 90% lateral recall and no more than 1% benign false positives. Conditional means from feasible seeds could not satisfy the all-ten prerequisite. A fixed-seed DEDALE check therefore evaluated conventional controls only: argmax generated {argmax['fp']:,} false alerts among 100,000 sampled benign groups and detected {argmax['per_stage']['LateralMovement']['detected']} of four lateral groups; a source-normal threshold generated {threshold['fp']:,} false alerts and detected {threshold['per_stage']['LateralMovement']['detected']} of four. All lateral groups came from one execution. Independent consistency audits passed, but the previously exposed source data and one target execution do not establish incident-level generalization. The contribution is a reproducible failure boundary for a specified applied procedure, not a novel proven algorithm or production-ready suppression method.

**Keywords:** lateral movement; intrusion detection; false positives; class weighting; constrained selection; negative feasibility; network flows

## Executive explanation

We completed the test. The proposed selection process did **not** reliably find a detector that was both quiet enough and sensitive enough to lateral movement across all ten planned fitting supports. Some supports could supply a qualifying policy, but the primary rule required all ten. We retained the failures instead of averaging them away.

{feasible_tradeoff(e)}

The new external data did not supply a successful candidate test either. The fixed source seed had no qualifying candidate, so only its conventional controls were tested. The argmax control alerted on one of four lateral flows; the source-normal threshold alerted on all four but generated many false alarms. Those four flows came from one attack execution, not four independent attacks. Detecting just one flow could still alert on that execution, so these counts are not incident-level recall.

The software and evidence checks passed. The scientific conclusion is narrower and unfavorable: this particular weighted-tree and threshold-selection procedure did not establish reliable protection under the declared requirements. A better overall score, an easier secondary budget, or a selected successful seed would not change that conclusion. The next useful study needs new independent executions, strong equally informed controls, and a new protocol before those outcomes are examined.

"""
    chapter1 = "# Chapter 1. Introduction and problem definition" + extract(original, "# Chapter 1. Introduction and problem definition", "# Chapter 2. Literature and conceptual basis")
    chapter1 = chapter1.replace("The next experiment asks", "The present experiment tested").replace("The purpose is to determine", "The purpose was to determine")
    chapter1 = chapter1.replace("Two other findings constrain the present proposal.", "Two other findings constrain the present study.")
    chapter1 = chapter1.replace("they are not ten independently collected datasets.", "they are not ten independently collected datasets (Praxis experiment repository, 2026).")
    chapter1 = chapter1.replace("**Thesis to evaluate:**", "**Thesis evaluated:**").replace("The primary development hypothesis is joint:", "The primary development hypothesis was joint:")
    chapter1 = chapter1.replace("The threshold-only ablation tests", "The threshold-only ablation tested")
    chapter1 = chapter1.split("## 1.6 Scope and potential contribution", 1)[0] + """## 1.6 Scope and completed contribution

The completed empirical scope was numerical flow classification and alerting with existing tree methods. The work reports the tested procedure's feasibility boundary, stage tradeoffs, label costs, threshold ablation, and a qualified controls-only external stress. It does not establish actor attribution, early warning, missing-log resilience, measured analyst savings, a successful new algorithm, or independently confirmed protection. Chapter 4 retains the negative and infeasible outcomes; Chapter 5 explains their limits.

"""
    chapter2 = "# Chapter 2. Literature and conceptual basis" + extract(original, "# Chapter 2. Literature and conceptual basis", "# Chapter 3. Research methodology")
    chapter2 = chapter2.replace("its subscription-limited full methods were not fully available", "its full methods were not inspected in this bounded review")
    chapter2 = chapter2.replace("Access limits affect the claims that can be made.", "The scope of the review limits the claims that can be made.")
    chapter2 = chapter2.replace("DEDALE is a candidate for a separately qualified evaluation, not a result in this draft.", "DEDALE was qualified for the limited controls-only stress reported in Chapter 4.")
    chapter2 = chapter2.replace("Its published temporal setup and label semantics must govern a new protocol; a shared file format does not establish compatible predictors or reliable label joins.", "Its author-provided labeled CICFlowMeter tables supported a documented feature adapter; the resulting four lateral rows remained one execution, and extractor equivalence was not established.")
    chapter3 = "# Chapter 3. Research methodology" + extract(original, "# Chapter 3. Research methodology", "# Chapter 4. Results — pending completed execution and independent audit")
    chapter3 = replace_section(chapter3, "## 3.1 Design and execution status", "## 3.2 Data provenance and preparation", f"""## 3.1 Design and completed execution

The governing [protocol](../protocol.json) and [executable specification](../specification.py) were frozen before the new model fits. The completed study remained `exposed_source_development`. All 19 registered groups completed: ten primary groups with 1,024 normal fitting examples, plus three seeds at each of three smaller normal budgets. Two families and four weighting schemes produced 152 final models after 4,788 inner-CV fits. The source freeze revision was `{e['source_freeze_git_head']}`. The independent source and external audits passed; their scientific outcomes are reported separately in Chapter 4.
""")
    chapter3 = chapter3.replace("The old fit pool supplies fitting examples.", "The old fit pool supplied fitting examples.")
    chapter3 = chapter3.replace("An independent audit must recompute the rosters, policy choices, and metrics before results enter the manuscript.", "An independent audit recomputed the rosters, policy choices, and saved metrics before results entered the manuscript.")
    chapter3 = chapter3.replace("No confidence interval or significance claim is inferred", "No confidence interval or significance claim was inferred")
    chapter3 = replace_section(chapter3, "## 3.9 External qualification and future confirmation", "## 3.10 Reproducibility, rights, and practical safeguards", """## 3.9 Completed DEDALE qualification and external stress

The [DEDALE qualification](../dedale/QUALIFICATION.md) acquired named members of the author's CICFlowMeter archive and verified member CRC32 and SHA-256 values. The entire archive's advertised checksum was not independently verified. The acquired author tables already contained attack labels, steps, tactics, and techniques, so no inferred Zeek-to-CICFlowMeter label join was required. Author category 2, attack-related but not inherently malicious, remained distinct from confirmed benign traffic.

The acquired subset contained four lateral flows on day 17, linked by the author's labeling procedure to one PrintNightmare execution and two substeps. The [preparation protocol](../dedale/PREPARATION_PROTOCOL.json) retained every eligible lateral feature group and selected at most 100,000 unique benign groups by a fixed hash rule. Exact source overlap and conflicting labels were excluded; none occurred in this stress preparation. Other attack stages were excluded by its fixed scope. The prepared sample contained 100,004 groups, including all four lateral groups.

All 73 source predictors were mapped in order, with documented renames for Protocol and Flow Duration. The target implementation's duration unit was verified, but the exact source extractor revision/settings remain unknown. Matching names and units therefore support a transparent stress test, not proof of identical extraction. No target-derived preprocessing, fitting, calibration, or threshold choice occurred.

The external protocol fixed source budget 1,024 and seed 20260921 before target inference. That source selection was infeasible. The prespecified policy roster consequently contained only the source-locked natural argmax control and its source-normal 1% threshold; no candidate or fallback was invented. Chapter 4 reports both controls regardless of their performance. Four flows from one execution cannot confirm a three-point incident-level protection margin.
""")
    chapter3 = chapter3.replace("The final empirical package must identify", "The final empirical package identifies")
    chapter3 = chapter3.replace("Claims about saved analyst time would require", "Claims about saved analyst time would require")
    refs = "# References" + extract(original, "# References", "## Reference and completion notes")
    refs += """## Reference verification and publication status

The journal issue years and DOI metadata were checked against primary records. LARES is cited as an accepted-paper author version because final proceedings details were not verified. Layman and Roden is labeled as a preprint. The bounded Sysmon review used abstract/metadata, and ULTIMATE's overlap was assessed from its publisher abstract; no omission in their full methods is inferred. The local repository report is audited project evidence, not a peer-reviewed publication.

"""
    text = abstract + chapter1 + chapter2 + chapter3 + chapter_four(e, s, cells, diag, link) + "\n" + chapter_five(e, s) + "\n" + refs
    text += appendices(e, cells, software, results, diag, diagnostics, validation, link)
    prohibited = ["Chapter 4 is deliberately pending", "New experimental results are pending", "No new protection-experiment results are reported", "will be completed only", "Manuscript source draft"]
    require(not any(value in text for value in prohibited), "Unresolved result-draft placeholder")
    require("pending" not in text.lower(), "Unexpected pending-result language remains")
    require(not re.search(r"(?:\b[A-Za-z]:[/\\]|/Users/|/mnt/)", text), "Private filesystem path in manuscript")
    output.write_text(text.rstrip() + "\n", encoding="utf-8")
    return {"status": "COMPLETED_EMPIRICAL_NEGATIVE_FEASIBILITY_MANUSCRIPT", "manuscript_sha256": digest(output),
            "draft_source_sha256": digest(draft), "publication_manifest_sha256": digest(results / "PUBLICATION.json"),
            "primary_gate": s["primary_gate"]["status"], "source_cells": len(cells), "groups": s["completed_groups"],
            "feasible_primary_seeds": count, "software_tests_recorded": software["test_count"],
            "diagnostics_included": diag is not None, "word_count": len(text.split()), "assembled_utc": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--draft", type=Path, default=HERE / "DRAFT_EMPIRICAL_PRAXIS.md")
    parser.add_argument("--diagnostics", type=Path)
    parser.add_argument("--validation", type=Path, default=EXPERIMENT / "SOFTWARE_VALIDATION.json")
    args = parser.parse_args()
    print(json.dumps(assemble(args.results, args.output, args.draft, args.diagnostics, args.validation), ensure_ascii=True))
