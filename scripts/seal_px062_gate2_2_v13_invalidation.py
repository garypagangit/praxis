#!/usr/bin/env python
"""Seal the failed PX-062 Gate 2.2 v1.3 balanced-consensus review.

This validator is candidate-specific and fail-closed. It authenticates the
prospectively registered repository checkpoint, reconstructs and re-reads the
complete four-pass raw evidence inventory, derives the canonical nonunanimous
row ledger, proves that the verifier and check-only finalizer reject the
evidence, and requires resolution and target-execution artifacts to be absent.

The default mode verifies byte-identical canonical outputs. The --write mode
may create them once, but never replaces a nonmatching existing file.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GATE = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728"
)
CONFLICTS = GATE / "label_audit_conflicts.jsonl"
INVALIDATION = GATE / "label_audit_invalidation.json"
REPORT = GATE / "LABEL_AUDIT_INVALIDATION_V1_3_20260729.md"
CONSENSUS_MANIFEST = GATE / "label_audit_evidence_manifest.json"
PROVISIONAL_RESOLUTION = GATE / "label_audit_provisional_resolution.json"
FINAL_RESOLUTION = GATE / "label_audit_resolution.json"

REPOSITORY_CHECKPOINT = "0291f2052b312a740cfb9779e2895bd4942330eb"
SOURCE_MANIFEST_CREATED_UTC = "2026-07-29T15:09:10.807419Z"
EXPECTED_FAILURE = (
    "label audits do not satisfy balanced 3-of-4 consensus on all 1032 rows"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "d1f93ee43842ebe22dd4f23851532aabd571ea70c26a587733d49a567cf9cf67"
)
EXPECTED_ARTIFACT_INVENTORY_SHA256 = (
    "331f366c4b40115ebdb349afe767320b9baa476ab506a3564f68070c9187e8ef"
)
EXPECTED_SESSION_BINDING_SHA256 = (
    "5a9416eb5ce9d8d505a507b29baf4253f678a7ac729e07546e545a2ab7ad6260"
)
EXPECTED_MODELS = {
    1: "gpt-5.6-sol",
    2: "gpt-5.6-terra",
    3: "gpt-5.6-sol",
    4: "gpt-5.6-terra",
}
EXPECTED_DISAGREEMENT_IDS = {
    1: ["g22-ba732261f65ca75f9d2e"],
    2: [
        "g22-0c93b02f79924ffb7f44",
        "g22-39d85e405d26fb74a7b8",
        "g22-a714fb66f15b32e3c59e",
        "g22-0fbb1effb594d2d413bb",
        "g22-00775f6db2ed35aca4d5",
    ],
    3: [
        "g22-b64001c05552057a61af",
        "g22-ba732261f65ca75f9d2e",
    ],
    4: [
        "g22-2636bb0b0cf5c0d1df7e",
        "g22-ba2c15332881e08c49d8",
    ],
}
EXPECTED_CONFIDENCE_COUNTS = {
    1: {"high": 971, "medium": 60, "low": 1},
    2: {"high": 968, "medium": 60, "low": 4},
    3: {"high": 960, "medium": 72, "low": 0},
    4: {"high": 966, "medium": 65, "low": 1},
}
EXPECTED_SINGLE_DISSENT_IDS = [
    "g22-0c93b02f79924ffb7f44",
    "g22-2636bb0b0cf5c0d1df7e",
    "g22-39d85e405d26fb74a7b8",
    "g22-a714fb66f15b32e3c59e",
    "g22-ba2c15332881e08c49d8",
    "g22-0fbb1effb594d2d413bb",
    "g22-b64001c05552057a61af",
    "g22-00775f6db2ed35aca4d5",
]
EXPECTED_REJECTED_ID = "g22-ba732261f65ca75f9d2e"
EXPECTED_DIAGNOSTIC_TASK_TYPE_COUNTS = {
    "available_single_skill": 1,
    "misleading_name_none": 2,
    "misleading_name_real_skill": 3,
    "unavailable_capability": 3,
}


SEALED_FILES: dict[str, tuple[str, int, str]] = {
    "tasks": (
        (GATE / "frozen_inputs/tasks.jsonl").as_posix(),
        2_119_409,
        "79becaa213147f98146777bdf1e0cee7baf0afd2cdbfb4226daae6a961d58b0c",
    ),
    "answer_key": (
        (GATE / "frozen_inputs/answer_key.jsonl").as_posix(),
        301_680,
        "e7de909cce9b8e10a8d148cac4a60012dfe4ac6e61d6034bdc7919dfbb0e44e1",
    ),
    "registry_catalog": (
        (GATE / "frozen_inputs/registry_catalog.json").as_posix(),
        20_543,
        "97b751849bd26e6bd9f347d5153f4237d995e4e0f8eda289faaa18d75523b905",
    ),
    "benchmark_manifest": (
        (GATE / "frozen_inputs/benchmark_manifest.json").as_posix(),
        9_731,
        "31d2c24f916b805bc9f70d9a582aead26468ae67788bf1e4bba6a11e94c06c30",
    ),
    "consensus_manifest": (
        CONSENSUS_MANIFEST.as_posix(),
        315_626,
        "509aad00a8a49be55fecfcaab4f4dc75573720d34ed5443edaa9f6d0ca762ee0",
    ),
    "audit_1_predictions": (
        (GATE / "label_audit_1_predictions.jsonl").as_posix(),
        190_033,
        "66f63173a6313568440751771cc64f2a116e4233869533bb392326affa894516",
    ),
    "audit_1_sidecar": (
        (GATE / "label_audit_1_run.json").as_posix(),
        226_810,
        "ead72c3fd10a879c73ff0325f46c1e3d9fa0482be888f00ffe51fd50dc140da9",
    ),
    "audit_2_predictions": (
        (GATE / "label_audit_2_predictions.jsonl").as_posix(),
        175_148,
        "aef8bcd99781620100f301814ddb3686946979243bb3ce9ce87f1460887cb8a4",
    ),
    "audit_2_sidecar": (
        (GATE / "label_audit_2_run.json").as_posix(),
        227_500,
        "ca1c32ea3c37c3300436308bb78a79bc93b7d00977d1d506b53c964bfea9dd5e",
    ),
    "audit_3_predictions": (
        (GATE / "label_audit_3_predictions.jsonl").as_posix(),
        187_795,
        "9800264e239892acae7e6bf933b6a23cd4b652264c8385a265ccfd2fd5b54a86",
    ),
    "audit_3_sidecar": (
        (GATE / "label_audit_3_run.json").as_posix(),
        226_810,
        "607e89845e41910cc37b8b8dcdfb9b44a8d289c00ed267fc848330cace9b9a1f",
    ),
    "audit_4_predictions": (
        (GATE / "label_audit_4_predictions.jsonl").as_posix(),
        175_297,
        "b08d4cea0afe149ee86773c33015e9937d0bc06a8d5e418c259ed6ac8494e511",
    ),
    "audit_4_sidecar": (
        (GATE / "label_audit_4_run.json").as_posix(),
        227_500,
        "a7118744e874e7d03047b35a14dde40b656896d439e882efb4be6f879861e6be",
    ),
    "verifier": (
        "scripts/verify_px062_gate2_2_v13_label_audits.py",
        7_890,
        "eb506c5e0188a71d78ce84b268d9b63739d20e8e4b45c392c2244d9fb803b8a9",
    ),
    "finalizer": (
        "scripts/finalize_px062_gate2_2_v13_labels.py",
        20_550,
        "4c5e254a6da22684cbccf2ac63315eb894c6561428ad8019d779ae16bc23f7d6",
    ),
}


TARGET_EXECUTION_PATHS = {
    "collection_output_dir": Path("outputs/px062_gate2_2_v1_3"),
    "launch_registration": Path(
        "manifests/px062_gate2_2_v1_3_20260728/confirmatory_registration.json"
    ),
    "launch_receipt": Path(
        "manifests/px062_gate2_2_v1_3_20260728/launch_receipt.json"
    ),
    "completion_registration": Path(
        "manifests/px062_gate2_2_v1_3_20260728/completion_registration.json"
    ),
    "adjudication_authorization": Path(
        "manifests/px062_gate2_2_v1_3_20260728/adjudication_authorization.json"
    ),
    "sealed_confirmation": GATE / "sealed_confirmation",
    "confirmatory_result": GATE / "PX062_GATE2_2_V1_3_CONFIRMATORY_RESULT.json",
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


def historical_consensus_verifier(
    root: Path, *, write_manifest: bool = False
) -> dict[str, Any]:
    """Authenticate all four audits from their recorded ancestor checkpoint."""

    if write_manifest:
        raise SealError("historical invalidation verification cannot write a manifest")
    try:
        try:
            from scripts.run_px062_gate2_2_v13_blind_audit import verify_consensus
        except ModuleNotFoundError:
            from run_px062_gate2_2_v13_blind_audit import (  # type: ignore[no-redef]
                verify_consensus,
            )
        return verify_consensus(
            root.resolve(), write_manifest=False, verification_mode="historical"
        )
    except Exception as exc:
        raise SealError("historical four-pass authentication failed") from exc


def validate_consensus_manifest(root: Path, raw: bytes) -> dict[str, Any]:
    manifest = strict_json(raw, CONSENSUS_MANIFEST.as_posix())
    if not isinstance(manifest, dict):
        raise SealError("audit consensus manifest is not an object")
    if (
        manifest.get("schema_version")
        != "px062-gate2.2-v1.3-label-audit-evidence-manifest-v1"
    ):
        raise SealError("audit consensus manifest schema drift")
    if manifest.get("created_utc") != SOURCE_MANIFEST_CREATED_UTC:
        raise SealError("audit consensus manifest timestamp drift")
    if manifest.get("answer_key_contents_included") is not False:
        raise SealError("audit consensus manifest contains answer-key contents")
    if manifest.get("pending_answer_checkpoint_hash_included") is not True:
        raise SealError("pending answer checkpoint hash is absent")
    if manifest.get("cross_audit_input_prompt_schema_hashes_match") is not True:
        raise SealError("cross-audit prompt/schema hashes do not match")

    reconstructed = historical_consensus_verifier(root, write_manifest=False)
    if reconstructed != manifest:
        raise SealError(
            "historical four-pass reconstruction differs from sealed manifest"
        )
    try:
        try:
            from scripts.run_px062_gate2_2_v13_blind_audit import (
                reauthenticate_manifest_artifact_inventory,
            )
        except ModuleNotFoundError:
            from run_px062_gate2_2_v13_blind_audit import (  # type: ignore[no-redef]
                reauthenticate_manifest_artifact_inventory,
            )
        reauthenticate_manifest_artifact_inventory(root.resolve(), manifest)
    except Exception as exc:
        raise SealError("raw evidence inventory reauthentication failed") from exc

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 873:
        raise SealError("audit consensus manifest must bind exactly 873 artifacts")
    paths: set[str] = set()
    roles: set[str] = set()
    for index, artifact in enumerate(artifacts, 1):
        if not isinstance(artifact, dict) or set(artifact) != {
            "bytes",
            "path",
            "role",
            "sha256",
        }:
            raise SealError(f"invalid evidence artifact entry {index}")
        path = artifact["path"]
        role = artifact["role"]
        if (
            not isinstance(path, str)
            or not isinstance(role, str)
            or path in paths
            or role in roles
        ):
            raise SealError(f"duplicate evidence identity at entry {index}")
        paths.add(path)
        roles.add(role)
    if sum(item["bytes"] for item in artifacts) != 10_151_496:
        raise SealError("evidence artifact byte aggregate drift")
    if sha256_bytes(canonical_json_bytes(artifacts)) != EXPECTED_ARTIFACT_INVENTORY_SHA256:
        raise SealError("evidence artifact inventory hash drift")
    evidence_prefix = (GATE / "label_audits").as_posix() + "/"
    if sum(path.startswith(evidence_prefix) for path in paths) != 860:
        raise SealError("per-attempt raw evidence file count drift")

    audits = manifest.get("audits")
    if not isinstance(audits, list) or len(audits) != 4:
        raise SealError("audit consensus manifest must contain exactly four audits")
    all_session_ids: list[str] = []
    session_binding: list[dict[str, Any]] = []
    for expected_slot, audit in enumerate(audits, 1):
        if not isinstance(audit, dict):
            raise SealError(f"invalid consensus audit {expected_slot}")
        session_ids = audit.get("accepted_session_ids")
        if (
            audit.get("slot") != expected_slot
            or audit.get("model") != EXPECTED_MODELS[expected_slot]
            or not isinstance(session_ids, list)
            or len(session_ids) != 43
            or not all(isinstance(item, str) and item for item in session_ids)
            or len(set(session_ids)) != 43
            or audit.get("prediction_sha256")
            != SEALED_FILES[f"audit_{expected_slot}_predictions"][2]
            or audit.get("sidecar_sha256")
            != SEALED_FILES[f"audit_{expected_slot}_sidecar"][2]
        ):
            raise SealError(f"invalid audit/session binding for slot {expected_slot}")

        _, sidecar_raw = validate_sealed_file(
            root, f"audit_{expected_slot}_sidecar"
        )
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
            event_summary = accepted[0].get("event_summary")
            if (
                not isinstance(session_id, str)
                or not isinstance(event_summary, dict)
                or event_summary.get("session_id") != session_id
            ):
                raise SealError(f"sidecar session binding invalid for audit {expected_slot}")
            observed.append(session_id)
        if attempt_count != 43 or observed != session_ids:
            raise SealError(f"sidecar sessions do not match audit {expected_slot}")
        all_session_ids.extend(session_ids)
        session_binding.append({"slot": expected_slot, "session_ids": session_ids})

    if len(all_session_ids) != 172 or len(set(all_session_ids)) != 172:
        raise SealError("accepted audit sessions are not exactly 172 unique IDs")
    if sha256_bytes(canonical_json_bytes(session_binding)) != EXPECTED_SESSION_BINDING_SHA256:
        raise SealError("accepted session binding hash drift")
    if manifest.get("global_session_ids") != {
        "accepted_count": 172,
        "all_attempt_count": 172,
        "all_disjoint_from_sealed_v1_2_blacklist": True,
        "all_unique_and_cross_audit_disjoint": True,
        "sealed_v1_2_blacklisted_count": 86,
    }:
        raise SealError("global session attestation drift")
    if manifest.get("isolated_workdirs") != {
        "all_unique": True,
        "attempt_count": 172,
    }:
        raise SealError("isolated workdir attestation drift")

    checkpoint = manifest.get("repository_checkpoint")
    if not isinstance(checkpoint, dict):
        raise SealError("repository checkpoint is missing")
    if (
        checkpoint.get("head_commit") != REPOSITORY_CHECKPOINT
        or checkpoint.get("upstream_commit") != REPOSITORY_CHECKPOINT
        or checkpoint.get("remote_commit") != REPOSITORY_CHECKPOINT
        or checkpoint.get("tracked_tree_clean") is not True
        or len(checkpoint.get("tracked_files", {})) != 19
        or sha256_bytes(canonical_json_bytes(checkpoint))
        != EXPECTED_CHECKPOINT_SHA256
    ):
        raise SealError("preregistered repository checkpoint drift")

    return {
        "artifact_count": len(artifacts),
        "artifact_bytes": sum(item["bytes"] for item in artifacts),
        "per_attempt_raw_evidence_files": 860,
        "artifact_inventory_sha256": EXPECTED_ARTIFACT_INVENTORY_SHA256,
        "accepted_session_count": len(all_session_ids),
        "all_attempt_count": 172,
        "retry_attempt_count": 0,
        "accepted_session_ids_sha256": EXPECTED_SESSION_BINDING_SHA256,
        "repository_checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "tracked_checkpoint_files": 19,
    }


def build_diagnostics(
    root: Path,
) -> tuple[list[dict[str, Any]], bytes, dict[str, Any]]:
    raw_by_key = {
        key: validate_sealed_file(root, key)[1]
        for key in (
            "tasks",
            "answer_key",
            "audit_1_predictions",
            "audit_2_predictions",
            "audit_3_predictions",
            "audit_4_predictions",
        )
    }
    tasks = strict_jsonl(raw_by_key["tasks"], SEALED_FILES["tasks"][0])
    answers = strict_jsonl(raw_by_key["answer_key"], SEALED_FILES["answer_key"][0])
    audits = [
        strict_jsonl(
            raw_by_key[f"audit_{slot}_predictions"],
            SEALED_FILES[f"audit_{slot}_predictions"][0],
        )
        for slot in (1, 2, 3, 4)
    ]
    if not all(len(rows) == 1032 for rows in [tasks, answers, *audits]):
        raise SealError("tasks, answers, and all four audits must contain 1,032 rows")
    task_ids = [row.get("task_id") for row in tasks]
    if len(set(task_ids)) != 1032 or any(
        [row.get("task_id") for row in rows] != task_ids
        for rows in [answers, *audits]
    ):
        raise SealError("task IDs are not unique and in identical canonical order")

    try:
        try:
            from scripts.verify_px062_gate2_2_v13_label_audits import evaluate
        except ModuleNotFoundError:
            from verify_px062_gate2_2_v13_label_audits import (  # type: ignore[no-redef]
                evaluate,
            )
        evaluation = evaluate(
            canonical_path(root, SEALED_FILES["tasks"][0]),
            canonical_path(root, SEALED_FILES["answer_key"][0]),
            [
                canonical_path(root, SEALED_FILES[f"audit_{slot}_predictions"][0])
                for slot in (1, 2, 3, 4)
            ],
            canonical_path(root, SEALED_FILES["registry_catalog"][0]),
        )
    except Exception as exc:
        raise SealError("v1.3 semantic evaluation failed unexpectedly") from exc

    if (
        evaluation.get("unanimous_key_rows") != 1023
        or evaluation.get("single_dissent_rows") != 8
        or evaluation.get("single_dissent_task_ids") != EXPECTED_SINGLE_DISSENT_IDS
        or evaluation.get("accepted_rows") != 1031
        or evaluation.get("rejected_rows") != 1
        or evaluation.get("rejected_task_ids") != [EXPECTED_REJECTED_ID]
        or evaluation.get("all_labels_balanced_consensus_accepted") is not False
    ):
        raise SealError("balanced-consensus semantic aggregate drift")
    rejected_details = evaluation.get("rejected_details")
    if rejected_details != [
        {
            "task_id": EXPECTED_REJECTED_ID,
            "expected_skill": "linear",
            "predictions": {
                "1": None,
                "2": "linear",
                "3": None,
                "4": "linear",
            },
            "key_vote_count": 2,
            "key_support_from_sol": False,
            "key_support_from_terra": True,
        }
    ]:
        raise SealError("rejected-row identity or model-family pattern drift")

    audit_summaries: list[dict[str, Any]] = []
    for slot, summary in enumerate(evaluation.get("audits", []), 1):
        if (
            summary.get("slot") != slot
            or summary.get("model") != EXPECTED_MODELS[slot]
            or summary.get("rows") != 1032
            or summary.get("agreement_with_answer_key")
            != 1032 - len(EXPECTED_DISAGREEMENT_IDS[slot])
            or summary.get("disagreement_task_ids")
            != EXPECTED_DISAGREEMENT_IDS[slot]
            or summary.get("confidence_counts")
            != EXPECTED_CONFIDENCE_COUNTS[slot]
        ):
            raise SealError(f"semantic audit summary drift for slot {slot}")
        audit_summaries.append(
            {
                "slot": slot,
                "model": EXPECTED_MODELS[slot],
                "rows": 1032,
                "agreement_with_answer_key": summary["agreement_with_answer_key"],
                "disagreement_task_ids": summary["disagreement_task_ids"],
                "confidence_counts": summary["confidence_counts"],
                "predictions": binding(f"audit_{slot}_predictions", rows=1032),
                "sidecar": binding(f"audit_{slot}_sidecar"),
                "accepted_session_count": 43,
                "attempt_count": 43,
                "retry_attempt_count": 0,
            }
        )
    if len(audit_summaries) != 4:
        raise SealError("semantic evaluation did not return four audit summaries")

    single_dissent = set(EXPECTED_SINGLE_DISSENT_IDS)
    rejected = {EXPECTED_REJECTED_ID}
    diagnostics: list[dict[str, Any]] = []
    task_type_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    expected_audit_schema = {"task_id", "predicted_skill", "confidence", "note"}
    for index, (task, answer) in enumerate(zip(tasks, answers, strict=True)):
        task_id = task["task_id"]
        if task_id not in single_dissent | rejected:
            continue
        prediction_rows = [rows[index] for rows in audits]
        if any(set(row) != expected_audit_schema for row in prediction_rows):
            raise SealError(f"audit schema drift at {task_id}")
        expected = answer.get("expected_skill")
        matching_slots = [
            slot
            for slot, row in enumerate(prediction_rows, 1)
            if row["predicted_skill"] == expected
        ]
        outcome = (
            "REJECTED_BALANCED_CONSENSUS"
            if task_id in rejected
            else "ACCEPTED_SINGLE_DISSENT"
        )
        task_type = answer.get("task_type")
        if not isinstance(task_type, str):
            raise SealError(f"missing task type at {task_id}")
        payload = {
            "task_id": task_id,
            "task_type": task_type,
            "prompt_sha256": sha256_bytes(task["prompt"].encode("utf-8")),
            "expected_skill": expected,
            "audits": [
                {
                    "slot": slot,
                    "model": EXPECTED_MODELS[slot],
                    "predicted_skill": row["predicted_skill"],
                    "confidence": row["confidence"],
                    "note": row["note"],
                }
                for slot, row in enumerate(prediction_rows, 1)
            ],
            "key_vote_count": len(matching_slots),
            "key_support_from_sol": bool(set(matching_slots) & {1, 3}),
            "key_support_from_terra": bool(set(matching_slots) & {2, 4}),
            "dissenting_slots": [
                slot for slot in (1, 2, 3, 4) if slot not in matching_slots
            ],
            "consensus_outcome": outcome,
        }
        row = dict(payload)
        row["canonical_row_sha256"] = sha256_bytes(canonical_json_bytes(payload))
        diagnostics.append(row)
        task_type_counts[task_type] += 1
        outcome_counts[outcome] += 1

    if len(diagnostics) != 9:
        raise SealError("canonical nonunanimous ledger must contain exactly nine rows")
    if dict(task_type_counts) != EXPECTED_DIAGNOSTIC_TASK_TYPE_COUNTS:
        raise SealError("nonunanimous task-type aggregate drift")
    if dict(outcome_counts) != {
        "ACCEPTED_SINGLE_DISSENT": 8,
        "REJECTED_BALANCED_CONSENSUS": 1,
    }:
        raise SealError("nonunanimous outcome aggregate drift")
    diagnostics_raw = b"".join(
        canonical_json_bytes(row) + b"\n" for row in diagnostics
    )
    semantic = {
        "status": "FAIL",
        "rows": 1032,
        "policy": evaluation["policy"],
        "unanimous_key_rows": 1023,
        "single_dissent_rows": 8,
        "single_dissent_task_ids": EXPECTED_SINGLE_DISSENT_IDS,
        "accepted_rows": 1031,
        "rejected_rows": 1,
        "rejected_task_ids": [EXPECTED_REJECTED_ID],
        "rejected_details": rejected_details,
        "all_labels_balanced_consensus_accepted": False,
        "audits": audit_summaries,
        "nonunanimous_by_task_type": EXPECTED_DIAGNOSTIC_TASK_TYPE_COUNTS,
        "nonunanimous_outcome_counts": dict(outcome_counts),
        "observed_family_split_on_rejected_row": {
            "sol_slots": {"slots": [1, 3], "prediction": None},
            "terra_slots": {"slots": [2, 4], "prediction": "linear"},
            "description": (
                "Both Sol passes selected NONE while both Terra passes selected "
                "the frozen Linear answer."
            ),
        },
    }
    semantic["canonical_evaluation_sha256"] = sha256_bytes(
        canonical_json_bytes(semantic)
    )
    return diagnostics, diagnostics_raw, semantic


def _assert_resolution_absent(root: Path) -> None:
    for logical in (PROVISIONAL_RESOLUTION, FINAL_RESOLUTION):
        if canonical_path(root, logical.as_posix()).exists():
            raise SealError(f"label-resolution output exists: {logical.as_posix()}")


def _rejection_record(key: str, function: str) -> dict[str, Any]:
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


def validate_verifier_failure(root: Path) -> dict[str, Any]:
    validate_sealed_file(root, "verifier")
    _assert_resolution_absent(root)
    try:
        try:
            from scripts.verify_px062_gate2_2_v13_label_audits import verify
        except ModuleNotFoundError:
            from verify_px062_gate2_2_v13_label_audits import (  # type: ignore[no-redef]
                verify,
            )
        verify(
            canonical_path(root, SEALED_FILES["tasks"][0]),
            canonical_path(root, SEALED_FILES["answer_key"][0]),
            [
                canonical_path(root, SEALED_FILES[f"audit_{slot}_predictions"][0])
                for slot in (1, 2, 3, 4)
            ],
            canonical_path(root, SEALED_FILES["registry_catalog"][0]),
        )
    except ValueError as exc:
        if type(exc) is not ValueError or str(exc) != EXPECTED_FAILURE:
            raise SealError(
                f"unexpected verifier failure: {type(exc).__name__}: {exc}"
            ) from exc
    else:
        raise SealError("verifier unexpectedly accepted the invalid audit consensus")
    _assert_resolution_absent(root)
    return _rejection_record("verifier", "verify")


def validate_finalizer_failure(root: Path) -> dict[str, Any]:
    validate_sealed_file(root, "finalizer")
    _assert_resolution_absent(root)
    try:
        try:
            from scripts.finalize_px062_gate2_2_v13_labels import (
                DEFAULT_CANDIDATE_DIR,
                DEFAULT_FINAL_RESOLUTION,
                DEFAULT_PRIOR_TASKS,
                DEFAULT_PROVISIONAL_RESOLUTION,
                DEFAULT_REGISTRY_INVENTORY,
                DEFAULT_SEED_BANK,
                prepare_finalization,
            )
        except ModuleNotFoundError:
            from finalize_px062_gate2_2_v13_labels import (  # type: ignore[no-redef]
                DEFAULT_CANDIDATE_DIR,
                DEFAULT_FINAL_RESOLUTION,
                DEFAULT_PRIOR_TASKS,
                DEFAULT_PROVISIONAL_RESOLUTION,
                DEFAULT_REGISTRY_INVENTORY,
                DEFAULT_SEED_BANK,
                prepare_finalization,
            )
        prepare_finalization(
            root=root,
            seed_bank_path=DEFAULT_SEED_BANK,
            registry_path=DEFAULT_REGISTRY_INVENTORY,
            prior_tasks_path=DEFAULT_PRIOR_TASKS,
            candidate_dir=DEFAULT_CANDIDATE_DIR,
            provisional_resolution_path=DEFAULT_PROVISIONAL_RESOLUTION,
            final_resolution_path=DEFAULT_FINAL_RESOLUTION,
            pair_verifier=historical_consensus_verifier,
        )
    except ValueError as exc:
        if type(exc) is not ValueError or str(exc) != EXPECTED_FAILURE:
            raise SealError(
                f"unexpected finalizer failure: {type(exc).__name__}: {exc}"
            ) from exc
    else:
        raise SealError("finalizer unexpectedly accepted the invalid audit consensus")
    _assert_resolution_absent(root)
    return _rejection_record("finalizer", "prepare_finalization")


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


def build_report(
    *, invalidation_sha256: str, conflicts_sha256: str, semantic: dict[str, Any]
) -> bytes:
    rejected = semantic["rejected_details"][0]
    text = f"""# PX-062 Gate 2.2 v1.3 Label-Audit Invalidation

Status: INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED

Decision: v1.3 is not eligible for Qwen/Mistral target collection or an AWS
experiment launch.

All four fresh blinded passes completed mechanically. Historical
authentication reconstructed all 873 byte-bound artifacts, re-read the 860
per-attempt raw evidence files, and accepted all 172 unique sessions at the
preregistered Git checkpoint {REPOSITORY_CHECKPOINT}. There were zero retries.

The prospectively frozen semantic rule required every answer-key row to
receive at least three of four votes, including support from both model
families. Of 1,032 rows:

- 1,023 were unanimous with the frozen answer;
- 8 had one dissent and were accepted by the preregistered rule;
- 1,031 total rows were accepted; and
- 1 row failed the rule, invalidating the complete v1.3 benchmark.

The rejected row is {rejected["task_id"]}. Its frozen answer is Linear.
Both Sol passes selected NONE, while both Terra passes selected Linear. The
frozen answer therefore received only two votes and no Sol-family support.
This is an observed model-family boundary disagreement, not a mechanical
runner or evidence-integrity failure.

The pinned verifier and real check-only finalizer both terminate with:

    ValueError: {EXPECTED_FAILURE}

Neither wrote a provisional or final label resolution. Canonical collection,
launch, completion, and adjudication paths are absent. No target-model
collection and no SageMaker job was launched.

No v1.3 row may be patched in place, no disputed-only rerun is acceptable,
and the unchanged inputs may not be rerun to seek a pass. The four v1.3
audits remain immutable historical evidence and cannot be reused as
acceptance evidence for a successor version.

## Canonical evidence seal

The write-once invalidation record is label_audit_invalidation.json with
SHA-256 {invalidation_sha256}.

The nine nonunanimous rows are preserved in frozen task order in
label_audit_conflicts.jsonl with SHA-256 {conflicts_sha256}. The ledger
distinguishes the eight accepted single-dissent rows from the one rejected
balanced-consensus row and binds every prompt, answer, four predictions,
confidence values, notes, outcome, and canonical row hash.

Run the fail-closed validator from the repository root:

    python scripts/seal_px062_gate2_2_v13_invalidation.py --root .

The validator authenticates the historical preregistration checkpoint,
reconstructs the exact evidence inventory, re-hashes every raw artifact,
re-evaluates balanced consensus, invokes both semantic rejection paths, and
requires all resolution and target-execution paths to remain absent.
"""
    return text.encode("utf-8")


def build_outputs(
    root: Path, *, probe_rejectors: bool = True
) -> tuple[bytes, bytes, bytes]:
    root = root.resolve()
    for key in SEALED_FILES:
        validate_sealed_file(root, key)
    _, manifest_raw = validate_sealed_file(root, "consensus_manifest")
    manifest_summary = validate_consensus_manifest(root, manifest_raw)
    diagnostics, conflicts_raw, semantic = build_diagnostics(root)
    _assert_resolution_absent(root)
    execution_absence = validate_target_execution_absence(root)

    verifier_check = (
        validate_verifier_failure(root)
        if probe_rejectors
        else _rejection_record("verifier", "verify")
    )
    finalizer_check = (
        validate_finalizer_failure(root)
        if probe_rejectors
        else _rejection_record("finalizer", "prepare_finalization")
    )
    record = {
        "schema_version": "px062-gate2.2-v1.3-label-audit-invalidation-v1",
        "experiment_id": "px062-skill-selection-gate2-2-v1-3-20260728",
        "benchmark_version": "1.3",
        "status": "INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED",
        "source_manifest_created_utc": SOURCE_MANIFEST_CREATED_UTC,
        "repository_checkpoint": {
            "commit": REPOSITORY_CHECKPOINT,
            "canonical_checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
            "historical_authentication": "PASS",
        },
        "sealed_inputs": {
            "tasks": binding("tasks", rows=1032),
            "answer_key": binding("answer_key", rows=1032),
            "registry_catalog": binding("registry_catalog"),
            "benchmark_manifest": binding("benchmark_manifest"),
        },
        "sealed_audit_evidence": {
            "mechanical_four_pass_verification": "PASS",
            "consensus_manifest": binding("consensus_manifest"),
            **manifest_summary,
        },
        "nonunanimous_ledger": {
            "path": CONFLICTS.as_posix(),
            "bytes": len(conflicts_raw),
            "sha256": sha256_bytes(conflicts_raw),
            "rows": len(diagnostics),
            "order": "frozen tasks.jsonl row order",
            "accepted_single_dissent_rows": 8,
            "rejected_balanced_consensus_rows": 1,
            "prompt_sha256_definition": (
                "SHA-256 of the exact UTF-8 prompt string bytes, without an added newline"
            ),
            "canonical_row_sha256_definition": (
                "SHA-256 of canonical compact sorted-key UTF-8 JSON for the row "
                "excluding canonical_row_sha256, without an added newline"
            ),
        },
        "semantic_gate": semantic,
        "resolution_absence": {
            "provisional": {
                "path": PROVISIONAL_RESOLUTION.as_posix(),
                "exists": False,
            },
            "final": {
                "path": FINAL_RESOLUTION.as_posix(),
                "exists": False,
            },
        },
        "verifier_check": verifier_check,
        "finalizer_check": finalizer_check,
        "target_execution_absence": execution_absence,
        "required_disposition": {
            "benchmark_version_1_3_valid_for_model_collection": False,
            "row_patching_permitted": False,
            "disputed_only_reaudit_permitted": False,
            "unchanged_input_rerun_to_seek_pass_permitted": False,
            "semantic_retry_permitted": False,
            "new_benchmark_version_required": True,
            "new_task_catalog_answer_hashes_required": True,
            "version_1_3_audits_reusable_for_acceptance": False,
            "qwen_or_mistral_gate2_2_collection_launched": False,
            "aws_gate2_2_training_job_launched": False,
        },
    }
    invalidation_raw = pretty_json_bytes(record)
    report_raw = build_report(
        invalidation_sha256=sha256_bytes(invalidation_raw),
        conflicts_sha256=sha256_bytes(conflicts_raw),
        semantic=semantic,
    )
    return invalidation_raw, conflicts_raw, report_raw


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
    invalidation_raw, conflicts_raw, report_raw = build_outputs(
        root, probe_rejectors=True
    )
    outputs = {
        canonical_path(root, INVALIDATION.as_posix()): invalidation_raw,
        canonical_path(root, CONFLICTS.as_posix()): conflicts_raw,
        canonical_path(root, REPORT.as_posix()): report_raw,
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
                "report_sha256": sha256_bytes(report_raw),
                "diagnostic_rows": 9,
                "rejected_rows": 1,
                "evidence_artifacts": 873,
                "accepted_sessions": 172,
                "retry_attempts": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
