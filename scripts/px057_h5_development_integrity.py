#!/usr/bin/env python
"""Strict reusable integrity replay for the PX-057 H5 C1 r2 pilot.

The fetcher can call :func:`verify_fetched_collection` on the five-file cloud
bundle.  The evaluator can call :func:`verify_scientific_collection` on the
installed local directory before computing any outcome.  Both paths replay
the pinned source selection, prompt chain, extraction, strict response schema,
trace construction, summary, and byte hashes.

No model is loaded and no gold label is consulted while replaying extraction
or schema validity.  The supplied 500-row H4 calibration manifest bytes and
their expected hash are the sole source authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.px057_h5_development_contract import (
    CELL_ID,
    EXPERIMENT_ID,
    FROZEN_CELL_ID,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_SHA256,
    validate_frozen_development_config,
)
from scripts.px057_h5_mechanism import extract_last_valid_answer
from scripts.run_px057_h5_development_pilot import (
    build_prompt,
    validate_bounded_response,
)


SCIENTIFIC_FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
)
CLOUD_FILES = (*SCIENTIFIC_FILES, "cloud_job_evidence.json")
EXPECTED_ROWS = 500
EXPECTED_ROUNDS = 8
EXPECTED_GENERATIONS = EXPECTED_ROWS * EXPECTED_ROUNDS
EXPECTED_SAMPLE_SEED = 5758
SELECTION_ALGORITHM = "SHA256('<sample_seed>:<question_id>') ascending"

SHARED_STEP_FIELDS = (
    "confidence",
    "tokens",
    "generated_tokens",
    "prompt_tokens",
    "termination_reason",
    "token_cap_reached",
    "marker_count",
    "used_prior_valid_marker",
    "repetition_detected",
    "response_schema_valid",
    "wall_seconds",
    "gpu_seconds",
)

EXPECTED_CLOUD_KEYS = {
    "job_name",
    "git_commit",
    "repository_url",
    "branch",
    "container_image_digest",
    "source_archive",
    "code",
}
REQUIRED_CODE_KEYS = {
    "entrypoint_sha256",
    "config_sha256",
    "runner_sha256",
    "mechanism_sha256",
    "contract_sha256",
    "integrity_sha256",
    "h4_requirements_sha256",
}
REGISTERED_TERMINATION_REASONS = {
    "literal_end_marker",
    "literal_end_marker_at_token_cap",
    "native_eos_or_eot",
    "token_cap",
    "unexpected_no_registered_terminator",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _json_exact(observed: Any, expected: Any) -> bool:
    """Compare parsed JSON values without Python's ``True == 1`` coercion."""

    return canonical_json_bytes(observed) == canonical_json_bytes(expected)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def strict_json_bytes(value: bytes, *, source: str = "JSON") -> dict[str, Any]:
    try:
        decoded = json.loads(
            value.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{source}: invalid UTF-8 JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"{source}: expected a JSON object")
    return decoded


def strict_jsonl_bytes(
    value: bytes,
    *,
    source: str = "JSONL",
) -> list[dict[str, Any]]:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source}: invalid UTF-8 JSONL") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            decoded = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{line_number}: invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValueError(f"{source}:{line_number}: expected a JSON object")
        rows.append(decoded)
    if not rows:
        raise ValueError(f"{source}: no JSONL rows")
    return rows


def read_json_strict(path: Path) -> dict[str, Any]:
    return strict_json_bytes(path.read_bytes(), source=str(path))


def read_jsonl_strict(path: Path) -> list[dict[str, Any]]:
    return strict_jsonl_bytes(path.read_bytes(), source=str(path))


def hash_rank(question_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def load_pinned_source(
    source_manifest_bytes: bytes,
    *,
    expected_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    observed_sha256 = sha256_bytes(source_manifest_bytes)
    if expected_sha256 != SOURCE_MANIFEST_SHA256:
        raise ValueError("caller supplied an unregistered C1 source hash")
    if observed_sha256 != expected_sha256:
        raise ValueError(
            "pinned source manifest SHA-256 mismatch: "
            f"{observed_sha256} != {expected_sha256}"
        )
    rows = strict_jsonl_bytes(
        source_manifest_bytes,
        source=SOURCE_MANIFEST,
    )
    by_id = {str(row.get("question_id", "")): row for row in rows}
    if len(rows) != EXPECTED_ROWS or "" in by_id or len(by_id) != len(rows):
        raise ValueError("pinned C1 manifest must contain 500 unique question IDs")
    for question_id, row in by_id.items():
        if (
            row.get("domain") != "gsm8k"
            or row.get("answer_type") != "numeric"
            or not isinstance(row.get("gold_answer"), str)
            or not isinstance(row.get("question"), str)
        ):
            raise ValueError(f"pinned source row schema mismatch: {question_id}")
    return rows, by_id


def expected_selected_rows(
    source_rows: Sequence[dict[str, Any]],
    *,
    seed: int = EXPECTED_SAMPLE_SEED,
) -> list[dict[str, Any]]:
    if seed != EXPECTED_SAMPLE_SEED:
        raise ValueError("development selection seed must remain 5758")
    return sorted(
        source_rows,
        key=lambda row: (
            hash_rank(str(row["question_id"]), seed),
            str(row["question_id"]),
        ),
    )


def _file_record(path: Path) -> dict[str, Any]:
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size}


def _require_exact_file_records(
    observed: Any,
    expected: Mapping[str, dict[str, Any]],
    *,
    label: str,
) -> None:
    if not _json_exact(observed, dict(expected)):
        raise ValueError(f"{label} file hashes/byte lengths do not match")


def _require_bool(value: Any, *, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be an explicit boolean")
    return value


def _require_int(value: Any, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _require_float(value: Any, *, label: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _verify_summary(
    summary: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    cell: Mapping[str, Any],
    selected_ids: Sequence[str],
    scientific_records: Mapping[str, dict[str, Any]],
) -> None:
    generation = config["generation"]
    source = summary.get("source_manifest", {})
    selection = summary.get("selection", {})
    if not isinstance(source, Mapping) or not isinstance(selection, Mapping):
        raise ValueError("collection summary source/selection must be objects")
    if (
        summary.get("experiment_id") != EXPERIMENT_ID
        or summary.get("px_id") != "PX-057"
        or summary.get("attempt_id") != config["attempt_id"]
        or summary.get("protocol_id") != config["protocol_id"]
        or summary.get("frozen_cell_id") != config["frozen_cell_id"]
        or summary.get("policy_id")
        != config["primary_development_policy"]["policy_id"]
        or summary.get("stage") != "H5_DEVELOPMENT_PILOT_COLLECTION"
        or summary.get("status") != "PASS"
        or summary.get("confirmatory_evidence") is not False
        or summary.get("claim_boundary") != config["claim_boundary"]
        or summary.get("cell_id") != CELL_ID
        or not _json_exact(source, {
            "path": SOURCE_MANIFEST,
            "sha256": SOURCE_MANIFEST_SHA256,
            "available_rows": EXPECTED_ROWS,
            "outcome_exposed": True,
        })
        or selection.get("algorithm") != SELECTION_ALGORITHM
        or selection.get("sample_seed") != EXPECTED_SAMPLE_SEED
        or selection.get("rows") != EXPECTED_ROWS
        or selection.get("selected_id_sha256")
        != sha256_bytes(canonical_json_bytes(list(selected_ids)))
        or not _json_exact(
            summary.get("model"), config["models"][cell["model_key"]]
        )
        or not _json_exact(summary.get("generation"), generation)
        or not _json_exact(summary.get("response_protocol"), config["prompts"])
        or summary.get("observed_generation_rows") != EXPECTED_GENERATIONS
        or not isinstance(summary.get("runtime"), dict)
        or not summary["runtime"]
    ):
        raise ValueError("collection summary identity/config/model/source mismatch")
    _require_exact_file_records(
        summary.get("files"),
        {
            name: scientific_records[name]
            for name in SCIENTIFIC_FILES
            if name != "collection_summary.json"
        },
        label="collection summary",
    )


def verify_scientific_collection(
    collection_dir: Path,
    *,
    config: Mapping[str, Any],
    source_manifest_bytes: bytes,
    expected_source_sha256: str,
) -> dict[str, Any]:
    """Replay the complete four-file local scientific collection."""

    validate_frozen_development_config(config)
    if not collection_dir.is_dir():
        raise ValueError("development collection directory is missing")
    missing = [
        name for name in SCIENTIFIC_FILES if not (collection_dir / name).is_file()
    ]
    if missing:
        raise ValueError(f"development collection files are missing: {missing}")

    source_rows, source_by_id = load_pinned_source(
        source_manifest_bytes,
        expected_sha256=expected_source_sha256,
    )
    expected_selected = expected_selected_rows(source_rows)
    selected = read_jsonl_strict(collection_dir / "selected_rows.jsonl")
    traces = read_jsonl_strict(collection_dir / "reasoning_traces.jsonl")
    raw = read_jsonl_strict(collection_dir / "raw_generations.jsonl")
    summary = read_json_strict(collection_dir / "collection_summary.json")

    if not _json_exact(selected, expected_selected):
        raise ValueError("selected rows differ from exact SHA5758 source order/content")
    selected_ids = [str(row["question_id"]) for row in selected]
    if len(selected_ids) != EXPECTED_ROWS or len(set(selected_ids)) != EXPECTED_ROWS:
        raise ValueError("selected rows do not contain 500 ordered unique IDs")
    if len(traces) != EXPECTED_ROWS or len(raw) != EXPECTED_GENERATIONS:
        raise ValueError("collection cardinality is not exactly 500 traces by 8 rounds")
    trace_ids = [str(trace.get("question_id", "")) for trace in traces]
    if trace_ids != selected_ids or len(set(trace_ids)) != EXPECTED_ROWS:
        raise ValueError("trace IDs/order differ from selected SHA5758 order")

    expected_pairs = [
        (question_id, round_index)
        for question_id in selected_ids
        for round_index in range(1, EXPECTED_ROUNDS + 1)
    ]
    if any(type(row.get("round")) is not int for row in raw):
        raise ValueError("raw round values must be exact integers")
    observed_pairs = [
        (str(row.get("question_id", "")), row["round"]) for row in raw
    ]
    if observed_pairs != expected_pairs or len(set(observed_pairs)) != len(
        observed_pairs
    ):
        raise ValueError(
            "raw rows are not the exact ordered unique 500-by-8 ID-round product"
        )

    raw_index = {
        (str(row["question_id"]), int(row["round"])): row for row in raw
    }
    generation = config["generation"]
    max_new_tokens = int(generation["max_new_tokens"])
    cell = config["cells"][0]
    for trace in traces:
        question_id = str(trace["question_id"])
        source_row = source_by_id[question_id]
        if (
            trace.get("gold_answer") != source_row["gold_answer"]
            or trace.get("domain") != source_row["domain"]
            or trace.get("answer_type") != source_row["answer_type"]
        ):
            raise ValueError(f"trace source/gold/domain/type mismatch: {question_id}")
        steps = trace.get("steps")
        if not isinstance(steps, list) or len(steps) != EXPECTED_ROUNDS:
            raise ValueError(f"trace does not contain eight steps: {question_id}")
        if any(not isinstance(step, Mapping) for step in steps):
            raise ValueError(f"trace steps must be JSON objects: {question_id}")
        if any(type(step.get("step")) is not int for step in steps) or [
            step["step"] for step in steps
        ] != list(range(1, EXPECTED_ROUNDS + 1)):
            raise ValueError(f"trace rounds are not exactly 1..8: {question_id}")

        preceding_strict_answer = ""
        cumulative_tokens = 0
        for round_index, step in enumerate(steps, 1):
            raw_row = raw_index[(question_id, round_index)]
            if (
                type(raw_row.get("step")) is not int
                or raw_row["step"] != round_index
            ):
                raise ValueError(
                    f"raw step/round mismatch: {(question_id, round_index)}"
                )
            expected_prompt = build_prompt(
                source_row,
                previous_answer=preceding_strict_answer,
                round_index=round_index,
                prompts=config["prompts"],
            )
            if raw_row.get("prompt") != expected_prompt:
                raise ValueError(
                    f"prompt replay mismatch: {(question_id, round_index)}"
                )

            if not isinstance(raw_row.get("response"), str):
                raise ValueError(
                    f"response must be text: {(question_id, round_index)}"
                )
            generated_tokens = _require_int(
                raw_row.get("generated_tokens"),
                label=f"{question_id}/{round_index} generated_tokens",
            )
            if generated_tokens > max_new_tokens:
                raise ValueError(
                    "generated token count exceeds cap: "
                    f"{(question_id, round_index)}"
                )
            cumulative_tokens += generated_tokens
            _require_int(
                raw_row.get("tokens"),
                label=f"{question_id}/{round_index} raw tokens",
            )
            _require_int(
                step.get("tokens"),
                label=f"{question_id}/{round_index} trace tokens",
            )
            if (
                raw_row.get("tokens") != cumulative_tokens
                or step.get("tokens") != cumulative_tokens
            ):
                raise ValueError(
                    f"cumulative-token replay mismatch: {(question_id, round_index)}"
                )
            _require_int(
                raw_row.get("prompt_tokens"),
                label=f"{question_id}/{round_index} prompt_tokens",
                minimum=1,
            )
            _require_int(
                step.get("generated_tokens"),
                label=f"{question_id}/{round_index} trace generated_tokens",
            )
            _require_int(
                step.get("prompt_tokens"),
                label=f"{question_id}/{round_index} trace prompt_tokens",
                minimum=1,
            )
            confidence = _require_float(
                raw_row.get("confidence"),
                label=f"{question_id}/{round_index} confidence",
            )
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(
                    f"confidence outside [0,1]: {(question_id, round_index)}"
                )

            allowed = (
                source_row.get("choice_labels", ())
                if source_row["answer_type"] == "choice"
                else ()
            )
            extraction = extract_last_valid_answer(
                str(raw_row.get("response", "")),
                answer_type=str(source_row["answer_type"]),
                allowed_labels=allowed,
                generated_tokens=generated_tokens,
                max_new_tokens=max_new_tokens,
            )
            termination_reason = str(raw_row.get("termination_reason", ""))
            if (
                not isinstance(raw_row.get("termination_reason"), str)
                or termination_reason not in REGISTERED_TERMINATION_REASONS
            ):
                raise ValueError(
                    f"unregistered termination reason: {(question_id, round_index)}"
                )
            schema = validate_bounded_response(
                str(raw_row.get("response", "")),
                extraction=extraction,
                answer_type=str(source_row["answer_type"]),
                allowed_labels=allowed,
                termination_reason=termination_reason,
            )
            strict_answer = extraction.answer if schema["valid"] else ""
            expected_flags = {
                "token_cap_reached": generated_tokens >= max_new_tokens,
                "marker_count": extraction.marker_count,
                "used_prior_valid_marker": extraction.used_prior_valid_marker,
                "repetition_detected": extraction.repetition_detected,
                "response_schema_valid": schema["valid"],
            }
            for boolean_name in (
                "token_cap_reached",
                "used_prior_valid_marker",
                "repetition_detected",
                "response_schema_valid",
            ):
                _require_bool(
                    raw_row.get(boolean_name),
                    label=f"{question_id}/{round_index} raw {boolean_name}",
                )
                _require_bool(
                    step.get(boolean_name),
                    label=f"{question_id}/{round_index} trace {boolean_name}",
                )
            _require_int(
                raw_row.get("marker_count"),
                label=f"{question_id}/{round_index} raw marker_count",
            )
            _require_int(
                step.get("marker_count"),
                label=f"{question_id}/{round_index} trace marker_count",
            )
            if raw_row.get("parsed_candidate") != extraction.answer:
                raise ValueError(
                    "parsed candidate replay mismatch: "
                    f"{(question_id, round_index)}"
                )
            if not _json_exact(raw_row.get("response_schema"), schema):
                raise ValueError(
                    "response-schema replay mismatch: "
                    f"{(question_id, round_index)}"
                )
            if (
                raw_row.get("extracted_answer") != strict_answer
                or step.get("answer") != strict_answer
            ):
                raise ValueError(
                    f"strict answer replay mismatch: {(question_id, round_index)}"
                )
            for name, expected in expected_flags.items():
                if raw_row.get(name) != expected or step.get(name) != expected:
                    raise ValueError(
                        f"{name} replay mismatch: {(question_id, round_index)}"
                    )
            for name in SHARED_STEP_FIELDS:
                if not _json_exact(raw_row.get(name), step.get(name)):
                    raise ValueError(
                        f"raw/trace {name} mismatch: {(question_id, round_index)}"
                    )
            wall_seconds = _require_float(
                raw_row.get("wall_seconds"),
                label=f"{question_id}/{round_index} wall_seconds",
            )
            if wall_seconds < 0.0:
                raise ValueError(
                    f"negative wall time: {(question_id, round_index)}"
                )
            gpu_seconds = raw_row.get("gpu_seconds")
            if gpu_seconds is not None and _require_float(
                gpu_seconds,
                label=f"{question_id}/{round_index} gpu_seconds",
            ) < 0.0:
                raise ValueError(
                    f"negative GPU time: {(question_id, round_index)}"
                )
            preceding_strict_answer = strict_answer

    scientific_records = {
        name: _file_record(collection_dir / name) for name in SCIENTIFIC_FILES
    }
    _verify_summary(
        summary,
        config=config,
        cell=cell,
        selected_ids=selected_ids,
        scientific_records=scientific_records,
    )
    return {
        "status": "PASS",
        "experiment_id": EXPERIMENT_ID,
        "frozen_cell_id": FROZEN_CELL_ID,
        "cell_id": CELL_ID,
        "trace_count": EXPECTED_ROWS,
        "rounds_per_trace": EXPECTED_ROUNDS,
        "raw_generation_count": EXPECTED_GENERATIONS,
        "source_membership": "EXACT_H4_CALIBRATION_MANIFEST",
        "source_sha256": expected_source_sha256,
        "selected_id_sha256": sha256_bytes(
            canonical_json_bytes(selected_ids)
        ),
        "files": scientific_records,
    }


def _require_sha256(value: Any, *, label: str, prefixed: bool = False) -> str:
    pattern = r"sha256:[0-9a-f]{64}" if prefixed else r"[0-9a-f]{64}"
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        raise ValueError(f"{label} is not a full lowercase SHA-256")
    return value


def validate_expected_cloud_metadata(expected: Mapping[str, Any]) -> None:
    if set(expected) != EXPECTED_CLOUD_KEYS:
        raise ValueError(
            "expected cloud metadata keys differ from the strict contract: "
            f"{sorted(set(expected) ^ EXPECTED_CLOUD_KEYS)}"
        )
    if re.fullmatch(r"[0-9a-f]{40}", str(expected["git_commit"])) is None:
        raise ValueError("expected git_commit is not a full lowercase commit")
    _require_sha256(
        expected["container_image_digest"],
        label="expected container image digest",
        prefixed=True,
    )
    source_archive = expected["source_archive"]
    if (
        not isinstance(source_archive, Mapping)
        or set(source_archive) != {"version_id", "sha256"}
        or not str(source_archive["version_id"]).strip()
        or str(source_archive["version_id"]).strip().casefold() == "null"
    ):
        raise ValueError("expected source archive identity is incomplete")
    _require_sha256(source_archive["sha256"], label="expected source archive")
    code = expected["code"]
    if not isinstance(code, Mapping) or not REQUIRED_CODE_KEYS.issubset(code):
        raise ValueError("expected code hash inventory is incomplete")
    for name, digest in code.items():
        _require_sha256(digest, label=f"expected code.{name}")


def verify_cloud_evidence(
    evidence: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    collection_verification: Mapping[str, Any],
    expected_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind cloud provenance to caller-supplied job/source/code metadata."""

    validate_frozen_development_config(config)
    validate_expected_cloud_metadata(expected_metadata)
    if (
        evidence.get("experiment_id") != EXPERIMENT_ID
        or evidence.get("px_id") != "PX-057"
        or evidence.get("attempt_id") != config["attempt_id"]
        or evidence.get("protocol_id") != config["protocol_id"]
        or evidence.get("frozen_cell_id") != config["frozen_cell_id"]
        or evidence.get("policy_id")
        != config["primary_development_policy"]["policy_id"]
        or evidence.get("stage")
        != "PX057_H5_DEVELOPMENT_PILOT_CLOUD_COLLECTION"
        or evidence.get("status") != "PASS"
        or evidence.get("confirmatory_evidence") is not False
        or evidence.get("scientific_data_generated") is not True
        or evidence.get("claim_boundary") != config["claim_boundary"]
        or evidence.get("cell_id") != CELL_ID
        or evidence.get("job_name") != expected_metadata["job_name"]
        or evidence.get("git_commit") != expected_metadata["git_commit"]
        or evidence.get("repository_url") != expected_metadata["repository_url"]
        or evidence.get("branch") != expected_metadata["branch"]
        or evidence.get("container_image_digest")
        != expected_metadata["container_image_digest"]
        or not _json_exact(
            evidence.get("source_archive"), expected_metadata["source_archive"]
        )
        or not _json_exact(evidence.get("code"), expected_metadata["code"])
    ):
        raise ValueError("cloud evidence identity/code/image/source mismatch")
    observed_head = str(evidence.get("observed_remote_branch_head", ""))
    if re.fullmatch(r"[0-9a-f]{40}", observed_head) is None:
        raise ValueError("cloud evidence lacks a full observed remote branch head")
    if not _json_exact(evidence.get("h4_calibration_source"), {
        "path": SOURCE_MANIFEST,
        "sha256": SOURCE_MANIFEST_SHA256,
        "rows": EXPECTED_ROWS,
        "outcome_exposed": True,
    }):
        raise ValueError("cloud evidence H4 source identity mismatch")
    files = collection_verification["files"]
    if not _json_exact(evidence.get("collection_files"), files):
        raise ValueError("cloud evidence collection file hashes mismatch")
    expected_collection = {
        "status": "PASS",
        "experiment_id": EXPERIMENT_ID,
        "frozen_cell_id": FROZEN_CELL_ID,
        "cell_id": CELL_ID,
        "trace_count": EXPECTED_ROWS,
        "rounds_per_trace": EXPECTED_ROUNDS,
        "raw_generation_count": EXPECTED_GENERATIONS,
        "source_membership": "EXACT_H4_CALIBRATION_MANIFEST",
        "source_sha256": SOURCE_MANIFEST_SHA256,
        "selected_id_sha256": collection_verification["selected_id_sha256"],
        "files": files,
    }
    if not _json_exact(
        evidence.get("collection_verification"), expected_collection
    ):
        raise ValueError("cloud evidence collection verification mismatch")
    return {
        "status": "PASS",
        "job_name": expected_metadata["job_name"],
        "git_commit": expected_metadata["git_commit"],
        "container_image_digest": expected_metadata["container_image_digest"],
        "source_archive": dict(expected_metadata["source_archive"]),
        "code": dict(expected_metadata["code"]),
    }


def verify_fetched_collection(
    bundle_dir: Path,
    *,
    config: Mapping[str, Any],
    source_manifest_bytes: bytes,
    expected_source_sha256: str,
    expected_cloud_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the exact five-file SageMaker bundle before local installation."""

    if not bundle_dir.is_dir():
        raise ValueError("development cloud bundle directory is missing")
    observed = {path.name for path in bundle_dir.iterdir()}
    if observed != set(CLOUD_FILES) or any(
        not (bundle_dir / name).is_file() for name in CLOUD_FILES
    ):
        raise ValueError("cloud bundle is not the exact five-file contract")
    collection = verify_scientific_collection(
        bundle_dir,
        config=config,
        source_manifest_bytes=source_manifest_bytes,
        expected_source_sha256=expected_source_sha256,
    )
    evidence = read_json_strict(bundle_dir / "cloud_job_evidence.json")
    cloud = verify_cloud_evidence(
        evidence,
        config=config,
        collection_verification=collection,
        expected_metadata=expected_cloud_metadata,
    )
    return {"status": "PASS", "collection": collection, "cloud": cloud}
