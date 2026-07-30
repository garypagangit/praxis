from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import seal_px062_gate2_2_v13_invalidation as seal


EXPECTED_INVALIDATION_SHA256 = (
    "8878a20c6fedda90f28721f26f7f370576a018f2892c4309ae1fb43a3f498e43"
)
EXPECTED_CONFLICTS_SHA256 = (
    "c2f8de446ca40552106116ea3875313b352864242a65e0ede99bef30832b439b"
)
EXPECTED_REPORT_SHA256 = (
    "eb03705ad498de71aadd7d6a3a846f7d4e186a22a10bb008be3d4271d259cdf1"
)


def test_canonical_nonunanimous_ledger_is_complete_and_row_hashed() -> None:
    rows, raw, semantic = seal.build_diagnostics(seal.ROOT)

    assert len(rows) == 9
    assert raw.count(b"\n") == 9
    assert seal.sha256_bytes(raw) == EXPECTED_CONFLICTS_SHA256
    assert semantic["unanimous_key_rows"] == 1023
    assert semantic["single_dissent_rows"] == 8
    assert semantic["accepted_rows"] == 1031
    assert semantic["rejected_rows"] == 1
    assert semantic["rejected_task_ids"] == [seal.EXPECTED_REJECTED_ID]
    assert semantic["all_labels_balanced_consensus_accepted"] is False
    assert semantic["nonunanimous_outcome_counts"] == {
        "ACCEPTED_SINGLE_DISSENT": 8,
        "REJECTED_BALANCED_CONSENSUS": 1,
    }

    observed_ids: set[str] = set()
    outcomes = {
        "ACCEPTED_SINGLE_DISSENT": 0,
        "REJECTED_BALANCED_CONSENSUS": 0,
    }
    for line, row in zip(raw.splitlines(), rows, strict=True):
        assert json.loads(line) == row
        assert row["task_id"] not in observed_ids
        observed_ids.add(row["task_id"])
        payload = {
            key: value for key, value in row.items() if key != "canonical_row_sha256"
        }
        assert row["canonical_row_sha256"] == seal.sha256_bytes(
            seal.canonical_json_bytes(payload)
        )
        assert len(row["prompt_sha256"]) == 64
        assert [item["slot"] for item in row["audits"]] == [1, 2, 3, 4]
        outcomes[row["consensus_outcome"]] += 1
    assert outcomes == {
        "ACCEPTED_SINGLE_DISSENT": 8,
        "REJECTED_BALANCED_CONSENSUS": 1,
    }

    rejected = next(
        row
        for row in rows
        if row["consensus_outcome"] == "REJECTED_BALANCED_CONSENSUS"
    )
    assert rejected["task_id"] == seal.EXPECTED_REJECTED_ID
    assert rejected["expected_skill"] == "linear"
    assert [item["predicted_skill"] for item in rejected["audits"]] == [
        None,
        "linear",
        None,
        "linear",
    ]
    assert rejected["key_vote_count"] == 2
    assert rejected["key_support_from_sol"] is False
    assert rejected["key_support_from_terra"] is True


def test_historical_consensus_binds_complete_inventory_and_sessions() -> None:
    _, raw = seal.validate_sealed_file(seal.ROOT, "consensus_manifest")
    summary = seal.validate_consensus_manifest(seal.ROOT, raw)

    assert summary == {
        "artifact_count": 873,
        "artifact_bytes": 10_151_496,
        "per_attempt_raw_evidence_files": 860,
        "artifact_inventory_sha256": seal.EXPECTED_ARTIFACT_INVENTORY_SHA256,
        "accepted_session_count": 172,
        "all_attempt_count": 172,
        "retry_attempt_count": 0,
        "accepted_session_ids_sha256": seal.EXPECTED_SESSION_BINDING_SHA256,
        "repository_checkpoint_sha256": seal.EXPECTED_CHECKPOINT_SHA256,
        "tracked_checkpoint_files": 19,
    }

    reconstructed = seal.historical_consensus_verifier(seal.ROOT)
    manifest = json.loads((seal.ROOT / seal.CONSENSUS_MANIFEST).read_bytes())
    assert reconstructed == manifest


def test_canonical_outputs_and_report_are_byte_deterministic() -> None:
    invalidation_raw, conflicts_raw, report_raw = seal.build_outputs(
        seal.ROOT, probe_rejectors=False
    )

    assert invalidation_raw == (seal.ROOT / seal.INVALIDATION).read_bytes()
    assert conflicts_raw == (seal.ROOT / seal.CONFLICTS).read_bytes()
    assert report_raw == (seal.ROOT / seal.REPORT).read_bytes()
    assert seal.sha256_bytes(invalidation_raw) == EXPECTED_INVALIDATION_SHA256
    assert seal.sha256_bytes(conflicts_raw) == EXPECTED_CONFLICTS_SHA256
    assert seal.sha256_bytes(report_raw) == EXPECTED_REPORT_SHA256

    parsed = json.loads(invalidation_raw)
    assert parsed["repository_checkpoint"] == {
        "commit": seal.REPOSITORY_CHECKPOINT,
        "canonical_checkpoint_sha256": seal.EXPECTED_CHECKPOINT_SHA256,
        "historical_authentication": "PASS",
    }
    assert parsed["sealed_audit_evidence"]["artifact_count"] == 873
    assert parsed["sealed_audit_evidence"]["accepted_session_count"] == 172
    assert parsed["sealed_audit_evidence"]["retry_attempt_count"] == 0
    assert parsed["semantic_gate"]["accepted_rows"] == 1031
    assert parsed["semantic_gate"]["rejected_rows"] == 1
    assert parsed["required_disposition"][
        "benchmark_version_1_3_valid_for_model_collection"
    ] is False
    assert EXPECTED_INVALIDATION_SHA256.encode("ascii") in report_raw
    assert EXPECTED_CONFLICTS_SHA256.encode("ascii") in report_raw


def test_real_verifier_and_finalizer_fail_before_resolution_write() -> None:
    verifier = seal.validate_verifier_failure(seal.ROOT)
    finalizer = seal.validate_finalizer_failure(seal.ROOT)

    for result in (verifier, finalizer):
        assert result["exit_semantics"]["cli_exit_code"] == 1
        assert result["exit_semantics"]["message"] == seal.EXPECTED_FAILURE
        assert result["provisional_resolution_written"] is False
        assert result["final_resolution_written"] is False
    assert not (seal.ROOT / seal.PROVISIONAL_RESOLUTION).exists()
    assert not (seal.ROOT / seal.FINAL_RESOLUTION).exists()


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


def test_historical_consensus_rejects_prediction_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import run_px062_gate2_2_v13_blind_audit as audit_runner

    target = (seal.ROOT / seal.SEALED_FILES["audit_1_predictions"][0]).resolve()
    original_sha256_file = audit_runner.sha256_file

    def tampered_sha256_file(path: Path) -> str:
        if path.resolve() == target:
            return "0" * 64
        return original_sha256_file(path)

    monkeypatch.setattr(audit_runner, "sha256_file", tampered_sha256_file)
    with pytest.raises(seal.SealError, match="historical four-pass authentication failed"):
        seal.historical_consensus_verifier(seal.ROOT)


def test_target_execution_absence_fails_closed(tmp_path: Path) -> None:
    collection = tmp_path / seal.TARGET_EXECUTION_PATHS["collection_output_dir"]
    collection.mkdir(parents=True)

    with pytest.raises(seal.SealError, match="target-execution artifact exists"):
        seal.validate_target_execution_absence(tmp_path)
