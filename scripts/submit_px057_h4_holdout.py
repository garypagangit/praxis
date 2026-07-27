#!/usr/bin/env python
"""Submit exactly one frozen PX-057 H4 held-out collection job."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import committed_file_info, read_json, sha256_file, write_json
from scripts.freeze_px057_h4_holdout_transport import validate_freeze_manifest
from scripts.run_px057_h4_holdout_gate import verify_all_locks


DEFAULT_TRANSPORT_CONFIG = ROOT / "configs/px057_h4_holdout_transport_20260727.json"
DEFAULT_FREEZE_MANIFEST = (
    ROOT / "manifests/px057_h4_20260725/holdout_transport_freeze.json"
)
ENTRY = "cloud_jobs/px057_h4_holdout_20260727/sagemaker_entry.py"
CALIBRATION_ENTRY = "cloud_jobs/px057_h4_calibration_20260725/sagemaker_entry.py"
PHASE_A_ENTRY = "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"
SCIENCE_CONFIG = "configs/px057_h4_ltt_transfer_20260725.json"
HOLDOUT_MAX_RUNTIME_SECONDS = 86_400
SAGEMAKER_G5_2XL_QUOTA_CODE = "L-2D6DEB3C"
CELL_JOB_CODES = {
    "cell1_llama31_gsm8k": "c1",
    "cell2_qwen25_arc": "c2",
    "cell3_llama31_arc": "c3",
}
COLLECTION_FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
)


def command_output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws(profile: str, region: str, *args: str) -> str:
    return command_output(["aws", *args, "--profile", profile, "--region", region])


def aws_json(profile: str, region: str, *args: str) -> dict[str, Any]:
    raw = aws(profile, region, *args, "--output", "json")
    return json.loads(raw) if raw else {}


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_transport(path: Path) -> dict[str, Any]:
    return read_json_strict(path)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, nested in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = nested
    return value


def read_json_strict(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def science_config_path(transport: dict[str, Any]) -> Path:
    return repo_path(transport["frozen_science"]["config_path"])


def freeze_manifest_path(transport: dict[str, Any]) -> Path:
    return repo_path(transport["source"]["freeze_manifest"])


def transport_cell(transport: dict[str, Any], cell_id: str) -> dict[str, Any]:
    cells = transport["cells"]
    if not isinstance(cells, dict) or cell_id not in cells:
        raise ValueError(f"unknown holdout transport cell: {cell_id}")
    return cells[cell_id]


def holdout_job_name(cell_id: str) -> str:
    try:
        code = CELL_JOB_CODES[cell_id]
    except KeyError as exc:
        raise ValueError(f"unknown PX-057 H4 cell: {cell_id}") from exc
    return f"px057-h4-hold-{code}-r1-20260727"


def source_launch_command() -> str:
    command = (
        "a=/tmp/s;mkdir -p /opt/ml/code&&aws s3api get-object "
        "--bucket \"$B\" --key \"$K\" --version-id \"$V\" $a>/dev/null&&"
        "echo \"$H  $a\"|sha256sum -c -&&tar xzf $a -C /opt/ml/code&&"
        f"python /opt/ml/code/{ENTRY}"
    )
    if len(command) > 256:
        raise ValueError("holdout bootstrap exceeds SageMaker's 256-character limit")
    return command


def verify_git(branch: str) -> str:
    if command_output(["git", "status", "--porcelain"]):
        raise ValueError("holdout submission requires a clean worktree")
    head = command_output(["git", "rev-parse", "HEAD"])
    current_branch = command_output(["git", "branch", "--show-current"])
    if current_branch != branch:
        raise ValueError(f"expected branch {branch}, found {current_branch}")
    remote_line = command_output(
        ["git", "ls-remote", "origin", f"refs/heads/{branch}"]
    )
    remote_head = remote_line.split()[0] if remote_line else ""
    if remote_head != head:
        raise ValueError("local HEAD is not the pushed branch HEAD")
    return head


def committed_and_pushed(path: Path) -> dict[str, Any]:
    evidence = committed_file_info(ROOT, path)
    remote_refs = [
        value.strip()
        for value in subprocess.check_output(
            [
                "git",
                "branch",
                "-r",
                "--contains",
                evidence["last_change_commit"],
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if value.strip()
    ]
    if not remote_refs:
        raise ValueError(f"{evidence['path']}: defining commit has not been pushed")
    return {**evidence, "remote_refs": remote_refs}


def verify_transport_config(transport: dict[str, Any]) -> None:
    aws_config = transport["aws"]
    source = transport["source"]
    collection = transport["collection"]
    expected_jobs = {
        cell_id: holdout_job_name(cell_id) for cell_id in CELL_JOB_CODES
    }
    if (
        transport.get("stage") != "H4_holdout_transport_pre_outcome_freeze"
        or transport.get("status") != "FREEZE_PENDING"
        or transport.get("rules", {}).get("first_attempt_only") is not True
        or int(aws_config.get("max_runtime_seconds", -1))
        != HOLDOUT_MAX_RUNTIME_SECONDS
        or aws_config.get("retry_strategy_omitted") is not True
        or aws_config.get("enable_managed_spot_training") is not False
        or aws_config.get("quota_code")
        != SAGEMAKER_G5_2XL_QUOTA_CODE
        or transport.get("rules", {}).get("no_retry")
        != "No retry or replacement job is allowed under this transport ID."
        or source.get("bootstrap")
        != "explicit_s3_version_and_sha256_before_extraction"
        or source.get("entrypoint") != ENTRY
        or source.get("calibration_entrypoint") != CALIBRATION_ENTRY
        or source.get("phase_a_entrypoint") != PHASE_A_ENTRY
        or source.get("freeze_manifest")
        != DEFAULT_FREEZE_MANIFEST.relative_to(ROOT).as_posix()
        or set(source.get("archive_members", []))
        != {
            "cloud_jobs/px057_h4_holdout_20260727/.gitattributes",
            ENTRY,
            CALIBRATION_ENTRY,
            PHASE_A_ENTRY,
            "configs/px057_h4_holdout_transport_20260727.json",
            SCIENCE_CONFIG,
            "configs/px057_h4_prompt_templates_20260725.json",
            "requirements-px057-h4.txt",
            "scripts/run_px057_h4_trace_collection.py",
            "scripts/px057_h4_common.py",
            "scripts/run_px057_h4_holdout_gate.py",
        }
        or collection.get("split") != "holdout"
        or int(collection.get("expected_traces", -1)) != 300
        or int(collection.get("rounds", -1)) != 8
        or int(collection.get("expected_generations", -1)) != 2400
        or tuple(collection.get("files", [])) != COLLECTION_FILES
        or set(transport.get("cells", {})) != set(CELL_JOB_CODES)
        or any(
            transport_cell(transport, cell_id).get("job_name") != job_name
            for cell_id, job_name in expected_jobs.items()
        )
        or aws_config.get("instance_type") != "ml.g5.2xlarge"
        or aws_config.get("container_pinned_uri", aws_config.get("container_image_pinned_uri"))
        is None
    ):
        raise ValueError("holdout transport differs from the frozen protocol")


def _freeze_artifact_records(freeze: dict[str, Any]) -> list[dict[str, Any]]:
    records = freeze.get("protected_artifacts", freeze.get("artifacts", {}))
    if not isinstance(records, dict):
        raise ValueError("holdout transport freeze has no artifact map")
    return list(records.values())


def verify_artifact_at_freeze_base(
    record: dict[str, Any], *, freeze_base_commit: str
) -> None:
    """Prove the recorded bytes already existed at the claimed freeze commit."""

    relative = str(record["path"])
    last_change_commit = str(record["last_change_commit"])
    if (
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                last_change_commit,
                freeze_base_commit,
            ],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError(f"artifact postdates the holdout freeze: {relative}")
    try:
        frozen_bytes = subprocess.check_output(
            ["git", "show", f"{freeze_base_commit}:{relative}"], cwd=ROOT
        )
        frozen_blob = command_output(
            ["git", "rev-parse", f"{freeze_base_commit}:{relative}"]
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"artifact did not exist at the holdout freeze: {relative}"
        ) from exc
    if (
        hashlib.sha256(frozen_bytes).hexdigest() != record["sha256"]
        or len(frozen_bytes) != int(record["bytes"])
        or frozen_blob != record["git_blob"]
    ):
        raise ValueError(f"artifact bytes differ at the holdout freeze: {relative}")


def verify_transport_freeze(
    transport_path: Path, transport: dict[str, Any]
) -> dict[str, Any]:
    """Verify the committed/pushed pre-result transport and its freeze record."""

    verify_transport_config(transport)
    transport_commit = committed_and_pushed(transport_path)
    freeze_path = freeze_manifest_path(transport)
    freeze_commit = committed_and_pushed(freeze_path)
    freeze = read_json_strict(freeze_path)
    validate_freeze_manifest(transport, freeze, repo_root=ROOT)
    freeze_base_commit = str(freeze["freeze_base_commit"])
    records = _freeze_artifact_records(freeze)
    by_path = {str(record.get("path")): record for record in records}
    transport_relative = transport_path.resolve().relative_to(ROOT).as_posix()
    science_path = science_config_path(transport)
    science_relative = science_path.resolve().relative_to(ROOT).as_posix()
    if (
        freeze.get("transport_id") != transport["transport_id"]
        or freeze.get("experiment_id") != transport["experiment_id"]
        or freeze.get("status") != "PASS"
        or freeze.get("scientific_data_generated") not in (None, False)
        or by_path.get(transport_relative, {}).get("sha256")
        != sha256_file(transport_path)
        or by_path.get(science_relative, {}).get("sha256") != sha256_file(science_path)
    ):
        raise ValueError("holdout transport freeze identity is invalid")
    for record in records:
        path = repo_path(str(record["path"]))
        committed = committed_file_info(ROOT, path)
        git_blob = command_output(
            ["git", "rev-parse", f"HEAD:{committed['path']}"]
        )
        if (
            record.get("sha256") != committed["sha256"]
            or record.get("last_change_commit") != committed["last_change_commit"]
            or record.get("git_blob") != git_blob
            or int(record.get("bytes", -1)) != path.stat().st_size
            or record.get("verified_at_head") != freeze["freeze_base_commit"]
        ):
            raise ValueError(f"holdout frozen artifact changed: {record['path']}")
        verify_artifact_at_freeze_base(
            record, freeze_base_commit=freeze_base_commit
        )
    expected_science_hash = transport["frozen_science"]["config_sha256"]
    if sha256_file(science_path) != expected_science_hash:
        raise ValueError("science config differs from the holdout transport freeze")
    calibration_commit = transport["frozen_science"]["calibration_evidence_commit"]
    if (
        len(calibration_commit) != 40
        or subprocess.run(
            ["git", "merge-base", "--is-ancestor", calibration_commit, "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("calibration evidence commit is not an ancestor of HEAD")
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", freeze_base_commit, "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("holdout freeze base commit is not an ancestor of HEAD")
    freeze_change_commit = str(freeze_commit["last_change_commit"])
    for ancestor, descendant, label in (
        (
            freeze_base_commit,
            freeze_change_commit,
            "freeze base does not precede its manifest commit",
        ),
        (
            freeze_change_commit,
            "HEAD",
            "freeze manifest commit is not an ancestor of HEAD",
        ),
    ):
        if (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
        ):
            raise ValueError(label)
    remote_refs = [
        value.strip()
        for value in subprocess.check_output(
            ["git", "branch", "-r", "--contains", calibration_commit],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if value.strip()
    ]
    if not remote_refs:
        raise ValueError("calibration evidence commit has not been pushed")
    return {
        "transport": transport_commit,
        "freeze": freeze_commit,
        "freeze_sha256": sha256_file(freeze_path),
        "science_config_sha256": sha256_file(science_path),
        "calibration_evidence_commit": calibration_commit,
        "calibration_evidence_remote_refs": remote_refs,
    }


def verify_ltt_locks(
    transport: dict[str, Any],
    science_config: dict[str, Any],
    science_path: Path,
    *,
    eligible_cell_id: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Verify all terminal locks and require a policy only for the target cell."""

    evidence = verify_all_locks(science_config, science_path)
    if set(evidence) != set(CELL_JOB_CODES):
        raise ValueError("canonical LTT verifier did not return all three cells")
    science_cells = {cell["cell_id"]: cell for cell in science_config["cells"]}
    locks: dict[str, dict[str, Any]] = {}
    for cell_id in CELL_JOB_CODES:
        lock_path = repo_path(science_cells[cell_id]["ltt_lock_manifest"])
        lock = read_json(lock_path)
        if transport_cell(transport, cell_id).get("ltt_lock_manifest") not in (
            None,
            lock_path.relative_to(ROOT).as_posix(),
        ):
            raise ValueError(f"{cell_id}: transport points to a different LTT lock")
        locks[cell_id] = lock
    if eligible_cell_id not in locks:
        raise ValueError(f"unknown holdout target cell: {eligible_cell_id}")
    if locks[eligible_cell_id].get("selected_policy") is None:
        raise ValueError(
            f"{eligible_cell_id}: selected_policy is null; this cell's holdout is closed"
        )
    return evidence, locks


def preflight_aws(
    transport: dict[str, Any],
    science_config: dict[str, Any],
    profile: str,
    region: str,
) -> None:
    aws_config = transport["aws"]
    science_aws = science_config["phase_a"]["aws"]
    comparable = {
        "profile": "profile",
        "region": "region",
        "role_arn": "role_arn",
        "bucket": "bucket",
        "s3_prefix": "s3_prefix",
        "instance_type": "instance_type",
        "volume_size_gb": "volume_size_gb",
        "container_image_pinned_uri": "container_image_pinned_uri",
        "container_digest": "container_image_digest",
        "huggingface_secret_id": "huggingface_secret_id",
    }
    if any(
        aws_config[transport_key] != science_aws[science_key]
        for transport_key, science_key in comparable.items()
    ) or transport["repository"] != {
        "url": science_aws["repository_url"],
        "branch": science_aws["branch"],
    }:
        raise ValueError("holdout AWS/repository identity differs from frozen science")
    pinned_uri = aws_config["container_image_pinned_uri"]
    registry_and_repository, requested_digest = pinned_uri.rsplit("@", 1)
    registry, repository = registry_and_repository.split("/", 1)
    registry_id = registry.split(".", 1)[0]
    observed_digest = aws(
        profile,
        region,
        "ecr",
        "batch-get-image",
        "--registry-id",
        registry_id,
        "--repository-name",
        repository,
        "--image-ids",
        f"imageDigest={requested_digest}",
        "--query",
        "images[0].imageId.imageDigest",
        "--output",
        "text",
    )
    if (
        observed_digest != requested_digest
        or requested_digest != aws_config["container_digest"]
        or science_aws["container_image_digest"] != aws_config["container_digest"]
        or science_aws["container_image_pinned_uri"]
        != aws_config["container_image_pinned_uri"]
    ):
        raise ValueError("resolved ECR digest differs from the frozen transport")
    versioning = aws_json(
        profile,
        region,
        "s3api",
        "get-bucket-versioning",
        "--bucket",
        aws_config["bucket"],
    )
    if versioning.get("Status") != "Enabled":
        raise ValueError("H4 bucket versioning must be Enabled before submission")
    aws_json(
        profile,
        region,
        "secretsmanager",
        "describe-secret",
        "--secret-id",
        aws_config["huggingface_secret_id"],
    )
    aws_json(
        profile,
        region,
        "iam",
        "get-role",
        "--role-name",
        aws_config["role_arn"].rsplit("/", 1)[1],
    )


def preflight_capacity(
    transport: dict[str, Any], profile: str, region: str
) -> dict[str, Any]:
    aws_config = transport["aws"]
    quota = aws_json(
        profile,
        region,
        "service-quotas",
        "get-service-quota",
        "--service-code",
        "sagemaker",
        "--quota-code",
        SAGEMAKER_G5_2XL_QUOTA_CODE,
    )
    quota_value = int(float(quota["Quota"]["Value"]))
    active: list[dict[str, Any]] = []
    for status in ("InProgress", "Stopping"):
        listing = aws_json(
            profile,
            region,
            "sagemaker",
            "list-training-jobs",
            "--status-equals",
            status,
        )
        for summary in listing.get("TrainingJobSummaries", []):
            description = aws_json(
                profile,
                region,
                "sagemaker",
                "describe-training-job",
                "--training-job-name",
                summary["TrainingJobName"],
            )
            resource = description["ResourceConfig"]
            if resource["InstanceType"] == aws_config["instance_type"]:
                active.append(
                    {
                        "job_name": summary["TrainingJobName"],
                        "status": status,
                        "instance_count": int(resource["InstanceCount"]),
                    }
                )
    active_instances = sum(item["instance_count"] for item in active)
    if active_instances + 1 > quota_value:
        raise ValueError(
            f"SageMaker {aws_config['instance_type']} capacity is {quota_value}; "
            f"{active_instances} instance(s) are active and one was requested"
        )
    return {
        "quota_code": SAGEMAKER_G5_2XL_QUOTA_CODE,
        "quota_value": quota_value,
        "active_instances": active_instances,
        "active_jobs": active,
        "requested_jobs": 1,
    }


def _s3_history(
    *, profile: str, region: str, bucket: str, prefix: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    listing = aws_json(
        profile,
        region,
        "s3api",
        "list-object-versions",
        "--bucket",
        bucket,
        "--prefix",
        prefix,
    )
    versions = [
        row
        for row in listing.get("Versions", [])
        if str(row.get("Key", "")).startswith(prefix)
    ]
    deletes = [
        row
        for row in listing.get("DeleteMarkers", [])
        if str(row.get("Key", "")).startswith(prefix)
    ]
    return versions, deletes


def verify_first_attempt(
    transport: dict[str, Any], *, cell_id: str, profile: str, region: str
) -> None:
    cell = transport_cell(transport, cell_id)
    job_name = holdout_job_name(cell_id)
    for key in ("launch_manifest", "cloud_manifest"):
        path = repo_path(cell[key])
        if path.exists():
            raise FileExistsError(f"holdout {key} already exists: {path}")
    if repo_path(cell["output_dir"]).exists():
        raise FileExistsError(f"holdout output already exists for {cell_id}")
    verify_no_downstream_evidence(transport, cell_id=cell_id)
    listing = aws_json(
        profile,
        region,
        "sagemaker",
        "list-training-jobs",
        "--name-contains",
        job_name,
    )
    if any(
        row.get("TrainingJobName") == job_name
        for row in listing.get("TrainingJobSummaries", [])
    ):
        raise ValueError(f"{cell_id}: prior SageMaker holdout attempt exists")
    aws_config = transport["aws"]
    prefix = aws_config["s3_prefix"].strip("/")
    source_prefix = f"{prefix}/code/{job_name}/"
    result_prefix = str(cell["result_prefix"]).strip("/") + "/"
    model_prefix = f"{prefix}/sagemaker-output/{job_name}/"
    for label, candidate in (
        ("source", source_prefix),
        ("result", result_prefix),
        ("model", model_prefix),
    ):
        versions, deletes = _s3_history(
            profile=profile,
            region=region,
            bucket=aws_config["bucket"],
            prefix=candidate,
        )
        if versions or deletes:
            raise ValueError(
                f"{cell_id}: prior {label} S3 history exists; first attempt is closed"
            )


def verify_no_downstream_evidence(
    transport: dict[str, Any], *, cell_id: str
) -> None:
    """Preserve collection-before-audit/adjudication chronology for one cell."""

    cell = transport_cell(transport, cell_id)
    for key in (
        "manual_audit_blinded",
        "manual_audit",
        "holdout_determination",
    ):
        path = repo_path(cell[key])
        if path.exists():
            raise FileExistsError(
                f"{cell_id}: downstream {key} exists before holdout retrieval: {path}"
            )


def build_source_archive(path: Path, transport: dict[str, Any]) -> None:
    """Build deterministic source bytes from committed Git blobs only."""

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as handle:
        for relative in sorted(transport["source"]["archive_members"]):
            body = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
            metadata = tarfile.TarInfo(relative)
            metadata.size = len(body)
            metadata.mode = 0o644
            metadata.mtime = 0
            metadata.uid = 0
            metadata.gid = 0
            metadata.uname = ""
            metadata.gname = ""
            handle.addfile(metadata, io.BytesIO(body))
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", fileobj=raw, mode="wb", mtime=0
        ) as compressed:
            compressed.write(tar_buffer.getvalue())


def upload_source(
    *,
    archive: Path,
    archive_sha256: str,
    code_key: str,
    bucket: str,
    profile: str,
    region: str,
) -> dict[str, Any]:
    response = aws_json(
        profile,
        region,
        "s3api",
        "put-object",
        "--bucket",
        bucket,
        "--key",
        code_key,
        "--body",
        f"fileb://{archive.resolve()}",
        "--server-side-encryption",
        "AES256",
        "--metadata",
        f"sha256={archive_sha256}",
        "--content-type",
        "application/gzip",
    )
    version_id = response.get("VersionId")
    if not version_id:
        raise ValueError("versioned holdout source upload returned no VersionId")
    head = aws_json(
        profile,
        region,
        "s3api",
        "head-object",
        "--bucket",
        bucket,
        "--key",
        code_key,
        "--version-id",
        str(version_id),
    )
    if (
        head.get("VersionId") != version_id
        or head.get("ServerSideEncryption") != "AES256"
        or head.get("Metadata", {}).get("sha256") != archive_sha256
        or int(head.get("ContentLength", -1)) != archive.stat().st_size
    ):
        raise ValueError("holdout source object failed version/hash/AES256 checks")
    return {
        "version_id": str(version_id),
        "sha256": archive_sha256,
        "size_bytes": archive.stat().st_size,
        "etag": str(head.get("ETag", "")).strip('"'),
        "server_side_encryption": head.get("ServerSideEncryption"),
    }


def expected_environment(
    transport: dict[str, Any],
    *,
    cell_id: str,
    git_commit: str,
    code_key: str,
    code_version_id: str,
    code_sha256: str,
    transport_sha256: str,
    science_sha256: str,
    freeze_sha256: str,
    lock_sha256: str,
    selected_policy_sha256: str,
) -> dict[str, str]:
    aws_config = transport["aws"]
    repository = transport["repository"]
    cell = transport_cell(transport, cell_id)
    result_uri = f"s3://{aws_config['bucket']}/{str(cell['result_prefix']).strip('/')}"
    return {
        "AWS_REGION": aws_config["region"],
        "AWS_DEFAULT_REGION": aws_config["region"],
        "HF_HOME": "/opt/ml/input/data/huggingface",
        "TOKENIZERS_PARALLELISM": "false",
        "PX057_H4_REPOSITORY_URL": repository["url"],
        "PX057_H4_BRANCH": repository["branch"],
        "PX057_H4_GIT_COMMIT": git_commit,
        "PX057_CONTAINER_IMAGE_DIGEST": aws_config["container_digest"],
        "PX057_H4_HF_SECRET_ID": aws_config["huggingface_secret_id"],
        "PX057_H4_RESULT_S3_URI": result_uri,
        "PX057_H4_JOB_NAME": holdout_job_name(cell_id),
        "PX057_H4_SOURCE_VERSION_ID": code_version_id,
        "PX057_H4_SOURCE_SHA256": code_sha256,
        "PX057_H4_SOURCE_BUCKET": aws_config["bucket"],
        "PX057_H4_SOURCE_KEY": code_key,
        "PX057_H4_TRANSPORT_ID": transport["transport_id"],
        "PX057_H4_SCIENCE_CONFIG_SHA256": science_sha256,
        "PX057_H4_TRANSPORT_CONFIG_SHA256": transport_sha256,
        "PX057_H4_FREEZE_SHA256": freeze_sha256,
        "PX057_H4_LOCK_SHA256": lock_sha256,
        "PX057_H4_SELECTED_POLICY_SHA256": selected_policy_sha256,
        "B": aws_config["bucket"],
        "K": code_key,
        "V": code_version_id,
        "H": code_sha256,
        "PX057_H4_CELL_ID": cell_id,
    }


def training_request(
    transport: dict[str, Any],
    *,
    cell_id: str,
    git_commit: str,
    code_uri: str,
    code_version_id: str,
    code_sha256: str,
    transport_sha256: str,
    science_sha256: str,
    freeze_sha256: str,
    lock_sha256: str,
    selected_policy_sha256: str,
) -> dict[str, Any]:
    aws_config = transport["aws"]
    code_key = code_uri.split(f"s3://{aws_config['bucket']}/", 1)[1]
    job_name = holdout_job_name(cell_id)
    return {
        "TrainingJobName": job_name,
        "RoleArn": aws_config["role_arn"],
        "AlgorithmSpecification": {
            "TrainingImage": aws_config["container_image_pinned_uri"],
            "TrainingInputMode": "File",
            "ContainerEntrypoint": ["bash", "-lc"],
            "ContainerArguments": [source_launch_command()],
        },
        "InputDataConfig": [
            {
                "ChannelName": "code",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": code_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "InputMode": "File",
            }
        ],
        "OutputDataConfig": {
            "S3OutputPath": (
                f"s3://{aws_config['bucket']}/"
                f"{aws_config['s3_prefix'].strip('/')}/sagemaker-output"
            )
        },
        "ResourceConfig": {
            "InstanceType": aws_config["instance_type"],
            "InstanceCount": 1,
            "VolumeSizeInGB": int(aws_config["volume_size_gb"]),
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": HOLDOUT_MAX_RUNTIME_SECONDS,
        },
        "Environment": expected_environment(
            transport,
            cell_id=cell_id,
            git_commit=git_commit,
            code_key=code_key,
            code_version_id=code_version_id,
            code_sha256=code_sha256,
            transport_sha256=transport_sha256,
            science_sha256=science_sha256,
            freeze_sha256=freeze_sha256,
            lock_sha256=lock_sha256,
            selected_policy_sha256=selected_policy_sha256,
        ),
        "EnableNetworkIsolation": False,
        "EnableManagedSpotTraining": aws_config["enable_managed_spot_training"],
        "Tags": [
            {"Key": "Project", "Value": "PraxisResearch"},
            {"Key": "PraxisId", "Value": "PX-057"},
            {"Key": "Gate", "Value": "H4-Holdout"},
            {"Key": "Cell", "Value": cell_id},
            {"Key": "GitCommit", "Value": git_commit[:40]},
            {"Key": "TransportId", "Value": transport["transport_id"]},
        ],
    }


def write_launch_manifest(
    transport: dict[str, Any],
    *,
    cell_id: str,
    request: dict[str, Any],
    training_job_arn: str,
    source_object: dict[str, Any],
) -> Path:
    cell = transport_cell(transport, cell_id)
    path = repo_path(cell["launch_manifest"])
    if path.exists():
        raise FileExistsError(f"refusing to replace holdout launch manifest: {path}")
    environment = request["Environment"]
    payload = {
        "transport_id": transport["transport_id"],
        "experiment_id": transport["experiment_id"],
        "stage": "H4_holdout_launch_registration",
        "status": "REGISTERED_PRE_RESULT",
        "scientific_result_observed": False,
        "cell_id": cell_id,
        "job_name": request["TrainingJobName"],
        "training_job_arn": training_job_arn,
        "git_commit": environment["PX057_H4_GIT_COMMIT"],
        "container_image": request["AlgorithmSpecification"]["TrainingImage"],
        "code_uri": request["InputDataConfig"][0]["DataSource"]["S3DataSource"][
            "S3Uri"
        ],
        "code_version_id": source_object["version_id"],
        "code_sha256": source_object["sha256"],
        "source_object": source_object,
        "result_uri": environment["PX057_H4_RESULT_S3_URI"],
        "max_runtime_seconds": HOLDOUT_MAX_RUNTIME_SECONDS,
        "retry_strategy_omitted": transport["aws"]["retry_strategy_omitted"],
        "managed_spot_training": transport["aws"][
            "enable_managed_spot_training"
        ],
        "transport_config_sha256": environment[
            "PX057_H4_TRANSPORT_CONFIG_SHA256"
        ],
        "science_config_sha256": environment["PX057_H4_SCIENCE_CONFIG_SHA256"],
        "transport_freeze_sha256": environment["PX057_H4_FREEZE_SHA256"],
        "ltt_lock_sha256": environment["PX057_H4_LOCK_SHA256"],
        "selected_policy_sha256": environment[
            "PX057_H4_SELECTED_POLICY_SHA256"
        ],
        "request_sha256": canonical_json_sha256(request),
        "registered_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rule": (
            "This is the sole registered held-out attempt for this cell. A retry "
            "requires a new experiment identifier or formal pre-result amendment."
        ),
    }
    write_json(path, payload)
    return path


def validate_training_request(
    request: dict[str, Any],
    *,
    request_path: Path,
    profile: str,
    region: str,
) -> None:
    """Run local AWS CLI schema validation without making a service request."""

    request_path.write_text(json.dumps(request), encoding="utf-8")
    try:
        subprocess.run(
            [
                "aws",
                "sagemaker",
                "create-training-job",
                "--generate-cli-skeleton",
                "output",
                "--cli-input-json",
                f"file://{request_path}",
                "--profile",
                profile,
                "--region",
                region,
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details = "\n".join(
            value.strip()
            for value in (exc.stdout or "", exc.stderr or "")
            if value.strip()
        )
        raise ValueError(
            "AWS CLI rejected the frozen SageMaker request schema"
            + (f":\n{details}" if details else "")
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", required=True, choices=tuple(CELL_JOB_CODES))
    parser.add_argument("--config", type=Path, default=DEFAULT_TRANSPORT_CONFIG)
    parser.add_argument("--profile")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    transport_path = args.config.resolve()
    transport = read_transport(transport_path)
    verify_transport_config(transport)
    repository = transport["repository"]
    git_commit = verify_git(repository["branch"])
    freeze_evidence = verify_transport_freeze(transport_path, transport)
    science_path = science_config_path(transport)
    science = read_json(science_path)
    cell_id = args.cell
    _, locks = verify_ltt_locks(
        transport,
        science,
        science_path,
        eligible_cell_id=cell_id,
    )
    lock = locks[cell_id]

    aws_config = transport["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    preflight_aws(transport, science, profile, region)
    verify_first_attempt(
        transport, cell_id=cell_id, profile=profile, region=region
    )
    capacity = preflight_capacity(transport, profile, region)

    job_name = holdout_job_name(cell_id)
    prefix = aws_config["s3_prefix"].strip("/")
    code_key = f"{prefix}/code/{job_name}/source.tar.gz"
    code_uri = f"s3://{aws_config['bucket']}/{code_key}"
    transport_sha256 = sha256_file(transport_path)
    science_sha256 = sha256_file(science_path)
    freeze_sha256 = freeze_evidence["freeze_sha256"]
    science_cells = {cell["cell_id"]: cell for cell in science["cells"]}
    lock_path = repo_path(science_cells[cell_id]["ltt_lock_manifest"])
    lock_sha256 = sha256_file(lock_path)
    selected_policy_sha256 = canonical_json_sha256(lock["selected_policy"])

    with tempfile.TemporaryDirectory(prefix="px057-h4-holdout-") as temp:
        temp_path = Path(temp)
        archive = temp_path / "source.tar.gz"
        build_source_archive(archive, transport)
        archive_sha256 = sha256_file(archive)
        placeholder_source = {
            "version_id": "PREVALIDATION_VERSION_ID",
            "sha256": archive_sha256,
            "size_bytes": archive.stat().st_size,
            "etag": "PREVALIDATION_ETAG",
            "server_side_encryption": "AES256",
        }
        placeholder_request = training_request(
            transport,
            cell_id=cell_id,
            git_commit=git_commit,
            code_uri=code_uri,
            code_version_id=placeholder_source["version_id"],
            code_sha256=placeholder_source["sha256"],
            transport_sha256=transport_sha256,
            science_sha256=science_sha256,
            freeze_sha256=freeze_sha256,
            lock_sha256=lock_sha256,
            selected_policy_sha256=selected_policy_sha256,
        )
        validate_training_request(
            placeholder_request,
            request_path=temp_path / f"{job_name}.prevalidation.json",
            profile=profile,
            region=region,
        )
        if args.dry_run:
            source_object = {
                "version_id": "DRY_RUN_VERSION_ID",
                "sha256": archive_sha256,
                "size_bytes": archive.stat().st_size,
                "etag": "DRY_RUN_ETAG",
                "server_side_encryption": "AES256",
            }
        else:
            source_object = upload_source(
                archive=archive,
                archive_sha256=archive_sha256,
                code_key=code_key,
                bucket=aws_config["bucket"],
                profile=profile,
                region=region,
            )
        request = training_request(
            transport,
            cell_id=cell_id,
            git_commit=git_commit,
            code_uri=code_uri,
            code_version_id=source_object["version_id"],
            code_sha256=source_object["sha256"],
            transport_sha256=transport_sha256,
            science_sha256=science_sha256,
            freeze_sha256=freeze_sha256,
            lock_sha256=lock_sha256,
            selected_policy_sha256=selected_policy_sha256,
        )
        request_path = temp_path / f"{job_name}.json"
        validate_training_request(
            request,
            request_path=request_path,
            profile=profile,
            region=region,
        )
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "dry_run": True,
                        "capacity": capacity,
                        "source_object": source_object,
                        "request": request,
                    },
                    indent=2,
                )
            )
            return
        response = aws_json(
            profile,
            region,
            "sagemaker",
            "create-training-job",
            "--cli-input-json",
            f"file://{request_path}",
        )
        launch_path = write_launch_manifest(
            transport,
            cell_id=cell_id,
            request=request,
            training_job_arn=response["TrainingJobArn"],
            source_object=source_object,
        )
    print(
        json.dumps(
            {
                "status": "SUBMITTED",
                "scientific_result_observed": False,
                "cell_id": cell_id,
                "job_name": job_name,
                "training_job_arn": response["TrainingJobArn"],
                "launch_manifest": launch_path.relative_to(ROOT).as_posix(),
                "source_object": source_object,
                "capacity": capacity,
                "next_required_action": (
                    "Commit and push the launch manifest before protected fetch."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
