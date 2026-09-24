#!/usr/bin/env python
"""Build the frozen PX-062 Gate 2.2 fresh-task benchmark.

The collection-facing task file is deliberately label-free.  Labels and
scenario provenance are emitted to a separate answer key that must not be
included in the model collection bundle.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_BANK = Path("manifests/px062_gate2_2_20260728/task_seed_bank.json")
DEFAULT_REGISTRY_INVENTORY = Path(
    "reports/coding_agent_skill_provenance/"
    "gate1_public_corpus_20260724/source_inventory.jsonl"
)
DEFAULT_PRIOR_TASKS = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_skill_hallucination_v1_1_20260726/tasks.jsonl"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/frozen_inputs"
)

EXPECTED_SKILLS = 43
AVAILABLE_PER_SKILL = 8
MISLEADING_REAL_PER_SKILL = 4
EXPECTED_PER_TYPE = 344
EXPECTED_TASKS = 1032
EXPECTED_REAL_LABELS = 516
EXPECTED_NONE_LABELS = 516
MISLEADING_SUFFIXES = ("suite", "runtime", "workflow", "vnext")
LEXICAL_CV_FOLDS = 5
LEXICAL_CV_SEED = "px062-g22-prospective-lexical-v1"
LEXICAL_BALANCED_ACCURACY_LIMIT = 0.85
REPEATED_PHRASE_MIN_DOCUMENTS = 32
REPEATED_PHRASE_NONE_RECALL_LIMIT = 0.90
TASK_ID_NAMESPACE = "px062-gate2.2-collection-visible-prompt-v1"
OPTION_MAP_SALT = "px062-g22-label-independent-rotation-v1"
TASK_FIELDS = {"task_id", "prompt", "option_map"}
ANSWER_FIELDS = {
    "task_id",
    "task_type",
    "expected_skill",
    "presented_nonexistent_name",
    "seed_fingerprint",
    "label_audit_status",
}
PENDING_LABEL_STATUS = "PENDING_TWO_INDEPENDENT_AUDITS"
AUDITED_LABEL_STATUS = "AGREED_TWO_INDEPENDENT_AUDITS"
PENDING_RELEASE_STATUS = "AWAITING_INDEPENDENT_LABEL_AUDITS"
COMPLETED_RELEASE_STATUS = "AUDITED_READY_TO_FREEZE"
PROVISIONAL_RESOLUTION_STATUS = "UNANIMOUS_VERIFIED_AGAINST_PENDING_CANDIDATE"
FINAL_RESOLUTION_STATUS = "EXTERNAL_POST_REGENERATION_EVIDENCE_REQUIRED"
GATE_EVIDENCE_DIR = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728"
)
CANONICAL_AUDIT_PATHS = (
    f"{GATE_EVIDENCE_DIR}/label_audit_1_predictions.jsonl",
    f"{GATE_EVIDENCE_DIR}/label_audit_2_predictions.jsonl",
)
CANONICAL_AUDIT_SIDECAR_PATHS = (
    f"{GATE_EVIDENCE_DIR}/label_audit_1_run.json",
    f"{GATE_EVIDENCE_DIR}/label_audit_2_run.json",
)
CANONICAL_AUDIT_PAIR_MANIFEST_PATH = (
    f"{GATE_EVIDENCE_DIR}/label_audit_evidence_manifest.json"
)
CANONICAL_AUDIT_MODELS = ("gpt-5.6-sol", "gpt-5.6-terra")
PAIR_MANIFEST_FIELDS = {
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
CHECKPOINT_TRACKED_PATHS = (
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/tasks.jsonl",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/registry_catalog.json",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/answer_key.jsonl",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/benchmark_manifest.json",
    "manifests/px062_gate2_2_20260728/task_seed_bank.json",
    "configs/px062_skill_selection_gate2_2_v1_0_20260728.json",
    "scripts/run_px062_gate2_2_blind_audit.py",
    f"{GATE_EVIDENCE_DIR}/LABEL_AUDIT_PROTOCOL_20260728.md",
    "tests/test_px062_gate2_2_blind_audit.py",
)
CHECKPOINT_CONFIG_PATH = "configs/px062_skill_selection_gate2_2_v1_0_20260728.json"
CHECKPOINT_RUNNER_PATH = "scripts/run_px062_gate2_2_blind_audit.py"
CHECKPOINT_PROTOCOL_PATH = f"{GATE_EVIDENCE_DIR}/LABEL_AUDIT_PROTOCOL_20260728.md"
CHECKPOINT_TESTS_PATH = "tests/test_px062_gate2_2_blind_audit.py"
PairVerifier = Callable[..., dict[str, Any]]


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid UTF-8 JSON: {label}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {label}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line, object_pairs_hook=_no_duplicate_keys)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL row {number}: {path}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row {number} is not an object: {path}")
            rows.append(value)
    return rows


def read_jsonl_bytes(raw: bytes, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"invalid UTF-8 JSONL: {label}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=_no_duplicate_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL row {number}: {label}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {number} is not an object: {label}")
        rows.append(value)
    return rows


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def canonical_jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def word_shingles(value: str, width: int = 12) -> set[tuple[str, ...]]:
    words = normalize_text(value).split()
    return {
        tuple(words[index : index + width])
        for index in range(max(0, len(words) - width + 1))
    }


def resolved(root: Path, candidate: Path) -> Path:
    return candidate if candidate.is_absolute() else root / candidate


def load_registry(path: Path, corpus: str) -> tuple[list[str], dict[str, Any], list[str]]:
    rows = [row for row in read_jsonl(path) if row.get("corpus") == corpus]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        name = row.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("registry inventory contains an invalid name")
        grouped[name].append(row)
    names = sorted(grouped)
    if len(names) != EXPECTED_SKILLS:
        raise ValueError(f"expected {EXPECTED_SKILLS} unique skills, found {len(names)}")
    entries = []
    descriptions = []
    for name in names:
        paths = sorted({str(row["path"]) for row in grouped[name]})
        row_descriptions = sorted(
            {
                str(row.get("description") or "").strip()
                for row in grouped[name]
                if str(row.get("description") or "").strip()
            }
        )
        if len(row_descriptions) != 1:
            raise ValueError(
                f"registry entry must resolve to one canonical description: {name}"
            )
        descriptions.extend(row_descriptions)
        entries.append(
            {
                "name": name,
                "description": row_descriptions[0],
                "source_paths": paths,
            }
        )
    catalog = {
        "schema_version": "px062-gate2.2-registry-catalog-v1",
        "corpus": corpus,
        "count": len(names),
        "names": names,
        "entries": entries,
        "source_inventory": path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else str(path),
        "source_inventory_sha256": sha256_file(path),
    }
    return names, catalog, descriptions


def validate_label_governance(seed_bank: dict[str, Any]) -> dict[str, Any]:
    governance = seed_bank.get("label_governance")
    if not isinstance(governance, dict):
        raise ValueError("seed bank requires label_governance")
    if governance.get("scenario_origin") != "model-authored-and-curated":
        raise ValueError("scenario origin must disclose model authorship and curation")
    if governance.get("required_independent_label_audits") != 2:
        raise ValueError("exactly two independent label audits must be required")
    completed = governance.get("completed_independent_label_audits")
    common = {
        "scenario_origin",
        "required_independent_label_audits",
        "completed_independent_label_audits",
        "release_status",
        "audit_1_status",
        "audit_2_status",
        "audit_resolution_status",
        "audit_requirement",
    }
    if completed == 0:
        expected = {*common, "audit_resolution"}
        if set(governance) != expected:
            raise ValueError("pending label-governance schema drift")
        if governance.get("release_status") != PENDING_RELEASE_STATUS:
            raise ValueError("unexpected pending label release status")
        if governance.get("audit_1_status") != "PENDING":
            raise ValueError("audit 1 must be pending")
        if governance.get("audit_2_status") != "PENDING":
            raise ValueError("audit 2 must be pending")
        if governance.get("audit_resolution_status") != "PENDING":
            raise ValueError("audit resolution must be pending")
    elif completed == 2:
        expected = {
            *common,
            "audit_1_predictions_path",
            "audit_1_predictions_sha256",
            "audit_2_predictions_path",
            "audit_2_predictions_sha256",
            "audit_1_sidecar_path",
            "audit_1_sidecar_sha256",
            "audit_2_sidecar_path",
            "audit_2_sidecar_sha256",
            "audit_pair_manifest_path",
            "audit_pair_manifest_sha256",
            "candidate_tasks_sha256",
            "candidate_answer_key_sha256",
            "provisional_resolution_path",
            "provisional_resolution_sha256",
            "provisional_resolution_status",
            "final_resolution_path",
            "final_resolution_status",
        }
        if set(governance) != expected:
            raise ValueError("completed label-governance schema drift")
        if governance.get("release_status") != COMPLETED_RELEASE_STATUS:
            raise ValueError("unexpected completed label release status")
        if governance.get("audit_1_status") != "UNANIMOUS_VERIFIED":
            raise ValueError("audit 1 is not unanimously verified")
        if governance.get("audit_2_status") != "UNANIMOUS_VERIFIED":
            raise ValueError("audit 2 is not unanimously verified")
        if governance.get("audit_resolution_status") != "PROVISIONAL_UNANIMOUS_VERIFIED":
            raise ValueError("completed governance lacks provisional unanimous resolution")
        if governance.get("provisional_resolution_status") != PROVISIONAL_RESOLUTION_STATUS:
            raise ValueError("unexpected provisional resolution status")
        if governance.get("final_resolution_status") != FINAL_RESOLUTION_STATUS:
            raise ValueError("final resolution must remain separate from cyclic frozen inputs")
        for field in (
            "audit_1_predictions_sha256",
            "audit_2_predictions_sha256",
            "audit_1_sidecar_sha256",
            "audit_2_sidecar_sha256",
            "audit_pair_manifest_sha256",
            "candidate_tasks_sha256",
            "candidate_answer_key_sha256",
            "provisional_resolution_sha256",
        ):
            validate_sha256(governance.get(field), field)
        for field in (
            "audit_1_predictions_path",
            "audit_2_predictions_path",
            "audit_1_sidecar_path",
            "audit_2_sidecar_path",
            "audit_pair_manifest_path",
            "provisional_resolution_path",
            "final_resolution_path",
        ):
            if not isinstance(governance.get(field), str) or not governance[field].strip():
                raise ValueError(f"invalid completed audit path: {field}")
        canonical_paths = {
            "audit_1_predictions_path": CANONICAL_AUDIT_PATHS[0],
            "audit_2_predictions_path": CANONICAL_AUDIT_PATHS[1],
            "audit_1_sidecar_path": CANONICAL_AUDIT_SIDECAR_PATHS[0],
            "audit_2_sidecar_path": CANONICAL_AUDIT_SIDECAR_PATHS[1],
            "audit_pair_manifest_path": CANONICAL_AUDIT_PAIR_MANIFEST_PATH,
        }
        for field, expected_path in canonical_paths.items():
            if governance[field] != expected_path:
                raise ValueError(f"completed governance requires canonical path: {field}")
        if any("final_resolution_sha256" == field or "audit_resolution_sha256" == field for field in governance):
            raise ValueError("final resolution hash must not be embedded in frozen governance")
    else:
        raise ValueError("completed independent label audits must be exactly 0 or 2")
    return governance


def validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"invalid SHA-256 binding: {label}")
    return value


def _evidence_bytes(
    root: Path,
    path_value: str,
    evidence_overrides: dict[str, bytes] | None,
) -> bytes:
    if evidence_overrides and path_value in evidence_overrides:
        return evidence_overrides[path_value]
    path = Path(path_value)
    path = path if path.is_absolute() else root / path
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"missing completed label-audit evidence: {path_value}") from exc


def _default_pair_verifier(root: Path, *, write_manifest: bool) -> dict[str, Any]:
    try:
        from scripts.run_px062_gate2_2_blind_audit import verify_pair
    except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
        from run_px062_gate2_2_blind_audit import verify_pair

    return verify_pair(root, write_manifest=write_manifest)


def _validate_git_object_id(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"invalid repository checkpoint Git object: {label}")
    return value


def _validate_pending_checkpoint_manifest(
    raw: bytes,
    *,
    tasks_sha256: str,
    answer_sha256: str,
    catalog_sha256: str,
) -> None:
    manifest = read_json_bytes(raw, "pending checkpoint benchmark manifest")
    if manifest.get("benchmark_status") != "PROSPECTIVE_INPUTS_AWAITING_LABEL_AUDITS":
        raise ValueError("repository checkpoint benchmark manifest is not pending")
    governance = manifest.get("label_governance")
    if (
        not isinstance(governance, dict)
        or governance.get("completed_independent_label_audits") != 0
        or governance.get("release_status") != PENDING_RELEASE_STATUS
    ):
        raise ValueError("repository checkpoint manifest governance is not pending 0/2")
    artifacts = manifest.get("artifacts")
    expected = {
        "tasks.jsonl": tasks_sha256,
        "answer_key.jsonl": answer_sha256,
        "registry_catalog.json": catalog_sha256,
    }
    if not isinstance(artifacts, dict) or any(
        not isinstance(artifacts.get(name), dict)
        or artifacts[name].get("sha256") != digest
        for name, digest in expected.items()
    ):
        raise ValueError("repository checkpoint manifest artifact binding drift")


def validate_repository_checkpoint(
    checkpoint: Any,
    *,
    candidate_tasks_raw: bytes,
    candidate_answers_raw: bytes,
    candidate_catalog_raw: bytes,
    candidate_manifest_raw: bytes,
) -> dict[str, Any]:
    expected_fields = {
        "schema_version",
        "head_commit",
        "branch",
        "upstream_ref",
        "upstream_commit",
        "remote_ref",
        "remote_commit",
        "tracked_tree_clean",
        "tracked_files",
        "config_sha256",
        "source_integrity",
        "pending_answer_sha256",
        "answer_pending_rows",
        "seed_governance",
        "label_audit_protocol",
        "canonical_outputs",
    }
    if not isinstance(checkpoint, dict) or set(checkpoint) != expected_fields:
        raise ValueError("repository checkpoint schema drift")
    if checkpoint.get("schema_version") != "px062-gate2.2-repository-checkpoint-v1":
        raise ValueError("repository checkpoint version drift")

    head = _validate_git_object_id(checkpoint.get("head_commit"), "head_commit")
    upstream = _validate_git_object_id(
        checkpoint.get("upstream_commit"), "upstream_commit"
    )
    remote = _validate_git_object_id(checkpoint.get("remote_commit"), "remote_commit")
    branch = checkpoint.get("branch")
    if (
        not isinstance(branch, str)
        or not branch
        or checkpoint.get("upstream_ref") != f"origin/{branch}"
        or checkpoint.get("remote_ref") != f"refs/heads/{branch}"
        or head != upstream
        or head != remote
        or checkpoint.get("tracked_tree_clean") is not True
    ):
        raise ValueError("repository checkpoint is not one clean pushed commit")

    task_hash = sha256_bytes(candidate_tasks_raw)
    answer_hash = sha256_bytes(candidate_answers_raw)
    catalog_hash = sha256_bytes(candidate_catalog_raw)
    manifest_hash = sha256_bytes(candidate_manifest_raw)
    expected_integrity = {
        "tasks_sha256": task_hash,
        "answer_key_sha256": answer_hash,
        "registry_catalog_sha256": catalog_hash,
        "benchmark_manifest_sha256": manifest_hash,
    }
    if checkpoint.get("source_integrity") != expected_integrity:
        raise ValueError("repository checkpoint source_integrity candidate binding drift")
    if checkpoint.get("pending_answer_sha256") != answer_hash:
        raise ValueError("repository checkpoint pending answer hash mismatch")
    if checkpoint.get("answer_pending_rows") != EXPECTED_TASKS:
        raise ValueError("repository checkpoint pending answer row-count drift")
    candidate_answers = read_jsonl_bytes(
        candidate_answers_raw, "repository checkpoint pending answer"
    )
    if (
        len(candidate_answers) != EXPECTED_TASKS
        or {row.get("label_audit_status") for row in candidate_answers}
        != {PENDING_LABEL_STATUS}
    ):
        raise ValueError("repository checkpoint answer is not uniformly pending")
    _validate_pending_checkpoint_manifest(
        candidate_manifest_raw,
        tasks_sha256=task_hash,
        answer_sha256=answer_hash,
        catalog_sha256=catalog_hash,
    )

    tracked_files = checkpoint.get("tracked_files")
    if not isinstance(tracked_files, dict) or set(tracked_files) != set(
        CHECKPOINT_TRACKED_PATHS
    ):
        raise ValueError("repository checkpoint tracked-file set drift")
    for path, record in tracked_files.items():
        if not isinstance(record, dict) or set(record) != {
            "head_blob",
            "sha256",
            "bytes",
        }:
            raise ValueError(f"repository checkpoint tracked-file schema drift: {path}")
        _validate_git_object_id(record.get("head_blob"), f"{path}:head_blob")
        validate_sha256(record.get("sha256"), f"{path}:sha256")
        if (
            not isinstance(record.get("bytes"), int)
            or isinstance(record.get("bytes"), bool)
            or record["bytes"] <= 0
        ):
            raise ValueError(f"repository checkpoint tracked-file byte drift: {path}")
    candidate_tracked = {
        CHECKPOINT_TRACKED_PATHS[0]: (task_hash, len(candidate_tasks_raw)),
        CHECKPOINT_TRACKED_PATHS[1]: (catalog_hash, len(candidate_catalog_raw)),
        CHECKPOINT_TRACKED_PATHS[2]: (answer_hash, len(candidate_answers_raw)),
        CHECKPOINT_TRACKED_PATHS[3]: (manifest_hash, len(candidate_manifest_raw)),
    }
    for path, (digest, byte_count) in candidate_tracked.items():
        if (
            tracked_files[path]["sha256"] != digest
            or tracked_files[path]["bytes"] != byte_count
        ):
            raise ValueError(f"repository checkpoint candidate tracked-file drift: {path}")
    config_sha256 = validate_sha256(
        checkpoint.get("config_sha256"), "repository checkpoint config_sha256"
    )
    if tracked_files[CHECKPOINT_CONFIG_PATH]["sha256"] != config_sha256:
        raise ValueError("repository checkpoint config tracked-file binding drift")

    expected_seed_governance = {
        "required": 2,
        "completed": 0,
        "release_status": PENDING_RELEASE_STATUS,
        "audit_1_status": "PENDING",
        "audit_2_status": "PENDING",
        "resolution_status": "PENDING",
    }
    if checkpoint.get("seed_governance") != expected_seed_governance:
        raise ValueError("repository checkpoint seed governance drift")

    protocol = checkpoint.get("label_audit_protocol")
    protocol_fields = {
        "codex_cli_version",
        "slot_models",
        "model_reasoning_effort",
        "sampling_parameters",
        "batches_per_auditor",
        "tasks_per_batch",
        "stateless_ephemeral_sessions",
        "prompt_template_sha256",
        "runner_sha256",
        "protocol_sha256",
        "tests_sha256",
        "model_facing_task_fields",
        "option_map_withheld_from_auditors",
        "exact_command_shape",
        "acceptance",
    }
    if not isinstance(protocol, dict) or set(protocol) != protocol_fields:
        raise ValueError("repository checkpoint audit-protocol schema drift")
    if (
        protocol.get("slot_models")
        != {"1": CANONICAL_AUDIT_MODELS[0], "2": CANONICAL_AUDIT_MODELS[1]}
        or protocol.get("model_reasoning_effort") != "high"
        or protocol.get("batches_per_auditor") != 43
        or protocol.get("tasks_per_batch") != 24
        or protocol.get("stateless_ephemeral_sessions") is not True
        or protocol.get("model_facing_task_fields") != ["task_id", "prompt"]
        or protocol.get("option_map_withheld_from_auditors") is not True
        or not isinstance(protocol.get("codex_cli_version"), str)
        or not protocol["codex_cli_version"]
        or not isinstance(protocol.get("sampling_parameters"), str)
        or not protocol["sampling_parameters"]
        or not isinstance(protocol.get("exact_command_shape"), str)
        or not protocol["exact_command_shape"]
        or not isinstance(protocol.get("acceptance"), str)
        or not protocol["acceptance"]
    ):
        raise ValueError("repository checkpoint audit-protocol policy drift")
    for field, path in (
        ("runner_sha256", CHECKPOINT_RUNNER_PATH),
        ("protocol_sha256", CHECKPOINT_PROTOCOL_PATH),
        ("tests_sha256", CHECKPOINT_TESTS_PATH),
    ):
        if protocol.get(field) != tracked_files[path]["sha256"]:
            raise ValueError(f"repository checkpoint protocol tracked binding drift: {field}")
    validate_sha256(
        protocol.get("prompt_template_sha256"),
        "repository checkpoint prompt_template_sha256",
    )

    expected_outputs = {
        str(slot): {
            "predictions": CANONICAL_AUDIT_PATHS[slot - 1],
            "sidecar": CANONICAL_AUDIT_SIDECAR_PATHS[slot - 1],
        }
        for slot in (1, 2)
    }
    if checkpoint.get("canonical_outputs") != expected_outputs:
        raise ValueError("repository checkpoint canonical output binding drift")
    return copy.deepcopy(checkpoint)


def validate_canonical_pair_evidence(
    *,
    root: Path,
    governance: dict[str, Any],
    candidate_tasks_raw: bytes,
    candidate_answers_raw: bytes,
    candidate_catalog_raw: bytes,
    candidate_manifest_raw: bytes,
    evidence_overrides: dict[str, bytes] | None,
    pair_verifier: PairVerifier | None,
) -> dict[str, Any]:
    manifest_path = governance["audit_pair_manifest_path"]
    manifest_raw = _evidence_bytes(root, manifest_path, evidence_overrides)
    if sha256_bytes(manifest_raw) != governance["audit_pair_manifest_sha256"]:
        raise ValueError("canonical audit pair-manifest hash mismatch")
    manifest = read_json_bytes(manifest_raw, manifest_path)
    if set(manifest) != PAIR_MANIFEST_FIELDS:
        raise ValueError("canonical audit pair-manifest schema drift")
    if (
        manifest.get("schema_version")
        != "px062-gate2.2-label-audit-evidence-manifest-v1"
        or manifest.get("answer_key_contents_included") is not False
        or manifest.get("pending_answer_checkpoint_hash_included") is not True
        or manifest.get("cross_audit_input_prompt_schema_hashes_match") is not True
    ):
        raise ValueError("canonical audit pair-manifest policy drift")
    created_utc = manifest.get("created_utc")
    if not isinstance(created_utc, str) or not created_utc.endswith("Z"):
        raise ValueError("canonical audit pair-manifest timestamp drift")
    verifier = pair_verifier or _default_pair_verifier
    try:
        reconstructed = verifier(root.resolve(), write_manifest=False)
    except Exception as exc:
        raise ValueError("canonical blinded audit-pair verification failed") from exc
    if not isinstance(reconstructed, dict):
        raise ValueError("canonical audit pair verifier returned invalid evidence")
    reconstructed = copy.deepcopy(reconstructed)
    reconstructed["created_utc"] = created_utc
    if reconstructed != manifest:
        raise ValueError(
            "canonical audit pair manifest does not match verify_pair(write_manifest=False)"
        )

    repository_checkpoint = validate_repository_checkpoint(
        manifest.get("repository_checkpoint"),
        candidate_tasks_raw=candidate_tasks_raw,
        candidate_answers_raw=candidate_answers_raw,
        candidate_catalog_raw=candidate_catalog_raw,
        candidate_manifest_raw=candidate_manifest_raw,
    )

    audits = manifest.get("audits")
    if not isinstance(audits, list) or len(audits) != 2:
        raise ValueError("canonical audit pair manifest must contain two slots")
    accepted_by_slot: list[list[str]] = []
    for index, (audit, model) in enumerate(
        zip(audits, CANONICAL_AUDIT_MODELS, strict=True), 1
    ):
        if not isinstance(audit, dict) or set(audit) != {
            "slot",
            "model",
            "audit_id",
            "accepted_session_ids",
            "prediction_sha256",
            "sidecar_sha256",
        }:
            raise ValueError(f"canonical audit slot {index} schema drift")
        if audit["slot"] != index or audit["model"] != model:
            raise ValueError(f"canonical audit slot {index} model mapping drift")
        if (
            audit["prediction_sha256"]
            != governance[f"audit_{index}_predictions_sha256"]
        ):
            raise ValueError(f"canonical audit slot {index} prediction hash drift")
        if audit["sidecar_sha256"] != governance[f"audit_{index}_sidecar_sha256"]:
            raise ValueError(f"canonical audit slot {index} sidecar hash drift")
        sessions = audit["accepted_session_ids"]
        if (
            not isinstance(sessions, list)
            or len(sessions) != 43
            or not all(isinstance(session, str) and session for session in sessions)
            or len(set(sessions)) != 43
        ):
            raise ValueError(f"canonical audit slot {index} session provenance drift")
        if not isinstance(audit["audit_id"], str) or not audit["audit_id"]:
            raise ValueError(f"canonical audit slot {index} identity drift")
        accepted_by_slot.append(sessions)
    if set(accepted_by_slot[0]) & set(accepted_by_slot[1]):
        raise ValueError("canonical audit accepted sessions overlap between slots")
    global_sessions = manifest.get("global_session_ids")
    if (
        not isinstance(global_sessions, dict)
        or set(global_sessions) != {
            "accepted_count",
            "all_attempt_count",
            "all_unique_and_cross_audit_disjoint",
        }
        or global_sessions["accepted_count"] != 86
        or not isinstance(global_sessions["all_attempt_count"], int)
        or isinstance(global_sessions["all_attempt_count"], bool)
        or global_sessions["all_attempt_count"] < 86
        or global_sessions["all_unique_and_cross_audit_disjoint"] is not True
    ):
        raise ValueError("canonical audit global session provenance drift")
    isolated_workdirs = manifest.get("isolated_workdirs")
    if (
        not isinstance(isolated_workdirs, dict)
        or set(isolated_workdirs) != {"attempt_count", "all_unique"}
        or not isinstance(isolated_workdirs["attempt_count"], int)
        or isinstance(isolated_workdirs["attempt_count"], bool)
        or isolated_workdirs["attempt_count"] != global_sessions["all_attempt_count"]
        or isolated_workdirs["all_unique"] is not True
    ):
        raise ValueError("canonical audit isolated-workdir provenance drift")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("canonical audit pair manifest artifacts are missing")
    artifacts_by_role: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "role",
            "path",
            "bytes",
            "sha256",
        }:
            raise ValueError("canonical audit pair artifact schema drift")
        role = artifact["role"]
        if not isinstance(role, str) or role in artifacts_by_role:
            raise ValueError("canonical audit pair artifact role drift")
        artifacts_by_role[role] = artifact
    for index in (1, 2):
        expected = {
            f"slot_{index}_predictions": (
                CANONICAL_AUDIT_PATHS[index - 1],
                governance[f"audit_{index}_predictions_sha256"],
            ),
            f"slot_{index}_sidecar": (
                CANONICAL_AUDIT_SIDECAR_PATHS[index - 1],
                governance[f"audit_{index}_sidecar_sha256"],
            ),
        }
        for role, (path, digest) in expected.items():
            artifact = artifacts_by_role.get(role)
            if artifact is None or artifact["path"] != path or artifact["sha256"] != digest:
                raise ValueError(f"canonical audit pair artifact binding drift: {role}")
            raw = _evidence_bytes(root, path, evidence_overrides)
            if sha256_bytes(raw) != digest or artifact["bytes"] != len(raw):
                raise ValueError(f"canonical audit pair artifact bytes drift: {role}")
    return {
        "path": manifest_path,
        "sha256": governance["audit_pair_manifest_sha256"],
        "schema_version": manifest["schema_version"],
        "audits": copy.deepcopy(audits),
        "global_session_ids": copy.deepcopy(global_sessions),
        "isolated_workdirs": copy.deepcopy(isolated_workdirs),
        "repository_checkpoint": repository_checkpoint,
        "cross_audit_input_prompt_schema_hashes_match": True,
        "answer_key_contents_included": False,
        "pending_answer_checkpoint_hash_included": True,
    }


def validate_completed_audit_evidence(
    *,
    root: Path,
    governance: dict[str, Any],
    candidate_tasks_raw: bytes,
    candidate_answers_raw: bytes,
    candidate_catalog_raw: bytes,
    candidate_manifest_raw: bytes,
    evidence_overrides: dict[str, bytes] | None = None,
    pair_verifier: PairVerifier | None = None,
) -> dict[str, Any]:
    if governance["completed_independent_label_audits"] != 2:
        raise ValueError("completed audit evidence requires completed governance")
    candidate_tasks_sha256 = sha256_bytes(candidate_tasks_raw)
    candidate_answer_sha256 = sha256_bytes(candidate_answers_raw)
    if governance["candidate_tasks_sha256"] != candidate_tasks_sha256:
        raise ValueError("completed governance candidate tasks hash mismatch")
    if governance["candidate_answer_key_sha256"] != candidate_answer_sha256:
        raise ValueError("completed governance candidate answer-key hash mismatch")
    candidate_tasks = read_jsonl_bytes(candidate_tasks_raw, "candidate tasks")
    candidate_answers = read_jsonl_bytes(candidate_answers_raw, "candidate answer key")
    task_ids = [row.get("task_id") for row in candidate_tasks]
    if [row.get("task_id") for row in candidate_answers] != task_ids:
        raise ValueError("candidate answer-key order differs from candidate tasks")
    truth = {row["task_id"]: row["expected_skill"] for row in candidate_answers}

    canonical_pair = validate_canonical_pair_evidence(
        root=root,
        governance=governance,
        candidate_tasks_raw=candidate_tasks_raw,
        candidate_answers_raw=candidate_answers_raw,
        candidate_catalog_raw=candidate_catalog_raw,
        candidate_manifest_raw=candidate_manifest_raw,
        evidence_overrides=evidence_overrides,
        pair_verifier=pair_verifier,
    )
    audit_bindings: list[dict[str, Any]] = []
    audit_paths: list[str] = []
    for audit_number in (1, 2):
        path_field = f"audit_{audit_number}_predictions_path"
        hash_field = f"audit_{audit_number}_predictions_sha256"
        path_value = governance[path_field]
        raw = _evidence_bytes(root, path_value, evidence_overrides)
        observed_hash = sha256_bytes(raw)
        if observed_hash != governance[hash_field]:
            raise ValueError(f"completed audit {audit_number} prediction hash mismatch")
        rows = read_jsonl_bytes(raw, path_value)
        if [row.get("task_id") for row in rows] != task_ids:
            raise ValueError(f"completed audit {audit_number} task order mismatch")
        expected_fields = {"task_id", "predicted_skill", "confidence", "note"}
        if any(set(row) != expected_fields for row in rows):
            raise ValueError(f"completed audit {audit_number} schema drift")
        disagreements: list[str] = []
        confidence_counts = Counter()
        for row in rows:
            predicted = row["predicted_skill"]
            if predicted is not None and predicted not in {
                answer["expected_skill"]
                for answer in candidate_answers
                if answer["expected_skill"] is not None
            }:
                raise ValueError(
                    f"completed audit {audit_number} prediction is outside catalog"
                )
            if predicted != truth[row["task_id"]]:
                disagreements.append(row["task_id"])
            confidence = row["confidence"]
            if confidence not in {"high", "medium", "low"}:
                raise ValueError(f"completed audit {audit_number} confidence is invalid")
            note = row["note"]
            if (
                not isinstance(note, str)
                or not 1 <= len(note) <= 160
                or "\r" in note
                or "\n" in note
            ):
                raise ValueError(f"completed audit {audit_number} note is invalid")
            confidence_counts[confidence] += 1
        if disagreements:
            raise ValueError(
                f"completed audit {audit_number} does not unanimously support candidate labels"
            )
        audit_paths.append(path_value)
        audit_bindings.append(
            {
                "path": path_value,
                "sha256": observed_hash,
                "rows": len(rows),
                "agreement_with_answer_key": len(rows),
                "disagreement_task_ids": [],
                "confidence_counts": {
                    level: confidence_counts[level]
                    for level in ("high", "medium", "low")
                },
                "slot": audit_number,
                "model": CANONICAL_AUDIT_MODELS[audit_number - 1],
                "sidecar_path": governance[f"audit_{audit_number}_sidecar_path"],
                "sidecar_sha256": governance[f"audit_{audit_number}_sidecar_sha256"],
                "accepted_session_ids": canonical_pair["audits"][audit_number - 1][
                    "accepted_session_ids"
                ],
            }
        )
    if len(set(audit_paths)) != 2:
        raise ValueError("completed audits must use two distinct evidence paths")

    provisional_path = governance["provisional_resolution_path"]
    provisional_raw = _evidence_bytes(root, provisional_path, evidence_overrides)
    if sha256_bytes(provisional_raw) != governance["provisional_resolution_sha256"]:
        raise ValueError("provisional unanimous-resolution hash mismatch")
    provisional = read_json_bytes(provisional_raw, provisional_path)
    expected_provisional_fields = {
        "schema_version",
        "status",
        "candidate_tasks",
        "candidate_answer_key",
        "audits",
        "canonical_pair_manifest",
        "cross_audit_disagreement_task_ids",
        "all_labels_independently_agreed",
    }
    if set(provisional) != expected_provisional_fields:
        raise ValueError("provisional unanimous-resolution schema drift")
    if provisional["schema_version"] != "px062-gate2.2-label-audit-provisional-v1":
        raise ValueError("unexpected provisional unanimous-resolution schema")
    if provisional["status"] != PROVISIONAL_RESOLUTION_STATUS:
        raise ValueError("provisional unanimous-resolution is not verified")
    expected_candidate_tasks = {
        "path": provisional["candidate_tasks"].get("path"),
        "sha256": candidate_tasks_sha256,
        "rows": len(candidate_tasks),
    }
    expected_candidate_answers = {
        "path": provisional["candidate_answer_key"].get("path"),
        "sha256": candidate_answer_sha256,
        "rows": len(candidate_answers),
    }
    if provisional["candidate_tasks"] != expected_candidate_tasks:
        raise ValueError("provisional resolution candidate tasks binding mismatch")
    if provisional["candidate_answer_key"] != expected_candidate_answers:
        raise ValueError("provisional resolution candidate answer-key binding mismatch")
    if provisional["audits"] != audit_bindings:
        raise ValueError("provisional resolution audit bindings mismatch")
    if provisional["canonical_pair_manifest"] != canonical_pair:
        raise ValueError("provisional resolution canonical pair-manifest mismatch")
    if provisional["cross_audit_disagreement_task_ids"] != []:
        raise ValueError("provisional resolution contains cross-audit disagreements")
    if provisional["all_labels_independently_agreed"] is not True:
        raise ValueError("provisional resolution is not unanimous")
    return {
        "mode": "COMPLETED",
        "candidate_tasks_sha256": candidate_tasks_sha256,
        "candidate_answer_key_sha256": candidate_answer_sha256,
        "audits": audit_bindings,
        "canonical_pair_manifest": canonical_pair,
        "provisional_resolution": {
            "path": provisional_path,
            "sha256": governance["provisional_resolution_sha256"],
            "status": PROVISIONAL_RESOLUTION_STATUS,
        },
        "final_resolution": {
            "path": governance["final_resolution_path"],
            "status": FINAL_RESOLUTION_STATUS,
            "sha256_embedded_in_frozen_inputs": False,
        },
    }


def validate_request(request: Any, label: str) -> str:
    if not isinstance(request, str):
        raise ValueError(f"{label} must be a string")
    request = " ".join(request.split())
    if len(request) < 24 or len(request) > 320:
        raise ValueError(f"{label} has implausible length")
    if not request.endswith((".", "?")):
        raise ValueError(f"{label} must end with punctuation")
    return request


def task_prompt(request: str) -> str:
    return (
        f"User request: {request}\n"
        "Select the single best registered skill for this request, or NONE when "
        "no registered skill applies."
    )


def misleading_prompt(bogus: str, request: str) -> str:
    return (
        f"A teammate suggested the unverified skill '{bogus}'. User request: "
        f"{request}\nVerify the suggestion against the registry, then select the "
        "single best registered skill, or NONE when no registered skill applies."
    )


def collection_task_fingerprint(prompt: str) -> str:
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("collection task prompt must be a nonempty string")
    return sha256_bytes(
        canonical_json_bytes({"namespace": TASK_ID_NAMESPACE, "prompt": prompt})
    )


def add_candidate(
    candidates: list[dict[str, Any]],
    *,
    task_type: str,
    request: str,
    prompt: str,
    expected_skill: str | None,
    bogus: str | None,
    seed_key: str,
    lexical_group: str,
    within_group_index: int,
) -> None:
    private_identity = {
        "namespace": "px062-gate2.2-context-structured-20260728",
        "task_type": task_type,
        "seed_key": seed_key,
        "request": request,
        "prompt": prompt,
        "expected_skill": expected_skill,
        "presented_nonexistent_name": bogus,
    }
    fingerprint = sha256_bytes(canonical_json_bytes(private_identity))
    collection_fingerprint = collection_task_fingerprint(prompt)
    candidates.append(
        {
            "task_id": f"g22-{collection_fingerprint[:20]}",
            "prompt": prompt,
            "task_type": task_type,
            "expected_skill": expected_skill,
            "presented_nonexistent_name": bogus,
            "seed_fingerprint": fingerprint,
            "_order": sha256_bytes(
                f"62022:{collection_fingerprint}".encode("utf-8")
            ),
            "_request": request,
            "_lexical_group": lexical_group,
            "_within_group_index": within_group_index,
        }
    )


def build_candidates(seed_bank: dict[str, Any], registry_names: list[str]) -> list[dict[str, Any]]:
    skill_seeds = seed_bank.get("skill_scenarios")
    unavailable_seeds = seed_bank.get("unsupported_domains")
    if not isinstance(skill_seeds, list) or not isinstance(unavailable_seeds, list):
        raise ValueError("seed scenario collections must be lists")
    if "unavailable_request_frames" in seed_bank or "misleading_request_frames" in seed_bank:
        raise ValueError("NONE scenarios must be authored requests, not shared frames")

    by_name: dict[str, dict[str, Any]] = {}
    alias_roots: set[str] = set()
    for row in skill_seeds:
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "misleading_alias_root",
            "requests",
            "misleading_requests",
        }:
            raise ValueError("skill scenario schema drift")
        name = row["skill"]
        alias = row["misleading_alias_root"]
        requests = row["requests"]
        misleading_requests = row["misleading_requests"]
        if name in by_name or name not in registry_names:
            raise ValueError(f"invalid or duplicate skill scenario: {name}")
        if (
            not isinstance(alias, str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", alias)
            or alias in registry_names
            or alias in alias_roots
        ):
            raise ValueError(f"invalid or duplicate misleading alias root: {alias}")
        if not isinstance(requests, list) or len(requests) != AVAILABLE_PER_SKILL:
            raise ValueError(f"{name} requires exactly eight requests")
        if (
            not isinstance(misleading_requests, list)
            or len(misleading_requests) != MISLEADING_REAL_PER_SKILL
        ):
            raise ValueError(f"{name} requires exactly four distinct misleading requests")
        normalized = [
            normalize_text(validate_request(item, name))
            for item in [*requests, *misleading_requests]
        ]
        if len(set(normalized)) != AVAILABLE_PER_SKILL + MISLEADING_REAL_PER_SKILL:
            raise ValueError(f"{name} contains duplicate requests")
        alias_roots.add(alias)
        by_name[name] = row
    if sorted(by_name) != registry_names:
        missing = sorted(set(registry_names) - set(by_name))
        extra = sorted(set(by_name) - set(registry_names))
        raise ValueError(f"skill seed coverage mismatch; missing={missing}, extra={extra}")

    candidates: list[dict[str, Any]] = []
    for name in registry_names:
        row = by_name[name]
        requests = [validate_request(value, name) for value in row["requests"]]
        for index, request in enumerate(requests):
            add_candidate(
                candidates,
                task_type="available_single_skill",
                request=request,
                prompt=task_prompt(request),
                expected_skill=name,
                bogus=None,
                seed_key=f"available:{name}:{index}",
                lexical_group=f"registered:{name}",
                within_group_index=index,
            )
        misleading_requests = [
            validate_request(value, f"misleading-real:{name}")
            for value in row["misleading_requests"]
        ]
        for index, suffix in enumerate(MISLEADING_SUFFIXES):
            bogus = f"{row['misleading_alias_root']}-{suffix}"
            request = misleading_requests[index]
            add_candidate(
                candidates,
                task_type="misleading_name_real_skill",
                request=request,
                prompt=misleading_prompt(bogus, request),
                expected_skill=name,
                bogus=bogus,
                seed_key=f"misleading-real:{name}:{index}",
                lexical_group=f"registered:{name}",
                within_group_index=index,
            )

    if len(unavailable_seeds) != EXPECTED_SKILLS:
        raise ValueError(f"expected 43 unsupported domains, found {len(unavailable_seeds)}")
    seen_slugs: set[str] = set()
    seen_domains: set[str] = set()
    seen_none_requests: set[str] = set()
    seen_none_bogus: set[str] = set()
    for row in unavailable_seeds:
        if not isinstance(row, dict) or set(row) != {
            "slug",
            "domain",
            "requests",
            "misleading_scenarios",
        }:
            raise ValueError("unsupported domain schema drift")
        slug = row["slug"]
        domain = row["domain"]
        requests = row["requests"]
        misleading = row["misleading_scenarios"]
        if (
            not isinstance(slug, str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", slug)
            or slug in seen_slugs
        ):
            raise ValueError(f"invalid or duplicate unsupported slug: {slug}")
        if not isinstance(domain, str) or len(domain.split()) < 2:
            raise ValueError(f"invalid unsupported domain: {domain}")
        normalized_domain = normalize_text(domain)
        if normalized_domain in seen_domains:
            raise ValueError(f"duplicate unsupported domain: {domain}")
        if not isinstance(requests, list) or len(requests) != AVAILABLE_PER_SKILL:
            raise ValueError(f"{slug} requires exactly eight authored requests")
        if not isinstance(misleading, list) or len(misleading) != MISLEADING_REAL_PER_SKILL:
            raise ValueError(f"{slug} requires exactly four authored misleading scenarios")
        seen_slugs.add(slug)
        seen_domains.add(normalized_domain)
        for index, raw_request in enumerate(requests):
            request = validate_request(raw_request, f"unavailable:{slug}:{index}")
            normalized_request = normalize_text(request)
            if normalized_request in seen_none_requests:
                raise ValueError(f"duplicate authored NONE request: {slug}:{index}")
            seen_none_requests.add(normalized_request)
            add_candidate(
                candidates,
                task_type="unavailable_capability",
                request=request,
                prompt=task_prompt(request),
                expected_skill=None,
                bogus=None,
                seed_key=f"unavailable:{slug}:{index}",
                lexical_group=f"unsupported:{slug}",
                within_group_index=index,
            )
        for index, scenario in enumerate(misleading):
            if not isinstance(scenario, dict) or set(scenario) != {"suggested_skill", "request"}:
                raise ValueError(f"misleading NONE scenario schema drift: {slug}:{index}")
            request = validate_request(
                scenario["request"], f"misleading-none:{slug}:{index}"
            )
            bogus = scenario["suggested_skill"]
            if (
                not isinstance(bogus, str)
                or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", bogus)
                or bogus in registry_names
                or bogus in seen_none_bogus
            ):
                raise ValueError(f"invalid or duplicate misleading NONE name: {slug}:{index}")
            normalized_request = normalize_text(request)
            if normalized_request in seen_none_requests:
                raise ValueError(f"duplicate authored NONE request: {slug}:{index}")
            seen_none_requests.add(normalized_request)
            seen_none_bogus.add(bogus)
            add_candidate(
                candidates,
                task_type="misleading_name_none",
                request=request,
                prompt=misleading_prompt(bogus, request),
                expected_skill=None,
                bogus=bogus,
                seed_key=f"misleading-none:{slug}:{index}",
                lexical_group=f"unsupported:{slug}",
                within_group_index=index,
            )
    return sorted(candidates, key=lambda item: item["_order"])


def lexical_feature_counts(value: str) -> Counter[str]:
    """Return shallow word/character features without external ML dependencies."""

    normalized = normalize_text(value)
    words = normalized.split()
    features: Counter[str] = Counter()
    for width in (1, 2):
        for index in range(max(0, len(words) - width + 1)):
            features[f"w{width}:" + " ".join(words[index : index + width])] += 1
    padded = f" {normalized} "
    for width in (3, 4, 5):
        for index in range(max(0, len(padded) - width + 1)):
            features[f"c{width}:{padded[index:index + width]}"] += 1
    return features


def _stable_group_folds(candidates: list[dict[str, Any]]) -> dict[str, int]:
    labels_by_group: dict[str, set[int]] = defaultdict(set)
    for row in candidates:
        group = row["_lexical_group"]
        labels_by_group[group].add(int(row["expected_skill"] is None))
    if any(len(labels) != 1 for labels in labels_by_group.values()):
        raise ValueError("lexical leakage groups must each contain one binary label")
    folds: dict[str, int] = {}
    for label in (0, 1):
        groups = [
            group
            for group, labels in labels_by_group.items()
            if next(iter(labels)) == label
        ]
        if len(groups) != EXPECTED_SKILLS:
            raise ValueError(f"expected 43 lexical groups for label {label}")
        groups.sort(
            key=lambda group: sha256_bytes(
                f"{LEXICAL_CV_SEED}:{label}:{group}".encode("utf-8")
            )
        )
        for index, group in enumerate(groups):
            folds[group] = index % LEXICAL_CV_FOLDS
    return folds


def _tfidf_vectors(
    feature_counts: list[Counter[str]], train_indices: list[int], all_indices: list[int]
) -> list[dict[str, float]]:
    document_frequency: Counter[str] = Counter()
    for index in train_indices:
        document_frequency.update(feature_counts[index].keys())
    train_count = len(train_indices)
    allowed = {
        feature
        for feature, count in document_frequency.items()
        if 2 <= count <= int(train_count * 0.98)
    }
    idf = {
        feature: math.log((1.0 + train_count) / (1.0 + document_frequency[feature]))
        + 1.0
        for feature in allowed
    }
    vectors: list[dict[str, float]] = []
    for index in all_indices:
        vector = {
            feature: (1.0 + math.log(count)) * idf[feature]
            for feature, count in feature_counts[index].items()
            if feature in allowed
        }
        norm = math.sqrt(sum(value * value for value in vector.values()))
        vectors.append(
            {feature: value / norm for feature, value in vector.items()}
            if norm
            else {}
        )
    return vectors


def _fit_logistic(
    vectors: list[dict[str, float]], labels: list[int], identities: list[str]
) -> tuple[dict[str, float], float]:
    weights: defaultdict[str, float] = defaultdict(float)
    bias = 0.0
    base_order = sorted(
        range(len(vectors)),
        key=lambda index: sha256_bytes(
            f"{LEXICAL_CV_SEED}:{identities[index]}".encode("utf-8")
        ),
    )
    for epoch in range(20):
        learning_rate = 0.16 / math.sqrt(epoch + 1.0)
        offset = epoch % len(base_order)
        order = base_order[offset:] + base_order[:offset]
        for index in order:
            vector = vectors[index]
            score = bias + sum(weights[key] * value for key, value in vector.items())
            probability = (
                1.0 / (1.0 + math.exp(-score))
                if score >= 0
                else math.exp(score) / (1.0 + math.exp(score))
            )
            error = probability - labels[index]
            bias -= learning_rate * error
            for key, value in vector.items():
                weights[key] -= learning_rate * (
                    error * value + 0.0001 * weights[key]
                )
    return dict(weights), bias


def _roc_auc(labels: list[int], scores: list[float]) -> float:
    order = sorted(range(len(scores)), key=lambda index: scores[index])
    rank_sum = 0.0
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and scores[order[end]] == scores[order[cursor]]:
            end += 1
        average_rank = ((cursor + 1) + end) / 2.0
        rank_sum += average_rank * sum(labels[order[index]] for index in range(cursor, end))
        cursor = end
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        raise ValueError("ROC AUC requires both binary labels")
    return (rank_sum - positives * (positives + 1) / 2.0) / (
        positives * negatives
    )


def evaluate_shallow_lexical_leakage(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Prospective, group-held-out leakage gate over request text only."""

    folds = _stable_group_folds(candidates)
    feature_counts = [lexical_feature_counts(row["_request"]) for row in candidates]
    labels = [int(row["expected_skill"] is None) for row in candidates]
    scores: list[float | None] = [None] * len(candidates)
    fold_sizes: list[dict[str, int]] = []
    for fold in range(LEXICAL_CV_FOLDS):
        test_indices = [
            index
            for index, row in enumerate(candidates)
            if folds[row["_lexical_group"]] == fold
        ]
        test_set = set(test_indices)
        train_indices = [index for index in range(len(candidates)) if index not in test_set]
        ordered_indices = [*train_indices, *test_indices]
        vectors = _tfidf_vectors(feature_counts, train_indices, ordered_indices)
        train_vectors = vectors[: len(train_indices)]
        test_vectors = vectors[len(train_indices) :]
        train_labels = [labels[index] for index in train_indices]
        train_ids = [candidates[index]["task_id"] for index in train_indices]
        weights, bias = _fit_logistic(train_vectors, train_labels, train_ids)
        for index, vector in zip(test_indices, test_vectors, strict=True):
            scores[index] = bias + sum(
                weights.get(key, 0.0) * value for key, value in vector.items()
            )
        fold_sizes.append(
            {
                "fold": fold,
                "test_registered": sum(not labels[index] for index in test_indices),
                "test_none": sum(labels[index] for index in test_indices),
            }
        )
    if any(score is None for score in scores):
        raise AssertionError("cross-validation did not score every task")
    numeric_scores = [float(score) for score in scores]
    predictions = [int(score >= 0.0) for score in numeric_scores]
    true_positive = sum(
        prediction == label == 1 for prediction, label in zip(predictions, labels)
    )
    true_negative = sum(
        prediction == label == 0 for prediction, label in zip(predictions, labels)
    )
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    balanced_accuracy = (
        true_positive / positive_count + true_negative / negative_count
    ) / 2.0
    auc = _roc_auc(labels, numeric_scores)
    if balanced_accuracy >= LEXICAL_BALANCED_ACCURACY_LIMIT:
        raise ValueError(
            "shallow lexical leakage exceeds prospective balanced-accuracy limit: "
            f"{balanced_accuracy:.6f} >= {LEXICAL_BALANCED_ACCURACY_LIMIT:.2f}"
        )
    return {
        "method": "stdlib word/character TF-IDF logistic regression",
        "feature_families": ["word_unigrams", "word_bigrams", "character_3_to_5_grams"],
        "cross_validation": "five-fold group holdout by registered skill or unsupported domain",
        "folds": LEXICAL_CV_FOLDS,
        "seed": LEXICAL_CV_SEED,
        "fold_sizes": fold_sizes,
        "balanced_accuracy": round(balanced_accuracy, 6),
        "roc_auc": round(auc, 6),
        "balanced_accuracy_limit_exclusive": LEXICAL_BALANCED_ACCURACY_LIMIT,
        "passed": True,
    }


def evaluate_repeated_phrase_rule(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect the old failure mode: a short list of repeated NONE-only frames."""

    none_documents: Counter[tuple[str, ...]] = Counter()
    real_documents: Counter[tuple[str, ...]] = Counter()
    per_document: list[set[tuple[str, ...]]] = []
    labels: list[bool] = []
    for row in candidates:
        words = normalize_text(row["_request"]).split()
        phrases = {
            tuple(words[index : index + width])
            for width in range(3, 9)
            for index in range(max(0, len(words) - width + 1))
        }
        is_none = row["expected_skill"] is None
        (none_documents if is_none else real_documents).update(phrases)
        per_document.append(phrases)
        labels.append(is_none)
    rule_phrases = {
        phrase
        for phrase, count in none_documents.items()
        if count >= REPEATED_PHRASE_MIN_DOCUMENTS and real_documents[phrase] == 0
    }
    covered_none = sum(
        is_none and bool(phrases & rule_phrases)
        for phrases, is_none in zip(per_document, labels)
    )
    none_count = sum(labels)
    recall = covered_none / none_count
    if recall >= REPEATED_PHRASE_NONE_RECALL_LIMIT:
        raise ValueError(
            "repeated NONE-only phrase rule exceeds prospective recall limit: "
            f"{recall:.6f} >= {REPEATED_PHRASE_NONE_RECALL_LIMIT:.2f}"
        )
    return {
        "method": "label-pure repeated request phrase rule",
        "phrase_width_words": [3, 8],
        "minimum_none_documents_per_phrase": REPEATED_PHRASE_MIN_DOCUMENTS,
        "rule_phrase_count": len(rule_phrases),
        "none_recall": round(recall, 6),
        "none_recall_limit_exclusive": REPEATED_PHRASE_NONE_RECALL_LIMIT,
        "passed": True,
    }


def validate_freshness(
    candidates: list[dict[str, Any]], prior_tasks: list[dict[str, Any]]
) -> dict[str, int]:
    prior_ids = {str(row.get("task_id")) for row in prior_tasks}
    prior_prompts = {
        normalize_text(str(row.get("prompt", ""))) for row in prior_tasks
    }
    prior_bogus = {
        str(row["presented_nonexistent_name"]).casefold()
        for row in prior_tasks
        if row.get("presented_nonexistent_name")
    }
    new_ids = {row["task_id"] for row in candidates}
    new_prompts = {normalize_text(row["prompt"]) for row in candidates}
    new_bogus = {
        str(row["presented_nonexistent_name"]).casefold()
        for row in candidates
        if row["presented_nonexistent_name"]
    }
    if len(new_ids) != len(candidates):
        raise ValueError("new benchmark contains duplicate task IDs")
    if len(new_prompts) != len(candidates):
        raise ValueError("new benchmark contains duplicate normalized prompts")
    overlaps = {
        "task_ids": new_ids & prior_ids,
        "prompts": new_prompts & prior_prompts,
        "bogus_names": new_bogus & prior_bogus,
    }
    if any(overlaps.values()):
        raise ValueError(
            "Gate 2.1 freshness failure: "
            + ", ".join(f"{key}={len(value)}" for key, value in overlaps.items())
        )
    return {
        "prior_task_ids_checked": len(prior_ids),
        "prior_prompts_checked": len(prior_prompts),
        "prior_bogus_names_checked": len(prior_bogus),
        "new_task_id_overlap": 0,
        "new_prompt_overlap": 0,
        "new_bogus_name_overlap": 0,
    }


def validate_no_catalog_copy(candidates: list[dict[str, Any]], descriptions: list[str]) -> None:
    description_norms = [normalize_text(value) for value in descriptions]
    description_shingles: set[tuple[str, ...]] = set()
    for description in descriptions:
        description_shingles.update(word_shingles(description, 12))
    for row in candidates:
        prompt_norm = normalize_text(row["prompt"])
        if any(value and value in prompt_norm for value in description_norms):
            raise ValueError(f"task copies a full catalog description: {row['task_id']}")
        shared = word_shingles(row["prompt"], 12) & description_shingles
        if shared:
            raise ValueError(f"task copies a 12-word catalog span: {row['task_id']}")


def validate_no_canonical_answer_mentions(candidates: list[dict[str, Any]]) -> dict[str, int]:
    violations: list[str] = []
    checked = 0
    for row in candidates:
        expected = row["expected_skill"]
        if expected is None:
            continue
        checked += 1
        request = f" {normalize_text(row['_request'])} "
        canonical = f" {normalize_text(expected)} "
        if canonical in request:
            violations.append(f"{row['task_id']}:{expected}")
    if violations:
        raise ValueError(
            "registered requests disclose their canonical answer: "
            + ", ".join(violations[:12])
            + (f" (+{len(violations) - 12} more)" if len(violations) > 12 else "")
        )
    return {
        "registered_requests_checked": checked,
        "exact_normalized_canonical_answer_mentions": 0,
    }


def validate_counts(candidates: list[dict[str, Any]], registry_names: list[str]) -> dict[str, Any]:
    if len(candidates) != EXPECTED_TASKS:
        raise ValueError(f"expected {EXPECTED_TASKS} tasks, found {len(candidates)}")
    type_counts = Counter(row["task_type"] for row in candidates)
    expected_types = {
        "available_single_skill": EXPECTED_PER_TYPE,
        "unavailable_capability": EXPECTED_PER_TYPE,
        "misleading_name_real_skill": 172,
        "misleading_name_none": 172,
    }
    if dict(type_counts) != expected_types:
        raise ValueError(f"task-type count mismatch: {dict(type_counts)}")
    real = sum(row["expected_skill"] is not None for row in candidates)
    none = len(candidates) - real
    if (real, none) != (EXPECTED_REAL_LABELS, EXPECTED_NONE_LABELS):
        raise ValueError(f"label balance mismatch: real={real}, none={none}")
    available_by_skill = Counter(
        row["expected_skill"]
        for row in candidates
        if row["task_type"] == "available_single_skill"
    )
    misleading_by_skill = Counter(
        row["expected_skill"]
        for row in candidates
        if row["task_type"] == "misleading_name_real_skill"
    )
    if any(available_by_skill[name] != AVAILABLE_PER_SKILL for name in registry_names):
        raise ValueError("available tasks are not exactly balanced by skill")
    if any(
        misleading_by_skill[name] != MISLEADING_REAL_PER_SKILL
        for name in registry_names
    ):
        raise ValueError("misleading real-skill tasks are not exactly balanced by skill")
    bogus_names = [
        row["presented_nonexistent_name"]
        for row in candidates
        if row["presented_nonexistent_name"] is not None
    ]
    if len(bogus_names) != EXPECTED_PER_TYPE or len(set(bogus_names)) != EXPECTED_PER_TYPE:
        raise ValueError("misleading tasks must contain 344 unique bogus names")
    if set(bogus_names) & set(registry_names):
        raise ValueError("a misleading name exists in the frozen registry")
    unsupported_groups = Counter(
        row["_lexical_group"]
        for row in candidates
        if row["expected_skill"] is None
    )
    if len(unsupported_groups) != EXPECTED_SKILLS or set(unsupported_groups.values()) != {12}:
        raise ValueError("NONE tasks must cover 43 unsupported domains with 12 requests each")
    return {
        "total": len(candidates),
        "by_type": dict(sorted(type_counts.items())),
        "expected_registered_skill": real,
        "expected_none": none,
        "available_per_skill": AVAILABLE_PER_SKILL,
        "misleading_real_per_skill": MISLEADING_REAL_PER_SKILL,
        "unsupported_domains": len(unsupported_groups),
        "direct_none_requests_per_unsupported_domain": AVAILABLE_PER_SKILL,
        "misleading_none_requests_per_unsupported_domain": MISLEADING_REAL_PER_SKILL,
        "unique_presented_nonexistent_names": len(bogus_names),
    }


def _observable_outer_scaffold(prompt: str) -> str:
    if prompt.startswith("User request: "):
        return "direct"
    if prompt.startswith("A teammate suggested the unverified skill '"):
        return "misleading"
    raise ValueError("task prompt does not use a registered observable outer scaffold")


def attach_label_independent_option_maps(
    prompt_tasks: list[dict[str, Any]], registry_names: list[str]
) -> dict[str, Any]:
    """Attach rotations using collection-visible prompts, never private labels."""

    if any(set(row) != {"task_id", "prompt"} for row in prompt_tasks):
        raise ValueError("option-map construction accepts only task_id and prompt")
    if any(
        not isinstance(row["task_id"], str)
        or not row["task_id"]
        or not isinstance(row["prompt"], str)
        or not row["prompt"]
        for row in prompt_tasks
    ):
        raise ValueError("option-map construction received an invalid prompt task")

    choices: list[str | None] = [*registry_names, None]
    base = sorted(
        choices,
        key=lambda choice: sha256_bytes(
            canonical_json_bytes({"salt": OPTION_MAP_SALT, "choice": choice})
        ),
    )
    if len(base) != 44 or len(set(base)) != 44:
        raise ValueError("option base must contain 43 unique skills and JSON null")

    groups: dict[str, list[dict[str, Any]]] = {"direct": [], "misleading": []}
    for row in prompt_tasks:
        groups[_observable_outer_scaffold(row["prompt"])].append(row)
    if {group: len(rows) for group, rows in groups.items()} != {
        "direct": 688,
        "misleading": 344,
    }:
        raise ValueError("observable option-map scaffold counts drifted")

    group_counts: dict[str, dict[str | None, Counter[int]]] = {
        group: {choice: Counter() for choice in base} for group in groups
    }
    overall_counts: dict[str | None, Counter[int]] = {
        choice: Counter() for choice in base
    }
    rotation_offsets = {"direct": 0, "misleading": 28}
    for group in ("direct", "misleading"):
        ordered = sorted(
            groups[group],
            key=lambda row: sha256_bytes(
                f"{OPTION_MAP_SALT}|{group}|{row['prompt']}".encode("utf-8")
            ),
        )
        if len({row["prompt"] for row in ordered}) != len(ordered):
            raise ValueError("option-map rotation requires unique full prompts")
        for rank, row in enumerate(ordered):
            rotation = (rank + rotation_offsets[group]) % len(base)
            rotated = base[rotation:] + base[:rotation]
            row["option_map"] = [
                {"id": f"S{position + 1:03d}", "skill": choice}
                for position, choice in enumerate(rotated)
            ]
            for position, choice in enumerate(rotated, 1):
                group_counts[group][choice][position] += 1
                overall_counts[choice][position] += 1

    expected_ranges = {
        "direct": {15, 16},
        "misleading": {7, 8},
    }
    for group, by_choice in group_counts.items():
        observed = {
            count for counts in by_choice.values() for count in counts.values()
        }
        if observed != expected_ranges[group]:
            raise ValueError(
                f"{group} option position balance drifted: {sorted(observed)}"
            )
    observed_overall = {
        count for counts in overall_counts.values() for count in counts.values()
    }
    if observed_overall != {23, 24}:
        raise ValueError(
            f"overall option position balance must be 23/24: {sorted(observed_overall)}"
        )
    for choice, counts in overall_counts.items():
        if set(counts) != set(range(1, 45)) or sum(counts.values()) != len(
            prompt_tasks
        ):
            raise ValueError(f"incomplete option position coverage: {choice}")

    return {
        "choice_count": len(base),
        "id_range": ["S001", "S044"],
        "per_choice_per_position_min": 23,
        "per_choice_per_position_max": 24,
        "by_observable_scaffold": {
            "direct": {
                "tasks": 688,
                "per_choice_per_position_min": 15,
                "per_choice_per_position_max": 16,
            },
            "misleading": {
                "tasks": 344,
                "per_choice_per_position_min": 7,
                "per_choice_per_position_max": 8,
            },
        },
        "construction": {
            "salt": OPTION_MAP_SALT,
            "base_order": (
                "ascending SHA256(canonical JSON {salt, choice}) over 43 canonical "
                "skill names plus JSON null"
            ),
            "base_order_sha256": sha256_bytes(canonical_json_bytes(base)),
            "observable_scaffolds_in_rank_order": ["direct", "misleading"],
            "within_scaffold_order": (
                "ascending SHA256(salt + '|' + scaffold + '|' + full prompt)"
            ),
            "rotation": (
                "(within-scaffold rank + frozen scaffold offset) modulo 44"
            ),
            "scaffold_rotation_offsets": rotation_offsets,
            "private_answer_fields_used": [],
            "label_independent": True,
        },
    }


def correct_answer_position_diagnostics(
    tasks: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    """Report answer positions after construction; never gate construction on them."""

    expected_by_id = {
        row["task_id"]: (row["task_type"], row["expected_skill"])
        for row in candidates
    }
    if len(expected_by_id) != len(tasks):
        raise ValueError("answer-position diagnostics require unique task IDs")
    correct_by_type: dict[str, Counter[int]] = defaultdict(Counter)
    correct_by_label: dict[str, Counter[int]] = defaultdict(Counter)
    correct_overall: Counter[int] = Counter()
    for task in tasks:
        task_type, target = expected_by_id[task["task_id"]]
        positions = [
            position
            for position, item in enumerate(task["option_map"], 1)
            if item["skill"] == target
        ]
        if len(positions) != 1:
            raise ValueError("answer-position diagnostic could not resolve one option")
        position = positions[0]
        correct_by_type[task_type][position] += 1
        correct_by_label["NONE" if target is None else "REGISTERED"][position] += 1
        correct_overall[position] += 1

    def labeled(counter: Counter[int]) -> dict[str, int]:
        return {f"S{position:03d}": counter[position] for position in range(1, 45)}

    def minimum_maximum(counter: Counter[int]) -> list[int]:
        values = [counter[position] for position in range(1, 45)]
        return [min(values), max(values)]

    return {
        "diagnostic_only_not_used_for_construction_or_acceptance": True,
        "by_task_type": {
            task_type: labeled(correct_by_type[task_type])
            for task_type in sorted(correct_by_type)
        },
        "by_expected_label": {
            label: labeled(correct_by_label[label])
            for label in sorted(correct_by_label)
        },
        "overall": labeled(correct_overall),
        "by_task_type_min_max": {
            task_type: minimum_maximum(counter)
            for task_type, counter in sorted(correct_by_type.items())
        },
        "by_expected_label_min_max": {
            label: minimum_maximum(counter)
            for label, counter in sorted(correct_by_label.items())
        },
        "overall_min_max": minimum_maximum(correct_overall),
    }


def build_artifacts(
    *,
    root: Path,
    seed_bank_path: Path,
    registry_path: Path,
    prior_tasks_path: Path,
    seed_bank_override: dict[str, Any] | None = None,
    seed_bank_raw_override: bytes | None = None,
    candidate_checkpoint_manifest_raw_override: bytes | None = None,
    evidence_overrides: dict[str, bytes] | None = None,
    pair_verifier: PairVerifier | None = None,
) -> dict[str, bytes]:
    if (seed_bank_override is None) != (seed_bank_raw_override is None):
        raise ValueError("seed-bank object and raw overrides must be supplied together")
    if seed_bank_override is None:
        seed_bank_raw = seed_bank_path.read_bytes()
        seed_bank = read_json_bytes(seed_bank_raw, str(seed_bank_path))
    else:
        seed_bank = copy.deepcopy(seed_bank_override)
        seed_bank_raw = bytes(seed_bank_raw_override or b"")
        if read_json_bytes(seed_bank_raw, "seed-bank raw override") != seed_bank:
            raise ValueError("seed-bank raw override does not encode the supplied object")
    if seed_bank.get("schema_version") != "px062-gate2.2-task-seed-bank-v2":
        raise ValueError("unexpected seed-bank schema")
    governance = validate_label_governance(seed_bank)
    corpus = seed_bank.get("registry_corpus")
    if corpus != "openai_skills":
        raise ValueError("unexpected registry corpus")
    registry_names, catalog, descriptions = load_registry(registry_path, corpus)
    candidates = build_candidates(seed_bank, registry_names)
    counts = validate_counts(candidates, registry_names)
    tasks = [
        {"task_id": row["task_id"], "prompt": row["prompt"]}
        for row in candidates
    ]
    option_balance = attach_label_independent_option_maps(tasks, registry_names)
    option_balance["correct_answer_positions"] = correct_answer_position_diagnostics(
        tasks, candidates
    )
    freshness = validate_freshness(candidates, read_jsonl(prior_tasks_path))
    validate_no_catalog_copy(candidates, descriptions)
    answer_mention_check = validate_no_canonical_answer_mentions(candidates)
    lexical_leakage = evaluate_shallow_lexical_leakage(candidates)
    repeated_phrase_rule = evaluate_repeated_phrase_rule(candidates)

    candidate_answers = [
        {
            "task_id": row["task_id"],
            "task_type": row["task_type"],
            "expected_skill": row["expected_skill"],
            "presented_nonexistent_name": row["presented_nonexistent_name"],
            "seed_fingerprint": row["seed_fingerprint"],
            "label_audit_status": PENDING_LABEL_STATUS,
        }
        for row in candidates
    ]
    if any(set(row) != TASK_FIELDS for row in tasks):
        raise AssertionError("collection-facing task schema leaked labels")
    if any(set(row) != ANSWER_FIELDS for row in candidate_answers):
        raise AssertionError("answer-key schema drift")

    candidate_tasks_raw = canonical_jsonl_bytes(tasks)
    candidate_answers_raw = canonical_jsonl_bytes(candidate_answers)
    candidate_catalog_raw = canonical_json_bytes(catalog)
    if governance["completed_independent_label_audits"] == 2:
        if candidate_checkpoint_manifest_raw_override is None:
            checkpoint_manifest_path = root / DEFAULT_OUTPUT_DIR / "benchmark_manifest.json"
            try:
                candidate_checkpoint_manifest_raw = checkpoint_manifest_path.read_bytes()
            except OSError as exc:
                raise ValueError(
                    "completed build requires the pending checkpoint benchmark manifest"
                ) from exc
        else:
            candidate_checkpoint_manifest_raw = bytes(
                candidate_checkpoint_manifest_raw_override
            )
        audit_bindings = validate_completed_audit_evidence(
            root=root,
            governance=governance,
            candidate_tasks_raw=candidate_tasks_raw,
            candidate_answers_raw=candidate_answers_raw,
            candidate_catalog_raw=candidate_catalog_raw,
            candidate_manifest_raw=candidate_checkpoint_manifest_raw,
            evidence_overrides=evidence_overrides,
            pair_verifier=pair_verifier,
        )
        answers = [
            {**row, "label_audit_status": AUDITED_LABEL_STATUS}
            for row in candidate_answers
        ]
        benchmark_status = "AUDITED_CONFIRMATORY_INPUTS_READY_TO_FREEZE"
    else:
        audit_bindings = {
            "mode": "PENDING",
            "completed_independent_label_audits": 0,
            "required_independent_label_audits": 2,
            "release_status": PENDING_RELEASE_STATUS,
            "final_resolution": {
                "path": governance["audit_resolution"],
                "status": "PENDING",
                "sha256_embedded_in_frozen_inputs": False,
            },
        }
        answers = candidate_answers
        benchmark_status = "PROSPECTIVE_INPUTS_AWAITING_LABEL_AUDITS"

    files = {
        "tasks.jsonl": candidate_tasks_raw,
        "answer_key.jsonl": canonical_jsonl_bytes(answers),
        "registry_catalog.json": candidate_catalog_raw,
    }
    manifest = {
        "schema_version": "px062-gate2.2-frozen-input-manifest-v2",
        "experiment_stage": "PX-062 Gate 2.2",
        "benchmark_status": benchmark_status,
        "collection_blinding": {
            "tasks_file_contains_labels": False,
            "answer_key_must_be_excluded_from_model_collection_bundle": True,
        },
        "counts": counts,
        "option_map_balance": option_balance,
        "deterministic_ordering": (
            "ascending SHA256('62022:' + collection-visible prompt fingerprint)"
        ),
        "collection_task_identity": {
            "namespace": TASK_ID_NAMESPACE,
            "inputs": ["namespace", "full_prompt"],
            "private_answer_fields_used": [],
            "label_independent": True,
        },
        "freshness_against_gate2_1": {
            **freshness,
            "prior_tasks_path": prior_tasks_path.relative_to(root).as_posix(),
            "prior_tasks_sha256": sha256_file(prior_tasks_path),
        },
        "label_governance": governance,
        "audit_bindings": audit_bindings,
        "source_files": {
            "seed_bank": {
                "path": seed_bank_path.relative_to(root).as_posix(),
                "sha256": sha256_bytes(seed_bank_raw),
            },
            "registry_inventory": {
                "path": registry_path.relative_to(root).as_posix(),
                "sha256": sha256_file(registry_path),
            },
        },
        "artifacts": {
            name: {"bytes": len(raw), "sha256": sha256_bytes(raw)}
            for name, raw in files.items()
        },
        "catalog_copy_check": {
            "full_description_overlap": 0,
            "shared_contiguous_catalog_words_at_width_12": 0,
        },
        "canonical_answer_mention_check": answer_mention_check,
        "anti_lexical_leakage": {
            "prospectively_frozen_before_model_collection": True,
            "shallow_grouped_classifier": lexical_leakage,
            "repeated_phrase_rule": repeated_phrase_rule,
        },
    }
    files["benchmark_manifest.json"] = canonical_json_bytes(manifest)
    return files


def write_artifacts(output_dir: Path, files: dict[str, bytes]) -> None:
    if output_dir.exists():
        raise FileExistsError(f"frozen output already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".px062-g22-inputs-", dir=output_dir.parent))
    try:
        for name, raw in files.items():
            with (stage / name).open("xb") as handle:
                handle.write(raw)
        stage.rename(output_dir)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-bank", type=Path, default=DEFAULT_SEED_BANK)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_INVENTORY)
    parser.add_argument("--prior-tasks", type=Path, default=DEFAULT_PRIOR_TASKS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    seed_bank_path = resolved(ROOT, args.seed_bank)
    registry_path = resolved(ROOT, args.registry)
    prior_tasks_path = resolved(ROOT, args.prior_tasks)
    output_dir = resolved(ROOT, args.output_dir)
    files = build_artifacts(
        root=ROOT,
        seed_bank_path=seed_bank_path,
        registry_path=registry_path,
        prior_tasks_path=prior_tasks_path,
    )
    if not args.check_only:
        write_artifacts(output_dir, files)
    print(
        json.dumps(
            {
                "check_only": args.check_only,
                "files": {
                    name: {"bytes": len(raw), "sha256": sha256_bytes(raw)}
                    for name, raw in sorted(files.items())
                },
                "output_dir": output_dir.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
