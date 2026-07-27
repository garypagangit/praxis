from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.fetch_px062_gate2_v11_results import (
    LAUNCH_RECEIPT_COMMIT,
    SEALED_FILES,
    canonical_json_bytes,
    fetch_and_seal,
    normalized_text_sha256,
    sha256_bytes,
    validate_download,
    validate_listing,
    validate_source_archive,
    validate_tar,
)


JOB = "px062-g21-retry1-20260727"
EXPERIMENT = "px062-skill-hallucination-gate2-v1-1-20260726"
REGISTRATION_COMMIT = "6" * 40
SOURCE_COMMIT = "7" * 40
FETCH_COMMIT = "8" * 40
JOB_ARN = f"arn:aws:sagemaker:us-east-1:123456789012:training-job/{JOB}"
BUCKET = "px062-test-bucket"
SOURCE_KEY = "experiments/px062/code/source.tar.gz"
OUTPUT_PREFIX = "experiments/px062/output"
OUTPUT_KEY = f"{OUTPUT_PREFIX}/{JOB}/output/model.tar.gz"
CREATED = "2026-07-27T04:05:34.006Z"
STARTED = "2026-07-27T04:11:36.563Z"
OUTPUT_TIME = "2026-07-27T04:41:24Z"
ENDED = "2026-07-27T04:41:29.325Z"
MODIFIED = "2026-07-27T04:41:30Z"
SOURCE_TIME = "2026-07-27T03:57:52Z"


def json_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2).encode("utf-8") + b"\n"


def write_json(path: Path, value: object) -> bytes:
    raw = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def add_file(handle: tarfile.TarFile, name: str, raw: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(raw)
    member.mtime = 0
    handle.addfile(member, io.BytesIO(raw))


def make_tar(
    files: dict[str, bytes],
    *,
    directories: tuple[str, ...] = (),
    mutation: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as handle:
        for name in directories:
            member = tarfile.TarInfo(name)
            member.type = tarfile.DIRTYPE
            member.mtime = 0
            handle.addfile(member)
        for name, raw in files.items():
            if mutation == "symlink" and name == next(iter(files)):
                member = tarfile.TarInfo(name)
                member.type = tarfile.SYMTYPE
                member.linkname = "../../outside"
                handle.addfile(member)
            else:
                add_file(handle, name, raw)
        if mutation == "duplicate":
            name = next(iter(files))
            add_file(handle, name, files[name])
        if mutation == "traversal":
            add_file(handle, "../outside", b"unsafe")
    return buffer.getvalue()


def artifact_record(
    raw: bytes,
    *,
    key: str,
    version: str,
    modified: str,
    algorithm: str,
) -> dict:
    sha = hashlib.sha256(raw).digest()
    record = {
        "bucket": BUCKET,
        "key": key,
        "version_id": version,
        "etag": hashlib.md5(raw, usedforsecurity=False).hexdigest(),
        "bytes": len(raw),
        "sha256": sha.hex(),
        "last_modified_utc": modified,
        "checksum_algorithm": [algorithm],
        "checksum_type": "FULL_OBJECT",
    }
    if algorithm == "SHA256":
        record["checksum_sha256_base64"] = base64.b64encode(sha).decode("ascii")
    else:
        record["checksum_crc32c_base64"] = "test-crc32c=="
    return record


def member_contract(files: dict[str, bytes], directories: tuple[str, ...] = ()) -> dict:
    contract = {
        name: {"bytes": len(raw), "sha256": sha256_bytes(raw)}
        for name, raw in files.items()
    }
    contract.update(
        {name: {"kind": "directory", "bytes": 0} for name in directories}
    )
    return contract


def version_listing(record: dict) -> dict:
    return {
        "Versions": [
            {
                "Key": record["key"],
                "VersionId": record["version_id"],
                "ETag": f'"{record["etag"]}"',
                "Size": record["bytes"],
                "IsLatest": True,
                "LastModified": record["last_modified_utc"],
                "ChecksumAlgorithm": record["checksum_algorithm"],
                "ChecksumType": record["checksum_type"],
            }
        ]
    }


def object_head(record: dict) -> dict:
    head = {
        "VersionId": record["version_id"],
        "ETag": f'"{record["etag"]}"',
        "ContentLength": record["bytes"],
        "LastModified": record["last_modified_utc"],
        "ChecksumType": record["checksum_type"],
    }
    if "checksum_sha256_base64" in record:
        head["ChecksumSHA256"] = record["checksum_sha256_base64"]
        head["Metadata"] = {"sha256": record["sha256"]}
    if "checksum_crc32c_base64" in record:
        head["ChecksumCRC32C"] = record["checksum_crc32c_base64"]
    return head


def transitions() -> list[dict]:
    statuses = ["Starting", "Pending", "Downloading", "Training", "Uploading"]
    rows = [
        {
            "Status": status,
            "StartTime": CREATED,
            "EndTime": ENDED,
            "StatusMessage": status,
        }
        for status in statuses
    ]
    rows.append(
        {
            "Status": "Completed",
            "StartTime": ENDED,
            "EndTime": ENDED,
            "StatusMessage": "Completed",
        }
    )
    return rows


def make_case(tmp_path: Path) -> dict:
    root = tmp_path / "repo"
    (root / "reports/coding_agent_skill_provenance").mkdir(parents=True)
    fetcher_path = root / "scripts/fetch_px062_gate2_v11_results.py"
    test_path = root / "tests/test_px062_gate2_fetch.py"
    fetcher_path.parent.mkdir()
    test_path.parent.mkdir()
    fetcher_raw = b"# frozen fetcher\n"
    tests_raw = b"# frozen adversarial tests\n"
    fetcher_path.write_bytes(fetcher_raw)
    test_path.write_bytes(tests_raw)

    config = {
        "experiment_id": EXPERIMENT,
        "protocol_version": "1.1",
        "benchmark_dir": "data/px062/hallucination_benchmark",
        "expected_tasks": 300,
        "expected_outputs": 1800,
        "models": ["model-a", "model-b"],
        "model_revisions": {"model-a": "rev-a", "model-b": "rev-b"},
        "conditions": [
            "open_ended",
            "registry_constrained",
            "post_generation_verification",
        ],
    }
    config_raw = json_bytes(config)
    tasks_raw = b'{"task_id":"frozen-source-task"}\n'
    registry_raw = b'{"names":["frozen-source-skill"]}\n'
    requirements_raw = b"transformers==4.46.3\n"
    entrypoint_raw = b"# source entrypoint\n"
    collector_raw = b"# source collector\n"
    source_files_without_manifest = {
        "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt": requirements_raw,
        "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py": entrypoint_raw,
        "configs/px062_skill_hallucination_gate2_v1_1_20260726.json": config_raw,
        "data/px062/hallucination_benchmark/registry_names.json": registry_raw,
        "data/px062/hallucination_benchmark/tasks.jsonl": tasks_raw,
        "requirements.txt": requirements_raw,
        "scripts/run_px062_skill_hallucination_models.py": collector_raw,
    }
    manifest_files = {
        name: sha256_bytes(raw) for name, raw in source_files_without_manifest.items()
    }
    bundle_manifest = {
        "base_aborted_bundle_sha256": (
            "afe0fd3a90e605766f1da555ac7b320c44187b50689c3379829a9b121534d3fb"
        ),
        "experiment_id": EXPERIMENT,
        "files": manifest_files,
        "parser_conformance": {
            "adjudicator_preserved_nonexistent": 100,
            "collector_preserved_nonexistent": 100,
            "near_miss_count": 100,
        },
        "protocol_version": "1.1",
        "registry_sha256": sha256_bytes(registry_raw),
        "tasks_sha256": sha256_bytes(tasks_raw),
    }
    bundle_raw = json_bytes(bundle_manifest)
    source_files = {"bundle_manifest.json": bundle_raw, **source_files_without_manifest}
    source_contract = member_contract(source_files)
    source_archive = make_tar(source_files)
    source_record = artifact_record(
        source_archive,
        key=SOURCE_KEY,
        version="source-version",
        modified=SOURCE_TIME,
        algorithm="SHA256",
    )

    summary = {
        "experiment_id": EXPERIMENT,
        "protocol_version": "1.1",
        "models": config["models"],
        "model_revisions": config["model_revisions"],
        "conditions": config["conditions"],
        "tasks": 300,
        "outputs": 1800,
        "expected_outputs": 1800,
        "source_integrity": {
            "config_sha256": sha256_bytes(config_raw),
            "tasks_sha256": sha256_bytes(tasks_raw),
            "registry_sha256": sha256_bytes(registry_raw),
        },
    }
    summary_raw = json_bytes(summary)
    outputs_raw = b'{"raw_response":"never parse or print"}\n' * 3
    output_files = {
        "px062_gate2/source_bundle_manifest.json": bundle_raw,
        "px062_gate2/collection_summary.json": summary_raw,
        "px062_gate2/model_outputs.jsonl": outputs_raw,
        "px062_gate2/frozen_config.json": config_raw,
    }
    output_contract = member_contract(output_files, ("px062_gate2",))
    output_archive = make_tar(output_files, directories=("px062_gate2",))
    output_record = artifact_record(
        output_archive,
        key=OUTPUT_KEY,
        version="output-version",
        modified=OUTPUT_TIME,
        algorithm="CRC32C",
    )

    request = {
        "TrainingJobName": JOB,
        "AlgorithmSpecification": {
            "TrainingImage": "image@sha256:digest",
            "TrainingInputMode": "File",
        },
        "RoleArn": "arn:aws:iam::123456789012:role/PX062",
        "OutputDataConfig": {"S3OutputPath": f"s3://{BUCKET}/{OUTPUT_PREFIX}"},
        "ResourceConfig": {
            "InstanceType": "ml.g5.2xlarge",
            "InstanceCount": 1,
            "VolumeSizeInGB": 150,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 43200},
        "HyperParameters": {
            "sagemaker_program": (
                "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py"
            ),
            "sagemaker_submit_directory": f"s3://{BUCKET}/{SOURCE_KEY}",
        },
        "Environment": {
            "PX062_CONFIG": (
                "configs/px062_skill_hallucination_gate2_v1_1_20260726.json"
            )
        },
        "EnableNetworkIsolation": False,
    }
    request_path = root / "manifests/px062_gate2_20260727/retry_request.json"
    request_raw = write_json(request_path, request)
    source_bundle = {
        **source_record,
        "uploaded_at_utc": source_record["last_modified_utc"],
        "config_sha256": sha256_bytes(config_raw),
        "tasks_sha256": sha256_bytes(tasks_raw),
        "registry_sha256": sha256_bytes(registry_raw),
        "collector_sha256": sha256_bytes(collector_raw),
    }
    registration = {
        "experiment_id": EXPERIMENT,
        "protocol_version": "1.1",
        "branch": "agent/px062-gate2-retry",
        "source_commit": SOURCE_COMMIT,
        "region": "us-east-1",
        "job_name": JOB,
        "request_file": "manifests/px062_gate2_20260727/retry_request.json",
        "request_sha256": normalized_text_sha256(request_raw),
        "source_bundle": source_bundle,
        "frozen_collection": {
            "container_image_digest": "sha256:digest",
            "instance_type": "ml.g5.2xlarge",
            "max_runtime_seconds": 43200,
        },
    }
    registration_path = root / "manifests/px062_gate2_20260727/retry_registration.json"
    registration_raw = write_json(registration_path, registration)
    launch = {
        "experiment_id": EXPERIMENT,
        "launched_at_utc": CREATED,
        "registration_commit": REGISTRATION_COMMIT,
        "training_job_name": JOB,
        "training_job_arn": JOB_ARN,
        "matching_training_jobs": 1,
        "request_sha256": registration["request_sha256"],
        "source_bundle_sha256": source_record["sha256"],
        "source_version_id": source_record["version_id"],
        "source_etag": source_record["etag"],
        "container_image_digest": "sha256:digest",
        "instance_type": "ml.g5.2xlarge",
        "max_runtime_seconds": 43200,
        "selected_config": request["Environment"]["PX062_CONFIG"],
    }
    launch_path = root / "manifests/px062_gate2_20260727/launch_receipt.json"
    launch_raw = write_json(launch_path, launch)
    prefetch = {
        "schema_version": "px062-fetch-registration-v1",
        "experiment_id": EXPERIMENT,
        "protocol_version": "1.1",
        "registered_at_utc": "2026-07-27T16:00:00Z",
        "purpose": "Outcome-blind source and output fetch registration",
        "branch": "agent/px062-gate2-retry",
        "required_state": "clean pushed commit before fetch",
        "launch_receipt_commit": LAUNCH_RECEIPT_COMMIT,
        "source_commit": SOURCE_COMMIT,
        "registration_path": registration_path.relative_to(root).as_posix(),
        "launch_receipt_path": launch_path.relative_to(root).as_posix(),
        "request_path": request_path.relative_to(root).as_posix(),
        "fetcher": {
            "path": "scripts/fetch_px062_gate2_v11_results.py",
            "sha256": sha256_bytes(fetcher_raw),
        },
        "tests": {
            "path": "tests/test_px062_gate2_fetch.py",
            "sha256": sha256_bytes(tests_raw),
        },
        "source_archive": {
            key: source_record[key]
            for key in (
                "bucket",
                "key",
                "version_id",
                "etag",
                "bytes",
                "sha256",
                "checksum_sha256_base64",
                "last_modified_utc",
                "checksum_algorithm",
                "checksum_type",
            )
        },
        "output_artifact": output_record,
    }
    prefetch_path = root / "manifests/px062_gate2_20260727/fetch_registration.json"
    prefetch_raw = write_json(prefetch_path, prefetch)

    description = {
        "TrainingJobName": JOB,
        "TrainingJobArn": JOB_ARN,
        "ModelArtifacts": {"S3ModelArtifacts": f"s3://{BUCKET}/{OUTPUT_KEY}"},
        "TrainingJobStatus": "Completed",
        "SecondaryStatus": "Completed",
        "HyperParameters": request["HyperParameters"],
        "AlgorithmSpecification": {
            **request["AlgorithmSpecification"],
            "EnableSageMakerMetricsTimeSeries": False,
        },
        "RoleArn": request["RoleArn"],
        "InputDataConfig": [],
        "OutputDataConfig": {
            "KmsKeyId": "",
            **request["OutputDataConfig"],
            "CompressionType": "GZIP",
        },
        "ResourceConfig": request["ResourceConfig"],
        "StoppingCondition": request["StoppingCondition"],
        "CreationTime": CREATED,
        "TrainingStartTime": STARTED,
        "TrainingEndTime": ENDED,
        "LastModifiedTime": MODIFIED,
        "SecondaryStatusTransitions": transitions(),
        "EnableNetworkIsolation": False,
        "EnableInterContainerTrafficEncryption": False,
        "EnableManagedSpotTraining": False,
        "TrainingTimeInSeconds": 1793,
        "BillableTimeInSeconds": 1793,
        "ProfilingStatus": "Disabled",
        "Environment": request["Environment"],
    }
    blobs: dict[tuple[str, str], bytes] = {
        (
            REGISTRATION_COMMIT,
            registration_path.relative_to(root).as_posix(),
        ): registration_raw,
        (REGISTRATION_COMMIT, request_path.relative_to(root).as_posix()): request_raw,
        (LAUNCH_RECEIPT_COMMIT, launch_path.relative_to(root).as_posix()): launch_raw,
        (FETCH_COMMIT, prefetch_path.relative_to(root).as_posix()): prefetch_raw,
        (FETCH_COMMIT, fetcher_path.relative_to(root).as_posix()): fetcher_raw,
        (FETCH_COMMIT, test_path.relative_to(root).as_posix()): tests_raw,
    }
    cloud_requirements = (
        "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt"
    )
    for name, raw in source_files_without_manifest.items():
        if name != "requirements.txt":
            blobs[(SOURCE_COMMIT, name)] = raw
    assert blobs[(SOURCE_COMMIT, cloud_requirements)] == requirements_raw
    return {
        "root": root,
        "registration_path": registration_path,
        "launch_path": launch_path,
        "prefetch_path": prefetch_path,
        "destination": root
        / "reports/coding_agent_skill_provenance/gate2_skill_hallucination_v1_1_20260726",
        "description": description,
        "source_record": source_record,
        "output_record": output_record,
        "source_listing": version_listing(source_record),
        "output_listing": version_listing(output_record),
        "source_head": object_head(source_record),
        "output_head": object_head(output_record),
        "source_archive": source_archive,
        "output_archive": output_archive,
        "source_contract": source_contract,
        "output_contract": output_contract,
        "source_files": source_files,
        "source_inputs": {
            "config": config_raw,
            "tasks": tasks_raw,
            "registry": registry_raw,
            "bundle": bundle_raw,
        },
        "output_inputs": {"summary": summary_raw, "outputs": outputs_raw},
        "registration": registration,
        "request": request,
        "blobs": blobs,
        "state": {
            "branch": "agent/px062-gate2-retry",
            "clean": True,
            "head": FETCH_COMMIT,
            "remote_refs": ["origin/agent/px062-gate2-retry"],
        },
    }


def run_case(case: dict, *, mutate: dict | None = None) -> dict:
    mutate = mutate or {}
    list_counts = {SOURCE_KEY: 0, OUTPUT_KEY: 0}

    def fake_aws(_profile: str, _region: str, *args: str):
        if args[:2] == ("sagemaker", "describe-training-job"):
            return mutate.get("description", case["description"])
        if args[:2] == ("s3api", "list-object-versions"):
            key = args[args.index("--prefix") + 1]
            list_counts[key] += 1
            base = (
                case["source_listing"] if key == SOURCE_KEY else case["output_listing"]
            )
            return mutate.get(("listing", key, list_counts[key]), base)
        if args[:2] == ("s3api", "head-object"):
            key = args[args.index("--key") + 1]
            return mutate.get(
                ("head", key),
                case["source_head"] if key == SOURCE_KEY else case["output_head"],
            )
        raise AssertionError(args)

    def fake_download(
        _profile: str,
        _region: str,
        _bucket: str,
        key: str,
        version_id: str,
        destination: Path,
    ):
        record = case["source_record"] if key == SOURCE_KEY else case["output_record"]
        assert version_id == record["version_id"]
        destination.write_bytes(
            case["source_archive"] if key == SOURCE_KEY else case["output_archive"]
        )
        response = {"VersionId": version_id, "ETag": f'"{record["etag"]}"'}
        if "checksum_sha256_base64" in record:
            response["ChecksumSHA256"] = record["checksum_sha256_base64"]
        else:
            response["ChecksumCRC32C"] = record["checksum_crc32c_base64"]
        return response

    def fake_blob(_root: Path, revision: str, path: str) -> bytes:
        override = mutate.get(("blob", revision, path))
        return override if override is not None else case["blobs"][(revision, path)]

    return fetch_and_seal(
        root=case["root"],
        profile="test-profile",
        registration_path=case["registration_path"],
        launch_path=case["launch_path"],
        prefetch_path=case["prefetch_path"],
        destination=case["destination"],
        aws_call=fake_aws,
        download_call=fake_download,
        blob_reader=fake_blob,
        state_reader=lambda _root: mutate.get("state", case["state"]),
        source_contract=case["source_contract"],
        output_contract=case["output_contract"],
        source_compressed_ceiling=len(case["source_archive"]) + 1,
        source_uncompressed_ceiling=sum(
            item["bytes"] for item in case["source_contract"].values()
        )
        + 1,
        output_compressed_ceiling=len(case["output_archive"]) + 1,
        output_uncompressed_ceiling=sum(
            item["bytes"] for item in case["output_contract"].values()
        )
        + 1,
        fetched_at=datetime(2026, 7, 27, 17, 0, tzinfo=timezone.utc),
    )


def test_success_uses_only_authenticated_source_inputs_and_is_outcome_blind(
    tmp_path, capsys
):
    case = make_case(tmp_path)
    receipt = run_case(case)
    assert capsys.readouterr().out == ""
    destination = case["destination"]
    assert {item.name for item in destination.iterdir()} == SEALED_FILES
    assert (destination / "frozen_config.json").read_bytes() == case["source_inputs"][
        "config"
    ]
    assert (destination / "tasks.jsonl").read_bytes() == case["source_inputs"][
        "tasks"
    ]
    assert (destination / "registry_names.json").read_bytes() == case[
        "source_inputs"
    ]["registry"]
    assert (destination / "model_outputs.jsonl").read_bytes() == case[
        "output_inputs"
    ]["outputs"]
    receipt_raw = (destination / "completion_fetch_receipt.json").read_bytes()
    assert receipt_raw == canonical_json_bytes(json.loads(receipt_raw))
    assert receipt["adjudication_run"] is False
    assert receipt["scientific_outputs_inspected"] is False
    assert receipt["source_artifact"]["version_listing_repeated"] is True
    assert receipt["output_artifact"]["version_listing_repeated"] is True


def test_existing_destination_fails_before_fetch(tmp_path):
    case = make_case(tmp_path)
    case["destination"].mkdir()
    with pytest.raises(FileExistsError):
        run_case(case)


@pytest.mark.parametrize("status", ["InProgress", "Failed", "Stopped"])
def test_job_must_be_completed(tmp_path, status):
    case = make_case(tmp_path)
    description = copy.deepcopy(case["description"])
    description["TrainingJobStatus"] = status
    with pytest.raises(ValueError, match="not Completed"):
        run_case(case, mutate={"description": description})


@pytest.mark.parametrize(
    ("field", "nested", "value"),
    [
        ("AlgorithmSpecification", "ContainerEntrypoint", ["python"]),
        ("AlgorithmSpecification", "ContainerArguments", ["--unsafe"]),
        ("OutputDataConfig", "Unexpected", True),
        ("ResourceConfig", "TrainingPlanArn", "arn:drift"),
        ("StoppingCondition", "MaxWaitTimeInSeconds", 999),
    ],
)
def test_closed_world_rejects_nested_sagemaker_drift(tmp_path, field, nested, value):
    case = make_case(tmp_path)
    description = copy.deepcopy(case["description"])
    description[field][nested] = value
    with pytest.raises(ValueError, match="schema drift"):
        run_case(case, mutate={"description": description})


def test_closed_world_rejects_top_level_control(tmp_path):
    case = make_case(tmp_path)
    description = copy.deepcopy(case["description"])
    description["RetryStrategy"] = {"MaximumRetryAttempts": 0}
    with pytest.raises(ValueError, match="top-level schema drift"):
        run_case(case, mutate={"description": description})


@pytest.mark.parametrize("kind", ["missing", "null", "multiple", "delete"])
def test_version_listing_requires_one_nonnull_latest_undeleted(kind):
    expected = {
        "version_id": "v1",
        "etag": "a" * 32,
        "bytes": 1,
        "last_modified_utc": SOURCE_TIME,
        "checksum_algorithm": ["SHA256"],
        "checksum_type": "FULL_OBJECT",
    }
    base = version_listing({"key": SOURCE_KEY, **expected})
    if kind == "missing":
        base["Versions"] = []
    elif kind == "null":
        base["Versions"][0]["VersionId"] = "null"
    elif kind == "multiple":
        base["Versions"].append(copy.deepcopy(base["Versions"][0]))
    else:
        base["DeleteMarkers"] = [{"Key": SOURCE_KEY, "VersionId": "deleted"}]
    with pytest.raises(ValueError):
        validate_listing(base, SOURCE_KEY, expected, "test")


def test_source_listing_is_repeated_and_change_fails(tmp_path):
    case = make_case(tmp_path)
    changed = copy.deepcopy(case["source_listing"])
    changed["Versions"].append(
        {
            **copy.deepcopy(changed["Versions"][0]),
            "VersionId": "new-version",
            "IsLatest": False,
        }
    )
    with pytest.raises(ValueError, match="one version"):
        run_case(
            case,
            mutate={("listing", SOURCE_KEY, 2): changed},
        )


def test_output_listing_is_repeated_and_change_fails(tmp_path):
    case = make_case(tmp_path)
    changed = copy.deepcopy(case["output_listing"])
    changed["DeleteMarkers"] = [{"Key": OUTPUT_KEY, "VersionId": "deleted"}]
    with pytest.raises(ValueError, match="no delete marker"):
        run_case(case, mutate={("listing", OUTPUT_KEY, 2): changed})


def test_source_checksum_metadata_is_required(tmp_path):
    case = make_case(tmp_path)
    head = copy.deepcopy(case["source_head"])
    head["Metadata"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="metadata mismatch"):
        run_case(case, mutate={("head", SOURCE_KEY): head})


def test_equivalent_utc_timestamp_encodings_are_accepted(tmp_path):
    case = make_case(tmp_path)
    listing = copy.deepcopy(case["source_listing"])
    listing["Versions"][0]["LastModified"] = "2026-07-27T03:57:52+00:00"
    head = copy.deepcopy(case["source_head"])
    head["LastModified"] = "2026-07-27T03:57:52+00:00"
    run_case(
        case,
        mutate={
            ("listing", SOURCE_KEY, 1): listing,
            ("listing", SOURCE_KEY, 2): listing,
            ("head", SOURCE_KEY): head,
        },
    )


def test_source_must_predate_job_creation(tmp_path):
    case = make_case(tmp_path)
    head = copy.deepcopy(case["source_head"])
    head["LastModified"] = CREATED
    with pytest.raises(ValueError, match="LastModified mismatch"):
        run_case(case, mutate={("head", SOURCE_KEY): head})


@pytest.mark.parametrize("field", ["bytes", "sha256", "etag"])
def test_download_verifies_size_sha_and_etag(tmp_path, field):
    raw = b"artifact"
    archive = tmp_path / "artifact.tar.gz"
    archive.write_bytes(raw)
    sha = hashlib.sha256(raw).digest()
    expected = {
        "version_id": "v1",
        "etag": hashlib.md5(raw, usedforsecurity=False).hexdigest(),
        "bytes": len(raw),
        "sha256": sha.hex(),
        "checksum_sha256_base64": base64.b64encode(sha).decode("ascii"),
    }
    if field == "bytes":
        expected[field] += 1
    else:
        expected[field] = "0" * len(expected[field])
    response = {
        "VersionId": "v1",
        "ETag": f'"{expected["etag"]}"',
        "ChecksumSHA256": expected["checksum_sha256_base64"],
    }
    with pytest.raises(ValueError):
        validate_download(archive, response, expected, "test", 1024)


@pytest.mark.parametrize("mutation", ["symlink", "duplicate", "traversal"])
def test_tar_rejects_links_duplicates_and_traversal(tmp_path, mutation):
    files = {"safe/file.txt": b"safe"}
    archive = tmp_path / "bad.tar.gz"
    archive.write_bytes(make_tar(files, mutation=mutation))
    contract = member_contract(files)
    with tarfile.open(archive, "r:gz") as handle:
        with pytest.raises(ValueError):
            validate_tar(handle, contract, 1024, "test archive")


def test_tar_rejects_member_and_total_size_ceiling(tmp_path):
    files = {"safe.txt": b"12345"}
    archive = tmp_path / "large.tar.gz"
    archive.write_bytes(make_tar(files))
    wrong_contract = {"safe.txt": {"bytes": 4}}
    with tarfile.open(archive, "r:gz") as handle:
        with pytest.raises(ValueError, match="member size mismatch"):
            validate_tar(handle, wrong_contract, 1024, "test archive")
    with tarfile.open(archive, "r:gz") as handle:
        with pytest.raises(ValueError, match="ceiling"):
            validate_tar(handle, member_contract(files), 4, "test archive")


def test_source_manifest_parser_or_base_field_drift_fails(tmp_path):
    case = make_case(tmp_path)
    files = dict(case["source_files"])
    manifest = json.loads(files["bundle_manifest.json"])
    manifest["parser_conformance"]["near_miss_count"] = 99
    files["bundle_manifest.json"] = json_bytes(manifest)
    contract = member_contract(files)
    archive = tmp_path / "source-drift.tar.gz"
    archive.write_bytes(make_tar(files))

    def blob(_root: Path, revision: str, path: str) -> bytes:
        return case["blobs"][(revision, path)]

    with pytest.raises(ValueError, match="exact frozen inventory"):
        validate_source_archive(
            archive,
            contract,
            case["registration"],
            case["request"],
            case["root"],
            blob,
            1024 * 1024,
        )


def test_source_member_must_match_source_commit(tmp_path):
    case = make_case(tmp_path)
    entrypoint = "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py"
    with pytest.raises(ValueError, match="source_commit"):
        run_case(
            case,
            mutate={("blob", SOURCE_COMMIT, entrypoint): b"different committed code"},
        )


def test_launch_receipt_bytes_are_bound_to_receipt_commit(tmp_path):
    case = make_case(tmp_path)
    relative = case["launch_path"].relative_to(case["root"]).as_posix()
    with pytest.raises(ValueError, match="committed evidence mismatch"):
        run_case(
            case,
            mutate={("blob", LAUNCH_RECEIPT_COMMIT, relative): b"different receipt"},
        )


@pytest.mark.parametrize(
    "state_change",
    [
        {"clean": False},
        {"remote_refs": []},
        {"branch": "wrong-branch"},
    ],
)
def test_fetch_requires_clean_pushed_registered_code(tmp_path, state_change):
    case = make_case(tmp_path)
    state = {**case["state"], **state_change}
    with pytest.raises(ValueError):
        run_case(case, mutate={"state": state})


def test_prefetch_fetcher_hash_is_enforced(tmp_path):
    case = make_case(tmp_path)
    fetcher = case["root"] / "scripts/fetch_px062_gate2_v11_results.py"
    fetcher.write_bytes(b"modified after registration\n")
    with pytest.raises(ValueError, match="differs from pushed|hash mismatch"):
        run_case(case)
