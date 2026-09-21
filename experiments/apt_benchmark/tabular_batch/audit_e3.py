"""Independent audit of saved E3 inputs, probabilities, treatments and gates.

No model is trained or selected. Model files are checksum-verified, not replayed.
The original learner, metric functions and summary functions are not imported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def compare(actual: Any, expected: Any, path: str = "root") -> None:
    """Compare JSON-like evidence, allowing roundoff but rejecting extra fields."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f"{path}: keys differ")
        for key in expected:
            compare(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f"{path}: list shape differs")
        for index, value in enumerate(expected):
            compare(actual[index], value, f"{path}[{index}]")
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        require(type(actual) is type(expected) and actual == expected, f"{path}: value differs")
    elif isinstance(expected, (int, float)):
        require(type(actual) in (int, float) and np.isfinite(actual), f"{path}: nonfinite/non-numeric value")
        require(abs(actual - expected) <= 1e-10, f"{path}: number differs")
    else:
        raise TypeError(f"Unexpected comparison type at {path}")


def local_artifact(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    require(candidate.is_relative_to(root.resolve()), "Artifact path leaves the run directory")
    require(candidate.is_file(), f"Missing completed artifact: {relative}")
    return candidate


def independent_metrics(y: np.ndarray, probabilities: np.ndarray, classes: list[str]) -> dict[str, Any]:
    require(y.ndim == 1 and np.issubdtype(y.dtype, np.integer) and len(y) > 0, "Invalid evaluation labels")
    require(np.all((y >= 0) & (y < len(classes))), "Evaluation labels exceed class roster")
    require(probabilities.shape == (len(y), len(classes)), "Probability shape differs")
    require(np.isfinite(probabilities).all() and np.all((probabilities >= 0) & (probabilities <= 1)), "Invalid probabilities")
    require(np.allclose(probabilities.sum(axis=1), 1, rtol=0, atol=1e-6), "Probability rows do not sum to one")
    predicted = probabilities.argmax(axis=1)
    counts = np.zeros((len(classes), len(classes)), dtype=np.int64)
    np.add.at(counts, (y, predicted), 1)
    stages = {}
    for index, label in enumerate(classes):
        true_positive = int(counts[index, index])
        support = int(counts[index, :].sum())
        flagged = int(counts[:, index].sum())
        binary = y == index
        supported = 0 < support < len(y)
        stages[label] = {
            "precision": true_positive / flagged if flagged else 0.0,
            "recall": true_positive / support if support else 0.0,
            "f1": 2 * true_positive / (support + flagged) if support + flagged else 0.0,
            "support": support,
            "roc_auc": float(roc_auc_score(binary, probabilities[:, index])) if supported else None,
            "average_precision": float(average_precision_score(binary, probabilities[:, index])) if supported else None,
        }
    return {"macro_f1": float(np.mean([row["f1"] for row in stages.values()])),
            "accuracy": int(np.trace(counts)) / len(y), "count": len(y),
            "per_stage": stages, "confusion_matrix": counts.tolist()}


def independent_treatment(arrays: dict[str, np.ndarray], classes: list[str]) -> dict[str, Any]:
    truth = arrays["clean_fit_labels"]
    observed = arrays["noisy_fit_labels"]
    assigned = arrays["assigned_fit_labels"]
    active = arrays["active_fit_mask"]
    changed = arrays["treated_fit_mask"]
    candidates = arrays["candidate_fit_mask"]
    noisy = truth != observed
    require(np.array_equal(arrays["hidden_noise_mask"], noisy), "Hidden corruption mask disagrees with labels")
    clean = ~noisy
    damaged = clean & ((~active) | (assigned != truth))
    counts = {}
    for name, selected in (("candidate_detection", candidates), ("actual_treatment", changed)):
        selected_count = int(np.count_nonzero(selected))
        selected_errors = int(np.count_nonzero(selected & noisy))
        total_errors = int(np.count_nonzero(noisy))
        counts[name] = {"selected": selected_count, "truly_noisy_selected": selected_errors,
                        "clean_selected": selected_count - selected_errors,
                        "precision": selected_errors / selected_count if selected_count else None,
                        "recall": selected_errors / total_errors if total_errors else None}
    per_stage = {}
    for index, label in enumerate(classes):
        source_class = truth == index
        clean_class = source_class & clean
        denominator = int(clean_class.sum())
        numerator = int(np.count_nonzero(clean_class & damaged))
        per_stage[label] = {"original_count": int(source_class.sum()), "originally_clean_count": denominator,
                            "originally_clean_removed_or_mislabeled": numerator,
                            "clean_damage_fraction": numerator / denominator if denominator else None}
    return {"injected_noise_count": int(noisy.sum()), "injected_noise_fraction": int(noisy.sum()) / len(noisy),
            **counts, "originally_clean_removed_or_mislabeled": int(damaged.sum()),
            "noisy_labels_corrected_and_retained": int(np.count_nonzero(noisy & active & (assigned == truth))),
            "noisy_examples_removed": int(np.count_nonzero(noisy & (~active))),
            "retained_incorrect_labels": int(np.count_nonzero(active & (assigned != truth))), "per_stage": per_stage}


def expected_support(y: np.ndarray, split: np.ndarray, groups: np.ndarray,
                     seed: int, cap: int, classes: list[str]) -> np.ndarray:
    selected = []
    for label in range(len(classes)):
        indices = [int(i) for i in np.flatnonzero((y == label) & (split == 0))]
        fingerprints = [(hashlib.sha256((str(seed) + "|" + str(groups[i])).encode()).digest(), i) for i in indices]
        selected.extend(i for _, i in sorted(fingerprints)[:cap])
    return np.asarray(selected, dtype=np.int64)


def expected_corruption(clean: np.ndarray, seed: int, rate: float, classes: list[str]) -> np.ndarray:
    generator = np.random.default_rng(seed + 917)
    indices = generator.choice(len(clean), int(np.floor(rate * len(clean))), replace=False)
    offsets = generator.integers(1, len(classes), len(indices))
    expected = clean.copy()
    expected[indices] = np.remainder(clean[indices] + offsets, len(classes))
    return expected


def array_hash(value: np.ndarray) -> str:
    value = np.ascontiguousarray(value)
    return hashlib.sha256(str(value.dtype).encode() + str(value.shape).encode() + value.tobytes()).hexdigest()


def check_treatment_state(row: dict[str, Any], arrays: dict[str, np.ndarray], protocol: dict[str, Any]) -> None:
    count = len(arrays["fit_indices"])
    for key in ("hidden_noise_mask", "active_fit_mask", "treated_fit_mask", "candidate_fit_mask"):
        require(arrays[key].dtype == bool and arrays[key].shape == (count,), f"Invalid boolean mask: {key}")
    for key in ("clean_fit_labels", "noisy_fit_labels", "assigned_fit_labels"):
        require(arrays[key].shape == (count,) and np.issubdtype(arrays[key].dtype, np.integer), f"Invalid label array: {key}")
        require(np.all((arrays[key] >= 0) & (arrays[key] < len(protocol["classes"]))), f"Label outside class set: {key}")
    active, treated, candidate = arrays["active_fit_mask"], arrays["treated_fit_mask"], arrays["candidate_fit_mask"]
    assigned, observed = arrays["assigned_fit_labels"], arrays["noisy_fit_labels"]
    require(np.all(~treated | candidate), "Treated row was never a candidate")
    arm = row["arm"]
    if arm == "no_correction":
        require(active.all() and not treated.any() and not candidate.any(), "Baseline contains treatment")
        require(np.array_equal(assigned, observed) and row["treatment_trace"] == [], "Baseline labels/trace changed")
        return
    if arm == "gradient_gmm_removal_adaptation":
        require(np.array_equal(treated, ~active), "Removal state disagrees with treatment mask")
        require(np.array_equal(assigned, observed), "Removal arm relabeled examples")
        require(int(treated.sum()) <= int(np.floor(protocol["treatment"]["removal_cap_fraction"] * count)), "Removal cap exceeded")
        for label in np.unique(observed):
            require(np.any(active & (assigned == label)), "Removal erased an observed class")
    elif arm == "gradient_gmm_relabel_adaptation":
        require(active.all(), "Relabel arm removed examples")
        require(np.array_equal(treated, assigned != observed), "Relabel mask disagrees with changed labels")
    else:
        raise ValueError("Unknown treatment arm")
    settings = protocol["treatment"]
    rounds = list(range(settings["warmup_rounds"], protocol["boosting_rounds"], settings["intervention_every_rounds"]))
    trace = row["treatment_trace"]
    require([entry["after_round"] for entry in trace] == rounds, "Treatment schedule differs from protocol")
    cumulative = 0
    for entry in trace:
        require(all(type(entry[key]) is int for key in ("after_round", "candidates", "changed", "active_count", "treated_count")), "Trace counts are not integers")
        require(0 <= entry["changed"] <= entry["candidates"] <= count - cumulative, "Trace candidate/change counts are impossible")
        cumulative += entry["changed"]
        require(entry["treated_count"] == cumulative, "Trace treatment counts do not accumulate")
        expected_active = count - cumulative if arm == "gradient_gmm_removal_adaptation" else count
        require(entry["active_count"] == expected_active, "Trace active count is inconsistent")
    require(cumulative == int(treated.sum()), "Final trace treatment count differs from saved state")


def independent_summary(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    by_key = {(row["seed"], row["noise_rate"], row["arm"]): row for row in rows}
    screens = {}
    for arm in protocol["arms"]:
        if arm == "no_correction":
            continue
        paired = []
        for seed in protocol["seeds"]:
            clean = by_key[(seed, 0.0, arm)]["test"]
            noisy = by_key[(seed, protocol["primary_noise_rate"], arm)]["test"]
            base_clean = by_key[(seed, 0.0, "no_correction")]["test"]
            base_noisy = by_key[(seed, protocol["primary_noise_rate"], "no_correction")]["test"]
            rare = protocol["rare_stage"]
            paired.append({"seed": seed, "noisy_macro_f1_delta": noisy["macro_f1"] - base_noisy["macro_f1"],
                           "clean_macro_f1_delta": clean["macro_f1"] - base_clean["macro_f1"],
                           "clean_rare_stage_recall_delta": clean["per_stage"][rare]["recall"] - base_clean["per_stage"][rare]["recall"],
                           "noisy_rare_stage_recall_delta": noisy["per_stage"][rare]["recall"] - base_noisy["per_stage"][rare]["recall"]})
        means = {key: sum(row[key] for row in paired) / len(paired) for key in paired[0] if key != "seed"}
        settings = protocol["screen"]
        guards = {"noisy_macro_f1_recovery": means["noisy_macro_f1_delta"] >= settings["noisy_macro_f1_gain_min"],
                  "clean_macro_f1_preserved": means["clean_macro_f1_delta"] >= settings["clean_macro_f1_delta_min"],
                  "clean_rare_recall_preserved": means["clean_rare_stage_recall_delta"] >= settings["clean_rare_stage_recall_delta_min"],
                  "noisy_rare_recall_preserved": means["noisy_rare_stage_recall_delta"] >= settings["noisy_rare_stage_recall_delta_min"]}
        screens[arm] = {"paired_seed_deltas": paired, "mean_deltas": means, "guards": guards,
                        "all_gates_pass": all(guards.values())}
    return {"screen_status": "PROMISING_DEVELOPMENT_ONLY" if any(item["all_gates_pass"] for item in screens.values()) else "NEGATIVE_DEVELOPMENT",
            "run_count": len(rows), "screens": screens,
            "interpretation": "Three seeds on one exposed development split; no confidence interval, significance, independent-campaign, original-algorithm, or novelty claim."}


def audit(prepared: Path, run_root: Path, protocol_path: Path,
          runner_path: Path | None = None) -> dict[str, Any]:
    prepared, run_root, protocol_path = Path(prepared), Path(run_root), Path(protocol_path)
    runner_path = Path(runner_path) if runner_path else Path(__file__).with_name("run_e3.py")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    compare(json.loads((run_root / "PROTOCOL.json").read_text(encoding="utf-8")), protocol, "protocol_snapshot")
    manifest_path, data_path = prepared / "MANIFEST.json", prepared / "DATA.npz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt_path = run_root / "PRE_FIT_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(digest(data_path) == manifest["data_npz_sha256"] == protocol["dataset_npz_sha256"] == receipt["data_npz_sha256"], "Prepared data hash mismatch")
    require(digest(manifest_path) == receipt["manifest_sha256"], "Prepared manifest hash mismatch")
    require(digest(protocol_path) == receipt["protocol_sha256"], "Protocol hash mismatch")
    require(digest(runner_path) == receipt["runner_sha256"], "Runner source changed after freeze")
    require(receipt["versions"]["xgboost"] == protocol["xgboost_version"], "XGBoost version mismatch")
    require(receipt["fits_started"] is False, "Receipt does not declare pre-fit state")
    with np.load(data_path, allow_pickle=False) as archive:
        classes = archive["classes"].tolist()
        y, split, groups = archive["y"], archive["split"], archive["group_sha256"]
    compare(classes, protocol["classes"], "class_roster")
    compare(classes, manifest["classes"], "manifest_class_roster")
    require(np.isin(split, [0, 1, 2]).all() and len(set(groups.tolist())) == len(groups), "Invalid split/group roster")
    test_indices = np.flatnonzero(split == 2)
    require(receipt["test_count"] == len(test_indices) and receipt["test_indices_sha256"] == array_hash(test_indices), "Frozen test roster mismatch")
    require(receipt["calibration_count_unused"] == int(np.count_nonzero(split == 1)), "Calibration count mismatch")
    supports = {}
    selections = []
    for seed in protocol["seeds"]:
        indices = expected_support(y, split, groups, seed, protocol["fit_per_class_cap"], classes)
        supports[seed] = indices
        selections.append({"seed": seed, "count": len(indices), "indices_sha256": array_hash(indices),
                           "group_sha256": array_hash(groups[indices]),
                           "class_counts": {label: int(np.count_nonzero(y[indices] == index)) for index, label in enumerate(classes)}})
    compare(receipt["selections"], selections, "prefit_selections")
    expected_keys = {(seed, rate, arm) for seed in protocol["seeds"] for rate in protocol["noise_rates"] for arm in protocol["arms"]}
    final_path = run_root / "RESULTS.json"
    partial_path = run_root / "RESULTS.partial.json"
    if final_path.exists():
        result = json.loads(final_path.read_text(encoding="utf-8"))
        compare(result["protocol"], protocol, "result_protocol")
        rows = result["rows"]
    else:
        result = None
        rows = json.loads(partial_path.read_text(encoding="utf-8")) if partial_path.exists() else []
    if rows or (run_root / "RUN_STARTED.json").exists():
        started = json.loads((run_root / "RUN_STARTED.json").read_text(encoding="utf-8"))
        require(started["receipt_sha256"] == digest(receipt_path), "Pre-fit receipt changed after run start")
    seen = set()
    audited = []
    required_arrays = {"probabilities", "y_test", "test_indices", "fit_indices", "clean_fit_labels", "noisy_fit_labels",
                       "hidden_noise_mask", "assigned_fit_labels", "active_fit_mask", "treated_fit_mask", "candidate_fit_mask"}
    for row in rows:
        key = row["seed"], row["noise_rate"], row["arm"]
        require(key in expected_keys and key not in seen, "Duplicate or unregistered result cell")
        seen.add(key)
        prediction_path = local_artifact(run_root, row["prediction_file"])
        model_path = local_artifact(run_root, row["model_file"])
        require(digest(prediction_path) == row["prediction_sha256"], "Prediction archive checksum mismatch")
        require(digest(model_path) == row["model_sha256"], "Model checksum mismatch")
        require(type(row["fit_seconds"]) in (int, float) and np.isfinite(row["fit_seconds"]) and row["fit_seconds"] >= 0, "Invalid fit duration")
        with np.load(prediction_path, allow_pickle=False) as archive:
            require(set(archive.files) == required_arrays, "Prediction archive fields differ")
            arrays = {name: archive[name] for name in archive.files}
        indices = supports[row["seed"]]
        require(np.array_equal(arrays["fit_indices"], indices) and row["fit_count"] == len(indices), "Fit subset differs from frozen selection")
        require(np.array_equal(arrays["clean_fit_labels"], y[indices]), "Post-hoc source labels differ from prepared input")
        require(np.array_equal(arrays["test_indices"], test_indices), "Test rows/order differ from frozen input")
        require(np.array_equal(arrays["y_test"], y[test_indices]), "Test labels differ from frozen input")
        expected_noisy = expected_corruption(y[indices], row["seed"], row["noise_rate"], classes)
        require(np.array_equal(arrays["noisy_fit_labels"], expected_noisy), "Injected corruption differs from protocol")
        check_treatment_state(row, arrays, protocol)
        metrics = independent_metrics(arrays["y_test"], arrays["probabilities"], classes)
        treatment = independent_treatment(arrays, classes)
        compare(row["test"], metrics, f"{key}.test")
        compare(row["treatment_audit"], treatment, f"{key}.treatment")
        audited.append({**row, "test": metrics, "treatment_audit": treatment})
    missing = sorted(expected_keys - seen)
    completed_path = run_root / "RUN_COMPLETE.json"
    complete = not missing and result is not None and completed_path.exists()
    summary = None
    if complete:
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
        require(completed["run_count"] == len(expected_keys) and completed["results_sha256"] == digest(final_path), "Run completion checksum/count mismatch")
        summary = independent_summary(audited, protocol)
        compare(result["summary"], summary, "results_summary")
        compare(json.loads((run_root / "SUMMARY.json").read_text(encoding="utf-8")), summary, "summary_file")
    elif completed_path.exists():
        raise ValueError("Run claims completion while required results are absent")
    return {"schema_version": 1, "audit_status": "PASS", "run_status": "COMPLETE" if complete else "INCOMPLETE",
            "audited_cells": len(audited), "expected_cells": len(expected_keys),
            "missing_cells": [{"seed": key[0], "noise_rate": key[1], "arm": key[2]} for key in missing],
            "independent_summary": summary, "protocol_sha256": digest(protocol_path), "receipt_sha256": digest(receipt_path),
            "checks": ["Frozen source/protocol/data hashes and fit/test rosters", "Per-cell prediction/model byte checksums",
                       "Exact source labels and deterministic training corruption", "Independent confusion/F1/AUC/AP metrics",
                       "Treatment masks, trace schedule, caps and observed-class retention", "Independent post-hoc noise/treatment precision/recall",
                       "Complete-grid paired seed deltas and all four gates"],
            "limitations": ["Model bytes are checksum-verified; model predictions and the learning trajectory were not replayed.",
                            "A passing calculation audit does not establish independent incidents, correct source annotations, or novelty.",
                            "A partial-run PASS applies only to the artifacts audited; no final outcome is issued until COMPLETE."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol_e3.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Choose a fresh audit output directory")
    report = audit(args.prepared, args.run, args.protocol)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "AUDIT.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (args.output / "AUDIT.md").write_text(
        "# Independent E3 calculation audit\n\n" + f"Audit: **{report['audit_status']}**. Run: **{report['run_status']}**. " +
        f"Audited cells: {report['audited_cells']}/{report['expected_cells']}.\n\n" +
        "\n".join("- " + item for item in report["checks"]) + "\n\n## Limits\n\n" +
        "\n".join("- " + item for item in report["limitations"]) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("audit_status", "run_status", "audited_cells", "expected_cells")}, indent=2))
