#!/usr/bin/env python
"""Fetch and bind a completed PX-057 H4 Phase A SageMaker capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.submit_px057_h4_phase_a import source_launch_command

DEFAULT_CONFIG = ROOT / "configs/px057_h4_ltt_transfer_20260725.json"
ENTRY = "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws_json(profile: str, region: str, *args: str) -> Any:
    raw = output(
        ["aws", *args, "--profile", profile, "--region", region, "--output", "json"]
    )
    return json.loads(raw) if raw else {}


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.strip("/"):
        raise ValueError(f"invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path.strip("/")


def download_versioned(
    *,
    profile: str,
    region: str,
    uri: str,
    destination: Path,
    expected_version_id: str | None = None,
) -> dict[str, Any]:
    bucket, key = parse_s3_uri(uri)
    head_args = ["s3api", "head-object", "--bucket", bucket, "--key", key]
    if expected_version_id is not None:
        head_args.extend(["--version-id", expected_version_id])
    head = aws_json(profile, region, *head_args)
    version_id = head.get("VersionId")
    if not version_id:
        raise ValueError(f"{uri}: no immutable VersionId")
    if expected_version_id is not None and version_id != expected_version_id:
        raise ValueError(f"{uri}: object VersionId differs from the frozen request")
    subprocess.run(
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
            str(destination),
            "--profile",
            profile,
            "--region",
            region,
            "--output",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    recorded = head.get("Metadata", {}).get("sha256")
    if recorded and recorded != digest:
        raise ValueError(f"{uri}: downloaded SHA-256 differs from object metadata")
    return {
        "uri": uri,
        "bucket": bucket,
        "key": key,
        "version_id": version_id,
        "sha256": digest,
        "content_length": int(head["ContentLength"]),
        "etag": str(head["ETag"]).strip('"'),
        "server_side_encryption": head.get("ServerSideEncryption"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    phase = config["phase_a"]
    aws_config = phase["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    description = aws_json(
        profile,
        region,
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        args.job_name,
    )
    if description["TrainingJobStatus"] != "Completed":
        raise ValueError(
            f"{args.job_name}: expected Completed, found "
            f"{description['TrainingJobStatus']}"
        )
    environment = description["Environment"]
    current_head = output(["git", "rev-parse", "HEAD"])
    capture_commit = environment["PX057_H4_GIT_COMMIT"]
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", capture_commit, current_head],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("cloud capture commit is not an ancestor of current HEAD")
    prefix = aws_config["s3_prefix"].strip("/")
    expected_result_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/phase-a-runtime/{args.job_name}"
    )
    expected_code_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/code/{args.job_name}/source.tar.gz"
    )
    expected_output_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/sagemaker-output"
    )
    expected_launch = source_launch_command()
    source_data = description["InputDataConfig"][0]["DataSource"][
        "S3DataSource"
    ]
    expected_environment = {
        "AWS_REGION": region,
        "AWS_DEFAULT_REGION": region,
        "HF_HOME": "/opt/ml/input/data/huggingface",
        "TOKENIZERS_PARALLELISM": "false",
        "PX057_H4_REPOSITORY_URL": aws_config["repository_url"],
        "PX057_H4_BRANCH": aws_config["branch"],
        "PX057_H4_GIT_COMMIT": capture_commit,
        "PX057_CONTAINER_IMAGE_DIGEST": aws_config[
            "container_image_digest"
        ],
        "PX057_H4_HF_SECRET_ID": aws_config["huggingface_secret_id"],
        "PX057_H4_RESULT_S3_URI": expected_result_uri,
        "PX057_H4_JOB_NAME": args.job_name,
        "PX057_H4_SOURCE_VERSION_ID": environment.get(
            "PX057_H4_SOURCE_VERSION_ID"
        ),
        "PX057_H4_SOURCE_SHA256": environment.get("PX057_H4_SOURCE_SHA256"),
        "PX057_H4_SOURCE_BUCKET": aws_config["bucket"],
        "PX057_H4_SOURCE_KEY": f"{prefix}/code/{args.job_name}/source.tar.gz",
        "B": aws_config["bucket"],
        "K": f"{prefix}/code/{args.job_name}/source.tar.gz",
        "V": environment.get("PX057_H4_SOURCE_VERSION_ID"),
        "H": environment.get("PX057_H4_SOURCE_SHA256"),
    }
    algorithm = description["AlgorithmSpecification"]
    resource = description["ResourceConfig"]
    if (
        description["TrainingJobName"] != args.job_name
        or description["RoleArn"] != aws_config["role_arn"]
        or algorithm["TrainingImage"]
        != aws_config["container_image_pinned_uri"]
        or algorithm["TrainingInputMode"] != "File"
        or algorithm.get("ContainerEntrypoint") != ["bash", "-lc"]
        or algorithm.get("ContainerArguments") != [expected_launch]
        or environment != expected_environment
        or description.get("EnableNetworkIsolation") is not False
        or len(description["InputDataConfig"]) != 1
        or description["InputDataConfig"][0]["ChannelName"] != "code"
        or description["InputDataConfig"][0]["InputMode"] != "File"
        or source_data["S3DataType"] != "S3Prefix"
        or source_data["S3Uri"] != expected_code_uri
        or source_data["S3DataDistributionType"] != "FullyReplicated"
        or description["OutputDataConfig"]["S3OutputPath"]
        != expected_output_uri
        or resource["InstanceType"] != aws_config["instance_type"]
        or int(resource["InstanceCount"]) != 1
        or int(resource["VolumeSizeInGB"])
        != int(aws_config["volume_size_gb"])
        or int(description["StoppingCondition"]["MaxRuntimeInSeconds"])
        != int(aws_config["max_runtime_seconds"])
        or not environment["PX057_H4_SOURCE_VERSION_ID"]
        or len(environment["PX057_H4_SOURCE_SHA256"]) != 64
    ):
        raise ValueError("cloud job identity differs from the current frozen branch")

    result_uri = environment["PX057_H4_RESULT_S3_URI"].rstrip("/")
    with tempfile.TemporaryDirectory(prefix="px057-h4-phase-a-fetch-") as temp:
        temp_path = Path(temp)
        runtime_temp = temp_path / "runtime_environment.json"
        evidence_temp = temp_path / "cloud_job_evidence.json"
        source_temp = temp_path / "source.tar.gz"
        model_temp = temp_path / "model.tar.gz"
        runtime_object = download_versioned(
            profile=profile,
            region=region,
            uri=f"{result_uri}/runtime_environment.json",
            destination=runtime_temp,
        )
        evidence_object = download_versioned(
            profile=profile,
            region=region,
            uri=f"{result_uri}/cloud_job_evidence.json",
            destination=evidence_temp,
        )
        source_object = download_versioned(
            profile=profile,
            region=region,
            uri=expected_code_uri,
            destination=source_temp,
            expected_version_id=environment["PX057_H4_SOURCE_VERSION_ID"],
        )
        runtime = json.loads(runtime_temp.read_text(encoding="utf-8"))
        evidence = json.loads(evidence_temp.read_text(encoding="utf-8"))
        if (
            runtime.get("status") != "PASS"
            or runtime.get("scientific_data_generated") is not False
            or runtime.get("config_sha256")
            != hashlib.sha256(args.config.read_bytes()).hexdigest()
            or evidence.get("status") != "PASS"
            or evidence.get("scientific_data_generated") is not False
            or evidence.get("git_commit") != environment["PX057_H4_GIT_COMMIT"]
            or evidence.get("runtime_sha256") != runtime_object["sha256"]
            or evidence.get("runtime_s3", {}).get("version_id")
            != runtime_object["version_id"]
            or evidence.get("job_name") != args.job_name
            or evidence.get("repository_url") != aws_config["repository_url"]
            or evidence.get("branch") != aws_config["branch"]
            or evidence.get("container_image_digest")
            != aws_config["container_image_digest"]
            or evidence.get("source_version_id") != source_object["version_id"]
            or evidence.get("source_sha256") != source_object["sha256"]
            or evidence.get("entrypoint_sha256")
            != hashlib.sha256(
                (
                    ROOT
                    / ENTRY
                ).read_bytes()
            ).hexdigest()
        ):
            raise ValueError("downloaded Phase A evidence failed identity checks")

        runtime_target = ROOT / phase["runtime_manifest"]
        cloud_target = ROOT / phase["cloud_job_manifest"]
        if runtime_target.exists() or cloud_target.exists():
            raise FileExistsError("Phase A evidence targets already exist")

        model_uri = description["ModelArtifacts"]["S3ModelArtifacts"]
        model_object = download_versioned(
            profile=profile,
            region=region,
            uri=model_uri,
            destination=model_temp,
        )
        cloud_manifest = {
            "experiment_id": config["experiment_id"],
            "stage": "H4_phase_a_cloud_job_manifest",
            "status": "PASS",
            "scientific_data_generated": False,
            "job_name": args.job_name,
            "job_arn": description["TrainingJobArn"],
            "job_status": description["TrainingJobStatus"],
            "creation_time": description["CreationTime"],
            "training_start_time": description["TrainingStartTime"],
            "training_end_time": description["TrainingEndTime"],
            "billable_seconds": description.get("BillableTimeInSeconds"),
            "git_commit": environment["PX057_H4_GIT_COMMIT"],
            "role_arn": description["RoleArn"],
            "repository_url": environment["PX057_H4_REPOSITORY_URL"],
            "branch": environment["PX057_H4_BRANCH"],
            "huggingface_secret_id": environment[
                "PX057_H4_HF_SECRET_ID"
            ],
            "runtime_result_uri": result_uri,
            "output_s3_path": description["OutputDataConfig"][
                "S3OutputPath"
            ],
            "max_runtime_seconds": int(
                description["StoppingCondition"]["MaxRuntimeInSeconds"]
            ),
            "network_isolation": description["EnableNetworkIsolation"],
            "entrypoint_sha256": evidence["entrypoint_sha256"],
            "container_image_tag_uri": aws_config["container_image_tag_uri"],
            "container_image_digest": environment[
                "PX057_CONTAINER_IMAGE_DIGEST"
            ],
            "container_image_pinned_uri": description[
                "AlgorithmSpecification"
            ]["TrainingImage"],
            "resource_config": description["ResourceConfig"],
            "source_artifact": source_object,
            "runtime_object": runtime_object,
            "cloud_evidence_object": evidence_object,
            "model_artifact": model_object,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": (
                "The supplied digest is an operator-verified expected-image "
                "assertion, corroborated by the captured runtime fingerprint; "
                "it is not independent in-container image attestation."
            ),
        }
        from scripts.px057_h4_common import write_json

        runtime_target.parent.mkdir(parents=True, exist_ok=True)
        runtime_target.write_bytes(runtime_temp.read_bytes())
        write_json(cloud_target, cloud_manifest)
    print(
        json.dumps(
            {
                "status": "PASS",
                "runtime_manifest": str(runtime_target.relative_to(ROOT)),
                "cloud_job_manifest": str(cloud_target.relative_to(ROOT)),
                "runtime_version_id": runtime_object["version_id"],
                "model_artifact_version_id": model_object["version_id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
