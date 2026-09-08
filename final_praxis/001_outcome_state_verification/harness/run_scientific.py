#!/usr/bin/env python3
"""Fail-closed scientific runner for Final Praxis 001.

This orchestrator deliberately requires external agent and judge adapters. It
must never silently substitute synthetic decisions for the scientific run.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE2 = ROOT / "artifacts" / "fixtures" / "GATE2_PASS.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agent-adapter", required=True, help="Importable/callable external adapter identifier")
    p.add_argument("--judge-adapter", required=True, help="Importable/callable external adapter identifier")
    p.add_argument("--config", default=str(ROOT / "configs" / "experiment.json"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not GATE2.exists():
        raise SystemExit("BLOCKED: Gate 2 fixture marker is missing. Run fixture validation first.")
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise SystemExit(f"BLOCKED: frozen experiment config missing: {cfg_path}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if args.dry_run:
        print(json.dumps({"status":"READY_FOR_EXTERNAL_COMPUTE","agent_adapter":args.agent_adapter,
                          "judge_adapter":args.judge_adapter,"config":cfg}, indent=2))
        return 0
    raise SystemExit(
        "BLOCKED: this repository runner contains no embedded model credentials/endpoints. "
        "Bind reviewed external agent and judge adapters before scientific execution; synthetic fallback is forbidden."
    )

if __name__ == "__main__":
    raise SystemExit(main())
