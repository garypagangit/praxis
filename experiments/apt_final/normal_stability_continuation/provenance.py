"""Freeze a runtime-only continuation and its verified same-experiment checkpoints."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from ..normal_stability import provenance as original
from .checkpoints import verify_reuse

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "normal_stability"
NATIVE = HERE.parent / "native_graph"
REPO = HERE.parents[2]
STATUS = "FROZEN_NORMAL_STABILITY_CONTINUATION"
digest = original.digest
read = original.read
contained_file = original.contained_file


def runtime_settings():
    settings = read(HERE / "config.json")
    expected = {
        "scope": "DEVELOPMENT_ONLY", "mode": "RUNTIME_ONLY_NORMAL_ENCODER_CACHE_REUSE",
        "recompute_all_banks": True, "recompute_all_calibration_and_normal_results": True,
        "replay_all_attack_conditions": True, "reuse_bank_or_attack_outputs": False,
        "archive_max_members": 2000, "archive_max_bytes": 4_000_000_000,
    }
    if settings != expected:
        raise ValueError("Continuation settings must preserve the fixed runtime-only contract")
    return settings


def code_paths(config_path, original_registration_path, source_record):
    paths = {Path(config_path).resolve(), Path(original_registration_path).resolve(),
             HERE / "config.json", HERE / "PROTOCOL.md", *HERE.glob("*.py"), *HERE.glob("*.sh"),
             *(REPO / relative for relative in source_record["code_hashes"])}
    if any(not path.resolve().is_relative_to(REPO.resolve()) for path in paths):
        raise ValueError("Continuation source or original registration escapes the repository")
    return sorted(paths, key=str)


def reuse_inventory(reuse_dir):
    root = Path(reuse_dir).resolve()
    manifest = read(root / "REUSE_MANIFEST.json")
    expected = manifest.get("inventory")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("A nonempty verified checkpoint inventory is required")
    actual, folded = {}, set()
    for relative, sha in expected.items():
        path = contained_file(root, relative)
        if not relative.startswith("checkpoints/") or relative.casefold() in folded:
            raise ValueError("Checkpoint path must be unique and inside checkpoints/")
        folded.add(relative.casefold())
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or digest(path) != sha:
            raise ValueError("Verified checkpoint bytes changed: " + relative)
        actual[relative] = sha
    present = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if present != set(actual) | {"REUSE_MANIFEST.json"}:
        raise ValueError("Reuse tree contains unregistered or missing checkpoint files")
    return actual


def verify_registration(config_path, data_dir, original_registration_path, reuse_dir, registration_path):
    record = read(registration_path)
    if record.get("scope") != "DEVELOPMENT_ONLY" or record.get("status") != STATUS:
        raise ValueError("A frozen runtime-only normal-stability continuation is required")
    if (record.get("scientific_settings_changed") is not False
            or record.get("all_banks_and_calibration_recomputed") is not True
            or record.get("all_attack_conditions_replayed") is not True
            or record.get("confirmation_registered") is not False
            or record.get("test_outcomes_previously_inspected") is not True):
        raise ValueError("Continuation receipt violates the unchanged-science contract")
    if record.get("original_registration_sha256") != digest(original_registration_path):
        raise ValueError("Original scientific registration changed")
    if record.get("original_config_sha256") != digest(config_path):
        raise ValueError("Original scientific configuration changed")
    source_record = original.verify_registration(config_path, data_dir, original_registration_path)
    if record.get("original_source_commit") != source_record["git_commit"]:
        raise ValueError("Original source commit reference changed")
    expected = {path.relative_to(REPO).as_posix() for path in code_paths(config_path, original_registration_path, source_record)}
    if set(record.get("code_hashes", {})) != expected:
        raise ValueError("Continuation source inventory does not match runtime")
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", record.get("git_commit", "")):
        raise ValueError("Continuation requires a complete Git commit digest")
    has_git = (REPO / ".git").exists()
    if not has_git and not re.fullmatch(r"[0-9a-f]{64}", os.environ.get("APT_FROZEN_BUNDLE_SHA256", "")):
        raise ValueError("Remote continuation requires the externally hash-verified bundle marker")
    for relative, sha in record["code_hashes"].items():
        path = contained_file(REPO, relative)
        if digest(path) != sha:
            raise ValueError("Registered continuation source changed: " + relative)
        if has_git:
            blob = subprocess.check_output(["git", "show", record["git_commit"] + ":" + relative], cwd=REPO)
            if hashlib.sha256(blob).hexdigest() != sha:
                raise ValueError("Continuation source does not match its recorded commit: " + relative)
    runtime_settings()
    if (record.get("data_manifest_sha256") != digest(Path(data_dir) / "MANIFEST.json")
            or record.get("data_files") != source_record["data_files"]):
        raise ValueError("Continuation data references differ from the original registration")
    if record.get("reuse_manifest_sha256") != digest(Path(reuse_dir) / "REUSE_MANIFEST.json"):
        raise ValueError("Reuse manifest changed after continuation registration")
    if record.get("reuse_files") != reuse_inventory(reuse_dir):
        raise ValueError("Registered checkpoint inventory changed")
    verify_reuse(reuse_dir, config_path, data_dir, original_registration_path)
    return record


def register(config_path, data_dir, original_registration_path, reuse_dir, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Continuation registration already exists: " + str(output))
    source_record = original.verify_registration(config_path, data_dir, original_registration_path)
    runtime_settings()
    verify_reuse(reuse_dir, config_path, data_dir, original_registration_path)
    reused = reuse_inventory(reuse_dir)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    hashes = {}
    for path in code_paths(config_path, original_registration_path, source_record):
        relative = path.relative_to(REPO).as_posix()
        blob = subprocess.check_output(["git", "show", commit + ":" + relative], cwd=REPO)
        if hashlib.sha256(blob).hexdigest() != digest(path):
            raise ValueError("Commit exact continuation and original-registration bytes first: " + relative)
        hashes[relative] = digest(path)
    record = {
        "scope": "DEVELOPMENT_ONLY", "status": STATUS,
        "created_utc": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
        "original_registration_sha256": digest(original_registration_path),
        "original_config_sha256": digest(config_path), "original_source_commit": source_record["git_commit"],
        "code_hashes": hashes, "data_manifest_sha256": digest(Path(data_dir) / "MANIFEST.json"),
        "data_files": source_record["data_files"],
        "reuse_manifest_sha256": digest(Path(reuse_dir) / "REUSE_MANIFEST.json"), "reuse_files": reused,
        "scientific_settings_changed": False, "all_banks_and_calibration_recomputed": True,
        "all_attack_conditions_replayed": True, "confirmation_registered": False,
        "test_outcomes_previously_inspected": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    verify_registration(config_path, data_dir, original_registration_path, reuse_dir, output)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["register", "verify"])
    parser.add_argument("--config", type=Path, default=ORIGINAL / "config.json")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--original-registration", type=Path, required=True)
    parser.add_argument("--reuse-dir", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args(argv)
    action = register if args.action == "register" else verify_registration
    record = action(args.config, args.data_dir, args.original_registration, args.reuse_dir, args.registration)
    print(json.dumps({"status": record["status"], "commit": record["git_commit"],
                      "source_files": len(record["code_hashes"]), "reused_files": len(record["reuse_files"])}))


if __name__ == "__main__":
    main()
