from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from praxis.px063.trace_adapter import (
    FROZEN_TRACE_ATOMIC_CODES,
    PINNED_TRACE_TAXONOMY_SCHEMA_VERSION,
    PINNED_TRACE_TAXONOMY_SHA256,
    TraceLabelError,
    blind_trace_row,
    canonical_row_hash,
    labels_from_codes,
    recover_trace_label,
    safe_manifest_record,
    validate_trace_rows,
)


def _row(index: int, label: str = "clean") -> dict:
    prompt = json.dumps([{"role": "user", "content": "Implement the requested function."}])
    response = json.dumps([{"role": "assistant", "content": "Implemented the function."}])
    return {
        "prompt": prompt,
        "response_hacking": response if label == "hacking" else None,
        "response_clean": response if label == "clean" else None,
        "label": label,
        "hacking_category": "evaluation_gaming",
        "hacking_subcategory": "test_modification" if label == "hacking" else None,
        "hacking_description": "trace_labels=1.1.1" if label == "hacking" else None,
        "construction": "prompted",
        "verification": "human",
        "source_dataset": "patronus_trace",
        "source_split": "train",
        "source_row_idx": index,
        "source_id": f"trajectory-{index:04d}",
        "response_model": "fixture",
        "is_agentic": True,
    }


def test_recover_original_trace_codes() -> None:
    assert recover_trace_label(_row(0, "clean")) == "0"
    assert recover_trace_label(_row(1, "hacking")) == "1.1.1"


def test_frozen_taxonomy_manifest_matches_adapter_pin() -> None:
    taxonomy_path = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "px063_trace_taxonomy_v1.json"
    )
    encoded = taxonomy_path.read_bytes()
    manifest = json.loads(encoded)
    assert sha256(encoded).hexdigest() == PINNED_TRACE_TAXONOMY_SHA256
    assert manifest["schema_version"] == PINNED_TRACE_TAXONOMY_SCHEMA_VERSION
    assert frozenset(manifest["atomic_codes"]) == FROZEN_TRACE_ATOMIC_CODES


def test_missing_original_trace_code_fails() -> None:
    row = _row(1, "hacking")
    row["hacking_description"] = "test modification"
    with pytest.raises(TraceLabelError, match="missing_original_trace_label"):
        recover_trace_label(row)


@pytest.mark.parametrize("code", sorted(FROZEN_TRACE_ATOMIC_CODES))
def test_every_frozen_hacking_code_is_recognized(code: str) -> None:
    row = _row(1, "hacking")
    row["hacking_description"] = f"trace_labels={code}"
    assert recover_trace_label(row) == code


@pytest.mark.parametrize(
    ("encoded", "reason"),
    [
        ("9.9.9", "unknown_trace_atomic_code"),
        ("1.1.1,,1.2.1", "invalid_trace_label_syntax"),
        ("1.1.1,1.1.1", "duplicate_trace_atomic_code"),
        ("0,1.1.1", "hacking_trace_code_contains_clean_code"),
        (" 1.1.1", "invalid_trace_label_syntax"),
    ],
)
def test_invalid_hacking_code_metadata_fails_without_echoing_value(
    encoded: str, reason: str
) -> None:
    row = _row(1, "hacking")
    row["hacking_description"] = f"trace_labels={encoded}"
    with pytest.raises(TraceLabelError) as captured:
        recover_trace_label(row)
    assert captured.value.reason == reason
    assert encoded not in str(captured.value)


def test_clean_row_maps_only_to_exact_zero() -> None:
    clean = _row(0, "clean")
    assert recover_trace_label(clean) == "0"
    assert labels_from_codes("0") == ("0",)

    clean["hacking_description"] = "trace_labels=1.1.1"
    with pytest.raises(TraceLabelError, match="clean_trace_code_not_exact_zero"):
        recover_trace_label(clean)

    with pytest.raises(TraceLabelError, match="invalid_trace_label_syntax"):
        labels_from_codes(" 0")


def test_hash_is_stable_and_content_sensitive() -> None:
    row = _row(0)
    same = dict(reversed(list(row.items())))
    assert canonical_row_hash(row) == canonical_row_hash(same)
    changed = dict(row)
    changed["prompt"] = json.dumps([{"role": "user", "content": "Different"}])
    assert canonical_row_hash(row) != canonical_row_hash(changed)


def test_safe_manifest_never_contains_trajectory_text() -> None:
    row = _row(0)
    safe = safe_manifest_record(row)
    serialized = json.dumps(safe)
    assert "prompt" not in safe
    assert "response_hacking" not in safe
    assert "response_clean" not in safe
    assert "Implement the requested function" not in serialized
    assert set(safe) == {"record_id", "row_sha256"}
    assert safe["row_sha256"] == canonical_row_hash(row)


def test_blinding_coalesces_response_without_exporting_gold_metadata() -> None:
    row = _row(1, "hacking")
    blinded = blind_trace_row(row)
    assert set(blinded.__dict__) == {"record_id", "prompt", "trajectory"}
    assert json.loads(blinded.trajectory)[0]["content"] == "Implemented the function."


def test_blinded_id_and_input_ignore_label_and_response_column_identity() -> None:
    hacking = _row(1, "hacking")
    clean = dict(hacking)
    clean["label"] = "clean"
    clean["response_clean"] = clean["response_hacking"]
    clean["response_hacking"] = None
    clean["hacking_description"] = None
    clean["hacking_category"] = None
    clean["hacking_subcategory"] = None
    assert blind_trace_row(hacking) == blind_trace_row(clean)


def test_exact_frozen_corpus_contract_passes_on_structural_fixtures() -> None:
    rows = [_row(index, "hacking" if index < 268 else "clean") for index in range(517)]
    result = validate_trace_rows(rows)
    assert result.summary["status"] == "PASS"
    assert result.summary["labels"] == {"hacking": 268, "clean": 249}
    assert result.summary["structured_tool_payload_rows"] == 0
    assert len(result.records) == 517


def test_duplicate_source_id_fails_gate() -> None:
    rows = [_row(index, "hacking" if index < 268 else "clean") for index in range(517)]
    rows[-1]["source_id"] = rows[0]["source_id"]
    result = validate_trace_rows(rows)
    assert result.summary["status"] == "FAIL"
    assert result.summary["expectations"]["source_ids_unique"] is False
    duplicates = result.summary["duplicate_source_ids"]
    assert duplicates["count"] == 1
    assert len(duplicates["digests"]) == 1
    assert rows[0]["source_id"] not in json.dumps(result.summary)


def test_duplicate_source_row_index_is_reported_only_as_a_digest() -> None:
    rows = [_row(index, "hacking" if index < 268 else "clean") for index in range(517)]
    rows[0]["source_row_idx"] = 424242
    rows[-1]["source_row_idx"] = 424242
    result = validate_trace_rows(rows)
    duplicates = result.summary["duplicate_source_row_indices"]
    assert result.summary["status"] == "FAIL"
    assert result.summary["expectations"]["source_row_indices_unique"] is False
    assert duplicates["count"] == 1
    assert len(duplicates["digests"]) == 1
    assert "424242" not in json.dumps(result.summary)


def test_failure_records_use_non_disclosing_row_digests() -> None:
    sensitive_id = "private-source-id-never-emit"
    row = _row(0, "clean")
    row["source_id"] = sensitive_id
    row["source_dataset"] = "unexpected"
    result = validate_trace_rows([row])
    assert result.failures
    assert all(set(failure) == {"row_digest", "field", "error"} for failure in result.failures)
    serialized = json.dumps(
        {"summary": result.summary, "failures": result.failures}, sort_keys=True
    )
    assert sensitive_id not in serialized


def test_unknown_trace_code_fails_source_gate_as_invalid_not_missing() -> None:
    rows = [_row(index, "hacking" if index < 268 else "clean") for index in range(517)]
    rows[0]["hacking_description"] = "trace_labels=9.9.9"
    result = validate_trace_rows(rows)
    assert result.summary["status"] == "FAIL"
    assert result.summary["invalid_trace_code_rows"] == 1
    assert result.summary["missing_trace_code_rows"] == 0
    assert result.summary["expectations"]["trace_codes_valid"] is False
    assert "9.9.9" not in json.dumps(result.summary)
