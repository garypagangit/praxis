#!/usr/bin/env python
"""Submit all PX-057 H4 calibration cells as parallel SageMaker jobs."""

from __future__ import annotations

import argparse
import datetime as dt
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

from scripts.px057_h4_common import verify_phase_a_freeze, write_json


DEFAULT_CONFIG = ROOT / "configs/px057_h4_ltt_transfer_20260725.json"
ENTRY = "cloud_jobs/px057_h4_calibration_20260725/sagemaker_entry.py"
PHASE_A_ENTRY = "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"
CALIBRATION_MAX_RUNTIME_SECONDS = 86_400
SAGEMAKER_G5_2XL_QUOTA_CODE = "L-2D6DEB3C"
CELL_JOB_CODES = {
    "cell1_llama31_gsm8k": "c1",
    "cell2_qwen25_arc": "c2",
    "cell3_llama31_arc": "c3",
}


def command_output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws(profile: str, region: str, *args: str) -> str:
    return command_output(["aws", *args, "--profile", profile, "--region", region])


def read_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_transport_config(config: dict[str, Any]) -> None:
    transport = config["calibration_transport"]
    if (
        int(transport["max_runtime_seconds"])
        != CALIBRATION_MAX_RUNTIME_SECONDS
        or transport["sagemaker_quota_code"]
        != SAGEMAKER_G5_2XL_QUOTA_CODE
        or transport["first_attempt_only"] is not True
        or transport["source_bootstrap"]
        != "explicit_s3_version_and_sha256_before_extraction"
    ):
        raise ValueError("calibration transport differs from the frozen protocol")


def verify_git(branch: str) -> str:
    if command_output(["git", "status", "--porcelain"]):
        raise ValueError("submission requires a clean worktree")
    head = command_output(["git", "rev-parse", "HEAD"])
    current_branch = command_output(["git", "branch", "--show-current"])
    if current_branch != branch:
        raise ValueError(f"expected branch {branch}, found {current_branch}")
    remote_line = command_output(["git", "ls-remote", "origin", f"refs/heads/{branch}"])
    remote_head = remote_line.split()[0] if remote_line else ""
    if remote_head != head:
        raise ValueError("local HEAD is not the pushed branch HEAD")
    return head


def preflight_aws(config: dict[str, Any], profile: str, region: str) -> None:
    aws_config = config["phase_a"]["aws"]
    image_tag = aws_config["container_image_tag_uri"].rsplit("/", 1)[1]
    repository, tag = image_tag.rsplit(":", 1)
    registry_id = aws_config["container_image_tag_uri"].split(".", 1)[0]
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
        f"imageTag={tag}",
        "--query",
        "images[0].imageId.imageDigest",
        "--output",
        "text",
    )
    if observed_digest != aws_config["container_image_digest"]:
        raise ValueError("resolved ECR digest differs from the frozen config")
    versioning = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "get-bucket-versioning",
            "--bucket",
            aws_config["bucket"],
            "--output",
            "json",
        )
        or "{}"
    )
    if versioning.get("Status") != "Enabled":
        raise ValueError("H4 bucket versioning must be Enabled before submission")
    aws(
        profile,
        region,
        "secretsmanager",
        "describe-secret",
        "--secret-id",
        aws_config["huggingface_secret_id"],
        "--output",
        "json",
    )
    aws(
        profile,
        region,
        "iam",
        "get-role",
        "--role-name",
        aws_config["role_arn"].rsplit("/", 1)[1],
        "--output",
        "json",
    )


def preflight_capacity(
    config: dict[str, Any], profile: str, region: str, requested_jobs: int
) -> dict[str, Any]:
    aws_config = config["phase_a"]["aws"]
    quota = json.loads(
        aws(
            profile,
            region,
            "service-quotas",
            "get-service-quota",
            "--service-code",
            "sagemaker",
            "--quota-code",
            SAGEMAKER_G5_2XL_QUOTA_CODE,
            "--output",
            "json",
        )
    )
    quota_value = int(float(quota["Quota"]["Value"]))
    active: list[dict[str, Any]] = []
    for status in ("InProgress", "Stopping"):
        listing = json.loads(
            aws(
                profile,
                region,
                "sagemaker",
                "list-training-jobs",
                "--status-equals",
                status,
                "--output",
                "json",
            )
        )
        for summary in listing.get("TrainingJobSummaries", []):
            description = json.loads(
                aws(
                    profile,
                    region,
                    "sagemaker",
                    "describe-training-job",
                    "--training-job-name",
                    summary["TrainingJobName"],
                    "--output",
                    "json",
                )
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
    if active_instances + requested_jobs > quota_value:
        raise ValueError(
            f"SageMaker {aws_config['instance_type']} capacity is {quota_value}; "
            f"{active_instances} instance(s) are active and {requested_jobs} were requested"
        )
    return {
        "quota_code": SAGEMAKER_G5_2XL_QUOTA_CODE,
        "quota_value": quota_value,
        "active_instances": active_instances,
        "active_jobs": active,
        "requested_jobs": requested_jobs,
    }


def verify_first_attempt(
    *, profile: str, region: str, cell_id: str, launch_manifest: Path
) -> None:
    if launch_manifest.exists():
        raise FileExistsError(f"calibration launch is already registered: {launch_manifest}")
    name_prefix = f"px057-h4-cal-{CELL_JOB_CODES[cell_id]}-"
    listing = json.loads(
        aws(
            profile,
            region,
            "sagemaker",
            "list-training-jobs",
            "--name-contains",
            name_prefix,
            "--output",
            "json",
        )
    )
    prior = [
        row["TrainingJobName"] for row in listing.get("TrainingJobSummaries", [])
    ]
    if prior:
        raise ValueError(
            f"{cell_id}: a calibration attempt already exists and rerun is forbidden: {prior}"
        )


def source_launch_command() -> str:
    archive = "/tmp/px057-h4-source.tar.gz"
    return (
        "set -euo pipefail && "
        "mkdir -p /opt/ml/code && "
        "aws s3api get-object "
        "--bucket \"$PX057_H4_SOURCE_BUCKET\" "
        "--key \"$PX057_H4_SOURCE_KEY\" "
        "--version-id \"$PX057_H4_SOURCE_VERSION_ID\" "
        f"--region \"$AWS_REGION\" {archive} >/dev/null && "
        f"printf '%s  %s\\n' \"$PX057_H4_SOURCE_SHA256\" {archive} "
        "| sha256sum -c - && "
        f"tar -xzf {archive} -C /opt/ml/code && "
        f"python /opt/ml/code/{ENTRY}"
    )


def training_request(
    config: dict[str, Any],
    *,
    job_name: str,
    cell_id: str,
    code_uri: str,
    code_version_id: str,
    code_sha256: str,
    git_commit: str,
) -> dict[str, Any]:
    aws_config = config["phase_a"]["aws"]
    prefix = aws_config["s3_prefix"].strip("/")
    result_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/calibration/{cell_id}/{job_name}"
    )
    launch = source_launch_command()
    return {
        "TrainingJobName": job_name,
        "RoleArn": aws_config["role_arn"],
        "AlgorithmSpecification": {
            "TrainingImage": aws_config["container_image_pinned_uri"],
            "TrainingInputMode": "File",
            "ContainerEntrypoint": ["bash", "-lc"],
            "ContainerArguments": [launch],
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
            "S3OutputPath": f"s3://{aws_config['bucket']}/{prefix}/sagemaker-output"
        },
        "ResourceConfig": {
            "InstanceType": aws_config["instance_type"],
            "InstanceCount": 1,
            "VolumeSizeInGB": int(aws_config["volume_size_gb"]),
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": CALIBRATION_MAX_RUNTIME_SECONDS,
        },
        "Environment": {
            "AWS_REGION": aws_config["region"],
            "HF_HOME": "/opt/ml/input/data/huggingface",
            "TOKENIZERS_PARALLELISM": "false",
            "PX057_H4_REPOSITORY_URL": aws_config["repository_url"],
            "PX057_H4_BRANCH": aws_config["branch"],
            "PX057_H4_GIT_COMMIT": git_commit,
            "PX057_CONTAINER_IMAGE_DIGEST": aws_config["container_image_digest"],
            "PX057_H4_HF_SECRET_ID": aws_config["huggingface_secret_id"],
            "PX057_H4_RESULT_S3_URI": result_uri,
            "PX057_H4_JOB_NAME": job_name,
            "PX057_H4_SOURCE_VERSION_ID": code_version_id,
            "PX057_H4_SOURCE_SHA256": code_sha256,
            "PX057_H4_SOURCE_BUCKET": aws_config["bucket"],
            "PX057_H4_SOURCE_KEY": code_uri.split(f"s3://{aws_config['bucket']}/", 1)[1],
            "PX057_H4_CELL_ID": cell_id,
        },
        "EnableNetworkIsolation": False,
        "Tags": [
            {"Key": "Project", "Value": "PraxisResearch"},
            {"Key": "PraxisId", "Value": "PX-057"},
            {"Key": "Gate", "Value": "H4-Calibration"},
            {"Key": "Cell", "Value": cell_id},
            {"Key": "GitCommit", "Value": git_commit[:40]},
        ],
    }


def upload_source(
    *,
    archive: Path,
    archive_sha256: str,
    code_uri: str,
    code_key: str,
    bucket: str,
    profile: str,
    region: str,
) -> str:
    subprocess.run(
        [
            "aws",
            "s3",
            "cp",
            str(archive),
            code_uri,
            "--profile",
            profile,
            "--region",
            region,
            "--only-show-errors",
            "--sse",
            "AES256",
            "--metadata",
            f"sha256={archive_sha256}",
        ],
        cwd=ROOT,
        check=True,
    )
    head = json.loads(
        aws(
            profile,
            region,
            "s3api",
            "head-object",
            "--bucket",
            bucket,
            "--key",
            code_key,
            "--output",
            "json",
        )
    )
    if not head.get("VersionId"):
        raise ValueError("versioned calibration source upload returned no VersionId")
    if head.get("ServerSideEncryption") != "AES256":
        raise ValueError("calibration source upload did not confirm AES256")
    if head.get("Metadata", {}).get("sha256") != archive_sha256:
        raise ValueError("calibration source object metadata hash mismatch")
    return str(head["VersionId"])


def build_source_archive(path: Path) -> None:
    """Archive exact Git blob bytes, independent of Windows checkout EOLs."""

    with tarfile.open(path, "w:gz") as handle:
        for relative in (ENTRY, PHASE_A_ENTRY):
            body = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
            metadata = tarfile.TarInfo(relative)
            metadata.size = len(body)
            metadata.mode = 0o644
            metadata.mtime = 0
            handle.addfile(metadata, io.BytesIO(body))


def write_launch_manifests(
    config: dict[str, Any], records: list[dict[str, Any]], requests: list[dict[str, Any]]
) -> None:
    requests_by_job = {request["TrainingJobName"]: request for request in requests}
    cells = {cell["cell_id"]: cell for cell in config["cells"]}
    for record in records:
        request = requests_by_job[record["job_name"]]
        path = ROOT / cells[record["cell_id"]]["calibration_launch_manifest"]
        if path.exists():
            raise FileExistsError(f"refusing to replace launch manifest: {path}")
        payload = {
            "experiment_id": config["experiment_id"],
            "stage": "H4_calibration_launch_registration",
            "status": "REGISTERED_PRE_RESULT",
            "scientific_result_observed": False,
            "cell_id": record["cell_id"],
            "job_name": record["job_name"],
            "training_job_arn": record["training_job_arn"],
            "git_commit": record["git_commit"],
            "container_image": record["container_image"],
            "code_uri": record["code_uri"],
            "code_version_id": record["code_version_id"],
            "code_sha256": record["code_sha256"],
            "calibration_result_uri": record["calibration_result_uri"],
            "max_runtime_seconds": record["max_runtime_seconds"],
            "request_sha256": hashlib.sha256(
                (json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode(
                    "utf-8"
                )
            ).hexdigest(),
            "registered_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rule": (
                "This is the sole registered calibration attempt for this cell. "
                "A retry requires a new experiment identifier or formal pre-result amendment."
            ),
        }
        write_json(path, payload)
        record["launch_manifest"] = path.relative_to(ROOT).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    parser.add_argument(
        "--cell",
        action="append",
        choices=tuple(CELL_JOB_CODES),
        help="repeat to submit a subset; defaults to all three cells",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = read_config(config_path)
    verify_transport_config(config)
    aws_config = config["phase_a"]["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    git_commit = verify_git(aws_config["branch"])
    verify_phase_a_freeze(ROOT, config_path, config, require_current_runtime=False)
    preflight_aws(config, profile, region)

    configured_cells = [cell["cell_id"] for cell in config["cells"]]
    if set(configured_cells) != set(CELL_JOB_CODES):
        raise ValueError("frozen cell set differs from the calibration launcher")
    cells = list(dict.fromkeys(args.cell or configured_cells))
    cells_by_id = {cell["cell_id"]: cell for cell in config["cells"]}
    for cell_id in cells:
        verify_first_attempt(
            profile=profile,
            region=region,
            cell_id=cell_id,
            launch_manifest=ROOT / cells_by_id[cell_id]["calibration_launch_manifest"],
        )
    capacity = preflight_capacity(config, profile, region, len(cells))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    prefix = aws_config["s3_prefix"].strip("/")

    with tempfile.TemporaryDirectory(prefix="px057-h4-calibration-") as temp:
        temp_path = Path(temp)
        archive = temp_path / "source.tar.gz"
        build_source_archive(archive)
        archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
        requests: list[dict[str, Any]] = []
        launch_records: list[dict[str, Any]] = []
        for cell_id in cells:
            job_name = f"px057-h4-cal-{CELL_JOB_CODES[cell_id]}-{stamp}"
            code_key = f"{prefix}/code/{job_name}/source.tar.gz"
            code_uri = f"s3://{aws_config['bucket']}/{code_key}"
            if args.dry_run:
                code_version_id = "DRY_RUN_VERSION_ID"
            else:
                code_version_id = upload_source(
                    archive=archive,
                    archive_sha256=archive_sha256,
                    code_uri=code_uri,
                    code_key=code_key,
                    bucket=aws_config["bucket"],
                    profile=profile,
                    region=region,
                )
            request = training_request(
                config,
                job_name=job_name,
                cell_id=cell_id,
                code_uri=code_uri,
                code_version_id=code_version_id,
                code_sha256=archive_sha256,
                git_commit=git_commit,
            )
            request_path = temp_path / f"{job_name}.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
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
            requests.append(request)
            launch_records.append(
                {
                    "job_name": job_name,
                    "cell_id": cell_id,
                    "git_commit": git_commit,
                    "container_image": aws_config["container_image_pinned_uri"],
                    "code_uri": code_uri,
                    "code_version_id": code_version_id,
                    "code_sha256": archive_sha256,
                    "calibration_result_uri": request["Environment"][
                        "PX057_H4_RESULT_S3_URI"
                    ],
                    "max_runtime_seconds": CALIBRATION_MAX_RUNTIME_SECONDS,
                }
            )
        if args.dry_run:
            print(json.dumps({"dry_run": True, "requests": requests}, indent=2))
            return

        started: list[dict[str, Any]] = []
        try:
            for request, record in zip(requests, launch_records):
                request_path = temp_path / f"{record['job_name']}.json"
                response = json.loads(
                    aws(
                        profile,
                        region,
                        "sagemaker",
                        "create-training-job",
                        "--cli-input-json",
                        f"file://{request_path}",
                        "--output",
                        "json",
                    )
                )
                record["training_job_arn"] = response["TrainingJobArn"]
                started.append(record)
        except Exception:
            write_launch_manifests(config, started, requests)
            print(json.dumps({"started_before_error": started}, indent=2), file=sys.stderr)
            raise
        write_launch_manifests(config, started, requests)
    print(json.dumps({"capacity": capacity, "submitted": started}, indent=2))


if __name__ == "__main__":
    main()
