#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path


ROLE = "arn:aws:iam::272615233626:role/service-role/AmazonSageMaker-ExecutionRole-20260416T191047"
BUCKET = "praxis-garypagan-272615233626-us-east-1"


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--max-run", type=int, default=21600)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    import boto3
    import sagemaker
    from sagemaker.pytorch import PyTorch

    root = Path(__file__).resolve().parents[1]
    config = Path("configs/px062_skill_hallucination_gate2_20260724.json")
    with tempfile.TemporaryDirectory(prefix="px062-sagemaker-") as temp:
        target = Path(temp)
        for relative in (
            "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py",
            "scripts/run_px062_skill_hallucination_models.py",
            config.as_posix(),
            "data/px062/hallucination_benchmark/tasks.jsonl",
            "data/px062/hallucination_benchmark/registry_names.json",
        ):
            copy(root / relative, target / relative)
        copy(
            root / "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt",
            target / "requirements.txt",
        )
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        sm = sagemaker.session.Session(
            boto_session=session, default_bucket=BUCKET
        )
        prefix = "experiments/px062-skill-provenance/gate2-hallucination-20260724"
        estimator = PyTorch(
            entry_point="cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py",
            source_dir=target,
            role=ROLE,
            framework_version="2.3.0",
            py_version="py311",
            instance_count=1,
            instance_type=args.instance_type,
            volume_size=150,
            max_run=args.max_run,
            output_path=f"s3://{BUCKET}/{prefix}/output",
            code_location=f"s3://{BUCKET}/{prefix}/code",
            base_job_name="px062-skill-hallucination",
            sagemaker_session=sm,
            environment={
                "PX062_CONFIG": config.as_posix(),
                "HF_HOME": "/opt/ml/input/data/huggingface",
                "TOKENIZERS_PARALLELISM": "false",
            },
        )
        estimator.fit(wait=args.wait, logs="All" if args.wait else False)
        print(
            json.dumps(
                {
                    "training_job_name": estimator.latest_training_job.name,
                    "instance_type": args.instance_type,
                    "output_path": estimator.output_path,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
