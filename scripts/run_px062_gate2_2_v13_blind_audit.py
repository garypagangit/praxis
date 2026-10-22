#!/usr/bin/env python
"""Run or verify one PX-062 Gate 2.2 v1.3 four-pass label audit.

Slots 1/3 use gpt-5.6-sol and slots 2/4 use gpt-5.6-terra. Every slot is a
fresh full 1,032-row pass in 43 stateless sessions. The qualified v1 engine
remains the mechanical execution core; this wrapper changes only the frozen
v1.3 paths and prospectively registered four-pass evidence topology.
"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterator

try:
    from scripts import run_px062_gate2_2_blind_audit as core
except ImportError:  # Direct ``python scripts/...`` execution.
    import run_px062_gate2_2_blind_audit as core  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SLOTS = (1, 2, 3, 4)
SLOT_MODELS = {
    1: "gpt-5.6-sol",
    2: "gpt-5.6-terra",
    3: "gpt-5.6-sol",
    4: "gpt-5.6-terra",
}
SLOT_STEMS = {
    slot: f"audit_{slot}_{SLOT_MODELS[slot]}" for slot in AUDIT_SLOTS
}
GATE_DIR = (
    ROOT
    / "reports"
    / "coding_agent_skill_provenance"
    / "gate2_2_context_structured_v1_3_20260728"
)
FROZEN_DIR = GATE_DIR / "frozen_inputs"
AUDIT_DIR = GATE_DIR / "label_audits"
TASKS_PATH = FROZEN_DIR / "tasks.jsonl"
CATALOG_PATH = FROZEN_DIR / "registry_catalog.json"
EXPECTED_TASKS_SHA256 = (
    "79becaa213147f98146777bdf1e0cee7baf0afd2cdbfb4226daae6a961d58b0c"
)
EXPECTED_CATALOG_SHA256 = (
    "97b751849bd26e6bd9f347d5153f4237d995e4e0f8eda289faaa18d75523b905"
)
EXPECTED_CODEX_VERSION = core.EXPECTED_CODEX_VERSION
EXPECTED_TASKS = core.EXPECTED_TASKS
BATCH_SIZE = core.BATCH_SIZE
EXPECTED_BATCHES = core.EXPECTED_BATCHES
ATTEMPT_TIMEOUT_SECONDS = core.ATTEMPT_TIMEOUT_SECONDS
TASK_ID_NAMESPACE = core.TASK_ID_NAMESPACE

CONFIG_RELATIVE_PATH = Path("configs/px062_skill_selection_gate2_2_v1_3_20260728.json")
ANSWER_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/frozen_inputs/answer_key.jsonl"
)
MANIFEST_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/frozen_inputs/benchmark_manifest.json"
)
SEED_RELATIVE_PATH = Path(
    "manifests/px062_gate2_2_v1_3_20260728/task_seed_bank.json"
)
PROTOCOL_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/"
    "LABEL_AUDIT_PROTOCOL_V1_3_20260728.md"
)
RUNNER_RELATIVE_PATH = Path("scripts/run_px062_gate2_2_v13_blind_audit.py")
TESTS_RELATIVE_PATH = Path("tests/test_px062_gate2_2_v13_blind_audit.py")
CORE_RELATIVE_PATH = Path("scripts/run_px062_gate2_2_blind_audit.py")
BUILDER_RELATIVE_PATH = Path("scripts/build_px062_gate2_2_v13_benchmark.py")
VERIFIER_RELATIVE_PATH = Path("scripts/verify_px062_gate2_2_v13_label_audits.py")
FINALIZER_RELATIVE_PATH = Path("scripts/finalize_px062_gate2_2_v13_labels.py")
BASE_BUILDER_RELATIVE_PATH = Path("scripts/build_px062_gate2_2_benchmark.py")
V11_BUILDER_RELATIVE_PATH = Path("scripts/build_px062_gate2_2_v11_benchmark.py")
V11_RUNNER_RELATIVE_PATH = Path("scripts/run_px062_gate2_2_v11_blind_audit.py")
V11_VERIFIER_RELATIVE_PATH = Path(
    "scripts/verify_px062_gate2_2_v11_label_audits.py"
)
V11_FINALIZER_RELATIVE_PATH = Path("scripts/finalize_px062_gate2_2_v11_labels.py")
V12_PAIR_MANIFEST_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/"
    "label_audit_evidence_manifest.json"
)
EXPECTED_V12_PAIR_MANIFEST_SHA256 = (
    "f34151882216c35196bd0c26d80f7603bb371187efe3862fa6eacc96ef4b90c0"
)
EXPECTED_V12_ACCEPTED_SESSION_IDS_SHA256 = (
    "893d9aba0182f9bf5ba5a612d59eb826e9878c5d45d321805c09e5c1c9f6e632"
)
TRACKED_CHECKPOINT_PATHS = (
    Path(
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_v1_3_20260728/frozen_inputs/tasks.jsonl"
    ),
    Path(
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_v1_3_20260728/frozen_inputs/registry_catalog.json"
    ),
    ANSWER_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATH,
    SEED_RELATIVE_PATH,
    CONFIG_RELATIVE_PATH,
    RUNNER_RELATIVE_PATH,
    CORE_RELATIVE_PATH,
    BUILDER_RELATIVE_PATH,
    BASE_BUILDER_RELATIVE_PATH,
    V11_BUILDER_RELATIVE_PATH,
    V11_RUNNER_RELATIVE_PATH,
    VERIFIER_RELATIVE_PATH,
    V11_VERIFIER_RELATIVE_PATH,
    FINALIZER_RELATIVE_PATH,
    V11_FINALIZER_RELATIVE_PATH,
    PROTOCOL_RELATIVE_PATH,
    TESTS_RELATIVE_PATH,
    V12_PAIR_MANIFEST_RELATIVE_PATH,
)
GOVERNANCE_EXECUTABLE_PATHS = (
    RUNNER_RELATIVE_PATH,
    CORE_RELATIVE_PATH,
    BUILDER_RELATIVE_PATH,
    BASE_BUILDER_RELATIVE_PATH,
    V11_BUILDER_RELATIVE_PATH,
    V11_RUNNER_RELATIVE_PATH,
    VERIFIER_RELATIVE_PATH,
    V11_VERIFIER_RELATIVE_PATH,
    FINALIZER_RELATIVE_PATH,
    V11_FINALIZER_RELATIVE_PATH,
)
IMMUTABLE_CURRENT_CONTROL_PATHS = (
    *GOVERNANCE_EXECUTABLE_PATHS,
    PROTOCOL_RELATIVE_PATH,
    TESTS_RELATIVE_PATH,
)

DISABLED_FEATURES = tuple(core.DISABLED_FEATURES)
CONFIG_EXACT_COMMAND_SHAPE = core.CONFIG_EXACT_COMMAND_SHAPE
PROMPT_TEMPLATE_VERSION = core.PROMPT_TEMPLATE_VERSION
PROMPT_TEMPLATE = core.PROMPT_TEMPLATE
AuditError = core.AuditError
EventPolicyError = core.EventPolicyError
sha256_bytes = core.sha256_bytes
sha256_file = core.sha256_file
strict_json_loads = core.strict_json_loads
read_expected_bytes = core.read_expected_bytes
read_jsonl_bytes = core.read_jsonl_bytes
load_catalog = core.load_catalog
validate_tasks = core.validate_tasks
canonical_json_bytes = core.canonical_json_bytes
task_id_for_prompt = core.task_id_for_prompt
make_batches = core.make_batches
project_tasks_for_auditor = core.project_tasks_for_auditor
build_prompt = core.build_prompt
build_output_schema = core.build_output_schema
validate_response = core.validate_response
validate_canonical_audit_rows = core.validate_canonical_audit_rows
build_command = core.build_command
validate_exact_recorded_command = core.validate_exact_recorded_command
inspect_event_log = core.inspect_event_log
execute_attempt = core.execute_attempt


def extract_exposed_thread_ids(raw: bytes) -> frozenset[str]:
    """Recover every valid thread ID exposed by a partial or invalid event log."""

    found: set[str] = set()
    for raw_line in raw.splitlines():
        try:
            line = raw_line.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        if not line:
            continue
        try:
            event = strict_json_loads(line)
        except AuditError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "thread.started"
            and isinstance(event.get("thread_id"), str)
            and event["thread_id"]
        ):
            found.add(event["thread_id"])
    return frozenset(found)


def extract_exposed_thread_id(raw: bytes) -> str | None:
    """Compatibility projection for callers that require exactly one ID."""

    found = extract_exposed_thread_ids(raw)
    return next(iter(found)) if len(found) == 1 else None


def output_paths(root: Path, slot: int) -> dict[str, Path]:
    if slot not in SLOT_MODELS:
        raise AuditError("audit slot must be 1, 2, 3, or 4")
    gate_dir = (
        root
        / "reports"
        / "coding_agent_skill_provenance"
        / "gate2_2_context_structured_v1_3_20260728"
    )
    return {
        "audit": gate_dir / f"label_audit_{slot}_predictions.jsonl",
        "sidecar": gate_dir / f"label_audit_{slot}_run.json",
        "evidence": gate_dir / "label_audits" / f"{SLOT_STEMS[slot]}.evidence",
        "manifest": gate_dir / "label_audit_evidence_manifest.json",
    }


def _sidecar_session_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    value = strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuditError(f"existing audit sidecar is not an object: {path}")
    found: set[str] = set()
    for batch in value.get("batches", []):
        for attempt in batch.get("attempts", []):
            session_id = attempt.get("session_id")
            if isinstance(session_id, str):
                found.add(session_id)
            exposed = attempt.get("exposed_session_ids", [])
            if not isinstance(exposed, list) or not all(
                isinstance(item, str) and item for item in exposed
            ):
                raise AuditError(f"existing audit sidecar has invalid exposed IDs: {path}")
            found.update(exposed)
    return found


def _validate_v12_pair_manifest_raw(raw: bytes) -> dict[str, Any]:
    if sha256_bytes(raw) != EXPECTED_V12_PAIR_MANIFEST_SHA256:
        raise AuditError("sealed v1.2 pair-manifest hash drift")
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AuditError("sealed v1.2 pair manifest is invalid JSON") from exc
    if not isinstance(value, dict):
        raise AuditError("sealed v1.2 pair manifest is not an object")
    if value.get("schema_version") != "px062-gate2.2-label-audit-evidence-manifest-v1":
        raise AuditError("sealed v1.2 pair-manifest schema drift")
    audits = value.get("audits")
    expected_models = ("gpt-5.6-sol", "gpt-5.6-terra")
    if not isinstance(audits, list) or len(audits) != 2:
        raise AuditError("sealed v1.2 pair manifest must contain two audit slots")
    accepted: list[str] = []
    for slot, (record, model) in enumerate(zip(audits, expected_models, strict=True), 1):
        if (
            not isinstance(record, dict)
            or record.get("slot") != slot
            or record.get("model") != model
        ):
            raise AuditError(f"sealed v1.2 audit slot {slot} identity drift")
        ids = record.get("accepted_session_ids")
        if (
            not isinstance(ids, list)
            or len(ids) != EXPECTED_BATCHES
            or len(set(ids)) != EXPECTED_BATCHES
            or not all(isinstance(item, str) and item for item in ids)
        ):
            raise AuditError(f"sealed v1.2 audit slot {slot} session provenance drift")
        accepted.extend(ids)
    global_sessions = value.get("global_session_ids")
    if (
        not isinstance(global_sessions, dict)
        or global_sessions.get("accepted_count") != 86
        or global_sessions.get("all_attempt_count") != 86
        or global_sessions.get("all_unique_and_cross_audit_disjoint") is not True
        or len(accepted) != 86
        or len(set(accepted)) != 86
    ):
        raise AuditError("sealed v1.2 global session provenance drift")
    session_ids_sha256 = sha256_bytes(canonical_json_bytes(sorted(accepted)))
    if session_ids_sha256 != EXPECTED_V12_ACCEPTED_SESSION_IDS_SHA256:
        raise AuditError("sealed v1.2 accepted-session identity drift")
    return {
        "session_ids": frozenset(accepted),
        "evidence": {
            "path": V12_PAIR_MANIFEST_RELATIVE_PATH.as_posix(),
            "sha256": EXPECTED_V12_PAIR_MANIFEST_SHA256,
            "accepted_session_count": 86,
            "accepted_session_ids_sha256": session_ids_sha256,
        },
    }


def v12_audit_blacklist(root: Path) -> dict[str, Any]:
    path = _safe_root_relative_path(
        root, V12_PAIR_MANIFEST_RELATIVE_PATH, "sealed v1.2 pair manifest"
    )
    _require_unaliased_regular_file(path, "sealed v1.2 pair manifest")
    return _validate_v12_pair_manifest_raw(path.read_bytes())


def v12_blacklist_evidence(root: Path) -> dict[str, Any]:
    return dict(v12_audit_blacklist(root)["evidence"])


def load_prior_session_ids(root: Path, slot: int) -> set[str]:
    found = set(v12_audit_blacklist(root)["session_ids"])
    for other in AUDIT_SLOTS:
        if other == slot:
            continue
        values = _sidecar_session_ids(output_paths(root, other)["sidecar"])
        if found.intersection(values):
            raise AuditError(
                "existing v1.3 sidecar reuses a blacklisted or prior Codex session ID"
            )
        found.update(values)
    return found


def _is_symlink_like(path: Path) -> bool:
    """Detect symbolic links, junctions, and other reparse-point objects."""

    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _safe_root_relative_path(root: Path, relative: str | Path, role: str) -> Path:
    """Validate every lexical component from the trusted root through the leaf."""

    root = Path(os.path.abspath(root))
    relative_path = Path(relative)
    relative_text = relative_path.as_posix()
    supplied_text = relative if isinstance(relative, str) else relative.as_posix()
    if (
        relative_path.is_absolute()
        or bool(relative_path.drive)
        or "\\" in supplied_text
        or any(part in {"", ".", ".."} for part in relative_path.parts)
        or relative_text != supplied_text
    ):
        raise AuditError(f"{role} path is not canonical root-relative POSIX")
    if _is_symlink_like(root):
        raise AuditError(f"{role} root is symlink-like")
    candidate = root
    for part in relative_path.parts:
        candidate = candidate / part
        if _is_symlink_like(candidate):
            raise AuditError(f"{role} path contains a symlink-like component")
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise AuditError(f"{role} path escapes root") from exc
    return candidate


def _require_unaliased_regular_file(path: Path, role: str) -> tuple[int, int] | None:
    """Require a regular one-link leaf and return a stable identity when exposed."""

    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise AuditError(f"{role} file is missing") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise AuditError(f"{role} is not a regular file")
    if metadata.st_nlink != 1:
        raise AuditError(f"{role} hard-link count is not exactly one")
    device = getattr(metadata, "st_dev", None)
    inode = getattr(metadata, "st_ino", None)
    if (
        isinstance(device, int)
        and isinstance(inode, int)
        and (device != 0 or inode != 0)
    ):
        return device, inode
    return None


def _artifact_matches(root: Path, relative: str, digest: str, role: str) -> None:
    if not isinstance(relative, str) or not relative or not isinstance(digest, str):
        raise AuditError(f"{role} artifact binding is invalid")
    path = _safe_root_relative_path(root, relative, role)
    _require_unaliased_regular_file(path, role)
    if sha256_file(path) != digest:
        raise AuditError(f"{role} artifact is missing or hash-invalid")


def validate_completed_predecessor_slot(
    root: Path,
    slot: int,
    *,
    expected_checkpoint: dict[str, Any] | None = None,
) -> set[str]:
    """Fully reconstruct one completed predecessor before allowing a successor."""

    root = Path(os.path.abspath(root))
    paths = output_paths(root, slot)
    for key, label in (("audit", "prediction"), ("sidecar", "sidecar")):
        relative = paths[key].relative_to(root)
        paths[key] = _safe_root_relative_path(
            root, relative, f"predecessor slot {slot} {label}"
        )
        _require_unaliased_regular_file(
            paths[key], f"predecessor slot {slot} {label}"
        )
    evidence_relative = paths["evidence"].relative_to(root)
    paths["evidence"] = _safe_root_relative_path(
        root, evidence_relative, f"predecessor slot {slot} evidence directory"
    )
    if not paths["evidence"].is_dir():
        raise AuditError(f"predecessor slot {slot} evidence directory is missing")
    sidecar = _strict_json_bytes(paths["sidecar"].read_bytes(), f"slot {slot} sidecar")
    if set(sidecar) != {
        "schema_version", "audit_id", "audit_slot", "started_utc", "finished_utc",
        "repository_checkpoint", "auditor", "inputs", "execution", "batches",
        "attestations", "output",
    }:
        raise AuditError(f"predecessor slot {slot} sidecar top-level schema drift")
    checkpoint = sidecar.get("repository_checkpoint")
    if not isinstance(checkpoint, dict):
        raise AuditError(f"predecessor slot {slot} checkpoint is missing")
    if expected_checkpoint is not None and checkpoint != expected_checkpoint:
        raise AuditError(f"predecessor slot {slot} checkpoint drift")
    if (
        sidecar.get("schema_version") != "px062-gate2.2-label-audit-run-v1"
        or sidecar.get("audit_slot") != slot
    ):
        raise AuditError(f"predecessor slot {slot} identity drift")

    auditor = sidecar.get("auditor")
    if not isinstance(auditor, dict) or set(auditor) != {
        "kind", "provider", "requested_model", "returned_model",
        "returned_model_disclosure", "model_snapshot", "cli_version",
        "codex_executable", "codex_executable_sha256",
        "model_reasoning_effort_requested", "sampling_parameters",
    }:
        raise AuditError(f"predecessor slot {slot} auditor schema drift")
    if (
        auditor.get("kind") != "codex_cli_model_session_batches"
        or auditor.get("provider") != "OpenAI"
        or auditor.get("requested_model") != SLOT_MODELS[slot]
        or auditor.get("returned_model") is not None
        or auditor.get("model_snapshot") is not None
        or auditor.get("returned_model_disclosure")
        != "codex --json does not echo model/snapshot in this CLI version"
        or auditor.get("cli_version") != EXPECTED_CODEX_VERSION
        or auditor.get("model_reasoning_effort_requested") != "high"
        or auditor.get("sampling_parameters")
        != "model-default; Codex CLI exposes no temperature/top_p/seed controls"
    ):
        raise AuditError(f"predecessor slot {slot} auditor identity drift")
    codex_executable = auditor.get("codex_executable")
    if not isinstance(codex_executable, str) or not codex_executable:
        raise AuditError(f"predecessor slot {slot} Codex executable is missing")
    executable_hash = auditor.get("codex_executable_sha256")
    if executable_hash is not None:
        executable_path = Path(codex_executable)
        if not executable_path.is_file() or sha256_file(executable_path) != executable_hash:
            raise AuditError(f"predecessor slot {slot} Codex executable hash drift")
        if core._codex_version(codex_executable) != EXPECTED_CODEX_VERSION:
            raise AuditError(f"predecessor slot {slot} Codex executable/version drift")

    frozen_dir = paths["manifest"].parent / "frozen_inputs"
    tasks_raw = read_expected_bytes(
        frozen_dir / "tasks.jsonl", EXPECTED_TASKS_SHA256, "frozen tasks"
    )
    catalog_raw = read_expected_bytes(
        frozen_dir / "registry_catalog.json", EXPECTED_CATALOG_SHA256, "registry catalog"
    )
    tasks = read_jsonl_bytes(tasks_raw, "frozen tasks")
    _, catalog_names, semantic_registry_raw = load_catalog(catalog_raw)
    validate_tasks(tasks, catalog_names)
    expected_batches = make_batches(tasks)
    gate_dir = paths["manifest"].parent
    inputs = sidecar.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "tasks", "registry_catalog", "semantic_registry_sha256",
        "prompt_template_version", "prompt_template_sha256", "protocol", "runner",
        "prior_audit_session_blacklist",
    }:
        raise AuditError(f"predecessor slot {slot} input-evidence schema drift")
    expected_inputs = {
        "tasks": {
            "path": (frozen_dir / "tasks.jsonl").relative_to(root).as_posix(),
            "bytes": len(tasks_raw), "rows": len(tasks), "sha256": EXPECTED_TASKS_SHA256,
        },
        "registry_catalog": {
            "path": (frozen_dir / "registry_catalog.json").relative_to(root).as_posix(),
            "bytes": len(catalog_raw), "names": len(catalog_names),
            "sha256": EXPECTED_CATALOG_SHA256,
        },
    }
    if inputs.get("tasks") != expected_inputs["tasks"]:
        raise AuditError(f"predecessor slot {slot} frozen-task evidence drift")
    if inputs.get("registry_catalog") != expected_inputs["registry_catalog"]:
        raise AuditError(f"predecessor slot {slot} registry evidence drift")
    if (
        inputs.get("semantic_registry_sha256") != sha256_bytes(semantic_registry_raw)
        or inputs.get("prompt_template_version") != PROMPT_TEMPLATE_VERSION
        or inputs.get("prompt_template_sha256")
        != sha256_bytes(PROMPT_TEMPLATE.encode("utf-8"))
        or inputs.get("prior_audit_session_blacklist") != v12_blacklist_evidence(root)
    ):
        raise AuditError(f"predecessor slot {slot} frozen input binding drift")
    expected_source_paths = {
        "protocol": (gate_dir / "LABEL_AUDIT_PROTOCOL_V1_3_20260728.md")
        .relative_to(root).as_posix(),
        "runner": RUNNER_RELATIVE_PATH.as_posix(),
    }
    for key, relative in expected_source_paths.items():
        if inputs.get(key) != {"path": relative, "sha256": sha256_file(root / relative)}:
            raise AuditError(f"predecessor slot {slot} {key} binding drift")
    if sidecar.get("execution") != {
        "batch_count": EXPECTED_BATCHES, "batch_size": BATCH_SIZE,
        "stateless": True, "ephemeral": True,
        "isolated_empty_workdir_per_attempt": True, "sandbox": "read-only",
        "disabled_features": list(DISABLED_FEATURES), "maximum_retries_per_batch": 1,
        "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
        "retry_reasons": ["transport_failure", "invalid_json_or_schema"],
    }:
        raise AuditError(f"predecessor slot {slot} execution contract drift")
    if sidecar.get("attestations") != {
        "answer_key_used_only_for_checkpoint_hash_and_pending_status": True,
        "answer_key_contents_never_serialized_into_model_prompt": True,
        "seed_bank_used_only_for_pending_governance_validation": True,
        "seed_bank_contents_never_serialized_into_model_prompt": True,
        "other_audit_labels_never_opened_or_passed": True,
        "no_resume_or_cross_batch_response_history": True,
        "no_semantic_retry": True, "no_model_fallback": True,
        "event_logs_reject_tool_command_web_and_mcp_calls": True,
        "all_session_ids_unique_within_audit": True,
        "session_ids_disjoint_from_all_existing_sidecars": True,
        "session_ids_disjoint_from_sealed_v1_2_blacklist": True,
        "fixed_slot_order_preflight_passed": True,
    }:
        raise AuditError(f"predecessor slot {slot} attestations drift")

    prediction_raw = paths["audit"].read_bytes()
    output = sidecar.get("output")
    if output != {
        "path": paths["audit"].relative_to(root).as_posix(),
        "bytes": len(prediction_raw), "rows": EXPECTED_TASKS,
        "sha256": sha256_bytes(prediction_raw),
        "encoding": "UTF-8 without BOM; LF; final LF",
    }:
        raise AuditError(f"predecessor slot {slot} output binding drift")
    prediction_rows = read_jsonl_bytes(prediction_raw, f"slot {slot} predictions")
    validate_canonical_audit_rows(prediction_rows, tasks, set(catalog_names))
    if b"".join(canonical_json_bytes(row) + b"\n" for row in prediction_rows) != prediction_raw:
        raise AuditError(f"predecessor slot {slot} predictions are not canonical JSONL")

    batches = sidecar.get("batches")
    if not isinstance(batches, list) or len(batches) != EXPECTED_BATCHES:
        raise AuditError(f"predecessor slot {slot} does not have 43 complete batches")
    accepted_ids: set[str] = set()
    all_ids: set[str] = set()
    all_workdirs: set[str] = set()
    expected_evidence_paths: set[str] = set()
    attempt_schema = {
        "attempt", "started_utc", "finished_utc", "command", "timeout_seconds",
        "prompt_sha256", "schema_path", "schema_sha256", "isolated_workdir",
        "isolated_workdir_empty_before_launch", "event_log_path", "event_log_sha256",
        "last_message_path", "last_message_exists", "last_message_sha256",
        "stderr_path", "stderr_sha256", "return_code", "transport_error", "session_id",
        "exposed_session_ids",
        "event_validation_error", "response_validation_error", "valid_response_sha256",
        "event_summary",
    }
    for number, batch in enumerate(batches, 1):
        if not isinstance(batch, dict) or set(batch) != {
            "batch_number", "task_count", "task_ids_sha256", "prompt_path",
            "prompt_sha256", "schema_sha256", "accepted_attempt", "attempts",
        }:
            raise AuditError(f"predecessor slot {slot} batch {number} schema drift")
        expected_task_batch = expected_batches[number - 1]
        with _bound_core():
            expected_prompt_raw = build_prompt(
                number, expected_task_batch, semantic_registry_raw
            )
            expected_schema_raw = canonical_json_bytes(
                build_output_schema(expected_task_batch, catalog_names)
            )
        expected_prompt_path = paths["evidence"] / f"batch_{number:02d}.prompt.txt"
        if (
            batch.get("batch_number") != number
            or batch.get("task_count") != BATCH_SIZE
            or batch.get("task_ids_sha256")
            != sha256_bytes(canonical_json_bytes([row["task_id"] for row in expected_task_batch]))
            or batch.get("prompt_path") != expected_prompt_path.relative_to(root).as_posix()
            or batch.get("prompt_sha256") != sha256_bytes(expected_prompt_raw)
            or batch.get("schema_sha256") != sha256_bytes(expected_schema_raw)
        ):
            raise AuditError(f"predecessor slot {slot} batch {number} reconstruction drift")
        _artifact_matches(root, batch["prompt_path"], batch["prompt_sha256"], "prompt")
        expected_evidence_paths.add(batch["prompt_path"])
        if expected_prompt_path.read_bytes() != expected_prompt_raw:
            raise AuditError(f"predecessor slot {slot} batch {number} prompt bytes drift")
        attempts = batch.get("attempts")
        accepted_attempt = batch.get("accepted_attempt")
        if (
            not isinstance(attempts, list) or len(attempts) not in {1, 2}
            or [item.get("attempt") for item in attempts] != list(range(1, len(attempts) + 1))
            or accepted_attempt != len(attempts)
        ):
            raise AuditError(f"predecessor slot {slot} batch {number} attempt sequence drift")
        accepted_record: dict[str, Any] | None = None
        valid_hashes: list[str] = []
        for attempt in attempts:
            if not isinstance(attempt, dict) or set(attempt) != attempt_schema:
                raise AuditError(f"predecessor slot {slot} batch {number} attempt schema drift")
            if attempt["attempt"] == accepted_attempt:
                accepted_record = attempt
            session_id = attempt.get("session_id")
            if session_id is not None and (
                not isinstance(session_id, str) or not session_id
            ):
                raise AuditError(f"predecessor slot {slot} has an invalid session ID")
            if (
                attempt.get("prompt_sha256") != batch["prompt_sha256"]
                or attempt.get("schema_sha256") != batch["schema_sha256"]
                or attempt.get("timeout_seconds") != ATTEMPT_TIMEOUT_SECONDS
            ):
                raise AuditError(f"predecessor slot {slot} batch {number} retry bytes drift")
            with _bound_core():
                workdir = validate_exact_recorded_command(
                    root=root, slot=slot, batch_number=number, attempt=attempt,
                    codex_executable=codex_executable,
                )
            if workdir in all_workdirs:
                raise AuditError(f"predecessor slot {slot} reuses an isolated workdir")
            all_workdirs.add(workdir)
            stem = f"batch_{number:02d}_attempt_{attempt['attempt']}"
            expected_paths = {
                "event_log_path": paths["evidence"] / f"{stem}.events.jsonl",
                "last_message_path": paths["evidence"] / f"{stem}.last-message.json",
                "stderr_path": paths["evidence"] / f"{stem}.stderr.txt",
                "schema_path": paths["evidence"] / f"{stem}.schema.json",
            }
            for field, expected_path in expected_paths.items():
                if attempt.get(field) != expected_path.relative_to(root).as_posix():
                    raise AuditError(f"predecessor slot {slot} batch {number} artifact path drift")
            for field in ("event_log", "stderr", "schema"):
                _artifact_matches(
                    root, attempt[f"{field}_path"], attempt[f"{field}_sha256"], field
                )
                expected_evidence_paths.add(attempt[f"{field}_path"])
            if expected_paths["schema_path"].read_bytes() != expected_schema_raw:
                raise AuditError(f"predecessor slot {slot} batch {number} schema bytes drift")
            event_raw = expected_paths["event_log_path"].read_bytes()
            exposed_session_ids = extract_exposed_thread_ids(event_raw)
            if attempt.get("exposed_session_ids") != sorted(exposed_session_ids):
                raise AuditError(
                    f"predecessor slot {slot} exposed-session evidence drift"
                )
            for exposed_session_id in exposed_session_ids:
                if exposed_session_id in all_ids:
                    raise AuditError(f"predecessor slot {slot} reuses a session ID")
                all_ids.add(exposed_session_id)
            event_info: dict[str, Any] | None = None
            try:
                event_info = inspect_event_log(event_raw, SLOT_MODELS[slot])
            except AuditError as exc:
                if attempt.get("event_validation_error") != str(exc):
                    raise AuditError(f"predecessor slot {slot} event evidence drift") from exc
                if attempt.get("event_summary") is not None:
                    raise AuditError(f"predecessor slot {slot} invalid event has summary")
                recovered_session_id = (
                    next(iter(exposed_session_ids))
                    if len(exposed_session_ids) == 1
                    else None
                )
                if recovered_session_id != session_id:
                    raise AuditError(f"predecessor slot {slot} invalid-event session drift")
            if event_info is not None:
                if (
                    exposed_session_ids != {event_info["session_id"]}
                    or event_info["session_id"] != session_id
                    or attempt.get("event_validation_error") is not None
                ):
                    raise AuditError(f"predecessor slot {slot} event/session drift")
            last_exists = attempt.get("last_message_exists")
            last_path = expected_paths["last_message_path"]
            if not isinstance(last_exists, bool) or last_path.exists() != last_exists:
                raise AuditError(f"predecessor slot {slot} last-message existence drift")
            response_rows: list[dict[str, Any]] | None = None
            response_error: str | None = None
            if last_exists:
                _artifact_matches(
                    root, attempt["last_message_path"], attempt["last_message_sha256"],
                    "last message",
                )
                expected_evidence_paths.add(attempt["last_message_path"])
                last_raw = last_path.read_bytes()
                if event_info is not None and event_info["agent_message_text"].encode("utf-8") != last_raw:
                    raise AuditError(f"predecessor slot {slot} event/last-message drift")
                try:
                    last_text = last_raw.decode("utf-8")
                    if last_text.startswith("\ufeff") or "\r" in last_text:
                        raise AuditError("last message has BOM or non-LF endings")
                    response_rows = validate_response(
                        strict_json_loads(last_text), expected_task_batch, set(catalog_names)
                    )
                except (AuditError, UnicodeDecodeError) as exc:
                    response_error = str(exc)
                if attempt.get("response_validation_error") != response_error:
                    raise AuditError(f"predecessor slot {slot} response evidence drift")
                expected_valid_hash = (
                    sha256_bytes(canonical_json_bytes(response_rows))
                    if response_rows is not None else None
                )
                if attempt.get("valid_response_sha256") != expected_valid_hash:
                    raise AuditError(f"predecessor slot {slot} valid-response hash drift")
                if event_info is not None:
                    summary = dict(event_info)
                    message = summary.pop("agent_message_text")
                    summary["agent_message_sha256"] = sha256_bytes(message.encode("utf-8"))
                    summary["last_message_binding"] = "exact_utf8_bytes"
                    if attempt.get("event_summary") != summary:
                        raise AuditError(f"predecessor slot {slot} event-summary drift")
            else:
                if (
                    attempt.get("last_message_sha256") is not None
                    or attempt.get("response_validation_error") != "last-message capture is missing"
                    or attempt.get("valid_response_sha256") is not None
                ):
                    raise AuditError(f"predecessor slot {slot} missing-response drift")
                if event_info is not None:
                    summary = dict(event_info)
                    message = summary.pop("agent_message_text")
                    summary["agent_message_sha256"] = sha256_bytes(message.encode("utf-8"))
                    summary["last_message_binding"] = None
                    if attempt.get("event_summary") != summary:
                        raise AuditError(f"predecessor slot {slot} event-summary drift")
            if attempt.get("valid_response_sha256") is not None:
                valid_hashes.append(attempt["valid_response_sha256"])
        if len(attempts) == 2 and (
            attempts[0].get("return_code") == 0
            and attempts[0].get("response_validation_error") is None
            and attempts[0].get("event_validation_error") is None
        ):
            raise AuditError(f"predecessor slot {slot} batch {number} unauthorized retry")
        if len(set(valid_hashes)) > 1:
            raise AuditError(f"predecessor slot {slot} batch {number} divergent retries")
        if (
            accepted_record is None or accepted_record.get("return_code") != 0
            or not isinstance(accepted_record.get("session_id"), str)
            or accepted_record.get("event_validation_error") is not None
            or accepted_record.get("response_validation_error") is not None
            or accepted_record.get("event_summary", {}).get("last_message_binding")
            != "exact_utf8_bytes"
        ):
            raise AuditError(f"predecessor slot {slot} batch {number} lacks accepted attempt")
        accepted_raw = (root / accepted_record["last_message_path"]).read_bytes()
        accepted_rows = validate_response(
            strict_json_loads(accepted_raw.decode("utf-8")), expected_task_batch,
            set(catalog_names),
        )
        predicted_rows = prediction_rows[(number - 1) * BATCH_SIZE : number * BATCH_SIZE]
        if accepted_rows != predicted_rows:
            raise AuditError(f"predecessor slot {slot} accepted response/predictions drift")
        accepted_ids.add(accepted_record["session_id"])
    if len(accepted_ids) != EXPECTED_BATCHES:
        raise AuditError(f"predecessor slot {slot} accepted-session count drift")
    if all_ids.intersection(v12_audit_blacklist(root)["session_ids"]):
        raise AuditError(f"predecessor slot {slot} reuses a sealed v1.2 session ID")
    _require_exact_evidence_directory_inventory(
        root, expected_evidence_paths, slots=(slot,)
    )
    return all_ids


def validate_slot_order(
    root: Path,
    slot: int,
    *,
    expected_checkpoint: dict[str, Any] | None = None,
) -> None:
    """Enforce the immutable execution order 1 -> 2 -> 3 -> 4."""

    if slot not in AUDIT_SLOTS:
        raise AuditError("audit slot must be 1, 2, 3, or 4")
    if output_paths(root, 1)["manifest"].exists():
        raise AuditError("consensus manifest already exists; no further slot may run")
    current = output_paths(root, slot)
    if current["audit"].exists() or current["sidecar"].exists() or current["evidence"].exists():
        raise AuditError(f"slot {slot} already has canonical evidence")
    for successor in range(slot + 1, 5):
        paths = output_paths(root, successor)
        if paths["audit"].exists() or paths["sidecar"].exists() or paths["evidence"].exists():
            raise AuditError(f"successor slot {successor} evidence exists before slot {slot}")
    accepted: set[str] = set()
    for predecessor in range(1, slot):
        ids = validate_completed_predecessor_slot(
            root,
            predecessor,
            expected_checkpoint=expected_checkpoint,
        )
        if accepted.intersection(ids):
            raise AuditError("predecessor slots reuse an accepted session ID")
        accepted.update(ids)


def reauthenticate_manifest_artifact_inventory(
    root: Path,
    manifest: dict[str, Any],
) -> None:
    """Re-read every raw manifest artifact and require exact bytes/hash/path."""

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise AuditError("evidence manifest artifact inventory is missing")
    roles: set[str] = set()
    paths: set[str] = set()
    resolved_paths: set[str] = set()
    file_identities: set[tuple[int, int]] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "role",
            "path",
            "bytes",
            "sha256",
        }:
            raise AuditError("evidence manifest artifact record drift")
        role = artifact["role"]
        relative = artifact["path"]
        byte_count = artifact["bytes"]
        digest = artifact["sha256"]
        if (
            not isinstance(role, str)
            or not role
            or role in roles
            or not isinstance(relative, str)
            or not relative
            or "\\" in relative
            or Path(relative).is_absolute()
            or Path(relative).as_posix() != relative
            or any(part in {"", ".", ".."} for part in Path(relative).parts)
            or relative in paths
            or not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
            or not isinstance(digest, str)
        ):
            raise AuditError("evidence manifest artifact identity drift")
        roles.add(role)
        paths.add(relative)
        path = _safe_root_relative_path(root, relative, "evidence artifact")
        file_identity = _require_unaliased_regular_file(path, "evidence artifact")
        resolved_identity = str(path.resolve(strict=True)).casefold()
        if resolved_identity in resolved_paths:
            raise AuditError(f"evidence artifact resolved-path alias: {relative}")
        resolved_paths.add(resolved_identity)
        if file_identity is not None:
            if file_identity in file_identities:
                raise AuditError(f"evidence artifact stable-file alias: {relative}")
            file_identities.add(file_identity)
        if (
            path.stat().st_size != byte_count
            or sha256_file(path) != digest
        ):
            raise AuditError(f"evidence artifact changed before seal/write: {relative}")
    _require_exact_evidence_directory_inventory(root, paths)


def _require_exact_evidence_directory_inventory(
    root: Path,
    manifest_paths: set[str],
    *,
    slots: tuple[int, ...] = AUDIT_SLOTS,
) -> None:
    """Require each canonical evidence directory's exact safe leaf-file set."""

    root = Path(os.path.abspath(root))
    for slot in slots:
        proposed = output_paths(root, slot)["evidence"]
        relative_directory = proposed.relative_to(root)
        directory = _safe_root_relative_path(
            root, relative_directory, f"slot {slot} canonical evidence directory"
        )
        if not directory.is_dir():
            raise AuditError(f"slot {slot} canonical evidence directory is unsafe or missing")

        expected: set[str] = set()
        for relative in manifest_paths:
            candidate = _safe_root_relative_path(root, relative, "evidence inventory")
            try:
                candidate.resolve(strict=True).relative_to(directory.resolve(strict=True))
            except ValueError:
                continue
            expected.add(relative)

        observed: set[str] = set()
        for child in directory.iterdir():
            child_relative = child.relative_to(root)
            child = _safe_root_relative_path(
                root, child_relative, f"slot {slot} evidence inventory"
            )
            if child.is_dir():
                raise AuditError(
                    f"slot {slot} evidence inventory contains an unlisted directory"
                )
            if child.is_file():
                _require_unaliased_regular_file(
                    child, f"slot {slot} evidence inventory"
                )
                observed.add(child.relative_to(root).as_posix())
            else:
                raise AuditError(
                    f"slot {slot} evidence inventory contains an unsafe object"
                )
        if observed != expected:
            missing = sorted(expected - observed)
            extra = sorted(observed - expected)
            raise AuditError(
                f"slot {slot} evidence directory inventory drift; "
                f"missing={missing}; extra={extra}"
            )


def expected_label_audit_protocol_config(
    *,
    runner_sha256: str,
    protocol_sha256: str,
    tests_sha256: str,
    core_runner_sha256: str,
    builder_sha256: str,
    base_builder_sha256: str,
    v11_builder_sha256: str,
    v11_runner_sha256: str,
    verifier_sha256: str,
    v11_verifier_sha256: str,
    finalizer_sha256: str,
    v11_finalizer_sha256: str,
) -> dict[str, Any]:
    return {
        "codex_cli_version": EXPECTED_CODEX_VERSION,
        "slot_models": {str(slot): SLOT_MODELS[slot] for slot in AUDIT_SLOTS},
        "model_reasoning_effort": "high",
        "sampling_parameters": (
            "model-default; Codex CLI exposes no temperature, top_p, or seed controls"
        ),
        "batches_per_auditor": EXPECTED_BATCHES,
        "tasks_per_batch": BATCH_SIZE,
        "stateless_ephemeral_sessions": True,
        "prompt_template_sha256": sha256_bytes(PROMPT_TEMPLATE.encode("utf-8")),
        "runner_sha256": runner_sha256,
        "protocol_sha256": protocol_sha256,
        "tests_sha256": tests_sha256,
        "governance_code": {
            "runner_core": {
                "path": CORE_RELATIVE_PATH.as_posix(),
                "sha256": core_runner_sha256,
            },
            "builder": {
                "path": BUILDER_RELATIVE_PATH.as_posix(),
                "sha256": builder_sha256,
            },
            "builder_base": {
                "path": BASE_BUILDER_RELATIVE_PATH.as_posix(),
                "sha256": base_builder_sha256,
            },
            "v11_builder": {
                "path": V11_BUILDER_RELATIVE_PATH.as_posix(),
                "sha256": v11_builder_sha256,
            },
            "v11_runner": {
                "path": V11_RUNNER_RELATIVE_PATH.as_posix(),
                "sha256": v11_runner_sha256,
            },
            "verifier": {
                "path": VERIFIER_RELATIVE_PATH.as_posix(),
                "sha256": verifier_sha256,
            },
            "verifier_base": {
                "path": V11_VERIFIER_RELATIVE_PATH.as_posix(),
                "sha256": v11_verifier_sha256,
            },
            "finalizer": {
                "path": FINALIZER_RELATIVE_PATH.as_posix(),
                "sha256": finalizer_sha256,
            },
            "finalizer_base": {
                "path": V11_FINALIZER_RELATIVE_PATH.as_posix(),
                "sha256": v11_finalizer_sha256,
            },
        },
        "filesystem_identity_policy": {
            "component_chain_symlink_junction_reparse_forbidden": True,
            "regular_file_hardlink_count_must_equal_one": True,
            "duplicate_stable_file_identities_forbidden": True,
            "canonical_evidence_directories_are_flat": True,
        },
        "prior_audit_session_blacklist": {
            "path": V12_PAIR_MANIFEST_RELATIVE_PATH.as_posix(),
            "sha256": EXPECTED_V12_PAIR_MANIFEST_SHA256,
            "accepted_session_count": 86,
            "accepted_session_ids_sha256": (
                EXPECTED_V12_ACCEPTED_SESSION_IDS_SHA256
            ),
        },
        "slot_execution_order": [1, 2, 3, 4],
        "model_facing_task_fields": ["task_id", "prompt"],
        "option_map_withheld_from_auditors": True,
        "exact_command_shape": CONFIG_EXACT_COMMAND_SHAPE,
        "acceptance": (
            "for every one of 1032 rows the frozen answer receives at least 3 of "
            "4 votes, including at least one Sol and at least one Terra vote"
        ),
        "full_audit_passes": 4,
        "accepted_sessions_required": 172,
        "single_dissent_tolerated": True,
        "semantic_retry_permitted": False,
        "disputed_only_rerun_permitted": False,
    }


def validate_pending_seed_governance(seed: dict[str, Any]) -> dict[str, Any]:
    governance = seed.get("label_governance")
    expected = {
        "required_independent_label_audits": 4,
        "completed_independent_label_audits": 0,
        "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
        "audit_1_status": "PENDING",
        "audit_2_status": "PENDING",
        "audit_3_status": "PENDING",
        "audit_4_status": "PENDING",
        "audit_resolution_status": "PENDING",
    }
    if not isinstance(governance, dict) or any(
        governance.get(key) != value for key, value in expected.items()
    ):
        raise AuditError("seed-bank label_governance is not pending 0/4")
    policy = governance.get("consensus_policy", {})
    if (
        policy.get("minimum_key_votes") != 3
        or policy.get("sol_slots") != [1, 3]
        or policy.get("terra_slots") != [2, 4]
        or policy.get("require_key_support_from_each_model_family") is not True
        or policy.get("semantic_retry_permitted") is not False
        or policy.get("disputed_only_rerun_permitted") is not False
    ):
        raise AuditError("seed-bank balanced-consensus policy drift")
    return {
        "required": 4,
        "completed": 0,
        "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
        "audit_1_status": "PENDING",
        "audit_2_status": "PENDING",
        "audit_3_status": "PENDING",
        "audit_4_status": "PENDING",
        "resolution_status": "PENDING",
    }


def _strict_json_file(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    return core._strict_json_file(path, label)


def _strict_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    return core._strict_json_bytes(raw, label)


def validate_git_checkpoint_state(**kwargs: str) -> None:
    core.validate_git_checkpoint_state(**kwargs)


def collect_repository_checkpoint(root: Path = ROOT) -> dict[str, Any]:
    root = Path(os.path.abspath(root))
    if _is_symlink_like(root):
        raise AuditError("repository checkpoint root is symlink-like")
    tracked_status = core._git(root, "status", "--porcelain=v1", "--untracked-files=no")
    head = core._git(root, "rev-parse", "HEAD")
    branch = core._git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    upstream_ref = core._git(
        root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    upstream_commit = core._git(root, "rev-parse", upstream_ref)
    remote_ref = f"refs/heads/{branch}"
    remote_output = core._git(root, "ls-remote", "--heads", "origin", remote_ref)
    rows = [line.split() for line in remote_output.splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) != 2 or rows[0][1] != remote_ref:
        raise AuditError("live origin branch did not resolve uniquely")
    remote_commit = rows[0][0]
    validate_git_checkpoint_state(
        tracked_status=tracked_status,
        head=head,
        branch=branch,
        upstream_ref=upstream_ref,
        upstream_commit=upstream_commit,
        remote_commit=remote_commit,
    )
    tracked_files: dict[str, dict[str, Any]] = {}
    tracked_identities: set[tuple[int, int]] = set()
    for relative in TRACKED_CHECKPOINT_PATHS:
        logical = relative.as_posix()
        path = _safe_root_relative_path(root, relative, "checkpoint control")
        identity = _require_unaliased_regular_file(path, "checkpoint control")
        if identity is not None:
            if identity in tracked_identities:
                raise AuditError(f"checkpoint stable-file alias: {logical}")
            tracked_identities.add(identity)
        if core._git(root, "ls-files", "--error-unmatch", "--", logical) != logical:
            raise AuditError(f"checkpoint file is not tracked exactly: {logical}")
        head_blob = core._git(root, "rev-parse", f"HEAD:{logical}")
        if head_blob != core._git(root, "hash-object", "--", logical):
            raise AuditError(f"checkpoint file differs from HEAD: {logical}")
        tracked_files[logical] = {
            "head_blob": head_blob,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    config, config_raw = _strict_json_file(root / CONFIG_RELATIVE_PATH, "audit config")
    if config.get("status") != "REDESIGN_PENDING_FRESH_CORPUS_AND_BALANCED_FOUR_PASS_LABEL_AUDIT":
        raise AuditError("audit config status is not the frozen v1.3 pending status")
    if config.get("expected_tasks") != EXPECTED_TASKS:
        raise AuditError("audit config expected_tasks drift")
    integrity = {
        "tasks_sha256": sha256_file(root / TRACKED_CHECKPOINT_PATHS[0]),
        "answer_key_sha256": sha256_file(root / ANSWER_RELATIVE_PATH),
        "registry_catalog_sha256": sha256_file(root / TRACKED_CHECKPOINT_PATHS[1]),
        "benchmark_manifest_sha256": sha256_file(root / MANIFEST_RELATIVE_PATH),
    }
    if config.get("source_integrity") != integrity:
        raise AuditError("audit config source_integrity does not match frozen artifacts")
    if integrity["tasks_sha256"] != EXPECTED_TASKS_SHA256:
        raise AuditError("repository checkpoint tasks hash differs from runner freeze")
    if integrity["registry_catalog_sha256"] != EXPECTED_CATALOG_SHA256:
        raise AuditError("repository checkpoint catalog hash differs from runner freeze")
    protocol = expected_label_audit_protocol_config(
        runner_sha256=sha256_file(root / RUNNER_RELATIVE_PATH),
        protocol_sha256=sha256_file(root / PROTOCOL_RELATIVE_PATH),
        tests_sha256=sha256_file(root / TESTS_RELATIVE_PATH),
        core_runner_sha256=sha256_file(root / CORE_RELATIVE_PATH),
        builder_sha256=sha256_file(root / BUILDER_RELATIVE_PATH),
        base_builder_sha256=sha256_file(root / BASE_BUILDER_RELATIVE_PATH),
        v11_builder_sha256=sha256_file(root / V11_BUILDER_RELATIVE_PATH),
        v11_runner_sha256=sha256_file(root / V11_RUNNER_RELATIVE_PATH),
        verifier_sha256=sha256_file(root / VERIFIER_RELATIVE_PATH),
        v11_verifier_sha256=sha256_file(root / V11_VERIFIER_RELATIVE_PATH),
        finalizer_sha256=sha256_file(root / FINALIZER_RELATIVE_PATH),
        v11_finalizer_sha256=sha256_file(root / V11_FINALIZER_RELATIVE_PATH),
    )
    if config.get("label_audit_protocol") != protocol:
        raise AuditError("audit config label_audit_protocol anchors drift")
    _validate_v12_pair_manifest_raw(
        (root / V12_PAIR_MANIFEST_RELATIVE_PATH).read_bytes()
    )
    answer_rows = read_jsonl_bytes(
        (root / ANSWER_RELATIVE_PATH).read_bytes(), "pending answer key"
    )
    if len(answer_rows) != EXPECTED_TASKS or {
        row.get("label_audit_status") for row in answer_rows
    } != {"PENDING_FOUR_PASS_BALANCED_CONSENSUS"}:
        raise AuditError("answer key is not uniformly pending four-pass consensus")
    seed, _ = _strict_json_file(root / SEED_RELATIVE_PATH, "task seed bank")
    governance = validate_pending_seed_governance(seed)
    outputs = {
        str(slot): {
            "predictions": output_paths(root, slot)["audit"].relative_to(root).as_posix(),
            "sidecar": output_paths(root, slot)["sidecar"].relative_to(root).as_posix(),
        }
        for slot in AUDIT_SLOTS
    }
    return {
        "schema_version": "px062-gate2.2-v1.3-repository-checkpoint-v1",
        "head_commit": head,
        "branch": branch,
        "upstream_ref": upstream_ref,
        "upstream_commit": upstream_commit,
        "remote_ref": remote_ref,
        "remote_commit": remote_commit,
        "tracked_tree_clean": True,
        "tracked_files": tracked_files,
        "config_sha256": sha256_bytes(config_raw),
        "source_integrity": integrity,
        "pending_answer_sha256": integrity["answer_key_sha256"],
        "answer_pending_rows": len(answer_rows),
        "seed_governance": governance,
        "label_audit_protocol": protocol,
        "canonical_outputs": outputs,
    }


def authenticate_historical_repository_checkpoint(
    root: Path, checkpoint: dict[str, Any]
) -> dict[str, bytes]:
    root = Path(os.path.abspath(root))
    if _is_symlink_like(root):
        raise AuditError("historical checkpoint root is symlink-like")
    if checkpoint.get("schema_version") != "px062-gate2.2-v1.3-repository-checkpoint-v1":
        raise AuditError("historical v1.3 checkpoint schema drift")
    head = checkpoint.get("head_commit")
    branch = checkpoint.get("branch")
    if (
        not isinstance(head, str)
        or not isinstance(branch, str)
        or checkpoint.get("tracked_tree_clean") is not True
        or checkpoint.get("upstream_ref") != f"origin/{branch}"
        or checkpoint.get("remote_ref") != f"refs/heads/{branch}"
        or checkpoint.get("upstream_commit") != head
        or checkpoint.get("remote_commit") != head
    ):
        raise AuditError("historical checkpoint did not record clean pushed ref equality")
    core._git(root, "cat-file", "-e", f"{head}^{{commit}}")
    current_head = core._git(root, "rev-parse", "HEAD")
    core._git(root, "merge-base", "--is-ancestor", head, current_head)
    tracked = checkpoint.get("tracked_files")
    expected = {path.as_posix() for path in TRACKED_CHECKPOINT_PATHS}
    if not isinstance(tracked, dict) or set(tracked) != expected:
        raise AuditError("historical checkpoint tracked-file set drift")
    blobs: dict[str, bytes] = {}
    for logical in sorted(expected):
        record = tracked[logical]
        if not isinstance(record, dict) or set(record) != {"head_blob", "sha256", "bytes"}:
            raise AuditError(f"historical tracked-file record drift: {logical}")
        blob = core._git(root, "rev-parse", f"{head}:{logical}")
        if blob != record["head_blob"]:
            raise AuditError(f"historical tracked blob identity drift: {logical}")
        raw = core._git_bytes(root, "cat-file", "blob", blob)
        if len(raw) != record["bytes"] or sha256_bytes(raw) != record["sha256"]:
            raise AuditError(f"historical tracked blob bytes drift: {logical}")
        blobs[logical] = raw
    config_raw = blobs[CONFIG_RELATIVE_PATH.as_posix()]
    config = _strict_json_bytes(config_raw, "historical config")
    if config.get("status") != "REDESIGN_PENDING_FRESH_CORPUS_AND_BALANCED_FOUR_PASS_LABEL_AUDIT":
        raise AuditError("historical config was not pending v1.3")
    integrity = {
        "tasks_sha256": sha256_bytes(blobs[TRACKED_CHECKPOINT_PATHS[0].as_posix()]),
        "answer_key_sha256": sha256_bytes(blobs[ANSWER_RELATIVE_PATH.as_posix()]),
        "registry_catalog_sha256": sha256_bytes(blobs[TRACKED_CHECKPOINT_PATHS[1].as_posix()]),
        "benchmark_manifest_sha256": sha256_bytes(blobs[MANIFEST_RELATIVE_PATH.as_posix()]),
    }
    if config.get("source_integrity") != integrity:
        raise AuditError("historical config source_integrity drift")
    if integrity["tasks_sha256"] != EXPECTED_TASKS_SHA256 or integrity["registry_catalog_sha256"] != EXPECTED_CATALOG_SHA256:
        raise AuditError("historical frozen input hash differs from runner freeze")
    protocol = expected_label_audit_protocol_config(
        runner_sha256=sha256_bytes(blobs[RUNNER_RELATIVE_PATH.as_posix()]),
        protocol_sha256=sha256_bytes(blobs[PROTOCOL_RELATIVE_PATH.as_posix()]),
        tests_sha256=sha256_bytes(blobs[TESTS_RELATIVE_PATH.as_posix()]),
        core_runner_sha256=sha256_bytes(blobs[CORE_RELATIVE_PATH.as_posix()]),
        builder_sha256=sha256_bytes(blobs[BUILDER_RELATIVE_PATH.as_posix()]),
        base_builder_sha256=sha256_bytes(
            blobs[BASE_BUILDER_RELATIVE_PATH.as_posix()]
        ),
        v11_builder_sha256=sha256_bytes(
            blobs[V11_BUILDER_RELATIVE_PATH.as_posix()]
        ),
        v11_runner_sha256=sha256_bytes(
            blobs[V11_RUNNER_RELATIVE_PATH.as_posix()]
        ),
        verifier_sha256=sha256_bytes(blobs[VERIFIER_RELATIVE_PATH.as_posix()]),
        v11_verifier_sha256=sha256_bytes(
            blobs[V11_VERIFIER_RELATIVE_PATH.as_posix()]
        ),
        finalizer_sha256=sha256_bytes(blobs[FINALIZER_RELATIVE_PATH.as_posix()]),
        v11_finalizer_sha256=sha256_bytes(
            blobs[V11_FINALIZER_RELATIVE_PATH.as_posix()]
        ),
    )
    if config.get("label_audit_protocol") != protocol:
        raise AuditError("historical config audit-protocol anchors drift")
    _validate_v12_pair_manifest_raw(
        blobs[V12_PAIR_MANIFEST_RELATIVE_PATH.as_posix()]
    )
    answers = read_jsonl_bytes(
        blobs[ANSWER_RELATIVE_PATH.as_posix()], "historical pending answer"
    )
    if len(answers) != EXPECTED_TASKS or {
        row.get("label_audit_status") for row in answers
    } != {"PENDING_FOUR_PASS_BALANCED_CONSENSUS"}:
        raise AuditError("historical answer key was not uniformly pending 0/4")
    seed = _strict_json_bytes(blobs[SEED_RELATIVE_PATH.as_posix()], "historical seed")
    seed_governance = validate_pending_seed_governance(seed)
    expected_outputs = {
        str(slot): {
            "predictions": output_paths(root, slot)["audit"].relative_to(root).as_posix(),
            "sidecar": output_paths(root, slot)["sidecar"].relative_to(root).as_posix(),
        }
        for slot in AUDIT_SLOTS
    }
    expected_checkpoint_values = {
        "config_sha256": sha256_bytes(config_raw),
        "source_integrity": integrity,
        "pending_answer_sha256": integrity["answer_key_sha256"],
        "answer_pending_rows": len(answers),
        "seed_governance": seed_governance,
        "label_audit_protocol": protocol,
        "canonical_outputs": expected_outputs,
    }
    for key, expected_value in expected_checkpoint_values.items():
        if checkpoint.get(key) != expected_value:
            raise AuditError(f"historical checkpoint {key} drift")
    assert_current_controls_match_historical_blobs(root, blobs)
    return blobs


def assert_current_controls_match_historical_blobs(
    root: Path, historical_blobs: dict[str, bytes]
) -> None:
    """Bind currently executing immutable controls to authenticated checkpoint bytes."""

    root = Path(os.path.abspath(root))
    identities: set[tuple[int, int]] = set()
    for relative in IMMUTABLE_CURRENT_CONTROL_PATHS:
        logical = relative.as_posix()
        expected = historical_blobs.get(logical)
        current = _safe_root_relative_path(root, relative, "current governance control")
        if expected is None:
            raise AuditError(f"historical governance control is unbound: {logical}")
        identity = _require_unaliased_regular_file(
            current, "current governance control"
        )
        if identity is not None:
            if identity in identities:
                raise AuditError(f"current governance control stable-file alias: {logical}")
            identities.add(identity)
        if current.read_bytes() != expected:
            raise AuditError(
                f"current governance control differs from historical checkpoint: {logical}"
            )


_CORE_BINDINGS: dict[str, Any] = {
    "ROOT": ROOT,
    "FROZEN_DIR": FROZEN_DIR,
    "AUDIT_DIR": AUDIT_DIR,
    "TASKS_PATH": TASKS_PATH,
    "CATALOG_PATH": CATALOG_PATH,
    "EXPECTED_TASKS_SHA256": EXPECTED_TASKS_SHA256,
    "EXPECTED_CATALOG_SHA256": EXPECTED_CATALOG_SHA256,
    "SLOT_MODELS": SLOT_MODELS,
    "SLOT_STEMS": SLOT_STEMS,
    "CONFIG_RELATIVE_PATH": CONFIG_RELATIVE_PATH,
    "ANSWER_RELATIVE_PATH": ANSWER_RELATIVE_PATH,
    "MANIFEST_RELATIVE_PATH": MANIFEST_RELATIVE_PATH,
    "SEED_RELATIVE_PATH": SEED_RELATIVE_PATH,
    "PROTOCOL_RELATIVE_PATH": PROTOCOL_RELATIVE_PATH,
    "RUNNER_RELATIVE_PATH": RUNNER_RELATIVE_PATH,
    "CORE_RELATIVE_PATH": CORE_RELATIVE_PATH,
    "BUILDER_RELATIVE_PATH": BUILDER_RELATIVE_PATH,
    "BASE_BUILDER_RELATIVE_PATH": BASE_BUILDER_RELATIVE_PATH,
    "V11_BUILDER_RELATIVE_PATH": V11_BUILDER_RELATIVE_PATH,
    "V11_RUNNER_RELATIVE_PATH": V11_RUNNER_RELATIVE_PATH,
    "VERIFIER_RELATIVE_PATH": VERIFIER_RELATIVE_PATH,
    "V11_VERIFIER_RELATIVE_PATH": V11_VERIFIER_RELATIVE_PATH,
    "FINALIZER_RELATIVE_PATH": FINALIZER_RELATIVE_PATH,
    "V11_FINALIZER_RELATIVE_PATH": V11_FINALIZER_RELATIVE_PATH,
    "TESTS_RELATIVE_PATH": TESTS_RELATIVE_PATH,
    "TRACKED_CHECKPOINT_PATHS": TRACKED_CHECKPOINT_PATHS,
    "output_paths": output_paths,
    "collect_repository_checkpoint": collect_repository_checkpoint,
    "authenticate_historical_repository_checkpoint": authenticate_historical_repository_checkpoint,
    "expected_label_audit_protocol_config": expected_label_audit_protocol_config,
    "validate_pending_seed_governance": validate_pending_seed_governance,
    "load_prior_session_ids": load_prior_session_ids,
    "v12_audit_blacklist": v12_audit_blacklist,
    "v12_blacklist_evidence": v12_blacklist_evidence,
    "extract_exposed_thread_ids": extract_exposed_thread_ids,
    "extract_exposed_thread_id": extract_exposed_thread_id,
    "validate_slot_order": validate_slot_order,
    "reauthenticate_manifest_artifact_inventory": (
        reauthenticate_manifest_artifact_inventory
    ),
    "AUDIT_SLOTS": AUDIT_SLOTS,
}


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    previous = {name: getattr(core, name) for name in _CORE_BINDINGS if hasattr(core, name)}
    missing = [name for name in _CORE_BINDINGS if not hasattr(core, name)]
    try:
        for name, value in _CORE_BINDINGS.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)
        for name in missing:
            delattr(core, name)


def _derive_run_audit() -> Any:
    source = inspect.getsource(core.run_audit)
    replacements = {
        "gate2_2_context_structured_20260728": "gate2_2_context_structured_v1_3_20260728",
        "LABEL_AUDIT_PROTOCOL_20260728.md": "LABEL_AUDIT_PROTOCOL_V1_3_20260728.md",
        "run_px062_gate2_2_blind_audit.py": "run_px062_gate2_2_v13_blind_audit.py",
        'other_session_ids = load_other_session_ids(paths["other_sidecar"])': (
            "other_session_ids = load_prior_session_ids(root, slot)"
        ),
        '"session_ids_disjoint_from_existing_other_sidecar": True': (
            '"session_ids_disjoint_from_all_existing_sidecars": True,\n'
            '            "session_ids_disjoint_from_sealed_v1_2_blacklist": True,\n'
            '            "fixed_slot_order_preflight_passed": True'
        ),
    }
    expected = {
        "gate2_2_context_structured_20260728": 2,
        "LABEL_AUDIT_PROTOCOL_20260728.md": 1,
        "run_px062_gate2_2_blind_audit.py": 1,
        'other_session_ids = load_other_session_ids(paths["other_sidecar"])': 1,
        '"session_ids_disjoint_from_existing_other_sidecar": True': 1,
    }
    for old, count in expected.items():
        if source.count(old) != count:
            raise RuntimeError(f"sealed run_audit source shape drift: {old}")
        source = source.replace(old, replacements[old])
    start_marker = "    paths = output_paths(root, slot)\n"
    if source.count(start_marker) != 1:
        raise RuntimeError("sealed run_audit slot-order insertion point drift")
    source = source.replace(
        start_marker,
        "    v12_audit_blacklist(root)\n"
        "    validate_slot_order(root, slot)\n"
        + start_marker,
    )
    checkpoint_marker = "    repository_checkpoint = collect_repository_checkpoint(root)\n"
    if source.count(checkpoint_marker) != 1:
        raise RuntimeError("sealed run_audit checkpoint insertion point drift")
    source = source.replace(
        checkpoint_marker,
        checkpoint_marker
        + "    validate_slot_order(\n"
        + "        root, slot, expected_checkpoint=repository_checkpoint\n"
        + "    )\n",
    )
    runner_input = '''            "runner": {
                "path": runner_path.relative_to(root).as_posix(),
                "sha256": sha256_file(runner_path),
            },
'''
    if source.count(runner_input) != 1:
        raise RuntimeError("sealed run_audit blacklist-input insertion point drift")
    source = source.replace(
        runner_input,
        runner_input
        + '            "prior_audit_session_blacklist": '
        + "v12_blacklist_evidence(root),\n",
    )
    singleton_session_block = '''            session_id = (
                event_info["session_id"]
                if event_info
                else extract_exposed_thread_id(event_raw)
            )
            if session_id is not None:
                if session_id in seen_session_ids:
                    raise AuditError(f"reused Codex session ID: {session_id}")
                seen_session_ids.add(session_id)
'''
    complete_session_block = '''            exposed_session_ids = extract_exposed_thread_ids(event_raw)
            session_id = (
                event_info["session_id"]
                if event_info
                else (
                    next(iter(exposed_session_ids))
                    if len(exposed_session_ids) == 1
                    else None
                )
            )
            for exposed_session_id in exposed_session_ids:
                if exposed_session_id in seen_session_ids:
                    raise AuditError(
                        f"reused or blacklisted Codex session ID: {exposed_session_id}"
                    )
                seen_session_ids.add(exposed_session_id)
'''
    if source.count(singleton_session_block) != 1:
        raise RuntimeError("sealed run_audit complete-session insertion point drift")
    source = source.replace(singleton_session_block, complete_session_block)
    attempt_session_marker = '                "session_id": session_id,\n'
    if source.count(attempt_session_marker) != 1:
        raise RuntimeError("sealed run_audit exposed-session record point drift")
    source = source.replace(
        attempt_session_marker,
        attempt_session_marker
        + '                "exposed_session_ids": sorted(exposed_session_ids),\n',
    )
    namespace = dict(core.__dict__)
    namespace.update(_CORE_BINDINGS)
    exec(compile(source, str(RUNNER_RELATIVE_PATH), "exec"), namespace)
    return namespace["run_audit"]


def _derive_verify_consensus() -> Any:
    source = inspect.getsource(core.verify_pair)
    simple = {
        "LABEL_AUDIT_PROTOCOL_20260728.md": "LABEL_AUDIT_PROTOCOL_V1_3_20260728.md",
        "run_px062_gate2_2_blind_audit.py": "run_px062_gate2_2_v13_blind_audit.py",
        "px062-gate2.2-label-audit-evidence-manifest-v1": (
            "px062-gate2.2-v1.3-label-audit-evidence-manifest-v1"
        ),
        '"session_ids_disjoint_from_existing_other_sidecar": True': (
            '"session_ids_disjoint_from_all_existing_sidecars": True,\n'
            '            "session_ids_disjoint_from_sealed_v1_2_blacklist": True,\n'
            '            "fixed_slot_order_preflight_passed": True'
        ),
        "for slot in (1, 2)": "for slot in AUDIT_SLOTS",
    }
    for old, new in simple.items():
        if old not in source:
            raise RuntimeError(f"sealed verify source shape drift: {old}")
        source = source.replace(old, new)
    old_checkpoint = '''        checkpoint_1 = preloaded_sidecars[1][0].get("repository_checkpoint")
        checkpoint_2 = preloaded_sidecars[2][0].get("repository_checkpoint")
        checkpoint_manifest = existing_manifest.get("repository_checkpoint")
        if (
            not isinstance(checkpoint_1, dict)
            or checkpoint_1 != checkpoint_2
            or checkpoint_1 != checkpoint_manifest
        ):
            raise AuditError("historical checkpoint differs across sidecars/manifest")
        repository_checkpoint = checkpoint_1
'''
    new_checkpoint = '''        checkpoints = [
            preloaded_sidecars[slot][0].get("repository_checkpoint")
            for slot in AUDIT_SLOTS
        ]
        checkpoint_manifest = existing_manifest.get("repository_checkpoint")
        if (
            not isinstance(checkpoints[0], dict)
            or any(value != checkpoints[0] for value in checkpoints[1:])
            or checkpoints[0] != checkpoint_manifest
        ):
            raise AuditError("historical checkpoint differs across sidecars/manifest")
        repository_checkpoint = checkpoints[0]
'''
    old_common = '''    common_input_fields = (
        ("tasks", "sha256"),
        ("registry_catalog", "sha256"),
    )
    for outer, inner in common_input_fields:
        if sidecars[1]["inputs"][outer][inner] != sidecars[2]["inputs"][outer][inner]:
            raise AuditError(f"cross-audit {outer} hash mismatch")
    for key in (
        "semantic_registry_sha256",
        "prompt_template_version",
        "prompt_template_sha256",
    ):
        if sidecars[1]["inputs"].get(key) != sidecars[2]["inputs"].get(key):
            raise AuditError(f"cross-audit {key} mismatch")
    if sidecars[1]["repository_checkpoint"] != sidecars[2]["repository_checkpoint"]:
        raise AuditError("audits were not produced from the same repository checkpoint")
'''
    new_common = '''    common_input_fields = (
        ("tasks", "sha256"),
        ("registry_catalog", "sha256"),
    )
    for slot in AUDIT_SLOTS[1:]:
        for outer, inner in common_input_fields:
            if sidecars[1]["inputs"][outer][inner] != sidecars[slot]["inputs"][outer][inner]:
                raise AuditError(f"cross-audit {outer} hash mismatch")
        for key in (
            "semantic_registry_sha256",
            "prompt_template_version",
            "prompt_template_sha256",
        ):
            if sidecars[1]["inputs"].get(key) != sidecars[slot]["inputs"].get(key):
                raise AuditError(f"cross-audit {key} mismatch")
        if sidecars[1]["repository_checkpoint"] != sidecars[slot]["repository_checkpoint"]:
            raise AuditError("audits were not produced from the same repository checkpoint")
'''
    old_ids = "    accepted_session_ids: dict[int, list[str]] = {1: [], 2: []}\n"
    new_ids = "    accepted_session_ids: dict[int, list[str]] = {slot: [] for slot in AUDIT_SLOTS}\n"
    old_overlap = '''    if set(accepted_session_ids[1]) & set(accepted_session_ids[2]):
        raise AuditError("accepted session IDs overlap between audits")

    for index, (left, right) in enumerate(
        zip(batches_by_slot[1], batches_by_slot[2], strict=True), 1
    ):
        for key in ("task_ids_sha256", "prompt_sha256", "schema_sha256"):
            if left.get(key) != right.get(key):
                raise AuditError(f"batch {index} cross-audit {key} mismatch")
'''
    new_overlap = '''    flattened_accepted = [
        session_id for slot in AUDIT_SLOTS for session_id in accepted_session_ids[slot]
    ]
    if len(flattened_accepted) != len(set(flattened_accepted)):
        raise AuditError("accepted session IDs overlap between audits")

    for slot in AUDIT_SLOTS[1:]:
        for index, (left, right) in enumerate(
            zip(batches_by_slot[1], batches_by_slot[slot], strict=True), 1
        ):
            for key in ("task_ids_sha256", "prompt_sha256", "schema_sha256"):
                if left.get(key) != right.get(key):
                    raise AuditError(f"batch {index} cross-audit {key} mismatch")
'''
    for old, new in (
        (old_checkpoint, new_checkpoint),
        (old_common, new_common),
        (old_ids, new_ids),
        (old_overlap, new_overlap),
    ):
        if source.count(old) != 1:
            raise RuntimeError("sealed verify multi-slot migration point drift")
        source = source.replace(old, new)
    input_schema_old = '''            "prompt_template_sha256",
            "protocol",
            "runner",
        }:
'''
    input_schema_new = '''            "prompt_template_sha256",
            "protocol",
            "runner",
            "prior_audit_session_blacklist",
        }:
'''
    if source.count(input_schema_old) != 1:
        raise RuntimeError("sealed verify blacklist-input schema point drift")
    source = source.replace(input_schema_old, input_schema_new)
    task_hash_marker = '''        if inputs.get("tasks", {}).get("sha256") != EXPECTED_TASKS_SHA256:
'''
    if source.count(task_hash_marker) != 1:
        raise RuntimeError("sealed verify blacklist-input validation point drift")
    source = source.replace(
        task_hash_marker,
        '''        if inputs.get("prior_audit_session_blacklist") != v12_blacklist_evidence(root):
            raise AuditError(f"slot {slot} prior-session blacklist drift")
'''
        + task_hash_marker,
    )
    common_key_marker = '''            "prompt_template_sha256",
        ):
'''
    if source.count(common_key_marker) != 1:
        raise RuntimeError("sealed verify cross-audit blacklist point drift")
    source = source.replace(
        common_key_marker,
        '''            "prompt_template_sha256",
            "prior_audit_session_blacklist",
        ):
''',
    )
    session_sets_marker = '''    all_attempt_session_ids: set[str] = set()
    all_isolated_workdirs: set[str] = set()
'''
    if source.count(session_sets_marker) != 1:
        raise RuntimeError("sealed verify prior-session set point drift")
    source = source.replace(
        session_sets_marker,
        '''    prior_blacklisted_session_ids = set(v12_audit_blacklist(root)["session_ids"])
    all_attempt_session_ids: set[str] = set()
    all_isolated_workdirs: set[str] = set()
''',
    )
    attempt_schema_marker = '''                    "session_id",
                    "event_validation_error",
'''
    if source.count(attempt_schema_marker) != 1:
        raise RuntimeError("sealed verify exposed-session schema point drift")
    source = source.replace(
        attempt_schema_marker,
        '''                    "session_id",
                    "exposed_session_ids",
                    "event_validation_error",
''',
    )
    singleton_validation = '''                session_id = attempt.get("session_id")
                if session_id is not None:
                    if not isinstance(session_id, str) or not session_id:
                        raise AuditError(
                            f"slot {slot} batch {expected_number} has invalid session ID"
                        )
                    if session_id in all_attempt_session_ids:
                        raise AuditError(f"globally reused audit session ID: {session_id}")
                    all_attempt_session_ids.add(session_id)
'''
    type_only_validation = '''                session_id = attempt.get("session_id")
                if session_id is not None and (
                    not isinstance(session_id, str) or not session_id
                ):
                    raise AuditError(
                        f"slot {slot} batch {expected_number} has invalid session ID"
                    )
'''
    if source.count(singleton_validation) != 1:
        raise RuntimeError("sealed verify singleton-session validation point drift")
    source = source.replace(singleton_validation, type_only_validation)
    event_read_marker = '''                event_path = _resolved_evidence_path(root, attempt["event_log_path"])
                event_info: dict[str, Any] | None = None
                try:
                    event_info = inspect_event_log(event_path.read_bytes(), SLOT_MODELS[slot])
'''
    complete_event_read = '''                event_path = _resolved_evidence_path(root, attempt["event_log_path"])
                event_raw = event_path.read_bytes()
                exposed_session_ids = extract_exposed_thread_ids(event_raw)
                if attempt.get("exposed_session_ids") != sorted(exposed_session_ids):
                    raise AuditError(
                        f"slot {slot} batch {expected_number} exposed-session evidence drift"
                    )
                for exposed_session_id in exposed_session_ids:
                    if exposed_session_id in prior_blacklisted_session_ids:
                        raise AuditError(
                            f"reused sealed v1.2 audit session ID: {exposed_session_id}"
                        )
                    if exposed_session_id in all_attempt_session_ids:
                        raise AuditError(
                            f"globally reused audit session ID: {exposed_session_id}"
                        )
                    all_attempt_session_ids.add(exposed_session_id)
                event_info: dict[str, Any] | None = None
                try:
                    event_info = inspect_event_log(event_raw, SLOT_MODELS[slot])
'''
    if source.count(event_read_marker) != 1:
        raise RuntimeError("sealed verify complete-session event point drift")
    source = source.replace(event_read_marker, complete_event_read)
    invalid_recovery = '''                    recovered_session_id = extract_exposed_thread_id(event_path.read_bytes())
                    if recovered_session_id != session_id:
'''
    complete_recovery = '''                    recovered_session_id = (
                        next(iter(exposed_session_ids))
                        if len(exposed_session_ids) == 1
                        else None
                    )
                    if recovered_session_id != session_id:
'''
    if source.count(invalid_recovery) != 1:
        raise RuntimeError("sealed verify invalid-event session point drift")
    source = source.replace(invalid_recovery, complete_recovery)
    valid_session_marker = '''                if event_info is not None and event_info["session_id"] != session_id:
'''
    if source.count(valid_session_marker) != 1:
        raise RuntimeError("sealed verify valid-event session point drift")
    source = source.replace(
        valid_session_marker,
        '''                if event_info is not None and (
                    exposed_session_ids != {event_info["session_id"]}
                    or event_info["session_id"] != session_id
                ):
''',
    )
    artifact_marker = "    artifact_paths = [item[\"path\"] for item in artifacts]\n"
    if source.count(artifact_marker) != 1:
        raise RuntimeError("sealed verify blacklist-artifact insertion point drift")
    source = source.replace(
        artifact_marker,
        '''    blacklist = v12_blacklist_evidence(root)
    artifacts.append(
        _validated_artifact(
            root,
            blacklist["path"],
            blacklist["sha256"],
            "sealed_v1_2_pair_manifest_session_blacklist",
        )
    )
'''
        + artifact_marker,
    )
    global_marker = '''            "all_unique_and_cross_audit_disjoint": True,
'''
    if source.count(global_marker) != 1:
        raise RuntimeError("sealed verify global blacklist attestation point drift")
    source = source.replace(
        global_marker,
        global_marker
        + '            "sealed_v1_2_blacklisted_count": 86,\n'
        + '            "all_disjoint_from_sealed_v1_2_blacklist": True,\n',
    )
    namespace = dict(core.__dict__)
    namespace.update(_CORE_BINDINGS)
    exec(compile(source, str(RUNNER_RELATIVE_PATH), "exec"), namespace)
    return namespace["verify_pair"]


_RUN_AUDIT_V13 = _derive_run_audit()
_VERIFY_CONSENSUS_V13 = _derive_verify_consensus()


def run_audit(
    slot: int,
    *,
    root: Path = ROOT,
    codex_executable: str | None = None,
) -> tuple[Path, Path]:
    # Public fail-before-delegation guard. The derived core repeats this check
    # before its first filesystem write to close an in-process ordering race.
    v12_audit_blacklist(root)
    validate_slot_order(root, slot)
    with _bound_core():
        return _RUN_AUDIT_V13(slot, root=root, codex_executable=codex_executable)


def verify_consensus(
    root: Path = ROOT,
    *,
    write_manifest: bool = True,
    verification_mode: str = "current",
) -> dict[str, Any]:
    root = Path(os.path.abspath(root))
    manifest_relative = output_paths(root, 1)["manifest"].relative_to(root)
    manifest_path = _safe_root_relative_path(
        root, manifest_relative, "label-audit evidence manifest"
    )
    if verification_mode == "historical":
        _require_unaliased_regular_file(
            manifest_path, "historical label-audit evidence manifest"
        )
        historical_manifest = _strict_json_bytes(
            manifest_path.read_bytes(), "sealed label-audit evidence manifest"
        )
        checkpoint = historical_manifest.get("repository_checkpoint")
        if not isinstance(checkpoint, dict):
            raise AuditError("sealed evidence manifest lacks a repository checkpoint")
        authenticate_historical_repository_checkpoint(root, checkpoint)
    with _bound_core():
        result = _VERIFY_CONSENSUS_V13(
            root,
            write_manifest=False if write_manifest else write_manifest,
            verification_mode=verification_mode,
        )
    reauthenticate_manifest_artifact_inventory(root, result)
    if verification_mode == "historical":
        checkpoint = result.get("repository_checkpoint")
        if not isinstance(checkpoint, dict):
            raise AuditError("historical consensus result lacks a repository checkpoint")
        authenticate_historical_repository_checkpoint(root, checkpoint)
    if write_manifest:
        if verification_mode != "current":
            raise AuditError("historical verification never writes the sealed manifest")
        if collect_repository_checkpoint(root) != result.get("repository_checkpoint"):
            raise AuditError("repository checkpoint changed before manifest write")
        reauthenticate_manifest_artifact_inventory(root, result)
        if collect_repository_checkpoint(root) != result.get("repository_checkpoint"):
            raise AuditError("repository checkpoint changed after final inventory check")
        manifest_path = _safe_root_relative_path(
            root, manifest_relative, "label-audit evidence manifest"
        )
        if manifest_path.exists():
            raise AuditError("label-audit evidence manifest already exists; refusing overwrite")
        raw = (
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        core.write_exclusive(manifest_path, raw)
    return result


# Generic compatibility name for builder/finalizer callback signatures.
verify_pair = verify_consensus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--slot", type=int, choices=AUDIT_SLOTS)
    operation.add_argument("--verify-consensus", action="store_true")
    args = parser.parse_args()
    if args.verify_consensus:
        result = verify_consensus(ROOT, write_manifest=True)
        manifest_path = output_paths(ROOT, 1)["manifest"]
        print(
            json.dumps(
                {
                    "manifest": manifest_path.relative_to(ROOT).as_posix(),
                    "manifest_sha256": sha256_file(manifest_path),
                    "accepted_session_count": result["global_session_ids"]["accepted_count"],
                },
                sort_keys=True,
            )
        )
        return
    audit_path, sidecar_path = run_audit(args.slot)
    print(
        json.dumps(
            {
                "audit": audit_path.relative_to(ROOT).as_posix(),
                "sidecar": sidecar_path.relative_to(ROOT).as_posix(),
                "audit_sha256": sha256_file(audit_path),
                "sidecar_sha256": sha256_file(sidecar_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
