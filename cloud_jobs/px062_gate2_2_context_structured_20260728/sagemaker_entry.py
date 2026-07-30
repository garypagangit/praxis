from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    config = Path(os.environ["PX062_GATE22_CONFIG"])
    if not config.is_file():
        raise FileNotFoundError(f"frozen config not found: {config}")
    subprocess.run(
        [
            sys.executable,
            "scripts/run_px062_gate2_2_models.py",
            "--config",
            str(config),
        ],
        check=True,
    )
    payload = json.loads(config.read_text(encoding="utf-8"))
    source = Path(payload["collection_output_dir"])
    if not source.is_dir():
        raise FileNotFoundError(f"collector output not found: {source}")
    target = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model")) / "px062_gate2_2"
    if target.exists():
        raise FileExistsError(f"exclusive model output already exists: {target}")
    target.mkdir(parents=True)
    for filename in (
        "model_traces.jsonl",
        "collection_summary.json",
        "tokenizer_artifacts.tar.gz",
    ):
        shutil.copy2(source / filename, target / filename)
    shutil.copy2(config, target / "frozen_config.json")
    manifest = root / "bundle_manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError("source bundle manifest is missing")
    shutil.copy2(manifest, target / "source_bundle_manifest.json")


if __name__ == "__main__":
    main()
