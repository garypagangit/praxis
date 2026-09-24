#!/usr/bin/env python
"""Finalize PX-062 Gate 2.2 v1.1 label governance without a hash cycle.

The default is check-only.  ``--apply`` performs a fail-before-write transition:

1. Rebuild and byte-verify the pending candidate inputs.
2. Verify two independent prediction files against the pending answer key.
3. Bind those files, the candidate task/answer hashes, and a provisional
   unanimous-resolution hash in label_governance only.
4. Regenerate the audited answer key and release-ready manifest while proving
   tasks and catalog bytes are unchanged.
5. Re-run the verifier against the regenerated audited answer key.
6. Atomically replace the seed/input files and write the final resolution last
   as separate evidence.  Its hash is intentionally absent from the seed and
   manifest, so the evidence graph is acyclic.

Do not run ``--apply`` until both blinded auditors have completed their files.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.build_px062_gate2_2_v11_benchmark import (
        AUDITED_LABEL_STATUS,
        CANONICAL_AUDIT_MODELS,
        CANONICAL_AUDIT_PAIR_MANIFEST_PATH,
        CANONICAL_AUDIT_PATHS,
        CANONICAL_AUDIT_SIDECAR_PATHS,
        COMPLETED_RELEASE_STATUS,
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        DEFAULT_SEED_BANK,
        FINAL_RESOLUTION_STATUS,
        PROVISIONAL_RESOLUTION_STATUS,
        ROOT,
        PairVerifier,
        build_artifacts,
        read_json,
        read_json_bytes,
        read_jsonl_bytes,
        sha256_bytes,
        validate_canonical_pair_evidence,
        validate_label_governance,
    )
    from scripts.verify_px062_gate2_2_v11_label_audits import verify
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from build_px062_gate2_2_v11_benchmark import (
        AUDITED_LABEL_STATUS,
        CANONICAL_AUDIT_MODELS,
        CANONICAL_AUDIT_PAIR_MANIFEST_PATH,
        CANONICAL_AUDIT_PATHS,
        CANONICAL_AUDIT_SIDECAR_PATHS,
        COMPLETED_RELEASE_STATUS,
        DEFAULT_PRIOR_TASKS,
        DEFAULT_REGISTRY_INVENTORY,
        DEFAULT_SEED_BANK,
        FINAL_RESOLUTION_STATUS,
        PROVISIONAL_RESOLUTION_STATUS,
        ROOT,
        PairVerifier,
        build_artifacts,
        read_json,
        read_json_bytes,
        read_jsonl_bytes,
        sha256_bytes,
        validate_canonical_pair_evidence,
        validate_label_governance,
    )
    from verify_px062_gate2_2_v11_label_audits import verify


DEFAULT_CANDIDATE_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728/frozen_inputs"
)
DEFAULT_PROVISIONAL_RESOLUTION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728/label_audit_provisional_resolution.json"
)
DEFAULT_FINAL_RESOLUTION = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_1_20260728/label_audit_resolution.json"
)
FROZEN_NAMES = (
    "tasks.jsonl",
    "answer_key.jsonl",
    "registry_catalog.json",
    "benchmark_manifest.json",
)


def pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def logical_path(root: Path, path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def evidence_bytes(
    root: Path,
    path_value: str,
    overrides: dict[str, bytes] | None,
) -> bytes:
    if overrides and path_value in overrides:
        return overrides[path_value]
    path = (root / path_value).resolve()
    try:
        if path.relative_to(root.resolve()).as_posix() != path_value:
            raise ValueError(f"noncanonical audit evidence path: {path_value}")
    except ValueError as exc:
        raise ValueError(f"audit evidence path escapes root: {path_value}") from exc
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"missing canonical audit evidence: {path_value}") from exc


def validate_pair_for_finalization(
    *,
    root: Path,
    candidate_files: dict[str, bytes],
    evidence_overrides: dict[str, bytes] | None,
    pair_verifier: PairVerifier | None,
) -> tuple[dict[str, Any], bytes]:
    manifest_raw = evidence_bytes(
        root, CANONICAL_AUDIT_PAIR_MANIFEST_PATH, evidence_overrides
    )
    manifest = read_json_bytes(manifest_raw, CANONICAL_AUDIT_PAIR_MANIFEST_PATH)
    audits = manifest.get("audits")
    if not isinstance(audits, list) or len(audits) != 2:
        raise ValueError("canonical audit pair manifest must contain two slots")
    bootstrap = {
        "audit_pair_manifest_path": CANONICAL_AUDIT_PAIR_MANIFEST_PATH,
        "audit_pair_manifest_sha256": sha256_bytes(manifest_raw),
    }
    for slot, audit in enumerate(audits, 1):
        if not isinstance(audit, dict):
            raise ValueError(f"canonical audit slot {slot} is invalid")
        bootstrap[f"audit_{slot}_predictions_sha256"] = audit.get(
            "prediction_sha256"
        )
        bootstrap[f"audit_{slot}_sidecar_sha256"] = audit.get("sidecar_sha256")
    pair = validate_canonical_pair_evidence(
        root=root,
        governance=bootstrap,
        candidate_tasks_raw=candidate_files["tasks.jsonl"],
        candidate_answers_raw=candidate_files["answer_key.jsonl"],
        candidate_catalog_raw=candidate_files["registry_catalog.json"],
        candidate_manifest_raw=candidate_files["benchmark_manifest.json"],
        evidence_overrides=evidence_overrides,
        pair_verifier=pair_verifier,
    )
    return pair, manifest_raw


def _audit_binding(
    summary: dict[str, Any],
    path: str,
    pair_audit: dict[str, Any],
    sidecar_path: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": summary["sha256"],
        "rows": summary["rows"],
        "agreement_with_answer_key": summary["agreement_with_answer_key"],
        "disagreement_task_ids": summary["disagreement_task_ids"],
        "confidence_counts": summary["confidence_counts"],
        "slot": pair_audit["slot"],
        "model": pair_audit["model"],
        "sidecar_path": sidecar_path,
        "sidecar_sha256": pair_audit["sidecar_sha256"],
        "accepted_session_ids": copy.deepcopy(pair_audit["accepted_session_ids"]),
    }


def build_provisional_resolution(
    *,
    verification: dict[str, Any],
    candidate_tasks_path: str,
    candidate_answer_path: str,
    audit_paths: list[str],
    canonical_pair: dict[str, Any],
) -> dict[str, Any]:
    if verification.get("all_labels_independently_agreed") is not True:
        raise ValueError("cannot finalize without unanimous candidate verification")
    if verification.get("cross_audit_disagreement_task_ids") != []:
        raise ValueError("cannot finalize with cross-audit disagreements")
    return {
        "schema_version": "px062-gate2.2-label-audit-provisional-v1",
        "status": PROVISIONAL_RESOLUTION_STATUS,
        "candidate_tasks": {
            **verification["tasks"],
            "path": candidate_tasks_path,
        },
        "candidate_answer_key": {
            **verification["answer_key"],
            "path": candidate_answer_path,
        },
        "audits": [
            _audit_binding(summary, path, pair_audit, sidecar_path)
            for summary, path, pair_audit, sidecar_path in zip(
                verification["audits"],
                audit_paths,
                canonical_pair["audits"],
                CANONICAL_AUDIT_SIDECAR_PATHS,
                strict=True,
            )
        ],
        "canonical_pair_manifest": copy.deepcopy(canonical_pair),
        "cross_audit_disagreement_task_ids": [],
        "all_labels_independently_agreed": True,
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
    audits = provisional["audits"]
    return {
        "scenario_origin": pending_governance["scenario_origin"],
        "required_independent_label_audits": 2,
        "completed_independent_label_audits": 2,
        "release_status": COMPLETED_RELEASE_STATUS,
        "audit_1_status": "UNANIMOUS_VERIFIED",
        "audit_2_status": "UNANIMOUS_VERIFIED",
        "audit_resolution_status": "PROVISIONAL_UNANIMOUS_VERIFIED",
        "audit_1_predictions_path": audits[0]["path"],
        "audit_1_predictions_sha256": audits[0]["sha256"],
        "audit_2_predictions_path": audits[1]["path"],
        "audit_2_predictions_sha256": audits[1]["sha256"],
        "audit_1_sidecar_path": audits[0]["sidecar_path"],
        "audit_1_sidecar_sha256": audits[0]["sidecar_sha256"],
        "audit_2_sidecar_path": audits[1]["sidecar_path"],
        "audit_2_sidecar_sha256": audits[1]["sidecar_sha256"],
        "audit_pair_manifest_path": canonical_pair["path"],
        "audit_pair_manifest_sha256": canonical_pair["sha256"],
        "candidate_tasks_sha256": provisional["candidate_tasks"]["sha256"],
        "candidate_answer_key_sha256": provisional["candidate_answer_key"]["sha256"],
        "provisional_resolution_path": provisional_path,
        "provisional_resolution_sha256": sha256_bytes(provisional_raw),
        "provisional_resolution_status": PROVISIONAL_RESOLUTION_STATUS,
        "final_resolution_path": final_resolution_path,
        "final_resolution_status": FINAL_RESOLUTION_STATUS,
        "audit_requirement": pending_governance["audit_requirement"],
    }


def _assert_candidate_matches(
    candidate_dir: Path, candidate_files: dict[str, bytes]
) -> None:
    for name in FROZEN_NAMES:
        path = candidate_dir / name
        try:
            observed = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"missing pending candidate artifact: {path}") from exc
        if observed != candidate_files[name]:
            raise ValueError(f"pending candidate artifact differs from builder: {name}")


def _answer_semantics(raw: bytes) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in row.items() if key != "label_audit_status"}
        for row in read_jsonl_bytes(raw, "answer-key invariant check")
    ]


def build_final_resolution(
    *,
    final_verification: dict[str, Any],
    completed_files: dict[str, bytes],
    provisional_path: str,
    provisional_raw: bytes,
    audit_paths: list[str],
    canonical_pair: dict[str, Any],
) -> dict[str, Any]:
    if final_verification.get("all_labels_independently_agreed") is not True:
        raise ValueError("final regenerated answer key did not reverify unanimously")
    return {
        "schema_version": "px062-gate2.2-label-audit-final-resolution-v1",
        "status": "UNANIMOUS_REVERIFIED_AGAINST_AUDITED_FINAL_ANSWER",
        "provisional_resolution": {
            "path": provisional_path,
            "sha256": sha256_bytes(provisional_raw),
            "status": PROVISIONAL_RESOLUTION_STATUS,
        },
        "final_inputs": {
            name: {
                "sha256": sha256_bytes(completed_files[name]),
                "bytes": len(completed_files[name]),
            }
            for name in FROZEN_NAMES
        },
        "answer_label_status": AUDITED_LABEL_STATUS,
        "audits": [
            _audit_binding(summary, path, pair_audit, sidecar_path)
            for summary, path, pair_audit, sidecar_path in zip(
                final_verification["audits"],
                audit_paths,
                canonical_pair["audits"],
                CANONICAL_AUDIT_SIDECAR_PATHS,
                strict=True,
            )
        ],
        "canonical_pair_manifest": copy.deepcopy(canonical_pair),
        "cross_audit_disagreement_task_ids": [],
        "all_labels_independently_agreed": True,
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
    if len(audit_raws) != 2:
        raise ValueError("exactly two fixed-slot audit payloads are required")
    with tempfile.TemporaryDirectory(prefix="px062-g22-staged-verify-") as temporary:
        directory = Path(temporary)
        tasks_path = directory / "tasks.jsonl"
        answer_path = directory / "answer_key.jsonl"
        catalog_path = directory / "registry_catalog.json"
        audit_paths = [directory / "audit_1.jsonl", directory / "audit_2.jsonl"]
        tasks_path.write_bytes(tasks_raw)
        answer_path.write_bytes(answer_raw)
        catalog_path.write_bytes(catalog_raw)
        for path, raw in zip(audit_paths, audit_raws, strict=True):
            path.write_bytes(raw)
        return verify(tasks_path, answer_path, audit_paths, catalog_path)


def prepare_finalization(
    *,
    root: Path,
    seed_bank_path: Path,
    registry_path: Path,
    prior_tasks_path: Path,
    candidate_dir: Path,
    provisional_resolution_path: Path,
    final_resolution_path: Path,
    evidence_overrides: dict[str, bytes] | None = None,
    pair_verifier: PairVerifier | None = None,
) -> dict[str, Any]:
    """Build a fail-closed plan from the two canonical audit slots only."""

    root = root.resolve()
    seed_bank_path = resolve(root, seed_bank_path)
    registry_path = resolve(root, registry_path)
    prior_tasks_path = resolve(root, prior_tasks_path)
    candidate_dir = resolve(root, candidate_dir)
    provisional_resolution_path = resolve(root, provisional_resolution_path)
    final_resolution_path = resolve(root, final_resolution_path)
    canonical_audit_paths = [root / path for path in CANONICAL_AUDIT_PATHS]

    seed = read_json(seed_bank_path)
    pending_governance = validate_label_governance(seed)
    if pending_governance["completed_independent_label_audits"] != 0:
        raise ValueError("finalization must start from the pending 0/2 candidate")
    candidate_files = build_artifacts(
        root=root,
        seed_bank_path=seed_bank_path,
        registry_path=registry_path,
        prior_tasks_path=prior_tasks_path,
    )
    _assert_candidate_matches(candidate_dir, candidate_files)

    canonical_pair, pair_manifest_raw = validate_pair_for_finalization(
        root=root,
        candidate_files=candidate_files,
        evidence_overrides=evidence_overrides,
        pair_verifier=pair_verifier,
    )
    audit_raws = [
        evidence_bytes(root, path, evidence_overrides)
        for path in CANONICAL_AUDIT_PATHS
    ]
    first_verification = _verify_raw_evidence(
        tasks_raw=candidate_files["tasks.jsonl"],
        answer_raw=candidate_files["answer_key.jsonl"],
        catalog_raw=candidate_files["registry_catalog.json"],
        audit_raws=audit_raws,
    )
    logical_audits = list(CANONICAL_AUDIT_PATHS)
    logical_candidate_tasks = logical_path(root, candidate_dir / "tasks.jsonl")
    logical_candidate_answer = logical_path(root, candidate_dir / "answer_key.jsonl")
    logical_provisional = logical_path(root, provisional_resolution_path)
    logical_final = logical_path(root, final_resolution_path)
    provisional = build_provisional_resolution(
        verification=first_verification,
        candidate_tasks_path=logical_candidate_tasks,
        candidate_answer_path=logical_candidate_answer,
        audit_paths=logical_audits,
        canonical_pair=canonical_pair,
    )
    provisional_raw = pretty_json_bytes(provisional)

    completed_seed = copy.deepcopy(seed)
    completed_seed["label_governance"] = completed_governance(
        pending_governance=pending_governance,
        provisional=provisional,
        provisional_path=logical_provisional,
        provisional_raw=provisional_raw,
        final_resolution_path=logical_final,
        canonical_pair=canonical_pair,
    )
    if {
        key: value for key, value in completed_seed.items() if key != "label_governance"
    } != {key: value for key, value in seed.items() if key != "label_governance"}:
        raise AssertionError("finalization changed seed content outside label_governance")
    completed_seed_raw = pretty_json_bytes(completed_seed)
    completed_evidence = dict(evidence_overrides or {})
    completed_evidence[logical_provisional] = provisional_raw
    completed_files = build_artifacts(
        root=root,
        seed_bank_path=seed_bank_path,
        registry_path=registry_path,
        prior_tasks_path=prior_tasks_path,
        seed_bank_override=completed_seed,
        seed_bank_raw_override=completed_seed_raw,
        candidate_checkpoint_manifest_raw_override=candidate_files[
            "benchmark_manifest.json"
        ],
        evidence_overrides=completed_evidence,
        pair_verifier=pair_verifier,
    )
    if completed_files["tasks.jsonl"] != candidate_files["tasks.jsonl"]:
        raise AssertionError("finalization changed task bytes, IDs, prompts, or option maps")
    if completed_files["registry_catalog.json"] != candidate_files["registry_catalog.json"]:
        raise AssertionError("finalization changed registry catalog bytes")
    if _answer_semantics(completed_files["answer_key.jsonl"]) != _answer_semantics(
        candidate_files["answer_key.jsonl"]
    ):
        raise AssertionError("finalization changed answer semantics")
    completed_manifest = json.loads(completed_files["benchmark_manifest.json"])
    if completed_manifest.get("benchmark_status") != "AUDITED_CONFIRMATORY_INPUTS_READY_TO_FREEZE":
        raise AssertionError("completed manifest is not collector release-ready")

    final_verification = _verify_raw_evidence(
        tasks_raw=completed_files["tasks.jsonl"],
        answer_raw=completed_files["answer_key.jsonl"],
        catalog_raw=completed_files["registry_catalog.json"],
        audit_raws=audit_raws,
    )
    final_resolution = build_final_resolution(
        final_verification=final_verification,
        completed_files=completed_files,
        provisional_path=logical_provisional,
        provisional_raw=provisional_raw,
        audit_paths=logical_audits,
        canonical_pair=canonical_pair,
    )
    final_resolution_raw = pretty_json_bytes(final_resolution)
    sealed_evidence_hashes = {
        CANONICAL_AUDIT_PAIR_MANIFEST_PATH: sha256_bytes(pair_manifest_raw),
        **{
            path: sha256_bytes(raw)
            for path, raw in zip(CANONICAL_AUDIT_PATHS, audit_raws, strict=True)
        },
        **{
            path: canonical_pair["audits"][index]["sidecar_sha256"]
            for index, path in enumerate(CANONICAL_AUDIT_SIDECAR_PATHS)
        },
    }
    return {
        "root": root,
        "seed_bank_path": seed_bank_path,
        "candidate_dir": candidate_dir,
        "audit_paths": canonical_audit_paths,
        "provisional_resolution_path": provisional_resolution_path,
        "final_resolution_path": final_resolution_path,
        "candidate_seed_sha256": sha256_file(seed_bank_path),
        "candidate_files": candidate_files,
        "completed_seed": completed_seed,
        "completed_seed_raw": completed_seed_raw,
        "completed_files": completed_files,
        "canonical_pair_manifest": canonical_pair,
        "sealed_evidence_hashes": sealed_evidence_hashes,
        "provisional_resolution": provisional,
        "provisional_resolution_raw": provisional_raw,
        "final_resolution": final_resolution,
        "final_resolution_raw": final_resolution_raw,
    }


def _atomic_replace(path: Path, raw: bytes) -> None:
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


def apply_finalization(plan: dict[str, Any]) -> None:
    seed_path: Path = plan["seed_bank_path"]
    candidate_dir: Path = plan["candidate_dir"]
    provisional_path: Path = plan["provisional_resolution_path"]
    final_path: Path = plan["final_resolution_path"]
    if sha256_file(seed_path) != plan["candidate_seed_sha256"]:
        raise ValueError("seed bank changed after finalization plan was prepared")
    _assert_candidate_matches(candidate_dir, plan["candidate_files"])
    for logical_evidence_path, expected_hash in plan["sealed_evidence_hashes"].items():
        evidence_path = (plan["root"] / logical_evidence_path).resolve()
        if sha256_file(evidence_path) != expected_hash:
            raise ValueError(
                "canonical audit evidence changed after finalization plan was prepared: "
                f"{logical_evidence_path}"
            )
    if provisional_path.exists() or final_path.exists():
        raise FileExistsError("refusing to overwrite existing label-resolution evidence")

    # Provisional evidence is committed before the completed seed that binds it.
    _atomic_replace(provisional_path, plan["provisional_resolution_raw"])
    _atomic_replace(seed_path, plan["completed_seed_raw"])
    for name in FROZEN_NAMES:
        _atomic_replace(candidate_dir / name, plan["completed_files"][name])
    # This external resolution is the commit marker and is always written last.
    _atomic_replace(final_path, plan["final_resolution_raw"])


def plan_summary(plan: dict[str, Any], applied: bool) -> dict[str, Any]:
    return {
        "applied": applied,
        "candidate_tasks_sha256": sha256_bytes(
            plan["candidate_files"]["tasks.jsonl"]
        ),
        "candidate_answer_key_sha256": sha256_bytes(
            plan["candidate_files"]["answer_key.jsonl"]
        ),
        "completed_tasks_sha256": sha256_bytes(
            plan["completed_files"]["tasks.jsonl"]
        ),
        "completed_answer_key_sha256": sha256_bytes(
            plan["completed_files"]["answer_key.jsonl"]
        ),
        "completed_manifest_sha256": sha256_bytes(
            plan["completed_files"]["benchmark_manifest.json"]
        ),
        "provisional_resolution_sha256": sha256_bytes(
            plan["provisional_resolution_raw"]
        ),
        "final_resolution_sha256_external_only": sha256_bytes(
            plan["final_resolution_raw"]
        ),
        "final_resolution_hash_embedded_in_frozen_inputs": False,
        "manifest_status": "AUDITED_CONFIRMATORY_INPUTS_READY_TO_FREEZE",
    }


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
