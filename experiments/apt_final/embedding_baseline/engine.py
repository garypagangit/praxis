"""Extract embeddings from the already frozen native-graph pilot models.

This module changes the scoring input only.  It does not train an encoder,
reproduce MAGIC, load attack labels, or alter the frozen native_graph code.
The representation is the output of second_norm, immediately before decoder.
GIN always sees the complete supplied graph; only MLP extraction is batched.
"""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import time
from collections.abc import Mapping

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch

from experiments.apt_final.native_graph.pilot import ReconstructionModel


CHECKPOINT_FIELDS = {
    "state_dict", "arm", "input_dim", "hidden_dim", "bottleneck_dim", "seed"
}
MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _expected_state_shapes(arm, input_dim, hidden_dim, bottleneck_dim):
    shapes = {
        "first.weight": (hidden_dim, input_dim),
        "first.bias": (hidden_dim,),
        "first_norm.weight": (hidden_dim,),
        "first_norm.bias": (hidden_dim,),
        "second.weight": (bottleneck_dim, hidden_dim),
        "second.bias": (bottleneck_dim,),
        "second_norm.weight": (bottleneck_dim,),
        "second_norm.bias": (bottleneck_dim,),
        "decoder.0.weight": (hidden_dim, bottleneck_dim),
        "decoder.0.bias": (hidden_dim,),
        "decoder.2.weight": (input_dim, hidden_dim),
        "decoder.2.bias": (input_dim,),
    }
    if arm == "gin":
        shapes["epsilon"] = (2,)
    return shapes


def _state_digest(model):
    """Canonical parameter/buffer fingerprint, independent of torch.save bytes."""
    result = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        result.update(name.encode("utf-8") + b"\0")
        result.update(str(value.dtype).encode("ascii") + b"\0")
        result.update(str(tuple(value.shape)).encode("ascii") + b"\0")
        result.update(value.numpy().tobytes(order="C"))
    return result.hexdigest()


def load_frozen_checkpoint(path, expected_sha256, *, expected_arm=None,
                           expected_input_dim=None, expected_seed=None):
    """Return (CPU eval model, metadata) from exact registered checkpoint bytes.

    The file is read once, hashed, then deserialized from those same bytes using
    weights_only=True.  The known old architecture and state schema are fixed;
    no code object or attack labels are accepted in the checkpoint contract.
    All parameters have gradients disabled.  Callers bind the expected hash to
    the earlier experiment's hash-checked artifact inventory.
    """
    if not _valid_digest(expected_sha256):
        raise ValueError("A lowercase SHA-256 from the frozen inventory is required")
    path = Path(path)
    if not 0 < path.stat().st_size <= MAX_CHECKPOINT_BYTES:
        raise ValueError("Checkpoint is empty or exceeds the bounded native-model limit")
    raw = path.read_bytes()
    if len(raw) > MAX_CHECKPOINT_BYTES or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Frozen checkpoint hash mismatch")
    checkpoint = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_FIELDS:
        raise ValueError("Unexpected frozen native-pilot checkpoint fields")
    arm = checkpoint["arm"]
    if arm not in ("mlp", "gin"):
        raise ValueError("Only the frozen native-pilot mlp/gin architectures are supported")
    if expected_arm is not None and arm != expected_arm:
        raise ValueError("Frozen checkpoint arm differs from the expected arm")
    dims = {name: _positive_integer(checkpoint[name], name)
            for name in ("input_dim", "hidden_dim", "bottleneck_dim")}
    if expected_input_dim is not None and dims["input_dim"] != expected_input_dim:
        raise ValueError("Frozen feature width differs from the declared input schema")
    seed = checkpoint["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2 ** 63:
        raise ValueError("Checkpoint seed must be an integer in [0, 2**63)")
    if expected_seed is not None and seed != expected_seed:
        raise ValueError("Frozen checkpoint seed differs from the expected seed")
    state = checkpoint["state_dict"]
    expected_shapes = _expected_state_shapes(arm, **dims)
    if not isinstance(state, Mapping) or set(state) != set(expected_shapes):
        raise ValueError("Frozen state_dict keys differ from the native architecture")
    for name, shape in expected_shapes.items():
        value = state[name]
        if not isinstance(value, torch.Tensor) or value.device.type != "cpu":
            raise ValueError("Checkpoint state must contain CPU tensors only")
        if value.dtype != torch.float32 or tuple(value.shape) != shape:
            raise ValueError("Frozen tensor shape/dtype mismatch: " + name)
        if not bool(torch.isfinite(value).all()):
            raise ValueError("Nonfinite frozen parameter: " + name)
    # Preserve caller RNG state: initialization is only a container for saved weights.
    with torch.random.fork_rng(devices=[]):
        model = ReconstructionModel(dims["input_dim"], dims["hidden_dim"],
                                    dims["bottleneck_dim"], graph=arm == "gin")
    model.load_state_dict(state, strict=True)
    model.requires_grad_(False)
    model.eval()
    metadata = {
        "checkpoint_sha256": expected_sha256,
        "state_sha256": _state_digest(model),
        "arm": arm, "seed": seed, **dims,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "loaded_on": "cpu", "weights_only": True,
        "trainable_parameters": 0, "training_performed": False,
        "representation": "second_norm_output_before_decoder",
        "architecture_source": "frozen native_graph.pilot.ReconstructionModel",
    }
    # Diagnostic metadata is deliberately not a state_dict tensor or learned field.
    model._embedding_checkpoint_sha256 = expected_sha256
    model._embedding_expected_state_sha256 = metadata["state_sha256"]
    return model, metadata


def _device(value):
    value = torch.device(value)
    if value.type not in ("cpu", "cuda"):
        raise ValueError("Frozen extraction supports explicit CPU or CUDA devices")
    if value.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA explicitly requested but unavailable; no CPU fallback")
    return value


def _synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _validated_arrays(model, features, src, dst):
    if type(model) is not ReconstructionModel:
        raise ValueError("Extraction requires the unchanged native ReconstructionModel")
    values = np.asarray(features)
    if (values.ndim != 2 or values.shape[0] == 0
            or values.shape[1] != model.first.in_features
            or values.dtype.kind not in "fiu"):
        raise ValueError("Features must be nonempty numeric [nodes, frozen_input_dim]")
    if not np.all(np.isfinite(values)):
        raise ValueError("Features must be finite")
    # Float32 matches the original pilot. Reject overflow during conversion.
    with np.errstate(over="ignore", invalid="ignore"):
        values = np.ascontiguousarray(values, dtype=np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError("Features overflow the frozen float32 model")
    source, target = np.asarray(src), np.asarray(dst)
    if source.ndim != 1 or target.ndim != 1 or source.shape != target.shape:
        raise ValueError("Source and target must be aligned one-dimensional arrays")
    if source.dtype.kind not in "iu" or target.dtype.kind not in "iu":
        raise ValueError("Edge endpoints must use an integer dtype")
    if len(source) and (min(source.min(), target.min()) < 0
                        or max(source.max(), target.max()) >= len(values)):
        raise ValueError("Edge endpoint outside the supplied graph")
    return values, np.ascontiguousarray(source, dtype=np.int64), np.ascontiguousarray(target, dtype=np.int64)


def extract_embeddings(model, features, src, dst, device="cpu", batch_size=32768):
    """Return (float32 ndarray[N, bottleneck_dim], extraction receipt).

    GIN sees every node and every retained directed edge in one forward call;
    batch_size affects MLP only. A temporary second_norm forward hook captures
    the bottleneck. Re-decoding that tensor must exactly reproduce the model's
    full output. The check and state-integrity verification are included in the
    measured extraction time. Callers receive the model on the requested device.
    """
    batch_size = _positive_integer(batch_size, "batch_size")
    device = _device(device)
    if not torch.are_deterministic_algorithms_enabled():
        raise RuntimeError("Configure deterministic algorithms before frozen extraction")
    values, source, target = _validated_arrays(model, features, src, dst)
    if any(parameter.dtype != torch.float32 for parameter in model.parameters()):
        raise ValueError("The frozen model must retain its float32 weights")
    for parameter in model.parameters():
        if not bool(torch.isfinite(parameter).all()):
            raise ValueError("The frozen model contains nonfinite weights")
    _synchronize(device)
    started = time.perf_counter()
    before = _state_digest(model)
    if getattr(model, "_embedding_expected_state_sha256", before) != before:
        raise RuntimeError("Model parameters no longer match the loaded frozen checkpoint")
    model.to(device)
    model.eval()
    captured = []

    def remember(_module, _inputs, output):
        captured.append(output)

    handle = model.second_norm.register_forward_hook(remember)
    parts, calls, largest_error = [], 0, 0.0
    try:
        with torch.no_grad():
            if model.graph:
                batches = [(values, source, target)]
            else:
                empty = np.empty(0, dtype=np.int64)
                batches = ((values[start:start + batch_size], empty, empty)
                           for start in range(0, len(values), batch_size))
            for value_batch, source_batch, target_batch in batches:
                captured.clear()
                x = torch.from_numpy(value_batch).to(device)
                source_tensor = torch.from_numpy(source_batch).to(device)
                target_tensor = torch.from_numpy(target_batch).to(device)
                full_reconstruction = model(x, source_tensor, target_tensor)
                if len(captured) != 1:
                    raise RuntimeError("Expected exactly one second_norm activation per forward")
                z = captured[0]
                if z.shape != (len(value_batch), model.second.out_features):
                    raise RuntimeError("Unexpected bottleneck activation shape")
                decoded = model.decoder(z)
                if not bool(torch.isfinite(z).all()) or not bool(torch.isfinite(decoded).all()):
                    raise RuntimeError("Nonfinite frozen embedding or reconstruction")
                error = float((decoded - full_reconstruction).abs().max().cpu())
                largest_error = max(largest_error, error)
                if not torch.equal(decoded, full_reconstruction):
                    raise RuntimeError("Captured bottleneck fails exact decoder/full-model parity")
                parts.append(z.detach().cpu().numpy().copy())
                calls += 1
    finally:
        handle.remove()
        captured.clear()
    after = _state_digest(model)
    if after != before:
        raise RuntimeError("Frozen parameters changed during extraction")
    _synchronize(device)
    elapsed = time.perf_counter() - started
    embeddings = np.concatenate(parts, axis=0).astype(np.float32, copy=False)
    receipt = {
        "status": "FROZEN_EMBEDDINGS_EXTRACTED",
        "nodes": int(len(values)), "embedding_dim": int(embeddings.shape[1]),
        "arm": "gin" if model.graph else "mlp", "device": str(device),
        "input_edges": int(len(source)), "edges_used": int(len(source)) if model.graph else 0,
        "context": "entire supplied graph" if model.graph else "individual feature rows",
        "forward_calls": calls, "mlp_batch_size": batch_size if not model.graph else None,
        "extraction_seconds": elapsed,
        "timing_includes_validation_decoder_recheck_and_state_digest": True,
        "decoder_reconstruction_exact": True, "decoder_max_absolute_error": largest_error,
        "state_sha256_before": before, "state_sha256_after": after,
        "checkpoint_sha256": getattr(model, "_embedding_checkpoint_sha256", None),
        "deterministic_algorithms": True, "attack_labels_used": False,
        "training_performed": False,
        "representation": "second_norm_output_before_decoder",
    }
    return embeddings, receipt


def qualify_device(device="cpu"):
    """Qualify the real frozen-extraction path on a small deterministic graph.

    CPU repeatability is always measured. CUDA qualification additionally checks
    CPU/CUDA agreement and exact repeated CUDA extraction for both old models.
    This is an inference qualification; no optimizer or retraining is involved.
    """
    device = _device(device)
    if not torch.are_deterministic_algorithms_enabled():
        raise RuntimeError("Enable deterministic algorithms before device qualification")
    x = np.asarray([[.2, -.3, 1.1, .4], [1.3, .7, -.4, .5],
                    [-.1, .9, .2, -.8], [.3, .2, .4, .7],
                    [.9, -.2, -.5, .8]], dtype=np.float32)
    src = np.asarray([0, 1, 0, 2, 3, 3, 4], dtype=np.int64)
    dst = np.asarray([1, 2, 2, 3, 0, 2, 3], dtype=np.int64)
    checks = []
    for graph in (False, True):
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(90210)
            model = ReconstructionModel(4, 8, 3, graph).requires_grad_(False).eval()
        expected, _ = extract_embeddings(model, x, src, dst, "cpu", batch_size=2)
        expected_again, _ = extract_embeddings(model, x, src, dst, "cpu", batch_size=2)
        cpu_repeat = bool(np.array_equal(expected, expected_again))
        actual, receipt = extract_embeddings(model, x, src, dst, device, batch_size=2)
        again, _ = extract_embeddings(model, x, src, dst, device, batch_size=2)
        repeat = bool(np.array_equal(actual, again))
        parity = bool(np.allclose(expected, actual, rtol=1e-4, atol=1e-5))
        check = {"arm": "gin" if graph else "mlp", "cpu_repeat_exact": cpu_repeat,
                 "selected_device_repeat_exact": repeat, "cpu_device_allclose": parity,
                 "max_absolute_error": float(np.max(np.abs(expected - actual))),
                 "decoder_reconstruction_exact": receipt["decoder_reconstruction_exact"]}
        checks.append(check)
        if not cpu_repeat or not repeat or not parity:
            raise RuntimeError("Frozen extraction device qualification failed: " + repr(check))
        model.cpu()
    return {"status": "PASS", "device": str(device), "checks": checks,
            "cuda_parity_executed": device.type == "cuda", "rtol": 1e-4, "atol": 1e-5,
            "training_performed": False, "scope": "SYNTHETIC_SOFTWARE_QUALIFICATION_ONLY"}
