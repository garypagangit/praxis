#!/usr/bin/env python
"""Outcome-blind, version-pinned fetch/seal gate for PX-062 Gate 2.1.

The fetcher authenticates both the submitted source bundle and completed model
artifact.  It copies raw adjudication inputs without parsing or printing model
responses and never invokes the adjudicator.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import urlparse


DEFAULT_REGISTRATION = Path("manifests/px062_gate2_20260727/retry_registration.json")
DEFAULT_LAUNCH_RECEIPT = Path("manifests/px062_gate2_20260727/launch_receipt.json")
DEFAULT_FETCH_REGISTRATION = Path(
    "manifests/px062_gate2_20260727/fetch_registration.json"
)
DEFAULT_DESTINATION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_skill_hallucination_v1_1_20260726"
)
FETCHER_PATH = "scripts/fetch_px062_gate2_v11_results.py"
FETCHER_TEST_PATH = "tests/test_px062_gate2_fetch.py"
LAUNCH_RECEIPT_COMMIT = "dbeb7e2e1dd365166e7f31934428c63fb41a7ba7"

SOURCE_MEMBER_CONTRACT = {
    "bundle_manifest.json": {
        "bytes": 1440,
        "sha256": "5cecfa290f96213e847dfeb58bd546b28d7ecc4cd4730071d9fbb1eb236d66a6",
    },
    "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt": {
        "bytes": 79,
        "sha256": "2277687fb746306ed7df0f03d0b117c71dffeebe1e0cc3d407a9197dfddb49ed",
    },
    "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py": {
        "bytes": 1001,
        "sha256": "b2b9b92306fea67aa46fc5c4847c6a1e3146f75ea3d76e41d2fb65cfd3405d62",
    },
    "configs/px062_skill_hallucination_gate2_v1_1_20260726.json": {
        "bytes": 2526,
        "sha256": "8fe4e9e5d141e111b6d4c03aac567da33d14a6f41642682db4727d077f23a1ec",
    },
    "data/px062/hallucination_benchmark/registry_names.json": {
        "bytes": 1145,
        "sha256": "2c447b5eee07b2f2930fc8649860652b36d4902dafadfa83e3f5d7aa041a76db",
    },
    "data/px062/hallucination_benchmark/tasks.jsonl": {
        "bytes": 119801,
        "sha256": "fbda2e8039d2a6087fb1cd3584470269c3e2c409d4bbe13f7eb1e59a4fc19316",
    },
    "requirements.txt": {
        "bytes": 79,
        "sha256": "2277687fb746306ed7df0f03d0b117c71dffeebe1e0cc3d407a9197dfddb49ed",
    },
    "scripts/run_px062_skill_hallucination_models.py": {
        "bytes": 9354,
        "sha256": "0e47aaf7fcb912f3d864abae44bc877e75f7f983441fbe0da3b8702cdb43eb65",
    },
}
OUTPUT_MEMBER_CONTRACT = {
    "px062_gate2": {"kind": "directory", "bytes": 0},
    "px062_gate2/source_bundle_manifest.json": {"kind": "file", "bytes": 1440},
    "px062_gate2/collection_summary.json": {"kind": "file", "bytes": 1228},
    "px062_gate2/model_outputs.jsonl": {"kind": "file", "bytes": 979134},
    "px062_gate2/frozen_config.json": {"kind": "file", "bytes": 2526},
}
SOURCE_ARCHIVE_MAX_BYTES = 32 * 1024
SOURCE_UNCOMPRESSED_MAX_BYTES = 256 * 1024
OUTPUT_ARCHIVE_MAX_BYTES = 128 * 1024
OUTPUT_UNCOMPRESSED_MAX_BYTES = 2 * 1024 * 1024
SEALED_FILES = {
    "frozen_config.json",
    "tasks.jsonl",
    "registry_names.json",
    "model_outputs.jsonl",
    "collection_summary.json",
    "completion_fetch_receipt.json",
}
DESCRIPTION_KEYS = {
    "TrainingJobName",
    "TrainingJobArn",
    "ModelArtifacts",
    "TrainingJobStatus",
    "SecondaryStatus",
    "HyperParameters",
    "AlgorithmSpecification",
    "RoleArn",
    "InputDataConfig",
    "OutputDataConfig",
    "ResourceConfig",
    "StoppingCondition",
    "CreationTime",
    "TrainingStartTime",
    "TrainingEndTime",
    "LastModifiedTime",
    "SecondaryStatusTransitions",
    "EnableNetworkIsolation",
    "EnableInterContainerTrafficEncryption",
    "EnableManagedSpotTraining",
    "TrainingTimeInSeconds",
    "BillableTimeInSeconds",
    "ProfilingStatus",
    "Environment",
}
NESTED_DESCRIPTION_KEYS = {
    "AlgorithmSpecification": {
        "TrainingImage",
        "TrainingInputMode",
        "EnableSageMakerMetricsTimeSeries",
    },
    "OutputDataConfig": {"KmsKeyId", "S3OutputPath", "CompressionType"},
    "ResourceConfig": {"InstanceType", "InstanceCount", "VolumeSizeInGB"},
    "StoppingCondition": {"MaxRuntimeInSeconds"},
}

AwsCall = Callable[..., Any]
AwsDownload = Callable[..., Mapping[str, Any]]
GitBlobRead = Callable[[Path, str, str], bytes]
GitStateRead = Callable[[Path], Mapping[str, Any]]


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path, name: str) -> str:
    if name == "sha256":
        digest = hashlib.sha256()
    elif name == "md5":
        digest = hashlib.md5(usedforsecurity=False)
    else:  # pragma: no cover - internal contract
        raise ValueError(name)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON in {label}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def load_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    return raw, strict_json_bytes(raw, str(path))


def repo_path(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {candidate}") from exc
    return resolved


def aws_json(profile: str, region: str, *arguments: str) -> Any:
    raw = subprocess.check_output(
        [
            "aws",
            *arguments,
            "--profile",
            profile,
            "--region",
            region,
            "--output",
            "json",
        ]
    )
    return strict_json_bytes(raw, "AWS CLI response")


def aws_download(
    profile: str,
    region: str,
    bucket: str,
    key: str,
    version_id: str,
    destination: Path,
) -> Mapping[str, Any]:
    raw = subprocess.check_output(
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
            "--checksum-mode",
            "ENABLED",
            str(destination),
            "--profile",
            profile,
            "--region",
            region,
            "--output",
            "json",
        ]
    )
    return strict_json_bytes(raw, "AWS get-object response")


def git_blob(root: Path, revision: str, relative_path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Git revision must be a full lowercase SHA")
    posix = PurePosixPath(relative_path)
    if posix.is_absolute() or ".." in posix.parts or "\\" in relative_path:
        raise ValueError("unsafe Git evidence path")
    return subprocess.check_output(
        ["git", "-C", str(root), "show", f"{revision}:{relative_path}"]
    )


def git_state(root: Path) -> Mapping[str, Any]:
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
    ).strip()
    branch = subprocess.check_output(
        ["git", "-C", str(root), "branch", "--show-current"],
        text=True,
        encoding="utf-8",
    ).strip()
    status = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        text=True,
        encoding="utf-8",
    )
    refs = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "for-each-ref",
            "--format=%(refname:short)",
            "--contains",
            head,
            "refs/remotes/",
        ],
        text=True,
        encoding="utf-8",
    ).splitlines()
    return {
        "branch": branch,
        "clean": status == "",
        "head": head,
        "remote_refs": sorted(ref for ref in refs if not ref.endswith("/HEAD")),
    }


def normalized_text_sha256(raw: bytes) -> str:
    return sha256_bytes(raw.replace(b"\r\n", b"\n"))


def parse_time(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {label}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"timezone missing: {label}")
    return parsed.astimezone(timezone.utc)


def parse_s3(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or not parsed.path.startswith("/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path[1:]


def validate_prefetch_registration(
    root: Path,
    path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
    registration: Mapping[str, Any],
    launch_path: Path,
    request_path: Path,
    blob_reader: GitBlobRead,
    state_reader: GitStateRead,
) -> Mapping[str, Any]:
    expected_keys = {
        "schema_version",
        "experiment_id",
        "protocol_version",
        "registered_at_utc",
        "purpose",
        "branch",
        "required_state",
        "launch_receipt_commit",
        "source_commit",
        "registration_path",
        "launch_receipt_path",
        "request_path",
        "fetcher",
        "tests",
        "source_archive",
        "output_artifact",
    }
    if set(payload) != expected_keys:
        raise ValueError("prefetch registration schema drift")
    if payload["schema_version"] != "px062-fetch-registration-v1":
        raise ValueError("unexpected prefetch registration schema")
    if payload["experiment_id"] != registration["experiment_id"]:
        raise ValueError("prefetch experiment mismatch")
    if payload["protocol_version"] != registration["protocol_version"]:
        raise ValueError("prefetch protocol mismatch")
    if payload["launch_receipt_commit"] != LAUNCH_RECEIPT_COMMIT:
        raise ValueError("prefetch launch receipt commit mismatch")
    if payload["source_commit"] != registration["source_commit"]:
        raise ValueError("prefetch source commit mismatch")
    expected_paths = {
        "registration_path": Path(payload["registration_path"]),
        "launch_receipt_path": Path(payload["launch_receipt_path"]),
        "request_path": Path(payload["request_path"]),
    }
    observed_paths = {
        "registration_path": path.parent / "retry_registration.json",
        "launch_receipt_path": launch_path,
        "request_path": request_path,
    }
    for label in expected_paths:
        if repo_path(root, expected_paths[label]) != observed_paths[label].resolve():
            raise ValueError(f"prefetch {label} mismatch")
    if payload["fetcher"].get("path") != FETCHER_PATH:
        raise ValueError("prefetch fetcher path mismatch")
    if payload["tests"].get("path") != FETCHER_TEST_PATH:
        raise ValueError("prefetch test path mismatch")
    source = registration["source_bundle"]
    expected_source = {
        "bucket": source["bucket"],
        "key": source["key"],
        "version_id": source["version_id"],
        "etag": source["etag"].strip('"'),
        "bytes": source["bytes"],
        "sha256": source["sha256"],
        "checksum_sha256_base64": source["checksum_sha256_base64"],
        "last_modified_utc": source["uploaded_at_utc"],
        "checksum_algorithm": ["SHA256"],
        "checksum_type": "FULL_OBJECT",
    }
    if payload["source_archive"] != expected_source:
        raise ValueError("prefetch source artifact mismatch")

    state = dict(state_reader(root))
    if not state.get("clean"):
        raise ValueError("repository must be clean before fetching")
    if state.get("branch") != payload["branch"]:
        raise ValueError("prefetch branch mismatch")
    head = state.get("head", "")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("invalid current Git HEAD")
    if not state.get("remote_refs"):
        raise ValueError("current fetch code commit is not present on a remote ref")
    evidence = (
        (path, None, "prefetch registration"),
        (
            repo_path(root, Path(FETCHER_PATH)),
            payload["fetcher"]["sha256"],
            "fetcher",
        ),
        (
            repo_path(root, Path(FETCHER_TEST_PATH)),
            payload["tests"]["sha256"],
            "fetcher tests",
        ),
    )
    for local_path, expected_hash, label in evidence:
        local_raw = local_path.read_bytes()
        relative = local_path.relative_to(root).as_posix()
        if blob_reader(root, head, relative) != local_raw:
            raise ValueError(f"{label} differs from pushed fetch commit")
        if expected_hash is not None and expected_hash != sha256_bytes(local_raw):
            raise ValueError(f"{label} hash mismatch")
    return state


def validate_local_evidence(
    root: Path,
    registration_path: Path,
    launch_path: Path,
    prefetch_path: Path,
    blob_reader: GitBlobRead,
    state_reader: GitStateRead,
) -> dict[str, Any]:
    registration_raw, registration = load_json(registration_path)
    launch_raw, launch = load_json(launch_path)
    prefetch_raw, prefetch = load_json(prefetch_path)
    request_path = repo_path(root, Path(registration["request_file"]))
    request_raw, request = load_json(request_path)
    if normalized_text_sha256(request_raw) != registration["request_sha256"]:
        raise ValueError("request hash does not match registration")
    if launch["request_sha256"] != registration["request_sha256"]:
        raise ValueError("launch request hash mismatch")
    if request["TrainingJobName"] != registration["job_name"]:
        raise ValueError("request job name mismatch")
    source = registration["source_bundle"]
    source_uri = f"s3://{source['bucket']}/{source['key']}"
    if request["HyperParameters"]["sagemaker_submit_directory"] != source_uri:
        raise ValueError("request source URI mismatch")
    selected_config = request["Environment"]["PX062_CONFIG"]
    if selected_config != launch["selected_config"]:
        raise ValueError("request/launch config mismatch")
    frozen = registration["frozen_collection"]
    image = request["AlgorithmSpecification"]["TrainingImage"]
    if "@" not in image or image.rsplit("@", 1)[1] != frozen["container_image_digest"]:
        raise ValueError("request container digest mismatch")
    if request["ResourceConfig"]["InstanceType"] != frozen["instance_type"]:
        raise ValueError("request instance mismatch")
    if request["StoppingCondition"]["MaxRuntimeInSeconds"] != frozen[
        "max_runtime_seconds"
    ]:
        raise ValueError("request runtime mismatch")
    cross_checks = {
        launch["experiment_id"]: registration["experiment_id"],
        launch["training_job_name"]: registration["job_name"],
        launch["source_bundle_sha256"]: source["sha256"],
        launch["source_version_id"]: source["version_id"],
        launch["source_etag"].strip('"'): source["etag"].strip('"'),
        launch["container_image_digest"]: frozen["container_image_digest"],
        launch["instance_type"]: frozen["instance_type"],
        launch["max_runtime_seconds"]: frozen["max_runtime_seconds"],
    }
    if any(observed != expected for observed, expected in cross_checks.items()):
        raise ValueError("launch/registration binding mismatch")
    if launch["matching_training_jobs"] != 1:
        raise ValueError("launch did not observe exactly one registered job")
    registration_commit = launch["registration_commit"]
    for local_path, revision in (
        (registration_path, registration_commit),
        (request_path, registration_commit),
        (launch_path, LAUNCH_RECEIPT_COMMIT),
    ):
        relative = local_path.relative_to(root).as_posix()
        if blob_reader(root, revision, relative) != local_path.read_bytes():
            raise ValueError(f"committed evidence mismatch: {relative}")
    state = validate_prefetch_registration(
        root,
        prefetch_path,
        prefetch_raw,
        prefetch,
        registration,
        launch_path,
        request_path,
        blob_reader,
        state_reader,
    )
    return {
        "registration": registration,
        "registration_raw": registration_raw,
        "launch": launch,
        "launch_raw": launch_raw,
        "prefetch": prefetch,
        "prefetch_raw": prefetch_raw,
        "request": request,
        "request_raw": request_raw,
        "request_path": request_path,
        "git_state": state,
    }


def validate_job(
    description: Mapping[str, Any],
    request: Mapping[str, Any],
    registration: Mapping[str, Any],
    launch: Mapping[str, Any],
) -> tuple[str, datetime, datetime, datetime]:
    if set(description) != DESCRIPTION_KEYS:
        raise ValueError("closed-world SageMaker top-level schema drift")
    for field, expected_keys in NESTED_DESCRIPTION_KEYS.items():
        if not isinstance(description[field], dict) or set(description[field]) != expected_keys:
            raise ValueError(f"closed-world SageMaker {field} schema drift")
    if set(description["ModelArtifacts"]) != {"S3ModelArtifacts"}:
        raise ValueError("closed-world SageMaker ModelArtifacts drift")
    if set(description["HyperParameters"]) != set(request["HyperParameters"]):
        raise ValueError("closed-world SageMaker hyperparameter drift")
    if set(description["Environment"]) != set(request["Environment"]):
        raise ValueError("closed-world SageMaker environment drift")
    projection = {
        key: (
            {
                nested: description[key][nested]
                for nested in request[key]
            }
            if key in NESTED_DESCRIPTION_KEYS
            else description[key]
        )
        for key in request
    }
    if projection != request:
        raise ValueError("live SageMaker request differs from registered request")
    exact_defaults = {
        "InputDataConfig": [],
        "EnableInterContainerTrafficEncryption": False,
        "EnableManagedSpotTraining": False,
        "ProfilingStatus": "Disabled",
    }
    for field, expected in exact_defaults.items():
        if description[field] != expected:
            raise ValueError(f"unexpected SageMaker default: {field}")
    if description["AlgorithmSpecification"]["EnableSageMakerMetricsTimeSeries"] is not False:
        raise ValueError("unexpected SageMaker metrics setting")
    if description["OutputDataConfig"]["KmsKeyId"] != "":
        raise ValueError("unexpected output KMS drift")
    if description["OutputDataConfig"]["CompressionType"] != "GZIP":
        raise ValueError("unexpected output compression drift")
    if description["TrainingJobStatus"] != "Completed":
        raise ValueError("registered SageMaker job is not Completed")
    if description["SecondaryStatus"] != "Completed":
        raise ValueError("registered SageMaker secondary status is not Completed")
    if description["TrainingJobName"] != registration["job_name"]:
        raise ValueError("SageMaker job name mismatch")
    if description["TrainingJobArn"] != launch["training_job_arn"]:
        raise ValueError("SageMaker job ARN mismatch")
    transitions = description["SecondaryStatusTransitions"]
    if [row.get("Status") for row in transitions] != [
        "Starting",
        "Pending",
        "Downloading",
        "Training",
        "Uploading",
        "Completed",
    ]:
        raise ValueError("unexpected SageMaker status-transition sequence")
    for row in transitions:
        if set(row) != {"Status", "StartTime", "EndTime", "StatusMessage"}:
            raise ValueError("SageMaker transition schema drift")
        if parse_time(row["StartTime"], "transition start") > parse_time(
            row["EndTime"], "transition end"
        ):
            raise ValueError("invalid SageMaker transition timing")
    creation = parse_time(description["CreationTime"], "CreationTime")
    start = parse_time(description["TrainingStartTime"], "TrainingStartTime")
    end = parse_time(description["TrainingEndTime"], "TrainingEndTime")
    modified = parse_time(description["LastModifiedTime"], "LastModifiedTime")
    if creation != parse_time(launch["launched_at_utc"], "launch time"):
        raise ValueError("SageMaker creation time mismatch")
    if not creation <= start <= end <= modified:
        raise ValueError("invalid SageMaker lifecycle timing")
    elapsed = description["TrainingTimeInSeconds"]
    billable = description["BillableTimeInSeconds"]
    if (
        not isinstance(elapsed, int)
        or elapsed <= 0
        or billable != elapsed
        or elapsed > request["StoppingCondition"]["MaxRuntimeInSeconds"]
    ):
        raise ValueError("unexpected SageMaker runtime accounting")
    artifact = (
        request["OutputDataConfig"]["S3OutputPath"].rstrip("/")
        + f"/{registration['job_name']}/output/model.tar.gz"
    )
    if description["ModelArtifacts"]["S3ModelArtifacts"] != artifact:
        raise ValueError("SageMaker artifact URI mismatch")
    return artifact, creation, start, end


def validate_listing(
    listing: Mapping[str, Any], key: str, expected: Mapping[str, Any], label: str
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    if listing.get("IsTruncated") is True or listing.get("NextKeyMarker"):
        raise ValueError(f"{label} version listing is truncated")
    versions = [row for row in listing.get("Versions", []) if row.get("Key") == key]
    markers = [row for row in listing.get("DeleteMarkers", []) if row.get("Key") == key]
    if len(versions) != 1 or markers:
        raise ValueError(f"{label} must have one version and no delete marker")
    row = versions[0]
    checks = {
        "VersionId": expected["version_id"],
        "ETag": f'"{expected["etag"]}"',
        "Size": expected["bytes"],
        "IsLatest": True,
        "ChecksumAlgorithm": expected["checksum_algorithm"],
        "ChecksumType": expected["checksum_type"],
    }
    for field, value in checks.items():
        if row.get(field) != value:
            raise ValueError(f"{label} version {field} mismatch")
    if not row["VersionId"] or row["VersionId"] == "null":
        raise ValueError(f"{label} version ID is null")
    listed_time = parse_time(row.get("LastModified"), f"{label} listed time")
    expected_time = parse_time(
        expected["last_modified_utc"], f"{label} expected listed time"
    )
    if listed_time != expected_time:
        raise ValueError(f"{label} version LastModified mismatch")
    fingerprint = {field: row[field] for field in checks}
    fingerprint["Key"] = key
    fingerprint["LastModified"] = expected_time.isoformat().replace("+00:00", "Z")
    return row, fingerprint


def validate_head(
    head: Mapping[str, Any],
    expected: Mapping[str, Any],
    label: str,
    earliest: datetime | None,
    latest: datetime,
) -> datetime:
    checks = {
        "VersionId": expected["version_id"],
        "ETag": f'"{expected["etag"]}"',
        "ContentLength": expected["bytes"],
        "ChecksumType": expected["checksum_type"],
    }
    for field, value in checks.items():
        if head.get(field) != value:
            raise ValueError(f"{label} head {field} mismatch")
    if "checksum_sha256_base64" in expected:
        if head.get("ChecksumSHA256") != expected["checksum_sha256_base64"]:
            raise ValueError(f"{label} SHA-256 checksum mismatch")
        if head.get("Metadata", {}).get("sha256") != expected["sha256"]:
            raise ValueError(f"{label} SHA-256 metadata mismatch")
    if "checksum_crc32c_base64" in expected and head.get("ChecksumCRC32C") != expected[
        "checksum_crc32c_base64"
    ]:
        raise ValueError(f"{label} CRC32C checksum mismatch")
    modified = parse_time(head.get("LastModified"), f"{label} LastModified")
    if modified != parse_time(
        expected["last_modified_utc"], f"{label} expected LastModified"
    ):
        raise ValueError(f"{label} head LastModified mismatch")
    if earliest is not None and modified < earliest:
        raise ValueError(f"{label} predates its permitted window")
    if modified >= latest:
        raise ValueError(f"{label} was not frozen before its deadline")
    return modified


def validate_download(
    archive: Path,
    response: Mapping[str, Any],
    expected: Mapping[str, Any],
    label: str,
    compressed_ceiling: int,
) -> dict[str, Any]:
    if response.get("VersionId") != expected["version_id"]:
        raise ValueError(f"{label} get-object version mismatch")
    if response.get("ETag") != f'"{expected["etag"]}"':
        raise ValueError(f"{label} get-object ETag mismatch")
    if "checksum_sha256_base64" in expected and response.get(
        "ChecksumSHA256"
    ) != expected["checksum_sha256_base64"]:
        raise ValueError(f"{label} get-object checksum mismatch")
    if "checksum_crc32c_base64" in expected and response.get(
        "ChecksumCRC32C"
    ) != expected["checksum_crc32c_base64"]:
        raise ValueError(f"{label} get-object checksum mismatch")
    size = archive.stat().st_size
    if size != expected["bytes"] or size > compressed_ceiling:
        raise ValueError(f"{label} downloaded size mismatch or ceiling exceeded")
    observed_sha = digest_file(archive, "sha256")
    if observed_sha != expected["sha256"]:
        raise ValueError(f"{label} downloaded SHA-256 mismatch")
    if not re.fullmatch(r"[0-9a-f]{32}", expected["etag"]):
        raise ValueError(f"{label} ETag is malformed")
    observed_md5 = digest_file(archive, "md5")
    # The registered source was a single-part SSE-S3 put-object, so its ETag
    # is also a plaintext MD5 and remains an independent local check.  The
    # SageMaker model artifact is SSE-KMS encrypted; AWS does not guarantee
    # that such an ETag equals the plaintext MD5.  Its downloaded bytes are
    # instead bound by the preregistered SHA-256 plus AWS's full-object CRC32C.
    if "checksum_sha256_base64" in expected and observed_md5 != expected["etag"]:
        raise ValueError(f"{label} downloaded MD5/ETag mismatch")
    if "checksum_sha256_base64" in expected:
        checksum = base64.b64encode(bytes.fromhex(observed_sha)).decode("ascii")
        if checksum != expected["checksum_sha256_base64"]:
            raise ValueError(f"{label} downloaded base64 SHA-256 mismatch")
    return {
        "bytes": size,
        "etag": expected["etag"],
        "md5": observed_md5,
        "sha256": observed_sha,
        "version_id": expected["version_id"],
    }


def validate_tar(
    handle: tarfile.TarFile,
    contract: Mapping[str, Mapping[str, Any]],
    uncompressed_ceiling: int,
    label: str,
) -> dict[str, tarfile.TarInfo]:
    members = handle.getmembers()
    names = [member.name for member in members]
    if len(names) != len(set(names)):
        raise ValueError(f"{label} contains duplicate members")
    if set(names) != set(contract):
        raise ValueError(f"{label} member set mismatch")
    total = 0
    indexed: dict[str, tarfile.TarInfo] = {}
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\\" in member.name:
            raise ValueError(f"unsafe {label} member path")
        expected = contract[member.name]
        kind = expected.get("kind", "file")
        if kind == "directory":
            if not member.isdir() or member.linkname or member.size != 0:
                raise ValueError(f"invalid {label} directory member")
        elif not member.isfile() or member.islnk() or member.issym() or member.linkname:
            raise ValueError(f"nonregular {label} member")
        if member.size != expected["bytes"]:
            raise ValueError(f"{label} member size mismatch: {member.name}")
        total += member.size
        if total > uncompressed_ceiling:
            raise ValueError(f"{label} decompressed-size ceiling exceeded")
        indexed[member.name] = member
    return indexed


def read_member(handle: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    source = handle.extractfile(member)
    if source is None:
        raise ValueError(f"unable to read archive member: {member.name}")
    raw = source.read(member.size + 1)
    if len(raw) != member.size:
        raise ValueError(f"archive member length mismatch: {member.name}")
    return raw


def validate_source_archive(
    archive: Path,
    contract: Mapping[str, Mapping[str, Any]],
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    root: Path,
    blob_reader: GitBlobRead,
    uncompressed_ceiling: int,
) -> dict[str, bytes]:
    with tarfile.open(archive, "r:gz") as handle:
        members = validate_tar(handle, contract, uncompressed_ceiling, "source archive")
        raw_files = {name: read_member(handle, member) for name, member in members.items()}
    for name, expected in contract.items():
        if sha256_bytes(raw_files[name]) != expected["sha256"]:
            raise ValueError(f"source member SHA-256 mismatch: {name}")
    manifest_raw = raw_files["bundle_manifest.json"]
    manifest = strict_json_bytes(manifest_raw, "source bundle manifest")
    expected_files = {
        name: data["sha256"] for name, data in contract.items() if name != "bundle_manifest.json"
    }
    expected_manifest = {
        "base_aborted_bundle_sha256": (
            "afe0fd3a90e605766f1da555ac7b320c44187b50689c3379829a9b121534d3fb"
        ),
        "experiment_id": registration["experiment_id"],
        "files": expected_files,
        "parser_conformance": {
            "adjudicator_preserved_nonexistent": 100,
            "collector_preserved_nonexistent": 100,
            "near_miss_count": 100,
        },
        "protocol_version": registration["protocol_version"],
        "registry_sha256": registration["source_bundle"]["registry_sha256"],
        "tasks_sha256": registration["source_bundle"]["tasks_sha256"],
    }
    if manifest != expected_manifest:
        raise ValueError("source bundle manifest is not the exact frozen inventory")
    config_path = request["Environment"]["PX062_CONFIG"]
    entrypoint = request["HyperParameters"]["sagemaker_program"]
    if config_path not in raw_files or entrypoint not in raw_files:
        raise ValueError("request-selected source files are absent")
    source_commit = registration["source_commit"]
    cloud_requirements = "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt"
    inherited_base_members = {
        "data/px062/hallucination_benchmark/tasks.jsonl",
        "data/px062/hallucination_benchmark/registry_names.json",
    }
    for name in expected_files:
        # These two ignored data files were inherited byte-for-byte from the
        # authenticated base bundle, whose exact SHA is bound above.  Every
        # executable/configuration override is instead byte-bound to the
        # registered source_commit.
        if name in inherited_base_members:
            continue
        if name == "requirements.txt":
            committed = raw_files[cloud_requirements]
        else:
            committed = blob_reader(root, source_commit, name)
        if raw_files[name] != committed:
            raise ValueError(f"source member differs from source_commit: {name}")
    config = strict_json_bytes(raw_files[config_path], "authenticated frozen config")
    benchmark = config["benchmark_dir"].rstrip("/")
    tasks_path = f"{benchmark}/tasks.jsonl"
    registry_path = f"{benchmark}/registry_names.json"
    source = registration["source_bundle"]
    if sha256_bytes(raw_files[config_path]) != source["config_sha256"]:
        raise ValueError("authenticated config hash mismatch")
    if sha256_bytes(raw_files[tasks_path]) != source["tasks_sha256"]:
        raise ValueError("authenticated tasks hash mismatch")
    if sha256_bytes(raw_files[registry_path]) != source["registry_sha256"]:
        raise ValueError("authenticated registry hash mismatch")
    return {
        "bundle_manifest": manifest_raw,
        "config": raw_files[config_path],
        "tasks": raw_files[tasks_path],
        "registry": raw_files[registry_path],
    }


def validate_output_metadata(
    config_raw: bytes,
    summary_raw: bytes,
    bundle_raw: bytes,
    source_inputs: Mapping[str, bytes],
    registration: Mapping[str, Any],
) -> None:
    if config_raw != source_inputs["config"]:
        raise ValueError("output config differs from authenticated source config")
    if bundle_raw != source_inputs["bundle_manifest"]:
        raise ValueError("output source manifest differs from authenticated source manifest")
    config = strict_json_bytes(config_raw, "output frozen config")
    summary = strict_json_bytes(summary_raw, "collection summary")
    source = registration["source_bundle"]
    for label, value in (("config", config), ("summary", summary)):
        if value["experiment_id"] != registration["experiment_id"]:
            raise ValueError(f"{label} experiment mismatch")
        if value["protocol_version"] != registration["protocol_version"]:
            raise ValueError(f"{label} protocol mismatch")
    expected_integrity = {
        "config_sha256": source["config_sha256"],
        "tasks_sha256": source["tasks_sha256"],
        "registry_sha256": source["registry_sha256"],
    }
    if summary["source_integrity"] != expected_integrity:
        raise ValueError("collection source-integrity mismatch")
    if summary["outputs"] != config["expected_outputs"]:
        raise ValueError("collection output count mismatch")
    if summary["expected_outputs"] != config["expected_outputs"]:
        raise ValueError("collection expected-output count mismatch")
    if summary["tasks"] != config["expected_tasks"]:
        raise ValueError("collection task count mismatch")
    for field in ("models", "model_revisions", "conditions"):
        if summary[field] != config[field]:
            raise ValueError(f"collection {field} mismatch")


def copy_stream(source: BinaryIO, destination: Path, size: int) -> dict[str, Any]:
    digest = hashlib.sha256()
    observed = 0
    with destination.open("xb") as target:
        while observed < size:
            chunk = source.read(min(1024 * 1024, size - observed))
            if not chunk:
                break
            target.write(chunk)
            digest.update(chunk)
            observed += len(chunk)
        if source.read(1):
            raise ValueError("model-output member exceeds registered size")
    if observed != size:
        raise ValueError("model-output member is truncated")
    return {"bytes": observed, "sha256": digest.hexdigest()}


def write_bytes(path: Path, raw: bytes) -> dict[str, Any]:
    with path.open("xb") as handle:
        handle.write(raw)
    return {"bytes": len(raw), "sha256": sha256_bytes(raw)}


def list_versions(
    aws_call: AwsCall, profile: str, region: str, bucket: str, key: str
) -> Mapping[str, Any]:
    return aws_call(
        profile,
        region,
        "s3api",
        "list-object-versions",
        "--bucket",
        bucket,
        "--prefix",
        key,
    )


def head_version(
    aws_call: AwsCall,
    profile: str,
    region: str,
    bucket: str,
    key: str,
    version_id: str,
) -> Mapping[str, Any]:
    return aws_call(
        profile,
        region,
        "s3api",
        "head-object",
        "--bucket",
        bucket,
        "--key",
        key,
        "--version-id",
        version_id,
        "--checksum-mode",
        "ENABLED",
    )


def fetch_and_seal(
    *,
    root: Path,
    profile: str,
    registration_path: Path,
    launch_path: Path,
    prefetch_path: Path,
    destination: Path,
    aws_call: AwsCall = aws_json,
    download_call: AwsDownload = aws_download,
    blob_reader: GitBlobRead = git_blob,
    state_reader: GitStateRead = git_state,
    source_contract: Mapping[str, Mapping[str, Any]] = SOURCE_MEMBER_CONTRACT,
    output_contract: Mapping[str, Mapping[str, Any]] = OUTPUT_MEMBER_CONTRACT,
    source_compressed_ceiling: int = SOURCE_ARCHIVE_MAX_BYTES,
    source_uncompressed_ceiling: int = SOURCE_UNCOMPRESSED_MAX_BYTES,
    output_compressed_ceiling: int = OUTPUT_ARCHIVE_MAX_BYTES,
    output_uncompressed_ceiling: int = OUTPUT_UNCOMPRESSED_MAX_BYTES,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    registration_path = repo_path(root, registration_path)
    launch_path = repo_path(root, launch_path)
    prefetch_path = repo_path(root, prefetch_path)
    destination = repo_path(root, destination)
    if destination.exists():
        raise FileExistsError(f"sealed directory already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("sealed directory parent does not exist")
    evidence = validate_local_evidence(
        root,
        registration_path,
        launch_path,
        prefetch_path,
        blob_reader,
        state_reader,
    )
    registration = evidence["registration"]
    launch = evidence["launch"]
    request = evidence["request"]
    prefetch = evidence["prefetch"]
    region = registration["region"]
    description = aws_call(
        profile,
        region,
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        registration["job_name"],
    )
    output_uri, creation, job_start, job_end = validate_job(
        description, request, registration, launch
    )
    output_bucket, output_key = parse_s3(output_uri)
    output_expected = prefetch["output_artifact"]
    if (output_bucket, output_key) != (
        output_expected["bucket"],
        output_expected["key"],
    ):
        raise ValueError("prefetch output artifact URI mismatch")
    source_expected = prefetch["source_archive"]
    source_bucket, source_key = source_expected["bucket"], source_expected["key"]

    source_listing_before = list_versions(
        aws_call, profile, region, source_bucket, source_key
    )
    _, source_fingerprint = validate_listing(
        source_listing_before, source_key, source_expected, "source artifact"
    )
    output_listing_before = list_versions(
        aws_call, profile, region, output_bucket, output_key
    )
    _, output_fingerprint = validate_listing(
        output_listing_before, output_key, output_expected, "output artifact"
    )
    source_head = head_version(
        aws_call,
        profile,
        region,
        source_bucket,
        source_key,
        source_expected["version_id"],
    )
    source_modified = validate_head(
        source_head, source_expected, "source artifact", None, creation
    )
    output_head = head_version(
        aws_call,
        profile,
        region,
        output_bucket,
        output_key,
        output_expected["version_id"],
    )
    output_modified = validate_head(
        output_head, output_expected, "output artifact", job_start, job_end
    )

    with tempfile.TemporaryDirectory(prefix="px062-fetch-") as temporary:
        temp = Path(temporary)
        source_archive = temp / "source.tar.gz"
        source_get = download_call(
            profile,
            region,
            source_bucket,
            source_key,
            source_expected["version_id"],
            source_archive,
        )
        source_archive_evidence = validate_download(
            source_archive,
            source_get,
            source_expected,
            "source artifact",
            source_compressed_ceiling,
        )
        source_inputs = validate_source_archive(
            source_archive,
            source_contract,
            registration,
            request,
            root,
            blob_reader,
            source_uncompressed_ceiling,
        )

        output_archive = temp / "model.tar.gz"
        output_get = download_call(
            profile,
            region,
            output_bucket,
            output_key,
            output_expected["version_id"],
            output_archive,
        )
        output_archive_evidence = validate_download(
            output_archive,
            output_get,
            output_expected,
            "output artifact",
            output_compressed_ceiling,
        )

        _, source_after = validate_listing(
            list_versions(aws_call, profile, region, source_bucket, source_key),
            source_key,
            source_expected,
            "source artifact after download",
        )
        _, output_after = validate_listing(
            list_versions(aws_call, profile, region, output_bucket, output_key),
            output_key,
            output_expected,
            "output artifact after download",
        )
        if source_after != source_fingerprint or output_after != output_fingerprint:
            raise ValueError("S3 version evidence changed during fetch")

        stage = Path(tempfile.mkdtemp(prefix=".px062-seal-", dir=destination.parent))
        try:
            with tarfile.open(output_archive, "r:gz") as handle:
                members = validate_tar(
                    handle,
                    output_contract,
                    output_uncompressed_ceiling,
                    "output archive",
                )
                config_raw = read_member(
                    handle, members["px062_gate2/frozen_config.json"]
                )
                summary_raw = read_member(
                    handle, members["px062_gate2/collection_summary.json"]
                )
                bundle_raw = read_member(
                    handle, members["px062_gate2/source_bundle_manifest.json"]
                )
                validate_output_metadata(
                    config_raw, summary_raw, bundle_raw, source_inputs, registration
                )
                sealed = {
                    "frozen_config.json": write_bytes(
                        stage / "frozen_config.json", source_inputs["config"]
                    ),
                    "tasks.jsonl": write_bytes(
                        stage / "tasks.jsonl", source_inputs["tasks"]
                    ),
                    "registry_names.json": write_bytes(
                        stage / "registry_names.json", source_inputs["registry"]
                    ),
                    "collection_summary.json": write_bytes(
                        stage / "collection_summary.json", summary_raw
                    ),
                }
                model_member = members["px062_gate2/model_outputs.jsonl"]
                model_source = handle.extractfile(model_member)
                if model_source is None:
                    raise ValueError("unable to stream raw model outputs")
                sealed["model_outputs.jsonl"] = copy_stream(
                    model_source, stage / "model_outputs.jsonl", model_member.size
                )

            now = fetched_at or datetime.now(timezone.utc)
            if now.tzinfo is None:
                raise ValueError("fetch time must be timezone-aware")
            receipt = {
                "adjudication_run": False,
                "experiment_id": registration["experiment_id"],
                "protocol_version": registration["protocol_version"],
                "fetched_at_utc": now.astimezone(timezone.utc)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
                "scientific_outputs_inspected": False,
                "repository": evidence["git_state"],
                "prefetch_registration": {
                    "path": prefetch_path.relative_to(root).as_posix(),
                    "sha256": sha256_bytes(evidence["prefetch_raw"]),
                },
                "registration": {
                    "path": registration_path.relative_to(root).as_posix(),
                    "sha256": sha256_bytes(evidence["registration_raw"]),
                    "source_commit": registration["source_commit"],
                },
                "launch": {
                    "path": launch_path.relative_to(root).as_posix(),
                    "sha256": sha256_bytes(evidence["launch_raw"]),
                    "receipt_commit": LAUNCH_RECEIPT_COMMIT,
                },
                "request": {
                    "path": evidence["request_path"].relative_to(root).as_posix(),
                    "raw_sha256": sha256_bytes(evidence["request_raw"]),
                    "normalized_text_sha256": normalized_text_sha256(
                        evidence["request_raw"]
                    ),
                    "canonical_sha256": sha256_bytes(canonical_json_bytes(request)),
                },
                "job": {
                    "name": description["TrainingJobName"],
                    "arn": description["TrainingJobArn"],
                    "status": description["TrainingJobStatus"],
                    "secondary_status": description["SecondaryStatus"],
                    "creation_time_utc": creation.isoformat().replace("+00:00", "Z"),
                    "start_time_utc": job_start.isoformat().replace("+00:00", "Z"),
                    "end_time_utc": job_end.isoformat().replace("+00:00", "Z"),
                },
                "source_artifact": {
                    **source_archive_evidence,
                    "bucket": source_bucket,
                    "key": source_key,
                    "last_modified_utc": source_modified.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "version_listing_repeated": True,
                },
                "output_artifact": {
                    **output_archive_evidence,
                    "bucket": output_bucket,
                    "key": output_key,
                    "last_modified_utc": output_modified.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "version_listing_repeated": True,
                },
                "archive_contracts": {
                    "source_members": sorted(source_contract),
                    "output_members": sorted(output_contract),
                    "source_uncompressed_ceiling": source_uncompressed_ceiling,
                    "output_uncompressed_ceiling": output_uncompressed_ceiling,
                },
                "sealed_files": sealed,
            }
            write_bytes(
                stage / "completion_fetch_receipt.json", canonical_json_bytes(receipt)
            )
            if {item.name for item in stage.iterdir()} != SEALED_FILES:
                raise ValueError("sealed output contains unexpected files")
            stage.rename(destination)
            return receipt
        except BaseException:
            if stage.exists():
                shutil.rmtree(stage)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Outcome-blind, source-and-output-pinned PX-062 fetch/seal"
    )
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument("--launch-receipt", type=Path, default=DEFAULT_LAUNCH_RECEIPT)
    parser.add_argument(
        "--fetch-registration", type=Path, default=DEFAULT_FETCH_REGISTRATION
    )
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipt = fetch_and_seal(
        root=root,
        profile=args.profile,
        registration_path=args.registration,
        launch_path=args.launch_receipt,
        prefetch_path=args.fetch_registration,
        destination=args.destination,
    )
    print(
        json.dumps(
            {
                "adjudication_run": receipt["adjudication_run"],
                "job_name": receipt["job"]["name"],
                "output_version_id": receipt["output_artifact"]["version_id"],
                "sealed_directory": args.destination.as_posix(),
                "source_version_id": receipt["source_artifact"]["version_id"],
                "status": receipt["job"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
