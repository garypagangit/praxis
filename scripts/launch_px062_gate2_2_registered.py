#!/usr/bin/env python
"""Launch the single committed PX-062 Gate 2.2 confirmatory request."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REGISTRATION = Path(
    "manifests/px062_gate2_2_20260728/confirmatory_registration.json"
)
EXPECTED_CONFIG = "configs/px062_skill_selection_gate2_2_v1_0_20260728.json"
EXPECTED_ENTRYPOINT = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/sagemaker_entry.py"
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def aws(profile: str, region: str, *arguments: str) -> dict[str, Any]:
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


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=root, text=True
    ).strip()


def validate_repository(root: Path, registration_path: Path) -> dict[str, Any]:
    if git(root, "status", "--porcelain"):
        raise ValueError("launch requires a clean worktree")
    head = git(root, "rev-parse", "HEAD")
    remote_refs = [
        line.strip()
        for line in git(root, "branch", "-r", "--contains", head).splitlines()
        if line.strip()
    ]
    if not remote_refs:
        raise ValueError("launch commit is not present on a remote ref")
    relative = registration_path.relative_to(root).as_posix()
    committed = subprocess.check_output(["git", "show", f"{head}:{relative}"], cwd=root)
    if committed != registration_path.read_bytes():
        raise ValueError("registration differs from the launch commit")
    return {"head": head, "remote_refs": remote_refs}


def validate_request(
    root: Path,
    registration: dict[str, Any],
    profile: str,
) -> tuple[dict[str, Any], bytes]:
    region = registration["region"]
    request_path = root / registration["request_file"]
    request_raw = request_path.read_bytes()
    if sha256_bytes(request_raw) != registration["request_sha256"]:
        raise ValueError("request hash differs from registration")
    request = json.loads(request_raw)
    if request["TrainingJobName"] != registration["job_name"]:
        raise ValueError("request job name differs from registration")
    source = registration["source_bundle"]
    source_uri = f"s3://{source['bucket']}/{source['key']}"
    if request["HyperParameters"].get("sagemaker_submit_directory") != source_uri:
        raise ValueError("request source URI differs from registered object")
    if request["HyperParameters"].get("sagemaker_program") != EXPECTED_ENTRYPOINT:
        raise ValueError("request entry point is not frozen Gate 2.2")
    if request["Environment"] != {
        "PX062_GATE22_CONFIG": EXPECTED_CONFIG,
        "HF_HOME": "/opt/ml/input/data/huggingface",
        "TOKENIZERS_PARALLELISM": "false",
    }:
        raise ValueError("request environment differs from frozen closed schema")
    if request.get("RetryStrategy") != {"MaximumRetryAttempts": 0}:
        raise ValueError("confirmatory request must forbid platform retries")
    head = aws(
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
        "--checksum-mode",
        "ENABLED",
    )
    checks = {
        "VersionId": source["version_id"],
        "ContentLength": source["bytes"],
        "ChecksumSHA256": source["checksum_sha256_base64"],
    }
    for field, expected in checks.items():
        if head.get(field) != expected:
            raise ValueError(f"registered source {field} changed")
    if head.get("Metadata", {}).get("sha256") != source["sha256"]:
        raise ValueError("registered source metadata hash changed")
    return request, request_raw


def validate_unversioned_source_binding(
    profile: str, region: str, source: dict[str, Any]
) -> None:
    """Prove the unversioned SageMaker URI resolves only to the pinned version."""

    listing = aws(
        profile,
        region,
        "s3api",
        "list-object-versions",
        "--bucket",
        source["bucket"],
        "--prefix",
        source["key"],
    )
    versions = [
        row
        for row in listing.get("Versions", [])
        if row.get("Key") == source["key"]
    ]
    markers = [
        row
        for row in listing.get("DeleteMarkers", [])
        if row.get("Key") == source["key"]
    ]
    if (
        len(versions) != 1
        or markers
        or versions[0].get("VersionId") != source["version_id"]
        or versions[0].get("IsLatest") is not True
    ):
        raise ValueError("source key is not exactly one sole/latest registered version")
    latest = aws(
        profile,
        region,
        "s3api",
        "head-object",
        "--bucket",
        source["bucket"],
        "--key",
        source["key"],
        "--checksum-mode",
        "ENABLED",
    )
    expected = {
        "VersionId": source["version_id"],
        "ContentLength": source["bytes"],
        "ChecksumSHA256": source["checksum_sha256_base64"],
    }
    for field, value in expected.items():
        if latest.get(field) != value:
            raise ValueError(f"unversioned source binding {field} mismatch")
    if latest.get("Metadata", {}).get("sha256") != source["sha256"]:
        raise ValueError("unversioned source binding metadata hash mismatch")


def find_training_job(
    profile: str, region: str, job_name: str
) -> dict[str, Any] | None:
    """Describe the exact job; only ResourceNotFound establishes absence."""

    try:
        return aws(
            profile,
            region,
            "sagemaker",
            "describe-training-job",
            "--training-job-name",
            job_name,
        )
    except subprocess.CalledProcessError as error:
        # Throttling, auth, validation, malformed/empty responses, and transport
        # failures remain fatal and can never be interpreted as absence.
        text = f"{error.stderr or ''}\n{error.stdout or ''}"
        if re.search(
            r"\(ResourceNotFound(?:Exception)?\)|[\"'](?:Code|code)[\"']\s*:\s*[\"']ResourceNotFound(?:Exception)?[\"']",
            text,
        ):
            return None
        raise


def _contains_requested(observed: Any, requested: Any) -> bool:
    if isinstance(requested, dict):
        return isinstance(observed, dict) and all(
            key in observed and _contains_requested(observed[key], value)
            for key, value in requested.items()
        )
    if isinstance(requested, list):
        return observed == requested
    return observed == requested


def validate_recoverable_job(
    description: dict[str, Any], request: dict[str, Any], registration: dict[str, Any]
) -> None:
    if description.get("TrainingJobName") != registration["job_name"]:
        raise ValueError("existing job name differs from registration")
    fields = (
        "AlgorithmSpecification",
        "RoleArn",
        "OutputDataConfig",
        "ResourceConfig",
        "StoppingCondition",
        "HyperParameters",
        "Environment",
        "EnableNetworkIsolation",
        "RetryStrategy",
    )
    for field in fields:
        if not _contains_requested(description.get(field), request.get(field)):
            raise ValueError(f"existing job differs from registered request: {field}")
    arn = description.get("TrainingJobArn")
    if not isinstance(arn, str) or not arn.endswith("/" + registration["job_name"]):
        raise ValueError("existing job ARN is not bound to the registered name")


def utc_text(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("SageMaker creation time is timezone-naive")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
    if isinstance(value, str) and value:
        return value
    raise ValueError("SageMaker creation time is missing")


def validate_existing_receipt(
    receipt_path: Path,
    registration_path: Path,
    registration: dict[str, Any],
    request_raw: bytes,
) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checks = {
        "registration_path": registration_path.relative_to(
            registration_path.parents[2]
        ).as_posix(),
        "registration_sha256": sha256_bytes(registration_path.read_bytes()),
        "request_sha256": sha256_bytes(request_raw),
        "training_job_name": registration["job_name"],
        "source_version_id": registration["source_bundle"]["version_id"],
        "source_sha256": registration["source_bundle"]["sha256"],
    }
    for field, expected in checks.items():
        if receipt.get(field) != expected:
            raise ValueError(f"existing launch receipt mismatch: {field}")
    return receipt


def launch(
    root: Path, profile: str, registration_path: Path
) -> dict[str, Any]:
    root = root.resolve()
    registration_path = (
        registration_path
        if registration_path.is_absolute()
        else root / registration_path
    ).resolve()
    state = validate_repository(root, registration_path)
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    request, request_raw = validate_request(root, registration, profile)
    source_commit = registration["source_commit"]
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, state["head"]],
        cwd=root,
    ).returncode != 0:
        raise ValueError("frozen source commit is not an ancestor of launch commit")
    receipt_path = registration_path.parent / "launch_receipt.json"
    if receipt_path.exists():
        return validate_existing_receipt(
            receipt_path, registration_path, registration, request_raw
        )

    region = registration["region"]
    existing = find_training_job(profile, region, registration["job_name"])
    # This check is intentionally as late as possible: SageMaker consumes an
    # unversioned S3 URI, so immediately before create (or receipt recovery) we
    # prove it still resolves to the sole registered object version.
    validate_unversioned_source_binding(
        profile, region, registration["source_bundle"]
    )
    recorded_at = datetime.now(timezone.utc)
    if existing is None:
        try:
            response = aws(
                profile,
                region,
                "sagemaker",
                "create-training-job",
                "--cli-input-json",
                json.dumps(request, separators=(",", ":")),
            )
        except subprocess.CalledProcessError:
            # A timeout can occur after AWS accepted the create.  Do not issue
            # a second create: recover only if the exact registered job now
            # exists and matches the full request.
            existing = find_training_job(profile, region, registration["job_name"])
            if existing is None:
                raise
            description = existing
            response = {"RecoveredAfterCreateError": True}
            launch_mode = "RECOVERED_AFTER_CREATE_ERROR"
        else:
            description = find_training_job(profile, region, registration["job_name"])
            if description is None:
                raise RuntimeError(
                    "create was accepted but exact job is not yet describable; rerun to recover"
                )
            launch_mode = "CREATE_ACCEPTED"
    else:
        description = existing
        response = {"RecoveredExistingRegisteredJob": True}
        launch_mode = "RECOVERED_EXISTING_REGISTERED_JOB"
    validate_recoverable_job(description, request, registration)
    receipt = {
        "schema_version": "px062-gate2.2-launch-receipt-v1",
        "experiment_id": registration["experiment_id"],
        "protocol_version": registration["protocol_version"],
        "launch_commit": state["head"],
        "launch_remote_refs": state["remote_refs"],
        "registration_path": registration_path.relative_to(root).as_posix(),
        "registration_sha256": sha256_bytes(registration_path.read_bytes()),
        "request_sha256": sha256_bytes(request_raw),
        "launched_at_utc": utc_text(description.get("CreationTime")),
        "receipt_recorded_at_utc": recorded_at.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        ),
        "launch_mode": launch_mode,
        "training_job_name": description["TrainingJobName"],
        "training_job_arn": description["TrainingJobArn"],
        "status_at_receipt": description["TrainingJobStatus"],
        "secondary_status_at_receipt": description.get("SecondaryStatus"),
        "source_version_id": registration["source_bundle"]["version_id"],
        "source_sha256": registration["source_bundle"]["sha256"],
        "create_response": response,
        "interpretation": (
            "The single registered job was accepted or idempotently recovered "
            "after acceptance. Pending or running status is infrastructure state, "
            "not a scientific result."
        ),
    }
    receipt_path.write_bytes(
        (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipt = launch(root, args.profile, args.registration)
    print(
        json.dumps(
            {
                "job_name": receipt["training_job_name"],
                "status": receipt["status_at_receipt"],
                "source_version_id": receipt["source_version_id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
