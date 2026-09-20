"""Post-hoc aggregate diagnosis of frozen scores; no model or threshold changes.

Private arrays are read locally and SHA-256 checked against the completed run's
inventory. Only aggregate counts, score distributions, and hashes are exported.
No operative model, scorer, configuration, or original result is modified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np


SCOPE = "POSTHOC_EXPLORATORY_NO_THRESHOLD_CHANGES"
QUANTILES = (0., .01, .1, .25, .5, .75, .9, .95, .99, 1.)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score_summary(scores, top=5):
    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all():
        raise ValueError("Score summaries require finite, nonempty one-dimensional scores")
    values, counts = np.unique(scores, return_counts=True)
    # Ties in frequency are ordered by numeric score, never favorable performance.
    order = np.lexsort((values, -counts))[:top]
    return {"n": int(len(scores)), "unique_scores": int(len(values)),
            "exact_zero_scores": int(np.sum(scores == 0)),
            "quantiles": {str(q): float(v) for q, v in zip(QUANTILES, np.quantile(scores, QUANTILES))},
            "largest_exact_score_ties": [
                {"score": float(values[i]), "count": int(counts[i]),
                 "fraction": float(counts[i] / len(scores))} for i in order]}


def confusion(y, selected):
    return {"tp": int(np.sum((y == 1) & selected)),
            "fp": int(np.sum((y == 0) & selected)),
            "tn": int(np.sum((y == 0) & ~selected)),
            "fn": int(np.sum((y == 1) & ~selected))}


def diagnostic_counts(y, degree, mlp_margin, gin_margin, gate_margin, minimum_degree):
    if (y.ndim != 1 or not len(y) or set(np.unique(y)) != {0, 1}
            or any(np.asarray(value).shape != y.shape for value in (degree, mlp_margin, gin_margin, gate_margin))):
        raise ValueError("Aligned binary labels, degree, and margin arrays required")
    if not all(np.isfinite(value).all() for value in (degree, mlp_margin, gin_margin, gate_margin)):
        raise ValueError("Nonfinite diagnostic input")
    if np.any(degree < 0) or np.any(degree != np.floor(degree)):
        raise ValueError("Degree must count nonnegative retained relationships")
    low = degree < minimum_degree
    expected = np.where(low, mlp_margin, gin_margin)
    if not np.array_equal(expected, gate_margin):
        raise ValueError("Stored checker does not match the frozen degree rule")
    attack = y == 1
    mlp, gin, gate = mlp_margin >= 0, gin_margin >= 0, gate_margin >= 0
    lost, gained = attack & gin & ~gate, attack & ~gin & gate
    if np.any(lost & ~low) or np.any(gained & ~low):
        raise ValueError("Degree checker altered a high-degree GIN decision")
    return {
        "entities": int(len(y)), "annotated_malicious_entities": int(attack.sum()),
        "unannotated_test_negative_entities": int((~attack).sum()),
        "low_degree_threshold_exclusive": int(minimum_degree),
        "low_degree_entities": int(low.sum()),
        "low_degree_malicious_entities": int((low & attack).sum()),
        "gin_detected_low_degree_malicious_entities": int((low & attack & gin).sum()),
        "mlp_detected_low_degree_malicious_entities": int((low & attack & mlp).sum()),
        "checker_detected_low_degree_malicious_entities": int((low & attack & gate).sum()),
        "checker_loses_gin_true_positives": int(lost.sum()),
        "checker_loses_gin_true_positives_low_degree": int((lost & low).sum()),
        "checker_gains_gin_missed_malicious_entities": int(gained.sum()),
        "checker_removes_gin_negative_label_alerts": int(((~attack) & gin & ~gate).sum()),
        "checker_adds_gin_negative_label_alerts": int(((~attack) & ~gin & gate).sum()),
        "mlp_gin_complementarity": {
            "both_detected_malicious_entities": int((attack & mlp & gin).sum()),
            "mlp_only_malicious_entities": int((attack & mlp & ~gin).sum()),
            "gin_only_malicious_entities": int((attack & ~mlp & gin).sum()),
            "union_malicious_entities": int((attack & (mlp | gin)).sum()),
            "neither_detected_malicious_entities": int((attack & ~mlp & ~gin).sum())},
        "frozen_operating_point": {arm: confusion(y, values) for arm, values in
                                   (("mlp_knn", mlp), ("gin_knn", gin), ("quality_gate", gate))}}


def query_shape_summary(path):
    result = {}
    with np.load(path, allow_pickle=False) as arrays:
        for arm in ("local_knn", "mlp_knn", "gin_knn"):
            unique, inverse = arrays[arm + "_unique"], arrays[arm + "_inverse"]
            if (unique.ndim != 2 or inverse.ndim != 1 or not len(unique)
                    or inverse.dtype.kind not in "iu" or not len(inverse)
                    or inverse.min() < 0 or inverse.max() >= len(unique)
                    or not np.isfinite(unique).all()):
                raise ValueError("Invalid saved query deduplication arrays")
            counts = np.bincount(inverse, minlength=len(unique))
            result[arm] = {"query_rows": int(len(inverse)), "unique_vectors": int(len(unique)),
                           "embedding_or_feature_width": int(unique.shape[1]),
                           "largest_identical_vector_group": int(counts.max()),
                           "largest_identical_vector_fraction": float(counts.max() / len(inverse))}
    return result


def run(outputs_root, config_path, output):
    outputs_root, config_path, output = Path(outputs_root), Path(config_path), Path(output)
    if output.exists():
        raise FileExistsError("Use a new output path; preserve earlier diagnostics")
    config = read(config_path)
    input_hashes = {"config.json": digest(config_path)}
    datasets = []
    for dataset in config["datasets"]:
        root = outputs_root / dataset
        result_path = root / "RESULTS.json"
        result = read(result_path)
        input_hashes[f"{dataset}/RESULTS.json"] = digest(result_path)
        if result["status"] != "COMPLETE_DEVELOPMENT_ONLY" or result["config_sha256"] != input_hashes["config.json"]:
            raise ValueError("Completed result/config mismatch")
        freeze_path = root / "FIT_FREEZE.json"
        freeze_sha = digest(freeze_path)
        if freeze_sha != result["fit_freeze_sha256"]:
            raise ValueError("Completed result/freeze mismatch")
        input_hashes[f"{dataset}/FIT_FREEZE.json"] = freeze_sha
        freeze = read(freeze_path)

        def verified(name, frozen=False):
            path = root / "private" / name
            if path.resolve().parent != (root / "private").resolve():
                raise ValueError("Private artifact must be a direct child")
            actual = digest(path)
            if result["private_artifact_sha256"].get(name) != actual:
                raise ValueError("Private artifact hash mismatch: " + name)
            if frozen and freeze["artifacts"].get(name) != actual:
                raise ValueError("Bank/calibration not bound to pre-evaluation freeze: " + name)
            input_hashes[f"{dataset}/private/{name}"] = actual
            return path

        seed_reports = []
        for seed in config["seeds"]:
            bank_path = verified(f"bank_{seed}.npz", frozen=True)
            verified(f"bank_indices_{seed}.npz", frozen=True)
            calibration_path = verified(f"calibration_{seed}.npz", frozen=True)
            calibration_queries = verified(f"calibration_queries_{seed}.npz", frozen=True)
            with np.load(bank_path, allow_pickle=False) as bank:
                bank_counts = {arm: {"sampled_training_entities": int(len(bank[arm + "_bank_raw"])),
                                     "distinct_raw_vectors": int(len(np.unique(bank[arm + "_bank_raw"], axis=0)))}
                               for arm in ("local_knn", "mlp_knn", "gin_knn")}
            with np.load(calibration_path, allow_pickle=False) as arrays:
                cal_gin = arrays["gin_knn"].copy()
            conditions = []
            clean_distributions = None
            expected_conditions = [r for r in result["records"] if r["seed"] == seed and r["drop_rate"] in (0., .5)]
            if len(expected_conditions) != 2:
                raise ValueError("This diagnostic expects one clean and one 50% condition per seed")
            for row in expected_conditions:
                name = row["name"]
                predictions = verified(f"predictions_{seed}_{name}.npz")
                queries = verified(f"queries_{seed}_{name}.npz")
                with np.load(predictions, allow_pickle=False) as arrays:
                    y, degree = arrays["y"].copy(), arrays["degree"].copy()
                    counts = diagnostic_counts(y, degree, arrays["margin_mlp_knn"], arrays["margin_gin_knn"],
                                               arrays["margin_quality_gate"], config["gate_min_degree"])
                    gin_scores = arrays["score_gin_knn"].copy()
                for arm, observed in counts["frozen_operating_point"].items():
                    if any(row["metrics"][arm][key] != value for key, value in observed.items()):
                        raise ValueError("Diagnostic confusion counts disagree with run metrics")
                if any(counts["mlp_gin_complementarity"][key] != value for key, value in row["complementarity"].items()):
                    raise ValueError("Diagnostic union counts disagree with run metrics")
                conditions.append({"name": name, "drop_rate": row["drop_rate"], "mask_seed": row["mask_seed"],
                                   **counts, "query_duplication": query_shape_summary(queries)})
                if row["drop_rate"] == 0:
                    groups = {"declared_benign_calibration": cal_gin,
                              "unannotated_test_negative": gin_scores[y == 0],
                              "annotated_malicious_test": gin_scores[y == 1]}
                    clean_distributions = {group: score_summary(values) for group, values in groups.items()}
                    ordered = np.sort(cal_gin)
                    # Interpret existing operating points only; no alternative cutoffs.
                    for group, summary in clean_distributions.items():
                        for tie in summary["largest_exact_score_ties"]:
                            score = tie["score"]
                            tail_p = (1 + len(ordered) - np.searchsorted(ordered, score, side="left")) / (len(ordered) + 1)
                            tie["frozen_calibration_tail_p"] = float(tail_p)
                            tie["flagged_at_existing_alpha"] = bool(tail_p <= config["calibration_fpr"])
                            tie["exact_score_count_by_population"] = {
                                population: int(np.sum(values == score)) for population, values in groups.items()}
            seed_reports.append({"seed": seed, "training_bank": bank_counts,
                                 "calibration_query_duplication": query_shape_summary(calibration_queries),
                                 "conditions": conditions, "clean_gin_score_distributions": clean_distributions})
        datasets.append({"dataset": dataset, "seeds": seed_reports})
    report = {
        "status": SCOPE, "created_utc": datetime.now(timezone.utc).isoformat(),
        "self_script_sha256": digest(__file__), "input_hashes": input_hashes,
        "frozen_degree_threshold": config["gate_min_degree"], "frozen_calibration_alpha": config["calibration_fpr"],
        "thresholds_changed": False, "model_fit_or_retraining_performed": False,
        "queries_or_entity_arrays_published": False, "datasets": datasets,
        "interpretation_limits": [
            "These are post-hoc aggregate descriptions on previously inspected development test graphs.",
            "Test y=0 denotes the benchmark's unannotated negative class, not independently verified harmless behavior.",
            "The checker counts identify consequences of the frozen degree routing rule, not a newly tested improved rule.",
            "Score ties and calibration/test shifts describe saved floating-point outputs; they do not establish a causal architecture defect.",
            "The three seed arms vary both predecessor encoder weights and sampled training banks; this diagnostic cannot isolate their contributions.",
            "Repeated seeds and entity counts are not independent attack campaigns or confidence intervals.",
            "Input hashes bind bank/query artifacts; this helper does not recompute nearest-neighbor distances. Use the separate independent result auditor for that check."
        ]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.outputs_root, args.config, args.output)
    print(json.dumps({"status": report["status"], "datasets": len(report["datasets"]),
                      "hash_bound_inputs": len(report["input_hashes"]), "output": str(args.output)}))
