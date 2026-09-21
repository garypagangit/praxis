"""Independent, read-only arithmetic/provenance audit of a completed review gate.

Never imports the policy runner and never fits or invokes a classifier. Score
thresholds use a separately implemented exact rational rank and sorted array.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path

import numpy as np

from ..tabular_batch import analyze_e1
from ..tabular_batch.audit_e3 import compare, digest, require
from ..tabular_batch.conformal import fit_lac, predict_sets, evaluate_sets

PROTOCOL_HASH = "03199d57cbb68c339a38926b8d338076695e0aace3045b90c4c578fbd6fd18cd"
RUNNER_HASH = "a76a2030612ba61ffbd4bdd74f36a5c625e91ee78b898ad9ea9b9602c8374e4a"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {name: z[name] for name in z.files}


def quantile_record(scores, alpha):
    scores = np.asarray(scores, dtype=float)
    require(scores.ndim == 1 and np.isfinite(scores).all() and np.all((scores >= 0) & (scores <= 1)), "Invalid benign scores")
    require(0 < alpha < 1, "Invalid alpha")
    fraction = (len(scores) + 1) * (1 - Fraction(str(alpha)))
    rank = (fraction.numerator + fraction.denominator - 1) // fraction.denominator
    value = float(np.sort(scores)[rank - 1]) if rank <= len(scores) else None
    return {"value": value, "infinite": value is None, "rank": rank, "benign_calibration_count": len(scores),
            "alpha": alpha, "comparison": "strict_greater_than"}


def counts(flags, labels, classes, normal):
    require(flags.dtype == bool and flags.ndim == 1 and flags.shape == labels.shape, "Invalid review flags")
    supports = np.bincount(labels, minlength=len(classes))
    routed = np.bincount(labels[flags], minlength=len(classes))
    n, reviewed = len(labels), int(routed.sum())
    benign, fp = int(supports[normal]), int(routed[normal])
    attacks, tp = n - benign, reviewed - fp
    return {"rows": n, "reviewed": reviewed, "review_fraction": reviewed / n if n else None,
            "benign_rows": benign, "benign_reviewed": fp, "benign_fpr": fp / benign if benign else None,
            "attack_rows": attacks, "attack_reviewed": tp, "attack_routing_recall": tp / attacks if attacks else None,
            "review_queue_attack_precision": tp / reviewed if reviewed else None,
            "per_stage": {name: {"support": int(supports[k]), "routed": int(routed[k]),
                                  "routing_fraction": float(routed[k] / supports[k]) if supports[k] else None} for k, name in enumerate(classes)}}


def no_notice(value):
    return {key: item for key, item in value.items() if key != "interpretation"}


def reconstruct_row(foundation, tree, classes, protocol):
    normal = classes.index(protocol["normal_class"])
    rare = [classes.index(name) for name in protocol["rare_classes"]]
    benign = foundation["calibration_y"] == normal
    require(np.array_equal(foundation["calibration_y"], tree["calibration_y"]) and np.array_equal(foundation["test_y"], tree["test_y"]), "Paired labels differ")
    def scores(model, partition):
        p = model[partition + "_probabilities"]
        analyze_e1.probabilities(p, model[partition + "_y"], len(classes))
        ratios = [p[:, k] / (p[:, k] + p[:, normal] + protocol["ratio_epsilon"]) for k in rare]
        return 1 - p[:, normal], np.maximum.reduce(ratios)
    ca, cr = scores(foundation, "calibration")
    ta, tr = scores(tree, "calibration")
    qa, qr = scores(foundation, "test")
    ba, br = scores(tree, "test")
    definitions = {
        "common": (ca, qa, protocol["common_tail_alpha"]),
        "rescue_joint": (np.maximum(cr, tr), np.maximum(qr, br), protocol["rescue_tail_alpha"]),
        "rescue_foundation": (cr, qr, protocol["rescue_tail_alpha"]),
        "single_tabicl": (ca, qa, protocol["single_control_tail_alpha"]),
        "single_tree": (ta, ba, protocol["single_control_tail_alpha"]),
    }
    thresholds, decisions = {}, {}
    for name, (cal_scores, test_scores, alpha) in definitions.items():
        record = quantile_record(cal_scores[benign], alpha)
        thresholds[name] = record
        decisions[name] = np.zeros(len(test_scores), dtype=bool) if record["infinite"] else test_scores > record["value"]
    c, r = decisions["common"], decisions["rescue_joint"]
    flags = {"candidate": np.logical_or(c, r), "single_tabicl": decisions["single_tabicl"], "single_tree": decisions["single_tree"],
             "two_channel_tabicl_only": np.logical_or(c, decisions["rescue_foundation"]), "common_channel": c, "rescue_channel": r,
             "common_only": c & ~r, "rescue_only": r & ~c, "channel_overlap": c & r}
    metrics = {name: counts(value, foundation["test_y"], classes, normal) for name, value in flags.items()}
    conformal = []
    for name, predictions in (("tabicl_v2", foundation), ("selected_tree", tree)):
        for nominal in protocol["conformal_nominal_coverages"]:
            cal = fit_lac(predictions["calibration_probabilities"], np.asarray(classes)[predictions["calibration_y"]],
                          alpha=float(1 - Fraction(str(nominal))), method="mondrian", class_labels=classes)
            sets = predict_sets(predictions["test_probabilities"], cal)
            exact_benign = np.zeros_like(sets); exact_benign[:, normal] = True
            review = np.any(sets != exact_benign, axis=1)
            flags[f"{name}_mondrian_{nominal}"] = review
            conformal.append({"model": name, "method": "mondrian", "nominal_coverage": nominal, "calibration": cal.to_dict(),
                              "set_metrics": evaluate_sets(sets, np.asarray(classes)[predictions["test_y"]], class_labels=classes),
                              "routing_metrics": counts(review, predictions["test_y"], classes, normal), "routing_rule": protocol["conformal_routing"]})
    return {"thresholds": thresholds, "policies": metrics, "conformal_controls": conformal}, flags


def verify_row(reported, foundation, tree, classes, protocol, packet):
    actual, flags = reconstruct_row(foundation, tree, classes, protocol)
    compare(reported["thresholds"], actual["thresholds"], "thresholds")
    require(set(reported["policies"]) == set(actual["policies"]), "Policy roster differs")
    for name, metric in actual["policies"].items():
        compare(no_notice(reported["policies"][name]), metric, "routing metrics " + name)
    require(len(reported["conformal_controls"]) == len(actual["conformal_controls"]), "Conformal control count differs")
    for reported_cp, expected_cp in zip(reported["conformal_controls"], actual["conformal_controls"]):
        cp = dict(reported_cp); cp["routing_metrics"] = no_notice(cp["routing_metrics"])
        compare(cp, expected_cp, "conformal control")
    for name, flag in flags.items():
        key = f"{name}_{reported['seed']}"
        require(key in packet and packet[key].dtype == bool and np.array_equal(packet[key], flag), "Routing packet differs: " + key)
    return actual, flags


def primary_summary(rows, classes, protocol):
    require(len({row["seed"] for row in rows}) == len(rows), "Duplicate seed")
    paired, mean_delta, stage_delta = [], {}, {}
    attack_stages = [name for name in classes if name != protocol["normal_class"]]
    for control in protocol["controls"]:
        comparisons = []
        for row in rows:
            a, b = row["policies"]["candidate"], row["policies"][control]
            recall_a = [a["per_stage"][name]["routing_fraction"] for name in protocol["rare_classes"]]
            recall_b = [b["per_stage"][name]["routing_fraction"] for name in protocol["rare_classes"]]
            comparisons.append({"seed": row["seed"], "control": control,
                                "candidate_minimum_rare_routing_recall": min(recall_a), "control_minimum_rare_routing_recall": min(recall_b),
                                "minimum_rare_routing_recall_delta": min(recall_a) - min(recall_b),
                                "attack_stage_recall_deltas": {name: a["per_stage"][name]["routing_fraction"] - b["per_stage"][name]["routing_fraction"] for name in attack_stages}})
        paired.extend(comparisons)
        mean_delta[control] = sum(r["minimum_rare_routing_recall_delta"] for r in comparisons) / len(comparisons) if comparisons else None
        stage_delta[control] = {name: sum(r["attack_stage_recall_deltas"][name] for r in comparisons) / len(comparisons) if comparisons else None for name in attack_stages}
    g = protocol["gate"]
    guards = {"minimum_rare_gain_against_both_controls": all(v is not None and v + 1e-12 >= g["minimum_rare_recall_mean_delta_vs_each_control"] for v in mean_delta.values()),
              "every_attack_stage_mean_loss_at_most_0_05_against_both_controls": all(v is not None and v + 1e-12 >= g["all_attack_stage_mean_recall_delta_min_vs_each_control"] for group in stage_delta.values() for v in group.values()),
              "every_seed_benign_fpr_within_0_015": bool(rows) and all(r["policies"]["candidate"]["benign_fpr"] is not None and r["policies"]["candidate"]["benign_fpr"] <= g["every_seed_empirical_benign_fpr_max"] + 1e-12 for r in rows)}
    complete = len(rows) == g["required_paired_seeds"] and sorted(r["seed"] for r in rows) == sorted(protocol["seeds"])
    return {"status": ("DEVELOPMENT_PROMISING" if all(guards.values()) else "DEVELOPMENT_NEGATIVE") if complete else "INCOMPLETE",
            "paired_seed_count": len(rows), "required_paired_seeds": g["required_paired_seeds"], "guards": guards,
            "mean_minimum_rare_recall_deltas": mean_delta, "mean_attack_stage_recall_deltas": stage_delta,
            "paired_comparisons": paired, "interpretation": protocol["interpretation"]}


def verify_artifacts(root, completion):
    expected = {"PREFIT_RECEIPT.json", "SOURCE_ANALYSIS.json", "AGGREGATE.json", "ROUTING_PRIVATE.npz"}
    require(set(completion["artifact_sha256"]) == expected, "Wrong gate artifact roster")
    for name, claimed in completion["artifact_sha256"].items():
        require(digest(root / name) == claimed, "Gate artifact hash differs: " + name)


def audit(prepared, run_root, protocol_path, e1_protocol_path):
    prepared, run_root, protocol_path, e1_protocol_path = map(Path, (prepared, run_root, protocol_path, e1_protocol_path))
    data_path = prepared / "DATA.npz" if prepared.is_dir() else prepared
    protocol, prefit, aggregate, complete = read(protocol_path), read(run_root / "PREFIT_RECEIPT.json"), read(run_root / "AGGREGATE.json"), read(run_root / "COMPLETE.json")
    require(digest(protocol_path) == PROTOCOL_HASH and protocol["status"] == "FROZEN_BEFORE_GATE_OUTCOMES", "Frozen protocol differs")
    binding = prefit["execution"]; binding_hash = analyze_e1.value_hash(binding)
    require(binding_hash == prefit["execution_binding"] == aggregate["execution_binding"] == complete["execution_binding"], "Execution binding mismatch")
    require(prefit["policy_outcomes_evaluated"] is False and prefit["previous_E1_and_prescreen_results_known"] is True, "Invalid freeze receipt")
    require(binding["protocol_sha256"] == aggregate["policy_protocol_sha256"] == PROTOCOL_HASH, "Protocol receipt differs")
    require(binding["e1_protocol_sha256"] == protocol["e1_protocol_sha256"] == digest(e1_protocol_path), "E1 protocol differs")
    for field, path in (("data_npz_sha256", data_path), ("manifest_sha256", data_path.with_name("MANIFEST.json"))):
        require(binding[field] == protocol[field] == digest(path), "Prepared input differs")
    source = Path(__file__).parent
    expected_sources = {"run_rare_stage_gate.py": source / "run_rare_stage_gate.py",
                        "analyze_e1.py": source.parent / "tabular_batch" / "analyze_e1.py", "conformal.py": source.parent / "tabular_batch" / "conformal.py"}
    require(set(binding["code_sha256"]) == set(expected_sources), "Gate source roster differs")
    for name, path in expected_sources.items():
        require(binding["code_sha256"][name] == digest(path), "Bound source changed: " + name)
    require(binding["code_sha256"]["run_rare_stage_gate.py"] == RUNNER_HASH, "Runner differs from reviewed frozen source")
    verify_artifacts(run_root, complete)
    require(aggregate["prefit_sha256"] == digest(run_root / "PREFIT_RECEIPT.json"), "Aggregate prefit differs")
    roots = [Path(item["path"]) for item in binding["input_runs"]]
    require(len(set(path.resolve() for path in roots)) == len(roots), "Duplicate input run")
    for root, item in zip(roots, binding["input_runs"]):
        require(digest(root / "PREFIT_RECEIPT.json") == item["prefit_sha256"], "E1 prefit hash changed")
        for name, claimed in read(root / "PREFIT_RECEIPT.json")["execution"]["code_sha256"].items():
            require(name in {"run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt"}, "Unexpected E1 source path")
            require(digest(source.parent / "tabular_batch" / name) == claimed, "E1 source changed")
    source_audit = analyze_e1.analyze(data_path, e1_protocol_path, roots)
    compare(read(run_root / "SOURCE_ANALYSIS.json"), source_audit, "source prediction audit")
    require(aggregate["source_prediction_audit_status"] == source_audit["audit_status"] == "PASS", "Source prediction audit failed")
    data = arrays(data_path); classes = data["classes"].tolist(); packet = arrays(run_root / "ROUTING_PRIVATE.npz")
    test = np.flatnonzero(data["split"] == 2); cal = np.flatnonzero(data["split"] == 1)
    compare(aggregate["classes"], classes, "classes")
    for name, expected in (("classes", data["classes"]), ("test_indices", test), ("test_y", data["y"][test])):
        require(name in packet and np.array_equal(packet[name], expected), "Routing input/order differs: " + name)
    roster = {(cell["model"], cell["seed"]): cell for cell in source_audit["cells"]}
    expected_rows = []; expected_sources = {}; expected_packet = {"classes", "test_indices", "test_y"}; missing = []
    by_seed = {row["seed"]: row for row in aggregate["rows"]}
    require(len(by_seed) == len(aggregate["rows"]), "Duplicate gate row")
    for seed in protocol["seeds"]:
        missing_models = [name for name in [protocol["foundation_model"], *protocol["tree_models"]] if (name, seed) not in roster]
        if missing_models:
            missing.append({"seed": seed, "missing_models": missing_models}); continue
        require(seed in by_seed, "Completed pair missing from aggregate")
        row = by_seed[seed]
        scores = {name: roster[(name, seed)]["inner_cv_selected_macro_f1"] for name in protocol["tree_models"]}
        tree_model = "xgboost" if scores["xgboost"] >= scores["lightgbm"] else "lightgbm"
        compare(row["tree_selection_scores"], scores, "CV selection scores")
        require(row["selected_tree"] == tree_model, "Wrong CV-selected tree")
        predictions = []
        for model in (protocol["foundation_model"], tree_model):
            candidates = [root / "cells" / model / str(seed) for root in roots if (root / "cells" / model / str(seed) / "COMPLETE.json").exists()]
            require(len(candidates) == 1, "Missing/duplicate source cell")
            directory = candidates[0]
            expected_sources[f"{model}/{seed}"] = {name: digest(directory / name) for name in ("COMPLETE.json", "CELL.json", "PREDICTIONS.npz")}
            require(expected_sources[f"{model}/{seed}"]["PREDICTIONS.npz"] == roster[(model, seed)]["prediction_sha256"], "Audited source changed")
            predictions.append(arrays(directory / "PREDICTIONS.npz"))
        reconstructed, flags = verify_row(row, *predictions, classes, protocol, packet)
        expected_packet.update(f"{name}_{seed}" for name in flags)
        expected_rows.append({"seed": seed, "policies": reconstructed["policies"]})
    require(set(packet) == expected_packet, "Unexpected/missing private routing array")
    require(len(expected_rows) == len(aggregate["rows"]), "Unexpected evaluated seed")
    compare(aggregate["source_cells"], expected_sources, "source cell hashes")
    compare(aggregate["missing_pairs"], missing, "missing pairs")
    actual_primary = primary_summary(expected_rows, classes, protocol)
    compare(aggregate["primary"], actual_primary, "primary arithmetic")
    compare(aggregate["label_cost"], {"unique_model_fit_labels_per_seed": len(classes) * protocol["samples_per_class"],
            "candidate_benign_calibration_labels": int(np.count_nonzero(data["y"][cal] == classes.index(protocol["normal_class"]))),
            "candidate_rare_stage_calibration_labels_used_for_thresholds": 0, "conformal_control_all_calibration_labels": len(cal), "new_labels_collected": 0}, "label cost")
    status = "INCOMPLETE" if missing else "COMPLETE"
    require(complete["run_status"] == status, "Completion status mismatch")
    return {"audit_status": "PASS", "run_status": status, "audited_pair_count": len(expected_rows), "experiment": protocol["experiment"],
            "artifact_hashes": {name: digest(run_root / name) for name in ("AGGREGATE.json", "PREFIT_RECEIPT.json", "COMPLETE.json", "SOURCE_ANALYSIS.json", "ROUTING_PRIVATE.npz")},
            "protocol_sha256": PROTOCOL_HASH, "runner_sha256": RUNNER_HASH, "audit_source_sha256": digest(Path(__file__)),
            "primary": actual_primary,
            "checks": ["Frozen protocol, code, input, source-cell and output hashes", "Full E1 source audit and fit-CV comparator", "Independent sorted finite-sample thresholds and strict tie handling", "Every saved candidate/control routing flag, FPR, workload and stage count", "Class-conditional LAC mappings", "Both-control, all-stage, each-seed FPR and completeness arithmetic"],
            "limitations": ["No model fitting, inference or human review was replayed.", "PASS verifies saved evidence; routing is not correct stage identification or successful human adjudication.", "No novelty, independence, deployment coverage, false-alarm or missed-attack guarantee is established."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepared", "run", "protocol", "e1-protocol", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.prepared, args.run, args.protocol, args.e1_protocol)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "AUDIT.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"audit_status": result["audit_status"], "run_status": result["run_status"], "paired_seeds": result["audited_pair_count"]}))


if __name__ == "__main__":
    main()
