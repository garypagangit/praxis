#!/usr/bin/env python
"""Submit a preregistered PX-057 SageMaker GPU training job."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path


DEFAULT_ROLE = (
    "arn:aws:iam::272615233626:role/service-role/"
    "AmazonSageMaker-ExecutionRole-20260416T191047"
)
DEFAULT_BUCKET = "praxis-garypagan-272615233626-us-east-1"


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def stage_source(repo: Path, config_relative: Path) -> tempfile.TemporaryDirectory:
    temp = tempfile.TemporaryDirectory(prefix="px057-sagemaker-")
    target = Path(temp.name)
    copy(
        repo / "cloud_jobs/px057_adaptive_stopping_20260723/sagemaker_entry.py",
        target / "cloud_jobs/px057_adaptive_stopping_20260723/sagemaker_entry.py",
    )
    copy(
        repo / "cloud_jobs/px057_adaptive_stopping_20260723/requirements.txt",
        target / "requirements.txt",
    )
    copy(
        repo / "scripts/run_px057_trace_collection.py",
        target / "scripts/run_px057_trace_collection.py",
    )
    copy(
        repo / "scripts/run_px057_adaptive_stopping_gate.py",
        target / "scripts/run_px057_adaptive_stopping_gate.py",
    )
    copy(repo / config_relative, target / config_relative)
    return temp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--role-arn", default=DEFAULT_ROLE)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--volume-size", type=int, default=100)
    parser.add_argument("--max-run", type=int, default=7200)
    parser.add_argument("--base-job-name", default="px057-adaptive-stop")
    parser.add_argument(
        "--config",
        default="configs/px057_adaptive_stopping_gate1_gpu_pilot_20260723.json",
        help="Repository-relative frozen experiment configuration.",
    )
    parser.add_argument(
        "--prefix",
        default="experiments/px057-adaptive-stopping/gate1-gpu-pilot-20260723",
        help="S3 prefix for source and output artifacts.",
    )
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    import boto3
    import sagemaker
    from sagemaker.pytorch import PyTorch

    repo = Path(__file__).resolve().parents[1]
    boto_session = boto3.Session(
        profile_name=args.profile,
        region_name=args.region,
    )
    identity = boto_session.client("sts").get_caller_identity()
    print(json.dumps({"aws_identity": identity["Arn"], "account": identity["Account"]}))
    sm_session = sagemaker.session.Session(
        boto_session=boto_session,
        default_bucket=args.bucket,
    )
    config_relative = Path(args.config)
    if config_relative.is_absolute() or ".." in config_relative.parts:
        raise ValueError("--config must be a safe repository-relative path")
    if not (repo / config_relative).is_file():
        raise FileNotFoundError(repo / config_relative)
    prefix = args.prefix.strip("/")
    with stage_source(repo, config_relative) as staged:
        estimator = PyTorch(
            entry_point="cloud_jobs/px057_adaptive_stopping_20260723/sagemaker_entry.py",
            source_dir=staged,
            role=args.role_arn,
            framework_version="2.3.0",
            py_version="py311",
            instance_count=1,
            instance_type=args.instance_type,
            volume_size=args.volume_size,
            max_run=args.max_run,
            output_path=f"s3://{args.bucket}/{prefix}/output",
            code_location=f"s3://{args.bucket}/{prefix}/code",
            base_job_name=args.base_job_name,
            sagemaker_session=sm_session,
            environment={
                "HF_HOME": "/opt/ml/input/data/huggingface",
                "PX057_CONFIG": config_relative.as_posix(),
                "TOKENIZERS_PARALLELISM": "false",
            },
        )
        estimator.fit(wait=args.wait, logs="All" if args.wait else False)
        job_name = estimator.latest_training_job.name
        print(json.dumps({
            "training_job_name": job_name,
            "region": args.region,
            "instance_type": args.instance_type,
            "output_path": estimator.output_path,
            "status_command": (
                f"aws sagemaker describe-training-job --profile {args.profile} "
                f"--region {args.region} --training-job-name {job_name}"
            ),
        }, indent=2))


if __name__ == "__main__":
    main()
