#!/usr/bin/env python
"""Independent adjudicator for PX-062 Gate 2.2.

The collector writes one JSON object per ``(model_id, task_id)``.  Each trace
contains the task-local ``option_map`` and five nested arms named by the frozen
configuration:

``A_open_text``
    ``generated``, canonical ``messages`` and hash, exact ``raw_response`` and
    hash, generated token IDs, ``parser_status``, ``parsed_candidate``, and
    ``selection``.

``B_structured_names`` / ``C_structured_catalog``
    A generated structured arm: trigger/generation flags, canonical messages
    and hash, response and hash, token IDs, decoder-escape flag, frozen choice
    set hash, local ``choice_id``, canonical ``selection``, canonical-decision
    JSON, and a null ``source_initial_sha256``.

``D_contextual_repair`` / ``E_decontextualized_repair``
    The same structured schema.  When A is invalid, both arms must be generated
    and bind ``source_initial_sha256`` to the exact A response bytes.  Otherwise
    they must be non-generated pass-through decisions with null message/response
    fields, empty token IDs, and A's selection.

The task JSONL is answer-key blind.  Ground truth comes from a separately
sealed answer-key JSONL.  The adjudicator reconstructs every message list from
the task, registry catalog, option map, and frozen templates; it does not import
collector parsing or prompt code.

Frozen statistical conventions
------------------------------
* 1,032 tasks: 516 registered-skill labels and 516 NONE labels.
* One trace per model/task (2,064 total), with all five arms nested.
* Wilson intervals are ordinary two-sided 95% score intervals using
  z=1.959963984540054.  Inclusive comparisons are used at every boundary.
* Direct arm C must have point accuracy >= .75 and Wilson lower bound >= .70
  over 1,032 tasks; registered-target recall lower bound >= .65 over 516 tasks;
  and wrong-existing selection Wilson upper bound <= .10 over 516 NONE tasks.
* Each model needs >=200 A-invalid events whose answer key requires a registered
  skill.  On that frozen registered-target subset, D recovery accuracy must be
  >=.60 and D-E paired accuracy gain must be >=.15.  Metrics across all
  A-invalid events remain diagnostic and can never substitute for this cohort.
* D wrong-existing selection on the 516 NONE tasks must have Wilson upper bound
  <=.10.
* The D-vs-E directional tests are one-sided exact McNemar tests.  The two
  frozen model p-values form one Holm family; zero discordance has p=1.  This
  is required secondary context-ablation evidence, but its failure does not
  erase otherwise valid absolute C/D efficacy.
* Any integrity defect is INVALID.  A directly evaluable semantic failure is
  CROSS_MODEL_NO_GO.  If direct gates and D's always-evaluable NONE-safety gate pass, no
  powered registered-target repair comparison fails, and at least one model
  has <200 A-invalid registered-target events, determination is NOT_EVALUABLE
  and classification is
  BOUNDED_SELECTOR_PASS.  A primary PASS and BOUNDED_EFFICACY_PASS require all
  absolute efficacy gates for both models.  D-vs-E is reported
  separately as CONTEXT_MECHANISM_SUPPORTED or its negative/not-evaluable form.

Closed-set output validity is an implementation property, never an efficacy
endpoint.  Every registered-but-wrong choice and unnecessary NONE is scored as
incorrect.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import tarfile
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

try:
    from scripts.fetch_px062_gate2_2_results import (
        OUTPUT_FILES,
        SEALED_PAYLOAD_FILES,
        SOURCE_GIT_PATHS,
        git_blob as registered_git_blob,
        git_state as registered_git_state,
        validate_completion_evidence,
        validate_checksum_verification_record,
        validate_fetch_receipt_against_completion,
        verify_archive_checksum_contract,
    )
    from scripts.register_px062_gate2_2_fetch import (
        DEFAULT_ADJUDICATION_AUTHORIZATION,
        DEFAULT_ADJUDICATION_CONSUMPTION,
        DEFAULT_ADJUDICATION_RESULT,
        FROZEN_EVIDENCE_CONTRACT,
        LAUNCH_REGISTRATION_KEYS,
        validate_launch_evidence,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from fetch_px062_gate2_2_results import (  # type: ignore[no-redef]
        OUTPUT_FILES,
        SEALED_PAYLOAD_FILES,
        SOURCE_GIT_PATHS,
        git_blob as registered_git_blob,
        git_state as registered_git_state,
        validate_completion_evidence,
        validate_checksum_verification_record,
        validate_fetch_receipt_against_completion,
        verify_archive_checksum_contract,
    )
    from register_px062_gate2_2_fetch import (  # type: ignore[no-redef]
        DEFAULT_ADJUDICATION_AUTHORIZATION,
        DEFAULT_ADJUDICATION_CONSUMPTION,
        DEFAULT_ADJUDICATION_RESULT,
        FROZEN_EVIDENCE_CONTRACT,
        LAUNCH_REGISTRATION_KEYS,
        validate_launch_evidence,
    )


Z_95 = 1.959963984540054
EXPECTED_TASKS = 1032
EXPECTED_TRACES = 2064
EXPECTED_MODELS = 2
FROZEN_MODEL_REVISIONS = {
    "Qwen/Qwen2.5-7B-Instruct": "a09a35458c702b33eeacc393d103063234e8bc28",
    "mistralai/Mistral-7B-Instruct-v0.3": (
        "c170c708c41dac9275d15a8fff4eca08d52bab71"
    ),
}
FROZEN_CONFIG_CONTRACT_SHA256 = (
    "8dcf3f8c939c8dcabaf90f4b1a8dd745c032274ded85a2ae4444424a3f79aeed"
)
EXPECTED_REGISTRY_NAMES = 43
EXPECTED_REAL_LABELS = 516
EXPECTED_NONE_LABELS = 516
EXPECTED_TYPE_COUNTS = sorted((344, 344, 172, 172))
FROZEN_DEPENDENCIES = {
    "torch": "2.3.0",
    "transformers": "4.46.3",
    "accelerate": "1.1.1",
    "jinja2": "3.1.4",
    "numpy": "1.26.4",
    "protobuf": "5.28.3",
    "safetensors": "0.4.5",
    "sentencepiece": "0.2.0",
}
ADJUDICATOR_PATH = "scripts/adjudicate_px062_gate2_2.py"
DEFAULT_REGISTRATION = Path(
    "manifests/px062_gate2_2_20260728/confirmatory_registration.json"
)
ADJUDICATION_AUTHORIZATION_KEYS = {
    "schema_version",
    "experiment_id",
    "protocol_version",
    "authorized_at_utc",
    "repository",
    "fetch_receipt",
    "completion_registration",
    "launch_registration",
    "launch_receipt",
    "request",
    "registered_fetcher",
    "registered_adjudicator",
    "job",
    "source_artifact",
    "output_artifact",
    "sealed_files",
    "canonical_result_path",
    "consumption_marker_path",
    "one_look",
}
ONE_LOOK_MARKER_KEYS = {
    "schema_version",
    "state",
    "authorization_path",
    "authorization_sha256",
    "canonical_result_path",
    "claim_id",
    "claimed_at_utc",
    "recovery_count",
    "outcome_read_started_at_utc",
    "completed_at_utc",
    "result_sha256",
    "result_bytes",
}
GitBlobReader = Callable[[Path, str, str], bytes]
GitStateReader = Callable[[Path], Mapping[str, Any]]
TOKENIZER_ARCHIVE_MAX_BYTES = 64 * 1024 * 1024
TOKENIZER_UNCOMPRESSED_MAX_BYTES = 96 * 1024 * 1024
EXPECTED_ARMS = (
    "A_open_text",
    "B_structured_names",
    "C_structured_catalog",
    "D_contextual_repair",
    "E_decontextualized_repair",
)
FROZEN_GATES: dict[str, float | int] = {
    "minimum_A_invalid_registered_events_per_model": 200,
    "C_overall_accuracy_min": 0.75,
    "C_overall_wilson_lower_min": 0.70,
    "C_real_target_wilson_lower_min": 0.65,
    "C_none_wrong_existing_wilson_upper_max": 0.10,
    "D_registered_recovery_accuracy_min": 0.60,
    "D_minus_E_registered_paired_accuracy_gain_min": 0.15,
    "D_none_wrong_existing_wilson_upper_max": 0.10,
    "paired_test_one_sided_alpha": 0.05,
    "trace_completeness_required": 1.0,
    "constrained_decoder_escapes_max": 0,
}

A_FIELDS = {
    "generated",
    "messages",
    "messages_sha256",
    "raw_response",
    "raw_response_utf8_base64",
    "raw_response_bytes",
    "raw_response_sha256",
    "generated_token_ids",
    "tokenizer_reconstruction_verified",
    "parser_status",
    "parsed_candidate",
    "selection",
}
STRUCTURED_FIELDS = {
    "triggered",
    "generated",
    "messages",
    "messages_sha256",
    "raw_response",
    "raw_response_utf8_base64",
    "raw_response_bytes",
    "raw_response_sha256",
    "generated_token_ids",
    "tokenizer_reconstruction_verified",
    "decoder_escape",
    "choice_set_sha256",
    "choice_id",
    "selection",
    "canonical_decision",
    "source_initial_sha256",
}
TRACE_FIELDS = {
    "experiment_id",
    "protocol_version",
    "task_id",
    "model_id",
    "model_revision",
    "tokenizer_artifact_key",
    "option_map",
    "option_map_sha256",
    "arms",
}


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid {label}: {error}") from error


def read_json(path: Path) -> Any:
    return strict_json_bytes(path.read_bytes(), path.as_posix())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                value = strict_json_bytes(
                    line.encode("utf-8"), f"{path.as_posix()} line {line_number}"
                )
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL row is not an object: {path}:{line_number}")
                rows.append(value)
        return rows


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def text_sha256(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _repo_path(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {candidate}") from exc
    return path


def _atomic_json_replace(path: Path, payload: dict[str, Any]) -> None:
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_marker(marker: Any) -> dict[str, Any]:
    if not isinstance(marker, dict) or set(marker) != ONE_LOOK_MARKER_KEYS:
        raise ValueError("one-look consumption marker schema drift")
    if marker.get("schema_version") != "px062-gate2.2-one-look-consumption-v1":
        raise ValueError("one-look consumption marker version drift")
    return marker


def acquire_one_look_claim(
    *,
    root: Path,
    authorization_path: Path,
    authorization: dict[str, Any],
    requested_output: Path,
    recover_pre_outcome: bool = False,
    claimed_at_utc: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Atomically claim the sole run before any scientific outcome is read."""

    root = root.resolve()
    authorization_path = _repo_path(root, authorization_path)
    expected_output = _repo_path(root, Path(authorization["canonical_result_path"]))
    requested_output = _repo_path(root, requested_output)
    if requested_output != expected_output:
        raise ValueError("alternative adjudication result paths are forbidden")
    marker_path = _repo_path(root, Path(authorization["consumption_marker_path"]))
    if marker_path.relative_to(root).as_posix() != DEFAULT_ADJUDICATION_CONSUMPTION.as_posix():
        raise ValueError("one-look consumption marker path drift")
    if requested_output.exists():
        raise FileExistsError("canonical adjudication result already exists")
    authorization_sha256 = sha256_file(authorization_path)
    now = claimed_at_utc or _utc_now()
    base = {
        "schema_version": "px062-gate2.2-one-look-consumption-v1",
        "state": "CLAIMED_PRE_OUTCOME",
        "authorization_path": authorization_path.relative_to(root).as_posix(),
        "authorization_sha256": authorization_sha256,
        "canonical_result_path": requested_output.relative_to(root).as_posix(),
        "claim_id": uuid.uuid4().hex,
        "claimed_at_utc": now,
        "recovery_count": 0,
        "outcome_read_started_at_utc": None,
        "completed_at_utc": None,
        "result_sha256": None,
        "result_bytes": None,
    }
    try:
        with marker_path.open("xb") as handle:
            handle.write(
                (
                    json.dumps(
                        base,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
            )
            handle.flush()
            os.fsync(handle.fileno())
        return marker_path, base
    except FileExistsError:
        existing = _validate_marker(read_json(marker_path))
        if not recover_pre_outcome:
            raise FileExistsError("one-look adjudication was already claimed")
        if existing.get("state") != "CLAIMED_PRE_OUTCOME":
            raise ValueError("started or completed one-look claim is not recoverable")
        expected_bindings = {
            "authorization_path": base["authorization_path"],
            "authorization_sha256": base["authorization_sha256"],
            "canonical_result_path": base["canonical_result_path"],
        }
        if any(existing.get(key) != value for key, value in expected_bindings.items()):
            raise ValueError("pre-outcome claim binding drift")
        existing["recovery_count"] += 1
        existing["claimed_at_utc"] = now
        _atomic_json_replace(marker_path, existing)
        return marker_path, existing


def resolve_adjudication_paths(
    *,
    root: Path,
    authorization: Mapping[str, Any],
    requested_output: Path | None,
    supplied_fetch_receipt: Path,
    supplied_inputs: Mapping[str, Path],
) -> tuple[Path, Path, dict[str, Path]]:
    """Validate all CLI path identities without opening outcome-bearing files."""

    root = root.resolve()
    canonical_output = _repo_path(
        root, Path(str(authorization["canonical_result_path"]))
    )
    output = (
        canonical_output
        if requested_output is None
        else _repo_path(root, requested_output)
    )
    if output != canonical_output:
        raise ValueError("alternative adjudication result paths are forbidden")
    receipt_path = _repo_path(
        root, Path(str(authorization["fetch_receipt"]["path"]))
    )
    if _repo_path(root, supplied_fetch_receipt) != receipt_path:
        raise ValueError("fetch receipt path differs from adjudication authorization")
    sealed_dir = receipt_path.parent
    inputs: dict[str, Path] = {}
    for name in SEALED_PAYLOAD_FILES:
        expected = (sealed_dir / name).resolve()
        supplied = supplied_inputs.get(name)
        if supplied is not None and supplied.resolve() != expected:
            raise ValueError(f"adjudication input is not the canonical sealed file: {name}")
        inputs[name] = expected
    return output, receipt_path, inputs


def mark_one_look_outcome_read_started(
    marker_path: Path,
    claim: dict[str, Any],
    *,
    started_at_utc: str | None = None,
) -> dict[str, Any]:
    """Cross the irreversible one-look boundary immediately before outcome read."""

    existing = _validate_marker(read_json(marker_path))
    if (
        existing.get("state") != "CLAIMED_PRE_OUTCOME"
        or existing.get("claim_id") != claim.get("claim_id")
        or existing.get("authorization_sha256") != claim.get("authorization_sha256")
    ):
        raise ValueError("one-look claim changed before outcome-read boundary")
    # ``os.replace`` alone is not a compare-and-swap: two explicit recovery
    # processes could otherwise observe CLAIMED_PRE_OUTCOME concurrently and
    # both cross the boundary.  This exclusive, never-reused boundary token is
    # fail-closed.  A crash after its creation can make the look unavailable,
    # but can never authorize a second scientific look.
    boundary_path = marker_path.with_name(f"{marker_path.name}.outcome-read.lock")
    boundary = {
        "schema_version": "px062-gate2.2-outcome-read-boundary-v1",
        "claim_id": claim.get("claim_id"),
        "authorization_sha256": claim.get("authorization_sha256"),
        "created_at_utc": started_at_utc or _utc_now(),
    }
    with boundary_path.open("xb") as handle:
        handle.write(
            (
                json.dumps(
                    boundary,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        )
        handle.flush()
        os.fsync(handle.fileno())
    existing = _validate_marker(read_json(marker_path))
    if (
        existing.get("state") != "CLAIMED_PRE_OUTCOME"
        or existing.get("claim_id") != claim.get("claim_id")
        or existing.get("authorization_sha256") != claim.get("authorization_sha256")
    ):
        raise ValueError("one-look claim raced at outcome-read boundary")
    existing["state"] = "OUTCOME_READ_STARTED"
    existing["outcome_read_started_at_utc"] = boundary["created_at_utc"]
    _atomic_json_replace(marker_path, existing)
    return existing


def complete_one_look_claim(
    marker_path: Path,
    claim: dict[str, Any],
    result_path: Path,
    *,
    completed_at_utc: str | None = None,
) -> dict[str, Any]:
    existing = _validate_marker(read_json(marker_path))
    if (
        existing.get("state") != "OUTCOME_READ_STARTED"
        or existing.get("claim_id") != claim.get("claim_id")
    ):
        raise ValueError("one-look marker is not in the started state")
    if not result_path.is_file():
        raise ValueError("canonical adjudication result is missing")
    existing["state"] = "COMPLETED"
    existing["completed_at_utc"] = completed_at_utc or _utc_now()
    existing["result_sha256"] = sha256_file(result_path)
    existing["result_bytes"] = result_path.stat().st_size
    _atomic_json_replace(marker_path, existing)
    return existing


def _registered_state_for_selected_paths(root: Path) -> Mapping[str, Any]:
    state = dict(registered_git_state(root))
    # Outcome files are expected to be untracked. Every trusted code/evidence
    # path is independently compared with a pushed Git blob below.
    state["clean"] = True
    return state


def verify_committed_adjudication_authorization(
    root: Path,
    authorization_path: Path,
    *,
    blob_reader: GitBlobReader = registered_git_blob,
    state_reader: GitStateReader = registered_git_state,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    authorization_path = _repo_path(root, authorization_path)
    if authorization_path.relative_to(root).as_posix() != (
        DEFAULT_ADJUDICATION_AUTHORIZATION.as_posix()
    ):
        raise ValueError("adjudication authorization path drift")
    raw = authorization_path.read_bytes()
    authorization = strict_json_bytes(raw, "adjudication authorization")
    if not isinstance(authorization, dict) or set(authorization) != (
        ADJUDICATION_AUTHORIZATION_KEYS
    ):
        raise ValueError("adjudication authorization schema drift")
    if authorization.get("schema_version") != (
        "px062-gate2.2-adjudication-authorization-v1"
    ):
        raise ValueError("adjudication authorization version drift")
    if authorization.get("one_look") != {
        "allowed_adjudications": 1,
        "alternative_result_paths_allowed": False,
        "claim_must_precede_outcome_read": True,
        "started_claim_is_never_recoverable": True,
    }:
        raise ValueError("adjudication authorization one-look policy drift")
    state = dict(state_reader(root))
    head = str(state.get("head", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not state.get("remote_refs"):
        raise ValueError("adjudication authorization is not on a pushed commit")
    relative = authorization_path.relative_to(root).as_posix()
    if blob_reader(root, head, relative) != raw:
        raise ValueError("adjudication authorization differs from pushed HEAD")
    return authorization, {
        "authorization_path": relative,
        "authorization_sha256": sha256_bytes(raw),
        "authorization_commit": head,
        "authorization_remote_refs": list(state["remote_refs"]),
        "verified_before_outcome_read": True,
    }


def verify_registered_adjudicator(
    root: Path, registration_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the preregistered one-look adjudicator before reading outcomes."""

    registration = read_json(registration_path)
    if not isinstance(registration, dict) or registration.get(
        "schema_version"
    ) != "px062-gate2.2-launch-registration-v1":
        raise ValueError("unexpected launch registration schema")
    evidence = registration.get("frozen_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("launch registration has no frozen evidence bindings")
    record = evidence.get("adjudicator")
    if (
        not isinstance(record, dict)
        or set(record)
        != {
            "path",
            "sha256",
            "bytes",
            "included_in_collection_source_bundle",
        }
        or record.get("path") != ADJUDICATOR_PATH
        or record.get("included_in_collection_source_bundle") is not False
    ):
        raise ValueError("launch registration adjudicator binding is missing")
    current = Path(__file__).resolve()
    expected = (root / ADJUDICATOR_PATH).resolve()
    if current != expected:
        raise ValueError("running adjudicator is outside the registered repository path")
    observed = sha256_file(current)
    if observed != record.get("sha256") or current.stat().st_size != record.get("bytes"):
        raise ValueError("running adjudicator hash differs from preregistration")
    return registration, {
        "registration_path": registration_path.relative_to(root).as_posix(),
        "registration_sha256": sha256_file(registration_path),
        "adjudicator_path": ADJUDICATOR_PATH,
        "adjudicator_sha256": observed,
        "verified_before_outcome_read": True,
    }


def load_frozen_tokenizers(
    archive_path: Path,
    destination: Path,
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Authenticate and load the collector-emitted tokenizer artifact bundle."""

    if archive_path.stat().st_size > TOKENIZER_ARCHIVE_MAX_BYTES:
        raise ValueError("tokenizer archive exceeds frozen size limit")
    with tarfile.open(archive_path, "r:gz") as handle:
        members = handle.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError("tokenizer archive contains duplicate member names")
        total = 0
        raw: dict[str, bytes] = {}
        for member in members:
            path = Path(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in member.name
            ):
                raise ValueError(f"unsafe tokenizer archive member: {member.name}")
            total += member.size
            if total > TOKENIZER_UNCOMPRESSED_MAX_BYTES:
                raise ValueError("tokenizer archive exceeds uncompressed size limit")
            stream = handle.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read tokenizer member: {member.name}")
            payload = stream.read(member.size + 1)
            if len(payload) != member.size:
                raise ValueError(f"truncated tokenizer member: {member.name}")
            raw[member.name] = payload
    manifest_raw = raw.get("tokenizer_manifest.json")
    if manifest_raw is None:
        raise ValueError("tokenizer archive manifest is missing")
    manifest = strict_json_bytes(manifest_raw, "tokenizer artifact manifest")
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "decode_contract",
        "models",
    }:
        raise ValueError("tokenizer artifact manifest schema drift")
    if manifest["schema_version"] != "px062-gate2.2-tokenizer-artifacts-v1":
        raise ValueError("tokenizer artifact manifest version drift")
    if manifest["decode_contract"] != {
        "skip_special_tokens": True,
        "clean_up_tokenization_spaces": False,
        "completion_token_ids_include_special_tokens": True,
        "empty_generated_token_ids_allowed": False,
    }:
        raise ValueError("tokenizer decode contract drift")
    records = manifest.get("models")
    if not isinstance(records, dict) or set(records) != set(config.get("models", [])):
        raise ValueError("tokenizer manifest models differ from config")
    expected_members = {"tokenizer_manifest.json"}
    for model_id, record in records.items():
        if not isinstance(record, dict) or set(record) != {
            "artifact_key",
            "model_id",
            "revision",
            "tokenizer_class",
            "verification_tokenizer_class",
            "eos_token_id",
            "files",
        } or record.get("model_id") != model_id:
            raise ValueError(f"invalid tokenizer record: {model_id}")
        if record.get("revision") != config["model_revisions"].get(model_id):
            raise ValueError(f"tokenizer revision drift: {model_id}")
        key = record.get("artifact_key")
        files = record.get("files")
        if not isinstance(key, str) or not key or not isinstance(files, dict) or not files:
            raise ValueError(f"tokenizer file manifest is invalid: {model_id}")
        expected_key = "tokenizer-" + sha256_bytes(
            f"{model_id}@{record['revision']}".encode("utf-8")
        )[:16]
        if key != expected_key:
            raise ValueError(f"tokenizer artifact key drift: {model_id}")
        for relative, file_record in files.items():
            if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise ValueError(f"unsafe tokenizer file path: {relative}")
            member_name = f"tokenizers/{key}/{relative}"
            expected_members.add(member_name)
            payload = raw.get(member_name)
            if payload is None or not isinstance(file_record, dict):
                raise ValueError(f"tokenizer member is missing: {member_name}")
            if file_record != {
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
            }:
                raise ValueError(f"tokenizer member hash/size mismatch: {member_name}")
            target = destination / member_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    if set(raw) != expected_members:
        raise ValueError("tokenizer archive contains unregistered members")

    from transformers import AutoTokenizer

    verifiers: dict[str, Any] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for model_id, record in records.items():
        tokenizer_dir = destination / "tokenizers" / record["artifact_key"]
        verifier = AutoTokenizer.from_pretrained(
            tokenizer_dir, local_files_only=True
        )
        if (
            type(verifier).__name__ != record["verification_tokenizer_class"]
            or verifier.eos_token_id != record["eos_token_id"]
        ):
            raise ValueError(f"reloaded tokenizer identity drift: {model_id}")
        verifiers[model_id] = verifier
        metadata[model_id] = record
    archive_record = {
        "path": archive_path.name,
        "sha256": sha256_file(archive_path),
        "bytes": archive_path.stat().st_size,
        "manifest_sha256": sha256_bytes(manifest_raw),
    }
    return verifiers, metadata, archive_record


def verify_sealed_evidence(
    receipt_path: Path, inputs: dict[str, Path]
) -> dict[str, Any]:
    """Bind every adjudication input to the outcome-blind fetch receipt."""

    if receipt_path.name != "completion_fetch_receipt.json":
        raise ValueError("fetch receipt filename drift")
    receipt = read_json(receipt_path)
    if not isinstance(receipt, dict) or receipt.get(
        "schema_version"
    ) != "px062-gate2.2-fetch-receipt-v1":
        raise ValueError("unexpected fetch receipt schema")
    if (
        receipt.get("adjudication_run") is not False
        or receipt.get("model_trace_structure_validated") is not True
        or receipt.get("trace_summary_reconciled") is not True
    ):
        raise ValueError("fetch receipt is not an unused structurally validated seal")
    sealed = receipt.get("sealed_files")
    if not isinstance(sealed, dict):
        raise ValueError("fetch receipt sealed-file inventory is missing")
    verified: dict[str, Any] = {}
    for expected_name, path in inputs.items():
        if path.name != expected_name:
            raise ValueError(f"adjudication input filename drift: {expected_name}")
        record = sealed.get(expected_name)
        if not isinstance(record, dict) or record != {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }:
            raise ValueError(f"adjudication input differs from fetch seal: {expected_name}")
        verified[expected_name] = record
    return {
        "fetch_receipt_path": receipt_path.as_posix(),
        "fetch_receipt_sha256": sha256_file(receipt_path),
        "sealed_inputs": verified,
        "verified_before_outcome_read": True,
    }


def _tar_records(path: Path, expected_names: set[str]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with tarfile.open(path, "r:gz") as handle:
        members = handle.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or set(names) != expected_names:
            raise ValueError(f"authenticated archive member inventory drift: {path.name}")
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts or "\\" in member.name:
                raise ValueError(f"unsafe authenticated archive member: {member.name}")
            if member.isdir():
                if member.size != 0 or member.linkname:
                    raise ValueError(f"invalid archive directory: {member.name}")
                records[member.name] = {"bytes": 0, "sha256": sha256_bytes(b"")}
                continue
            if not member.isfile() or member.issym() or member.islnk() or member.linkname:
                raise ValueError(f"nonregular authenticated archive member: {member.name}")
            stream = handle.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read authenticated archive member: {member.name}")
            digest = hashlib.sha256()
            observed = 0
            while observed < member.size:
                block = stream.read(min(1024 * 1024, member.size - observed))
                if not block:
                    break
                digest.update(block)
                observed += len(block)
            if observed != member.size or stream.read(1):
                raise ValueError(f"truncated authenticated archive member: {member.name}")
            records[member.name] = {
                "bytes": observed,
                "sha256": digest.hexdigest(),
            }
    return records


def verify_registered_cloud_archives(
    *,
    launch: Mapping[str, Any],
    receipt: Mapping[str, Any],
    inputs: Mapping[str, Path],
) -> dict[str, Any]:
    source_archive = inputs["source_artifact.tar.gz"]
    output_archive = inputs["output_artifact.tar.gz"]
    for name, archive, artifact in (
        ("source_artifact.tar.gz", source_archive, receipt["source_artifact"]),
        ("output_artifact.tar.gz", output_archive, receipt["output_artifact"]),
    ):
        if archive.stat().st_size != artifact["bytes"] or sha256_file(
            archive
        ) != artifact["sha256"]:
            raise ValueError(f"retained archive differs from AWS-bound receipt: {name}")
        validate_checksum_verification_record(
            artifact.get("checksum_verification"), artifact, name
        )
        if verify_archive_checksum_contract(archive, artifact, name) != artifact.get(
            "checksum_verification"
        ):
            raise ValueError(f"retained archive checksum proof drift: {name}")

    source_manifest = launch["source_bundle"]["manifest"]
    source_files = source_manifest["files"]
    source_records = _tar_records(
        source_archive, {*source_files, "bundle_manifest.json"}
    )
    for member_name, expected in source_files.items():
        if source_records[member_name] != expected:
            raise ValueError(f"registered source archive member drift: {member_name}")
    source_local_map = {
        "configs/px062_skill_selection_gate2_2_v1_0_20260728.json": (
            "frozen_config.json"
        ),
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl": (
            "tasks.jsonl"
        ),
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json": (
            "registry_catalog.json"
        ),
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs/benchmark_manifest.json": (
            "benchmark_manifest.json"
        ),
        "bundle_manifest.json": "source_bundle_manifest.json",
    }
    for member_name, local_name in source_local_map.items():
        expected = {
            "bytes": inputs[local_name].stat().st_size,
            "sha256": sha256_file(inputs[local_name]),
        }
        if source_records[member_name] != expected:
            raise ValueError(f"sealed source input differs from AWS archive: {local_name}")

    output_names = {"px062_gate2_2", *OUTPUT_FILES}
    output_records = _tar_records(output_archive, output_names)
    output_local_map = {
        "px062_gate2_2/frozen_config.json": "frozen_config.json",
        "px062_gate2_2/source_bundle_manifest.json": "source_bundle_manifest.json",
        "px062_gate2_2/collection_summary.json": "collection_summary.json",
        "px062_gate2_2/model_traces.jsonl": "model_traces.jsonl",
        "px062_gate2_2/tokenizer_artifacts.tar.gz": "tokenizer_artifacts.tar.gz",
    }
    for member_name, local_name in output_local_map.items():
        expected = {
            "bytes": inputs[local_name].stat().st_size,
            "sha256": sha256_file(inputs[local_name]),
        }
        if output_records[member_name] != expected:
            raise ValueError(f"sealed outcome differs from AWS archive: {local_name}")
    return {
        "source_archive_sha256": sha256_file(source_archive),
        "source_version_id": receipt["source_artifact"]["version_id"],
        "output_archive_sha256": sha256_file(output_archive),
        "output_version_id": receipt["output_artifact"]["version_id"],
        "sealed_outcomes_match_registered_archive": True,
    }


def verify_adjudication_provenance(
    *,
    root: Path,
    authorization_path: Path,
    authorization: Mapping[str, Any],
    inputs: dict[str, Path],
    blob_reader: GitBlobReader = registered_git_blob,
    state_reader: GitStateReader = _registered_state_for_selected_paths,
) -> dict[str, Any]:
    """Authenticate Git, launch, AWS artifacts, fetch receipt, and sealed bytes."""

    root = root.resolve()
    completion_path = _repo_path(
        root, Path(authorization["completion_registration"]["path"])
    )
    evidence = validate_completion_evidence(
        root,
        completion_path,
        blob_reader=blob_reader,
        state_reader=state_reader,
    )
    completion = evidence["completion"]
    launch = evidence["launch"]
    if set(launch) != LAUNCH_REGISTRATION_KEYS:
        raise ValueError("registered launch schema drift at adjudication")
    launch_evidence = validate_launch_evidence(
        root,
        evidence["paths"]["launch"],
        evidence["paths"]["receipt"],
        blob_reader=blob_reader,
        state_reader=state_reader,
    )
    if launch_evidence["launch_raw"] != evidence["launch_raw"]:
        raise ValueError("launch registration chain split at adjudication")

    receipt_path = _repo_path(root, Path(authorization["fetch_receipt"]["path"]))
    receipt_raw = receipt_path.read_bytes()
    receipt = strict_json_bytes(receipt_raw, "fetch receipt")
    validate_fetch_receipt_against_completion(
        receipt, completion, evidence["completion_raw"]
    )
    if authorization["fetch_receipt"] != {
        "path": receipt_path.relative_to(root).as_posix(),
        "sha256": sha256_bytes(receipt_raw),
    }:
        raise ValueError("authorization/fetch-receipt hash relationship drift")
    if authorization["completion_registration"] != {
        "path": completion_path.relative_to(root).as_posix(),
        "sha256": sha256_bytes(evidence["completion_raw"]),
    }:
        raise ValueError("authorization/completion hash relationship drift")
    for key in ("launch_registration", "launch_receipt", "request"):
        if authorization.get(key) != completion.get(key):
            raise ValueError(f"authorization registered {key} drift")
    if authorization.get("registered_fetcher") != {
        **completion["fetcher"],
        "fetch_code_commit": completion["fetch_code_commit"],
    }:
        raise ValueError("authorization registered fetcher drift")
    if authorization.get("registered_adjudicator") != launch["frozen_evidence"].get(
        "adjudicator"
    ):
        raise ValueError("authorization registered adjudicator drift")
    for key in ("job", "source_artifact", "output_artifact", "sealed_files"):
        if authorization.get(key) != receipt.get(key):
            raise ValueError(f"authorization fetch provenance drift: {key}")

    source_commit = launch["source_commit"]
    if set(launch["frozen_evidence"]) != set(FROZEN_EVIDENCE_CONTRACT):
        raise ValueError("registered evidence inventory drift at adjudication")
    for label, expected_path in FROZEN_EVIDENCE_CONTRACT.items():
        raw = blob_reader(root, source_commit, expected_path)
        record = launch["frozen_evidence"][label]
        if record.get("path") != expected_path or record.get("sha256") != sha256_bytes(
            raw
        ) or record.get("bytes") != len(raw):
            raise ValueError(f"registered evidence hash drift at adjudication: {label}")

    repo = receipt.get("repository")
    if not isinstance(repo, dict) or not re.fullmatch(
        r"[0-9a-f]{40}", str(repo.get("head", ""))
    ) or not repo.get("remote_refs"):
        raise ValueError("fetch receipt repository provenance drift")
    if blob_reader(
        root,
        str(repo["head"]),
        completion_path.relative_to(root).as_posix(),
    ) != evidence["completion_raw"]:
        raise ValueError("fetch receipt completion was not on its pushed evidence commit")

    sealed_verification = verify_sealed_evidence(receipt_path, inputs)
    archive_verification = verify_registered_cloud_archives(
        launch=launch, receipt=receipt, inputs=inputs
    )
    return {
        "launch_registration_sha256": sha256_bytes(evidence["launch_raw"]),
        "completion_registration_sha256": sha256_bytes(evidence["completion_raw"]),
        "fetch_receipt_sha256": sha256_bytes(receipt_raw),
        "fetcher_sha256": completion["fetcher"]["sha256"],
        "job_arn": receipt["job"]["arn"],
        "sealed_evidence": sealed_verification,
        "cloud_archives": archive_verification,
        "verified_before_semantic_adjudication": True,
    }


def wilson_95(successes: int, total: int) -> list[float] | None:
    """Return the ordinary two-sided 95% Wilson score interval."""

    if total <= 0:
        return None
    proportion = successes / total
    z2 = Z_95 * Z_95
    denominator = 1 + z2 / total
    center = (proportion + z2 / (2 * total)) / denominator
    radius = (
        Z_95
        * math.sqrt(
            proportion * (1 - proportion) / total + z2 / (4 * total * total)
        )
        / denominator
    )
    return [max(0.0, center - radius), min(1.0, center + radius)]


def rate(successes: int, total: int) -> dict[str, Any]:
    return {
        "numerator": successes,
        "denominator": total,
        "rate": successes / total if total else None,
        "wilson_95": wilson_95(successes, total),
    }


def one_sided_mcnemar(improvements: int, regressions: int) -> float:
    """Exact P(D correct, E wrong) > P(D wrong, E correct) test."""

    discordant = improvements + regressions
    if discordant == 0:
        return 1.0
    return sum(
        math.comb(discordant, count)
        for count in range(improvements, discordant + 1)
    ) / (2**discordant)


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Return step-down Holm adjusted values for the complete frozen family."""

    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    family_size = len(ordered)
    for rank, (name, value) in enumerate(ordered):
        candidate = min(1.0, value * (family_size - rank))
        running = max(running, candidate)
        adjusted[name] = running
    return adjusted


def _valid_message_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            isinstance(message, dict)
            and set(message) == {"role", "content"}
            and message["role"] in {"system", "user", "assistant", "tool"}
            and isinstance(message["content"], str)
            for message in value
        )
    )


def _valid_token_ids(value: Any, *, generated: bool) -> bool:
    return (
        isinstance(value, list)
        and all(
            isinstance(token, int) and not isinstance(token, bool) and token >= 0
            for token in value
        )
        and ((generated and bool(value)) or (not generated and value == []))
    )


def _check_decoded_completion(
    *,
    arm_name: str,
    arm: dict[str, Any],
    tokenizer: Any,
    errors: list[str],
    key: tuple[str, str],
) -> str | None:
    """Authenticate preserved UTF-8 bytes and reconstruct them from token IDs."""

    raw = arm.get("raw_response")
    if not isinstance(raw, str):
        errors.append(f"{key} {arm_name} raw response is not a string")
        return None
    raw_bytes = raw.encode("utf-8")
    if arm.get("raw_response_bytes") != len(raw_bytes):
        errors.append(f"{key} {arm_name} raw-response byte count mismatch")
    encoded = arm.get("raw_response_utf8_base64")
    try:
        decoded_bytes = base64.b64decode(encoded, validate=True)
    except (TypeError, ValueError):
        decoded_bytes = None
    if decoded_bytes != raw_bytes:
        errors.append(f"{key} {arm_name} preserved UTF-8 bytes mismatch")
    if arm.get("raw_response_sha256") != sha256_bytes(raw_bytes):
        errors.append(f"{key} {arm_name} raw-response hash mismatch")
    token_ids = arm.get("generated_token_ids")
    if not _valid_token_ids(token_ids, generated=True):
        errors.append(f"{key} {arm_name} generated token IDs are invalid or empty")
        return raw
    try:
        reconstructed = tokenizer.decode(
            token_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
    except Exception as error:  # Token ID range/type failures are evidence defects.
        errors.append(f"{key} {arm_name} tokenizer reconstruction failed: {error}")
    else:
        if reconstructed.encode("utf-8") != raw_bytes:
            errors.append(f"{key} {arm_name} token IDs decode to different bytes")
    if arm.get("tokenizer_reconstruction_verified") is not True:
        errors.append(f"{key} {arm_name} collector reconstruction flag is not true")
    return raw


def strict_initial_parse(
    text: str, registry_names: set[str]
) -> tuple[str, str | None, str | None]:
    """Independently reproduce the frozen arm-A exact parser."""

    candidate = text.strip()
    if candidate == "NONE":
        return "explicit_none", None, None
    if candidate in registry_names:
        return "valid_skill", candidate, candidate
    return "invalid", candidate or None, None


def validate_option_map(
    option_map: Any, registry_names: set[str]
) -> tuple[dict[str, str | None], list[str]]:
    if not isinstance(option_map, list):
        raise ValueError("option_map is not a list")
    if len(option_map) != EXPECTED_REGISTRY_NAMES + 1:
        raise ValueError("option_map must contain 43 skills plus NONE")
    expected_ids = {f"S{index:03d}" for index in range(1, 45)}
    ids: list[str] = []
    skills: list[str | None] = []
    for entry in option_map:
        if not isinstance(entry, dict) or "id" not in entry or "skill" not in entry:
            raise ValueError("option_map entry schema is invalid")
        option_id = entry["id"]
        skill = entry["skill"]
        if not isinstance(option_id, str):
            raise ValueError("option_map ID is not a string")
        if skill is not None and not isinstance(skill, str):
            raise ValueError("option_map skill is neither string nor null")
        ids.append(option_id)
        skills.append(skill)
    if set(ids) != expected_ids or len(set(ids)) != len(ids):
        raise ValueError("option_map local IDs are not exactly S001..S044")
    nonnull = [skill for skill in skills if skill is not None]
    if skills.count(None) != 1 or set(nonnull) != registry_names or len(nonnull) != len(
        set(nonnull)
    ):
        raise ValueError("option_map is not a one-to-one closed registry plus NONE")
    mapping = dict(zip(ids, skills, strict=True))
    allowed = sorted(
        json.dumps({"choice": option_id}, separators=(",", ":")) for option_id in ids
    )
    return mapping, allowed


def render_catalog(
    option_map: list[dict[str, Any]],
    descriptions: dict[str, str],
    *,
    include_descriptions: bool,
) -> str:
    lines: list[str] = []
    for entry in option_map:
        option_id = entry["id"]
        skill = entry["skill"]
        if skill is None:
            label = "NONE \u2014 no suitable registered skill"
        elif include_descriptions:
            label = f"{skill} \u2014 {descriptions[skill]}"
        else:
            label = skill
        lines.append(f"{option_id}: {label}")
    return "\n".join(lines)


def reconstructed_messages(
    config: dict[str, Any],
    task: dict[str, Any],
    option_map: list[dict[str, Any]],
    descriptions: dict[str, str],
    a_raw_response: str,
) -> dict[str, list[dict[str, str]]]:
    """Rebuild all generated-arm messages without importing collector code."""

    templates = config["message_templates"]
    prompt = task["prompt"]
    names_catalog = render_catalog(
        option_map, descriptions, include_descriptions=False
    )
    full_catalog = render_catalog(option_map, descriptions, include_descriptions=True)
    a_messages = [
        {"role": "system", "content": templates["open_system"]},
        {
            "role": "user",
            "content": templates["open_user"].format(task=prompt),
        },
    ]
    b_messages = [
        {"role": "system", "content": templates["structured_system"]},
        {
            "role": "user",
            "content": templates["direct_names_user"].format(
                task=prompt, catalog=names_catalog
            ),
        },
    ]
    c_messages = [
        {"role": "system", "content": templates["structured_system"]},
        {
            "role": "user",
            "content": templates["direct_catalog_user"].format(
                task=prompt, catalog=full_catalog
            ),
        },
    ]
    d_messages = [
        *a_messages,
        {"role": "assistant", "content": a_raw_response},
        {
            "role": "user",
            "content": templates["contextual_repair_user"].format(
                catalog=full_catalog
            ),
        },
    ]
    e_messages = [
        {"role": "system", "content": templates["open_system"]},
        {
            "role": "user",
            "content": templates["decontextualized_task_placeholder"],
        },
        {"role": "assistant", "content": a_raw_response},
        {
            "role": "user",
            "content": templates["contextual_repair_user"].format(
                catalog=full_catalog
            ),
        },
    ]
    return {
        "A_open_text": a_messages,
        "B_structured_names": b_messages,
        "C_structured_catalog": c_messages,
        "D_contextual_repair": d_messages,
        "E_decontextualized_repair": e_messages,
    }


def _check_message_binding(
    *,
    arm_name: str,
    arm: dict[str, Any],
    expected_messages: list[dict[str, str]],
    errors: list[str],
    key: tuple[str, str],
) -> None:
    if not _valid_message_list(arm.get("messages")):
        errors.append(f"{key} {arm_name} messages are invalid")
        return
    if arm["messages"] != expected_messages:
        errors.append(f"{key} {arm_name} messages differ from reconstruction")
    observed_hash = canonical_json_sha256(arm["messages"])
    if arm.get("messages_sha256") != observed_hash:
        errors.append(f"{key} {arm_name} message hash mismatch")


def _check_structured_arm(
    *,
    arm_name: str,
    arm: Any,
    expected_messages: list[dict[str, str]],
    mapping: dict[str, str | None],
    allowed: list[str],
    expected_triggered: bool,
    a_selection: str | None,
    a_sha256: str,
    errors: list[str],
    key: tuple[str, str],
    tokenizer: Any,
) -> str | None:
    if not isinstance(arm, dict) or set(arm) != STRUCTURED_FIELDS:
        errors.append(f"{key} {arm_name} structured-arm schema drift")
        return None
    is_repair = arm_name in {
        "D_contextual_repair",
        "E_decontextualized_repair",
    }
    expected_source = a_sha256 if is_repair else None
    if arm.get("source_initial_sha256") != expected_source:
        errors.append(f"{key} {arm_name} is not bound to the exact A response")
    choice_set_sha = canonical_json_sha256(allowed)
    if arm.get("choice_set_sha256") != choice_set_sha:
        errors.append(f"{key} {arm_name} choice-set hash mismatch")
    if not isinstance(arm.get("decoder_escape"), bool):
        errors.append(f"{key} {arm_name} decoder_escape is not boolean")

    if not expected_triggered:
        if arm.get("triggered") is not False or arm.get("generated") is not False:
            errors.append(f"{key} {arm_name} should be a non-generated pass-through")
        null_fields = (
            "messages",
            "messages_sha256",
            "raw_response",
            "raw_response_utf8_base64",
            "raw_response_bytes",
            "raw_response_sha256",
            "tokenizer_reconstruction_verified",
            "choice_id",
        )
        if any(arm.get(field) is not None for field in null_fields):
            errors.append(f"{key} {arm_name} pass-through contains generated fields")
        if not _valid_token_ids(arm.get("generated_token_ids"), generated=False):
            errors.append(f"{key} {arm_name} pass-through token IDs are invalid")
        if arm.get("decoder_escape") is not False:
            errors.append(f"{key} {arm_name} pass-through records a decoder escape")
        if arm.get("selection") != a_selection:
            errors.append(f"{key} {arm_name} pass-through selection differs from A")
        canonical = json.dumps({"skill": a_selection}, separators=(",", ":"))
        if arm.get("canonical_decision") != canonical:
            errors.append(f"{key} {arm_name} pass-through decision mismatch")
        return a_selection

    if arm.get("triggered") is not True or arm.get("generated") is not True:
        errors.append(f"{key} {arm_name} should be generated")
    _check_message_binding(
        arm_name=arm_name,
        arm=arm,
        expected_messages=expected_messages,
        errors=errors,
        key=key,
    )
    raw = _check_decoded_completion(
        arm_name=arm_name,
        arm=arm,
        tokenizer=tokenizer,
        errors=errors,
        key=key,
    )
    if raw is None:
        return None
    independent_escape = raw not in allowed
    if arm.get("decoder_escape") is not independent_escape:
        errors.append(f"{key} {arm_name} decoder-escape flag mismatch")
    if independent_escape:
        errors.append(f"{key} {arm_name} constrained decoder escaped")
        independent_choice = None
    else:
        independent_choice = strict_json_bytes(raw.encode("utf-8"), "structured response")[
            "choice"
        ]
    if arm.get("choice_id") != independent_choice:
        errors.append(f"{key} {arm_name} choice ID mismatch")
    independent_selection = mapping.get(independent_choice)
    if arm.get("selection") != independent_selection:
        errors.append(f"{key} {arm_name} selection mismatch")
    canonical = json.dumps({"skill": independent_selection}, separators=(",", ":"))
    if arm.get("canonical_decision") != canonical:
        errors.append(f"{key} {arm_name} canonical decision mismatch")
    return independent_selection


def adjudication_config_contract_sha256(config: dict[str, Any]) -> str:
    projected = copy.deepcopy(config)
    for field in ("status", "source_integrity"):
        if field not in projected:
            raise ValueError(f"config contract field is missing: {field}")
        del projected[field]
    protocol = projected.get("label_audit_protocol")
    if not isinstance(protocol, dict) or not {
        "runner_sha256",
        "protocol_sha256",
        "tests_sha256",
    } <= set(protocol):
        raise ValueError("config contract audit-file bindings are missing")
    del protocol["runner_sha256"]
    del protocol["protocol_sha256"]
    del protocol["tests_sha256"]
    return canonical_json_sha256(projected)


def _config_errors(
    config: dict[str, Any], expected_config_contract_sha256: str
) -> list[str]:
    errors: list[str] = []
    try:
        observed_contract = adjudication_config_contract_sha256(config)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if observed_contract != expected_config_contract_sha256:
            errors.append("config semantic contract differs from the registered freeze")
    if config.get("protocol_version") != "2.2.0":
        errors.append("config protocol version is not exactly 2.2.0")
    if config.get("status") != "FROZEN_PREREGISTERED":
        errors.append("config status is not exactly FROZEN_PREREGISTERED")
    exact_values = {
        "expected_tasks": EXPECTED_TASKS,
        "expected_traces": EXPECTED_TRACES,
        "expected_registry_names": EXPECTED_REGISTRY_NAMES,
    }
    for field, expected in exact_values.items():
        if config.get(field) != expected:
            errors.append(f"config {field} {config.get(field)!r} != {expected!r}")
    if config.get("dependency_versions") != FROZEN_DEPENDENCIES:
        errors.append("config dependency versions differ from the frozen runtime")
    if config.get("arms") != list(EXPECTED_ARMS):
        errors.append("config arms differ from the frozen A-E order")
    models = config.get("models")
    if models != list(FROZEN_MODEL_REVISIONS):
        errors.append("config does not contain the exact two frozen model IDs")
    revisions = config.get("model_revisions")
    if revisions != FROZEN_MODEL_REVISIONS:
        errors.append("config does not contain the exact frozen model revisions")
    if config.get("decoding") != {
        "do_sample": False,
        "open_max_new_tokens": 32,
        "structured_decoder": "greedy_prefix_trie_over_exact_local_id_json_choices",
        "structured_response_schema": '{"choice":"Snnn"}',
        "choice_count": 44,
    }:
        errors.append("config decoding contract differs from the frozen protocol")
    counts = config.get("expected_task_type_counts")
    if (
        not isinstance(counts, dict)
        or sorted(counts.values()) != EXPECTED_TYPE_COUNTS
        or sum(counts.values()) != EXPECTED_TASKS
    ):
        errors.append("config task-type counts are not frozen at 344/344/172/172")
    labels = config.get("expected_label_counts")
    if labels != {"registered_skill": 516, "none": 516}:
        errors.append("config label counts are not frozen at 516/516")
    gates = config.get("gates")
    if gates != FROZEN_GATES:
        errors.append("config gates differ from the frozen Gate 2.2 thresholds")
    multiplicity = config.get("multiplicity", {})
    if multiplicity.get("method") != "Holm" or multiplicity.get("family_size") != 2:
        errors.append("config multiplicity is not the frozen two-model Holm family")
    templates = config.get("message_templates")
    required_templates = {
        "open_system",
        "open_user",
        "structured_system",
        "direct_names_user",
        "direct_catalog_user",
        "contextual_repair_user",
        "decontextualized_task_placeholder",
    }
    if not isinstance(templates, dict) or set(templates) != required_templates:
        errors.append("config message template schema drift")
    elif not all(isinstance(value, str) for value in templates.values()):
        errors.append("config message templates must all be strings")
    else:
        # These strings are passed through ``str.format`` when messages are
        # reconstructed, so literal JSON braces must be escaped in the frozen
        # template.  The rendered prompt contains the single-brace schema.
        exact_schema = '{{"choice":"Snnn"}}'
        if exact_schema not in templates["contextual_repair_user"]:
            errors.append(
                "config contextual_repair_user does not explicitly state the exact JSON schema"
            )
    if not isinstance(config.get("claim_boundary"), str) or not config["claim_boundary"].strip():
        errors.append("config claim boundary is missing")
    return errors


def adjudicate(
    config: dict[str, Any],
    tasks: list[dict[str, Any]],
    answer_key: list[dict[str, Any]],
    registry_catalog: dict[str, Any],
    traces: list[dict[str, Any]],
    artifact_hashes: dict[str, str] | None = None,
    tokenizer_verifiers: dict[str, Any] | None = None,
    tokenizer_metadata: dict[str, dict[str, Any]] | None = None,
    expected_config_contract_sha256: str = FROZEN_CONFIG_CONTRACT_SHA256,
) -> dict[str, Any]:
    errors = _config_errors(config, expected_config_contract_sha256)
    tokenizer_verifiers = tokenizer_verifiers or {}
    tokenizer_metadata = tokenizer_metadata or {}
    if set(tokenizer_verifiers) != set(config.get("models", [])):
        errors.append("frozen tokenizer verifiers do not exactly cover the models")
    if set(tokenizer_metadata) != set(config.get("models", [])):
        errors.append("frozen tokenizer metadata do not exactly cover the models")

    entries = registry_catalog.get("entries") if isinstance(registry_catalog, dict) else None
    descriptions: dict[str, str] = {}
    if not isinstance(entries, list) or len(entries) != EXPECTED_REGISTRY_NAMES:
        errors.append("registry catalog does not contain exactly 43 entries")
    else:
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"registry entry {index} is not an object")
                continue
            name = entry.get("name")
            description = entry.get("description")
            if not isinstance(name, str) or not name or name == "NONE":
                errors.append(f"registry entry {index} has an invalid name")
                continue
            if not isinstance(description, str) or not description.strip():
                errors.append(f"registry entry {name!r} has no description")
                continue
            if name.casefold() in {item.casefold() for item in descriptions}:
                errors.append(f"case-insensitive duplicate registry name: {name}")
                continue
            descriptions[name] = description
    registry_names = set(descriptions)

    task_map: dict[str, dict[str, Any]] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"task row {index} is not an object")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id or task_id in task_map:
            errors.append(f"invalid or duplicate task ID: {task_id!r}")
            continue
        if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
            errors.append(f"task {task_id} has no prompt")
        if "expected_skill" in task or "label" in task:
            errors.append(f"task {task_id} leaks an answer-key field")
        try:
            validate_option_map(task.get("option_map"), registry_names)
        except ValueError as exc:
            errors.append(f"task {task_id} {exc}")
        task_map[task_id] = task
    if len(task_map) != EXPECTED_TASKS:
        errors.append(f"task count {len(task_map)} != {EXPECTED_TASKS}")

    answer_map: dict[str, dict[str, Any]] = {}
    type_counts: Counter[str] = Counter()
    skill_target_counts: Counter[str] = Counter()
    real_labels = 0
    none_labels = 0
    for index, answer in enumerate(answer_key):
        if not isinstance(answer, dict):
            errors.append(f"answer row {index} is not an object")
            continue
        task_id = answer.get("task_id")
        if not isinstance(task_id, str) or task_id in answer_map:
            errors.append(f"invalid or duplicate answer task ID: {task_id!r}")
            continue
        expected = answer.get("expected_skill")
        if expected is not None and expected not in registry_names:
            errors.append(f"answer {task_id} is not a canonical registry skill or null")
        task = task_map.get(task_id)
        task_type = answer.get("task_type")
        if task_type is None and task is not None:
            task_type = task.get("task_type", task.get("stratum"))
        if task is not None:
            task_declared_type = task.get("task_type", task.get("stratum"))
            if task_declared_type is not None and task_declared_type != task_type:
                errors.append(f"task/answer type mismatch for {task_id}")
        if not isinstance(task_type, str) or task_type not in config.get(
            "expected_task_type_counts", {}
        ):
            errors.append(f"answer {task_id} has an invalid task type {task_type!r}")
        else:
            type_counts[task_type] += 1
        if expected is None:
            none_labels += 1
        else:
            real_labels += 1
            skill_target_counts[expected] += 1
        answer_map[task_id] = {**answer, "resolved_task_type": task_type}
    if set(answer_map) != set(task_map):
        errors.append("answer-key task IDs do not exactly match task IDs")
    if dict(type_counts) != config.get("expected_task_type_counts"):
        errors.append(
            f"answer-key task-type counts {dict(type_counts)} != "
            f"{config.get('expected_task_type_counts')}"
        )
    if (real_labels, none_labels) != (EXPECTED_REAL_LABELS, EXPECTED_NONE_LABELS):
        errors.append(
            f"answer-key label counts real={real_labels}, none={none_labels} != 516/516"
        )
    if registry_names and any(skill_target_counts[name] != 12 for name in registry_names):
        errors.append("registered-skill targets are not exactly 12 per skill")

    expected_source = config.get("source_integrity")
    if not isinstance(expected_source, dict):
        errors.append("config source_integrity is missing")
        expected_source = {}
    observed_source = artifact_hashes or {}
    required_hash_keys = {
        "tasks_sha256",
        "answer_key_sha256",
        "registry_catalog_sha256",
        "benchmark_manifest_sha256",
    }
    for name in required_hash_keys:
        expected_hash = expected_source.get(name)
        observed_hash = observed_source.get(name)
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(character not in "0123456789abcdef" for character in expected_hash)
        ):
            errors.append(f"source hash {name} is not a frozen lowercase SHA-256")
        elif observed_hash != expected_hash:
            errors.append(f"source hash mismatch for {name}")

    expected_models = config.get("models", [])
    expected_keys = {
        (model_id, task_id) for model_id in expected_models for task_id in task_map
    }
    seen: set[tuple[str, str]] = set()
    valid_rows: list[dict[str, Any]] = []
    option_position_counts: dict[int, Counter[str]] = defaultdict(Counter)
    recorded_task_options: set[str] = set()
    for index, trace in enumerate(traces):
        if not isinstance(trace, dict) or set(trace) != TRACE_FIELDS:
            errors.append(f"trace row {index} schema drift")
            continue
        key = (trace.get("model_id"), trace.get("task_id"))
        if not all(isinstance(value, str) for value in key):
            errors.append(f"trace row {index} has invalid key {key!r}")
            continue
        if key in seen:
            errors.append(f"duplicate trace key: {key}")
            continue
        seen.add(key)
        if key not in expected_keys:
            errors.append(f"unexpected trace key: {key}")
            continue
        model_id, task_id = key
        if trace["experiment_id"] != config.get("experiment_id"):
            errors.append(f"{key} experiment ID mismatch")
        if trace["protocol_version"] != config.get("protocol_version"):
            errors.append(f"{key} protocol version mismatch")
        if trace["model_revision"] != config["model_revisions"].get(model_id):
            errors.append(f"{key} model revision mismatch")
        tokenizer = tokenizer_verifiers.get(model_id)
        tokenizer_record = tokenizer_metadata.get(model_id)
        if tokenizer is None or not isinstance(tokenizer_record, dict):
            errors.append(f"{key} frozen tokenizer is unavailable")
            continue
        if tokenizer_record.get("revision") != trace["model_revision"]:
            errors.append(f"{key} tokenizer revision mismatch")
        if trace["tokenizer_artifact_key"] != tokenizer_record.get("artifact_key"):
            errors.append(f"{key} tokenizer artifact key mismatch")
        task = task_map[task_id]
        if trace["option_map"] != task.get("option_map"):
            errors.append(f"{key} option_map differs from frozen task bytes")
        if trace["option_map_sha256"] != canonical_json_sha256(trace["option_map"]):
            errors.append(f"{key} option_map hash mismatch")
        try:
            mapping, allowed = validate_option_map(trace["option_map"], registry_names)
        except ValueError as exc:
            errors.append(f"{key} {exc}")
            continue
        if task_id not in recorded_task_options:
            for position, entry in enumerate(trace["option_map"]):
                label = entry["skill"] if entry["skill"] is not None else "__NONE__"
                option_position_counts[position][label] += 1
            recorded_task_options.add(task_id)

        arms = trace["arms"]
        if not isinstance(arms, dict) or list(arms) != list(EXPECTED_ARMS):
            errors.append(f"{key} arm schema/order drift")
            continue
        a = arms["A_open_text"]
        if not isinstance(a, dict) or set(a) != A_FIELDS:
            errors.append(f"{key} arm A schema drift")
            continue
        if a.get("generated") is not True:
            errors.append(f"{key} arm A was not generated")
        raw_a = _check_decoded_completion(
            arm_name="A_open_text",
            arm=a,
            tokenizer=tokenizer,
            errors=errors,
            key=key,
        )
        if raw_a is None:
            continue
        expected_messages = reconstructed_messages(
            config, task, trace["option_map"], descriptions, raw_a
        )
        _check_message_binding(
            arm_name="A_open_text",
            arm=a,
            expected_messages=expected_messages["A_open_text"],
            errors=errors,
            key=key,
        )
        parser_status, parsed_candidate, a_selection = strict_initial_parse(
            raw_a, registry_names
        )
        if a.get("parser_status") != parser_status:
            errors.append(f"{key} arm A parser status mismatch")
        if a.get("parsed_candidate") != parsed_candidate:
            errors.append(f"{key} arm A parsed candidate mismatch")
        if a.get("selection") != a_selection:
            errors.append(f"{key} arm A selection mismatch")
        a_invalid = parser_status == "invalid"
        a_sha = text_sha256(raw_a)

        decisions: dict[str, str | None] = {"A_open_text": a_selection}
        for arm_name in EXPECTED_ARMS[1:]:
            expected_triggered = (
                True
                if arm_name in {"B_structured_names", "C_structured_catalog"}
                else a_invalid
            )
            decisions[arm_name] = _check_structured_arm(
                arm_name=arm_name,
                arm=arms[arm_name],
                expected_messages=expected_messages[arm_name],
                mapping=mapping,
                allowed=allowed,
                expected_triggered=expected_triggered,
                a_selection=a_selection,
                a_sha256=a_sha,
                errors=errors,
                key=key,
                tokenizer=tokenizer,
            )
        expected_skill = answer_map[task_id]["expected_skill"]
        valid_rows.append(
            {
                "model_id": model_id,
                "task_id": task_id,
                "task_type": answer_map[task_id]["resolved_task_type"],
                "expected": expected_skill,
                "a_invalid": a_invalid,
                "decisions": decisions,
            }
        )

    missing_keys = expected_keys - seen
    if missing_keys:
        errors.append(f"missing trace keys: {len(missing_keys)}")
    if len(traces) != EXPECTED_TRACES:
        errors.append(f"trace count {len(traces)} != {EXPECTED_TRACES}")
    if len(seen & expected_keys) != EXPECTED_TRACES:
        errors.append(
            f"unique expected trace keys {len(seen & expected_keys)} != {EXPECTED_TRACES}"
        )
    for position in range(44):
        counts = option_position_counts[position]
        if set(counts) != registry_names | {"__NONE__"} or (
            counts and max(counts.values()) - min(counts.values()) > 1
        ):
            errors.append(f"task option-map position {position} is not balanced")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in valid_rows:
        grouped[row["model_id"]].append(row)
    metrics: dict[str, Any] = {}
    raw_p_values: dict[str, float] = {}
    for model_id in expected_models:
        rows = grouped.get(model_id, [])
        c_correct = sum(
            row["decisions"]["C_structured_catalog"] == row["expected"]
            for row in rows
        )
        real_rows = [row for row in rows if row["expected"] is not None]
        none_rows = [row for row in rows if row["expected"] is None]
        c_real_correct = sum(
            row["decisions"]["C_structured_catalog"] == row["expected"]
            for row in real_rows
        )
        c_none_wrong = sum(
            row["decisions"]["C_structured_catalog"] is not None for row in none_rows
        )
        invalid_rows = [row for row in rows if row["a_invalid"]]
        registered_invalid_rows = [
            row for row in invalid_rows if row["expected"] is not None
        ]
        a_invalid_by_task_type = {
            task_type: rate(
                sum(
                    row["a_invalid"] and row["task_type"] == task_type
                    for row in rows
                ),
                sum(row["task_type"] == task_type for row in rows),
            )
            for task_type in config["expected_task_type_counts"]
        }
        d_correct_all = sum(
            row["decisions"]["D_contextual_repair"] == row["expected"]
            for row in invalid_rows
        )
        e_correct_all = sum(
            row["decisions"]["E_decontextualized_repair"] == row["expected"]
            for row in invalid_rows
        )
        improvements_all = sum(
            row["decisions"]["D_contextual_repair"] == row["expected"]
            and row["decisions"]["E_decontextualized_repair"] != row["expected"]
            for row in invalid_rows
        )
        regressions_all = sum(
            row["decisions"]["D_contextual_repair"] != row["expected"]
            and row["decisions"]["E_decontextualized_repair"] == row["expected"]
            for row in invalid_rows
        )
        d_correct_registered = sum(
            row["decisions"]["D_contextual_repair"] == row["expected"]
            for row in registered_invalid_rows
        )
        e_correct_registered = sum(
            row["decisions"]["E_decontextualized_repair"] == row["expected"]
            for row in registered_invalid_rows
        )
        improvements_registered = sum(
            row["decisions"]["D_contextual_repair"] == row["expected"]
            and row["decisions"]["E_decontextualized_repair"] != row["expected"]
            for row in registered_invalid_rows
        )
        regressions_registered = sum(
            row["decisions"]["D_contextual_repair"] != row["expected"]
            and row["decisions"]["E_decontextualized_repair"] == row["expected"]
            for row in registered_invalid_rows
        )
        d_none_wrong = sum(
            row["decisions"]["D_contextual_repair"] is not None for row in none_rows
        )
        paired_all_n = len(invalid_rows)
        paired_registered_n = len(registered_invalid_rows)
        diagnostic_raw_p = one_sided_mcnemar(improvements_all, regressions_all)
        raw_p = one_sided_mcnemar(
            improvements_registered, regressions_registered
        )
        raw_p_values[model_id] = raw_p
        metrics[model_id] = {
            "trace_count": len(rows),
            "C_overall_accuracy": rate(c_correct, len(rows)),
            "C_registered_target_recall": rate(c_real_correct, len(real_rows)),
            "C_wrong_existing_on_expected_NONE": rate(c_none_wrong, len(none_rows)),
            "A_invalid_events": rate(paired_all_n, len(rows)),
            "A_invalid_events_by_task_type": a_invalid_by_task_type,
            "A_invalid_registered_target_events": rate(
                paired_registered_n, len(real_rows)
            ),
            # These all-invalid metrics are diagnostic only.  In particular,
            # successful NONE repairs cannot satisfy a registered-skill gate.
            "D_recovery_accuracy_on_all_A_invalid_diagnostic": rate(
                d_correct_all, paired_all_n
            ),
            "E_recovery_accuracy_on_all_A_invalid_diagnostic": rate(
                e_correct_all, paired_all_n
            ),
            "D_wrong_existing_on_expected_NONE": rate(d_none_wrong, len(none_rows)),
            "D_vs_E_all_A_invalid_diagnostic": {
                "denominator": paired_all_n,
                "D_correct": d_correct_all,
                "E_correct": e_correct_all,
                "accuracy_gain": (d_correct_all - e_correct_all) / paired_all_n
                if paired_all_n
                else None,
                "improvements": improvements_all,
                "regressions": regressions_all,
                "discordant": improvements_all + regressions_all,
                "mcnemar_one_sided_p_diagnostic": diagnostic_raw_p,
                "primary_gate": False,
            },
            "D_registered_recovery_accuracy_on_A_invalid_registered": rate(
                d_correct_registered, paired_registered_n
            ),
            "E_registered_recovery_accuracy_on_A_invalid_registered": rate(
                e_correct_registered, paired_registered_n
            ),
            "D_vs_E_registered_paired": {
                "denominator": paired_registered_n,
                "D_correct": d_correct_registered,
                "E_correct": e_correct_registered,
                "accuracy_gain": (
                    d_correct_registered - e_correct_registered
                )
                / paired_registered_n
                if paired_registered_n
                else None,
                "improvements": improvements_registered,
                "regressions": regressions_registered,
                "discordant": improvements_registered + regressions_registered,
                "mcnemar_one_sided_p": raw_p,
                "primary_gate": False,
                "outcome_role": "required_secondary_context_ablation",
            },
        }

    adjusted = holm_adjust(raw_p_values) if raw_p_values else {}
    model_gates: dict[str, Any] = {}
    for model_id in expected_models:
        item = metrics.get(model_id, {})
        c_overall = item.get("C_overall_accuracy", rate(0, 0))
        c_real = item.get("C_registered_target_recall", rate(0, 0))
        c_none_wrong = item.get("C_wrong_existing_on_expected_NONE", rate(0, 0))
        d_recovery = item.get(
            "D_registered_recovery_accuracy_on_A_invalid_registered", rate(0, 0)
        )
        d_none_wrong = item.get("D_wrong_existing_on_expected_NONE", rate(0, 0))
        paired = item.get("D_vs_E_registered_paired", {})
        c_overall_interval = c_overall["wilson_95"]
        c_real_interval = c_real["wilson_95"]
        c_none_interval = c_none_wrong["wilson_95"]
        d_none_interval = d_none_wrong["wilson_95"]
        direct_components = {
            "C_overall_point_pass": c_overall["rate"] is not None
            and c_overall["rate"] >= 0.75,
            "C_overall_lower_pass": c_overall_interval is not None
            and c_overall_interval[0] >= 0.70,
            "C_registered_target_lower_pass": c_real_interval is not None
            and c_real_interval[0] >= 0.65,
            "C_NONE_wrong_existing_upper_pass": c_none_interval is not None
            and c_none_interval[1] <= 0.10,
        }
        event_sufficient = (
            item.get("A_invalid_registered_target_events", {}).get("numerator", 0)
            >= 200
        )
        repair_components = {
            "D_registered_recovery_point_pass": d_recovery["rate"] is not None
            and d_recovery["rate"] >= 0.60,
            "D_minus_E_registered_gain_pass": paired.get("accuracy_gain") is not None
            and paired["accuracy_gain"] >= 0.15,
            "D_minus_E_registered_holm_pass": adjusted.get(model_id, 1.0) <= 0.05,
            "D_NONE_wrong_existing_upper_pass": d_none_interval is not None
            and d_none_interval[1] <= 0.10,
        }
        paired["holm_adjusted_p"] = adjusted.get(model_id)
        direct_pass = all(direct_components.values())
        absolute_repair_pass = (
            event_sufficient
            and repair_components["D_registered_recovery_point_pass"]
            and repair_components["D_NONE_wrong_existing_upper_pass"]
        )
        context_mechanism_pass = (
            event_sufficient
            and repair_components["D_minus_E_registered_gain_pass"]
            and repair_components["D_minus_E_registered_holm_pass"]
        )
        primary_efficacy_pass = direct_pass and absolute_repair_pass
        model_gates[model_id] = {
            **direct_components,
            "direct_selector_pass": direct_pass,
            "A_invalid_registered_event_sufficiency": event_sufficient,
            **repair_components,
            "absolute_contextual_repair_pass": absolute_repair_pass,
            "primary_efficacy_pass": primary_efficacy_pass,
            "context_mechanism_pass": context_mechanism_pass,
        }

    integrity_pass = not errors
    directly_failed = any(
        not gates["direct_selector_pass"] for gates in model_gates.values()
    )
    always_evaluable_D_harm_failed = any(
        not gates["D_NONE_wrong_existing_upper_pass"]
        for gates in model_gates.values()
    )
    evaluable_absolute_repair_failed = any(
        gates["A_invalid_registered_event_sufficiency"]
        and not gates["D_registered_recovery_point_pass"]
        for gates in model_gates.values()
    )
    any_not_evaluable = any(
        not gates["A_invalid_registered_event_sufficiency"]
        for gates in model_gates.values()
    )
    if not integrity_pass:
        determination = "INVALID"
    elif (
        directly_failed
        or always_evaluable_D_harm_failed
        or evaluable_absolute_repair_failed
    ):
        determination = "CROSS_MODEL_NO_GO"
    elif any_not_evaluable:
        determination = "NOT_EVALUABLE"
    elif all(gates["primary_efficacy_pass"] for gates in model_gates.values()):
        determination = "PASS"
    else:
        determination = "CROSS_MODEL_NO_GO"
    if determination == "PASS":
        classification = "BOUNDED_EFFICACY_PASS"
    elif determination == "NOT_EVALUABLE":
        # By construction this branch is reached only when integrity, all C
        # gates, and the always-evaluable D harm gate pass, no sufficiently
        # powered model fails repair, and at least one A-invalid registered-
        # target cohort is <200.
        classification = "BOUNDED_SELECTOR_PASS"
    else:
        classification = determination
    powered_context_failure = any(
        gates["A_invalid_registered_event_sufficiency"]
        and not gates["context_mechanism_pass"]
        for gates in model_gates.values()
    )
    if not integrity_pass:
        context_mechanism_determination = "INVALID"
    elif powered_context_failure:
        context_mechanism_determination = "CONTEXT_MECHANISM_NOT_SUPPORTED"
    elif any_not_evaluable:
        context_mechanism_determination = "CONTEXT_MECHANISM_NOT_EVALUABLE"
    else:
        context_mechanism_determination = "CONTEXT_MECHANISM_SUPPORTED"
    return {
        "experiment_id": config.get("experiment_id"),
        "protocol_version": config.get("protocol_version"),
        "determination": determination,
        "result_classification": classification,
        "context_mechanism_determination": context_mechanism_determination,
        "integrity": {
            "pass": integrity_pass,
            "errors": errors,
            "expected_traces": EXPECTED_TRACES,
            "observed_traces": len(traces),
            "unique_expected_trace_keys": len(seen & expected_keys),
            "valid_rows": len(valid_rows),
            "trace_completeness": len(valid_rows) / EXPECTED_TRACES,
            "source_artifact_hashes": observed_source,
        },
        "denominators": {
            "C_overall_per_model": EXPECTED_TASKS,
            "C_registered_targets_per_model": EXPECTED_REAL_LABELS,
            "C_expected_NONE_per_model": EXPECTED_NONE_LABELS,
            "D_expected_NONE_per_model": EXPECTED_NONE_LABELS,
            "D_and_E_primary_recovery_per_model": (
                "observed A-invalid registered-target events; minimum 200"
            ),
            "D_and_E_all_A_invalid_diagnostic_per_model": (
                "all observed A-invalid events; diagnostic only"
            ),
        },
        "wilson_convention": {
            "kind": "two-sided Wilson score interval",
            "confidence": 0.95,
            "z": Z_95,
            "boundary_comparisons": "inclusive",
        },
        "holm_family": {
            "tests": [
                f"D_vs_E_registered_A_invalid::{model_id}"
                for model_id in expected_models
            ],
            "family_size": len(expected_models),
            "method": "Holm step-down",
            "alpha": 0.05,
        },
        "metrics": metrics,
        "model_gates": model_gates,
        "mechanistic_interpretation": (
            "D-versus-E is a required context-ablation test. E intentionally "
            "removes task context and is not represented as a realistic deployment "
            "comparator. Main efficacy rests on arm C and absolute D recovery on "
            "A-invalid registered-target events."
        ),
        "claim_boundary": config.get("claim_boundary"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--answer-key", type=Path, required=True)
    parser.add_argument("--registry-catalog", type=Path, required=True)
    parser.add_argument("--benchmark-manifest", type=Path, required=True)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--tokenizer-artifacts", type=Path, required=True)
    parser.add_argument("--collection-summary", type=Path, required=True)
    parser.add_argument("--fetch-receipt", type=Path, required=True)
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument(
        "--authorization",
        type=Path,
        default=DEFAULT_ADJUDICATION_AUTHORIZATION,
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recover-pre-outcome-claim", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    authorization_path = _repo_path(root, args.authorization)
    authorization, authorization_verification = (
        verify_committed_adjudication_authorization(root, authorization_path)
    )
    registration_path = (
        args.registration if args.registration.is_absolute() else root / args.registration
    ).resolve()
    authorized_registration = _repo_path(
        root, Path(authorization["launch_registration"]["path"])
    )
    if registration_path != authorized_registration:
        raise ValueError("registration path differs from adjudication authorization")
    registration, one_look_verification = verify_registered_adjudicator(
        root, registration_path
    )
    if authorization["registered_adjudicator"] != registration["frozen_evidence"].get(
        "adjudicator"
    ):
        raise ValueError("authorization adjudicator binding differs from registration")
    supplied_inputs = {
        "frozen_config.json": args.config,
        "tasks.jsonl": args.tasks,
        "answer_key.jsonl": args.answer_key,
        "registry_catalog.json": args.registry_catalog,
        "benchmark_manifest.json": args.benchmark_manifest,
        "model_traces.jsonl": args.traces,
        "tokenizer_artifacts.tar.gz": args.tokenizer_artifacts,
        "collection_summary.json": args.collection_summary,
    }
    requested_output, receipt_path, inputs = resolve_adjudication_paths(
        root=root,
        authorization=authorization,
        requested_output=args.output,
        supplied_fetch_receipt=args.fetch_receipt,
        supplied_inputs=supplied_inputs,
    )

    marker_path, claim = acquire_one_look_claim(
        root=root,
        authorization_path=authorization_path,
        authorization=authorization,
        requested_output=requested_output,
        recover_pre_outcome=args.recover_pre_outcome_claim,
    )
    claim = mark_one_look_outcome_read_started(marker_path, claim)
    provenance_verification = verify_adjudication_provenance(
        root=root,
        authorization_path=authorization_path,
        authorization=authorization,
        inputs=inputs,
    )
    config = read_json(args.config)
    if sha256_file(args.config) != registration.get("frozen_sources", {}).get(
        "config_sha256"
    ):
        raise ValueError("adjudication config differs from launch registration")
    manifest_path = args.benchmark_manifest
    artifact_hashes = {
        "tasks_sha256": sha256_file(args.tasks),
        "answer_key_sha256": sha256_file(args.answer_key),
        "registry_catalog_sha256": sha256_file(args.registry_catalog),
    }
    artifact_hashes["benchmark_manifest_sha256"] = sha256_file(manifest_path)
    summary = read_json(args.collection_summary)
    with tempfile.TemporaryDirectory(prefix="px062-g22-tokenizer-verify-") as temp:
        tokenizer_verifiers, tokenizer_metadata, tokenizer_record = load_frozen_tokenizers(
            args.tokenizer_artifacts, Path(temp), config
        )
        # Compare the immutable outer bindings explicitly; the full manifest
        # is independently authenticated inside the archive.
        expected_outer = (
            summary.get("tokenizer_artifacts", {})
            if isinstance(summary, dict)
            else {}
        )
        if any(
            expected_outer.get(field) != tokenizer_record[field]
            for field in ("path", "sha256", "bytes", "manifest_sha256")
        ) or canonical_json_sha256(expected_outer.get("manifest")) != tokenizer_record[
            "manifest_sha256"
        ]:
            raise ValueError("tokenizer artifacts differ from collection summary")
        result = adjudicate(
            config,
            read_jsonl(args.tasks),
            read_jsonl(args.answer_key),
            read_json(args.registry_catalog),
            read_jsonl(args.traces),
            artifact_hashes,
            tokenizer_verifiers,
            tokenizer_metadata,
        )
    result["integrity"]["source_artifact_hashes"].update(
        {
            "config_sha256": sha256_file(args.config),
            "traces_sha256": sha256_file(args.traces),
            "tokenizer_artifacts_sha256": tokenizer_record["sha256"],
        }
    )
    result["integrity"]["one_look_adjudicator_verification"] = one_look_verification
    result["integrity"]["adjudication_authorization_verification"] = (
        authorization_verification
    )
    result["integrity"]["sealed_evidence_verification"] = provenance_verification
    result["integrity"]["tokenizer_artifacts"] = tokenizer_record
    requested_output.parent.mkdir(parents=True, exist_ok=True)
    with requested_output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    complete_one_look_claim(marker_path, claim, requested_output)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["determination"] == "INVALID":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
