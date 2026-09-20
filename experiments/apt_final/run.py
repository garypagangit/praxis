"""Gated CLI for APT-final. Real data requires hash-bound readiness receipts."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SYNTHETIC = "SYNTHETIC_SMOKE_NOT_SCIENTIFIC_EVIDENCE"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO).decode().strip()


def source_paths(config):
    contracts = [HERE / "docs/PROTOCOL.md", HERE / "data/DATA_CONTRACT.md", HERE / "candidates.json"]
    return sorted(set([Path(config).resolve(), *HERE.glob("*.py"),
                       *[p for p in contracts if p.exists()]]), key=str)


def register(config_path, output):
    config_path = Path(config_path).resolve()
    config = read(config_path)
    if config.get("scope") != "DEVELOPMENT_ONLY":
        raise ValueError("Only a DEVELOPMENT_ONLY configuration can be registered here")
    commit = git("rev-parse", "HEAD")
    hashes = {}
    for path in source_paths(config_path):
        rel = path.relative_to(REPO).as_posix()
        blob = subprocess.check_output(["git", "show", commit + ":" + rel], cwd=REPO)
        if hashlib.sha256(blob).hexdigest() != digest(path):
            raise ValueError("Commit the exact code/config bytes before registering: " + rel)
        hashes[rel] = digest(path)
    record = {"status": "DEVELOPMENT_CONFIGURATION_FROZEN", "scope": "DEVELOPMENT_ONLY",
              "created_utc": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
              "config": config_path.relative_to(REPO).as_posix(), "config_sha256": digest(config_path),
              "files": hashes, "scientific_experiments_completed": False,
              "confirmation_registered": False}
    write_new(output, record)
    return record


def verify_registration(config_path, registration):
    record = read(registration)
    if record.get("status") != "DEVELOPMENT_CONFIGURATION_FROZEN":
        raise ValueError("Missing valid development registration")
    if record.get("config_sha256") != digest(config_path):
        raise ValueError("Configuration changed since registration")
    expected = {p.relative_to(REPO).as_posix() for p in source_paths(config_path)}
    if set(record.get("files", {})) != expected:
        raise ValueError("Registered source inventory differs from runnable code")
    for rel, sha in record["files"].items():
        path = (REPO / rel).resolve()
        if not path.is_relative_to(REPO) or digest(path) != sha:
            raise ValueError("Registered source changed: " + rel)
        blob = subprocess.check_output(["git", "show", record["git_commit"] + ":" + rel], cwd=REPO)
        if hashlib.sha256(blob).hexdigest() != sha:
            raise ValueError("Registered source does not match its Git commit: " + rel)
    return record


def require_e0(receipt, rows=None, edges=None):
    # Resolve beside this module even when the CLI is imported by an audit test.
    import importlib.util
    spec = importlib.util.spec_from_file_location("apt_final_release_boundary", Path(__file__).with_name("readiness.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.require_data_release(receipt, rows=rows, edges=edges)


def status():
    receipts = sorted((HERE / "results").glob("e0*/E0_RESULT.json"))
    latest = read(receipts[-1]) if receipts else {}
    reg = HERE / "REGISTRATION.json"
    return {"program": "APT-final", "branch": git("branch", "--show-current"),
            "e0_status": latest.get("status", "NOT_RUN"),
            "e0_receipt": str(receipts[-1]) if receipts else None,
            "registration_present": reg.exists(),
            "e1_e4_real_data": "NOT_RELEASED" if latest.get("status") != "PASS" else "CHECK_NORMALIZED_DATA_BINDINGS",
            "candidate_topics": "candidates.json", "primary_program": "telemetry_quality_gate",
            "scientific_positive_result_claimed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    p = commands.add_parser("register")
    p.add_argument("--config", type=Path, default=HERE / "configs/development.json")
    p.add_argument("--output", type=Path, default=HERE / "REGISTRATION.json")
    p = commands.add_parser("smoke")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--config", type=Path, default=HERE / "configs/smoke.json")
    p = commands.add_parser("run")
    p.add_argument("--stage", choices=["E1", "E2", "E3", "E4"], required=True)
    p.add_argument("--config", type=Path, default=HERE / "configs/development.json")
    p.add_argument("--registration", type=Path, default=HERE / "REGISTRATION.json")
    p.add_argument("--e0-receipt", type=Path, required=True)
    p.add_argument("--rows", type=Path)
    p.add_argument("--edges", type=Path)
    p.add_argument("--e1-dir", type=Path)
    p.add_argument("--e2-dir", type=Path)
    p.add_argument("--policy", type=Path)
    p.add_argument("--readiness", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "status":
        result = status()
    elif args.command == "register":
        result = register(args.config, args.output)
    elif args.command == "smoke":
        import smoke_runner
        result = smoke_runner.run(args.output, args.config)
    else:
        verify_registration(args.config, args.registration)
        config = read(args.config)
        if config.get("scope") != "DEVELOPMENT_ONLY":
            raise ValueError("Wrong scientific configuration scope")
        require_e0(args.e0_receipt, args.rows, args.edges)
        if args.stage != "E3" and (args.rows is None or args.edges is None):
            raise ValueError("Rows and edges are required")
        if args.stage in ("E2", "E4") and args.e1_dir is None:
            raise ValueError("--e1-dir is required")
        if args.stage == "E3" and args.e2_dir is None:
            raise ValueError("--e2-dir is required")
        if args.stage == "E4" and (args.policy is None or args.readiness is None):
            raise ValueError("E4 requires frozen policy and separate confirmation readiness")
        import engine
        if args.stage == "E1":
            result = engine.run_e1(config, args.rows, args.edges, args.output, args.e0_receipt)
        elif args.stage == "E2":
            result = engine.run_e2(config, args.e1_dir, args.rows, args.edges, args.output, args.e0_receipt)
        elif args.stage == "E3":
            result = engine.run_e3(config, args.e2_dir, args.output)
        else:
            result = engine.run_e4(config, args.e1_dir, args.policy, args.rows, args.edges,
                                   args.output, args.e0_receipt, args.readiness)
    print(json.dumps(result, indent=2, allow_nan=False, default=str))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        sys.exit(2)
