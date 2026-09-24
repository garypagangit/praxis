#!/usr/bin/env python
"""Register completed PX-062 Gate 2.2 cloud evidence without downloading it."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.fetch_px062_gate2_2_results import (
        ANSWER_KEY_PATH,
        CHECKSUM_REQUIREMENTS_PATH,
        OPERATOR_FETCH_POLICY_PATH,
        PX062_GATE22_PREFIX,
        FETCH_RECEIPT_KEYS,
        SEALED_PAYLOAD_FILES,
        DEFAULT_COMPLETION_REGISTRATION,
        DEFAULT_DESTINATION,
        FETCHER_PATH,
        FETCH_TEST_PATH,
        REGISTRAR_PATH,
        S3_CHECKSUM_FIELDS,
        AwsCall,
        GitBlobRead,
        GitStateRead,
        aws_json,
        canonical_tags,
        canonical_json_bytes,
        checksum_runtime_record,
        compare_head,
        digest_file,
        git_blob,
        git_state,
        get_object_attributes,
        head_version,
        list_versions,
        load_json,
        negotiate_head_checksums,
        operator_fetch_policy_record,
        parse_s3,
        parse_time,
        parse_s3_etag,
        repo_path,
        sha256_bytes,
        single_version,
        s3_head_fingerprint,
        validate_git_evidence,
        validate_registered_artifact_contract,
        validate_completion_evidence,
        validate_fetch_receipt_against_completion,
        validate_job,
        version_fingerprint,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from fetch_px062_gate2_2_results import (  # type: ignore[no-redef]
        ANSWER_KEY_PATH,
        CHECKSUM_REQUIREMENTS_PATH,
        OPERATOR_FETCH_POLICY_PATH,
        PX062_GATE22_PREFIX,
        FETCH_RECEIPT_KEYS,
        SEALED_PAYLOAD_FILES,
        DEFAULT_COMPLETION_REGISTRATION,
        DEFAULT_DESTINATION,
        FETCHER_PATH,
        FETCH_TEST_PATH,
        REGISTRAR_PATH,
        S3_CHECKSUM_FIELDS,
        AwsCall,
        GitBlobRead,
        GitStateRead,
        aws_json,
        canonical_tags,
        canonical_json_bytes,
        checksum_runtime_record,
        compare_head,
        digest_file,
        git_blob,
        git_state,
        get_object_attributes,
        head_version,
        list_versions,
        load_json,
        negotiate_head_checksums,
        operator_fetch_policy_record,
        parse_s3,
        parse_time,
        parse_s3_etag,
        repo_path,
        sha256_bytes,
        single_version,
        s3_head_fingerprint,
        validate_git_evidence,
        validate_registered_artifact_contract,
        validate_completion_evidence,
        validate_fetch_receipt_against_completion,
        validate_job,
        version_fingerprint,
    )


DEFAULT_LAUNCH_REGISTRATION = Path(
    "manifests/px062_gate2_2_20260728/confirmatory_registration.json"
)
DEFAULT_LAUNCH_RECEIPT = Path(
    "manifests/px062_gate2_2_20260728/launch_receipt.json"
)
DEFAULT_FETCH_RECEIPT = DEFAULT_DESTINATION / "completion_fetch_receipt.json"
DEFAULT_ADJUDICATION_AUTHORIZATION = Path(
    "manifests/px062_gate2_2_20260728/adjudication_authorization.json"
)
DEFAULT_ADJUDICATION_RESULT = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728/PX062_GATE2_2_CONFIRMATORY_RESULT.json"
)
DEFAULT_ADJUDICATION_CONSUMPTION = Path(
    "manifests/px062_gate2_2_20260728/adjudication_consumption.json"
)
ADJUDICATOR_PATH = "scripts/adjudicate_px062_gate2_2.py"
CHECKSUM_FIELDS = S3_CHECKSUM_FIELDS
LAUNCH_REGISTRATION_KEYS = {
    "schema_version",
    "experiment_id",
    "protocol_version",
    "registered_at_utc",
    "branch",
    "source_commit",
    "source_remote_refs",
    "region",
    "job_name",
    "initial_job_absence",
    "request_file",
    "request_sha256",
    "source_bundle",
    "frozen_sources",
    "frozen_evidence",
    "checksum_runtime",
    "fetch_operator_policy",
    "operator_access_preflight",
    "frozen_collection",
    "role_arn",
    "output_prefix",
    "one_look",
}
LAUNCH_RECEIPT_KEYS = {
    "schema_version",
    "experiment_id",
    "protocol_version",
    "launch_commit",
    "launch_remote_refs",
    "registration_path",
    "registration_sha256",
    "request_sha256",
    "launched_at_utc",
    "receipt_recorded_at_utc",
    "launch_mode",
    "training_job_name",
    "training_job_arn",
    "status_at_receipt",
    "secondary_status_at_receipt",
    "source_version_id",
    "source_sha256",
    "create_response",
    "interpretation",
}
FROZEN_EVIDENCE_CONTRACT = {
    "audit_1_predictions": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_1_predictions.jsonl"
    ),
    "audit_2_predictions": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_2_predictions.jsonl"
    ),
    "audit_1_run": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_1_run.json"
    ),
    "audit_2_run": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_2_run.json"
    ),
    "audit_evidence_manifest": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_evidence_manifest.json"
    ),
    "audit_protocol": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/LABEL_AUDIT_PROTOCOL_20260728.md"
    ),
    "audit_provisional_resolution": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/"
        "label_audit_provisional_resolution.json"
    ),
    "audit_resolution": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/label_audit_resolution.json"
    ),
    "preregistration": (
        "reports/coding_agent_skill_provenance/"
        "PX062_GATE2_2_CONTEXT_STRUCTURED_PREREG_20260728.md"
    ),
    "prelaunch_redesign_record": (
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/"
        "PRELAUNCH_REDESIGN_RECORD_20260728.md"
    ),
    "collector": "scripts/run_px062_gate2_2_models.py",
    "adjudicator": "scripts/adjudicate_px062_gate2_2.py",
    "audit_runner": "scripts/run_px062_gate2_2_blind_audit.py",
    "label_finalizer": "scripts/finalize_px062_gate2_2_labels.py",
    "label_verifier": "scripts/verify_px062_gate2_2_label_audits.py",
    "benchmark_builder": "scripts/build_px062_gate2_2_benchmark.py",
    "tokenizer_conformance_checker": (
        "scripts/check_px062_gate2_2_tokenizer_conformance.py"
    ),
    "tokenizer_conformance_manifest": (
        "manifests/px062_gate2_2_20260728/tokenizer_conformance.json"
    ),
    "collector_tests": "tests/test_px062_gate2_2_collector.py",
    "adjudicator_tests": "tests/test_px062_gate2_2_adjudicator.py",
    "blind_audit_tests": "tests/test_px062_gate2_2_blind_audit.py",
    "benchmark_tests": "tests/test_px062_gate2_2_benchmark.py",
    "tokenizer_conformance_tests": (
        "tests/test_px062_gate2_2_tokenizer_conformance.py"
    ),
    "bundle_tests": "tests/test_px062_gate2_2_bundle.py",
    "launch_tests": "tests/test_px062_gate2_2_launch.py",
    "fetch_tests": "tests/test_px062_gate2_2_fetch.py",
    "checksum_requirements": CHECKSUM_REQUIREMENTS_PATH,
    "operator_fetch_policy": OPERATOR_FETCH_POLICY_PATH,
}


def tracked_git_state(root: Path) -> Mapping[str, Any]:
    """Require tracked files clean while permitting untracked sealed evidence."""

    state = dict(git_state(root))
    status = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        ],
        text=True,
        encoding="utf-8",
    )
    state["clean"] = status == ""
    return state


def register_adjudication_authorization(
    *,
    root: Path,
    fetch_receipt_path: Path = DEFAULT_FETCH_RECEIPT,
    completion_path: Path = DEFAULT_COMPLETION_REGISTRATION,
    authorization_path: Path = DEFAULT_ADJUDICATION_AUTHORIZATION,
    blob_reader: GitBlobRead = git_blob,
    state_reader: GitStateRead = tracked_git_state,
    authorized_at: datetime | None = None,
) -> dict[str, Any]:
    """Register one canonical adjudication after outcome-blind sealed fetch."""

    root = root.resolve()
    fetch_receipt_path = repo_path(root, fetch_receipt_path)
    completion_path = repo_path(root, completion_path)
    authorization_path = repo_path(root, authorization_path)
    if fetch_receipt_path.relative_to(root).as_posix() != DEFAULT_FETCH_RECEIPT.as_posix():
        raise ValueError("fetch receipt is not at the canonical sealed path")
    if completion_path.relative_to(root).as_posix() != DEFAULT_COMPLETION_REGISTRATION.as_posix():
        raise ValueError("completion registration path drift")
    if authorization_path.relative_to(root).as_posix() != (
        DEFAULT_ADJUDICATION_AUTHORIZATION.as_posix()
    ):
        raise ValueError("adjudication authorization path drift")
    if authorization_path.exists():
        raise FileExistsError("adjudication authorization already exists")
    if not authorization_path.parent.is_dir():
        raise ValueError("adjudication authorization parent does not exist")

    evidence = validate_completion_evidence(
        root,
        completion_path,
        blob_reader=blob_reader,
        state_reader=state_reader,
    )
    receipt_raw, receipt = load_json(fetch_receipt_path)
    validate_fetch_receipt_against_completion(
        receipt, evidence["completion"], evidence["completion_raw"]
    )
    sealed_dir = fetch_receipt_path.parent
    sealed = receipt["sealed_files"]
    if set(sealed) != SEALED_PAYLOAD_FILES:
        raise ValueError("sealed payload inventory drift")
    for name, record in sealed.items():
        path = sealed_dir / name
        if not path.is_file() or record != {
            "bytes": path.stat().st_size,
            "sha256": digest_file(path),
        }:
            raise ValueError(f"sealed payload differs from fetch receipt: {name}")

    launch = evidence["launch"]
    completion = evidence["completion"]
    adjudicator = launch.get("frozen_evidence", {}).get("adjudicator")
    if not isinstance(adjudicator, dict) or adjudicator.get("path") != ADJUDICATOR_PATH:
        raise ValueError("registered adjudicator binding is missing")
    now = authorized_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("authorization timestamp must be timezone-aware")
    authorization = {
        "schema_version": "px062-gate2.2-adjudication-authorization-v1",
        "experiment_id": completion["experiment_id"],
        "protocol_version": completion["protocol_version"],
        "authorized_at_utc": now.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        "repository": dict(evidence["git_state"]),
        "fetch_receipt": {
            "path": fetch_receipt_path.relative_to(root).as_posix(),
            "sha256": sha256_bytes(receipt_raw),
        },
        "completion_registration": {
            "path": completion_path.relative_to(root).as_posix(),
            "sha256": sha256_bytes(evidence["completion_raw"]),
        },
        "launch_registration": dict(completion["launch_registration"]),
        "launch_receipt": dict(completion["launch_receipt"]),
        "request": dict(completion["request"]),
        "registered_fetcher": {
            **completion["fetcher"],
            "fetch_code_commit": completion["fetch_code_commit"],
        },
        "registered_adjudicator": dict(adjudicator),
        "job": dict(receipt["job"]),
        "source_artifact": dict(receipt["source_artifact"]),
        "output_artifact": dict(receipt["output_artifact"]),
        "sealed_files": dict(sealed),
        "canonical_result_path": DEFAULT_ADJUDICATION_RESULT.as_posix(),
        "consumption_marker_path": DEFAULT_ADJUDICATION_CONSUMPTION.as_posix(),
        "one_look": {
            "allowed_adjudications": 1,
            "alternative_result_paths_allowed": False,
            "claim_must_precede_outcome_read": True,
            "started_claim_is_never_recoverable": True,
        },
    }
    with authorization_path.open("xb") as handle:
        handle.write(canonical_json_bytes(authorization))
        handle.flush()
        os.fsync(handle.fileno())
    return authorization


def checksum_values(
    algorithms: list[str], head: Mapping[str, Any], label: str
) -> dict[str, str]:
    values: dict[str, str] = {}
    for algorithm in algorithms:
        field = CHECKSUM_FIELDS.get(algorithm)
        if field is None or not isinstance(head.get(field), str) or not head[field]:
            raise ValueError(f"{label} missing registered {algorithm} checksum")
        values[field] = str(head[field])
    if not values:
        raise ValueError(f"{label} has no checksum values")
    return values


def registered_artifact(
    *,
    bucket: str,
    key: str,
    row: Mapping[str, Any],
    head: Mapping[str, Any],
    sha256: str | None = None,
    metadata_sha256: str | None = None,
) -> dict[str, Any]:
    checks = {
        "VersionId": row["VersionId"],
        "ETag": row["ETag"],
        "ContentLength": row["Size"],
    }
    for field, expected in checks.items():
        if head.get(field) != expected:
            raise ValueError(f"artifact listing/head {field} mismatch")
    row_modified = parse_time(row["LastModified"], "artifact listed time")
    head_modified = parse_time(head.get("LastModified"), "artifact head time")
    if row_modified != head_modified:
        raise ValueError("artifact listing/head LastModified mismatch")
    checksum_contract = negotiate_head_checksums(row, head, "artifact")
    etag = parse_s3_etag(row["ETag"], "artifact")
    head_fingerprint = s3_head_fingerprint(head, "artifact")
    result = {
        "bucket": bucket,
        "key": key,
        "version_id": row["VersionId"],
        "etag": etag["value"],
        "etag_shape": etag["shape"],
        "multipart_part_count": etag["multipart_part_count"],
        "bytes": row["Size"],
        "last_modified_utc": row_modified.isoformat().replace("+00:00", "Z"),
        "checksum_algorithm": checksum_contract["checksum_algorithm"],
        "checksum_type": checksum_contract["checksum_type"],
        "checksums": checksum_contract["checksums"],
        "server_side_encryption": head.get("ServerSideEncryption"),
        "metadata": dict(head_fingerprint["Metadata"]),
        "version_fingerprint": version_fingerprint(row),
        "head_fingerprint": head_fingerprint,
        "object_attributes_fingerprint": None,
    }
    if sha256 is not None:
        result["sha256"] = sha256
    if metadata_sha256 is not None:
        result["metadata_sha256"] = metadata_sha256
    return result


def validate_launch_evidence(
    root: Path,
    launch_path: Path,
    receipt_path: Path,
    *,
    blob_reader: GitBlobRead,
    state_reader: GitStateRead,
) -> dict[str, Any]:
    launch_raw, launch = load_json(launch_path)
    receipt_raw, receipt = load_json(receipt_path)
    request_path = repo_path(root, Path(launch["request_file"]))
    request_raw, request = load_json(request_path)
    code_paths = [
        launch_path,
        receipt_path,
        request_path,
        repo_path(root, Path(REGISTRAR_PATH)),
        repo_path(root, Path(FETCHER_PATH)),
        repo_path(root, Path(FETCH_TEST_PATH)),
    ]
    state = validate_git_evidence(
        root, code_paths, blob_reader=blob_reader, state_reader=state_reader
    )
    if set(launch) != LAUNCH_REGISTRATION_KEYS or launch.get(
        "schema_version"
    ) != "px062-gate2.2-launch-registration-v1":
        raise ValueError("unexpected launch registration schema")
    if set(receipt) != LAUNCH_RECEIPT_KEYS or receipt.get(
        "schema_version"
    ) != "px062-gate2.2-launch-receipt-v1":
        raise ValueError("unexpected launch receipt schema")
    checksum_requirements_raw = blob_reader(
        root, launch["source_commit"], CHECKSUM_REQUIREMENTS_PATH
    )
    if launch.get("checksum_runtime") != checksum_runtime_record(
        checksum_requirements_raw
    ):
        raise ValueError("launch checksum-runtime preflight drift")
    operator_policy_raw = blob_reader(
        root, launch["source_commit"], OPERATOR_FETCH_POLICY_PATH
    )
    if launch.get("fetch_operator_policy") != operator_fetch_policy_record(
        operator_policy_raw, launch["source_bundle"]["bucket"]
    ):
        raise ValueError("launch operator fetch-policy drift")
    source_bundle = launch["source_bundle"]
    expected_operator_preflight = {
        "source_version_attributes": {
            "method": "GetObjectAttributes",
            "version_id": source_bundle["version_id"],
            "etag": source_bundle["etag"],
            "bytes": source_bundle["bytes"],
            "checksum_sha256_base64": source_bundle["checksum_sha256_base64"],
            "checksum_type": "FULL_OBJECT",
            "authorized": True,
        },
        "output_version_listing": {
            "method": "ListObjectVersions",
            "prefix": f"{PX062_GATE22_PREFIX}/output/{launch['job_name']}/",
            "authorized": True,
            "existing_versions": 0,
            "existing_delete_markers": 0,
        },
    }
    if launch.get("operator_access_preflight") != expected_operator_preflight:
        raise ValueError("launch operator access-preflight drift")
    frozen_evidence = launch["frozen_evidence"]
    if not isinstance(frozen_evidence, dict) or set(frozen_evidence) != set(
        FROZEN_EVIDENCE_CONTRACT
    ):
        raise ValueError("launch frozen-evidence inventory drift")
    bundle_files = launch["source_bundle"]["manifest"]["files"]
    for label, expected_path in FROZEN_EVIDENCE_CONTRACT.items():
        record = frozen_evidence[label]
        if not isinstance(record, dict) or set(record) != {
            "path",
            "sha256",
            "bytes",
            "included_in_collection_source_bundle",
        }:
            raise ValueError(f"launch frozen-evidence schema drift: {label}")
        raw = blob_reader(root, launch["source_commit"], expected_path)
        expected_inclusion = expected_path in bundle_files
        if (
            record["path"] != expected_path
            or record["sha256"] != sha256_bytes(raw)
            or record["bytes"] != len(raw)
            or record["included_in_collection_source_bundle"] is not expected_inclusion
        ):
            raise ValueError(f"launch frozen-evidence binding drift: {label}")
        if label != "collector" and expected_inclusion:
            raise ValueError(f"blinded protocol evidence leaked to source bundle: {label}")
    expected_absence = {
        "method": "DescribeTrainingJob",
        "job_name": launch["job_name"],
        "result": "ResourceNotFound",
        "authorized_initial_absence": True,
    }
    if launch.get("initial_job_absence") != expected_absence:
        raise ValueError("launch initial job-absence evidence drift")
    if (
        receipt["experiment_id"] != launch["experiment_id"]
        or receipt["protocol_version"] != launch["protocol_version"]
    ):
        raise ValueError("launch receipt experiment identity mismatch")
    if sha256_bytes(request_raw) != launch["request_sha256"]:
        raise ValueError("launch request hash mismatch")
    if receipt["registration_path"] != launch_path.relative_to(root).as_posix():
        raise ValueError("launch receipt registration path mismatch")
    if receipt["registration_sha256"] != sha256_bytes(launch_raw):
        raise ValueError("launch receipt registration hash mismatch")
    if receipt["request_sha256"] != sha256_bytes(request_raw):
        raise ValueError("launch receipt request hash mismatch")
    if receipt["training_job_name"] != launch["job_name"]:
        raise ValueError("launch receipt job name mismatch")
    if receipt["source_version_id"] != launch["source_bundle"]["version_id"]:
        raise ValueError("launch receipt source version mismatch")
    if receipt["source_sha256"] != launch["source_bundle"]["sha256"]:
        raise ValueError("launch receipt source hash mismatch")
    return {
        "launch": launch,
        "launch_raw": launch_raw,
        "receipt": receipt,
        "receipt_raw": receipt_raw,
        "request": request,
        "request_raw": request_raw,
        "request_path": request_path,
        "state": state,
    }


def register_completion(
    *,
    root: Path,
    profile: str,
    launch_path: Path,
    receipt_path: Path,
    completion_path: Path,
    aws_call: AwsCall = aws_json,
    blob_reader: GitBlobRead = git_blob,
    state_reader: GitStateRead = git_state,
    registered_at: datetime | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    launch_path = repo_path(root, launch_path)
    receipt_path = repo_path(root, receipt_path)
    completion_path = repo_path(root, completion_path)
    if completion_path.exists():
        raise FileExistsError(f"completion registration already exists: {completion_path}")
    if not completion_path.parent.is_dir():
        raise ValueError("completion registration parent does not exist")
    evidence = validate_launch_evidence(
        root,
        launch_path,
        receipt_path,
        blob_reader=blob_reader,
        state_reader=state_reader,
    )
    launch = evidence["launch"]
    receipt = evidence["receipt"]
    request = evidence["request"]
    state = evidence["state"]
    region = launch["region"]

    description = aws_call(
        profile,
        region,
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        launch["job_name"],
    )
    tags = aws_call(
        profile,
        region,
        "sagemaker",
        "list-tags",
        "--resource-arn",
        receipt["training_job_arn"],
    )
    lifecycle = validate_job(description, tags, request, launch, receipt)

    source_registered = launch["source_bundle"]
    source_row = single_version(
        list_versions(
            aws_call,
            profile,
            region,
            source_registered["bucket"],
            source_registered["key"],
        ),
        source_registered["key"],
        "source artifact",
    )
    source_expected_checks = {
        "VersionId": source_registered["version_id"],
        "ETag": f'"{source_registered["etag"]}"',
        "Size": source_registered["bytes"],
    }
    for field, expected in source_expected_checks.items():
        if source_row.get(field) != expected:
            raise ValueError(f"source artifact registration {field} drift")
    source_head = head_version(
        aws_call,
        profile,
        region,
        source_registered["bucket"],
        source_registered["key"],
        source_registered["version_id"],
    )
    source_artifact = registered_artifact(
        bucket=source_registered["bucket"],
        key=source_registered["key"],
        row=source_row,
        head=source_head,
        sha256=source_registered["sha256"],
        metadata_sha256=source_registered["sha256"],
    )
    validate_registered_artifact_contract(
        source_artifact, "source artifact", controlled_source=True
    )
    if source_artifact["checksums"].get("ChecksumSHA256") != source_registered[
        "checksum_sha256_base64"
    ]:
        raise ValueError("source artifact registered checksum drift")
    if source_head.get("Metadata", {}).get("sha256") != source_registered["sha256"]:
        raise ValueError("source artifact metadata hash drift")
    source_modified = compare_head(
        source_head,
        source_artifact,
        "source artifact",
        earliest=None,
        latest=lifecycle["creation"],
    )
    if source_modified >= lifecycle["creation"]:
        raise ValueError("source artifact was not frozen before job creation")

    output_bucket, output_key = parse_s3(lifecycle["artifact_uri"])
    output_row = single_version(
        list_versions(aws_call, profile, region, output_bucket, output_key),
        output_key,
        "output artifact",
    )
    output_head = head_version(
        aws_call,
        profile,
        region,
        output_bucket,
        output_key,
        output_row["VersionId"],
    )
    output_artifact = registered_artifact(
        bucket=output_bucket,
        key=output_key,
        row=output_row,
        head=output_head,
    )
    if output_artifact["checksum_type"] == "COMPOSITE":
        output_artifact["object_attributes_fingerprint"] = get_object_attributes(
            aws_call,
            profile,
            region,
            output_artifact,
            "output artifact",
        )
    validate_registered_artifact_contract(
        output_artifact, "output artifact", controlled_source=False
    )
    compare_head(
        output_head,
        output_artifact,
        "output artifact",
        earliest=lifecycle["start"],
        latest=lifecycle["end"],
    )

    answer_contract = source_registered["manifest"]["answer_key_blinding"]
    if answer_contract.get("included_in_archive") is not False:
        raise ValueError("answer key was not blinded from source archive")
    answer_raw = blob_reader(root, launch["source_commit"], ANSWER_KEY_PATH)
    if len(answer_raw) != answer_contract["registered_bytes"] or sha256_bytes(
        answer_raw
    ) != answer_contract["registered_sha256"]:
        raise ValueError("source-commit answer key differs from source registration")
    if launch["frozen_sources"]["answer_key_sha256"] != sha256_bytes(answer_raw):
        raise ValueError("launch frozen answer-key hash drift")

    now = registered_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("completion registration time must be timezone-aware")
    if now.astimezone(timezone.utc) < lifecycle["end"]:
        raise ValueError("completion registration predates completed job")
    code_commit = state["head"]
    code_records = {}
    for label, path in (
        ("fetcher", FETCHER_PATH),
        ("fetch_tests", FETCH_TEST_PATH),
        ("registrar", REGISTRAR_PATH),
    ):
        raw = repo_path(root, Path(path)).read_bytes()
        if blob_reader(root, code_commit, path) != raw:
            raise ValueError(f"{label} differs from completion code commit")
        code_records[label] = {"path": path, "sha256": sha256_bytes(raw)}
    completion = {
        "schema_version": "px062-gate2.2-completion-registration-v1",
        "experiment_id": launch["experiment_id"],
        "protocol_version": launch["protocol_version"],
        "registered_at_utc": now.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        "purpose": (
            "Authenticate completed cloud metadata and freeze immutable artifact "
            "versions before outcome-blind download and before adjudication."
        ),
        "scientific_outputs_downloaded": False,
        "scientific_outputs_inspected": False,
        "fetch_code_commit": code_commit,
        "fetch_code_branch": state["branch"],
        "fetch_code_remote_refs": state["remote_refs"],
        "launch_registration": {
            "path": launch_path.relative_to(root).as_posix(),
            "sha256": sha256_bytes(evidence["launch_raw"]),
        },
        "launch_receipt": {
            "path": receipt_path.relative_to(root).as_posix(),
            "sha256": sha256_bytes(evidence["receipt_raw"]),
        },
        "request": {
            "path": evidence["request_path"].relative_to(root).as_posix(),
            "sha256": sha256_bytes(evidence["request_raw"]),
        },
        "job": {
            "name": description["TrainingJobName"],
            "arn": description["TrainingJobArn"],
            "status": description["TrainingJobStatus"],
            "secondary_status": description["SecondaryStatus"],
            "artifact_uri": lifecycle["artifact_uri"],
            "creation_time_utc": lifecycle["creation"].isoformat().replace(
                "+00:00", "Z"
            ),
            "start_time_utc": lifecycle["start"].isoformat().replace(
                "+00:00", "Z"
            ),
            "end_time_utc": lifecycle["end"].isoformat().replace("+00:00", "Z"),
            "description_sha256": sha256_bytes(canonical_json_bytes(description)),
            "tags_sha256": sha256_bytes(
                canonical_json_bytes({"Tags": canonical_tags(tags["Tags"])})
            ),
        },
        "source_artifact": source_artifact,
        "output_artifact": output_artifact,
        "answer_key": {
            "path": ANSWER_KEY_PATH,
            "source_commit": launch["source_commit"],
            "bytes": len(answer_raw),
            "sha256": sha256_bytes(answer_raw),
            "included_in_cloud_source": False,
        },
        "fetcher": code_records["fetcher"],
        "fetch_tests": code_records["fetch_tests"],
        "registrar": code_records["registrar"],
        "sealed_destination": DEFAULT_DESTINATION.as_posix(),
    }
    with completion_path.open("xb") as handle:
        handle.write(canonical_json_bytes(completion))
    return completion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Metadata-only PX-062 Gate 2.2 completion registration"
    )
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument(
        "--launch-registration", type=Path, default=DEFAULT_LAUNCH_REGISTRATION
    )
    parser.add_argument("--launch-receipt", type=Path, default=DEFAULT_LAUNCH_RECEIPT)
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_COMPLETION_REGISTRATION
    )
    parser.add_argument(
        "--fetch-receipt",
        type=Path,
        help="Create the exclusive adjudication authorization from this sealed receipt",
    )
    parser.add_argument(
        "--authorization-output",
        type=Path,
        default=DEFAULT_ADJUDICATION_AUTHORIZATION,
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.fetch_receipt is not None:
        authorization = register_adjudication_authorization(
            root=root,
            fetch_receipt_path=args.fetch_receipt,
            completion_path=args.output,
            authorization_path=args.authorization_output,
        )
        print(
            json.dumps(
                {
                    "authorization": args.authorization_output.as_posix(),
                    "fetch_receipt_sha256": authorization["fetch_receipt"]["sha256"],
                    "status": "REGISTERED_NOT_ADJUDICATED",
                },
                indent=2,
            )
        )
        return
    completion = register_completion(
        root=root,
        profile=args.profile,
        launch_path=args.launch_registration,
        receipt_path=args.launch_receipt,
        completion_path=args.output,
    )
    print(
        json.dumps(
            {
                "job_name": completion["job"]["name"],
                "output_bytes": completion["output_artifact"]["bytes"],
                "output_version_id": completion["output_artifact"]["version_id"],
                "scientific_outputs_downloaded": completion[
                    "scientific_outputs_downloaded"
                ],
                "scientific_outputs_inspected": completion[
                    "scientific_outputs_inspected"
                ],
                "status": completion["job"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
