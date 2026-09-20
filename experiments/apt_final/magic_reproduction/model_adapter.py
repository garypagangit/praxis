"""Narrow adapter for the unchanged, privately bundled MAGIC author source."""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import torch

UPSTREAM_COMMIT = "aa0b647eea74b6faa0e52eb444370c4411a32cbe"


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify_source(source_dir):
    root = Path(source_dir).resolve(strict=True)
    manifest_path = root / "SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["commit"] != UPSTREAM_COMMIT or not manifest["files"]:
        raise ValueError("Wrong or empty upstream source manifest")
    required = {"model/autoencoder.py", "model/gat.py", "model/loss_func.py", "utils/utils.py"}
    if not required.issubset(manifest["files"]):
        raise ValueError("Missing required author modules")
    for relative, expected in manifest["files"].items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or "\\" in relative or not path.is_file():
            raise ValueError("Invalid author source path")
        if digest(path) != expected:
            raise ValueError("Author source hash mismatch: " + relative)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*.py")}
    expected = {r for r in manifest["files"] if r.endswith(".py")}
    if actual != expected:
        raise ValueError("Unexpected author Python source")
    return manifest


def load_author(source_dir):
    """Import only after byte verification; do not substitute model implementations."""
    verify_source(source_dir)
    root = Path(source_dir).resolve(strict=True)
    for prefix in ("model", "utils"):
        for name, module in list(sys.modules.items()):
            if name == prefix or name.startswith(prefix + "."):
                location = getattr(module, "__file__", None)
                if location is None or not Path(location).resolve().is_relative_to(root):
                    raise RuntimeError("Conflicting imported namespace: " + name)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import dgl
    model = importlib.import_module("model.autoencoder")
    utilities = importlib.import_module("utils.utils")
    return SimpleNamespace(dgl=dgl, model=model, utilities=utilities)


def build_model(author, training, specification, device):
    args = SimpleNamespace(num_hidden=training["hidden_dim"], num_layers=training["num_layers"],
                           negative_slope=training["negative_slope"], mask_rate=training["mask_rate"],
                           alpha_l=training["alpha_l"], n_dim=specification["node_types"],
                           e_dim=specification["edge_types"])
    return author.model.build_model(args).to(device)


def load_arrays(data_dir, dataset, graph_name, hashes, *, training_only=True, labels=False):
    if dataset not in {"cadets", "theia"}:
        raise ValueError("Unsupported prepared dataset")
    if graph_name not in {"train0", "train1", "train2", "train3", "test0"}:
        raise ValueError("Unsupported graph name")
    if training_only and (not graph_name.startswith("train") or labels):
        raise ValueError("Qualification cannot access evaluation arrays or labels")
    relative = f"{dataset}/{graph_name}.npz"
    root = Path(data_dir).resolve(strict=True)
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or digest(path) != hashes.get(relative):
        raise ValueError("Prepared graph hash or path mismatch: " + relative)
    with np.load(path, allow_pickle=False) as archive:
        result = {key: np.asarray(archive[key]) for key in ("node_type", "src", "dst", "relation")}
        if labels:
            result["y"] = np.asarray(archive["y"])
    for key, array in result.items():
        if array.ndim != 1 or array.dtype.kind not in "iu":
            raise ValueError("Prepared arrays must be one-dimensional integers: " + key)
    n = len(result["node_type"])
    if n == 0 or not (len(result["src"]) == len(result["dst"]) == len(result["relation"])):
        raise ValueError("Empty graph or unequal edge arrays")
    if any(np.any(result[key] < 0) or np.any(result[key] >= n) for key in ("src", "dst")):
        raise ValueError("Edge endpoint outside graph")
    if labels and (len(result["y"]) != n or not np.isin(result["y"], [0, 1]).all()):
        raise ValueError("Invalid binary evaluation labels")
    return result


def graph_from_arrays(author, arrays, specification, device):
    """Match author transform_graph: typed directed edges, one-hot float32 attributes.

    NPZ order and explicit node count preserve the audited graph, including isolates.
    No degree features, scaling, reverse edges, or self loops are added.
    """
    for key, width in (("node_type", specification["node_types"]), ("relation", specification["edge_types"])):
        if np.any(arrays[key] < 0) or np.any(arrays[key] >= width):
            raise ValueError("Type outside fixed vocabulary")
    graph = author.dgl.graph((torch.as_tensor(arrays["src"], dtype=torch.int64),
                              torch.as_tensor(arrays["dst"], dtype=torch.int64)),
                             num_nodes=len(arrays["node_type"]))
    graph.ndata["type"] = torch.as_tensor(arrays["node_type"], dtype=torch.int64)
    graph.edata["type"] = torch.as_tensor(arrays["relation"], dtype=torch.int64)
    graph.ndata["attr"] = torch.nn.functional.one_hot(graph.ndata["type"], specification["node_types"]).float()
    graph.edata["attr"] = torch.nn.functional.one_hot(graph.edata["type"], specification["edge_types"]).float()
    return graph.to(device)


def source_semantics_probe(author, training, device):
    """Report actual source behavior and qualify its real CPU/CUDA embedding path."""
    spec = {"node_types": 3, "edge_types": 2}
    arrays = {"node_type": np.arange(20) % 3, "src": np.arange(20),
              "dst": (np.arange(20) + 1) % 20, "relation": np.arange(20) % 2}
    author.utilities.set_random_seed(0)
    model = build_model(author, training, spec, "cpu")
    graph = graph_from_arrays(author, arrays, spec, "cpu")
    before = graph.ndata["attr"].clone()
    masked, (indices, _) = model.encoding_mask_noise(graph, training["mask_rate"])
    mutation = {"masked_rows": len(indices),
                "original_rows_changed": int((graph.ndata["attr"] != before).any(dim=1).sum()),
                "shared_feature_storage": graph.ndata["attr"].data_ptr() == masked.ndata["attr"].data_ptr(),
                "behavior_retained_without_fix": True}
    graph = graph_from_arrays(author, arrays, spec, "cpu")
    model.eval()
    with torch.no_grad():
        expected = model.embed(graph).detach().cpu().numpy()
        model = model.to(device)
        actual = model.embed(graph.to(device)).detach().cpu().numpy()
    if not np.isfinite(actual).all() or not np.allclose(actual, expected, rtol=1e-4, atol=1e-5):
        raise RuntimeError("Author CPU/device embedding qualification failed")
    model.train()
    loss = model(graph_from_arrays(author, arrays, spec, device))
    if not torch.isfinite(loss):
        raise RuntimeError("Nonfinite author small-graph training loss")
    loss.backward()
    gradients = [p.grad for p in model.parameters() if p.grad is not None]
    if not gradients or not all(torch.isfinite(g).all() for g in gradients):
        raise RuntimeError("Author small-graph backward qualification failed")
    parameters_before = [p.detach().clone() for p in model.parameters()]
    optimizer = author.utilities.create_optimizer("adam", model, training["learning_rate"], training["weight_decay"])
    optimizer.step()
    changed = any(not torch.equal(before, after) for before, after in zip(parameters_before, model.parameters()))
    if not changed or not all(torch.isfinite(p).all() for p in model.parameters()):
        raise RuntimeError("Author small-graph optimizer qualification failed")
    return {"status": "PASS", "device": str(device), "embedding_shape": list(actual.shape),
            "cpu_device_max_absolute_error": float(np.max(np.abs(actual - expected))),
            "embedding_rtol": 1e-4, "embedding_atol": 1e-5,
            "forward_backward_qualified": True, "training_loss": float(loss.detach().cpu()),
            "optimizer_step_changed_parameters": changed,
            "mask_target_alias_probe": mutation,
            "encoder_normalizations": [type(layer.norm).__name__ for layer in model.encoder.gats],
            "determinism_fix_applied": False, "normalization_fix_applied": False,
            "source_dgl_rng_explicitly_seeded": False}
