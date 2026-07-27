#!/usr/bin/env python
"""Launch exactly one pre-registered PX-062 Gate 2.1 SageMaker request."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aws(profile: str, region: str, *arguments: str) -> Any:
    command = [
        "aws",
        *arguments,
        "--profile",
        profile,
        "--region",
        region,
        "--output",
        "json",
    ]
    return json.loads(subprocess.check_output(command, text=True))


def validate_registration(root: Path, registration: dict[str, Any], profile: str) -> dict:
    region = registration["region"]
    request_path = root / registration["request_file"]
    observed_request_hash = sha256_file(request_path)
    if observed_request_hash != registration["request_sha256"]:
        raise ValueError(
            f"request SHA-256 {observed_request_hash} != "
            f"{registration['request_sha256']}"
        )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request["TrainingJobName"] != registration["job_name"]:
        raise ValueError("registered job name does not match the request")
    source = registration["source_bundle"]
    code_uri = f"s3://{source['bucket']}/{source['key']}"
    if request["HyperParameters"]["sagemaker_submit_directory"] != code_uri:
        raise ValueError("registered source URI does not match the request")
    if (
        request["Environment"]["PX062_CONFIG"]
        != "configs/px062_skill_hallucination_gate2_v1_1_20260726.json"
    ):
        raise ValueError("request does not select the frozen Gate 2.1 config")
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
    )
    if head["VersionId"] != source["version_id"]:
        raise ValueError("S3 version ID does not match the frozen registration")
    if head["ETag"].strip('"') != source["etag"].strip('"'):
        raise ValueError("S3 ETag does not match the frozen registration")
    if head.get("Metadata", {}).get("sha256") != source["sha256"]:
        raise ValueError("S3 SHA-256 metadata does not match the frozen registration")
    return request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument(
        "--registration",
        type=Path,
        default=Path("manifests/px062_gate2_20260727/retry_registration.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    registration_path = (
        args.registration
        if args.registration.is_absolute()
        else root / args.registration
    )
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    request = validate_registration(root, registration, args.profile)
    response = aws(
        args.profile,
        registration["region"],
        "sagemaker",
        "create-training-job",
        "--cli-input-json",
        json.dumps(request, separators=(",", ":")),
    )
    description = aws(
        args.profile,
        registration["region"],
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        registration["job_name"],
    )
    print(
        json.dumps(
            {
                "create_response": response,
                "job_name": description["TrainingJobName"],
                "status": description["TrainingJobStatus"],
                "source_version_id": registration["source_bundle"]["version_id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
