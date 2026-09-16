"""Independent D0 evidence audit. No worker/model imports; no model execution.

Rebuilds the fixed design from the pinned CSV and recomputes decisions from exact
saved forecasts. Passing synthetic controls never supplies a scientific result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

import numpy as np


PIPELINES = (
    "joint_native3", "independent_native3",
    "joint_channel0_clip_minus3_plus3", "joint_channel0_causal_sma5",
)
STATES = ("clean", "step1", "step3", "step6", "ramp1", "ramp3", "ramp6", "clean_repeat")
SOURCE_SHA256 = "e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584"
SOURCE_REVISION = "8cb0628371af142e16b8c232cc9fbf667ffb12f9"
MODEL_REVISION = "43046b85ec22d584a13f8098c2ed39c889e129c2"
WEIGHTS_SHA256 = "a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da"
SOURCE_ARCHIVE_SHA256 = "ecb62c7cc793937991bbaf4a481d60ac74e84724db3e9d6ea457b2b350f11692"
SOURCE_FILES = {
    "src/timesfm3/torch/configs.py": "911e29ab7aa54b34dfa3ca5fe89b2564055b20da87ad490d2c63d64fa4fd3739",
    "src/timesfm3/torch/evaluator.py": "4ad0ddc5e264206cf6db706b493c2b4f20bf6698e89b990a4c37c15089971af2",
    "src/timesfm3/torch/model.py": "474b8035db514d852e6358c73ebd1ba90dcd25f17d1ecf4e5bb884ca788e7dbf",
    "src/timesfm3/torch/timesfm3_forecaster.py": "33870c9676be6aab4e62c45a0a89bc1d6c49ca3149ddc46a19c6d9e2c23e0037",
}


class AuditError(ValueError):
    """Saved evidence fails a fixed protocol or provenance requirement."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes(order="C")).hexdigest()


def exact_equal(left: np.ndarray, right: np.ndarray) -> bool:
    return left.shape == right.shape and left.dtype == right.dtype and array_sha256(left) == array_sha256(right)


def source_values(path: Path) -> np.ndarray:
    require(sha256_file(path) == SOURCE_SHA256, "source CSV SHA-256 differs from the frozen public source")
    values: list[float] = []
    # Only the value column is parsed. The pinned file permits a single header;
    # reading stops at row 1006 and neither labels nor later values are used.
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row_number, row in enumerate(csv.reader(stream)):
            if not row:
                raise AuditError("empty source CSV row")
            try:
                value = float(row[0])
            except ValueError:
                require(row_number == 0 and not values, "nonnumeric value after source header")
                continue
            values.append(value)
            if len(values) == 1007:
                break
    result = np.asarray(values, dtype=np.float64)
    require(result.shape == (1007,) and np.isfinite(result).all(), "expected 1007 finite permitted values")
    return result


def reconstruct(values: np.ndarray) -> dict[str, np.ndarray]:
    """Independent literal implementation of the frozen construction.

    In particular, SMA is a separate finite-window reduction at every context
    position, including its first four positions. Only final inputs are cast.
    """
    require(values.dtype == np.float64 and values.shape == (1007,), "invalid source-value dtype/shape")
    require(np.isfinite(values).all(), "nonfinite source values")
    mean = values[:256].mean(dtype=np.float64)
    sd = values[:256].std(ddof=0, dtype=np.float64)
    require(sd >= 1e-6, "commissioning population SD below 1e-6")
    z = (values - mean) / sd
    noise = np.random.Generator(np.random.PCG64(20260915)).standard_normal((1007, 3)) * 0.01
    derived = np.empty((1003, 3), dtype=np.float64)
    derived[:, 0] = z[4:] + noise[4:, 0]
    derived[:, 1] = 0.8 * z[4:] + 0.2 * z[3:-1] + noise[4:, 1]
    derived[:, 2] = 0.6 * z[4:] + 0.4 * z[:-4] + noise[4:, 2]
    origins = np.asarray([384 + j * 622 // 31 for j in range(32)], dtype=np.int64)
    targets = np.stack([derived[e - 4] for e in origins])
    inputs = np.empty((4, 32, 8, 3, 128), dtype=np.float32)
    for pi in range(4):
        for oi, origin in enumerate(origins):
            clean = derived[origin - 132:origin - 4].T
            for si in range(8):
                x = clean.copy()
                if si in (1, 2, 3):
                    x[0, -64:] += (1.0, 3.0, 6.0)[si - 1]
                elif si in (4, 5, 6):
                    x[0, -64:] += np.linspace(0.0, (1.0, 3.0, 6.0)[si - 4], 64, dtype=np.float64)
                if pi == 2:
                    x[0] = np.clip(x[0], -3.0, 3.0)
                elif pi == 3:
                    history = x[0].copy()
                    for t in range(128):
                        x[0, t] = history[max(0, t - 4):t + 1].mean(dtype=np.float64)
                inputs[pi, oi, si] = x.astype(np.float32)
    return {"inputs": inputs, "targets": targets, "origins": origins,
            "values": values, "noise": noise, "derived": derived}


def check_inputs(saved: dict[str, np.ndarray], expected: dict[str, np.ndarray]) -> None:
    require(set(saved) == set(expected), "inputs.npz key set differs from frozen schema")
    for name, reference in expected.items():
        candidate = saved[name]
        require(np.isfinite(candidate).all(), f"nonfinite {name}")
        require(exact_equal(candidate, reference), f"{name} differs from independent float64 construction/final float32 cast")
    x = saved["inputs"]
    require(exact_equal(x[:, :, 0], x[:, :, 7]), "clean repeat has different input bytes")
    protected = np.broadcast_to(x[0:1, :, 0:1, 1:, :], x[:, :, :, 1:, :].shape).copy()
    require(exact_equal(x[:, :, :, 1:, :], protected), "protected input channels were modified")


def compute_metrics(points: np.ndarray, targets: np.ndarray) -> dict[str, Any]:
    require(points.shape == (4, 32, 8, 3), "forecast shape differs from (4,32,8,3)")
    require(targets.shape == (32, 3), "target shape differs from (32,3)")
    require(np.isfinite(points).all() and np.isfinite(targets).all(), "nonfinite metric inputs")
    f = points.astype(np.float64)
    y = targets.astype(np.float64)
    repeat = float(np.max(np.abs(f[:, :, 7] - f[:, :, 0])))
    floor = max(1e-5, 10.0 * repeat)
    clean = f[:, :, 0, 1:]
    perturbed = f[:, :, 1:7, 1:]
    spillover = np.mean(np.abs(perturbed - clean[:, :, None, :]), axis=-1)
    inflation = np.mean(np.abs(perturbed - y[None, :, None, 1:])
                        - np.abs(clean[:, :, None, :] - y[None, :, None, 1:]), axis=-1)
    # Make the 32-origin reduction contiguous for NumPy's stable pairwise sum.
    # No rounding/tolerance is inserted into the fixed decision boundaries.
    mean_inflation = np.ascontiguousarray(inflation.transpose(0, 2, 1)).mean(axis=-1)
    mean_spillover = np.ascontiguousarray(spillover.transpose(0, 2, 1)).mean(axis=-1)
    qualifying_counts = ((spillover >= 0.05) & (spillover > floor)).sum(axis=1)
    clean_mae = np.abs(clean - y[None, :, 1:]).mean(axis=(1, 2))
    qualifying = (qualifying_counts[0] >= 8) & (mean_inflation[0] >= 0.02)
    # Scientific spillover remains the protected-channel mean. The pre-run
    # technical interpretation additionally requires each independent scalar
    # to stay within the same numerical floor (no cancellation by averaging).
    independent_scalar_max = float(np.max(np.abs(perturbed[1] - clean[1, :, None, :])))
    independent_spillover_max = float(np.max(spillover[1]))
    mechanism = int(qualifying.sum()) >= 2
    adequate: list[str] = []
    if mechanism:
        for pi in (2, 3):
            if np.all(mean_inflation[pi, qualifying] <= 0.005) and clean_mae[pi] - clean_mae[0] <= 0.01:
                adequate.append(PIPELINES[pi])
    operational_reasons: list[str] = []
    if repeat > 1e-5:
        operational_reasons.append("maximum clean-repeat discrepancy exceeds 1e-5")
    if independent_spillover_max > floor:
        operational_reasons.append("independent-channel spillover exceeds numerical floor")
    if independent_scalar_max > floor:
        operational_reasons.append("individual independent protected-channel displacement exceeds numerical floor")
    if operational_reasons:
        decision = "HOLD_OPERATIONAL"
    elif not mechanism:
        decision = "HOLD_CROSS_CHANNEL_HARM_SCALE_UP"
    elif adequate:
        decision = "HOLD_COMPLEX_DEFENSE"
    else:
        decision = "ELIGIBLE_FOR_SEPARATE_D1_DESIGN_ONLY"
    return {
        "decision": decision, "operational_hold_reasons": operational_reasons,
        "maximum_clean_repeat_discrepancy": repeat, "numerical_floor": floor,
        "independent_maximum_spillover": independent_spillover_max,
        "independent_maximum_scalar_displacement": independent_scalar_max,
        "independent_scalar_gate_interpretation": "each independent protected-channel point forecast must stay within the same point-repeat numerical floor",
        "mechanism_numerical_conditions_met": mechanism,
        "qualifying_joint_variants": [STATES[i + 1] for i in np.flatnonzero(qualifying)],
        "adequate_simple_controls": adequate,
        "context_denominator": 32, "clean_mae_scalar_denominator": 64,
        "pipelines": {
            name: {"clean_off_channel_mae": float(clean_mae[pi]),
                   "clean_mae_delta_from_raw_joint": float(clean_mae[pi] - clean_mae[0]),
                   "variants": {
                       STATES[vi + 1]: {
                           "mean_spillover": float(mean_spillover[pi, vi]),
                           "mean_error_inflation": float(mean_inflation[pi, vi]),
                           "contexts_with_practical_spillover_above_floor": int(qualifying_counts[pi, vi]),
                           "spillover_by_origin": spillover[pi, :, vi].tolist(),
                           "error_inflation_by_origin": inflation[pi, :, vi].tolist(),
                       } for vi in range(6)}
                   } for pi, name in enumerate(PIPELINES)},
    }


def check_observations(rows: list[dict[str, Any]], inputs: dict[str, np.ndarray],
                       forecasts: dict[str, np.ndarray]) -> dict[str, Any]:
    require(len(rows) == 1024, "expected exactly 1024 observation identities")
    seen: set[tuple[int, int, int]] = set()
    totals = {"forward_calls": 0, "tensor_batch_sequences": 0, "tensor_channel_sequences": 0}
    elapsed = 0.0
    for row in rows:
        key = tuple(row.get(k) for k in ("pi", "oi", "si"))
        require(all(type(v) is int for v in key), "observation indexes must be integers")
        pi, oi, si = key
        require(0 <= pi < 4 and 0 <= oi < 32 and 0 <= si < 8, "out-of-range observation identity")
        require(key not in seen, "duplicate observation identity")
        seen.add(key)
        require(row.get("pipeline") == PIPELINES[pi] and row.get("state") == STATES[si], "observation label/index mismatch")
        require(row.get("origin") == int(inputs["origins"][oi]), "observation origin mismatch")
        require(row.get("evaluation_index") == pi * 256 + oi * 8 + si, "evaluation_index mismatch")
        require(row.get("input_sha256") == array_sha256(inputs["inputs"][pi, oi, si]), "observation model-input hash mismatch")
        require(row.get("target_sha256") == array_sha256(inputs["targets"][oi]), "observation target hash mismatch")
        require(exact_equal(np.asarray(row.get("forecast"), dtype=np.float32), forecasts["points"][pi, oi, si]), "observation forecast mismatch")
        require(exact_equal(np.asarray(row.get("quantiles"), dtype=np.float32), forecasts["quantiles"][pi, oi, si]), "observation quantiles mismatch")
        require(row.get("point_dtype") == "float32" and row.get("quantile_dtype") == "float32", "native output dtype mismatch")
        check_routing(row, inputs["inputs"][pi, oi, si], pi)
        expected = {"forward_calls": 3 if pi == 1 else 1,
                    "tensor_batch_sequences": 3 if pi == 1 else 1,
                    "tensor_channel_sequences": 3}
        for name, count in expected.items():
            require(type(row.get(name)) is int and row[name] == count, f"{name} incompatible with native {'independent' if pi == 1 else 'joint'} routing")
            totals[name] += count
        duration = row.get("elapsed_seconds")
        require(isinstance(duration, (int, float)) and np.isfinite(duration) and duration >= 0, "invalid observation elapsed time")
        elapsed += duration
    require(seen == {(pi, oi, si) for pi in range(4) for oi in range(32) for si in range(8)}, "missing assigned evaluation")
    return {"evaluations": len(rows), **totals, "summed_evaluation_seconds": elapsed}


def check_routing(row: dict[str, Any], context: np.ndarray, pipeline_index: int) -> None:
    independent = pipeline_index == 1
    require(type(row.get("univariate")) is bool and row["univariate"] == independent, "wrong univariate API routing")
    calls = row.get("decode_calls_detail", [])
    require(len(calls) == (3 if independent else 1), "wrong native decode routing count")
    for ci, call in enumerate(calls):
        expected = context[ci:ci + 1][None] if independent else context[None]
        require(call.get("target_shape") == list(expected.shape), "native decode target shape/routing mismatch")
        require(call.get("target_sha256") == array_sha256(expected), "native decode target bytes/routing mismatch")
        require(call.get("dtype") == "torch.float32", "native decode dtype mismatch")
        require(call.get("horizon") == 64, "native decode horizon differs from pinned 64-step patch expansion")
    forwards = row.get("forward_calls_detail", [])
    require(len(forwards) == len(calls), "wrong native forward routing count")
    for call in forwards:
        shape = call.get("values_shape", [])
        require(shape == [1, 1 if independent else 3, 6, 32], "native forward tensor shape/routing mismatch")
        require(call.get("dtype") == "torch.float32", "native forward dtype mismatch")


def check_forecasts(saved: dict[str, np.ndarray]) -> None:
    expected = {"points": ((4, 32, 8, 3), np.dtype("float32")),
                "quantiles": ((4, 32, 8, 3, 9), np.dtype("float32")),
                "completed": ((4, 32, 8), np.dtype("bool"))}
    require(set(saved) == set(expected), "forecasts.npz key set differs from frozen schema")
    for name, (shape, dtype) in expected.items():
        require(saved[name].shape == shape and saved[name].dtype == dtype, f"invalid {name} shape/dtype")
        require(np.isfinite(saved[name]).all(), f"nonfinite {name}")
    require(saved["completed"].all(), "incomplete assigned evaluations")
    require(np.all(np.diff(saved["quantiles"].astype(np.float64), axis=-1) >= 0), "unsorted quantiles")
    require(exact_equal(saved["points"], saved["quantiles"][..., 4]), "point forecast is not native sorted median quantile")


def quantile_repeat_max(quantiles: np.ndarray) -> float:
    result = float(np.max(np.abs(quantiles[:, :, 7].astype(np.float64) - quantiles[:, :, 0].astype(np.float64))))
    require(result <= 1e-5, "clean-repeat quantile discrepancy exceeds separate technical integrity ceiling 1e-5")
    return result


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def descriptors_match(arrays: dict[str, np.ndarray], descriptions: dict[str, Any], label: str) -> None:
    require(set(arrays) == set(descriptions), f"{label} array descriptor key mismatch")
    for name, array in arrays.items():
        expected = {"shape": list(array.shape), "dtype": str(array.dtype), "sha256": array_sha256(array)}
        require(descriptions[name] == expected, f"{label} {name} hash/shape/dtype mismatch")


def check_manifest(manifest: dict[str, Any], arrays: dict[str, np.ndarray],
                   directory: Path, execution_root: Path) -> dict[str, Any]:
    expected_fields = {
        "schema_version": 1, "source_csv_sha256": SOURCE_SHA256,
        "source_revision": SOURCE_REVISION, "model_revision": MODEL_REVISION,
        "weights_sha256": WEIGHTS_SHA256, "pipelines": list(PIPELINES), "states": list(STATES),
        "origins": arrays["origins"].tolist(), "source_value_rows_inclusive": [0, 1006],
        "labels_parsed": False, "hai_accessed": False, "derived_array_first_time_index": 4,
        "actual_model_calls": 0, "quantile_levels": [i / 10 for i in range(1, 10)],
    }
    for name, expected in expected_fields.items():
        require(manifest.get(name) == expected, f"prepared manifest {name} mismatch")
    require(manifest.get("inputs_npz_sha256") == sha256_file(directory / "inputs.npz"), "prepared input archive hash mismatch")
    descriptors_match(arrays, manifest.get("arrays", {}), "prepared")
    expected_identities = []
    for pi in range(4):
        for oi in range(32):
            for si in range(8):
                expected_identities.append({
                    "evaluation_index": pi * 256 + oi * 8 + si, "pi": pi, "oi": oi, "si": si,
                    "pipeline": PIPELINES[pi], "origin": int(arrays["origins"][oi]), "state": STATES[si],
                    "input_sha256": array_sha256(arrays["inputs"][pi, oi, si]),
                    "target_sha256": array_sha256(arrays["targets"][oi]),
                })
    require(manifest.get("identities") == expected_identities, "prepared identities incomplete, duplicated, reordered, or inconsistent")
    values = arrays["values"]
    expected_commissioning = {"mean": float(values[:256].mean(dtype=np.float64)),
                             "population_sd": float(values[:256].std(ddof=0, dtype=np.float64)),
                             "commissioning_rows_inclusive": [0, 255]}
    require(manifest.get("commissioning") == expected_commissioning, "commissioning statistics differ from source reconstruction")
    freeze_path = directory / "runtime_freeze.json"
    freeze = load_json(freeze_path)
    require(manifest.get("runtime_freeze_sha256") == sha256_file(freeze_path), "runtime freeze hash mismatch")
    for name, expected in {"schema_version": 1, "source_revision": SOURCE_REVISION,
                           "weights_sha256": WEIGHTS_SHA256, "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
                           "model_dtype": "float32"}.items():
        require(freeze.get(name) == expected, f"runtime freeze {name} mismatch")
    require(freeze.get("packages", {}).get("numpy") == manifest.get("numpy"), "preparation NumPy differs from freeze")
    require(freeze.get("python_major_minor") == "3.10", "production Python major/minor must match qualified 3.10 runtime")
    frozen_files = freeze.get("files", {})
    require("code/d0_worker.py" in frozen_files and "code/audit_d0.py" in frozen_files,
            "worker and independent auditor must be frozen")
    for name, expected in frozen_files.items():
        local = (execution_root / name).resolve()
        require(local.is_relative_to(execution_root.parent.resolve()), "frozen file escapes permitted Praxis parent")
        require(local.is_file() and sha256_file(local) == expected, f"frozen local implementation/protocol changed: {name}")
    require(manifest.get("worker_sha256") == frozen_files["code/d0_worker.py"], "prepared worker hash differs from freeze")
    plan = execution_root.parent / "010_development_20260915"
    require(manifest.get("protocol_sha256") == sha256_file(plan / "D0_PROTOCOL.md"), "frozen protocol document changed")
    require(manifest.get("spec_sha256") == sha256_file(plan / "D0_SPEC.json"), "frozen D0 spec changed")
    return freeze


def archive_source_hashes(path: Path) -> dict[str, str]:
    require(sha256_file(path) == SOURCE_ARCHIVE_SHA256, "source archive differs from frozen TimesFM revision")
    result: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            parts = Path(entry.filename).parts
            require(not Path(entry.filename).is_absolute() and ".." not in parts, "unsafe source archive member")
            if not entry.is_dir() and len(parts) >= 2 and parts[-1].endswith(".py"):
                name = Path(*parts[1:]).as_posix()
                require(name not in result, "duplicate source archive Python member")
                result[name] = hashlib.sha256(archive.read(entry)).hexdigest()
    for name, expected in SOURCE_FILES.items():
        require(result.get(name) == expected, f"pinned API source hash mismatch: {name}")
    return result


def check_provenance(receipt: dict[str, Any], started: dict[str, Any], manifest: dict[str, Any],
                     freeze: dict[str, Any], source_hashes: dict[str, str], directory: Path) -> None:
    expected = {"schema_version": 1, "source_revision": SOURCE_REVISION,
                "model_revision": MODEL_REVISION, "weights_sha256": WEIGHTS_SHA256,
                "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
                "source_file_sha256": source_hashes, "total_assigned_evaluations": 1024,
                "hai_accessed": False, "median_quantile_index": 4,
                "quantile_levels": [i / 10 for i in range(1, 10)],
                "prepared_manifest_sha256": sha256_file(directory / "MANIFEST.json"),
                "runtime_freeze_sha256": sha256_file(directory / "runtime_freeze.json"),
                "worker_sha256": manifest["worker_sha256"]}
    for name, value in expected.items():
        require(receipt.get(name) == value and started.get(name) == value, f"run source/config provenance mismatch: {name}")
    require(receipt.get("status") == "COMPLETE_PENDING_INDEPENDENT_AUDIT", "run receipt does not certify complete execution")
    require(receipt.get("completed_evaluations") == 1024, "run receipt evaluation count mismatch")
    require(started.get("status") == "RUN_STARTED_NOT_COMPLETE", "invalid run-start receipt status")
    for name in ("model_config", "forecast_config", "routing", "environment", "loaded_source_modules",
                 "model_parameter_dtypes", "model_parameter_devices", "native_model_config", "native_use_variate_attention"):
        require(receipt.get(name) == started.get(name), f"run-start/run-end {name} drift")
    config = receipt.get("model_config", {})
    for name, value in {"use_variate_attention": True, "per_core_batch_size": 1, "device": "cuda", "local_files_only": True}.items():
        require(config.get(name) == value, f"native ModelConfig {name} differs from frozen route")
    require(config.get("checkpoint_path"), "actual checkpoint path missing")
    require(receipt.get("native_use_variate_attention") is True, "observed native variate attention was not enabled")
    native = receipt.get("native_model_config", {})
    for name, value in {"use_variate_attention": True, "input_patch_len": 32, "output_patch_len": 64,
                       "quantiles": [i / 10 for i in range(1, 10)]}.items():
        require(native.get(name) == value, f"actual native architecture mismatch: {name}")
    require(isinstance(native.get("residual_block_config"), dict) and isinstance(native.get("transformer_config"), dict),
            "actual native architecture subconfigs missing")
    options = {"horizon": 1, "return_quantiles": True, "use_symmetric_averaging": False,
               "make_positive": False, "sort_quantiles": True, "use_znorm": False, "padding_mode": "none"}
    require(receipt.get("forecast_config") == options, "native prediction API options differ from protocol")
    require(receipt.get("routing") == {pipeline: {"univariate": pi == 1} for pi, pipeline in enumerate(PIPELINES)},
            "recorded pipeline API routing differs from protocol")
    loaded = receipt.get("loaded_source_modules", {})
    loaded_paths = set()
    require(bool(loaded), "loaded model-module evidence missing")
    for name, entry in loaded.items():
        require(name == "timesfm3" or name.startswith("timesfm3."), "unexpected model module namespace")
        relative = entry.get("path")
        require(relative in source_hashes and entry.get("sha256") == source_hashes[relative], "executed module does not match pinned source archive")
        loaded_paths.add(relative)
    require(set(SOURCE_FILES).issubset(loaded_paths), "required pinned API/config/model modules were not recorded as loaded")
    require(receipt.get("model_parameter_dtypes") == ["torch.float32"], "model parameters not uniformly float32")
    require(receipt.get("model_parameter_devices") == ["cuda:0"], "model parameters not uniformly on the one CUDA device")
    env = receipt.get("environment", {})
    require(env.get("packages") == freeze["packages"], "production packages differ from executable freeze")
    require(env.get("numpy") == freeze["packages"]["numpy"], "production NumPy mismatch")
    require(env.get("torch") == freeze["packages"]["torch"], "production Torch mismatch")
    require(".".join(env.get("python", "").split(".")[:2]) == freeze["python_major_minor"], "production Python mismatch")
    for name, value in {"model_dtype": "float32", "deterministic_algorithms": True, "tf32": False,
                       "cudnn_benchmark": False, "cublas_workspace_config": ":4096:8", "torch_threads": 4}.items():
        require(env.get(name) == value, f"production device/numeric behavior differs: {name}")
    require(isinstance(env.get("device"), str) and bool(env["device"]), "GPU identity missing")
    require(0 < receipt.get("maximum_worker_seconds", 0) < 1800, "worker cap not below 30-minute host cap")
    require(0 <= receipt.get("runtime_seconds", -1) < receipt["maximum_worker_seconds"], "worker exceeded frozen cap")
    for name in ("peak_allocated_gib", "peak_reserved_gib"):
        require(isinstance(receipt.get(name), (int, float)) and np.isfinite(receipt[name]) and receipt[name] >= 0,
                f"missing/nonfinite memory accounting: {name}")
    artifacts = receipt.get("artifacts", {})
    required_artifacts = {"RUN_STARTED.json", "MANIFEST.json", "runtime_freeze.json", "inputs.npz", "forecasts.npz", "observations.jsonl", "COUNTERS.json", "PROGRESS.json"}
    require(required_artifacts.issubset(artifacts), "run artifact hash inventory incomplete")
    for name, expected_hash in artifacts.items():
        path = (directory / name).resolve()
        require(path.parent == directory.resolve(), "run artifact path escapes output directory")
        require(path.is_file() and sha256_file(path) == expected_hash, f"run artifact hash mismatch: {name}")


def audit_directory(directory: Path, source_csv: Path, execution_root: Path,
                    source_archive: Path | None = None, prepared_only: bool = False) -> dict[str, Any]:
    summary: dict[str, Any] = {"schema_version": 1, "audit_status": "FAIL", "decision": "HOLD_EVIDENCE_INTEGRITY",
                              "prepared_only": prepared_only, "errors": [], "audit_numpy": np.__version__,
                              "auditor_sha256": sha256_file(Path(__file__)), "scientific_effect_claimed": False}
    try:
        values = source_values(source_csv)
        expected = reconstruct(values)
        with np.load(directory / "inputs.npz", allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        check_inputs(arrays, expected)
        manifest = load_json(directory / "MANIFEST.json")
        freeze = check_manifest(manifest, arrays, directory, execution_root)
        summary["input_array_sha256"] = {name: array_sha256(array) for name, array in arrays.items()}
        summary["source_csv_sha256"] = SOURCE_SHA256
        summary["runtime_freeze_sha256"] = sha256_file(directory / "runtime_freeze.json")
        if prepared_only:
            summary.update(audit_status="PASS", decision="INPUTS_AND_FREEZE_VERIFIED_NO_MODEL_RESULTS",
                           prepared_evaluations=1024)
            return summary
        require(source_archive is not None, "full audit requires --source-archive for independent source-bound provenance")
        source_hashes = archive_source_hashes(source_archive)
        with np.load(directory / "forecasts.npz", allow_pickle=False) as archive:
            forecasts = {name: archive[name] for name in archive.files}
        check_forecasts(forecasts)
        rows = [json.loads(line) for line in (directory / "observations.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        accounting = check_observations(rows, arrays, forecasts)
        receipt = load_json(directory / "RUN_RECEIPT.json")
        started = load_json(directory / "RUN_STARTED.json")
        check_provenance(receipt, started, manifest, freeze, source_hashes, directory)
        descriptors_match(forecasts, receipt.get("output_arrays", {}), "forecast")
        counters = load_json(directory / "COUNTERS.json")
        for name in ("forward_calls", "tensor_batch_sequences", "tensor_channel_sequences"):
            require(receipt.get(name) == accounting[name] == counters.get(name), f"receipt/counter {name} mismatch")
        require(counters.get("completed_evaluations") == 1024 and receipt.get("actual_model_calls") == 1536,
                "actual evaluation/native call accounting mismatch")
        metrics = compute_metrics(forecasts["points"], arrays["targets"])
        summary["metrics"] = metrics
        summary["accounting"] = {**accounting, "runtime_seconds": receipt["runtime_seconds"],
                                 "peak_allocated_gib": receipt["peak_allocated_gib"],
                                 "peak_reserved_gib": receipt["peak_reserved_gib"]}
        require(receipt.get("maximum_clean_repeat_point_discrepancy") == metrics["maximum_clean_repeat_discrepancy"], "worker clean-repeat point summary mismatch")
        quantile_max = quantile_repeat_max(forecasts["quantiles"])
        require(receipt.get("maximum_clean_repeat_quantile_discrepancy") == quantile_max, "worker quantile repeat summary mismatch")
        summary["maximum_clean_repeat_quantile_discrepancy"] = quantile_max
        summary["quantile_repeat_gate_interpretation"] = "separate conservative technical-integrity ceiling <=1e-5; endpoint floor uses point forecasts only"
        summary.update(audit_status="PASS", decision=metrics["decision"])
    except (AuditError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        summary["errors"].append(f"{type(error).__name__}: {error}")
    return summary


def write_results(path: Path, summary: dict[str, Any]) -> None:
    metrics = summary.get("metrics", {})
    lines = ["# D0 mechanism screen: audited results", "",
             f"**Audit: {summary['audit_status']}. Decision: {summary['decision']}.**", ""]
    if summary.get("errors"):
        lines += ["Evidence failures:", ""] + [f"- {error}" for error in summary["errors"]] + [""]
    if metrics:
        lines += [f"Qualifying raw-joint variants: {', '.join(metrics['qualifying_joint_variants']) or 'none'}.",
                  f"Clean-repeat maximum: {metrics['maximum_clean_repeat_discrepancy']:.9g}; numerical floor: {metrics['numerical_floor']:.9g}.",
                  f"Independent maximum spillover: {metrics['independent_maximum_spillover']:.9g}.", "",
                  "| Pipeline | Clean off-channel MAE | Change from raw joint |", "|---|---:|---:|"]
        for name, row in metrics["pipelines"].items():
            lines.append(f"| {name} | {row['clean_off_channel_mae']:.9g} | {row['clean_mae_delta_from_raw_joint']:.9g} |")
        lines += ["", "| Pipeline | Variant | Contexts with spillover >=0.05 and above floor | Mean error inflation (all 32) |", "|---|---|---:|---:|"]
        for name, pipeline in metrics["pipelines"].items():
            for variant, row in pipeline["variants"].items():
                lines.append(f"| {name} | {variant} | {row['contexts_with_practical_spillover_above_floor']} | {row['mean_error_inflation']:.9g} |")
        lines += ["", "Adequate simple controls: " + (", ".join(metrics["adequate_simple_controls"]) or "none") + ".", ""]
    if summary.get("accounting"):
        accounting = summary["accounting"]
        lines += [f"Accounting: {accounting['evaluations']} evaluations; {accounting['forward_calls']} native forward calls; "
                  f"{accounting['tensor_batch_sequences']} tensor batch sequences; {accounting['tensor_channel_sequences']} tensor channel sequences.", ""]
    lines += ["## Scope", "", "This is a descriptive mechanism screen using 32 overlapping origins from one previously inspected public series with semisynthetic channels. It does not establish independent incident replication, a novel defense, attack detection, persistent retention, or recovery. A positive mechanism result only permits a separately frozen D1 design.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--execution-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prepared-only", action="store_true")
    args = parser.parse_args()
    summary = audit_directory(args.run_dir, args.source_csv, args.execution_root,
                              args.source_archive, args.prepared_only)
    output = args.output_dir or args.run_dir
    output.mkdir(parents=True, exist_ok=True)
    name = "PREPARED_AUDIT.json" if args.prepared_only else "AUDIT.json"
    (output / name).write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    if not args.prepared_only:
        write_results(output / "RESULTS.md", summary)
    print(json.dumps({"audit_status": summary["audit_status"], "decision": summary["decision"],
                      "errors": summary["errors"], "summary": str(output / name)}, allow_nan=False))
    return 0 if summary["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
