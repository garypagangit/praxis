"""Real model runner; immutable stage attempts, resumable complete records, no fallback."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import platform
import sys
from pathlib import Path
from .common import ARMS, ROOT, file_hash, load_json, now, write_json
from .workflow import run_one


def preflight():
    config = load_json(ROOT / "configs" / "experiment.json")
    frozen = load_json(ROOT / "FROZEN_PROTOCOL.json")
    for path, wanted in frozen["files"].items():
        if file_hash(ROOT / path) != wanted:
            raise RuntimeError("Frozen file changed: " + path)
    fixture = load_json(ROOT / "artifacts" / "fixtures" / "FIXTURE_GATE.json")
    if fixture["status"] != "PASS" or fixture["fixture_count"] < 144:
        raise RuntimeError("Fixture gate has not passed")
    if fixture["fixture_sha256"] != file_hash(ROOT / "artifacts" / "fixtures" / "fixtures.json"):
        raise RuntimeError("Fixture hash mismatch")
    cases = load_json(ROOT / "configs" / "scenarios.json")
    if len(cases) != 120 or len({c["case_id"] for c in cases}) != 120:
        raise RuntimeError("Scenario count/identity mismatch")
    for family in ("E1", "E2", "E3", "E4", "E5", "E6"):
        for condition in ("clean", "injected"):
            if sum(c["family"] == family and c["condition"] == condition for c in cases) != 10:
                raise RuntimeError("Frozen family denominators invalid")
    return config, cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pilot", "discovery"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--pilot-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config, cases = preflight()
    protocol_hash = file_hash(ROOT / "FROZEN_PROTOCOL.json")
    if args.mode == "pilot":
        cases = [case for case in cases if case["case_id"] in config["pilot_case_ids"]]
    else:
        if not args.pilot_dir:
            raise RuntimeError("Discovery requires --pilot-dir with a completed independent pilot audit")
        pilot = load_json(args.pilot_dir / "verification" / "audit.json")
        if pilot["status"] != "PASS" or pilot["mode"] != "pilot" or pilot["record_count"] != 16 or pilot["protocol_hash"] != protocol_hash:
            raise RuntimeError("Infrastructure pilot audit missing, incomplete or stale")
    manifest_path = args.output / "RUN_MANIFEST.json"
    spec = {"mode": args.mode, "protocol_hash": protocol_hash, "case_ids": [case["case_id"] for case in cases], "config": config, "evidence_kind": "real_model_inference"}
    if args.resume:
        manifest = load_json(manifest_path)
        if any(manifest.get(k) != v for k,v in spec.items()):
            raise RuntimeError("Resume manifest does not match frozen run")
    else:
        if args.output.exists() and any(args.output.iterdir()):
            raise RuntimeError("Output directory must be empty/new")
        args.output.mkdir(parents=True, exist_ok=True)
        write_json(manifest_path, {**spec, "started_at": now(), "python": sys.version, "platform": platform.platform(), "pilot_dir": str(args.pilot_dir) if args.pilot_dir else None}, exclusive=True)
    from final_praxis.shared.model_adapter import HTTPAdapter
    adapter = HTTPAdapter(args.base_url, config["model_id"], config["model_revision"])
    policy = load_json(ROOT / "configs" / "policy.json")
    (args.output / "records").mkdir(exist_ok=True)

    def execute(case, arm):
        logical_id = case["case_id"] + "_" + arm
        record_path = args.output / "records" / (logical_id + ".json")
        if record_path.exists():
            return logical_id, "already_complete"
        attempt_root = args.output / "raw" / logical_id
        attempt_root.mkdir(parents=True, exist_ok=True)
        prior_attempts = sorted(attempt_root.glob("attempt-*"))
        for attempt in range(len(prior_attempts), config["max_infrastructure_retries"] + 1):
            attempt_dir = attempt_root / f"attempt-{attempt:02d}"
            attempt_dir.mkdir(exist_ok=False)
            def sink(index, stage):
                path = attempt_dir / f"stage-{index:02d}.json"
                write_json(path, stage, exclusive=True)
                return path.relative_to(args.output).as_posix()
            try:
                result = run_one(case, arm, adapter.generate, policy, config, call_sink=sink)
                result.update({"experiment_id": config["experiment_id"], "protocol_hash": protocol_hash,
                               "seed": config["seed"], "evidence_kind": "real_model_inference", "attempt": attempt, "completed_at": now()})
                write_json(record_path, result, exclusive=True)
                return logical_id, "complete"
            except Exception as exc:
                write_json(attempt_dir / "INFRASTRUCTURE_ERROR.json", {"at": now(), "type": type(exc).__name__, "message": str(exc), "logical_id": logical_id, "attempt": attempt}, exclusive=True)
        return logical_id, "infrastructure_failed"

    failures = []
    with ThreadPoolExecutor(max_workers=config["concurrency"]) as pool:
        jobs = [pool.submit(execute, case, arm) for case in cases for arm in ARMS]
        for index, future in enumerate(as_completed(jobs), 1):
            logical_id, status = future.result()
            if status == "infrastructure_failed": failures.append(logical_id)
            print(json.dumps({"completed": index, "expected": len(jobs), "id": logical_id, "status": status}), flush=True)
    if failures:
        raise RuntimeError("Incomplete infrastructure cases: " + ", ".join(failures))
    print("All frozen workflows completed; run independent_verify before analysis.", flush=True)


if __name__ == "__main__":
    main()
