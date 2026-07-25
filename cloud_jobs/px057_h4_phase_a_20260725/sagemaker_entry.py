#!/usr/bin/env python
"""Capture PX-057 H4 Phase A runtime evidence from an exact Git commit."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"missing required environment variable: {name}")
    return value


def run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def output(command: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.strip("/"):
        raise ValueError(f"invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path.strip("/")


def read_huggingface_token(secret_id: str, region: str) -> str:
    import boto3

    response = boto3.client("secretsmanager", region_name=region).get_secret_value(
        SecretId=secret_id
    )
    raw = response.get("SecretString")
    if raw is None:
        raw = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        token = raw.strip()
    else:
        if isinstance(decoded, str):
            token = decoded.strip()
        elif isinstance(decoded, dict):
            token = str(
                decoded.get("HF_TOKEN")
                or decoded.get("token")
                or decoded.get("huggingface_token")
                or ""
            ).strip()
        else:
            token = ""
    if not token:
        raise ValueError("Hugging Face secret contains no supported token value")
    return token


def clone_exact_commit(
    repository_url: str, branch: str, expected_commit: str, target: Path
) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=target)
    run(["git", "remote", "add", "origin", repository_url], cwd=target)
    run(
        ["git", "fetch", "--depth=1", "origin", f"refs/heads/{branch}"],
        cwd=target,
    )
    observed = output(["git", "rev-parse", "FETCH_HEAD"], cwd=target)
    if observed != expected_commit:
        raise ValueError(
            f"remote branch moved: expected {expected_commit}, observed {observed}"
        )
    run(["git", "checkout", "-q", "--detach", expected_commit], cwd=target)
    if output(["git", "status", "--porcelain"], cwd=target):
        raise ValueError("fresh Phase A clone is unexpectedly dirty")


def install_locked_dependencies(repo: Path) -> None:
    requirements = []
    for line in (repo / "requirements-px057-h4.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        value = line.strip()
        if value and not value.startswith("#") and not value.startswith("torch=="):
            requirements.append(value)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            *requirements,
        ]
    )


def put_json_or_file(
    client: Any,
    *,
    bucket: str,
    key: str,
    body: bytes,
    sha256: str,
    git_commit: str,
) -> dict[str, Any]:
    response = client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
        Metadata={"sha256": sha256, "git-commit": git_commit},
    )
    return {
        "bucket": bucket,
        "key": key,
        "version_id": response.get("VersionId"),
        "sha256": sha256,
    }


def main() -> None:
    repository_url = required_env("PX057_H4_REPOSITORY_URL")
    branch = required_env("PX057_H4_BRANCH")
    expected_commit = required_env("PX057_H4_GIT_COMMIT")
    container_digest = required_env("PX057_CONTAINER_IMAGE_DIGEST")
    secret_id = required_env("PX057_H4_HF_SECRET_ID")
    result_uri = required_env("PX057_H4_RESULT_S3_URI")
    region = required_env("AWS_REGION")
    job_name = required_env("PX057_H4_JOB_NAME")
    source_version_id = required_env("PX057_H4_SOURCE_VERSION_ID")
    source_sha256 = required_env("PX057_H4_SOURCE_SHA256")

    staged_archive = Path("/tmp/s")
    if not staged_archive.is_file() or sha256_file(staged_archive) != source_sha256:
        raise ValueError("staged Phase A source differs from the submitted SHA-256")

    repo = Path("/opt/ml/code/px057_h4_repo")
    clone_exact_commit(repository_url, branch, expected_commit, repo)
    committed_entry = (
        repo
        / "cloud_jobs"
        / "px057_h4_phase_a_20260725"
        / "sagemaker_entry.py"
    )
    if sha256_file(Path(__file__).resolve()) != sha256_file(committed_entry):
        raise ValueError("staged entry point differs from the committed entry point")

    install_locked_dependencies(repo)
    token = read_huggingface_token(secret_id, region)
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    os.environ["PX057_CONTAINER_IMAGE_DIGEST"] = container_digest
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    started = datetime.now(timezone.utc).isoformat()
    run(
        [
            sys.executable,
            "scripts/freeze_px057_h4_phase_a.py",
            "--capture-runtime",
            "--container-image-digest",
            container_digest,
        ],
        cwd=repo,
    )
    config = json.loads(
        (repo / "configs/px057_h4_ltt_transfer_20260725.json").read_text(
            encoding="utf-8"
        )
    )
    runtime_path = repo / config["phase_a"]["runtime_manifest"]
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if runtime.get("status") != "PASS" or runtime.get("scientific_data_generated") is not False:
        raise ValueError("Phase A runtime capture did not produce a valid pre-data PASS")

    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    target_dir = model_dir / "px057_h4_phase_a"
    target_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(runtime_path, target_dir / runtime_path.name)

    import boto3

    bucket, prefix = parse_s3_uri(result_uri)
    client = boto3.client("s3", region_name=region)
    runtime_bytes = runtime_path.read_bytes()
    runtime_sha = hashlib.sha256(runtime_bytes).hexdigest()
    runtime_receipt = put_json_or_file(
        client,
        bucket=bucket,
        key=f"{prefix}/runtime_environment.json",
        body=runtime_bytes,
        sha256=runtime_sha,
        git_commit=expected_commit,
    )
    if not runtime_receipt["version_id"]:
        raise ValueError("versioned S3 runtime upload returned no VersionId")

    evidence = {
        "stage": "PX057_H4_phase_a_cloud_capture",
        "status": "PASS",
        "scientific_data_generated": False,
        "job_name": job_name,
        "repository_url": repository_url,
        "branch": branch,
        "git_commit": expected_commit,
        "container_image_digest": container_digest,
        "entrypoint_sha256": sha256_file(committed_entry),
        "source_version_id": source_version_id,
        "source_sha256": source_sha256,
        "runtime_sha256": runtime_sha,
        "runtime_s3": runtime_receipt,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    evidence_bytes = canonical_json_bytes(evidence)
    evidence_path = target_dir / "cloud_job_evidence.json"
    evidence_path.write_bytes(evidence_bytes)
    evidence_receipt = put_json_or_file(
        client,
        bucket=bucket,
        key=f"{prefix}/cloud_job_evidence.json",
        body=evidence_bytes,
        sha256=hashlib.sha256(evidence_bytes).hexdigest(),
        git_commit=expected_commit,
    )
    if not evidence_receipt["version_id"]:
        raise ValueError("versioned S3 evidence upload returned no VersionId")
    print(
        json.dumps(
            {
                "status": "PASS",
                "job_name": job_name,
                "runtime_version_id": runtime_receipt["version_id"],
                "evidence_version_id": evidence_receipt["version_id"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
