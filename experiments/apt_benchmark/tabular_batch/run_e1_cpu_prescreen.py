"""Separate case-control CPU plausibility screen; never a full E1/E4 result."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

from . import run_e1
from .analyze_e1 import check_reported_metrics, recompute_metrics, validate_cv
from .model_backend import CHECKPOINTS, create_foundation_classifier, ensure_checkpoint


SEEDS = [20260921, 20260922, 20260923]
BASELINES = ["random_forest", "xgboost", "lightgbm"]
FOUNDATIONS = ["tabicl_v2", "tabpfn_2_5_synthetic"]
QUERY_TAG = "E1_CPU_PRESCREEN_20260921"
RISKY = ["InitialCompromise", "DataExfiltration"]


def query_design(data: dict[str, np.ndarray], *, normal_count: int = 1024) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    classes = data["classes"].tolist()
    normal = classes.index("NormalTraffic")
    ids = np.flatnonzero(data["split"] == 2)
    attack = ids[data["y"][ids] != normal]
    benign = ids[data["y"][ids] == normal]
    if len(benign) < normal_count:
        raise ValueError("Not enough NormalTraffic development-test rows.")
    def key(index: int) -> bytes:
        return hashlib.sha256(f"{QUERY_TAG}|{data['group_sha256'][index]}".encode("ascii")).digest()
    benign_sample = sorted(benign.tolist(), key=key)[:normal_count]
    # Hash-order the combined query too, avoiding label-block-dependent batches.
    queries = np.asarray(sorted([*attack.tolist(), *benign_sample], key=key), dtype=np.int64)
    normal_weight = len(benign) / normal_count
    weights = np.where(data["y"][queries] == normal, normal_weight, 1.0)
    description = {"rows": len(queries), "attack_rows": len(attack), "normal_rows": normal_count,
                   "original_test_normal_rows": len(benign), "normal_weight": normal_weight,
                   "represented_weight_sum": float(weights.sum()), "query_hash_tag": QUERY_TAG,
                   "query_normal_sampling": "Fixed SHA256-ranked sample; all attack rows retained",
                   "enriched_attack_prevalence": len(attack) / len(queries),
                   "original_test_attack_prevalence": len(attack) / len(ids)}
    return queries, weights, description


def weighted_metrics(y: np.ndarray, probabilities: np.ndarray, classes: list[str], weights: np.ndarray) -> dict[str, Any]:
    # Validate distributions using the E1 checker; no fitting or model selection.
    run_e1.probability_metrics(y, probabilities, classes)
    if weights.shape != y.shape or not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("Weights must be positive, finite, and row-aligned.")
    predicted = probabilities.argmax(axis=1)
    matrix = np.zeros((len(classes), len(classes)), dtype=np.float64)
    np.add.at(matrix, (y, predicted), weights)
    per_stage = {}
    for label, name in enumerate(classes):
        tp = float(matrix[label, label])
        support, predicted_count = float(matrix[label].sum()), float(matrix[:, label].sum())
        truth = y == label
        per_stage[name] = {
            "precision": tp / predicted_count if predicted_count else 0.0,
            "recall": tp / support if support else 0.0,
            "f1": 2 * tp / (support + predicted_count) if support + predicted_count else 0.0,
            "support": support, "sample_support": int(truth.sum()),
            "roc_auc_ovr": float(roc_auc_score(truth, probabilities[:, label], sample_weight=weights)) if truth.any() and (~truth).any() else None,
            "average_precision_ovr": float(average_precision_score(truth, probabilities[:, label], sample_weight=weights)) if truth.any() else None,
        }
    aucs = [item["roc_auc_ovr"] for item in per_stage.values()]
    aps = [item["average_precision_ovr"] for item in per_stage.values()]
    return {"n": len(y), "represented_weight_sum": float(weights.sum()), "classes": classes,
            "accuracy": float(np.trace(matrix) / weights.sum()),
            "macro_f1": float(np.mean([item["f1"] for item in per_stage.values()])),
            "roc_auc_ovr_macro": float(np.mean(aucs)) if all(v is not None for v in aucs) else None,
            "average_precision_ovr_macro": float(np.mean(aps)) if all(v is not None for v in aps) else None,
            "confusion_matrix": matrix.tolist(), "per_stage": per_stage,
            "interpretation": "Prevalence-adjusted estimated score for this prescreen execution. Sampled NormalTraffic and changed query batches prevent treating it as an actual full-E1 score or unbiased ratio estimate."}


def evaluate(y: np.ndarray, probabilities: np.ndarray, classes: list[str], weights: np.ndarray) -> dict[str, Any]:
    unweighted = run_e1.probability_metrics(y, probabilities, classes)
    weighted = weighted_metrics(y, probabilities, classes, weights)
    normal = classes.index("NormalTraffic")
    mistakes = (y == normal) & (probabilities.argmax(axis=1) != normal)
    return {"query_unweighted_metrics": unweighted, "prevalence_weighted_estimated_metrics": weighted,
            "sampled_benign_false_positives": int(mistakes.sum()),
            "estimated_original_test_benign_false_positives": float(weights[mistakes].sum())}


def primary_summary(cells: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[int, dict[str, Any]] = {}
    for cell in cells:
        if cell["model"] in grouped.setdefault(cell["seed"], {}):
            raise ValueError("Duplicate model/seed cell.")
        grouped[cell["seed"]][cell["model"]] = cell
    pairs = []
    for seed in SEEDS:
        models = grouped.get(seed, {})
        if not {"tabicl_v2", "xgboost", "lightgbm"} <= models.keys():
            continue
        comparator = max([models["xgboost"], models["lightgbm"]], key=lambda cell: cell["inner_cv_selected_macro_f1"])
        candidate = models["tabicl_v2"]
        a, b = candidate["prevalence_weighted_estimated_metrics"], comparator["prevalence_weighted_estimated_metrics"]
        pairs.append({"seed": seed, "comparator_selected_by_e1_inner_cv": comparator["model"],
                      "candidate_weighted_estimated_macro_f1": a["macro_f1"], "comparator_weighted_estimated_macro_f1": b["macro_f1"],
                      "weighted_estimated_macro_f1_delta": a["macro_f1"] - b["macro_f1"],
                      "high_risk_recall_deltas": {name: a["per_stage"][name]["recall"] - b["per_stage"][name]["recall"] for name in RISKY}})
    mean_delta = float(np.mean([item["weighted_estimated_macro_f1_delta"] for item in pairs])) if pairs else None
    recall = {name: float(np.mean([item["high_risk_recall_deltas"][name] for item in pairs])) if pairs else None for name in RISKY}
    guards = {"mean_weighted_estimated_macro_f1_gain_at_least_0.02": mean_delta is not None and mean_delta >= .02,
              **{name + "_mean_recall_loss_at_most_0.05": value is not None and value >= -.05 for name, value in recall.items()}}
    status = "INCOMPLETE" if len(pairs) != 3 else ("PRELIMINARY_PROMISING" if all(guards.values()) else "PRELIMINARY_NEGATIVE")
    return {"status": status, "primary_candidate": "tabicl_v2", "paired_seed_count": len(pairs), "required_paired_seeds": 3,
            "mean_weighted_estimated_macro_f1_delta": mean_delta, "mean_high_risk_recall_deltas": recall,
            "guards": guards, "pairs": pairs,
            "interpretation": "Descriptive rescope after classical results were known, before foundation outcomes. Never full E1 PASS, independent replication, significance, or confirmation."}


def validate_protocol(protocol: dict[str, Any], e1_protocol_path: Path) -> dict[str, Any]:
    expected = {"schema_version": 1, "experiment": "E1_CPU_PRESCREEN", "status": "FROZEN_BEFORE_FOUNDATION_CLASSIFICATION_OUTCOMES",
                "seeds": SEEDS, "samples_per_class": 32, "normal_query_rows": 1024, "expected_attack_query_rows": 858,
                "expected_original_normal_rows": 29929, "query_hash_tag": QUERY_TAG, "foundation_n_estimators": 4,
                "prediction_chunk_rows": 1024, "cpu_threads": 4, "torch_interop_threads": 2,
                "foundation_models": FOUNDATIONS, "primary_candidate": "tabicl_v2", "macro_f1_delta_min": .02,
                "high_risk_classes": RISKY, "mean_recall_delta_min": -.05}
    if any(protocol.get(key) != value for key, value in expected.items()):
        raise ValueError("Prescreen protocol differs from the frozen design or is not frozen.")
    if protocol["e1_protocol_sha256"] != run_e1.sha256_file(e1_protocol_path):
        raise ValueError("E1 protocol hash mismatch.")
    e1_protocol = json.loads(e1_protocol_path.read_text(encoding="utf-8"))
    run_e1.validate_protocol(e1_protocol)
    if any(protocol[key] != e1_protocol[key] for key in ("data_npz_sha256", "manifest_sha256")):
        raise ValueError("Prescreen and E1 input hashes differ.")
    return e1_protocol


def extract_baselines(root: Path, data: dict[str, np.ndarray], e1_protocol: dict[str, Any], e1_protocol_path: Path,
                      queries: np.ndarray, weights: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, np.ndarray]]:
    prefit_path = root / "PREFIT_RECEIPT.json"
    prefit = json.loads(prefit_path.read_text(encoding="utf-8"))
    execution = prefit["execution"]
    if run_e1.canonical_hash(execution) != prefit["execution_binding"]:
        raise ValueError("Baseline prefit execution hash invalid.")
    source = Path(__file__).parent
    common = {key: execution[key] for key in ("data_sha256", "manifest_sha256", "protocol_sha256", "code_sha256")}
    source_names = ("run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt")
    if set(execution["code_sha256"]) != set(source_names):
        raise ValueError("Unexpected baseline source file roster.")
    expected = {"data_sha256": e1_protocol["data_npz_sha256"], "manifest_sha256": e1_protocol["manifest_sha256"],
                "protocol_sha256": run_e1.sha256_file(e1_protocol_path),
                "code_sha256": {name: run_e1.sha256_file(source / name) for name in source_names}}
    if common != expected or not set(BASELINES) <= set(execution["models"]):
        raise ValueError("Baseline input/protocol/source/model binding mismatch.")
    test_rows = np.flatnonzero(data["split"] == 2)
    positions = np.searchsorted(test_rows, queries)
    if not np.array_equal(test_rows[positions], queries):
        raise ValueError("Query does not map exactly into baseline test rows.")
    cells, evidence, saved_predictions = [], {"prefit_sha256": run_e1.sha256_file(prefit_path), "cells": {}}, {}
    classes = data["classes"].tolist()
    for seed in SEEDS:
        support = run_e1.select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=seed, budget=32)
        support_record = {"indices": support.tolist(), "fingerprints": data["group_sha256"][support].tolist()}
        if execution["supports"][str(seed)] != support_record:
            raise ValueError("Baseline support roster mismatch.")
        comparison = run_e1.canonical_hash({**common, "seed": seed, "support": support_record})
        for model in BASELINES:
            cell_dir = root / "cells" / model / str(seed)
            original = run_e1.validate_completed(cell_dir, prefit["execution_binding"], comparison)
            if original is None or original["model"] != model or original["seed"] != seed or original["common_binding"] != common:
                raise ValueError("Required baseline cell is incomplete or misbound.")
            if original["prefit_receipt_sha256"] != evidence["prefit_sha256"] or original["selected_fit_fingerprints_sha256"] != run_e1.canonical_hash(support_record["fingerprints"]):
                raise ValueError("Baseline support/prefit fingerprint receipt mismatch.")
            with np.load(cell_dir / "PREDICTIONS.npz", allow_pickle=False) as archive:
                p = {key: archive[key] for key in ("test_probabilities", "test_y", "test_indices", "classes", "selected_fit_indices", "selected_fit_fingerprints")}
            checks = [(p["test_indices"], test_rows), (p["test_y"], data["y"][test_rows]), (p["classes"], data["classes"]),
                      (p["selected_fit_indices"], support), (p["selected_fit_fingerprints"], data["group_sha256"][support])]
            if not all(np.array_equal(left, right) for left, right in checks):
                raise ValueError("Baseline array row/class/support order mismatch.")
            full_metrics = recompute_metrics(p["test_y"], p["test_probabilities"], classes)
            check_reported_metrics(original["metrics"]["test"], full_metrics)
            cv_score = validate_cv(original, e1_protocol)
            probabilities = p["test_probabilities"][positions]
            metrics = evaluate(data["y"][queries], probabilities, classes, weights)
            cells.append({"model": model, "seed": seed, "source": "verified E1 baseline predictions; no refit",
                          "inner_cv_selected_macro_f1": cv_score, **metrics, "baseline_full_test_metrics": full_metrics,
                          "baseline_weighted_minus_full_test_macro_f1": metrics["prevalence_weighted_estimated_metrics"]["macro_f1"] - full_metrics["macro_f1"]})
            key = f"{model}_{seed}"
            evidence["cells"][key] = {"complete_sha256": run_e1.sha256_file(cell_dir / "COMPLETE.json"),
                                     "cell_sha256": run_e1.sha256_file(cell_dir / "CELL.json"), "predictions_sha256": original["prediction_sha256"],
                                     "comparison_binding": comparison}
            saved_predictions[key] = probabilities
    return cells, evidence, saved_predictions


def aggregate(cells: list[dict[str, Any]], query: dict[str, Any], receipt_sha: str, protocol_sha: str) -> dict[str, Any]:
    summaries = {}
    for model in [*BASELINES, *FOUNDATIONS]:
        subset = [cell for cell in cells if cell["model"] == model]
        summaries[model] = {"seed_count": len(subset),
                            "mean_query_unweighted_macro_f1": float(np.mean([cell["query_unweighted_metrics"]["macro_f1"] for cell in subset])) if subset else None,
                            "mean_prevalence_weighted_estimated_macro_f1": float(np.mean([cell["prevalence_weighted_estimated_metrics"]["macro_f1"] for cell in subset])) if subset else None}
        if model in BASELINES:
            summaries[model]["mean_baseline_full_test_macro_f1"] = float(np.mean([cell["baseline_full_test_metrics"]["macro_f1"] for cell in subset]))
            summaries[model]["mean_weighted_estimate_minus_full_test_macro_f1"] = float(np.mean([cell["baseline_weighted_minus_full_test_macro_f1"] for cell in subset]))
    return {"schema_version": 1, "experiment": "E1_CPU_PRESCREEN", "query": query, "cells": cells,
            "model_summaries": summaries, "primary_descriptive": primary_summary(cells),
            "prefit_receipt_sha256": receipt_sha, "protocol_sha256": protocol_sha,
            "foundation_cell_count": sum(cell["model"] in FOUNDATIONS for cell in cells),
            "full_e1_completed": False, "e4_evaluated": False, "gpu_evaluated": False,
            "limitations": ["Separate CPU plausibility screen after classical results were known, before foundation classification outcomes.",
                            "Weighted estimates are not full-test scores; sampled NormalTraffic induces uncertainty not measured by the three fitting seeds.",
                            "Each sampled benign error represents about 29.23 original-test rows; zero sampled false positives does not establish zero original-test false positives.",
                            "All three seeds share the same query and fitting pool; no CI, significance, independent incident or confirmation claim.",
                            "Query batch composition differs from full E1; foundation prediction batch invariance has not been established.",
                            "InitialCompromise recall denominator15; DataExfiltration106. No calibration or E4 evaluation in this prescreen.",
                            "TabICL remains primary and TabPFN secondary regardless of outcomes; novelty remains unestablished."]}


def run(data_path: Path, protocol_path: Path, e1_protocol_path: Path, baseline_root: Path, output: Path, model_cache: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    e1_protocol = validate_protocol(protocol, e1_protocol_path)
    if data_path.is_dir():
        data_path = data_path / "DATA.npz"
    data, _ = run_e1.load_data(data_path, e1_protocol)
    queries, weights, query = query_design(data)
    if query["attack_rows"] != 858 or query["original_test_normal_rows"] != 29929:
        raise ValueError("Actual query counts differ from the frozen prescreen design.")
    baseline_cells, baseline_evidence, baseline_predictions = extract_baselines(baseline_root, data, e1_protocol, e1_protocol_path, queries, weights)
    supports = {str(seed): run_e1.select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=seed, budget=32).tolist() for seed in SEEDS}
    # Verify cached weights before any scientific model fit; no automatic downloads.
    checkpoint_receipts = {}
    for name in FOUNDATIONS:
        ensure_checkpoint(name, model_cache, allow_download=False)
        checkpoint_receipts[name] = {"sha256": CHECKPOINTS[name].sha256, "revision": CHECKPOINTS[name].revision, "filename": CHECKPOINTS[name].filename}
    source = Path(__file__).parent
    execution = {"protocol_sha256": run_e1.sha256_file(protocol_path), "e1_protocol_sha256": run_e1.sha256_file(e1_protocol_path),
                 "data_npz_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
                 "code_sha256": {name: run_e1.sha256_file(source / name) for name in ("run_e1_cpu_prescreen.py", "run_e1.py", "model_backend.py", "analyze_e1.py", "requirementsfoundation.txt")},
                 "supports": {seed: {"indices": ids, "fingerprints": data["group_sha256"][ids].tolist()} for seed, ids in supports.items()},
                 "query_indices": queries.tolist(), "query_fingerprints": data["group_sha256"][queries].tolist(), "query_weights": weights.tolist(),
                 "checkpoints": checkpoint_receipts, "baselines": baseline_evidence, "versions": run_e1.package_versions(),
                 "device": "cpu", "cpu_threads": 4, "torch_interop_threads": 2,
                 "prescreen_parameter_overrides": {"tabicl_v2": {"n_jobs": 4}}}
    binding = run_e1.canonical_hash(execution)
    prefit_path = output / "PREFIT_RECEIPT.json"
    if prefit_path.exists():
        prefit = json.loads(prefit_path.read_text(encoding="utf-8"))
        if prefit["execution_binding"] != binding or prefit["execution"] != execution:
            raise ValueError("Output is bound to another prescreen; use a fresh directory.")
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("Nonempty output without a prefit receipt is preserved.")
        run_e1.write_json(prefit_path, {"created_utc": run_e1.utc_now(), "execution_binding": binding, "binding_sha256": binding, "execution": execution,
                                      "foundation_classification_outcomes_observed_at_freeze": False,
                                      "classical_results_already_known": True, "query": query})
    receipt_sha = run_e1.sha256_file(prefit_path)
    baseline_path = output / "BASELINE_QUERY_PRIVATE.npz"
    if not baseline_path.exists():
        np.savez_compressed(baseline_path, **baseline_predictions, query_indices=queries, query_y=data["y"][queries],
                            query_fingerprints=data["group_sha256"][queries], query_weights=weights, classes=data["classes"])
    else:
        with np.load(baseline_path, allow_pickle=False) as existing:
            expected_arrays = {**baseline_predictions, "query_indices": queries, "query_y": data["y"][queries],
                               "query_fingerprints": data["group_sha256"][queries], "query_weights": weights, "classes": data["classes"]}
            if set(existing.files) != set(expected_arrays) or any(not np.array_equal(existing[key], value) for key, value in expected_arrays.items()):
                raise ValueError("Saved baseline/query packet changed; preserving it.")
    cells = list(baseline_cells)
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    with threadpool_limits(limits=4):
        for seed in SEEDS:
            rows = np.asarray(supports[str(seed)], dtype=np.int64)
            for name in FOUNDATIONS:
                directory = output / "cells" / name / str(seed)
                comparison = run_e1.canonical_hash({"execution_binding": binding, "seed": seed, "model": name})
                cell = run_e1.validate_completed(directory, binding, comparison)
                if cell is not None:
                    if cell["model"] != name or cell["seed"] != seed or cell["prefit_receipt_sha256"] != receipt_sha:
                        raise ValueError("Resumed cell metadata differs from its prescreen binding.")
                    if run_e1.sha256_file(directory / "BACKEND_PRIVATE.json") != cell["backend_private_sha256"]:
                        raise ValueError("Resumed backend receipt changed; preserving artifacts.")
                    cells.append(cell)
                    continue
                print(json.dumps({"event": "prescreen_model_start", "model": name, "seed": seed}), flush=True)
                started = time.perf_counter()
                model, backend = create_foundation_classifier(name, model_cache, seed=seed, device="cpu", n_estimators=4, allow_download=False)
                if name == "tabicl_v2":
                    # The shared E1 backend stays frozen; this CPU-specific run
                    # explicitly assigns its registered four-thread inference budget.
                    model.set_params(n_jobs=4)
                    backend["prescreen_parameter_overrides"] = {"n_jobs": 4}
                constructor_seconds = time.perf_counter() - started
                imputer = SimpleImputer(strategy="median", keep_empty_features=True)
                started = time.perf_counter()
                model.fit(imputer.fit_transform(data["X"][rows]), data["y"][rows])
                fit_seconds = time.perf_counter() - started
                probabilities, predict_seconds = run_e1.predict_chunks(model, imputer, data["X"][queries], n_classes=len(data["classes"]), chunk_rows=1024, device="cpu")
                metrics = evaluate(data["y"][queries], probabilities, data["classes"].tolist(), weights)
                directory.mkdir(parents=True, exist_ok=True)
                predictions_path = directory / "PREDICTIONS.npz"
                np.savez_compressed(predictions_path, probabilities=probabilities, query_indices=queries, query_y=data["y"][queries],
                                    query_fingerprints=data["group_sha256"][queries], query_weights=weights, classes=data["classes"],
                                    selected_fit_indices=rows, selected_fit_fingerprints=data["group_sha256"][rows], imputer_statistics=imputer.statistics_)
                backend.update(fitted=True, runtime_compatibility_tested=True)
                # Keep constructor paths in the private receipt, not public metrics.
                run_e1.write_json(directory / "BACKEND_PRIVATE.json", backend)
                cell = {"model": name, "seed": seed, "execution_binding": binding, "comparison_binding": comparison,
                        "prefit_receipt_sha256": receipt_sha, "prediction_sha256": run_e1.sha256_file(predictions_path),
                        "backend_private_sha256": run_e1.sha256_file(directory / "BACKEND_PRIVATE.json"),
                        "checkpoint": checkpoint_receipts[name], "versions": execution["versions"], "actual_device": "cpu", "cpu_threads": 4,
                        "prediction_chunk_rows": 1024, "selected_fit_rows": len(rows), **metrics,
                        "timing_seconds": {"constructor": constructor_seconds, "fit_including_imputer": fit_seconds, "predict_query_including_transform": predict_seconds}}
                run_e1.write_json(directory / "CELL.json", cell)
                run_e1.write_json(directory / "COMPLETE.json", {"execution_binding": binding, "comparison_binding": comparison,
                                      "file_sha256": {"CELL.json": run_e1.sha256_file(directory / "CELL.json"), "PREDICTIONS.npz": cell["prediction_sha256"]}})
                cells.append(cell)
                result = aggregate(cells, query, receipt_sha, execution["protocol_sha256"])
                run_e1.write_json(output / "AGGREGATE.json", result)
                print(json.dumps({"event": "prescreen_model_complete", "model": name, "seed": seed,
                                  "weighted_estimated_macro_f1": metrics["prevalence_weighted_estimated_metrics"]["macro_f1"]}), flush=True)
                del model, imputer
    result = aggregate(cells, query, receipt_sha, execution["protocol_sha256"])
    run_e1.write_json(output / "AGGREGATE.json", result)
    run_e1.write_json(output / "COMPLETE.json", {"execution_binding": binding, "binding_sha256": binding,
                          "artifact_sha256": {name: run_e1.sha256_file(output / name) for name in ("PREFIT_RECEIPT.json", "BASELINE_QUERY_PRIVATE.npz", "AGGREGATE.json")},
                          "cell_complete_sha256": {f"{name}/{seed}": run_e1.sha256_file(output / "cells" / name / str(seed) / "COMPLETE.json") for seed in SEEDS for name in FOUNDATIONS}})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--e1-protocol", type=Path, required=True)
    parser.add_argument("--baselines", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    args = parser.parse_args()
    run(args.data, args.protocol, args.e1_protocol, args.baselines, args.output, args.model_cache)


if __name__ == "__main__":
    main()
