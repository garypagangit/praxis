#!/usr/bin/env python
"""Build the deterministic PX-062 Gate 2.1 cloud source from the aborted bundle."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import tarfile
import tempfile
from pathlib import Path


BASE_BUNDLE_SHA256 = "afe0fd3a90e605766f1da555ac7b320c44187b50689c3379829a9b121534d3fb"
TASKS_SHA256 = "fbda2e8039d2a6087fb1cd3584470269c3e2c409d4bbe13f7eb1e59a4fc19316"
REGISTRY_SHA256 = "2c447b5eee07b2f2930fc8649860652b36d4902dafadfa83e3f5d7aa041a76db"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_extract(archive: Path, target: Path) -> None:
    with tarfile.open(archive, "r:gz") as handle:
        root = target.resolve()
        for member in handle.getmembers():
            destination = (target / member.name).resolve()
            if root not in destination.parents and destination != root:
                raise ValueError(f"unsafe archive member: {member.name}")
        handle.extractall(target)


def copy_normalized_text(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))


def load_function(module_path: Path, function_name: str):
    spec = importlib.util.spec_from_file_location(
        f"px062_{module_path.stem}_{function_name}", module_path
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load parser module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function_name)


def verify_frozen_parser_conformance(root: Path, tasks: Path, registry: Path) -> dict:
    collector_parser = load_function(
        root / "scripts/run_px062_skill_hallucination_models.py", "extract_name"
    )
    adjudicator_parser = load_function(
        root / "scripts/adjudicate_px062_skill_hallucination.py", "exact_candidate"
    )
    task_rows = [
        json.loads(line)
        for line in tasks.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = json.loads(registry.read_text(encoding="utf-8"))["names"]
    canonical_registry = {name.casefold(): name for name in names}
    near_misses = [
        row["presented_nonexistent_name"]
        for row in task_rows
        if row["task_type"] == "near_miss_name"
    ]
    if len(near_misses) != 100:
        raise ValueError(f"expected 100 frozen near misses, found {len(near_misses)}")
    failures = []
    for candidate in near_misses:
        expected = candidate.casefold()
        collector_value = collector_parser(candidate, names)
        adjudicator_value = adjudicator_parser(candidate, canonical_registry)
        if (
            expected in canonical_registry
            or collector_value != expected
            or adjudicator_value != expected
        ):
            failures.append(
                {
                    "candidate": candidate,
                    "collector": collector_value,
                    "adjudicator": adjudicator_value,
                }
            )
    if failures:
        raise ValueError(f"frozen parser conformance failures: {failures}")
    return {
        "near_miss_count": len(near_misses),
        "collector_preserved_nonexistent": len(near_misses),
        "adjudicator_preserved_nonexistent": len(near_misses),
    }


def deterministic_archive(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
                    if not path.is_file():
                        continue
                    relative = path.relative_to(source).as_posix()
                    info = tar.gettarinfo(str(path), arcname=relative)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with path.open("rb") as handle:
                        tar.addfile(info, handle)


def build(base_archive: Path, output: Path, root: Path) -> dict:
    observed_base = sha256_file(base_archive)
    if observed_base != BASE_BUNDLE_SHA256:
        raise ValueError(f"base bundle SHA-256 {observed_base} != {BASE_BUNDLE_SHA256}")
    with tempfile.TemporaryDirectory(prefix="px062-g21-") as temp:
        source = Path(temp) / "source"
        source.mkdir()
        safe_extract(base_archive, source)
        tasks = source / "data/px062/hallucination_benchmark/tasks.jsonl"
        registry = source / "data/px062/hallucination_benchmark/registry_names.json"
        if sha256_file(tasks) != TASKS_SHA256:
            raise ValueError("base task file does not match the admitted Gate 2.1 task hash")
        if sha256_file(registry) != REGISTRY_SHA256:
            raise ValueError("base registry file does not match the admitted Gate 2.1 registry hash")
        parser_conformance = verify_frozen_parser_conformance(
            root, tasks, registry
        )
        (source / "configs/px062_skill_hallucination_gate2_20260724.json").unlink(
            missing_ok=True
        )

        overrides = {
            "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py": root
            / "cloud_jobs/px062_skill_hallucination_20260724/sagemaker_entry.py",
            "scripts/run_px062_skill_hallucination_models.py": root
            / "scripts/run_px062_skill_hallucination_models.py",
            "configs/px062_skill_hallucination_gate2_v1_1_20260726.json": root
            / "configs/px062_skill_hallucination_gate2_v1_1_20260726.json",
            "requirements.txt": root
            / "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt",
            "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt": root
            / "cloud_jobs/px062_skill_hallucination_20260724/requirements.txt",
        }
        for relative, local_source in overrides.items():
            copy_normalized_text(local_source, source / relative)

        files = {
            path.relative_to(source).as_posix(): sha256_file(path)
            for path in sorted(source.rglob("*"), key=lambda item: item.as_posix())
            if path.is_file() and path.name != "bundle_manifest.json"
        }
        manifest = {
            "experiment_id": "px062-skill-hallucination-gate2-v1-1-20260726",
            "protocol_version": "1.1",
            "base_aborted_bundle_sha256": BASE_BUNDLE_SHA256,
            "tasks_sha256": TASKS_SHA256,
            "registry_sha256": REGISTRY_SHA256,
            "parser_conformance": parser_conformance,
            "files": files,
        }
        (source / "bundle_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        deterministic_archive(source, output)
    return {
        "output": str(output.resolve()),
        "sha256": sha256_file(output),
        "bytes": output.stat().st_size,
        "manifest": manifest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(build(args.base_archive, args.output, root), indent=2))


if __name__ == "__main__":
    main()
