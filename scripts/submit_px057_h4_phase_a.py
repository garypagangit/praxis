#!/usr/bin/env python
"""Submit the PX-057 H4 Phase A runtime-capture job through AWS CLI."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/px057_h4_ltt_transfer_20260725.json"
ENTRY = "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"


def source_launch_command() -> str:
    command = (
        "a=/tmp/s;mkdir -p /opt/ml/code&&aws s3api get-object "
        "--bucket \"$B\" --key \"$K\" --version-id \"$V\" $a>/dev/null&&"
        "echo \"$H  $a\"|sha256sum -c -&&tar xzf $a -C /opt/ml/code&&"
        f"python /opt/ml/code/{ENTRY}"
    )
    if len(command) > 256:
        raise ValueError("Phase A bootstrap exceeds SageMaker's 256-char limit")
    return command


def command_output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws(profile: str, region: str, *args: str) -> str:
    return command_output(["aws", *args, "--profile", profile, "--region", region])


def read_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_git(branch: str) -> str:
    if command_output(["git", "status", "--porcelain"]):
        raise ValueError("submission requires a clean worktree")
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


def training_request(
    config: dict[str, Any], *, job_name: str, code_uri: str, git_commit: str
) -> dict[str, Any]:
    aws_config = config["phase_a"]["aws"]
    prefix = aws_config["s3_prefix"].strip("/")
    result_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/phase-a-runtime/{job_name}"
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
            "S3OutputPath": (
                f"s3://{aws_config['bucket']}/{prefix}/sagemaker-output"
            )
        },
        "ResourceConfig": {
            "InstanceType": aws_config["instance_type"],
            "InstanceCount": 1,
            "VolumeSizeInGB": int(aws_config["volume_size_gb"]),
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": int(aws_config["max_runtime_seconds"])
        },
        "Environment": {
            "AWS_REGION": aws_config["region"],
            "AWS_DEFAULT_REGION": aws_config["region"],
            "HF_HOME": "/opt/ml/input/data/huggingface",
            "TOKENIZERS_PARALLELISM": "false",
            "PX057_H4_REPOSITORY_URL": aws_config["repository_url"],
            "PX057_H4_BRANCH": aws_config["branch"],
            "PX057_H4_GIT_COMMIT": git_commit,
            "PX057_CONTAINER_IMAGE_DIGEST": aws_config[
                "container_image_digest"
            ],
            "PX057_H4_HF_SECRET_ID": aws_config["huggingface_secret_id"],
            "PX057_H4_RESULT_S3_URI": result_uri,
            "PX057_H4_JOB_NAME": job_name,
            "PX057_H4_SOURCE_BUCKET": aws_config["bucket"],
            "PX057_H4_SOURCE_KEY": code_uri.split(
                f"s3://{aws_config['bucket']}/", 1
            )[1],
            "B": aws_config["bucket"],
            "K": code_uri.split(f"s3://{aws_config['bucket']}/", 1)[1],
        },
        "EnableNetworkIsolation": False,
        "Tags": [
            {"Key": "Project", "Value": "PraxisResearch"},
            {"Key": "PraxisId", "Value": "PX-057"},
            {"Key": "Gate", "Value": "H4-Phase-A"},
            {"Key": "GitCommit", "Value": git_commit[:40]},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = read_config(config_path)
    aws_config = config["phase_a"]["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    git_commit = verify_git(aws_config["branch"])

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

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    job_name = f"px057-h4-phase-a-{stamp}"
    prefix = aws_config["s3_prefix"].strip("/")
    code_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/code/{job_name}/source.tar.gz"
    )
    code_key = f"{prefix}/code/{job_name}/source.tar.gz"
    request = training_request(
        config, job_name=job_name, code_uri=code_uri, git_commit=git_commit
    )
    if args.dry_run:
        print(json.dumps({"code_uri": code_uri, "request": request}, indent=2))
        return

    with tempfile.TemporaryDirectory(prefix="px057-h4-phase-a-") as temp:
        temp_path = Path(temp)
        archive = temp_path / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as handle:
            body = subprocess.check_output(
                ["git", "show", f"HEAD:{ENTRY}"], cwd=ROOT
            )
            metadata = tarfile.TarInfo(ENTRY)
            metadata.size = len(body)
            metadata.mode = 0o644
            metadata.mtime = 0
            handle.addfile(metadata, io.BytesIO(body))
        archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
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
            check=True,
        )
        code_head = json.loads(
            aws(
                profile,
                region,
                "s3api",
                "head-object",
                "--bucket",
                aws_config["bucket"],
                "--key",
                code_key,
                "--output",
                "json",
            )
        )
        if not code_head.get("VersionId"):
            raise ValueError("versioned source upload returned no VersionId")
        request["Environment"].update(
            {
                "PX057_H4_SOURCE_VERSION_ID": code_head["VersionId"],
                "PX057_H4_SOURCE_SHA256": archive_sha256,
                "V": code_head["VersionId"],
                "H": archive_sha256,
            }
        )
        request_path = temp_path / "create-training-job.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
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
    print(
        json.dumps(
            {
                "job_name": job_name,
                "training_job_arn": response["TrainingJobArn"],
                "git_commit": git_commit,
                "container_image": aws_config["container_image_pinned_uri"],
                "code_uri": code_uri,
                "code_version_id": code_head["VersionId"],
                "code_sha256": archive_sha256,
                "runtime_result_uri": request["Environment"][
                    "PX057_H4_RESULT_S3_URI"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
