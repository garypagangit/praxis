"""Independent, post-run MAGIC evidence audit; no inference or training is rerun.

Distances use SciPy's direct Euclidean kernel and exhaustive CPU reference tiles.
Metrics use a separate sorted-tie implementation, not the worker or sklearn metrics.
Every saved qualification query (64 in the frozen run), plus eight fixed evenly
spaced normalizer and test queries, is checked against EVERY reference row.
This is a sampled evaluation-score audit, never a full neural reproduction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import random
import re
import sys
import time

import numpy as np
from scipy.spatial.distance import cdist
import torch

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]
UPSTREAM = "aa0b647eea74b6faa0e52eb444370c4411a32cbe"
DATA_MANIFEST = "de06215e30e36c6063eeeb6a1ed18a738735fd909dbeeda7fa7789728fb2feab"
OPERATIVE = {"experiments/apt_final/magic_reproduction/" + name for name in
             ("provenance.py", "model_adapter.py", "qualification.py", "worker.py", "launch.py",
              "run_cloud.sh", "config.json", "RUNTIME.json", "PROTOCOL.md")}
OPERATIVE |= {"experiments/apt_final/native_graph/cloud_control.py", "experiments/apt_final/native_graph/data.py"}
OPERATIONAL = {"ENV_SELECTION.log", "VENV_SETUP.log", "DEPENDENCIES.log", "PYTHON.txt", "GPU.txt",
               "ENVIRONMENT.json", "PIP_FREEZE.txt", "worker.log", "WORKER_STATUS.json", "WORKER_EXIT.txt"}
SAMPLE_QUERIES = 8


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read(path):
    def invalid(value):
        raise AuditError("Nonfinite JSON number: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def bound(root, relative):
    require(isinstance(relative, str) and relative and not PurePosixPath(relative).is_absolute()
            and "\\" not in relative and ":" not in relative
            and all(p not in {"", ".", ".."} for p in relative.split("/")), "Unsafe artifact path")
    root = Path(root).resolve(strict=True)
    path = root / relative
    require(not path.is_symlink(), "Symlink artifact refused")
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(root) and resolved.is_file(), "Artifact escaped its root")
    return resolved


def hashed(root, relative, expected):
    require(isinstance(expected, str) and re.fullmatch("[0-9a-f]{64}", expected), "Invalid digest")
    path = bound(root, relative)
    require(digest(path) == expected, "Hash mismatch: " + relative)
    return path


def close(actual, expected, name, rtol=1e-12, atol=1e-12):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and a.dtype.kind in "iuf" and b.dtype.kind in "iuf"
            and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, rtol=rtol, atol=atol), "Recomputation mismatch: " + name)


def finite(value, name):
    require(type(value) in {float, int} and math.isfinite(value) and value >= 0, "Invalid measurement: " + name)
    return value


def verify_inputs(data_dir, source_dir, registration):
    record = read(registration)
    require(record["status"] == "FROZEN_MAGIC_DEVELOPMENT_REPRODUCTION"
            and record["upstream_commit"] == UPSTREAM, "Wrong registration")
    require(record["novelty_claimed"] is False and record["confirmation_claimed"] is False
            and record["test_previously_exposed"] is True, "Registration overstates evidence")
    require(set(record["code_hashes"]) == OPERATIVE, "Incomplete operative inventory")
    for rel, sha in record["code_hashes"].items():
        hashed(REPO, rel, sha)
    manifest = read(hashed(data_dir, "MANIFEST.json", DATA_MANIFEST))
    expected = {"MANIFEST.json": DATA_MANIFEST}
    for dataset in manifest["datasets"]:
        for graph in dataset["graphs"]:
            require(graph["npz"] not in expected, "Duplicate data path")
            expected[graph["npz"]] = graph["npz_sha256"]
    require(record["data_files"] == expected, "Incomplete data inventory")
    for rel, sha in expected.items():
        hashed(data_dir, rel, sha)
    source = read(hashed(source_dir, "SOURCE_MANIFEST.json", record["source_manifest_sha256"]))
    require(source["commit"] == UPSTREAM and source["files"] == record["upstream_files"]
            and source["files"], "Wrong upstream source manifest")
    for rel, sha in source["files"].items():
        hashed(source_dir, rel, sha)
    actual = {p.relative_to(source_dir).as_posix() for p in Path(source_dir).rglob("*.py")}
    require(actual == {p for p in source["files"] if p.endswith(".py")}, "Extra upstream Python file")
    return record, manifest, read(HERE / "config.json"), read(HERE / "RUNTIME.json")


def verify_environment(output, runtime, bindings):
    environment = read(hashed(output, "WORKER_ENVIRONMENT.json", bindings["worker_environment_sha256"]))
    require(environment["python"].startswith(runtime["python"] + "."), "Worker Python differs from runtime")
    for key in ("torch", "dgl", "numpy"):
        require(environment[key] == runtime[key], "Worker runtime version mismatch: " + key)
    require(environment["sklearn"] == runtime["scikit_learn"] and environment["cuda"] == "12.1",
            "Worker sklearn/CUDA mismatch")
    require(environment["historical_runtime_reproduced"] is False, "Historical runtime claim")
    bootstrap = read(bound(output, "ENVIRONMENT.json"))
    expected = {k: v for k, v in runtime.items() if k not in {"python", "wheel", "wheel_url", "wheel_sha256"}}
    require(bootstrap["dependency_versions"] == expected, "Bootstrap runtime versions mismatch")
    require(bootstrap["python"].startswith(runtime["python"] + "."), "Bootstrap Python mismatch")
    qualification = read(bound(output, "RUNTIME_QUALIFICATION.json"))
    require(qualification["bindings"] == bindings, "Runtime qualification bindings mismatch")
    author = qualification["author"]
    require(author["status"] == "PASS" and author["forward_backward_qualified"] is True,
            "Runtime forward/backward qualification missing")
    require(author["encoder_normalizations"] == ["NoneType"] * 3 and author["normalization_fix_applied"] is False
            and author["determinism_fix_applied"] is False, "Author behavior changed")
    mutation = author["mask_target_alias_probe"]
    require(mutation["shared_feature_storage"] is True and mutation["masked_rows"] > 0
            and mutation["masked_rows"] == mutation["original_rows_changed"], "Mask-target alias behavior differs")
    require(qualification["synthetic_exact_knn"]["status"] == "PASS", "Runtime numerical qualification missing")
    return {"status": "VERIFIED_RECORDED_QUALIFICATION", "neural_probe_independently_rerun": False}


def checkpoint(path, epoch, bindings, shape_reference=None):
    value = torch.load(path, map_location="cpu", weights_only=True)
    require(value["completed_epochs"] == epoch and value["bindings"] == bindings
            and value["source_mode"] == "source_original", "Checkpoint epoch/bindings mismatch")
    require(value["rng"]["dgl_rng_state_captured"] is False
            and value["rng"]["checkpoint_continuation_qualified"] is False, "Unqualified checkpoint reuse claim")
    model = value["model"]
    require(isinstance(model, dict) and model and all(isinstance(v, torch.Tensor) for v in model.values()),
            "Checkpoint has no tensor model")
    count = 0
    def inspect(item):
        nonlocal count
        if isinstance(item, torch.Tensor):
            count += 1
            require(torch.isfinite(item).all().item(), "Nonfinite checkpoint tensor")
        elif isinstance(item, dict):
            for v in item.values():
                inspect(v)
        elif isinstance(item, (list, tuple)):
            for v in item:
                inspect(v)
        elif isinstance(item, float):
            require(math.isfinite(item), "Nonfinite checkpoint scalar")
    inspect(value)
    shapes = {k: (tuple(v.shape), str(v.dtype)) for k, v in model.items()}
    if shape_reference is not None:
        require(shapes == shape_reference, "Checkpoint model topology changed between epochs")
    return shapes, {"epoch": epoch, "model_tensors": len(model), "all_tensors_checked": count,
                    "weights_only": True, "all_tensor_values_finite": True}


def standardize(path, rows, dimension):
    with np.load(path, allow_pickle=False) as archive:
        raw, mean, scale = archive["raw"], archive["mean"], archive["scale"]
    require(raw.dtype == np.float32 and raw.shape == (rows, dimension) and np.isfinite(raw).all(),
            "Invalid saved training embedding matrix")
    require(mean.shape == (dimension,) and scale.shape == (dimension,) and np.all(scale > 0), "Invalid scaler")
    close(mean, raw.mean(axis=0), "training mean", rtol=1e-6, atol=1e-8)
    close(scale, raw.std(axis=0), "training std", rtol=1e-6, atol=1e-8)
    return (raw - mean) / scale, mean, scale


def exact_distances(bank, queries, k, block=16384):
    """Exhaustive direct-distance CPU audit, preserving duplicates and self rows."""
    bank, queries = np.asarray(bank), np.asarray(queries)
    require(bank.ndim == queries.ndim == 2 and bank.shape[1] == queries.shape[1]
            and 1 <= k <= len(bank) and np.isfinite(bank).all() and np.isfinite(queries).all(), "Invalid distance inputs")
    best = np.full((len(queries), k), np.inf)
    query64 = np.asarray(queries, dtype=np.float64)
    for start in range(0, len(bank), block):
        distance = cdist(query64, np.asarray(bank[start:start + block], dtype=np.float64), metric="euclidean")
        candidate = np.concatenate((best, distance), axis=1)
        best = np.partition(candidate, k - 1, axis=1)[:, :k]
    return best.mean(axis=1)


def sample_check(bank, query, saved, k, settings, name, count=SAMPLE_QUERIES):
    require(len(query) > 0 and np.asarray(saved).shape == (len(query),), "Invalid saved distance vector")
    positions = np.arange(len(query)) if count is None else np.linspace(0, len(query) - 1, min(count, len(query)), dtype=np.int64)
    expected = exact_distances(bank, query[positions], k)
    close(np.asarray(saved)[positions], expected, name, settings["numerical_rtol"], settings["numerical_atol"])
    return {"saved_queries": len(query), "verified_queries": len(positions), "verified_positions": positions.tolist(),
            "reference_rows_per_query": len(bank), "all_reference_rows_used": True,
            "max_absolute_error": float(np.max(np.abs(np.asarray(saved)[positions] - expected))),
            "method": "independent scipy direct Euclidean distances and exhaustive partition"}


def recompute_gate(qualification, config, specification, rows):
    q, resource = qualification, config["resources"]
    gate = q["resource_gate"]
    epoch = finite(q["epoch"]["seconds"], "epoch seconds")
    embedding = finite(q["training_embeddings"]["seconds"], "embedding seconds")
    timing = q["full_reference_sample_timing"]
    seconds = finite(timing["seconds"], "query seconds")
    queries = timing["query_rows"]
    require(type(queries) is int and queries > 0 and timing["reference_rows"] == rows
            and timing["k"] == specification["k"] and timing["reference_sampling"] is False,
            "Wrong full-reference timing population")
    per_query = seconds / queries
    test_rows = specification["expected_test_nodes"]
    components = {
        "remaining_training": epoch * (config["training"]["epochs"] - 1),
        "final_training_embeddings": embedding,
        "evaluation_embeddings": 2 * test_rows * max(finite(g["seconds"], "graph embedding seconds") / g["nodes"]
                                                     for g in q["training_embeddings"]["graphs"]),
        "full_reference_normalizer": per_query * min(50000, rows),
        "full_evaluation_scoring": per_query * test_rows,
        # This observation is stored only inside the component map by the worker.
        "reference_transfer": finite(gate["components_seconds_before_multiplier"]["reference_transfer"], "transfer seconds"),
        "artifact_serialization": finite(q["saved_embeddings"]["seconds"], "serialization seconds") * (1 + test_rows / rows),
    }
    require(set(gate["components_seconds_before_multiplier"]) == set(components), "Wrong resource component inventory")
    for key, value in components.items():
        close(gate["components_seconds_before_multiplier"][key], value, "resource component " + key)
    predicted = sum(components.values()) * resource["estimate_multiplier"] + resource["safety_seconds"]
    remaining = finite(gate["remaining_seconds"], "remaining seconds")
    close(gate["predicted_remaining_seconds"], predicted, "predicted resource budget")
    for key, value in {"estimate_multiplier": resource["estimate_multiplier"], "safety_seconds": resource["safety_seconds"],
                       "measured_full_epoch_seconds": epoch, "measured_sample_queries": queries,
                       "measured_sample_seconds": seconds, "normalizer_queries": min(50000, rows),
                       "planned_evaluation_queries": test_rows, "reference_rows": rows}.items():
        close(gate[key], value, "resource field " + key)
    expected_status = "PASS" if predicted <= remaining else "NOT_RUN_RESOURCE_HOLD"
    require(gate["status"] == expected_status and gate["qualification_uses_evaluation_arrays_or_labels"] is False
            and gate["reference_sampling"] is False, "Resource gate decision mismatch")
    return {"status": expected_status, "predicted_remaining_seconds": predicted, "remaining_seconds": remaining,
            "arithmetic_independently_verified": True, "timing_observations_independently_remeasured": False,
            "reference_transfer_measurement_stored_only_in_component_map": True}


def independent_metrics(y, scores, target):
    y, scores = np.asarray(y), np.asarray(scores)
    require(y.ndim == 1 and scores.shape == y.shape and np.isfinite(scores).all()
            and set(np.unique(y)) == {0, 1} and 0 < target <= 1, "Invalid metric inputs")
    order = np.argsort(scores, kind="stable")
    thresholds, starts, counts = np.unique(scores[order], return_index=True, return_counts=True)
    positive = np.add.reduceat(y[order].astype(np.int64), starts)
    negative = counts - positive
    p, n = int(positive.sum()), int(negative.sum())
    negatives_below = np.r_[0, np.cumsum(negative)[:-1]]
    positives_below = np.r_[0, np.cumsum(positive)[:-1]]
    tp, fp = p - positives_below, n - negatives_below
    recall, precision = tp / p, tp / (tp + fp)
    auc = float(np.sum(positive * (negatives_below + .5 * negative)) / (p * n))
    ap = float(np.sum(positive / p * precision))
    author_index = int(np.flatnonzero(recall >= target)[-1])
    maximum_index = int(np.argmax(2 * precision * recall / (precision + recall + 1e-9)))
    def row(index):
        t, f = int(tp[index]), int(fp[index])
        fn, tn = p - t, n - f
        pr, rec = t / (t + f) if t + f else 0., t / p
        return {"tp": t, "fp": f, "fn": fn, "tn": tn, "precision": pr, "recall": rec,
                "false_positive_rate": f / n, "f1": 2 * t / (2 * t + f + fn) if 2 * t + f + fn else 0.,
                "threshold": float(thresholds[index]), "threshold_index": index}
    return {"auroc": auc, "average_precision": ap, "author_recall_rule": row(author_index),
            "supplemental_max_f1_oracle": row(maximum_index)}


def verify_metrics(saved, expected, target):
    for key in ("auroc", "average_precision"):
        close(saved[key], expected[key], key)
    for arm in ("author_recall_rule", "supplemental_max_f1_oracle"):
        for key, value in expected[arm].items():
            close(saved[arm][key], value, arm + "." + key)
        require(saved[arm]["threshold_uses_test_labels"] is True and saved[arm]["deployment_readiness"] is False,
                "Oracle threshold mislabeled")
    close(saved["author_recall_rule"]["target_recall"], target, "author recall target")
    require(saved["all_threshold_metrics_label_selected"] is True and saved["novelty_claimed"] is False
            and saved["operational_threshold_evaluated"] is False, "Metric evidence scope overstated")


def audit_case(output, name, status, config, manifest, data_dir, bindings):
    specification = config["dataset_specs"][name]
    graphs = {g["npz"].split("/")[-1].removesuffix(".npz"): g for d in manifest["datasets"]
              if d["dataset"] == name for g in d["graphs"]}
    train_names = specification["train_graphs"]
    rows = sum(graphs[n]["n_nodes"] for n in train_names)
    case = Path(output) / name
    epochs = status["completed_epochs"]
    require(type(epochs) is int and 0 <= epochs <= config["training"]["epochs"], "Invalid completed epoch count")
    require(status["dataset"] == name and type(status["evaluation_complete"]) is bool
            and type(status["training_complete"]) is bool, "Invalid dataset status")
    report = {"reported_status": status["status"], "completed_epochs": epochs, "evaluation_complete": False,
              "scientific_conclusion": "INCOMPLETE_EVALUATION_NOT_A_NEGATIVE_RESULT", "checkpoints_checked": []}
    if not case.exists():
        require(epochs == 0 and status["status"] == "NOT_RUN_RESOURCE_HOLD" and status["evaluation_complete"] is False
                and status["training_complete"] is False and status["test_arrays_loaded"] is False
                and status["test_labels_loaded"] is False, "Missing case output for claimed work")
        return report
    require(read(bound(case, "STATUS.json")) == status, "Dataset status differs from final results")
    require(status["bindings"] == bindings and status["source_mode"] == "source_original", "Case bindings mismatch")
    history = status["epochs"]
    require([e["epoch"] for e in history] == list(range(1, epochs + 1)), "Epoch history incomplete")
    shapes = None
    for epoch in history:
        require([g["graph"] for g in epoch["graphs"]] == train_names, "Training graph order changed")
        for row in epoch["graphs"]:
            require(row["nodes"] == graphs[row["graph"]]["n_nodes"] and row["edges"] == graphs[row["graph"]]["n_edges"],
                    "Training graph counts differ from prepared manifest")
            finite(row["seconds"], "training graph seconds")
            finite(row["scaled_loss"], "scaled loss")
        close(epoch["epoch_loss"], sum(r["scaled_loss"] for r in epoch["graphs"]), "epoch loss")
        finite(epoch["seconds"], "epoch seconds")
        shapes, detail = checkpoint(bound(case, f"epoch_{epoch['epoch']:03d}.pt"), epoch["epoch"], bindings, shapes)
        report["checkpoints_checked"].append(detail)
    if epochs:
        latest = status["latest_checkpoint"]
        require(latest["file"] == f"epoch_{epochs:03d}.pt" and latest["completed_epochs"] == epochs,
                "Latest checkpoint epoch mismatch")
        hashed(case, latest["file"], latest["sha256"])
    qualification_path = case / "QUALIFICATION.json"
    if qualification_path.exists():
        qualification = read(hashed(case, "QUALIFICATION.json", status["qualification_sha256"]))
        require(qualification["bindings"] == bindings and qualification["dataset"] == name
                and qualification["source_mode"] == "source_original"
                and qualification["test_arrays_loaded"] is False and qualification["test_labels_loaded"] is False,
                "Qualification read test data or has wrong binding")
        require({k: v for k, v in history[0].items() if k != "epoch"} == qualification["epoch"], "First epoch mismatch")
        embeddings = qualification["training_embeddings"]
        require([g["graph"] for g in embeddings["graphs"]] == train_names and embeddings["rows"] == rows,
                "Qualification embedding population mismatch")
        for graph in embeddings["graphs"]:
            require(graph["nodes"] == graphs[graph["graph"]]["n_nodes"], "Embedding graph node count mismatch")
        saved = qualification["saved_embeddings"]
        require(saved["file"] == "QUALIFICATION_TRAIN_EMBEDDINGS.npz" and saved["rows"] == rows
                and saved["dimension"] == config["training"]["hidden_dim"], "Qualification bank receipt mismatch")
        path = hashed(case, saved["file"], saved["sha256"])
        bank, _, _ = standardize(path, rows, config["training"]["hidden_dim"])
        with np.load(path, allow_pickle=False) as archive:
            indices, distance, numerical_bank = archive["sample_indices"], archive["sample_distances"], archive["numerical_bank_indices"]
        rng = np.random.default_rng(90210)
        require(np.array_equal(indices, rng.choice(rows, min(config["knn"]["qualification_queries"], rows), replace=False))
                and np.array_equal(numerical_bank, rng.choice(rows, min(512, rows), replace=False)), "Qualification sampling changed")
        report["qualification_distance_check"] = sample_check(bank, bank[indices], distance, specification["k"], config["knn"], "qualification distances", count=None)
        report["resource_gate"] = recompute_gate(qualification, config, specification, rows)
        require(qualification["resource_gate"] == status["resource_gate"], "Qualification/status gate mismatch")
        require(qualification["real_training_numeric_qualification"]["status"] == "PASS", "Real numerical qualification absent")
        del bank
    elif status["status"] not in {"FAILED_RUNTIME", "SOURCE_NUMERICAL_HOLD", "INCOMPLETE_RESOURCE_DEADLINE"}:
        raise AuditError("Terminal case lacks resource qualification")
    if not status["evaluation_complete"]:
        require(status["status"] in {"NOT_RUN_RESOURCE_HOLD", "QUALIFIED_FULL_RUN_DISABLED", "FAILED_RUNTIME",
                                     "SOURCE_NUMERICAL_HOLD", "INCOMPLETE_RESOURCE_DEADLINE"}, "Unrecognized incomplete terminal status")
        if status["status"] == "NOT_RUN_RESOURCE_HOLD":
            require(epochs == 1 and report["resource_gate"]["status"] == "NOT_RUN_RESOURCE_HOLD"
                    and status["test_arrays_loaded"] is False and status["test_labels_loaded"] is False
                    and status["training_complete"] is False, "Resource hold contradicts observed training/evaluation")
        if status["test_labels_loaded"] or status["test_arrays_loaded"]:
            require(epochs == config["training"]["epochs"] and (case / "FIT_FREEZE.json").is_file(), "Evaluation loaded before fit freeze")
        return report
    require(status["status"] == "COMPLETE_SOURCE_ORIGINAL_DEVELOPMENT_REPRODUCTION" and epochs == 50
            and status["training_complete"] is True and status["test_arrays_loaded"] is True
            and status["test_labels_loaded"] is True and report["resource_gate"]["status"] == "PASS", "False completed evaluation")
    freeze = read(hashed(case, "FIT_FREEZE.json", status["fit_freeze_sha256"]))
    require(freeze["bindings"] == bindings and freeze["dataset"] == name and freeze["completed_epochs"] == 50
            and freeze["test_arrays_loaded"] is False and freeze["test_labels_loaded"] is False
            and freeze["checkpoint"] == status["latest_checkpoint"], "Invalid pre-evaluation fit freeze")
    saved = freeze["training_embeddings"]
    require(saved["file"] == "TRAIN_EMBEDDINGS.npz" and saved["rows"] == rows
            and saved["dimension"] == config["training"]["hidden_dim"], "Final training bank receipt mismatch")
    bank, mean, scale = standardize(hashed(case, saved["file"], saved["sha256"]), rows, config["training"]["hidden_dim"])
    evaluation = hashed(case, "EVALUATION.npz", status["evaluation_sha256"])
    with np.load(evaluation, allow_pickle=False) as archive:
        raw, y, distances, scores = (archive[k] for k in ("raw", "y", "distances", "scores"))
        indices, normalizer = archive["normalizer_indices"], archive["normalizer_distances"]
        mean_distance = float(archive["mean_distance"])
    require(raw.dtype == np.float32 and raw.shape == (specification["expected_test_nodes"], config["training"]["hidden_dim"])
            and np.isfinite(raw).all(), "Invalid evaluation embeddings")
    with np.load(bound(data_dir, f"{name}/{specification['test_graph']}.npz"), allow_pickle=False) as source:
        require(np.array_equal(y, source["y"]), "Evaluation labels differ from prepared original row indices")
    shuffled = list(range(rows))
    random.Random(config["training"]["seed"]).shuffle(shuffled)
    require(np.array_equal(indices, np.asarray(shuffled[:min(50000, rows)])), "Author shuffled normalizer rows differ")
    require(normalizer.shape == indices.shape and np.isfinite(normalizer).all() and np.all(normalizer >= 0), "Invalid normalizer distances")
    close(mean_distance, normalizer.mean(), "normalization mean")
    require(mean_distance > 0 and np.isfinite(distances).all() and np.all(distances >= 0), "Nonpositive normalizer/invalid distances")
    close(scores, distances / mean_distance, "all normalized scores")
    report["normalizer_distance_check"] = sample_check(bank, bank[indices], normalizer, specification["k"], config["knn"], "normalizer distances")
    report["test_distance_check"] = sample_check(bank, (raw - mean) / scale, distances, specification["k"], config["knn"], "test distances")
    metrics = independent_metrics(y, scores, specification["author_recall_target"])
    verify_metrics(status["metrics"], metrics, specification["author_recall_target"])
    require(status["reference_rows"] == rows and status["test_rows"] == len(y)
            and status["test_labels_selected_thresholds"] is True, "Evaluation population/scope mismatch")
    report.update(evaluation_complete=True, scientific_conclusion="DESCRIPTIVE_EXPOSED_DATA_ORACLE_EVALUATION_ONLY",
                  independently_recomputed_metrics=metrics, normalizer_shuffle_and_original_labels_verified=True,
                  all_saved_scores_arithmetically_verified=True)
    return report


def audit(output_dir, data_dir, source_dir, registration, *, verified_post_run_receipts=None):
    started = time.perf_counter()
    output = Path(output_dir).resolve(strict=True)
    record, manifest, config, runtime = verify_inputs(data_dir, source_dir, registration)
    observed = {p.relative_to(output).as_posix(): digest(bound(output, p.relative_to(output).as_posix()))
                for p in output.rglob("*") if p.is_file()}
    # Only the separate compact-chain auditor supplies this narrowly named receipt.
    # It is written after the original worker freezes its private artifact map.
    post_run = verified_post_run_receipts or {}
    require(set(post_run).issubset({"COMPACT_RUNTIME_RECEIPT.json"})
            and all(observed.get(name) == sha for name, sha in post_run.items()), "Unverified post-run receipt")
    report = {"status": "INCOMPLETE_EVIDENCE", "evidence_audit_passed": False, "scientific_completion": False,
              "novelty_claimed": False, "negative_scientific_conclusion": False,
              "checked_utc": datetime.now(timezone.utc).isoformat(), "auditor_sha256": digest(__file__),
              "input_hashes": {"registration": digest(registration), "data_manifest": DATA_MANIFEST,
                               "source_manifest": record["source_manifest_sha256"], "observed_outputs": observed},
              "scope": {"qualification_queries_checked": "all saved queries", "normalizer_and_test_query_sample_size": SAMPLE_QUERIES,
                        "full_reference_for_every_sample": True,
                        "neural_training_or_embedding_inference_rerun": False,
                        "transport_and_AWS_shutdown_verified_here": False,
                        "timing_observations_independently_remeasured": False}, "datasets": {}}
    if "RESULTS.json" not in observed:
        report["reason"] = "No final RESULTS.json; hashes recorded, no terminal scientific claim verified."
        report["elapsed_seconds"] = time.perf_counter() - started
        return report
    results = read(output / "RESULTS.json")
    require(read(output / "RUN_STATUS.json") == results, "Final run status differs from results")
    expected_inventory = {r: sha for r, sha in observed.items()
                          if r not in OPERATIONAL | {"RESULTS.json", "RUN_STATUS.json"} and r not in post_run}
    require(results["private_artifacts"] == expected_inventory, "Private artifact inventory/hash mismatch")
    bindings = {"config_sha256": digest(HERE / "config.json"), "registration_sha256": digest(registration),
                "author_source_manifest_sha256": record["source_manifest_sha256"],
                "worker_environment_sha256": observed["WORKER_ENVIRONMENT.json"], "source_commit": record["source_commit"],
                "upstream_commit": record["upstream_commit"], "data_manifest_sha256": DATA_MANIFEST}
    require(results["bindings"] == bindings, "Results input/runtime bindings mismatch")
    report["runtime"] = verify_environment(output, runtime, bindings)
    selected = results["selected_datasets"]
    require(selected and selected == [d for d in config["datasets"] if d in selected]
            and set(results["datasets"]) == set(selected)
            and results["unselected_datasets"] == [d for d in config["datasets"] if d not in selected], "Dataset coverage mismatch")
    require(results["novelty_claimed"] is False and results["deployment_readiness_claimed"] is False
            and results["scope"] == "EXPOSED_DATA_DEVELOPMENT_REPRODUCTION", "Results evidence scope overstated")
    for name in selected:
        report["datasets"][name] = audit_case(output, name, results["datasets"][name], config, manifest, data_dir, bindings)
    complete = all(d["evaluation_complete"] for d in report["datasets"].values())
    require(results["all_selected_evaluations_complete"] is complete
            and results["all_registered_evaluations_complete_in_this_attempt"] is (complete and selected == config["datasets"]),
            "Aggregate completeness mismatch")
    failed = any(d["reported_status"] in {"FAILED_RUNTIME", "SOURCE_NUMERICAL_HOLD"} for d in report["datasets"].values())
    expected_status = "FAILED_RUNTIME" if failed else ("COMPLETE_SELECTED_REPRODUCTIONS" if complete else "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION")
    require(results["status"] == expected_status, "Aggregate terminal outcome mismatch")
    worker = read(bound(output, "WORKER_STATUS.json"))
    require(worker["results_sha256"] == observed["RESULTS.json"] and worker["scientific_completion"] is complete
            and worker["selected_datasets"] == selected
            and worker["status"] == ("FAILED" if failed else ("COMPLETE" if complete else "RESOURCE_HOLD")), "Worker completion receipt mismatch")
    report.update(status="VERIFIED_DESCRIPTIVE_EVALUATION" if complete else "VERIFIED_INCOMPLETE_EVALUATION",
                  evidence_audit_passed=True, scientific_completion=complete,
                  all_registered_evaluations_complete_in_this_attempt=complete and selected == config["datasets"],
                  private_artifacts_checked=len(expected_inventory), elapsed_seconds=time.perf_counter() - started)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output-dir", "data-dir", "source-dir", "registration", "audit-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    destination = args.audit_output.resolve()
    for protected in (args.output_dir, args.data_dir, args.source_dir):
        root = protected.resolve(strict=True)
        require(not destination.is_relative_to(root), "Audit output must be outside evidence/input trees")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        report = audit(args.output_dir, args.data_dir, args.source_dir, args.registration)
    except Exception as error:
        report = {"status": "INVALID_OR_UNVERIFIABLE_EVIDENCE", "evidence_audit_passed": False,
                  "scientific_completion": False, "negative_scientific_conclusion": False,
                  "error_type": type(error).__name__, "reason": str(error), "auditor_sha256": digest(__file__),
                  "checked_utc": datetime.now(timezone.utc).isoformat()}
    (destination / "AUDIT.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    text = "# Independent MAGIC evidence audit\n\nStatus: **" + report["status"] + "**.\n\n"
    text += "Scientific completion: " + str(report["scientific_completion"]) + ". A resource hold or incomplete run is not a negative scientific result.\n\n"
    text += "The audit checks all saved qualification queries and up to eight fixed normalizer/test queries against every reference row. It does not retrain the neural model, regenerate embeddings, or verify AWS shutdown. All test-label thresholds remain descriptive oracles.\n"
    if "reason" in report:
        text += "\nReason: " + report["reason"] + "\n"
    (destination / "AUDIT.md").write_text(text, encoding="utf-8")
    print(json.dumps({"status": report["status"], "scientific_completion": report["scientific_completion"]}))
    return 0 if report.get("evidence_audit_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
