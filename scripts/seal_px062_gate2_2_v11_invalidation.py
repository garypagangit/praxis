#!/usr/bin/env python
"""Seal the failed PX-062 Gate 2.2 v1.1 label review.

This validator is candidate-specific and fail-closed.  It binds the exact
v1.1 corpus and dual-audit evidence at the preregistered Git checkpoint,
reconstructs the canonical 10-row conflict ledger, proves that both the
verifier and check-only finalizer reject the evidence, and requires resolution
and target-execution artifacts to be absent.

The default mode verifies byte-identical canonical outputs.  ``--write`` may
create them once, but it never replaces a nonmatching existing file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728"
)
CONFLICTS = GATE / "label_audit_conflicts.jsonl"
INVALIDATION = GATE / "label_audit_invalidation.json"
PAIR_MANIFEST = GATE / "label_audit_evidence_manifest.json"
PROVISIONAL_RESOLUTION = GATE / "label_audit_provisional_resolution.json"
FINAL_RESOLUTION = GATE / "label_audit_resolution.json"
CREATED_UTC = "2026-07-28T23:06:55Z"
REPOSITORY_CHECKPOINT = "ed8dbf2c7fbef930a1c38830ccfcfe7e7d9a2a9b"
EXPECTED_FAILURE = "label audits do not unanimously support the answer key"


SEALED_FILES: dict[str, tuple[str, int, str]] = {
    "tasks": (
        (GATE / "frozen_inputs/tasks.jsonl").as_posix(),
        2_118_443,
        "68f776fe51ce3d2bd7eef42124448a1a6f58c0b0c6213fbd34b4b1e1e155ddbb",
    ),
    "answer_key": (
        (GATE / "frozen_inputs/answer_key.jsonl").as_posix(),
        295_488,
        "2c2b1561b2beeb72584df3ed9dfe3a848e40b5f4bc4c74b2773e15038f616e38",
    ),
    "registry_catalog": (
        (GATE / "frozen_inputs/registry_catalog.json").as_posix(),
        20_543,
        "ec12c41e14c086f41a2bb42ddff8b7e137ba15d89bb12fb7645f6440a09f5d8b",
    ),
    "benchmark_manifest": (
        (GATE / "frozen_inputs/benchmark_manifest.json").as_posix(),
        9_185,
        "bbf7c24d9a8bb661f82edb3f3ebe553ad3d3cb8bafa508cfce6ef22eb9559518",
    ),
    "audit_pair_manifest": (
        PAIR_MANIFEST.as_posix(),
        158_680,
        "5ad6e4631d82095d60bc46d736a795b330d27742018554e4b6fff1954a562654",
    ),
    "audit_1_predictions": (
        (GATE / "label_audit_1_predictions.jsonl").as_posix(),
        189_723,
        "9a13e76908616017330f6f5a4c95052c699a1eeddf9625271e241c57b807efcd",
    ),
    "audit_1_sidecar": (
        (GATE / "label_audit_1_run.json").as_posix(),
        216_343,
        "c565f261a55bb65302ec56e058a6643ed252e27aa3e4f2476c950cfa24587d84",
    ),
    "audit_2_predictions": (
        (GATE / "label_audit_2_predictions.jsonl").as_posix(),
        176_085,
        "2687bcb826353f0606bef7f68c4f645cb823872d8e1c5c036b6810345ada6bc8",
    ),
    "audit_2_sidecar": (
        (GATE / "label_audit_2_run.json").as_posix(),
        217_033,
        "dab26de3e3d33f278190bc937493734cf0b2dff713839e0310b78d346bdacfd6",
    ),
    "verifier": (
        "scripts/verify_px062_gate2_2_v11_label_audits.py",
        8_600,
        "64a723b952105bf4ec4bf3b4cf8a684fe3ca8fb5d79f0d7972f9814997fe4fc1",
    ),
    "finalizer": (
        "scripts/finalize_px062_gate2_2_v11_labels.py",
        24_617,
        "493cf1d92bedf34b5e44ed600b65e33215dd1958d22fe1d4378931e3d75ba5d7",
    ),
}

EXPECTED_AGGREGATES = {
    "audit_1_disagreements_with_frozen_answer": 3,
    "audit_2_disagreements_with_frozen_answer": 9,
    "cross_audit_disagreement_rows": 8,
    "union_nonunanimous_rows": 10,
    "both_auditors_same_alternative_against_frozen_answer": 2,
}
EXPECTED_TASK_TYPE_COUNTS = {
    "available_single_skill": 1,
    "misleading_name_none": 2,
    "misleading_name_real_skill": 3,
    "unavailable_capability": 4,
}
EXPECTED_MODELS = {1: "gpt-5.6-sol", 2: "gpt-5.6-terra"}

TARGET_EXECUTION_PATHS = {
    "collection_output_dir": Path("outputs/px062_gate2_2_v1_1"),
    "launch_registration": Path(
        "manifests/px062_gate2_2_v1_1_20260728/confirmatory_registration.json"
    ),
    "launch_receipt": Path(
        "manifests/px062_gate2_2_v1_1_20260728/launch_receipt.json"
    ),
    "completion_registration": Path(
        "manifests/px062_gate2_2_v1_1_20260728/completion_registration.json"
    ),
    "adjudication_authorization": Path(
        "manifests/px062_gate2_2_v1_1_20260728/adjudication_authorization.json"
    ),
    "sealed_confirmation": GATE / "sealed_confirmation",
    "confirmatory_result": GATE / "PX062_GATE2_2_V1_1_CONFIRMATORY_RESULT.json",
}


class SealError(ValueError):
    """A sealed input, evidence artifact, or derived fact did not match."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SealError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json(raw: bytes, label: str) -> Any:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise SealError(f"JSON must be BOM-free UTF-8 with LF endings: {label}")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SealError(f"invalid JSON: {label}") from exc


def strict_jsonl(raw: bytes, label: str) -> list[dict[str, Any]]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        raise SealError(f"JSONL must be BOM-free UTF-8 with LF and final LF: {label}")
    lines = raw[:-1].split(b"\n")
    if not lines or any(not line for line in lines):
        raise SealError(f"JSONL contains an empty row: {label}")
    rows = [strict_json(line, f"{label}:{index}") for index, line in enumerate(lines, 1)]
    if not all(isinstance(row, dict) for row in rows):
        raise SealError(f"JSONL contains a non-object row: {label}")
    return rows


def canonical_path(root: Path, logical: str) -> Path:
    root = root.resolve()
    path = (root / logical).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise SealError(f"path escapes repository root: {logical}") from exc
    if relative != logical:
        raise SealError(f"noncanonical repository path: {logical}")
    return path


def validate_sealed_file(root: Path, key: str) -> tuple[Path, bytes]:
    logical, expected_bytes, expected_sha256 = SEALED_FILES[key]
    path = canonical_path(root, logical)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SealError(f"missing sealed file: {logical}") from exc
    if len(raw) != expected_bytes or sha256_bytes(raw) != expected_sha256:
        raise SealError(f"sealed file changed: {logical}")
    return path, raw


def binding(key: str, *, rows: int | None = None) -> dict[str, Any]:
    path, size, digest = SEALED_FILES[key]
    result: dict[str, Any] = {"path": path, "bytes": size, "sha256": digest}
    if rows is not None:
        result["rows"] = rows
    return result


def historical_pair_verifier(
    root: Path, *, write_manifest: bool = False
) -> dict[str, Any]:
    """Authenticate the pair from its recorded ancestor checkpoint."""

    if write_manifest:
        raise SealError("historical invalidation verification cannot write a manifest")
    try:
        try:
            from scripts.run_px062_gate2_2_v11_blind_audit import verify_pair
        except ModuleNotFoundError:  # Direct execution from scripts/.
            from run_px062_gate2_2_v11_blind_audit import verify_pair  # type: ignore[no-redef]
        return verify_pair(
            root.resolve(), write_manifest=False, verification_mode="historical"
        )
    except Exception as exc:
        raise SealError("historical audit-pair authentication failed") from exc


def validate_pair_manifest(root: Path, raw: bytes) -> dict[str, Any]:
    manifest = strict_json(raw, PAIR_MANIFEST.as_posix())
    if not isinstance(manifest, dict):
        raise SealError("audit-pair manifest is not an object")
    if manifest.get("schema_version") != "px062-gate2.2-label-audit-evidence-manifest-v1":
        raise SealError("audit-pair manifest schema drift")
    if manifest.get("answer_key_contents_included") is not False:
        raise SealError("audit-pair manifest unexpectedly contains answer-key contents")
    reconstructed = historical_pair_verifier(root, write_manifest=False)
    if reconstructed != manifest:
        raise SealError("historical audit-pair reconstruction differs from sealed manifest")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 438:
        raise SealError("audit-pair manifest must bind exactly 438 artifacts")
    paths: list[str] = []
    roles: list[str] = []
    for index, artifact in enumerate(artifacts, 1):
        if not isinstance(artifact, dict) or set(artifact) != {
            "bytes", "path", "role", "sha256"
        }:
            raise SealError(f"invalid evidence artifact entry {index}")
        logical = artifact["path"]
        role = artifact["role"]
        if not isinstance(logical, str) or not isinstance(role, str):
            raise SealError(f"invalid evidence artifact identity {index}")
        path = canonical_path(root, logical)
        try:
            evidence_raw = path.read_bytes()
        except OSError as exc:
            raise SealError(f"missing evidence artifact: {logical}") from exc
        if (
            artifact["bytes"] != len(evidence_raw)
            or artifact["sha256"] != sha256_bytes(evidence_raw)
        ):
            raise SealError(f"evidence artifact changed: {logical}")
        paths.append(logical)
        roles.append(role)
    if len(set(paths)) != 438 or len(set(roles)) != 438:
        raise SealError("evidence artifact paths and roles must be unique")

    evidence_prefix = (GATE / "label_audits").as_posix() + "/"
    evidence_root = canonical_path(root, (GATE / "label_audits").as_posix())
    on_disk_evidence = {
        path.relative_to(root.resolve()).as_posix()
        for path in evidence_root.rglob("*")
        if path.is_file()
    }
    manifested_evidence = {path for path in paths if path.startswith(evidence_prefix)}
    if len(on_disk_evidence) != 430 or on_disk_evidence != manifested_evidence:
        raise SealError("per-attempt evidence directory does not equal its 430-file manifest")

    audits = manifest.get("audits")
    if not isinstance(audits, list) or len(audits) != 2:
        raise SealError("audit-pair manifest must contain exactly two audits")
    all_session_ids: list[str] = []
    session_binding: list[dict[str, Any]] = []
    for expected_slot, audit in enumerate(audits, 1):
        if not isinstance(audit, dict):
            raise SealError(f"invalid pair audit {expected_slot}")
        session_ids = audit.get("accepted_session_ids")
        if (
            audit.get("slot") != expected_slot
            or audit.get("model") != EXPECTED_MODELS[expected_slot]
            or not isinstance(session_ids, list)
            or len(session_ids) != 43
            or not all(isinstance(item, str) and item for item in session_ids)
            or len(set(session_ids)) != 43
        ):
            raise SealError(f"invalid accepted sessions for audit {expected_slot}")
        if audit.get("prediction_sha256") != SEALED_FILES[
            f"audit_{expected_slot}_predictions"
        ][2]:
            raise SealError(f"pair prediction binding drift for audit {expected_slot}")
        if audit.get("sidecar_sha256") != SEALED_FILES[
            f"audit_{expected_slot}_sidecar"
        ][2]:
            raise SealError(f"pair sidecar binding drift for audit {expected_slot}")

        _, sidecar_raw = validate_sealed_file(root, f"audit_{expected_slot}_sidecar")
        sidecar = strict_json(
            sidecar_raw, SEALED_FILES[f"audit_{expected_slot}_sidecar"][0]
        )
        batches = sidecar.get("batches") if isinstance(sidecar, dict) else None
        if not isinstance(batches, list) or len(batches) != 43:
            raise SealError(f"sidecar batch count drift for audit {expected_slot}")
        observed: list[str] = []
        attempt_count = 0
        for batch_number, batch in enumerate(batches, 1):
            if not isinstance(batch, dict) or batch.get("batch_number") != batch_number:
                raise SealError(f"sidecar batch ordering drift for audit {expected_slot}")
            attempts = batch.get("attempts")
            accepted_attempt = batch.get("accepted_attempt")
            if not isinstance(attempts, list):
                raise SealError(f"sidecar attempts invalid for audit {expected_slot}")
            attempt_count += len(attempts)
            accepted = [
                item
                for item in attempts
                if isinstance(item, dict) and item.get("attempt") == accepted_attempt
            ]
            if len(accepted) != 1:
                raise SealError(f"sidecar accepted attempt invalid for audit {expected_slot}")
            session_id = accepted[0].get("session_id")
            if (
                not isinstance(session_id, str)
                or accepted[0].get("event_summary", {}).get("session_id") != session_id
            ):
                raise SealError(f"sidecar session binding invalid for audit {expected_slot}")
            observed.append(session_id)
        if attempt_count != 43 or observed != session_ids:
            raise SealError(f"sidecar sessions do not match pair audit {expected_slot}")
        all_session_ids.extend(session_ids)
        session_binding.append({"slot": expected_slot, "session_ids": session_ids})

    if len(all_session_ids) != 86 or len(set(all_session_ids)) != 86:
        raise SealError("accepted audit sessions are not exactly 86 unique IDs")
    if manifest.get("global_session_ids") != {
        "accepted_count": 86,
        "all_attempt_count": 86,
        "all_unique_and_cross_audit_disjoint": True,
    }:
        raise SealError("global session attestation drift")
    if manifest.get("isolated_workdirs") != {"all_unique": True, "attempt_count": 86}:
        raise SealError("isolated workdir attestation drift")
    checkpoint = manifest.get("repository_checkpoint")
    if not isinstance(checkpoint, dict) or checkpoint.get("head_commit") != REPOSITORY_CHECKPOINT:
        raise SealError("audit-pair repository checkpoint drift")

    return {
        "artifact_count": len(artifacts),
        "artifact_bytes": sum(item["bytes"] for item in artifacts),
        "artifact_inventory_sha256": sha256_bytes(canonical_json_bytes(artifacts)),
        "accepted_session_count": len(all_session_ids),
        "accepted_session_ids_sha256": sha256_bytes(
            canonical_json_bytes(session_binding)
        ),
    }


def build_conflicts(root: Path) -> tuple[list[dict[str, Any]], bytes, dict[str, Any]]:
    raws = {
        key: validate_sealed_file(root, key)[1]
        for key in (
            "tasks",
            "answer_key",
            "audit_1_predictions",
            "audit_2_predictions",
        )
    }
    tasks = strict_jsonl(raws["tasks"], SEALED_FILES["tasks"][0])
    answers = strict_jsonl(raws["answer_key"], SEALED_FILES["answer_key"][0])
    audit_1 = strict_jsonl(
        raws["audit_1_predictions"], SEALED_FILES["audit_1_predictions"][0]
    )
    audit_2 = strict_jsonl(
        raws["audit_2_predictions"], SEALED_FILES["audit_2_predictions"][0]
    )
    if not all(len(rows) == 1032 for rows in (tasks, answers, audit_1, audit_2)):
        raise SealError("tasks, answers, and both audits must each contain 1,032 rows")
    task_ids = [row.get("task_id") for row in tasks]
    if len(set(task_ids)) != 1032 or any(
        [row.get("task_id") for row in rows] != task_ids
        for rows in (answers, audit_1, audit_2)
    ):
        raise SealError("task IDs are not unique and in identical canonical order")

    conflicts: list[dict[str, Any]] = []
    audit_disagreements = [0, 0]
    cross_disagreements = 0
    same_alternative = 0
    task_type_counts: dict[str, int] = {}
    for task, answer, prediction_1, prediction_2 in zip(
        tasks, answers, audit_1, audit_2, strict=True
    ):
        expected_schema = {"task_id", "predicted_skill", "confidence", "note"}
        if set(prediction_1) != expected_schema:
            raise SealError(f"audit 1 schema drift at {task['task_id']}")
        if set(prediction_2) != expected_schema:
            raise SealError(f"audit 2 schema drift at {task['task_id']}")
        expected = answer.get("expected_skill")
        p1 = prediction_1["predicted_skill"]
        p2 = prediction_2["predicted_skill"]
        audit_disagreements[0] += p1 != expected
        audit_disagreements[1] += p2 != expected
        if p1 == p2 == expected:
            continue
        if p1 != p2:
            conflict_class = "AUDITORS_DISAGREE"
            cross_disagreements += 1
        elif p1 == p2 != expected:
            conflict_class = "BOTH_AUDITORS_SAME_ALTERNATIVE"
            same_alternative += 1
        else:  # pragma: no cover - exhaustive equality guard.
            raise SealError("unclassifiable label conflict")
        task_type = answer.get("task_type")
        if not isinstance(task_type, str):
            raise SealError(f"missing task type at {task['task_id']}")
        task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
        payload = {
            "task_id": task["task_id"],
            "task_type": task_type,
            "prompt_sha256": sha256_bytes(task["prompt"].encode("utf-8")),
            "expected_skill": expected,
            "audit_1": {
                "predicted_skill": p1,
                "confidence": prediction_1["confidence"],
                "note": prediction_1["note"],
            },
            "audit_2": {
                "predicted_skill": p2,
                "confidence": prediction_2["confidence"],
                "note": prediction_2["note"],
            },
            "conflict_class": conflict_class,
        }
        row = dict(payload)
        row["canonical_row_sha256"] = sha256_bytes(canonical_json_bytes(payload))
        conflicts.append(row)

    aggregates = {
        "audit_1_disagreements_with_frozen_answer": audit_disagreements[0],
        "audit_2_disagreements_with_frozen_answer": audit_disagreements[1],
        "cross_audit_disagreement_rows": cross_disagreements,
        "union_nonunanimous_rows": len(conflicts),
        "both_auditors_same_alternative_against_frozen_answer": same_alternative,
    }
    if aggregates != EXPECTED_AGGREGATES:
        raise SealError(f"semantic aggregate drift: {aggregates!r}")
    if task_type_counts != EXPECTED_TASK_TYPE_COUNTS:
        raise SealError(f"conflict task-type aggregate drift: {task_type_counts!r}")
    raw = b"".join(canonical_json_bytes(row) + b"\n" for row in conflicts)
    return conflicts, raw, {**aggregates, "by_task_type": task_type_counts}


def _assert_resolution_absent(root: Path) -> None:
    for logical in (PROVISIONAL_RESOLUTION, FINAL_RESOLUTION):
        if canonical_path(root, logical.as_posix()).exists():
            raise SealError(f"label-resolution output exists: {logical.as_posix()}")


def validate_verifier_failure(root: Path) -> dict[str, Any]:
    validate_sealed_file(root, "verifier")
    _assert_resolution_absent(root)
    try:
        try:
            from scripts.verify_px062_gate2_2_v11_label_audits import verify
        except ModuleNotFoundError:  # Direct execution from scripts/.
            from verify_px062_gate2_2_v11_label_audits import verify  # type: ignore[no-redef]
        verify(
            canonical_path(root, SEALED_FILES["tasks"][0]),
            canonical_path(root, SEALED_FILES["answer_key"][0]),
            [
                canonical_path(root, SEALED_FILES["audit_1_predictions"][0]),
                canonical_path(root, SEALED_FILES["audit_2_predictions"][0]),
            ],
            canonical_path(root, SEALED_FILES["registry_catalog"][0]),
        )
    except ValueError as exc:
        if type(exc) is not ValueError or str(exc) != EXPECTED_FAILURE:
            raise SealError(f"unexpected verifier failure: {type(exc).__name__}: {exc}") from exc
    else:
        raise SealError("verifier unexpectedly accepted the invalid audit pair")
    _assert_resolution_absent(root)
    return {
        **binding("verifier"),
        "mode": "check_only",
        "function": "verify",
        "exit_semantics": {
            "exception_type": "ValueError",
            "message": EXPECTED_FAILURE,
            "cli_exit_code": 1,
            "terminal_stderr_line": f"ValueError: {EXPECTED_FAILURE}",
        },
        "provisional_resolution_written": False,
        "final_resolution_written": False,
    }


def validate_finalizer_failure(root: Path) -> dict[str, Any]:
    validate_sealed_file(root, "finalizer")
    _assert_resolution_absent(root)
    try:
        try:
            from scripts.finalize_px062_gate2_2_v11_labels import (
                DEFAULT_CANDIDATE_DIR,
                prepare_finalization,
            )
            from scripts.build_px062_gate2_2_v11_benchmark import (
                DEFAULT_PRIOR_TASKS,
                DEFAULT_REGISTRY_INVENTORY,
                DEFAULT_SEED_BANK,
            )
        except ModuleNotFoundError:  # Direct execution from scripts/.
            from finalize_px062_gate2_2_v11_labels import (  # type: ignore[no-redef]
                DEFAULT_CANDIDATE_DIR,
                prepare_finalization,
            )
            from build_px062_gate2_2_v11_benchmark import (  # type: ignore[no-redef]
                DEFAULT_PRIOR_TASKS,
                DEFAULT_REGISTRY_INVENTORY,
                DEFAULT_SEED_BANK,
            )
        prepare_finalization(
            root=root,
            seed_bank_path=DEFAULT_SEED_BANK,
            registry_path=DEFAULT_REGISTRY_INVENTORY,
            prior_tasks_path=DEFAULT_PRIOR_TASKS,
            candidate_dir=DEFAULT_CANDIDATE_DIR,
            provisional_resolution_path=PROVISIONAL_RESOLUTION,
            final_resolution_path=FINAL_RESOLUTION,
            pair_verifier=historical_pair_verifier,
        )
    except ValueError as exc:
        if type(exc) is not ValueError or str(exc) != EXPECTED_FAILURE:
            raise SealError(f"unexpected finalizer failure: {type(exc).__name__}: {exc}") from exc
    else:
        raise SealError("finalizer unexpectedly accepted the invalid audit pair")
    _assert_resolution_absent(root)
    return {
        **binding("finalizer"),
        "mode": "check_only",
        "function": "prepare_finalization",
        "exit_semantics": {
            "exception_type": "ValueError",
            "message": EXPECTED_FAILURE,
            "cli_exit_code": 1,
            "terminal_stderr_line": f"ValueError: {EXPECTED_FAILURE}",
        },
        "provisional_resolution_written": False,
        "final_resolution_written": False,
    }


def validate_target_execution_absence(root: Path) -> dict[str, Any]:
    paths: dict[str, dict[str, Any]] = {}
    for role, logical_path in TARGET_EXECUTION_PATHS.items():
        logical = logical_path.as_posix()
        path = canonical_path(root, logical)
        if path.exists():
            raise SealError(f"target-execution artifact exists: {logical}")
        paths[role] = {"path": logical, "exists": False}
    return {
        "repository_evidence_scope": (
            "Canonical local output, launch, completion, and adjudication paths"
        ),
        "paths": paths,
        "qwen_or_mistral_gate2_2_collection_launched": False,
        "aws_gate2_2_training_job_launched": False,
    }


def build_outputs(
    root: Path, *, probe_rejectors: bool = True
) -> tuple[bytes, bytes]:
    root = root.resolve()
    for key in SEALED_FILES:
        validate_sealed_file(root, key)
    _, pair_raw = validate_sealed_file(root, "audit_pair_manifest")
    pair_summary = validate_pair_manifest(root, pair_raw)
    conflicts, conflicts_raw, aggregates = build_conflicts(root)
    _assert_resolution_absent(root)
    execution_absence = validate_target_execution_absence(root)

    def rejection_record(key: str, function: str) -> dict[str, Any]:
        return {
            **binding(key),
            "mode": "check_only",
            "function": function,
            "exit_semantics": {
                "exception_type": "ValueError",
                "message": EXPECTED_FAILURE,
                "cli_exit_code": 1,
                "terminal_stderr_line": f"ValueError: {EXPECTED_FAILURE}",
            },
            "provisional_resolution_written": False,
            "final_resolution_written": False,
        }
    verifier_check = (
        validate_verifier_failure(root)
        if probe_rejectors
        else rejection_record("verifier", "verify")
    )
    finalizer_check = (
        validate_finalizer_failure(root)
        if probe_rejectors
        else rejection_record("finalizer", "prepare_finalization")
    )

    audits: list[dict[str, Any]] = []
    for slot in (1, 2):
        disagreements = aggregates[f"audit_{slot}_disagreements_with_frozen_answer"]
        audits.append(
            {
                "slot": slot,
                "model": EXPECTED_MODELS[slot],
                "rows": 1032,
                "agreement_with_frozen_answer": 1032 - disagreements,
                "disagreements_with_frozen_answer": disagreements,
                "predictions": binding(f"audit_{slot}_predictions", rows=1032),
                "sidecar": binding(f"audit_{slot}_sidecar"),
                "accepted_session_count": 43,
            }
        )

    record = {
        "schema_version": "px062-gate2.2-label-audit-invalidation-v3",
        "experiment_id": "px062-skill-selection-gate2-2-v1-1-20260728",
        "benchmark_version": "1.1",
        "status": "INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED",
        "created_utc": CREATED_UTC,
        "repository_checkpoint": REPOSITORY_CHECKPOINT,
        "sealed_inputs": {
            "tasks": binding("tasks", rows=1032),
            "answer_key": binding("answer_key", rows=1032),
            "registry_catalog": binding("registry_catalog"),
            "benchmark_manifest": binding("benchmark_manifest"),
        },
        "sealed_audit_evidence": {
            "mechanical_pair_verification": "PASS",
            "pair_manifest": binding("audit_pair_manifest"),
            **pair_summary,
            "audits": audits,
        },
        "conflict_ledger": {
            "path": CONFLICTS.as_posix(),
            "bytes": len(conflicts_raw),
            "sha256": sha256_bytes(conflicts_raw),
            "rows": len(conflicts),
            "order": "frozen tasks.jsonl row order",
            "prompt_sha256_definition": (
                "SHA-256 of the exact UTF-8 prompt string bytes, without an added newline"
            ),
            "canonical_row_sha256_definition": (
                "SHA-256 of canonical compact sorted-key UTF-8 JSON for the row "
                "excluding canonical_row_sha256, without an added newline"
            ),
            "conflict_class_counts": {
                "AUDITORS_DISAGREE": aggregates["cross_audit_disagreement_rows"],
                "BOTH_AUDITORS_SAME_ALTERNATIVE": aggregates[
                    "both_auditors_same_alternative_against_frozen_answer"
                ],
            },
        },
        "semantic_gate": {
            "status": "FAIL",
            "rows": 1032,
            "three_way_unanimous_rows": 1022,
            "three_way_unanimous_rate": 1022 / 1032,
            "cross_audit_agreement_rows": 1024,
            **aggregates,
        },
        "resolution_absence": {
            "provisional": {
                "path": PROVISIONAL_RESOLUTION.as_posix(),
                "exists": False,
            },
            "final": {"path": FINAL_RESOLUTION.as_posix(), "exists": False},
        },
        "verifier_check": verifier_check,
        "finalizer_check": finalizer_check,
        "target_execution_absence": execution_absence,
        "required_disposition": {
            "benchmark_version_1_1_valid_for_model_collection": False,
            "row_patching_permitted": False,
            "disputed_only_reaudit_permitted": False,
            "unchanged_input_rerun_to_seek_pass_permitted": False,
            "new_benchmark_version_required": True,
            "new_task_catalog_answer_hashes_required": True,
            "two_fresh_full_blinded_audits_required": True,
            "version_1_1_audits_reusable_for_acceptance": False,
            "qwen_or_mistral_gate2_2_collection_launched": False,
            "aws_gate2_2_training_job_launched": False,
        },
    }
    return pretty_json_bytes(record), conflicts_raw


def _atomic_create_or_match(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise SealError(f"refusing to overwrite nonmatching canonical output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    invalidation_raw, conflicts_raw = build_outputs(root, probe_rejectors=True)
    outputs = {
        canonical_path(root, INVALIDATION.as_posix()): invalidation_raw,
        canonical_path(root, CONFLICTS.as_posix()): conflicts_raw,
    }
    if args.write:
        for path, raw in outputs.items():
            _atomic_create_or_match(path, raw)
    else:
        for path, expected in outputs.items():
            try:
                actual = path.read_bytes()
            except OSError as exc:
                raise SealError(f"missing canonical invalidation output: {path}") from exc
            if actual != expected:
                raise SealError(f"canonical invalidation output drift: {path}")
    print(
        json.dumps(
            {
                "status": "PASS",
                "mode": "write" if args.write else "check",
                "invalidation_sha256": sha256_bytes(invalidation_raw),
                "conflicts_sha256": sha256_bytes(conflicts_raw),
                "conflict_rows": 10,
                "evidence_artifacts": 438,
                "accepted_sessions": 86,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
