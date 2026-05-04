from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path


DEFAULT_CONFIGS = ",".join(
    [
        "configs/praxis04-baseline-single.json",
        "configs/praxis04-baseline-tse.json",
        "configs/praxis04-treatment-stage.json",
        "configs/praxis04-ablation-nostage.json",
        "configs/praxis04-ablation-oraclestage.json",
    ]
)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def stage_source(repo_root: Path) -> tempfile.TemporaryDirectory:
    tempdir = tempfile.TemporaryDirectory(prefix="praxis04-sagemaker-src-")
    target = Path(tempdir.name)
    shutil.copytree(
        repo_root / "src",
        target / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    for config in (repo_root / "configs").glob("praxis04-*.json"):
        copy_file(config, target / "configs" / config.name)
    copy_file(repo_root / "scripts" / "sagemaker_praxis04_entry.py", target / "scripts" / "sagemaker_praxis04_entry.py")
    copy_file(repo_root / "scripts" / "analyze_praxis04.py", target / "scripts" / "analyze_praxis04.py")
    copy_file(repo_root / "requirements-sagemaker.txt", target / "requirements.txt")
    return tempdir


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit Praxis 04 as a SageMaker training job.")
    parser.add_argument("--role-arn", default=os.environ.get("SAGEMAKER_ROLE_ARN"), help="SageMaker execution role ARN.")
    parser.add_argument("--bucket", default=os.environ.get("PRAXIS04_S3_BUCKET"), help="S3 bucket for SageMaker code/output.")
    parser.add_argument("--prefix", default=os.environ.get("PRAXIS04_S3_PREFIX", "sagemaker/praxis04"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"))
    parser.add_argument("--instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--instance-count", type=int, default=1)
    parser.add_argument("--volume-size", type=int, default=250)
    parser.add_argument("--max-run", type=int, default=43200)
    parser.add_argument("--framework-version", default="2.3.0")
    parser.add_argument("--py-version", default="py310")
    parser.add_argument("--seeds", default="13,42,137,271,1729")
    parser.add_argument("--configs", default=DEFAULT_CONFIGS)
    parser.add_argument("--sample-rows-per-file", type=int, default=0, help="0 means full CSVs.")
    parser.add_argument("--chunksize", type=int, default=200000)
    parser.add_argument("--fast-pilot", action="store_true", help="Use shorter model settings for a quick connectivity run.")
    parser.add_argument("--base-job-name", default="praxis04-stage-routing")
    parser.add_argument("--use-spot", action="store_true")
    parser.add_argument("--max-wait", type=int, default=86400)
    parser.add_argument("--wait", action="store_true", help="Stream logs and wait for the job to finish.")
    args = parser.parse_args()

    if not args.role_arn:
        raise SystemExit("Missing --role-arn or SAGEMAKER_ROLE_ARN.")
    if not args.bucket:
        raise SystemExit("Missing --bucket or PRAXIS04_S3_BUCKET.")

    import boto3
    import sagemaker
    from sagemaker.pytorch import PyTorch

    repo_root = Path(__file__).resolve().parents[1]
    session = boto3.Session(region_name=args.region)
    region = session.region_name
    if not region:
        raise SystemExit("No AWS region found. Set AWS_REGION, AWS_DEFAULT_REGION, or pass --region.")

    sm_session = sagemaker.session.Session(
        boto_session=session,
        default_bucket=args.bucket,
    )

    with stage_source(repo_root) as staged:
        hyperparameters = {
            "configs": args.configs,
            "seeds": args.seeds,
            "sample-rows-per-file": args.sample_rows_per_file,
            "chunksize": args.chunksize,
            "download-data": "true",
            "fast-pilot": "true" if args.fast_pilot else "false",
        }
        estimator = PyTorch(
            entry_point="scripts/sagemaker_praxis04_entry.py",
            source_dir=staged,
            role=args.role_arn,
            framework_version=args.framework_version,
            py_version=args.py_version,
            instance_count=args.instance_count,
            instance_type=args.instance_type,
            volume_size=args.volume_size,
            max_run=args.max_run,
            output_path=f"s3://{args.bucket}/{args.prefix}/output",
            code_location=f"s3://{args.bucket}/{args.prefix}/code",
            base_job_name=args.base_job_name,
            hyperparameters=hyperparameters,
            use_spot_instances=args.use_spot,
            max_wait=args.max_wait if args.use_spot else None,
            sagemaker_session=sm_session,
        )
        estimator.fit(wait=args.wait, logs="All" if args.wait else False)
        print(f"Submitted SageMaker training job: {estimator.latest_training_job.name}")
        print(f"Output path: {estimator.output_path}")
        print("Check status:")
        print(f"  aws sagemaker describe-training-job --training-job-name {estimator.latest_training_job.name} --region {region}")
        print("Download model/results artifact after completion:")
        print(f"  aws s3 cp {estimator.model_data} ./praxis04_sagemaker_model.tar.gz --region {region}")


if __name__ == "__main__":
    main()
