"""Read-only audit of saved CPU prescreen artifacts; never fits or predicts.

Weighted scores use sklearn sample_weight independently of the runner's manual
confusion formulas. Provenance/rosters and primary arithmetic are reconstructed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score,
                             confusion_matrix, precision_recall_fscore_support,
                             roc_auc_score)

from .audit_e3 import compare, digest, require
from .analyze_e1 import fit_support, probabilities, recompute_metrics, check_reported_metrics, validate_cv

BASELINES = ("random_forest", "xgboost", "lightgbm")
FOUNDATIONS = ("tabicl_v2", "tabpfn_2_5_synthetic")


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def check_arrays(actual, expected):
    for key, value in expected.items():
        require(key in actual and np.array_equal(actual[key], value), f"Array mismatch: {key}")


def score(y, p, classes, weights=None):
    p, y = probabilities(p, y, len(classes))
    if weights is not None:
        require(weights.shape == y.shape and np.isfinite(weights).all() and (weights > 0).all(), "Invalid weights")
    predicted = p.argmax(axis=1)
    pr, re, f1, support = precision_recall_fscore_support(y, predicted, labels=np.arange(len(classes)), sample_weight=weights, zero_division=0)
    stage = {}
    for k, name in enumerate(classes):
        truth = y == k
        stage[name] = {"precision": float(pr[k]), "recall": float(re[k]), "f1": float(f1[k]),
                       "support": float(support[k]) if weights is not None else int(support[k]),
                       "roc_auc_ovr": float(roc_auc_score(truth, p[:, k], sample_weight=weights)) if truth.any() and (~truth).any() else None,
                       "average_precision_ovr": float(average_precision_score(truth, p[:, k], sample_weight=weights)) if truth.any() else None}
        if weights is not None:
            stage[name]["sample_support"] = int(truth.sum())
    aucs = [v["roc_auc_ovr"] for v in stage.values()]
    aps = [v["average_precision_ovr"] for v in stage.values()]
    result = {"n": len(y), "classes": classes, "accuracy": float(accuracy_score(y, predicted, sample_weight=weights)),
              "macro_f1": float(f1.mean()), "roc_auc_ovr_macro": float(np.mean(aucs)) if all(v is not None for v in aucs) else None,
              "average_precision_ovr_macro": float(np.mean(aps)) if all(v is not None for v in aps) else None,
              "confusion_matrix": confusion_matrix(y, predicted, labels=np.arange(len(classes)), sample_weight=weights).tolist(), "per_stage": stage}
    if weights is not None:
        result["represented_weight_sum"] = float(weights.sum())
    return result


def verify_scores(cell, y, p, classes, weights):
    for key, w in (("query_unweighted_metrics", None), ("prevalence_weighted_estimated_metrics", weights)):
        reported = {k: v for k, v in cell[key].items() if k != "interpretation"}
        compare(reported, score(y, p, classes, w), key)
    mistakes = (y == classes.index("NormalTraffic")) & (p.argmax(axis=1) != classes.index("NormalTraffic"))
    compare(cell["sampled_benign_false_positives"], int(mistakes.sum()), "benign false positives")
    compare(cell["estimated_original_test_benign_false_positives"], float(weights[mistakes].sum()), "weighted benign false positives")


def verify_primary(cells, protocol, reported):
    roster = {(c["model"], c["seed"]): c for c in cells}
    require(len(roster) == len(cells) == 15, "Expected 15 unique model/seed cells")
    pairs = []
    for seed in protocol["seeds"]:
        require(all((model, seed) in roster for model in BASELINES + FOUNDATIONS), "Missing required foundation/baseline cell")
        xgb, lgb = (roster[(name, seed)] for name in ("xgboost", "lightgbm"))
        baseline = xgb if xgb["inner_cv_selected_macro_f1"] >= lgb["inner_cv_selected_macro_f1"] else lgb
        a = roster[(protocol["primary_candidate"], seed)]["prevalence_weighted_estimated_metrics"]
        b = baseline["prevalence_weighted_estimated_metrics"]
        pairs.append({"seed": seed, "comparator_selected_by_e1_inner_cv": baseline["model"],
                      "candidate_weighted_estimated_macro_f1": a["macro_f1"], "comparator_weighted_estimated_macro_f1": b["macro_f1"],
                      "weighted_estimated_macro_f1_delta": a["macro_f1"] - b["macro_f1"],
                      "high_risk_recall_deltas": {name: a["per_stage"][name]["recall"] - b["per_stage"][name]["recall"] for name in protocol["high_risk_classes"]}})
    delta = float(np.mean([p["weighted_estimated_macro_f1_delta"] for p in pairs]))
    recall = {name: float(np.mean([p["high_risk_recall_deltas"][name] for p in pairs])) for name in protocol["high_risk_classes"]}
    guards = {"mean_weighted_estimated_macro_f1_gain_at_least_0.02": delta >= protocol["macro_f1_delta_min"],
              **{name + "_mean_recall_loss_at_most_0.05": value >= protocol["mean_recall_delta_min"] for name, value in recall.items()}}
    expected = {"status": "PRELIMINARY_PROMISING" if all(guards.values()) else "PRELIMINARY_NEGATIVE", "primary_candidate": protocol["primary_candidate"],
                "paired_seed_count": 3, "required_paired_seeds": 3, "mean_weighted_estimated_macro_f1_delta": delta,
                "mean_high_risk_recall_deltas": recall, "guards": guards, "pairs": pairs}
    compare({k: v for k, v in reported.items() if k != "interpretation"}, expected, "primary summary")
    return expected


def verify_complete(directory, binding, comparison):
    completion = read(directory / "COMPLETE.json")
    require(completion["execution_binding"] == binding and completion["comparison_binding"] == comparison, "Cell completion binding mismatch")
    require(set(completion["file_sha256"]) == {"CELL.json", "PREDICTIONS.npz"}, "Wrong cell artifact roster")
    for name, claimed in completion["file_sha256"].items():
        require(digest(directory / name) == claimed, f"Cell hash differs: {name}")
    cell = read(directory / "CELL.json")
    require(cell["execution_binding"] == binding and cell["comparison_binding"] == comparison, "Cell binding mismatch")
    require(cell["prediction_sha256"] == digest(directory / "PREDICTIONS.npz"), "Prediction checksum mismatch")
    return cell, arrays(directory / "PREDICTIONS.npz")


def audit(prepared, run_root, baselines, protocol_path, e1_protocol_path):
    prepared, run_root, baselines = map(Path, (prepared, run_root, baselines))
    protocol_path, e1_protocol_path = map(Path, (protocol_path, e1_protocol_path))
    protocol, e1 = read(protocol_path), read(e1_protocol_path)
    prefit, complete, aggregate = (read(run_root / name) for name in ("PREFIT_RECEIPT.json", "COMPLETE.json", "AGGREGATE.json"))
    ex = prefit["execution"]; binding = canonical(ex)
    require(binding == prefit["execution_binding"] == prefit["binding_sha256"] == complete["execution_binding"] == complete["binding_sha256"], "Global execution binding mismatch")
    require(prefit["foundation_classification_outcomes_observed_at_freeze"] is False and prefit["classical_results_already_known"] is True, "Rescope receipt differs")
    require(protocol["seeds"] == [20260921, 20260922, 20260923] and protocol["status"] == "FROZEN_BEFORE_FOUNDATION_CLASSIFICATION_OUTCOMES", "Unexpected protocol")
    require(digest(protocol_path) == ex["protocol_sha256"] == aggregate["protocol_sha256"], "Protocol hash differs")
    require(digest(e1_protocol_path) == protocol["e1_protocol_sha256"] == ex["e1_protocol_sha256"], "E1 protocol hash differs")
    for field, name in (("data_npz_sha256", "DATA.npz"), ("manifest_sha256", "MANIFEST.json")):
        require(all(record[field] == digest(prepared / name) for record in (ex, protocol, e1)), f"Input checksum mismatch: {name}")
    source = Path(__file__).parent
    require(set(ex["code_sha256"]) == {"run_e1_cpu_prescreen.py", "run_e1.py", "model_backend.py", "analyze_e1.py", "requirementsfoundation.txt"}, "Wrong source roster")
    for name, claimed in ex["code_sha256"].items():
        require(digest(source / name) == claimed, f"Source changed: {name}")
    require(set(complete["artifact_sha256"]) == {"PREFIT_RECEIPT.json", "BASELINE_QUERY_PRIVATE.npz", "AGGREGATE.json"}, "Wrong global artifact roster")
    for name, claimed in complete["artifact_sha256"].items():
        require(digest(run_root / name) == claimed, f"Global artifact changed: {name}")
    require(aggregate["prefit_receipt_sha256"] == digest(run_root / "PREFIT_RECEIPT.json"), "Wrong aggregate prefit receipt")
    data = arrays(prepared / "DATA.npz"); classes = data["classes"].tolist()
    y, groups = data["y"], data["group_sha256"]
    test = np.flatnonzero(data["split"] == 2); normal = classes.index("NormalTraffic")
    benign = test[y[test] == normal]; attacks = test[y[test] != normal]
    rank = lambda i: hashlib.sha256((protocol["query_hash_tag"] + "|" + str(groups[i])).encode("ascii")).digest()
    queries = np.asarray(sorted([*attacks.tolist(), *sorted(benign.tolist(), key=rank)[:protocol["normal_query_rows"]]], key=rank), dtype=np.int64)
    weights = np.where(y[queries] == normal, len(benign) / protocol["normal_query_rows"], 1.)
    require(len(attacks) == protocol["expected_attack_query_rows"] == 858 and len(benign) == protocol["expected_original_normal_rows"] == 29929 and len(queries) == 1882, "Query counts differ")
    query_arrays = {"query_indices": queries, "query_y": y[queries], "query_fingerprints": groups[queries], "query_weights": weights, "classes": data["classes"]}
    check_arrays(ex, {k: v for k, v in query_arrays.items() if k in ex})
    packet = arrays(run_root / "BASELINE_QUERY_PRIVATE.npz"); check_arrays(packet, query_arrays)
    compare(aggregate["query"], prefit["query"], "query description")
    for key, value in {"rows": len(queries), "attack_rows": len(attacks), "normal_rows": 1024, "original_test_normal_rows": len(benign), "normal_weight": len(benign)/1024, "represented_weight_sum": float(weights.sum())}.items():
        compare(aggregate["query"][key], value, key)
    supports = {str(seed): fit_support(data, seed, protocol["samples_per_class"]) for seed in protocol["seeds"]}
    support_records = {seed: {"indices": ids.tolist(), "fingerprints": groups[ids].tolist()} for seed, ids in supports.items()}
    compare(ex["supports"], support_records, "supports")
    original_prefit = read(baselines / "PREFIT_RECEIPT.json"); bx = original_prefit["execution"]
    require(canonical(bx) == original_prefit["execution_binding"], "Baseline prefit binding differs")
    require(ex["baselines"]["prefit_sha256"] == digest(baselines / "PREFIT_RECEIPT.json"), "Wrong baseline prefit hash")
    common = {key: bx[key] for key in ("data_sha256", "manifest_sha256", "protocol_sha256", "code_sha256")}
    require(common["data_sha256"] == protocol["data_npz_sha256"] and common["manifest_sha256"] == protocol["manifest_sha256"] and common["protocol_sha256"] == digest(e1_protocol_path), "Baseline inputs differ")
    require(set(common["code_sha256"]) == {"run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt"}, "Baseline source roster differs")
    for name, claimed in common["code_sha256"].items():
        require(digest(source / name) == claimed, "Baseline source changed")
    cells = aggregate["cells"]; roster = {(c["model"], c["seed"]): c for c in cells}
    require(len(cells) == len(roster) == 15, "Expected fifteen unique cells")
    positions = np.searchsorted(test, queries); require(np.array_equal(test[positions], queries), "Query mapping failed")
    checkpoint_hashes = {}
    expected_completions = {f"{model}/{seed}" for model in FOUNDATIONS for seed in protocol["seeds"]}
    require(set(complete["cell_complete_sha256"]) == expected_completions and aggregate["foundation_cell_count"] == 6, "Six foundation completions required")
    for seed in protocol["seeds"]:
        ids = supports[str(seed)]; support_record = support_records[str(seed)]
        compare(bx["supports"][str(seed)], support_record, "baseline support")
        for model in BASELINES + FOUNDATIONS:
            require((model, seed) in roster, "Missing model/seed")
            reported = roster[(model, seed)]
            directory = (baselines if model in BASELINES else run_root) / "cells" / model / str(seed)
            comparison = canonical({**common, "seed": seed, "support": support_record}) if model in BASELINES else canonical({"execution_binding": binding, "seed": seed, "model": model})
            cell, saved = verify_complete(directory, original_prefit["execution_binding"] if model in BASELINES else binding, comparison)
            require(cell["model"] == model and cell["seed"] == seed, "Cell identity differs")
            check_arrays(saved, {"classes": data["classes"], "selected_fit_indices": ids, "selected_fit_fingerprints": groups[ids]})
            if model in BASELINES:
                compare(cell["common_binding"], common, "baseline common binding")
                require(cell["prefit_receipt_sha256"] == ex["baselines"]["prefit_sha256"] and cell["selected_fit_fingerprints_sha256"] == canonical(support_record["fingerprints"]), "Baseline receipt differs")
                check_arrays(saved, {"test_indices": test, "test_y": y[test]})
                full = recompute_metrics(y[test], saved["test_probabilities"], classes)
                check_reported_metrics(cell["metrics"]["test"], full)
                compare(reported["baseline_full_test_metrics"], full, "full baseline metrics")
                compare(reported["inner_cv_selected_macro_f1"], validate_cv(cell, e1), "CV selected score")
                p = saved["test_probabilities"][positions]
                check_arrays(packet, {f"{model}_{seed}": p})
                compare(reported["baseline_weighted_minus_full_test_macro_f1"], score(y[queries], p, classes, weights)["macro_f1"] - full["macro_f1"], "sample/full discrepancy")
                evidence = ex["baselines"]["cells"][f"{model}_{seed}"]
                compare(evidence, {"complete_sha256": digest(directory / "COMPLETE.json"), "cell_sha256": digest(directory / "CELL.json"), "predictions_sha256": digest(directory / "PREDICTIONS.npz"), "comparison_binding": comparison}, "baseline evidence")
            else:
                compare(cell, reported, "foundation aggregate cell")
                require(complete["cell_complete_sha256"][f"{model}/{seed}"] == digest(directory / "COMPLETE.json"), "Foundation completion hash differs")
                require(cell["prefit_receipt_sha256"] == digest(run_root / "PREFIT_RECEIPT.json"), "Foundation prefit hash differs")
                require(cell["backend_private_sha256"] == digest(directory / "BACKEND_PRIVATE.json"), "Backend receipt hash differs")
                check_arrays(saved, query_arrays); p = saved["probabilities"]
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    medians = np.nanmedian(data["X"][ids], axis=0)
                medians[np.isnan(medians)] = 0
                check_arrays(saved, {"imputer_statistics": medians})
                backend = read(directory / "BACKEND_PRIVATE.json"); spec = backend["checkpoint"]
                compare(cell["checkpoint"], ex["checkpoints"][model], "checkpoint binding")
                compare(cell["checkpoint"], {k: spec[k] for k in ("sha256", "revision", "filename")}, "checkpoint spec")
                checkpoint_path = Path(backend["constructor_settings"]["model_path"])
                if model not in checkpoint_hashes:
                    require(checkpoint_path.stat().st_size == spec["size_bytes"], "Checkpoint size differs")
                    checkpoint_hashes[model] = digest(checkpoint_path)
                require(checkpoint_hashes[model] == spec["sha256"] and backend["fitted"] is True and backend["runtime_compatibility_tested"] is True, "Checkpoint/runtime receipt differs")
                require(backend["constructor_settings"]["n_estimators"] == 4 and cell["actual_device"] == "cpu" and cell["cpu_threads"] == 4 and cell["prediction_chunk_rows"] == 1024 and cell["selected_fit_rows"] == 192, "Execution scope differs")
                compare(cell["versions"], ex["versions"], "versions")
            verify_scores(reported, y[queries], p, classes, weights)
    summaries = {}
    for model in BASELINES + FOUNDATIONS:
        subset = [roster[(model, seed)] for seed in protocol["seeds"]]
        summary = {"seed_count": 3, "mean_query_unweighted_macro_f1": float(np.mean([c["query_unweighted_metrics"]["macro_f1"] for c in subset])),
                   "mean_prevalence_weighted_estimated_macro_f1": float(np.mean([c["prevalence_weighted_estimated_metrics"]["macro_f1"] for c in subset]))}
        if model in BASELINES:
            summary.update(mean_baseline_full_test_macro_f1=float(np.mean([c["baseline_full_test_metrics"]["macro_f1"] for c in subset])),
                           mean_weighted_estimate_minus_full_test_macro_f1=float(np.mean([c["baseline_weighted_minus_full_test_macro_f1"] for c in subset])))
        summaries[model] = summary
    compare(aggregate["model_summaries"], summaries, "model summaries")
    primary = verify_primary(cells, protocol, aggregate["primary_descriptive"])
    require(all(aggregate[key] is False for key in ("full_e1_completed", "e4_evaluated", "gpu_evaluated")), "Unperformed experiment claimed")
    return {"audit_status": "PASS", "run_status": "COMPLETE", "experiment": "E1_CPU_PRESCREEN", "audited_cell_count": 15, "foundation_cell_count": 6,
            "artifact_hashes": {name: digest(run_root / name) for name in ("AGGREGATE.json", "PREFIT_RECEIPT.json", "COMPLETE.json", "BASELINE_QUERY_PRIVATE.npz")},
            "input_hashes": {name: digest(prepared / name) for name in ("DATA.npz", "MANIFEST.json")},
            "audit_source_sha256": digest(Path(__file__)), "checkpoint_hashes": checkpoint_hashes,
            "primary_descriptive": primary, "model_summaries": summaries,
            "checks": ["Input, protocol, source, checkpoint, global and cell hashes", "Query/support reconstruction and exact baseline source mapping", "All 15 weighted/unweighted score tables, confusion, AUC/AP and false alarms", "Nine original full-test baseline score tables and CV selections", "Three paired primary guards and model summary arithmetic"],
            "limitations": ["Read-only artifact/source audit; fitting, inference and timings were not replayed.", "PASS verifies saved arithmetic and provenance; it does not independently attest historical execution or create scientific confirmation.", "Weights produce sampled-prevalence estimates; full E1, E4 and GPU evaluation remain incomplete. Query batch invariance is unverified."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepared", "run", "baselines", "protocol", "e1-protocol", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.prepared, args.run, args.baselines, args.protocol, args.e1_protocol)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "AUDIT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"audit_status": result["audit_status"], "primary_descriptive": result["primary_descriptive"]}))


if __name__ == "__main__":
    main()
