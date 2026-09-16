"""Frozen D0 input preparation and bounded native TimesFM 3 inference.

No downloads, cloud APIs, calibration, outcome-based choices, or CPU inference.
Prepare requires NumPy only. Run requires the separately frozen GPU environment.
All array hashes are SHA-256 of C-order raw bytes; dtype/shape are recorded too.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import importlib.metadata
import itertools
import json
import os
from pathlib import Path
import platform
import random
import shutil
import signal
import sys
import time
import traceback
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT.parent / "010_development_20260915"
SOURCE_REVISION = "8cb0628371af142e16b8c232cc9fbf667ffb12f9"
MODEL_REVISION = "43046b85ec22d584a13f8098c2ed39c889e129c2"
WEIGHTS_SHA256 = "a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da"
SOURCE_ARCHIVE_SHA256 = "ecb62c7cc793937991bbaf4a481d60ac74e84724db3e9d6ea457b2b350f11692"
CSV_SHA256 = "e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584"
PIPELINES = ["joint_native3", "independent_native3",
             "joint_channel0_clip_minus3_plus3", "joint_channel0_causal_sma5"]
STATES = ["clean", "step1", "step3", "step6", "ramp1", "ramp3", "ramp6", "clean_repeat"]
OPTIONS = dict(horizon=1, return_quantiles=True, use_symmetric_averaging=False,
               make_positive=False, sort_quantiles=True, use_znorm=False,
               padding_mode="none")
QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def array_digest(array):
    return hashlib.sha256(np.asarray(array).tobytes(order="C")).hexdigest()


def describe(array):
    return dict(shape=list(array.shape), dtype=str(array.dtype), sha256=array_digest(array))


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def save_npz(path, **arrays):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_values(path):
    """Read first-column values only; no label tokens or post-1006 rows parsed.

    Whole-file bytes are hashed solely for provenance, not interpreted as data.
    The pinned source has exactly one header line and unquoted numeric values.
    """
    require(digest(path) == CSV_SHA256, "Canonical public CSV SHA-256 mismatch")
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        require(next(stream).partition(",")[0] == "Data", "Unexpected value-column header")
        values = np.asarray([float(line.partition(",")[0])
                             for line in itertools.islice(stream, 1007)], dtype=np.float64)
    require(values.shape == (1007,), "Require first 1007 value rows")
    require(np.isfinite(values).all(), "Nonfinite permitted source value")
    return values


def construct(values):
    """Prospective protocol arithmetic, in float64 until final input cast."""
    require(values.dtype == np.float64 and values.shape == (1007,), "Value schema mismatch")
    require(np.isfinite(values).all(), "Nonfinite source values")
    mean = float(np.mean(values[:256], dtype=np.float64))
    sd = float(np.std(values[:256], ddof=0, dtype=np.float64))
    require(np.isfinite(mean) and np.isfinite(sd) and sd >= 1e-6,
            "Invalid commissioning mean/standard deviation")
    z = (values - mean) / sd
    noise = 0.01 * np.random.Generator(np.random.PCG64(20260915)).standard_normal((1007, 3))
    derived = np.empty((1003, 3), dtype=np.float64)
    derived[:, 0] = z[4:] + noise[4:, 0]
    derived[:, 1] = 0.8 * z[4:] + 0.2 * z[3:-1] + noise[4:, 1]
    derived[:, 2] = 0.6 * z[4:] + 0.4 * z[:-4] + noise[4:, 2]
    origins = np.asarray([384 + j * 622 // 31 for j in range(32)], dtype=np.int64)
    targets = derived[origins - 4].copy()
    inputs = np.empty((4, 32, 8, 3, 128), dtype=np.float32)
    for pi, oi, si in itertools.product(range(4), range(32), range(8)):
        end = int(origins[oi])
        context = derived[end - 128 - 4:end - 4].T.copy()
        if 1 <= si <= 3:
            context[0, -64:] += [1.0, 3.0, 6.0][si - 1]
        elif 4 <= si <= 6:
            context[0, -64:] += np.linspace(0.0, [1.0, 3.0, 6.0][si - 4], 64, dtype=np.float64)
        if pi == 2:
            context[0] = np.clip(context[0], -3.0, 3.0)
        elif pi == 3:
            original = context[0].copy()
            context[0] = np.asarray([np.mean(original[max(0, k - 4):k + 1], dtype=np.float64)
                                     for k in range(128)], dtype=np.float64)
        inputs[pi, oi, si] = context.astype(np.float32)
    arrays = dict(inputs=inputs, targets=targets, origins=origins, values=values.copy(),
                  noise=noise, derived=derived)
    require(all(np.isfinite(a).all() for a in arrays.values()), "Nonfinite prepared array")
    require(np.array_equal(inputs[:, :, 0], inputs[:, :, 7]), "Clean repeat not identical")
    require(np.array_equal(inputs[..., 1:, :],
                           np.broadcast_to(inputs[0, :, 0, 1:, :][None, :, None], inputs[..., 1:, :].shape)),
            "Protected channel input changed")
    return arrays, dict(mean=mean, population_sd=sd, commissioning_rows_inclusive=[0, 255])


def identities(arrays):
    rows = []
    for pi, oi, si in itertools.product(range(4), range(32), range(8)):
        rows.append(dict(evaluation_index=len(rows), pi=pi, oi=oi, si=si,
                         pipeline=PIPELINES[pi], origin=int(arrays["origins"][oi]), state=STATES[si],
                         input_sha256=array_digest(arrays["inputs"][pi, oi, si]),
                         target_sha256=array_digest(arrays["targets"][oi])))
    return rows


def check_freeze(path, full_environment=False):
    freeze = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    require(freeze["schema_version"] == 1, "Unsupported runtime freeze schema")
    require(freeze["source_revision"] == SOURCE_REVISION, "Frozen source revision mismatch")
    require(freeze["weights_sha256"] == WEIGHTS_SHA256, "Frozen weights mismatch")
    require(freeze["source_archive_sha256"] == SOURCE_ARCHIVE_SHA256, "Frozen source archive mismatch")
    require(freeze["model_dtype"] == "float32", "Native model dtype must be float32")
    require(freeze["packages"]["numpy"] == np.__version__, "NumPy runtime differs from freeze")
    require("code/d0_worker.py" in freeze["files"], "Worker must be hashed in runtime freeze")
    for name, expected in freeze["files"].items():
        local = (ROOT / name).resolve()
        require(local.is_relative_to(ROOT.parent.resolve()), "Freeze file escapes Praxis root")
        require(digest(local) == expected, "Frozen file changed: " + name)
    if full_environment:
        require(".".join(platform.python_version_tuple()[:2]) == freeze["python_major_minor"],
                "Python major/minor differs from runtime freeze")
        for package, expected in freeze["packages"].items():
            require(importlib.metadata.version(package) == expected, "Package mismatch: " + package)
    return freeze


def prepare(args):
    freeze = check_freeze(args.runtime_freeze)
    arrays, commissioning = construct(read_values(args.csv))
    manifest = dict(schema_version=1, status="PREPARED_NO_MODEL_INFERENCE", created_utc=utc(),
                    source_csv_sha256=CSV_SHA256, source_revision=SOURCE_REVISION,
                    model_revision=MODEL_REVISION, weights_sha256=WEIGHTS_SHA256,
                    pipelines=PIPELINES, states=STATES, origins=arrays["origins"].tolist(),
                    arrays={key: describe(value) for key, value in arrays.items()},
                    commissioning=commissioning, numpy=np.__version__, python=platform.python_version(),
                    source_value_rows_inclusive=[0, 1006], labels_parsed=False, hai_accessed=False,
                    derived_array_first_time_index=4, identities=identities(arrays),
                    protocol_sha256=digest(PLAN / "D0_PROTOCOL.md"), spec_sha256=digest(PLAN / "D0_SPEC.json"),
                    worker_sha256=digest(__file__), runtime_freeze_sha256=digest(args.runtime_freeze),
                    quantile_levels=QUANTILES, actual_model_calls=0)
    save_npz(args.output / "inputs.npz", **arrays)
    manifest["inputs_npz_sha256"] = digest(args.output / "inputs.npz")
    write_json(args.output / "MANIFEST.json", manifest)
    shutil.copyfile(args.runtime_freeze, args.output / "runtime_freeze.json")
    print(json.dumps({"status": manifest["status"], "evaluations_prepared": 1024,
                      "arrays": manifest["arrays"]}), flush=True)


def check_source(source_root, archive_path):
    require(digest(archive_path) == SOURCE_ARCHIVE_SHA256, "Pinned source archive mismatch")
    observed = {}
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            parts = Path(entry.filename).parts
            require(not Path(entry.filename).is_absolute() and ".." not in parts, "Unsafe archive name")
            if len(parts) < 2 or entry.is_dir():
                continue
            relative = Path(*parts[1:])
            local = source_root / relative
            require(local.read_bytes() == archive.read(entry), "Extracted source differs: " + str(relative))
            if relative.suffix == ".py":
                observed[relative.as_posix()] = digest(local)
    actual = {p.relative_to(source_root).as_posix() for p in source_root.rglob("*.py")}
    require(actual == set(observed), "Unexpected Python files in model source tree")
    return observed


def load_prepared(directory):
    manifest = json.loads((directory / "MANIFEST.json").read_text(encoding="utf-8"))
    require(manifest["source_csv_sha256"] == CSV_SHA256, "Prepared source identity mismatch")
    require(manifest["pipelines"] == PIPELINES and manifest["states"] == STATES, "Prepared ordering mismatch")
    require(manifest["worker_sha256"] == digest(__file__), "Prepared by different worker bytes")
    require(digest(directory / "inputs.npz") == manifest["inputs_npz_sha256"], "Input archive changed")
    with np.load(directory / "inputs.npz", allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    require(set(arrays) == {"inputs", "targets", "origins", "values", "noise", "derived"}, "Input keys mismatch")
    for name, value in arrays.items():
        require(describe(value) == manifest["arrays"][name], "Input array changed: " + name)
        require(np.isfinite(value).all(), "Nonfinite input array: " + name)
    rebuilt, commissioning = construct(arrays["values"])
    require(all(describe(rebuilt[name]) == describe(arrays[name]) for name in arrays), "Input reconstruction mismatch")
    require(commissioning == manifest["commissioning"], "Commissioning mismatch")
    require(identities(arrays) == manifest["identities"], "Evaluation identities mismatch")
    return arrays, manifest


class NativeCounter:
    """Observe native decode/forward execution without changing tensor outputs."""
    def __init__(self, model):
        self.native_decode = model.decode
        self.native_forward = model.forward
        self.decode_rows = []
        self.forward_rows = []
        self.forward_calls = self.tensor_batch_sequences = self.tensor_channel_sequences = 0
        model.decode = self.decode
        model.forward = self.forward

    def decode(self, *args, **kwargs):
        target = kwargs.get("target", args[0] if args else None)
        self.decode_rows.append(dict(target_shape=list(target.shape), dtype=str(target.dtype),
                                     target_sha256=array_digest(target.detach().cpu().numpy()),
                                     horizon=int(kwargs.get("horizon", 0))))
        return self.native_decode(*args, **kwargs)

    def forward(self, *args, **kwargs):
        inputs = kwargs.get("inputs", args[0] if args else None)
        values = inputs["values"]
        shape = list(values.shape)
        require(len(shape) == 4, "Unexpected native forward value tensor rank")
        self.forward_rows.append(dict(values_shape=shape, dtype=str(values.dtype)))
        self.forward_calls += 1
        self.tensor_batch_sequences += shape[0]
        self.tensor_channel_sequences += shape[0] * shape[1]
        return self.native_forward(*args, **kwargs)


def check_deadline(start, maximum):
    require(time.monotonic() - start < maximum, "Worker wall-time cap reached")


def run(args, started):
    freeze = check_freeze(args.runtime_freeze, full_environment=True)
    arrays, manifest = load_prepared(args.prepared)
    require(manifest["runtime_freeze_sha256"] == digest(args.runtime_freeze), "Prepared runtime freeze mismatch")
    for name in ["inputs.npz", "MANIFEST.json"]:
        shutil.copyfile(args.prepared / name, args.output / name)
    shutil.copyfile(args.runtime_freeze, args.output / "runtime_freeze.json")
    source_hashes = check_source(args.source_root, args.source_archive)
    require(digest(args.weights) == WEIGHTS_SHA256, "Pinned weights SHA-256 mismatch")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch
    require(torch.cuda.is_available(), "CUDA required; CPU substitution prohibited")
    require(torch.cuda.device_count() == 1, "D0 freezes one visible GPU")
    torch.set_default_dtype(torch.float32)
    torch.set_num_threads(4)
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.reset_peak_memory_stats()
    sys.path.insert(0, str(args.source_root / "src"))
    from timesfm3 import TimesFM3Evaluator, ModelConfig
    config = ModelConfig(checkpoint_path=str(args.weights), per_core_batch_size=1,
                         device="cuda", local_files_only=True, use_variate_attention=True)
    environment = dict(python=platform.python_version(), numpy=np.__version__, torch=torch.__version__,
                       packages={name: importlib.metadata.version(name) for name in freeze["packages"]},
                       platform=platform.platform(), model_dtype="float32", device=torch.cuda.get_device_name(0),
                       cuda_version=torch.version.cuda, cudnn_version=torch.backends.cudnn.version(),
                       deterministic_algorithms=True, tf32=False, cudnn_benchmark=False,
                       torch_threads=torch.get_num_threads(), cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
                       cublas_workspace_config=os.environ["CUBLAS_WORKSPACE_CONFIG"])
    receipt = dict(schema_version=1, status="RUN_STARTED_NOT_COMPLETE", started_utc=utc(),
                   source_revision=SOURCE_REVISION, model_revision=MODEL_REVISION,
                   weights_sha256=WEIGHTS_SHA256, source_archive_sha256=SOURCE_ARCHIVE_SHA256,
                   source_file_sha256=source_hashes, model_config=dataclasses.asdict(config),
                   forecast_config=OPTIONS, routing={p: {"univariate": i == 1} for i, p in enumerate(PIPELINES)},
                   environment=environment, runtime_freeze_sha256=digest(args.runtime_freeze),
                   prepared_manifest_sha256=digest(args.prepared / "MANIFEST.json"),
                   worker_sha256=digest(__file__), maximum_worker_seconds=args.max_seconds,
                   quantile_levels=QUANTILES, median_quantile_index=4,
                   total_assigned_evaluations=1024, actual_model_calls=0, hai_accessed=False)
    write_json(args.output / "RUN_STARTED.json", receipt)
    check_deadline(started, args.max_seconds)
    load_start = time.monotonic()
    evaluator = TimesFM3Evaluator(config)
    receipt["model_initialization_seconds"] = time.monotonic() - load_start
    require(evaluator.model.use_variate_attention is True, "Native model variate attention disabled")
    require(not evaluator.model.training, "Model must be in evaluation mode")
    require(all(p.dtype == torch.float32 and p.device.type == "cuda" for p in evaluator.model.parameters()),
            "Native parameters not uniformly CUDA float32")
    require(list(evaluator.config.quantiles) == QUANTILES, "Unexpected native quantile levels")
    loaded = {}
    for name, module in list(sys.modules.items()):
        if name == "timesfm3" or name.startswith("timesfm3."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(args.source_root.resolve()), "Model module loaded outside verified source")
            loaded[name] = {"path": path.relative_to(args.source_root.resolve()).as_posix(), "sha256": digest(path)}
    receipt["loaded_source_modules"] = loaded
    receipt["model_config"] = dataclasses.asdict(evaluator.config)
    receipt["native_model_config"] = evaluator.model.to_dict()
    receipt["native_use_variate_attention"] = evaluator.model.use_variate_attention
    receipt["model_parameter_dtypes"] = sorted({str(p.dtype) for p in evaluator.model.parameters()})
    receipt["model_parameter_devices"] = sorted({str(p.device) for p in evaluator.model.parameters()})
    write_json(args.output / "RUN_STARTED.json", receipt)
    counter = NativeCounter(evaluator.model)
    points = np.full((4, 32, 8, 3), np.nan, dtype=np.float32)
    quantiles = np.full((4, 32, 8, 3, 9), np.nan, dtype=np.float32)
    completed = np.zeros((4, 32, 8), dtype=np.bool_)
    try:
        with (args.output / "observations.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            for identity in manifest["identities"]:
                check_deadline(started, args.max_seconds)
                pi, oi, si = [identity[name] for name in ("pi", "oi", "si")]
                context = arrays["inputs"][pi, oi, si]
                before = (counter.forward_calls, counter.tensor_batch_sequences, counter.tensor_channel_sequences)
                decode_start, forward_start = len(counter.decode_rows), len(counter.forward_rows)
                torch.cuda.synchronize()
                evaluation_start = time.monotonic()
                result_list = list(evaluator.predict_batch([context], ts_ids=[str(identity["evaluation_index"])],
                                                          univariate=pi == 1, **OPTIONS))
                torch.cuda.synchronize()
                require(len(result_list) == 1, "Unexpected native output count")
                result = result_list[0]
                # Preserve returned invalid arrays before fail-closed validation.
                # This is a failure artifact, never a completed observation.
                if (result.forecast is None or result.quantiles is None
                        or result.forecast.shape != (3, 1) or result.quantiles.shape != (3, 1, 9)
                        or not np.isfinite(result.forecast).all() or not np.isfinite(result.quantiles).all()):
                    invalid = {name: value for name, value in
                               [("forecast", result.forecast), ("quantiles", result.quantiles)]
                               if value is not None}
                    save_npz(args.output / "FAILED_NATIVE_OUTPUT.npz", **invalid)
                    write_json(args.output / "FAILED_NATIVE_IDENTITY.json", identity)
                    raise RuntimeError("Invalid native outputs preserved; no scientific completion")
                require(result.ts_id == str(identity["evaluation_index"]), "Native output identity mismatch")
                require(result.forecast.shape == (3, 1) and result.quantiles.shape == (3, 1, 9),
                        "Unexpected native forecast/quantile shape")
                require(result.forecast.dtype == np.float32 and result.quantiles.dtype == np.float32,
                        "Unexpected native forecast dtype")
                require(np.isfinite(result.forecast).all() and np.isfinite(result.quantiles).all(),
                        "Nonfinite forecast or quantile")
                require(np.array_equal(result.forecast, result.quantiles[..., 4]), "Point differs from native median")
                require((np.diff(result.quantiles, axis=-1) >= 0).all(), "Unsorted quantiles")
                require(array_digest(context) == identity["input_sha256"], "Native call mutated saved model input")
                delta = (counter.forward_calls - before[0], counter.tensor_batch_sequences - before[1],
                         counter.tensor_channel_sequences - before[2])
                require(delta == ((3, 3, 3) if pi == 1 else (1, 1, 3)), "Native routing/call counts mismatch")
                row = dict(identity, univariate=pi == 1, forecast=result.forecast[:, 0].tolist(),
                           quantiles=result.quantiles[:, 0, :].tolist(), point_dtype=str(result.forecast.dtype),
                           quantile_dtype=str(result.quantiles.dtype), forward_calls=delta[0],
                           tensor_batch_sequences=delta[1], tensor_channel_sequences=delta[2],
                           decode_calls_detail=counter.decode_rows[decode_start:],
                           forward_calls_detail=counter.forward_rows[forward_start:],
                           elapsed_seconds=time.monotonic() - evaluation_start, completed_utc=utc())
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                points[pi, oi, si] = result.forecast[:, 0]
                quantiles[pi, oi, si] = result.quantiles[:, 0, :]
                completed[pi, oi, si] = True
                if si == 7:
                    save_npz(args.output / "forecasts.npz", points=points, quantiles=quantiles, completed=completed)
                    progress = dict(completed_evaluations=int(completed.sum()), assigned_evaluations=1024,
                                    last_identity=identity, forward_calls=counter.forward_calls,
                                    tensor_batch_sequences=counter.tensor_batch_sequences,
                                    tensor_channel_sequences=counter.tensor_channel_sequences,
                                    elapsed_seconds=time.monotonic() - started, updated_utc=utc())
                    write_json(args.output / "PROGRESS.json", progress)
                    print(json.dumps(progress), flush=True)
        require(completed.all() and int(completed.sum()) == 1024, "Incomplete assignment")
        check_deadline(started, args.max_seconds)
        receipt.update(status="COMPLETE_PENDING_INDEPENDENT_AUDIT", completed_evaluations=int(completed.sum()),
                       actual_model_calls=counter.forward_calls, forward_calls=counter.forward_calls,
                       tensor_batch_sequences=counter.tensor_batch_sequences,
                       tensor_channel_sequences=counter.tensor_channel_sequences,
                       maximum_clean_repeat_point_discrepancy=float(np.max(np.abs(points[:, :, 7].astype(np.float64) - points[:, :, 0].astype(np.float64)))),
                       maximum_clean_repeat_quantile_discrepancy=float(np.max(np.abs(quantiles[:, :, 7].astype(np.float64) - quantiles[:, :, 0].astype(np.float64)))),
                       output_arrays={"points": describe(points), "quantiles": describe(quantiles), "completed": describe(completed)})
    finally:
        save_npz(args.output / "forecasts.npz", points=points, quantiles=quantiles, completed=completed)
        write_json(args.output / "COUNTERS.json", dict(completed_evaluations=int(completed.sum()),
                   forward_calls=counter.forward_calls, tensor_batch_sequences=counter.tensor_batch_sequences,
                   tensor_channel_sequences=counter.tensor_channel_sequences,
                   peak_allocated_gib=torch.cuda.max_memory_allocated() / 1024**3,
                   peak_reserved_gib=torch.cuda.max_memory_reserved() / 1024**3))
    receipt.update(completed_utc=utc(), runtime_seconds=time.monotonic() - started,
                   peak_allocated_gib=torch.cuda.max_memory_allocated() / 1024**3,
                   peak_reserved_gib=torch.cuda.max_memory_reserved() / 1024**3)
    receipt["artifacts"] = {p.name: digest(p) for p in args.output.iterdir() if p.is_file() and p.name != "RUN_RECEIPT.json"}
    write_json(args.output / "RUN_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "completed_evaluations": 1024,
                      "forward_calls": counter.forward_calls, "runtime_seconds": receipt["runtime_seconds"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prepare", "run"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-freeze", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--max-seconds", type=float, default=1200)
    args = parser.parse_args()
    require(0 < args.max_seconds < 1800, "Worker cap must be positive and below total 1800-second host cap")
    needed = ["csv"] if args.mode == "prepare" else ["prepared", "source_root", "source_archive", "weights"]
    require(all(getattr(args, name) is not None for name in needed), "Missing arguments: " + ", ".join(needed))
    require(not args.output.exists() or not any(args.output.iterdir()), "Use fresh output; preserve previous attempts")
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    if args.mode == "run" and hasattr(signal, "SIGALRM"):
        def timeout(signum, frame):
            raise TimeoutError("Worker wall-time cap reached; external host stop remains authoritative")
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.max_seconds)
    try:
        if args.mode == "prepare":
            prepare(args)
        else:
            run(args, started)
    except BaseException as exc:
        write_json(args.output / "FAILED_RUN_RECEIPT.json", dict(status="HOLD_EXECUTION_FAILURE", mode=args.mode,
                   exception_type=type(exc).__name__, exception_message=str(exc), traceback=traceback.format_exc(),
                   runtime_seconds=time.monotonic() - started, completed_utc=utc(), worker_sha256=digest(__file__),
                   scientific_effect_claimed=False, hai_accessed=False))
        raise
    finally:
        if args.mode == "run" and hasattr(signal, "SIGALRM"):
            signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    main()
