#!/usr/bin/env python
"""Fetch and verify one completed PX-057 H5 development-pilot artifact."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h5_development_contract import (
    JOB_NAME,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_SHA256,
    require_c1,
    validate_frozen_development_config,
)
from scripts.px057_h5_development_integrity import (
    CLOUD_FILES,
    REQUIRED_CODE_KEYS,
    read_json_strict,
    verify_fetched_collection,
)
from scripts.submit_px057_h5_development_pilot import (
    COMMITTED_ENTRY,
    canonical_bytes,
    training_request,
)
DEFAULT_CONFIG = ROOT / "configs/px057_h5_development_pilot_20260727.json"
FILES = CLOUD_FILES
CODE_PATHS = {
    "entrypoint_sha256": COMMITTED_ENTRY,
    "config_sha256": "configs/px057_h5_development_pilot_20260727.json",
    "runner_sha256": "scripts/run_px057_h5_development_pilot.py",
    "mechanism_sha256": "scripts/px057_h5_mechanism.py",
    "contract_sha256": "scripts/px057_h5_development_contract.py",
    "integrity_sha256": "scripts/px057_h5_development_integrity.py",
    "h4_requirements_sha256": "requirements-px057-h4.txt",
}
LOCAL_ANALYSIS_PATHS = (
    "configs/px057_h5_development_pilot_20260727.json",
    "scripts/submit_px057_h5_development_pilot.py",
    "scripts/fetch_px057_h5_development_pilot.py",
    "scripts/evaluate_px057_h5_development_pilot.py",
    "scripts/run_px057_h5_development_pilot.py",
    "scripts/run_px057_h4_trace_collection.py",
    "scripts/run_px057_h4_holdout_gate.py",
    "scripts/px057_h4_common.py",
    "scripts/run_px057_trace_collection.py",
    "scripts/run_px057_adaptive_stopping_gate.py",
    "scripts/px057_h5_mechanism.py",
    "scripts/px057_h5_development_contract.py",
    "scripts/px057_h5_development_integrity.py",
)
FETCH_RECEIPT_KEYS = {
    "experiment_id",
    "attempt_id",
    "protocol_id",
    "frozen_cell_id",
    "policy_id",
    "stage",
    "status",
    "confirmatory_evidence",
    "claim_boundary",
    "cell_id",
    "job_name",
    "git_commit",
    "rows",
    "generations",
    "expected_cloud_metadata",
    "integrity_verification",
    "files",
    "model_artifact_uri",
    "aws_request_verification",
    "source_object",
    "model_artifact",
}
LAUNCH_KEYS = {
    "experiment_id",
    "stage",
    "confirmatory_evidence",
    "claim_boundary",
    "cell_id",
    "attempt_id",
    "protocol_id",
    "frozen_cell_id",
    "policy_id",
    "job_name",
    "training_job_arn",
    "git_commit",
    "source",
    "request_sha256",
    "submitted_at_utc",
}
COMPLETED_DESCRIBE_KEYS = {
    "AlgorithmSpecification",
    "BillableTimeInSeconds",
    "CreationTime",
    "EnableInterContainerTrafficEncryption",
    "EnableManagedSpotTraining",
    "EnableNetworkIsolation",
    "Environment",
    "InputDataConfig",
    "LastModifiedTime",
    "ModelArtifacts",
    "OutputDataConfig",
    "ProfilingStatus",
    "ResourceConfig",
    "RoleArn",
    "SecondaryStatus",
    "SecondaryStatusTransitions",
    "StoppingCondition",
    "TrainingEndTime",
    "TrainingJobArn",
    "TrainingJobName",
    "TrainingJobStatus",
    "TrainingStartTime",
    "TrainingTimeInSeconds",
}


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws(profile: str, region: str, *args: str) -> str:
    return output(["aws", *args, "--profile", profile, "--region", region])


def read_json(path: Path) -> dict[str, Any]:
    return read_json_strict(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_bytes(commit: str, path: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("launch git commit must be a full lowercase SHA-1")
    try:
        return subprocess.check_output(
            ["git", "show", f"{commit}:{path}"], cwd=ROOT
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"launch commit does not contain required path: {path}") from exc


def verify_local_execution_tree(launch: dict[str, Any]) -> dict[str, str]:
    """Require every locally executed analysis file to match the launch commit."""

    commit = str(launch.get("git_commit", ""))
    records: dict[str, str] = {}
    root = ROOT.resolve()
    for relative in LOCAL_ANALYSIS_PATHS:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"local analysis path is not a regular file: {relative}")
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f"local analysis path escapes repository: {relative}") from exc
        expected = git_blob_bytes(commit, relative)
        observed = path.read_bytes()
        if observed.replace(b"\r\n", b"\n") != expected.replace(b"\r\n", b"\n"):
            raise ValueError(
                f"local analysis code/config differs from launch commit: {relative}"
            )
        records[relative] = hashlib.sha256(expected).hexdigest()
    return records


def expected_cloud_metadata(
    config: dict[str, Any], *, launch: dict[str, Any]
) -> dict[str, Any]:
    """Derive cloud evidence solely from the immutable launch and git commit."""

    cells = config.get("cells")
    if not isinstance(cells, list) or len(cells) != 1:
        raise ValueError("development config must contain the sole C1 cell")
    validate_launch_manifest(config, cell=cells[0], launch=launch)
    if set(CODE_PATHS) != set(REQUIRED_CODE_KEYS):
        raise ValueError("local cloud code inventory differs from integrity contract")
    source = launch.get("source")
    if not isinstance(source, dict):
        raise ValueError("launch source identity is missing")
    version_id = str(source.get("version_id", ""))
    source_sha256 = str(source.get("sha256", ""))
    if (
        not version_id
        or version_id.casefold() == "null"
        or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None
    ):
        raise ValueError("launch source version/hash identity is malformed")
    image = str(config["aws"]["container_image"])
    if "@" not in image:
        raise ValueError("development container image is not digest pinned")
    image_digest = image.rsplit("@", 1)[1]
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest) is None:
        raise ValueError("development container image digest is malformed")
    commit = str(launch.get("git_commit", ""))
    code = {
        name: hashlib.sha256(git_blob_bytes(commit, path)).hexdigest()
        for name, path in CODE_PATHS.items()
    }
    return {
        "job_name": str(launch.get("job_name", "")),
        "git_commit": commit,
        "repository_url": str(config["repository"]["url"]),
        "branch": str(config["repository"]["branch"]),
        "container_image_digest": image_digest,
        "source_archive": {
            "version_id": version_id,
            "sha256": source_sha256,
        },
        "code": code,
    }


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination_root)
            except ValueError as exc:
                raise ValueError(f"unsafe model artifact member: {member.name}") from exc
            if member.issym() or member.islnk():
                raise ValueError(f"links are forbidden in model artifact: {member.name}")
            if not member.isfile() and not member.isdir():
                raise ValueError(
                    f"special files are forbidden in model artifact: {member.name}"
                )
        archive.extractall(destination)


def validate_launch_manifest(
    config: dict[str, Any], *, cell: dict[str, Any], launch: dict[str, Any]
) -> dict[str, Any]:
    """Validate and reconstruct the immutable local launch registration."""

    require_c1(str(cell["cell_id"]))
    if set(launch) != LAUNCH_KEYS:
        raise ValueError("launch manifest fields differ from the exact contract")
    if (
        launch.get("experiment_id") != config["experiment_id"]
        or launch.get("stage") != "H5_DEVELOPMENT_PILOT_LAUNCH"
        or launch.get("confirmatory_evidence") is not False
        or launch.get("claim_boundary") != config["claim_boundary"]
        or launch.get("cell_id") != cell["cell_id"]
        or launch.get("attempt_id") != config["attempt_id"]
        or launch.get("protocol_id") != config["protocol_id"]
        or launch.get("frozen_cell_id") != config["frozen_cell_id"]
        or launch.get("policy_id")
        != config["primary_development_policy"]["policy_id"]
        or launch.get("job_name") != JOB_NAME
        or re.fullmatch(r"[0-9a-f]{40}", str(launch.get("git_commit", "")))
        is None
        or re.fullmatch(r"[0-9a-f]{64}", str(launch.get("request_sha256", "")))
        is None
    ):
        raise ValueError("launch manifest identity/boundary mismatch")
    try:
        submitted = dt.datetime.fromisoformat(str(launch["submitted_at_utc"]))
    except ValueError as exc:
        raise ValueError("launch timestamp is not ISO-8601") from exc
    if submitted.tzinfo is None:
        raise ValueError("launch timestamp is not timezone aware")

    aws_config = config["aws"]
    role_match = re.fullmatch(r"arn:aws:iam::([0-9]{12}):role/.+", aws_config["role_arn"])
    if role_match is None:
        raise ValueError("configured SageMaker role ARN is malformed")
    expected_arn = (
        f"arn:aws:sagemaker:{aws_config['region']}:{role_match.group(1)}:"
        f"training-job/{JOB_NAME}"
    )
    if launch.get("training_job_arn") != expected_arn:
        raise ValueError("launch training-job ARN differs from exact job identity")
    expected_source_key = (
        f"{aws_config['s3_prefix'].strip('/')}/code/{JOB_NAME}/source.tar.gz"
    )
    source = launch.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bucket", "key", "version_id", "sha256"}
        or source.get("bucket") != aws_config["bucket"]
        or source.get("key") != expected_source_key
        or not str(source.get("version_id", ""))
        or str(source.get("version_id", "")).casefold() == "null"
        or re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", ""))) is None
    ):
        raise ValueError("launch source object identity mismatch")
    request = training_request(
        config,
        cell=cell,
        name=JOB_NAME,
        commit=str(launch["git_commit"]),
        source_key=expected_source_key,
        source_version=str(source["version_id"]),
        source_sha256=str(source["sha256"]),
    )
    request_sha256 = hashlib.sha256(canonical_bytes(request)).hexdigest()
    if request_sha256 != launch["request_sha256"]:
        raise ValueError("reconstructed launch request SHA-256 mismatch")
    return request


def verify_aws_request(
    config: dict[str, Any],
    *,
    cell: dict[str, Any],
    launch: dict[str, Any],
    described: dict[str, Any],
    observed_tags: list[dict[str, str]],
) -> dict[str, Any]:
    """Reconstruct and compare every immutable scientific launch field."""

    request = validate_launch_manifest(config, cell=cell, launch=launch)
    request_sha256 = hashlib.sha256(canonical_bytes(request)).hexdigest()
    if set(described) != COMPLETED_DESCRIBE_KEYS:
        unexpected = sorted(set(described) - COMPLETED_DESCRIBE_KEYS)
        missing = sorted(COMPLETED_DESCRIBE_KEYS - set(described))
        raise ValueError(
            "AWS described training-job field set is not exact: "
            f"unexpected={unexpected}, missing={missing}"
        )
    if (
        described.get("TrainingJobName") != JOB_NAME
        or described.get("TrainingJobArn") != launch.get("training_job_arn")
        or described.get("TrainingJobStatus") != "Completed"
        or described.get("SecondaryStatus") != "Completed"
        or described.get("EnableManagedSpotTraining") is not False
        or described.get("EnableInterContainerTrafficEncryption") is not False
        or described.get("ProfilingStatus") != "Disabled"
    ):
        raise ValueError("described training-job identity differs from launch")
    expected_described = {
        key: copy.deepcopy(request[key])
        for key in (
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
    expected_described["AlgorithmSpecification"][
        "EnableSageMakerMetricsTimeSeries"
    ] = False
    for channel in expected_described["InputDataConfig"]:
        channel["CompressionType"] = "None"
        channel["RecordWrapperType"] = "None"
    expected_described["OutputDataConfig"].update(
        {"KmsKeyId": "", "CompressionType": "GZIP"}
    )
    observed_described = {
        key: described.get(key) for key in expected_described
    }
    if canonical_bytes(observed_described) != canonical_bytes(expected_described):
        raise ValueError(
            "AWS request provenance mismatch: described request fields are not exact"
        )
    expected_tags = {row["Key"]: row["Value"] for row in request["Tags"]}
    if any(
        not isinstance(row, dict) or set(row) != {"Key", "Value"}
        for row in observed_tags
    ):
        raise ValueError("training-job tags have an unexpected schema")
    actual_tags = {row["Key"]: row["Value"] for row in observed_tags}
    if len(actual_tags) != len(observed_tags) or actual_tags != expected_tags:
        raise ValueError("training-job tags differ from the exact request")
    return {
        "status": "PASS",
        "request_sha256": request_sha256,
        "training_job_arn": described["TrainingJobArn"],
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
    }


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://") or "/" not in uri[5:]:
        raise ValueError(f"invalid S3 URI: {uri}")
    bucket, key = uri[5:].split("/", 1)
    if not bucket or not key:
        raise ValueError(f"invalid S3 URI: {uri}")
    return bucket, key


def expected_model_artifact_uri(config: dict[str, Any]) -> str:
    prefix = config["aws"]["s3_prefix"].strip("/")
    return (
        f"s3://{config['aws']['bucket']}/{prefix}/sagemaker-output/"
        f"{JOB_NAME}/output/model.tar.gz"
    )


def select_unique_artifact_version(
    listing: dict[str, Any], *, artifact_key: str
) -> dict[str, Any]:
    """Accept only the sole immutable version ever written at the job key."""

    versions = [
        row
        for row in listing.get("Versions", [])
        if isinstance(row, dict) and row.get("Key") == artifact_key
    ]
    deletes = [
        row
        for row in listing.get("DeleteMarkers", [])
        if isinstance(row, dict) and row.get("Key") == artifact_key
    ]
    if len(versions) != 1 or deletes:
        raise ValueError(
            "model artifact key must have exactly one version and no delete marker"
        )
    version = versions[0]
    if (
        not str(version.get("VersionId", ""))
        or version.get("VersionId") == "null"
        or version.get("IsLatest") is not True
        or type(version.get("Size")) is not int
        or int(version["Size"]) <= 0
    ):
        raise ValueError("model artifact version identity is malformed")
    return version


def verify_bundle(
    bundle: Path,
    *,
    config: dict[str, Any],
    cell: dict[str, Any],
    launch: dict[str, Any],
    source_manifest_bytes: bytes | None = None,
    cloud_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require_c1(str(cell["cell_id"]))
    canonical_source = git_blob_bytes(str(launch["git_commit"]), SOURCE_MANIFEST)
    if source_manifest_bytes is not None and source_manifest_bytes != canonical_source:
        raise ValueError("caller source bytes differ from the launch commit")
    source_manifest_bytes = canonical_source
    canonical_cloud_metadata = expected_cloud_metadata(config, launch=launch)
    if (
        cloud_metadata is not None
        and canonical_bytes(cloud_metadata)
        != canonical_bytes(canonical_cloud_metadata)
    ):
        raise ValueError("caller cloud metadata differs from canonical launch/git data")
    cloud_metadata = canonical_cloud_metadata
    integrity = verify_fetched_collection(
        bundle,
        config=config,
        source_manifest_bytes=source_manifest_bytes,
        expected_source_sha256=SOURCE_MANIFEST_SHA256,
        expected_cloud_metadata=cloud_metadata,
    )
    records = {
        name: {
            "sha256": sha256_file(bundle / name),
            "bytes": (bundle / name).stat().st_size,
        }
        for name in FILES
    }
    return {
        "status": "PASS",
        "experiment_id": config["experiment_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "cell_id": cell["cell_id"],
        "job_name": launch["job_name"],
        "git_commit": launch["git_commit"],
        "rows": integrity["collection"]["trace_count"],
        "generations": integrity["collection"]["raw_generation_count"],
        "expected_cloud_metadata": cloud_metadata,
        "integrity_verification": integrity,
        "files": records,
    }


def verify_fetch_receipt(
    receipt: dict[str, Any],
    *,
    config: dict[str, Any],
    cell: dict[str, Any],
    launch: dict[str, Any],
    bundle_verification: dict[str, Any],
) -> dict[str, Any]:
    """Cross-bind the installed files, launch, AWS request, and S3 objects."""

    if set(receipt) != FETCH_RECEIPT_KEYS:
        raise ValueError("fetch receipt fields differ from the exact receipt contract")
    expected_identity = {
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
        "rows": bundle_verification["rows"],
        "generations": bundle_verification["generations"],
        "expected_cloud_metadata": bundle_verification[
            "expected_cloud_metadata"
        ],
        "integrity_verification": bundle_verification[
            "integrity_verification"
        ],
        "files": bundle_verification["files"],
    }
    for key, expected in expected_identity.items():
        if canonical_bytes(receipt.get(key)) != canonical_bytes(expected):
            raise ValueError(f"fetch receipt identity/integrity mismatch: {key}")

    request = receipt.get("aws_request_verification")
    expected_request_fields = [
        "RoleArn",
        "AlgorithmSpecification",
        "InputDataConfig",
        "OutputDataConfig",
        "ResourceConfig",
        "StoppingCondition",
        "Environment",
        "EnableNetworkIsolation",
        "Tags",
    ]
    if (
        not isinstance(request, dict)
        or set(request)
        != {
            "status",
            "request_sha256",
            "training_job_arn",
            "source",
            "verified_request_fields",
        }
        or request.get("status") != "PASS"
        or request.get("request_sha256") != launch["request_sha256"]
        or request.get("training_job_arn") != launch["training_job_arn"]
        or canonical_bytes(request.get("source"))
        != canonical_bytes(launch["source"])
        or request.get("verified_request_fields") != expected_request_fields
    ):
        raise ValueError("fetch receipt AWS request verification mismatch")

    source = receipt.get("source_object")
    launch_source = launch["source"]
    if (
        not isinstance(source, dict)
        or set(source)
        != {"bucket", "key", "version_id", "sha256", "size_bytes"}
        or any(source.get(key) != launch_source[key] for key in launch_source)
        or type(source.get("size_bytes")) is not int
        or int(source["size_bytes"]) <= 0
    ):
        raise ValueError("fetch receipt source object mismatch")

    artifact = receipt.get("model_artifact")
    if (
        not isinstance(artifact, dict)
        or set(artifact)
        != {
            "bucket",
            "key",
            "version_id",
            "sha256",
            "size_bytes",
            "etag",
            "server_side_encryption",
        }
        or not str(artifact.get("version_id", ""))
        or str(artifact.get("version_id", "")).casefold() == "null"
        or re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", "")))
        is None
        or type(artifact.get("size_bytes")) is not int
        or int(artifact["size_bytes"]) <= 0
    ):
        raise ValueError("fetch receipt model artifact identity is malformed")
    artifact_uri = str(receipt.get("model_artifact_uri", ""))
    if parse_s3_uri(artifact_uri) != (artifact["bucket"], artifact["key"]):
        raise ValueError("fetch receipt model artifact URI mismatch")
    return {
        "status": "PASS",
        "job_name": launch["job_name"],
        "git_commit": launch["git_commit"],
        "request_sha256": launch["request_sha256"],
        "source_version_id": launch_source["version_id"],
        "model_artifact_version_id": artifact["version_id"],
        "model_artifact_sha256": artifact["sha256"],
    }


def _aws_time(value: Any, *, label: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not an AWS ISO-8601 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is not an AWS ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} is not timezone aware")
    return parsed


def validate_remote_timeline(
    described: dict[str, Any],
    *,
    launch: dict[str, Any],
    artifact_listing: dict[str, Any],
) -> None:
    creation = _aws_time(described.get("CreationTime"), label="CreationTime")
    submitted = _aws_time(
        launch.get("submitted_at_utc"), label="submitted_at_utc"
    )
    training_start = _aws_time(
        described.get("TrainingStartTime"), label="TrainingStartTime"
    )
    training_end = _aws_time(
        described.get("TrainingEndTime"), label="TrainingEndTime"
    )
    job_last_modified = _aws_time(
        described.get("LastModifiedTime"), label="LastModifiedTime"
    )
    artifact_time = _aws_time(
        artifact_listing.get("LastModified"), label="artifact LastModified"
    )
    if not creation <= submitted <= training_start <= training_end <= job_last_modified:
        raise ValueError("registered job timestamps are not monotonically ordered")
    if not training_start <= artifact_time <= training_end + dt.timedelta(minutes=5):
        raise ValueError("model artifact version timestamp is outside the job window")


def resolve_registered_remote_artifact(
    config: dict[str, Any],
    *,
    cell: dict[str, Any],
    launch: dict[str, Any],
    profile: str,
    region: str,
) -> dict[str, Any]:
    """Recheck AWS and resolve the sole version at the exact job artifact key."""

    validate_launch_manifest(config, cell=cell, launch=launch)
    described = json.loads(
        aws(
            profile,
            region,
            "sagemaker",
            "describe-training-job",
            "--training-job-name",
            launch["job_name"],
            "--output",
            "json",
        )
    )
    if described.get("TrainingJobStatus") != "Completed":
        raise ValueError(
            "registered development job is not Completed: "
            f"{described.get('TrainingJobStatus')}"
        )
    artifact_uri = str(
        described.get("ModelArtifacts", {}).get("S3ModelArtifacts", "")
    )
    if artifact_uri != expected_model_artifact_uri(config):
        raise ValueError("training job model artifact URI differs from exact job key")
    tags_payload = json.loads(
        aws(
            profile,
            region,
            "sagemaker",
            "list-tags",
            "--resource-arn",
            described["TrainingJobArn"],
            "--output",
            "json",
        )
    )
    request_verification = verify_aws_request(
        config,
        cell=cell,
        launch=launch,
        described=described,
        observed_tags=tags_payload.get("Tags", []),
    )

    source = launch["source"]
    source_versioning = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "get-bucket-versioning",
            "--bucket",
            source["bucket"],
            "--output",
            "json",
        )
        or "{}"
    )
    if source_versioning.get("Status") != "Enabled":
        raise ValueError("source bucket versioning is not Enabled")
    source_head = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "head-object",
            "--bucket",
            source["bucket"],
            "--key",
            source["key"],
            "--version-id",
            source["version_id"],
            "--output",
            "json",
        )
    )
    if (
        source_head.get("VersionId") != source["version_id"]
        or str(source_head.get("VersionId", "")).casefold() == "null"
        or source_head.get("Metadata", {}).get("sha256") != source["sha256"]
        or source_head.get("ServerSideEncryption") != "AES256"
        or int(source_head.get("ContentLength", 0)) <= 0
    ):
        raise ValueError("versioned source object metadata differs from launch")

    artifact_bucket, artifact_key = parse_s3_uri(artifact_uri)
    artifact_versioning = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "get-bucket-versioning",
            "--bucket",
            artifact_bucket,
            "--output",
            "json",
        )
        or "{}"
    )
    if artifact_versioning.get("Status") != "Enabled":
        raise ValueError("model artifact bucket versioning is not Enabled")
    listing = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "list-object-versions",
            "--bucket",
            artifact_bucket,
            "--prefix",
            artifact_key,
            "--output",
            "json",
        )
    )
    if listing.get("IsTruncated") is True:
        raise ValueError("model artifact version listing is truncated")
    artifact_listing = select_unique_artifact_version(
        listing, artifact_key=artifact_key
    )
    artifact_version = str(artifact_listing["VersionId"])
    artifact_head = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "head-object",
            "--bucket",
            artifact_bucket,
            "--key",
            artifact_key,
            "--version-id",
            artifact_version,
            "--output",
            "json",
        )
    )
    if (
        artifact_head.get("VersionId") != artifact_version
        or int(artifact_head.get("ContentLength", 0))
        != int(artifact_listing["Size"])
        or artifact_head.get("ETag") != artifact_listing.get("ETag")
    ):
        raise ValueError("versioned model artifact head differs from version listing")
    validate_remote_timeline(
        described, launch=launch, artifact_listing=artifact_listing
    )
    return {
        "described": described,
        "request_verification": request_verification,
        "source_head": source_head,
        "artifact_uri": artifact_uri,
        "artifact_bucket": artifact_bucket,
        "artifact_key": artifact_key,
        "artifact_version": artifact_version,
        "artifact_head": artifact_head,
        "artifact_listing": artifact_listing,
    }


def _download_s3_version(
    *,
    bucket: str,
    key: str,
    version_id: str,
    destination: Path,
    profile: str,
    region: str,
) -> None:
    if not version_id or version_id.casefold() == "null":
        raise ValueError("refusing to download an unversioned S3 object")
    subprocess.run(
        [
            "aws",
            "s3api",
            "get-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--version-id",
            version_id,
            str(destination),
            "--profile",
            profile,
            "--region",
            region,
        ],
        cwd=ROOT,
        check=True,
    )


def download_verified_remote_bundle(
    config: dict[str, Any],
    *,
    cell: dict[str, Any],
    launch: dict[str, Any],
    destination: Path,
    profile: str,
    region: str,
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Download, replay, and return the exact registered remote bundle."""

    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("remote-verification destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    remote = resolve_registered_remote_artifact(
        config,
        cell=cell,
        launch=launch,
        profile=profile,
        region=region,
    )
    source = launch["source"]
    source_archive = destination / "source.tar.gz"
    _download_s3_version(
        bucket=source["bucket"],
        key=source["key"],
        version_id=source["version_id"],
        destination=source_archive,
        profile=profile,
        region=region,
    )
    if (
        source_archive.stat().st_size
        != int(remote["source_head"]["ContentLength"])
        or sha256_file(source_archive) != source["sha256"]
    ):
        raise ValueError("downloaded versioned source archive differs from launch")

    artifact_archive = destination / "model.tar.gz"
    _download_s3_version(
        bucket=remote["artifact_bucket"],
        key=remote["artifact_key"],
        version_id=remote["artifact_version"],
        destination=artifact_archive,
        profile=profile,
        region=region,
    )
    artifact_sha256 = sha256_file(artifact_archive)
    if artifact_archive.stat().st_size != int(
        remote["artifact_head"]["ContentLength"]
    ):
        raise ValueError("downloaded model artifact size differs from S3 head")
    extracted = destination / "extracted"
    extracted.mkdir()
    safe_extract(artifact_archive, extracted)
    bundle = extracted / "px057_h5_development_pilot" / cell["cell_id"]
    if not bundle.is_dir():
        raise ValueError(f"model artifact lacks expected bundle: {bundle}")
    expected_artifact_files = {
        f"px057_h5_development_pilot/{cell['cell_id']}/{name}"
        for name in FILES
    }
    observed_artifact_files = {
        str(path.relative_to(extracted)).replace("\\", "/")
        for path in extracted.rglob("*")
        if path.is_file()
    }
    if observed_artifact_files != expected_artifact_files:
        raise ValueError("model artifact regular-file set differs from exact bundle")
    verification = verify_bundle(
        bundle,
        config=config,
        cell=cell,
        launch=launch,
    )

    if receipt is not None:
        receipt_verification = verify_fetch_receipt(
            receipt,
            config=config,
            cell=cell,
            launch=launch,
            bundle_verification=verification,
        )
        expected_source = {
            "bucket": source["bucket"],
            "key": source["key"],
            "version_id": source["version_id"],
            "sha256": source["sha256"],
            "size_bytes": int(remote["source_head"]["ContentLength"]),
        }
        expected_artifact = {
            "bucket": remote["artifact_bucket"],
            "key": remote["artifact_key"],
            "version_id": remote["artifact_version"],
            "sha256": artifact_sha256,
            "size_bytes": int(remote["artifact_head"]["ContentLength"]),
            "etag": remote["artifact_head"].get("ETag"),
            "server_side_encryption": remote["artifact_head"].get(
                "ServerSideEncryption"
            ),
        }
        if (
            canonical_bytes(receipt.get("aws_request_verification"))
            != canonical_bytes(remote["request_verification"])
            or receipt.get("model_artifact_uri") != remote["artifact_uri"]
            or canonical_bytes(receipt.get("source_object"))
            != canonical_bytes(expected_source)
            or canonical_bytes(receipt.get("model_artifact"))
            != canonical_bytes(expected_artifact)
        ):
            raise ValueError("fetch receipt differs from independently rechecked AWS/S3")
    else:
        receipt_verification = None
    return {
        "bundle": bundle,
        "verification": verification,
        "remote": remote,
        "artifact_sha256": artifact_sha256,
        "receipt_verification": receipt_verification,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    parser.add_argument("--cell", required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    if config_path.resolve() != DEFAULT_CONFIG.resolve():
        raise ValueError("fetch requires the committed default development config")
    config = read_json(config_path)
    validate_frozen_development_config(config)
    require_c1(args.cell)
    matches = [cell for cell in config["cells"] if cell["cell_id"] == args.cell]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate cell: {args.cell}")
    cell = matches[0]
    launch_path = (
        ROOT
        / "manifests/px057_h5_development_pilot_20260727/launches"
        / f"{cell['cell_id']}_r2.json"
    )
    launch = read_json(launch_path)
    validate_launch_manifest(config, cell=cell, launch=launch)
    verify_local_execution_tree(launch)
    aws_config = config["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    source = launch["source"]
    output_dir = ROOT / cell["output_dir"]
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"local development output is immutable: {output_dir}")

    with tempfile.TemporaryDirectory(prefix="px057-h5-dev-fetch-") as temp:
        downloaded = download_verified_remote_bundle(
            config,
            cell=cell,
            launch=launch,
            destination=Path(temp),
            profile=profile,
            region=region,
        )
        bundle = downloaded["bundle"]
        verification = downloaded["verification"]
        remote = downloaded["remote"]
        artifact_sha256 = downloaded["artifact_sha256"]
        output_dir.mkdir(parents=True, exist_ok=False)
        for name in FILES:
            shutil.copy2(bundle / name, output_dir / name)
        installed_verification = verify_bundle(
            output_dir,
            config=config,
            cell=cell,
            launch=launch,
        )
        if canonical_bytes(installed_verification) != canonical_bytes(verification):
            raise ValueError("installed bundle differs from verified artifact bundle")
        verification = installed_verification
    artifact_uri = remote["artifact_uri"]
    request_verification = remote["request_verification"]
    source_head = remote["source_head"]
    artifact_bucket = remote["artifact_bucket"]
    artifact_key = remote["artifact_key"]
    artifact_version = remote["artifact_version"]
    artifact_head = remote["artifact_head"]
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
        "rows": verification["rows"],
        "generations": verification["generations"],
        "expected_cloud_metadata": copy.deepcopy(
            verification["expected_cloud_metadata"]
        ),
        "integrity_verification": copy.deepcopy(
            verification["integrity_verification"]
        ),
        "files": copy.deepcopy(verification["files"]),
        "model_artifact_uri": artifact_uri,
        "aws_request_verification": copy.deepcopy(request_verification),
        "source_object": {
            "bucket": source["bucket"],
            "key": source["key"],
            "version_id": source["version_id"],
            "sha256": source["sha256"],
            "size_bytes": int(source_head["ContentLength"]),
        },
        "model_artifact": {
            "bucket": artifact_bucket,
            "key": artifact_key,
            "version_id": artifact_version,
            "sha256": artifact_sha256,
            "size_bytes": int(artifact_head["ContentLength"]),
            "etag": artifact_head.get("ETag"),
            "server_side_encryption": artifact_head.get("ServerSideEncryption"),
        },
    }
    verify_fetch_receipt(
        receipt,
        config=config,
        cell=cell,
        launch=launch,
        bundle_verification=verification,
    )
    receipt_path = output_dir / "fetch_receipt.json"
    with receipt_path.open("xb") as handle:
        handle.write(canonical_bytes(receipt))
    persisted_receipt = read_json(receipt_path)
    verify_fetch_receipt(
        persisted_receipt,
        config=config,
        cell=cell,
        launch=launch,
        bundle_verification=verification,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
