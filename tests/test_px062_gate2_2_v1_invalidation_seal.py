from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import seal_px062_gate2_2_v1_invalidation as seal


def test_canonical_conflict_ledger_is_complete_and_row_hashed() -> None:
    conflicts, raw, aggregates = seal.build_conflicts(seal.ROOT)

    assert len(conflicts) == 33
    assert raw.count(b"\n") == 33
    assert seal.sha256_bytes(raw) == (
        "5b899e78cac1ee60c7fafbe37088c3ce58221c6f55680964235b896b1fc91c0c"
    )
    assert aggregates == {
        **seal.EXPECTED_AGGREGATES,
        "by_task_type": seal.EXPECTED_TASK_TYPE_COUNTS,
    }

    observed_task_ids: set[str] = set()
    class_counts = {
        "AUDITORS_DISAGREE": 0,
        "BOTH_AUDITORS_SAME_ALTERNATIVE": 0,
    }
    for line, row in zip(raw.splitlines(), conflicts, strict=True):
        assert json.loads(line) == row
        assert row["task_id"] not in observed_task_ids
        observed_task_ids.add(row["task_id"])
        payload = {key: value for key, value in row.items() if key != "canonical_row_sha256"}
        assert row["canonical_row_sha256"] == seal.sha256_bytes(
            seal.canonical_json_bytes(payload)
        )
        assert len(row["prompt_sha256"]) == 64
        assert set(row["audit_1"]) == {"predicted_skill", "confidence", "note"}
        assert set(row["audit_2"]) == {"predicted_skill", "confidence", "note"}
        class_counts[row["conflict_class"]] += 1
    assert class_counts == {
        "AUDITORS_DISAGREE": 19,
        "BOTH_AUDITORS_SAME_ALTERNATIVE": 14,
    }


def test_pair_manifest_binds_all_artifacts_and_sessions() -> None:
    _, raw = seal.validate_sealed_file(seal.ROOT, "audit_pair_manifest")
    summary = seal.validate_pair_manifest(seal.ROOT, raw)

    assert summary == {
        "artifact_count": 438,
        "artifact_bytes": 6_096_000,
        "artifact_inventory_sha256": (
            "737d16a4a4dd9443908eb7305d34640dde699e56c0b6e005795718c730324344"
        ),
        "accepted_session_count": 86,
        "accepted_session_ids_sha256": (
            "b07b136223e75597799d57c66384ba7a3a200c6c913b3ce006244933eec45139"
        ),
    }


def test_canonical_outputs_are_byte_deterministic_without_reprobing_finalizer() -> None:
    invalidation_raw, conflicts_raw = seal.build_outputs(
        seal.ROOT, probe_finalizer=False
    )

    assert invalidation_raw == (seal.ROOT / seal.INVALIDATION).read_bytes()
    assert conflicts_raw == (seal.ROOT / seal.CONFLICTS).read_bytes()
    assert seal.sha256_bytes(invalidation_raw) == (
        "3c0a3d83877ea2eb5b8fc829e92cd9661b72ac5cf8c016ae145a5fd3dd3a9e42"
    )
    parsed = json.loads(invalidation_raw)
    assert parsed["semantic_gate"]["status"] == "FAIL"
    assert parsed["resolution_absence"]["provisional"]["exists"] is False
    assert parsed["resolution_absence"]["final"]["exists"] is False
    assert parsed["finalizer_check"]["exit_semantics"] == {
        "exception_type": "ValueError",
        "message": seal.EXPECTED_FINALIZER_ERROR,
        "cli_exit_code": 1,
        "terminal_stderr_line": (
            "ValueError: label audits do not unanimously support the answer key"
        ),
    }


def test_pinned_file_validation_fails_closed_on_byte_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "sealed.bin"
    original = b"sealed evidence\n"
    path.write_bytes(original)
    monkeypatch.setitem(
        seal.SEALED_FILES,
        "probe",
        ("sealed.bin", len(original), seal.sha256_bytes(original)),
    )
    assert seal.validate_sealed_file(tmp_path, "probe")[1] == original

    path.write_bytes(b"changed evidence\n")
    with pytest.raises(seal.SealError, match="sealed file changed"):
        seal.validate_sealed_file(tmp_path, "probe")


def test_real_finalizer_fails_before_writing_resolution() -> None:
    result = seal.validate_finalizer_failure(seal.ROOT)

    assert result["exit_semantics"]["cli_exit_code"] == 1
    assert result["exit_semantics"]["message"] == seal.EXPECTED_FINALIZER_ERROR
    assert result["provisional_resolution_written"] is False
    assert result["final_resolution_written"] is False
    assert not (seal.ROOT / seal.PROVISIONAL_RESOLUTION).exists()
    assert not (seal.ROOT / seal.FINAL_RESOLUTION).exists()
