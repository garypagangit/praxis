"""Bind normal-stability development execution to committed code and audited arrays."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / "native_graph"
EMBEDDING = HERE.parent / "embedding_baseline"
REPO = HERE.parents[2]
STATUS = "FROZEN_NORMAL_STABILITY"


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def code_paths(config):
    paths = {Path(config).resolve(), HERE / "PROTOCOL.md", HERE / "PROTOCOL_REVIEW.md",
             HERE / "PINNED_BASELINES.json", *HERE.glob("*.py"), *HERE.glob("*.sh"),
             *(NATIVE / name for name in ("data.py", "pilot.py", "provenance.py", "cloud_control.py")),
             *(EMBEDDING / name for name in ("engine.py", "scoring.py"))}
    if any(not path.resolve().is_relative_to(REPO.resolve()) for path in paths):
        raise ValueError("Runtime source or configuration escapes the repository")
    return sorted(paths, key=str)


def contained_file(root, relative):
    """Reject aliases, Windows drive paths, and escapes before reading bytes."""
    if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative
            or relative.startswith("/") or any(part in {"", ".", ".."} for part in relative.split("/"))
            or PurePosixPath(relative).as_posix() != relative):
        raise ValueError("Invalid or escaping graph path")
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Invalid or escaping graph path")
    return path


def data_inventory(data_dir):
    root = Path(data_dir).resolve()
    result = {}
    folded = set()
    for path in sorted(root.rglob("*.npz")):
        relative = path.relative_to(root).as_posix()
        checked = contained_file(root, relative)
        if relative.casefold() in folded:
            raise ValueError("Colliding graph paths")
        folded.add(relative.casefold())
        result[relative] = digest(checked)
    return result


def validate_manifest(data_dir):
    root = Path(data_dir).resolve()
    manifest = read(root / "MANIFEST.json")
    if (manifest.get("schema") != "apt-final-native-graph-data-v1"
            or manifest.get("status") != "STATIC_DEVELOPMENT_ONLY"
            or manifest.get("adapter_sha256") != digest(NATIVE / "data.py")):
        raise ValueError("A matching native static-development data audit is required")
    expected, folded = {}, set()
    for dataset in manifest.get("datasets", []):
        if (dataset.get("status") != "STATIC_DEVELOPMENT_ONLY"
                or dataset.get("matches_upstream_git_blob") is not True):
            raise ValueError("Data source provenance did not qualify")
        for graph in dataset.get("graphs", []):
            relative = graph["npz"]
            contained_file(root, relative)
            if relative.casefold() in folded:
                raise ValueError("Duplicate or colliding graph path")
            folded.add(relative.casefold())
            if not re.fullmatch(r"[0-9a-f]{64}", graph.get("npz_sha256", "")):
                raise ValueError("Invalid normalized graph digest")
            expected[relative] = graph["npz_sha256"]
    if not expected or expected != data_inventory(root):
        raise ValueError("Actual arrays do not match the audited graph inventory")
    return manifest


def verify_registration(config_path, data_dir, registration_path):
    config_path, data_dir = Path(config_path).resolve(), Path(data_dir).resolve()
    record = read(registration_path)
    if record.get("scope") != "DEVELOPMENT_ONLY" or record.get("status") != STATUS:
        raise ValueError("A frozen normal-stability development registration is required")
    if (read(config_path).get("scope") != "DEVELOPMENT_ONLY"
            or record.get("config_sha256") != digest(config_path)):
        raise ValueError("Configuration changed after registration")
    expected = {path.relative_to(REPO).as_posix() for path in code_paths(config_path)}
    if set(record.get("code_hashes", {})) != expected:
        raise ValueError("Registered source inventory does not match runtime")
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", record.get("git_commit", "")):
        raise ValueError("Registration requires a complete Git commit digest")
    has_git = (REPO / ".git").exists()
    if not has_git and not re.fullmatch(r"[0-9a-f]{64}", os.environ.get("APT_FROZEN_BUNDLE_SHA256", "")):
        raise ValueError("Remote execution requires the externally hash-verified bundle marker")
    for relative, sha in record["code_hashes"].items():
        path = contained_file(REPO, relative)
        if digest(path) != sha:
            raise ValueError("Registered source changed: " + relative)
        if has_git:
            blob = subprocess.check_output(["git", "show", record["git_commit"] + ":" + relative], cwd=REPO)
            if hashlib.sha256(blob).hexdigest() != sha:
                raise ValueError("Source does not match its recorded commit: " + relative)
    if record.get("data_manifest_sha256") != digest(data_dir / "MANIFEST.json"):
        raise ValueError("Data audit manifest changed after registration")
    validate_manifest(data_dir)
    if not record.get("data_files") or record["data_files"] != data_inventory(data_dir):
        raise ValueError("Normalized graph bytes changed after registration")
    return record


def register(config_path, data_dir, output):
    config_path, data_dir, output = Path(config_path).resolve(), Path(data_dir).resolve(), Path(output)
    if output.exists():
        raise FileExistsError("Registration already exists: " + str(output))
    if read(config_path).get("scope") != "DEVELOPMENT_ONLY":
        raise ValueError("Only development scope is supported")
    paths = code_paths(config_path)
    validate_manifest(data_dir)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    hashes = {}
    for path in paths:
        relative = path.relative_to(REPO).as_posix()
        blob = subprocess.check_output(["git", "show", commit + ":" + relative], cwd=REPO)
        if hashlib.sha256(blob).hexdigest() != digest(path):
            raise ValueError("Commit exact code/config/protocol bytes first: " + relative)
        hashes[relative] = digest(path)
    record = {
        "scope": "DEVELOPMENT_ONLY", "status": STATUS,
        "created_utc": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
        "config_sha256": digest(config_path), "code_hashes": hashes,
        "data_manifest_sha256": digest(data_dir / "MANIFEST.json"),
        "data_files": data_inventory(data_dir), "scientific_runs_before_this_freeze": 0,
        "confirmation_registered": False, "test_outcomes_previously_inspected": True,
        "predecessor_weights_used": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    verify_registration(config_path, data_dir, output)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["register", "verify"])
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args(argv)
    action = register if args.action == "register" else verify_registration
    record = action(args.config, args.data_dir, args.registration)
    print(json.dumps({"status": record["status"], "commit": record["git_commit"],
                      "source_files": len(record["code_hashes"]), "data_files": len(record["data_files"])}))


if __name__ == "__main__":
    main()
