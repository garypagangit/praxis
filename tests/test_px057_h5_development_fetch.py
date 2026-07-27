from __future__ import annotations

import ast
import io
import json
import tarfile
import copy
import hashlib

import pytest

import scripts.fetch_px057_h5_development_pilot as fetch
from scripts.fetch_px057_h5_development_pilot import (
    FILES,
    safe_extract,
    select_unique_artifact_version,
    sha256_file,
    verify_aws_request,
    verify_bundle,
    verify_fetch_receipt,
    verify_local_execution_tree,
    validate_remote_timeline,
)
from scripts.px057_h5_development_contract import EXPECTED_CONFIG, JOB_NAME
from scripts.submit_px057_h5_development_pilot import canonical_bytes, training_request


def write_json(path, value) -> None:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def write_jsonl(path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def make_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    ids = ["q1", "q2"]
    write_jsonl(bundle / "selected_rows.jsonl", [{"question_id": q} for q in ids])
    write_jsonl(bundle / "reasoning_traces.jsonl", [{"question_id": q} for q in ids])
    write_jsonl(
        bundle / "raw_generations.jsonl",
        [
            {"question_id": q, "round": round_index}
            for q in ids
            for round_index in (1, 2)
        ],
    )
    write_json(bundle / "collection_summary.json", {"claim_boundary": "development"})
    collection = {
        name: {"sha256": sha256_file(bundle / name)}
        for name in (
            "selected_rows.jsonl",
            "reasoning_traces.jsonl",
            "raw_generations.jsonl",
            "collection_summary.json",
        )
    }
    write_json(
        bundle / "cloud_job_evidence.json",
        {
            "status": "PASS",
            "confirmatory_evidence": False,
            "cell_id": "c1",
            "job_name": "job",
            "git_commit": "a" * 40,
            "experiment_id": "dev",
            "collection_verification": {"files": collection},
        },
    )
    return bundle


def test_verify_bundle_delegates_to_full_integrity_replay(
    tmp_path, monkeypatch
) -> None:
    bundle = make_bundle(tmp_path)
    config, cell, launch, _, _ = request_fixture()
    cloud_metadata = {
        "job_name": JOB_NAME,
        "git_commit": "a" * 40,
        "repository_url": config["repository"]["url"],
        "branch": config["repository"]["branch"],
        "container_image_digest": config["aws"]["container_image"].rsplit("@", 1)[1],
        "source_archive": {"version_id": "source-version", "sha256": "b" * 64},
        "code": {},
    }
    observed = {}

    def fake_integrity(path, **kwargs):
        observed["path"] = path
        observed.update(kwargs)
        return {
            "status": "PASS",
            "collection": {"trace_count": 500, "raw_generation_count": 4000},
            "cloud": {"status": "PASS"},
        }

    monkeypatch.setattr(
        "scripts.fetch_px057_h5_development_pilot.verify_fetched_collection",
        fake_integrity,
    )
    monkeypatch.setattr(
        "scripts.fetch_px057_h5_development_pilot.git_blob_bytes",
        lambda *_args: b"pinned-source",
    )
    monkeypatch.setattr(
        "scripts.fetch_px057_h5_development_pilot.expected_cloud_metadata",
        lambda *_args, **_kwargs: cloud_metadata,
    )
    result = verify_bundle(
        bundle,
        config=config,
        cell=cell,
        launch=launch,
        source_manifest_bytes=b"pinned-source",
        cloud_metadata=cloud_metadata,
    )

    assert result["status"] == "PASS"
    assert result["rows"] == 500
    assert result["generations"] == 4000
    assert observed["source_manifest_bytes"] == b"pinned-source"
    assert observed["expected_cloud_metadata"] == cloud_metadata
    assert set(result["files"]) == set(FILES)


def test_verify_bundle_propagates_integrity_failure(tmp_path, monkeypatch) -> None:
    bundle = make_bundle(tmp_path)
    config, cell, launch, _, _ = request_fixture()

    def fail_integrity(*args, **kwargs):
        raise ValueError("raw generations are not the exact ordered product")

    monkeypatch.setattr(
        "scripts.fetch_px057_h5_development_pilot.verify_fetched_collection",
        fail_integrity,
    )
    monkeypatch.setattr(
        "scripts.fetch_px057_h5_development_pilot.git_blob_bytes",
        lambda *_args: b"pinned-source",
    )
    monkeypatch.setattr(
        "scripts.fetch_px057_h5_development_pilot.expected_cloud_metadata",
        lambda *_args, **_kwargs: {},
    )

    with pytest.raises(ValueError, match="exact ordered product"):
        verify_bundle(
            bundle,
            config=config,
            cell=cell,
            launch=launch,
            source_manifest_bytes=b"pinned-source",
            cloud_metadata={},
        )


def test_safe_extract_rejects_path_traversal(tmp_path) -> None:
    archive_path = tmp_path / "bad.tar.gz"
    payload = b"escape"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("../escape.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with pytest.raises(ValueError, match="unsafe model artifact"):
        safe_extract(archive_path, tmp_path / "out")


def test_local_execution_tree_is_byte_bound_to_launch_commit(
    tmp_path, monkeypatch
) -> None:
    relative = "scripts/analysis.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"print('bound')\r\n")
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    monkeypatch.setattr(fetch, "LOCAL_ANALYSIS_PATHS", (relative,))
    monkeypatch.setattr(
        fetch, "git_blob_bytes", lambda *_args: b"print('bound')\n"
    )

    assert verify_local_execution_tree({"git_commit": "a" * 40})[relative]
    path.write_bytes(b"print('changed')\n")
    with pytest.raises(ValueError, match="differs from launch commit"):
        verify_local_execution_tree({"git_commit": "a" * 40})


def test_local_analysis_inventory_closes_transitive_scripts_imports() -> None:
    inventory = set(fetch.LOCAL_ANALYSIS_PATHS)
    for relative in sorted(inventory):
        if not relative.endswith(".py"):
            continue
        tree = ast.parse((fetch.ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith("scripts."):
                continue
            imported = node.module.replace(".", "/") + ".py"
            if (fetch.ROOT / imported).is_file():
                assert imported in inventory, (
                    f"{relative} imports unbound local module {imported}"
                )


def test_unique_artifact_version_rejects_overwrite_delete_and_null() -> None:
    key = "prefix/job/output/model.tar.gz"
    valid = {
        "Versions": [
            {
                "Key": key,
                "VersionId": "version-1",
                "IsLatest": True,
                "Size": 123,
            }
        ]
    }
    assert select_unique_artifact_version(valid, artifact_key=key)[
        "VersionId"
    ] == "version-1"

    overwritten = copy.deepcopy(valid)
    overwritten["Versions"].append(
        {
            "Key": key,
            "VersionId": "version-0",
            "IsLatest": False,
            "Size": 122,
        }
    )
    with pytest.raises(ValueError, match="exactly one version"):
        select_unique_artifact_version(overwritten, artifact_key=key)

    deleted = copy.deepcopy(valid)
    deleted["DeleteMarkers"] = [{"Key": key, "VersionId": "delete-1"}]
    with pytest.raises(ValueError, match="no delete marker"):
        select_unique_artifact_version(deleted, artifact_key=key)

    unversioned = copy.deepcopy(valid)
    unversioned["Versions"][0]["VersionId"] = "null"
    with pytest.raises(ValueError, match="malformed"):
        select_unique_artifact_version(unversioned, artifact_key=key)


def test_remote_timeline_rejects_reversed_job_interval() -> None:
    described = {
        "CreationTime": "2026-07-27T12:00:00+00:00",
        "TrainingStartTime": "2026-07-27T13:04:00+00:00",
        "TrainingEndTime": "2026-07-27T13:00:00+00:00",
        "LastModifiedTime": "2026-07-27T13:05:00+00:00",
    }
    launch = {"submitted_at_utc": "2026-07-27T12:01:00+00:00"}
    artifact = {"LastModified": "2026-07-27T13:04:00+00:00"}

    with pytest.raises(ValueError, match="not monotonically ordered"):
        validate_remote_timeline(described, launch=launch, artifact_listing=artifact)


def request_fixture():
    config = copy.deepcopy(EXPECTED_CONFIG)
    cell = config["cells"][0]
    source_key = (
        f"{config['aws']['s3_prefix']}/code/{JOB_NAME}/source.tar.gz"
    )
    source = {
        "bucket": config["aws"]["bucket"],
        "key": source_key,
        "version_id": "source-version",
        "sha256": "b" * 64,
    }
    request = training_request(
        config,
        cell=cell,
        name=JOB_NAME,
        commit="a" * 40,
        source_key=source_key,
        source_version=source["version_id"],
        source_sha256=source["sha256"],
    )
    arn = f"arn:aws:sagemaker:us-east-1:272615233626:training-job/{JOB_NAME}"
    launch = {
        "experiment_id": config["experiment_id"],
        "stage": "H5_DEVELOPMENT_PILOT_LAUNCH",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell["cell_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "job_name": JOB_NAME,
        "git_commit": "a" * 40,
        "training_job_arn": arn,
        "source": source,
        "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
        "submitted_at_utc": "2026-07-27T12:00:00+00:00",
    }
    described = {
        key: copy.deepcopy(request[key])
        for key in (
            "TrainingJobName",
            "RoleArn",
            "AlgorithmSpecification",
            "InputDataConfig",
            "OutputDataConfig",
            "ResourceConfig",
            "StoppingCondition",
            "Environment",
            "EnableNetworkIsolation",
        )
    }
    described.update(
        {
            "TrainingJobArn": arn,
            "TrainingJobStatus": "Completed",
            "SecondaryStatus": "Completed",
            "SecondaryStatusTransitions": [],
            "CreationTime": "2026-07-27T12:00:00+00:00",
            "TrainingStartTime": "2026-07-27T12:01:00+00:00",
            "TrainingEndTime": "2026-07-27T13:00:00+00:00",
            "LastModifiedTime": "2026-07-27T13:00:01+00:00",
            "TrainingTimeInSeconds": 3540,
            "BillableTimeInSeconds": 3540,
            "ModelArtifacts": {
                "S3ModelArtifacts": (
                    f"s3://{config['aws']['bucket']}/"
                    f"{config['aws']['s3_prefix']}/sagemaker-output/{JOB_NAME}/"
                    "output/model.tar.gz"
                )
            },
            "ProfilingStatus": "Disabled",
            "EnableManagedSpotTraining": False,
            "EnableInterContainerTrafficEncryption": False,
        }
    )
    described["AlgorithmSpecification"][
        "EnableSageMakerMetricsTimeSeries"
    ] = False
    described["InputDataConfig"][0].update(
        {"CompressionType": "None", "RecordWrapperType": "None"}
    )
    described["OutputDataConfig"].update(
        {"KmsKeyId": "", "CompressionType": "GZIP"}
    )
    return config, cell, launch, described, request["Tags"]


def test_aws_request_verifier_reconstructs_every_scientific_field() -> None:
    config, cell, launch, described, tags = request_fixture()

    result = verify_aws_request(
        config,
        cell=cell,
        launch=launch,
        described=described,
        observed_tags=tags,
    )

    assert result["status"] == "PASS"
    assert result["request_sha256"] == launch["request_sha256"]
    assert result["source"] is not launch["source"]
    original_source = copy.deepcopy(result["source"])
    launch["source"]["version_id"] = "mutated-after-verification"
    assert result["source"] == original_source


def test_aws_request_verifier_rejects_resource_or_environment_drift() -> None:
    config, cell, launch, described, tags = request_fixture()
    described["ResourceConfig"]["VolumeSizeInGB"] = 201

    with pytest.raises(ValueError, match="request provenance mismatch"):
        verify_aws_request(
            config,
            cell=cell,
            launch=launch,
            described=described,
            observed_tags=tags,
        )


def test_aws_request_verifier_rejects_unrequested_environment_key() -> None:
    config, cell, launch, described, tags = request_fixture()
    described["Environment"]["PYTHONPATH"] = "/tmp/attacker"

    with pytest.raises(ValueError, match="request provenance mismatch"):
        verify_aws_request(
            config,
            cell=cell,
            launch=launch,
            described=described,
            observed_tags=tags,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("RetryStrategy", {"MaximumRetryAttempts": 3}),
        ("EnableManagedSpotTraining", True),
        ("VpcConfig", {"SecurityGroupIds": ["sg-1"], "Subnets": ["subnet-1"]}),
        ("CheckpointConfig", {"S3Uri": "s3://bucket/checkpoints"}),
        ("EnableInterContainerTrafficEncryption", True),
        ("DebugHookConfig", {"S3OutputPath": "s3://bucket/debug"}),
        ("ProfilerConfig", {"DisableProfiler": False}),
        ("TensorBoardOutputConfig", {"S3OutputPath": "s3://bucket/tensorboard"}),
        ("RemoteDebugConfig", {"EnableRemoteDebug": True}),
        ("InfraCheckConfig", {"EnableInfraCheck": True}),
        ("ExperimentConfig", {"ExperimentName": "changed"}),
    ],
)
def test_aws_request_verifier_rejects_unregistered_top_level_controls(
    field, value
) -> None:
    config, cell, launch, described, tags = request_fixture()
    described[field] = value

    with pytest.raises(ValueError, match="field set is not exact|identity"):
        verify_aws_request(
            config,
            cell=cell,
            launch=launch,
            described=described,
            observed_tags=tags,
        )


def receipt_fixture(tmp_path):
    config, cell, launch, _, _ = request_fixture()
    bundle = make_bundle(tmp_path)
    files = {
        name: {
            "sha256": sha256_file(bundle / name),
            "bytes": (bundle / name).stat().st_size,
        }
        for name in FILES
    }
    cloud_metadata = {
        "job_name": JOB_NAME,
        "git_commit": launch["git_commit"],
        "repository_url": config["repository"]["url"],
        "branch": config["repository"]["branch"],
        "container_image_digest": config["aws"]["container_image"].rsplit("@", 1)[1],
        "source_archive": {
            "version_id": launch["source"]["version_id"],
            "sha256": launch["source"]["sha256"],
        },
        "code": {},
    }
    integrity = {"status": "PASS", "collection": {}, "cloud": {}}
    verification = {
        "rows": 500,
        "generations": 4000,
        "expected_cloud_metadata": copy.deepcopy(cloud_metadata),
        "integrity_verification": copy.deepcopy(integrity),
        "files": copy.deepcopy(files),
    }
    receipt = {
        "experiment_id": config["experiment_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "stage": "H5_DEVELOPMENT_PILOT_FETCH",
        "status": "PASS",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell["cell_id"],
        "job_name": launch["job_name"],
        "git_commit": launch["git_commit"],
        "rows": 500,
        "generations": 4000,
        "expected_cloud_metadata": cloud_metadata,
        "integrity_verification": integrity,
        "files": files,
        "model_artifact_uri": "s3://bucket/model.tar.gz",
        "aws_request_verification": {
            "status": "PASS",
            "request_sha256": launch["request_sha256"],
            "training_job_arn": launch["training_job_arn"],
            "source": copy.deepcopy(launch["source"]),
            "verified_request_fields": [
                "RoleArn",
                "AlgorithmSpecification",
                "InputDataConfig",
                "OutputDataConfig",
                "ResourceConfig",
                "StoppingCondition",
                "Environment",
                "EnableNetworkIsolation",
                "Tags",
            ],
        },
        "source_object": {**launch["source"], "size_bytes": 123},
        "model_artifact": {
            "bucket": "bucket",
            "key": "model.tar.gz",
            "version_id": "artifact-version",
            "sha256": "c" * 64,
            "size_bytes": 456,
            "etag": '"etag"',
            "server_side_encryption": "AES256",
        },
    }
    return config, cell, launch, verification, receipt


def test_fetch_receipt_cross_binds_launch_integrity_and_s3_objects(tmp_path) -> None:
    config, cell, launch, verification, receipt = receipt_fixture(tmp_path)

    result = verify_fetch_receipt(
        receipt,
        config=config,
        cell=cell,
        launch=launch,
        bundle_verification=verification,
    )

    assert result["status"] == "PASS"
    assert result["model_artifact_version_id"] == "artifact-version"


def test_fetch_receipt_rejects_changed_verified_file_hash(tmp_path) -> None:
    config, cell, launch, verification, receipt = receipt_fixture(tmp_path)
    receipt["files"]["raw_generations.jsonl"]["sha256"] = "d" * 64

    with pytest.raises(ValueError, match="files"):
        verify_fetch_receipt(
            receipt,
            config=config,
            cell=cell,
            launch=launch,
            bundle_verification=verification,
        )


def test_fetch_receipt_rejects_null_artifact_version(tmp_path) -> None:
    config, cell, launch, verification, receipt = receipt_fixture(tmp_path)
    receipt["model_artifact"]["version_id"] = "null"

    with pytest.raises(ValueError, match="artifact identity is malformed"):
        verify_fetch_receipt(
            receipt,
            config=config,
            cell=cell,
            launch=launch,
            bundle_verification=verification,
        )


def test_versioned_download_uses_portable_s3api_arguments(
    tmp_path, monkeypatch
) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs

    monkeypatch.setattr(fetch.subprocess, "run", fake_run)
    destination = tmp_path / "source.tar.gz"

    fetch._download_s3_version(
        bucket="bucket",
        key="frozen/source.tar.gz",
        version_id="version-1",
        destination=destination,
        profile="praxis-build",
        region="us-east-1",
    )

    assert observed["command"] == [
        "aws",
        "s3api",
        "get-object",
        "--bucket",
        "bucket",
        "--key",
        "frozen/source.tar.gz",
        "--version-id",
        "version-1",
        str(destination),
        "--profile",
        "praxis-build",
        "--region",
        "us-east-1",
    ]
    assert "--only-show-errors" not in observed["command"]
    assert observed["kwargs"] == {"cwd": fetch.ROOT, "check": True}
