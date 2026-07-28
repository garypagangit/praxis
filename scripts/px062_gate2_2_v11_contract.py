#!/usr/bin/env python
"""Shared fail-closed contract for PX-062 Gate 2.2 v1.1 execution.

The v1.1 experiment deliberately reuses the qualified model collector and
cloud entry point.  Every stateful path around them is versioned here so the
failed v1 label audit can never be mistaken for launch-ready evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable


EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-1-20260728"
PROTOCOL_VERSION = "2.2.1"
FINAL_CONFIG_STATUS = "FROZEN_PREREGISTERED"
FINAL_RESOLUTION_STATUS = "UNANIMOUS_REVERIFIED_AGAINST_AUDITED_FINAL_ANSWER"
EXPECTED_TASKS_SHA256 = (
    "68f776fe51ce3d2bd7eef42124448a1a6f58c0b0c6213fbd34b4b1e1e155ddbb"
)
EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256 = (
    "542cf05140c9bd3fe2e54fac41d2f7b077c6180f8084593d5412949c64377633"
)
DEFAULT_JOB_NAME = "px062-g22-v11-confirm1-20260728"
S3_PREFIX = (
    "experiments/px062-skill-provenance/"
    "gate2-2-context-structured-v1-1-20260728"
)

CONFIG_PATH = "configs/px062_skill_selection_gate2_2_v1_1_20260728.json"
GATE_DIR = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728"
)
MANIFEST_DIR = Path("manifests/px062_gate2_2_v1_1_20260728")
TASKS_PATH = f"{GATE_DIR}/frozen_inputs/tasks.jsonl"
ANSWER_KEY_PATH = f"{GATE_DIR}/frozen_inputs/answer_key.jsonl"
CATALOG_PATH = f"{GATE_DIR}/frozen_inputs/registry_catalog.json"
BENCHMARK_MANIFEST_PATH = f"{GATE_DIR}/frozen_inputs/benchmark_manifest.json"
AUDIT_PROTOCOL_PATH = f"{GATE_DIR}/LABEL_AUDIT_PROTOCOL_V1_1_20260728.md"
AUDIT_RESOLUTION_PATH = f"{GATE_DIR}/label_audit_resolution.json"
AUDIT_PROVISIONAL_RESOLUTION_PATH = (
    f"{GATE_DIR}/label_audit_provisional_resolution.json"
)
AUDIT_EVIDENCE_MANIFEST_PATH = f"{GATE_DIR}/label_audit_evidence_manifest.json"
CONFORMANCE_PATH = (
    "manifests/px062_gate2_2_v1_1_20260728/tokenizer_conformance.json"
)
COLLECTION_OUTPUT_DIR = "outputs/px062_gate2_2_v1_1"
SEALED_CONFIRMATION_DIR = Path(GATE_DIR) / "sealed_confirmation"
CONFIRMATORY_RESULT_PATH = Path(GATE_DIR) / "PX062_GATE2_2_V1_1_CONFIRMATORY_RESULT.json"

COLLECTOR_PATH = "scripts/run_px062_gate2_2_models.py"
ENTRYPOINT_PATH = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/sagemaker_entry.py"
)
REQUIREMENTS_GIT_PATH = (
    "cloud_jobs/px062_gate2_2_context_structured_20260728/requirements.txt"
)
CHECKSUM_REQUIREMENTS_PATH = "requirements-px062-evidence.txt"
SAGEMAKER_POLICY_PATH = (
    "configs/aws_px062_gate2_2_v1_1_sagemaker_s3_policy_20260728.json"
)
OPERATOR_FETCH_POLICY_PATH = (
    "configs/aws_px062_gate2_2_v1_1_operator_fetch_s3_policy_20260728.json"
)

AUDIT_RUNNER_PATH = "scripts/run_px062_gate2_2_v11_blind_audit.py"
AUDIT_TEST_PATH = "tests/test_px062_gate2_2_v11_blind_audit.py"
AUDIT_VERIFIER_PATH = "scripts/verify_px062_gate2_2_v11_label_audits.py"
LABEL_FINALIZER_PATH = "scripts/finalize_px062_gate2_2_v11_labels.py"
BENCHMARK_BUILDER_PATH = "scripts/build_px062_gate2_2_v11_benchmark.py"
TOKENIZER_CHECKER_PATH = "scripts/check_px062_gate2_2_v11_tokenizer_conformance.py"
BUNDLE_BUILDER_PATH = "scripts/build_px062_gate2_2_v11_bundle.py"
LAUNCH_REGISTRAR_PATH = "scripts/register_px062_gate2_2_v11_launch.py"
LAUNCHER_PATH = "scripts/launch_px062_gate2_2_v11_registered.py"
FETCH_REGISTRAR_PATH = "scripts/register_px062_gate2_2_v11_fetch.py"
FETCHER_PATH = "scripts/fetch_px062_gate2_2_v11_results.py"
ADJUDICATOR_PATH = "scripts/adjudicate_px062_gate2_2_v11.py"
EXECUTION_TEST_PATH = "tests/test_px062_gate2_2_v11_execution_migration.py"

FROZEN_EVIDENCE_PATHS = {
    "audit_1_predictions": f"{GATE_DIR}/label_audit_1_predictions.jsonl",
    "audit_2_predictions": f"{GATE_DIR}/label_audit_2_predictions.jsonl",
    "audit_1_run": f"{GATE_DIR}/label_audit_1_run.json",
    "audit_2_run": f"{GATE_DIR}/label_audit_2_run.json",
    "audit_evidence_manifest": AUDIT_EVIDENCE_MANIFEST_PATH,
    "audit_protocol": AUDIT_PROTOCOL_PATH,
    "audit_provisional_resolution": AUDIT_PROVISIONAL_RESOLUTION_PATH,
    "audit_resolution": AUDIT_RESOLUTION_PATH,
    "preregistration_addendum": f"{GATE_DIR}/PX062_GATE2_2_V1_1_PREREG_ADDENDUM_20260728.md",
    "v1_invalidation": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_invalidation.json"
    ),
    "collector": COLLECTOR_PATH,
    "adjudicator": ADJUDICATOR_PATH,
    "audit_runner": AUDIT_RUNNER_PATH,
    "label_finalizer": LABEL_FINALIZER_PATH,
    "label_verifier": AUDIT_VERIFIER_PATH,
    "benchmark_builder": BENCHMARK_BUILDER_PATH,
    "tokenizer_conformance_checker": TOKENIZER_CHECKER_PATH,
    "tokenizer_conformance_manifest": CONFORMANCE_PATH,
    "bundle_builder": BUNDLE_BUILDER_PATH,
    "launch_registrar": LAUNCH_REGISTRAR_PATH,
    "launcher": LAUNCHER_PATH,
    "fetch_registrar": FETCH_REGISTRAR_PATH,
    "fetcher": FETCHER_PATH,
    "collector_tests": "tests/test_px062_gate2_2_collector.py",
    "adjudicator_tests": "tests/test_px062_gate2_2_adjudicator.py",
    "blind_audit_tests": AUDIT_TEST_PATH,
    "benchmark_tests": "tests/test_px062_gate2_2_v11_construction.py",
    "execution_migration_tests": EXECUTION_TEST_PATH,
    "checksum_requirements": CHECKSUM_REQUIREMENTS_PATH,
    "sagemaker_policy": SAGEMAKER_POLICY_PATH,
    "operator_fetch_policy": OPERATOR_FETCH_POLICY_PATH,
}

HEX64 = re.compile(r"[0-9a-f]{64}")
BlobReader = Callable[[Path, str, str], bytes]


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strict_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=no_duplicates)
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def git_blob(root: Path, revision: str, relative_path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{revision}:{relative_path}"], cwd=root
    )


def validate_frozen_config(
    config: dict[str, Any],
    *,
    input_bytes: dict[str, bytes] | None = None,
) -> None:
    """Reject every pre-freeze or cross-version configuration."""

    if config.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("v1.1 experiment identity drift")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("v1.1 protocol version drift")
    if config.get("status") != FINAL_CONFIG_STATUS:
        raise ValueError("v1.1 configuration is not frozen and preregistered")
    if config.get("collection_output_dir") != COLLECTION_OUTPUT_DIR:
        raise ValueError("v1.1 collection output directory drift")
    if config.get("frozen_inputs") != {
        "tasks": TASKS_PATH,
        "answer_key": ANSWER_KEY_PATH,
        "registry_catalog": CATALOG_PATH,
        "benchmark_manifest": BENCHMARK_MANIFEST_PATH,
    }:
        raise ValueError("v1.1 frozen-input path contract drift")
    integrity = config.get("source_integrity")
    if not isinstance(integrity, dict) or set(integrity) != {
        "tasks_sha256",
        "answer_key_sha256",
        "registry_catalog_sha256",
        "benchmark_manifest_sha256",
    } or any(not isinstance(value, str) or not HEX64.fullmatch(value) for value in integrity.values()):
        raise ValueError("v1.1 source-integrity hashes are not frozen")
    protocol = config.get("label_audit_protocol")
    if not isinstance(protocol, dict) or any(
        not isinstance(protocol.get(field), str)
        or not HEX64.fullmatch(protocol[field])
        for field in ("runner_sha256", "protocol_sha256", "tests_sha256")
    ):
        raise ValueError("v1.1 label-audit code and protocol are not frozen")
    if "PENDING" in json.dumps(config, sort_keys=True):
        raise ValueError("v1.1 configuration still contains a pending marker")
    if input_bytes is not None:
        observed = {
            "tasks_sha256": sha256_bytes(input_bytes[TASKS_PATH]),
            "answer_key_sha256": sha256_bytes(input_bytes[ANSWER_KEY_PATH]),
            "registry_catalog_sha256": sha256_bytes(input_bytes[CATALOG_PATH]),
            "benchmark_manifest_sha256": sha256_bytes(
                input_bytes[BENCHMARK_MANIFEST_PATH]
            ),
        }
        if observed != integrity:
            raise ValueError("v1.1 source-integrity hashes differ from frozen inputs")


def validate_final_resolution(
    resolution: dict[str, Any], input_bytes: dict[str, bytes]
) -> None:
    if resolution.get("status") != FINAL_RESOLUTION_STATUS:
        raise ValueError("v1.1 unanimous final label resolution is missing")
    if resolution.get("all_labels_independently_agreed") is not True:
        raise ValueError("v1.1 label resolution is not unanimously agreed")
    if resolution.get("cross_audit_disagreement_task_ids") != []:
        raise ValueError("v1.1 label resolution contains disagreements")
    if not isinstance(resolution.get("audits"), list) or len(resolution["audits"]) != 2:
        raise ValueError("v1.1 label resolution does not bind two audits")
    final_inputs = resolution.get("final_inputs")
    expected_names = {
        "tasks.jsonl": TASKS_PATH,
        "answer_key.jsonl": ANSWER_KEY_PATH,
        "registry_catalog.json": CATALOG_PATH,
        "benchmark_manifest.json": BENCHMARK_MANIFEST_PATH,
    }
    if not isinstance(final_inputs, dict) or set(final_inputs) != set(expected_names):
        raise ValueError("v1.1 label resolution final-input schema drift")
    for name, path in expected_names.items():
        record = final_inputs[name]
        raw = input_bytes[path]
        if record != {"sha256": sha256_bytes(raw), "bytes": len(raw)}:
            raise ValueError(f"v1.1 label resolution input binding drift: {name}")


def validate_label_freeze(
    root: Path,
    *,
    source_commit: str | None = None,
    blob_reader: BlobReader = git_blob,
) -> dict[str, Any]:
    """Authenticate the label-freeze gate from a worktree or Git commit."""

    root = root.resolve()

    def read(path: str) -> bytes:
        if source_commit is None:
            return (root / path).read_bytes()
        return blob_reader(root, source_commit, path)

    paths = (CONFIG_PATH, TASKS_PATH, ANSWER_KEY_PATH, CATALOG_PATH, BENCHMARK_MANIFEST_PATH)
    raw = {path: read(path) for path in paths}
    config = strict_json_bytes(raw[CONFIG_PATH], "v1.1 frozen config")
    validate_frozen_config(config, input_bytes=raw)
    resolution_raw = read(AUDIT_RESOLUTION_PATH)
    resolution = strict_json_bytes(resolution_raw, "v1.1 final label resolution")
    validate_final_resolution(resolution, raw)
    return {
        "config": config,
        "config_sha256": sha256_bytes(raw[CONFIG_PATH]),
        "resolution": resolution,
        "resolution_sha256": sha256_bytes(resolution_raw),
        "source_integrity": dict(config["source_integrity"]),
    }
