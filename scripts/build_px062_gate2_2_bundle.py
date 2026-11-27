#!/usr/bin/env python
"""Build a deterministic, answer-key-blind PX-062 Gate 2.2 source archive."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


CONFIG = "configs/px062_skill_selection_gate2_2_v1_0_20260728.json"
TASKS = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl"
)
CATALOG = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json"
)
BENCHMARK_MANIFEST = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/benchmark_manifest.json"
)
ANSWER_KEY = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/answer_key.jsonl"
)
COLLECTOR = "scripts/run_px062_gate2_2_models.py"
ENTRYPOINT = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/sagemaker_entry.py"
)
REQUIREMENTS_SOURCE = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/requirements.txt"
)

ARCHIVE_MEMBERS = {
    CONFIG: CONFIG,
    TASKS: TASKS,
    CATALOG: CATALOG,
    BENCHMARK_MANIFEST: BENCHMARK_MANIFEST,
    COLLECTOR: COLLECTOR,
    ENTRYPOINT: ENTRYPOINT,
    "requirements.txt": REQUIREMENTS_SOURCE,
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def git(*args: str, root: Path) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root)


def git_blob(root: Path, commit: str, path: str) -> bytes:
    return git("show", f"{commit}:{path}", root=root)


def validate_source_commit(root: Path, commit: str) -> str:
    resolved = git("rev-parse", f"{commit}^{{commit}}", root=root).decode().strip()
    if resolved != commit:
        raise ValueError("source commit must be a full canonical commit SHA")
    return resolved


def validate_frozen_config(config: dict[str, Any]) -> None:
    if config.get("status") != "FROZEN_PREREGISTERED":
        raise ValueError("configuration is not frozen and preregistered")
    integrity = config.get("source_integrity", {})
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in integrity.values()
    ):
        raise ValueError("configuration contains an unfrozen source hash")


def build_manifest(
    *,
    source_commit: str,
    files: dict[str, bytes],
    config: dict[str, Any],
    answer_key_raw: bytes,
) -> dict[str, Any]:
    return {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "source_commit": source_commit,
        "answer_key_blinding": {
            "included_in_archive": False,
            "registered_sha256": sha256_bytes(answer_key_raw),
            "registered_bytes": len(answer_key_raw),
        },
        "files": {
            name: {"sha256": sha256_bytes(raw), "bytes": len(raw)}
            for name, raw in sorted(files.items())
        },
    }


def deterministic_archive(files: dict[str, bytes], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for name, payload in sorted(files.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with tempfile.SpooledTemporaryFile() as handle:
                        handle.write(payload)
                        handle.seek(0)
                        tar.addfile(info, handle)


def build(root: Path, source_commit: str, output: Path) -> dict[str, Any]:
    root = root.resolve()
    source_commit = validate_source_commit(root, source_commit)
    repo_files = {
        archive_name: git_blob(root, source_commit, repo_path)
        for archive_name, repo_path in ARCHIVE_MEMBERS.items()
    }
    config = json.loads(repo_files[CONFIG].decode("utf-8"))
    validate_frozen_config(config)
    expected_paths = config["frozen_inputs"]
    if expected_paths["tasks"] != TASKS:
        raise ValueError("frozen task path differs from archive contract")
    if expected_paths["registry_catalog"] != CATALOG:
        raise ValueError("frozen registry path differs from archive contract")
    if expected_paths["benchmark_manifest"] != BENCHMARK_MANIFEST:
        raise ValueError("benchmark-manifest path differs from archive contract")
    if expected_paths["answer_key"] != ANSWER_KEY:
        raise ValueError("answer-key path differs from blinding contract")
    answer_key_raw = git_blob(root, source_commit, ANSWER_KEY)
    integrity = config["source_integrity"]
    observed = {
        "tasks_sha256": sha256_bytes(repo_files[TASKS]),
        "answer_key_sha256": sha256_bytes(answer_key_raw),
        "registry_catalog_sha256": sha256_bytes(repo_files[CATALOG]),
        "benchmark_manifest_sha256": sha256_bytes(repo_files[BENCHMARK_MANIFEST]),
    }
    if observed != integrity:
        raise ValueError(f"frozen source hashes differ: {observed} != {integrity}")
    manifest = build_manifest(
        source_commit=source_commit,
        files=repo_files,
        config=config,
        answer_key_raw=answer_key_raw,
    )
    archive_files = {**repo_files, "bundle_manifest.json": canonical_json_bytes(manifest)}
    deterministic_archive(archive_files, output)
    return {
        "archive": output.as_posix(),
        "archive_sha256": sha256_file(output),
        "archive_bytes": output.stat().st_size,
        "manifest": manifest,
        "members": sorted(archive_files),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(build(root, args.source_commit, args.output), indent=2))


if __name__ == "__main__":
    main()
