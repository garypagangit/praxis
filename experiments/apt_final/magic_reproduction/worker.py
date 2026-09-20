"""Registered, bounded author-MAGIC reproduction; no novel or operational claim."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
import traceback

import numpy as np
import torch

from .model_adapter import build_model, digest, graph_from_arrays, load_arrays, load_author, source_semantics_probe
from .provenance import verify_runtime
from .qualification import (ExactFullReferenceKNN, ResourceDeadline, author_standardize,
                            numerical_check, oracle_metrics, resource_estimate,
                            synthetic_numerical_check, synchronize)

HERE = Path(__file__).resolve().parent
BOOTSTRAP_FILES = {"ENV_SELECTION.log", "VENV_SETUP.log", "DEPENDENCIES.log", "PYTHON.txt",
                   "GPU.txt", "ENVIRONMENT.json", "PIP_FREEZE.txt", "worker.log", "WORKER_STATUS.json"}


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def emit(event, **details):
    print(json.dumps({"utc": utc(), "event": event, **details}, allow_nan=False), flush=True)


def select_datasets(config, selected):
    requested = list(config["datasets"]) if not selected else selected.split(",")
    if not requested or len(set(requested)) != len(requested) or requested != [d for d in config["datasets"] if d in requested]:
        raise ValueError("Dataset selector must be an ordered nonempty subset of the registration")
    return requested


def validate_config(config):
    if config["schema_version"] != 1 or config["source_mode"] != "source_original" or config["datasets"] != ["theia", "cadets"]:
        raise ValueError("Unsupported original-source configuration")
    expected = {"seed": 0, "epochs": 50, "hidden_dim": 64, "num_layers": 3,
                "learning_rate": .001, "weight_decay": .0005, "mask_rate": .5,
                "alpha_l": 3., "negative_slope": .2}
    if config["training"] != expected:
        raise ValueError("Author training settings changed")
    for name, k, nodes, edges, count, recall in (("theia", 10, 5, 17, 344767, .99996),
                                               ("cadets", 200, 6, 27, 357173, .9976)):
        expected_spec = {"node_types": nodes, "edge_types": edges, "k": k,
                         "train_graphs": ["train0", "train1", "train2", "train3"],
                         "test_graph": "test0", "expected_test_nodes": count, "author_recall_target": recall}
        if config["dataset_specs"][name] != expected_spec:
            raise ValueError("Author dataset settings changed")
    if config["resources"]["science_cap_seconds"] > 2400 or config["resources"]["science_cap_seconds"] <= 0:
        raise ValueError("Invalid scientific time cap")
    if config["resources"]["estimate_multiplier"] < 1 or config["resources"]["safety_seconds"] < 0:
        raise ValueError("Invalid resource estimate safety")
    return config


def capture_rng():
    state = np.random.get_state()
    return {"python": random.getstate(), "numpy": {"kind": state[0], "keys": state[1].tolist(),
            "position": int(state[2]), "has_gauss": int(state[3]), "cached_gaussian": float(state[4])},
            "torch_cpu": torch.get_rng_state(), "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            "dgl_rng_state_captured": False, "checkpoint_continuation_qualified": False}


def save_checkpoint(path, model, optimizer, epoch, bindings):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    torch.save({"model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                "optimizer": optimizer.state_dict(), "completed_epochs": epoch, "rng": capture_rng(),
                "bindings": bindings, "source_mode": "source_original"}, temporary)
    temporary.replace(path)
    # Our own tensor/primitive checkpoint must be readable without arbitrary globals.
    checked = torch.load(path, map_location="cpu", weights_only=True)
    if checked["completed_epochs"] != epoch or checked["bindings"] != bindings:
        raise RuntimeError("Own checkpoint verification failed")
    return {"file": path.name, "sha256": digest(path), "completed_epochs": epoch,
            "weights_only_load_verified": True, "checkpoint_continuation_qualified": False,
            "dgl_rng_state_captured": False}


class Budget:
    def __init__(self, cap_seconds, deadline_epoch):
        self.started = time.perf_counter()
        self.deadline = min(self.started + cap_seconds,
                            self.started + max(0., deadline_epoch - time.time()))

    def remaining(self):
        return max(0., self.deadline - time.perf_counter())

    def check(self):
        if self.remaining() <= 0:
            raise ResourceDeadline("Registered scientific/absolute deadline reached")


def train_epoch(author, model, optimizer, config, dataset, data_dir, hashes, device, budget):
    specification = config["dataset_specs"][dataset]
    synchronize(device)
    started = time.perf_counter()
    graph_records = []
    for name in specification["train_graphs"]:
        budget.check()
        graph_start = time.perf_counter()
        arrays = load_arrays(data_dir, dataset, name, hashes)
        graph = graph_from_arrays(author, arrays, specification, device)
        model.train()
        # Preserve author order, graph reload, loss / n_train, and per-graph update.
        loss = model(graph) / len(specification["train_graphs"])
        optimizer.zero_grad()
        if not torch.isfinite(loss):
            raise ValueError("SOURCE_NUMERICAL_HOLD: nonfinite training loss")
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise ValueError("SOURCE_NUMERICAL_HOLD: nonfinite gradients")
        optimizer.step()
        synchronize(device)
        graph_records.append({"graph": name, "nodes": len(arrays["node_type"]), "edges": len(arrays["src"]),
                              "scaled_loss": float(loss.detach().cpu()), "seconds": time.perf_counter() - graph_start})
        del arrays, graph, loss
    return {"seconds": time.perf_counter() - started, "graphs": graph_records,
            "epoch_loss": sum(g["scaled_loss"] for g in graph_records)}


def training_embeddings(author, model, config, dataset, data_dir, hashes, device, budget):
    model.eval()
    specification = config["dataset_specs"][dataset]
    started = time.perf_counter()
    parts, receipts = [], []
    with torch.no_grad():
        for name in specification["train_graphs"]:
            budget.check()
            graph_start = time.perf_counter()
            arrays = load_arrays(data_dir, dataset, name, hashes)
            graph = graph_from_arrays(author, arrays, specification, device)
            embedding = model.embed(graph).detach().cpu().numpy()
            if embedding.shape != (len(arrays["node_type"]), 64) or not np.isfinite(embedding).all():
                raise ValueError("SOURCE_NUMERICAL_HOLD: invalid training embeddings")
            parts.append(embedding)
            receipts.append({"graph": name, "nodes": len(embedding), "seconds": time.perf_counter() - graph_start})
            del arrays, graph
    result = np.concatenate(parts, axis=0)
    return result, {"seconds": time.perf_counter() - started, "graphs": receipts, "rows": len(result)}


def save_embeddings(path, raw, mean, scale, **extra):
    started = time.perf_counter()
    np.savez_compressed(path, raw=raw, mean=mean, scale=scale, **extra)
    return {"file": Path(path).name, "sha256": digest(path), "seconds": time.perf_counter() - started,
            "rows": len(raw), "dimension": raw.shape[1]}


def run_dataset(author, config, dataset, data_dir, hashes, output, device, budget, bindings):
    output.mkdir()
    specification, training, knn = config["dataset_specs"][dataset], config["training"], config["knn"]
    status = {"dataset": dataset, "status": "QUALIFICATION_RUNNING", "completed_epochs": 0,
              "test_arrays_loaded": False, "test_labels_loaded": False, "evaluation_complete": False,
              "training_complete": False, "source_mode": "source_original", "bindings": bindings,
              "checkpoint_continuation_qualified": False, "epochs": []}

    def update():
        write_json(output / "STATUS.json", status)

    author.utilities.set_random_seed(training["seed"])
    model = build_model(author, training, specification, device)
    optimizer = author.utilities.create_optimizer("adam", model, training["learning_rate"], training["weight_decay"])
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    update()
    try:
        epoch = train_epoch(author, model, optimizer, config, dataset, data_dir, hashes, device, budget)
        status["epochs"].append({"epoch": 1, **epoch})
        status["completed_epochs"] = 1
        status["latest_checkpoint"] = save_checkpoint(output / "epoch_001.pt", model, optimizer, 1, bindings)
        update()
        emit("qualification_epoch_complete", dataset=dataset, **epoch)

        raw, embedding_receipt = training_embeddings(author, model, config, dataset, data_dir, hashes, device, budget)
        scaled, mean, scale = author_standardize(raw)
        rng = np.random.default_rng(90210)
        sample_indices = rng.choice(len(raw), min(knn["qualification_queries"], len(raw)), replace=False)
        bank_indices = rng.choice(len(raw), min(512, len(raw)), replace=False)
        real_numeric = numerical_check(scaled[bank_indices], scaled[sample_indices[:8]], min(specification["k"], len(bank_indices)), device, knn)
        transfer_started = time.perf_counter()
        scorer = ExactFullReferenceKNN(scaled, specification["k"], device, knn["query_batch_size"], knn["reference_batch_size"])
        transfer_seconds = time.perf_counter() - transfer_started
        scorer.score(scaled[sample_indices[:1]], budget.check)  # warm the qualified full-reference path
        sample_distances, timing = scorer.score(scaled[sample_indices], budget.check)
        saved = save_embeddings(output / "QUALIFICATION_TRAIN_EMBEDDINGS.npz", raw, mean, scale,
                                sample_indices=sample_indices, sample_distances=sample_distances,
                                numerical_bank_indices=bank_indices)
        estimate_test = max(r["seconds"] / r["nodes"] for r in embedding_receipt["graphs"]) * specification["expected_test_nodes"] * 2
        gate = resource_estimate(epoch_seconds=epoch["seconds"], embedding_seconds=embedding_receipt["seconds"],
            test_embedding_seconds=estimate_test, query_seconds=timing["seconds"], sample_queries=len(sample_indices),
            reference_rows=len(raw), test_rows=specification["expected_test_nodes"], serialization_seconds=saved["seconds"],
            index_seconds=transfer_seconds, remaining_seconds=budget.remaining(), resources=config["resources"], epochs=training["epochs"])
        qualification = {"dataset": dataset, "source_mode": "source_original", "bindings": bindings,
                         "test_arrays_loaded": False, "test_labels_loaded": False, "epoch": epoch,
                         "training_embeddings": embedding_receipt, "saved_embeddings": saved,
                         "real_training_numeric_qualification": real_numeric, "full_reference_sample_timing": timing,
                         "resource_gate": gate, "test_embedding_estimate_rule": "2 * maximum measured training-graph seconds/node * manifest test node count",
                         "peak_cuda_memory_allocated": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else None}
        write_json(output / "QUALIFICATION.json", qualification)
        status["qualification_sha256"] = digest(output / "QUALIFICATION.json")
        status["resource_gate"] = gate
        del raw, scaled, scorer
        gc.collect()
        if gate["status"] != "PASS" or not config["allow_full_run"]:
            status["status"] = gate["status"] if gate["status"] != "PASS" else "QUALIFIED_FULL_RUN_DISABLED"
            update()
            return status

        status["status"] = "FULL_TRAINING_RUNNING"
        update()
        for number in range(2, training["epochs"] + 1):
            epoch = train_epoch(author, model, optimizer, config, dataset, data_dir, hashes, device, budget)
            status["epochs"].append({"epoch": number, **epoch})
            status["completed_epochs"] = number
            status["latest_checkpoint"] = save_checkpoint(output / f"epoch_{number:03d}.pt", model, optimizer, number, bindings)
            update()
            emit("training_epoch_complete", dataset=dataset, epoch=number, seconds=epoch["seconds"], loss=epoch["epoch_loss"])
        status["training_complete"] = True
        status["status"] = "TRAINING_EMBEDDINGS_RUNNING"
        update()
        # The author eval entry point resets seed zero independently of training.
        author.utilities.set_random_seed(training["seed"])
        raw, receipt = training_embeddings(author, model, config, dataset, data_dir, hashes, device, budget)
        scaled, mean, scale = author_standardize(raw)
        saved = save_embeddings(output / "TRAIN_EMBEDDINGS.npz", raw, mean, scale)
        freeze = {"dataset": dataset, "bindings": bindings, "completed_epochs": status["completed_epochs"],
                  "checkpoint": status["latest_checkpoint"], "training_embeddings": saved,
                  "test_arrays_loaded": False, "test_labels_loaded": False, "created_utc": utc()}
        write_json(output / "FIT_FREEZE.json", freeze)
        status["fit_freeze_sha256"] = digest(output / "FIT_FREEZE.json")
        status["status"] = "EVALUATION_RUNNING"
        update()
        budget.check()
        arrays = load_arrays(data_dir, dataset, specification["test_graph"], hashes, training_only=False, labels=True)
        status["test_arrays_loaded"] = status["test_labels_loaded"] = True
        update()
        if len(arrays["node_type"]) != specification["expected_test_nodes"]:
            raise ValueError("Evaluation row count differs from declared prepared graph")
        model.eval()
        with torch.no_grad():
            graph = graph_from_arrays(author, arrays, specification, device)
            test_raw = model.embed(graph).detach().cpu().numpy()
        y = arrays["y"].copy()
        del graph, arrays
        if not np.isfinite(test_raw).all():
            raise ValueError("SOURCE_NUMERICAL_HOLD: nonfinite test embeddings")
        test_scaled = (test_raw - mean) / scale
        scorer = ExactFullReferenceKNN(scaled, specification["k"], device, knn["query_batch_size"], knn["reference_batch_size"])
        # Exactly the author's Python random.shuffle order; no reference subsampling.
        indices = list(range(len(raw)))
        random.shuffle(indices)
        normalizer_indices = np.asarray(indices[:min(50000, len(raw))], dtype=np.int64)
        del indices
        normalizer_distances, normalizer_timing = scorer.score(scaled[normalizer_indices], budget.check)
        mean_distance = float(normalizer_distances.mean())
        if not np.isfinite(mean_distance) or mean_distance <= 0:
            raise ValueError("SOURCE_NUMERICAL_HOLD: zero/nonfinite author distance normalizer")
        distances, test_timing = scorer.score(test_scaled, budget.check)
        score = distances / mean_distance
        metrics = oracle_metrics(y, score, specification["author_recall_target"])
        np.savez_compressed(output / "EVALUATION.npz", raw=test_raw, y=y, distances=distances, scores=score,
                            normalizer_indices=normalizer_indices, normalizer_distances=normalizer_distances,
                            mean_distance=np.asarray(mean_distance))
        status.update({"status": "COMPLETE_SOURCE_ORIGINAL_DEVELOPMENT_REPRODUCTION", "evaluation_complete": True,
                       "metrics": metrics, "normalizer_timing": normalizer_timing, "test_scoring_timing": test_timing,
                       "evaluation_sha256": digest(output / "EVALUATION.npz"), "training_embedding_receipt": receipt,
                       "reference_rows": len(raw), "test_rows": len(y), "test_labels_selected_thresholds": True})
        update()
        return status
    except ResourceDeadline as error:
        status.update(status="INCOMPLETE_RESOURCE_DEADLINE", reason=str(error))
        update()
        return status
    except Exception as error:
        status.update(status="SOURCE_NUMERICAL_HOLD" if "SOURCE_NUMERICAL_HOLD" in str(error) else "FAILED_RUNTIME",
                      reason=str(error), error_type=type(error).__name__)
        update()
        emit("dataset_failed", dataset=dataset, status=status["status"], reason=str(error))
        return status
    finally:
        del model, optimizer
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()


def run(args):
    config = validate_config(json.loads(args.config.read_text(encoding="utf-8")))
    datasets = select_datasets(config, args.datasets)
    if args.output.exists() and any(p.name not in BOOTSTRAP_FILES or not p.is_file() for p in args.output.iterdir()):
        raise ValueError("Refusing existing scientific output or unknown startup files")
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    registration = verify_runtime(args.registration, args.data_dir, args.source_dir)
    relative_config = args.config.resolve().relative_to(HERE.parents[2]).as_posix()
    if registration["code_hashes"].get(relative_config) != digest(args.config):
        raise ValueError("Config is not bound by registration")
    write_json(args.output / "WORKER_STATUS.json", {"status": "RUNNING", "scientific_completion": False,
               "worker_pid": os.getpid(), "created_utc": utc(), "selected_datasets": datasets})
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required by registered runtime")
    device = torch.device("cuda:0")
    author = load_author(args.source_dir)
    environment = {"python": sys.version, "platform": platform.platform(), "torch": torch.__version__,
                   "dgl": author.dgl.__version__, "numpy": np.__version__,
                   "sklearn": importlib.metadata.version("scikit-learn"), "cuda": torch.version.cuda,
                   "gpu": torch.cuda.get_device_name(device), "torch_threads": torch.get_num_threads(),
                   "deterministic_algorithms_enabled": torch.are_deterministic_algorithms_enabled(),
                   "historical_runtime_reproduced": False}
    write_json(args.output / "WORKER_ENVIRONMENT.json", environment)
    bindings = {"config_sha256": digest(args.config), "registration_sha256": digest(args.registration),
                "author_source_manifest_sha256": digest(args.source_dir / "SOURCE_MANIFEST.json"),
                "worker_environment_sha256": digest(args.output / "WORKER_ENVIRONMENT.json"),
                "source_commit": registration["source_commit"], "upstream_commit": registration["upstream_commit"],
                "data_manifest_sha256": registration["data_files"]["MANIFEST.json"]}
    qualification = {"author": source_semantics_probe(author, config["training"], device),
                     "synthetic_exact_knn": synthetic_numerical_check(device, config["knn"]), "bindings": bindings}
    write_json(args.output / "RUNTIME_QUALIFICATION.json", qualification)
    # Includes runtime qualification in the 2400-second cap; provenance/setup time is recorded separately.
    budget = Budget(max(0., config["resources"]["science_cap_seconds"] - (time.perf_counter() - started)), args.deadline_epoch)
    results = {"status": "RUNNING", "scope": "EXPOSED_DATA_DEVELOPMENT_REPRODUCTION", "bindings": bindings,
               "selected_datasets": datasets, "unselected_datasets": [d for d in config["datasets"] if d not in datasets],
               "datasets": {}, "novelty_claimed": False, "deployment_readiness_claimed": False,
               "checkpoint_continuation_qualified": False, "created_utc": utc()}
    write_json(args.output / "RUN_STATUS.json", results)
    for dataset in datasets:
        if budget.remaining() < config["resources"]["minimum_qualification_remaining_seconds"]:
            outcome = {"dataset": dataset, "status": "NOT_RUN_RESOURCE_HOLD", "completed_epochs": 0,
                       "training_complete": False, "evaluation_complete": False, "test_arrays_loaded": False,
                       "test_labels_loaded": False, "reason": "Insufficient remaining time to begin qualification"}
        else:
            outcome = run_dataset(author, config, dataset, args.data_dir, registration["data_files"],
                                  args.output / dataset, device, budget, bindings)
        results["datasets"][dataset] = outcome
        emit("dataset_terminal", dataset=dataset, status=outcome["status"])
        write_json(args.output / "RUN_STATUS.json", results)
    results["all_selected_evaluations_complete"] = all(v["evaluation_complete"] for v in results["datasets"].values())
    results["all_registered_evaluations_complete_in_this_attempt"] = datasets == config["datasets"] and results["all_selected_evaluations_complete"]
    failed = any(v["status"] in {"FAILED_RUNTIME", "SOURCE_NUMERICAL_HOLD"} for v in results["datasets"].values())
    results["status"] = "FAILED_RUNTIME" if failed else ("COMPLETE_SELECTED_REPRODUCTIONS" if results["all_selected_evaluations_complete"] else "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION")
    results["elapsed_seconds"] = time.perf_counter() - started
    results["private_artifacts"] = {p.relative_to(args.output).as_posix(): digest(p) for p in args.output.rglob("*")
                                    if p.is_file() and p.name not in BOOTSTRAP_FILES and p.name not in {"RUN_STATUS.json", "RESULTS.json"}}
    write_json(args.output / "RESULTS.json", results)
    write_json(args.output / "RUN_STATUS.json", results)
    write_json(args.output / "WORKER_STATUS.json", {
        "status": "FAILED" if failed else ("COMPLETE" if results["all_selected_evaluations_complete"] else "RESOURCE_HOLD"),
        "scientific_completion": results["all_selected_evaluations_complete"],
        "all_registered_evaluations_complete_in_this_attempt": results["all_registered_evaluations_complete_in_this_attempt"],
        "worker_pid": os.getpid(), "selected_datasets": datasets, "results_sha256": digest(args.output / "RESULTS.json"),
        "dataset_statuses": {d: r["status"] for d, r in results["datasets"].items()}, "completed_utc": utc()})
    emit("worker_terminal", status=results["status"], elapsed_seconds=results["elapsed_seconds"])
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "data-dir", "source-dir", "output", "registration"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--deadline-epoch", type=float, required=True)
    parser.add_argument("--datasets", default="")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        emit("worker_failed", error_type=type(error).__name__, reason=str(error))
        status_path = args.output / "WORKER_STATUS.json"
        if status_path.exists():
            previous = json.loads(status_path.read_text(encoding="utf-8"))
            if previous.get("status") == "RUNNING" and previous.get("worker_pid") == os.getpid():
                write_json(status_path, {**previous, "status": "FAILED", "scientific_completion": False,
                                        "reason": str(error), "error_type": type(error).__name__, "completed_utc": utc()})
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
