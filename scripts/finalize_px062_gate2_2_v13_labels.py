#!/usr/bin/env python
"""Finalize PX-062 Gate 2.2 v1.3 balanced four-pass label governance.

Check-only is the default. ``--apply`` is valid only after all four full audit
slots and their sealed evidence manifest exist and every row satisfies the
prospectively frozen balanced 3-of-4 rule.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import build_px062_gate2_2_v13_benchmark as builder
    from scripts import finalize_px062_gate2_2_v11_labels as core
    from scripts import run_px062_gate2_2_v13_blind_audit as audit_runner
    from scripts.verify_px062_gate2_2_v13_label_audits import verify
except ImportError:  # Direct ``python scripts/...`` execution.
    import build_px062_gate2_2_v13_benchmark as builder  # type: ignore[no-redef]
    import finalize_px062_gate2_2_v11_labels as core  # type: ignore[no-redef]
    import run_px062_gate2_2_v13_blind_audit as audit_runner  # type: ignore[no-redef]
    from verify_px062_gate2_2_v13_label_audits import verify  # type: ignore[no-redef]


ROOT = builder.ROOT
DEFAULT_SEED_BANK = builder.DEFAULT_SEED_BANK
DEFAULT_REGISTRY_INVENTORY = builder.DEFAULT_REGISTRY_INVENTORY
DEFAULT_PRIOR_TASKS = builder.DEFAULT_PRIOR_TASKS
DEFAULT_CANDIDATE_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/frozen_inputs"
)
DEFAULT_PROVISIONAL_RESOLUTION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/label_audit_provisional_resolution.json"
)
DEFAULT_FINAL_RESOLUTION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728/label_audit_resolution.json"
)
FROZEN_NAMES = core.FROZEN_NAMES
CORE_DEPENDENCIES = (
    "scripts/finalize_px062_gate2_2_v11_labels.py",
    "scripts/build_px062_gate2_2_v13_benchmark.py",
    "scripts/build_px062_gate2_2_benchmark.py",
    "scripts/build_px062_gate2_2_v11_benchmark.py",
    "scripts/verify_px062_gate2_2_v13_label_audits.py",
    "scripts/verify_px062_gate2_2_v11_label_audits.py",
    "scripts/run_px062_gate2_2_v13_blind_audit.py",
    "scripts/run_px062_gate2_2_blind_audit.py",
    "scripts/run_px062_gate2_2_v11_blind_audit.py",
)

pretty_json_bytes = core.pretty_json_bytes
sha256_file = core.sha256_file
resolve = core.resolve
logical_path = core.logical_path
evidence_bytes = core.evidence_bytes
_CORE_PREPARE = core.prepare_finalization
_CORE_PLAN_SUMMARY = core.plan_summary
_assert_candidate_matches = core._assert_candidate_matches
_atomic_replace = core._atomic_replace


def validate_consensus_for_finalization(
    *,
    root: Path,
    candidate_files: dict[str, bytes],
    evidence_overrides: dict[str, bytes] | None,
    pair_verifier: builder.PairVerifier | None,
) -> tuple[dict[str, Any], bytes]:
    path = builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    raw = evidence_bytes(root, path, evidence_overrides)
    manifest = builder.read_json_bytes(raw, path)
    audits = manifest.get("audits")
    if not isinstance(audits, list) or len(audits) != 4:
        raise ValueError("canonical audit consensus manifest must contain four slots")
    bootstrap: dict[str, Any] = {
        "audit_consensus_manifest_path": path,
        "audit_consensus_manifest_sha256": builder.sha256_bytes(raw),
    }
    for slot, audit in enumerate(audits, 1):
        if not isinstance(audit, dict):
            raise ValueError(f"canonical audit slot {slot} is invalid")
        bootstrap[f"audit_{slot}_predictions_sha256"] = audit.get("prediction_sha256")
        bootstrap[f"audit_{slot}_sidecar_sha256"] = audit.get("sidecar_sha256")
    consensus = builder.validate_canonical_consensus_evidence(
        root=root,
        governance=bootstrap,
        candidate_tasks_raw=candidate_files["tasks.jsonl"],
        candidate_answers_raw=candidate_files["answer_key.jsonl"],
        candidate_catalog_raw=candidate_files["registry_catalog.json"],
        candidate_manifest_raw=candidate_files["benchmark_manifest.json"],
        evidence_overrides=evidence_overrides,
        pair_verifier=pair_verifier,
    )
    return consensus, raw


def _audit_binding(
    summary: dict[str, Any],
    path: str,
    consensus_audit: dict[str, Any],
    sidecar_path: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": summary["sha256"],
        "rows": summary["rows"],
        "agreement_with_answer_key": summary["agreement_with_answer_key"],
        "disagreement_task_ids": summary["disagreement_task_ids"],
        "confidence_counts": summary["confidence_counts"],
        "slot": consensus_audit["slot"],
        "model": consensus_audit["model"],
        "sidecar_path": sidecar_path,
        "sidecar_sha256": consensus_audit["sidecar_sha256"],
        "accepted_session_ids": copy.deepcopy(consensus_audit["accepted_session_ids"]),
    }


def build_provisional_resolution(
    *,
    verification: dict[str, Any],
    candidate_tasks_path: str,
    candidate_answer_path: str,
    audit_paths: list[str],
    canonical_pair: dict[str, Any],
) -> dict[str, Any]:
    if verification.get("all_labels_balanced_consensus_accepted") is not True:
        raise ValueError("cannot finalize without balanced consensus on every row")
    if verification.get("rejected_task_ids") != []:
        raise ValueError("cannot finalize with rejected consensus rows")
    return {
        "schema_version": "px062-gate2.2-v1.3-label-audit-provisional-v1",
        "status": builder.PROVISIONAL_RESOLUTION_STATUS,
        "candidate_tasks": {**verification["tasks"], "path": candidate_tasks_path},
        "candidate_answer_key": {
            **verification["answer_key"],
            "path": candidate_answer_path,
        },
        "policy": copy.deepcopy(verification["policy"]),
        "audits": [
            _audit_binding(summary, path, audit, sidecar)
            for summary, path, audit, sidecar in zip(
                verification["audits"],
                audit_paths,
                canonical_pair["audits"],
                builder.CANONICAL_AUDIT_SIDECAR_PATHS,
                strict=True,
            )
        ],
        "canonical_consensus_manifest": copy.deepcopy(canonical_pair),
        "unanimous_key_rows": verification["unanimous_key_rows"],
        "single_dissent_task_ids": verification["single_dissent_task_ids"],
        "rejected_task_ids": [],
        "all_labels_balanced_consensus_accepted": True,
    }


def completed_governance(
    *,
    pending_governance: dict[str, Any],
    provisional: dict[str, Any],
    provisional_path: str,
    provisional_raw: bytes,
    final_resolution_path: str,
    canonical_pair: dict[str, Any],
) -> dict[str, Any]:
    governance: dict[str, Any] = {
        "scenario_origin": pending_governance["scenario_origin"],
        "required_independent_label_audits": 4,
        "completed_independent_label_audits": 4,
        "release_status": builder.COMPLETED_RELEASE_STATUS,
        "audit_resolution_status": "PROVISIONAL_BALANCED_CONSENSUS_VERIFIED",
        "audit_consensus_manifest_path": canonical_pair["path"],
        "audit_consensus_manifest_sha256": canonical_pair["sha256"],
        "candidate_tasks_sha256": provisional["candidate_tasks"]["sha256"],
        "candidate_answer_key_sha256": provisional["candidate_answer_key"]["sha256"],
        "provisional_resolution_path": provisional_path,
        "provisional_resolution_sha256": builder.sha256_bytes(provisional_raw),
        "provisional_resolution_status": builder.PROVISIONAL_RESOLUTION_STATUS,
        "final_resolution_path": final_resolution_path,
        "final_resolution_status": builder.FINAL_RESOLUTION_STATUS,
        "audit_requirement": pending_governance["audit_requirement"],
        "consensus_policy": copy.deepcopy(pending_governance["consensus_policy"]),
    }
    for slot, audit in enumerate(provisional["audits"], 1):
        governance[f"audit_{slot}_status"] = "BALANCED_CONSENSUS_VERIFIED"
        governance[f"audit_{slot}_predictions_path"] = audit["path"]
        governance[f"audit_{slot}_predictions_sha256"] = audit["sha256"]
        governance[f"audit_{slot}_sidecar_path"] = audit["sidecar_path"]
        governance[f"audit_{slot}_sidecar_sha256"] = audit["sidecar_sha256"]
    return governance


def build_final_resolution(
    *,
    final_verification: dict[str, Any],
    completed_files: dict[str, bytes],
    provisional_path: str,
    provisional_raw: bytes,
    audit_paths: list[str],
    canonical_pair: dict[str, Any],
) -> dict[str, Any]:
    if final_verification.get("all_labels_balanced_consensus_accepted") is not True:
        raise ValueError("final regenerated answer key failed balanced-consensus reverification")
    return {
        "schema_version": "px062-gate2.2-v1.3-label-audit-final-resolution-v1",
        "status": "BALANCED_CONSENSUS_REVERIFIED_AGAINST_AUDITED_FINAL_ANSWER",
        "provisional_resolution": {
            "path": provisional_path,
            "sha256": builder.sha256_bytes(provisional_raw),
            "status": builder.PROVISIONAL_RESOLUTION_STATUS,
        },
        "final_inputs": {
            name: {
                "sha256": builder.sha256_bytes(completed_files[name]),
                "bytes": len(completed_files[name]),
            }
            for name in FROZEN_NAMES
        },
        "answer_label_status": builder.AUDITED_LABEL_STATUS,
        "audits": [
            _audit_binding(summary, path, audit, sidecar)
            for summary, path, audit, sidecar in zip(
                final_verification["audits"],
                audit_paths,
                canonical_pair["audits"],
                builder.CANONICAL_AUDIT_SIDECAR_PATHS,
                strict=True,
            )
        ],
        "canonical_consensus_manifest": copy.deepcopy(canonical_pair),
        "single_dissent_task_ids": final_verification["single_dissent_task_ids"],
        "rejected_task_ids": [],
        "all_labels_balanced_consensus_accepted": True,
        "hash_cycle_boundary": (
            "This final-resolution hash is intentionally not embedded in the "
            "seed bank or benchmark manifest."
        ),
    }


def _verify_raw_evidence(
    *,
    tasks_raw: bytes,
    answer_raw: bytes,
    catalog_raw: bytes,
    audit_raws: list[bytes],
) -> dict[str, Any]:
    if len(audit_raws) != 4:
        raise ValueError("exactly four fixed-slot audit payloads are required")
    with tempfile.TemporaryDirectory(prefix="px062-g22-v13-staged-verify-") as temporary:
        directory = Path(temporary)
        tasks_path = directory / "tasks.jsonl"
        answer_path = directory / "answer_key.jsonl"
        catalog_path = directory / "registry_catalog.json"
        audit_paths = [directory / f"audit_{slot}.jsonl" for slot in (1, 2, 3, 4)]
        tasks_path.write_bytes(tasks_raw)
        answer_path.write_bytes(answer_raw)
        catalog_path.write_bytes(catalog_raw)
        for path, raw in zip(audit_paths, audit_raws, strict=True):
            path.write_bytes(raw)
        return verify(tasks_path, answer_path, audit_paths, catalog_path)


_CORE_BINDINGS: dict[str, Any] = {
    "AUDITED_LABEL_STATUS": builder.AUDITED_LABEL_STATUS,
    "CANONICAL_AUDIT_MODELS": builder.CANONICAL_AUDIT_MODELS,
    "CANONICAL_AUDIT_PAIR_MANIFEST_PATH": builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH,
    "CANONICAL_AUDIT_PATHS": builder.CANONICAL_AUDIT_PATHS,
    "CANONICAL_AUDIT_SIDECAR_PATHS": builder.CANONICAL_AUDIT_SIDECAR_PATHS,
    "COMPLETED_RELEASE_STATUS": builder.COMPLETED_RELEASE_STATUS,
    "DEFAULT_PRIOR_TASKS": DEFAULT_PRIOR_TASKS,
    "DEFAULT_REGISTRY_INVENTORY": DEFAULT_REGISTRY_INVENTORY,
    "DEFAULT_SEED_BANK": DEFAULT_SEED_BANK,
    "FINAL_RESOLUTION_STATUS": builder.FINAL_RESOLUTION_STATUS,
    "PROVISIONAL_RESOLUTION_STATUS": builder.PROVISIONAL_RESOLUTION_STATUS,
    "ROOT": ROOT,
    "PairVerifier": builder.PairVerifier,
    "build_artifacts": builder.build_artifacts,
    "read_json": builder.read_json,
    "read_json_bytes": builder.read_json_bytes,
    "read_jsonl_bytes": builder.read_jsonl_bytes,
    "sha256_bytes": builder.sha256_bytes,
    "validate_label_governance": builder.validate_label_governance,
    "validate_pair_for_finalization": validate_consensus_for_finalization,
    "build_provisional_resolution": build_provisional_resolution,
    "completed_governance": completed_governance,
    "build_final_resolution": build_final_resolution,
    "_verify_raw_evidence": _verify_raw_evidence,
    "DEFAULT_CANDIDATE_DIR": DEFAULT_CANDIDATE_DIR,
    "DEFAULT_PROVISIONAL_RESOLUTION": DEFAULT_PROVISIONAL_RESOLUTION,
    "DEFAULT_FINAL_RESOLUTION": DEFAULT_FINAL_RESOLUTION,
}


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    previous = {name: getattr(core, name) for name in _CORE_BINDINGS}
    try:
        for name, value in _CORE_BINDINGS.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def _authenticate_planning_controls(kwargs: dict[str, Any]) -> None:
    """Authenticate live controls whenever canonical/overridden evidence exists."""

    root = Path(os.path.abspath(kwargs["root"]))
    logical = builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    overrides = kwargs.get("evidence_overrides")
    raw: bytes | None = None
    if isinstance(overrides, dict) and logical in overrides:
        raw = overrides[logical]
    else:
        path = audit_runner._safe_root_relative_path(
            root, logical, "finalization consensus manifest"
        )
        if path.is_file():
            audit_runner._require_unaliased_regular_file(
                path, "finalization consensus manifest"
            )
            raw = path.read_bytes()
    if raw is None:
        # Preserve the qualified core's canonical missing-evidence diagnostic.
        return
    manifest = builder.read_json_bytes(raw, logical)
    checkpoint = manifest.get("repository_checkpoint")
    if not isinstance(checkpoint, dict):
        raise ValueError("consensus manifest lacks a historical repository checkpoint")
    try:
        audit_runner.authenticate_historical_repository_checkpoint(root, checkpoint)
    except Exception as exc:
        raise ValueError(
            "current governance controls differ during finalization planning"
        ) from exc


def prepare_finalization(**kwargs: Any) -> dict[str, Any]:
    _authenticate_planning_controls(kwargs)
    with _bound_core():
        plan = _CORE_PREPARE(**kwargs)
    _authenticate_planning_controls(kwargs)
    return plan


def _reauthenticate_complete_manifest_inventory(plan: dict[str, Any]) -> None:
    """Reconstruct and re-read the entire raw inventory before any write."""

    logical = builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    manifest_path = audit_runner._safe_root_relative_path(
        plan["root"], logical, "finalization consensus manifest"
    )
    audit_runner._require_unaliased_regular_file(
        manifest_path, "finalization consensus manifest"
    )
    expected_hash = plan["sealed_evidence_hashes"].get(logical)
    if not manifest_path.is_file() or sha256_file(manifest_path) != expected_hash:
        raise ValueError("canonical consensus manifest changed before finalization")
    observed = builder.read_json_bytes(manifest_path.read_bytes(), logical)
    try:
        reconstructed = builder._historical_consensus_verifier(
            plan["root"], write_manifest=False
        )
    except Exception as exc:
        raise ValueError(
            "complete consensus-manifest artifact reconstruction failed before write"
        ) from exc
    if reconstructed != observed:
        raise ValueError("reconstructed consensus manifest differs before write")
    try:
        audit_runner.reauthenticate_manifest_artifact_inventory(
            plan["root"], observed
        )
    except Exception as exc:
        raise ValueError(
            "raw consensus-manifest artifact changed before finalization write"
        ) from exc
    checkpoint = observed.get("repository_checkpoint")
    if not isinstance(checkpoint, dict):
        raise ValueError("consensus manifest lacks a historical repository checkpoint")
    try:
        audit_runner.authenticate_historical_repository_checkpoint(
            plan["root"], checkpoint
        )
    except Exception as exc:
        raise ValueError(
            "current governance controls differ before finalization write"
        ) from exc


def apply_finalization(plan: dict[str, Any]) -> None:
    """Fail before the first write, including a complete raw-inventory reread."""

    seed_path: Path = plan["seed_bank_path"]
    candidate_dir: Path = plan["candidate_dir"]
    provisional_path: Path = plan["provisional_resolution_path"]
    final_path: Path = plan["final_resolution_path"]
    if sha256_file(seed_path) != plan["candidate_seed_sha256"]:
        raise ValueError("seed bank changed after finalization plan was prepared")
    _assert_candidate_matches(candidate_dir, plan["candidate_files"])
    for logical_evidence_path, expected_hash in plan["sealed_evidence_hashes"].items():
        evidence_path = audit_runner._safe_root_relative_path(
            plan["root"], logical_evidence_path, "canonical audit evidence"
        )
        audit_runner._require_unaliased_regular_file(
            evidence_path, "canonical audit evidence"
        )
        if sha256_file(evidence_path) != expected_hash:
            raise ValueError(
                "canonical audit evidence changed after finalization plan was prepared: "
                f"{logical_evidence_path}"
            )
    root = Path(os.path.abspath(plan["root"]))
    provisional_path = audit_runner._safe_root_relative_path(
        root,
        provisional_path.relative_to(root),
        "provisional-resolution output",
    )
    final_path = audit_runner._safe_root_relative_path(
        root, final_path.relative_to(root), "final-resolution output"
    )
    if provisional_path.exists() or final_path.exists():
        raise FileExistsError("refusing to overwrite existing label-resolution evidence")

    # This is intentionally the final read/check before the first atomic write.
    # It reconstructs the manifest and re-hashes every prompt/schema/event/log/
    # response/sidecar/prediction/input artifact, not only the stable top-level
    # evidence files stored in sealed_evidence_hashes.
    _reauthenticate_complete_manifest_inventory(plan)

    _atomic_replace(provisional_path, plan["provisional_resolution_raw"])
    _atomic_replace(seed_path, plan["completed_seed_raw"])
    for name in FROZEN_NAMES:
        _atomic_replace(candidate_dir / name, plan["completed_files"][name])
    _atomic_replace(final_path, plan["final_resolution_raw"])


def plan_summary(plan: dict[str, Any], applied: bool) -> dict[str, Any]:
    with _bound_core():
        summary = _CORE_PLAN_SUMMARY(plan, applied)
    summary["label_gate"] = "BALANCED_FOUR_PASS_3_OF_4_WITH_FAMILY_SUPPORT"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--seed-bank", type=Path, default=DEFAULT_SEED_BANK)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_INVENTORY)
    parser.add_argument("--prior-tasks", type=Path, default=DEFAULT_PRIOR_TASKS)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument(
        "--provisional-resolution",
        type=Path,
        default=DEFAULT_PROVISIONAL_RESOLUTION,
    )
    parser.add_argument("--final-resolution", type=Path, default=DEFAULT_FINAL_RESOLUTION)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the transition; without this flag the command is check-only",
    )
    args = parser.parse_args()
    plan = prepare_finalization(
        root=args.root,
        seed_bank_path=args.seed_bank,
        registry_path=args.registry,
        prior_tasks_path=args.prior_tasks,
        candidate_dir=args.candidate_dir,
        provisional_resolution_path=args.provisional_resolution,
        final_resolution_path=args.final_resolution,
    )
    if args.apply:
        apply_finalization(plan)
    print(json.dumps(plan_summary(plan, args.apply), indent=2))


if __name__ == "__main__":
    main()
