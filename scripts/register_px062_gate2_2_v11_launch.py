#!/usr/bin/env python
"""Register, but never launch, the PX-062 Gate 2.2 v1.1 AWS job."""

from __future__ import annotations

import argparse
import contextlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import build_px062_gate2_2_v11_benchmark as benchmark
    from scripts import build_px062_gate2_2_v11_bundle as bundle
    from scripts import check_px062_gate2_2_v11_tokenizer_conformance as conformance
    from scripts import fetch_px062_gate2_2_results as fetch_core
    from scripts import register_px062_gate2_2_launch as core
    from scripts import run_px062_gate2_2_v11_blind_audit as audit
    from scripts.px062_gate2_2_v11_contract import (
        ANSWER_KEY_PATH,
        AUDIT_EVIDENCE_MANIFEST_PATH,
        AUDIT_PROTOCOL_PATH,
        AUDIT_RUNNER_PATH,
        AUDIT_TEST_PATH,
        BENCHMARK_MANIFEST_PATH,
        CATALOG_PATH,
        COLLECTION_OUTPUT_DIR,
        CONFIG_PATH,
        CONFORMANCE_PATH,
        DEFAULT_JOB_NAME,
        EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256,
        FROZEN_EVIDENCE_PATHS,
        MANIFEST_DIR,
        OPERATOR_FETCH_POLICY_PATH,
        S3_PREFIX,
        TASKS_PATH,
        TOKENIZER_CHECKER_PATH,
        validate_label_freeze,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import build_px062_gate2_2_v11_benchmark as benchmark  # type: ignore[no-redef]
    import build_px062_gate2_2_v11_bundle as bundle  # type: ignore[no-redef]
    import check_px062_gate2_2_v11_tokenizer_conformance as conformance  # type: ignore[no-redef]
    import fetch_px062_gate2_2_results as fetch_core  # type: ignore[no-redef]
    import register_px062_gate2_2_launch as core  # type: ignore[no-redef]
    import run_px062_gate2_2_v11_blind_audit as audit  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        ANSWER_KEY_PATH,
        AUDIT_EVIDENCE_MANIFEST_PATH,
        AUDIT_PROTOCOL_PATH,
        AUDIT_RUNNER_PATH,
        AUDIT_TEST_PATH,
        BENCHMARK_MANIFEST_PATH,
        CATALOG_PATH,
        COLLECTION_OUTPUT_DIR,
        CONFIG_PATH,
        CONFORMANCE_PATH,
        DEFAULT_JOB_NAME,
        EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256,
        FROZEN_EVIDENCE_PATHS,
        MANIFEST_DIR,
        OPERATOR_FETCH_POLICY_PATH,
        S3_PREFIX,
        TASKS_PATH,
        TOKENIZER_CHECKER_PATH,
        validate_label_freeze,
    )


DEFAULT_BUCKET = core.DEFAULT_BUCKET
DEFAULT_REGION = core.DEFAULT_REGION
DEFAULT_ROLE = core.DEFAULT_ROLE
DEFAULT_IMAGE = core.DEFAULT_IMAGE
FINAL_CONFIG_STATUS = "FROZEN_PREREGISTERED"

# These deterministic values are populated from an actual full v1.1
# conformance run before launch registration.  ``None`` is intentionally a
# hard stop, not a permissive wildcard.
EXPECTED_CONTEXT_HEADROOM: dict[str, int] | None = None

CONFORMANCE_TOP_LEVEL_KEYS = set(core.CONFORMANCE_TOP_LEVEL_KEYS)
CONFORMANCE_MODEL_KEYS = set(core.CONFORMANCE_MODEL_KEYS)

sha256_bytes = core.sha256_bytes
sha256_file = core.sha256_file
checksum_sha256_base64 = core.checksum_sha256_base64
canonical_json_bytes = core.canonical_json_bytes
strict_json_bytes = core.strict_json_bytes
validate_git_state = core.validate_git_state
validate_new_key = core.validate_new_key
require_explicit_training_job_absence = core.require_explicit_training_job_absence
aws = core.aws
git = core.git

_CORE_REGISTER = core.register
_CORE_VALIDATE_LABEL_MANIFEST = core.validate_label_audit_evidence_manifest
_CORE_VALIDATE_HISTORICAL_CHECKPOINT = core.validate_historical_audit_checkpoint


def _hash_record(path: str, raw: bytes) -> dict[str, Any]:
    return {"path": path, "sha256": sha256_bytes(raw)}


def validate_historical_audit_checkpoint(
    root: Path,
    checkpoint: Any,
    *,
    descendant_commit: str | None = None,
) -> dict[str, Any]:
    with _bound_core(include_validators=False):
        return _CORE_VALIDATE_HISTORICAL_CHECKPOINT(
            root, checkpoint, descendant_commit=descendant_commit
        )


def validate_label_audit_evidence_manifest(
    root: Path,
    *,
    source_commit: str | None = None,
) -> dict[str, Any]:
    with _bound_core(include_validators=False):
        return _CORE_VALIDATE_LABEL_MANIFEST(
            root,
            pair_verifier=audit.verify_pair,
            source_commit=source_commit,
            checkpoint_validator=validate_historical_audit_checkpoint,
        )


def validate_final_config_and_conformance(
    root: Path,
    source_commit: str,
    *,
    blob_reader: Any = core.git_blob,
) -> dict[str, Any]:
    """Bind the final label freeze to the independently rerun tokenizer gate."""

    freeze = validate_label_freeze(
        root, source_commit=source_commit, blob_reader=blob_reader
    )
    paths = (
        CONFIG_PATH,
        TASKS_PATH,
        ANSWER_KEY_PATH,
        CATALOG_PATH,
        BENCHMARK_MANIFEST_PATH,
        AUDIT_RUNNER_PATH,
        AUDIT_TEST_PATH,
        AUDIT_PROTOCOL_PATH,
        CONFORMANCE_PATH,
        TOKENIZER_CHECKER_PATH,
        "scripts/run_px062_gate2_2_models.py",
    )
    raw = {path: blob_reader(root, source_commit, path) for path in paths}
    config = strict_json_bytes(raw[CONFIG_PATH], "v1.1 final config")
    receipt = strict_json_bytes(raw[CONFORMANCE_PATH], "v1.1 conformance receipt")
    projection = conformance.semantic_config_projection_record(config)
    if (
        projection.get("sha256")
        != EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256
        or receipt.get("semantic_config_projection") != projection
    ):
        raise ValueError("v1.1 final config semantic projection drift")
    protocol = config["label_audit_protocol"]
    expected_audit_bindings = {
        "runner_sha256": sha256_bytes(raw[AUDIT_RUNNER_PATH]),
        "protocol_sha256": sha256_bytes(raw[AUDIT_PROTOCOL_PATH]),
        "tests_sha256": sha256_bytes(raw[AUDIT_TEST_PATH]),
    }
    if any(protocol.get(key) != value for key, value in expected_audit_bindings.items()):
        raise ValueError("v1.1 final config label-audit source binding drift")
    if (
        set(receipt) != CONFORMANCE_TOP_LEVEL_KEYS
        or receipt.get("schema_version") != conformance.CONFORMANCE_SCHEMA
        or receipt.get("pass") is not True
    ):
        raise ValueError("stale, malformed, or failed v1.1 conformance receipt")
    checked_at = receipt.get("checked_at_utc")
    if not isinstance(checked_at, str) or not checked_at.endswith("Z"):
        raise ValueError("v1.1 conformance receipt timestamp drift")
    try:
        parsed_checked_at = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid v1.1 conformance receipt timestamp") from exc
    if parsed_checked_at.utcoffset() != timezone.utc.utcoffset(parsed_checked_at):
        raise ValueError("v1.1 conformance receipt timestamp is not UTC")
    if receipt.get("checker") != _hash_record(
        TOKENIZER_CHECKER_PATH, raw[TOKENIZER_CHECKER_PATH]
    ):
        raise ValueError("v1.1 tokenizer-conformance checker binding drift")
    collector_path = "scripts/run_px062_gate2_2_models.py"
    if receipt.get("message_constructor_source") != _hash_record(
        collector_path, raw[collector_path]
    ):
        raise ValueError("v1.1 tokenizer-conformance constructor binding drift")
    if receipt.get("config_sha256") != sha256_bytes(raw[CONFIG_PATH]):
        raise ValueError("v1.1 conformance did not run on the final config")
    if (
        receipt.get("tasks_sha256") != freeze["source_integrity"]["tasks_sha256"]
        or receipt.get("registry_catalog_sha256")
        != freeze["source_integrity"]["registry_catalog_sha256"]
    ):
        raise ValueError("v1.1 conformance frozen-input hash drift")
    if receipt.get("dependency_versions") != conformance.EXPECTED_DEPENDENCIES:
        raise ValueError("v1.1 conformance dependency drift")
    if receipt.get("arms") != list(conformance.EXPECTED_ARMS):
        raise ValueError("v1.1 conformance arm drift")
    exact_values = {
        "task_count": 1032,
        "option_maps_and_catalogs_validated": 1032,
        "structured_choices": 44,
        "structured_response_form": '{"choice":"Snnn"}',
        "open_response_max_new_tokens": 32,
        "minimum_model_context_window_tokens": conformance.CONTEXT_WINDOW_TOKENS,
        "strict_context_comparison": "prompt_plus_response_tokens < 32768",
    }
    for key, expected in exact_values.items():
        if receipt.get(key) != expected:
            raise ValueError(f"v1.1 tokenizer-conformance {key} drift")
    if EXPECTED_CONTEXT_HEADROOM is None:
        raise ValueError(
            "v1.1 conformance maxima have not been code-pinned after the full run"
        )
    model_rows = receipt.get("models")
    if not isinstance(model_rows, list) or [
        row.get("model_id") if isinstance(row, dict) else None for row in model_rows
    ] != list(conformance.EXPECTED_MODEL_REVISIONS):
        raise ValueError("v1.1 conformance model order drift")
    rendered_total = 0
    choice_set_sha256: str | None = None
    for row in model_rows:
        model_id = row["model_id"]
        if set(row) != CONFORMANCE_MODEL_KEYS:
            raise ValueError(f"v1.1 conformance model schema drift: {model_id}")
        if row.get("revision") != conformance.EXPECTED_MODEL_REVISIONS[model_id]:
            raise ValueError(f"v1.1 conformance revision drift: {model_id}")
        if (
            row.get("choice_count") != 44
            or row.get("choice_roundtrip_failures") != 0
            or row.get("open_response_budget_probe", {}).get("token_budget") != 32
        ):
            raise ValueError(f"v1.1 conformance choice/probe drift: {model_id}")
        current_choice_hash = row.get("choice_set_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(current_choice_hash)):
            raise ValueError(f"v1.1 conformance choice hash drift: {model_id}")
        if choice_set_sha256 is None:
            choice_set_sha256 = str(current_choice_hash)
        elif current_choice_hash != choice_set_sha256:
            raise ValueError("v1.1 conformance choice sets differ by model")
        totals = row.get("maximum_prompt_plus_response_tokens")
        if not isinstance(totals, dict) or set(totals) != set(
            conformance.EXPECTED_ARMS
        ) or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in totals.values()
        ):
            raise ValueError(f"v1.1 conformance token maxima drift: {model_id}")
        headroom = conformance.CONTEXT_WINDOW_TOKENS - max(totals.values())
        if (
            headroom <= 0
            or row.get("minimum_context_headroom_tokens") != headroom
            or headroom != EXPECTED_CONTEXT_HEADROOM.get(model_id)
        ):
            raise ValueError(f"v1.1 conformance context headroom drift: {model_id}")
        rendered = row.get("rendered_model_task_arm_sets")
        if rendered != 1032 * len(conformance.EXPECTED_ARMS):
            raise ValueError(f"v1.1 conformance rendered count drift: {model_id}")
        rendered_total += rendered
    if rendered_total != 10320:
        raise ValueError("v1.1 conformance total rendered count is not 10320")
    return {
        "config": config,
        "config_sha256": sha256_bytes(raw[CONFIG_PATH]),
        "conformance": receipt,
        "conformance_sha256": sha256_bytes(raw[CONFORMANCE_PATH]),
        "source_integrity": freeze["source_integrity"],
        "label_resolution_sha256": freeze["resolution_sha256"],
    }


@contextlib.contextmanager
def _bound_core(*, include_validators: bool = True) -> Iterator[None]:
    core_bindings: dict[str, Any] = {
        "PREFIX": S3_PREFIX,
        "MANIFEST_DIR": MANIFEST_DIR,
        "FROZEN_EVIDENCE_PATHS": FROZEN_EVIDENCE_PATHS,
        "CONFIG": CONFIG_PATH,
        "CONFIG_PATH": CONFIG_PATH,
        "TASKS_PATH": TASKS_PATH,
        "ANSWER_KEY_PATH": ANSWER_KEY_PATH,
        "CATALOG_PATH": CATALOG_PATH,
        "BENCHMARK_MANIFEST_PATH": BENCHMARK_MANIFEST_PATH,
        "AUDIT_RUNNER_PATH": AUDIT_RUNNER_PATH,
        "AUDIT_TEST_PATH": AUDIT_TEST_PATH,
        "AUDIT_PROTOCOL_PATH": AUDIT_PROTOCOL_PATH,
        "CONFORMANCE_PATH": CONFORMANCE_PATH,
        "ARCHIVE_MEMBERS": bundle.ARCHIVE_MEMBERS,
        "build": bundle.build,
        "CHECKPOINT_TRACKED_PATHS": benchmark.CHECKPOINT_TRACKED_PATHS,
        "CHECKPOINT_CONFIG_PATH": benchmark.CHECKPOINT_CONFIG_PATH,
        "verify_pair": audit.verify_pair,
        "semantic_config_projection_record": conformance.semantic_config_projection_record,
        "OPERATOR_FETCH_POLICY_PATH": OPERATOR_FETCH_POLICY_PATH,
    }
    if include_validators:
        core_bindings.update(
            {
                "validate_label_audit_evidence_manifest": validate_label_audit_evidence_manifest,
                "validate_final_config_and_conformance": validate_final_config_and_conformance,
            }
        )
    fetch_bindings = {
        "OPERATOR_FETCH_POLICY_PATH": OPERATOR_FETCH_POLICY_PATH,
        "PX062_GATE22_PREFIX": S3_PREFIX,
    }
    previous_core = {name: getattr(core, name) for name in core_bindings}
    previous_fetch = {name: getattr(fetch_core, name) for name in fetch_bindings}
    try:
        for name, value in core_bindings.items():
            setattr(core, name, value)
        for name, value in fetch_bindings.items():
            setattr(fetch_core, name, value)
        yield
    finally:
        for name, value in previous_fetch.items():
            setattr(fetch_core, name, value)
        for name, value in previous_core.items():
            setattr(core, name, value)


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
    if job_name != DEFAULT_JOB_NAME:
        raise ValueError("v1.1 confirmatory job name differs from the frozen contract")
    # This happens before any AWS call in the delegated registrar.
    validate_label_freeze(root, source_commit=source_commit)
    with _bound_core():
        return _CORE_REGISTER(
            root=root,
            profile=profile,
            source_commit=source_commit,
            job_name=job_name,
            bucket=bucket,
            region=region,
            role_arn=role_arn,
            image=image,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--job-name", default=DEFAULT_JOB_NAME)
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
