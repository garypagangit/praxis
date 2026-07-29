from __future__ import annotations

import hashlib
import io
import inspect
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

import scripts.fetch_px057_h4_holdout as fetch
import scripts.submit_px057_h4_holdout as submit


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/px057_h4_holdout_transport_20260727.json"


def load_transport() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_canonical_transport_has_one_first_attempt_per_cell() -> None:
    transport = load_transport()
    submit.verify_transport_config(transport)
    assert transport["transport_id"] == "px057-h4-holdout-cloud-transport-20260727"
    assert transport["rules"]["first_attempt_only"] is True
    assert transport["rules"]["no_retry"] == (
        "No retry or replacement job is allowed under this transport ID."
    )
    assert {
        cell_id: cell["job_name"] for cell_id, cell in transport["cells"].items()
    } == {
        "cell1_llama31_gsm8k": "px057-h4-hold-c1-r1-20260727",
        "cell2_qwen25_arc": "px057-h4-hold-c2-r1-20260727",
        "cell3_llama31_arc": "px057-h4-hold-c3-r1-20260727",
    }
    assert len({cell["launch_manifest"] for cell in transport["cells"].values()}) == 3
    assert len({cell["cloud_manifest"] for cell in transport["cells"].values()}) == 3
    assert len({cell["result_prefix"] for cell in transport["cells"].values()}) == 3


def test_consumer_rejects_a_forged_minimal_pass_freeze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = load_transport()
    forged = {
        "transport_id": transport["transport_id"],
        "experiment_id": transport["experiment_id"],
        "stage": "H4_holdout_transport_freeze_determination",
        "status": "PASS",
        "scientific_data_generated": False,
        "scientific_payload_or_outcome_inspected": False,
        "protected_artifacts": {},
    }
    monkeypatch.setattr(submit, "verify_transport_config", lambda config: None)
    monkeypatch.setattr(
        submit,
        "committed_and_pushed",
        lambda path: {
            "path": path.name,
            "sha256": "a" * 64,
            "last_change_commit": "b" * 40,
        },
    )
    monkeypatch.setattr(
        submit, "freeze_manifest_path", lambda config: tmp_path / "freeze.json"
    )
    monkeypatch.setattr(submit, "read_json_strict", lambda path: forged)
    with pytest.raises(ValueError, match="closed top-level schema"):
        submit.verify_transport_freeze(tmp_path / "transport.json", transport)


def test_strict_json_reader_rejects_duplicate_object_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"status":"PASS","status":"FAIL"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        submit.read_json_strict(path)


def test_freeze_consumer_rejects_artifact_created_after_claimed_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "experiment"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "px057@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PX057 Test"], cwd=repo, check=True
    )
    initial = repo / "initial.txt"
    initial.write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "initial.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    freeze_base = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    late = repo / "late.txt"
    late.write_text("created too late\n", encoding="utf-8")
    subprocess.run(["git", "add", "late.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "late artifact"], cwd=repo, check=True)
    late_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    blob = subprocess.check_output(
        ["git", "rev-parse", "HEAD:late.txt"], cwd=repo, text=True
    ).strip()
    body = late.read_bytes()
    record = {
        "path": "late.txt",
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "git_blob": blob,
        "last_change_commit": late_commit,
        "verified_at_head": freeze_base,
    }
    monkeypatch.setattr(submit, "ROOT", repo)
    with pytest.raises(ValueError, match="postdates the holdout freeze"):
        submit.verify_artifact_at_freeze_base(
            record, freeze_base_commit=freeze_base
        )


def test_transport_freezes_300_by_8_collection_and_exact_source_set() -> None:
    transport = load_transport()
    collection = transport["collection"]
    assert collection["expected_traces"] == 300
    assert collection["rounds"] == 8
    assert collection["expected_generations"] == 2400
    assert tuple(collection["files"]) == submit.COLLECTION_FILES
    assert set(transport["source"]["archive_members"]) == {
        "cloud_jobs/px057_h4_holdout_20260727/.gitattributes",
        submit.ENTRY,
        submit.CALIBRATION_ENTRY,
        submit.PHASE_A_ENTRY,
        "configs/px057_h4_holdout_transport_20260727.json",
        submit.SCIENCE_CONFIG,
        "configs/px057_h4_prompt_templates_20260725.json",
        "requirements-px057-h4.txt",
        "scripts/run_px057_h4_trace_collection.py",
        "scripts/px057_h4_common.py",
        "scripts/run_px057_h4_holdout_gate.py",
    }


def test_source_is_version_and_hash_checked_before_extraction() -> None:
    launch = submit.source_launch_command()
    assert len(launch) <= 256
    assert launch.index("--version-id") < launch.index("sha256sum -c -")
    assert launch.index("sha256sum -c -") < launch.index("tar xzf")
    assert launch.index("tar xzf") < launch.index(
        f"python /opt/ml/code/{submit.ENTRY}"
    )


def test_job_names_are_deterministic_r1_first_attempts() -> None:
    assert [submit.holdout_job_name(cell_id) for cell_id in submit.CELL_JOB_CODES] == [
        "px057-h4-hold-c1-r1-20260727",
        "px057-h4-hold-c2-r1-20260727",
        "px057-h4-hold-c3-r1-20260727",
    ]
    with pytest.raises(ValueError, match="unknown PX-057"):
        submit.holdout_job_name("cell4")


def test_training_request_binds_source_freeze_lock_policy_and_one_cell() -> None:
    transport = load_transport()
    cell_id = "cell2_qwen25_arc"
    cell = transport["cells"][cell_id]
    bucket = transport["aws"]["bucket"]
    code_key = (
        f"{transport['aws']['s3_prefix']}/code/{cell['job_name']}/source.tar.gz"
    )
    request = submit.training_request(
        transport,
        cell_id=cell_id,
        git_commit="a" * 40,
        code_uri=f"s3://{bucket}/{code_key}",
        code_version_id="source-version",
        code_sha256="b" * 64,
        transport_sha256="c" * 64,
        science_sha256="d" * 64,
        freeze_sha256="e" * 64,
        lock_sha256="f" * 64,
        selected_policy_sha256="1" * 64,
    )
    environment = request["Environment"]
    assert request["TrainingJobName"] == cell["job_name"]
    assert request["AlgorithmSpecification"]["TrainingImage"] == transport["aws"][
        "container_image_pinned_uri"
    ]
    assert request["ResourceConfig"]["InstanceCount"] == 1
    assert request["StoppingCondition"]["MaxRuntimeInSeconds"] == 86400
    assert "RetryStrategy" not in request
    assert transport["aws"]["retry_strategy_omitted"] is True
    assert request["EnableManagedSpotTraining"] is False
    assert environment["PX057_H4_CELL_ID"] == cell_id
    assert environment["PX057_H4_SOURCE_VERSION_ID"] == "source-version"
    assert environment["PX057_H4_SOURCE_SHA256"] == "b" * 64
    assert environment["PX057_H4_TRANSPORT_CONFIG_SHA256"] == "c" * 64
    assert environment["PX057_H4_SCIENCE_CONFIG_SHA256"] == "d" * 64
    assert environment["PX057_H4_FREEZE_SHA256"] == "e" * 64
    assert environment["PX057_H4_LOCK_SHA256"] == "f" * 64
    assert environment["PX057_H4_SELECTED_POLICY_SHA256"] == "1" * 64
    assert environment["PX057_H4_SOURCE_BUCKET"] == bucket
    assert environment["PX057_H4_SOURCE_KEY"] == code_key
    assert environment["PX057_H4_RESULT_S3_URI"] == (
        f"s3://{bucket}/{cell['result_prefix']}"
    )
    assert {tag["Key"] for tag in request["Tags"]} == {
        "Project",
        "PraxisId",
        "Gate",
        "Cell",
        "GitCommit",
        "TransportId",
    }


def test_selected_policy_hash_is_canonical_and_newline_terminated() -> None:
    left = {"patience": 2, "min_step": 4, "confidence_threshold": 0.1}
    right = {"confidence_threshold": 0.1, "min_step": 4, "patience": 2}
    expected = hashlib.sha256(
        b'{"confidence_threshold":0.1,"min_step":4,"patience":2}\n'
    ).hexdigest()
    assert submit.canonical_json_sha256(left) == expected
    assert submit.canonical_json_sha256(right) == expected


def test_verify_ltt_locks_allows_unrelated_null_but_closes_null_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cells = []
    transport_cells = {}
    for index, cell_id in enumerate(submit.CELL_JOB_CODES, 1):
        lock_relative = f"locks/{cell_id}.json"
        lock_path = tmp_path / lock_relative
        lock_path.parent.mkdir(exist_ok=True)
        lock_path.write_text(
            json.dumps(
                {
                    "cell_id": cell_id,
                    "selected_policy": None
                    if index == 2
                    else {"min_step": 4, "patience": 2, "confidence_threshold": 0.1},
                }
            ),
            encoding="utf-8",
        )
        cells.append({"cell_id": cell_id, "ltt_lock_manifest": lock_relative})
        transport_cells[cell_id] = {"ltt_lock_manifest": lock_relative}
    monkeypatch.setattr(submit, "ROOT", tmp_path)
    monkeypatch.setattr(
        submit,
        "verify_all_locks",
        lambda config, path: {cell_id: {} for cell_id in submit.CELL_JOB_CODES},
    )
    evidence, locks = submit.verify_ltt_locks(
        {"cells": transport_cells},
        {"cells": cells},
        tmp_path / "science.json",
        eligible_cell_id="cell1_llama31_gsm8k",
    )
    assert set(evidence) == set(submit.CELL_JOB_CODES)
    assert locks["cell2_qwen25_arc"]["selected_policy"] is None
    with pytest.raises(ValueError, match="selected_policy is null"):
        submit.verify_ltt_locks(
            {"cells": transport_cells},
            {"cells": cells},
            tmp_path / "science.json",
            eligible_cell_id="cell2_qwen25_arc",
        )


def test_first_attempt_guard_checks_job_source_result_and_model_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = load_transport()
    cell_id = "cell1_llama31_gsm8k"
    cell = dict(transport["cells"][cell_id])
    cell.update(
        {
            "launch_manifest": "launch.json",
            "cloud_manifest": "cloud.json",
            "output_dir": "output",
        }
    )
    transport = {**transport, "cells": {**transport["cells"], cell_id: cell}}
    monkeypatch.setattr(submit, "ROOT", tmp_path)
    monkeypatch.setattr(submit, "aws_json", lambda *args, **kwargs: {})
    prefixes = []

    def no_history(**kwargs):
        prefixes.append(kwargs["prefix"])
        return [], []

    monkeypatch.setattr(submit, "_s3_history", no_history)
    submit.verify_first_attempt(
        transport, cell_id=cell_id, profile="profile", region="region"
    )
    assert len(prefixes) == 3
    assert any("/code/" in prefix for prefix in prefixes)
    assert any("/holdout/" in prefix for prefix in prefixes)
    assert any("/sagemaker-output/" in prefix for prefix in prefixes)

    downstream = tmp_path / cell["manual_audit_blinded"]
    downstream.parent.mkdir(parents=True, exist_ok=True)
    downstream.write_text("{}\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="downstream manual_audit_blinded"):
        submit.verify_first_attempt(
            transport, cell_id=cell_id, profile="profile", region="region"
        )
    downstream.unlink()

    monkeypatch.setattr(
        submit,
        "aws_json",
        lambda *args, **kwargs: {
            "TrainingJobSummaries": [{"TrainingJobName": cell["job_name"]}]
        },
    )
    with pytest.raises(ValueError, match="prior SageMaker"):
        submit.verify_first_attempt(
            transport, cell_id=cell_id, profile="profile", region="region"
        )


def test_source_archive_is_deterministic_and_matches_exact_frozen_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = load_transport()
    bodies = {
        path: f"committed:{path}\n".encode("utf-8")
        for path in transport["source"]["archive_members"]
    }

    def fake_check_output(command, cwd=None, **kwargs):
        return bodies[command[-1].split("HEAD:", 1)[1]]

    monkeypatch.setattr(submit.subprocess, "check_output", fake_check_output)
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    submit.build_source_archive(first, transport)
    submit.build_source_archive(second, transport)
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as handle:
        members = [member for member in handle.getmembers() if member.isfile()]
        assert {member.name for member in members} == set(bodies)
        assert len(members) == len(bodies)
        for member in members:
            extracted = handle.extractfile(member)
            assert extracted is not None
            assert extracted.read() == bodies[member.name]


def test_upload_source_requires_version_hash_size_and_aes256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"source")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    responses = iter(
        [
            {"VersionId": "v1"},
            {
                "VersionId": "v1",
                "ServerSideEncryption": "AES256",
                "Metadata": {"sha256": digest},
                "ContentLength": len(archive.read_bytes()),
                "ETag": '"etag"',
            },
        ]
    )
    monkeypatch.setattr(submit, "aws_json", lambda *args, **kwargs: next(responses))
    result = submit.upload_source(
        archive=archive,
        archive_sha256=digest,
        code_key="prefix/source.tar.gz",
        bucket="bucket",
        profile="profile",
        region="region",
    )
    assert result["version_id"] == "v1"
    assert result["server_side_encryption"] == "AES256"


def test_request_schema_is_prevalidated_before_source_upload() -> None:
    source = inspect.getsource(submit.main)
    assert source.index("validate_training_request(") < source.index("upload_source(")


def test_request_schema_failure_surfaces_aws_validation_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = submit.subprocess.CalledProcessError(
        252,
        ["aws", "sagemaker", "create-training-job"],
        output="",
        stderr="Invalid value for parameter RetryStrategy",
    )
    monkeypatch.setattr(submit.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(ValueError, match="Invalid value for parameter RetryStrategy"):
        submit.validate_training_request(
            {"TrainingJobName": "job"},
            request_path=tmp_path / "request.json",
            profile="profile",
            region="region",
        )


def test_fetch_requires_one_latest_version_without_delete_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fetch,
        "aws_json",
        lambda *args, **kwargs: {
            "Versions": [{"Key": "key", "VersionId": "v1", "IsLatest": True}],
            "DeleteMarkers": [],
        },
    )
    assert (
        fetch.require_single_version(
            profile="profile", region="region", bucket="bucket", key="key"
        )
        == "v1"
    )
    monkeypatch.setattr(
        fetch,
        "aws_json",
        lambda *args, **kwargs: {
            "Versions": [
                {"Key": "key", "VersionId": "v1", "IsLatest": False},
                {"Key": "key", "VersionId": "v2", "IsLatest": True},
            ],
            "DeleteMarkers": [],
        },
    )
    with pytest.raises(ValueError, match="one latest immutable version"):
        fetch.require_single_version(
            profile="profile", region="region", bucket="bucket", key="key"
        )


def test_fetch_tags_are_exact_not_merely_a_subset() -> None:
    transport = load_transport()
    cell_id = "cell3_llama31_arc"
    expected = {
        "Project": "PraxisResearch",
        "PraxisId": "PX-057",
        "Gate": "H4-Holdout",
        "Cell": cell_id,
        "GitCommit": "a" * 40,
        "TransportId": transport["transport_id"],
    }
    response = {"Tags": [{"Key": key, "Value": value} for key, value in expected.items()]}
    assert fetch.verify_tags(
        response,
        transport=transport,
        cell_id=cell_id,
        capture_commit="a" * 40,
    ) == expected
    response["Tags"].append({"Key": "Unexpected", "Value": "tag"})
    with pytest.raises(ValueError, match="tags differ"):
        fetch.verify_tags(
            response,
            transport=transport,
            cell_id=cell_id,
            capture_commit="a" * 40,
        )


def test_fetch_requires_null_or_absent_retry_and_managed_spot_false() -> None:
    transport = load_transport()
    fetch.verify_execution_strategy(
        {"EnableManagedSpotTraining": False}, transport
    )
    fetch.verify_execution_strategy(
        {"RetryStrategy": None, "EnableManagedSpotTraining": False}, transport
    )
    with pytest.raises(ValueError, match="retry or managed-spot"):
        fetch.verify_execution_strategy(
            {
                "RetryStrategy": {"MaximumRetryAttempts": 1},
                "EnableManagedSpotTraining": False,
            },
            transport,
        )
    with pytest.raises(ValueError, match="retry or managed-spot"):
        fetch.verify_execution_strategy(
            {"EnableManagedSpotTraining": True}, transport
        )


def test_cloud_entry_uses_closed_freeze_validator() -> None:
    source = (
        ROOT / "cloud_jobs/px057_h4_holdout_20260727/sagemaker_entry.py"
    ).read_text(encoding="utf-8")
    assert "validate_freeze_manifest(transport, freeze, repo_root=repo)" in source
    assert "freeze_base_commit" in source


def test_fetch_verifies_every_source_member_against_capture_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = load_transport()
    bodies = {
        path: f"blob:{path}\n".encode("utf-8")
        for path in transport["source"]["archive_members"]
    }
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        for name, body in bodies.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            handle.addfile(info, io.BytesIO(body))

    def fake_check_output(command, cwd=None, **kwargs):
        return bodies[command[-1].split(":", 1)[1]]

    monkeypatch.setattr(fetch.subprocess, "check_output", fake_check_output)
    result = fetch.verify_source_archive(
        archive,
        transport=transport,
        capture_commit="a" * 40,
        expected_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    )
    assert set(result) == set(bodies)


def test_model_artifact_must_replicate_bundle_and_cloud_evidence(
    tmp_path: Path,
) -> None:
    cell_id = "cell1_llama31_gsm8k"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in submit.COLLECTION_FILES:
        (bundle / name).write_text(name, encoding="utf-8")
    evidence = tmp_path / "cloud_job_evidence.json"
    evidence.write_text("evidence", encoding="utf-8")
    model = tmp_path / "model.tar.gz"
    with tarfile.open(model, "w:gz") as handle:
        handle.add(evidence, arcname="cloud_job_evidence.json")
        prefix = f"px057_h4_holdout/{cell_id}"
        for name in submit.COLLECTION_FILES:
            handle.add(bundle / name, arcname=f"{prefix}/{name}")
        handle.add(evidence, arcname=f"{prefix}/cloud_job_evidence.json")
    members = fetch.verify_model_artifact(
        model,
        cell_id=cell_id,
        bundle_dir=bundle,
        evidence_path=evidence,
    )
    assert len(members) == 6


def test_model_artifact_rejects_duplicate_regular_member_names(
    tmp_path: Path,
) -> None:
    cell_id = "cell1_llama31_gsm8k"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in submit.COLLECTION_FILES:
        (bundle / name).write_text(name, encoding="utf-8")
    evidence = tmp_path / "cloud_job_evidence.json"
    evidence.write_text("evidence", encoding="utf-8")
    model = tmp_path / "model.tar.gz"
    prefix = f"px057_h4_holdout/{cell_id}"
    with tarfile.open(model, "w:gz") as handle:
        handle.add(evidence, arcname="cloud_job_evidence.json")
        for name in submit.COLLECTION_FILES:
            handle.add(bundle / name, arcname=f"{prefix}/{name}")
        handle.add(evidence, arcname=f"{prefix}/cloud_job_evidence.json")
        duplicate_body = b"duplicate"
        duplicate = tarfile.TarInfo(f"{prefix}/selected_rows.jsonl")
        duplicate.size = len(duplicate_body)
        handle.addfile(duplicate, io.BytesIO(duplicate_body))
    with pytest.raises(ValueError, match="duplicate SageMaker model member"):
        fetch.verify_model_artifact(
            model,
            cell_id=cell_id,
            bundle_dir=bundle,
            evidence_path=evidence,
        )


def test_atomic_install_refuses_overwrite_and_rolls_back_on_manifest_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "evidence.txt").write_text("verified", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    target = tmp_path / "installed" / "bundle"
    cloud = tmp_path / "installed" / "cloud.json"
    fetch.atomic_install(bundle, manifest, output_dir=target, cloud_target=cloud)
    assert (target / "evidence.txt").read_text(encoding="utf-8") == "verified"
    assert cloud.is_file()

    replacement = tmp_path / "replacement"
    replacement.mkdir()
    replacement_manifest = tmp_path / "replacement.json"
    replacement_manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        fetch.atomic_install(
            replacement,
            replacement_manifest,
            output_dir=target,
            cloud_target=cloud,
        )

    rollback_bundle = tmp_path / "rollback"
    rollback_bundle.mkdir()
    rollback_manifest = tmp_path / "rollback.json"
    rollback_manifest.write_text("{}", encoding="utf-8")
    rollback_target = tmp_path / "rollback-installed"
    rollback_cloud = tmp_path / "rollback-cloud.json"
    original_replace = fetch.os.replace
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated manifest failure")
        return original_replace(source, destination)

    monkeypatch.setattr(fetch.os, "replace", fail_second)
    with pytest.raises(OSError, match="simulated"):
        fetch.atomic_install(
            rollback_bundle,
            rollback_manifest,
            output_dir=rollback_target,
            cloud_target=rollback_cloud,
        )
    assert not rollback_target.exists()
    assert not rollback_cloud.exists()
