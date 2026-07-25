#!/usr/bin/env python
"""Capture the PX-057 H4 GPU runtime and create the Phase A freeze gate."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import (
    committed_file_info,
    read_json,
    sha256_file,
    write_json,
)


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def validate_static_config(config_path: Path, config: dict[str, Any]) -> None:
    if config["protocol_status"] != "PRE_DATA_FROZEN":
        raise ValueError("protocol_status must be PRE_DATA_FROZEN")
    committed_file_info(ROOT, config_path)
    phase = config["phase_a"]
    requirements_path = repo_path(phase["requirements_path"])
    prompt_path = repo_path(config["generation"]["prompt_template_path"])
    if sha256_file(requirements_path) != phase["requirements_sha256"]:
        raise ValueError("requirements lock hash mismatch")
    if sha256_file(prompt_path) != config["generation"]["prompt_template_sha256"]:
        raise ValueError("prompt-template hash mismatch")


def config_schema_checks(config: dict[str, Any]) -> dict[str, bool]:
    risk = config["risk_control"]
    grid = {
        (int(min_step), int(patience), float(threshold))
        for min_step in risk["policy_grid"]["min_step"]
        for patience in risk["policy_grid"]["patience"]
        for threshold in risk["policy_grid"]["confidence_threshold"]
    }
    ordered = [
        (int(min_step), int(patience), float(threshold))
        for min_step in risk["fixed_sequence_order"]["min_step"]
        for patience in risk["fixed_sequence_order"]["patience"]
        for threshold in risk["fixed_sequence_order"]["confidence_threshold"]
    ]
    cells = config["cells"]
    expected_locks = [str(cell["ltt_lock_manifest"]) for cell in cells]
    return {
        "experiment_identity": (
            config["px_id"] == "PX-057"
            and config["protocol_revision"] == "2.1-predata-correction"
        ),
        "three_unique_cells": (
            len(cells) == 3
            and len({str(cell["cell_id"]) for cell in cells}) == 3
        ),
        "registered_cell_matrix": (
            {
                (cell["model_key"], cell["dataset_key"])
                for cell in cells
            }
            == {
                ("second_model", "gsm8k"),
                ("gate2_model", "arc_challenge"),
                ("second_model", "arc_challenge"),
            }
        ),
        "registered_sample_sizes": (
            int(config["split_design"]["calibration_n"]) == 500
            and int(config["split_design"]["holdout_n"]) == 300
            and int(config["generation"]["rounds"]) == 8
        ),
        "registered_policy_grid": len(grid) == 30,
        "fixed_order_is_grid_permutation": (
            len(ordered) == 30 and len(set(ordered)) == 30 and set(ordered) == grid
        ),
        "family_error_allocation": math.isclose(
            float(risk["cell_delta"]),
            float(risk["family_delta"]) / len(cells),
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "registered_risk_threshold": math.isclose(
            float(risk["alpha"]), 0.02, rel_tol=0.0, abs_tol=1e-12
        ),
        "holdout_lock_list_matches_cells": (
            config["holdout_lock_manifests"] == expected_locks
        ),
        "arc_manifests_reused": (
            len(
                {
                    cell["calibration_manifest"]
                    for cell in cells
                    if cell["dataset_key"] == "arc_challenge"
                }
            )
            == 1
            and len(
                {
                    cell["holdout_manifest"]
                    for cell in cells
                    if cell["dataset_key"] == "arc_challenge"
                }
            )
            == 1
        ),
    }


def capture_runtime(
    config_path: Path,
    *,
    output_path: Path,
    container_image_digest: str,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"{output_path} already exists")
    if output_path.resolve() != repo_path(
        read_json(config_path)["phase_a"]["runtime_manifest"]
    ).resolve():
        raise ValueError("runtime-manifest path differs from the frozen config")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", container_image_digest):
        raise ValueError("container image digest must be sha256:<64 hex>")
    if os.environ.get("PX057_CONTAINER_IMAGE_DIGEST") != container_image_digest:
        raise ValueError(
            "PX057_CONTAINER_IMAGE_DIGEST must equal --container-image-digest"
        )
    config = read_json(config_path)
    validate_static_config(config_path, config)
    phase = config["phase_a"]
    python_major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    if python_major_minor != phase["required_python_major_minor"]:
        raise ValueError("Python major/minor differs from the frozen config")
    packages = {
        package: importlib.metadata.version(package)
        for package in phase["required_packages"]
    }
    if packages != phase["required_packages"]:
        raise ValueError("installed direct package versions differ from the lock")

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise ValueError("Phase A runtime capture requires a CUDA GPU")
    torch.manual_seed(int(config["generation"]["seed"]))
    torch.cuda.manual_seed_all(int(config["generation"]["seed"]))
    model_smokes: dict[str, Any] = {}
    for model_key, model_config in config["models"].items():
        tokenizer = AutoTokenizer.from_pretrained(
            model_config["model_id"],
            revision=model_config["revision"],
            local_files_only=bool(model_config.get("local_files_only", False)),
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_config["model_id"],
            revision=model_config["revision"],
            local_files_only=bool(model_config.get("local_files_only", False)),
            trust_remote_code=False,
            device_map=model_config["device_map"],
            torch_dtype="auto",
        )
        model.eval()
        prompt = phase["synthetic_model_smoke_prompt"]
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {
            key: value.to(model.device) for key, value in inputs.items()
        }
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=8,
                do_sample=False,
            )
        prompt_tokens = int(inputs["input_ids"].shape[1])
        generated = output[0][prompt_tokens:]
        response = tokenizer.decode(generated, skip_special_tokens=True)
        if len(generated) < 1:
            raise ValueError(f"{model_key}: synthetic generation was empty")
        chat_template = tokenizer.chat_template or ""
        model_smokes[model_key] = {
            "status": "PASS",
            "model_id": model_config["model_id"],
            "revision": model_config["revision"],
            "resolved_config_commit": getattr(
                model.config, "_commit_hash", None
            ),
            "model_class": model.__class__.__name__,
            "tokenizer_class": tokenizer.__class__.__name__,
            "model_dtype": str(next(model.parameters()).dtype),
            "chat_template_sha256": hashlib.sha256(
                chat_template.encode("utf-8")
            ).hexdigest(),
            "synthetic_prompt_sha256": hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest(),
            "generated_tokens": int(len(generated)),
            "response": response,
        }
        del output, inputs, model, tokenizer
        gc.collect()
        torch.cuda.empty_cache()
    all_packages = {
        distribution.metadata["Name"]: distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "H4_phase_a_runtime_capture",
        "status": "PASS",
        "scientific_data_generated": False,
        "synthetic_prompt_only": True,
        "config_sha256": sha256_file(config_path),
        "requirements_sha256": sha256_file(
            repo_path(phase["requirements_path"])
        ),
        "prompt_template_sha256": sha256_file(
            repo_path(config["generation"]["prompt_template_path"])
        ),
        "container_image_digest": container_image_digest.lower(),
        "python": sys.version,
        "python_major_minor": python_major_minor,
        "platform": platform.platform(),
        "packages": packages,
        "all_packages": dict(sorted(all_packages.items())),
        "torch": str(torch.__version__),
        "transformers": str(transformers.__version__),
        "cuda_runtime": str(torch.version.cuda),
        "cudnn": str(torch.backends.cudnn.version()),
        "cuda_devices": [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ],
        "model_smokes": model_smokes,
        "capture_base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
    }
    write_json(output_path, result)
    return result


def freeze_phase_a(
    config_path: Path, *, output_path: Path
) -> dict[str, Any]:
    config = read_json(config_path)
    validate_static_config(config_path, config)
    phase = config["phase_a"]
    expected_output = repo_path(phase["freeze_determination"])
    if output_path.resolve() != expected_output.resolve():
        raise ValueError("Phase A freeze path differs from the frozen config")
    if output_path.exists():
        raise FileExistsError(f"{output_path} already exists")
    runtime_path = repo_path(phase["runtime_manifest"])
    committed_file_info(ROOT, runtime_path)
    runtime = read_json(runtime_path)
    if (
        runtime.get("status") != "PASS"
        or runtime.get("scientific_data_generated") is not False
        or runtime.get("config_sha256") != sha256_file(config_path)
        or runtime.get("packages") != phase["required_packages"]
        or set(runtime.get("model_smokes", {})) != set(config["models"])
        or not re.fullmatch(
            r"sha256:[0-9a-f]{64}",
            str(runtime.get("container_image_digest", "")),
        )
        or not runtime.get("cuda_devices")
    ):
        raise ValueError("runtime manifest does not satisfy the frozen config")
    for model_key, model_config in config["models"].items():
        smoke = runtime["model_smokes"][model_key]
        if (
            smoke.get("status") != "PASS"
            or smoke.get("model_id") != model_config["model_id"]
            or smoke.get("revision") != model_config["revision"]
            or smoke.get("resolved_config_commit") != model_config["revision"]
            or int(smoke.get("generated_tokens", 0)) < 1
        ):
            raise ValueError(f"{model_key}: runtime smoke identity mismatch")
    schema_checks = config_schema_checks(config)
    if not all(schema_checks.values()):
        raise ValueError(f"config schema checks failed: {schema_checks}")
    from scripts.adjudicate_px057_h4 import check_splits

    design_checks = check_splits(config)
    if not all(design_checks.values()):
        raise ValueError(f"source/split design checks failed: {design_checks}")
    protected_paths = list(phase["protected_paths"]) + [
        phase["runtime_manifest"]
    ]
    protected_artifacts = {
        value: committed_file_info(ROOT, repo_path(value))
        for value in protected_paths
    }
    evidence_paths = [
        repo_path(value)
        for cell in config["cells"]
        for value in (
            *cell["output_dirs"].values(),
            cell["ltt_determination"],
            cell["ltt_lock_manifest"],
            cell["manual_audit_blinded"],
            cell["manual_audit"],
            cell["holdout_determination"],
        )
    ]
    populated = [
        path
        for path in evidence_paths
        if path.is_file() or (path.is_dir() and any(path.iterdir()))
    ]
    if populated:
        raise ValueError(
            "scientific or audit evidence exists before Phase A freeze: "
            + ", ".join(str(path) for path in populated)
        )
    test_command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_px057_h4_common.py",
        "tests/test_px057_h4_trace_collection.py",
        "tests/test_px057_h4_integrity.py",
        "tests/test_px057_adaptive_stopping.py",
        "tests/test_px057_trace_collection.py",
        "-q",
    ]
    test_result = subprocess.run(
        test_command, cwd=ROOT, capture_output=True, text=True, check=False
    )
    if test_result.returncode != 0:
        raise ValueError("focused PX-057 tests failed:\n" + test_result.stdout)
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if (
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                runtime["capture_base_commit"],
                base_commit,
            ],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("runtime capture base is not an ancestor of freeze base")
    remote_refs = [
        value.strip()
        for value in subprocess.check_output(
            ["git", "branch", "-r", "--contains", base_commit],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if value.strip()
    ]
    if not remote_refs:
        raise ValueError("freeze base commit must be pushed before Phase A freeze")
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "H4_phase_a_freeze_determination",
        "status": "PASS",
        "scientific_data_present": False,
        "freeze_base_commit": base_commit,
        "freeze_base_remote_refs": remote_refs,
        "runtime_manifest_sha256": sha256_file(runtime_path),
        "protected_artifacts": protected_artifacts,
        "focused_test_command": test_command,
        "focused_test_result": {
            "returncode": test_result.returncode,
            "stdout": test_result.stdout.strip(),
        },
        "config_schema_checks": schema_checks,
        "source_and_split_checks": design_checks,
        "rule": (
            "This determination must be committed and pushed before any H4 "
            "calibration generation. Any protected-artifact change requires a "
            "new pre-data freeze and is forbidden after scientific data exist."
        ),
    }
    write_json(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px057_h4_ltt_transfer_20260725.json"),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture-runtime", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    parser.add_argument("--container-image-digest")
    args = parser.parse_args()
    config_path = repo_path(args.config)
    config = read_json(config_path)
    if args.capture_runtime:
        if not args.container_image_digest:
            parser.error("--container-image-digest is required with --capture-runtime")
        result = capture_runtime(
            config_path,
            output_path=repo_path(config["phase_a"]["runtime_manifest"]),
            container_image_digest=args.container_image_digest,
        )
    else:
        result = freeze_phase_a(
            config_path,
            output_path=repo_path(config["phase_a"]["freeze_determination"]),
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
