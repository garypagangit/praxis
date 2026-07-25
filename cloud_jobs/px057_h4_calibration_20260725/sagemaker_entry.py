#!/usr/bin/env python
"""Collect one PX-057 H4 calibration cell from an exact frozen Git commit."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGED_ROOT = Path(__file__).resolve().parents[2]
if str(STAGED_ROOT) not in sys.path:
    sys.path.insert(0, str(STAGED_ROOT))

from cloud_jobs.px057_h4_phase_a_20260725.sagemaker_entry import (  # noqa: E402
    canonical_json_bytes,
    install_locked_dependencies,
    output,
    parse_s3_uri,
    read_huggingface_token,
    required_env,
    run,
    sha256_file,
)


ENTRY = "cloud_jobs/px057_h4_calibration_20260725/sagemaker_entry.py"
PHASE_A_ENTRY = "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"
CONFIG = "configs/px057_h4_ltt_transfer_20260725.json"
COLLECTION_FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
)


def clone_exact_branch_history(
    repository_url: str, branch: str, expected_commit: str, target: Path
) -> None:
    """Fetch the full branch so the frozen collector can prove ancestor commits."""

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=target)
    run(["git", "remote", "add", "origin", repository_url], cwd=target)
    run(
        [
            "git",
            "fetch",
            "--no-tags",
            "origin",
            f"refs/heads/{branch}:refs/remotes/origin/{branch}",
        ],
        cwd=target,
    )
    observed = output(["git", "rev-parse", f"refs/remotes/origin/{branch}"], cwd=target)
    if observed != expected_commit:
        raise ValueError(
            f"remote branch moved: expected {expected_commit}, observed {observed}"
        )
    run(["git", "checkout", "-q", "--detach", expected_commit], cwd=target)
    if output(["git", "status", "--porcelain"], cwd=target):
        raise ValueError("fresh calibration clone is unexpectedly dirty")


def put_file(
    client: Any,
    *,
    bucket: str,
    key: str,
    path: Path,
    git_commit: str,
) -> dict[str, Any]:
    digest = sha256_file(path)
    content_type = (
        "application/x-ndjson" if path.suffix == ".jsonl" else "application/json"
    )
    with path.open("rb") as handle:
        response = client.put_object(
            Bucket=bucket,
            Key=key,
            Body=handle,
            ContentLength=path.stat().st_size,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            Metadata={"sha256": digest, "git-commit": git_commit},
        )
    receipt = {
        "bucket": bucket,
        "key": key,
        "version_id": response.get("VersionId"),
        "sha256": digest,
        "size_bytes": path.stat().st_size,
        "server_side_encryption": response.get("ServerSideEncryption"),
    }
    if not receipt["version_id"]:
        raise ValueError(f"versioned S3 upload returned no VersionId for {path.name}")
    if receipt["server_side_encryption"] != "AES256":
        raise ValueError(f"S3 upload did not confirm AES256 for {path.name}")
    return receipt


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
    cell_id = required_env("PX057_H4_CELL_ID")

    staged_archive = Path("/tmp/px057-h4-source.tar.gz")
    if not staged_archive.is_file() or sha256_file(staged_archive) != source_sha256:
        raise ValueError("staged source archive differs from the submitted SHA-256")

    started = datetime.now(timezone.utc).isoformat()
    repo = Path("/opt/ml/code/px057_h4_repo")
    clone_exact_branch_history(repository_url, branch, expected_commit, repo)
    committed_entry = repo / ENTRY
    committed_phase_a_entry = repo / PHASE_A_ENTRY
    if sha256_file(Path(__file__).resolve()) != sha256_file(committed_entry):
        raise ValueError("staged calibration entry differs from the committed entry")
    if sha256_file(STAGED_ROOT / PHASE_A_ENTRY) != sha256_file(committed_phase_a_entry):
        raise ValueError("staged Phase A helper differs from the committed helper")

    config = json.loads((repo / CONFIG).read_text(encoding="utf-8"))
    transport = config["calibration_transport"]
    if (
        int(transport["max_runtime_seconds"]) != 86400
        or transport["sagemaker_quota_code"] != "L-2D6DEB3C"
        or transport["first_attempt_only"] is not True
        or transport["source_bootstrap"]
        != "explicit_s3_version_and_sha256_before_extraction"
    ):
        raise ValueError("calibration transport differs from the frozen protocol")
    matching_cells = [cell for cell in config["cells"] if cell["cell_id"] == cell_id]
    if len(matching_cells) != 1:
        raise ValueError(f"unknown or duplicate PX-057 H4 cell: {cell_id}")
    cell = matching_cells[0]
    output_dir = repo / cell["output_dirs"]["calibration"]
    if output_dir.exists():
        raise FileExistsError(f"calibration output already exists in clean clone: {output_dir}")

    install_locked_dependencies(repo)
    token = read_huggingface_token(secret_id, region)
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    os.environ["PX057_CONTAINER_IMAGE_DIGEST"] = container_digest
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    run(
        [
            sys.executable,
            "scripts/run_px057_h4_trace_collection.py",
            "--cell",
            cell_id,
            "--split",
            "calibration",
        ],
        cwd=repo,
    )

    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from scripts.px057_h4_common import verify_collection_bundle

    verification = verify_collection_bundle(
        output_dir,
        repo / cell["calibration_manifest"],
        expected_cell_id=cell_id,
        expected_split="calibration",
        expected_n=int(config["split_design"]["calibration_n"]),
        expected_rounds=int(config["generation"]["rounds"]),
        expected_model=config["models"][cell["model_key"]],
        expected_prompt_id=config["generation"]["prompt_template_id"],
        expected_prompt_sha256=config["generation"]["prompt_template_sha256"],
    )

    import boto3

    bucket, prefix = parse_s3_uri(result_uri)
    client = boto3.client("s3", region_name=region)
    receipts: dict[str, dict[str, Any]] = {}
    for name in COLLECTION_FILES:
        path = output_dir / name
        receipts[name] = put_file(
            client,
            bucket=bucket,
            key=f"{prefix}/{name}",
            path=path,
            git_commit=expected_commit,
        )

    summary = json.loads((output_dir / "collection_summary.json").read_text(encoding="utf-8"))
    evidence = {
        "experiment_id": config["experiment_id"],
        "stage": "PX057_H4_calibration_cloud_collection",
        "status": "PASS",
        "scientific_data_generated": True,
        "split": "calibration",
        "cell_id": cell_id,
        "job_name": job_name,
        "repository_url": repository_url,
        "branch": branch,
        "git_commit": expected_commit,
        "container_image_digest": container_digest,
        "entrypoint_sha256": sha256_file(committed_entry),
        "phase_a_helper_sha256": sha256_file(committed_phase_a_entry),
        "source_version_id": source_version_id,
        "source_sha256": source_sha256,
        "phase_a_evidence": summary["phase_a_evidence"],
        "collection_verification": verification,
        "collection_objects": receipts,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    evidence_bytes = canonical_json_bytes(evidence)
    evidence_path = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model")) / "cloud_job_evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_bytes(evidence_bytes)
    evidence_receipt = put_file(
        client,
        bucket=bucket,
        key=f"{prefix}/cloud_job_evidence.json",
        path=evidence_path,
        git_commit=expected_commit,
    )

    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    bundle_target = model_dir / "px057_h4_calibration" / cell_id
    bundle_target.mkdir(parents=True, exist_ok=False)
    for name in COLLECTION_FILES:
        shutil.copy2(output_dir / name, bundle_target / name)
    shutil.copy2(evidence_path, bundle_target / evidence_path.name)
    print(
        json.dumps(
            {
                "status": "PASS",
                "job_name": job_name,
                "cell_id": cell_id,
                "evidence_version_id": evidence_receipt["version_id"],
                "collection_version_ids": {
                    name: receipt["version_id"] for name, receipt in receipts.items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
