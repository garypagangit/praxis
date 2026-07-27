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
    config = Path(os.environ["PX062_CONFIG"])
    subprocess.run(
        [
            sys.executable,
            "scripts/run_px062_skill_hallucination_models.py",
            "--config",
            str(config),
        ],
        check=True,
    )
    payload = json.loads(config.read_text(encoding="utf-8"))
    source = Path(payload["output_dir"])
    shutil.copy2(config, source / "frozen_config.json")
    bundle_manifest = root / "bundle_manifest.json"
    if bundle_manifest.exists():
        shutil.copy2(bundle_manifest, source / "source_bundle_manifest.json")
    target = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model")) / "px062_gate2"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


if __name__ == "__main__":
    main()
