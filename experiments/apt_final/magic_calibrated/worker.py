"""Fresh MAGIC models with normal-only thresholds frozen before any test access."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
import torch

from ..magic_reproduction import worker as original
from ..magic_reproduction.model_adapter import build_model, digest, graph_from_arrays, load_arrays, load_author, source_semantics_probe
from ..magic_reproduction.qualification import ResourceDeadline, author_standardize, numerical_check
from ..magic_compact.scoring import ExactFullReferenceKNN

HERE = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat()


def threshold_from_normal(scores, alpha):
    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all() or not 0 < alpha < 1:
        raise ValueError("Calibration requires finite normal scores and alpha in (0,1)")
    rank = int((Decimal(len(scores) + 1) * (Decimal(1) - Decimal(str(alpha)))).to_integral_value(rounding=ROUND_CEILING))
    threshold = None if rank > len(scores) else float(np.sort(scores)[rank - 1])
    result = {"alpha": float(alpha), "n": len(scores), "rank_one_based": rank, "threshold": threshold,
              "comparison": "strict_greater_than", "no_alerts": threshold is None,
              "fit_uses_only_calibration_normal_scores": True, "independent_normal_validation": False}
    predicted = predict(scores, result)
    result.update(calibration_alerts=int(predicted.sum()), calibration_alert_rate=float(predicted.mean()))
    result["calibration_ties_at_threshold"] = 0 if threshold is None else int(np.count_nonzero(scores == threshold))
    if result["calibration_alert_rate"] > alpha:
        raise RuntimeError("Conservative calibration rate exceeds fixed alpha")
    return result


def predict(scores, threshold):
    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError("Prediction scores must be finite one-dimensional values")
    if threshold["comparison"] != "strict_greater_than" or threshold["no_alerts"] != (threshold["threshold"] is None):
        raise ValueError("Invalid frozen threshold receipt")
    return np.zeros(len(scores), dtype=bool) if threshold["no_alerts"] else scores > threshold["threshold"]


def metrics(y, scores, threshold):
    y = np.asarray(y)
    scores = np.asarray(scores)
    if y.shape != scores.shape or set(np.unique(y)) != {0, 1}:
        raise ValueError("Metrics require both binary classes aligned with scores")
    predicted, positive = predict(scores, threshold), y == 1
    tp, fp = int(np.sum(predicted & positive)), int(np.sum(predicted & ~positive))
    fn, tn = int(np.sum(~predicted & positive)), int(np.sum(~predicted & ~positive))
    precision = tp / (tp + fp) if tp + fp else 0.
    recall = tp / (tp + fn)
    return {"n": len(y), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "false_positive_rate": fp / (fp + tn),
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.,
            "auroc": float(roc_auc_score(y, scores)), "average_precision": float(average_precision_score(y, scores)),
            "threshold_selected_using_test_labels": False}


def validate_config(config):
    if config["schema_version"] != 1 or config["source_mode"] != "source_original" or config["datasets"] != ["theia", "cadets"] or config["seeds"] != [0, 101, 211]:
        raise ValueError("The complete fixed six-case inventory is required")
    for dataset, ntypes, etypes, k, ncal, ntest in (("theia", 5, 17, 10, 389106, 344767), ("cadets", 6, 27, 200, 245553, 357173)):
        spec = config["dataset_specs"][dataset]
        required = {"node_types": ntypes, "edge_types": etypes, "k": k, "expected_calibration_nodes": ncal,
                    "expected_test_nodes": ntest, "train_graphs": ["train0", "train1", "train2"],
                    "calibration_graph": "train3", "test_graph": "test0"}
        if any(spec.get(key) != value for key, value in required.items()):
            raise ValueError("Data roles, dimensions or scoring settings changed")
    expected = {"epochs": 50, "hidden_dim": 64, "num_layers": 3, "learning_rate": .001,
                "weight_decay": .0005, "mask_rate": .5, "alpha_l": 3., "negative_slope": .2}
    if any(config["training"].get(key) != value for key, value in expected.items()):
        raise ValueError("Author model/objective settings changed")
    if config["calibration"] != {"alpha": .01} or config["gates"] != {"min_recall": .5, "max_benchmark_negative_fpr": .02}:
        raise ValueError("Frozen normal calibration/readiness criteria changed")
    if not 0 < config["resources"]["science_cap_seconds"] <= 2400:
        raise ValueError("Invalid science cap")
    return config


def estimate_resource(epoch, embeddings, timing, transfer_seconds, serialization_seconds, spec,
                      config, remaining, reserved_tests):
    resources = config["resources"]
    rate = timing["seconds"] / timing["query_rows"]
    per_node = max(x["seconds"] / x["nodes"] for x in embeddings["graphs"])
    multiplier = resources["estimate_multiplier"]
    test_cost = (rate * spec["expected_test_nodes"] + 2 * per_node * spec["expected_test_nodes"]
                 + transfer_seconds + serialization_seconds * spec["expected_test_nodes"] / embeddings["rows"]) * multiplier
    normal_cost = ((config["training"]["epochs"] - 1) * epoch["seconds"] + embeddings["seconds"]
                   + 2 * per_node * spec["expected_calibration_nodes"] + rate * spec["expected_calibration_nodes"]
                   + transfer_seconds + serialization_seconds * (1 + spec["expected_calibration_nodes"] / embeddings["rows"])) * multiplier
    available = max(0., remaining - reserved_tests)
    total = normal_cost + test_cost + resources["safety_seconds"]
    return {"status": "PASS" if total <= available else "NOT_RUN_RESOURCE_HOLD",
            "estimated_remaining_normal_seconds": normal_cost, "reserved_test_seconds": test_cost,
            "prior_cases_reserved_test_seconds": reserved_tests, "available_after_prior_test_reserve": available,
            "estimated_total_with_safety_seconds": total, "remaining_science_seconds": remaining,
            "estimate_multiplier": multiplier, "safety_seconds": resources["safety_seconds"],
            "test_rows_from_config_only": spec["expected_test_nodes"], "test_arrays_or_labels_accessed": False,
            "author_normalizer_queries": 0, "estimate_is_not_guarantee": True}


def one_embedding(author, model, config, dataset, graph_name, data_dir, hashes, device, budget, *, test=False, on_loaded=None):
    budget.check()
    spec = config["dataset_specs"][dataset]
    started = time.perf_counter()
    arrays = load_arrays(data_dir, dataset, graph_name, hashes, training_only=not test, labels=test)
    if on_loaded is not None:
        on_loaded()
    graph = graph_from_arrays(author, arrays, spec, device)
    model.eval()
    with torch.no_grad():
        raw = model.embed(graph).detach().cpu().numpy()
    if raw.shape != (len(arrays["node_type"]), 64) or not np.isfinite(raw).all():
        raise ValueError("Invalid held-out embedding matrix")
    y = arrays["y"].copy() if test else None
    return raw, y, time.perf_counter() - started


def normal_case(author, config, dataset, seed, data_dir, hashes, output, device, budget, bindings, reserved_tests):
    case = f"{dataset}/seed_{seed}"
    directory = output / case
    directory.mkdir(parents=True)
    spec, knn = config["dataset_specs"][dataset], config["knn"]
    status = {"case": case, "dataset": dataset, "seed": seed, "status": "NORMAL_RUNNING", "normal_complete": False,
              "evaluation_complete": False, "completed_epochs": 0, "fit_graphs": spec["train_graphs"],
              "calibration_graph": spec["calibration_graph"], "test_arrays_loaded": False, "test_labels_loaded": False}
    epochs = []
    def update():
        original.write_json(directory / "STATUS.json", status)
        original.write_json(directory / "EPOCHS.json", epochs)
    author.utilities.set_random_seed(seed)
    model = build_model(author, config["training"], spec, device)
    optimizer = author.utilities.create_optimizer("adam", model, config["training"]["learning_rate"], config["training"]["weight_decay"])
    case_bindings = {**bindings, "case": case, "seed": seed}
    update()
    try:
        first = original.train_epoch(author, model, optimizer, config, dataset, data_dir, hashes, device, budget)
        epochs.append({"epoch": 1, **first})
        status["completed_epochs"] = 1
        original.save_checkpoint(directory / "epoch_001.pt", model, optimizer, 1, case_bindings)
        update()
        raw, embedding_time = original.training_embeddings(author, model, config, dataset, data_dir, hashes, device, budget)
        scaled, mean, scale = author_standardize(raw)
        rng = np.random.default_rng(90210)
        ids = rng.choice(len(raw), min(knn["qualification_queries"], len(raw)), replace=False)
        small_bank = rng.choice(len(raw), min(512, len(raw)), replace=False)
        # Direct NumPy oracle validates the new compact path on these real arrays.
        direct = np.sqrt(((scaled[ids[:8], None, :].astype(np.float64) - scaled[small_bank][None].astype(np.float64)) ** 2).sum(axis=2))
        small = ExactFullReferenceKNN(scaled[small_bank], min(spec["k"], len(small_bank)), device,
                                     knn["query_batch_size"], knn["reference_batch_size"])
        checked, _ = small.score(scaled[ids[:8]], budget.check)
        expected = np.sort(direct, axis=1)[:, :min(spec["k"], len(small_bank))].mean(axis=1)
        if not np.allclose(checked, expected, rtol=knn["numerical_rtol"], atol=knn["numerical_atol"]):
            raise RuntimeError("Compact scoring failed direct-distance qualification")
        del small, direct
        start = time.perf_counter()
        scorer = ExactFullReferenceKNN(scaled, spec["k"], device, knn["query_batch_size"], knn["reference_batch_size"])
        transfer = time.perf_counter() - start
        scorer.score(scaled[ids[:1]], budget.check)
        sampled, timing = scorer.score(scaled[ids], budget.check)
        saved = original.save_embeddings(directory / "QUALIFICATION_FIT_EMBEDDINGS.npz", raw, mean, scale,
                                          sample_indices=ids, sample_distances=sampled, numerical_bank_indices=small_bank)
        gate = estimate_resource(first, embedding_time, timing, transfer, saved["seconds"], spec, config, budget.remaining(), reserved_tests)
        original.write_json(directory / "QUALIFICATION.json", {"case": case, "bindings": case_bindings,
            "epoch": first, "training_embeddings": embedding_time, "saved_embeddings": saved,
            "full_reference_sample_timing": timing, "direct_distance_max_error": float(np.max(np.abs(checked - expected))),
            "bank_construction_transfer_seconds": transfer,
            "resource_gate": gate, "test_arrays_loaded": False, "test_labels_loaded": False})
        status["resource_gate"] = gate
        del raw, scaled, scorer
        gc.collect()
        if gate["status"] != "PASS":
            status["status"] = "NOT_RUN_RESOURCE_HOLD"
            update()
            return status
        for epoch in range(2, config["training"]["epochs"] + 1):
            measured = original.train_epoch(author, model, optimizer, config, dataset, data_dir, hashes, device, budget)
            epochs.append({"epoch": epoch, **measured})
            status["completed_epochs"] = epoch
            update()
            original.emit("calibrated_training_epoch", case=case, epoch=epoch, seconds=measured["seconds"])
        checkpoint = original.save_checkpoint(directory / "epoch_050.pt", model, optimizer, config["training"]["epochs"], case_bindings)
        raw, final_embedding_time = original.training_embeddings(author, model, config, dataset, data_dir, hashes, device, budget)
        scaled, mean, scale = author_standardize(raw)
        fit_saved = original.save_embeddings(directory / "FIT_EMBEDDINGS.npz", raw, mean, scale,
                      graph_sizes=np.asarray([x["nodes"] for x in final_embedding_time["graphs"]], dtype=np.int64))
        cal_raw, _, cal_embedding_seconds = one_embedding(author, model, config, dataset, spec["calibration_graph"], data_dir, hashes, device, budget)
        if len(cal_raw) != spec["expected_calibration_nodes"]:
            raise ValueError("Calibration graph row count changed")
        start = time.perf_counter()
        scorer = ExactFullReferenceKNN(scaled, spec["k"], device, knn["query_batch_size"], knn["reference_batch_size"])
        final_transfer = time.perf_counter() - start
        cal_scores, cal_timing = scorer.score((cal_raw - mean) / scale, budget.check)
        threshold = threshold_from_normal(cal_scores, config["calibration"]["alpha"])
        start = time.perf_counter()
        np.savez_compressed(directory / "CALIBRATION.npz", raw=cal_raw, scores=cal_scores)
        cal_save_seconds = time.perf_counter() - start
        test_reserve = (cal_timing["seconds"] / len(cal_raw) * spec["expected_test_nodes"]
                        + 2 * cal_embedding_seconds / len(cal_raw) * spec["expected_test_nodes"] + final_transfer
                        + cal_save_seconds * spec["expected_test_nodes"] / len(cal_raw)) * config["resources"]["estimate_multiplier"]
        files = ["epoch_001.pt", "epoch_050.pt", "EPOCHS.json", "QUALIFICATION_FIT_EMBEDDINGS.npz",
                 "QUALIFICATION.json", "FIT_EMBEDDINGS.npz", "CALIBRATION.npz"]
        freeze = {"case": case, "dataset": dataset, "seed": seed, "bindings": case_bindings,
                  "completed_epochs": status["completed_epochs"], "fit_graphs": spec["train_graphs"],
                  "calibration_graph": spec["calibration_graph"], "threshold": threshold,
                  "checkpoint": checkpoint, "fit_embeddings": fit_saved, "fit_rows": len(raw),
                  "artifacts": {name: digest(directory / name) for name in files},
                  "test_arrays_loaded": False, "test_labels_loaded": False, "created_utc": utc()}
        original.write_json(directory / "FIT_CALIBRATION_FREEZE.json", freeze)
        status.update(status="NORMAL_COMPLETE_FROZEN", normal_complete=True, threshold=threshold,
                      calibration={"rows": len(cal_raw), "alert_count": threshold["calibration_alerts"],
                                   "alert_rate": threshold["calibration_alert_rate"], "independent_normal_validation": False},
                      calibration_timing=cal_timing, reserved_test_seconds=test_reserve,
                      calibration_embedding_seconds=cal_embedding_seconds,
                      final_bank_construction_transfer_seconds=final_transfer,
                      calibration_serialization_seconds=cal_save_seconds,
                      freeze_sha256=digest(directory / "FIT_CALIBRATION_FREEZE.json"), fit_rows=len(raw))
        original.write_json(directory / "NORMAL_RESULT.json", status)
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
        return status
    finally:
        del model, optimizer
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()


def global_freeze(output, cases, expected_cases, bindings):
    if [r["case"] for r in cases] != expected_cases or not all(r["normal_complete"] for r in cases):
        raise ValueError("All six normal cases must finish before any test access")
    inventory = {}
    for case in cases:
        directory = output / case["case"]
        path = directory / "FIT_CALIBRATION_FREEZE.json"
        if digest(path) != case["freeze_sha256"]:
            raise ValueError("Case threshold freeze changed")
        frozen = json.loads(path.read_text(encoding="utf-8"))
        for name, expected in frozen["artifacts"].items():
            if digest(directory / name) != expected:
                raise ValueError("Normal artifact changed before global freeze")
            inventory[case["case"] + "/" + name] = expected
        inventory[case["case"] + "/FIT_CALIBRATION_FREEZE.json"] = digest(path)
        inventory[case["case"] + "/NORMAL_RESULT.json"] = digest(directory / "NORMAL_RESULT.json")
    result = {"status": "ALL_SIX_NORMAL_CASES_FROZEN", "cases": expected_cases, "bindings": bindings,
              "artifacts": inventory, "any_test_arrays_loaded": False, "any_test_labels_loaded": False, "created_utc": utc()}
    original.write_json(output / "GLOBAL_CALIBRATION_FREEZE.json", result)
    return digest(output / "GLOBAL_CALIBRATION_FREEZE.json")


def evaluate_case(author, config, case, data_dir, hashes, output, device, budget, bindings, global_hash):
    global_path = output / "GLOBAL_CALIBRATION_FREEZE.json"
    if digest(global_path) != global_hash:
        raise ValueError("Global normal freeze changed")
    global_record = json.loads(global_path.read_text(encoding="utf-8"))
    expected_cases = [f"{d}/seed_{s}" for d in config["datasets"] for s in config["seeds"]]
    if global_record["cases"] != expected_cases or global_record["bindings"] != bindings:
        raise ValueError("Global frozen case/config inventory changed")
    directory = output / case["case"]
    freeze_path = directory / "FIT_CALIBRATION_FREEZE.json"
    if digest(freeze_path) != case["freeze_sha256"] or global_record["artifacts"][case["case"] + "/FIT_CALIBRATION_FREEZE.json"] != case["freeze_sha256"]:
        raise ValueError("Case freeze differs from global inventory")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for name, expected in freeze["artifacts"].items():
        if digest(directory / name) != expected:
            raise ValueError("Fitted artifact changed before evaluation")
    dataset, seed = case["dataset"], case["seed"]
    spec, knn = config["dataset_specs"][dataset], config["knn"]
    state = torch.load(directory / "epoch_050.pt", map_location="cpu", weights_only=True)
    if state["completed_epochs"] != config["training"]["epochs"] or state["bindings"] != {**bindings, "case": case["case"], "seed": seed}:
        raise ValueError("Full-training checkpoint not bound to this case")
    author.utilities.set_random_seed(seed)
    model = build_model(author, config["training"], spec, device)
    model.load_state_dict(state["model"], strict=True)
    model.eval()
    with np.load(directory / "FIT_EMBEDDINGS.npz", allow_pickle=False) as archive:
        raw, mean, scale = archive["raw"], archive["mean"], archive["scale"]
    try:
        budget.check()
        case["test_access_attempted"] = True
        original.write_json(directory / "STATUS.json", {**case, "status": "TEST_ACCESS_ATTEMPTED"})
        def loaded():
            case["test_arrays_loaded"] = case["test_labels_loaded"] = True
            original.write_json(directory / "STATUS.json", {**case, "status": "TEST_ARRAYS_LOADED"})
        test_raw, y, embedding_seconds = one_embedding(author, model, config, dataset, spec["test_graph"], data_dir, hashes, device, budget, test=True, on_loaded=loaded)
        if len(y) != spec["expected_test_nodes"]:
            raise ValueError("Evaluation graph row count changed")
        scorer = ExactFullReferenceKNN((raw - mean) / scale, spec["k"], device, knn["query_batch_size"], knn["reference_batch_size"])
        scores, timing = scorer.score((test_raw - mean) / scale, budget.check)
        frozen_threshold = freeze["threshold"]
        predicted = predict(scores, frozen_threshold)
        measured = metrics(y, scores, frozen_threshold)
        np.savez_compressed(directory / "EVALUATION.npz", raw=test_raw, scores=scores, y=y, predicted=predicted)
        ready = measured["recall"] >= config["gates"]["min_recall"] and measured["false_positive_rate"] <= config["gates"]["max_benchmark_negative_fpr"]
        result = {**case, "status": "COMPLETE_FIXED_NORMAL_CALIBRATED_CASE", "evaluation_complete": True,
                  "test_arrays_loaded": True, "test_labels_loaded": True, "metrics": measured, "readiness": ready,
                  "threshold": frozen_threshold, "global_freeze_sha256": global_hash,
                  "test_embedding_seconds": embedding_seconds, "scoring_timing": timing,
                  "evaluation_sha256": digest(directory / "EVALUATION.npz")}
        original.write_json(directory / "CASE_RESULT.json", result)
        return result
    finally:
        del model
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()


def execute_cases(author, config, data_dir, hashes, output, device, budget, bindings):
    expected = [f"{d}/seed_{s}" for d in config["datasets"] for s in config["seeds"]]
    cases, reserved = [], 0.
    for dataset in config["datasets"]:
        for seed in config["seeds"]:
            if budget.remaining() - reserved < config["resources"]["minimum_qualification_remaining_seconds"]:
                case = {"case": f"{dataset}/seed_{seed}", "dataset": dataset, "seed": seed, "status": "NOT_RUN_RESOURCE_HOLD",
                        "normal_complete": False, "evaluation_complete": False, "completed_epochs": 0,
                        "test_arrays_loaded": False, "test_labels_loaded": False, "reason": "Remaining time reserved for earlier test replays"}
            else:
                case = normal_case(author, config, dataset, seed, data_dir, hashes, output, device, budget, bindings, reserved)
            cases.append(case)
            reserved += case.get("reserved_test_seconds", 0.) if case["normal_complete"] else 0.
            original.write_json(output / "NORMAL_PROGRESS.json", {"cases": cases, "pending_test_reserve_seconds": reserved})
            original.emit("normal_case_terminal", case=case["case"], status=case["status"])
    if not all(r["normal_complete"] for r in cases):
        return cases, None
    frozen_hash = global_freeze(output, cases, expected, bindings)
    completed = []
    for case in cases:
        try:
            result = evaluate_case(author, config, case, data_dir, hashes, output, device, budget, bindings, frozen_hash)
        except ResourceDeadline as error:
            result = {**case, "status": "INCOMPLETE_RESOURCE_DEADLINE", "reason": str(error)}
        except Exception as error:
            result = {**case, "status": "FAILED_RUNTIME", "reason": str(error), "error_type": type(error).__name__}
        completed.append(result)
        original.write_json(output / "EVALUATION_PROGRESS.json", {"cases": completed, "global_freeze_sha256": frozen_hash})
        original.emit("calibrated_case_terminal", case=case["case"], status=result["status"])
    return completed, frozen_hash


def run(args):
    from .provenance import verify_runtime
    config = validate_config(json.loads(args.config.read_text(encoding="utf-8")))
    if args.datasets and args.datasets.split(",") != config["datasets"]:
        raise ValueError("This study requires the complete registered case inventory")
    if args.output.exists() and any(p.name not in original.BOOTSTRAP_FILES or not p.is_file() for p in args.output.iterdir()):
        raise ValueError("Refusing preexisting scientific outputs")
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    record = verify_runtime(args.registration, args.data_dir, args.source_dir)
    config_relative = args.config.resolve().relative_to(HERE.parents[2]).as_posix()
    if record["code_hashes"].get(config_relative) != digest(args.config):
        raise ValueError("Unbound calibration configuration")
    if not torch.cuda.is_available():
        raise RuntimeError("Registered CUDA runtime required")
    device = torch.device("cuda:0")
    author = load_author(args.source_dir)
    environment = {"python": sys.version, "platform": platform.platform(), "torch": torch.__version__,
                   "dgl": author.dgl.__version__, "numpy": np.__version__, "sklearn": importlib.metadata.version("scikit-learn"),
                   "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(device), "torch_threads": torch.get_num_threads()}
    original.write_json(args.output / "WORKER_ENVIRONMENT.json", environment)
    bindings = {"config_sha256": digest(args.config), "registration_sha256": digest(args.registration),
                "source_commit": record["source_commit"], "upstream_commit": record["upstream_commit"],
                "source_manifest_sha256": digest(args.source_dir / "SOURCE_MANIFEST.json"),
                "environment_sha256": digest(args.output / "WORKER_ENVIRONMENT.json"),
                "bundle_sha256": os.environ.get("APT_FROZEN_BUNDLE_SHA256"),
                "original_source_commit": record.get("original_source_commit"),
                "compact_source_commit": record.get("compact_source_commit"),
                "data_manifest_sha256": record["data_files"]["MANIFEST.json"]}
    original.write_json(args.output / "RUNTIME_QUALIFICATION.json", source_semantics_probe(author, config["training"], device))
    budget = original.Budget(max(0., config["resources"]["science_cap_seconds"] - (time.perf_counter() - started)), args.deadline_epoch)
    cases, frozen = execute_cases(author, config, args.data_dir, record["data_files"], args.output, device, budget, bindings)
    complete = len(cases) == 6 and all(c["evaluation_complete"] for c in cases)
    ready = complete and all(c["readiness"] for c in cases)
    failed = any(c["status"] in {"FAILED_RUNTIME", "SOURCE_NUMERICAL_HOLD"} for c in cases)
    result = {"status": "FAILED_RUNTIME" if failed else ("COMPLETE_CALIBRATED_EVALUATION" if complete else "INCOMPLETE_CALIBRATION_OR_EVALUATION"),
              "scope": "PREVIOUSLY_EXPOSED_DEVELOPMENT_DATA", "bindings": bindings, "cases": cases,
              "selected_datasets": config["datasets"],
              "scientific_completion": complete, "all_selected_evaluations_complete": complete,
              "all_registered_evaluations_complete_in_this_attempt": complete,
              "decision": "DEVELOPMENT_READINESS_PASS" if ready else ("NO_GO_FIXED_CALIBRATED_METHOD" if complete else "PENDING_INCOMPLETE"),
              "global_freeze_sha256": frozen, "normal_phase_all_cases_before_any_test": True,
              "novelty_claimed": False, "independent_campaign_confirmation": False, "independent_normal_validation": False,
              "elapsed_seconds": time.perf_counter() - started, "created_utc": utc(),
              "private_artifacts": {p.relative_to(args.output).as_posix(): digest(p) for p in args.output.rglob("*")
                                    if p.is_file() and p.name not in original.BOOTSTRAP_FILES}}
    original.write_json(args.output / "RESULTS.json", result)
    original.write_json(args.output / "WORKER_STATUS.json", {"status": "FAILED" if failed else ("COMPLETE" if complete else "RESOURCE_HOLD"),
        "scientific_completion": complete, "decision": result["decision"], "results_sha256": digest(args.output / "RESULTS.json")})
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "registration", "data-dir", "source-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--deadline-epoch", type=float, required=True)
    parser.add_argument("--datasets", default="")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        original.emit("calibrated_worker_failed", reason=str(error), error_type=type(error).__name__)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
