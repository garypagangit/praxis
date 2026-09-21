"""Posthoc descriptive selection frontiers; never change a locked policy.

Only saved selection probabilities are used. Every tied attainable threshold is
retained. These are in-sample selection limits for a finite fitted library, not
new success gates or estimates of deployment capability.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from . import audit


NOTICE = ("Posthoc descriptive frontiers on the exposed-source selection partition. "
          "No model fit, inference, threshold change, new preferred policy or replacement gate. "
          "Best attainable means only within the saved finite model/weight/threshold library; "
          "it does not establish held-out or deployment performance. Seeds reuse the same cases.")


def frontier_summary(cells):
    """Summarize exact integer frontiers and retain all primary-objective ties."""
    audit.require(cells and len({c["cell_id"] for c in cells}) == len(cells), "Missing or duplicate frontier cells")
    all_points = [(cell["cell_id"], point) for cell in cells for point in cell["points"]]
    supports = {(p[3], p[4]) for _, p in all_points}
    audit.require(len(supports) == 1, "Mixed frontier class supports")
    benign_n, lateral_n = next(iter(supports))
    audit.require(benign_n > 0 and lateral_n > 0, "Unsupported frontier classes")
    under_budget = [(cell_id, p) for cell_id, p in all_points if 100 * p[1] <= benign_n]
    above_floor = [(cell_id, p) for cell_id, p in all_points if 10 * p[2] >= 9 * lateral_n]
    audit.require(under_budget and above_floor, "Frontier omitted all-clear/all-alert endpoints")
    best_tp = max(p[2] for _, p in under_budget)
    least_fp = min(p[1] for _, p in above_floor)
    def encode(records):
        return [{"cell_id": cell_id, "threshold": p[0], "benign_fp": p[1], "lateral_tp": p[2],
                 "benign_n": p[3], "lateral_n": p[4], "benign_fpr": p[1] / p[3],
                 "lateral_recall": p[2] / p[4]} for cell_id, p in records]
    def tied(records):
        values = encode(records)
        return {"attaining_cell_ids": sorted({r["cell_id"] for r in values}),
                "tied_threshold_count": len(values), "tied_thresholds": values}
    maximum = [(cell_id, p) for cell_id, p in under_budget if p[2] == best_tp]
    minimum = [(cell_id, p) for cell_id, p in above_floor if p[1] == least_fp]
    return {"benign_n": benign_n, "lateral_n": lateral_n,
            "maximum_benign_fp_at_1pct": benign_n // 100,
            "minimum_lateral_tp_at_90pct": (9 * lateral_n + 9) // 10,
            "joint_1pct_fpr_90pct_lateral_feasible": 10 * best_tp >= 9 * lateral_n,
            "maximum_lateral_recall_at_fpr_at_most_1pct": {
                "lateral_tp": best_tp, "lateral_recall": best_tp / lateral_n, **tied(maximum)},
            "minimum_fpr_for_lateral_recall_at_least_90pct": {
                "benign_fp": least_fp, "benign_fpr": least_fp / benign_n, **tied(minimum)}}


def group_frontiers(cells, y, normal, lateral):
    points = [{"cell_id": c["cell_id"], "points": audit.selection_options(c["scores"], y, normal, lateral)} for c in cells]
    models = list(dict.fromkeys(c["cell_id"].split("/")[0] for c in points))
    schemes = list(dict.fromkeys(c["cell_id"].split("/")[1] for c in points))
    return {"all_fit_library": frontier_summary(points),
            "by_model": {m: frontier_summary([c for c in points if c["cell_id"].split("/")[0] == m]) for m in models},
            "by_scheme": {s: frontier_summary([c for c in points if c["cell_id"].split("/")[1] == s]) for s in schemes},
            "by_cell": {c["cell_id"]: frontier_summary([c]) for c in points}}


def across_groups(rows, protocol):
    def summarize(frontiers, seeds):
        recalls = [f["maximum_lateral_recall_at_fpr_at_most_1pct"]["lateral_recall"] for f in frontiers]
        fprs = [f["minimum_fpr_for_lateral_recall_at_least_90pct"]["benign_fpr"] for f in frontiers]
        stats = lambda values: {"mean": sum(values) / len(values), "minimum": min(values), "maximum": max(values)}
        return {"seeds": seeds, "seed_count": len(seeds),
                "jointly_feasible_groups": sum(f["joint_1pct_fpr_90pct_lateral_feasible"] for f in frontiers),
                "maximum_attainable_lateral_recall_at_1pct_fpr": stats(recalls),
                "minimum_attainable_fpr_for_90pct_lateral_recall": stats(fprs),
                "interpretation": "Descriptive repeated-fitting summaries on common selection cases; no confidence interval."}
    result = {}
    for budget in sorted({g["budget"] for g in protocol["groups"]}):
        chosen = [r for r in rows if r["budget"] == budget]
        seeds = [r["seed"] for r in chosen]
        result[str(budget)] = {"all_fit_library": summarize([r["frontiers"]["all_fit_library"] for r in chosen], seeds)}
        for field in ("by_model", "by_scheme", "by_cell"):
            keys = list(chosen[0]["frontiers"][field])
            result[str(budget)][field] = {key: summarize([r["frontiers"][field][key] for r in chosen], seeds) for key in keys}
    return result


def diagnose(data_path, protocol_path, run, source_audit_path=None):
    protocol_path, run = Path(protocol_path), Path(run)
    protocol = audit.read_json(protocol_path)
    audit.check_protocol(protocol)
    data = audit.load_bound_input(data_path, protocol)
    prefit_path, summary_path = run / "PREFIT_RECEIPT.json", run / "SUMMARY.json"
    prefit, summary = audit.read_json(prefit_path), audit.read_json(summary_path)
    fixed, binding = prefit["fixed"], prefit["execution_binding"]
    audit.require(binding == audit.value_hash(fixed), "Prefit binding differs")
    audit.require(fixed["protocol_sha256"] == audit.file_hash(protocol_path), "Frozen protocol changed")
    audit.require(fixed["data_sha256"] == protocol["data_npz_sha256"] and fixed["manifest_sha256"] == protocol["manifest_sha256"], "Input provenance changed")
    audit.require(fixed["classes"] == data["classes"].tolist() and fixed["feature_names"] == data["feature_names"].tolist(), "Feature/class schema changed")
    audit.verify_files(audit.REPO, fixed["source_hashes"], audit.SOURCE_FILES)
    audit.require(summary["status"] == "COMPLETE" and summary["execution_binding"] == binding, "Diagnostics require a complete frozen source batch")
    audit.require(summary["completed_groups"] == summary["required_groups"] == len(protocol["groups"]), "Incomplete group roster")
    audit.require(summary["completed_cells"] == summary["required_cells"] == 8 * len(protocol["groups"]), "Incomplete cell roster")
    require_roster = {(g["budget"], g["seed"]) for g in protocol["groups"]}
    summary_rows = {(g["budget"], g["seed"]): g for g in summary["groups"]}
    audit.require(len(summary_rows) == len(summary["groups"]) and set(summary_rows) == require_roster, "Summary group roster differs")
    parts = audit.reconstruct_partitions(data, protocol["partition_tag"])
    audit.compare({k: audit.roster(data, v) for k, v in parts.items()}, fixed["partitions"], "Partition provenance")
    audit.compare([{**g, **audit.roster(data, audit.reconstruct_support(data, g["budget"], g["seed"]))}
                   for g in protocol["groups"]], fixed["groups"], "Support provenance")
    source_audit = None
    if source_audit_path is not None:
        source_audit = audit.read_json(source_audit_path)
        audit.require(source_audit["audit_status"] == "PASS" and source_audit["run_status"] == "COMPLETE", "Source independent audit is not complete")
        audit.require(source_audit["audited_cells"] == 8 * len(protocol["groups"]) and source_audit["execution_binding"] == binding, "Source audit roster/binding differs")
        for name in ("PREFIT_RECEIPT.json", "SUMMARY.json"):
            audit.require(source_audit["artifact_hashes"][name] == audit.file_hash(run / name), "Source audit artifact changed")
    classes = data["classes"].tolist()
    normal, lateral = classes.index("NormalTraffic"), classes.index("LateralMovement")
    rows, provenance = [], {}
    for group in protocol["groups"]:
        budget, seed = group["budget"], group["seed"]
        root = run / "groups" / str(budget) / str(seed)
        saved, lock = audit.read_json(root / "RESULT.json"), audit.read_json(root / "SELECTION_LOCK.json")
        audit.compare(saved, summary_rows[(budget, seed)], "Summary versus saved group")
        result_hash = audit.file_hash(root / "RESULT.json")
        if source_audit is not None:
            audit.require(source_audit["group_result_hashes"][f"{budget}/{seed}"] == result_hash, "Audited group result changed")
        audit.require(lock["execution_binding"] == binding and lock["budget"] == budget and lock["seed"] == seed, "Selection lock identity differs")
        audit.require(saved["selection_lock_sha256"] == audit.file_hash(root / "SELECTION_LOCK.json"), "Selection lock bytes changed")
        cells, receipts = [], {}
        for model in protocol["models"]:
            for scheme in protocol["schemes"]:
                cell_id = f"{model}/{scheme}"
                folder = run / "cells" / str(budget) / str(seed) / model / scheme
                complete, fit = audit.read_json(folder / "COMPLETE.json"), audit.read_json(folder / "FIT_COMPLETE.json")
                audit.require(complete["execution_binding"] == fit["execution_binding"] == binding, "Cell execution binding changed")
                audit.require(complete["selection_lock_sha256"] == saved["selection_lock_sha256"], "Cell policy lock changed")
                audit.require(saved["cell_complete_sha256"][cell_id] == audit.file_hash(folder / "COMPLETE.json"), "Group cell completion changed")
                audit.verify_files(folder, complete["files"], ["CELL.json", "EVALUATION.npz", "EVALUATION_STARTED.json", "FIT_COMPLETE.json"])
                audit.verify_files(folder, fit["files"], ["STARTED.json", "MODEL.joblib", "SELECTION.npz", "FITTED.json"])
                audit.require(lock["fit_complete_sha256"][cell_id] == audit.file_hash(folder / "FIT_COMPLETE.json"), "Locked fitting artifact changed")
                p = audit.packet(folder / "SELECTION.npz", data, parts["selection"], keys=["probabilities", "y", "indices", "fingerprints", "classes"])
                cells.append({"cell_id": cell_id, "scores": 1 - p[:, normal]})
                receipts[cell_id] = {"selection_sha256": audit.file_hash(folder / "SELECTION.npz"),
                                     "fit_complete_sha256": audit.file_hash(folder / "FIT_COMPLETE.json")}
        frontiers = group_frontiers(cells, data["y"][parts["selection"]], normal, lateral)
        feasible = frontiers["all_fit_library"]["joint_1pct_fpr_90pct_lateral_feasible"]
        audit.require(lock["status"] == ("SELECTED" if feasible else "INFEASIBLE"), "Frontier feasibility contradicts frozen policy lock")
        rows.append({"budget": budget, "seed": seed, "locked_selection_status": lock["status"], "frontiers": frontiers})
        provenance[f"{budget}/{seed}"] = {"result_sha256": result_hash,
            "selection_lock_sha256": saved["selection_lock_sha256"], "cells": receipts}
    return {"schema_version": 1, "status": "COMPLETE_POSTHOC_DESCRIPTIVE", "experiment": protocol["experiment"],
        "interpretation": NOTICE, "completed_groups": len(rows), "completed_cells": 8 * len(rows),
        "threshold_rule": "Strict score > cutoff. Every distinct selection-score cutoff plus all-alert endpoint; tied scores are never separated.",
        "ties": "All thresholds tied on the stated primary frontier objective are retained; none is selected for a new policy.",
        "cross_validation_notice": "This examines the eight fit-CV-selected model/weight cells, not every discarded CV hyperparameter model.",
        "execution_binding": binding, "protocol_sha256": audit.file_hash(protocol_path),
        "input_artifact_hashes": {"PREFIT_RECEIPT.json": audit.file_hash(prefit_path), "SUMMARY.json": audit.file_hash(summary_path)},
        "source_audit_sha256": audit.file_hash(source_audit_path) if source_audit_path is not None else None,
        "source_audit_notice": "Complete independent source audit bound" if source_audit is not None else "Receipt and selection-packet integrity checked; complete independent source audit was not supplied",
        "diagnostic_source_sha256": audit.file_hash(__file__), "independent_count_source_sha256": audit.file_hash(audit.__file__),
        "groups": rows, "by_budget": across_groups(rows, protocol), "source_group_hashes": provenance}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--source-audit", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "DIAGNOSTICS.json"
    audit.require(not target.exists(), "Use a fresh diagnostics directory")
    result = diagnose(args.data, args.protocol, args.run, args.source_audit)
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    target.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "completed_groups", "completed_cells")}))


if __name__ == "__main__":
    main()
