from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import scripts.run_px057_ltt_calibration as calibration_module
from cloud_jobs.px057_h4_calibration_20260725.sagemaker_entry import (
    clone_exact_branch_history,
)
from scripts.run_px057_ltt_calibration import verify_calibration_transport
from scripts.submit_px057_h4_phase_a import (
    source_launch_command as phase_a_source_launch_command,
)
from scripts.submit_px057_h4_calibration import (
    CALIBRATION_MAX_RUNTIME_SECONDS,
    calibration_job_name,
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
    assert transport["job_name_scheme"] == (
        "px057-h4-cal-{c1|c2|c3}-r2-20260725"
    )
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


def test_phase_a_v2_uses_configured_runtime_and_authenticated_source() -> None:
    launch = phase_a_source_launch_command()
    assert launch.index("--version-id") < launch.index("sha256sum -c -")
    assert launch.index("sha256sum -c -") < launch.index("tar -xzf")
    entry = (
        ROOT / "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"
    ).read_text(encoding="utf-8")
    assert 'runtime_path = repo / config["phase_a"]["runtime_manifest"]' in entry
    assert load_config()["phase_a"]["runtime_manifest"].endswith(
        "runtime_environment_v2.json"
    )


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


def test_each_cell_has_one_deterministic_atomic_job_name() -> None:
    cells = [cell["cell_id"] for cell in load_config()["cells"]]
    names = [calibration_job_name(cell_id) for cell_id in cells]
    assert names == [
        "px057-h4-cal-c1-r2-20260725",
        "px057-h4-cal-c2-r2-20260725",
        "px057-h4-cal-c3-r2-20260725",
    ]
    assert len(set(names)) == 3


def test_cloud_clone_allows_only_a_descendant_launch_registration(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    subprocess.run(["git", "init", "-q", "-b", "experiment", str(source)], check=True)
    tracked = source / "tracked.txt"
    tracked.write_text("frozen\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PX057 Test",
            "-c",
            "user.email=px057@example.invalid",
            "commit",
            "-q",
            "-m",
            "frozen",
        ],
        cwd=source,
        check=True,
    )
    expected = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    tracked.write_text("frozen\nlaunch registered\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=PX057 Test",
            "-c",
            "user.email=px057@example.invalid",
            "commit",
            "-q",
            "-m",
            "launch registration",
        ],
        cwd=source,
        check=True,
    )
    branch_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    observed = clone_exact_branch_history(
        str(source), "experiment", expected, target
    )
    checked_out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=target, text=True
    ).strip()
    assert observed == branch_head
    assert checked_out == expected


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
