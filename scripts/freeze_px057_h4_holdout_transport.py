#!/usr/bin/env python
"""Freeze PX-057 H4 holdout transport before calibration adjudication.

This gate verifies provenance and hashes only.  It deliberately does not read
calibration payloads or calculate any calibration statistic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path("configs/px057_h4_holdout_transport_20260727.json")
TRANSPORT_CONFIG_PATH = DEFAULT_CONFIG.as_posix()
FREEZE_SCHEMA_VERSION = "px057-h4-holdout-transport-freeze-v1"
EXPECTED_CELLS = {
    "cell1_llama31_gsm8k",
    "cell2_qwen25_arc",
    "cell3_llama31_arc",
}
EXPECTED_COLLECTION_FILES = {
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
}
ABSENT_FILE_KEYS = (
    "ltt_determination",
    "ltt_lock_manifest",
    "launch_manifest",
    "cloud_manifest",
    "manual_audit_blinded",
    "manual_audit",
    "holdout_determination",
)
FROZEN_SCIENCE_FIELDS = {
    "config_path": "config_sha256",
    "phase_a_freeze_path": "phase_a_freeze_sha256",
    "collector_path": "collector_sha256",
    "common_path": "common_sha256",
    "holdout_gate_path": "holdout_gate_sha256",
    "requirements_path": "requirements_sha256",
}
EXPECTED_REQUIRED_TRANSPORT_FILES = {
    TRANSPORT_CONFIG_PATH,
    "reports/adaptive_stopping_overthinking/PX057_H4_HOLDOUT_TRANSPORT_AMENDMENT_20260727.md",
    "cloud_jobs/px057_h4_holdout_20260727/.gitattributes",
    "cloud_jobs/px057_h4_holdout_20260727/sagemaker_entry.py",
    "cloud_jobs/px057_h4_calibration_20260725/sagemaker_entry.py",
    "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py",
    "scripts/freeze_px057_h4_holdout_transport.py",
    "scripts/submit_px057_h4_holdout.py",
    "scripts/fetch_px057_h4_holdout.py",
    "tests/test_px057_h4_holdout_transport_freeze.py",
    "tests/test_px057_h4_holdout_cloud.py",
}
EXPECTED_ARCHIVE_MEMBERS = {
    "cloud_jobs/px057_h4_holdout_20260727/.gitattributes",
    "cloud_jobs/px057_h4_holdout_20260727/sagemaker_entry.py",
    "cloud_jobs/px057_h4_calibration_20260725/sagemaker_entry.py",
    "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py",
    TRANSPORT_CONFIG_PATH,
    "configs/px057_h4_ltt_transfer_20260725.json",
    "configs/px057_h4_prompt_templates_20260725.json",
    "requirements-px057-h4.txt",
    "scripts/run_px057_h4_trace_collection.py",
    "scripts/px057_h4_common.py",
    "scripts/run_px057_h4_holdout_gate.py",
}
EXPECTED_FOCUSED_TESTS = {
    "tests/test_px057_h4_holdout_transport_freeze.py",
    "tests/test_px057_h4_holdout_cloud.py",
}
ARTIFACT_RECORD_FIELDS = {
    "path",
    "bytes",
    "sha256",
    "git_blob",
    "last_change_commit",
    "verified_at_head",
}


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {value}") from exc
    return resolved


def git(
    repo_root: Path,
    *args: str,
    text: bool = True,
    check: bool = True,
) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=text,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() if text else result.stderr.decode(errors="replace")
        raise ValueError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def committed_file_info(repo_root: Path, value: str | Path) -> dict[str, Any]:
    path = repo_path(repo_root, value)
    relative = path.relative_to(repo_root.resolve()).as_posix()
    if not path.is_file():
        raise ValueError(f"required file is missing: {relative}")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if tracked.returncode != 0:
        raise ValueError(f"required file is not committed: {relative}")
    head_bytes = git(repo_root, "show", f"HEAD:{relative}", text=False)
    assert isinstance(head_bytes, bytes)
    head_sha256 = sha256_bytes(head_bytes)
    worktree_sha256 = sha256_file(path)
    if head_sha256 != worktree_sha256:
        raise ValueError(f"required file differs from HEAD: {relative}")
    return {
        "path": relative,
        "bytes": len(head_bytes),
        "sha256": head_sha256,
        "git_blob": str(git(repo_root, "rev-parse", f"HEAD:{relative}")).strip(),
        "last_change_commit": str(
            git(repo_root, "log", "-1", "--format=%H", "--", relative)
        ).strip(),
        "verified_at_head": str(git(repo_root, "rev-parse", "HEAD")).strip(),
    }


def verify_binding(
    repo_root: Path,
    binding: dict[str, Any],
    *,
    expected_last_commit: str | None = None,
) -> dict[str, Any]:
    if not {"path", "sha256"} <= set(binding):
        raise ValueError("artifact binding requires path and sha256")
    info = committed_file_info(repo_root, str(binding["path"]))
    if info["sha256"] != str(binding["sha256"]):
        raise ValueError(f"SHA-256 mismatch: {binding['path']}")
    if "bytes" in binding and info["bytes"] != int(binding["bytes"]):
        raise ValueError(f"byte-length mismatch: {binding['path']}")
    if expected_last_commit and info["last_change_commit"] != expected_last_commit:
        raise ValueError(
            f"artifact was not last changed by {expected_last_commit}: {binding['path']}"
        )
    return info


def normalized_remote(value: str) -> str:
    return value.strip().rstrip("/").removesuffix(".git").lower()


def require_clean_pushed_head(
    repo_root: Path, repository: dict[str, Any]
) -> dict[str, str]:
    status = str(
        git(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    ).strip()
    if status:
        raise ValueError("holdout transport freeze requires a clean worktree")
    head = str(git(repo_root, "rev-parse", "HEAD")).strip()
    branch = str(git(repo_root, "branch", "--show-current")).strip()
    if branch != repository["branch"]:
        raise ValueError(
            f"current branch {branch!r} differs from registered {repository['branch']!r}"
        )
    upstream_ref = str(
        git(repo_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ).strip()
    upstream_head = str(git(repo_root, "rev-parse", "@{u}")).strip()
    if upstream_head != head:
        raise ValueError("HEAD is not identical to its pushed upstream ref")
    origin_url = str(git(repo_root, "remote", "get-url", "origin")).strip()
    if normalized_remote(origin_url) != normalized_remote(repository["url"]):
        raise ValueError("origin URL differs from the registered repository")
    remote_line = str(
        git(repo_root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    ).strip()
    remote_head = remote_line.split()[0] if remote_line else ""
    if remote_head != head:
        raise ValueError("remote branch does not contain the exact freeze HEAD")
    return {
        "head": head,
        "branch": branch,
        "upstream_ref": upstream_ref,
        "upstream_head": upstream_head,
        "origin_url": origin_url,
        "remote_head": remote_head,
    }


def validate_config(config: dict[str, Any]) -> None:
    if (
        config.get("transport_id")
        != "px057-h4-holdout-cloud-transport-20260727"
        or config.get("experiment_id")
        != "px057-h4-ltt-certified-transfer-20260725"
        or config.get("stage") != "H4_holdout_transport_pre_outcome_freeze"
        or config.get("status") != "FREEZE_PENDING"
        or config.get("freeze_schema_version") != FREEZE_SCHEMA_VERSION
    ):
        raise ValueError("unexpected holdout transport identity or status")
    source = config["source"]
    collection = config["collection"]
    calibration = config["calibration_evidence"]
    cells = config["cells"]
    if source["bootstrap"] != "explicit_s3_version_and_sha256_before_extraction":
        raise ValueError("source bootstrap is not version-and-hash authenticated")
    required_bootstrap = {
        source["entrypoint"],
        source["calibration_entrypoint"],
        source["phase_a_entrypoint"],
    }
    if not required_bootstrap <= set(source.get("archive_members", [])):
        raise ValueError("authenticated bootstrap archive omits an entry helper")
    if set(source.get("required_transport_files", [])) != (
        EXPECTED_REQUIRED_TRANSPORT_FILES
    ) or len(source.get("required_transport_files", [])) != len(
        EXPECTED_REQUIRED_TRANSPORT_FILES
    ):
        raise ValueError("required transport file inventory differs from the freeze")
    if set(source.get("archive_members", [])) != EXPECTED_ARCHIVE_MEMBERS or len(
        source.get("archive_members", [])
    ) != len(EXPECTED_ARCHIVE_MEMBERS):
        raise ValueError("source archive inventory differs from the freeze")
    if source["freeze_manifest"] != (
        "manifests/px057_h4_20260725/holdout_transport_freeze.json"
    ):
        raise ValueError("unexpected holdout transport freeze-manifest path")
    if (
        collection.get("split") != "holdout"
        or int(collection.get("expected_traces", -1)) != 300
        or int(collection.get("rounds", -1)) != 8
        or int(collection.get("expected_generations", -1)) != 2400
        or set(collection.get("files", [])) != EXPECTED_COLLECTION_FILES
    ):
        raise ValueError("unexpected holdout collection contract")
    if set(cells) != EXPECTED_CELLS:
        raise ValueError("holdout transport must contain the three frozen H4 cells")
    jobs: set[str] = set()
    for cell_id, cell in cells.items():
        job = str(cell["job_name"])
        expected_job = (
            f"px057-h4-hold-{cell['short_id']}-r1-20260727"
        )
        if job != expected_job or len(job) > 63 or not re.fullmatch(r"[a-z0-9-]+", job):
            raise ValueError(f"{cell_id}: invalid deterministic job name")
        jobs.add(job)
        expected_prefix = (
            f"{config['aws']['s3_prefix'].strip('/')}/holdout/{cell_id}/{job}"
        )
        if cell["result_prefix"] != expected_prefix:
            raise ValueError(f"{cell_id}: result prefix is not deterministic")
    if len(jobs) != 3:
        raise ValueError("holdout job names are not unique")
    commit = config["frozen_science"]["calibration_evidence_commit"]
    if (
        calibration.get("protected_fetch_commit") != commit
        or calibration.get("protected_fetch_completed_before_transport_freeze")
        is not True
        or calibration.get("payload_or_outcome_inspected_before_transport_freeze")
        is not False
        or set(calibration.get("cloud_manifests", {})) != EXPECTED_CELLS
        or set(calibration.get("bundles", {})) != EXPECTED_CELLS
    ):
        raise ValueError("calibration evidence disclosure is incomplete")
    for cell_id in EXPECTED_CELLS:
        if set(calibration["bundles"][cell_id]) != EXPECTED_COLLECTION_FILES:
            raise ValueError(f"{cell_id}: expected exactly four calibration files")
    if config["rules"].get("first_attempt_only") is not True:
        raise ValueError("holdout transport must be first-attempt-only")
    if (
        config["aws"].get("retry_strategy_omitted") is not True
        or config["aws"].get("enable_managed_spot_training") is not False
    ):
        raise ValueError(
            "holdout AWS transport must omit retry strategy and disable managed spot"
        )
    if {
        value
        for value in source["required_transport_files"]
        if value.startswith("tests/")
    } != EXPECTED_FOCUSED_TESTS:
        raise ValueError("focused transport test inventory differs from the freeze")


def verify_frozen_science(
    repo_root: Path, config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    frozen = config["frozen_science"]
    return {
        str(frozen[path_key]): verify_binding(
            repo_root,
            {"path": frozen[path_key], "sha256": frozen[hash_key]},
        )
        for path_key, hash_key in FROZEN_SCIENCE_FIELDS.items()
    }


def verify_calibration_evidence(
    repo_root: Path, config: dict[str, Any]
) -> dict[str, Any]:
    """Hash calibration bytes without parsing any scientific payload file."""
    calibration = config["calibration_evidence"]
    evidence_commit = str(calibration["protected_fetch_commit"])
    resolved = str(git(repo_root, "rev-parse", f"{evidence_commit}^{{commit}}" )).strip()
    if resolved != evidence_commit:
        raise ValueError("calibration evidence commit did not resolve exactly")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", evidence_commit, "HEAD"],
        cwd=repo_root,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ValueError("calibration evidence commit is not an ancestor of HEAD")
    cloud_records: dict[str, Any] = {}
    bundle_records: dict[str, Any] = {}
    for cell_id in sorted(EXPECTED_CELLS):
        bundle_records[cell_id] = {
            name: verify_binding(
                repo_root,
                binding,
                expected_last_commit=evidence_commit,
            )
            for name, binding in sorted(calibration["bundles"][cell_id].items())
        }
        cloud_binding = calibration["cloud_manifests"][cell_id]
        cloud_info = verify_binding(
            repo_root, cloud_binding, expected_last_commit=evidence_commit
        )
        cloud_path = repo_path(repo_root, cloud_binding["path"])
        cloud = json.loads(cloud_path.read_text(encoding="utf-8"))
        objects = cloud.get("collection_objects", {})
        expected_hashes = {
            name: record["sha256"]
            for name, record in calibration["bundles"][cell_id].items()
        }
        observed_hashes = {
            name: value.get("sha256") for name, value in objects.items()
        }
        if (
            cloud.get("stage") != "H4_calibration_cloud_job_manifest"
            or cloud.get("status") != "PASS"
            or cloud.get("job_status") != "Completed"
            or cloud.get("scientific_data_generated") is not True
            or cloud.get("split") != "calibration"
            or cloud.get("cell_id") != cell_id
            or observed_hashes != expected_hashes
            or any(not value.get("version_id") for value in objects.values())
        ):
            raise ValueError(f"{cell_id}: calibration transport metadata mismatch")
        cloud_records[cell_id] = cloud_info
    return {
        "protected_fetch_commit": evidence_commit,
        "protected_fetch_completed_before_transport_freeze": True,
        "payload_or_outcome_inspected_before_transport_freeze": False,
        "verification_method": calibration["verification_method"],
        "cloud_manifests": cloud_records,
        "bundles": bundle_records,
    }


def require_no_outcome_or_holdout_evidence(
    repo_root: Path, config: dict[str, Any]
) -> dict[str, Any]:
    checked_files: list[str] = []
    checked_dirs: list[str] = []
    for cell_id, cell in sorted(config["cells"].items()):
        for key in ABSENT_FILE_KEYS:
            relative = str(cell[key])
            checked_files.append(relative)
            if repo_path(repo_root, relative).exists():
                raise ValueError(
                    f"{cell_id}: pre-freeze LTT/holdout evidence exists: {relative}"
                )
        output_relative = str(cell["output_dir"])
        output = repo_path(repo_root, output_relative)
        checked_dirs.append(output_relative)
        if output.is_file() or (output.is_dir() and any(output.iterdir())):
            raise ValueError(
                f"{cell_id}: holdout output exists before transport freeze: "
                f"{output_relative}"
            )
    checked_files = sorted(checked_files)
    checked_dirs = sorted(checked_dirs)
    return {
        "status": "PASS",
        "absent_file_count": len(checked_files),
        "absent_files": checked_files,
        "empty_or_absent_directory_count": len(checked_dirs),
        "empty_or_absent_directories": checked_dirs,
    }


def verify_transport_files(
    repo_root: Path, config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    required = list(config["source"]["required_transport_files"])
    if len(required) != len(set(required)) or len(required) < 8:
        raise ValueError("new transport file inventory is incomplete or duplicated")
    return {
        value: committed_file_info(repo_root, value) for value in sorted(required)
    }


def verify_source_archive_members(
    repo_root: Path, config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    members = list(config["source"]["archive_members"])
    if len(members) != len(set(members)):
        raise ValueError("source archive member inventory contains duplicates")
    return {
        value: committed_file_info(repo_root, value) for value in sorted(members)
    }


def run_focused_tests(repo_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    test_paths = sorted(
        value
        for value in config["source"]["required_transport_files"]
        if value.startswith("tests/")
    )
    command = [sys.executable, "-m", "pytest", *test_paths, "-q"]
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            "focused PX-057 holdout transport tests failed:\n"
            + result.stdout
            + result.stderr
        )
    return {
        "status": "PASS",
        "test_files": test_paths,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
    }


def merge_protected_artifacts(*records: dict[str, Any]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        relative = str(record["path"])
        previous = merged.get(relative)
        if previous is not None and previous != record:
            raise ValueError(f"conflicting protected-artifact records: {relative}")
        merged[relative] = record
    return dict(sorted(merged.items()))


def expected_freeze_inventory(config: dict[str, Any]) -> dict[str, Any]:
    frozen = config["frozen_science"]
    source = config["source"]
    calibration = config["calibration_evidence"]
    frozen_paths = sorted(
        str(frozen[path_key]) for path_key in FROZEN_SCIENCE_FIELDS
    )
    cloud_paths = sorted(
        str(binding["path"])
        for binding in calibration["cloud_manifests"].values()
    )
    bundle_paths = sorted(
        str(binding["path"])
        for bundles in calibration["bundles"].values()
        for binding in bundles.values()
    )
    transport_paths = sorted(str(value) for value in source["required_transport_files"])
    archive_paths = sorted(str(value) for value in source["archive_members"])
    absent_files = sorted(
        str(cell[key])
        for cell in config["cells"].values()
        for key in ABSENT_FILE_KEYS
    )
    absent_dirs = sorted(str(cell["output_dir"]) for cell in config["cells"].values())
    focused_tests = sorted(
        value for value in transport_paths if value.startswith("tests/")
    )
    calibration_paths = sorted(cloud_paths + bundle_paths)
    protected_paths = sorted(
        {
            TRANSPORT_CONFIG_PATH,
            *frozen_paths,
            *calibration_paths,
            *transport_paths,
            *archive_paths,
        }
    )
    expected_counts = {
        "frozen_science": 6,
        "calibration_cloud_manifests": 3,
        "calibration_bundle_files": 12,
        "calibration_evidence": 15,
        "required_transport_files": 11,
        "archive_members": 11,
        "protected_artifacts": 33,
        "focused_tests": 2,
        "pre_outcome_absent_files": 21,
        "pre_outcome_empty_or_absent_directories": 3,
    }
    observed_paths = {
        "frozen_science": frozen_paths,
        "calibration_cloud_manifests": cloud_paths,
        "calibration_bundle_files": bundle_paths,
        "calibration_evidence": calibration_paths,
        "required_transport_files": transport_paths,
        "archive_members": archive_paths,
        "protected_artifacts": protected_paths,
        "focused_tests": focused_tests,
        "pre_outcome_absent_files": absent_files,
        "pre_outcome_empty_or_absent_directories": absent_dirs,
    }
    for name, expected_count in expected_counts.items():
        paths = observed_paths[name]
        if len(paths) != expected_count or len(set(paths)) != expected_count:
            raise ValueError(
                f"{name}: expected {expected_count} unique registered paths"
            )
    return {
        name: {"count": expected_counts[name], "paths": observed_paths[name]}
        for name in expected_counts
    }


def _validate_artifact_record(
    record: Any,
    *,
    expected_path: str,
    freeze_head: str,
    expected_sha256: str | None = None,
    expected_bytes: int | None = None,
    expected_last_commit: str | None = None,
) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != ARTIFACT_RECORD_FIELDS:
        raise ValueError(f"invalid closed artifact-record schema: {expected_path}")
    if record.get("path") != expected_path:
        raise ValueError(f"artifact key/path mismatch: {expected_path}")
    if not isinstance(record.get("bytes"), int) or isinstance(record["bytes"], bool):
        raise ValueError(f"invalid artifact byte length: {expected_path}")
    if int(record["bytes"]) < 1:
        raise ValueError(f"empty protected artifact: {expected_path}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", ""))):
        raise ValueError(f"invalid artifact SHA-256: {expected_path}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(record.get("git_blob", ""))):
        raise ValueError(f"invalid artifact Git blob: {expected_path}")
    if not re.fullmatch(
        r"[0-9a-f]{40}", str(record.get("last_change_commit", ""))
    ):
        raise ValueError(f"invalid artifact last-change commit: {expected_path}")
    if record.get("verified_at_head") != freeze_head:
        raise ValueError(f"artifact was not verified at freeze HEAD: {expected_path}")
    if expected_sha256 is not None and record["sha256"] != expected_sha256:
        raise ValueError(f"artifact differs from registered SHA-256: {expected_path}")
    if expected_bytes is not None and int(record["bytes"]) != int(expected_bytes):
        raise ValueError(f"artifact differs from registered byte length: {expected_path}")
    if (
        expected_last_commit is not None
        and record["last_change_commit"] != expected_last_commit
    ):
        raise ValueError(f"artifact differs from protected-fetch commit: {expected_path}")
    return record


def _validate_artifact_map(
    name: str,
    records: Any,
    expected_paths: set[str],
    *,
    freeze_head: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(records, dict) or set(records) != expected_paths:
        raise ValueError(f"{name} does not contain its exact registered path set")
    validated: dict[str, dict[str, Any]] = {}
    for path in sorted(expected_paths):
        validated[path] = _validate_artifact_record(
            records[path], expected_path=path, freeze_head=freeze_head
        )
    return validated


def validate_freeze_manifest_schema(
    config: dict[str, Any], freeze: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Validate the closed freeze schema without trusting its PASS label."""
    validate_config(config)
    expected_top_level = {
        "transport_id",
        "experiment_id",
        "manifest_schema_version",
        "stage",
        "status",
        "scientific_data_generated",
        "scientific_payload_or_outcome_inspected",
        "freeze_base_commit",
        "repository",
        "config",
        "frozen_science",
        "calibration_evidence",
        "inventory_contract",
        "pre_outcome_absence_checks",
        "transport_artifacts",
        "authenticated_bootstrap_archive_members",
        "protected_artifacts",
        "focused_tests",
        "freeze_base_artifact_verification",
        "rule",
    }
    if set(freeze) != expected_top_level:
        raise ValueError("holdout freeze does not satisfy the closed top-level schema")
    if (
        freeze.get("transport_id") != config["transport_id"]
        or freeze.get("experiment_id") != config["experiment_id"]
        or freeze.get("manifest_schema_version") != FREEZE_SCHEMA_VERSION
        or freeze.get("stage") != "H4_holdout_transport_freeze_determination"
        or freeze.get("status") != "PASS"
        or freeze.get("scientific_data_generated") is not False
        or freeze.get("scientific_payload_or_outcome_inspected") is not False
    ):
        raise ValueError("holdout freeze identity, phase, or scientific flags are invalid")
    freeze_head = str(freeze.get("freeze_base_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", freeze_head):
        raise ValueError("holdout freeze base commit is invalid")
    repository = freeze.get("repository")
    repository_keys = {
        "head",
        "branch",
        "upstream_ref",
        "upstream_head",
        "origin_url",
        "remote_head",
    }
    if not isinstance(repository, dict) or set(repository) != repository_keys:
        raise ValueError("holdout freeze repository evidence is incomplete")
    if (
        repository["head"] != freeze_head
        or repository["upstream_head"] != freeze_head
        or repository["remote_head"] != freeze_head
        or repository["branch"] != config["repository"]["branch"]
        or repository["upstream_ref"] != f"origin/{repository['branch']}"
        or normalized_remote(repository["origin_url"])
        != normalized_remote(config["repository"]["url"])
    ):
        raise ValueError("holdout freeze repository commits are not self-consistent")

    inventory = expected_freeze_inventory(config)
    if freeze.get("inventory_contract") != inventory:
        raise ValueError("holdout freeze inventory contract is incomplete or ambiguous")
    inventory_paths = {
        name: set(record["paths"]) for name, record in inventory.items()
    }
    config_record = _validate_artifact_record(
        freeze.get("config"),
        expected_path=TRANSPORT_CONFIG_PATH,
        freeze_head=freeze_head,
    )
    frozen_records = _validate_artifact_map(
        "frozen_science",
        freeze.get("frozen_science"),
        inventory_paths["frozen_science"],
        freeze_head=freeze_head,
    )
    frozen_config = config["frozen_science"]
    for path_key, hash_key in FROZEN_SCIENCE_FIELDS.items():
        path = str(frozen_config[path_key])
        _validate_artifact_record(
            frozen_records[path],
            expected_path=path,
            freeze_head=freeze_head,
            expected_sha256=str(frozen_config[hash_key]),
        )

    calibration = freeze.get("calibration_evidence")
    calibration_config = config["calibration_evidence"]
    calibration_keys = {
        "protected_fetch_commit",
        "protected_fetch_completed_before_transport_freeze",
        "payload_or_outcome_inspected_before_transport_freeze",
        "verification_method",
        "cloud_manifests",
        "bundles",
    }
    if not isinstance(calibration, dict) or set(calibration) != calibration_keys:
        raise ValueError("calibration evidence does not satisfy its closed schema")
    evidence_commit = str(config["frozen_science"]["calibration_evidence_commit"])
    if (
        calibration["protected_fetch_commit"] != evidence_commit
        or calibration["protected_fetch_completed_before_transport_freeze"] is not True
        or calibration["payload_or_outcome_inspected_before_transport_freeze"]
        is not False
        or calibration["verification_method"]
        != calibration_config["verification_method"]
        or set(calibration["cloud_manifests"]) != EXPECTED_CELLS
        or set(calibration["bundles"]) != EXPECTED_CELLS
    ):
        raise ValueError("calibration evidence disclosure or cell inventory is invalid")
    calibration_records: dict[str, dict[str, Any]] = {}
    for cell_id in sorted(EXPECTED_CELLS):
        cloud_binding = calibration_config["cloud_manifests"][cell_id]
        cloud_path = str(cloud_binding["path"])
        cloud_record = _validate_artifact_record(
            calibration["cloud_manifests"][cell_id],
            expected_path=cloud_path,
            freeze_head=freeze_head,
            expected_sha256=str(cloud_binding["sha256"]),
            expected_bytes=int(cloud_binding["bytes"]),
            expected_last_commit=evidence_commit,
        )
        calibration_records[cloud_path] = cloud_record
        if set(calibration["bundles"][cell_id]) != EXPECTED_COLLECTION_FILES:
            raise ValueError(f"{cell_id}: calibration bundle inventory is incomplete")
        for name in sorted(EXPECTED_COLLECTION_FILES):
            binding = calibration_config["bundles"][cell_id][name]
            path = str(binding["path"])
            record = _validate_artifact_record(
                calibration["bundles"][cell_id][name],
                expected_path=path,
                freeze_head=freeze_head,
                expected_sha256=str(binding["sha256"]),
                expected_bytes=int(binding["bytes"]),
                expected_last_commit=evidence_commit,
            )
            if path in calibration_records:
                raise ValueError(f"duplicate calibration evidence path: {path}")
            calibration_records[path] = record
    if set(calibration_records) != inventory_paths["calibration_evidence"]:
        raise ValueError("calibration evidence path set is incomplete")

    transport_records = _validate_artifact_map(
        "transport_artifacts",
        freeze.get("transport_artifacts"),
        inventory_paths["required_transport_files"],
        freeze_head=freeze_head,
    )
    archive_records = _validate_artifact_map(
        "authenticated_bootstrap_archive_members",
        freeze.get("authenticated_bootstrap_archive_members"),
        inventory_paths["archive_members"],
        freeze_head=freeze_head,
    )
    protected_records = _validate_artifact_map(
        "protected_artifacts",
        freeze.get("protected_artifacts"),
        inventory_paths["protected_artifacts"],
        freeze_head=freeze_head,
    )
    category_records = merge_protected_artifacts(
        *frozen_records.values(),
        *calibration_records.values(),
        *transport_records.values(),
        *archive_records.values(),
    )
    if category_records != protected_records:
        raise ValueError("protected artifacts differ from exact category union")
    if (
        protected_records.get(TRANSPORT_CONFIG_PATH) != config_record
        or transport_records.get(TRANSPORT_CONFIG_PATH) != config_record
        or archive_records.get(TRANSPORT_CONFIG_PATH) != config_record
    ):
        raise ValueError("transport config record is not identical across inventories")

    expected_absence = {
        "status": "PASS",
        "absent_file_count": inventory["pre_outcome_absent_files"]["count"],
        "absent_files": inventory["pre_outcome_absent_files"]["paths"],
        "empty_or_absent_directory_count": inventory[
            "pre_outcome_empty_or_absent_directories"
        ]["count"],
        "empty_or_absent_directories": inventory[
            "pre_outcome_empty_or_absent_directories"
        ]["paths"],
    }
    if freeze.get("pre_outcome_absence_checks") != expected_absence:
        raise ValueError("pre-outcome absence inventory is incomplete")
    focused = freeze.get("focused_tests")
    focused_keys = {"status", "test_files", "command", "returncode", "stdout"}
    expected_tests = inventory["focused_tests"]["paths"]
    if not isinstance(focused, dict) or set(focused) != focused_keys:
        raise ValueError("focused-test evidence does not satisfy its closed schema")
    command = focused.get("command")
    expected_tail = ["-m", "pytest", *expected_tests, "-q"]
    if (
        focused.get("status") != "PASS"
        or focused.get("test_files") != expected_tests
        or focused.get("returncode") != 0
        or not isinstance(command, list)
        or len(command) != len(expected_tail) + 1
        or not isinstance(command[0], str)
        or not command[0]
        or command[1:] != expected_tail
        or not isinstance(focused.get("stdout"), str)
        or re.search(r"\b\d+ passed\b", focused["stdout"]) is None
        or "failed" in focused["stdout"].lower()
    ):
        raise ValueError("focused tests were not executed successfully and exactly")
    base_verification = freeze.get("freeze_base_artifact_verification")
    expected_base_verification = {
        "status": "PASS",
        "freeze_base_commit": freeze_head,
        "protected_record_count": inventory["protected_artifacts"]["count"],
        "paths": inventory["protected_artifacts"]["paths"],
        "method": (
            "git_show_freeze_base_path_blob_bytes_sha256_and_exact_"
            "last_change_ancestry"
        ),
    }
    if base_verification != expected_base_verification:
        raise ValueError("freeze-base artifact verification inventory is incomplete")
    return protected_records


def verify_freeze_base_artifacts(
    repo_root: Path, freeze: dict[str, Any]
) -> dict[str, Any]:
    """Recompute every protected record from its historical freeze commit."""
    repo_root = repo_root.resolve()
    freeze_base = str(freeze.get("freeze_base_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", freeze_base):
        raise ValueError("holdout freeze base commit is invalid")
    resolved_base = str(git(repo_root, "rev-parse", f"{freeze_base}^{{commit}}" )).strip()
    if resolved_base != freeze_base:
        raise ValueError("holdout freeze base did not resolve exactly")
    records = freeze.get("protected_artifacts")
    if not isinstance(records, dict):
        raise ValueError("holdout freeze has no protected-artifact map")
    verified_paths: list[str] = []
    for key in sorted(records):
        record = records[key]
        if not isinstance(record, dict) or record.get("path") != key:
            raise ValueError(f"protected artifact key/path mismatch: {key}")
        relative_path = Path(key)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"protected artifact path is not repository-relative: {key}")
        try:
            base_bytes = git(repo_root, "show", f"{freeze_base}:{key}", text=False)
        except ValueError as exc:
            raise ValueError(
                f"protected artifact did not exist at freeze base: {key}"
            ) from exc
        assert isinstance(base_bytes, bytes)
        base_blob = str(git(repo_root, "rev-parse", f"{freeze_base}:{key}")).strip()
        if (
            len(base_bytes) != int(record.get("bytes", -1))
            or sha256_bytes(base_bytes) != record.get("sha256")
            or base_blob != record.get("git_blob")
        ):
            raise ValueError(f"protected artifact differs at freeze base: {key}")
        last_change = str(record.get("last_change_commit", ""))
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", last_change, freeze_base],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if ancestor.returncode != 0:
            raise ValueError(
                f"protected artifact last-change commit is after freeze base: {key}"
            )
        observed_last_change = str(
            git(repo_root, "log", "-1", "--format=%H", freeze_base, "--", key)
        ).strip()
        if observed_last_change != last_change:
            raise ValueError(
                f"protected artifact last-change commit differs at freeze base: {key}"
            )
        verified_paths.append(key)
    return {
        "status": "PASS",
        "freeze_base_commit": freeze_base,
        "protected_record_count": len(verified_paths),
        "paths": verified_paths,
        "method": (
            "git_show_freeze_base_path_blob_bytes_sha256_and_exact_"
            "last_change_ancestry"
        ),
    }


def validate_freeze_manifest(
    config: dict[str, Any], freeze: dict[str, Any], *, repo_root: Path
) -> dict[str, dict[str, Any]]:
    protected = validate_freeze_manifest_schema(config, freeze)
    observed = verify_freeze_base_artifacts(repo_root, freeze)
    if observed != freeze["freeze_base_artifact_verification"]:
        raise ValueError("freeze-base artifact verification could not be reproduced")
    return protected


def freeze_transport(
    config_path: Path,
    *,
    output_path: Path | None = None,
    repo_root: Path = ROOT,
    run_tests: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config_path = repo_path(repo_root, config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    expected_output = repo_path(repo_root, config["source"]["freeze_manifest"])
    output = expected_output if output_path is None else repo_path(repo_root, output_path)
    if output != expected_output:
        raise ValueError("output path differs from the registered freeze manifest")
    if output.exists():
        raise FileExistsError(f"freeze manifest already exists: {output}")
    repository_state = require_clean_pushed_head(repo_root, config["repository"])
    config_info = committed_file_info(repo_root, config_path)
    frozen_science = verify_frozen_science(repo_root, config)
    calibration = verify_calibration_evidence(repo_root, config)
    absence = require_no_outcome_or_holdout_evidence(repo_root, config)
    transport_files = verify_transport_files(repo_root, config)
    source_archive_members = verify_source_archive_members(repo_root, config)
    focused = run_focused_tests(repo_root, config) if run_tests else {
        "status": "SKIPPED",
        "test_files": sorted(EXPECTED_FOCUSED_TESTS),
        "command": [],
        "returncode": 0,
        "stdout": "skipped only by direct test invocation",
    }
    if str(git(repo_root, "status", "--porcelain=v1", "--untracked-files=all")).strip():
        raise ValueError("worktree changed while the freeze gate was running")
    protected_records = [
        config_info,
        *frozen_science.values(),
        *calibration["cloud_manifests"].values(),
        *(
            record
            for cell_records in calibration["bundles"].values()
            for record in cell_records.values()
        ),
        *transport_files.values(),
        *source_archive_members.values(),
    ]
    protected_artifacts = merge_protected_artifacts(*protected_records)
    inventory_contract = expected_freeze_inventory(config)
    result = {
        "transport_id": config["transport_id"],
        "experiment_id": config["experiment_id"],
        "manifest_schema_version": config["freeze_schema_version"],
        "stage": "H4_holdout_transport_freeze_determination",
        "status": "PASS",
        "scientific_data_generated": False,
        "scientific_payload_or_outcome_inspected": False,
        "freeze_base_commit": repository_state["head"],
        "repository": repository_state,
        "config": config_info,
        "frozen_science": frozen_science,
        "calibration_evidence": calibration,
        "inventory_contract": inventory_contract,
        "pre_outcome_absence_checks": absence,
        "transport_artifacts": transport_files,
        "authenticated_bootstrap_archive_members": source_archive_members,
        "protected_artifacts": protected_artifacts,
        "focused_tests": focused,
        "freeze_base_artifact_verification": {},
        "rule": (
            "This manifest must be committed and pushed before any calibration "
            "outcome is calculated. After calibration adjudication, each eligible "
            "cell must dynamically bind its exact committed LTT determination and "
            "terminal lock hashes before its sole registered holdout launch."
        ),
    }
    result["freeze_base_artifact_verification"] = verify_freeze_base_artifacts(
        repo_root, result
    )
    validate_freeze_manifest(config, result, repo_root=repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(canonical_json_bytes(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = freeze_transport(args.config, output_path=args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
