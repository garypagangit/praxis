"""Independent audit of six fixed normal-calibrated MAGIC development cases.

No calibrated worker functions are imported. Thresholds use exact rational ranks;
metrics use sorted ties and direct confusion counts. Every qualification query,
eight calibration queries and eight test queries use the full original fit bank.
Neural training/inference and execution timings are not independently rerun.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import re
import time

import numpy as np

from ...magic_reproduction.analysis import audit as core
from ...magic_reproduction.analysis.compact_audit import COMPACT_FILES

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]
ORIGINAL = HERE.parent / "magic_reproduction"
COMPACT = HERE.parent / "magic_compact"
OWN_FILES = {"experiments/apt_final/magic_calibrated/" + name for name in
             ("PROTOCOL.md", "config.json", "worker.py", "provenance.py", "launch.py", "run_cloud.sh")}
NORMAL_FILES = {"epoch_001.pt", "epoch_050.pt", "EPOCHS.json", "QUALIFICATION_FIT_EMBEDDINGS.npz",
                "QUALIFICATION.json", "FIT_EMBEDDINGS.npz", "CALIBRATION.npz"}
require, read, digest, bound, hashed, close = core.require, core.read, core.digest, core.bound, core.hashed, core.close


def verify_inputs(data_dir, source_dir, registration):
    old, manifest, _, runtime = core.verify_inputs(data_dir, source_dir, ORIGINAL / "REGISTRATION.json")
    compact = read(COMPACT / "REGISTRATION.json")
    require(compact["status"] == "FROZEN_EXACT_MULTIPLICITY_RUNTIME"
            and compact["original_registration_sha256"] == digest(ORIGINAL / "REGISTRATION.json")
            and compact["original_source_commit"] == old["source_commit"]
            and compact["science_changed"] is False and compact["checkpoint_reuse"] is False
            and compact["exact_duplicate_storage_only"] is True and compact["novelty_claimed"] is False,
            "Original/compact parent chain mismatch")
    require(set(compact["code_hashes"]) == COMPACT_FILES, "Compact parent source inventory mismatch")
    for rel, sha in compact["code_hashes"].items():
        hashed(REPO, rel, sha)
    record = read(registration)
    parents = {p.relative_to(REPO).as_posix(): digest(p) for p in
               (ORIGINAL / "REGISTRATION.json", COMPACT / "REGISTRATION.json")}
    expected = {**old["code_hashes"], **compact["code_hashes"], **{r: digest(bound(REPO, r)) for r in OWN_FILES}}
    require(record["status"] == "FROZEN_NORMAL_CALIBRATED_MAGIC_DEVELOPMENT"
            and record["code_hashes"] == expected and record["parent_registrations"] == parents,
            "Calibrated source/parent registration mismatch")
    require(record["data_files"] == old["data_files"] and record["upstream_files"] == old["upstream_files"]
            and record["source_manifest_sha256"] == old["source_manifest_sha256"]
            and record["upstream_commit"] == old["upstream_commit"]
            and record["original_source_commit"] == old["source_commit"]
            and record["compact_source_commit"] == compact["source_commit"], "Calibrated data/source chain mismatch")
    require(record["test_previously_exposed"] is True and record["confirmation_claimed"] is False
            and record["novelty_claimed"] is False and re.fullmatch("[0-9a-f]{40}", record["source_commit"]), "Incorrect evidence scope")
    config = read(HERE / "config.json")
    require(config["datasets"] == ["theia", "cadets"] and config["seeds"] == [0, 101, 211]
            and config["training"]["epochs"] == 50 and config["calibration"] == {"alpha": .01}
            and config["gates"] == {"min_recall": .5, "max_benchmark_negative_fpr": .02}, "Frozen six-case design differs")
    for spec in config["dataset_specs"].values():
        require(spec["train_graphs"] == ["train0", "train1", "train2"]
                and spec["calibration_graph"] == "train3" and spec["test_graph"] == "test0", "Partition leakage")
    return record, manifest, config, runtime


def threshold_from_scores(scores, alpha):
    scores = np.asarray(scores)
    require(scores.ndim == 1 and len(scores) and np.isfinite(scores).all() and np.all(scores >= 0), "Invalid calibration scores")
    tail = Fraction(str(alpha))
    require(0 < tail < 1, "Invalid calibration alpha")
    rank_fraction = (len(scores) + 1) * (1 - tail)
    rank = (rank_fraction.numerator + rank_fraction.denominator - 1) // rank_fraction.denominator
    value = None if rank > len(scores) else float(np.partition(scores, rank - 1)[rank - 1])
    alerts = np.zeros(len(scores), dtype=bool) if value is None else scores > value
    return {"alpha": float(alpha), "n": len(scores), "rank_one_based": rank, "threshold": value,
            "comparison": "strict_greater_than", "no_alerts": value is None,
            "fit_uses_only_calibration_normal_scores": True, "independent_normal_validation": False,
            "calibration_alerts": int(alerts.sum()), "calibration_alert_rate": float(alerts.mean()),
            "calibration_ties_at_threshold": 0 if value is None else int(np.count_nonzero(scores == value))}


def verify_threshold(observed, expected):
    require(set(observed) == set(expected), "Threshold receipt schema mismatch")
    integer_fields = {"n", "rank_one_based", "calibration_alerts", "calibration_ties_at_threshold"}
    for key, value in expected.items():
        if value is None or isinstance(value, (str, bool)):
            require(observed[key] == value and (not isinstance(value, bool) or observed[key] is value), "Threshold policy mismatch: " + key)
        elif key in integer_fields:
            require(type(observed[key]) is int and observed[key] == value, "Exact threshold integer mismatch: " + key)
        else:
            # Sorting and partition select the same stored float64 element. Even
            # one ULP can change a strict comparison, so tolerances are unsafe.
            require(type(observed[key]) in {float, int} and np.isfinite(observed[key])
                    and observed[key] == value, "Exact normal threshold mismatch: " + key)


def fixed_metrics(y, scores, threshold):
    y, scores = np.asarray(y), np.asarray(scores)
    require(y.ndim == 1 and y.shape == scores.shape and np.isfinite(scores).all()
            and set(np.unique(y)) == {0, 1}, "Invalid labeled scores")
    predicted = np.zeros(len(scores), dtype=bool) if threshold["no_alerts"] else scores > threshold["threshold"]
    positive = y == 1
    tp, fp = int(np.count_nonzero(predicted & positive)), int(np.count_nonzero(predicted & ~positive))
    fn, tn = int(np.count_nonzero(~predicted & positive)), int(np.count_nonzero(~predicted & ~positive))
    order = np.argsort(scores, kind="stable")
    _, starts, count = np.unique(scores[order], return_index=True, return_counts=True)
    positives = np.add.reduceat(y[order].astype(np.int64), starts)
    negatives = count - positives
    total_positive, total_negative = int(positives.sum()), int(negatives.sum())
    negative_below = np.r_[0, np.cumsum(negatives)[:-1]]
    true_above = total_positive - np.r_[0, np.cumsum(positives)[:-1]]
    all_above = len(scores) - np.r_[0, np.cumsum(count)[:-1]]
    auc = float(np.sum(positives * (negative_below + .5 * negatives)) / (total_positive * total_negative))
    ap = float(np.sum(positives / total_positive * (true_above / all_above)))
    return predicted, {"n": len(y), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else 0., "recall": tp / (tp + fn),
        "false_positive_rate": fp / (fp + tn), "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
        "auroc": auc, "average_precision": ap, "threshold_selected_using_test_labels": False}


def resource_gate(q, spec, config, prior_reserve):
    gate, timing, embeddings = q["resource_gate"], q["full_reference_sample_timing"], q["training_embeddings"]
    rows = embeddings["rows"]
    transfer = core.finite(q["bank_construction_transfer_seconds"], "bank transfer")
    serialize = core.finite(q["saved_embeddings"]["seconds"], "bank serialization")
    rate = core.finite(timing["seconds"], "scoring seconds") / timing["query_rows"]
    node_time = max(core.finite(g["seconds"], "embedding seconds") / g["nodes"] for g in embeddings["graphs"])
    remaining = core.finite(gate["remaining_science_seconds"], "science remainder")
    m, safety = config["resources"]["estimate_multiplier"], config["resources"]["safety_seconds"]
    normal = ((config["training"]["epochs"] - 1) * core.finite(q["epoch"]["seconds"], "epoch seconds") + embeddings["seconds"]
              + 2 * node_time * spec["expected_calibration_nodes"] + rate * spec["expected_calibration_nodes"]
              + transfer + serialize * (1 + spec["expected_calibration_nodes"] / rows)) * m
    test = (rate * spec["expected_test_nodes"] + 2 * node_time * spec["expected_test_nodes"]
            + transfer + serialize * spec["expected_test_nodes"] / rows) * m
    available, total = max(0., remaining - prior_reserve), normal + test + safety
    expected = {"estimated_remaining_normal_seconds": normal, "reserved_test_seconds": test,
                "prior_cases_reserved_test_seconds": prior_reserve, "available_after_prior_test_reserve": available,
                "estimated_total_with_safety_seconds": total, "estimate_multiplier": m, "safety_seconds": safety,
                "test_rows_from_config_only": spec["expected_test_nodes"], "author_normalizer_queries": 0}
    for key, value in expected.items(): close(gate[key], value, "resource " + key)
    status = "PASS" if total <= available else "NOT_RUN_RESOURCE_HOLD"
    require(gate["status"] == status and gate["test_arrays_or_labels_accessed"] is False, "Resource decision/test access mismatch")
    require(transfer + 1e-9 >= timing["construction_seconds"], "Compact construction omitted from budget")
    return {"status": status, **expected, "timing_observations_independently_remeasured": False}


def check_timing(timing, rows, queries, k):
    require(timing["reference_rows"] == rows and timing["query_rows"] == queries and timing["k"] == k
            and timing["reference_sampling"] is False and timing["reference_duplicates_preserved"] is True
            and timing["integer_multiplicities_preserved"] is True and timing["reference_occurrences_preserved"] == rows,
            "Distance population/multiplicity mismatch")


def normal_case(output, case, config, manifest, bindings, prior_reserve):
    name, dataset, seed = case["case"], case["dataset"], case["seed"]
    require(name == f"{dataset}/seed_{seed}", "Case identity mismatch")
    directory, spec = output / name, config["dataset_specs"][dataset]
    planned_epochs = config["training"]["epochs"]
    graphs = {g["npz"].split("/")[-1].removesuffix(".npz"): g for d in manifest["datasets"]
              if d["dataset"] == dataset for g in d["graphs"]}
    sizes = [graphs[g]["n_nodes"] for g in spec["train_graphs"]]
    rows, dimension = sum(sizes), config["training"]["hidden_dim"]
    require(graphs["train3"]["n_nodes"] == spec["expected_calibration_nodes"]
            and graphs["test0"]["n_nodes"] == spec["expected_test_nodes"], "Declared held-out rows differ")
    local_binding = {**bindings, "case": name, "seed": seed}
    report = {"case": name, "dataset": dataset, "seed": seed, "normal_complete": case["normal_complete"], "evaluation_complete": False,
              "completed_epochs": case["completed_epochs"], "checkpoint_checks": []}
    if not directory.exists():
        require(case["status"] == "NOT_RUN_RESOURCE_HOLD" and case["completed_epochs"] == 0
                and case["normal_complete"] is False and case["evaluation_complete"] is False
                and case["test_arrays_loaded"] is False and case["test_labels_loaded"] is False, "Missing case directory for claimed work")
        return report, {}, 0.
    epochs = read(bound(directory, "EPOCHS.json"))
    require([e["epoch"] for e in epochs] == list(range(1, case["completed_epochs"] + 1))
            and 0 <= len(epochs) <= planned_epochs, "Epoch history mismatch")
    for epoch in epochs:
        require([g["graph"] for g in epoch["graphs"]] == spec["train_graphs"], "Calibration/test graph entered fitting")
        for g in epoch["graphs"]:
            require(g["nodes"] == graphs[g["graph"]]["n_nodes"] and g["edges"] == graphs[g["graph"]]["n_edges"], "Fit graph population mismatch")
            core.finite(g["scaled_loss"], "scaled training loss")
            core.finite(g["seconds"], "graph training time")
        close(epoch["epoch_loss"], sum(g["scaled_loss"] for g in epoch["graphs"]), "epoch loss")
    shapes = None
    for number, filename in ((1, "epoch_001.pt"), (planned_epochs, "epoch_050.pt")):
        path = directory / filename
        if path.is_file():
            require(len(epochs) >= number, "Checkpoint predates its claimed completed epoch")
            shapes, detail = core.checkpoint(path, number, local_binding, shapes)
            report["checkpoint_checks"].append(detail)
        elif (number == 1 and len(epochs)) or case["normal_complete"]:
            raise core.AuditError("Required safe checkpoint missing")
    if (directory / "QUALIFICATION.json").is_file():
        q = read(directory / "QUALIFICATION.json")
        require(q["case"] == name and q["bindings"] == local_binding and q["test_arrays_loaded"] is False
                and q["test_labels_loaded"] is False, "Qualification binding/test boundary mismatch")
        require(q["epoch"] == {k: v for k, v in epochs[0].items() if k != "epoch"}, "Qualification first epoch mismatch")
        embeddings = q["training_embeddings"]
        require(embeddings["rows"] == rows and [g["graph"] for g in embeddings["graphs"]] == spec["train_graphs"]
                and [g["nodes"] for g in embeddings["graphs"]] == sizes, "Qualification bank includes non-fit rows")
        saved = q["saved_embeddings"]
        require(saved["file"] == "QUALIFICATION_FIT_EMBEDDINGS.npz" and saved["rows"] == rows and saved["dimension"] == dimension,
                "Qualification bank receipt mismatch")
        path = hashed(directory, saved["file"], saved["sha256"])
        bank, _, _ = core.standardize(path, rows, dimension)
        with np.load(path, allow_pickle=False) as z:
            ids, distances, small_bank = z["sample_indices"], z["sample_distances"], z["numerical_bank_indices"]
        rng = np.random.default_rng(90210)
        require(np.array_equal(ids, rng.choice(rows, min(config["knn"]["qualification_queries"], rows), replace=False))
                and np.array_equal(small_bank, rng.choice(rows, min(512, rows), replace=False)), "Qualification sample changed")
        check_timing(q["full_reference_sample_timing"], rows, len(ids), spec["k"])
        report["qualification_distances"] = core.sample_check(bank, bank[ids], distances, spec["k"], config["knn"], "qualification", count=None)
        report["resource_gate"] = resource_gate(q, spec, config, prior_reserve)
        require(q["resource_gate"] == case["resource_gate"], "Case/qualification resource mismatch")
        del bank
    if not case["normal_complete"]:
        require(case["evaluation_complete"] is False and case["test_arrays_loaded"] is False
                and case["test_labels_loaded"] is False, "Test accessed after incomplete normal case")
        if case["status"] == "NOT_RUN_RESOURCE_HOLD" and len(epochs):
            require(len(epochs) == 1 and report["resource_gate"]["status"] == "NOT_RUN_RESOURCE_HOLD", "Contradictory resource hold")
        return report, {}, 0.
    require(len(epochs) == planned_epochs and report["resource_gate"]["status"] == "PASS", "Normal completion without full training/qualification")
    normal = read(bound(directory, "NORMAL_RESULT.json"))
    require(normal["status"] == "NORMAL_COMPLETE_FROZEN"
            and normal["test_arrays_loaded"] is False and normal["test_labels_loaded"] is False, "Normal phase receipt mismatch")
    status = read(bound(directory, "STATUS.json"))
    expected_status = dict(normal)
    if case.get("test_access_attempted"):
        expected_status.update(test_access_attempted=True, status="TEST_ACCESS_ATTEMPTED")
        if case["test_arrays_loaded"]:
            expected_status.update(test_arrays_loaded=True, test_labels_loaded=True, status="TEST_ARRAYS_LOADED")
    require(status == expected_status, "Test access phase receipt mismatch")
    mutable = {"status", "evaluation_complete", "test_arrays_loaded", "test_labels_loaded", "test_access_attempted"}
    require(all(case.get(key) == value for key, value in normal.items() if key not in mutable), "Evaluation changed a frozen normal result")
    freeze_path = hashed(directory, "FIT_CALIBRATION_FREEZE.json", case["freeze_sha256"])
    freeze = read(freeze_path)
    require(freeze["case"] == name and freeze["dataset"] == dataset and freeze["seed"] == seed
            and freeze["bindings"] == local_binding and freeze["completed_epochs"] == planned_epochs
            and freeze["fit_graphs"] == spec["train_graphs"] and freeze["calibration_graph"] == "train3"
            and freeze["test_arrays_loaded"] is False and freeze["test_labels_loaded"] is False
            and freeze["fit_rows"] == rows and set(freeze["artifacts"]) == NORMAL_FILES, "Fit/calibration freeze contract mismatch")
    inventory = {}
    for relative, sha in freeze["artifacts"].items():
        hashed(directory, relative, sha)
        inventory[name + "/" + relative] = sha
    inventory[name + "/FIT_CALIBRATION_FREEZE.json"] = digest(freeze_path)
    inventory[name + "/NORMAL_RESULT.json"] = digest(directory / "NORMAL_RESULT.json")
    require(freeze["checkpoint"]["file"] == "epoch_050.pt" and freeze["checkpoint"]["completed_epochs"] == planned_epochs
            and freeze["checkpoint"]["sha256"] == freeze["artifacts"]["epoch_050.pt"], "Final checkpoint receipt mismatch")
    saved = freeze["fit_embeddings"]
    require(saved["file"] == "FIT_EMBEDDINGS.npz" and saved["sha256"] == freeze["artifacts"][saved["file"]]
            and saved["rows"] == rows and saved["dimension"] == dimension, "Fit bank receipt mismatch")
    bank, mean, scale = core.standardize(directory / saved["file"], rows, dimension)
    with np.load(directory / saved["file"], allow_pickle=False) as z:
        require(np.array_equal(z["graph_sizes"], sizes), "Fit bank graph boundaries changed")
    with np.load(directory / "CALIBRATION.npz", allow_pickle=False) as z:
        cal_raw, scores = z["raw"], z["scores"]
    require(cal_raw.dtype == np.float32 and cal_raw.shape == (spec["expected_calibration_nodes"], dimension)
            and np.isfinite(cal_raw).all() and scores.shape == (len(cal_raw),), "Invalid calibration rows")
    check_timing(normal["calibration_timing"], rows, len(cal_raw), spec["k"])
    report["calibration_distances"] = core.sample_check(bank, (cal_raw - mean) / scale, scores, spec["k"], config["knn"], "calibration")
    expected = threshold_from_scores(scores, config["calibration"]["alpha"])
    for actual in (freeze["threshold"], normal["threshold"], case["threshold"]): verify_threshold(actual, expected)
    require(normal["calibration"] == {"rows": len(scores), "alert_count": expected["calibration_alerts"],
            "alert_rate": expected["calibration_alert_rate"], "independent_normal_validation": False}, "Calibration summary mismatch")
    multiplier, ntest = config["resources"]["estimate_multiplier"], spec["expected_test_nodes"]
    reserve = (normal["calibration_timing"]["seconds"] / len(scores) * ntest
               + 2 * core.finite(normal["calibration_embedding_seconds"], "calibration embedding") / len(scores) * ntest
               + core.finite(normal["final_bank_construction_transfer_seconds"], "final bank construction")
               + core.finite(normal["calibration_serialization_seconds"], "calibration serialization") * ntest / len(scores)) * multiplier
    close(normal["reserved_test_seconds"], reserve, "updated test reserve")
    report.update(threshold=expected, updated_reserved_test_seconds=reserve, freeze_created_utc=freeze["created_utc"])
    return report, inventory, reserve


def evaluation(output, case, config, data_dir, bindings, global_hash):
    directory, spec = output / case["case"], config["dataset_specs"][case["dataset"]]
    require(case == read(bound(directory, "CASE_RESULT.json")) and case["status"] == "COMPLETE_FIXED_NORMAL_CALIBRATED_CASE"
            and case["global_freeze_sha256"] == global_hash and case["test_arrays_loaded"] is True
            and case["test_labels_loaded"] is True, "Case evaluation/freeze receipt mismatch")
    freeze = read(directory / "FIT_CALIBRATION_FREEZE.json")
    require(case["threshold"] == freeze["threshold"], "Evaluation changed threshold")
    bank, mean, scale = core.standardize(directory / "FIT_EMBEDDINGS.npz", freeze["fit_rows"], config["training"]["hidden_dim"])
    path = hashed(directory, "EVALUATION.npz", case["evaluation_sha256"])
    with np.load(path, allow_pickle=False) as z:
        raw, scores, y, predicted = z["raw"], z["scores"], z["y"], z["predicted"]
    require(raw.dtype == np.float32 and raw.shape == (spec["expected_test_nodes"], config["training"]["hidden_dim"])
            and np.isfinite(raw).all() and scores.shape == (len(raw),) and predicted.dtype == np.bool_, "Invalid evaluated arrays")
    with np.load(bound(data_dir, case["dataset"] + "/test0.npz"), allow_pickle=False) as z:
        require(np.array_equal(y, z["y"]), "Labels changed from original row indices")
    check_timing(case["scoring_timing"], len(bank), len(raw), spec["k"])
    distances = core.sample_check(bank, (raw - mean) / scale, scores, spec["k"], config["knn"], "test raw mean distances")
    expected_prediction, metrics = fixed_metrics(y, scores, freeze["threshold"])
    require(np.array_equal(predicted, expected_prediction), "Fixed-threshold predictions changed")
    require(set(case["metrics"]) == set(metrics) and case["metrics"]["threshold_selected_using_test_labels"] is False, "Test-selected threshold/metric schema")
    for key, value in metrics.items():
        if key != "threshold_selected_using_test_labels": close(case["metrics"][key], value, "metric " + key)
    ready = metrics["recall"] >= config["gates"]["min_recall"] and metrics["false_positive_rate"] <= config["gates"]["max_benchmark_negative_fpr"]
    require(case["readiness"] is ready, "Development readiness gate mismatch")
    return {"evaluation_complete": True, "test_distances": distances, "independent_metrics": metrics,
            "fixed_predictions_all_rows_verified": True, "development_readiness": ready}


def verify_environment(output, runtime, bindings):
    env = read(hashed(output, "WORKER_ENVIRONMENT.json", bindings["environment_sha256"]))
    require(env["python"].startswith(runtime["python"] + ".") and env["cuda"] == "12.1", "Runtime Python/CUDA mismatch")
    for key, field in (("torch", "torch"), ("dgl", "dgl"), ("numpy", "numpy"), ("sklearn", "scikit_learn")):
        require(env[key] == runtime[field], "Runtime package mismatch")
    bootstrap = read(bound(output, "ENVIRONMENT.json"))
    versions = {k: v for k, v in runtime.items() if k not in {"python", "wheel", "wheel_sha256", "wheel_url"}}
    require(bootstrap["dependency_versions"] == versions and bootstrap["python"].startswith(runtime["python"] + "."), "Bootstrap dependency mismatch")
    probe = read(bound(output, "RUNTIME_QUALIFICATION.json"))
    require(probe["status"] == "PASS" and probe["forward_backward_qualified"] is True
            and probe["encoder_normalizations"] == ["NoneType"] * 3
            and probe["normalization_fix_applied"] is False and probe["determinism_fix_applied"] is False, "Source runtime qualification failed")
    alias = probe["mask_target_alias_probe"]
    require(alias["shared_feature_storage"] is True and alias["masked_rows"] > 0
            and alias["masked_rows"] == alias["original_rows_changed"], "Author mask-target alias behavior changed")


def audit(output_dir, data_dir, source_dir, registration, *, bundle=None):
    started, output = time.perf_counter(), Path(output_dir).resolve(strict=True)
    record, manifest, config, runtime = verify_inputs(data_dir, source_dir, registration)
    observed = {p.relative_to(output).as_posix(): digest(bound(output, p.relative_to(output).as_posix()))
                for p in output.rglob("*") if p.is_file()}
    report = {"status": "INCOMPLETE_EVIDENCE", "evidence_audit_passed": False, "scientific_completion": False,
              "bounded_development_gate_pass": None, "novelty_claimed": False, "confirmation_claimed": False,
              "independent_normal_validation": False, "auditor_sha256": digest(__file__),
              "shared_auditor_sha256": digest(core.__file__), "checked_utc": datetime.now(timezone.utc).isoformat(),
              "input_hashes": {"registration": digest(registration), "outputs": observed}, "cases": [],
              "limitations": {"neural_training_or_inference_rerun": False, "independent_campaign_replication": False,
                              "timing_observations_remeasured": False, "AWS_shutdown_verified_here": False,
                              "qualifier_queries": "all saved qualification queries", "calibration_and_test_queries_each": 8}}
    if "RESULTS.json" not in observed:
        report["reason"] = "No final result: incomplete evidence, no efficacy conclusion."
        return report
    results = read(output / "RESULTS.json")
    inventory = {r: sha for r, sha in observed.items() if r not in core.OPERATIONAL | {"RESULTS.json"}}
    require(results["private_artifacts"] == inventory, "Private artifact inventory/hash mismatch")
    binding = results["bindings"]
    expected_binding = {"config_sha256": digest(HERE / "config.json"), "registration_sha256": digest(registration),
        "source_commit": record["source_commit"], "upstream_commit": record["upstream_commit"],
        "source_manifest_sha256": record["source_manifest_sha256"], "environment_sha256": observed["WORKER_ENVIRONMENT.json"],
        "data_manifest_sha256": record["data_files"]["MANIFEST.json"], "original_source_commit": record["original_source_commit"],
        "compact_source_commit": record["compact_source_commit"], "bundle_sha256": binding.get("bundle_sha256")}
    require(binding == expected_binding and isinstance(binding["bundle_sha256"], str)
            and re.fullmatch("[0-9a-f]{64}", binding["bundle_sha256"]), "Result/source/runtime bindings mismatch")
    if bundle is not None: require(digest(bundle) == binding["bundle_sha256"], "Input bundle bytes changed")
    report["input_bundle_bytes_checked"] = bundle is not None
    verify_environment(output, runtime, binding)
    expected_cases = [f"{d}/seed_{s}" for d in config["datasets"] for s in config["seeds"]]
    cases = results["cases"]
    require([c["case"] for c in cases] == expected_cases and results["selected_datasets"] == config["datasets"], "Missing, duplicate or reordered registered case")
    require(results["scope"] == "PREVIOUSLY_EXPOSED_DEVELOPMENT_DATA" and results["novelty_claimed"] is False
            and results["independent_campaign_confirmation"] is False and results["independent_normal_validation"] is False
            and results["normal_phase_all_cases_before_any_test"] is True, "Incorrect scientific scope")
    global_inventory, reserved = {}, 0.
    for case in cases:
        item, frozen, reserve = normal_case(output, case, config, manifest, binding, reserved)
        report["cases"].append(item)
        global_inventory.update(frozen)
        reserved += reserve
    all_normal = all(c["normal_complete"] for c in cases)
    normal_progress = read(bound(output, "NORMAL_PROGRESS.json"))
    require([c["case"] for c in normal_progress["cases"]] == expected_cases, "Normal progress coverage mismatch")
    for normal in normal_progress["cases"]:
        if normal["normal_complete"]:
            require(normal == read(bound(output, normal["case"] + "/NORMAL_RESULT.json")), "Normal progress/freeze mismatch")
    close(normal_progress["pending_test_reserve_seconds"], reserved, "total pending test reserve")
    if all_normal:
        global_path = hashed(output, "GLOBAL_CALIBRATION_FREEZE.json", results["global_freeze_sha256"])
        global_record = read(global_path)
        require(global_record["status"] == "ALL_SIX_NORMAL_CASES_FROZEN" and global_record["cases"] == expected_cases
                and global_record["bindings"] == binding and global_record["artifacts"] == global_inventory
                and global_record["any_test_arrays_loaded"] is False and global_record["any_test_labels_loaded"] is False,
                "Global six-case freeze mismatch")
        global_time = datetime.fromisoformat(global_record["created_utc"])
        require(global_time.tzinfo is not None and all(datetime.fromisoformat(r["freeze_created_utc"]) <= global_time for r in report["cases"]),
                "Global freeze precedes a case calibration freeze")
        for case, item in zip(cases, report["cases"]):
            if case["evaluation_complete"]:
                item.update(evaluation(output, case, config, data_dir, binding, results["global_freeze_sha256"]))
            else:
                require(case["status"] in {"FAILED_RUNTIME", "INCOMPLETE_RESOURCE_DEADLINE"}, "Nonterminal incomplete evaluation")
        require(read(bound(output, "EVALUATION_PROGRESS.json")) == {"cases": cases, "global_freeze_sha256": results["global_freeze_sha256"]},
                "Evaluation progress/final case mismatch")
    else:
        require(results["global_freeze_sha256"] is None and not (output / "GLOBAL_CALIBRATION_FREEZE.json").exists()
                and not any(c["evaluation_complete"] or c["test_arrays_loaded"] or c["test_labels_loaded"] for c in cases)
                and not any(output.rglob("EVALUATION.npz")), "Test accessed without all six normal freezes")
    complete = all(r["evaluation_complete"] for r in report["cases"])
    ready = complete and all(r["development_readiness"] for r in report["cases"])
    decision = "DEVELOPMENT_READINESS_PASS" if ready else ("NO_GO_FIXED_CALIBRATED_METHOD" if complete else "PENDING_INCOMPLETE")
    failed = any(c["status"] in {"FAILED_RUNTIME", "SOURCE_NUMERICAL_HOLD"} for c in cases)
    status = "FAILED_RUNTIME" if failed else ("COMPLETE_CALIBRATED_EVALUATION" if complete else "INCOMPLETE_CALIBRATION_OR_EVALUATION")
    require(results["status"] == status and results["decision"] == decision
            and results["scientific_completion"] is complete and results["all_selected_evaluations_complete"] is complete
            and results["all_registered_evaluations_complete_in_this_attempt"] is complete, "Aggregate completion/gate mismatch")
    worker = read(bound(output, "WORKER_STATUS.json"))
    require(worker["results_sha256"] == observed["RESULTS.json"] and worker["scientific_completion"] is complete
            and worker["decision"] == decision and worker["status"] == ("FAILED" if failed else ("COMPLETE" if complete else "RESOURCE_HOLD")), "Worker final receipt mismatch")
    report.update(status="VERIFIED_FIXED_NORMAL_CALIBRATION" if complete else "VERIFIED_INCOMPLETE_EVALUATION",
                  evidence_audit_passed=True, scientific_completion=complete, bounded_development_gate_pass=ready if complete else None,
                  independent_decision=decision, private_artifacts_checked=len(inventory),
                  all_six_normal_freezes_verified=all_normal, elapsed_seconds=time.perf_counter() - started)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output-dir", "data-dir", "source-dir", "registration", "audit-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args(argv)
    destination = args.audit_output.resolve()
    for path in (args.output_dir, args.data_dir, args.source_dir):
        require(not destination.is_relative_to(path.resolve(strict=True)), "Audit output must be outside evidence trees")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        result = audit(args.output_dir, args.data_dir, args.source_dir, args.registration, bundle=args.bundle)
    except Exception as error:
        result = {"status": "INVALID_OR_UNVERIFIABLE_EVIDENCE", "evidence_audit_passed": False,
                  "scientific_completion": False, "bounded_development_gate_pass": None,
                  "error_type": type(error).__name__, "reason": str(error), "auditor_sha256": digest(__file__)}
    (destination / "AUDIT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    text = "# Independent normal-calibrated MAGIC audit\n\nStatus: **" + result["status"] + "**.\n\n"
    text += "Scientific completion: " + str(result["scientific_completion"]) + ". Development gate: " + str(result["bounded_development_gate_pass"]) + ".\n\n"
    text += "All six cases and their fixed normal-only thresholds are required. Calibration alert rate is in-sample; seeds are not independent campaigns. Incomplete runs do not establish a negative efficacy result. Neural training and embedding inference are not rerun.\n"
    if "reason" in result: text += "\nReason: " + result["reason"] + "\n"
    (destination / "AUDIT.md").write_text(text, encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "scientific_completion", "bounded_development_gate_pass")}))
    return 0 if result.get("evidence_audit_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
