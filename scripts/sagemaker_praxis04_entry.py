from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "src"))


def ensure_imports() -> None:
    missing = []
    for module_name in ("boto3", "botocore", "numpy", "pandas", "sklearn", "matplotlib"):
        try:
            __import__(module_name)
        except Exception:
            missing.append(module_name)
    if missing:
        requirements = ROOT / "requirements.txt"
        if requirements.exists():
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
        else:
            raise RuntimeError(f"Missing Python dependencies: {missing}")


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_paths(value: str) -> list[Path]:
    return [ROOT / item.strip() for item in value.split(",") if item.strip()]


def download_cicids2018(data_dir: Path) -> None:
    ensure_imports()
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config

    data_dir.mkdir(parents=True, exist_ok=True)
    if any(data_dir.glob("*.csv")):
        print(f"CIC-IDS2018 CSVs already present under {data_dir}")
        return

    bucket = "cse-cic-ids2018"
    prefix = "Processed Traffic Data for ML Algorithms/"
    s3 = boto3.client("s3", region_name="ca-central-1", config=Config(signature_version=UNSIGNED))
    paginator = s3.get_paginator("list_objects_v2")
    downloaded = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".csv"):
                continue
            target = data_dir / Path(key).name
            print(f"Downloading s3://{bucket}/{key} -> {target}")
            s3.download_file(bucket, key, str(target))
            downloaded += 1
    if downloaded == 0:
        raise RuntimeError("No CIC-IDS2018 CSV files were downloaded.")


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_all(args: argparse.Namespace) -> None:
    from praxis.praxis04.data_loader import write_csv_manifest
    from praxis.praxis04.experiment import run_experiment

    data_dir = Path(args.data_dir)
    if args.download_data:
        download_cicids2018(data_dir)
    manifest_path = write_csv_manifest(data_dir)
    print(f"Wrote data manifest to {manifest_path}")

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    config_paths = parse_csv_paths(args.configs)
    seeds = parse_csv_ints(args.seeds)
    runs = []

    for config_path in config_paths:
        config_template = load_config(config_path)
        for seed in seeds:
            config = dict(config_template)
            config["seed"] = int(seed)
            config["data_dir"] = str(data_dir)
            if args.sample_rows_per_file > 0:
                config["sample_rows_per_file"] = int(args.sample_rows_per_file)
                config["chunksize"] = int(args.chunksize or args.sample_rows_per_file)
            elif args.chunksize > 0:
                config["chunksize"] = int(args.chunksize)
            if args.fast_pilot:
                config["rf_n_estimators"] = int(config.get("rf_n_estimators", 24))
                config["rf_max_depth"] = int(config.get("rf_max_depth", 14))
                config["mlp_max_iter"] = int(config.get("mlp_max_iter", 40))
                config["bilstm_epochs"] = int(config.get("bilstm_epochs", 2))
                config["router_epochs"] = int(config.get("router_epochs", 40))
                config["deterministic_torch"] = False
                if not config["name"].startswith("praxis04-sm-"):
                    config["name"] = f"praxis04-sm-{config['name']}"

            run_name = f"{config['name']}_seed{seed}"
            run_dir = results_dir / run_name
            print(f"=== Running {run_name} ===", flush=True)
            payload = run_experiment(config, run_dir)
            runs.append(
                {
                    "run_name": run_name,
                    "config": config_path.name,
                    "seed": seed,
                    "macro_f1": payload["metrics"].get("macro_f1"),
                    "run_dir": str(run_dir),
                }
            )

    write_json(results_dir / "sagemaker_run_index.json", {"runs": runs})
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "scripts" / "analyze_praxis04.py"),
            "--results-dir",
            str(results_dir),
            "--output",
            str(results_dir / "praxis04_headline_table.csv"),
        ]
    )

    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    output_copy = model_dir / "praxis04_results"
    if output_copy.exists():
        shutil.rmtree(output_copy)
    shutil.copytree(results_dir, output_copy)
    shutil.copy2(manifest_path, output_copy / "manifest.json")
    print(f"Copied final results to {output_copy}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SageMaker entrypoint for Praxis 04.")
    parser.add_argument("--configs", required=True)
    parser.add_argument("--seeds", default="13,42,137,271,1729")
    parser.add_argument("--data-dir", default="/opt/ml/input/data/cic-ids-2018")
    parser.add_argument("--results-dir", default="/opt/ml/output/data/runs")
    parser.add_argument("--sample-rows-per-file", type=int, default=0)
    parser.add_argument("--chunksize", type=int, default=200000)
    parser.add_argument("--download-data", type=lambda value: str(value).lower() in {"1", "true", "yes"}, default=True)
    parser.add_argument("--fast-pilot", type=lambda value: str(value).lower() in {"1", "true", "yes"}, default=False)
    args = parser.parse_args()
    ensure_imports()
    run_all(args)


if __name__ == "__main__":
    main()
