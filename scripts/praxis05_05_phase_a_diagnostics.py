from __future__ import annotations

import argparse
import json

from praxis.praxis05.config import load_config
from praxis.praxis05.diagnostics import phase_a_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Praxis 05 Phase A diagnostics and enforce the kill switch.")
    parser.add_argument("--config", default="configs/praxis05-sae-topk-k32-x16.json")
    parser.add_argument("--phase-a-root", default="runs/praxis05-phase-a")
    parser.add_argument("--output", default="results/praxis05/phase_a/diagnostics.json")
    args = parser.parse_args()

    config = load_config(args.config)
    payload = phase_a_diagnostics(args.phase_a_root, config, args.output)
    print(json.dumps({"status": payload["status"], "checks": payload["checks"], "next_step": payload["next_step"]}, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

