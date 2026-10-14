#!/usr/bin/env python
"""Build the versioned PX-062 Gate 2.2 v1.3 benchmark.

Version 1.3 keeps the sealed collection construction algorithm and registry
semantics, replaces only the nine rows rejected by the v1.2 label gate, and
uses a prospectively frozen balanced four-pass label-consensus policy.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

try:
    from scripts import build_px062_gate2_2_benchmark as base
except ImportError:  # Direct ``python scripts/...`` execution.
    import build_px062_gate2_2_benchmark as base  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_BANK = Path(
    "manifests/px062_gate2_2_v1_3_20260728/task_seed_bank.json"
)
DEFAULT_REGISTRY_INVENTORY = base.DEFAULT_REGISTRY_INVENTORY
DEFAULT_PRIOR_TASKS = base.DEFAULT_PRIOR_TASKS
DEFAULT_OUTPUT_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/frozen_inputs"
)
EXPERIMENT_STAGE = "PX-062 Gate 2.2 v1.3"
EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-3-20260728"
SOURCE_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-2-20260728"
SOURCE_CATALOG_SHA256 = (
    "90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212"
)
SOURCE_TASKS_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/frozen_inputs/tasks.jsonl"
)
SOURCE_TASKS_SHA256 = (
    "e9a4c387781b7299884d75ebbb59f3ba1dcd398599821fb586db95e02fabea16"
)
PRIVATE_SEED_FINGERPRINT_NAMESPACE = (
    "px062-gate2.2-v1.3-private-seed-fingerprint-v1"
)

PENDING_LABEL_STATUS = "PENDING_FOUR_PASS_BALANCED_CONSENSUS"
AUDITED_LABEL_STATUS = "ACCEPTED_FOUR_PASS_BALANCED_CONSENSUS"
PENDING_RELEASE_STATUS = base.PENDING_RELEASE_STATUS
COMPLETED_RELEASE_STATUS = base.COMPLETED_RELEASE_STATUS
PROVISIONAL_RESOLUTION_STATUS = (
    "BALANCED_3_OF_4_CONSENSUS_VERIFIED_AGAINST_PENDING_CANDIDATE"
)
FINAL_RESOLUTION_STATUS = base.FINAL_RESOLUTION_STATUS

CANONICAL_AUDIT_MODELS = (
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
)
AUDIT_SLOTS = (1, 2, 3, 4)
SOL_SLOTS = (1, 3)
TERRA_SLOTS = (2, 4)
GATE_EVIDENCE_DIR = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728"
)
CANONICAL_AUDIT_PATHS = tuple(
    f"{GATE_EVIDENCE_DIR}/label_audit_{slot}_predictions.jsonl"
    for slot in AUDIT_SLOTS
)
CANONICAL_AUDIT_SIDECAR_PATHS = tuple(
    f"{GATE_EVIDENCE_DIR}/label_audit_{slot}_run.json" for slot in AUDIT_SLOTS
)
CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH = (
    f"{GATE_EVIDENCE_DIR}/label_audit_evidence_manifest.json"
)
# Compatibility name used by the qualified finalization engine.
CANONICAL_AUDIT_PAIR_MANIFEST_PATH = CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH

CHECKPOINT_CONFIG_PATH = (
    "configs/px062_skill_selection_gate2_2_v1_3_20260728.json"
)
CHECKPOINT_RUNNER_PATH = "scripts/run_px062_gate2_2_v13_blind_audit.py"
CHECKPOINT_CORE_PATH = "scripts/run_px062_gate2_2_blind_audit.py"
CHECKPOINT_BUILDER_PATH = "scripts/build_px062_gate2_2_v13_benchmark.py"
CHECKPOINT_BASE_BUILDER_PATH = "scripts/build_px062_gate2_2_benchmark.py"
CHECKPOINT_V11_BUILDER_PATH = "scripts/build_px062_gate2_2_v11_benchmark.py"
CHECKPOINT_V11_RUNNER_PATH = "scripts/run_px062_gate2_2_v11_blind_audit.py"
CHECKPOINT_VERIFIER_PATH = "scripts/verify_px062_gate2_2_v13_label_audits.py"
CHECKPOINT_V11_VERIFIER_PATH = "scripts/verify_px062_gate2_2_v11_label_audits.py"
CHECKPOINT_FINALIZER_PATH = "scripts/finalize_px062_gate2_2_v13_labels.py"
CHECKPOINT_V11_FINALIZER_PATH = "scripts/finalize_px062_gate2_2_v11_labels.py"
CHECKPOINT_PROTOCOL_PATH = (
    f"{GATE_EVIDENCE_DIR}/LABEL_AUDIT_PROTOCOL_V1_3_20260728.md"
)
CHECKPOINT_TESTS_PATH = "tests/test_px062_gate2_2_v13_blind_audit.py"
PRIOR_AUDIT_BLACKLIST_MANIFEST_PATH = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/"
    "label_audit_evidence_manifest.json"
)
CHECKPOINT_TRACKED_PATHS = (
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/tasks.jsonl",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/registry_catalog.json",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/answer_key.jsonl",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/benchmark_manifest.json",
    DEFAULT_SEED_BANK.as_posix(),
    CHECKPOINT_CONFIG_PATH,
    CHECKPOINT_RUNNER_PATH,
    CHECKPOINT_CORE_PATH,
    CHECKPOINT_BUILDER_PATH,
    CHECKPOINT_BASE_BUILDER_PATH,
    CHECKPOINT_V11_BUILDER_PATH,
    CHECKPOINT_V11_RUNNER_PATH,
    CHECKPOINT_VERIFIER_PATH,
    CHECKPOINT_V11_VERIFIER_PATH,
    CHECKPOINT_FINALIZER_PATH,
    CHECKPOINT_V11_FINALIZER_PATH,
    CHECKPOINT_PROTOCOL_PATH,
    CHECKPOINT_TESTS_PATH,
    PRIOR_AUDIT_BLACKLIST_MANIFEST_PATH,
)
PairVerifier = Callable[..., dict[str, Any]]


def _retained_task_projection(root: Path, new_tasks_raw: bytes) -> dict[str, Any]:
    """Recompute the retained-row disclosure embedded in the benchmark seal."""

    source_raw = (root / SOURCE_TASKS_PATH).read_bytes()
    if sha256_bytes(source_raw) != SOURCE_TASKS_SHA256:
        raise ValueError("v1.2 source tasks changed before projection reconstruction")
    source_rows = {row["task_id"]: row for row in base.read_jsonl_bytes(source_raw, "v1.2 tasks")}
    new_rows = {row["task_id"]: row for row in base.read_jsonl_bytes(new_tasks_raw, "v1.3 tasks")}
    retained = sorted(set(source_rows).intersection(new_rows))
    unchanged_prompts = sum(
        source_rows[task_id]["prompt"] == new_rows[task_id]["prompt"]
        for task_id in retained
    )
    identical_rows = sum(source_rows[task_id] == new_rows[task_id] for task_id in retained)
    rotations: Counter[int] = Counter()
    for task_id in retained:
        old_map = [entry["skill"] for entry in source_rows[task_id]["option_map"]]
        new_map = [entry["skill"] for entry in new_rows[task_id]["option_map"]]
        if old_map == new_map:
            continue
        offsets = [
            offset
            for offset in range(len(old_map))
            if new_map == old_map[offset:] + old_map[:offset]
        ]
        if len(offsets) != 1:
            raise ValueError("retained option-map change is not one pure rotation")
        rotations[offsets[0]] += 1
    if (
        len(retained) != 1023
        or unchanged_prompts != 1023
        or identical_rows != 433
        or rotations != Counter({1: 327, 2: 249, 3: 14})
    ):
        raise ValueError("v1.3 retained-task projection drift")
    return {
        "prompt_ids_and_prompt_text_unchanged": len(retained),
        "full_task_rows_byte_identical": identical_rows,
        "option_map_rotations": sum(rotations.values()),
        "reason": (
            "Label-independent option maps are assigned from corpus-wide "
            "sorted prompt rank; replacing nine prompts moves retained ranks."
        ),
        "construction_algorithm_changed": False,
    }


def _valid_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"invalid SHA-256 binding: {label}")
    return value


def validate_label_governance(seed_bank: dict[str, Any]) -> dict[str, Any]:
    """Validate the v1.3 four-pass pending or completed governance schema."""

    governance = seed_bank.get("label_governance")
    if not isinstance(governance, dict):
        raise ValueError("seed bank requires label_governance")
    if governance.get("scenario_origin") != "model-authored-and-curated":
        raise ValueError("scenario origin must disclose model authorship and curation")
    if governance.get("required_independent_label_audits") != 4:
        raise ValueError("v1.3 requires exactly four independent full audit passes")
    common = {
        "scenario_origin",
        "required_independent_label_audits",
        "completed_independent_label_audits",
        "release_status",
        "audit_1_status",
        "audit_2_status",
        "audit_3_status",
        "audit_4_status",
        "audit_resolution_status",
        "audit_requirement",
        "consensus_policy",
    }
    completed = governance.get("completed_independent_label_audits")
    if completed == 0:
        if set(governance) != {*common, "audit_resolution"}:
            raise ValueError("pending v1.3 label-governance schema drift")
        if governance.get("release_status") != PENDING_RELEASE_STATUS:
            raise ValueError("unexpected pending label release status")
        if any(governance.get(f"audit_{slot}_status") != "PENDING" for slot in AUDIT_SLOTS):
            raise ValueError("all four v1.3 audits must be pending")
        if governance.get("audit_resolution_status") != "PENDING":
            raise ValueError("audit resolution must be pending")
    elif completed == 4:
        evidence_fields = {
            field
            for slot in AUDIT_SLOTS
            for field in (
                f"audit_{slot}_predictions_path",
                f"audit_{slot}_predictions_sha256",
                f"audit_{slot}_sidecar_path",
                f"audit_{slot}_sidecar_sha256",
            )
        }
        expected = {
            *common,
            *evidence_fields,
            "audit_consensus_manifest_path",
            "audit_consensus_manifest_sha256",
            "candidate_tasks_sha256",
            "candidate_answer_key_sha256",
            "provisional_resolution_path",
            "provisional_resolution_sha256",
            "provisional_resolution_status",
            "final_resolution_path",
            "final_resolution_status",
        }
        if set(governance) != expected:
            raise ValueError("completed v1.3 label-governance schema drift")
        if governance.get("release_status") != COMPLETED_RELEASE_STATUS:
            raise ValueError("unexpected completed label release status")
        if any(
            governance.get(f"audit_{slot}_status") != "BALANCED_CONSENSUS_VERIFIED"
            for slot in AUDIT_SLOTS
        ):
            raise ValueError("completed audits are not consensus verified")
        if governance.get("audit_resolution_status") != "PROVISIONAL_BALANCED_CONSENSUS_VERIFIED":
            raise ValueError("completed governance lacks provisional consensus")
        if governance.get("provisional_resolution_status") != PROVISIONAL_RESOLUTION_STATUS:
            raise ValueError("unexpected provisional resolution status")
        if governance.get("final_resolution_status") != FINAL_RESOLUTION_STATUS:
            raise ValueError("final resolution must remain external")
        for slot in AUDIT_SLOTS:
            if governance[f"audit_{slot}_predictions_path"] != CANONICAL_AUDIT_PATHS[slot - 1]:
                raise ValueError(f"audit {slot} prediction path is not canonical")
            if governance[f"audit_{slot}_sidecar_path"] != CANONICAL_AUDIT_SIDECAR_PATHS[slot - 1]:
                raise ValueError(f"audit {slot} sidecar path is not canonical")
            _valid_sha256(
                governance[f"audit_{slot}_predictions_sha256"],
                f"audit_{slot}_predictions_sha256",
            )
            _valid_sha256(
                governance[f"audit_{slot}_sidecar_sha256"],
                f"audit_{slot}_sidecar_sha256",
            )
        if governance["audit_consensus_manifest_path"] != CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH:
            raise ValueError("consensus manifest path is not canonical")
        for field in (
            "audit_consensus_manifest_sha256",
            "candidate_tasks_sha256",
            "candidate_answer_key_sha256",
            "provisional_resolution_sha256",
        ):
            _valid_sha256(governance[field], field)
    else:
        raise ValueError("completed independent label audits must be exactly 0 or 4")

    policy = governance.get("consensus_policy")
    expected_policy = {
        "slots": 4,
        "sol_slots": [1, 3],
        "terra_slots": [2, 4],
        "minimum_key_votes": 3,
        "require_key_support_from_each_model_family": True,
        "single_dissent_tolerated": True,
        "semantic_retry_permitted": False,
        "disputed_only_rerun_permitted": False,
        "same_version_prompt_edit_or_relabel_permitted": False,
    }
    if policy != expected_policy:
        raise ValueError("v1.3 balanced-consensus policy drift")
    return governance


def _v13_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(catalog)
    value["benchmark_identity"] = {
        "experiment_id": EXPERIMENT_ID,
        "revision": "v1.3",
        "source_catalog_sha256": SOURCE_CATALOG_SHA256,
        "registry_semantics_changed": False,
    }
    return value


def _v13_answer_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    migrated: list[dict[str, Any]] = []
    for source in rows:
        row = copy.deepcopy(source)
        identity = {
            "namespace": PRIVATE_SEED_FINGERPRINT_NAMESPACE,
            "source_seed_fingerprint": row["seed_fingerprint"],
        }
        row["seed_fingerprint"] = hashlib.sha256(
            base.canonical_json_bytes(identity)
        ).hexdigest()
        migrated.append(row)
    return migrated


def _historical_consensus_verifier(
    root: Path, *, write_manifest: bool
) -> dict[str, Any]:
    if write_manifest:
        raise ValueError("builder evidence validation never writes the consensus manifest")
    try:
        from scripts import run_px062_gate2_2_v13_blind_audit as audit_runner
    except (ImportError, ModuleNotFoundError):
        # Required for ``python scripts/finalize_px062_gate2_2_v13_labels.py``:
        # direct script execution puts scripts/ rather than the repo root first.
        try:
            import run_px062_gate2_2_v13_blind_audit as audit_runner  # type: ignore[no-redef]
        except (ImportError, ModuleNotFoundError) as exc:
            raise ValueError("v1.3 audit runner is not yet frozen") from exc
    return audit_runner.verify_consensus(
        root,
        write_manifest=False,
        verification_mode="historical",
    )


def _evidence_bytes(
    root: Path, path_value: str, evidence_overrides: dict[str, bytes] | None
) -> bytes:
    if evidence_overrides and path_value in evidence_overrides:
        return evidence_overrides[path_value]
    try:
        return (root / path_value).read_bytes()
    except OSError as exc:
        raise ValueError(f"missing completed label-audit evidence: {path_value}") from exc


def validate_canonical_consensus_evidence(
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
    """Validate the sealed four-pass evidence and its pending checkpoint."""

    manifest_path = governance["audit_consensus_manifest_path"]
    manifest_raw = _evidence_bytes(root, manifest_path, evidence_overrides)
    if base.sha256_bytes(manifest_raw) != governance["audit_consensus_manifest_sha256"]:
        raise ValueError("canonical audit consensus-manifest hash mismatch")
    manifest = base.read_json_bytes(manifest_raw, manifest_path)
    required = {
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
    if set(manifest) != required:
        raise ValueError("canonical audit consensus-manifest schema drift")
    if (
        manifest.get("schema_version")
        != "px062-gate2.2-v1.3-label-audit-evidence-manifest-v1"
        or manifest.get("answer_key_contents_included") is not False
        or manifest.get("pending_answer_checkpoint_hash_included") is not True
        or manifest.get("cross_audit_input_prompt_schema_hashes_match") is not True
    ):
        raise ValueError("canonical audit consensus-manifest policy drift")
    verifier = pair_verifier or _historical_consensus_verifier
    try:
        reconstructed = verifier(root.resolve(), write_manifest=False)
    except Exception as exc:
        raise ValueError("canonical blinded four-pass verification failed") from exc
    if not isinstance(reconstructed, dict):
        raise ValueError("canonical audit consensus verifier returned invalid evidence")
    normalized = copy.deepcopy(reconstructed)
    normalized["created_utc"] = manifest["created_utc"]
    if normalized != manifest:
        raise ValueError("canonical consensus manifest differs from reconstruction")

    checkpoint = manifest.get("repository_checkpoint")
    if not isinstance(checkpoint, dict):
        raise ValueError("repository checkpoint is missing")
    integrity = checkpoint.get("source_integrity")
    expected_integrity = {
        "tasks_sha256": base.sha256_bytes(candidate_tasks_raw),
        "answer_key_sha256": base.sha256_bytes(candidate_answers_raw),
        "registry_catalog_sha256": base.sha256_bytes(candidate_catalog_raw),
        "benchmark_manifest_sha256": base.sha256_bytes(candidate_manifest_raw),
    }
    if integrity != expected_integrity:
        raise ValueError("repository checkpoint source-integrity drift")
    if checkpoint.get("seed_governance", {}).get("required") != 4:
        raise ValueError("repository checkpoint is not pending four-pass governance")

    audits = manifest.get("audits")
    if not isinstance(audits, list) or len(audits) != 4:
        raise ValueError("canonical audit consensus manifest must contain four slots")
    accepted: set[str] = set()
    for slot, (audit, model) in enumerate(
        zip(audits, CANONICAL_AUDIT_MODELS, strict=True), 1
    ):
        if (
            not isinstance(audit, dict)
            or audit.get("slot") != slot
            or audit.get("model") != model
            or audit.get("prediction_sha256")
            != governance[f"audit_{slot}_predictions_sha256"]
            or audit.get("sidecar_sha256")
            != governance[f"audit_{slot}_sidecar_sha256"]
        ):
            raise ValueError(f"canonical audit slot {slot} binding drift")
        ids = audit.get("accepted_session_ids")
        if not isinstance(ids, list) or len(ids) != 43 or len(set(ids)) != 43:
            raise ValueError(f"canonical audit slot {slot} session provenance drift")
        if accepted.intersection(ids):
            raise ValueError("accepted session IDs overlap across audit slots")
        accepted.update(ids)
        for path, digest in (
            (CANONICAL_AUDIT_PATHS[slot - 1], audit["prediction_sha256"]),
            (CANONICAL_AUDIT_SIDECAR_PATHS[slot - 1], audit["sidecar_sha256"]),
        ):
            if base.sha256_bytes(_evidence_bytes(root, path, evidence_overrides)) != digest:
                raise ValueError(f"canonical audit slot {slot} artifact bytes drift")
    if len(accepted) != 172:
        raise ValueError("four-pass evidence requires 172 unique accepted sessions")
    return {
        "path": manifest_path,
        "sha256": governance["audit_consensus_manifest_sha256"],
        "schema_version": manifest["schema_version"],
        "audits": copy.deepcopy(audits),
        "global_session_ids": copy.deepcopy(manifest["global_session_ids"]),
        "isolated_workdirs": copy.deepcopy(manifest["isolated_workdirs"]),
        "repository_checkpoint": copy.deepcopy(checkpoint),
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
    """Revalidate four payloads and the 3-of-4 balanced consensus resolution."""

    if governance["completed_independent_label_audits"] != 4:
        raise ValueError("completed audit evidence requires four completed passes")
    if governance["candidate_tasks_sha256"] != base.sha256_bytes(candidate_tasks_raw):
        raise ValueError("completed governance candidate tasks hash mismatch")
    if governance["candidate_answer_key_sha256"] != base.sha256_bytes(candidate_answers_raw):
        raise ValueError("completed governance candidate answer-key hash mismatch")
    consensus = validate_canonical_consensus_evidence(
        root=root,
        governance=governance,
        candidate_tasks_raw=candidate_tasks_raw,
        candidate_answers_raw=candidate_answers_raw,
        candidate_catalog_raw=candidate_catalog_raw,
        candidate_manifest_raw=candidate_manifest_raw,
        evidence_overrides=evidence_overrides,
        pair_verifier=pair_verifier,
    )
    tasks = base.read_jsonl_bytes(candidate_tasks_raw, "candidate tasks")
    answers = base.read_jsonl_bytes(candidate_answers_raw, "candidate answer key")
    task_ids = [row["task_id"] for row in tasks]
    truth = {row["task_id"]: row["expected_skill"] for row in answers}
    catalog = base.read_json_bytes(candidate_catalog_raw, "candidate catalog")
    valid_skills = set(catalog["names"])
    rows_by_slot: dict[int, list[dict[str, Any]]] = {}
    bindings: list[dict[str, Any]] = []
    for slot in AUDIT_SLOTS:
        path = governance[f"audit_{slot}_predictions_path"]
        raw = _evidence_bytes(root, path, evidence_overrides)
        digest = base.sha256_bytes(raw)
        if digest != governance[f"audit_{slot}_predictions_sha256"]:
            raise ValueError(f"completed audit {slot} prediction hash mismatch")
        rows = base.read_jsonl_bytes(raw, path)
        if [row.get("task_id") for row in rows] != task_ids:
            raise ValueError(f"completed audit {slot} task order mismatch")
        confidence = Counter()
        disagreements: list[str] = []
        for row in rows:
            if set(row) != {"task_id", "predicted_skill", "confidence", "note"}:
                raise ValueError(f"completed audit {slot} schema drift")
            if row["predicted_skill"] is not None and row["predicted_skill"] not in valid_skills:
                raise ValueError(f"completed audit {slot} prediction outside catalog")
            if row["confidence"] not in {"high", "medium", "low"}:
                raise ValueError(f"completed audit {slot} confidence drift")
            if row["predicted_skill"] != truth[row["task_id"]]:
                disagreements.append(row["task_id"])
            confidence[row["confidence"]] += 1
        rows_by_slot[slot] = rows
        bindings.append(
            {
                "path": path,
                "sha256": digest,
                "rows": len(rows),
                "agreement_with_answer_key": len(rows) - len(disagreements),
                "disagreement_task_ids": disagreements,
                "confidence_counts": {
                    level: confidence[level] for level in ("high", "medium", "low")
                },
                "slot": slot,
                "model": CANONICAL_AUDIT_MODELS[slot - 1],
                "sidecar_path": governance[f"audit_{slot}_sidecar_path"],
                "sidecar_sha256": governance[f"audit_{slot}_sidecar_sha256"],
                "accepted_session_ids": consensus["audits"][slot - 1]["accepted_session_ids"],
            }
        )
    rejected: list[str] = []
    single_dissent: list[str] = []
    for index, task_id in enumerate(task_ids):
        expected = truth[task_id]
        matching = {
            slot for slot in AUDIT_SLOTS if rows_by_slot[slot][index]["predicted_skill"] == expected
        }
        accepted = (
            len(matching) >= 3
            and bool(matching.intersection(SOL_SLOTS))
            and bool(matching.intersection(TERRA_SLOTS))
        )
        if not accepted:
            rejected.append(task_id)
        elif len(matching) == 3:
            single_dissent.append(task_id)
    if rejected:
        raise ValueError(
            "four-pass audits do not satisfy balanced 3-of-4 consensus on every row"
        )
    provisional_path = governance["provisional_resolution_path"]
    provisional_raw = _evidence_bytes(root, provisional_path, evidence_overrides)
    if base.sha256_bytes(provisional_raw) != governance["provisional_resolution_sha256"]:
        raise ValueError("provisional balanced-consensus resolution hash mismatch")
    provisional = base.read_json_bytes(provisional_raw, provisional_path)
    if (
        provisional.get("status") != PROVISIONAL_RESOLUTION_STATUS
        or provisional.get("all_labels_balanced_consensus_accepted") is not True
        or provisional.get("rejected_task_ids") != []
        or provisional.get("single_dissent_task_ids") != single_dissent
        or provisional.get("audits") != bindings
        or provisional.get("canonical_consensus_manifest") != consensus
    ):
        raise ValueError("provisional balanced-consensus resolution drift")
    return {
        "mode": "COMPLETED",
        "candidate_tasks_sha256": base.sha256_bytes(candidate_tasks_raw),
        "candidate_answer_key_sha256": base.sha256_bytes(candidate_answers_raw),
        "audits": bindings,
        "canonical_consensus_manifest": consensus,
        "consensus": {
            "minimum_key_votes": 3,
            "family_support_required": True,
            "accepted_rows": len(task_ids),
            "single_dissent_task_ids": single_dissent,
            "rejected_task_ids": [],
        },
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


def _derive_build_artifacts() -> Any:
    source = inspect.getsource(base.build_artifacts)
    marker = "    if any(set(row) != TASK_FIELDS for row in tasks):\n"
    if source.count(marker) != 1:
        raise RuntimeError("sealed builder candidate-identity insertion point drift")
    source = source.replace(
        marker,
        "    catalog = _v13_catalog(catalog)\n"
        "    candidate_answers = _v13_answer_rows(candidate_answers)\n"
        + marker,
    )
    replacements = {
        'if governance["completed_independent_label_audits"] == 2:': (
            'if governance["completed_independent_label_audits"] == 4:'
        ),
        '"required_independent_label_audits": 2,': (
            '"required_independent_label_audits": 4,'
        ),
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise RuntimeError(f"sealed builder v1.3 migration point drift: {old}")
        source = source.replace(old, new)
    namespace = dict(base.__dict__)
    namespace.update(
        {
            "DEFAULT_SEED_BANK": DEFAULT_SEED_BANK,
            "DEFAULT_OUTPUT_DIR": DEFAULT_OUTPUT_DIR,
            "PENDING_LABEL_STATUS": PENDING_LABEL_STATUS,
            "AUDITED_LABEL_STATUS": AUDITED_LABEL_STATUS,
            "validate_label_governance": validate_label_governance,
            "validate_completed_audit_evidence": validate_completed_audit_evidence,
            "_v13_catalog": _v13_catalog,
            "_v13_answer_rows": _v13_answer_rows,
        }
    )
    exec(compile(source, __file__, "exec"), namespace)
    return namespace["build_artifacts"]


_BUILD_ARTIFACTS_V13 = _derive_build_artifacts()


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
    files = _BUILD_ARTIFACTS_V13(
        root=root,
        seed_bank_path=seed_bank_path,
        registry_path=registry_path,
        prior_tasks_path=prior_tasks_path,
        seed_bank_override=seed_bank_override,
        seed_bank_raw_override=seed_bank_raw_override,
        candidate_checkpoint_manifest_raw_override=candidate_checkpoint_manifest_raw_override,
        evidence_overrides=evidence_overrides,
        pair_verifier=pair_verifier or _historical_consensus_verifier,
    )
    manifest = json.loads(files["benchmark_manifest.json"])
    manifest["experiment_stage"] = EXPERIMENT_STAGE
    manifest["revision_lineage"] = {
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "retained_prompt_ids": 1023,
        "replaced_prompt_ids": 9,
        "private_seed_fingerprint_namespace": PRIVATE_SEED_FINGERPRINT_NAMESPACE,
        "registry_semantics_changed": False,
        "label_governance_redesigned": True,
        "label_governance_reason": "RETAINED_ROW_AUDITOR_STOCHASTICITY",
        "retained_task_projection": _retained_task_projection(
            root, files["tasks.jsonl"]
        ),
    }
    files["benchmark_manifest.json"] = base.canonical_json_bytes(manifest)
    return files


read_json = base.read_json
read_json_bytes = base.read_json_bytes
read_jsonl_bytes = base.read_jsonl_bytes
sha256_bytes = base.sha256_bytes
write_artifacts = base.write_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-bank", type=Path, default=DEFAULT_SEED_BANK)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_INVENTORY)
    parser.add_argument("--prior-tasks", type=Path, default=DEFAULT_PRIOR_TASKS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    resolved = lambda value: value if value.is_absolute() else ROOT / value
    output_dir = resolved(args.output_dir)
    files = build_artifacts(
        root=ROOT,
        seed_bank_path=resolved(args.seed_bank),
        registry_path=resolved(args.registry),
        prior_tasks_path=resolved(args.prior_tasks),
    )
    if not args.check_only:
        write_artifacts(output_dir, files)
    print(
        json.dumps(
            {
                "check_only": args.check_only,
                "experiment_stage": EXPERIMENT_STAGE,
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
