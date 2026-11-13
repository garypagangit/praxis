#!/usr/bin/env python
"""Build, upload, and register (but do not launch) PX-062 Gate 2.2."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.build_px062_gate2_2_benchmark import (
        CANONICAL_AUDIT_MODELS,
        CHECKPOINT_CONFIG_PATH,
        CHECKPOINT_TRACKED_PATHS,
        validate_repository_checkpoint as validate_pending_repository_checkpoint,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from build_px062_gate2_2_benchmark import (  # type: ignore[no-redef]
        CANONICAL_AUDIT_MODELS,
        CHECKPOINT_CONFIG_PATH,
        CHECKPOINT_TRACKED_PATHS,
        validate_repository_checkpoint as validate_pending_repository_checkpoint,
    )

try:
    from scripts.build_px062_gate2_2_bundle import (
        ARCHIVE_MEMBERS,
        CONFIG,
        build,
        sha256_file,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from build_px062_gate2_2_bundle import ARCHIVE_MEMBERS, CONFIG, build, sha256_file

try:
    from scripts.run_px062_gate2_2_blind_audit import (
        AuditError,
        strict_json_loads,
        verify_pair,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from run_px062_gate2_2_blind_audit import (  # type: ignore[no-redef]
        AuditError,
        strict_json_loads,
        verify_pair,
    )

try:
    from scripts.check_px062_gate2_2_tokenizer_conformance import (
        CONTEXT_WINDOW_TOKENS,
        EXPECTED_ARMS,
        EXPECTED_DEPENDENCIES,
        EXPECTED_MODEL_REVISIONS,
        semantic_config_projection_record,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from check_px062_gate2_2_tokenizer_conformance import (  # type: ignore[no-redef]
        CONTEXT_WINDOW_TOKENS,
        EXPECTED_ARMS,
        EXPECTED_DEPENDENCIES,
        EXPECTED_MODEL_REVISIONS,
        semantic_config_projection_record,
    )

try:
    from scripts.fetch_px062_gate2_2_results import (
        CHECKSUM_REQUIREMENTS_PATH,
        OPERATOR_FETCH_POLICY_PATH,
        checksum_runtime_record,
        operator_fetch_policy_record,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from fetch_px062_gate2_2_results import (  # type: ignore[no-redef]
        CHECKSUM_REQUIREMENTS_PATH,
        OPERATOR_FETCH_POLICY_PATH,
        checksum_runtime_record,
        operator_fetch_policy_record,
    )


DEFAULT_BUCKET = "praxis-garypagan-272615233626-us-east-1"
DEFAULT_REGION = "us-east-1"
DEFAULT_ROLE = (
    "arn:aws:iam::272615233626:role/service-role/"
    "AmazonSageMaker-ExecutionRole-20260416T191047"
)
DEFAULT_IMAGE = (
    "763104351884.dkr.ecr.us-east-1.amazonaws.com/"
    "pytorch-training@sha256:"
    "01d8dfbde8f6e47a20e5b1e4033e105976663f2641084921b8769ee6998ef807"
)
PREFIX = (
    "experiments/px062-skill-provenance/"
    "gate2-2-context-structured-20260728"
)
MANIFEST_DIR = Path("manifests/px062_gate2_2_20260728")
FROZEN_EVIDENCE_PATHS = {
    "audit_1_predictions": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_1_predictions.jsonl"
    ),
    "audit_2_predictions": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_2_predictions.jsonl"
    ),
    "audit_1_run": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_1_run.json"
    ),
    "audit_2_run": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_2_run.json"
    ),
    "audit_evidence_manifest": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_evidence_manifest.json"
    ),
    "audit_protocol": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/LABEL_AUDIT_PROTOCOL_20260728.md"
    ),
    "audit_provisional_resolution": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/"
        "label_audit_provisional_resolution.json"
    ),
    "audit_resolution": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_resolution.json"
    ),
    "preregistration": (
        "reports/coding_agent_skill_provenance/"
        "PX062_GATE2_2_CONTEXT_STRUCTURED_PREREG_20260728.md"
    ),
    "prelaunch_redesign_record": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/"
        "PRELAUNCH_REDESIGN_RECORD_20260728.md"
    ),
    "collector": "scripts/run_px062_gate2_2_models.py",
    "adjudicator": "scripts/adjudicate_px062_gate2_2.py",
    "audit_runner": "scripts/run_px062_gate2_2_blind_audit.py",
    "label_finalizer": "scripts/finalize_px062_gate2_2_labels.py",
    "label_verifier": "scripts/verify_px062_gate2_2_label_audits.py",
    "benchmark_builder": "scripts/build_px062_gate2_2_benchmark.py",
    "tokenizer_conformance_checker": (
        "scripts/check_px062_gate2_2_tokenizer_conformance.py"
    ),
    "tokenizer_conformance_manifest": (
        "manifests/px062_gate2_2_20260728/tokenizer_conformance.json"
    ),
    "collector_tests": "tests/test_px062_gate2_2_collector.py",
    "adjudicator_tests": "tests/test_px062_gate2_2_adjudicator.py",
    "blind_audit_tests": "tests/test_px062_gate2_2_blind_audit.py",
    "benchmark_tests": "tests/test_px062_gate2_2_benchmark.py",
    "tokenizer_conformance_tests": (
        "tests/test_px062_gate2_2_tokenizer_conformance.py"
    ),
    "bundle_tests": "tests/test_px062_gate2_2_bundle.py",
    "launch_tests": "tests/test_px062_gate2_2_launch.py",
    "fetch_tests": "tests/test_px062_gate2_2_fetch.py",
    "checksum_requirements": CHECKSUM_REQUIREMENTS_PATH,
    "operator_fetch_policy": OPERATOR_FETCH_POLICY_PATH,
}

LABEL_AUDIT_MANIFEST_KEYS = {
    "schema_version",
    "created_utc",
    "answer_key_contents_included",
    "pending_answer_checkpoint_hash_included",
    "repository_checkpoint",
    "audits",
    "global_session_ids",
    "isolated_workdirs",
    "cross_audit_input_prompt_schema_hashes_match",
    "artifacts",
}
PairVerifier = Callable[..., dict[str, Any]]
GitBlobReader = Callable[[Path, str, str], bytes]
GitObjectReader = Callable[[Path, str, str], str]
GitAncestorCheck = Callable[[Path, str, str], bool]

FINAL_CONFIG_STATUS = "FROZEN_PREREGISTERED"
EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256 = (
    "8dcf3f8c939c8dcabaf90f4b1a8dd745c032274ded85a2ae4444424a3f79aeed"
)
EXPECTED_CONFORMANCE_RUN_CONFIG_SHA256 = (
    "46960b69431e05d8dc23afae0dc0d542d718d29246f4c2d4beac49bab60dd83a"
)
EXPECTED_CONTEXT_HEADROOM = {
    "Qwen/Qwen2.5-7B-Instruct": 29452,
    "mistralai/Mistral-7B-Instruct-v0.3": 28950,
}
CONFIG_PATH = "configs/px062_skill_selection_gate2_2_v1_0_20260728.json"
TASKS_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl"
)
ANSWER_KEY_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/answer_key.jsonl"
)
CATALOG_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json"
)
BENCHMARK_MANIFEST_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs/benchmark_manifest.json"
)
AUDIT_RUNNER_PATH = "scripts/run_px062_gate2_2_blind_audit.py"
AUDIT_TEST_PATH = "tests/test_px062_gate2_2_blind_audit.py"
AUDIT_PROTOCOL_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/LABEL_AUDIT_PROTOCOL_20260728.md"
)
CONFORMANCE_PATH = "manifests/px062_gate2_2_20260728/tokenizer_conformance.json"
CONFORMANCE_TOP_LEVEL_KEYS = {
    "schema_version",
    "checked_at_utc",
    "checker",
    "message_constructor_source",
    "python",
    "dependency_versions",
    "config_sha256",
    "semantic_config_projection",
    "tasks_sha256",
    "registry_catalog_sha256",
    "task_count",
    "option_maps_and_catalogs_validated",
    "structured_choices",
    "structured_response_form",
    "open_response_max_new_tokens",
    "arms",
    "models",
    "minimum_model_context_window_tokens",
    "strict_context_comparison",
    "pass",
    "interpretation",
}
CONFORMANCE_MODEL_KEYS = {
    "model_id",
    "revision",
    "eos_token_id",
    "choice_count",
    "choice_set_sha256",
    "choice_token_length_min",
    "choice_token_length_max",
    "choice_roundtrip_failures",
    "open_response_budget_probe",
    "maximum_prompt_tokens",
    "maximum_prompt_first_task_id",
    "maximum_prompt_tie_count",
    "maximum_prompt_plus_response_tokens",
    "maximum_prompt_plus_response_first_task_id",
    "maximum_prompt_plus_response_tie_count",
    "response_token_allowance_by_arm",
    "minimum_context_headroom_tokens",
    "rendered_model_task_arm_sets",
    "rendered_evidence_sha256",
    "saved_tokenizer_artifacts",
}


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(root: Path, revision: str, relative_path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source commit must be a full lowercase SHA")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative_path:
        raise ValueError(f"unsafe source-commit evidence path: {relative_path}")
    return subprocess.check_output(
        ["git", "show", f"{revision}:{relative_path}"], cwd=root
    )


def strict_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (AuditError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON: {label}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {label}")
    return value


def _hash_record(path: str, raw: bytes) -> dict[str, Any]:
    return {"path": path, "sha256": sha256_bytes(raw)}


def validate_final_config_and_conformance(
    root: Path,
    source_commit: str,
    *,
    blob_reader: GitBlobReader = git_blob,
) -> dict[str, Any]:
    """Validate final config semantics and the pre-launch conformance receipt."""

    raw = {
        path: blob_reader(root, source_commit, path)
        for path in (
            CONFIG_PATH,
            TASKS_PATH,
            ANSWER_KEY_PATH,
            CATALOG_PATH,
            BENCHMARK_MANIFEST_PATH,
            AUDIT_RUNNER_PATH,
            AUDIT_TEST_PATH,
            AUDIT_PROTOCOL_PATH,
            CONFORMANCE_PATH,
            "scripts/check_px062_gate2_2_tokenizer_conformance.py",
            "scripts/run_px062_gate2_2_models.py",
        )
    }
    config = strict_json_bytes(raw[CONFIG_PATH], "final config")
    receipt = strict_json_bytes(raw[CONFORMANCE_PATH], "conformance receipt")

    if config.get("status") != FINAL_CONFIG_STATUS:
        raise ValueError("final config is not FROZEN_PREREGISTERED")
    projection = semantic_config_projection_record(config)
    if (
        projection.get("sha256") != EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256
        or receipt.get("semantic_config_projection") != projection
    ):
        raise ValueError("final config semantic projection drift")

    source_integrity = config.get("source_integrity")
    expected_integrity = {
        "tasks_sha256": sha256_bytes(raw[TASKS_PATH]),
        "answer_key_sha256": sha256_bytes(raw[ANSWER_KEY_PATH]),
        "registry_catalog_sha256": sha256_bytes(raw[CATALOG_PATH]),
        "benchmark_manifest_sha256": sha256_bytes(raw[BENCHMARK_MANIFEST_PATH]),
    }
    if source_integrity != expected_integrity:
        raise ValueError("final config source-integrity hashes are not frozen")
    audit_protocol = config.get("label_audit_protocol")
    if not isinstance(audit_protocol, dict):
        raise ValueError("final config label-audit protocol is missing")
    if audit_protocol.get("runner_sha256") != sha256_bytes(raw[AUDIT_RUNNER_PATH]):
        raise ValueError("final config audit-runner hash drift")
    if audit_protocol.get("protocol_sha256") != sha256_bytes(raw[AUDIT_PROTOCOL_PATH]):
        raise ValueError("final config audit-protocol hash drift")
    if audit_protocol.get("tests_sha256") != sha256_bytes(raw[AUDIT_TEST_PATH]):
        raise ValueError("final config audit-tests hash drift")

    if set(receipt) != CONFORMANCE_TOP_LEVEL_KEYS or receipt.get(
        "schema_version"
    ) != "px062-gate2.2-tokenizer-conformance-v3":
        raise ValueError("stale or malformed tokenizer-conformance receipt")
    if receipt.get("pass") is not True:
        raise ValueError("tokenizer-conformance receipt did not pass")
    checked_at = receipt.get("checked_at_utc")
    if not isinstance(checked_at, str) or not checked_at.endswith("Z"):
        raise ValueError("tokenizer-conformance receipt timestamp drift")
    try:
        parsed_checked_at = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid tokenizer-conformance receipt timestamp") from exc
    if parsed_checked_at.utcoffset() != timezone.utc.utcoffset(parsed_checked_at):
        raise ValueError("tokenizer-conformance receipt timestamp is not UTC")

    checker_path = "scripts/check_px062_gate2_2_tokenizer_conformance.py"
    collector_path = "scripts/run_px062_gate2_2_models.py"
    if receipt.get("checker") != _hash_record(checker_path, raw[checker_path]):
        raise ValueError("tokenizer-conformance checker binding drift")
    if receipt.get("message_constructor_source") != _hash_record(
        collector_path, raw[collector_path]
    ):
        raise ValueError("tokenizer-conformance constructor binding drift")
    if receipt.get("config_sha256") != EXPECTED_CONFORMANCE_RUN_CONFIG_SHA256:
        raise ValueError("tokenizer-conformance run-config identity drift")
    if (
        receipt.get("tasks_sha256") != expected_integrity["tasks_sha256"]
        or receipt.get("registry_catalog_sha256")
        != expected_integrity["registry_catalog_sha256"]
    ):
        raise ValueError("tokenizer-conformance frozen-input hash drift")
    if receipt.get("dependency_versions") != EXPECTED_DEPENDENCIES:
        raise ValueError("tokenizer-conformance dependency drift")
    if receipt.get("arms") != list(EXPECTED_ARMS):
        raise ValueError("tokenizer-conformance arm drift")
    exact_receipt_values = {
        "task_count": 1032,
        "option_maps_and_catalogs_validated": 1032,
        "structured_choices": 44,
        "structured_response_form": '{"choice":"Snnn"}',
        "open_response_max_new_tokens": 32,
        "minimum_model_context_window_tokens": CONTEXT_WINDOW_TOKENS,
        "strict_context_comparison": "prompt_plus_response_tokens < 32768",
    }
    for key, expected in exact_receipt_values.items():
        if receipt.get(key) != expected:
            raise ValueError(f"tokenizer-conformance {key} drift")

    model_rows = receipt.get("models")
    if not isinstance(model_rows, list) or [
        row.get("model_id") if isinstance(row, dict) else None for row in model_rows
    ] != list(EXPECTED_MODEL_REVISIONS):
        raise ValueError("tokenizer-conformance model order drift")
    rendered_total = 0
    choice_set_sha256: str | None = None
    for row in model_rows:
        model_id = row["model_id"]
        if set(row) != CONFORMANCE_MODEL_KEYS:
            raise ValueError(f"tokenizer-conformance model schema drift: {model_id}")
        if row.get("revision") != EXPECTED_MODEL_REVISIONS[model_id]:
            raise ValueError(f"tokenizer-conformance revision drift: {model_id}")
        if (
            row.get("choice_count") != 44
            or row.get("choice_roundtrip_failures") != 0
            or row.get("open_response_budget_probe", {}).get("token_budget") != 32
        ):
            raise ValueError(f"tokenizer-conformance choice/probe drift: {model_id}")
        current_choice_hash = row.get("choice_set_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(current_choice_hash)):
            raise ValueError(f"tokenizer-conformance choice hash drift: {model_id}")
        if choice_set_sha256 is None:
            choice_set_sha256 = str(current_choice_hash)
        elif current_choice_hash != choice_set_sha256:
            raise ValueError("tokenizer-conformance choice sets differ by model")
        totals = row.get("maximum_prompt_plus_response_tokens")
        if not isinstance(totals, dict) or set(totals) != set(EXPECTED_ARMS) or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in totals.values()
        ):
            raise ValueError(f"tokenizer-conformance token maxima drift: {model_id}")
        headroom = CONTEXT_WINDOW_TOKENS - max(totals.values())
        if (
            headroom <= 0
            or row.get("minimum_context_headroom_tokens") != headroom
            or headroom != EXPECTED_CONTEXT_HEADROOM[model_id]
        ):
            raise ValueError(f"tokenizer-conformance context headroom drift: {model_id}")
        rendered = row.get("rendered_model_task_arm_sets")
        if rendered != 1032 * len(EXPECTED_ARMS):
            raise ValueError(f"tokenizer-conformance rendered count drift: {model_id}")
        rendered_total += rendered
    if rendered_total != 10320:
        raise ValueError("tokenizer-conformance total rendered count is not 10320")
    return {
        "config": config,
        "config_sha256": sha256_bytes(raw[CONFIG_PATH]),
        "conformance": receipt,
        "conformance_sha256": sha256_bytes(raw[CONFORMANCE_PATH]),
        "source_integrity": expected_integrity,
    }


def checksum_sha256_base64(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return base64.b64encode(digest.digest()).decode("ascii")


def git_object_id(root: Path, revision: str, relative_path: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("checkpoint commit must be a full lowercase SHA")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative_path:
        raise ValueError(f"unsafe checkpoint evidence path: {relative_path}")
    return subprocess.check_output(
        ["git", "rev-parse", f"{revision}:{relative_path}"],
        cwd=root,
        text=True,
    ).strip()


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    if not re.fullmatch(r"[0-9a-f]{40}", ancestor) or not re.fullmatch(
        r"[0-9a-f]{40}", descendant
    ):
        raise ValueError("checkpoint ancestry requires full lowercase SHAs")
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            capture_output=True,
        ).returncode
        == 0
    )


def validate_historical_audit_checkpoint(
    root: Path,
    checkpoint: Any,
    *,
    descendant_commit: str | None = None,
    blob_reader: GitBlobReader = git_blob,
    object_reader: GitObjectReader = git_object_id,
    ancestor_check: GitAncestorCheck = git_is_ancestor,
) -> dict[str, Any]:
    """Authenticate the pending audit checkpoint against its actual Git commit."""

    if not isinstance(checkpoint, dict):
        raise ValueError("repository checkpoint is not an object")
    head = checkpoint.get("head_commit")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("repository checkpoint head commit drift")
    tracked = checkpoint.get("tracked_files")
    if not isinstance(tracked, dict) or set(tracked) != set(CHECKPOINT_TRACKED_PATHS):
        raise ValueError("repository checkpoint tracked-file set drift")

    historical: dict[str, bytes] = {}
    for path in CHECKPOINT_TRACKED_PATHS:
        record = tracked.get(path)
        if not isinstance(record, dict) or set(record) != {
            "head_blob",
            "sha256",
            "bytes",
        }:
            raise ValueError(f"repository checkpoint tracked-file schema drift: {path}")
        raw = blob_reader(root, head, path)
        if (
            record.get("head_blob") != object_reader(root, head, path)
            or record.get("sha256") != sha256_bytes(raw)
            or record.get("bytes") != len(raw)
        ):
            raise ValueError(f"repository checkpoint Git binding drift: {path}")
        historical[path] = raw

    validated = validate_pending_repository_checkpoint(
        checkpoint,
        candidate_tasks_raw=historical[CHECKPOINT_TRACKED_PATHS[0]],
        candidate_catalog_raw=historical[CHECKPOINT_TRACKED_PATHS[1]],
        candidate_answers_raw=historical[CHECKPOINT_TRACKED_PATHS[2]],
        candidate_manifest_raw=historical[CHECKPOINT_TRACKED_PATHS[3]],
    )
    config_raw = historical[CHECKPOINT_CONFIG_PATH]
    config = strict_json_bytes(config_raw, "pending audit checkpoint config")
    if (
        checkpoint.get("config_sha256") != sha256_bytes(config_raw)
        or config.get("status")
        != "REDESIGN_PENDING_FRESH_CORPUS_AND_DUAL_LABEL_AUDIT"
        or config.get("source_integrity") != checkpoint.get("source_integrity")
        or config.get("label_audit_protocol")
        != checkpoint.get("label_audit_protocol")
    ):
        raise ValueError("repository checkpoint pending config binding drift")
    if descendant_commit is not None and not ancestor_check(
        root, head, descendant_commit
    ):
        raise ValueError("repository checkpoint is not an ancestor of final source")
    return validated


def validate_label_audit_evidence_manifest(
    root: Path,
    *,
    pair_verifier: PairVerifier = verify_pair,
    source_commit: str | None = None,
    checkpoint_validator: Callable[..., dict[str, Any]] = (
        validate_historical_audit_checkpoint
    ),
) -> dict[str, Any]:
    """Read-only validation of the sealed audit pair and its evidence manifest."""

    root = root.resolve()
    relative_path = FROZEN_EVIDENCE_PATHS["audit_evidence_manifest"]
    manifest_path = (root / relative_path).resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("label-audit evidence manifest path escapes repository") from exc
    if not manifest_path.is_file():
        raise ValueError("label-audit evidence manifest is missing")
    try:
        manifest = strict_json_loads(manifest_path.read_text(encoding="utf-8"))
    except (AuditError, UnicodeDecodeError) as exc:
        raise ValueError("invalid label-audit evidence manifest") from exc
    if not isinstance(manifest, dict) or set(manifest) != LABEL_AUDIT_MANIFEST_KEYS:
        raise ValueError("label-audit evidence manifest schema drift")
    if (
        manifest.get("schema_version")
        != "px062-gate2.2-label-audit-evidence-manifest-v1"
        or manifest.get("answer_key_contents_included") is not False
        or manifest.get("pending_answer_checkpoint_hash_included") is not True
        or manifest.get("cross_audit_input_prompt_schema_hashes_match") is not True
    ):
        raise ValueError("label-audit evidence manifest policy drift")
    created_utc = manifest.get("created_utc")
    if not isinstance(created_utc, str) or not created_utc.endswith("Z"):
        raise ValueError("label-audit evidence manifest timestamp drift")
    try:
        created = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid label-audit evidence manifest timestamp") from exc
    if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(created):
        raise ValueError("label-audit evidence manifest timestamp is not UTC")

    checkpoint_validator(
        root,
        manifest.get("repository_checkpoint"),
        descendant_commit=source_commit,
    )
    audits = manifest.get("audits")
    accepted_sessions: list[set[str]] = []
    if not isinstance(audits, list) or len(audits) != 2:
        raise ValueError("label-audit evidence manifest must contain two audit slots")
    for slot, (audit, model) in enumerate(
        zip(audits, CANONICAL_AUDIT_MODELS, strict=True), start=1
    ):
        if not isinstance(audit, dict) or set(audit) != {
            "slot",
            "model",
            "audit_id",
            "accepted_session_ids",
            "prediction_sha256",
            "sidecar_sha256",
        }:
            raise ValueError(f"label-audit evidence slot {slot} schema drift")
        sessions = audit.get("accepted_session_ids")
        if (
            audit.get("slot") != slot
            or audit.get("model") != model
            or not isinstance(audit.get("audit_id"), str)
            or not audit["audit_id"]
            or not isinstance(sessions, list)
            or len(sessions) != 43
            or not all(isinstance(value, str) and value for value in sessions)
            or len(set(sessions)) != 43
            or not re.fullmatch(r"[0-9a-f]{64}", str(audit.get("prediction_sha256")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(audit.get("sidecar_sha256")))
        ):
            raise ValueError(f"label-audit evidence slot {slot} binding drift")
        accepted_sessions.append(set(sessions))
    if accepted_sessions[0] & accepted_sessions[1]:
        raise ValueError("label-audit accepted sessions overlap across slots")
    global_sessions = manifest.get("global_session_ids")
    if (
        not isinstance(global_sessions, dict)
        or set(global_sessions)
        != {
            "accepted_count",
            "all_attempt_count",
            "all_unique_and_cross_audit_disjoint",
        }
        or global_sessions.get("accepted_count") != 86
        or not isinstance(global_sessions.get("all_attempt_count"), int)
        or isinstance(global_sessions.get("all_attempt_count"), bool)
        or global_sessions["all_attempt_count"] < 86
        or global_sessions.get("all_unique_and_cross_audit_disjoint") is not True
    ):
        raise ValueError("label-audit global session provenance drift")
    isolated = manifest.get("isolated_workdirs")
    if isolated != {
        "attempt_count": global_sessions["all_attempt_count"],
        "all_unique": True,
    }:
        raise ValueError("label-audit isolated-workdir provenance drift")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("label-audit evidence manifest artifacts are missing")
    seen_paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "role",
            "path",
            "bytes",
            "sha256",
        }:
            raise ValueError("label-audit evidence manifest artifact schema drift")
        path_text = artifact.get("path")
        if not isinstance(path_text, str) or not path_text:
            raise ValueError("label-audit evidence manifest artifact path is invalid")
        artifact_path = (root / path_text).resolve()
        try:
            canonical_path = artifact_path.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"label-audit evidence artifact escapes repository: {path_text}"
            ) from exc
        if canonical_path != path_text or path_text in seen_paths:
            raise ValueError(
                f"label-audit evidence artifact path is noncanonical or repeated: {path_text}"
            )
        seen_paths.add(path_text)
        if artifact_path.name.casefold() == "answer_key.jsonl":
            raise ValueError("answer key leaked into label-audit evidence manifest")
        if not artifact_path.is_file():
            raise ValueError(f"label-audit evidence artifact is missing: {path_text}")
        raw = artifact_path.read_bytes()
        if (
            not isinstance(artifact.get("bytes"), int)
            or isinstance(artifact.get("bytes"), bool)
            or artifact["bytes"] != len(raw)
            or artifact.get("sha256") != sha256_bytes(raw)
        ):
            raise ValueError(
                f"label-audit evidence artifact binding drift: {path_text}"
            )

    try:
        reconstructed = pair_verifier(
            root,
            write_manifest=False,
            verification_mode="historical",
        )
    except AuditError as exc:
        raise ValueError("sealed label-audit pair verification failed") from exc
    if not isinstance(reconstructed, dict):
        raise ValueError("label-audit pair verifier returned an invalid manifest")
    reconstructed = dict(reconstructed)
    reconstructed["created_utc"] = created_utc
    if reconstructed != manifest:
        raise ValueError(
            "label-audit evidence manifest does not match the read-only pair verifier"
        )
    return manifest


def aws(profile: str, region: str, *arguments: str) -> dict[str, Any]:
    command = [
        "aws",
        *arguments,
        "--profile",
        profile,
        "--region",
        region,
        "--output",
        "json",
    ]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout or "{}")


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=root, text=True
    ).strip()


def validate_git_state(root: Path, source_commit: str) -> dict[str, Any]:
    head = git(root, "rev-parse", "HEAD")
    if source_commit != head:
        raise ValueError("source commit must equal current HEAD")
    if git(root, "status", "--porcelain"):
        raise ValueError("registration requires a clean worktree")
    remote_refs = [
        line.strip()
        for line in git(root, "branch", "-r", "--contains", source_commit).splitlines()
        if line.strip()
    ]
    if not remote_refs:
        raise ValueError("source commit is not present on a remote ref")
    branch = git(root, "branch", "--show-current")
    return {"head": head, "branch": branch, "remote_refs": remote_refs}


def validate_new_key(
    profile: str, region: str, bucket: str, key: str
) -> None:
    listing = aws(
        profile,
        region,
        "s3api",
        "list-object-versions",
        "--bucket",
        bucket,
        "--prefix",
        key,
    )
    collisions = [
        row
        for collection in ("Versions", "DeleteMarkers")
        for row in listing.get(collection, [])
        if row.get("Key") == key
    ]
    if collisions:
        raise FileExistsError(f"registered source key already has versions: {key}")


def is_explicit_resource_not_found(error: subprocess.CalledProcessError) -> bool:
    text = f"{error.stderr or ''}\n{error.stdout or ''}"
    return bool(
        re.search(
            r"\(ResourceNotFound(?:Exception)?\)|"
            r"[\"'](?:Code|code)[\"']\s*:\s*"
            r"[\"']ResourceNotFound(?:Exception)?[\"']",
            text,
        )
    )


def require_explicit_training_job_absence(
    profile: str, region: str, job_name: str
) -> dict[str, Any]:
    """Require DescribeTrainingJob itself to return ResourceNotFound."""

    try:
        aws(
            profile,
            region,
            "sagemaker",
            "describe-training-job",
            "--training-job-name",
            job_name,
        )
    except subprocess.CalledProcessError as error:
        if not is_explicit_resource_not_found(error):
            raise
        return {
            "method": "DescribeTrainingJob",
            "job_name": job_name,
            "result": "ResourceNotFound",
            "authorized_initial_absence": True,
        }
    raise FileExistsError(f"training job already exists: {job_name}")


def register(
    *,
    root: Path,
    profile: str,
    source_commit: str,
    job_name: str,
    bucket: str,
    region: str,
    role_arn: str,
    image: str,
) -> dict[str, Any]:
    root = root.resolve()
    state = validate_git_state(root, source_commit)
    validate_label_audit_evidence_manifest(root, source_commit=source_commit)
    validate_final_config_and_conformance(root, source_commit)
    checksum_requirements_raw = subprocess.check_output(
        ["git", "show", f"{source_commit}:{CHECKSUM_REQUIREMENTS_PATH}"], cwd=root
    )
    checksum_runtime = checksum_runtime_record(checksum_requirements_raw)
    operator_policy_raw = subprocess.check_output(
        ["git", "show", f"{source_commit}:{OPERATOR_FETCH_POLICY_PATH}"], cwd=root
    )
    operator_policy = operator_fetch_policy_record(operator_policy_raw, bucket)
    versioning = aws(
        profile, region, "s3api", "get-bucket-versioning", "--bucket", bucket
    )
    if versioning.get("Status") != "Enabled":
        raise ValueError("S3 bucket versioning must be enabled")
    initial_job_absence = require_explicit_training_job_absence(
        profile, region, job_name
    )

    manifest_dir = root / MANIFEST_DIR
    request_path = manifest_dir / "confirmatory_request.json"
    registration_path = manifest_dir / "confirmatory_registration.json"
    if request_path.exists() or registration_path.exists():
        raise FileExistsError("confirmatory launch registration already exists")

    source_key = f"{PREFIX}/code/{job_name}/source.tar.gz"
    output_prefix = f"s3://{bucket}/{PREFIX}/output"
    validate_new_key(profile, region, bucket, source_key)
    config_raw = subprocess.check_output(
        ["git", "show", f"{source_commit}:{CONFIG}"], cwd=root
    )
    config = json.loads(config_raw)
    frozen_evidence: dict[str, Any] = {}
    archive_member_paths = set(ARCHIVE_MEMBERS)
    for label, path in FROZEN_EVIDENCE_PATHS.items():
        raw = subprocess.check_output(
            ["git", "show", f"{source_commit}:{path}"], cwd=root
        )
        frozen_evidence[label] = {
            "path": path,
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
            "included_in_collection_source_bundle": path in archive_member_paths,
        }
    with tempfile.TemporaryDirectory(prefix="px062-g22-register-") as temporary:
        temp = Path(temporary)
        first_path = temp / "source-first.tar.gz"
        second_path = temp / "source-second.tar.gz"
        first = build(root, source_commit, first_path)
        second = build(root, source_commit, second_path)
        if first["archive_sha256"] != second["archive_sha256"]:
            raise ValueError("two deterministic source builds differ")
        if first_path.read_bytes() != second_path.read_bytes():
            raise ValueError("two source builds differ byte-for-byte")
        source_sha = first["archive_sha256"]
        checksum_b64 = checksum_sha256_base64(first_path)
        put = aws(
            profile,
            region,
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            source_key,
            "--body",
            str(first_path),
            "--server-side-encryption",
            "AES256",
            "--checksum-algorithm",
            "SHA256",
            "--metadata",
            f"sha256={source_sha},source-commit={source_commit}",
        )
        version_id = put.get("VersionId")
        if not version_id or version_id == "null":
            raise ValueError("source upload did not return a non-null version ID")
        head = aws(
            profile,
            region,
            "s3api",
            "head-object",
            "--bucket",
            bucket,
            "--key",
            source_key,
            "--version-id",
            version_id,
            "--checksum-mode",
            "ENABLED",
        )
        if head.get("VersionId") != version_id:
            raise ValueError("uploaded source version mismatch")
        if int(head.get("ContentLength", -1)) != first_path.stat().st_size:
            raise ValueError("uploaded source size mismatch")
        if head.get("Metadata", {}).get("sha256") != source_sha:
            raise ValueError("uploaded source metadata hash mismatch")
        if head.get("ChecksumSHA256") != checksum_b64:
            raise ValueError("uploaded source checksum mismatch")
        source_attributes = aws(
            profile,
            region,
            "s3api",
            "get-object-attributes",
            "--bucket",
            bucket,
            "--key",
            source_key,
            "--version-id",
            version_id,
            "--object-attributes",
            "ETag",
            "Checksum",
            "ObjectSize",
        )
        if (
            source_attributes.get("VersionId") != version_id
            or str(source_attributes.get("ETag", "")).strip('"')
            != str(head.get("ETag", "")).strip('"')
            or source_attributes.get("ObjectSize") != first_path.stat().st_size
            or source_attributes.get("Checksum")
            != {
                "ChecksumSHA256": checksum_b64,
                "ChecksumType": "FULL_OBJECT",
            }
        ):
            raise ValueError("versioned source GetObjectAttributes preflight mismatch")
        output_probe_prefix = f"{PREFIX}/output/{job_name}/"
        output_listing = aws(
            profile,
            region,
            "s3api",
            "list-object-versions",
            "--bucket",
            bucket,
            "--prefix",
            output_probe_prefix,
        )
        output_versions = [
            row
            for row in output_listing.get("Versions", [])
            if str(row.get("Key", "")).startswith(output_probe_prefix)
        ]
        output_markers = [
            row
            for row in output_listing.get("DeleteMarkers", [])
            if str(row.get("Key", "")).startswith(output_probe_prefix)
        ]
        if output_listing.get("IsTruncated") is True or output_versions or output_markers:
            raise FileExistsError("registered output prefix already has object versions")
        operator_access_preflight = {
            "source_version_attributes": {
                "method": "GetObjectAttributes",
                "version_id": version_id,
                "etag": str(head.get("ETag", "")).strip('"'),
                "bytes": first_path.stat().st_size,
                "checksum_sha256_base64": checksum_b64,
                "checksum_type": "FULL_OBJECT",
                "authorized": True,
            },
            "output_version_listing": {
                "method": "ListObjectVersions",
                "prefix": output_probe_prefix,
                "authorized": True,
                "existing_versions": 0,
                "existing_delete_markers": 0,
            },
        }
        version_listing = aws(
            profile,
            region,
            "s3api",
            "list-object-versions",
            "--bucket",
            bucket,
            "--prefix",
            source_key,
        )
        exact_versions = [
            row
            for row in version_listing.get("Versions", [])
            if row.get("Key") == source_key
        ]
        exact_markers = [
            row
            for row in version_listing.get("DeleteMarkers", [])
            if row.get("Key") == source_key
        ]
        if (
            len(exact_versions) != 1
            or exact_markers
            or exact_versions[0].get("VersionId") != version_id
            or exact_versions[0].get("IsLatest") is not True
        ):
            raise ValueError("uploaded source is not the sole latest object version")
        downloaded = temp / "source-download.tar.gz"
        aws(
            profile,
            region,
            "s3api",
            "get-object",
            "--bucket",
            bucket,
            "--key",
            source_key,
            "--version-id",
            version_id,
            str(downloaded),
        )
        if sha256_file(downloaded) != source_sha:
            raise ValueError("version-pinned source download hash mismatch")

        source_uri = f"s3://{bucket}/{source_key}"
        request = {
            "TrainingJobName": job_name,
            "AlgorithmSpecification": {
                "TrainingImage": image,
                "TrainingInputMode": "File",
            },
            "RoleArn": role_arn,
            "OutputDataConfig": {"S3OutputPath": output_prefix},
            "ResourceConfig": {
                "InstanceType": "ml.g5.2xlarge",
                "InstanceCount": 1,
                "VolumeSizeInGB": 200,
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": 86400},
            "HyperParameters": {
                "sagemaker_program": (
                    "cloud_jobs/px062_gate2_2_context_structured_20260728/"
                    "sagemaker_entry.py"
                ),
                "sagemaker_submit_directory": source_uri,
                "sagemaker_container_log_level": "20",
                "sagemaker_region": region,
            },
            "Environment": {
                "PX062_GATE22_CONFIG": CONFIG,
                "HF_HOME": "/opt/ml/input/data/huggingface",
                "TOKENIZERS_PARALLELISM": "false",
            },
            "EnableNetworkIsolation": False,
            "RetryStrategy": {"MaximumRetryAttempts": 0},
            "Tags": [
                {"Key": "praxis-experiment", "Value": "PX-062-Gate-2.2"},
                {"Key": "praxis-one-look", "Value": "confirmatory"},
            ],
        }
        request_raw = canonical_json_bytes(request)
        request_path.write_bytes(request_raw)
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        registration = {
            "schema_version": "px062-gate2.2-launch-registration-v1",
            "experiment_id": config["experiment_id"],
            "protocol_version": config["protocol_version"],
            "registered_at_utc": now,
            "branch": state["branch"],
            "source_commit": source_commit,
            "source_remote_refs": state["remote_refs"],
            "region": region,
            "job_name": job_name,
            "initial_job_absence": initial_job_absence,
            "request_file": request_path.relative_to(root).as_posix(),
            "request_sha256": sha256_bytes(request_raw),
            "source_bundle": {
                "bucket": bucket,
                "key": source_key,
                "version_id": version_id,
                "etag": str(head.get("ETag", "")).strip('"'),
                "sha256": source_sha,
                "checksum_sha256_base64": checksum_b64,
                "bytes": first_path.stat().st_size,
                "server_side_encryption": head.get("ServerSideEncryption"),
                "last_modified": head.get("LastModified"),
                "deterministic_second_build_sha256": second["archive_sha256"],
                "download_verification_sha256": sha256_file(downloaded),
                "manifest": first["manifest"],
            },
            "frozen_sources": {
                "config_sha256": sha256_bytes(config_raw),
                **config["source_integrity"],
            },
            "frozen_evidence": frozen_evidence,
            "checksum_runtime": checksum_runtime,
            "fetch_operator_policy": operator_policy,
            "operator_access_preflight": operator_access_preflight,
            "frozen_collection": {
                "tasks": config["expected_tasks"],
                "traces": config["expected_traces"],
                "models": config["models"],
                "arms": config["arms"],
                "instance_type": "ml.g5.2xlarge",
                "max_runtime_seconds": 86400,
                "container_image": image,
            },
            "role_arn": role_arn,
            "output_prefix": output_prefix,
            "one_look": {
                "allowed_training_job_creations": 1,
                "threshold_prompt_parser_or_label_changes_after_launch": 0,
                "answer_key_in_source_bundle": False,
            },
        }
        registration_path.write_bytes(canonical_json_bytes(registration))
    return registration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--job-name", default="px062-g22-confirm1-20260728")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--role-arn", default=DEFAULT_ROLE)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    registration = register(
        root=root,
        profile=args.profile,
        source_commit=args.source_commit,
        job_name=args.job_name,
        bucket=args.bucket,
        region=args.region,
        role_arn=args.role_arn,
        image=args.image,
    )
    print(
        json.dumps(
            {
                "job_name": registration["job_name"],
                "request_file": registration["request_file"],
                "source_sha256": registration["source_bundle"]["sha256"],
                "source_version_id": registration["source_bundle"]["version_id"],
                "status": "REGISTERED_NOT_LAUNCHED",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
