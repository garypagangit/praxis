from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULTS = {
    "pipeline": "dapt2020_gml",
    "run_name": "dapt2020-local-fast",
    "output_dir": "runs",
    "notes": "Local DAPT2020 run for the imported GML pipeline.",
    "profile": "local-fast",
    "max_files": None,
    "sample_rate": None,
    "strategy": "hybrid",
    "merge_networks": False,
    "local_data_dir": "data/raw/dapt2020",
    "local_consolidated_csv": "data/processed/dapt2020/combined_flows.csv",
    "force_cpu": False,
    "optuna_trials": None,
    "train_epochs": None,
    "dgi_pretrain_epochs": None,
    "run_optuna": None,
    "run_dgi_pretraining": None,
}


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the imported DAPT2020 GML pipeline from the Praxis project."
    )
    parser.add_argument("--config", help="Optional path to a JSON config file.")
    parser.add_argument("--run-name", help="Name for this run.")
    parser.add_argument("--output-dir", help="Directory for run artifacts.")
    parser.add_argument("--notes", help="Short note describing the run.")
    parser.add_argument("--profile", help="Execution profile, for example local-fast or full.")
    parser.add_argument("--max-files", type=int, help="Optional limit on input CSV files.")
    parser.add_argument("--sample-rate", type=float, help="Optional row sampling fraction.")
    parser.add_argument("--strategy", help="Temporal split strategy.")
    parser.add_argument(
        "--merge-networks",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Whether to merge public/private network captures.",
    )
    parser.add_argument(
        "--force-cpu",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Force CPU execution even if CUDA is available.",
    )
    parser.add_argument("--optuna-trials", type=int, help="Override Optuna trials per model.")
    parser.add_argument("--train-epochs", type=int, help="Override supervised train epochs.")
    parser.add_argument(
        "--dgi-pretrain-epochs",
        type=int,
        help="Override DGI pretraining epochs.",
    )
    parser.add_argument(
        "--run-optuna",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable Optuna optimization.",
    )
    parser.add_argument(
        "--run-dgi-pretraining",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable DGI pretraining.",
    )
    return parser.parse_args()


def merge_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update(config)

    for arg_name, setting_name in (
        ("run_name", "run_name"),
        ("output_dir", "output_dir"),
        ("notes", "notes"),
        ("profile", "profile"),
        ("max_files", "max_files"),
        ("sample_rate", "sample_rate"),
        ("strategy", "strategy"),
        ("merge_networks", "merge_networks"),
        ("force_cpu", "force_cpu"),
        ("optuna_trials", "optuna_trials"),
        ("train_epochs", "train_epochs"),
        ("dgi_pretrain_epochs", "dgi_pretrain_epochs"),
        ("run_optuna", "run_optuna"),
        ("run_dgi_pretraining", "run_dgi_pretraining"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            merged[setting_name] = value

    return merged


def detect_environment() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd()),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "in_colab": "COLAB_RELEASE_TAG" in os.environ,
    }


def coerce_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): coerce_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [coerce_json(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(coerce_json(payload), indent=2), encoding="utf-8")


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def load_pipeline_module(repo_root: Path):
    script_path = repo_root / "imports" / "gml_to_detect_apt_final" / "gml_to_detect_apt_final.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_path}")

    spec = importlib.util.spec_from_file_location("praxis_dapt2020_pipeline", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec from {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, script_path


def apply_pipeline_env(settings: dict[str, Any], repo_root: Path, run_dir: Path) -> None:
    os.environ["DAPT2020_EXECUTION_PROFILE"] = str(settings["profile"])
    os.environ["DAPT2020_LOCAL_OUTPUT_DIR"] = str(run_dir.resolve())
    os.environ["DAPT2020_LOCAL_DATA_DIR"] = str(
        resolve_path(repo_root, settings["local_data_dir"])
    )
    os.environ["DAPT2020_LOCAL_CONSOLIDATED_CSV"] = str(
        resolve_path(repo_root, settings["local_consolidated_csv"])
    )

    if settings.get("force_cpu"):
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    optional_env = {
        "DAPT2020_OPTUNA_TRIALS": settings.get("optuna_trials"),
        "DAPT2020_TRAIN_EPOCHS": settings.get("train_epochs"),
        "DAPT2020_DGI_PRETRAIN_EPOCHS": settings.get("dgi_pretrain_epochs"),
        "DAPT2020_RUN_OPTUNA": settings.get("run_optuna"),
        "DAPT2020_RUN_DGI_PRETRAINING": settings.get("run_dgi_pretraining"),
    }

    for env_name, value in optional_env.items():
        if value is None:
            continue
        if isinstance(value, bool):
            os.environ[env_name] = "true" if value else "false"
        else:
            os.environ[env_name] = str(value)


def run_dapt2020_pipeline(settings: dict[str, Any]) -> Path:
    repo_root = resolve_repo_root()
    run_dir = resolve_path(repo_root, settings["output_dir"]) / settings["run_name"]
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "environment": detect_environment(),
    }
    write_json(run_dir / "metadata.json", metadata)

    apply_pipeline_env(settings, repo_root, run_dir)
    pipeline, pipeline_path = load_pipeline_module(repo_root)

    print(f"Run directory: {run_dir.resolve()}")
    print(f"Pipeline script: {pipeline_path}")
    print(f"Execution profile: {settings['profile']}")

    results = pipeline.main(
        max_files=settings.get("max_files"),
        sample_rate=settings.get("sample_rate"),
        strategy=settings.get("strategy", "hybrid"),
        merge_networks=bool(settings.get("merge_networks", False)),
    )
    if results is None:
        raise RuntimeError("The DAPT2020 pipeline returned no results.")

    summary = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": settings["pipeline"],
        "profile": settings["profile"],
        "results": results,
    }
    write_json(run_dir / "results-summary.json", summary)
    (run_dir / "README.txt").write_text(
        "This folder contains the DAPT2020 local pipeline outputs for this run.\n",
        encoding="utf-8",
    )
    return run_dir


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    settings = merge_settings(args, config)

    if settings["pipeline"] == "dapt2020_gml":
        run_dir = run_dapt2020_pipeline(settings)
    elif settings["pipeline"] == "unraveled_v02":
        from praxis.unraveled_v02 import run_unraveled_v02

        run_dir = run_unraveled_v02(settings)
    elif settings["pipeline"] == "unraveled_v03":
        from praxis.unraveled_v03 import run_unraveled_v03

        run_dir = run_unraveled_v03(settings)
    elif settings["pipeline"] == "synthetic_smoke":
        from praxis.synthetic_smoke import run_synthetic_smoke

        run_dir = run_synthetic_smoke(settings)
    else:
        raise ValueError(f"Unsupported pipeline: {settings['pipeline']}")

    print(f"Results summary: {run_dir / 'results-summary.json'}")


if __name__ == "__main__":
    main()
