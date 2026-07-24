#!/usr/bin/env python
"""SageMaker entry point for the PX-057 GPU capability pilot."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    source_dir = Path(__file__).resolve().parents[2]
    os.chdir(source_dir)
    config = Path(
        os.environ.get(
            "PX057_CONFIG",
            "configs/px057_adaptive_stopping_gate1_gpu_pilot_20260723.json",
        )
    )
    subprocess.run(
        [sys.executable, "scripts/run_px057_trace_collection.py", "--config", str(config)],
        check=True,
    )
    payload = json.loads(config.read_text(encoding="utf-8"))
    output_dir = Path(payload["output_dir"])
    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    target = model_dir / "px057_gate1_gpu_pilot"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(output_dir, target)
    print(f"Copied PX-057 results to {target}")


if __name__ == "__main__":
    main()
