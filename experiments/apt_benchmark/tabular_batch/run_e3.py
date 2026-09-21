"""Bounded label-noise pilot; explicit history-gradient/GMM adaptation.

First run --freeze-only, inspect/save the receipt, then run --run with the same
source/protocol/data. No SCVIC model is fitted by import or by --freeze-only.
True corruption labels/masks are used only by post-hoc scoring.
"""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score


DEFAULT_PREPARED = Path("C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared")
DEFAULT_PROTOCOL = Path(__file__).with_name("protocol_e3.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    return hashlib.sha256(str(array.dtype).encode() + str(array.shape).encode() + array.tobytes()).hexdigest()


def select_fit_indices(y: np.ndarray, split: np.ndarray, groups: np.ndarray,
                       cap: int, seed: int, n_classes: int) -> np.ndarray:
    """Select from the frozen fit split only; no test labels/features are used."""
    chosen = []
    for label in range(n_classes):
        eligible = np.flatnonzero((split == 0) & (y == label))
        ordered = sorted(eligible.tolist(), key=lambda index: hashlib.sha256(
            f"{seed}|{groups[index]}".encode()).digest())
        chosen.extend(ordered[:cap])
    return np.asarray(chosen, dtype=np.int64)


def inject_symmetric_noise(labels: np.ndarray, rate: float, n_classes: int,
                           seed: int) -> tuple[np.ndarray, np.ndarray]:
    labels = np.asarray(labels, dtype=np.int64)
    if labels.ndim != 1 or n_classes < 2 or not 0 <= rate <= 1:
        raise ValueError("Invalid labels, class count or noise rate.")
    if np.any((labels < 0) | (labels >= n_classes)):
        raise ValueError("Training labels must index the declared classes.")
    generator = np.random.default_rng(seed + 917)
    selected = generator.choice(len(labels), size=math.floor(rate * len(labels)), replace=False)
    noisy = labels.copy()
    noisy[selected] = (noisy[selected] + generator.integers(1, n_classes, len(selected))) % n_classes
    return noisy, noisy != labels


def gradient_statistic(probability_history: list[np.ndarray], labels: np.ndarray) -> np.ndarray:
    """Mean of per-round maximum absolute post-update softmax residuals."""
    if not probability_history:
        raise ValueError("An observed probability history is required.")
    labels = np.asarray(labels, dtype=np.int64)
    n_rows, n_classes = probability_history[0].shape
    if labels.shape != (n_rows,) or np.any((labels < 0) | (labels >= n_classes)):
        raise ValueError("Assigned labels must index probability columns.")
    target = np.eye(n_classes)[labels]
    residuals = []
    for probabilities in probability_history:
        if probabilities.shape != (n_rows, n_classes) or not np.all(np.isfinite(probabilities)):
            raise ValueError("History probabilities have inconsistent shape or nonfinite values.")
        residuals.append(np.max(np.abs(probabilities - target), axis=1))
    return np.mean(residuals, axis=0)


def identify_candidates(statistic: np.ndarray, active: np.ndarray, treated: np.ndarray,
                        seed: int, settings: dict[str, Any]) -> np.ndarray:
    """No corruption rate, clean labels or hidden mask is available here."""
    candidates = np.zeros(len(statistic), dtype=bool)
    values = statistic[active]
    if len(values) < 4 or float(np.std(values)) <= 1e-8:
        return candidates
    mixture = GaussianMixture(n_components=2, n_init=settings["gmm_n_init"],
                              max_iter=settings["gmm_max_iter"],
                              reg_covar=settings["gmm_reg_covar"], random_state=seed)
    mixture.fit(values.reshape(-1, 1))
    means = mixture.means_.ravel()
    if abs(float(means[0] - means[1])) <= 1e-8:
        return candidates
    component = int(np.argmax(means))
    posterior = mixture.predict_proba(statistic.reshape(-1, 1))[:, component]
    candidates = active & (~treated) & (posterior > 0.5)
    return candidates


def apply_treatment(arm: str, candidates: np.ndarray, statistic: np.ndarray,
                    mean_probabilities: np.ndarray, assigned: np.ndarray,
                    active: np.ndarray, treated: np.ndarray,
                    removal_cap_fraction: float) -> np.ndarray:
    """Mutate the learner's observed-label state and return actual changed rows."""
    changed = np.zeros(len(assigned), dtype=bool)
    eligible = candidates & active & (~treated)
    if arm == "gradient_gmm_removal_adaptation":
        remaining = max(0, math.floor(removal_cap_fraction * len(assigned)) - int((~active).sum()))
        counts = np.bincount(assigned[active], minlength=mean_probabilities.shape[1])
        for index in sorted(np.flatnonzero(eligible), key=lambda index: (-statistic[index], int(index))):
            if remaining == 0:
                break
            if counts[assigned[index]] <= 1:
                continue
            active[index] = False
            treated[index] = True
            changed[index] = True
            counts[assigned[index]] -= 1
            remaining -= 1
    elif arm == "gradient_gmm_relabel_adaptation":
        proposed = np.argmax(mean_probabilities, axis=1)
        changed = eligible & (proposed != assigned)
        assigned[changed] = proposed[changed]
        treated[changed] = True
    elif arm != "no_correction":
        raise ValueError(f"Unknown treatment arm: {arm}")
    return changed


def learner_config(protocol: dict[str, Any]) -> dict[str, Any]:
    """Restrict learner inputs; corruption settings and hidden truth stay outside."""
    keys = ("classes", "arms", "boosting_rounds", "model_parameters", "treatment")
    return {key: protocol[key] for key in keys}


def fit_treatment(X: np.ndarray, observed_labels: np.ndarray, *, arm: str,
                  seed: int, config: dict[str, Any]):
    """Fit with observed training labels only; calibration/test are not arguments."""
    import xgboost as xgb

    allowed = {"classes", "arms", "boosting_rounds", "model_parameters", "treatment"}
    if set(config) != allowed:
        raise ValueError("Learner config must contain only declared model/treatment settings.")
    if arm not in config["arms"]:
        raise ValueError("Arm is absent from the frozen protocol.")
    assigned = np.asarray(observed_labels, dtype=np.int64).copy()
    if X.ndim != 2 or X.shape[0] != len(assigned) or len(assigned) == 0:
        raise ValueError("Nonempty aligned training arrays are required.")
    n_classes = len(config["classes"])
    if np.any((assigned < 0) | (assigned >= n_classes)):
        raise ValueError("Observed labels are outside the frozen class set.")
    active = np.ones(len(assigned), dtype=bool)
    treated = np.zeros(len(assigned), dtype=bool)
    ever_candidate = np.zeros(len(assigned), dtype=bool)
    settings = config["treatment"]
    history = deque(maxlen=settings["history_rounds"])
    all_matrix = xgb.DMatrix(X, label=assigned)
    training_matrix = all_matrix
    params = dict(config["model_parameters"], seed=seed)
    params["num_class"] = n_classes
    model = xgb.Booster(params=params, cache=[all_matrix])
    trace = []
    started = time.perf_counter()
    for iteration in range(config["boosting_rounds"]):
        model.update(training_matrix, iteration)
        round_number = iteration + 1
        if arm == "no_correction":
            continue
        history.append(model.predict(all_matrix))
        scheduled = (round_number >= settings["warmup_rounds"] and
                     (round_number - settings["warmup_rounds"]) % settings["intervention_every_rounds"] == 0 and
                     round_number < config["boosting_rounds"])
        if not scheduled:
            continue
        statistic = gradient_statistic(list(history), assigned)
        candidates = identify_candidates(statistic, active, treated, seed, settings)
        ever_candidate |= candidates
        changed = apply_treatment(arm, candidates, statistic, np.mean(history, axis=0),
                                  assigned, active, treated, settings["removal_cap_fraction"])
        trace.append({"after_round": round_number, "candidates": int(candidates.sum()),
                      "changed": int(changed.sum()), "active_count": int(active.sum()),
                      "treated_count": int(treated.sum())})
        if changed.any():
            training_matrix = xgb.DMatrix(X[active], label=assigned[active])
        history.clear()
    return model, {"assigned_labels": assigned, "active": active, "treated": treated,
                   "ever_candidate": ever_candidate, "trace": trace,
                   "fit_seconds": time.perf_counter() - started}


def classification_metrics(y_true: np.ndarray, probabilities: np.ndarray,
                           classes: list[str]) -> dict[str, Any]:
    predicted = np.argmax(probabilities, axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, predicted, labels=np.arange(len(classes)), zero_division=0)
    stages = {}
    for index, label in enumerate(classes):
        binary = y_true == index
        supported = 0 < int(binary.sum()) < len(binary)
        stages[label] = {"precision": float(precision[index]), "recall": float(recall[index]),
                         "f1": float(f1[index]), "support": int(support[index]),
                         "roc_auc": float(roc_auc_score(binary, probabilities[:, index])) if supported else None,
                         "average_precision": float(average_precision_score(binary, probabilities[:, index])) if supported else None}
    return {"macro_f1": float(np.mean(f1)), "accuracy": float(np.mean(predicted == y_true)),
            "count": int(len(y_true)), "per_stage": stages,
            "confusion_matrix": confusion_matrix(y_true, predicted, labels=np.arange(len(classes))).tolist()}


def mask_metrics(selected: np.ndarray, hidden_noisy: np.ndarray) -> dict[str, Any]:
    detected = int(np.count_nonzero(selected & hidden_noisy))
    count = int(selected.sum())
    noisy_count = int(hidden_noisy.sum())
    return {"selected": count, "truly_noisy_selected": detected,
            "clean_selected": int(np.count_nonzero(selected & (~hidden_noisy))),
            "precision": detected / count if count else None,
            "recall": detected / noisy_count if noisy_count else None}


def posthoc_treatment_metrics(clean_labels: np.ndarray, noisy_labels: np.ndarray,
                             state: dict[str, Any], classes: list[str]) -> dict[str, Any]:
    hidden_noisy = clean_labels != noisy_labels
    clean = ~hidden_noisy
    final_labels, active, treated = state["assigned_labels"], state["active"], state["treated"]
    damaged = clean & ((~active) | (final_labels != clean_labels))
    repaired = hidden_noisy & active & (final_labels == clean_labels)
    per_stage = {}
    for index, label in enumerate(classes):
        known_clean = clean & (clean_labels == index)
        denominator = int(known_clean.sum())
        per_stage[label] = {"original_count": int(np.count_nonzero(clean_labels == index)),
                            "originally_clean_count": denominator,
                            "originally_clean_removed_or_mislabeled": int(np.count_nonzero(known_clean & damaged)),
                            "clean_damage_fraction": int(np.count_nonzero(known_clean & damaged)) / denominator if denominator else None}
    return {"injected_noise_count": int(hidden_noisy.sum()),
            "injected_noise_fraction": float(hidden_noisy.mean()),
            "candidate_detection": mask_metrics(state["ever_candidate"], hidden_noisy),
            "actual_treatment": mask_metrics(treated, hidden_noisy),
            "originally_clean_removed_or_mislabeled": int(damaged.sum()),
            "noisy_labels_corrected_and_retained": int(repaired.sum()),
            "noisy_examples_removed": int(np.count_nonzero(hidden_noisy & (~active))),
            "retained_incorrect_labels": int(np.count_nonzero(active & (final_labels != clean_labels))),
            "per_stage": per_stage}


def summarize(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    expected = {(seed, rate, arm) for seed in protocol["seeds"] for rate in protocol["noise_rates"] for arm in protocol["arms"]}
    by_key = {(row["seed"], row["noise_rate"], row["arm"]): row for row in rows}
    if len(by_key) != len(rows) or set(by_key) != expected:
        raise ValueError("Results do not match the complete prespecified run grid.")
    screens = {}
    rare = protocol["rare_stage"]
    primary = protocol["primary_noise_rate"]
    for arm in protocol["arms"]:
        if arm == "no_correction":
            continue
        deltas = []
        for seed in protocol["seeds"]:
            baseline_clean = by_key[(seed, 0.0, "no_correction")]["test"]
            baseline_noisy = by_key[(seed, primary, "no_correction")]["test"]
            arm_clean, arm_noisy = by_key[(seed, 0.0, arm)]["test"], by_key[(seed, primary, arm)]["test"]
            deltas.append({"seed": seed,
                           "noisy_macro_f1_delta": arm_noisy["macro_f1"] - baseline_noisy["macro_f1"],
                           "clean_macro_f1_delta": arm_clean["macro_f1"] - baseline_clean["macro_f1"],
                           "clean_rare_stage_recall_delta": arm_clean["per_stage"][rare]["recall"] - baseline_clean["per_stage"][rare]["recall"],
                           "noisy_rare_stage_recall_delta": arm_noisy["per_stage"][rare]["recall"] - baseline_noisy["per_stage"][rare]["recall"]})
        means = {key: float(np.mean([row[key] for row in deltas])) for key in deltas[0] if key != "seed"}
        guards = {"noisy_macro_f1_recovery": means["noisy_macro_f1_delta"] >= protocol["screen"]["noisy_macro_f1_gain_min"],
                  "clean_macro_f1_preserved": means["clean_macro_f1_delta"] >= protocol["screen"]["clean_macro_f1_delta_min"],
                  "clean_rare_recall_preserved": means["clean_rare_stage_recall_delta"] >= protocol["screen"]["clean_rare_stage_recall_delta_min"],
                  "noisy_rare_recall_preserved": means["noisy_rare_stage_recall_delta"] >= protocol["screen"]["noisy_rare_stage_recall_delta_min"]}
        screens[arm] = {"paired_seed_deltas": deltas, "mean_deltas": means, "guards": guards,
                        "all_gates_pass": all(guards.values())}
    return {"screen_status": "PROMISING_DEVELOPMENT_ONLY" if any(item["all_gates_pass"] for item in screens.values()) else "NEGATIVE_DEVELOPMENT",
            "run_count": len(rows), "screens": screens,
            "interpretation": "Three seeds on one exposed development split; no confidence interval, significance, independent-campaign, original-algorithm, or novelty claim."}


def prepare_receipt(prepared: Path, protocol_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, np.ndarray]]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest_path, data_path = prepared / "MANIFEST.json", prepared / "DATA.npz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_hash = sha256(data_path)
    if data_hash != protocol["dataset_npz_sha256"] or data_hash != manifest["data_npz_sha256"]:
        raise ValueError("Data checksum differs from the frozen protocol/manifest.")
    with np.load(data_path, allow_pickle=False) as source:
        data = {key: source[key] for key in source.files}
    classes = data["classes"].tolist()
    if classes != protocol["classes"] or classes != manifest["classes"]:
        raise ValueError("Frozen class order differs from prepared inputs.")
    X, y, split, groups = data["X"], data["y"], data["split"], data["group_sha256"]
    if X.ndim != 2 or any(len(value) != len(X) for value in (y, split, groups)):
        raise ValueError("Prepared input arrays are not aligned.")
    if not np.isin(split, [0, 1, 2]).all() or np.any((y < 0) | (y >= len(classes))):
        raise ValueError("Prepared split or label codes are invalid.")
    if len(set(groups.tolist())) != len(groups):
        raise ValueError("Exact feature groups repeat in the prepared roster.")
    finite = X[np.isfinite(X)]
    if np.isinf(X).any() or (len(finite) and np.max(np.abs(finite)) > np.finfo(np.float32).max):
        raise ValueError("Prepared features cannot be represented by XGBoost; no silent clipping permitted.")
    versions = {package: importlib.metadata.version(package) for package in ("xgboost", "numpy", "scikit-learn", "scipy")}
    if versions["xgboost"] != protocol["xgboost_version"]:
        raise ValueError("XGBoost version differs from the frozen protocol.")
    selections = []
    for seed in protocol["seeds"]:
        indices = select_fit_indices(y, split, groups, protocol["fit_per_class_cap"], seed, len(classes))
        selections.append({"seed": seed, "count": len(indices), "indices_sha256": array_digest(indices),
                           "group_sha256": array_digest(groups[indices]),
                           "class_counts": {label: int(np.count_nonzero(y[indices] == index)) for index, label in enumerate(classes)}})
    receipt = {"schema_version": 1, "protocol_sha256": sha256(protocol_path),
               "runner_sha256": sha256(Path(__file__)), "data_npz_sha256": data_hash,
               "manifest_sha256": sha256(manifest_path), "versions": versions,
               "selections": selections, "test_count": int(np.count_nonzero(split == 2)),
               "calibration_count_unused": int(np.count_nonzero(split == 1)),
               "test_indices_sha256": array_digest(np.flatnonzero(split == 2)),
               "fits_started": False}
    return receipt, protocol, data


def run(prepared: Path, output: Path, protocol_path: Path, *, freeze_only: bool) -> dict[str, Any]:
    receipt, protocol, data = prepare_receipt(prepared, protocol_path)
    receipt_path = output / "PRE_FIT_RECEIPT.json"
    if freeze_only:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError("Freeze output already exists; choose a fresh output directory.")
        output.mkdir(parents=True, exist_ok=True)
        write_json(receipt_path, dict(receipt, created_at_utc=datetime.now(timezone.utc).isoformat()))
        write_json(output / "PROTOCOL.json", protocol)
        return {"status": "FROZEN_NO_FITS", "receipt": str(receipt_path), "planned_runs": len(protocol["seeds"]) * len(protocol["noise_rates"]) * len(protocol["arms"])}
    if not receipt_path.exists():
        raise RuntimeError("Run --freeze-only first; fitting requires a matching pre-fit receipt.")
    frozen = json.loads(receipt_path.read_text(encoding="utf-8"))
    frozen.pop("created_at_utc", None)
    if frozen != receipt:
        raise RuntimeError("Source/protocol/data/environment changed since freezing. Use a new amended output.")
    if (output / "RUN_STARTED.json").exists():
        raise FileExistsError("This frozen run was already started; do not overwrite its evidence.")
    import xgboost as xgb
    write_json(output / "RUN_STARTED.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(), "receipt_sha256": sha256(receipt_path)})
    predictions = output / "predictions"
    models = output / "models"
    predictions.mkdir()
    models.mkdir()
    classes = protocol["classes"]
    X, y, split, groups = data["X"], data["y"], data["split"], data["group_sha256"]
    test_indices = np.flatnonzero(split == 2)
    test_matrix = xgb.DMatrix(X[test_indices])
    rows = []
    for seed in protocol["seeds"]:
        indices = select_fit_indices(y, split, groups, protocol["fit_per_class_cap"], seed, len(classes))
        for rate in protocol["noise_rates"]:
            noisy, hidden_mask = inject_symmetric_noise(y[indices], rate, len(classes), seed)
            for arm in protocol["arms"]:
                key = f"seed_{seed}_noise_{round(rate * 100):02d}_{arm}"
                model, state = fit_treatment(X[indices], noisy, arm=arm, seed=seed, config=learner_config(protocol))
                probabilities = model.predict(test_matrix)
                posthoc = posthoc_treatment_metrics(y[indices], noisy, state, classes)
                prediction_path, model_path = predictions / f"{key}.npz", models / f"{key}.json"
                np.savez_compressed(prediction_path, probabilities=probabilities, y_test=y[test_indices],
                                    test_indices=test_indices, fit_indices=indices, clean_fit_labels=y[indices],
                                    noisy_fit_labels=noisy, hidden_noise_mask=hidden_mask,
                                    assigned_fit_labels=state["assigned_labels"], active_fit_mask=state["active"],
                                    treated_fit_mask=state["treated"], candidate_fit_mask=state["ever_candidate"])
                model.save_model(model_path)
                row = {"seed": seed, "noise_rate": rate, "arm": arm, "fit_count": len(indices),
                       "fit_seconds": state["fit_seconds"], "test": classification_metrics(y[test_indices], probabilities, classes),
                       "treatment_audit": posthoc, "treatment_trace": state["trace"],
                       "prediction_file": str(prediction_path.relative_to(output)), "prediction_sha256": sha256(prediction_path),
                       "model_file": str(model_path.relative_to(output)), "model_sha256": sha256(model_path)}
                rows.append(row)
                write_json(output / "RESULTS.partial.json", rows)
                print(json.dumps({"completed": len(rows), "key": key, "macro_f1": row["test"]["macro_f1"], "fit_seconds": row["fit_seconds"]}), flush=True)
    summary = summarize(rows, protocol)
    write_json(output / "RESULTS.json", {"protocol": protocol, "rows": rows, "summary": summary})
    write_json(output / "SUMMARY.json", summary)
    lines = ["# Label-noise treatment development pilot", "", "**" + summary["screen_status"] + "**", "",
             "This tests an explicitly documented history-gradient GMM adaptation, not a reproduction of the original Gradients algorithm.", "",
             "| Arm | Noise | Mean macro-F1 | Mean InitialCompromise recall |", "|---|---:|---:|---:|"]
    for arm in protocol["arms"]:
        for rate in protocol["noise_rates"]:
            selected = [row for row in rows if row["arm"] == arm and row["noise_rate"] == rate]
            lines.append(f"| {arm} | {rate:.0%} | {np.mean([row['test']['macro_f1'] for row in selected]):.4f} | {np.mean([row['test']['per_stage'][protocol['rare_stage']]['recall'] for row in selected]):.4f} |")
    lines.extend(["", "## Gates", ""])
    for arm, screen in summary["screens"].items():
        lines.append(f"- {arm}: {'PASS' if screen['all_gates_pass'] else 'FAIL'}; " + ", ".join(f"{key}={value:+.4f}" for key, value in screen["mean_deltas"].items()))
    lines.extend(["", "## Limits", ""] + ["- " + value for value in protocol["limitations"]] + ["", summary["interpretation"], ""])
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(output / "RUN_COMPLETE.json", {"finished_at_utc": datetime.now(timezone.utc).isoformat(), "run_count": len(rows), "results_sha256": sha256(output / "RESULTS.json")})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.prepared, args.output, args.protocol, freeze_only=args.freeze_only), indent=2, allow_nan=False))
