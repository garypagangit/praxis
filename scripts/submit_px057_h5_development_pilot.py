#!/usr/bin/env python
"""Submit one outcome-exposed PX-057 H5 development pilot cell."""

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

from scripts.px057_h5_development_contract import (
    ATTEMPT_ID,
    FROZEN_CELL_ID,
    JOB_NAME,
    POLICY_ID,
    PROTOCOL_ID,
    require_c1,
    validate_frozen_development_config,
)
DEFAULT_CONFIG = ROOT / "configs/px057_h5_development_pilot_20260727.json"
COMMITTED_ENTRY = (
    "cloud_jobs/px057_h5_development_pilot_20260727/sagemaker_entry.py"
)
STAGED_ENTRY = "e.py"
QUOTA_CODE = "L-2D6DEB3C"


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws(profile: str, region: str, *args: str) -> str:
    return output(["aws", *args, "--profile", profile, "--region", region])


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def verify_git(branch: str) -> str:
    if output(["git", "status", "--porcelain"]):
        raise ValueError("development-pilot submission requires a clean worktree")
    if output(["git", "branch", "--show-current"]) != branch:
        raise ValueError(f"submission must run from branch {branch}")
    head = output(["git", "rev-parse", "HEAD"])
    remote = output(["git", "ls-remote", "origin", f"refs/heads/{branch}"])
    remote_head = remote.split()[0] if remote else ""
    if remote_head != head:
        raise ValueError("submission commit must be the pushed remote branch head")
    return head


def build_source_archive(path: Path) -> str:
    body = subprocess.check_output(["git", "show", f"HEAD:{COMMITTED_ENTRY}"], cwd=ROOT)
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(STAGED_ENTRY)
        info.size = len(body)
        info.mode = 0o644
        info.mtime = 0
        archive.addfile(info, io.BytesIO(body))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_command() -> str:
    command = (
        "a=/tmp/s;mkdir -p /opt/ml/code&&aws s3api get-object "
        "--bucket \"$B\" --key \"$K\" --version-id \"$V\" $a>/dev/null&&"
        "echo \"$H  $a\"|sha256sum -c -&&tar xzf $a -C /opt/ml/code&&"
        "python /opt/ml/code/e.py"
    )
    if len(command) > 256:
        raise ValueError("development-pilot bootstrap exceeds 256 characters")
    return command


def preflight(config: dict[str, Any], *, profile: str, region: str) -> dict[str, Any]:
    aws_config = config["aws"]
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
        raise ValueError("development-pilot bucket versioning must be Enabled")
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
    quota = json.loads(
        aws(
            profile,
            region,
            "service-quotas",
            "get-service-quota",
            "--service-code",
            "sagemaker",
            "--quota-code",
            QUOTA_CODE,
            "--output",
            "json",
        )
    )
    quota_value = int(float(quota["Quota"]["Value"]))
    active = json.loads(
        aws(
            profile,
            region,
            "sagemaker",
            "list-training-jobs",
            "--status-equals",
            "InProgress",
            "--output",
            "json",
        )
    ).get("TrainingJobSummaries", [])
    active_g5 = 0
    active_names: list[str] = []
    for row in active:
        described = json.loads(
            aws(
                profile,
                region,
                "sagemaker",
                "describe-training-job",
                "--training-job-name",
                row["TrainingJobName"],
                "--output",
                "json",
            )
        )
        if described["ResourceConfig"]["InstanceType"] == aws_config["instance_type"]:
            active_g5 += int(described["ResourceConfig"]["InstanceCount"])
            active_names.append(row["TrainingJobName"])
    if active_g5 + 1 > quota_value:
        raise ValueError(
            f"no {aws_config['instance_type']} capacity: quota={quota_value}, "
            f"active={active_names}"
        )
    return {"quota_value": quota_value, "active_g5": active_g5, "active": active_names}


def job_name(cell: dict[str, Any]) -> str:
    require_c1(str(cell["cell_id"]))
    return JOB_NAME


def ensure_first_attempt(
    *, profile: str, region: str, name: str, launch_path: Path
) -> None:
    if launch_path.exists():
        raise FileExistsError(f"launch is already registered: {launch_path}")
    listing = json.loads(
        aws(
            profile,
            region,
            "sagemaker",
            "list-training-jobs",
            "--name-contains",
            name,
            "--output",
            "json",
        )
    )
    exact = [
        row["TrainingJobName"]
        for row in listing.get("TrainingJobSummaries", [])
        if row["TrainingJobName"] == name
    ]
    if exact:
        raise ValueError(f"development-pilot attempt already exists: {exact}")


def upload_source(
    *,
    archive: Path,
    digest: str,
    bucket: str,
    key: str,
    profile: str,
    region: str,
) -> str:
    uri = f"s3://{bucket}/{key}"
    subprocess.run(
        [
            "aws",
            "s3",
            "cp",
            str(archive),
            uri,
            "--profile",
            profile,
            "--region",
            region,
            "--only-show-errors",
            "--sse",
            "AES256",
            "--metadata",
            f"sha256={digest}",
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
            key,
            "--output",
            "json",
        )
    )
    if (
        not head.get("VersionId")
        or str(head["VersionId"]).casefold() == "null"
    ):
        raise ValueError("source upload returned no S3 VersionId")
    if head.get("ServerSideEncryption") != "AES256":
        raise ValueError("source upload did not confirm AES256")
    if head.get("Metadata", {}).get("sha256") != digest:
        raise ValueError("source metadata hash mismatch")
    return str(head["VersionId"])


def training_request(
    config: dict[str, Any],
    *,
    cell: dict[str, Any],
    name: str,
    commit: str,
    source_key: str,
    source_version: str,
    source_sha256: str,
) -> dict[str, Any]:
    aws_config = config["aws"]
    branch = config["repository"]["branch"]
    source_uri = f"s3://{aws_config['bucket']}/{source_key}"
    return {
        "TrainingJobName": name,
        "RoleArn": aws_config["role_arn"],
        "AlgorithmSpecification": {
            "TrainingImage": aws_config["container_image"],
            "TrainingInputMode": "File",
            "ContainerEntrypoint": ["bash", "-lc"],
            "ContainerArguments": [source_command()],
        },
        "InputDataConfig": [
            {
                "ChannelName": "code",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": source_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "InputMode": "File",
            }
        ],
        "OutputDataConfig": {
            "S3OutputPath": (
                f"s3://{aws_config['bucket']}/{aws_config['s3_prefix'].strip('/')}"
                "/sagemaker-output"
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
            "PX057_H5_DEV_REPOSITORY_URL": config["repository"]["url"],
            "PX057_H5_DEV_BRANCH": branch,
            "PX057_H5_DEV_GIT_COMMIT": commit,
            "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST": aws_config["container_image"].rsplit("@", 1)[1],
            "PX057_H5_DEV_HF_SECRET_ID": aws_config["huggingface_secret_id"],
            "PX057_H5_DEV_AWS_REGION": aws_config["region"],
            "PX057_H5_DEV_JOB_NAME": name,
            "PX057_H5_DEV_CELL_ID": cell["cell_id"],
            "PX057_H5_DEV_ATTEMPT_ID": ATTEMPT_ID,
            "PX057_H5_DEV_PROTOCOL_ID": PROTOCOL_ID,
            "PX057_H5_DEV_FROZEN_CELL_ID": FROZEN_CELL_ID,
            "PX057_H5_DEV_POLICY_ID": POLICY_ID,
            "PX057_H5_DEV_SOURCE_ARCHIVE_SHA256": source_sha256,
            "PX057_H5_DEV_SOURCE_VERSION_ID": source_version,
            "PX057_H5_DEV_CONFIG_SHA256": hashlib.sha256(
                (ROOT / "configs/px057_h5_development_pilot_20260727.json").read_bytes()
            ).hexdigest(),
            "B": aws_config["bucket"],
            "K": source_key,
            "V": source_version,
            "H": source_sha256,
        },
        "EnableNetworkIsolation": False,
        "Tags": [
            {"Key": "Project", "Value": "PraxisResearch"},
            {"Key": "PraxisId", "Value": "PX-057"},
            {"Key": "Gate", "Value": "H5-Development-Pilot"},
            {"Key": "Cell", "Value": cell["cell_id"]},
            {"Key": "Attempt", "Value": ATTEMPT_ID},
            {"Key": "Policy", "Value": POLICY_ID},
            {"Key": "Confirmatory", "Value": "false"},
            {"Key": "GitCommit", "Value": commit[:40]},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    parser.add_argument("--cell", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    if config_path.resolve() != DEFAULT_CONFIG.resolve():
        raise ValueError("development-pilot submission requires the committed default config")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_frozen_development_config(config)
    require_c1(args.cell)
    if config.get("status") != "DEVELOPMENT_ONLY_NOT_CONFIRMATORY":
        raise ValueError("refusing to submit without the development-only boundary")
    matching = [cell for cell in config["cells"] if cell["cell_id"] == args.cell]
    if len(matching) != 1:
        raise ValueError(f"unknown or duplicate cell: {args.cell}")
    cell = matching[0]
    aws_config = config["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    commit = verify_git(config["repository"]["branch"])
    capacity = preflight(config, profile=profile, region=region)
    name = job_name(cell)
    launch_path = (
        ROOT
        / "manifests/px057_h5_development_pilot_20260727/launches"
        / f"{cell['cell_id']}_r2.json"
    )
    ensure_first_attempt(
        profile=profile, region=region, name=name, launch_path=launch_path
    )

    with tempfile.TemporaryDirectory(prefix="px057-h5-dev-") as temp:
        archive = Path(temp) / "source.tar.gz"
        source_sha256 = build_source_archive(archive)
        prefix = aws_config["s3_prefix"].strip("/")
        source_key = f"{prefix}/code/{name}/source.tar.gz"
        source_version = (
            "DRY_RUN_VERSION"
            if args.dry_run
            else upload_source(
                archive=archive,
                digest=source_sha256,
                bucket=aws_config["bucket"],
                key=source_key,
                profile=profile,
                region=region,
            )
        )
        request = training_request(
            config,
            cell=cell,
            name=name,
            commit=commit,
            source_key=source_key,
            source_version=source_version,
            source_sha256=source_sha256,
        )
        request_path = Path(temp) / "request.json"
        request_path.write_bytes(canonical_bytes(request))
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
        if args.dry_run:
            print(json.dumps({"dry_run": True, "capacity": capacity, "request": request}, indent=2))
            return
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

    launch = {
        "experiment_id": config["experiment_id"],
        "stage": "H5_DEVELOPMENT_PILOT_LAUNCH",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell["cell_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "job_name": name,
        "training_job_arn": response["TrainingJobArn"],
        "git_commit": commit,
        "source": {
            "bucket": aws_config["bucket"],
            "key": source_key,
            "version_id": source_version,
            "sha256": source_sha256,
        },
        "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
        "submitted_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    launch_path.parent.mkdir(parents=True, exist_ok=True)
    launch_path.write_bytes(canonical_bytes(launch))
    print(json.dumps({"capacity": capacity, "launch": launch}, indent=2))


if __name__ == "__main__":
    main()
