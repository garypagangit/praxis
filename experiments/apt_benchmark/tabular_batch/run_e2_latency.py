"""CPU-only necessary-speed-condition pilot; no held-out quality evaluation.

Both models predict the same label-blind sample with actual inference calls.
The screen alone must cost <= one fifth of the full stage model for the proposed
serial cascade to reach fivefold throughput under this execution configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time
from typing import Any, Callable

import numpy as np
from sklearn.impute import SimpleImputer
from threadpoolctl import threadpool_limits

from . import run_e1
from .model_backend import create_foundation_classifier


def select_latency_rows(split: np.ndarray, fingerprints: np.ndarray, *, seed: int, count: int) -> np.ndarray:
    """Query selection takes no labels, model scores, or outcome arguments."""
    candidates = np.flatnonzero(split == 2)
    if len(candidates) < count:
        raise ValueError("Insufficient development-test rows for the frozen timing batch.")
    ranked = sorted(candidates.tolist(), key=lambda index: hashlib.sha256(
        f"{seed}|{fingerprints[index]}".encode("ascii")).digest())
    return np.asarray(ranked[:count], dtype=np.int64)


def latency_decision(stage_seconds: list[float], screen_seconds: list[float], *, required_speedup: float = 5.0) -> dict[str, Any]:
    if len(stage_seconds) != 3 or len(screen_seconds) != 3:
        raise ValueError("Exactly three measured repeats are required per model.")
    if not all(np.isfinite(value) and value > 0 for value in [*stage_seconds, *screen_seconds]):
        raise ValueError("Measured durations must be positive and finite.")
    stage = float(np.median(stage_seconds))
    screen = float(np.median(screen_seconds))
    passed = screen <= stage / required_speedup
    return {
        "full_stage_median_seconds": stage,
        "screen_alone_median_seconds": screen,
        "required_screen_max_seconds": stage / required_speedup,
        "required_speedup": required_speedup,
        "observed_optimistic_serial_cascade_speedup_ceiling": stage / screen,
        "necessary_speed_condition_passed": bool(passed),
        "status": "NECESSARY_CONDITION_PASS_ONLY" if passed else "CPU_CANDIDATE_FAILS_NECESSARY_SPEED_CONDITION",
        "interpretation": "Measured CPU configuration only; not a full cascade, quality frontier, statistical timing guarantee, or GPU result.",
    }


def paired_predictions(
    stage_model: Any, screen_model: Any, imputer: SimpleImputer, query: np.ndarray,
    *, clock: Callable[[], float] = time.perf_counter,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """One warmup per model, then three alternating paired real predictions.

    Transform is inside every timer; no cached probabilities or cached transformed
    batch substitute for measured calls. Models may retain their ordinary fitted
    state and library caches. CPU calls complete synchronously.
    """
    models = {"full_stage": stage_model, "screen_alone": screen_model}
    recorded: dict[str, list[float]] = {key: [] for key in models}
    warmups: dict[str, float] = {}
    predictions: dict[str, list[np.ndarray]] = {key: [] for key in models}
    for name, model in models.items():
        started = clock()
        values = np.asarray(model.predict_proba(imputer.transform(query)))
        elapsed = clock() - started
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite warmup predictions.")
        warmups[name] = elapsed
    orders = [["full_stage", "screen_alone"], ["screen_alone", "full_stage"], ["full_stage", "screen_alone"]]
    for repeat, order in enumerate(orders):
        for name in order:
            print(json.dumps({"event": "latency_repeat_start", "model": name, "repeat": repeat + 1}), flush=True)
            started = clock()
            values = np.asarray(models[name].predict_proba(imputer.transform(query)))
            elapsed = clock() - started
            if len(values) != len(query) or not np.isfinite(values).all() or not np.allclose(values.sum(axis=1), 1, atol=1e-5):
                raise ValueError("Malformed measured probability output.")
            recorded[name].append(elapsed)
            predictions[name].append(values.copy())
            print(json.dumps({"event": "latency_repeat_complete", "model": name, "repeat": repeat + 1, "seconds": elapsed}), flush=True)
    return ({"warmup_seconds": warmups, "measured_seconds": recorded, "measured_order": orders},
            {name: np.stack(values) for name, values in predictions.items()})


def validate_protocol(protocol: dict[str, Any], e1_protocol: dict[str, Any], e1_path: Path) -> None:
    expected = {"schema_version": 1, "experiment": "E2_CPU_LATENCY_NECESSARY_CONDITION", "seed": 20260921,
                "status": "FROZEN_BEFORE_SCIENTIFIC_MODEL_FITS",
                "samples_per_class": 32, "query_rows": 1024, "warmup_repeats": 1, "measured_repeats": 3,
                "required_speedup": 5.0, "cpu_threads": 4, "torch_interop_threads": 2,
                "screen_model": "tabpfn_2_5_synthetic", "screen_n_estimators": 4, "device": "cpu",
                "negative_class": "NormalTraffic"}
    for key, value in expected.items():
        if protocol.get(key) != value:
            raise ValueError(f"Frozen protocol field {key} differs from the runner.")
    if protocol.get("measured_pair_order") != [["full_stage", "screen_alone"], ["screen_alone", "full_stage"], ["full_stage", "screen_alone"]]:
        raise ValueError("Frozen timing order differs from the runner.")
    if protocol["e1_protocol_sha256"] != run_e1.sha256_file(e1_path):
        raise ValueError("Linked E1 protocol hash mismatch.")
    if any(protocol[key] != e1_protocol[key] for key in ("data_npz_sha256", "manifest_sha256")):
        raise ValueError("E2 and E1 inputs differ.")
    run_e1.validate_protocol(e1_protocol)


def make_stage_tree(name: str, seed: int, params: dict[str, Any], n_classes: int) -> Any:
    return run_e1.make_tree(name, seed, params, n_classes).set_params(n_jobs=4)


def run(data_path: Path, protocol_path: Path, e1_protocol_path: Path, output: Path, model_cache: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a fresh output directory; prior attempts are preserved.")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    e1_protocol = json.loads(e1_protocol_path.read_text(encoding="utf-8"))
    validate_protocol(protocol, e1_protocol, e1_protocol_path)
    if data_path.is_dir():
        data_path = data_path / "DATA.npz"
    data, manifest = run_e1.load_data(data_path, e1_protocol)
    support = run_e1.select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=protocol["seed"], budget=32)
    queries = select_latency_rows(data["split"], data["group_sha256"], seed=protocol["seed"], count=1024)
    classes = data["classes"].tolist()
    if classes.count("NormalTraffic") != 1:
        raise ValueError("A qualified NormalTraffic class is required for the binary screen.")
    normal_label = classes.index("NormalTraffic")
    X_fit, y_fit = data["X"][support], data["y"][support]
    binary_fit = (y_fit != normal_label).astype(np.int64)
    source = Path(__file__).resolve().parent
    binding = {"protocol_sha256": run_e1.sha256_file(protocol_path),
               "e1_protocol_sha256": run_e1.sha256_file(e1_protocol_path),
               "data_npz_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
               "code_sha256": {name: run_e1.sha256_file(source / name) for name in
                               ("run_e2_latency.py", "run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt")},
               "seed": protocol["seed"], "selected_fit_indices": support.tolist(),
               "selected_fit_fingerprints": data["group_sha256"][support].tolist(),
               "query_indices": queries.tolist(), "query_fingerprints": data["group_sha256"][queries].tolist(),
               "versions": run_e1.package_versions(), "device": "cpu", "cpu_threads": 4,
               "processor": platform.processor(), "logical_cpu_count": os.cpu_count()}
    run_e1.write_json(output / "PREFIT_RECEIPT.json", {"created_utc": run_e1.utc_now(), "binding": binding,
                       "binding_sha256": run_e1.canonical_hash(binding), "fitting_started_at_receipt": False,
                       "heldout_outcomes_evaluated": False, "scope": manifest["evaluation_scope"]})
    # The receipt exists before preprocessing fit, inner CV, or final-model fits.
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    fit_receipt: dict[str, Any] = {"tree_selection": {}, "timing_seconds": {}}
    with threadpool_limits(limits=4):
        for name in ("xgboost", "lightgbm"):
            print(json.dumps({"event": "inner_cv_start", "model": name}), flush=True)
            started = time.perf_counter()
            # E1 tuning retains identical folds/grid and n_jobs=1; final inference
            # below gives the selected tree the declared four-thread CPU budget.
            fit_receipt["tree_selection"][name] = run_e1.tune_tree(name, X_fit, y_fit, protocol["seed"], e1_protocol["model_grids"][name], 3)
            fit_receipt["timing_seconds"][name + "_inner_cv"] = time.perf_counter() - started
        winner = max(("xgboost", "lightgbm"), key=lambda name: fit_receipt["tree_selection"][name]["selected_mean_macro_f1"])
        fit_receipt["selected_gbdt"] = winner
        selected_params = fit_receipt["tree_selection"][winner]["selected_parameters"]
        stage_model = make_stage_tree(winner, protocol["seed"], selected_params, len(classes))
        imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        started = time.perf_counter()
        fit_features = imputer.fit_transform(X_fit)
        fit_receipt["timing_seconds"]["shared_imputer_fit_transform"] = time.perf_counter() - started
        started = time.perf_counter()
        stage_model.fit(fit_features, y_fit)
        fit_receipt["timing_seconds"]["full_stage_fit"] = time.perf_counter() - started
        started = time.perf_counter()
        screen_model, backend = create_foundation_classifier("tabpfn_2_5_synthetic", model_cache, seed=protocol["seed"], device="cpu", n_estimators=4, allow_download=False)
        fit_receipt["timing_seconds"]["screen_constructor_and_checkpoint"] = time.perf_counter() - started
        started = time.perf_counter()
        screen_model.fit(fit_features, binary_fit)
        fit_receipt["timing_seconds"]["screen_fit"] = time.perf_counter() - started
        backend.update(fitted=True, runtime_compatibility_tested=True)
        fit_receipt["screen_backend"] = backend
        fit_receipt["training_binary_counts"] = np.bincount(binary_fit, minlength=2).tolist()
        run_e1.write_json(output / "FIT_RECEIPT.json", fit_receipt)
        # Query labels are never passed to the timer or to a quality metric.
        timing, predictions = paired_predictions(stage_model, screen_model, imputer, data["X"][queries])
    private_predictions = output / "PREDICTIONS_PRIVATE.npz"
    np.savez_compressed(private_predictions, full_stage_probabilities=predictions["full_stage"],
                        screen_probabilities=predictions["screen_alone"], query_indices=queries,
                        query_fingerprints=data["group_sha256"][queries], selected_fit_indices=support,
                        selected_fit_fingerprints=data["group_sha256"][support],
                        stage_classes=np.asarray(stage_model.classes_), screen_classes=np.asarray(screen_model.classes_),
                        imputer_statistics=imputer.statistics_)
    decision = latency_decision(timing["measured_seconds"]["full_stage"], timing["measured_seconds"]["screen_alone"])
    aggregate = {"schema_version": 1, "experiment": protocol["experiment"], "completed_utc": run_e1.utc_now(),
                 "input_sha256": protocol["data_npz_sha256"], "protocol_sha256": binding["protocol_sha256"],
                 "prefit_receipt_sha256": run_e1.sha256_file(output / "PREFIT_RECEIPT.json"),
                 "fit_receipt_sha256": run_e1.sha256_file(output / "FIT_RECEIPT.json"),
                 "private_predictions_sha256": run_e1.sha256_file(private_predictions),
                 "selected_gbdt": winner, "selected_gbdt_parameters": selected_params,
                 "screen_model": "tabpfn_2_5_synthetic", "device": "cpu", "cpu_threads": 4,
                 "torch_interop_threads": 2, "seed": protocol["seed"], "selected_fit_rows": len(support),
                 "query_rows": len(queries), "query_selection": "SHA256(seed|fingerprint), labels not consulted",
                 "timing": timing, "decision": decision, "versions": binding["versions"],
                 "heldout_classification_outcomes_evaluated": False, "full_cascade_evaluated": False,
                 "gpu_evaluated": False, "same_hardware": True,
                 "limitations": ["One development seed and one batch of 1024 rows.",
                                 "Warm CPU execution, no concurrency; median of three measurements is descriptive.",
                                 "Necessary speed condition only; screen accuracy and full quality/throughput frontier untested.",
                                 "Changing hardware, compression, caching strategy or model settings requires a separate registered test."]}
    run_e1.write_json(output / "AGGREGATE.json", aggregate)
    run_e1.write_json(output / "COMPLETE.json", {"binding_sha256": run_e1.canonical_hash(binding),
                       "artifact_sha256": {name: run_e1.sha256_file(output / name) for name in
                                           ("PREFIT_RECEIPT.json", "FIT_RECEIPT.json", "PREDICTIONS_PRIVATE.npz", "AGGREGATE.json")}})
    print(json.dumps({"event": "latency_pilot_complete", "decision": decision}), flush=True)
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--e1-protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    args = parser.parse_args()
    run(args.data, args.protocol, args.e1_protocol, args.output, args.model_cache)


if __name__ == "__main__":
    main()
