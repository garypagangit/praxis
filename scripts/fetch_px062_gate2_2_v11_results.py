#!/usr/bin/env python
"""Outcome-blind, version-pinned fetch for PX-062 Gate 2.2 v1.1."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import fetch_px062_gate2_2_results as core
    from scripts.px062_gate2_2_v11_contract import (
        ANSWER_KEY_PATH,
        BENCHMARK_MANIFEST_PATH,
        CATALOG_PATH,
        COLLECTOR_PATH,
        CONFIG_PATH,
        ENTRYPOINT_PATH,
        EXECUTION_TEST_PATH,
        FETCHER_PATH,
        FETCH_REGISTRAR_PATH,
        MANIFEST_DIR,
        OPERATOR_FETCH_POLICY_PATH,
        REQUIREMENTS_GIT_PATH,
        S3_PREFIX,
        SEALED_CONFIRMATION_DIR,
        TASKS_PATH,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import fetch_px062_gate2_2_results as core  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        ANSWER_KEY_PATH,
        BENCHMARK_MANIFEST_PATH,
        CATALOG_PATH,
        COLLECTOR_PATH,
        CONFIG_PATH,
        ENTRYPOINT_PATH,
        EXECUTION_TEST_PATH,
        FETCHER_PATH,
        FETCH_REGISTRAR_PATH,
        MANIFEST_DIR,
        OPERATOR_FETCH_POLICY_PATH,
        REQUIREMENTS_GIT_PATH,
        S3_PREFIX,
        SEALED_CONFIRMATION_DIR,
        TASKS_PATH,
    )


DEFAULT_COMPLETION_REGISTRATION = MANIFEST_DIR / "completion_registration.json"
DEFAULT_DESTINATION = SEALED_CONFIRMATION_DIR
SOURCE_GIT_PATHS = {
    CONFIG_PATH: CONFIG_PATH,
    TASKS_PATH: TASKS_PATH,
    CATALOG_PATH: CATALOG_PATH,
    BENCHMARK_MANIFEST_PATH: BENCHMARK_MANIFEST_PATH,
    COLLECTOR_PATH: COLLECTOR_PATH,
    ENTRYPOINT_PATH: ENTRYPOINT_PATH,
    "requirements.txt": REQUIREMENTS_GIT_PATH,
}

# Pure checksum/archive helpers retain their independently tested v1 behavior.
sha256_bytes = core.sha256_bytes
canonical_json_bytes = core.canonical_json_bytes
checksum_runtime_record = core.checksum_runtime_record
operator_fetch_policy_record = core.operator_fetch_policy_record
checksum_bytes_base64 = core.checksum_bytes_base64
validate_tar = core.validate_tar
validate_download = core.validate_download
validate_checksum_verification_record = core.validate_checksum_verification_record
verify_archive_checksum_contract = core.verify_archive_checksum_contract
validate_fetch_receipt_against_completion = core.validate_fetch_receipt_against_completion
validate_completion_evidence = core.validate_completion_evidence

OUTPUT_FILES = core.OUTPUT_FILES
SEALED_FILES = core.SEALED_FILES
SEALED_PAYLOAD_FILES = core.SEALED_PAYLOAD_FILES
FETCH_RECEIPT_KEYS = core.FETCH_RECEIPT_KEYS
S3_CHECKSUM_FIELDS = core.S3_CHECKSUM_FIELDS
CHECKSUM_REQUIREMENTS_PATH = core.CHECKSUM_REQUIREMENTS_PATH
_CORE_FETCH_AND_SEAL = core.fetch_and_seal


@contextlib.contextmanager
def bound_core() -> Iterator[None]:
    bindings = {
        "DEFAULT_COMPLETION_REGISTRATION": DEFAULT_COMPLETION_REGISTRATION,
        "DEFAULT_DESTINATION": DEFAULT_DESTINATION,
        "FETCHER_PATH": FETCHER_PATH,
        "FETCH_TEST_PATH": EXECUTION_TEST_PATH,
        "REGISTRAR_PATH": FETCH_REGISTRAR_PATH,
        "CONFIG_PATH": CONFIG_PATH,
        "TASKS_PATH": TASKS_PATH,
        "CATALOG_PATH": CATALOG_PATH,
        "BENCHMARK_MANIFEST_PATH": BENCHMARK_MANIFEST_PATH,
        "ANSWER_KEY_PATH": ANSWER_KEY_PATH,
        "COLLECTOR_PATH": COLLECTOR_PATH,
        "ENTRYPOINT_PATH": ENTRYPOINT_PATH,
        "REQUIREMENTS_GIT_PATH": REQUIREMENTS_GIT_PATH,
        "OPERATOR_FETCH_POLICY_PATH": OPERATOR_FETCH_POLICY_PATH,
        "PX062_GATE22_PREFIX": S3_PREFIX,
        "SOURCE_GIT_PATHS": SOURCE_GIT_PATHS,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        for name, value in bindings.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def fetch_and_seal(**kwargs: Any) -> dict[str, Any]:
    with bound_core():
        return _CORE_FETCH_AND_SEAL(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Outcome-blind version-pinned PX-062 Gate 2.2 v1.1 fetch"
    )
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument(
        "--completion-registration",
        type=Path,
        default=DEFAULT_COMPLETION_REGISTRATION,
    )
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipt = fetch_and_seal(
        root=root,
        profile=args.profile,
        completion_path=args.completion_registration,
        destination=args.destination,
    )
    print(
        json.dumps(
            {
                "adjudication_run": receipt["adjudication_run"],
                "job_name": receipt["job"]["name"],
                "model_trace_content_parsed": receipt[
                    "model_trace_content_parsed"
                ],
                "output_version_id": receipt["output_artifact"]["version_id"],
                "sealed_directory": args.destination.as_posix(),
                "source_version_id": receipt["source_artifact"]["version_id"],
                "status": receipt["job"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
