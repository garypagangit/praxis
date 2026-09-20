"""Post-run independent audit for the frozen-encoder distance-score diagnostic.

Confusion metrics, AP, masks, calibration and routing are recalculated in full.
Exact nearest-neighbor distances are checked on a deterministic sample using
direct NumPy float64 subtraction, without the experiment's KDTree scorer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from experiments.apt_final.native_graph.analysis import verify_results as base

NEW_FIXED = ("local_knn", "mlp_knn", "gin_knn")
NEW_SELECTORS = ("quality_gate", "confidence_selector")
PRIOR_ARMS = tuple("prior_" + name for name in base.ARMS)
ARMS = NEW_FIXED + NEW_SELECTORS + PRIOR_ARMS


def bank_scaling_check(bank, arm, floor):
    raw, scaled, mean, scale = [bank[arm + "_" + field] for field in ("bank_raw", "bank_scaled", "mean", "scale")]
    base.need(raw.ndim == scaled.ndim == 2 and raw.shape == scaled.shape and len(raw) > 0, "Invalid saved bank shape")
    base.need(mean.shape == scale.shape == (raw.shape[1],), "Invalid bank scaler shape")
    base.need(all(np.all(np.isfinite(x)) for x in (raw, scaled, mean, scale)), "Nonfinite saved bank/scaler")
    raw = raw.astype(np.float64)
    expected_mean = raw.mean(axis=0)
    expected_scale = np.maximum(raw.std(axis=0, ddof=0), floor)
    base.need(np.allclose(mean, expected_mean, rtol=1e-13, atol=1e-13), "Scaler mean was not fitted to saved bank")
    base.need(np.allclose(scale, expected_scale, rtol=1e-13, atol=1e-13), "Scaler std/floor differs from saved bank")
    base.need(np.allclose(scaled, (raw - expected_mean) / expected_scale, rtol=1e-13, atol=1e-13), "Saved transformed bank differs")
    return raw, expected_mean, expected_scale


def brute_force_score_sample(bank, unique, inverse, saved_scores, k, *, seed=20260920, sample_size=64):
    """Direct Euclidean calculation retaining all reference-row multiplicities.

    ``bank`` is (raw, mean, scale). Query rows are raw representation vectors.
    The sampled query IDs depend only on seed and array length, never labels,
    scores, model quality, or correctness. All query duplicates must agree.
    """
    raw, mean, scale = bank
    base.need(unique.ndim == 2 and unique.shape[1] == raw.shape[1], "Query representation width mismatch")
    base.need(inverse.ndim == saved_scores.ndim == 1 and len(inverse) == len(saved_scores), "Query inverse/score size mismatch")
    base.need(inverse.dtype.kind in "iu" and len(unique) > 0 and len(inverse) > 0, "Invalid query inverse")
    base.need(np.all(np.isfinite(unique)) and np.all(np.isfinite(saved_scores)), "Nonfinite saved query/score")
    base.need(inverse.min() >= 0 and inverse.max() < len(unique), "Query inverse out of bounds")
    ids, first = np.unique(inverse, return_index=True)
    base.need(np.array_equal(ids, np.arange(len(unique))), "Unused or missing unique query rows")
    base.need(np.array_equal(saved_scores, saved_scores[first][inverse]), "Identical saved queries have different scores")
    base.need(isinstance(k, int) and 1 <= k <= len(raw), "Invalid nearest-neighbor count")
    selected = np.sort(np.random.default_rng(seed).choice(len(unique), min(sample_size, len(unique)), replace=False))
    transformed_bank = (raw.astype(np.float64) - mean) / scale
    errors = []
    for query_id in selected:
        query = (unique[query_id].astype(np.float64) - mean) / scale
        distance = np.sqrt(np.sum(np.square(transformed_bank - query), axis=1, dtype=np.float64))
        expected = float(np.sort(distance)[:k].mean(dtype=np.float64))
        actual = float(saved_scores[first[query_id]])
        base.need(np.isclose(actual, expected, rtol=1e-10, atol=1e-12), "Independent brute-force kNN distance mismatch")
        errors.append(abs(actual - expected))
    return {"status": "PASS", "sample_seed": seed, "unique_queries": len(unique),
            "query_rows": len(inverse), "sampled_unique_queries": len(selected),
            "all_reference_rows_per_sample": len(raw), "k": k,
            "query_sample_sha256": hashlib.sha256(selected.astype(np.int64).tobytes()).hexdigest(),
            "max_absolute_score_error": max(errors, default=0.0),
            "distance_method": "direct float64 subtraction/square/sum/sqrt; full reference-bank sort",
            "all_query_duplicate_scores_verified": True,
            "full_query_distance_reexecution": len(selected) == len(unique)}


def source_binding(config_path, data_dir, prior_dir, registration_path):
    config, record = base.read(config_path), base.read(registration_path)
    manifest = base.read(data_dir / "MANIFEST.json")
    base.need(record["status"] == "FROZEN_EMBEDDING_SCORING" and record["scope"] == "DEVELOPMENT_ONLY", "Wrong embedding registration")
    base.need(record["test_outcomes_previously_inspected"] is True and record["confirmation_registered"] is False, "Prior exposure/scope changed")
    base.need(base.digest(config_path) == record["config_sha256"], "Config hash differs")
    base.need(base.digest(data_dir / "MANIFEST.json") == record["data_manifest_sha256"], "Data audit hash differs")
    for rel, expected in record["code_hashes"].items():
        path = (REPO / rel).resolve()
        base.need(path.is_relative_to(REPO) and base.digest(path) == expected, "Source hash/path differs: " + rel)
        blob = subprocess.check_output(["git", "show", record["git_commit"] + ":" + rel], cwd=REPO)
        base.need(hashlib.sha256(blob).hexdigest() == expected, "Source differs from committed snapshot")
    actual_data = {p.relative_to(data_dir).as_posix(): base.digest(p) for p in data_dir.rglob("*.npz")}
    base.need(actual_data == record["data_files"], "Normalized graph inventory differs")
    predecessor = base.read(config_path.with_name("PREDECESSOR.json"))
    base.need(record["prior_files"] == predecessor["files"], "Predecessor inventory differs from registration")
    for rel, expected in record["prior_files"].items():
        path = (prior_dir / rel).resolve()
        base.need(path.is_relative_to(prior_dir) and base.digest(path) == expected, "Predecessor artifact changed: " + rel)
    return config, record, manifest, predecessor


def observed_local_features(graph, node_types, relations, mean, scale, keep=None):
    """Independent typed count reconstruction, matching the declared float32 input."""
    n = len(graph["node_type"])
    src, dst, rel = graph["src"], graph["dst"], graph["relation"]
    if keep is not None:
        src, dst, rel = src[keep], dst[keep], rel[keep]
    values = np.zeros((n, node_types + 2 * relations), dtype=np.float32)
    values[np.arange(n), graph["node_type"]] = 1
    # Bincount gives independent count construction instead of the runner's add.at.
    values[:, node_types:node_types + relations] = np.bincount(
        dst * relations + rel, minlength=n * relations).reshape(n, relations)
    values[:, node_types + relations:] = np.bincount(
        src * relations + rel, minlength=n * relations).reshape(n, relations)
    np.log1p(values[:, node_types:], out=values[:, node_types:])
    return (values - mean) / scale


def check_bank_indices(indices, sizes, seed, config):
    names = sorted(config["train_graphs"])
    base.need(set(indices) == set(names), "Bank references a nontraining or missing graph")
    total = sum(sizes[name] for name in names)
    expected_global = np.sort(np.random.default_rng(seed + config["bank_seed_offset"]).choice(
        total, min(config["bank_size"], total), replace=False))
    actual_global, offset = [], 0
    for name in names:
        idx = indices[name]
        base.need(idx.ndim == 1 and idx.dtype.kind in "iu", "Invalid bank row indices")
        base.need(np.all(idx >= 0) and np.all(idx < sizes[name]) and len(np.unique(idx)) == len(idx), "Duplicate/out-of-range bank row")
        actual_global.extend((idx + offset).tolist())
        offset += sizes[name]
    base.need(np.array_equal(np.asarray(actual_global, dtype=np.int64), expected_global), "Bank differs from frozen global uniform row sample")
    return len(expected_global)


def check_local_queries(queries, expected):
    unique, inverse = queries["local_knn_unique"], queries["local_knn_inverse"]
    base.need(inverse.shape == (len(expected),) and unique.ndim == 2 and unique.shape[1] == expected.shape[1], "Local query shape differs")
    base.need(inverse.dtype.kind in "iu" and inverse.min() >= 0 and inverse.max() < len(unique), "Local query index invalid")
    for start in range(0, len(expected), 16384):
        stop = min(start + 16384, len(expected))
        base.need(np.allclose(unique[inverse[start:stop]], expected[start:stop], rtol=1e-6, atol=1e-6), "Saved local queries differ from registered observed graph rows")


def extraction_check(receipts, checkpoints, nodes, edges, config, device):
    base.need(set(receipts) == {"mlp", "gin"}, "Missing embedding extraction receipt")
    for arm in ("mlp", "gin"):
        r, checkpoint = receipts[arm], checkpoints[arm]
        base.need(r["status"] == "FROZEN_EMBEDDINGS_EXTRACTED", "Incomplete embedding extraction")
        base.need(r["training_performed"] is False and r["attack_labels_used"] is False, "Extraction training/label declaration differs")
        base.need(r["nodes"] == nodes and r["input_edges"] == edges and r["embedding_dim"] == 8, "Extraction shape differs")
        base.need(r["device"] == device and r["arm"] == arm, "Extraction device/arm differs")
        base.need(r["edges_used"] == (edges if arm == "gin" else 0), "Wrong graph context")
        base.need(r["forward_calls"] == (1 if arm == "gin" else (nodes + config["embedding_batch_size"] - 1) // config["embedding_batch_size"]), "Wrong embedding batching")
        base.need(r["checkpoint_sha256"] == checkpoint["checkpoint_sha256"], "Extraction checkpoint differs")
        base.need(r["state_sha256_before"] == r["state_sha256_after"] == checkpoint["state_sha256"], "Frozen state changed during extraction")
        base.need(r["decoder_reconstruction_exact"] is True and r["decoder_max_absolute_error"] == 0, "Encoder/decoder parity failed")


def development_decision(records, config):
    clean = [r for r in records if r["drop_rate"] == 0]
    best = float(max(np.mean([r["metrics"]["prior_" + arm]["f1"] for r in clean]) for arm in base.FIXED))
    arms = {}
    for arm in NEW_FIXED:
        ready = all(r["metrics"][arm]["recall"] >= config["readiness_min_recall"] and
                    r["metrics"][arm]["false_positive_rate"] <= config["readiness_max_fpr"] for r in clean)
        mean_f1 = float(np.mean([r["metrics"][arm]["f1"] for r in clean]))
        arms[arm] = {"detector_ready_all_seeds": ready, "mean_clean_f1": mean_f1,
                     "f1_change_vs_best_prior_fixed_mean": mean_f1 - best,
                     "positive_scoring_screen": ready and mean_f1 - best >= config["minimum_mean_f1_improvement"]}
    return {"scope": "PROSPECTIVE_DEVELOPMENT_SCREEN_ONLY", "best_prior_fixed_mean_f1": float(best),
            "arms": arms, "confirmation_or_novelty_established": False}


def audit_dataset(output, prior, dataset, config, registration, registration_path, data_dir, manifest, prior_audit):
    results, status = base.read(output / "RESULTS.json"), base.read(output / "RUN_STATUS.json")
    freeze, prior_results = base.read(output / "FIT_FREEZE.json"), base.read(prior / "RESULTS.json")
    prior_freeze = base.read(prior / "FIT_FREEZE.json")
    for value in (results, status):
        base.need(value["status"] == "COMPLETE_DEVELOPMENT_ONLY" and value["dataset"] == dataset, "Dataset did not complete")
        base.need(value["scope"] == "POST_RESULT_DEVELOPMENT" and value["test_outcomes_previously_inspected"] is True, "Result scope/prior exposure differs")
        base.need(value["encoder_weights_retrained"] is False, "Encoder retraining is outside scope")
        for key, expected in (("registration_sha256", base.digest(registration_path)), ("source_commit", registration["git_commit"]),
                              ("config_sha256", registration["config_sha256"]), ("data_manifest_sha256", registration["data_manifest_sha256"]),
                              ("prior_results_sha256", base.digest(prior / "RESULTS.json"))):
            base.need(value[key] == expected, "Result evidence binding differs: " + key)
        base.need(value["gpu_qualification"]["status"] == "PASS" and value["knn_device"] == "cpu", "Device/scoring qualification differs")
    base.need(results["fit_freeze_sha256"] == base.digest(output / "FIT_FREEZE.json"), "Fit freeze hash changed")
    base.need(freeze["status"] == "BANKS_AND_CALIBRATION_FROZEN_BEFORE_THIS_RUN_EVALUATION_LABEL_ACCESS", "Fit freeze incomplete")
    base.need(freeze["fit_labels_used"] is False and freeze["prior_test_label_exposure_acknowledged"] is True, "Fit/label declaration differs")
    for key in ("train_graphs", "calibration_graph", "seeds"):
        base.need(freeze[key] == config[key], "Fit partition/seed differs")
    base.need(results["fit_records"] == freeze["fit_records"], "Fitting records changed after freeze")
    private = output / "private"
    inventory = {p.name: base.digest(p) for p in private.iterdir() if p.is_file()}
    base.need(inventory == results["private_artifact_sha256"], "Private output hashes differ")
    fit_names = {f"{stem}_{seed}.npz" for seed in config["seeds"] for stem in ("bank_indices", "bank", "calibration", "calibration_queries")}
    base.need(set(freeze["artifacts"]) == fit_names, "Frozen fit artifact inventory differs")
    for name, expected in freeze["artifacts"].items():
        base.need(inventory.get(name) == expected, "Frozen bank/calibration artifact changed")
    spec = next(x for x in manifest["datasets"] if x["dataset"] == dataset)
    paths = {Path(x["npz"]).stem: data_dir / x["npz"] for x in spec["graphs"]}
    nt, nr = spec["metadata"]["node_feature_dim"], spec["metadata"]["edge_feature_dim"]
    prep = base.load_arrays(prior / "private/PREPROCESSING.npz")
    graph = base.load_arrays(paths[config["evaluation_graph"]])
    calibration_graph = base.load_arrays(paths[config["calibration_graph"]])
    cal_degree = np.bincount(calibration_graph["src"], minlength=len(calibration_graph["y"])) + np.bincount(calibration_graph["dst"], minlength=len(calibration_graph["y"]))
    calibration_local = observed_local_features(calibration_graph, nt, nr, prep["mean"], prep["scale"])
    sizes = {name: next(g["n_nodes"] for g in spec["graphs"] if Path(g["npz"]).stem == name) for name in config["train_graphs"]}
    fit_records = {r["seed"]: r for r in freeze["fit_records"]}
    base.need(set(fit_records) == set(config["seeds"]) and len(freeze["fit_records"]) == len(config["seeds"]), "Fit seed inventory differs")
    banks, calibrations, distance_checks = {}, {}, []
    for seed in config["seeds"]:
        fit = fit_records[seed]
        index = base.load_arrays(private / f"bank_indices_{seed}.npz")
        bank_count = check_bank_indices(index, sizes, seed, config)
        base.close(fit["bank_graph_rows"], {name: len(ids) for name, ids in index.items()}, "Sampled training rows")
        raw_bank = base.load_arrays(private / f"bank_{seed}.npz")
        base.need(set(raw_bank) == {a + "_" + field for a in NEW_FIXED for field in ("bank_raw", "bank_scaled", "mean", "scale")}, "Bank array inventory differs")
        banks[seed] = {a: bank_scaling_check(raw_bank, a, config["scale_floor"]) for a in NEW_FIXED}
        base.need(all(len(v[0]) == bank_count for v in banks[seed].values()), "Representations used different bank row counts")
        base.need(banks[seed]["local_knn"][0].shape[1] == nt + 2 * nr and
                  all(banks[seed][a][0].shape[1] == 8 for a in ("mlp_knn", "gin_knn")), "Saved representation dimensions differ from the frozen schema")
        local_parts = []
        for name in sorted(index):
            train = base.load_arrays(paths[name])
            local = observed_local_features(train, nt, nr, prep["mean"], prep["scale"])
            local_parts.append(local[index[name]])
            del train, local
        base.need(np.allclose(np.concatenate(local_parts), banks[seed]["local_knn"][0], rtol=1e-6, atol=1e-6), "Local-feature bank differs from registered training rows")
        for arm in ("mlp", "gin"):
            checkpoint = fit["checkpoints"][arm]
            expected = prior_freeze["artifacts"][f"{arm}_{seed}.pt"]
            base.need(checkpoint["checkpoint_sha256"] == expected and checkpoint["seed"] == seed and checkpoint["arm"] == arm, "Checkpoint receipt differs from predecessor")
            base.need(checkpoint["training_performed"] is False and checkpoint["weights_only"] is True and checkpoint["trainable_parameters"] == 0, "Frozen loading declaration differs")
        extraction_check(fit["calibration_extraction"], fit["checkpoints"], len(cal_degree), len(calibration_graph["src"]), config, results["device_actual"])
        calibration = base.load_arrays(private / f"calibration_{seed}.npz")
        queries = base.load_arrays(private / f"calibration_queries_{seed}.npz")
        base.need(set(calibration) == set(NEW_FIXED), "Calibration arm inventory differs")
        base.need(set(queries) == {a + suffix for a in NEW_FIXED for suffix in ("_unique", "_inverse")}, "Calibration query inventory differs")
        check_local_queries(queries, calibration_local)
        margins = {}
        for arm in NEW_FIXED:
            base.need(calibration[arm].shape == cal_degree.shape, "Calibration row count differs")
            check = brute_force_score_sample(banks[seed][arm], queries[arm + "_unique"], queries[arm + "_inverse"], calibration[arm], config["neighbors"], seed=20260920 + seed)
            distance_checks.append({"seed": seed, "condition": "calibration", "arm": arm, **check})
            margins[arm] = base.calibrated_margin(calibration[arm], calibration[arm], config["calibration_fpr"])
        margins["quality_gate"] = np.where(cal_degree >= config["gate_min_degree"], margins["gin_knn"], margins["mlp_knn"])
        margins["confidence_selector"] = np.where(np.abs(margins["gin_knn"]) >= np.abs(margins["mlp_knn"]), margins["gin_knn"], margins["mlp_knn"])
        base.close(fit["calibration_fpr"], {arm: float(np.mean(v >= 0)) for arm, v in margins.items()}, "Achieved calibration FPR")
        calibrations[seed] = calibration
    indexed = {(r["seed"], r["name"]): r for r in results["records"]}
    base.need(len(indexed) == len(results["records"]), "Duplicate seed/scenario results")
    prior_conditions = next(d["conditions"] for d in prior_audit["datasets"] if d["dataset"] == dataset)
    checked, expected_private = [], set(fit_names)
    for scenario in base.expected_scenarios(config, graph):
        y, degree = graph["y"], scenario["degree"]
        keep = None if scenario["drop_rate"] == 0 else np.random.default_rng(scenario["mask_seed"]).random(len(graph["src"])) >= scenario["drop_rate"]
        evaluation_local = observed_local_features(graph, nt, nr, prep["mean"], prep["scale"], keep)
        for seed in config["seeds"]:
            key = (seed, scenario["name"])
            base.need(key in indexed, "Missing seed/scenario")
            record = indexed.pop(key)
            for field in ("name", "mask_seed", "drop_rate", "observed_edges"):
                base.close(record[field], scenario[field], "Scenario " + field)
            base.need(record["mask_sha256"] == scenario["input_mask_sha256"], "Recorded mask differs from independent reconstruction")
            previous_condition = [r for r in prior_conditions if r["seed"] == seed and r["scenario"] == scenario["name"]]
            base.need(len(previous_condition) == 1 and previous_condition[0]["input_mask_sha256"] == record["mask_sha256"], "Condition differs from audited predecessor")
            pred_name, query_name = f"predictions_{seed}_{scenario['name']}.npz", f"queries_{seed}_{scenario['name']}.npz"
            expected_private.update((pred_name, query_name))
            arrays, queries = base.load_arrays(private / pred_name), base.load_arrays(private / query_name)
            base.need(set(arrays) == {"y", "degree", *("score_" + a for a in ARMS), *("margin_" + a for a in ARMS)}, "Prediction array inventory differs")
            base.need(set(queries) == {a + suffix for a in NEW_FIXED for suffix in ("_unique", "_inverse")}, "Evaluation query inventory differs")
            check_local_queries(queries, evaluation_local)
            base.need(np.array_equal(arrays["y"], y) and np.array_equal(arrays["degree"], degree), "Saved labels/degrees differ from registered graph condition")
            extraction_check(record["extraction"], fit_records[seed]["checkpoints"], len(y), scenario["observed_edges"], config, results["device_actual"])
            margins = {}
            for arm in NEW_FIXED:
                check = brute_force_score_sample(banks[seed][arm], queries[arm + "_unique"], queries[arm + "_inverse"], arrays["score_" + arm], config["neighbors"], seed=20260920 + seed)
                distance_checks.append({"seed": seed, "condition": scenario["name"], "arm": arm, **check})
                margins[arm] = base.calibrated_margin(calibrations[seed][arm], arrays["score_" + arm], config["calibration_fpr"])
            margins["quality_gate"] = np.where(degree >= config["gate_min_degree"], margins["gin_knn"], margins["mlp_knn"])
            margins["confidence_selector"] = np.where(np.abs(margins["gin_knn"]) >= np.abs(margins["mlp_knn"]), margins["gin_knn"], margins["mlp_knn"])
            prior_pred = base.load_arrays(prior / "private" / pred_name)
            base.need(np.array_equal(prior_pred["y"], y) and np.array_equal(prior_pred["degree"], degree), "Predecessor row/mask alignment differs")
            for arm in base.ARMS:
                margins["prior_" + arm] = prior_pred["margin_" + arm]
                source_score = prior_pred.get("score_" + arm, prior_pred["margin_" + arm])
                base.need(np.array_equal(arrays["score_prior_" + arm], source_score), "Reused predecessor scores changed")
            recomputed, predictions = {}, {}
            base.need(set(record["metrics"]) == set(ARMS), "Metric arm inventory differs")
            for arm in ARMS:
                base.need(np.allclose(arrays["margin_" + arm], margins[arm], rtol=1e-12, atol=1e-12), "Calibrated/routed margin differs")
                if arm in NEW_SELECTORS:
                    base.need(np.array_equal(arrays["score_" + arm], margins[arm]), "Selector score differs from chosen calibrated margin")
                predictions[arm] = margins[arm] >= 0
                recomputed[arm] = base.metrics(y, arrays["score_" + arm], predictions[arm])
                base.close(record["metrics"][arm], recomputed[arm], "Independent metrics " + arm)
            old_record = [r for r in prior_results["records"] if r["seed"] == seed and r["name"] == scenario["name"]]
            base.need(len(old_record) == 1, "Predecessor aggregate record missing")
            for arm in base.ARMS:
                base.close(recomputed["prior_" + arm], old_record[0]["metrics"][arm], "Prior aggregate replay")
            references = tuple("prior_" + a for a in base.FIXED) + NEW_FIXED
            changes = {arm: {ref: base.error_changes(y, predictions[arm], predictions[ref]) for ref in references if ref != arm} for arm in NEW_FIXED + NEW_SELECTORS}
            base.close(record["error_changes"], changes, "Corrected/introduced errors")
            mlp, gin = predictions["mlp_knn"], predictions["gin_knn"]
            complementarity = {"mlp_only_malicious_entities": int(np.sum((y == 1) & mlp & ~gin)),
                "gin_only_malicious_entities": int(np.sum((y == 1) & gin & ~mlp)),
                "union_malicious_entities": int(np.sum((y == 1) & (mlp | gin)))}
            base.close(record["complementarity"], complementarity, "Malicious-entity complementarity")
            checked.append({"seed": seed, "scenario": scenario["name"], "drop_rate": scenario["drop_rate"],
                "mask_sha256": record["mask_sha256"], "metrics": recomputed, "error_changes": changes,
                "complementarity": complementarity})
    base.need(not indexed and set(inventory) == expected_private, "Unexpected records/private artifacts")
    summaries = []
    base.need(len(results["descriptive_summary"]) == len(config["drop_rates"]) * len(ARMS), "Unexpected summary count")
    for rate in config["drop_rates"]:
        members = [r for r in checked if r["drop_rate"] == rate]
        for arm in ARMS:
            summary = {"drop_rate": rate, "arm": arm, "descriptive_runs": len(members)}
            for metric in ("precision", "recall", "f1", "false_positive_rate", "average_precision"):
                values = [r["metrics"][arm][metric] for r in members]
                summary[metric] = {"mean": float(np.mean(values)), "min": min(values), "max": max(values)}
            saved = [r for r in results["descriptive_summary"] if r["drop_rate"] == rate and r["arm"] == arm]
            base.need(len(saved) == 1, "Missing/duplicate summary")
            base.close(saved[0], summary, "Descriptive summary")
            summaries.append(summary)
    decision = development_decision(checked, config)
    base.close(results["development_decision"], decision, "Prospective development decision")
    return {"dataset": dataset, "status": "PASS_SAVED_EVIDENCE_AUDIT", "records_checked": len(checked),
        "private_artifacts_hash_checked": len(inventory), "fit_artifacts_hash_checked": len(fit_names),
        "evaluation_nodes": len(graph["y"]), "malicious_annotations": int(np.sum(graph["y"])),
        "results_sha256": base.digest(output / "RESULTS.json"), "fit_freeze_sha256": base.digest(output / "FIT_FREEZE.json"),
        "distance_checks": distance_checks, "development_decision": decision, "summaries": summaries, "conditions": checked}


def audit(outputs, data_dir, prior_dir, config_path, registration_path):
    config, registration, manifest, predecessor = source_binding(config_path, data_dir, prior_dir, registration_path)
    prior_audit = base.read(prior_dir / "INDEPENDENT_RESULT_AUDIT.json")
    base.need(prior_audit["status"] == "PASS_SAVED_EVIDENCE_AUDIT", "Predecessor independent audit failed")
    report = {"status": "PASS_SAVED_EVIDENCE_AUDIT", "scope": "POST_RESULT_DEVELOPMENT",
        "created_utc": datetime.now(timezone.utc).isoformat(), "auditor_sha256": base.digest(Path(__file__)),
        "metric_helper_sha256": base.digest(Path(base.__file__)), "registration_sha256": base.digest(registration_path),
        "source_commit": registration["git_commit"], "config_sha256": base.digest(config_path),
        "data_manifest_sha256": registration["data_manifest_sha256"], "prior_registration_sha256": predecessor["prior_registration_sha256"],
        "verification": "Full metrics/AP/margins/routing/mask and local training-bank reconstruction; sampled direct float64 kNN distances; artifact hashes.",
        "local_feature_float32_reconstruction_tolerance": {"rtol": 1e-6, "atol": 1e-6,
            "reason": "Portable log1p/scaling rederivation across recorded NumPy versions/platforms; integer counts, IDs and artifact hashes remain exact."},
        "limitations": ["Distance scores are independently recomputed for at most64 distinct query vectors per arm/seed/condition, including calibration; this is not all-query distance replay.",
            "All local-feature bank rows are rederived from training graphs; saved neural embeddings are hash-bound and extraction receipts checked but not independently inference-rerun.",
            "Checkpoint bytes and before/after state receipts are bound; JSON records do not independently attest wall-clock order.",
            "Both datasets are previously inspected development benchmarks; no independent-campaign, novel-method, untouched-confirmation or production claim follows."],
        "datasets": []}
    for dataset in config["datasets"]:
        report["datasets"].append(audit_dataset(outputs / dataset, prior_dir / dataset, dataset, config, registration, registration_path, data_dir, manifest, prior_audit))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("outputs", "data-dir", "prior-dir", "config", "registration", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.outputs.resolve(), args.data_dir.resolve(), args.prior_dir.resolve(), args.config.resolve(), args.registration.resolve())
    except Exception as error:
        result = {"status": "FAIL_SAVED_EVIDENCE_AUDIT", "error_type": type(error).__name__, "reason": str(error),
                  "auditor_sha256": base.digest(Path(__file__))}
        code = 1
    else:
        code = 0
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "report": str(args.report), "datasets_checked": len(result.get("datasets", []))}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
