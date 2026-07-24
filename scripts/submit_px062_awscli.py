#!/usr/bin/env python
"""Submit PX-062 through AWS CLI without boto3/sagemaker SDK dependencies."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


ROLE = "arn:aws:iam::272615233626:role/service-role/AmazonSageMaker-ExecutionRole-20260416T191047"
BUCKET = "praxis-garypagan-272615233626-us-east-1"
IMAGE = (
    "763104351884.dkr.ecr.us-east-1.amazonaws.com/"
    "pytorch-training:2.3.0-gpu-py311-cu121-ubuntu20.04-sagemaker"
)


def copy(root: Path, target: Path, relative: str) -> None:
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / relative, destination)


def aws(profile: str, *args: str) -> str:
    command = ["aws", *args, "--profile", profile, "--region", "us-east-1"]
    return subprocess.check_output(command, text=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--max-run", type=int, default=21600)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
    job_name = f"px062-skill-hallucination-{stamp}"
    prefix = "experiments/px062-skill-provenance/gate2-hallucination-20260724"
    with tempfile.TemporaryDirectory(prefix="px062-awscli-") as temp:
        temp_path = Path(temp)
        source = temp_path / "source"
        for relative in (
            "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py",
            "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt",
            "scripts/run_px062_skill_hallucination_models.py",
            "configs/px062_skill_hallucination_gate2_20260724.json",
            "data/px062/hallucination_benchmark/tasks.jsonl",
            "data/px062/hallucination_benchmark/registry_names.json",
        ):
            copy(root, source, relative)
        shutil.copy2(
            source
            / "cloud_jobs"
            / "px062_skill_hallucination_20260724"
            / "requirements.txt",
            source / "requirements.txt",
        )
        archive = temp_path / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as handle:
            for path in source.rglob("*"):
                if path.is_file():
                    handle.add(path, arcname=path.relative_to(source).as_posix())
        code_uri = f"s3://{BUCKET}/{prefix}/code/{job_name}/source.tar.gz"
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                str(archive),
                code_uri,
                "--profile",
                args.profile,
                "--region",
                "us-east-1",
            ],
            check=True,
        )
        request = {
            "TrainingJobName": job_name,
            "AlgorithmSpecification": {
                "TrainingImage": IMAGE,
                "TrainingInputMode": "File",
            },
            "RoleArn": ROLE,
            "OutputDataConfig": {
                "S3OutputPath": f"s3://{BUCKET}/{prefix}/output"
            },
            "ResourceConfig": {
                "InstanceType": args.instance_type,
                "InstanceCount": 1,
                "VolumeSizeInGB": 150,
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": args.max_run},
            "HyperParameters": {
                "sagemaker_program": (
                    "cloud_jobs/px062_skill_hallucination_20260724/"
                    "sagemaker_entry.py"
                ),
                "sagemaker_submit_directory": code_uri,
                "sagemaker_container_log_level": "20",
                "sagemaker_region": "us-east-1",
            },
            "Environment": {
                "PX062_CONFIG": (
                    "configs/px062_skill_hallucination_gate2_20260724.json"
                ),
                "HF_HOME": "/opt/ml/input/data/huggingface",
                "TOKENIZERS_PARALLELISM": "false",
            },
            "EnableNetworkIsolation": False,
        }
        request_path = temp_path / "request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        response = aws(
            args.profile,
            "sagemaker",
            "create-training-job",
            "--cli-input-json",
            f"file://{request_path}",
        )
        print(
            json.dumps(
                {
                    "job_name": job_name,
                    "code_uri": code_uri,
                    "response": json.loads(response),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
