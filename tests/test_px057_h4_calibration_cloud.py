from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import scripts.run_px057_ltt_calibration as calibration_module
from scripts.run_px057_ltt_calibration import verify_calibration_transport
from scripts.submit_px057_h4_calibration import (
    CALIBRATION_MAX_RUNTIME_SECONDS,
    ENTRY,
    PHASE_A_ENTRY,
    SAGEMAKER_G5_2XL_QUOTA_CODE,
    source_launch_command,
    training_request,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/px057_h4_ltt_transfer_20260725.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_calibration_transport_is_part_of_the_predata_protocol() -> None:
    config = load_config()
    transport = config["calibration_transport"]
    protected = set(config["phase_a"]["protected_paths"])
    assert config["protocol_revision"] == "2.2-predata-cloud-transport"
    assert transport["first_attempt_only"] is True
    assert transport["max_runtime_seconds"] == CALIBRATION_MAX_RUNTIME_SECONDS
    assert transport["sagemaker_quota_code"] == SAGEMAKER_G5_2XL_QUOTA_CODE
    assert transport["source_bootstrap"] == (
        "explicit_s3_version_and_sha256_before_extraction"
    )
    assert {
        ENTRY,
        PHASE_A_ENTRY,
        "scripts/submit_px057_h4_calibration.py",
        "scripts/fetch_px057_h4_calibration.py",
        "tests/test_px057_h4_calibration_cloud.py",
    } <= protected


def test_source_is_version_and_hash_checked_before_extraction() -> None:
    launch = source_launch_command()
    assert launch.startswith("set -euo pipefail")
    version_check = launch.index("--version-id")
    hash_check = launch.index("sha256sum -c -")
    extraction = launch.index("tar -xzf")
    execution = launch.index(f"python /opt/ml/code/{ENTRY}")
    assert version_check < hash_check < extraction < execution


def test_training_request_is_cell_specific_and_digest_pinned() -> None:
    config = load_config()
    aws_config = config["phase_a"]["aws"]
    job_name = "px057-h4-cal-c1-20260725-201500-123456"
    cell_id = "cell1_llama31_gsm8k"
    prefix = aws_config["s3_prefix"].strip("/")
    code_key = f"{prefix}/code/{job_name}/source.tar.gz"
    code_uri = f"s3://{aws_config['bucket']}/{code_key}"
    request = training_request(
        config,
        job_name=job_name,
        cell_id=cell_id,
        code_uri=code_uri,
        code_version_id="version-1",
        code_sha256="a" * 64,
        git_commit="b" * 40,
    )
    environment = request["Environment"]
    assert request["AlgorithmSpecification"]["TrainingImage"] == aws_config[
        "container_image_pinned_uri"
    ]
    assert request["StoppingCondition"]["MaxRuntimeInSeconds"] == (
        CALIBRATION_MAX_RUNTIME_SECONDS
    )
    assert environment["PX057_H4_CELL_ID"] == cell_id
    assert environment["PX057_H4_SOURCE_BUCKET"] == aws_config["bucket"]
    assert environment["PX057_H4_SOURCE_KEY"] == code_key
    assert environment["PX057_H4_SOURCE_VERSION_ID"] == "version-1"
    assert environment["PX057_H4_SOURCE_SHA256"] == "a" * 64
    assert environment["PX057_H4_RESULT_S3_URI"].endswith(
        f"/calibration/{cell_id}/{job_name}"
    )


def test_each_cell_has_unique_launch_and_cloud_manifests() -> None:
    cells = load_config()["cells"]
    launch_paths = {cell["calibration_launch_manifest"] for cell in cells}
    cloud_paths = {cell["calibration_cloud_manifest"] for cell in cells}
    assert len(launch_paths) == len(cells) == 3
    assert len(cloud_paths) == 3
    assert launch_paths.isdisjoint(cloud_paths)


def test_calibration_transport_binds_launch_cloud_and_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(calibration_module, "ROOT", tmp_path)
    monkeypatch.setattr(
        calibration_module,
        "committed_and_pushed",
        lambda path: {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "last_change_commit": "c" * 40,
            "verified_at_head": "d" * 40,
            "remote_refs": ["origin/test"],
        },
    )
    launch_path = tmp_path / "launch.json"
    cloud_path = tmp_path / "cloud.json"
    launch = {
        "experiment_id": "experiment",
        "stage": "H4_calibration_launch_registration",
        "status": "REGISTERED_PRE_RESULT",
        "scientific_result_observed": False,
        "cell_id": "cell",
        "job_name": "job",
        "training_job_arn": "arn:job",
        "git_commit": "a" * 40,
        "code_version_id": "source-version",
        "code_sha256": "b" * 64,
    }
    launch_path.write_text(json.dumps(launch), encoding="utf-8")
    file_hashes = {
        "selected_rows.jsonl": "1" * 64,
        "reasoning_traces.jsonl": "2" * 64,
        "raw_generations.jsonl": "3" * 64,
        "collection_summary.json": "4" * 64,
    }
    cloud = {
        "experiment_id": "experiment",
        "stage": "H4_calibration_cloud_job_manifest",
        "status": "PASS",
        "scientific_data_generated": True,
        "split": "calibration",
        "cell_id": "cell",
        "job_name": "job",
        "job_arn": "arn:job",
        "git_commit": "a" * 40,
        "source_artifact": {
            "version_id": "source-version",
            "sha256": "b" * 64,
        },
        "launch_registration": {
            "path": "launch.json",
            "sha256": hashlib.sha256(launch_path.read_bytes()).hexdigest(),
        },
        "cloud_evidence_object": {"version_id": "evidence-version"},
        "model_artifact": {"version_id": "model-version"},
        "collection_objects": {
            name: {"sha256": digest, "version_id": f"version-{index}"}
            for index, (name, digest) in enumerate(file_hashes.items())
        },
    }
    cloud_path.write_text(json.dumps(cloud), encoding="utf-8")
    config = {"experiment_id": "experiment"}
    cell = {
        "cell_id": "cell",
        "calibration_launch_manifest": "launch.json",
        "calibration_cloud_manifest": "cloud.json",
    }
    bundle = {
        "files": {
            name: {"sha256": digest} for name, digest in file_hashes.items()
        }
    }
    result = verify_calibration_transport(config, cell, bundle)
    assert result["launch_registration"]["path"] == "launch.json"
    assert result["cloud_job_manifest"]["path"] == "cloud.json"

    cloud["collection_objects"]["raw_generations.jsonl"]["sha256"] = "f" * 64
    cloud_path.write_text(json.dumps(cloud), encoding="utf-8")
    with pytest.raises(ValueError, match="cloud objects differ"):
        verify_calibration_transport(config, cell, bundle)
