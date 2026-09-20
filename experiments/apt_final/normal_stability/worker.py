"""One bounded runner invocation: all normal fits precede all attack replay."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from .provenance import verify_registration


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args(argv)
    config_path = Path(__file__).with_name("config.json")
    verify_registration(config_path, args.data_dir, args.registration)
    args.output.mkdir(parents=True, exist_ok=True)
    status_path = args.output / "WORKER_STATUS.json"
    if status_path.exists():
        raise FileExistsError("Worker attempt already exists")
    status = {"scope": "DEVELOPMENT_ONLY", "status": "RUNNING",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "runner_invocations": 1, "device": "cuda"}

    def save():
        temporary = args.output / ".WORKER_STATUS.tmp"
        temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        temporary.replace(status_path)

    save()
    command = [sys.executable, "-u", "-m", "experiments.apt_final.normal_stability.runner",
               "--config", str(config_path), "--data-dir", str(args.data_dir),
               "--output", str(args.output), "--registration", str(args.registration),
               "--device", "cuda"]
    print(json.dumps({"event": "normal_stability_runner_start"}), flush=True)
    try:
        result = subprocess.run(command)
    except Exception as error:
        status.update(status="INCOMPLETE", error_type=type(error).__name__,
                      ended_utc=datetime.now(timezone.utc).isoformat())
        save()
        raise
    status.update(status="COMPLETE" if result.returncode == 0 else "INCOMPLETE",
                  returncode=result.returncode, ended_utc=datetime.now(timezone.utc).isoformat())
    save()
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
