"""Fresh fold-specific encoders and label-free representation caches.

Training uses exactly two declared normal graphs. Calibration and normal
validation graphs never enter scaling or optimization. The caller must bind
those declarations to the dataset's normal-data provenance. This module never
accesses an NPZ y array, fits a nearest-neighbor bank, or chooses a threshold.

The architecture/training code is the unchanged native_graph pilot; embeddings
use the already qualified second_norm extraction adapter. This is not MAGIC.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch

from experiments.apt_final.native_graph import pilot as native
from experiments.apt_final.embedding_baseline import engine as embedding


REPRESENTATIONS = ("local_knn", "mlp_knn", "gin_knn")
TRAINING_KEYS = ("hidden_dim", "bottleneck_dim", "epochs", "learning_rate", "weight_decay",
                 "feature_mask_rate", "max_loss_nodes", "cpu_threads")
CONDITIONS = {"clean": 0.0, "masked": 0.5}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_new(path, record):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    return path


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("Graph names must be simple nonempty identifiers")
    return value


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(name + " must be a positive integer")
    return value


def _seed(value, name="seed"):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 2 ** 32:
        raise ValueError(name + " must be an integer in [0, 2**32)")
    return value


def _training_config(config):
    missing = set(TRAINING_KEYS) - set(config)
    if missing:
        raise ValueError("Missing training settings: " + ", ".join(sorted(missing)))
    result = {key: config[key] for key in TRAINING_KEYS}
    for key in ("hidden_dim", "bottleneck_dim", "epochs", "max_loss_nodes", "cpu_threads"):
        _positive_integer(result[key], key)
    for key in ("learning_rate", "weight_decay", "feature_mask_rate"):
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
            raise ValueError("Invalid finite training setting: " + key)
    if result["learning_rate"] <= 0 or result["weight_decay"] < 0 or not 0 <= result["feature_mask_rate"] < 1:
        raise ValueError("Training rate, regularization, or mask probability outside range")
    return result


def validate_roles(paths, fit_names, roles):
    if not isinstance(fit_names, (list, tuple)) or len(fit_names) != 2:
        raise ValueError("Exactly two normal fit graphs are required")
    if not isinstance(roles, dict) or set(roles) != {"calibration", "normal_validation"}:
        raise ValueError("Roles must specify only calibration and normal_validation graph names")
    names = [_name(name) for name in [*fit_names, roles["calibration"], roles["normal_validation"]]]
    if len(set(names)) != 4:
        raise ValueError("Two fit, one calibration, and one validation graph must be disjoint")
    if any(name not in paths for name in names):
        raise ValueError("A declared normal graph is missing from paths")
    resolved = [Path(paths[name]).resolve() for name in names]
    if len(set(resolved)) != 4:
        raise ValueError("Distinct role names must not alias the same source file")
    return names


def condition_mask(edge_count, condition, mask_seed):
    """The same graph mask is reused for every fold and encoder/bank seed."""
    if condition not in CONDITIONS:
        raise ValueError("Only registered clean and masked(50%) conditions are supported")
    if isinstance(edge_count, bool) or not isinstance(edge_count, int) or edge_count < 0:
        raise ValueError("edge_count must be a nonnegative integer")
    if condition == "clean":
        return np.ones(edge_count, dtype=bool)
    return np.random.default_rng(_seed(mask_seed, "mask_seed")).random(edge_count) >= 0.5


def cache_graph(graph_path, models, mean, scale, node_types, relations, device, output,
                *, batch_size=32768, keep=None, condition="clean", graph_name=None,
                mask_seed=None, expected_source_sha256=None):
    """Cache unique representations and inverse maps without opening y.

    Return an entry whose cache_npz/receipt_path are relative to this output
    directory. train_and_cache rebases those paths relative to its fold directory.
    The supplied model pair must already be frozen; no fitting takes place here.
    """
    graph_path = Path(graph_path)
    graph_name = _name(graph_name if graph_name is not None else graph_path.stem)
    _positive_integer(node_types, "node_types")
    _positive_integer(relations, "relations")
    _positive_integer(batch_size, "batch_size")
    if set(models) != {"mlp", "gin"}:
        raise ValueError("Exactly one frozen MLP and one frozen GIN are required")
    if models["mlp"].graph or not models["gin"].graph:
        raise ValueError("MLP/GIN model names do not match their architectures")
    if any(parameter.requires_grad for model in models.values() for parameter in model.parameters()):
        raise ValueError("Freeze both model parameter sets before representation caching")
    source_hash = digest(graph_path)
    if expected_source_sha256 is not None and source_hash != expected_source_sha256:
        raise ValueError("Source graph hash differs from the declared frozen input")
    graph = native.load_graph(graph_path)  # Explicit allowlist excludes y.
    n_nodes, n_edges = len(graph["node_type"]), len(graph["src"])
    if not n_nodes:
        raise ValueError("Representation caches require at least one node")
    expected_mask = condition_mask(n_edges, condition, mask_seed)
    if keep is None:
        keep = expected_mask
    else:
        keep = np.asarray(keep)
        if keep.dtype != np.bool_ or keep.shape != (n_edges,) or not np.array_equal(keep, expected_mask):
            raise ValueError("Supplied mask differs from the fixed per-graph condition mask")
    width = node_types + 2 * relations
    mean, scale = np.asarray(mean, dtype=np.float32), np.asarray(scale, dtype=np.float32)
    if (mean.shape != (width,) or scale.shape != (width,) or not np.isfinite(mean).all()
            or not np.isfinite(scale).all() or np.any(scale <= 0)):
        raise ValueError("Invalid fold-frozen feature scaler")
    if any(model.first.in_features != width for model in models.values()):
        raise ValueError("Model feature width does not match node/relation vocabulary")
    started = time.perf_counter()
    raw, degree, src, dst = native.observed_features(graph, node_types, relations, keep)
    features = native.scale_features(raw, mean, scale)
    if not np.isfinite(features).all():
        raise ValueError("Nonfinite standardized observed features")
    values, extraction = {"local_knn": features}, {}
    for arm in ("mlp", "gin"):
        values[arm + "_knn"], extraction[arm] = embedding.extract_embeddings(
            models[arm], features, src, dst, device, batch_size)
    cache = {"degree": degree, "node_type": graph["node_type"]}
    representations = {}
    for arm in REPRESENTATIONS:
        unique, inverse = np.unique(values[arm], axis=0, return_inverse=True)
        cache[arm + "_unique"], cache[arm + "_inverse"] = unique, inverse
        representations[arm] = {"unique_rows": int(len(unique)), "full_rows": n_nodes,
                                "width": int(unique.shape[1]),
                                "unique_key": arm + "_unique", "inverse_key": arm + "_inverse"}
    if digest(graph_path) != source_hash:
        raise ValueError("Source graph changed while representations were computed")
    out = _directory(output)
    cache_path = out / "CACHE.npz"
    np.savez_compressed(cache_path, **cache)
    record = {"status": "LABEL_FREE_REPRESENTATIONS_CACHED", "graph_name": graph_name,
              "condition": condition, "drop_probability": CONDITIONS[condition],
              "n_nodes": n_nodes, "n_edges": n_edges, "observed_edges": int(keep.sum()),
              "mask_seed": mask_seed if condition == "masked" else None,
              "mask_sha256": hashlib.sha256(keep.tobytes()).hexdigest(),
              "input_graph_sha256": source_hash, "cache_npz": "CACHE.npz",
              "cache_sha256": digest(cache_path), "receipt_path": "CACHE.json",
              "representations": representations, "extraction": extraction,
              "elapsed_seconds": time.perf_counter() - started,
              "target_labels_accessed": False, "model_fit_performed": False,
              "features_recomputed_from_retained_edges": True,
              "mask_reused_across_encoder_and_bank_seeds": True}
    _write_new(out / "CACHE.json", record)
    return record


def load_fold(output, device="cpu", *, expected_freeze_sha256=None):
    """Reload (models, mean, scale, freeze) from portable, hash-bound artifacts."""
    root = Path(output)
    freeze_path = root / "FIT_FREEZE.json"
    if expected_freeze_sha256 is None:
        manifest = _read(root / "MANIFEST.json")
        expected_freeze_sha256 = manifest["fit_freeze_sha256"]
    raw = freeze_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_freeze_sha256:
        raise ValueError("Fold fit-freeze hash mismatch")
    freeze = json.loads(raw)
    if freeze.get("status") != "NORMAL_FOLD_ENCODERS_FROZEN_BEFORE_CACHING":
        raise ValueError("Unexpected fold freeze status")
    if freeze.get("target_labels_accessed") is not False or len(freeze["roles"]["fit"]) != 2:
        raise ValueError("Invalid fold training role/label contract")
    prep_raw = (root / "PREPROCESSING.npz").read_bytes()
    if hashlib.sha256(prep_raw).hexdigest() != freeze["artifacts"]["PREPROCESSING.npz"]:
        raise ValueError("Fold preprocessing hash mismatch")
    with np.load(io.BytesIO(prep_raw), allow_pickle=False) as arrays:
        if set(arrays.files) != {"mean", "scale", "type_counts"}:
            raise ValueError("Unexpected preprocessing fields")
        mean, scale = arrays["mean"].copy(), arrays["scale"].copy()
        type_counts = arrays["type_counts"].copy()
    width = freeze["node_types"] + 2 * freeze["relations"]
    if (mean.shape != (width,) or scale.shape != (width,) or not np.isfinite(mean).all()
            or not np.isfinite(scale).all() or np.any(scale <= 0)
            or type_counts.shape != (freeze["node_types"],)
            or type_counts.dtype.kind not in "iu" or not np.all(type_counts >= 0) or type_counts.sum() <= 0):
        raise ValueError("Invalid frozen preprocessing arrays")
    models = {}
    for arm in ("mlp", "gin"):
        name = f"{arm}_{freeze['encoder_seed']}.pt"
        models[arm], _ = embedding.load_frozen_checkpoint(
            root / name, freeze["artifacts"][name], expected_arm=arm,
            expected_input_dim=width, expected_seed=freeze["encoder_seed"])
        models[arm].to(device)
    return models, mean, scale, freeze


def train_and_cache(paths, fit_names, roles, node_types, relations, config, seed, device, output):
    """Train on two normal graphs and cache all four normal graphs in two views.

    roles={'calibration': name, 'normal_validation': name}. The caller schedules
    four rotations and independent bank seeds. Additional paths (e.g. test0)
    are never opened here. All eight caches are fit-independent transformations.
    """
    names = validate_roles(paths, fit_names, roles)
    _positive_integer(node_types, "node_types")
    _positive_integer(relations, "relations")
    _seed(seed, "encoder_seed")
    settings = _training_config(config)
    batch_size = _positive_integer(config.get("embedding_batch_size", 32768), "embedding_batch_size")
    if config.get("conditions", CONDITIONS) != CONDITIONS:
        raise ValueError("The fold study supports exactly clean and masked(50%) views")
    for name in names:
        _seed(config["mask_seeds"][name], "mask_seed for " + name)
    out = _directory(output)
    inputs = {name: digest(paths[name]) for name in names}
    if len(set(inputs.values())) != 4:
        raise ValueError("Declared normal roles contain byte-identical graph files")
    native.configure_reproducibility(settings["cpu_threads"])
    device = torch.device(device)
    if device.type not in ("cpu", "cuda") or (device.type == "cuda" and not torch.cuda.is_available()):
        raise ValueError("Requested CPU/CUDA training device is unavailable")
    qualification = native.qualify_device(device)
    started = time.perf_counter()
    fit_paths = [paths[name] for name in fit_names]
    mean, scale, type_counts = native.fit_scaler(fit_paths, node_types, relations)
    np.savez_compressed(out / "PREPROCESSING.npz", mean=mean, scale=scale, type_counts=type_counts)
    artifacts = {"PREPROCESSING.npz": digest(out / "PREPROCESSING.npz")}
    fit_receipts, models = {}, {}
    for arm in ("mlp", "gin"):
        model, fit_receipts[arm] = native.fit_neural(
            fit_paths, node_types, relations, mean, scale, settings, seed, arm, device)
        model.cpu()
        checkpoint = {"state_dict": model.state_dict(), "arm": arm,
                      "input_dim": int(len(mean)), "hidden_dim": settings["hidden_dim"],
                      "bottleneck_dim": settings["bottleneck_dim"], "seed": seed}
        name = f"{arm}_{seed}.pt"
        torch.save(checkpoint, out / name)
        artifacts[name] = digest(out / name)
        # Re-load through the strict adapter to bind every subsequent extraction
        # to exact newly frozen weights, including state fingerprints.
        models[arm], _ = embedding.load_frozen_checkpoint(
            out / name, artifacts[name], expected_arm=arm,
            expected_input_dim=len(mean), expected_seed=seed)
        del model, checkpoint
    if any(digest(paths[name]) != inputs[name] for name in names):
        raise ValueError("A normal source graph changed while encoders were fit")
    freeze = {"status": "NORMAL_FOLD_ENCODERS_FROZEN_BEFORE_CACHING",
              "encoder_seed": seed, "node_types": node_types, "relations": relations,
              "roles": {"fit": list(fit_names), **roles}, "training_config": settings,
              "input_graph_sha256": inputs, "artifacts": artifacts,
              "fit_receipts": fit_receipts, "training_device_qualification": qualification,
              "target_labels_accessed": False, "fit_graphs_count": 2,
              "calibration_or_validation_graphs_used_in_fit": False,
              "architecture": "unchanged native_graph.pilot.ReconstructionModel"}
    _write_new(out / "FIT_FREEZE.json", freeze)
    freeze_hash = digest(out / "FIT_FREEZE.json")
    caches = {}
    for name in names:
        caches[name] = {}
        for condition in CONDITIONS:
            directory = out / "cache" / name / condition
            entry = cache_graph(paths[name], models, mean, scale, node_types, relations,
                                device, directory, batch_size=batch_size, condition=condition,
                                graph_name=name, mask_seed=config["mask_seeds"][name],
                                expected_source_sha256=inputs[name])
            entry["cache_npz"] = (directory / "CACHE.npz").relative_to(out).as_posix()
            entry["receipt_path"] = (directory / "CACHE.json").relative_to(out).as_posix()
            entry["receipt_sha256"] = digest(directory / "CACHE.json")
            caches[name][condition] = entry
    if digest(out / "FIT_FREEZE.json") != freeze_hash:
        raise ValueError("Fold freeze changed during representation caching")
    manifest = {"status": "NORMAL_FOLD_FIT_AND_CACHES_COMPLETE", "encoder_seed": seed,
                "roles": freeze["roles"], "input_graph_sha256": inputs,
                "fit_freeze_sha256": freeze_hash, "caches": caches,
                "conditions": CONDITIONS, "cache_count": 8,
                "elapsed_seconds": time.perf_counter() - started,
                "target_labels_accessed": False, "attack_graphs_accessed": False,
                "nearest_neighbor_banks_fitted": False, "thresholds_selected": False,
                "scientific_scope": "normal-only development; no attack-detection result"}
    _write_new(out / "MANIFEST.json", manifest)
    for model in models.values():
        model.cpu()
    return manifest
