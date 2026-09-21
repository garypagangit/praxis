"""Training-only wider tree search at equal-label and abundant-benign budgets."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
from typing import Any

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from ..tabular_batch import run_e1

SEEDS = list(range(20260921, 20260931))
MODELS = ["xgboost", "lightgbm", "random_forest"]
CONDITIONS = ["equal_32_per_class", "abundant_benign_1024"]
SUPPORT_TAG = "STRONG_BASELINES_BENIGN_20260921"
E1_PROTOCOL_SHA256 = "9d4c69f9ab8af48dae44aae6c237a25cedc56a1f50eff819513fa2e9beb7c687"
PRIMARY_GATE = {"required_paired_seeds": 10, "mean_macro_f1_delta_min": .02,
                "high_risk_classes": ["InitialCompromise", "DataExfiltration"],
                "mean_recall_delta_min": -.05, "reference": "Reuse the original E1 descriptive development gate",
                "required_tree_families": ["xgboost", "lightgbm"],
                "require_full_original_test_query": True,
                "interpretation": "Follow-up descriptive result only; not an untouched holdout or independent confirmation"}
GRIDS = {
    "xgboost": [
        {"n_estimators": 100, "max_depth": 2, "learning_rate": .05},
        {"n_estimators": 100, "max_depth": 3, "learning_rate": .1},
        {"n_estimators": 200, "max_depth": 3, "learning_rate": .05},
        {"n_estimators": 300, "max_depth": 2, "learning_rate": .05, "min_child_weight": 1, "reg_lambda": 1},
        {"n_estimators": 600, "max_depth": 2, "learning_rate": .03, "min_child_weight": 1, "reg_lambda": 5},
        {"n_estimators": 300, "max_depth": 3, "learning_rate": .1, "min_child_weight": 1, "reg_lambda": 5},
        {"n_estimators": 600, "max_depth": 3, "learning_rate": .03, "min_child_weight": 3, "reg_lambda": 1},
        {"n_estimators": 300, "max_depth": 5, "learning_rate": .05, "min_child_weight": 1, "reg_lambda": 1},
        {"n_estimators": 600, "max_depth": 5, "learning_rate": .03, "min_child_weight": 3, "reg_lambda": 5},
        {"n_estimators": 300, "max_depth": 7, "learning_rate": .05, "min_child_weight": 1, "reg_lambda": 5},
        {"n_estimators": 400, "max_depth": 3, "learning_rate": .05, "min_child_weight": 1, "reg_alpha": .1, "subsample": .8, "colsample_bytree": .8},
        {"n_estimators": 400, "max_depth": 5, "learning_rate": .05, "min_child_weight": 3, "reg_alpha": 1, "subsample": .8, "colsample_bytree": .8},
    ],
    "lightgbm": [
        {"n_estimators": 100, "num_leaves": 7, "learning_rate": .05, "min_child_samples": 5},
        {"n_estimators": 100, "num_leaves": 15, "learning_rate": .1, "min_child_samples": 5},
        {"n_estimators": 200, "num_leaves": 15, "learning_rate": .05, "min_child_samples": 5},
        {"n_estimators": 300, "num_leaves": 3, "learning_rate": .05, "min_child_samples": 5},
        {"n_estimators": 600, "num_leaves": 7, "learning_rate": .03, "min_child_samples": 5, "reg_lambda": 1},
        {"n_estimators": 300, "num_leaves": 15, "learning_rate": .05, "min_child_samples": 10, "reg_lambda": 1},
        {"n_estimators": 600, "num_leaves": 31, "learning_rate": .03, "min_child_samples": 5, "reg_lambda": 5},
        {"n_estimators": 300, "num_leaves": 7, "learning_rate": .1, "min_child_samples": 20, "reg_lambda": 5},
        {"n_estimators": 400, "num_leaves": 15, "learning_rate": .05, "min_child_samples": 5, "colsample_bytree": .8, "reg_alpha": .1},
        {"n_estimators": 300, "num_leaves": 7, "learning_rate": .05, "min_child_samples": 5, "class_weight": "balanced"},
        {"n_estimators": 400, "num_leaves": 15, "learning_rate": .05, "min_child_samples": 10, "class_weight": "balanced", "reg_lambda": 1},
        {"n_estimators": 400, "num_leaves": 31, "learning_rate": .05, "min_child_samples": 5, "class_weight": "balanced", "reg_lambda": 5},
    ],
    "random_forest": [
        {"n_estimators": 200, "max_depth": None, "min_samples_leaf": 1, "max_features": "sqrt", "class_weight": None},
        {"n_estimators": 400, "max_depth": None, "min_samples_leaf": 1, "max_features": .7, "class_weight": None},
        {"n_estimators": 400, "max_depth": 8, "min_samples_leaf": 2, "max_features": "sqrt", "class_weight": None},
        {"n_estimators": 600, "max_depth": 16, "min_samples_leaf": 1, "max_features": .7, "class_weight": "balanced"},
        {"n_estimators": 400, "max_depth": None, "min_samples_leaf": 2, "max_features": "sqrt", "class_weight": "balanced"},
        {"n_estimators": 600, "max_depth": 8, "min_samples_leaf": 4, "max_features": .7, "class_weight": "balanced_subsample"},
    ],
}


def validate_protocol(protocol: dict[str, Any], e1_protocol_path: Path) -> dict[str, Any]:
    expected = {"schema_version": 1, "experiment": "STRONG_BASELINES_FOLLOWUP",
                "status": "FROZEN_BEFORE_FOLLOWUP_MODEL_FITS", "models": MODELS,
                "conditions": CONDITIONS, "samples_per_attack_class": 32,
                "equal_budget_normal_rows": 32, "abundant_normal_rows": 1024,
                "n_splits": 3, "prediction_chunk_rows": 1024, "cpu_threads": 4,
                "support_hash_tag": SUPPORT_TAG, "model_grids": GRIDS,
                "same_budget_primary_gate": PRIMARY_GATE,
                "family_selection": "Maximum inner-CV macro-F1; ties prefer xgboost then lightgbm then random_forest",
                "primary_comparator_families": ["xgboost", "lightgbm"]}
    if any(protocol.get(key) != value for key, value in expected.items()):
        raise ValueError("Follow-up protocol differs from the frozen design or is not frozen.")
    synthetic = protocol.get("study_kind") == "synthetic_smoke"
    if protocol.get("seeds") != ([20260921] if synthetic else SEEDS):
        raise ValueError("Unexpected follow-up seeds.")
    digest = run_e1.sha256_file(e1_protocol_path)
    if protocol.get("e1_protocol_sha256") != digest or (not synthetic and digest != E1_PROTOCOL_SHA256):
        raise ValueError("Original E1 protocol binding is invalid.")
    original = json.loads(e1_protocol_path.read_text(encoding="utf-8"))
    run_e1.validate_protocol(original)
    if any(protocol.get(key) != original[key] for key in ("data_npz_sha256", "manifest_sha256")):
        raise ValueError("Follow-up data differ from the original E1 data.")
    return original


def select_support(data: dict[str, np.ndarray], seed: int, condition: str) -> np.ndarray:
    if condition not in CONDITIONS:
        raise ValueError("Unknown training condition.")
    original = run_e1.select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=seed, budget=32)
    if condition == CONDITIONS[0]:
        return original
    normal = data["classes"].tolist().index("NormalTraffic")
    selected = set(original.tolist())
    pool = np.flatnonzero((data["split"] == 0) & (data["y"] == normal))
    if len(pool) < 1024:
        raise ValueError("Insufficient benign fit rows for the abundant-benign condition.")
    available = [int(index) for index in pool if int(index) not in selected]
    def key(index: int) -> bytes:
        return hashlib.sha256(f"{SUPPORT_TAG}|{seed}|{data['group_sha256'][index]}".encode("ascii")).digest()
    # Preserve the complete original support and add a fixed 992 benign rows.
    return np.r_[original, np.asarray(sorted(available, key=key)[:992], dtype=np.int64)]


def inner_folds(y: np.ndarray, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    if np.min(np.bincount(y)) < 3:
        raise ValueError("Each training class needs at least three examples.")
    return list(StratifiedKFold(3, shuffle=True, random_state=seed).split(np.zeros((len(y), 1)), y))


def make_tree(name: str, seed: int, parameters: dict[str, Any], n_classes: int, threads: int) -> Any:
    common = {"random_state": seed, "n_jobs": threads}
    if name == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(**parameters, **common, tree_method="hist", device="cpu",
                             objective="multi:softprob", num_class=n_classes, eval_metric="mlogloss")
    if name == "lightgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(**parameters, **common, verbosity=-1, deterministic=True, force_col_wise=True)
    if name == "random_forest":
        return RandomForestClassifier(**parameters, **common)
    raise ValueError("Unknown tree family.")


def tune_tree(name: str, X: np.ndarray, y: np.ndarray, seed: int,
              grid: list[dict[str, Any]], threads: int) -> dict[str, Any]:
    folds = inner_folds(y, seed)
    candidates = []
    for parameters in grid:
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("classifier", make_tree(name, seed, parameters, len(np.unique(y)), threads)),
        ])
        scores = []
        for train, validation in folds:
            estimator = clone(pipeline).fit(X[train], y[train])
            scores.append(float(f1_score(y[validation], estimator.predict(X[validation]), average="macro", zero_division=0)))
        candidates.append({"parameters": parameters, "fold_macro_f1": scores, "mean_macro_f1": float(np.mean(scores))})
    winner = max(range(len(candidates)), key=lambda index: candidates[index]["mean_macro_f1"])
    return {"selected_candidate_index": winner, "selected_parameters": grid[winner],
            "selected_mean_macro_f1": candidates[winner]["mean_macro_f1"], "candidates": candidates,
            "selection_data": "Selected fit support only", "tie_policy": "First candidate in protocol order"}


def select_family(cells: list[dict[str, Any]], families: list[str]) -> dict[str, Any]:
    by_name = {cell["model"]: cell for cell in cells}
    if len(by_name) != len(cells) or not set(families) <= by_name.keys():
        raise ValueError("Missing or duplicate candidate family.")
    candidates = [by_name[name] for name in families]
    if len({cell["comparison_binding"] for cell in candidates}) != 1:
        raise ValueError("Cannot select across incompatible training supports.")
    return max(candidates, key=lambda cell: cell["inner_cv"]["selected_mean_macro_f1"])


def summary(cells: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for cell in cells:
        grouped.setdefault((cell["condition"], cell["seed"]), []).append(cell)
    selections = []
    for (condition, seed), group in sorted(grouped.items()):
        if {cell["model"] for cell in group} == set(MODELS):
            gbdt = select_family(group, ["xgboost", "lightgbm"])
            tree = select_family(group, MODELS)
            selections.append({"condition": condition, "seed": seed,
                               "gbdt_selected_by_inner_cv": gbdt["model"],
                               "all_tree_selected_by_inner_cv": tree["model"],
                               "selected_gbdt_test_metrics": gbdt["metrics"]["test"],
                               "selected_all_tree_test_metrics": tree["metrics"]["test"]})
    required = len(protocol["seeds"]) * len(CONDITIONS) * len(MODELS)
    return {"schema_version": 1, "experiment": protocol["experiment"],
            "status": "COMPLETE" if len(cells) == required else "INCOMPLETE",
            "completed_cells": len(cells), "required_cells": required, "cells": cells,
            "family_selections": selections, "foundation_comparison_status": "NOT_EVALUATED_BY_THIS_RUNNER",
            "interpretation": "Separately frozen follow-up after earlier results were known. Shared development test and correlated fitting seeds; no independent replication, confidence interval, temporal, actor, or early-warning claim."}


def validate_completed(cell_dir: Path, execution_binding: str, comparison_binding: str) -> dict[str, Any] | None:
    cell = run_e1.validate_completed(cell_dir, execution_binding, comparison_binding)
    if cell is not None and cell.get("started_receipt_sha256") != run_e1.sha256_file(cell_dir / "STARTED.json"):
        raise ValueError("Cell start receipt has changed.")
    return cell


def run(data_path: Path, protocol_path: Path, output: Path, *, e1_protocol_path: Path,
        models: list[str], conditions: list[str], prepare_only: bool = False) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    validate_protocol(protocol, e1_protocol_path)
    if not models or len(set(models)) != len(models) or not set(models) <= set(MODELS):
        raise ValueError("Unknown, duplicated, or empty model subset.")
    if not conditions or len(set(conditions)) != len(conditions) or not set(conditions) <= set(CONDITIONS):
        raise ValueError("Unknown, duplicated, or empty condition subset.")
    data_path = data_path / "DATA.npz" if data_path.is_dir() else data_path
    data, manifest = run_e1.load_data(data_path, protocol)
    query = np.flatnonzero(data["split"] == 2)
    if protocol.get("study_kind") != "synthetic_smoke" and len(query) != 30787:
        raise ValueError("Expected all 30,787 original development-test rows.")
    sources = {"followup/run_strong_baselines.py": Path(__file__),
               "followup/requirements_strong_baselines.txt": Path(__file__).with_name("requirements_strong_baselines.txt"),
               "tabular_batch/run_e1.py": Path(run_e1.__file__),
               "tabular_batch/model_backend.py": Path(run_e1.__file__).with_name("model_backend.py")}
    common = {"data_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
              "protocol_sha256": run_e1.sha256_file(protocol_path), "e1_protocol_sha256": run_e1.sha256_file(e1_protocol_path),
              "code_sha256": {name: run_e1.sha256_file(path) for name, path in sources.items()}}
    supports = {}
    for condition in conditions:
        supports[condition] = {}
        for seed in protocol["seeds"]:
            rows = select_support(data, seed, condition)
            folds = inner_folds(data["y"][rows], seed)
            supports[condition][str(seed)] = {
                "indices": rows.tolist(), "fingerprints": data["group_sha256"][rows].tolist(),
                "class_counts": {name: int(np.sum(data["y"][rows] == label)) for label, name in enumerate(data["classes"])},
                "inner_folds_support_positions": [{"train": train.tolist(), "validation": validation.tolist()} for train, validation in folds],
            }
    versions = run_e1.package_versions()
    versions["threadpoolctl"] = importlib.metadata.version("threadpoolctl")
    execution = {**common, "models": models, "conditions": conditions, "seeds": protocol["seeds"],
                 "supports": supports, "cpu_threads": protocol["cpu_threads"], "actual_device": "cpu", "versions": versions,
                 "test_query": {"indices": query.tolist(), "fingerprints": data["group_sha256"][query].tolist()},
                 "classes": data["classes"].tolist()}
    binding = run_e1.canonical_hash(execution)
    prefit_path = output / "PREFIT_RECEIPT.json"
    if prefit_path.exists():
        previous = json.loads(prefit_path.read_text(encoding="utf-8"))
        if previous.get("execution_binding") != binding or previous.get("execution") != execution:
            raise ValueError("Output belongs to a different immutable execution.")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("Nonempty output without a prefit receipt cannot be reused.")
        run_e1.write_json(prefit_path, {"created_utc": run_e1.utc_now(), "execution_binding": binding,
                                     "execution": execution, "scientific_fits_started": False,
                                     "scope": manifest.get("evaluation_scope")})
    completed_run = output / "COMPLETE.json"
    if completed_run.exists():
        marker = json.loads(completed_run.read_text(encoding="utf-8"))
        if marker.get("execution_binding") != binding or set(marker.get("artifact_sha256", {})) != {"PREFIT_RECEIPT.json", "RESULTS.json"}:
            raise ValueError("Completed run binding is invalid.")
        for name, digest in marker["artifact_sha256"].items():
            if run_e1.sha256_file(output / name) != digest:
                raise ValueError("Completed run artifact hash mismatch.")
        expected_cells = {f"{condition}/{name}/{seed}" for condition in conditions for name in models for seed in protocol["seeds"]}
        if set(marker.get("cell_complete_sha256", {})) != expected_cells:
            raise ValueError("Completed run cell roster is incomplete or changed.")
        for name, digest in marker["cell_complete_sha256"].items():
            if run_e1.sha256_file(output / "cells" / name / "COMPLETE.json") != digest:
                raise ValueError("Completed cell receipt hash mismatch.")
    if prepare_only:
        return {"status": "PREPARED_ONLY", "execution_binding": binding, "scientific_fits_started": False}
    prefit_sha = run_e1.sha256_file(prefit_path)
    cells = []
    with threadpool_limits(limits=protocol["cpu_threads"]):
        for condition in conditions:
            for seed in protocol["seeds"]:
                support = supports[condition][str(seed)]
                rows = np.asarray(support["indices"], dtype=np.int64)
                comparison = run_e1.canonical_hash({**common, "condition": condition, "seed": seed, "support": support})
                X_fit, y_fit = data["X"][rows], data["y"][rows]
                for name in models:
                    cell_dir = output / "cells" / condition / name / str(seed)
                    completed = validate_completed(cell_dir, binding, comparison)
                    if completed is not None:
                        cells.append(completed)
                        print(json.dumps({"event": "resume_completed", "condition": condition, "model": name, "seed": seed}), flush=True)
                        continue
                    run_e1.write_json(cell_dir / "STARTED.json", {"started_utc": run_e1.utc_now(), "execution_binding": binding,
                                                               "comparison_binding": comparison, "prefit_receipt_sha256": prefit_sha})
                    print(json.dumps({"event": "start", "condition": condition, "model": name, "seed": seed}), flush=True)
                    started = time.perf_counter()
                    cv = tune_tree(name, X_fit, y_fit, seed, protocol["model_grids"][name], protocol["cpu_threads"])
                    cv_seconds = time.perf_counter() - started
                    classifier = make_tree(name, seed, cv["selected_parameters"], len(data["classes"]), protocol["cpu_threads"])
                    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
                    started = time.perf_counter()
                    classifier.fit(imputer.fit_transform(X_fit), y_fit)
                    fit_seconds = time.perf_counter() - started
                    probabilities, predict_seconds = run_e1.predict_chunks(classifier, imputer, data["X"][query],
                                                                          n_classes=len(data["classes"]), chunk_rows=1024, device="cpu")
                    staged = cell_dir / "PREDICTIONS.tmp.npz"
                    np.savez_compressed(staged, test_probabilities=probabilities, test_y=data["y"][query], test_indices=query,
                                        test_fingerprints=data["group_sha256"][query], classes=data["classes"],
                                        selected_fit_indices=rows, selected_fit_fingerprints=data["group_sha256"][rows],
                                        imputer_statistics=imputer.statistics_)
                    predictions_path = cell_dir / "PREDICTIONS.npz"
                    os.replace(staged, predictions_path)
                    cell = {"schema_version": 1, "experiment": protocol["experiment"], "condition": condition,
                            "model": name, "seed": seed, "execution_binding": binding, "comparison_binding": comparison,
                            "common_binding": common, "prefit_receipt_sha256": prefit_sha,
                            "started_receipt_sha256": run_e1.sha256_file(cell_dir / "STARTED.json"),
                            "selected_fit_fingerprints_sha256": run_e1.canonical_hash(support["fingerprints"]),
                            "selected_fit_rows": len(rows), "class_label_costs": support["class_counts"],
                            "additional_tuning_labels": 0, "inner_cv": cv, "actual_device": "cpu", "versions": versions,
                            "timing_seconds": {"inner_cv": cv_seconds, "final_fit_including_imputer": fit_seconds,
                                               "test_predict_including_transform": predict_seconds},
                            "metrics": {"test": run_e1.probability_metrics(data["y"][query], probabilities, data["classes"].tolist())},
                            "prediction_sha256": run_e1.sha256_file(predictions_path), "completed_utc": run_e1.utc_now()}
                    run_e1.write_json(cell_dir / "CELL.json", cell)
                    run_e1.write_json(cell_dir / "COMPLETE.json", {"execution_binding": binding, "comparison_binding": comparison,
                                                                 "file_sha256": {"CELL.json": run_e1.sha256_file(cell_dir / "CELL.json"),
                                                                                 "PREDICTIONS.npz": cell["prediction_sha256"]}})
                    cells.append(cell)
                    run_e1.write_json(output / "RESULTS.json", summary(cells, protocol))
                    print(json.dumps({"event": "complete", "condition": condition, "model": name, "seed": seed,
                                      "test_macro_f1": cell["metrics"]["test"]["macro_f1"]}), flush=True)
    result = summary(cells, protocol)
    result.update(execution_binding=binding, protocol_sha256=common["protocol_sha256"], prefit_receipt_sha256=prefit_sha)
    run_e1.write_json(output / "RESULTS.json", result)
    run_e1.write_json(output / "COMPLETE.json", {"execution_binding": binding,
                                               "artifact_sha256": {"PREFIT_RECEIPT.json": prefit_sha, "RESULTS.json": run_e1.sha256_file(output / "RESULTS.json")},
                                               "cell_complete_sha256": {f"{cell['condition']}/{cell['model']}/{cell['seed']}": run_e1.sha256_file(output / "cells" / cell["condition"] / cell["model"] / str(cell["seed"]) / "COMPLETE.json") for cell in cells},
                                               "all_registered_cells_complete": result["status"] == "COMPLETE"})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--e1-protocol", type=Path, default=Path(run_e1.__file__).with_name("protocol.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run(args.data, args.protocol, args.output, e1_protocol_path=args.e1_protocol,
        models=args.models.split(","), conditions=args.conditions.split(","), prepare_only=args.prepare_only)


if __name__ == "__main__":
    main()
