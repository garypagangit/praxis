"""Pinned TRACE-derived ``rh-bench`` loading and integrity helpers.

The public derivative contains JSON-serialized ChatML messages, not the
structured tool-call records from an execution harness.  This module preserves
that distinction so downstream code cannot silently promote transcript text to
verified filesystem evidence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Collection, Mapping, Sequence

DATASET_ID = "ktolnos/rh-bench"
DATASET_CONFIG = "open_ended"
DATASET_SPLIT = "train"
SOURCE_DATASET = "patronus_trace"

DEFAULT_HF_REVISION = "1045a7336432c40182924bbd3698af292ea24acb"
PINNED_RHBENCH_COMMIT = "090e47b878192ee7a016d6c89e983141a415b154"
PINNED_PARQUET_SHA256 = "0a809f3fa648169f5a7df641095a72ee3218fa4e9d1ee68c5fdb7fb32d723b72"
OFFICIAL_TRACE_DATASET_ID = "PatronusAI/trace-dataset"
OFFICIAL_TRACE_HF_REVISION = "31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d"
OFFICIAL_TRACE_CARD_SHA256 = "b08109b2bbc431aea796193476e86df398f6eb662e930043d43911fa4e332d73"
PINNED_TRACE_TAXONOMY_SHA256 = "67f7133dc1e18da5701dac5c1bc9fa2f32b606832246d2b479b0fb0a20bfae3b"
PINNED_TRACE_TAXONOMY_SCHEMA_VERSION = "px063_trace_taxonomy_v1"

FROZEN_TRACE_ATOMIC_CODES = frozenset(
    {
        "1.1.1",
        "1.1.2",
        "1.1.3",
        "1.2.1",
        "1.2.2",
        "1.2.3",
        "1.3.1",
        "1.3.2",
        "1.4.1",
        "1.4.2",
    }
)

EXPECTED_TRACE_ROWS = 517
EXPECTED_HACKING_ROWS = 268
EXPECTED_CLEAN_ROWS = 249

CANONICAL_ROW_FIELDS = (
    "prompt",
    "response_hacking",
    "response_clean",
    "label",
    "hacking_category",
    "hacking_subcategory",
    "hacking_description",
    "construction",
    "verification",
    "source_dataset",
    "source_split",
    "source_row_idx",
    "source_id",
    "response_model",
    "is_agentic",
)


class TraceDataError(ValueError):
    """Raised when a TRACE-derived row violates the frozen adapter contract."""


class TraceLabelError(TraceDataError):
    """Raised with a non-disclosing reason code for invalid TRACE gold metadata."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ParsedMessage:
    role: str
    content: str
    turn: int
    field: str
    has_structured_payload: bool = False


@dataclass(frozen=True)
class SourceGateArtifacts:
    summary: dict[str, Any]
    records: list[dict[str, Any]]
    failures: list[dict[str, str]]


@dataclass(frozen=True)
class BlindedTraceRow:
    record_id: str
    prompt: str
    trajectory: str


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize deterministically for provenance hashing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_default,
    ).encode("utf-8")


def canonical_row_hash(row: Mapping[str, Any]) -> str:
    payload = {field: row.get(field) for field in CANONICAL_ROW_FIELDS}
    return sha256(canonical_json_bytes(payload)).hexdigest()


def _source_value_digest(field: str, value: Any) -> str:
    """Hash a source locator without emitting the locator itself.

    The immutable dataset revision and a field-specific domain separator prevent
    accidental equality with ordinary row/content hashes while retaining exact
    reproducibility for provenance audits.
    """

    payload = {
        "domain": "px063-source-locator-v1",
        "dataset_revision": DEFAULT_HF_REVISION,
        "field": field,
        "value": value,
    }
    return sha256(canonical_json_bytes(payload)).hexdigest()


def blinded_record_id(
    row: Mapping[str, Any], *, revision: str = DEFAULT_HF_REVISION
) -> str:
    """Create the stable pseudonym used before and after decision sealing."""

    neutral_input = {
        "prompt": row.get("prompt"),
        "trajectory": coalesced_response(row),
    }
    identity = {
        "revision": revision,
        "source_row_idx": row.get("source_row_idx"),
        "source_id": row.get("source_id"),
        "neutral_input_sha256": sha256(canonical_json_bytes(neutral_input)).hexdigest(),
    }
    return "px063-" + sha256(canonical_json_bytes(identity)).hexdigest()[:24]


def parse_messages(raw: Any, *, field: str, source_id: Any) -> list[ParsedMessage]:
    """Parse and validate a normalized ChatML message list."""

    if not isinstance(raw, str) or not raw.strip():
        raise TraceDataError(f"{field} is missing for source_id={source_id!r}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TraceDataError(
            f"{field} is invalid JSON for source_id={source_id!r}: {exc.msg}"
        ) from exc
    if not isinstance(value, list) or not value:
        raise TraceDataError(f"{field} must be a non-empty JSON list for source_id={source_id!r}")

    parsed: list[ParsedMessage] = []
    for turn, message in enumerate(value):
        if not isinstance(message, dict):
            raise TraceDataError(
                f"{field}[{turn}] must be an object for source_id={source_id!r}"
            )
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not role:
            raise TraceDataError(
                f"{field}[{turn}].role is invalid for source_id={source_id!r}"
            )
        if not isinstance(content, str):
            raise TraceDataError(
                f"{field}[{turn}].content is invalid for source_id={source_id!r}"
            )
        structured = role not in {"system", "user", "assistant"} or any(
            key not in {"role", "content"} for key in message
        )
        parsed.append(
            ParsedMessage(
                role=role,
                content=content,
                turn=turn,
                field=field,
                has_structured_payload=structured,
            )
        )
    return parsed


def selected_response_field(row: Mapping[str, Any]) -> str:
    label = row.get("label")
    if label == "hacking":
        return "response_hacking"
    if label == "clean":
        return "response_clean"
    raise TraceDataError(
        f"Unsupported TRACE label {label!r} for source_id={row.get('source_id')!r}"
    )


def coalesced_response(row: Mapping[str, Any]) -> str:
    """Return the sole populated continuation without consulting the gold label."""

    populated = [
        value
        for field in ("response_hacking", "response_clean")
        if isinstance((value := row.get(field)), str) and value.strip()
    ]
    if len(populated) != 1:
        raise TraceDataError(
            f"Expected exactly one populated response for source_id={row.get('source_id')!r}; "
            f"found {len(populated)}"
        )
    return populated[0]


def recover_trace_label(
    row: Mapping[str, Any],
    *,
    allowed_atomic_codes: Collection[str] = FROZEN_TRACE_ATOMIC_CODES,
) -> str:
    """Recover and strictly validate the TRACE label retained by ``rh-bench``.

    Error messages are stable reason codes and never contain a source identifier
    or the rejected label value.
    """

    if row.get("label") == "clean":
        clean_description = row.get("hacking_description")
        if clean_description is not None and clean_description != "":
            raise TraceLabelError("clean_trace_code_not_exact_zero")
        return "0"
    if row.get("label") != "hacking":
        raise TraceLabelError("missing_binary_trace_label")

    description = row.get("hacking_description")
    prefix = "trace_labels="
    if not isinstance(description, str) or not description.startswith(prefix):
        raise TraceLabelError("missing_original_trace_label")
    recovered = description[len(prefix) :]
    if not recovered:
        raise TraceLabelError("empty_original_trace_label")
    codes = labels_from_codes(recovered, allowed_atomic_codes=allowed_atomic_codes)
    if codes == ("0",) or "0" in codes:
        raise TraceLabelError("hacking_trace_code_contains_clean_code")
    return recovered


def row_messages(row: Mapping[str, Any]) -> list[ParsedMessage]:
    """Return prompt plus the ground-truth continuation for one normalized row."""

    source_id = row.get("source_id")
    prompt = parse_messages(row.get("prompt"), field="prompt", source_id=source_id)
    response_field = selected_response_field(row)
    response = parse_messages(
        row.get(response_field), field=response_field, source_id=source_id
    )
    offset = len(prompt)
    response = [
        ParsedMessage(
            role=message.role,
            content=message.content,
            turn=message.turn + offset,
            field=message.field,
            has_structured_payload=message.has_structured_payload,
        )
        for message in response
    ]
    return prompt + response


def blind_trace_row(
    row: Mapping[str, Any], *, revision: str = DEFAULT_HF_REVISION
) -> BlindedTraceRow:
    """Remove gold metadata and response-side identity before inference."""

    prompt = row.get("prompt")
    trajectory = coalesced_response(row)
    # Validate before constructing the blinded in-memory representation.
    parse_messages(prompt, field="prompt", source_id=row.get("source_id"))
    parse_messages(trajectory, field="trajectory", source_id=row.get("source_id"))
    return BlindedTraceRow(
        record_id=blinded_record_id(row, revision=revision),
        prompt=str(prompt),
        trajectory=str(trajectory),
    )


def blinded_messages(row: BlindedTraceRow | Mapping[str, Any]) -> list[ParsedMessage]:
    """Parse a label-free prompt/trajectory pair."""

    if isinstance(row, BlindedTraceRow):
        prompt_raw = row.prompt
        trajectory_raw = row.trajectory
        record_id = row.record_id
    else:
        prompt_raw = row.get("prompt")
        trajectory_raw = row.get("trajectory")
        record_id = row.get("record_id")
    prompt = parse_messages(prompt_raw, field="prompt", source_id=record_id)
    response = parse_messages(trajectory_raw, field="trajectory", source_id=record_id)
    offset = len(prompt)
    return prompt + [
        ParsedMessage(
            role=message.role,
            content=message.content,
            turn=message.turn + offset,
            field=message.field,
            has_structured_payload=message.has_structured_payload,
        )
        for message in response
    ]


def safe_manifest_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a gold-free, trajectory-free provenance record."""

    return {
        "record_id": blinded_record_id(row),
        "row_sha256": canonical_row_hash(row),
    }


def validate_trace_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    allowed_trace_codes: Collection[str] = FROZEN_TRACE_ATOMIC_CODES,
) -> SourceGateArtifacts:
    """Validate the frozen source contract without returning raw trajectories."""

    labels: Counter[str] = Counter()
    source_ids: list[str] = []
    source_row_indices: list[int | None] = []
    failures: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    json_parse_failure_rows: set[str] = set()
    missing_response_rows: set[str] = set()
    missing_label_rows: set[str] = set()
    missing_trace_code_rows: set[str] = set()
    invalid_trace_code_rows: set[str] = set()
    dual_response_rows: set[str] = set()
    structured_rows: set[str] = set()

    for position, row in enumerate(rows):
        source_id = str(row.get("source_id") or "")
        row_digest = _source_value_digest(
            "row_locator",
            {
                "source_id": source_id or None,
                "source_row_idx": row.get("source_row_idx"),
                "source_position": position,
            },
        )
        source_ids.append(source_id)
        raw_row_index = row.get("source_row_idx")
        try:
            source_row_indices.append(int(raw_row_index))
        except (TypeError, ValueError):
            source_row_indices.append(None)
        label = row.get("label")
        if label not in {"hacking", "clean"}:
            missing_label_rows.add(row_digest)
        else:
            labels[str(label)] += 1
            active_field = "response_hacking" if label == "hacking" else "response_clean"
            inactive_field = "response_clean" if label == "hacking" else "response_hacking"
            if not row.get(active_field):
                missing_response_rows.add(row_digest)
            if row.get(inactive_field):
                dual_response_rows.add(row_digest)

        if row.get("source_dataset") != SOURCE_DATASET:
            failures.append(
                {
                    "row_digest": row_digest,
                    "field": "source_dataset",
                    "error": "unexpected_source_dataset",
                }
            )

        try:
            messages = row_messages(row)
            if any(message.has_structured_payload for message in messages):
                structured_rows.add(row_digest)
        except TraceDataError as exc:
            text = str(exc)
            if "missing" in text and "response_" in text:
                missing_response_rows.add(row_digest)
            else:
                json_parse_failure_rows.add(row_digest)
            failures.append(
                {
                    "row_digest": row_digest,
                    "field": "messages",
                    "error": type(exc).__name__,
                }
            )

        try:
            recover_trace_label(row, allowed_atomic_codes=allowed_trace_codes)
        except TraceLabelError as exc:
            if exc.reason in {
                "missing_original_trace_label",
                "empty_original_trace_label",
            }:
                missing_trace_code_rows.add(row_digest)
            else:
                invalid_trace_code_rows.add(row_digest)
            failures.append(
                {
                    "row_digest": row_digest,
                    "field": "trace_label",
                    "error": exc.reason,
                }
            )

        try:
            records.append(safe_manifest_record(row))
        except (TraceDataError, TypeError, ValueError) as exc:
            failures.append(
                {
                    "row_digest": row_digest,
                    "field": "manifest",
                    "error": type(exc).__name__,
                }
            )

    id_counts = Counter(source_ids)
    duplicate_ids = sorted(
        source_id for source_id, count in id_counts.items() if source_id and count > 1
    )
    missing_source_ids = sum(1 for source_id in source_ids if not source_id)
    row_index_counts = Counter(index for index in source_row_indices if index is not None)
    duplicate_row_indices = sorted(
        index for index, count in row_index_counts.items() if count > 1
    )
    missing_row_indices = sum(index is None for index in source_row_indices)
    records.sort(key=lambda item: item["record_id"])
    manifest_sha256 = sha256(canonical_json_bytes(records)).hexdigest()
    row_hash_counts = Counter(record["row_sha256"] for record in records)
    duplicate_row_hashes = sorted(
        digest for digest, count in row_hash_counts.items() if count > 1
    )

    expectations = {
        "row_count": len(rows) == EXPECTED_TRACE_ROWS,
        "hacking_count": labels.get("hacking", 0) == EXPECTED_HACKING_ROWS,
        "clean_count": labels.get("clean", 0) == EXPECTED_CLEAN_ROWS,
        "json_parse": not json_parse_failure_rows,
        "responses_present": not missing_response_rows,
        "response_side_unambiguous": not dual_response_rows,
        "labels_present": not missing_label_rows,
        "trace_codes_present": not missing_trace_code_rows,
        "trace_codes_valid": not invalid_trace_code_rows,
        "source_ids_unique": not duplicate_ids and missing_source_ids == 0,
        "source_row_indices_unique": not duplicate_row_indices and missing_row_indices == 0,
        "canonical_row_hashes_unique": not duplicate_row_hashes,
        "manifest_complete": len(records) == len(rows),
    }
    summary: dict[str, Any] = {
        "schema_version": "px063_source_integrity_summary_v1_5",
        "status": "PASS" if all(expectations.values()) and not failures else "FAIL",
        "rows": len(rows),
        "labels": {
            "hacking": labels.get("hacking", 0),
            "clean": labels.get("clean", 0),
        },
        "json_parse_failure_rows": len(json_parse_failure_rows),
        "missing_response_rows": len(missing_response_rows),
        "dual_response_rows": len(dual_response_rows),
        "missing_label_rows": len(missing_label_rows),
        "missing_trace_code_rows": len(missing_trace_code_rows),
        "invalid_trace_code_rows": len(invalid_trace_code_rows),
        "duplicate_source_ids": {
            "count": len(duplicate_ids),
            "digests": [
                _source_value_digest("source_id", source_id)
                for source_id in duplicate_ids
            ],
        },
        "missing_source_ids": missing_source_ids,
        "duplicate_source_row_indices": {
            "count": len(duplicate_row_indices),
            "digests": [
                _source_value_digest("source_row_idx", index)
                for index in duplicate_row_indices
            ],
        },
        "missing_source_row_indices": missing_row_indices,
        "duplicate_canonical_row_hashes": {
            "count": len(duplicate_row_hashes),
            "digests": duplicate_row_hashes,
        },
        "structured_tool_payload_rows": len(structured_rows),
        "manifest_sha256": manifest_sha256,
        "expectations": expectations,
        "failure_count": len(failures),
        "source_limitation": (
            "The normalized rows contain ChatML role/content text. A zero value for "
            "structured_tool_payload_rows means execution and filesystem effects are not "
            "independently verified by this derivative."
        ),
    }
    return SourceGateArtifacts(summary=summary, records=records, failures=failures)


def load_trace_rows(*, revision: str = DEFAULT_HF_REVISION) -> list[dict[str, Any]]:
    """Load only the pinned TRACE-derived rows from the public normalization."""

    from datasets import load_dataset

    dataset = load_dataset(
        DATASET_ID,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
        revision=revision,
    )
    return [
        dict(row)
        for row in dataset
        if row.get("source_dataset") == SOURCE_DATASET
    ]


def labels_from_codes(
    value: str,
    *,
    allowed_atomic_codes: Collection[str] = FROZEN_TRACE_ATOMIC_CODES,
) -> tuple[str, ...]:
    """Parse a TRACE composite label under the frozen atomic-code taxonomy."""

    if not isinstance(value, str) or value != value.strip():
        raise TraceLabelError("invalid_trace_label_syntax")
    if value == "0":
        return ("0",)
    parts = value.split(",")
    if not parts or any(not part.strip() for part in parts):
        raise TraceLabelError("invalid_trace_label_syntax")
    codes = tuple(part.strip() for part in parts)
    if "0" in codes:
        raise TraceLabelError("hacking_trace_code_contains_clean_code")
    if len(set(codes)) != len(codes):
        raise TraceLabelError("duplicate_trace_atomic_code")
    if any(code not in allowed_atomic_codes for code in codes):
        raise TraceLabelError("unknown_trace_atomic_code")
    return codes
