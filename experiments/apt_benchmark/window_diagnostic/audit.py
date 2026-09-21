"""Independent calculation and evidence-binding audit; never trains models.

This module deliberately imports no runner or feature-selection/metric helper.
It recomputes selections, AP/AUC, metrics and gates from stored row-level scores.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits


def sha256_file(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def ids_hash(rows):
    return hashlib.sha256(json.dumps([r["window_id"] for r in rows],
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compare(actual, expected, path="value"):
    """Strict structural comparison with a small numeric arithmetic tolerance."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f"{path}: keys differ")
        for key in expected:
            compare(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, (list, tuple)):
        require(isinstance(actual, (list, tuple)) and len(actual) == len(expected), f"{path}: length differs")
        for index, value in enumerate(expected):
            compare(actual[index], value, f"{path}[{index}]")
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        require(type(actual) is type(expected) and actual == expected, f"{path}: differs")
    elif isinstance(expected, (int, float, np.number)):
        require(isinstance(actual, (int, float, np.number)) and not isinstance(actual, bool)
                and math.isfinite(float(actual)) and math.isclose(float(actual), float(expected),
                    rel_tol=1e-10, abs_tol=1e-12), f"{path}: {actual!r} != {expected!r}")
    else:
        require(actual == expected, f"{path}: differs")


def select(rows, scores, fraction, known_only=False):
    """Group indices once; labels affect only explicitly conditional selection."""
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        if not known_only or row["label"] != -1:
            groups[row["run_id"]].append(index)
    chosen = np.zeros(len(rows), dtype=bool)
    for indices in groups.values():
        budget = math.ceil(len(indices) * fraction)
        keys = [(float(scores[i]), hashlib.sha256(
            ("window-diagnostic-v1:" + rows[i]["window_id"]).encode("utf-8")).hexdigest(), i)
            for i in indices]
        keys.sort(key=lambda item: (-item[0], item[1]))
        for _, _, index in keys[:budget]:
            chosen[index] = True
    return chosen


def ranking_metrics(labels, scores):
    """Threshold-group AP and pair-count ROC-AUC, including exact-score ties."""
    positives = sum(int(label == 1) for label in labels)
    negatives = sum(int(label == 0) for label in labels)
    if not positives or not negatives:
        return None, None
    groups = defaultdict(lambda: [0, 0])
    for label, score in zip(labels, scores):
        groups[float(score)][0 if label == 1 else 1] += 1
    seen_pos = seen_neg = 0
    average_precision = 0.0
    for score in sorted(groups, reverse=True):
        group_pos, group_neg = groups[score]
        seen_pos += group_pos
        seen_neg += group_neg
        average_precision += group_pos / positives * seen_pos / (seen_pos + seen_neg)
    below_negative = 0
    favorable_pairs = 0.0
    for score in sorted(groups):
        group_pos, group_neg = groups[score]
        favorable_pairs += group_pos * (below_negative + group_neg / 2)
        below_negative += group_neg
    return average_precision, favorable_pairs / (positives * negatives)


def metrics(rows, scores, fraction):
    selected = select(rows, scores, fraction)
    conditional = select(rows, scores, fraction, known_only=True)
    total = {label: sum(row["label"] == label for row in rows) for label in (-1, 0, 1)}
    picked = {label: sum(bool(selected[i]) and row["label"] == label for i, row in enumerate(rows))
              for label in (-1, 0, 1)}
    budget = sum(picked.values())
    run_counts = defaultdict(lambda: [0, 0])
    for row in rows:
        run_counts[row["run_id"]][0] += 1
        run_counts[row["run_id"]][1] += row["label"] == 1
    expected = sum(pos * math.ceil(fraction * count) / count for count, pos in run_counts.values())
    known = [i for i, row in enumerate(rows) if row["label"] >= 0]
    ap, auc = ranking_metrics([rows[i]["label"] for i in known], [scores[i] for i in known])
    ktp = sum(bool(conditional[i]) and row["label"] == 1 for i, row in enumerate(rows))
    kfp = sum(bool(conditional[i]) and row["label"] == 0 for i, row in enumerate(rows))
    kfn = total[1] - ktp
    all_steps = set()
    picked_steps = set()
    for index, row in enumerate(rows):
        all_steps.update(row["positive_source_step_ids"])
        if selected[index]:
            picked_steps.update(row["positive_source_step_ids"])
    return {
        "windows": len(rows), "positive": total[1], "other_annotated": total[0], "unknown": total[-1],
        "reviewed": budget, "selected_target": picked[1], "selected_other": picked[0],
        "selected_unknown": picked[-1], "recall": picked[1] / total[1] if total[1] else None,
        "chance_recall": expected / total[1] if total[1] else None,
        "confirmed_positive_yield_lower_bound": picked[1] / budget if budget else 0.0,
        "possible_positive_yield_upper_bound": (picked[1] + picked[-1]) / budget if budget else 0.0,
        "unknown_selected_fraction": picked[-1] / budget if budget else 0.0,
        "known_average_precision": ap, "known_roc_auc": auc,
        "known_prevalence": total[1] / len(known) if known else None,
        "known_only_budget": {"reviewed": ktp + kfp, "tp": ktp, "fp": kfp, "fn": kfn,
            "precision": ktp / (ktp + kfp) if ktp + kfp else 0.0,
            "recall": ktp / total[1] if total[1] else 0.0,
            "f1": 2 * ktp / (2 * ktp + kfp + kfn) if 2 * ktp + kfp + kfn else 0.0},
        "represented_source_intervals": len(all_steps), "source_intervals_touched_by_review": len(picked_steps),
        "source_interval_touch_recall": len(picked_steps) / len(all_steps) if all_steps else None,
    }


def gates(family_metrics, protocol):
    spec = protocol["gates"]
    families = protocol["families"]
    primary = spec["primary_arm"]
    def values(arm, condition, field="recall"):
        return [family_metrics[arm, condition, family][field] for family in families]
    def mean(items):
        return sum(items) / len(items)
    clean = values(primary, "clean")
    chance = values(primary, "clean", "chance_recall")
    differences = [a - b for a, b in zip(clean, values(spec["pooling_benefit"]["comparator"], "clean"))]
    above = sum(a > b for a, b in zip(clean, chance))
    clean_mean, chance_mean = mean(clean), mean(chance)
    useful = spec["clean_useful_signal"]
    pooled = spec["pooling_benefit"]
    simple = clean_mean - mean(values(spec["simple_control_value"]["comparator"], "clean"))
    loss = clean_mean - mean(values(primary, "command_absent"))
    result = {
        "clean_useful_signal": {"passed": clean_mean >= useful["macro_recall_min"]
            and clean_mean >= useful["chance_multiplier_min"] * chance_mean
            and above >= useful["families_above_chance_min"],
            "macro_recall": clean_mean, "macro_chance_recall": chance_mean, "families_above_chance": above},
        "pooling_benefit": {"passed": mean(differences) >= pooled["macro_recall_delta_min"]
            and sum(value > 0 for value in differences) >= pooled["families_improved_min"]
            and min(differences) >= pooled["worst_family_delta_min"],
            "macro_delta": mean(differences), "families_improved": sum(value > 0 for value in differences),
            "worst_family_delta": min(differences)},
        "simple_control_value": {"passed": simple >= spec["simple_control_value"]["macro_recall_delta_min"],
                                 "macro_delta": simple},
        "loss_gap": {"present": loss >= spec["loss_gap"]["clean_minus_command_absent_macro_recall_min"],
                     "macro_clean_minus_loss_recall": loss},
        "activity_count_clean_recall_delta": clean_mean - mean(values("activity_count", "clean")),
        "novel_method_validated": False,
    }
    if not result["clean_useful_signal"]["passed"]:
        result["decision"] = "RETIRE_PRIMARY_POOLED_LR_FORMULATION; inspect secondary controls as disclosed developmental diagnostics only"
    elif result["loss_gap"]["present"]:
        result["decision"] = "CLEAN_SIGNAL_WITH_LOSS_GAP; qualify surviving additional sources before a new recovery experiment"
    else:
        result["decision"] = "CLEAN_SIGNAL_WITHOUT_LARGE_COMMAND_LOSS_GAP; no demonstrated need for a recovery mechanism under this stress"
    return result


def audit(cache, run_dir, protocol_path, output):
    cache, run_dir, protocol_path, output = map(Path, (cache, run_dir, protocol_path, output))
    require(not output.exists(), "Immutable audit output already exists")
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    protocol = read(protocol_path)
    receipt = read(run_dir / "PRE_FIT_RECEIPT.json")
    result = read(run_dir / "RESULTS.json")
    manifest = read(cache / "MANIFEST.json")
    rows = read(run_dir / "metadata.json")
    compare(read(run_dir / "PROTOCOL.json"), protocol, "protocol_copy")
    compare(read(run_dir / "FEATURE_MANIFEST.json"), manifest, "manifest_copy")
    require(sha256_file(run_dir / "metadata.json") == sha256_file(cache / "metadata.json"), "Metadata changed")
    p_hash = sha256_file(protocol_path)
    require(receipt["protocol_sha256"] == result["protocol_sha256"] == manifest["protocol_sha256"] == p_hash,
            "Protocol binding mismatch")
    require(receipt["frozen_before_fit"] is True and receipt["models_fit"] == 0 and receipt["development_only"] is True,
            "Missing pre-fit declaration")
    require(datetime.fromisoformat(receipt["created_utc"]) <= datetime.fromisoformat(result["created_utc"]),
            "Receipt postdates result")
    require(sha256_file(run_dir / "PRE_FIT_RECEIPT.json") == result["pre_fit_receipt_sha256"], "Receipt hash mismatch")
    require(sha256_file(cache / "MANIFEST.json") == receipt["feature_manifest_sha256"], "Cache manifest hash mismatch")
    require(sha256_file(run_dir / "predictions.npz") == result["predictions_sha256"], "Predictions hash mismatch")
    repo = Path(__file__).resolve().parents[3]
    for filename, expected in receipt["code_sha256"].items():
        require(sha256_file(repo / filename) == expected, f"Pre-fit code changed: {filename}")
    for filename, expected in manifest["code_sha256"].items():
        source = Path(__file__).with_name(filename) if "/" not in filename else Path(__file__).parents[1] / filename
        require(sha256_file(source) == expected, f"Feature code changed: {filename}")
    for filename, artifact in manifest["artifacts"].items():
        require(sha256_file(cache / filename) == artifact["sha256"], f"Manifest artifact changed: {filename}")
        require((cache / filename).stat().st_size == artifact["bytes"], f"Artifact size changed: {filename}")
    for filename, expected in receipt["cache_artifact_sha256"].items():
        require(sha256_file(cache / filename) == expected, f"Pre-fit cache changed: {filename}")
        require(manifest["artifacts"][filename]["sha256"] == expected, f"Unbound cache: {filename}")
    require(len({row["window_id"] for row in rows}) == len(rows), "Duplicate windows")
    require(sorted({row["family"] for row in rows}) == protocol["families"], "Family roster mismatch")
    require(all(row["label"] in (-1, 0, 1) for row in rows), "Invalid labels")
    for row in rows:
        require(row["end"] - row["start"] == protocol["window_seconds"], "Window width mismatch")
        require(row["start"] % protocol["window_seconds"] == 0, "Window is not UTC-grid aligned")
        require(bool(row["positive_source_step_ids"]) == (row["label"] == 1), "Target ID/label mismatch")
    predictions = np.load(run_dir / "predictions.npz", allow_pickle=False)
    require(np.array_equal(predictions["label"], [row["label"] for row in rows]), "Prediction labels mismatch")
    require(np.array_equal(predictions["family"], [row["family"] for row in rows]), "Prediction families mismatch")
    expected_keys = {"label", "family"}
    family_metrics = {}
    expected_families = []
    expected_runs = []
    expected_macro = []
    for arm in protocol["arms"]:
        for condition in protocol["conditions"]:
            key = f"{arm}__{condition}"
            expected_keys.update((key, key + "__selected"))
            scores = predictions[key]
            require(scores.shape == (len(rows),) and np.isfinite(scores).all(), f"Invalid scores: {key}")
            chosen = select(rows, scores, protocol["review_fraction"])
            require(np.array_equal(chosen, predictions[key + "__selected"]), f"Review selection mismatch: {key}")
            for family in protocol["families"]:
                indices = [i for i, row in enumerate(rows) if row["family"] == family]
                value = metrics([rows[i] for i in indices], scores[indices], protocol["review_fraction"])
                family_metrics[arm, condition, family] = value
                expected_families.append({"arm": arm, "condition": condition, "family": family, "metrics": value})
            for run in sorted({row["run_id"] for row in rows}):
                indices = [i for i, row in enumerate(rows) if row["run_id"] == run]
                expected_runs.append({"arm": arm, "condition": condition, "run_id": run,
                    "family": rows[indices[0]]["family"],
                    "metrics": metrics([rows[i] for i in indices], scores[indices], protocol["review_fraction"])})
            macro_keys = ("recall", "chance_recall", "confirmed_positive_yield_lower_bound", "unknown_selected_fraction",
                          "known_average_precision", "known_roc_auc", "known_prevalence", "source_interval_touch_recall")
            values = [family_metrics[arm, condition, family] for family in protocol["families"]]
            expected_macro.append({"arm": arm, "condition": condition,
                **{name: sum(value[name] for value in values) / len(values) for name in macro_keys},
                "known_only_f1": sum(value["known_only_budget"]["f1"] for value in values) / len(values)})
    require(set(predictions.files) == expected_keys, "Unexpected prediction archive keys")
    compare(result["family_results"], expected_families, "family_results")
    compare(result["run_results"], expected_runs, "run_results")
    compare(result["macro_family_results"], expected_macro, "macro_family_results")
    compare(result["gates"], gates(family_metrics, protocol), "gates")
    require(result["family_condition_arm_rows"] == len(expected_families), "Result-row count mismatch")
    require(result["novel_method_validated"] is False and result["independent_confirmation"] is False,
            "Unsupported confirmation claim")

    matrices = {(view, condition): sparse.load_npz(cache / f"{view}_{condition}.npz")
                for view in ("first", "pooled") for condition in protocol["conditions"]}
    checked_models = set()
    model_hashes = {}
    for fit in result["fits"]:
        family, arm = fit["heldout_family"], fit["arm"]
        require((family, arm) not in checked_models, "Duplicate model fit")
        checked_models.add((family, arm))
        train_indices = [i for i, row in enumerate(rows) if row["family"] != family and row["label"] >= 0]
        test_indices = [i for i, row in enumerate(rows) if row["family"] == family]
        train_rows = [rows[i] for i in train_indices]
        test_rows = [rows[i] for i in test_indices]
        compare(fit["train_windows"], len(train_rows), "train_windows")
        compare(fit["train_positive"], sum(row["label"] == 1 for row in train_rows), "train_positive")
        compare(fit["test_windows"], len(test_rows), "test_windows")
        compare(fit["train_families"], sorted({row["family"] for row in train_rows}), "train_families")
        require(set(row["label"] for row in train_rows) == {0, 1}, "Unsupported training fold")
        require(fit["train_window_ids_sha256"] == ids_hash(train_rows), "Training roster hash mismatch")
        require(fit["test_window_ids_sha256"] == ids_hash(test_rows), "Heldout roster hash mismatch")
        model_path = run_dir / f"model_{family}_{arm}.joblib"
        model_hashes[model_path.name] = sha256_file(model_path)
        require(fit["model_sha256"] == model_hashes[model_path.name], "Saved model hash mismatch")
        model = joblib.load(model_path)
        spec = protocol["extra_trees"] if arm == "pooled_extra_trees" else protocol["logistic_regression"]
        parameters = model.get_params()
        for name, value in spec.items():
            compare(parameters[name], value, f"model_parameter.{name}")
        require(list(model.classes_) == [0, 1], "Model classes mismatch")
        view = "first" if arm == "first_lr" else "pooled"
        for condition in protocol["conditions"]:
            with threadpool_limits(limits=2):
                reproduced = model.predict_proba(matrices[view, condition][test_indices])[:, 1]
            require(np.allclose(reproduced, predictions[f"{arm}__{condition}"][test_indices],
                                rtol=1e-10, atol=1e-12), "Saved-model predictions do not reproduce")
    wanted_models = {(family, arm) for family in protocol["families"]
                     for arm in ("first_lr", "pooled_lr", "pooled_extra_trees")}
    require(checked_models == wanted_models and result["models_fit"] == len(wanted_models), "Model roster mismatch")
    for condition in protocol["conditions"]:
        require(np.array_equal(predictions[f"transfer_rule__{condition}"], np.load(cache / f"rules_{condition}.npy")),
                "Transfer rule predictions differ from frozen features")
        require(np.array_equal(predictions[f"activity_count__{condition}"],
                    matrices["pooled", condition][:, protocol["features"]["hash_dimensions"]].toarray().ravel()),
                "Activity ranking scores differ from observed counts")
    report = {"status": "PASS", "created_utc": datetime.now(timezone.utc).isoformat(),
        "audit_code_sha256": sha256_file(__file__), "protocol_sha256": p_hash,
        "results_sha256": sha256_file(run_dir / "RESULTS.json"),
        "pre_fit_receipt_sha256": sha256_file(run_dir / "PRE_FIT_RECEIPT.json"),
        "predictions_sha256": sha256_file(run_dir / "predictions.npz"),
        "feature_manifest_sha256": sha256_file(cache / "MANIFEST.json"),
        "windows": len(rows), "family_result_rows_checked": len(expected_families),
        "run_result_rows_checked": len(expected_runs), "selection_masks_checked": len(protocol["arms"]) * len(protocol["conditions"]),
        "saved_models_checked": len(checked_models), "model_sha256": model_hashes,
        "checks": ["Independent full-grid and conditional selections including ties and per-run rounding",
                   "Independent AP/AUC, confusion counts, unknown-selection bounds, interval touches and macro averages",
                   "All primary gates independently recomputed",
                   "Protocol, feature cache, code, receipt and model hash bindings",
                   "Family-disjoint declared fit rosters and saved-model prediction reproduction without refitting"],
        "limitations": ["AI/code audit, not human source-label adjudication",
                        "Model receipts and code bind declared training rosters; this is not an external execution attestation",
                        "Raw source events are bound through the preparation manifest; this audit does not reread the entire source",
                        "PASS is calculation integrity, not a positive experimental outcome"],
        "gates": result["gates"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "windows", "family_result_rows_checked",
                                                  "run_result_rows_checked", "saved_models_checked")}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.cache, args.run, args.protocol, args.output)
