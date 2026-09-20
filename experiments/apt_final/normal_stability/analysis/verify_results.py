"""Independent post-run audit of the fixed normal-stability comparison.

No experiment fitting/scoring helper is imported. All score-derived decisions,
metrics and gates are recomputed. kNN distances use a declared deterministic
sample of unique queries and direct float64 Euclidean calculations. Neural
weights and extraction receipts are bound by hashes; neural inference itself
is not rerun. This file sits outside the operative source freeze.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from experiments.apt_final.native_graph.analysis import verify_results as base
from experiments.apt_final.embedding_baseline.analysis import verify_results as previous

need, read, digest = base.need, base.read, base.digest
AuditFailure = base.AuditFailure
ARMS = ("local_knn", "mlp_knn", "gin_knn")
NORMAL_GRAPHS = {"train0", "train1", "train2", "train3"}
IDENTITY = ("dataset", "fold", "encoder_seed", "bank_seed", "strategy", "representation", "condition")
TRAINING_KEYS = ("hidden_dim", "bottleneck_dim", "epochs", "learning_rate", "weight_decay",
                 "feature_mask_rate", "max_loss_nodes", "cpu_threads")


def close(actual, expected, label):
    if isinstance(expected, dict):
        need(isinstance(actual, dict) and set(actual) == set(expected), label + " keys differ")
        for key, value in expected.items():
            close(actual[key], value, label + "." + key)
    elif isinstance(expected, list):
        need(isinstance(actual, list) and len(actual) == len(expected), label + " list differs")
        for index, value in enumerate(expected):
            close(actual[index], value, label + "[" + str(index) + "]")
    else:
        base.close(actual, expected, label)


def safe(root, relative):
    need(isinstance(relative, str) and relative and not any(x in relative for x in ("\\", ":"))
         and all(p not in ("", ".", "..") for p in relative.split("/")), "Unsafe artifact path")
    result = (Path(root) / relative).resolve()
    need(result.is_relative_to(Path(root).resolve()), "Artifact escapes its directory")
    return result


def arrays(path):
    return base.load_arrays(path)


def fingerprint(*values):
    h = hashlib.sha256()
    for array in values:
        value = np.asarray(array)
        h.update(str(value.shape).encode("ascii") + b"\0")
        h.update(value.dtype.str.encode("ascii") + b"\0")
        h.update(value.tobytes())
    return h.hexdigest()


def integer_array(value, name):
    value = np.asarray(value)
    need(value.ndim == 1 and value.dtype.kind in "iu" and np.all(value >= 0), name + " is not a valid index array")
    return value


def finite_vector(value, name, nonempty=False):
    value = np.asarray(value)
    need(value.ndim == 1 and value.dtype.kind in "fiu" and np.all(np.isfinite(value))
         and (not nonempty or len(value) > 0), name + " is not a finite score vector")
    return value.astype(np.float64)


def empirical_tail(calibration, query, alpha):
    """Independent >=-tie empirical tail; decisions use probabilities directly."""
    cal = finite_vector(calibration, "Calibration", True)
    query = finite_vector(query, "Query")
    need(not isinstance(alpha, (bool, np.bool_)) and np.isfinite(alpha) and 0 < alpha < 1, "Invalid calibration alpha")
    counts = cal.size - np.searchsorted(np.sort(cal), query, side="left")
    p = (counts + 1).astype(np.float64) / (cal.size + 1)
    margin = np.log(alpha / p)
    prediction = p <= alpha
    need(np.array_equal(prediction, margin >= 0), "Log rounding changed a calibration decision")
    return margin, p, prediction


def check_records(records, config):
    axes = (config["datasets"], [f["name"] for f in config["folds"]], config["encoder_seeds"],
            config["bank_seeds"], list(config["strategies"]), config["representations"], list(config["conditions"]))
    need(all(len(set(values)) == len(values) and len(values) for values in axes), "Duplicate or empty registered identity axis")
    expected = set(itertools.product(*axes))
    result = {}
    for record in records:
        index = tuple(record[k] for k in IDENTITY)
        need(index in expected and index not in result, "Unexpected or repeated record identity")
        duplicate = (config["encoder_seeds"][0] if record["representation"] == "local_knn"
                     and record["encoder_seed"] != config["encoder_seeds"][0] else None)
        need(record["duplicate_of_encoder_seed"] == duplicate, "Incorrect local-feature duplicate declaration")
        result[index] = record
    need(set(result) == expected, "Incomplete fixed-family record inventory")
    for index, record in result.items():
        if record["duplicate_of_encoder_seed"] is not None:
            origin = list(index)
            origin[2] = record["duplicate_of_encoder_seed"]
            need(record["metrics"] == result[tuple(origin)]["metrics"], "Local-feature duplicate metrics differ")
    return result


def check_reference_rows(selection, state, metadata, sizes, fold, bank_seed, bank_size):
    fit = sorted(fold["fit"])
    roles = fit + [fold["calibration"], fold["validation"]]
    need(len(roles) == len(set(roles)) == 4 and set(roles) == NORMAL_GRAPHS, "Fitting/held-out roles overlap or changed")
    need(set(selection) == set(fit) and metadata["graph_names"] == fit, "Reference includes a held-out or missing fitting graph")
    total = sum(sizes[name] for name in fit)
    expected = np.sort(np.random.default_rng(bank_seed).choice(total, min(bank_size, total), replace=False))
    global_rows, graph_rows, original_rows, offset = [], [], [], 0
    for graph_index, name in enumerate(fit):
        ids = integer_array(selection[name], "Selected rows")
        need(np.all(ids < sizes[name]) and (len(ids) < 2 or np.all(ids[1:] > ids[:-1])), "Repeated, unsorted or out-of-range fitting row")
        global_rows.extend((ids + offset).tolist())
        graph_rows.extend([graph_index] * len(ids))
        original_rows.extend(ids.tolist())
        offset += sizes[name]
    need(np.array_equal(global_rows, expected), "Fitting rows differ from registered global uniform sampling")
    for name, value in (("bank_row_graph", graph_rows), ("bank_row_id", original_rows)):
        actual = integer_array(state[name], name)
        need(np.array_equal(actual, value), "Reference source-row identities changed")
    n = len(expected)
    domain = 0x56494557
    permuted = np.random.default_rng(np.random.SeedSequence([bank_seed, domain])).permutation(n)
    masked = np.zeros(n, dtype=bool)
    masked[permuted[n // 2:]] = True
    need(state["pooled_is_masked"].dtype == np.bool_ and np.array_equal(state["pooled_is_masked"], masked), "Pooled clean/masked row allocation changed")
    for name, expected_value in (("bank_rows", n), ("clean_rows", n // 2), ("masked_rows", n - n // 2),
                                 ("bank_seed", bank_seed), ("allocation_domain", domain),
                                 ("reference_multiplicity_preserved", True)):
        need(metadata[name] == expected_value, "Reference budget/allocation metadata differs: " + name)
    return n


def check_unique_distances(raw, mean, scale, unique, scores, k, sample_size=8):
    """Sample unique queries independently; every reference row keeps its mass."""
    raw, mean, scale, unique = map(np.asarray, (raw, mean, scale, unique))
    score = finite_vector(scores, "Saved unique distances", True)
    need(raw.ndim == unique.ndim == 2 and raw.shape[1] == unique.shape[1] and len(unique) == len(score), "Distance arrays do not align")
    need(mean.shape == scale.shape == (raw.shape[1],) and np.all(scale > 0), "Invalid distance scaling")
    need(all(np.all(np.isfinite(v)) for v in (raw, mean, scale, unique)), "Nonfinite distance inputs")
    need(isinstance(k, int) and 1 <= k <= len(raw) and isinstance(sample_size, int) and sample_size > 0, "Invalid neighbor/sample count")
    selected = np.sort(np.random.default_rng(20260920).choice(len(unique), min(sample_size, len(unique)), replace=False))
    bank = (raw.astype(np.float64) - mean) / scale
    errors = []
    for row in selected:
        query = (unique[row].astype(np.float64) - mean) / scale
        distance = np.sqrt(np.sum((bank - query) ** 2, axis=1, dtype=np.float64))
        expected = np.sort(distance)[:k].mean(dtype=np.float64)
        need(np.isclose(score[row], expected, rtol=1e-10, atol=1e-12), "Independent direct kNN distance differs")
        errors.append(float(abs(score[row] - expected)))
    return {"sampled_unique_queries": len(selected), "unique_queries": len(unique),
            "query_sample_sha256": hashlib.sha256(selected.astype(np.int64).tobytes()).hexdigest(),
            "max_absolute_error": max(errors, default=0.), "reference_rows_per_query": len(raw),
            "all_queries_reexecuted": len(selected) == len(unique)}


def normal_metrics(prediction, node_type):
    pred, types = np.asarray(prediction), integer_array(node_type, "Node types")
    need(pred.ndim == 1 and len(pred) == len(types) > 0 and set(np.unique(pred)) <= {0, 1}, "Invalid normal predictions")
    result = {"n": len(pred), "alerts": int(pred.sum()), "false_positive_rate": float(pred.mean()), "by_node_type": {}}
    for value in np.unique(types):
        mask = types == value
        alerts, n = int(pred[mask].sum()), int(mask.sum())
        result["by_node_type"][str(int(value))] = {"n": n, "alerts": alerts, "false_positive_rate": alerts / n}
    return result


def independent_decision(normal, attack, config, baselines):
    """Recompute registered gates without selecting a seed or changing a ceiling."""
    normal = [r for r in normal if r["duplicate_of_encoder_seed"] is None]
    attack = [r for r in attack if r["duplicate_of_encoder_seed"] is None]
    result = {"scope": "FIXED_DEVELOPMENT_FAMILY", "datasets": {}, "general_ready_candidates": [],
              "positive_repair_candidates": [], "novelty_established": False, "confirmation": False}
    for dataset in config["datasets"]:
        strongest = max(float(np.mean([r["metrics"]["f1"] for r in attack if r["dataset"] == dataset
                        and r["strategy"] == "clean" and r["representation"] == arm and r["condition"] == "masked"]))
                        for arm in config["representations"])
        candidates = {}
        for strategy, arm in itertools.product(config["strategies"], config["representations"]):
            n = [r for r in normal if (r["dataset"], r["strategy"], r["representation"]) == (dataset, strategy, arm)]
            a = [r for r in attack if (r["dataset"], r["strategy"], r["representation"]) == (dataset, strategy, arm)]
            need(n and a, "Empty candidate cannot pass a gate")
            normal_max = max(r["metrics"]["false_positive_rate"] for r in n)
            attack_max = max(r["metrics"]["false_positive_rate"] for r in a)
            recall_min = min(r["metrics"]["recall"] for r in a)
            normal_ready = normal_max <= config["readiness_max_fpr"]
            attack_ready = attack_max <= config["readiness_max_fpr"] and recall_min >= config["readiness_min_recall"]
            clean = float(np.mean([r["metrics"]["f1"] for r in a if r["condition"] == "clean"]))
            masked = float(np.mean([r["metrics"]["f1"] for r in a if r["condition"] == "masked"]))
            historical = clean - baselines["records"][dataset]["original_best_fixed_mean_clean_f1"]
            improvement = masked - strongest
            candidates[strategy + "/" + arm] = {
                "normal_ready": normal_ready, "detector_ready": attack_ready, "ready": normal_ready and attack_ready,
                "normal_worst_fpr": normal_max, "attack_worst_fpr": attack_max, "attack_min_recall": recall_min,
                "mean_clean_f1": clean, "mean_masked_f1": masked, "historical_mean_clean_f1_gain": historical,
                "masked_f1_gain_vs_strongest_clean_strategy": improvement,
                "positive_repair": strategy != "clean" and normal_ready and attack_ready
                and historical >= config["minimum_mean_f1_improvement"] and improvement >= config["minimum_mean_f1_improvement"],
                "unique_normal_cases": len(n), "unique_attack_cases": len(a)}
        result["datasets"][dataset] = {"candidates": candidates, "strongest_clean_strategy_mean_masked_f1": strongest}
    for candidate in result["datasets"][config["datasets"][0]]["candidates"]:
        if all(result["datasets"][d]["candidates"][candidate]["ready"] for d in config["datasets"]):
            result["general_ready_candidates"].append(candidate)
        if all(result["datasets"][d]["candidates"][candidate]["positive_repair"] for d in config["datasets"]):
            result["positive_repair_candidates"].append(candidate)
    result["status"] = "READY_CANDIDATE_REQUIRES_CONFIRMATION" if result["general_ready_candidates"] else "NO_GO_FIXED_REPAIR_FAMILY"
    return result


def paired_deltas(attack, config):
    """Descriptive paired repair deltas, including clean-data losses."""
    indexed = {tuple(r[k] for k in IDENTITY): r for r in attack}
    report = []
    for dataset, strategy, arm, condition, comparator in itertools.product(
            config["datasets"], config["strategies"], config["representations"], config["conditions"], config["representations"]):
        # Keep the complete paired encoder grid, especially for local-vs-neural
        # comparisons; selecting only the first encoder would bias its neural
        # comparator. Identical local copies do not become independent trials.
        rows = [r for r in attack
                if (r["dataset"], r["strategy"], r["representation"], r["condition"]) == (dataset, strategy, arm, condition)]
        differences = []
        for row in rows:
            identity = [row[k] for k in IDENTITY]
            identity[4], identity[5] = "clean", comparator
            differences.append(row["metrics"]["f1"] - indexed[tuple(identity)]["metrics"]["f1"])
        report.append({"dataset": dataset, "strategy": strategy, "representation": arm, "condition": condition,
                       "clean_strategy_comparator": comparator, "paired_cases": len(differences),
                       "local_duplicate_pair_positions": (len(differences) - len(differences) // len(config["encoder_seeds"]))
                       if "local_knn" in (arm, comparator) else 0,
                       "mean_f1_delta": float(np.mean(differences)), "minimum_f1_delta": min(differences),
                       "maximum_f1_delta": max(differences)})
    return report


def source_binding(config_path, data_dir, registration_path):
    config, reg, manifest = read(config_path), read(registration_path), read(data_dir / "MANIFEST.json")
    need(reg["status"] == "FROZEN_NORMAL_STABILITY" and reg["scope"] == config["scope"] == "DEVELOPMENT_ONLY", "Wrong registration scope")
    need(reg["confirmation_registered"] is False and reg["test_outcomes_previously_inspected"] is True
         and reg["predecessor_weights_used"] is False, "Exposure/retraining scope changed")
    need(digest(config_path) == reg["config_sha256"] and digest(data_dir / "MANIFEST.json") == reg["data_manifest_sha256"], "Config/data audit binding changed")
    here, native, embedding = config_path.parent, config_path.parent.parent / "native_graph", config_path.parent.parent / "embedding_baseline"
    expected_sources = {config_path, here / "PROTOCOL.md", here / "PROTOCOL_REVIEW.md", here / "PINNED_BASELINES.json",
                        *here.glob("*.py"), *here.glob("*.sh"),
                        *(native / p for p in ("data.py", "pilot.py", "provenance.py", "cloud_control.py")),
                        *(embedding / p for p in ("engine.py", "scoring.py"))}
    need(set(reg["code_hashes"]) == {p.relative_to(REPO).as_posix() for p in expected_sources}, "Registered operative inventory changed")
    for relative, expected in reg["code_hashes"].items():
        need(digest(safe(REPO, relative)) == expected, "Registered source bytes changed: " + relative)
        blob = subprocess.check_output(["git", "show", reg["git_commit"] + ":" + relative], cwd=REPO)
        need(hashlib.sha256(blob).hexdigest() == expected, "Source differs from committed snapshot")
    need(manifest["status"] == "STATIC_DEVELOPMENT_ONLY" and manifest["adapter_sha256"] == digest(native / "data.py"), "Data audit scope/adapter changed")
    actual = {p.relative_to(data_dir).as_posix(): digest(p) for p in data_dir.rglob("*.npz")}
    declared = {}
    for dataset in manifest["datasets"]:
        need(dataset["status"] == "STATIC_DEVELOPMENT_ONLY" and dataset["matches_upstream_git_blob"] is True, "Unqualified source dataset")
        for graph in dataset["graphs"]:
            need(graph["npz"] not in declared, "Duplicate graph in data audit")
            declared[graph["npz"]] = graph["npz_sha256"]
    need(actual == reg["data_files"] == declared, "Normalized graph inventory changed")
    return config, reg, manifest


def expected_files(config):
    normal, final = set(), set()
    for dataset, fold, seed in itertools.product(config["datasets"], config["folds"], config["encoder_seeds"]):
        root = f"{dataset}/{fold['name']}/encoder_{seed}/"
        normal.update(root + file for file in ("PREPROCESSING.npz", f"mlp_{seed}.pt", f"gin_{seed}.pt", "FIT_FREEZE.json", "MANIFEST.json"))
        for graph, condition, file in itertools.product(NORMAL_GRAPHS, config["conditions"], ("CACHE.npz", "CACHE.json")):
            normal.add(root + f"cache/{graph}/{condition}/{file}")
        for bank, file in itertools.product(config["bank_seeds"], ("REFERENCE_STATE.npz", "ROW_SELECTION.npz", "NORMAL_SCORES.npz", "FIT_RECEIPT.json")):
            normal.add(root + f"bank_{bank}/{file}")
        final.add(root + "ATTACK_CACHES.json")
        for condition, file in itertools.product(config["conditions"], ("CACHE.npz", "CACHE.json")):
            final.add(root + f"attack/{condition}/{file}")
        for bank, file in itertools.product(config["bank_seeds"], ("ATTACK_SCORES.npz", "ATTACK_TIMING.json")):
            final.add(root + f"bank_{bank}/{file}")
    return normal, normal | final


def checkpoint_state(path, arm, seed, config, width):
    """Primitive/tensor-only deserialization; no model code or inference."""
    import torch
    need(path.stat().st_size < 64 * 1024 * 1024, "Oversized native checkpoint")
    value = torch.load(path, map_location="cpu", weights_only=True)
    need(set(value) == {"state_dict", "arm", "input_dim", "hidden_dim", "bottleneck_dim", "seed"}, "Unexpected checkpoint schema")
    for key, expected in (("arm", arm), ("seed", seed), ("input_dim", width),
                          ("hidden_dim", config["hidden_dim"]), ("bottleneck_dim", config["bottleneck_dim"])):
        need(value[key] == expected, "Checkpoint identity/dimension differs")
    hidden, latent = config["hidden_dim"], config["bottleneck_dim"]
    shapes = {"first.weight": (hidden, width), "first.bias": (hidden,), "first_norm.weight": (hidden,),
              "first_norm.bias": (hidden,), "second.weight": (latent, hidden), "second.bias": (latent,),
              "second_norm.weight": (latent,), "second_norm.bias": (latent,), "decoder.0.weight": (hidden, latent),
              "decoder.0.bias": (hidden,), "decoder.2.weight": (width, hidden), "decoder.2.bias": (width,)}
    if arm == "gin":
        shapes["epsilon"] = (2,)
    need(set(value["state_dict"]) == set(shapes), "Unexpected model parameter inventory")
    h = hashlib.sha256()
    for name, tensor in sorted(value["state_dict"].items()):
        need(isinstance(tensor, torch.Tensor) and tensor.dtype == torch.float32
             and tuple(tensor.shape) == shapes[name] and torch.isfinite(tensor).all().item(), "Invalid checkpoint tensor")
        h.update(name.encode("utf-8") + b"\0")
        h.update(str(tensor.dtype).encode("ascii") + b"\0")
        h.update(str(tuple(tensor.shape)).encode("ascii") + b"\0")
        h.update(tensor.contiguous().numpy().tobytes())
    return h.hexdigest()


def raw_local(graph, nt, nr, keep):
    zero, one = np.zeros(nt + 2 * nr, dtype=np.float32), np.ones(nt + 2 * nr, dtype=np.float32)
    return previous.observed_local_features(graph, nt, nr, zero, one, keep)


def independent_scaler(paths, fit, nt, nr):
    total, square = np.zeros(nt + 2 * nr, dtype=np.float64), np.zeros(nt + 2 * nr, dtype=np.float64)
    count, types = 0, np.zeros(nt, dtype=np.int64)
    for name in fit:
        with np.load(paths[name], allow_pickle=False) as data:
            graph = {key: data[key] for key in ("node_type", "src", "dst", "relation")}
        values = raw_local(graph, nt, nr, None)
        total += values.sum(0, dtype=np.float64)
        for start in range(0, len(values), 16384):
            square += np.square(values[start:start + 16384].astype(np.float64)).sum(0)
        count += len(values)
        types += np.bincount(graph["node_type"], minlength=nt)
    mean = total / count
    scale = np.maximum(np.sqrt(np.maximum(square / count - mean ** 2, 0)), .001)
    return mean.astype(np.float32), scale.astype(np.float32), types


def check_cache(path, receipt, source, source_sha, name, condition, nt, nr, prep, config, model_states, checkpoint_hashes, device):
    cache = arrays(path)
    need(set(cache) == {"degree", "node_type", *(arm + suffix for arm in ARMS for suffix in ("_unique", "_inverse"))}, "Cache inventory differs")
    n, e = len(source["node_type"]), len(source["src"])
    keep = np.ones(e, dtype=bool) if condition == "clean" else np.random.default_rng(config["mask_seeds"][name]).random(e) >= .5
    need(receipt["status"] == "LABEL_FREE_REPRESENTATIONS_CACHED" and receipt["graph_name"] == name
         and receipt["condition"] == condition, "Cache identity/status differs")
    need(receipt["cache_sha256"] == digest(path) and receipt["input_graph_sha256"] == source_sha, "Cache/source hash differs")
    need(receipt["n_nodes"] == n and receipt["n_edges"] == e and receipt["observed_edges"] == int(keep.sum()), "Cache graph dimensions differ")
    need(receipt["mask_sha256"] == hashlib.sha256(keep.tobytes()).hexdigest(), "Cache intervention mask differs")
    need(receipt["mask_seed"] == (config["mask_seeds"][name] if condition == "masked" else None)
         and receipt["drop_probability"] == config["conditions"][condition], "Cache intervention declaration differs")
    need(receipt["target_labels_accessed"] is False and receipt["model_fit_performed"] is False
         and receipt["features_recomputed_from_retained_edges"] is True, "Cache leakage/recomputation declaration differs")
    degree = np.bincount(np.r_[source["src"][keep], source["dst"][keep]], minlength=n)
    need(np.array_equal(cache["node_type"], source["node_type"]) and np.array_equal(cache["degree"], degree), "Cache type/degree rows differ from observed graph")
    for arm in ARMS:
        unique, inverse = cache[arm + "_unique"], integer_array(cache[arm + "_inverse"], "Cache inverse")
        width = nt + 2 * nr if arm == "local_knn" else config["bottleneck_dim"]
        need(unique.ndim == 2 and unique.shape[1] == width and unique.dtype == np.float32
             and len(unique) > 0 and np.all(np.isfinite(unique)), "Invalid cache representation")
        need(len(inverse) == n and inverse.max() < len(unique)
             and np.array_equal(np.unique(inverse), np.arange(len(unique))), "Cache inverse has missing or invalid rows")
        expected = {"unique_rows": len(unique), "full_rows": n, "width": width,
                    "unique_key": arm + "_unique", "inverse_key": arm + "_inverse"}
        close(receipt["representations"][arm], expected, "Cache representation receipt")
    local = raw_local(source, nt, nr, keep)
    expected_local = (local - prep["mean"]) / prep["scale"]
    previous.check_local_queries(cache, expected_local)
    need(set(receipt["extraction"]) == {"mlp", "gin"}, "Missing encoder extraction receipt")
    for arm, extraction in receipt["extraction"].items():
        need(extraction["status"] == "FROZEN_EMBEDDINGS_EXTRACTED" and extraction["arm"] == arm
             and extraction["device"] == device and extraction["embedding_dim"] == config["bottleneck_dim"], "Extraction identity differs")
        need(extraction["checkpoint_sha256"] == checkpoint_hashes[arm]
             and extraction["state_sha256_before"] == extraction["state_sha256_after"] == model_states[arm], "Extraction weights changed")
        need(extraction["training_performed"] is False and extraction["attack_labels_used"] is False
             and extraction["decoder_reconstruction_exact"] is True and extraction["decoder_max_absolute_error"] == 0
             and extraction["deterministic_algorithms"] is True, "Extraction qualification failed")
        need(extraction["nodes"] == n and extraction["input_edges"] == int(keep.sum())
             and extraction["edges_used"] == (int(keep.sum()) if arm == "gin" else 0), "Extraction context differs")
        calls = 1 if arm == "gin" else (n + config["embedding_batch_size"] - 1) // config["embedding_batch_size"]
        need(extraction["forward_calls"] == calls, "Extraction batching changed")
    return cache


def bank_parameters(state, reference, arm, expected_raw, floor):
    prefix = reference + "__" + arm + "__"
    raw, scaled, mean, scale = (state[prefix + name] for name in ("bank_raw", "bank_scaled", "mean", "scale"))
    need(raw.dtype == scaled.dtype == mean.dtype == scale.dtype == np.float64, "Reference state must be float64")
    need(np.array_equal(raw, expected_raw.astype(np.float64)), "Reference vectors differ from selected fitting cache rows/views")
    need(raw.shape == scaled.shape and mean.shape == scale.shape == (raw.shape[1],), "Reference scaler shapes differ")
    need(all(np.all(np.isfinite(value)) for value in (raw, scaled, mean, scale)), "Nonfinite reference state")
    expected_mean, expected_scale = raw.mean(0), np.maximum(raw.std(0, ddof=0), floor)
    need(np.allclose(mean, expected_mean, rtol=1e-12, atol=1e-12)
         and np.allclose(scale, expected_scale, rtol=1e-12, atol=1e-12), "Reference-only scaling differs")
    need(np.allclose(scaled, (raw - mean) / scale, rtol=1e-12, atol=1e-12), "Standardized reference bank differs")
    return raw, mean, scale


def audit(config_path, data_dir, output, registration_path, sample_size=8):
    config_path, data_dir, output, registration_path = map(lambda p: Path(p).resolve(), (config_path, data_dir, output, registration_path))
    config, registration, manifest = source_binding(config_path, data_dir, registration_path)
    need(tuple(config["representations"]) == ARMS and config["conditions"] == {"clean": 0., "masked": .5}, "Unexpected candidate representations/interventions")
    strategies = {"clean": {"reference": "clean", "calibration": "clean"},
                  "pooled_calibration": {"reference": "clean", "calibration": "pooled"},
                  "pooled_reference_calibration": {"reference": "pooled", "calibration": "pooled"}}
    need(config["strategies"] == strategies, "Fixed strategy definitions changed")
    results, normal_report, freeze, status = (read(output / p) for p in ("RESULTS.json", "NORMAL_RESULTS.json", "NORMAL_FREEZE.json", "RUN_STATUS.json"))
    need(results["status"] == status["status"] == "COMPLETE_FIXED_FAMILY_DEVELOPMENT", "Scientific run incomplete")
    for report in (results, normal_report, status):
        need(report["scope"] == "POST_RESULT_DEVELOPMENT" and report["knn_device"] == "cpu", "Runtime scope/device differs")
        for name, expected in (("source_commit", registration["git_commit"]), ("registration_sha256", digest(registration_path)),
                               ("config_sha256", registration["config_sha256"]), ("data_manifest_sha256", registration["data_manifest_sha256"])):
            need(report[name] == expected, "Result source/data binding differs: " + name)
    need(normal_report["status"] == "NORMAL_PHASE_COMPLETE" and normal_report["test_labels_accessed"] is False
         and results["test_labels_accessed"] is True and results["previous_results_modified"] is False, "Normal/attack phase declarations differ")
    need(freeze["status"] == "ALL_NORMAL_FITTING_AND_CALIBRATION_FROZEN_BEFORE_TEST_LABEL_ACCESS"
         and freeze["test_labels_accessed_this_run"] is False and freeze["previous_test_exposure_acknowledged"] is True, "Normal freeze declaration differs")
    need(freeze["normal_results_sha256"] == digest(output / "NORMAL_RESULTS.json")
         and results["normal_freeze_sha256"] == status["normal_freeze_sha256"] == digest(output / "NORMAL_FREEZE.json"), "Normal phase freeze changed")
    need(normal_report["records"] == results["normal_records"] and normal_report["folds"] == freeze["folds"], "Normal results changed after freeze")
    normal_records, attack_records = check_records(results["normal_records"], config), check_records(results["attack_records"], config)
    unique_count = sum(r["duplicate_of_encoder_seed"] is None for r in normal_records.values())
    need(results["logged_records_per_phase"] == len(normal_records) == len(attack_records)
         and results["unique_records_per_phase"] == normal_report["unique_records"] == unique_count, "Duplicate-adjusted case count differs")
    expected_normal, expected_final = expected_files(config)
    private = output / "private"
    actual = {p.relative_to(private).as_posix(): digest(p) for p in private.rglob("*") if p.is_file()}
    need(set(actual) == expected_final and actual == results["private_artifacts"], "Private final artifact inventory/hash differs")
    need(set(freeze["private_files"]) == expected_normal
         and all(actual[name] == sha for name, sha in freeze["private_files"].items()), "Frozen normal inventory changed or contains attack artifacts")
    fold_index = {}
    for entry in freeze["folds"]:
        index = (entry["dataset"], entry["fold"]["name"], entry["encoder_seed"])
        need(index not in fold_index, "Duplicate fold freeze")
        fold_index[index] = entry
    need(set(fold_index) == set(itertools.product(config["datasets"], [f["name"] for f in config["folds"]], config["encoder_seeds"])), "Fold freeze inventory incomplete")
    audits, duplicate_fingerprints = [], {}
    recomputed_normal, recomputed_attack = [], []
    for dataset in config["datasets"]:
        matches = [s for s in manifest["datasets"] if s["dataset"] == dataset]
        need(len(matches) == 1, "Dataset data audit is missing or repeated")
        spec = matches[0]
        nt, nr = spec["metadata"]["node_feature_dim"], spec["metadata"]["edge_feature_dim"]
        paths = {Path(g["npz"]).stem: safe(data_dir, g["npz"]) for g in spec["graphs"]}
        need(set(paths) == NORMAL_GRAPHS | {config["evaluation_graph"]}, "Unexpected graph inventory")
        sizes = {}
        for name, path in paths.items():
            with np.load(path, allow_pickle=False) as values:
                sizes[name] = len(values["node_type"])
        with np.load(paths[config["evaluation_graph"]], allow_pickle=False) as values:
            y = values["y"]
        need(set(np.unique(y)) == {0, 1} and y.ndim == 1, "Invalid attack benchmark labels")
        for fold in config["folds"]:
            roles = {"fit": fold["fit"], "calibration": fold["calibration"], "normal_validation": fold["validation"]}
            mean, scale, types = independent_scaler(paths, fold["fit"], nt, nr)
            for seed in config["encoder_seeds"]:
                print(json.dumps({"audit_fold": [dataset, fold["name"], seed]}), flush=True)
                entry = fold_index[(dataset, fold["name"], seed)]
                relative_root = f"{dataset}/{fold['name']}/encoder_{seed}"
                need(entry["directory"] == relative_root and entry["fold"] == fold, "Fold directory/roles differ")
                root = safe(private, relative_root)
                fm, ff = read(root / "MANIFEST.json"), read(root / "FIT_FREEZE.json")
                need(entry["manifest_sha256"] == digest(root / "MANIFEST.json")
                     and entry["fit_freeze_sha256"] == fm["fit_freeze_sha256"] == digest(root / "FIT_FREEZE.json"), "Fold manifest/freeze hashes differ")
                need(fm["status"] == "NORMAL_FOLD_FIT_AND_CACHES_COMPLETE" and ff["status"] == "NORMAL_FOLD_ENCODERS_FROZEN_BEFORE_CACHING", "Fold incomplete")
                need(fm["roles"] == ff["roles"] == roles and ff["encoder_seed"] == fm["encoder_seed"] == seed
                     and ff["fit_graphs_count"] == 2 and ff["calibration_or_validation_graphs_used_in_fit"] is False, "Encoder fitting roles differ")
                need(ff["training_config"] == {k: config[k] for k in TRAINING_KEYS}, "Encoder training settings differ")
                need(ff["node_types"] == nt and ff["relations"] == nr and ff["target_labels_accessed"] is False
                     and fm["target_labels_accessed"] is False and fm["attack_graphs_accessed"] is False, "Fold vocabulary/label access differs")
                expected_input = {name: digest(paths[name]) for name in NORMAL_GRAPHS}
                need(ff["input_graph_sha256"] == fm["input_graph_sha256"] == expected_input, "Fold source graph hashes differ")
                prep = arrays(root / "PREPROCESSING.npz")
                need(set(prep) == {"mean", "scale", "type_counts"} and np.array_equal(prep["type_counts"], types), "Fold scaler fitted node types differ")
                need(np.allclose(prep["mean"], mean, rtol=1e-6, atol=1e-6)
                     and np.allclose(prep["scale"], scale, rtol=1e-6, atol=1e-6), "Scaler does not match only the fitting graphs")
                expected_fit_files = {"PREPROCESSING.npz", f"mlp_{seed}.pt", f"gin_{seed}.pt"}
                need(set(ff["artifacts"]) == expected_fit_files and all(digest(root / p) == sha for p, sha in ff["artifacts"].items()), "Fold fitted artifact binding differs")
                model_states = {arm: checkpoint_state(root / f"{arm}_{seed}.pt", arm, seed, config, nt + 2 * nr) for arm in ("mlp", "gin")}
                checkpoint_hashes = {arm: ff["artifacts"][f"{arm}_{seed}.pt"] for arm in model_states}
                qualification = ff["training_device_qualification"]
                if results["device"].startswith("cuda"):
                    need(qualification["status"] == "PASS" and qualification["cuda_parity_executed"] is True, "CUDA was not qualified")
                    need(len(qualification["checks"]) == 2 and all(c["cpu_cuda_allclose"] and c["cuda_repeat_exact"] and c["finite_gradients"] for c in qualification["checks"]), "CUDA parity/determinism qualification failed")
                else:
                    need(qualification["status"] == "CPU_SELECTED", "Unexpected CPU qualification")
                for arm in model_states:
                    receipt = ff["fit_receipts"][arm]
                    need(len(receipt["epoch_mean_loss"]) == config["epochs"] and np.all(np.isfinite(receipt["epoch_mean_loss"]))
                         and receipt["sampled_roots_per_graph_step_cap"] == config["max_loss_nodes"], "Encoder training receipt differs")
                need(set(fm["caches"]) == NORMAL_GRAPHS and fm["cache_count"] == 8, "Normal cache inventory differs")
                attack_cache_receipts = read(root / "ATTACK_CACHES.json")
                need(set(attack_cache_receipts) == set(config["conditions"]), "Attack cache conditions differ")
                caches = {}
                for name in sorted(paths):
                    with np.load(paths[name], allow_pickle=False) as values:
                        graph = {key: values[key] for key in ("node_type", "src", "dst", "relation")}
                    caches[name] = {}
                    for condition in config["conditions"]:
                        if name == config["evaluation_graph"]:
                            directory = root / "attack" / condition
                            receipt = read(directory / "CACHE.json")
                            need(receipt == attack_cache_receipts[condition], "Attack cache receipt differs")
                        else:
                            directory = root / "cache" / name / condition
                            ce = fm["caches"][name][condition]
                            need(ce["cache_npz"] == f"cache/{name}/{condition}/CACHE.npz"
                                 and ce["receipt_path"] == f"cache/{name}/{condition}/CACHE.json"
                                 and ce["receipt_sha256"] == digest(directory / "CACHE.json"), "Normal cache path/receipt binding differs")
                            receipt = read(directory / "CACHE.json")
                            bound_receipt = {**receipt, "cache_npz": ce["cache_npz"], "receipt_path": ce["receipt_path"], "receipt_sha256": ce["receipt_sha256"]}
                            need(bound_receipt == ce, "Normal cache embedded receipt differs")
                        caches[name][condition] = check_cache(directory / "CACHE.npz", receipt, graph, digest(paths[name]), name, condition,
                                                              nt, nr, prep, config, model_states, checkpoint_hashes, results["device"])
                        local = caches[name][condition]
                        identity = (dataset, fold["name"], name, condition, "cache")
                        value = fingerprint(local["local_knn_unique"], local["local_knn_inverse"], local["node_type"], local["degree"])
                        if seed == config["encoder_seeds"][0]:
                            duplicate_fingerprints[identity] = value
                        else:
                            need(duplicate_fingerprints[identity] == value, "Local representation changed across encoder seeds")
                bank_receipts = {b["bank_seed"]: b for b in entry["banks"]}
                need(set(bank_receipts) == set(config["bank_seeds"]) and len(entry["banks"]) == len(bank_receipts), "Bank-repeat receipt inventory differs")
                for bank_seed in config["bank_seeds"]:
                    br = root / f"bank_{bank_seed}"
                    fit_receipt = read(br / "FIT_RECEIPT.json")
                    need(digest(br / "FIT_RECEIPT.json") == bank_receipts[bank_seed]["receipt_sha256"] and fit_receipt["bank_seed"] == bank_seed
                         and fit_receipt["target_labels_used"] is False, "Bank fit receipt changed")
                    need(set(fit_receipt["artifacts"]) == {"REFERENCE_STATE.npz", "ROW_SELECTION.npz", "NORMAL_SCORES.npz"}
                         and all(digest(br / p) == sha for p, sha in fit_receipt["artifacts"].items()), "Bank/calibration freeze hashes differ")
                    selection, state = arrays(br / "ROW_SELECTION.npz"), arrays(br / "REFERENCE_STATE.npz")
                    check_reference_rows(selection, state, fit_receipt["selection"], sizes, fold, bank_seed, config["bank_size"])
                    expected_state = {"bank_row_graph", "bank_row_id", "pooled_is_masked", *(f"{ref}__{arm}__{field}" for ref in ("clean", "pooled")
                                      for arm in ARMS for field in ("bank_raw", "bank_scaled", "mean", "scale"))}
                    need(set(state) == expected_state, "Reference artifact fields differ")
                    normal_scores, attack_scores = arrays(br / "NORMAL_SCORES.npz"), arrays(br / "ATTACK_SCORES.npz")
                    score_sets = {"normal": normal_scores, "attack": attack_scores}
                    timing_sets = {"normal": fit_receipt["scoring"], "attack": read(br / "ATTACK_TIMING.json")}
                    for phase, scores in score_sets.items():
                        role_names = ("calibration", "normal_validation") if phase == "normal" else ("attack",)
                        expected_keys = {"__".join(parts) for parts in itertools.product(("clean", "pooled"), ARMS, role_names, config["conditions"])}
                        need(set(scores) == set(timing_sets[phase]) == expected_keys, "Saved distance score inventory differs")
                    parameters = {}
                    for arm in ARMS:
                        selected = {view: np.concatenate([caches[name][view][arm + "_unique"][caches[name][view][arm + "_inverse"][selection[name]]]
                                                         for name in sorted(fold["fit"])]) for view in config["conditions"]}
                        for reference in ("clean", "pooled"):
                            raw = selected["clean"] if reference == "clean" else np.where(state["pooled_is_masked"][:, None], selected["masked"], selected["clean"])
                            parameters[(reference, arm)] = bank_parameters(state, reference, arm, raw, config["scale_floor"])
                    for phase, scores in score_sets.items():
                        for name, score in scores.items():
                            reference, arm, role, condition = name.split("__")
                            graph_name = {"calibration": fold["calibration"], "normal_validation": fold["validation"], "attack": config["evaluation_graph"]}[role]
                            cache = caches[graph_name][condition]
                            checked = check_unique_distances(*parameters[(reference, arm)], cache[arm + "_unique"], score, config["neighbors"], sample_size)
                            audits.append({"dataset": dataset, "fold": fold["name"], "encoder_seed": seed, "bank_seed": bank_seed, "score_key": name, **checked})
                            timing = timing_sets[phase][name]
                            need(timing["search"] == "exact" and timing["metric"] == "euclidean" and timing["k"] == config["neighbors"]
                                 and timing["reference_rows"] == len(state["bank_row_id"])
                                 and timing["query_rows"] == timing["evaluated_query_rows"] == len(score), "kNN execution receipt differs")
                            if arm == "local_knn":
                                identity = (dataset, fold["name"], bank_seed, name, "score")
                                value = fingerprint(score, state[reference + "__local_knn__bank_raw"])
                                if seed == config["encoder_seeds"][0]:
                                    duplicate_fingerprints[identity] = value
                                else:
                                    need(duplicate_fingerprints[identity] == value, "Local scores/reference differ across encoder seeds")
                    for strategy, settings in config["strategies"].items():
                        for arm in ARMS:
                            reference = settings["reference"]
                            clean_cache = caches[fold["calibration"]]["clean"]
                            cal = normal_scores[f"{reference}__{arm}__calibration__clean"][clean_cache[arm + "_inverse"]]
                            if settings["calibration"] == "pooled":
                                masked_cache = caches[fold["calibration"]]["masked"]
                                masked_cal = normal_scores[f"{reference}__{arm}__calibration__masked"][masked_cache[arm + "_inverse"]]
                                need(len(cal) == len(masked_cal), "Pooled dependent calibration views have unequal mass")
                                cal = np.r_[cal, masked_cal]
                            _, _, cal_pred = empirical_tail(cal, cal, config["calibration_fpr"])
                            close(fit_receipt["calibration_achieved_fpr"][strategy + "/" + arm], float(cal_pred.mean()), "Calibration achieved FPR")
                            for condition in config["conditions"]:
                                index = (dataset, fold["name"], seed, bank_seed, strategy, arm, condition)
                                for role, scores, records, destination in (("normal_validation", normal_scores, normal_records, recomputed_normal),
                                                                          ("attack", attack_scores, attack_records, recomputed_attack)):
                                    graph_name = fold["validation"] if role == "normal_validation" else config["evaluation_graph"]
                                    cache = caches[graph_name][condition]
                                    query = scores[f"{reference}__{arm}__{role}__{condition}"][cache[arm + "_inverse"]]
                                    margin, _, predicted = empirical_tail(cal, query, config["calibration_fpr"])
                                    # Independent recalculation uses full scores; no saved margins exist.
                                    need(np.array_equal(margin >= 0, predicted), "Reconstructed score decisions differ")
                                    metrics = normal_metrics(predicted, cache["node_type"]) if role == "normal_validation" else base.metrics(y, query, predicted)
                                    close(records[index]["metrics"], metrics, "Independent " + role + " metrics")
                                    destination.append({**records[index], "metrics": metrics})
                del caches
    need(len(recomputed_normal) == len(normal_records) and len(recomputed_attack) == len(attack_records), "Audit reconstruction inventory incomplete")
    decision = independent_decision(recomputed_normal, recomputed_attack, config, read(config_path.with_name("PINNED_BASELINES.json")))
    close(results["decision"], decision, "Fixed-family decision")
    return {"status": "PASS", "scope": "POST_RESULT_DEVELOPMENT", "created_utc": datetime.now(timezone.utc).isoformat(),
            "auditor_sha256": digest(Path(__file__)), "results_sha256": digest(output / "RESULTS.json"),
            "registration_sha256": digest(registration_path), "normal_freeze_sha256": digest(output / "NORMAL_FREEZE.json"),
            "source_commit": registration["git_commit"], "logged_records_per_phase": len(normal_records), "unique_records_per_phase": unique_count,
            "normal_frozen_artifacts": len(expected_normal), "final_private_artifacts": len(expected_final),
            "all_record_metrics_recomputed": True, "node_type_normal_fpr_recomputed": True,
            "all_reference_rows_and_view_allocations_verified": True, "all_local_feature_cache_rows_recomputed": True,
            "all_local_duplicate_caches_banks_scores_verified": True, "dependent_calibration_views_acknowledged": True,
            "normal_role_exclusion_and_frozen_inventory_verified": True,
            "distance_check_batches": len(audits), "sampled_unique_queries": sum(r["sampled_unique_queries"] for r in audits),
            "max_absolute_distance_error": max((r["max_absolute_error"] for r in audits), default=0.),
            "distance_sampling": {"method": "fixed seed 20260920; uniform unique-query sample per score array; every reference row retained",
                                  "maximum_per_array": sample_size, "rtol": 1e-10, "atol": 1e-12,
                                  "full_distance_reexecution": all(r["all_queries_reexecuted"] for r in audits)},
            "numeric_tolerances": {"float64_bank_scaling_rtol_atol": 1e-12, "float32_local_features_scaler_rtol_atol": 1e-6,
                                   "decision_counts": "exact", "source_and_artifact_hashes": "exact"},
            "neural_inference_rerun": False, "neural_validation": "primitive-only tensor checkpoints, architecture dimensions, state hashes, and frozen extraction receipts",
            "decision": decision, "paired_f1_deltas": paired_deltas(recomputed_attack, config), "distance_checks": audits,
            "paired_delta_duplicate_treatment": "All encoder positions retained for pairing against neural arms; identical local-feature copies are dependent and not independent replications.",
            "limits": ["Development data already exposed; no novelty or untouched confirmation established.",
                       "Normal file roles may share entities/campaigns; overlapping folds are descriptive.",
                       "Pooled clean/masked calibration contains dependent views and gives no conformal guarantee.",
                       "kNN distances checked on a declared sample; neural inference is not independently rerun."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "data-dir", "output", "registration", "report"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--distance-samples", type=int, default=8)
    args = parser.parse_args(argv)
    need(not args.report.exists(), "Audit report already exists; preserve prior receipts")
    try:
        report = audit(args.config, args.data_dir, args.output, args.registration, args.distance_samples)
    except Exception as error:
        report = {"status": "FAIL", "auditor_sha256": digest(Path(__file__)), "error_type": type(error).__name__, "reason": str(error),
                  "created_utc": datetime.now(timezone.utc).isoformat()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("distance_checks", "paired_f1_deltas", "decision")}), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
