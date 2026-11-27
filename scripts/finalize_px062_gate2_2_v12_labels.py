#!/usr/bin/env python
"""Finalize PX-062 Gate 2.2 v1.2 label governance without a hash cycle.

The v1.1 finalization engine is reused only inside a scoped binding to the
v1.2 builder, verifier, evidence paths, and statuses.  Check-only remains the
default.  ``--apply`` is valid only after both fresh full audit slots and their
sealed pair manifest exist and unanimously support all 1,032 pending labels.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import build_px062_gate2_2_v12_benchmark as builder
    from scripts import finalize_px062_gate2_2_v11_labels as core
    from scripts.verify_px062_gate2_2_v12_label_audits import verify
except ImportError:  # Direct ``python scripts/...`` execution.
    import build_px062_gate2_2_v12_benchmark as builder  # type: ignore[no-redef]
    import finalize_px062_gate2_2_v11_labels as core  # type: ignore[no-redef]
    from verify_px062_gate2_2_v12_label_audits import verify  # type: ignore[no-redef]


ROOT = builder.ROOT
DEFAULT_SEED_BANK = builder.DEFAULT_SEED_BANK
DEFAULT_REGISTRY_INVENTORY = builder.DEFAULT_REGISTRY_INVENTORY
DEFAULT_PRIOR_TASKS = builder.DEFAULT_PRIOR_TASKS
DEFAULT_CANDIDATE_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/frozen_inputs"
)
DEFAULT_PROVISIONAL_RESOLUTION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/label_audit_provisional_resolution.json"
)
DEFAULT_FINAL_RESOLUTION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/label_audit_resolution.json"
)
FROZEN_NAMES = core.FROZEN_NAMES
CORE_DEPENDENCIES = (
    "scripts/finalize_px062_gate2_2_v11_labels.py",
    "scripts/build_px062_gate2_2_v12_benchmark.py",
    "scripts/verify_px062_gate2_2_v12_label_audits.py",
)

pretty_json_bytes = core.pretty_json_bytes
sha256_file = core.sha256_file
resolve = core.resolve
logical_path = core.logical_path
evidence_bytes = core.evidence_bytes

_CORE_VALIDATE_PAIR = core.validate_pair_for_finalization
_CORE_BUILD_PROVISIONAL = core.build_provisional_resolution
_CORE_COMPLETED_GOVERNANCE = core.completed_governance
_CORE_BUILD_FINAL = core.build_final_resolution
_CORE_PREPARE = core.prepare_finalization
_CORE_APPLY = core.apply_finalization
_CORE_PLAN_SUMMARY = core.plan_summary


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    bindings = {
        "AUDITED_LABEL_STATUS": builder.AUDITED_LABEL_STATUS,
        "CANONICAL_AUDIT_MODELS": builder.CANONICAL_AUDIT_MODELS,
        "CANONICAL_AUDIT_PAIR_MANIFEST_PATH": (
            builder.CANONICAL_AUDIT_PAIR_MANIFEST_PATH
        ),
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
        "validate_canonical_pair_evidence": (
            builder.validate_canonical_pair_evidence
        ),
        "validate_label_governance": builder.validate_label_governance,
        "verify": verify,
        "DEFAULT_CANDIDATE_DIR": DEFAULT_CANDIDATE_DIR,
        "DEFAULT_PROVISIONAL_RESOLUTION": DEFAULT_PROVISIONAL_RESOLUTION,
        "DEFAULT_FINAL_RESOLUTION": DEFAULT_FINAL_RESOLUTION,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        for name, value in bindings.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def validate_pair_for_finalization(**kwargs: Any) -> tuple[dict[str, Any], bytes]:
    with _bound_core():
        return _CORE_VALIDATE_PAIR(**kwargs)


def build_provisional_resolution(**kwargs: Any) -> dict[str, Any]:
    with _bound_core():
        return _CORE_BUILD_PROVISIONAL(**kwargs)


def completed_governance(**kwargs: Any) -> dict[str, Any]:
    with _bound_core():
        return _CORE_COMPLETED_GOVERNANCE(**kwargs)


def build_final_resolution(**kwargs: Any) -> dict[str, Any]:
    with _bound_core():
        return _CORE_BUILD_FINAL(**kwargs)


def prepare_finalization(**kwargs: Any) -> dict[str, Any]:
    with _bound_core():
        return _CORE_PREPARE(**kwargs)


def apply_finalization(plan: dict[str, Any]) -> None:
    with _bound_core():
        _CORE_APPLY(plan)


def plan_summary(plan: dict[str, Any], applied: bool) -> dict[str, Any]:
    with _bound_core():
        return _CORE_PLAN_SUMMARY(plan, applied)


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
