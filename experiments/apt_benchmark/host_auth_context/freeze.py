"""Bind qualified inputs and scientific source before any follow-up fit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..host_history_exfil.run import PARAMS, SEEDS, sha, utc, write
from .policy import BUDGETS, MIN_NEGATIVE, MIN_POSITIVE
from .run import ARMS, REPLAY_ARMS


def freeze(base_prepared, base_run, events, output):
    if output.exists():
        raise ValueError("Protocol already exists")
    qualification = json.loads((events / "QUALIFICATION.json").read_text(encoding="utf-8"))
    if not qualification.get("approved_for_event_time_replay", False):
        raise ValueError("Event-time replay is not qualified")
    for name, expected in qualification["artifact_sha256"].items():
        if sha(events / name) != expected:
            raise ValueError("Event artifact changed")
    directory = Path(__file__).resolve().parent
    if qualification["parser_sha256"] != sha(directory / "host_events.py"):
        raise ValueError("Parser changed since event qualification")
    files = [directory / name for name in ["freeze.py", "run.py", "features.py", "policy.py", "host_events.py", "DESIGN.md"]]
    files += [directory.parent / "host_history_exfil" / name for name in ["run.py", "context.py"]]
    files += [base_prepared / name for name in ["DATA.npz", "PREPARATION.json"]]
    files += [base_run / name for name in ["SUMMARY.json", "COMPLETE.json"]]
    files += [base_run / str(seed) / "PREDICTIONS.npz" for seed in SEEDS]
    files += [events / name for name in ["EVENTS.npz", "OBSERVED.npz", "QUALIFICATION.json"]]
    raw_root = Path(qualification["source_root"])
    for item in qualification["sources"]:
        raw = raw_root / item["source_file"]
        if sha(raw) != item["sha256"]:
            raise ValueError("Raw host source changed")
        files.append(raw)
    bindings = [{"path": str(path.resolve()), "sha256": sha(path)} for path in files]
    spec = {"created_utc": utc(), "version": 1, "status": "FROZEN_BEFORE_AUTH_FEATURE_PREPARATION_AND_FITS",
            "scope": "Previously exposed one-campaign author-stage development; not a novel algorithm or verified successful theft",
            "base_prepared": str(base_prepared.resolve()), "base_run": str(base_run.resolve()), "events": str(events.resolve()),
            "bindings": bindings, "auth_arms": ARMS, "replay_arms": REPLAY_ARMS, "model": "LightGBM", "parameters": PARAMS,
            "seeds": SEEDS, "fit_rows": "Exact prior per-seed fit_indices, 26767 each; unchanged later calibration and test rows",
            "auth_windows_ms": [300000, 1800000], "source_history_only": True,
            "availability_control": "Identical prior observed-log volume, timing, log family and eligible donor indicators in all seven arms",
            "wrong_host_control": "Different host with same coarse role and log family, observed strictly before query; queried source also observed",
            "primary_contrasts": ["current_auth minus current_availability", "context_auth minus context_availability", "context_auth minus context_wrong_auth"],
            "thresholds": {"f1": "Calibration exfiltration F1 maximum, higher cut on ties", "tails": list(BUDGETS), "comparison": ["global", "role_tail"],
                           "minimum_role_negatives": MIN_NEGATIVE, "minimum_role_positives_for_automatic_stage": MIN_POSITIVE,
                           "support_values": "Fixed engineering settings, not literature standards, confidence guarantees or study pass/fail criteria"},
            "retention": "Baseline current-flow movement flag is independent; baseline any-attack alert is preserved in review union mechanically",
            "ambiguous": "Both target flags or exfiltration in insufficiently calibrated role goes to unresolved review; no resolved-correct credit",
            "interpretation": "No movement calibration cases, sparse movement support, source/role confounding, unknown collection latency; publish all policies and actual costs",
            "qualification_status": qualification["status"], "cloud_compute": False}
    write(output, spec)
    print(json.dumps({"protocol": str(output), "sha256": sha(output), "bound_artifacts": len(bindings)}))


def main():
    p = argparse.ArgumentParser()
    for key in ["base-prepared", "base-run", "events", "output"]:
        p.add_argument("--" + key, type=Path, required=True)
    args = p.parse_args()
    freeze(args.base_prepared, args.base_run, args.events, args.output)


if __name__ == "__main__": main()
