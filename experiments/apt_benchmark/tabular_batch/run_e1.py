"""Frozen few-label development evaluation with fit-only model selection.

Every selected support set is recorded before fitting. Calibration labels are
saved for downstream uncertainty evaluation and never used for model selection.
An output directory binds one exact model subset/device/environment; separate
hardware runs can be combined using each cell's comparison_binding.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_recall_fscore_support, roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

try:
    from .model_backend import create_foundation_classifier
except ImportError:
    from model_backend import create_foundation_classifier


MODELS = ("random_forest", "xgboost", "lightgbm", "tabicl_v2", "tabpfn_2_5_synthetic")
FOUNDATION = frozenset(MODELS[3:])
DEFAULT_GRIDS = {
    "xgboost": [
        {"n_estimators": 100, "max_depth": 2, "learning_rate": 0.05},
        {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1},
        {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05},
    ],
    "lightgbm": [
        {"n_estimators": 100, "num_leaves": 7, "learning_rate": 0.05},
        {"n_estimators": 100, "num_leaves": 15, "learning_rate": 0.1},
        {"n_estimators": 200, "num_leaves": 15, "learning_rate": 0.05},
    ],
}


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + ".tmp")
    staged.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(staged, path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def package_versions() -> dict[str, str | None]:
    values: dict[str, str | None] = {"python": platform.python_version()}
    for name in ("numpy", "scipy", "scikit-learn", "pandas", "xgboost", "lightgbm", "torch", "tabicl", "tabpfn"):
        try:
            values[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            values[name] = None
    return values


def select_fit_indices(y: np.ndarray, split: np.ndarray, fingerprints: np.ndarray, *, seed: int, budget: int) -> np.ndarray:
    """Sample exclusively from fit; stable even if source row order changes."""
    rng = np.random.default_rng(seed)
    selected = []
    for label in np.unique(y):
        pool = np.flatnonzero((split == 0) & (y == label))
        pool = pool[np.argsort(fingerprints[pool], kind="stable")]
        if len(pool) < budget:
            raise ValueError(f"Class {label} has {len(pool)} fit rows, below budget {budget}.")
        selected.extend(rng.choice(pool, size=budget, replace=False).tolist())
    return np.asarray(selected, dtype=np.int64)


def validate_protocol(protocol: dict[str, Any]) -> None:
    if protocol.get("schema_version") != 1 or protocol.get("experiment") != "E1":
        raise ValueError("Expected schema_version=1 and experiment=E1.")
    if protocol.get("samples_per_class") != 32 or protocol.get("n_splits") != 3:
        raise ValueError("This registered runner requires 32 samples/class and 3 inner folds.")
    if protocol.get("prediction_chunk_rows") != 1024 or protocol.get("foundation_n_estimators") != 4:
        raise ValueError("Frozen chunk/ensemble settings differ from the runner.")
    if protocol.get("model_grids") != DEFAULT_GRIDS:
        raise ValueError("Model grids differ from the three frozen candidates.")
    if set(protocol.get("models", [])) != set(MODELS):
        raise ValueError("Protocol must register all five model families.")
    if protocol.get("seeds") != list(range(20260921, 20260931)):
        # Synthetic software tests can run one seed; never use this for SCVIC.
        if protocol.get("study_kind") != "synthetic_smoke" or protocol.get("seeds") != [20260921]:
            raise ValueError("Expected the ten registered seeds.")


def load_data(data_path: Path, protocol: dict[str, Any]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    manifest_path = data_path.with_name("MANIFEST.json")
    if sha256_file(data_path) != protocol["data_npz_sha256"] or sha256_file(manifest_path) != protocol["manifest_sha256"]:
        raise ValueError("Input or manifest hash does not match the frozen protocol.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with np.load(data_path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    required = {"X", "y", "split", "group_sha256", "classes", "feature_names"}
    if not required <= data.keys():
        raise ValueError("Prepared input is missing required arrays.")
    X, y, split, fingerprints = (data[key] for key in ("X", "y", "split", "group_sha256"))
    if X.ndim != 2 or any(len(a) != len(X) for a in (y, split, fingerprints)):
        raise ValueError("Prepared array dimensions disagree.")
    if not np.array_equal(np.unique(y), np.arange(len(data["classes"]))):
        raise ValueError("Labels must be contiguous integer class indices.")
    if set(np.unique(split)) != {0, 1, 2} or np.isinf(X).any():
        raise ValueError("Expected fit/calibration/test partitions and finite-or-NaN features.")
    if len(np.unique(fingerprints)) != len(fingerprints):
        raise ValueError("Repeated feature fingerprints violate the preparation gate.")
    if manifest.get("data_npz_sha256") != protocol["data_npz_sha256"]:
        raise ValueError("Manifest does not bind these input bytes.")
    if protocol.get("study_kind") != "synthetic_smoke" and len(data["classes"]) != 6:
        raise ValueError("The SCVIC development protocol requires six classes.")
    return data, manifest


def make_tree(name: str, seed: int, params: dict[str, Any], n_classes: int) -> Any:
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=1)
    if name == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(
            **params, random_state=seed, n_jobs=1, tree_method="hist", device="cpu",
            objective="multi:softprob", num_class=n_classes, eval_metric="mlogloss",
        )
    if name == "lightgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(
            **params, random_state=seed, n_jobs=1, verbosity=-1, deterministic=True,
            force_col_wise=True, min_child_samples=5,
        )
    raise ValueError(f"Unknown tree model {name}")


def tune_tree(name: str, X: np.ndarray, y: np.ndarray, seed: int, grid: list[dict[str, Any]], n_splits: int) -> dict[str, Any]:
    """All imputation and tuning occur inside the selected support rows."""
    folds = list(StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(X, y))
    scores = []
    for params in grid:
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("classifier", make_tree(name, seed, params, len(np.unique(y)))),
        ])
        fold_scores = []
        for train, validation in folds:
            fitted = clone(pipeline).fit(X[train], y[train])
            fold_scores.append(float(f1_score(y[validation], fitted.predict(X[validation]), average="macro", zero_division=0)))
        scores.append({"parameters": params, "fold_macro_f1": fold_scores, "mean_macro_f1": float(np.mean(fold_scores))})
    winner = max(range(len(scores)), key=lambda index: scores[index]["mean_macro_f1"])
    return {"selected_candidate_index": winner, "selected_parameters": grid[winner],
            "selected_mean_macro_f1": scores[winner]["mean_macro_f1"], "candidates": scores,
            "tie_policy": "first candidate in protocol order", "selection_data": "selected fit support only"}


def probability_metrics(y: np.ndarray, probabilities: np.ndarray, classes: list[str]) -> dict[str, Any]:
    if probabilities.shape != (len(y), len(classes)) or not np.isfinite(probabilities).all():
        raise ValueError("Invalid probability shape or nonfinite output.")
    if (probabilities < -1e-7).any() or not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-5):
        raise ValueError("Model probabilities do not form distributions.")
    labels = np.arange(len(classes))
    predicted = probabilities.argmax(axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(y, predicted, labels=labels, zero_division=0)
    stages, aucs, aps = {}, [], []
    for index, name in enumerate(classes):
        truth = y == index
        auc = float(roc_auc_score(truth, probabilities[:, index])) if truth.any() and (~truth).any() else None
        ap = float(average_precision_score(truth, probabilities[:, index])) if truth.any() else None
        aucs.append(auc)
        aps.append(ap)
        stages[name] = {"precision": float(precision[index]), "recall": float(recall[index]),
                        "f1": float(f1[index]), "support": int(support[index]), "roc_auc_ovr": auc, "average_precision_ovr": ap}
    return {"n": len(y), "accuracy": float(accuracy_score(y, predicted)),
            "macro_f1": float(f1.mean()),
            "roc_auc_ovr_macro": float(np.mean(aucs)) if all(v is not None for v in aucs) else None,
            "average_precision_ovr_macro": float(np.mean(aps)) if all(v is not None for v in aps) else None,
            "classes": classes, "confusion_matrix": confusion_matrix(y, predicted, labels=labels).tolist(), "per_stage": stages}


def synchronize(device: str) -> None:
    if device.startswith("cuda"):
        import torch
        torch.cuda.synchronize()


def predict_chunks(model: Any, imputer: SimpleImputer, X: np.ndarray, *, n_classes: int, chunk_rows: int, device: str) -> tuple[np.ndarray, float]:
    synchronize(device)
    started = time.perf_counter()
    result = np.empty((len(X), n_classes), dtype=np.float64)
    order = np.asarray(model.classes_, dtype=np.int64)
    if not np.array_equal(np.sort(order), np.arange(n_classes)):
        raise ValueError("Fitted model is missing registered classes.")
    for offset in range(0, len(X), chunk_rows):
        values = model.predict_proba(imputer.transform(X[offset:offset + chunk_rows]))
        result[offset:offset + len(values), order] = values
    synchronize(device)
    return result, time.perf_counter() - started


def validate_completed(cell_dir: Path, execution_binding: str, comparison_binding: str) -> dict[str, Any] | None:
    completion = cell_dir / "COMPLETE.json"
    if not completion.exists():
        if cell_dir.exists() and any(cell_dir.iterdir()):
            raise ValueError("Incomplete nonempty cell is preserved; use a fresh output directory.")
        return None
    marker = json.loads(completion.read_text(encoding="utf-8"))
    if marker.get("execution_binding") != execution_binding or marker.get("comparison_binding") != comparison_binding:
        raise ValueError("Completed cell belongs to another immutable run.")
    for name, digest in marker["file_sha256"].items():
        if name not in ("CELL.json", "PREDICTIONS.npz") or sha256_file(cell_dir / name) != digest:
            raise ValueError("Completed cell artifact hash mismatch.")
    if set(marker["file_sha256"]) != {"CELL.json", "PREDICTIONS.npz"}:
        raise ValueError("Completed cell is missing required artifacts.")
    cell = json.loads((cell_dir / "CELL.json").read_text(encoding="utf-8"))
    if cell.get("execution_binding") != execution_binding or cell.get("comparison_binding") != comparison_binding:
        raise ValueError("Cell metadata and completion binding disagree.")
    if cell.get("prediction_sha256") != marker["file_sha256"]["PREDICTIONS.npz"]:
        raise ValueError("Cell prediction binding and completion hash disagree.")
    return cell


def build_summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    by_seed: dict[int, dict[str, Any]] = {}
    for cell in cells:
        by_seed.setdefault(cell["seed"], {})[cell["model"]] = cell
    for seed, models in sorted(by_seed.items()):
        if {"tabicl_v2", "xgboost", "lightgbm"} <= models.keys():
            candidates = [models["xgboost"], models["lightgbm"]]
            winner = max(candidates, key=lambda cell: cell["inner_cv"]["selected_mean_macro_f1"])
            primary = models["tabicl_v2"]
            if len({cell["comparison_binding"] for cell in [primary, *candidates]}) != 1:
                raise ValueError("Cannot compare cells with different input/support bindings.")
            comparisons.append({"seed": seed, "gbdt_selected_by_inner_cv": winner["model"],
                                "tabicl_macro_f1": primary["metrics"]["test"]["macro_f1"],
                                "selected_gbdt_macro_f1": winner["metrics"]["test"]["macro_f1"],
                                "delta_macro_f1": primary["metrics"]["test"]["macro_f1"] - winner["metrics"]["test"]["macro_f1"]})
    return {"schema_version": 1, "completed_cells": len(cells), "cells": cells,
            "primary_comparisons": comparisons,
            "mean_primary_delta_macro_f1": float(np.mean([c["delta_macro_f1"] for c in comparisons])) if comparisons else None,
            "interpretation": "Descriptive within-training deduplicated development screen; repeated seeds share one test set. No independent-seed CI, chronological, early-warning, incident-generalization, or population claim.",
            "gbdt_family_tie_policy": "xgboost first", "success_claim": None}


def run(data_path: Path, protocol_path: Path, output: Path, models: list[str], *, device: str, model_cache: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    validate_protocol(protocol)
    if not models or len(set(models)) != len(models) or not set(models) <= set(MODELS):
        raise ValueError("Model subset contains unknown, duplicate, or no models.")
    if device not in ("cpu", "cuda"):
        raise ValueError("E1 requires explicit cpu or cuda execution.")
    if data_path.is_dir():
        data_path = data_path / "DATA.npz"
    data, manifest = load_data(data_path, protocol)
    source_root = Path(__file__).resolve().parent
    source_hashes = {name: sha256_file(source_root / name) for name in ("run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt")}
    common_binding = {"data_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
                      "protocol_sha256": sha256_file(protocol_path), "code_sha256": source_hashes}
    supports = {}
    for seed in protocol["seeds"]:
        rows = select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=seed, budget=32)
        supports[str(seed)] = {"indices": rows.tolist(), "fingerprints": data["group_sha256"][rows].tolist()}
    execution = {**common_binding, "models": models, "requested_device": device, "versions": package_versions(), "supports": supports}
    execution_binding = canonical_hash(execution)
    prefit_path = output / "PREFIT_RECEIPT.json"
    if prefit_path.exists():
        previous = json.loads(prefit_path.read_text(encoding="utf-8"))
        if previous["execution_binding"] != execution_binding or previous["execution"] != execution:
            raise ValueError("Output directory is bound to a different run; use a fresh directory.")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("Nonempty output without a prefit receipt cannot be reused.")
        write_json(prefit_path, {"created_utc": utc_now(), "execution_binding": execution_binding, "execution": execution,
                                "scientific_fits_started": False, "scope": manifest.get("evaluation_scope")})
    prefit_sha = sha256_file(prefit_path)
    calibration_rows = np.flatnonzero(data["split"] == 1)
    test_rows = np.flatnonzero(data["split"] == 2)
    classes = data["classes"].tolist()
    cells = []
    for seed in protocol["seeds"]:
        rows = np.asarray(supports[str(seed)]["indices"], dtype=np.int64)
        comparison_binding = canonical_hash({**common_binding, "seed": seed, "support": supports[str(seed)]})
        X_fit, y_fit = data["X"][rows], data["y"][rows]
        for name in models:
            cell_dir = output / "cells" / name / str(seed)
            complete = validate_completed(cell_dir, execution_binding, comparison_binding)
            if complete is not None:
                print(json.dumps({"event": "resume_completed", "model": name, "seed": seed}), flush=True)
                cells.append(complete)
                continue
            print(json.dumps({"event": "start", "model": name, "seed": seed, "utc": utc_now()}), flush=True)
            constructor_started = time.perf_counter()
            cv = None
            cv_seconds = 0.0
            backend_receipt = None
            actual_device = "cpu"
            if name in FOUNDATION:
                classifier, backend_receipt = create_foundation_classifier(name, model_cache, seed=seed, device=device, n_estimators=4)
                actual_device = backend_receipt["device"]["selected_device"]
            else:
                params: dict[str, Any] = {}
                if name in DEFAULT_GRIDS:
                    cv_started = time.perf_counter()
                    cv = tune_tree(name, X_fit, y_fit, seed, protocol["model_grids"][name], protocol["n_splits"])
                    cv_seconds = time.perf_counter() - cv_started
                    params = cv["selected_parameters"]
                classifier = make_tree(name, seed, params, len(classes))
            constructor_seconds = time.perf_counter() - constructor_started - cv_seconds
            imputer = SimpleImputer(strategy="median", keep_empty_features=True)
            if actual_device.startswith("cuda"):
                import torch
                torch.cuda.reset_peak_memory_stats()
            synchronize(actual_device)
            started = time.perf_counter()
            classifier.fit(imputer.fit_transform(X_fit), y_fit)
            synchronize(actual_device)
            fit_seconds = time.perf_counter() - started
            calibration_proba, calibration_seconds = predict_chunks(classifier, imputer, data["X"][calibration_rows], n_classes=len(classes), chunk_rows=1024, device=actual_device)
            test_proba, test_seconds = predict_chunks(classifier, imputer, data["X"][test_rows], n_classes=len(classes), chunk_rows=1024, device=actual_device)
            gpu_memory = None
            if actual_device.startswith("cuda"):
                gpu_memory = {"max_allocated_bytes": int(torch.cuda.max_memory_allocated()),
                              "max_reserved_bytes": int(torch.cuda.max_memory_reserved()),
                              "scope": "final fit plus calibration/test predictions"}
            cell_dir.mkdir(parents=True, exist_ok=True)
            predictions_path = cell_dir / "PREDICTIONS.npz"
            staged_predictions = cell_dir / "PREDICTIONS.tmp.npz"
            np.savez_compressed(staged_predictions, calibration_probabilities=calibration_proba, test_probabilities=test_proba,
                                calibration_y=data["y"][calibration_rows], test_y=data["y"][test_rows],
                                calibration_indices=calibration_rows, test_indices=test_rows,
                                selected_fit_indices=rows, selected_fit_fingerprints=data["group_sha256"][rows],
                                classes=data["classes"], imputer_statistics=imputer.statistics_)
            os.replace(staged_predictions, predictions_path)
            cell = {"schema_version": 1, "model": name, "seed": seed, "completed_utc": utc_now(),
                    "execution_binding": execution_binding, "comparison_binding": comparison_binding,
                    "common_binding": common_binding, "prefit_receipt_sha256": prefit_sha,
                    "selected_fit_fingerprints_sha256": canonical_hash(supports[str(seed)]["fingerprints"]),
                    "samples_per_class": 32, "selected_fit_rows": len(rows), "inner_cv": cv,
                    "actual_device": actual_device, "backend_receipt": backend_receipt,
                    "gpu_memory": gpu_memory, "cpu_peak_memory_measured": False,
                    "versions": execution["versions"], "prediction_chunk_rows": 1024,
                    "timing_seconds": {"constructor_and_checkpoint": constructor_seconds, "inner_cv": cv_seconds,
                                       "final_fit_including_imputer": fit_seconds, "calibration_predict_including_transform": calibration_seconds,
                                       "test_predict_including_transform": test_seconds},
                    "test_rows_per_second": len(test_rows) / test_seconds,
                    "metrics": {"calibration": probability_metrics(data["y"][calibration_rows], calibration_proba, classes),
                                "test": probability_metrics(data["y"][test_rows], test_proba, classes)},
                    "prediction_sha256": sha256_file(predictions_path)}
            if backend_receipt is not None:
                backend_receipt.update(fitted=True, runtime_compatibility_tested=True)
            write_json(cell_dir / "CELL.json", cell)
            write_json(cell_dir / "COMPLETE.json", {"execution_binding": execution_binding, "comparison_binding": comparison_binding,
                                                    "file_sha256": {"CELL.json": sha256_file(cell_dir / "CELL.json"), "PREDICTIONS.npz": cell["prediction_sha256"]}})
            cells.append(cell)
            write_json(output / "RESULTS.json", build_summary(cells))
            print(json.dumps({"event": "complete", "model": name, "seed": seed, "test_macro_f1": cell["metrics"]["test"]["macro_f1"]}), flush=True)
            del classifier, imputer
    result = build_summary(cells)
    write_json(output / "RESULTS.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", required=True, help="Comma-separated registered model IDs")
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    args = parser.parse_args()
    run(args.data, args.protocol, args.output, args.models.split(","), device=args.device, model_cache=args.model_cache)


if __name__ == "__main__":
    main()
