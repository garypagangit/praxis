"""Evaluate a frozen two-channel review policy from audited E1 predictions.

No models are fitted or invoked. Routing to review is not stage identification
or successful human correction. Thresholds use benign calibration rows only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path

import numpy as np

from ..tabular_batch import analyze_e1
from ..tabular_batch.audit_e3 import require
from ..tabular_batch.conformal import fit_lac, predict_sets, evaluate_sets

FROZEN_PROTOCOL_SHA256 = "03199d57cbb68c339a38926b8d338076695e0aace3045b90c4c578fbd6fd18cd"


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def benign_threshold(scores, alpha):
    scores = np.asarray(scores, dtype=float)
    require(scores.ndim == 1 and np.isfinite(scores).all() and np.all((scores >= 0) & (scores <= 1)), "Invalid bounded calibration scores")
    require(0 < alpha < 1, "Invalid tail alpha")
    rank = int((Decimal(len(scores) + 1) * (Decimal(1) - Decimal(str(alpha)))).to_integral_value(rounding=ROUND_CEILING))
    value = float(np.partition(scores, rank - 1)[rank - 1]) if rank <= len(scores) else None
    return {"value": value, "infinite": value is None, "rank": rank, "benign_calibration_count": len(scores), "alpha": alpha,
            "comparison": "strict_greater_than"}


def above(scores, threshold):
    return np.asarray(scores) > (np.inf if threshold["infinite"] else threshold["value"])


def stage_scores(prob, classes, protocol):
    prob = np.asarray(prob, dtype=float)
    analyze_e1.probabilities(prob, np.zeros(len(prob), dtype=np.int64), len(classes))
    normal = classes.index(protocol["normal_class"])
    rare = [classes.index(name) for name in protocol["rare_classes"]]
    rare_prob = prob[:, rare]
    ratios = rare_prob / (rare_prob + prob[:, [normal]] + protocol["ratio_epsilon"])
    return 1 - prob[:, normal], np.max(ratios, axis=1)


def calibrate_policy(benign_foundation_prob, benign_tree_prob, classes, protocol):
    """Accept only benign probability arrays: no rare labels or test outcomes."""
    require(len(benign_foundation_prob) == len(benign_tree_prob), "Benign arrays misaligned")
    fa, fr = stage_scores(benign_foundation_prob, classes, protocol)
    ta, tr = stage_scores(benign_tree_prob, classes, protocol)
    return {"common": benign_threshold(fa, protocol["common_tail_alpha"]),
            "rescue_joint": benign_threshold(np.maximum(fr, tr), protocol["rescue_tail_alpha"]),
            "rescue_foundation": benign_threshold(fr, protocol["rescue_tail_alpha"]),
            "single_tabicl": benign_threshold(fa, protocol["single_control_tail_alpha"]),
            "single_tree": benign_threshold(ta, protocol["single_control_tail_alpha"])}


def route_policy(foundation_prob, tree_prob, classes, protocol, thresholds):
    require(len(foundation_prob) == len(tree_prob), "Query arrays misaligned")
    fa, fr = stage_scores(foundation_prob, classes, protocol)
    ta, tr = stage_scores(tree_prob, classes, protocol)
    common = above(fa, thresholds["common"])
    rescue = above(np.maximum(fr, tr), thresholds["rescue_joint"])
    return {"candidate": common | rescue,
            "single_tabicl": above(fa, thresholds["single_tabicl"]),
            "single_tree": above(ta, thresholds["single_tree"]),
            "two_channel_tabicl_only": common | above(fr, thresholds["rescue_foundation"]),
            "common_channel": common, "rescue_channel": rescue,
            "common_only": common & ~rescue, "rescue_only": rescue & ~common, "channel_overlap": common & rescue}


def routing_metrics(flags, y, classes, normal_name):
    flags, y = np.asarray(flags), np.asarray(y)
    require(flags.dtype == bool and flags.shape == y.shape and flags.ndim == 1, "Invalid routing flags")
    normal = y == classes.index(normal_name)
    reviewed, benign, attacks = int(flags.sum()), int(normal.sum()), int((~normal).sum())
    fp, tp = int((flags & normal).sum()), int((flags & ~normal).sum())
    stage = {}
    for k, name in enumerate(classes):
        mask = y == k; support = int(mask.sum()); routed = int((flags & mask).sum())
        stage[name] = {"support": support, "routed": routed, "routing_fraction": routed / support if support else None}
    return {"rows": len(y), "reviewed": reviewed, "review_fraction": reviewed / len(y) if len(y) else None,
            "benign_rows": benign, "benign_reviewed": fp, "benign_fpr": fp / benign if benign else None,
            "attack_rows": attacks, "attack_reviewed": tp, "attack_routing_recall": tp / attacks if attacks else None,
            "review_queue_attack_precision": tp / reviewed if reviewed else None, "per_stage": stage,
            "interpretation": "Routing to review only; no claim that the stage was correctly predicted or a reviewer resolved it."}


def conformal_review_flags(sets, normal_index):
    sets = np.asarray(sets)
    require(sets.ndim == 2 and sets.dtype == bool, "Invalid conformal sets")
    return ~((sets.sum(axis=1) == 1) & sets[:, normal_index])


def compare_policies(rows, protocol, classes):
    gate = protocol["gate"]; rare = protocol["rare_classes"]
    require(len({row["seed"] for row in rows}) == len(rows), "Duplicate evaluation seed")
    paired = []; mean_delta = {}; stage_delta = {}
    for control in protocol["controls"]:
        entries = []
        for row in rows:
            a, b = row["policies"]["candidate"], row["policies"][control]
            ar = min(a["per_stage"][name]["routing_fraction"] for name in rare)
            br = min(b["per_stage"][name]["routing_fraction"] for name in rare)
            entries.append({"seed": row["seed"], "control": control, "candidate_minimum_rare_routing_recall": ar,
                            "control_minimum_rare_routing_recall": br, "minimum_rare_routing_recall_delta": ar - br,
                            "attack_stage_recall_deltas": {name: a["per_stage"][name]["routing_fraction"] - b["per_stage"][name]["routing_fraction"] for name in classes if name != protocol["normal_class"]}})
        paired.extend(entries)
        mean_delta[control] = float(np.mean([r["minimum_rare_routing_recall_delta"] for r in entries])) if entries else None
        stage_delta[control] = {name: float(np.mean([r["attack_stage_recall_deltas"][name] for r in entries])) if entries else None for name in classes if name != protocol["normal_class"]}
    guards = {"minimum_rare_gain_against_both_controls": all(v is not None and v >= gate["minimum_rare_recall_mean_delta_vs_each_control"] - 1e-12 for v in mean_delta.values()),
              "every_attack_stage_mean_loss_at_most_0_05_against_both_controls": all(v is not None and v >= gate["all_attack_stage_mean_recall_delta_min_vs_each_control"] - 1e-12 for values in stage_delta.values() for v in values.values()),
              "every_seed_benign_fpr_within_0_015": bool(rows) and all(row["policies"]["candidate"]["benign_fpr"] is not None and row["policies"]["candidate"]["benign_fpr"] <= gate["every_seed_empirical_benign_fpr_max"] + 1e-12 for row in rows)}
    complete = len(rows) == gate["required_paired_seeds"] and sorted(r["seed"] for r in rows) == sorted(protocol["seeds"])
    return {"status": "INCOMPLETE" if not complete else ("DEVELOPMENT_PROMISING" if all(guards.values()) else "DEVELOPMENT_NEGATIVE"),
            "paired_seed_count": len(rows), "required_paired_seeds": gate["required_paired_seeds"], "guards": guards,
            "mean_minimum_rare_recall_deltas": mean_delta, "mean_attack_stage_recall_deltas": stage_delta, "paired_comparisons": paired,
            "interpretation": protocol["interpretation"]}


def evaluate_pair(foundation, tree, classes, protocol):
    require(np.array_equal(foundation["calibration_y"], tree["calibration_y"]) and np.array_equal(foundation["test_y"], tree["test_y"]), "Paired labels differ")
    benign = foundation["calibration_y"] == classes.index(protocol["normal_class"])
    thresholds = calibrate_policy(foundation["calibration_probabilities"][benign], tree["calibration_probabilities"][benign], classes, protocol)
    flags = route_policy(foundation["test_probabilities"], tree["test_probabilities"], classes, protocol, thresholds)
    policies = {name: routing_metrics(value, foundation["test_y"], classes, protocol["normal_class"]) for name, value in flags.items()}
    conformal = []
    for name, prediction in (("tabicl_v2", foundation), ("selected_tree", tree)):
        for nominal in protocol["conformal_nominal_coverages"]:
            cal = fit_lac(prediction["calibration_probabilities"], np.asarray(classes)[prediction["calibration_y"]],
                          alpha=float(Decimal(1) - Decimal(str(nominal))), method="mondrian", class_labels=classes)
            sets = predict_sets(prediction["test_probabilities"], cal)
            review = conformal_review_flags(sets, classes.index(protocol["normal_class"]))
            flags[f"{name}_mondrian_{nominal}"] = review
            conformal.append({"model": name, "method": "mondrian", "nominal_coverage": nominal, "calibration": cal.to_dict(),
                              "set_metrics": evaluate_sets(sets, np.asarray(classes)[prediction["test_y"]], class_labels=classes),
                              "routing_metrics": routing_metrics(review, prediction["test_y"], classes, protocol["normal_class"]),
                              "routing_rule": protocol["conformal_routing"]})
    return {"thresholds": thresholds, "policies": policies, "conformal_controls": conformal}, flags


def run(data_path, protocol_path, e1_protocol_path, run_roots, output):
    data_path, protocol_path, e1_protocol_path, output = map(Path, (data_path, protocol_path, e1_protocol_path, output))
    if data_path.is_dir(): data_path = data_path / "DATA.npz"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    require(protocol["status"] == "FROZEN_BEFORE_GATE_OUTCOMES", "Root must freeze the policy protocol before execution")
    require(analyze_e1.file_hash(protocol_path) == FROZEN_PROTOCOL_SHA256, "Policy differs from protocol frozen at b1ae20f; amendment required")
    require(protocol["e1_protocol_sha256"] == analyze_e1.file_hash(e1_protocol_path), "E1 protocol changed")
    require(protocol["data_npz_sha256"] == analyze_e1.file_hash(data_path) and protocol["manifest_sha256"] == analyze_e1.file_hash(data_path.with_name("MANIFEST.json")), "Prepared input changed")
    require(not output.exists() or not any(output.iterdir()), "Use a fresh output directory; existing results preserved")
    source = Path(__file__).parent
    binding = {"protocol_sha256": analyze_e1.file_hash(protocol_path), "e1_protocol_sha256": analyze_e1.file_hash(e1_protocol_path),
               "data_npz_sha256": analyze_e1.file_hash(data_path), "manifest_sha256": analyze_e1.file_hash(data_path.with_name("MANIFEST.json")),
               "code_sha256": {"run_rare_stage_gate.py": analyze_e1.file_hash(Path(__file__)), "analyze_e1.py": analyze_e1.file_hash(source.parent / "tabular_batch" / "analyze_e1.py"),
                               "conformal.py": analyze_e1.file_hash(source.parent / "tabular_batch" / "conformal.py")},
               "input_runs": [{"path": str(Path(root).resolve()), "prefit_sha256": analyze_e1.file_hash(Path(root) / "PREFIT_RECEIPT.json")} for root in run_roots]}
    write_json(output / "PREFIT_RECEIPT.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "execution": binding,
               "execution_binding": analyze_e1.value_hash(binding), "policy_outcomes_evaluated": False, "previous_E1_and_prescreen_results_known": True})
    audited = analyze_e1.analyze(data_path, e1_protocol_path, run_roots)
    with np.load(data_path, allow_pickle=False) as prepared:
        classes = prepared["classes"].tolist(); test_ids = np.flatnonzero(prepared["split"] == 2)
        test_y = prepared["y"][test_ids]
        cal_y = prepared["y"][prepared["split"] == 1]
    roster = {(cell["model"], cell["seed"]): cell for cell in audited["cells"]}
    directories = {}
    for root in map(Path, run_roots):
        for model, seed in roster:
            directory = root / "cells" / model / str(seed)
            if (directory / "COMPLETE.json").exists():
                require((model, seed) not in directories, "Duplicate cell path")
                directories[(model, seed)] = directory
    rows, missing, packet, source_cells = [], [], {"test_indices": test_ids, "test_y": test_y, "classes": np.asarray(classes)}, {}
    for seed in protocol["seeds"]:
        required = [(model, seed) for model in [protocol["foundation_model"], *protocol["tree_models"]]]
        if not all(key in roster for key in required):
            missing.append({"seed": seed, "missing_models": [model for model, _ in required if (model, seed) not in roster]})
            continue
        tree_model = max(protocol["tree_models"], key=lambda name: roster[(name, seed)]["inner_cv_selected_macro_f1"])
        predictions = []
        for model in (protocol["foundation_model"], tree_model):
            directory = directories[(model, seed)]
            path = directory / "PREDICTIONS.npz"
            require(analyze_e1.file_hash(path) == roster[(model, seed)]["prediction_sha256"], "Audited predictions changed before policy evaluation")
            with np.load(path, allow_pickle=False) as saved:
                predictions.append({key: saved[key] for key in saved.files})
            source_cells[f"{model}/{seed}"] = {name: analyze_e1.file_hash(directory / name) for name in ("COMPLETE.json", "CELL.json", "PREDICTIONS.npz")}
        result, flags = evaluate_pair(*predictions, classes, protocol)
        rows.append({"seed": seed, "selected_tree": tree_model, "tree_selection_scores": {name: roster[(name, seed)]["inner_cv_selected_macro_f1"] for name in protocol["tree_models"]}, **result})
        packet.update({f"{name}_{seed}": value for name, value in flags.items()})
    summary = compare_policies(rows, protocol, classes)
    result = {"schema_version": 1, "experiment": protocol["experiment"], "execution_binding": analyze_e1.value_hash(binding),
              "prefit_sha256": analyze_e1.file_hash(output / "PREFIT_RECEIPT.json"), "policy_protocol_sha256": analyze_e1.file_hash(protocol_path),
              "source_prediction_audit_status": audited["audit_status"], "source_cells": source_cells, "missing_pairs": missing,
              "label_cost": {"unique_model_fit_labels_per_seed": len(classes) * protocol["samples_per_class"],
                             "candidate_benign_calibration_labels": int((cal_y == classes.index(protocol["normal_class"])).sum()),
                             "candidate_rare_stage_calibration_labels_used_for_thresholds": 0,
                             "conformal_control_all_calibration_labels": len(cal_y), "new_labels_collected": 0},
              "classes": classes, "rows": rows, "primary": summary, "interpretation": protocol["interpretation"],
              "conformal_operating_point_notice": "LAC controls have 90/95% nominal label coverage; their review burden is measured and is not matched to the gate's 1% nominal benign tail budget."}
    np.savez_compressed(output / "ROUTING_PRIVATE.npz", **packet)
    write_json(output / "SOURCE_ANALYSIS.json", audited)
    write_json(output / "AGGREGATE.json", result)
    write_json(output / "COMPLETE.json", {"run_status": "COMPLETE" if not missing else "INCOMPLETE", "execution_binding": analyze_e1.value_hash(binding),
               "artifact_sha256": {name: analyze_e1.file_hash(output / name) for name in ("PREFIT_RECEIPT.json", "SOURCE_ANALYSIS.json", "AGGREGATE.json", "ROUTING_PRIVATE.npz")}})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("data", "protocol", "e1-protocol", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    args = parser.parse_args()
    result = run(args.data, args.protocol, args.e1_protocol, args.run, args.output)
    print(json.dumps({"status": result["primary"]["status"], "paired_seeds": len(result["rows"])}))


if __name__ == "__main__":
    main()
