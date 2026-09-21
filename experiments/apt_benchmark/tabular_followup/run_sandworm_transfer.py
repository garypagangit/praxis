"""Source-only fitting and descriptive binary transfer to a frozen Sandworm query."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import time

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

from ..tabular_batch import analyze_e1 as audit
from ..tabular_batch import run_e1
from ..tabular_batch.model_backend import CHECKPOINTS, create_foundation_classifier, ensure_checkpoint

MODELS = ["selected_gbdt", "tabicl_v2"]
BASELINES = ["random_forest", "xgboost", "lightgbm"]
SEEDS = list(range(20260921, 20260931))
E1_PROTOCOL_SHA256 = "9d4c69f9ab8af48dae44aae6c237a25cedc56a1f50eff819513fa2e9beb7c687"


def validate_protocol(protocol, e1_path):
    expected = {"schema_version": 1, "experiment": "SANDWORM_BINARY_TRANSFER",
                "status": "FROZEN_BEFORE_TARGET_MODEL_FITS", "samples_per_class": 32,
                "foundation_model": "tabicl_v2", "tree_models": ["xgboost", "lightgbm"],
                "foundation_n_estimators": 4, "prediction_chunk_rows": 1024,
                "cpu_threads": 4, "tabicl_n_jobs": 1, "device": "cpu",
                "no_target_fit": True, "no_target_calibration": True,
                "no_target_threshold_tuning": True,
                "primary_rule": "source_argmax_is_not_NormalTraffic",
                "ranking_score": "1_minus_source_NormalTraffic_probability"}
    audit.require(all(protocol.get(key) == value for key, value in expected.items()), "Transfer protocol differs from the frozen design or is not frozen")
    synthetic = protocol.get("study_kind") == "synthetic_smoke"
    audit.require(protocol.get("seeds") == ([20260921] if synthetic else SEEDS), "Unexpected transfer seeds")
    digest = run_e1.sha256_file(e1_path)
    audit.require(protocol.get("e1_protocol_sha256") == digest and (synthetic or digest == E1_PROTOCOL_SHA256), "Original E1 protocol changed")
    original = json.loads(e1_path.read_text(encoding="utf-8"))
    run_e1.validate_protocol(original)
    audit.require(original["data_npz_sha256"] == protocol["source_data_npz_sha256"] and original["manifest_sha256"] == protocol["source_manifest_sha256"], "Source data binding differs from original E1")
    if not synthetic:
        counts = {"expected_unique_rows": 2091, "expected_raw_rows": 2133,
                  "expected_unique_attack_rows": 37, "expected_unique_normal_rows": 2054}
        audit.require(all(protocol.get(key) == value for key, value in counts.items()), "Target qualification counts changed")
    return original


def load_target(path, protocol, source):
    path = path / "DATA.npz" if path.is_dir() else path
    manifest_path = path.with_name("MANIFEST.json")
    audit.require(run_e1.sha256_file(path) == protocol["target_data_npz_sha256"] and run_e1.sha256_file(manifest_path) == protocol["target_manifest_sha256"], "Target input or manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit.require(manifest.get("target_data_npz_sha256") == protocol["target_data_npz_sha256"], "Target manifest does not bind these data bytes")
    if protocol.get("study_kind") != "synthetic_smoke":
        audit.require(manifest.get("adapter_sha256") == run_e1.sha256_file(Path(__file__).with_name("prepare_sandworm.py")), "Target preparation source changed")
        audit.require(manifest.get("source_data_npz_sha256") == protocol["source_data_npz_sha256"] and manifest.get("source_manifest_sha256") == protocol["source_manifest_sha256"], "Target preparation used another source feature contract")
    with np.load(path, allow_pickle=False) as saved:
        target = {name: saved[name] for name in saved.files}
    required = {"X", "y_binary", "procedure_labels", "group_sha256", "feature_names", "raw_to_unique"}
    audit.require(required <= set(target), "Target arrays missing")
    X, y, procedures, fingerprints, mapping = (target[name] for name in ["X", "y_binary", "procedure_labels", "group_sha256", "raw_to_unique"])
    audit.require(X.ndim == 2 and X.shape[1] == source["X"].shape[1] and np.isfinite(X).all(), "Target feature shape or values invalid")
    audit.require(np.array_equal(target["feature_names"], source["feature_names"]), "Target feature names or order differ from source")
    audit.require(all(array.ndim == 1 and len(array) == len(X) for array in [y, procedures, fingerprints]), "Target row metadata misaligned")
    audit.require(np.issubdtype(y.dtype, np.integer) and set(np.unique(y)) == {0, 1}, "Target must contain both integer binary labels")
    audit.require(len(set(fingerprints.tolist())) == len(X) and np.array_equal(fingerprints, np.sort(fingerprints)), "Target query must use sorted unique feature fingerprints")
    audit.require(not set(fingerprints.tolist()).intersection(source["group_sha256"].tolist()), "Exact source-target feature overlap")
    audit.require(mapping.ndim == 1 and np.issubdtype(mapping.dtype, np.integer) and np.all((mapping >= 0) & (mapping < len(X))), "Invalid raw-to-unique mapping")
    multiplicity = np.bincount(mapping, minlength=len(X))
    audit.require(np.all(multiplicity > 0), "Unique target row absent from raw mapping")
    audit.require(len(X) == protocol["expected_unique_rows"] and len(mapping) == protocol["expected_raw_rows"], "Target row counts changed")
    audit.require(int(y.sum()) == protocol["expected_unique_attack_rows"] and int((y == 0).sum()) == protocol["expected_unique_normal_rows"], "Target binary counts changed")
    if protocol.get("study_kind") != "synthetic_smoke":
        audit.require(int(y[mapping].sum()) == 37, "Qualified raw attack count changed")
    for procedure in np.unique(procedures):
        audit.require(len(np.unique(y[procedures == procedure])) == 1, "Procedure has conflicting binary labels")
    audit.require(np.all(procedures[y == 0] == "Normal") and np.all(procedures[y == 1] != "Normal"), "Target procedure and binary labels disagree")
    target["raw_multiplicity"] = multiplicity
    return target, manifest


def source_selection(root, source, original, original_path):
    """Audit original artifacts and CV arithmetic without selecting on query metrics."""
    prefit_path = root / "PREFIT_RECEIPT.json"
    prefit = json.loads(prefit_path.read_text(encoding="utf-8"))
    execution = prefit["execution"]
    audit.require(run_e1.canonical_hash(execution) == prefit["execution_binding"], "Original prefit binding invalid")
    original_source = Path(run_e1.__file__).parent
    expected = {"data_sha256": original["data_npz_sha256"], "manifest_sha256": original["manifest_sha256"],
                "protocol_sha256": run_e1.sha256_file(original_path),
                "code_sha256": {name: run_e1.sha256_file(original_source / name) for name in ["run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt"]}}
    audit.require(all(execution.get(key) == value for key, value in expected.items()), "Original code/input/protocol binding mismatch")
    audit.require(set(execution["models"]) == set(BASELINES) and len(execution["models"]) == 3, "Expected the original three baseline families")
    audit.require(set(execution["supports"]) == {str(seed) for seed in original["seeds"]}, "Original support roster mismatch")
    selected, evidence = {}, {"prefit_receipt_sha256": run_e1.sha256_file(prefit_path), "execution_binding": prefit["execution_binding"], "versions": execution["versions"], "cells": {}}
    for seed in original["seeds"]:
        rows = run_e1.select_fit_indices(source["y"], source["split"], source["group_sha256"], seed=seed, budget=32)
        support = {"indices": rows.tolist(), "fingerprints": source["group_sha256"][rows].tolist()}
        audit.require(execution["supports"][str(seed)] == support, "Original support changed")
        comparison = run_e1.canonical_hash({**expected, "seed": seed, "support": support})
        candidates = {}
        for name in BASELINES:
            folder = root / "cells" / name / str(seed)
            cell = run_e1.validate_completed(folder, prefit["execution_binding"], comparison)
            audit.require(cell is not None, "Original baseline cell incomplete")
            audit.require(cell["model"] == name and cell["seed"] == seed and cell["common_binding"] == expected, "Original baseline identity mismatch")
            audit.require(cell["prefit_receipt_sha256"] == evidence["prefit_receipt_sha256"] and cell["selected_fit_fingerprints_sha256"] == run_e1.canonical_hash(support["fingerprints"]), "Original support/prefit receipt mismatch")
            with np.load(folder / "PREDICTIONS.npz", allow_pickle=False) as saved:
                audit.require(np.array_equal(saved["selected_fit_indices"], rows) and np.array_equal(saved["selected_fit_fingerprints"], source["group_sha256"][rows]) and np.array_equal(saved["classes"], source["classes"]), "Original saved support/class order mismatch")
            score = audit.validate_cv(cell, original)
            evidence["cells"][f"{name}/{seed}"] = {file: run_e1.sha256_file(folder / file) for file in ["CELL.json", "PREDICTIONS.npz", "COMPLETE.json"]}
            if name in ("xgboost", "lightgbm"):
                candidates[name] = {"model": name, "parameters": cell["inner_cv"]["selected_parameters"], "inner_cv_macro_f1": score}
        winner = max([candidates["xgboost"], candidates["lightgbm"]], key=lambda item: item["inner_cv_macro_f1"])
        selected[str(seed)] = {"selected_tree": winner["model"], "selected_parameters": winner["parameters"],
                               "cv_scores": {name: value["inner_cv_macro_f1"] for name, value in candidates.items()}, "support": support}
    return selected, evidence


def binary_metrics(probabilities, source_classes, target, weights):
    probabilities, _ = audit.probabilities(probabilities, np.zeros(len(target["y_binary"]), dtype=np.int64), len(source_classes))
    y = target["y_binary"]
    weights = np.asarray(weights)
    audit.require(weights.shape == y.shape and np.issubdtype(weights.dtype, np.integer) and np.all(weights > 0), "Evaluation multiplicities must be positive row-aligned integers")
    normal = source_classes.index("NormalTraffic")
    predicted = (probabilities.argmax(axis=1) != normal).astype(np.int64)
    score = 1 - probabilities[:, normal]
    matrix = np.zeros((2, 2), dtype=np.int64)
    np.add.at(matrix, (y, predicted), weights)
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    attack_f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    normal_f1 = 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 0.0
    procedure = {}
    for name in sorted(np.unique(target["procedure_labels"][y == 1]).tolist()):
        mask = (target["procedure_labels"] == name) & (y == 1)
        count = int(weights[mask].sum())
        detected = int(weights[mask & (predicted == 1)].sum())
        procedure[name] = {"attack_rows": count, "detected": detected, "missed": count - detected,
                           "recall": detected / count, "unique_query_rows": int(mask.sum())}
    return {"unique_query_rows": len(y), "represented_rows": int(weights.sum()), "confusion_matrix_normal_attack": matrix.tolist(),
            "normal_rows": tn + fp, "attack_rows": tp + fn, "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
            "attack_precision": tp / (tp + fp) if tp + fp else 0.0, "attack_recall": tp / (tp + fn),
            "normal_false_positive_rate": fp / (tn + fp), "attack_f1": attack_f1, "binary_macro_f1": (attack_f1 + normal_f1) / 2,
            "accuracy": (tn + tp) / int(weights.sum()), "roc_auc": float(roc_auc_score(y, score, sample_weight=weights)),
            "average_precision": float(average_precision_score(y, score, sample_weight=weights)), "per_procedure_attack_recall": procedure,
            "decision_rule": "Source six-class argmax is not NormalTraffic", "ranking_score": "1 minus source NormalTraffic probability"}


def summarize(cells, protocol):
    grouped = {}
    for cell in cells:
        audit.require(cell["model"] not in grouped.setdefault(cell["seed"], {}), "Duplicate transfer cell")
        grouped[cell["seed"]][cell["model"]] = cell
    pairs = []
    for seed in protocol["seeds"]:
        models = grouped.get(seed, {})
        if set(MODELS) <= set(models):
            a, b = models["tabicl_v2"], models["selected_gbdt"]
            audit.require(a["comparison_binding"] == b["comparison_binding"], "Transfer comparison bindings differ")
            pairs.append({"seed": seed, "selected_original_tree": b["actual_model"],
                          "binary_macro_f1_delta": a["metrics"]["deduplicated_primary"]["binary_macro_f1"] - b["metrics"]["deduplicated_primary"]["binary_macro_f1"],
                          "attack_f1_delta": a["metrics"]["deduplicated_primary"]["attack_f1"] - b["metrics"]["deduplicated_primary"]["attack_f1"],
                          "attack_recall_delta": a["metrics"]["deduplicated_primary"]["attack_recall"] - b["metrics"]["deduplicated_primary"]["attack_recall"],
                          "normal_fpr_delta": a["metrics"]["deduplicated_primary"]["normal_false_positive_rate"] - b["metrics"]["deduplicated_primary"]["normal_false_positive_rate"]})
            pairs[-1]["raw_flow_sensitivity_deltas"] = {name: a["metrics"]["raw_flow_sensitivity"][name] - b["metrics"]["raw_flow_sensitivity"][name]
                                                         for name in ["binary_macro_f1", "attack_f1", "attack_recall", "normal_false_positive_rate"]}
    model_summaries = {}
    for model in MODELS:
        selected = [cell for cell in cells if cell["model"] == model]
        if not selected:
            continue
        views = {}
        for view in ["deduplicated_primary", "raw_flow_sensitivity"]:
            metrics = [cell["metrics"][view] for cell in selected]
            values = {name: audit.summarize([value[name] for value in metrics]) for name in
                      ["binary_macro_f1", "attack_f1", "attack_precision", "attack_recall", "normal_false_positive_rate",
                       "roc_auc", "average_precision", "true_positive", "false_positive", "true_negative", "false_negative"]}
            values["same_target_normal_rows"] = metrics[0]["normal_rows"]
            values["same_target_attack_rows"] = metrics[0]["attack_rows"]
            values["per_procedure"] = {name: {"same_target_attack_rows": metrics[0]["per_procedure_attack_recall"][name]["attack_rows"],
                                                  **{metric: audit.summarize([value["per_procedure_attack_recall"][name][metric] for value in metrics])
                                                     for metric in ["recall", "detected", "missed"]}}
                                       for name in metrics[0]["per_procedure_attack_recall"]}
            views[view] = values
        model_summaries[model] = {"seeds": [cell["seed"] for cell in selected], "views": views}
    return {"schema_version": 1, "experiment": protocol["experiment"], "status": "COMPLETE" if len(cells) == 2 * len(protocol["seeds"]) else "INCOMPLETE",
            "completed_cells": len(cells), "required_cells": 2 * len(protocol["seeds"]), "cells": cells, "model_summaries": model_summaries,
            "paired_seeds": len(pairs), "paired_differences": pairs,
            "mean_binary_macro_f1_delta": float(np.mean([pair["binary_macro_f1_delta"] for pair in pairs])) if pairs else None,
            "decision": "DESCRIPTIVE_ONLY_NO_PASS_GATE", "target_training_labels_used": 0, "target_calibration_labels_used": 0,
            "interpretation": "Independent target-campaign binary transfer with no target fitting or threshold tuning. One campaign and 37 attack flows do not establish population, temporal, early-warning, actor, or target six-stage identification claims. Fitting seeds are dependent.",
            "raw_flow_sensitivity_notice": "Raw-flow counts reweight the fixed unique-query predictions; no inference was rerun on duplicated query batches.",
            "source_threshold_diagnostic": "Not computed by this runner; requires separately audited saved original-source calibration predictions."}


def run(source_path, target_path, protocol_path, original_path, baseline_root, output, model_cache,
        *, models=MODELS, prepare_only=False):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    original = validate_protocol(protocol, original_path)
    audit.require(models and len(set(models)) == len(models) and set(models) <= set(MODELS), "Invalid transfer model subset")
    source_path = source_path / "DATA.npz" if source_path.is_dir() else source_path
    source, _ = run_e1.load_data(source_path, original)
    target, manifest = load_target(target_path, protocol, source)
    selections, source_evidence = source_selection(baseline_root, source, original, original_path)
    versions = run_e1.package_versions()
    for name in ["numpy", "scipy", "scikit-learn", "pandas", "xgboost", "lightgbm"]:
        audit.require(versions[name] == source_evidence["versions"][name], "Source and transfer preprocessing/tree package versions differ")
    checkpoint = asdict(CHECKPOINTS["tabicl_v2"])
    if "tabicl_v2" in models:
        verified = ensure_checkpoint("tabicl_v2", model_cache, allow_download=False)
        audit.require(run_e1.sha256_file(verified) == checkpoint["sha256"], "Foundation checkpoint changed")
    sources = {"run_sandworm_transfer.py": Path(__file__), "tabular_batch/run_e1.py": Path(run_e1.__file__),
               "tabular_batch/analyze_e1.py": Path(audit.__file__), "tabular_batch/model_backend.py": Path(run_e1.__file__).with_name("model_backend.py"),
               "tabular_batch/requirementsfoundation.txt": Path(run_e1.__file__).with_name("requirementsfoundation.txt"),
               "tabular_batch/requirements_baselines.txt": Path(run_e1.__file__).with_name("requirements_baselines.txt")}
    common = {key: protocol[key] for key in ["source_data_npz_sha256", "source_manifest_sha256", "target_data_npz_sha256", "target_manifest_sha256", "e1_protocol_sha256"]}
    common.update(protocol_sha256=run_e1.sha256_file(protocol_path), code_sha256={name: run_e1.sha256_file(path) for name, path in sources.items()},
                  foundation_checkpoint=checkpoint)
    execution = {**common, "models": models, "device": "cpu", "cpu_threads": 4,
                 "versions": versions, "source_selections": selections, "source_baseline_evidence": source_evidence,
                 "classes": source["classes"].tolist(), "target_query_fingerprints": target["group_sha256"].tolist(),
                 "target_raw_mapping_sha256": run_e1.canonical_hash(target["raw_to_unique"].tolist()),
                 "target_training_labels_used": 0, "target_calibration_labels_used": 0}
    binding = run_e1.canonical_hash(execution)
    prefit_path = output / "PREFIT_RECEIPT.json"
    if prefit_path.exists():
        previous = json.loads(prefit_path.read_text(encoding="utf-8"))
        audit.require(previous.get("execution_binding") == binding and previous.get("execution") == execution, "Output belongs to another immutable run")
    else:
        audit.require(not output.exists() or not any(output.iterdir()), "Nonempty output without prefit receipt cannot be reused")
        run_e1.write_json(prefit_path, {"created_utc": run_e1.utc_now(), "execution_binding": binding,
                                     "execution": execution, "transfer_fits_started": False, "target_policy": "No target fitting, calibration, or threshold tuning"})
    prefit_sha = run_e1.sha256_file(prefit_path)
    marker_path = output / "COMPLETE.json"
    if marker_path.exists():
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        audit.require(marker.get("execution_binding") == binding and set(marker.get("artifact_sha256", {})) == {"PREFIT_RECEIPT.json", "RESULTS.json"}, "Completed run binding invalid")
        for name, digest in marker["artifact_sha256"].items():
            audit.require(run_e1.sha256_file(output / name) == digest, "Completed run artifact changed")
        expected = {f"{model}/{seed}" for model in models for seed in protocol["seeds"]}
        audit.require(set(marker.get("cell_complete_sha256", {})) == expected, "Completed run cell roster changed")
        for name, digest in marker["cell_complete_sha256"].items():
            audit.require(run_e1.sha256_file(output / "cells" / name / "COMPLETE.json") == digest, "Completed cell receipt changed")
    if prepare_only:
        return {"status": "PREPARED_ONLY", "execution_binding": binding, "transfer_fits_started": False}
    if "tabicl_v2" in models:
        import torch
        torch.set_num_threads(protocol["cpu_threads"])
    cells = []
    with threadpool_limits(limits=protocol["cpu_threads"]):
        for seed in protocol["seeds"]:
            selection = selections[str(seed)]
            rows = np.asarray(selection["support"]["indices"], dtype=np.int64)
            comparison = run_e1.canonical_hash({**common, "seed": seed, "source_selection": selection})
            for model in models:
                folder = output / "cells" / model / str(seed)
                cell = run_e1.validate_completed(folder, binding, comparison)
                if cell is not None:
                    audit.require(cell["started_receipt_sha256"] == run_e1.sha256_file(folder / "STARTED.json"), "Cell start receipt changed")
                    cells.append(cell)
                    print(json.dumps({"event": "resume_completed", "model": model, "seed": seed}), flush=True)
                    continue
                run_e1.write_json(folder / "STARTED.json", {"created_utc": run_e1.utc_now(), "execution_binding": binding,
                                                          "comparison_binding": comparison, "prefit_receipt_sha256": prefit_sha})
                print(json.dumps({"event": "start", "model": model, "seed": seed}), flush=True)
                started = time.perf_counter()
                if model == "selected_gbdt":
                    actual_model = selection["selected_tree"]
                    classifier = run_e1.make_tree(actual_model, seed, selection["selected_parameters"], len(source["classes"]))
                    backend = None
                else:
                    actual_model = model
                    classifier, backend = create_foundation_classifier(model, model_cache, seed=seed, device="cpu", n_estimators=4, allow_download=False)
                constructor_seconds = time.perf_counter() - started
                imputer = SimpleImputer(strategy="median", keep_empty_features=True)
                started = time.perf_counter()
                classifier.fit(imputer.fit_transform(source["X"][rows]), source["y"][rows])
                fit_seconds = time.perf_counter() - started
                probabilities, prediction_seconds = run_e1.predict_chunks(classifier, imputer, target["X"], n_classes=len(source["classes"]), chunk_rows=1024, device="cpu")
                if backend is not None:
                    backend.update(fitted=True, runtime_compatibility_tested=True)
                staged = folder / "PREDICTIONS.tmp.npz"
                np.savez_compressed(staged, target_probabilities=probabilities, source_classes=source["classes"],
                                    target_y_binary=target["y_binary"], target_procedure_labels=target["procedure_labels"],
                                    target_fingerprints=target["group_sha256"], target_raw_to_unique=target["raw_to_unique"],
                                    selected_fit_indices=rows, selected_fit_fingerprints=source["group_sha256"][rows],
                                    imputer_statistics=imputer.statistics_)
                prediction_path = folder / "PREDICTIONS.npz"
                os.replace(staged, prediction_path)
                cell = {"schema_version": 1, "experiment": protocol["experiment"], "model": model, "actual_model": actual_model,
                        "seed": seed, "execution_binding": binding, "comparison_binding": comparison, "common_binding": common,
                        "prefit_receipt_sha256": prefit_sha, "started_receipt_sha256": run_e1.sha256_file(folder / "STARTED.json"),
                        "selected_fit_fingerprints_sha256": run_e1.canonical_hash(selection["support"]["fingerprints"]),
                        "source_fit_rows": len(rows), "source_fit_labels_per_class": 32, "target_fit_rows": 0, "target_calibration_rows": 0,
                        "new_hyperparameter_search": False, "source_tree_selection": {key: selection[key] for key in ["selected_tree", "selected_parameters", "cv_scores"]},
                        "backend_receipt": backend, "device": "cpu", "versions": execution["versions"],
                        "timing_seconds": {"constructor": constructor_seconds, "source_fit_including_imputer": fit_seconds, "target_predict_including_transform": prediction_seconds},
                        "metrics": {"deduplicated_primary": binary_metrics(probabilities, source["classes"].tolist(), target, np.ones(len(target["y_binary"]), dtype=np.int64)),
                                    "raw_flow_sensitivity": binary_metrics(probabilities, source["classes"].tolist(), target, target["raw_multiplicity"])},
                        "prediction_sha256": run_e1.sha256_file(prediction_path), "completed_utc": run_e1.utc_now()}
                run_e1.write_json(folder / "CELL.json", cell)
                run_e1.write_json(folder / "COMPLETE.json", {"execution_binding": binding, "comparison_binding": comparison,
                                                            "file_sha256": {"CELL.json": run_e1.sha256_file(folder / "CELL.json"), "PREDICTIONS.npz": cell["prediction_sha256"]}})
                cells.append(cell)
                run_e1.write_json(output / "RESULTS.json", summarize(cells, protocol))
                print(json.dumps({"event": "complete", "model": model, "seed": seed,
                                  "binary_macro_f1": cell["metrics"]["deduplicated_primary"]["binary_macro_f1"]}), flush=True)
                del classifier, imputer
    result = summarize(cells, protocol)
    result.update(execution_binding=binding, protocol_sha256=common["protocol_sha256"], prefit_receipt_sha256=prefit_sha)
    run_e1.write_json(output / "RESULTS.json", result)
    run_e1.write_json(output / "COMPLETE.json", {"execution_binding": binding,
                                               "artifact_sha256": {"PREFIT_RECEIPT.json": prefit_sha, "RESULTS.json": run_e1.sha256_file(output / "RESULTS.json")},
                                               "cell_complete_sha256": {f"{cell['model']}/{cell['seed']}": run_e1.sha256_file(output / "cells" / cell["model"] / str(cell["seed"]) / "COMPLETE.json") for cell in cells}})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["source-data", "target-data", "protocol", "e1-protocol", "source-baselines", "output", "model-cache"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    run(args.source_data, args.target_data, args.protocol, args.e1_protocol, args.source_baselines,
        args.output, args.model_cache, models=args.models.split(","), prepare_only=args.prepare_only)


if __name__ == "__main__":
    main()
