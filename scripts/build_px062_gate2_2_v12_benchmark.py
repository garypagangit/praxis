#!/usr/bin/env python
"""Build the versioned PX-062 Gate 2.2 v1.2 benchmark.

The byte-pinned v1 construction algorithm remains authoritative.  This module
only binds v1.2 paths, a version-specific private answer fingerprint, and a
catalog identity that explicitly preserves the frozen registry semantics.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import build_px062_gate2_2_benchmark as base
except ImportError:  # direct execution from scripts/
    import build_px062_gate2_2_benchmark as base  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_BANK = Path(
    "manifests/px062_gate2_2_v1_2_20260728/task_seed_bank.json"
)
DEFAULT_REGISTRY_INVENTORY = base.DEFAULT_REGISTRY_INVENTORY
DEFAULT_PRIOR_TASKS = base.DEFAULT_PRIOR_TASKS
DEFAULT_OUTPUT_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/frozen_inputs"
)
EXPERIMENT_STAGE = "PX-062 Gate 2.2 v1.2"
EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-2-20260728"
SOURCE_EXPERIMENT_ID = "px062-skill-selection-gate2-2-v1-1-20260728"
SOURCE_CATALOG_SHA256 = (
    "d775221aaa2d0bb11ee7b25c2236a241970175d97726fc70f55e47ca6589acde"
)
PRIVATE_SEED_FINGERPRINT_NAMESPACE = (
    "px062-gate2.2-v1.2-private-seed-fingerprint-v1"
)

AUDITED_LABEL_STATUS = base.AUDITED_LABEL_STATUS
CANONICAL_AUDIT_MODELS = base.CANONICAL_AUDIT_MODELS
COMPLETED_RELEASE_STATUS = base.COMPLETED_RELEASE_STATUS
FINAL_RESOLUTION_STATUS = base.FINAL_RESOLUTION_STATUS
PROVISIONAL_RESOLUTION_STATUS = base.PROVISIONAL_RESOLUTION_STATUS
PairVerifier = base.PairVerifier

GATE_EVIDENCE_DIR = (
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728"
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
CHECKPOINT_CONFIG_PATH = (
    "configs/px062_skill_selection_gate2_2_v1_2_20260728.json"
)
CHECKPOINT_RUNNER_PATH = "scripts/run_px062_gate2_2_v12_blind_audit.py"
CHECKPOINT_CORE_PATH = "scripts/run_px062_gate2_2_blind_audit.py"
CHECKPOINT_PROTOCOL_PATH = (
    f"{GATE_EVIDENCE_DIR}/LABEL_AUDIT_PROTOCOL_V1_2_20260728.md"
)
CHECKPOINT_TESTS_PATH = "tests/test_px062_gate2_2_v12_blind_audit.py"
CHECKPOINT_TRACKED_PATHS = (
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/tasks.jsonl",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/registry_catalog.json",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/answer_key.jsonl",
    f"{GATE_EVIDENCE_DIR}/frozen_inputs/benchmark_manifest.json",
    DEFAULT_SEED_BANK.as_posix(),
    CHECKPOINT_CONFIG_PATH,
    CHECKPOINT_RUNNER_PATH,
    CHECKPOINT_CORE_PATH,
    CHECKPOINT_PROTOCOL_PATH,
    CHECKPOINT_TESTS_PATH,
)

_BASE_BINDINGS: dict[str, Any] = {
    "DEFAULT_SEED_BANK": DEFAULT_SEED_BANK,
    "DEFAULT_OUTPUT_DIR": DEFAULT_OUTPUT_DIR,
    "GATE_EVIDENCE_DIR": GATE_EVIDENCE_DIR,
    "CANONICAL_AUDIT_PATHS": CANONICAL_AUDIT_PATHS,
    "CANONICAL_AUDIT_SIDECAR_PATHS": CANONICAL_AUDIT_SIDECAR_PATHS,
    "CANONICAL_AUDIT_PAIR_MANIFEST_PATH": CANONICAL_AUDIT_PAIR_MANIFEST_PATH,
    "CHECKPOINT_TRACKED_PATHS": CHECKPOINT_TRACKED_PATHS,
    "CHECKPOINT_CONFIG_PATH": CHECKPOINT_CONFIG_PATH,
    "CHECKPOINT_RUNNER_PATH": CHECKPOINT_RUNNER_PATH,
    "CHECKPOINT_PROTOCOL_PATH": CHECKPOINT_PROTOCOL_PATH,
    "CHECKPOINT_TESTS_PATH": CHECKPOINT_TESTS_PATH,
}


@contextlib.contextmanager
def _bound_base() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _BASE_BINDINGS}
    try:
        for name, value in _BASE_BINDINGS.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def _v12_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(catalog)
    value["benchmark_identity"] = {
        "experiment_id": EXPERIMENT_ID,
        "revision": "v1.2",
        "source_catalog_sha256": SOURCE_CATALOG_SHA256,
        "registry_semantics_changed": False,
    }
    return value


def _v12_answer_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _derive_build_artifacts() -> Any:
    source = inspect.getsource(base.build_artifacts)
    marker = "    if any(set(row) != TASK_FIELDS for row in tasks):\n"
    if source.count(marker) != 1:
        raise RuntimeError("sealed builder candidate-identity insertion point drift")
    insertion = (
        "    catalog = _v12_catalog(catalog)\n"
        "    candidate_answers = _v12_answer_rows(candidate_answers)\n"
    )
    source = source.replace(marker, insertion + marker)
    namespace = dict(base.__dict__)
    namespace.update(_BASE_BINDINGS)
    namespace.update(
        {
            "_v12_catalog": _v12_catalog,
            "_v12_answer_rows": _v12_answer_rows,
        }
    )
    exec(compile(source, __file__, "exec"), namespace)
    return namespace["build_artifacts"]


_BUILD_ARTIFACTS_V12 = _derive_build_artifacts()


def _historical_pair_verifier(root: Path, *, write_manifest: bool) -> dict[str, Any]:
    if write_manifest:
        raise ValueError("builder evidence validation never writes the pair manifest")
    try:
        from scripts import run_px062_gate2_2_v12_blind_audit as audit_runner
    except ImportError as exc:
        raise ValueError("v1.2 audit runner is not yet frozen") from exc
    return audit_runner.verify_pair(
        root,
        write_manifest=False,
        verification_mode="historical",
    )


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
    with _bound_base():
        files = _BUILD_ARTIFACTS_V12(
            root=root,
            seed_bank_path=seed_bank_path,
            registry_path=registry_path,
            prior_tasks_path=prior_tasks_path,
            seed_bank_override=seed_bank_override,
            seed_bank_raw_override=seed_bank_raw_override,
            candidate_checkpoint_manifest_raw_override=(
                candidate_checkpoint_manifest_raw_override
            ),
            evidence_overrides=evidence_overrides,
            pair_verifier=pair_verifier or _historical_pair_verifier,
        )
    manifest = json.loads(files["benchmark_manifest.json"])
    manifest["experiment_stage"] = EXPERIMENT_STAGE
    manifest["revision_lineage"] = {
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "retained_prompt_ids": 1022,
        "replaced_prompt_ids": 10,
        "private_seed_fingerprint_namespace": (
            PRIVATE_SEED_FINGERPRINT_NAMESPACE
        ),
        "registry_semantics_changed": False,
    }
    files["benchmark_manifest.json"] = base.canonical_json_bytes(manifest)
    return files


def validate_canonical_pair_evidence(**kwargs: Any) -> dict[str, Any]:
    with _bound_base():
        if kwargs.get("pair_verifier") is None:
            kwargs["pair_verifier"] = _historical_pair_verifier
        return base.validate_canonical_pair_evidence(**kwargs)


def validate_label_governance(seed_bank: dict[str, Any]) -> dict[str, Any]:
    with _bound_base():
        return base.validate_label_governance(seed_bank)


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
