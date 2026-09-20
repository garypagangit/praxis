"""Invoke one registered runtime continuation; original scientific order is preserved."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from .provenance import ORIGINAL, verify_registration


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--original-registration", type=Path, required=True)
    parser.add_argument("--reuse-dir", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args(argv)
    config = ORIGINAL / "config.json"
    verify_registration(config, args.data_dir, args.original_registration, args.reuse_dir, args.registration)
    args.output.mkdir(parents=True, exist_ok=True)
    status_path = args.output / "WORKER_STATUS.json"
    if status_path.exists():
        raise FileExistsError("Continuation worker attempt already exists")
    status = {"scope": "DEVELOPMENT_ONLY", "status": "RUNNING",
              "started_utc": datetime.now(timezone.utc).isoformat(), "runner_invocations": 1,
              "device": "cuda", "runtime_continuation": True, "scientific_settings_changed": False}

    def save():
        temporary = args.output / ".WORKER_STATUS.tmp"
        temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        temporary.replace(status_path)

    save()
    command = [sys.executable, "-u", "-m", "experiments.apt_final.normal_stability_continuation.runner",
               "--config", str(config), "--data-dir", str(args.data_dir),
               "--original-registration", str(args.original_registration), "--reuse-dir", str(args.reuse_dir),
               "--registration", str(args.registration), "--output", str(args.output), "--device", "cuda"]
    print(json.dumps({"event": "normal_stability_continuation_start"}), flush=True)
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
