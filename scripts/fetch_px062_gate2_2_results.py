#!/usr/bin/env python
"""Outcome-blind, version-pinned fetch and seal for PX-062 Gate 2.2.

This module authenticates the registered request, completed SageMaker job,
submitted source archive, and output archive.  It streams the raw trace member
to a sealed directory while parsing only enough structure to reconcile counts
and prove zero decoder escapes.  It never logs responses or adjudicates them.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import importlib.metadata
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import zlib
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import urlparse


DEFAULT_COMPLETION_REGISTRATION = Path(
    "manifests/px062_gate2_2_20260728/completion_registration.json"
)
DEFAULT_DESTINATION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/sealed_confirmation"
)
FETCHER_PATH = "scripts/fetch_px062_gate2_2_results.py"
FETCH_TEST_PATH = "tests/test_px062_gate2_2_fetch.py"
REGISTRAR_PATH = "scripts/register_px062_gate2_2_fetch.py"
CONFIG_PATH = "configs/px062_skill_selection_gate2_2_v1_0_20260728.json"
TASKS_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl"
)
CATALOG_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json"
)
BENCHMARK_MANIFEST_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/benchmark_manifest.json"
)
ANSWER_KEY_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/answer_key.jsonl"
)
COLLECTOR_PATH = "scripts/run_px062_gate2_2_models.py"
ENTRYPOINT_PATH = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/sagemaker_entry.py"
)
REQUIREMENTS_GIT_PATH = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/requirements.txt"
)
CHECKSUM_REQUIREMENTS_PATH = "requirements-px062-evidence.txt"
XXHASH_PINNED_VERSION = "3.8.1"
XXHASH_REQUIREMENT = f"xxhash=={XXHASH_PINNED_VERSION}"
OPERATOR_FETCH_POLICY_PATH = (
    "configs/aws_px062_gate2_2_operator_fetch_s3_policy_20260728.json"
)
PX062_GATE22_PREFIX = (
    "experiments/px062-skill-provenance/"
    "gate2-2-context-structured-20260728"
)

SOURCE_GIT_PATHS = {
    CONFIG_PATH: CONFIG_PATH,
    TASKS_PATH: TASKS_PATH,
    CATALOG_PATH: CATALOG_PATH,
    BENCHMARK_MANIFEST_PATH: BENCHMARK_MANIFEST_PATH,
    COLLECTOR_PATH: COLLECTOR_PATH,
    ENTRYPOINT_PATH: ENTRYPOINT_PATH,
    "requirements.txt": REQUIREMENTS_GIT_PATH,
}
SOURCE_ARCHIVE_MAX_BYTES = 32 * 1024 * 1024
SOURCE_UNCOMPRESSED_MAX_BYTES = 48 * 1024 * 1024
OUTPUT_ARCHIVE_MAX_BYTES = 600 * 1024 * 1024
OUTPUT_UNCOMPRESSED_MAX_BYTES = 540 * 1024 * 1024
TRACE_MEMBER_MAX_BYTES = 512 * 1024 * 1024
OUTPUT_FILES = {
    "px062_gate2_2/frozen_config.json": 256 * 1024,
    "px062_gate2_2/source_bundle_manifest.json": 256 * 1024,
    "px062_gate2_2/collection_summary.json": 2 * 1024 * 1024,
    "px062_gate2_2/model_traces.jsonl": TRACE_MEMBER_MAX_BYTES,
    "px062_gate2_2/tokenizer_artifacts.tar.gz": 64 * 1024 * 1024,
}
SEALED_FILES = {
    "frozen_config.json",
    "tasks.jsonl",
    "registry_catalog.json",
    "benchmark_manifest.json",
    "answer_key.jsonl",
    "source_bundle_manifest.json",
    "collection_summary.json",
    "model_traces.jsonl",
    "tokenizer_artifacts.tar.gz",
    "source_artifact.tar.gz",
    "output_artifact.tar.gz",
    "completion_fetch_receipt.json",
}
SEALED_PAYLOAD_FILES = SEALED_FILES - {"completion_fetch_receipt.json"}
FETCH_RECEIPT_KEYS = {
    "schema_version",
    "experiment_id",
    "protocol_version",
    "fetched_at_utc",
    "adjudication_run",
    "scientific_outputs_inspected",
    "model_trace_content_parsed",
    "model_trace_structure_validated",
    "trace_summary_reconciled",
    "trace_structural_validation",
    "raw_trace_console_output",
    "repository",
    "completion_registration",
    "job",
    "source_artifact",
    "output_artifact",
    "archive_contracts",
    "sealed_files",
}

REQUEST_KEYS = {
    "TrainingJobName",
    "AlgorithmSpecification",
    "RoleArn",
    "OutputDataConfig",
    "ResourceConfig",
    "StoppingCondition",
    "HyperParameters",
    "Environment",
    "EnableNetworkIsolation",
    "RetryStrategy",
    "Tags",
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
    "RetryStrategy",
}
SUMMARY_KEYS = {
    "experiment_id",
    "protocol_version",
    "models",
    "model_revisions",
    "expected_tasks",
    "expected_traces",
    "observed_traces",
    "generation_calls",
    "constrained_decoder_escapes",
    "tokenizer_artifacts",
    "source_integrity",
    "environment",
    "collector_pid",
}
SOURCE_MANIFEST_KEYS = {
    "experiment_id",
    "protocol_version",
    "source_commit",
    "answer_key_blinding",
    "files",
}

AwsCall = Callable[..., Any]
AwsDownload = Callable[..., Mapping[str, Any]]
GitBlobRead = Callable[[Path, str, str], bytes]
GitStateRead = Callable[[Path], Mapping[str, Any]]

S3_CHECKSUM_FIELDS = {
    "CRC32": "ChecksumCRC32",
    "CRC32C": "ChecksumCRC32C",
    "CRC64NVME": "ChecksumCRC64NVME",
    "SHA1": "ChecksumSHA1",
    "SHA256": "ChecksumSHA256",
    "SHA512": "ChecksumSHA512",
    "MD5": "ChecksumMD5",
    "XXHASH64": "ChecksumXXHASH64",
    "XXHASH3": "ChecksumXXHASH3",
    "XXHASH128": "ChecksumXXHASH128",
}
S3_CHECKSUM_WIDTHS = {
    "CRC32": 4,
    "CRC32C": 4,
    "CRC64NVME": 8,
    "SHA1": 20,
    "SHA256": 32,
    "SHA512": 64,
    "MD5": 16,
    "XXHASH64": 8,
    "XXHASH3": 8,
    "XXHASH128": 16,
}
S3_MULTIPART_FULL_OBJECT_ALGORITHMS = {"CRC32", "CRC32C", "CRC64NVME"}
S3_MULTIPART_COMPOSITE_ALGORITHMS = set(S3_CHECKSUM_FIELDS) - {"CRC64NVME"}
S3_SINGLE_PART_FULL_OBJECT_ALGORITHMS = set(S3_CHECKSUM_FIELDS)
S3_CHECKSUM_TYPES = {"FULL_OBJECT", "COMPOSITE"}
S3_ETAG_SINGLE = re.compile(r'"([0-9a-fA-F]{32})"')
S3_ETAG_MULTIPART = re.compile(r'"([0-9a-fA-F]{32})-([1-9][0-9]{0,4})"')
S3_LOCALLY_COMPUTABLE_CHECKSUMS = set(S3_CHECKSUM_FIELDS)
REGISTERED_ARTIFACT_BASE_KEYS = {
    "bucket",
    "key",
    "version_id",
    "etag",
    "etag_shape",
    "multipart_part_count",
    "bytes",
    "last_modified_utc",
    "checksum_algorithm",
    "checksum_type",
    "checksums",
    "server_side_encryption",
    "metadata",
    "version_fingerprint",
    "head_fingerprint",
    "object_attributes_fingerprint",
}


def _reflected_crc_table(polynomial: int, mask: int) -> tuple[int, ...]:
    values: list[int] = []
    for byte in range(256):
        value = byte
        for _ in range(8):
            value = (value >> 1) ^ (polynomial if value & 1 else 0)
        values.append(value & mask)
    return tuple(values)


CRC32C_TABLE = _reflected_crc_table(0x82F63B78, 0xFFFFFFFF)
CRC64NVME_TABLE = _reflected_crc_table(
    0x9A6C9329AC4BC9B5, 0xFFFFFFFFFFFFFFFF
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path, algorithm: str = "sha256") -> str:
    if algorithm == "sha256":
        digest = hashlib.sha256()
    elif algorithm == "md5":
        digest = hashlib.md5(usedforsecurity=False)
    else:  # pragma: no cover - internal contract
        raise ValueError(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _xxhash_module() -> Any:
    try:
        import xxhash  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError(
            "S3 XXHASH verification requires the pinned local xxhash dependency"
        ) from exc
    version = getattr(xxhash, "VERSION", getattr(xxhash, "__version__", None))
    if version != XXHASH_PINNED_VERSION:
        raise ValueError(
            "S3 XXHASH verification requires "
            f"xxhash=={XXHASH_PINNED_VERSION}; found {version!r}"
        )
    return xxhash


def checksum_runtime_record(requirements_raw: bytes) -> dict[str, Any]:
    if requirements_raw != f"{XXHASH_REQUIREMENT}\n".encode("ascii"):
        raise ValueError("PX-062 checksum requirements are not exactly pinned")
    _xxhash_module()
    distribution = importlib.metadata.distribution("xxhash")
    if distribution.version != XXHASH_PINNED_VERSION:
        raise ValueError("installed xxhash distribution version drift")
    files = []
    for item in distribution.files or ():
        file_hash = item.hash
        files.append(
            {
                "path": str(item).replace("\\", "/"),
                "hash_mode": None if file_hash is None else file_hash.mode,
                "hash_value": None if file_hash is None else file_hash.value,
                "size": item.size,
            }
        )
    if not files:
        raise ValueError("installed xxhash distribution has no file manifest")
    return {
        "requirements_path": CHECKSUM_REQUIREMENTS_PATH,
        "requirements_sha256": sha256_bytes(requirements_raw),
        "requirement": XXHASH_REQUIREMENT,
        "distribution": "xxhash",
        "version": distribution.version,
        "distribution_files_sha256": sha256_bytes(canonical_json_bytes(files)),
        "preflight_passed": True,
    }


def operator_fetch_policy_record(policy_raw: bytes, bucket: str) -> dict[str, Any]:
    prefix = PX062_GATE22_PREFIX
    expected = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListOnlyPX062Gate22ArtifactVersions",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucketVersions",
                ],
                "Resource": f"arn:aws:s3:::{bucket}",
                "Condition": {
                    "StringLike": {
                        "s3:prefix": [f"{prefix}/code/*", f"{prefix}/output/*"]
                    }
                },
            },
            {
                "Sid": "ReadOnlyVersionedPX062Gate22Artifacts",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObjectVersion",
                    "s3:GetObjectVersionAttributes",
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket}/{prefix}/code/*",
                    f"arn:aws:s3:::{bucket}/{prefix}/output/*",
                ],
            },
        ],
    }
    if strict_json_bytes(policy_raw, OPERATOR_FETCH_POLICY_PATH) != expected:
        raise ValueError("PX-062 operator fetch policy is not least-privilege exact")
    return {
        "path": OPERATOR_FETCH_POLICY_PATH,
        "sha256": sha256_bytes(policy_raw),
        "bucket": bucket,
        "prefix": prefix,
        "versioned_read_actions": [
            "s3:GetObjectVersion",
            "s3:GetObjectVersionAttributes",
        ],
        "version_listing_action": "s3:ListBucketVersions",
        "validated_least_privilege": True,
    }


def checksum_backend(algorithm: str) -> str:
    if algorithm in {"XXHASH64", "XXHASH3", "XXHASH128"}:
        module = _xxhash_module()
        version = getattr(module, "VERSION", getattr(module, "__version__", None))
        return f"python-xxhash/{version}"
    if algorithm in {"CRC32C", "CRC64NVME"}:
        return "px062-frozen-reflected-crc-v1"
    if algorithm == "CRC32":
        return f"python-zlib/{zlib.ZLIB_VERSION}"
    if algorithm in {"SHA1", "SHA256", "SHA512", "MD5"}:
        return "python-hashlib"
    raise ValueError(f"unsupported local checksum algorithm: {algorithm}")


def _checksum_stream_raw(handle: BinaryIO, size: int, algorithm: str) -> bytes:
    """Hash exactly ``size`` bytes from a stream using the S3 wire encoding."""

    if not isinstance(size, int) or size < 0:
        raise ValueError("checksum stream size is invalid")
    remaining = size
    if algorithm in {"SHA1", "SHA256", "SHA512", "MD5"}:
        name = {
            "SHA1": "sha1",
            "SHA256": "sha256",
            "SHA512": "sha512",
            "MD5": "md5",
        }[algorithm]
        digest = hashlib.new(name, usedforsecurity=False)
        while remaining:
            block = handle.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("checksum stream was truncated")
            digest.update(block)
            remaining -= len(block)
        return digest.digest()
    if algorithm in {"XXHASH64", "XXHASH3", "XXHASH128"}:
        module = _xxhash_module()
        factory = {
            "XXHASH64": module.xxh64,
            "XXHASH3": module.xxh3_64,
            "XXHASH128": module.xxh3_128,
        }[algorithm]
        digest = factory()
        while remaining:
            block = handle.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("checksum stream was truncated")
            digest.update(block)
            remaining -= len(block)
        return digest.digest()
    if algorithm == "CRC32":
        value = 0
        while remaining:
            block = handle.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("checksum stream was truncated")
            value = zlib.crc32(block, value)
            remaining -= len(block)
        return (value & 0xFFFFFFFF).to_bytes(4, "big")
    if algorithm in {"CRC32C", "CRC64NVME"}:
        table, value, mask = (
            (CRC32C_TABLE, 0xFFFFFFFF, 0xFFFFFFFF)
            if algorithm == "CRC32C"
            else (CRC64NVME_TABLE, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
        )
        while remaining:
            block = handle.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("checksum stream was truncated")
            for byte in block:
                value = table[(value ^ byte) & 0xFF] ^ (value >> 8)
            remaining -= len(block)
        width = S3_CHECKSUM_WIDTHS[algorithm]
        return (value ^ mask).to_bytes(width, "big")
    raise ValueError(f"unsupported local checksum algorithm: {algorithm}")


def checksum_bytes_base64(raw: bytes, algorithm: str) -> str:
    return base64.b64encode(
        _checksum_stream_raw(io.BytesIO(raw), len(raw), algorithm)
    ).decode("ascii")


def full_object_checksum_base64(path: Path, algorithm: str) -> str:
    """Compute a full-object checksum; composite values use a separate path."""

    with path.open("rb") as handle:
        raw = _checksum_stream_raw(handle, path.stat().st_size, algorithm)
        if handle.read(1):  # pragma: no cover - concurrent file mutation guard
            raise ValueError("checksum file grew during verification")
    return base64.b64encode(raw).decode("ascii")


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
        raise ValueError(f"{label} must contain one JSON object")
    return value


def load_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    return raw, strict_json_bytes(raw, str(path))


def repo_path(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    value = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        value.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {candidate}") from exc
    return value


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


def aws_json(profile: str, region: str, *arguments: str) -> Any:
    completed = subprocess.run(
        [
            "aws",
            *arguments,
            "--profile",
            profile,
            "--region",
            region,
            "--output",
            "json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout or "{}")


def aws_download(
    profile: str,
    region: str,
    bucket: str,
    key: str,
    version_id: str,
    destination: Path,
) -> Mapping[str, Any]:
    completed = subprocess.run(
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
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout or "{}")


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
    def output(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, encoding="utf-8"
        ).strip()

    head = output("rev-parse", "HEAD")
    branch = output("branch", "--show-current")
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
    refs = output(
        "for-each-ref",
        "--format=%(refname:short)",
        "--contains",
        head,
        "refs/remotes/",
    ).splitlines()
    return {
        "head": head,
        "branch": branch,
        "clean": status == "",
        "remote_refs": sorted(ref for ref in refs if ref and not ref.endswith("/HEAD")),
    }


def validate_git_evidence(
    root: Path,
    paths: list[Path],
    *,
    blob_reader: GitBlobRead,
    state_reader: GitStateRead,
) -> Mapping[str, Any]:
    state = dict(state_reader(root))
    head = state.get("head", "")
    if not state.get("clean"):
        raise ValueError("repository must be clean")
    if not re.fullmatch(r"[0-9a-f]{40}", str(head)):
        raise ValueError("repository HEAD is not a full commit SHA")
    if not state.get("remote_refs"):
        raise ValueError("current evidence commit is not present on a remote ref")
    for path in paths:
        local = repo_path(root, path)
        relative = local.relative_to(root).as_posix()
        if blob_reader(root, str(head), relative) != local.read_bytes():
            raise ValueError(f"local evidence differs from pushed HEAD: {relative}")
    return state


def canonical_tags(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("SageMaker tags must be a list")
    rows = []
    for row in value:
        if not isinstance(row, dict) or set(row) != {"Key", "Value"}:
            raise ValueError("SageMaker tag schema drift")
        if not isinstance(row["Key"], str) or not isinstance(row["Value"], str):
            raise ValueError("SageMaker tag values must be strings")
        rows.append({"Key": row["Key"], "Value": row["Value"]})
    if len({row["Key"] for row in rows}) != len(rows):
        raise ValueError("duplicate SageMaker tag key")
    return sorted(rows, key=lambda row: (row["Key"], row["Value"]))


def validate_job(
    description: Mapping[str, Any],
    tags_payload: Mapping[str, Any],
    request: Mapping[str, Any],
    launch_registration: Mapping[str, Any],
    launch_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if set(request) != REQUEST_KEYS:
        raise ValueError("registered SageMaker request schema drift")
    if set(description) != DESCRIPTION_KEYS:
        raise ValueError("closed-world SageMaker description schema drift")
    if set(tags_payload) != {"Tags"}:
        raise ValueError("closed-world SageMaker tag response drift")
    if canonical_tags(tags_payload["Tags"]) != canonical_tags(request["Tags"]):
        raise ValueError("live SageMaker tags differ from registered request")
    if description["TrainingJobStatus"] != "Completed" or description[
        "SecondaryStatus"
    ] != "Completed":
        raise ValueError("registered SageMaker job is not Completed")
    if description["TrainingJobName"] != launch_registration["job_name"]:
        raise ValueError("SageMaker job name mismatch")
    if description["TrainingJobArn"] != launch_receipt["training_job_arn"]:
        raise ValueError("SageMaker job ARN mismatch")
    if set(description["ModelArtifacts"]) != {"S3ModelArtifacts"}:
        raise ValueError("SageMaker ModelArtifacts schema drift")

    exact_top = {
        "TrainingJobName",
        "RoleArn",
        "HyperParameters",
        "Environment",
        "EnableNetworkIsolation",
        "RetryStrategy",
    }
    for key in exact_top:
        if description[key] != request[key]:
            raise ValueError(f"live SageMaker {key} differs from registered request")
    nested = {
        "AlgorithmSpecification",
        "OutputDataConfig",
        "ResourceConfig",
        "StoppingCondition",
    }
    for key in nested:
        if not isinstance(description[key], dict):
            raise ValueError(f"SageMaker {key} is not an object")
        projection = {name: description[key].get(name) for name in request[key]}
        if projection != request[key]:
            raise ValueError(f"live SageMaker {key} differs from registered request")
    if set(description["AlgorithmSpecification"]) != {
        *request["AlgorithmSpecification"],
        "EnableSageMakerMetricsTimeSeries",
    } or description["AlgorithmSpecification"]["EnableSageMakerMetricsTimeSeries"] is not False:
        raise ValueError("unexpected SageMaker AlgorithmSpecification defaults")
    if set(description["OutputDataConfig"]) != {
        *request["OutputDataConfig"],
        "KmsKeyId",
        "CompressionType",
    }:
        raise ValueError("unexpected SageMaker OutputDataConfig defaults")
    if description["OutputDataConfig"]["KmsKeyId"] != "" or description[
        "OutputDataConfig"
    ]["CompressionType"] != "GZIP":
        raise ValueError("unexpected SageMaker output configuration")
    if set(description["ResourceConfig"]) != set(request["ResourceConfig"]):
        raise ValueError("unexpected SageMaker ResourceConfig defaults")
    if set(description["StoppingCondition"]) != set(request["StoppingCondition"]):
        raise ValueError("unexpected SageMaker StoppingCondition defaults")
    defaults = {
        "InputDataConfig": [],
        "EnableInterContainerTrafficEncryption": False,
        "EnableManagedSpotTraining": False,
        "ProfilingStatus": "Disabled",
    }
    for key, expected in defaults.items():
        if description[key] != expected:
            raise ValueError(f"unexpected SageMaker default: {key}")
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
    launch_started = parse_time(launch_receipt["launched_at_utc"], "launch receipt")
    if not launch_started <= creation <= start <= end <= modified:
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
    expected_artifact = (
        request["OutputDataConfig"]["S3OutputPath"].rstrip("/")
        + f"/{launch_registration['job_name']}/output/model.tar.gz"
    )
    if description["ModelArtifacts"]["S3ModelArtifacts"] != expected_artifact:
        raise ValueError("SageMaker output artifact URI mismatch")
    return {
        "artifact_uri": expected_artifact,
        "creation": creation,
        "start": start,
        "end": end,
        "modified": modified,
        "training_seconds": elapsed,
    }


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


def parse_s3_etag(value: Any, label: str) -> dict[str, Any]:
    """Classify an exact quoted S3 ETag without treating it as a digest."""

    text = str(value)
    single = S3_ETAG_SINGLE.fullmatch(text)
    if single:
        return {
            "value": single.group(1),
            "shape": "SINGLE_PART",
            "multipart_part_count": None,
        }
    multipart = S3_ETAG_MULTIPART.fullmatch(text)
    if multipart:
        part_count = int(multipart.group(2))
        if part_count > 10000:
            raise ValueError(f"{label} multipart ETag part count is invalid")
        return {
            "value": f"{multipart.group(1)}-{multipart.group(2)}",
            "shape": "MULTIPART",
            "multipart_part_count": part_count,
        }
    raise ValueError(f"{label} has malformed ETag")


def listed_checksum_algorithms(row: Mapping[str, Any], label: str) -> list[str]:
    value = row.get("ChecksumAlgorithm")
    if value is None:
        return []
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) for item in value)
        or len(value) != len(set(value))
        or any(item not in S3_CHECKSUM_FIELDS for item in value)
    ):
        raise ValueError(f"{label} checksum algorithm listing is invalid")
    return [name for name in S3_CHECKSUM_FIELDS if name in value]


def _checksum_payload(
    value: Any,
    algorithm: str,
    checksum_type: str,
    multipart_part_count: int | None,
    label: str,
) -> str:
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise ValueError(f"{label} {algorithm} checksum value is invalid")
    encoded = value
    if checksum_type == "COMPOSITE":
        match = re.fullmatch(r"(.+)-([1-9][0-9]{0,4})", value)
        if match is None:
            raise ValueError(f"{label} {algorithm} composite checksum suffix is invalid")
        encoded = match.group(1)
        count = int(match.group(2))
        if count > 10000 or count != multipart_part_count:
            raise ValueError(f"{label} {algorithm} composite part count drift")
    elif re.search(r"-[1-9][0-9]{0,4}$", value):
        raise ValueError(f"{label} {algorithm} full-object checksum has a part suffix")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} {algorithm} checksum is not valid Base64") from exc
    if len(decoded) != S3_CHECKSUM_WIDTHS[algorithm]:
        raise ValueError(f"{label} {algorithm} checksum width is invalid")
    return value


def validate_checksum_compatibility(
    algorithms: list[str],
    checksum_type: str | None,
    etag: Mapping[str, Any],
    label: str,
) -> None:
    if not algorithms:
        if checksum_type is not None:
            raise ValueError(f"{label} checksum type exists without a checksum")
        return
    if checksum_type not in S3_CHECKSUM_TYPES:
        raise ValueError(f"{label} checksum type is invalid")
    if etag["shape"] == "SINGLE_PART":
        if checksum_type != "FULL_OBJECT" or any(
            algorithm not in S3_SINGLE_PART_FULL_OBJECT_ALGORITHMS
            for algorithm in algorithms
        ):
            raise ValueError(
                f"{label} single-part checksum algorithm/type is inconsistent"
            )
        return
    allowed = (
        S3_MULTIPART_FULL_OBJECT_ALGORITHMS
        if checksum_type == "FULL_OBJECT"
        else S3_MULTIPART_COMPOSITE_ALGORITHMS
    )
    if any(algorithm not in allowed for algorithm in algorithms):
        raise ValueError(
            f"{label} checksum algorithm/type is inconsistent with multipart upload"
        )


def negotiate_head_checksums(
    row: Mapping[str, Any], head: Mapping[str, Any], label: str
) -> dict[str, Any]:
    """Bind every supported checksum returned by HeadObject without substitution."""

    unknown = {
        key
        for key in head
        if key.startswith("Checksum")
        and key != "ChecksumType"
        and key not in S3_CHECKSUM_FIELDS.values()
    }
    if unknown:
        raise ValueError(f"{label} returned unsupported checksum fields: {sorted(unknown)}")
    checksums: dict[str, str] = {}
    algorithms: list[str] = []
    for algorithm, field in S3_CHECKSUM_FIELDS.items():
        if field in head:
            algorithms.append(algorithm)
            checksums[field] = head[field]
    if not algorithms:
        raise ValueError(f"{label} HeadObject returned no supported checksum")
    listed = listed_checksum_algorithms(row, label)
    if listed and listed != algorithms:
        raise ValueError(f"{label} listing/head checksum algorithm substitution")
    checksum_type = head.get("ChecksumType")
    listed_type = row.get("ChecksumType")
    if listed_type is not None and listed_type not in S3_CHECKSUM_TYPES:
        raise ValueError(f"{label} listed checksum type is invalid")
    if listed_type is not None and listed_type != checksum_type:
        raise ValueError(f"{label} listing/head checksum type mismatch")
    etag = parse_s3_etag(row.get("ETag"), label)
    validate_checksum_compatibility(algorithms, checksum_type, etag, label)
    for algorithm in algorithms:
        field = S3_CHECKSUM_FIELDS[algorithm]
        checksums[field] = _checksum_payload(
            checksums[field],
            algorithm,
            str(checksum_type),
            etag["multipart_part_count"],
            label,
        )
    return {
        "checksum_algorithm": algorithms,
        "checksum_type": checksum_type,
        "checksums": checksums,
        "etag": etag,
    }


def _attribute_etag(value: Any, label: str) -> str:
    text = str(value)
    parsed = parse_s3_etag(text if text.startswith('"') else f'"{text}"', label)
    return parsed["value"]


def object_attributes_fingerprint(
    pages: list[Mapping[str, Any]],
    expected: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    """Canonicalize version-pinned GetObjectAttributes part evidence."""

    if not pages or expected.get("checksum_type") != "COMPOSITE":
        raise ValueError(f"{label} composite object attributes are missing")
    algorithms = expected.get("checksum_algorithm")
    if not isinstance(algorithms, list) or not algorithms:
        raise ValueError(f"{label} composite checksum algorithms are missing")
    part_count = expected.get("multipart_part_count")
    if not isinstance(part_count, int) or part_count <= 0:
        raise ValueError(f"{label} multipart part count is invalid")
    expected_checksum = {
        **expected["checksums"],
        "ChecksumType": "COMPOSITE",
    }
    parts: list[dict[str, Any]] = []
    expected_marker = 0
    for page_index, page in enumerate(pages):
        for field, value in (
            ("VersionId", expected["version_id"]),
            ("ObjectSize", expected["bytes"]),
        ):
            if page.get(field) != value:
                raise ValueError(f"{label} object attributes {field} mismatch")
        if _attribute_etag(page.get("ETag"), label) != expected["etag"]:
            raise ValueError(f"{label} object attributes ETag mismatch")
        if parse_time(
            page.get("LastModified"), f"{label} attributes time"
        ) != parse_time(expected["last_modified_utc"], f"{label} registered time"):
            raise ValueError(f"{label} object attributes timestamp mismatch")
        if page.get("Checksum") != expected_checksum:
            raise ValueError(f"{label} object attributes checksum mismatch")
        object_parts = page.get("ObjectParts")
        if not isinstance(object_parts, dict):
            raise ValueError(f"{label} object attributes parts are missing")
        if object_parts.get("TotalPartsCount") != part_count:
            raise ValueError(f"{label} total parts count mismatch")
        marker = object_parts.get("PartNumberMarker", 0)
        if marker != expected_marker:
            raise ValueError(f"{label} object-parts marker drift")
        page_parts = object_parts.get("Parts")
        if not isinstance(page_parts, list) or not page_parts:
            raise ValueError(f"{label} object-parts page is empty")
        for item in page_parts:
            expected_keys = {
                "PartNumber",
                "Size",
                *(S3_CHECKSUM_FIELDS[name] for name in algorithms),
            }
            if not isinstance(item, dict) or set(item) != expected_keys:
                raise ValueError(f"{label} object-part checksum schema drift")
            number = item.get("PartNumber")
            size = item.get("Size")
            if number != len(parts) + 1 or not isinstance(size, int) or size <= 0:
                raise ValueError(f"{label} object-part sequence/size drift")
            record: dict[str, Any] = {"PartNumber": number, "Size": size}
            for algorithm in algorithms:
                field = S3_CHECKSUM_FIELDS[algorithm]
                record[field] = _checksum_payload(
                    item.get(field), algorithm, "FULL_OBJECT", None, label
                )
            parts.append(record)
        expected_marker = parts[-1]["PartNumber"]
        truncated = object_parts.get("IsTruncated")
        if truncated is True:
            if page_index == len(pages) - 1 or object_parts.get(
                "NextPartNumberMarker"
            ) != expected_marker:
                raise ValueError(f"{label} truncated part pagination drift")
        elif truncated not in (False, None) or page_index != len(pages) - 1:
            raise ValueError(f"{label} object-parts pagination termination drift")
    if len(parts) != part_count or sum(item["Size"] for item in parts) != expected[
        "bytes"
    ]:
        raise ValueError(f"{label} object-part inventory does not cover the object")
    for algorithm in algorithms:
        field = S3_CHECKSUM_FIELDS[algorithm]
        concatenated = b"".join(
            base64.b64decode(part[field], validate=True) for part in parts
        )
        recomputed = checksum_bytes_base64(concatenated, algorithm) + f"-{part_count}"
        if recomputed != expected["checksums"][field]:
            raise ValueError(f"{label} object-part composite checksum mismatch")
    return {
        "VersionId": expected["version_id"],
        "ETag": expected["etag"],
        "ObjectSize": expected["bytes"],
        "LastModified": parse_time(
            expected["last_modified_utc"], f"{label} registered time"
        ).isoformat().replace("+00:00", "Z"),
        "Checksum": expected_checksum,
        "TotalPartsCount": part_count,
        "Parts": parts,
    }


def get_object_attributes(
    aws_call: AwsCall,
    profile: str,
    region: str,
    expected: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    """Read every immutable multipart part record for exact composite proof."""

    pages: list[Mapping[str, Any]] = []
    marker = 0
    for _ in range(10):
        arguments = [
            "s3api",
            "get-object-attributes",
            "--bucket",
            expected["bucket"],
            "--key",
            expected["key"],
            "--version-id",
            expected["version_id"],
            "--object-attributes",
            "ETag",
            "Checksum",
            "ObjectParts",
            "ObjectSize",
            "--max-parts",
            "1000",
            "--no-paginate",
        ]
        if marker:
            arguments.extend(["--part-number-marker", str(marker)])
        page = aws_call(profile, region, *arguments)
        if not isinstance(page, dict):
            raise ValueError(f"{label} object attributes response is invalid")
        pages.append(page)
        object_parts = page.get("ObjectParts")
        if not isinstance(object_parts, dict):
            break
        if object_parts.get("IsTruncated") is not True:
            break
        next_marker = object_parts.get("NextPartNumberMarker")
        if not isinstance(next_marker, int) or next_marker <= marker:
            raise ValueError(f"{label} object-parts pagination did not advance")
        marker = next_marker
    else:
        raise ValueError(f"{label} object attributes exceeded 10,000 parts")
    return object_attributes_fingerprint(pages, expected, label)


def single_version(
    listing: Mapping[str, Any], key: str, label: str
) -> Mapping[str, Any]:
    if listing.get("IsTruncated") is True or listing.get("NextKeyMarker"):
        raise ValueError(f"{label} version listing is truncated")
    versions = [row for row in listing.get("Versions", []) if row.get("Key") == key]
    markers = [row for row in listing.get("DeleteMarkers", []) if row.get("Key") == key]
    if len(versions) != 1 or markers:
        raise ValueError(f"{label} must have one version and no delete marker")
    row = versions[0]
    if not row.get("VersionId") or row["VersionId"] == "null":
        raise ValueError(f"{label} has a null version ID")
    if row.get("IsLatest") is not True:
        raise ValueError(f"{label} version is not latest")
    if not isinstance(row.get("Size"), int) or row["Size"] <= 0:
        raise ValueError(f"{label} has invalid size")
    etag = parse_s3_etag(row.get("ETag"), label)
    algorithms = listed_checksum_algorithms(row, label)
    listed_type = row.get("ChecksumType")
    if listed_type is not None and listed_type not in S3_CHECKSUM_TYPES:
        raise ValueError(f"{label} listed checksum type is invalid")
    if algorithms and listed_type is not None:
        validate_checksum_compatibility(algorithms, listed_type, etag, label)
    elif listed_type is not None and not algorithms:
        raise ValueError(f"{label} listed checksum type exists without algorithms")
    parse_time(row.get("LastModified"), f"{label} listed time")
    return row


def version_fingerprint(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "Key": row["Key"],
        "VersionId": row["VersionId"],
        "IsLatest": row["IsLatest"],
        "ETag": row["ETag"],
        "Size": row["Size"],
        "LastModified": parse_time(
            row["LastModified"], "artifact listed time"
        ).isoformat().replace("+00:00", "Z"),
        "ChecksumAlgorithm": listed_checksum_algorithms(row, "artifact"),
        "ChecksumType": row.get("ChecksumType"),
    }


def compare_version(
    listing: Mapping[str, Any], key: str, expected: Mapping[str, Any], label: str
) -> dict[str, Any]:
    row = single_version(listing, key, label)
    checks = {
        "VersionId": expected["version_id"],
        "ETag": f'"{expected["etag"]}"',
        "Size": expected["bytes"],
        "ChecksumAlgorithm": expected["version_fingerprint"][
            "ChecksumAlgorithm"
        ],
        "ChecksumType": expected["version_fingerprint"]["ChecksumType"],
    }
    observed_algorithms = listed_checksum_algorithms(row, label)
    for field, value in checks.items():
        observed = observed_algorithms if field == "ChecksumAlgorithm" else row.get(field)
        if observed != value:
            raise ValueError(f"{label} version {field} mismatch")
    if parse_time(row["LastModified"], f"{label} listed time") != parse_time(
        expected["last_modified_utc"], f"{label} registered time"
    ):
        raise ValueError(f"{label} version timestamp mismatch")
    return version_fingerprint(row)


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


def s3_head_fingerprint(head: Mapping[str, Any], label: str) -> dict[str, Any]:
    unknown = {
        key
        for key in head
        if key.startswith("Checksum")
        and key != "ChecksumType"
        and key not in S3_CHECKSUM_FIELDS.values()
    }
    if unknown:
        raise ValueError(f"{label} returned unsupported checksum fields: {sorted(unknown)}")
    metadata = head.get("Metadata", {})
    if not isinstance(metadata, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in metadata.items()
    ):
        raise ValueError(f"{label} metadata is invalid")
    return {
        "VersionId": head.get("VersionId"),
        "ETag": head.get("ETag"),
        "ContentLength": head.get("ContentLength"),
        "LastModified": parse_time(
            head.get("LastModified"), f"{label} head time"
        ).isoformat().replace("+00:00", "Z"),
        "ChecksumType": head.get("ChecksumType"),
        "Checksums": {
            field: head[field]
            for field in S3_CHECKSUM_FIELDS.values()
            if field in head
        },
        "ServerSideEncryption": head.get("ServerSideEncryption"),
        "Metadata": dict(sorted(metadata.items())),
    }


def validate_registered_artifact_contract(
    artifact: Mapping[str, Any], label: str, *, controlled_source: bool
) -> None:
    """Validate the exact provenance schema shared by register/fetch/adjudicate."""

    expected_keys = set(REGISTERED_ARTIFACT_BASE_KEYS)
    if controlled_source:
        expected_keys.update({"sha256", "metadata_sha256"})
    if not isinstance(artifact, dict) or set(artifact) != expected_keys:
        raise ValueError(f"{label} registered artifact schema drift")
    if any(
        not isinstance(artifact.get(field), str) or not artifact[field]
        for field in ("bucket", "key", "version_id", "etag")
    ):
        raise ValueError(f"{label} registered artifact identity is invalid")
    if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
        raise ValueError(f"{label} registered artifact size is invalid")
    modified = parse_time(artifact.get("last_modified_utc"), f"{label} time")
    etag = parse_s3_etag(f'"{artifact["etag"]}"', label)
    if (
        artifact.get("etag_shape") != etag["shape"]
        or artifact.get("multipart_part_count") != etag["multipart_part_count"]
    ):
        raise ValueError(f"{label} registered ETag shape drift")
    algorithms = artifact.get("checksum_algorithm")
    if (
        not isinstance(algorithms, list)
        or not algorithms
        or algorithms != [name for name in S3_CHECKSUM_FIELDS if name in algorithms]
        or len(algorithms) != len(set(algorithms))
    ):
        raise ValueError(f"{label} registered checksum algorithms are invalid")
    checksum_type = artifact.get("checksum_type")
    validate_checksum_compatibility(algorithms, checksum_type, etag, label)
    expected_checksum_keys = {S3_CHECKSUM_FIELDS[name] for name in algorithms}
    checksums = artifact.get("checksums")
    if not isinstance(checksums, dict) or set(checksums) != expected_checksum_keys:
        raise ValueError(f"{label} registered checksum fields drift")
    for algorithm in algorithms:
        _checksum_payload(
            checksums[S3_CHECKSUM_FIELDS[algorithm]],
            algorithm,
            str(checksum_type),
            etag["multipart_part_count"],
            label,
        )
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in metadata.items()
    ):
        raise ValueError(f"{label} registered metadata is invalid")
    encryption = artifact.get("server_side_encryption")
    if encryption is not None and (not isinstance(encryption, str) or not encryption):
        raise ValueError(f"{label} registered encryption is invalid")

    version = artifact.get("version_fingerprint")
    if not isinstance(version, dict) or set(version) != {
        "Key",
        "VersionId",
        "IsLatest",
        "ETag",
        "Size",
        "LastModified",
        "ChecksumAlgorithm",
        "ChecksumType",
    }:
        raise ValueError(f"{label} version fingerprint schema drift")
    listed_algorithms = version.get("ChecksumAlgorithm")
    if (
        not isinstance(listed_algorithms, list)
        or listed_algorithms
        not in ([], algorithms)
        or version.get("ChecksumType")
        not in (None, checksum_type)
        or (bool(listed_algorithms) != (version.get("ChecksumType") is not None))
    ):
        raise ValueError(f"{label} version checksum fingerprint drift")
    expected_version = {
        "Key": artifact["key"],
        "VersionId": artifact["version_id"],
        "IsLatest": True,
        "ETag": f'"{artifact["etag"]}"',
        "Size": artifact["bytes"],
        "LastModified": modified.isoformat().replace("+00:00", "Z"),
        "ChecksumAlgorithm": listed_algorithms,
        "ChecksumType": version["ChecksumType"],
    }
    if version != expected_version:
        raise ValueError(f"{label} version fingerprint drift")
    expected_head = {
        "VersionId": artifact["version_id"],
        "ETag": f'"{artifact["etag"]}"',
        "ContentLength": artifact["bytes"],
        "LastModified": modified.isoformat().replace("+00:00", "Z"),
        "ChecksumType": checksum_type,
        "Checksums": checksums,
        "ServerSideEncryption": encryption,
        "Metadata": dict(sorted(metadata.items())),
    }
    if artifact.get("head_fingerprint") != expected_head:
        raise ValueError(f"{label} HeadObject fingerprint drift")

    attributes = artifact.get("object_attributes_fingerprint")
    if checksum_type == "COMPOSITE":
        if not isinstance(attributes, dict):
            raise ValueError(f"{label} composite attributes fingerprint is missing")
        synthetic_page = {
            "VersionId": attributes.get("VersionId"),
            "ETag": attributes.get("ETag"),
            "ObjectSize": attributes.get("ObjectSize"),
            "LastModified": attributes.get("LastModified"),
            "Checksum": attributes.get("Checksum"),
            "ObjectParts": {
                "TotalPartsCount": attributes.get("TotalPartsCount"),
                "PartNumberMarker": 0,
                "IsTruncated": False,
                "Parts": attributes.get("Parts"),
            },
        }
        if object_attributes_fingerprint([synthetic_page], artifact, label) != attributes:
            raise ValueError(f"{label} composite attributes fingerprint drift")
    elif attributes is not None:
        raise ValueError(f"{label} non-composite object has part attributes")

    if controlled_source:
        sha256 = artifact.get("sha256")
        metadata_sha256 = artifact.get("metadata_sha256")
        if (
            not re.fullmatch(r"[0-9a-f]{64}", str(sha256))
            or metadata_sha256 != sha256
            or metadata.get("sha256") != sha256
            or algorithms != ["SHA256"]
            or checksum_type != "FULL_OBJECT"
            or etag["shape"] != "SINGLE_PART"
        ):
            raise ValueError(f"{label} controlled source integrity contract drift")


def compare_head(
    head: Mapping[str, Any],
    expected: Mapping[str, Any],
    label: str,
    *,
    earliest: datetime | None,
    latest: datetime,
) -> datetime:
    if s3_head_fingerprint(head, label) != expected.get("head_fingerprint"):
        raise ValueError(f"{label} registered HeadObject fingerprint mismatch")
    if expected.get("metadata_sha256") is not None and head.get("Metadata", {}).get(
        "sha256"
    ) != expected["metadata_sha256"]:
        raise ValueError(f"{label} SHA-256 metadata mismatch")
    modified = parse_time(head.get("LastModified"), f"{label} head time")
    if modified != parse_time(
        expected["last_modified_utc"], f"{label} registered time"
    ):
        raise ValueError(f"{label} head timestamp mismatch")
    if earliest is not None and modified < earliest:
        raise ValueError(f"{label} predates its permitted window")
    if modified > latest:
        raise ValueError(f"{label} postdates its permitted window")
    return modified


def verify_archive_checksum_contract(
    archive: Path, expected: Mapping[str, Any], label: str
) -> dict[str, Any]:
    """Independently bind local bytes to full-object or multipart checksums."""

    algorithms = expected["checksum_algorithm"]
    checksum_type = expected["checksum_type"]
    records: dict[str, dict[str, Any]] = {}
    if checksum_type == "FULL_OBJECT":
        for algorithm in algorithms:
            field = S3_CHECKSUM_FIELDS[algorithm]
            local_value = full_object_checksum_base64(archive, algorithm)
            if local_value != expected["checksums"][field]:
                raise ValueError(f"{label} downloaded {algorithm} checksum mismatch")
            records[algorithm] = {
                "field": field,
                "registered_value": expected["checksums"][field],
                "local_value": local_value,
                "parts_recomputed": 0,
                "backend": checksum_backend(algorithm),
            }
        return {
            "method": "LOCAL_FULL_OBJECT_RECOMPUTATION",
            "checksum_type": checksum_type,
            "object_attributes_sha256": None,
            "algorithms": records,
        }

    if checksum_type != "COMPOSITE":  # pragma: no cover - artifact contract guard
        raise ValueError(f"{label} checksum type is unsupported")
    attributes = expected.get("object_attributes_fingerprint")
    if not isinstance(attributes, dict):
        raise ValueError(f"{label} composite part attributes are missing")
    parts = attributes["Parts"]
    part_count = attributes["TotalPartsCount"]
    for algorithm in algorithms:
        field = S3_CHECKSUM_FIELDS[algorithm]
        part_digests = bytearray()
        with archive.open("rb") as handle:
            for part in parts:
                raw = _checksum_stream_raw(handle, part["Size"], algorithm)
                local_part = base64.b64encode(raw).decode("ascii")
                if local_part != part[field]:
                    raise ValueError(
                        f"{label} downloaded {algorithm} part "
                        f"{part['PartNumber']} checksum mismatch"
                    )
                part_digests.extend(raw)
            if handle.read(1):
                raise ValueError(f"{label} object-part inventory left trailing bytes")
        composite_raw = _checksum_stream_raw(
            io.BytesIO(part_digests), len(part_digests), algorithm
        )
        local_value = (
            base64.b64encode(composite_raw).decode("ascii") + f"-{part_count}"
        )
        if local_value != expected["checksums"][field]:
            raise ValueError(f"{label} {algorithm} composite checksum mismatch")
        records[algorithm] = {
            "field": field,
            "registered_value": expected["checksums"][field],
            "local_value": local_value,
            "parts_recomputed": part_count,
            "backend": checksum_backend(algorithm),
        }
    return {
        "method": "LOCAL_PART_AWARE_COMPOSITE_RECOMPUTATION",
        "checksum_type": checksum_type,
        "object_attributes_sha256": sha256_bytes(
            canonical_json_bytes(attributes)
        ),
        "algorithms": records,
    }


def validate_checksum_verification_record(
    record: Mapping[str, Any], expected: Mapping[str, Any], label: str
) -> None:
    if not isinstance(record, dict) or set(record) != {
        "method",
        "checksum_type",
        "object_attributes_sha256",
        "algorithms",
    }:
        raise ValueError(f"{label} checksum-verification schema drift")
    checksum_type = expected["checksum_type"]
    expected_method = (
        "LOCAL_FULL_OBJECT_RECOMPUTATION"
        if checksum_type == "FULL_OBJECT"
        else "LOCAL_PART_AWARE_COMPOSITE_RECOMPUTATION"
    )
    expected_attributes_sha256 = (
        None
        if checksum_type == "FULL_OBJECT"
        else sha256_bytes(
            canonical_json_bytes(expected["object_attributes_fingerprint"])
        )
    )
    if (
        record.get("method") != expected_method
        or record.get("checksum_type") != checksum_type
        or record.get("object_attributes_sha256") != expected_attributes_sha256
    ):
        raise ValueError(f"{label} checksum-verification method drift")
    algorithms = record.get("algorithms")
    if not isinstance(algorithms, dict) or list(algorithms) != expected[
        "checksum_algorithm"
    ]:
        raise ValueError(f"{label} checksum-verification algorithms drift")
    part_count = (
        expected["multipart_part_count"] if checksum_type == "COMPOSITE" else 0
    )
    for algorithm, item in algorithms.items():
        field = S3_CHECKSUM_FIELDS[algorithm]
        if not isinstance(item, dict) or set(item) != {
            "field",
            "registered_value",
            "local_value",
            "parts_recomputed",
            "backend",
        }:
            raise ValueError(f"{label} {algorithm} verification schema drift")
        if (
            item["field"] != field
            or item["registered_value"] != expected["checksums"][field]
            or item["local_value"] != expected["checksums"][field]
            or item["parts_recomputed"] != part_count
            or not isinstance(item["backend"], str)
            or not item["backend"]
        ):
            raise ValueError(f"{label} {algorithm} checksum proof drift")


def validate_download(
    archive: Path,
    response: Mapping[str, Any],
    expected: Mapping[str, Any],
    label: str,
    ceiling: int,
    *,
    require_registered_sha256: bool,
    require_etag_md5: bool,
) -> dict[str, Any]:
    if s3_head_fingerprint(response, label) != expected.get("head_fingerprint"):
        raise ValueError(f"{label} get-object registered fingerprint mismatch")
    size = archive.stat().st_size
    if size != expected["bytes"] or size > ceiling:
        raise ValueError(f"{label} downloaded size mismatch or ceiling exceeded")
    sha256 = digest_file(archive)
    md5 = digest_file(archive, "md5")
    if require_registered_sha256 and sha256 != expected.get("sha256"):
        raise ValueError(f"{label} downloaded SHA-256 mismatch")
    if require_etag_md5:
        if expected.get("etag_shape") != "SINGLE_PART":
            raise ValueError(f"{label} controlled source ETag is multipart")
        if md5.casefold() != str(expected["etag"]).casefold():
            raise ValueError(f"{label} downloaded MD5/ETag mismatch")
    checksum_verification = verify_archive_checksum_contract(archive, expected, label)
    return {
        "bytes": size,
        "md5": md5,
        "sha256": sha256,
        "checksum_verification": checksum_verification,
    }


def validate_tar(
    handle: tarfile.TarFile,
    expected: Mapping[str, Mapping[str, Any]],
    total_ceiling: int,
    label: str,
) -> dict[str, tarfile.TarInfo]:
    members = handle.getmembers()
    names = [member.name for member in members]
    if len(names) != len(set(names)):
        raise ValueError(f"{label} contains duplicate members")
    if set(names) != set(expected):
        raise ValueError(f"{label} member set mismatch")
    indexed: dict[str, tarfile.TarInfo] = {}
    total = 0
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\\" in member.name:
            raise ValueError(f"unsafe {label} member path")
        contract = expected[member.name]
        if contract.get("kind", "file") == "directory":
            if not member.isdir() or member.linkname or member.size != 0:
                raise ValueError(f"invalid {label} directory member")
        elif not member.isfile() or member.issym() or member.islnk() or member.linkname:
            raise ValueError(f"nonregular {label} member")
        if "bytes" in contract and member.size != contract["bytes"]:
            raise ValueError(f"{label} member size mismatch: {member.name}")
        if member.size > contract.get("max_bytes", contract.get("bytes", 0)):
            raise ValueError(f"{label} member ceiling exceeded: {member.name}")
        total += member.size
        if total > total_ceiling:
            raise ValueError(f"{label} total uncompressed ceiling exceeded")
        indexed[member.name] = member
    return indexed


def read_member(handle: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    stream = handle.extractfile(member)
    if stream is None:
        raise ValueError(f"unable to read archive member: {member.name}")
    raw = stream.read(member.size + 1)
    if len(raw) != member.size:
        raise ValueError(f"archive member length mismatch: {member.name}")
    return raw


def write_bytes(path: Path, raw: bytes) -> dict[str, Any]:
    with path.open("xb") as handle:
        handle.write(raw)
    return {"bytes": len(raw), "sha256": sha256_bytes(raw)}


def copy_stream(stream: BinaryIO, path: Path, size: int) -> dict[str, Any]:
    digest = hashlib.sha256()
    observed = 0
    with path.open("xb") as target:
        while observed < size:
            block = stream.read(min(1024 * 1024, size - observed))
            if not block:
                break
            target.write(block)
            digest.update(block)
            observed += len(block)
        if stream.read(1):
            raise ValueError("trace member exceeded registered tar size")
    if observed != size:
        raise ValueError("trace member was truncated")
    return {"bytes": observed, "sha256": digest.hexdigest()}


def copy_file(source: Path, destination: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as stream, destination.open("xb") as target:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            target.write(block)
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def validate_fetch_receipt_against_completion(
    receipt: Mapping[str, Any],
    completion: Mapping[str, Any],
    completion_raw: bytes,
) -> None:
    """Cross-check the sealed receipt against registered cloud provenance."""

    if set(receipt) != FETCH_RECEIPT_KEYS or receipt.get(
        "schema_version"
    ) != "px062-gate2.2-fetch-receipt-v1":
        raise ValueError("fetch receipt schema drift")
    if (
        receipt.get("experiment_id") != completion.get("experiment_id")
        or receipt.get("protocol_version") != completion.get("protocol_version")
        or receipt.get("adjudication_run") is not False
        or receipt.get("scientific_outputs_inspected") is not False
        or receipt.get("model_trace_structure_validated") is not True
        or receipt.get("trace_summary_reconciled") is not True
    ):
        raise ValueError("fetch receipt experiment/state drift")
    completion_record = receipt.get("completion_registration")
    if completion_record != {
        "path": DEFAULT_COMPLETION_REGISTRATION.as_posix(),
        "sha256": sha256_bytes(completion_raw),
    }:
        raise ValueError("fetch receipt completion-registration binding drift")
    job = receipt.get("job")
    registered_job = completion.get("job")
    if not isinstance(job, dict) or not isinstance(registered_job, dict):
        raise ValueError("fetch receipt job provenance is missing")
    job_fields = {
        "name": "name",
        "arn": "arn",
        "status": "status",
        "creation_time_utc": "creation_time_utc",
        "start_time_utc": "start_time_utc",
        "end_time_utc": "end_time_utc",
    }
    if set(job) != set(job_fields) or any(
        job[receipt_field] != registered_job[completion_field]
        for receipt_field, completion_field in job_fields.items()
    ):
        raise ValueError("fetch receipt AWS job binding drift")
    for label in ("source_artifact", "output_artifact"):
        fetched = receipt.get(label)
        registered = completion.get(label)
        if not isinstance(fetched, dict) or not isinstance(registered, dict):
            raise ValueError(f"fetch receipt {label} provenance is missing")
        expected_keys = set(registered) | {
            "md5",
            "sha256",
            "checksum_verification",
            "version_listing_repeated",
            "object_attributes_repeated",
        }
        if set(fetched) != expected_keys:
            raise ValueError(f"fetch receipt {label} schema drift")
        for field, value in registered.items():
            if fetched.get(field) != value:
                raise ValueError(f"fetch receipt {label} {field} drift")
        if fetched.get("version_listing_repeated") is not True:
            raise ValueError(f"fetch receipt {label} version was not rechecked")
        expected_attributes_repeat = registered.get("checksum_type") == "COMPOSITE"
        if fetched.get("object_attributes_repeated") is not expected_attributes_repeat:
            raise ValueError(f"fetch receipt {label} object-parts recheck drift")
        digest = fetched.get("sha256")
        if (
            not re.fullmatch(r"[0-9a-f]{64}", str(digest))
            or not re.fullmatch(r"[0-9a-f]{32}", str(fetched.get("md5")))
        ):
            raise ValueError(f"fetch receipt {label} local digest is invalid")
        validate_checksum_verification_record(
            fetched.get("checksum_verification"), registered, f"fetch receipt {label}"
        )
        if (
            registered.get("checksum_type") == "FULL_OBJECT"
            and "SHA256" in registered.get("checksum_algorithm", [])
            and registered["checksums"]["ChecksumSHA256"]
            != base64.b64encode(bytes.fromhex(str(digest))).decode("ascii")
        ):
            raise ValueError(f"fetch receipt {label} local SHA-256 proof drift")
    if receipt["source_artifact"].get("sha256") != completion[
        "source_artifact"
    ].get("sha256"):
        raise ValueError("fetch receipt source artifact registered SHA-256 drift")
    sealed = receipt.get("sealed_files")
    if not isinstance(sealed, dict) or set(sealed) != SEALED_PAYLOAD_FILES:
        raise ValueError("fetch receipt sealed-file inventory drift")
    archive_bindings = {
        "source_artifact.tar.gz": receipt["source_artifact"],
        "output_artifact.tar.gz": receipt["output_artifact"],
    }
    for name, artifact in archive_bindings.items():
        if sealed.get(name) != {
            "bytes": artifact["bytes"],
            "sha256": artifact["sha256"],
        }:
            raise ValueError(f"fetch receipt retained archive binding drift: {name}")


def copy_and_validate_traces(
    stream: BinaryIO,
    path: Path,
    size: int,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Stream-seal traces while validating only registered structural counts."""

    digest = hashlib.sha256()
    observed = 0
    rows = 0
    decoder_escapes = 0
    generation_calls = 0
    keys: set[tuple[str, str]] = set()
    tasks_by_model: dict[str, set[str]] = {}
    arm_names = (
        "A_open_text",
        "B_structured_names",
        "C_structured_catalog",
        "D_contextual_repair",
        "E_decontextualized_repair",
    )
    with path.open("xb") as target:
        while observed < size:
            line = stream.readline(min(2 * 1024 * 1024, size - observed) + 1)
            if not line:
                break
            if len(line) > size - observed:
                raise ValueError("trace member exceeded registered tar size")
            if not line.endswith(b"\n"):
                raise ValueError("trace JSONL row is unterminated or exceeds line limit")
            target.write(line)
            digest.update(line)
            observed += len(line)
            row = strict_json_bytes(line, f"model trace row {rows + 1}")
            if not isinstance(row, dict):
                raise ValueError("model trace row is not an object")
            model_id = row.get("model_id")
            task_id = row.get("task_id")
            if not isinstance(model_id, str) or not isinstance(task_id, str):
                raise ValueError("model trace key is invalid")
            key = (model_id, task_id)
            if key in keys:
                raise ValueError("duplicate model/task trace key")
            keys.add(key)
            tasks_by_model.setdefault(model_id, set()).add(task_id)
            arms = row.get("arms")
            if not isinstance(arms, dict) or list(arms) != list(arm_names):
                raise ValueError("model trace arm order/schema drift")
            for arm_name, arm in arms.items():
                if not isinstance(arm, dict) or not isinstance(arm.get("generated"), bool):
                    raise ValueError("model trace generation flag is invalid")
                generation_calls += int(arm["generated"])
                if arm_name != "A_open_text":
                    escape = arm.get("decoder_escape")
                    if not isinstance(escape, bool):
                        raise ValueError("model trace decoder-escape flag is invalid")
                    decoder_escapes += int(escape)
            rows += 1
        if stream.read(1):
            raise ValueError("trace member exceeded registered tar size")
    if observed != size:
        raise ValueError("trace member was truncated")
    if rows != summary["observed_traces"] or rows != summary["expected_traces"]:
        raise ValueError("trace row count differs from collection summary")
    if len(keys) != rows:
        raise ValueError("trace unique-key count differs from collection summary")
    if set(tasks_by_model) != set(summary["models"]):
        raise ValueError("trace models differ from collection summary")
    if any(len(task_ids) != summary["expected_tasks"] for task_ids in tasks_by_model.values()):
        raise ValueError("per-model task counts differ from collection summary")
    if decoder_escapes != summary["constrained_decoder_escapes"] or decoder_escapes != 0:
        raise ValueError("trace decoder escapes differ from zero/summary")
    if generation_calls != summary["generation_calls"]:
        raise ValueError("trace generation-call count differs from collection summary")
    return {
        "bytes": observed,
        "sha256": digest.hexdigest(),
        "structural_rows_validated": rows,
        "unique_model_task_keys": len(keys),
        "generation_calls_reconciled": generation_calls,
        "decoder_escapes_reconciled": decoder_escapes,
    }


def validate_source_archive(
    archive: Path,
    launch_registration: Mapping[str, Any],
    root: Path,
    blob_reader: GitBlobRead,
) -> dict[str, bytes]:
    source_manifest = launch_registration["source_bundle"]["manifest"]
    if set(source_manifest) != SOURCE_MANIFEST_KEYS:
        raise ValueError("registered source bundle manifest schema drift")
    if set(source_manifest.get("answer_key_blinding", {})) != {
        "included_in_archive",
        "registered_sha256",
        "registered_bytes",
    }:
        raise ValueError("registered answer-key blinding schema drift")
    expected_files = source_manifest.get("files")
    if set(expected_files or {}) != set(SOURCE_GIT_PATHS):
        raise ValueError("registered source manifest file inventory drift")
    if any(
        not isinstance(values, dict)
        or set(values) != {"sha256", "bytes"}
        or not isinstance(values["bytes"], int)
        or values["bytes"] <= 0
        or not re.fullmatch(r"[0-9a-f]{64}", str(values["sha256"]))
        for values in expected_files.values()
    ):
        raise ValueError("registered source manifest member schema drift")
    contract: dict[str, dict[str, Any]] = {
        name: {"bytes": values["bytes"], "max_bytes": values["bytes"]}
        for name, values in expected_files.items()
    }
    manifest_raw_expected = canonical_json_bytes(source_manifest)
    contract["bundle_manifest.json"] = {
        "bytes": len(manifest_raw_expected),
        "max_bytes": len(manifest_raw_expected),
    }
    with tarfile.open(archive, "r:gz") as handle:
        members = validate_tar(
            handle, contract, SOURCE_UNCOMPRESSED_MAX_BYTES, "source archive"
        )
        raw = {name: read_member(handle, members[name]) for name in members}
    if raw["bundle_manifest.json"] != manifest_raw_expected:
        raise ValueError("source bundle manifest bytes differ from registration")
    source_commit = launch_registration["source_commit"]
    for name, git_path in SOURCE_GIT_PATHS.items():
        expected = expected_files[name]
        if len(raw[name]) != expected["bytes"] or sha256_bytes(raw[name]) != expected[
            "sha256"
        ]:
            raise ValueError(f"source member hash mismatch: {name}")
        if raw[name] != blob_reader(root, source_commit, git_path):
            raise ValueError(f"source member differs from source commit: {name}")
    config = strict_json_bytes(raw[CONFIG_PATH], "authenticated Gate 2.2 config")
    if config["experiment_id"] != launch_registration["experiment_id"] or config[
        "protocol_version"
    ] != launch_registration["protocol_version"]:
        raise ValueError("authenticated config identity mismatch")
    if config["frozen_inputs"] != {
        "tasks": TASKS_PATH,
        "answer_key": ANSWER_KEY_PATH,
        "registry_catalog": CATALOG_PATH,
        "benchmark_manifest": BENCHMARK_MANIFEST_PATH,
    }:
        raise ValueError("authenticated config frozen-input paths drift")
    observed = {
        "config_sha256": sha256_bytes(raw[CONFIG_PATH]),
        "tasks_sha256": sha256_bytes(raw[TASKS_PATH]),
        "registry_catalog_sha256": sha256_bytes(raw[CATALOG_PATH]),
        "benchmark_manifest_sha256": sha256_bytes(raw[BENCHMARK_MANIFEST_PATH]),
    }
    frozen = launch_registration["frozen_sources"]
    for key, value in observed.items():
        if frozen.get(key) != value:
            raise ValueError(f"authenticated source hash mismatch: {key}")
    benchmark = strict_json_bytes(
        raw[BENCHMARK_MANIFEST_PATH], "authenticated benchmark manifest"
    )
    artifact_hashes = benchmark.get("artifacts", {})
    for name, source_name in (
        ("tasks.jsonl", TASKS_PATH),
        ("registry_catalog.json", CATALOG_PATH),
    ):
        if artifact_hashes.get(name, {}).get("sha256") != sha256_bytes(raw[source_name]):
            raise ValueError(f"benchmark manifest hash mismatch: {name}")
    return {
        "config": raw[CONFIG_PATH],
        "tasks": raw[TASKS_PATH],
        "catalog": raw[CATALOG_PATH],
        "benchmark_manifest": raw[BENCHMARK_MANIFEST_PATH],
        "bundle_manifest": raw["bundle_manifest.json"],
    }


def validate_summary(
    summary_raw: bytes,
    config_raw: bytes,
    tasks_raw: bytes,
    catalog_raw: bytes,
    benchmark_manifest_raw: bytes,
) -> dict[str, Any]:
    summary = strict_json_bytes(summary_raw, "collection summary")
    config = strict_json_bytes(config_raw, "frozen config")
    if set(summary) != SUMMARY_KEYS:
        raise ValueError("collection summary schema drift")
    exact = {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "models": config["models"],
        "model_revisions": config["model_revisions"],
        "expected_tasks": config["expected_tasks"],
        "expected_traces": config["expected_traces"],
        "observed_traces": config["expected_traces"],
    }
    for key, value in exact.items():
        if summary.get(key) != value:
            raise ValueError(f"collection summary {key} mismatch")
    if not isinstance(summary["generation_calls"], int) or summary[
        "generation_calls"
    ] < config["expected_traces"]:
        raise ValueError("collection summary generation-call count is invalid")
    if summary["constrained_decoder_escapes"] != 0:
        raise ValueError("collection summary requires exactly zero decoder escapes")
    if not isinstance(summary["collector_pid"], int) or summary["collector_pid"] <= 0:
        raise ValueError("collection summary PID is invalid")
    expected_integrity = {
        "config_sha256": sha256_bytes(config_raw),
        "tasks_sha256": sha256_bytes(tasks_raw),
        "registry_catalog_sha256": sha256_bytes(catalog_raw),
        "benchmark_manifest_sha256": sha256_bytes(benchmark_manifest_raw),
    }
    if summary["source_integrity"] != expected_integrity:
        raise ValueError("collection summary source-integrity mismatch")
    environment = summary["environment"]
    if not isinstance(environment, dict):
        raise ValueError("collection environment is not an object")
    for package, version in config["dependency_versions"].items():
        if environment.get(package) != version:
            raise ValueError(f"collection environment {package} mismatch")
    if config.get("require_cuda") and environment.get("cuda_available") is not True:
        raise ValueError("collection did not use required CUDA runtime")
    tokenizer = summary["tokenizer_artifacts"]
    if not isinstance(tokenizer, dict) or set(tokenizer) != {
        "path",
        "sha256",
        "bytes",
        "manifest_sha256",
        "manifest",
    }:
        raise ValueError("collection tokenizer-artifact schema drift")
    if tokenizer["path"] != "tokenizer_artifacts.tar.gz":
        raise ValueError("collection tokenizer-artifact path drift")
    if (
        not isinstance(tokenizer["bytes"], int)
        or tokenizer["bytes"] <= 0
        or not re.fullmatch(r"[0-9a-f]{64}", str(tokenizer["sha256"]))
        or not re.fullmatch(r"[0-9a-f]{64}", str(tokenizer["manifest_sha256"]))
        or not isinstance(tokenizer["manifest"], dict)
    ):
        raise ValueError("collection tokenizer-artifact record is invalid")
    manifest_raw = json.dumps(
        tokenizer["manifest"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if sha256_bytes(manifest_raw) != tokenizer["manifest_sha256"]:
        raise ValueError("collection tokenizer manifest hash mismatch")
    return summary


def validate_completion_evidence(
    root: Path,
    completion_path: Path,
    *,
    blob_reader: GitBlobRead,
    state_reader: GitStateRead,
) -> dict[str, Any]:
    completion_raw, completion = load_json(completion_path)
    required = {
        "schema_version",
        "experiment_id",
        "protocol_version",
        "registered_at_utc",
        "purpose",
        "scientific_outputs_downloaded",
        "scientific_outputs_inspected",
        "fetch_code_commit",
        "fetch_code_branch",
        "fetch_code_remote_refs",
        "launch_registration",
        "launch_receipt",
        "request",
        "job",
        "source_artifact",
        "output_artifact",
        "answer_key",
        "fetcher",
        "fetch_tests",
        "registrar",
        "sealed_destination",
    }
    if set(completion) != required or completion.get("schema_version") != (
        "px062-gate2.2-completion-registration-v1"
    ):
        raise ValueError("completion registration schema drift")
    if completion["scientific_outputs_downloaded"] is not False or completion[
        "scientific_outputs_inspected"
    ] is not False:
        raise ValueError("completion registration is not outcome-blind")
    expected_destination = DEFAULT_DESTINATION.as_posix()
    if completion["sealed_destination"] != expected_destination:
        raise ValueError("completion registration sealed destination drift")
    if not re.fullmatch(r"[0-9a-f]{40}", completion["fetch_code_commit"]):
        raise ValueError("completion fetch code commit is invalid")
    if not completion["fetch_code_remote_refs"]:
        raise ValueError("completion fetch code was not registered on a remote ref")
    launch_path = repo_path(root, Path(completion["launch_registration"]["path"]))
    receipt_path = repo_path(root, Path(completion["launch_receipt"]["path"]))
    request_path = repo_path(root, Path(completion["request"]["path"]))
    paths = [completion_path, launch_path, receipt_path, request_path]
    for key, constant in (
        ("fetcher", FETCHER_PATH),
        ("fetch_tests", FETCH_TEST_PATH),
        ("registrar", REGISTRAR_PATH),
    ):
        if completion[key]["path"] != constant:
            raise ValueError(f"completion registration {key} path drift")
        path = repo_path(root, Path(constant))
        paths.append(path)
        raw = path.read_bytes()
        if sha256_bytes(raw) != completion[key]["sha256"]:
            raise ValueError(f"completion registration {key} hash mismatch")
        if blob_reader(root, completion["fetch_code_commit"], constant) != raw:
            raise ValueError(f"{key} differs from completion code commit")
    state = validate_git_evidence(
        root, paths, blob_reader=blob_reader, state_reader=state_reader
    )
    if state.get("branch") != completion["fetch_code_branch"]:
        raise ValueError("fetch branch differs from completion registration")
    for path, key in (
        (launch_path, "launch_registration"),
        (receipt_path, "launch_receipt"),
        (request_path, "request"),
    ):
        if sha256_bytes(path.read_bytes()) != completion[key]["sha256"]:
            raise ValueError(f"completion {key} evidence hash mismatch")
    launch_raw, launch = load_json(launch_path)
    receipt_raw, receipt = load_json(receipt_path)
    request_raw, request = load_json(request_path)
    checksum_requirements_raw = blob_reader(
        root, launch["source_commit"], CHECKSUM_REQUIREMENTS_PATH
    )
    if launch.get("checksum_runtime") != checksum_runtime_record(
        checksum_requirements_raw
    ):
        raise ValueError("launch checksum-runtime preflight drift")
    operator_policy_raw = blob_reader(
        root, launch["source_commit"], OPERATOR_FETCH_POLICY_PATH
    )
    source_bundle = launch["source_bundle"]
    if launch.get("fetch_operator_policy") != operator_fetch_policy_record(
        operator_policy_raw, source_bundle["bucket"]
    ):
        raise ValueError("launch operator fetch-policy drift")
    expected_operator_preflight = {
        "source_version_attributes": {
            "method": "GetObjectAttributes",
            "version_id": source_bundle["version_id"],
            "etag": source_bundle["etag"],
            "bytes": source_bundle["bytes"],
            "checksum_sha256_base64": source_bundle["checksum_sha256_base64"],
            "checksum_type": "FULL_OBJECT",
            "authorized": True,
        },
        "output_version_listing": {
            "method": "ListObjectVersions",
            "prefix": f"{PX062_GATE22_PREFIX}/output/{launch['job_name']}/",
            "authorized": True,
            "existing_versions": 0,
            "existing_delete_markers": 0,
        },
    }
    if launch.get("operator_access_preflight") != expected_operator_preflight:
        raise ValueError("launch operator access-preflight drift")
    if sha256_bytes(launch_raw) != completion["launch_registration"]["sha256"]:
        raise ValueError("launch registration hash mismatch")
    if sha256_bytes(receipt_raw) != completion["launch_receipt"]["sha256"]:
        raise ValueError("launch receipt hash mismatch")
    if sha256_bytes(request_raw) != completion["request"]["sha256"]:
        raise ValueError("request hash mismatch")
    answer = completion["answer_key"]
    if answer.get("source_commit") != launch["source_commit"]:
        raise ValueError("answer-key source commit drift")
    if answer.get("included_in_cloud_source") is not False:
        raise ValueError("answer key was not blinded from cloud collection")
    answer_contract = launch["source_bundle"]["manifest"]["answer_key_blinding"]
    if answer_contract.get("included_in_archive") is not False:
        raise ValueError("source bundle registration included the answer key")
    answer_raw = blob_reader(root, launch["source_commit"], answer["path"])
    if len(answer_raw) != answer["bytes"] or sha256_bytes(answer_raw) != answer[
        "sha256"
    ]:
        raise ValueError("source-commit answer key differs from registration")
    if (
        answer["bytes"] != answer_contract["registered_bytes"]
        or answer["sha256"] != answer_contract["registered_sha256"]
        or answer["sha256"] != launch["frozen_sources"]["answer_key_sha256"]
    ):
        raise ValueError("answer-key registration cross-check mismatch")
    source = completion["source_artifact"]
    validate_registered_artifact_contract(
        source, "completion source artifact", controlled_source=True
    )
    validate_registered_artifact_contract(
        completion["output_artifact"],
        "completion output artifact",
        controlled_source=False,
    )
    launch_source = launch["source_bundle"]
    source_cross_checks = {
        "bucket": launch_source["bucket"],
        "key": launch_source["key"],
        "version_id": launch_source["version_id"],
        "etag": launch_source["etag"],
        "bytes": launch_source["bytes"],
        "sha256": launch_source["sha256"],
        "metadata_sha256": launch_source["sha256"],
    }
    for field, value in source_cross_checks.items():
        if source.get(field) != value:
            raise ValueError(f"completion source artifact {field} drift")
    return {
        "completion": completion,
        "completion_raw": completion_raw,
        "launch": launch,
        "launch_raw": launch_raw,
        "receipt": receipt,
        "receipt_raw": receipt_raw,
        "request": request,
        "request_raw": request_raw,
        "answer_raw": answer_raw,
        "git_state": state,
        "paths": {
            "completion": completion_path,
            "launch": launch_path,
            "receipt": receipt_path,
            "request": request_path,
        },
    }


def fetch_and_seal(
    *,
    root: Path,
    profile: str,
    completion_path: Path,
    destination: Path,
    aws_call: AwsCall = aws_json,
    download_call: AwsDownload = aws_download,
    blob_reader: GitBlobRead = git_blob,
    state_reader: GitStateRead = git_state,
    fetched_at: datetime | None = None,
    source_compressed_ceiling: int = SOURCE_ARCHIVE_MAX_BYTES,
    output_compressed_ceiling: int = OUTPUT_ARCHIVE_MAX_BYTES,
) -> dict[str, Any]:
    root = root.resolve()
    completion_path = repo_path(root, completion_path)
    destination = repo_path(root, destination)
    if destination.exists():
        raise FileExistsError(f"sealed destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("sealed destination parent does not exist")
    evidence = validate_completion_evidence(
        root,
        completion_path,
        blob_reader=blob_reader,
        state_reader=state_reader,
    )
    completion = evidence["completion"]
    launch = evidence["launch"]
    receipt = evidence["receipt"]
    request = evidence["request"]
    region = launch["region"]
    description = aws_call(
        profile,
        region,
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        launch["job_name"],
    )
    tags = aws_call(
        profile,
        region,
        "sagemaker",
        "list-tags",
        "--resource-arn",
        receipt["training_job_arn"],
    )
    lifecycle = validate_job(description, tags, request, launch, receipt)
    if description["TrainingJobArn"] != completion["job"]["arn"]:
        raise ValueError("completion job ARN drift")
    job_checks = {
        "name": description["TrainingJobName"],
        "status": description["TrainingJobStatus"],
        "secondary_status": description["SecondaryStatus"],
        "artifact_uri": lifecycle["artifact_uri"],
        "description_sha256": sha256_bytes(canonical_json_bytes(description)),
        "tags_sha256": sha256_bytes(
            canonical_json_bytes({"Tags": canonical_tags(tags["Tags"])})
        ),
    }
    for field, value in job_checks.items():
        if completion["job"].get(field) != value:
            raise ValueError(f"completion job {field} drift")
    for field, observed in (
        ("creation_time_utc", lifecycle["creation"]),
        ("start_time_utc", lifecycle["start"]),
        ("end_time_utc", lifecycle["end"]),
    ):
        if parse_time(completion["job"][field], field) != observed:
            raise ValueError(f"completion job {field} drift")

    source = completion["source_artifact"]
    output = completion["output_artifact"]
    output_bucket, output_key = parse_s3(lifecycle["artifact_uri"])
    if (output_bucket, output_key) != (output["bucket"], output["key"]):
        raise ValueError("completion output artifact URI drift")
    source_before = compare_version(
        list_versions(
            aws_call, profile, region, source["bucket"], source["key"]
        ),
        source["key"],
        source,
        "source artifact",
    )
    output_before = compare_version(
        list_versions(
            aws_call, profile, region, output["bucket"], output["key"]
        ),
        output["key"],
        output,
        "output artifact",
    )
    source_head = head_version(
        aws_call,
        profile,
        region,
        source["bucket"],
        source["key"],
        source["version_id"],
    )
    source_modified = compare_head(
        source_head,
        source,
        "source artifact",
        earliest=None,
        latest=lifecycle["creation"],
    )
    if source_modified >= lifecycle["creation"]:
        raise ValueError("source artifact was not frozen before job creation")
    output_head = head_version(
        aws_call,
        profile,
        region,
        output["bucket"],
        output["key"],
        output["version_id"],
    )
    output_modified = compare_head(
        output_head,
        output,
        "output artifact",
        earliest=lifecycle["start"],
        latest=lifecycle["end"],
    )
    output_attributes_before = None
    if output["checksum_type"] == "COMPOSITE":
        output_attributes_before = get_object_attributes(
            aws_call, profile, region, output, "output artifact"
        )
        if output_attributes_before != output["object_attributes_fingerprint"]:
            raise ValueError("output artifact registered object attributes drift")

    with tempfile.TemporaryDirectory(prefix="px062-g22-fetch-") as temporary:
        temp = Path(temporary)
        source_archive = temp / "source.tar.gz"
        source_response = download_call(
            profile,
            region,
            source["bucket"],
            source["key"],
            source["version_id"],
            source_archive,
        )
        source_download = validate_download(
            source_archive,
            source_response,
            source,
            "source artifact",
            source_compressed_ceiling,
            require_registered_sha256=True,
            require_etag_md5=True,
        )
        source_inputs = validate_source_archive(
            source_archive, launch, root, blob_reader
        )
        output_archive = temp / "model.tar.gz"
        output_response = download_call(
            profile,
            region,
            output["bucket"],
            output["key"],
            output["version_id"],
            output_archive,
        )
        output_download = validate_download(
            output_archive,
            output_response,
            output,
            "output artifact",
            output_compressed_ceiling,
            require_registered_sha256=False,
            require_etag_md5=False,
        )
        source_after = compare_version(
            list_versions(
                aws_call, profile, region, source["bucket"], source["key"]
            ),
            source["key"],
            source,
            "source artifact after download",
        )
        output_after = compare_version(
            list_versions(
                aws_call, profile, region, output["bucket"], output["key"]
            ),
            output["key"],
            output,
            "output artifact after download",
        )
        if source_after != source_before or output_after != output_before:
            raise ValueError("S3 version evidence changed during outcome-blind fetch")
        if output_attributes_before is not None:
            output_attributes_after = get_object_attributes(
                aws_call, profile, region, output, "output artifact after download"
            )
            if (
                output_attributes_after != output_attributes_before
                or output_attributes_after
                != output["object_attributes_fingerprint"]
            ):
                raise ValueError(
                    "S3 object-part evidence changed during outcome-blind fetch"
                )

        output_contract = {
            "px062_gate2_2": {"kind": "directory", "bytes": 0},
            **{
                name: {"max_bytes": ceiling}
                for name, ceiling in OUTPUT_FILES.items()
            },
        }
        stage = Path(tempfile.mkdtemp(prefix=".px062-g22-seal-", dir=destination.parent))
        try:
            sealed = {
                "frozen_config.json": write_bytes(
                    stage / "frozen_config.json", source_inputs["config"]
                ),
                "tasks.jsonl": write_bytes(
                    stage / "tasks.jsonl", source_inputs["tasks"]
                ),
                "registry_catalog.json": write_bytes(
                    stage / "registry_catalog.json", source_inputs["catalog"]
                ),
                "benchmark_manifest.json": write_bytes(
                    stage / "benchmark_manifest.json",
                    source_inputs["benchmark_manifest"],
                ),
                "answer_key.jsonl": write_bytes(
                    stage / "answer_key.jsonl", evidence["answer_raw"]
                ),
                "source_bundle_manifest.json": write_bytes(
                    stage / "source_bundle_manifest.json",
                    source_inputs["bundle_manifest"],
                ),
                "source_artifact.tar.gz": copy_file(
                    source_archive, stage / "source_artifact.tar.gz"
                ),
                "output_artifact.tar.gz": copy_file(
                    output_archive, stage / "output_artifact.tar.gz"
                ),
            }
            if sealed["source_artifact.tar.gz"] != {
                "bytes": source_download["bytes"],
                "sha256": source_download["sha256"],
            } or sealed["output_artifact.tar.gz"] != {
                "bytes": output_download["bytes"],
                "sha256": output_download["sha256"],
            }:
                raise ValueError("retained cloud archive copy drift")
            with tarfile.open(output_archive, "r:gz") as handle:
                members = validate_tar(
                    handle,
                    output_contract,
                    OUTPUT_UNCOMPRESSED_MAX_BYTES,
                    "output archive",
                )
                output_config = read_member(
                    handle, members["px062_gate2_2/frozen_config.json"]
                )
                output_manifest = read_member(
                    handle, members["px062_gate2_2/source_bundle_manifest.json"]
                )
                summary_raw = read_member(
                    handle, members["px062_gate2_2/collection_summary.json"]
                )
                if output_config != source_inputs["config"]:
                    raise ValueError("output config differs from authenticated source")
                if output_manifest != source_inputs["bundle_manifest"]:
                    raise ValueError("output source manifest differs from authenticated source")
                summary = validate_summary(
                    summary_raw,
                    source_inputs["config"],
                    source_inputs["tasks"],
                    source_inputs["catalog"],
                    source_inputs["benchmark_manifest"],
                )
                sealed["collection_summary.json"] = write_bytes(
                    stage / "collection_summary.json", summary_raw
                )
                tokenizer_raw = read_member(
                    handle, members["px062_gate2_2/tokenizer_artifacts.tar.gz"]
                )
                tokenizer_record = summary["tokenizer_artifacts"]
                if (
                    len(tokenizer_raw) != tokenizer_record["bytes"]
                    or sha256_bytes(tokenizer_raw) != tokenizer_record["sha256"]
                ):
                    raise ValueError("tokenizer archive differs from collection summary")
                sealed["tokenizer_artifacts.tar.gz"] = write_bytes(
                    stage / "tokenizer_artifacts.tar.gz", tokenizer_raw
                )
                trace_member = members["px062_gate2_2/model_traces.jsonl"]
                trace_stream = handle.extractfile(trace_member)
                if trace_stream is None:
                    raise ValueError("unable to stream raw model traces")
                trace_validation = copy_and_validate_traces(
                    trace_stream,
                    stage / "model_traces.jsonl",
                    trace_member.size,
                    summary,
                )
                sealed["model_traces.jsonl"] = {
                    "bytes": trace_validation["bytes"],
                    "sha256": trace_validation["sha256"],
                }

            now = fetched_at or datetime.now(timezone.utc)
            if now.tzinfo is None:
                raise ValueError("fetch timestamp must be timezone-aware")
            if now.astimezone(timezone.utc) < parse_time(
                completion["registered_at_utc"], "completion registration time"
            ):
                raise ValueError("fetch timestamp predates completion registration")
            receipt_payload = {
                "schema_version": "px062-gate2.2-fetch-receipt-v1",
                "experiment_id": completion["experiment_id"],
                "protocol_version": completion["protocol_version"],
                "fetched_at_utc": now.astimezone(timezone.utc)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
                "adjudication_run": False,
                "scientific_outputs_inspected": False,
                "model_trace_content_parsed": True,
                "model_trace_structure_validated": True,
                "trace_summary_reconciled": True,
                "trace_structural_validation": {
                    key: value
                    for key, value in trace_validation.items()
                    if key not in {"bytes", "sha256"}
                },
                "raw_trace_console_output": False,
                "repository": evidence["git_state"],
                "completion_registration": {
                    "path": completion_path.relative_to(root).as_posix(),
                    "sha256": sha256_bytes(evidence["completion_raw"]),
                },
                "job": {
                    "name": description["TrainingJobName"],
                    "arn": description["TrainingJobArn"],
                    "status": description["TrainingJobStatus"],
                    "creation_time_utc": lifecycle["creation"].isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "start_time_utc": lifecycle["start"].isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "end_time_utc": lifecycle["end"].isoformat().replace(
                        "+00:00", "Z"
                    ),
                },
                "source_artifact": {
                    **source,
                    **source_download,
                    "last_modified_utc": source_modified.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "version_listing_repeated": True,
                    "object_attributes_repeated": False,
                },
                "output_artifact": {
                    **output,
                    **output_download,
                    "last_modified_utc": output_modified.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "version_listing_repeated": True,
                    "object_attributes_repeated": output_attributes_before is not None,
                },
                "archive_contracts": {
                    "source_members": sorted(
                        [*SOURCE_GIT_PATHS, "bundle_manifest.json"]
                    ),
                    "output_members": sorted(output_contract),
                    "trace_member_max_bytes": TRACE_MEMBER_MAX_BYTES,
                    "output_uncompressed_max_bytes": OUTPUT_UNCOMPRESSED_MAX_BYTES,
                },
                "sealed_files": sealed,
            }
            validate_fetch_receipt_against_completion(
                receipt_payload, completion, evidence["completion_raw"]
            )
            write_bytes(
                stage / "completion_fetch_receipt.json",
                canonical_json_bytes(receipt_payload),
            )
            if {path.name for path in stage.iterdir()} != SEALED_FILES:
                raise ValueError("sealed confirmation contains unexpected files")
            stage.rename(destination)
            return receipt_payload
        except BaseException:
            if stage.exists():
                shutil.rmtree(stage)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Outcome-blind version-pinned PX-062 Gate 2.2 fetch and seal"
    )
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument(
        "--completion-registration",
        type=Path,
        default=DEFAULT_COMPLETION_REGISTRATION,
    )
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipt = fetch_and_seal(
        root=root,
        profile=args.profile,
        completion_path=args.completion_registration,
        destination=args.destination,
    )
    print(
        json.dumps(
            {
                "adjudication_run": receipt["adjudication_run"],
                "job_name": receipt["job"]["name"],
                "model_trace_content_parsed": receipt[
                    "model_trace_content_parsed"
                ],
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
