from __future__ import annotations

import argparse
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULTS = {
    "run_name": "smoke-test",
    "epochs": 1,
    "output_dir": "runs",
    "notes": "",
}


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Starter training entrypoint for the Praxis project."
    )
    parser.add_argument("--config", help="Optional path to a JSON config file.")
    parser.add_argument("--run-name", help="Name for this run.")
    parser.add_argument("--epochs", type=int, help="Number of epochs to run.")
    parser.add_argument("--output-dir", help="Directory for run artifacts.")
    parser.add_argument("--notes", help="Short note describing the run.")
    return parser.parse_args()


def merge_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update(config)

    if args.run_name:
        merged["run_name"] = args.run_name
    if args.epochs is not None:
        merged["epochs"] = args.epochs
    if args.output_dir:
        merged["output_dir"] = args.output_dir
    if args.notes:
        merged["notes"] = args.notes

    return merged


def detect_environment() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd()),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "in_colab": "COLAB_RELEASE_TAG" in os.environ,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    settings = merge_settings(args, config)

    run_dir = Path(settings["output_dir"]) / settings["run_name"]
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "environment": detect_environment(),
    }
    metrics = {
        "status": "starter-run-complete",
        "epochs_requested": settings["epochs"],
        "message": (
            "Replace src/praxis/train.py with your real training loop when you are ready."
        ),
    }

    write_json(run_dir / "metadata.json", metadata)
    write_json(run_dir / "metrics.json", metrics)
    (run_dir / "README.txt").write_text(
        "This folder is a placeholder run artifact. Put checkpoints and logs here.\n",
        encoding="utf-8",
    )

    print(f"Run directory: {run_dir.resolve()}")
    print("Starter run finished successfully.")


if __name__ == "__main__":
    main()
