from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts import run_px062_gate2_2_blind_audit as core_audit_runner
from scripts import seal_px062_gate2_2_v12_invalidation as seal


EXPECTED_INVALIDATION_SHA256 = (
    "dc9a66283ad4a0a7cd7e5fd384f4d369232018aef1e4431bc2073cf8e23728fa"
)
EXPECTED_CONFLICTS_SHA256 = (
    "76188a8817ef236ef0a9afe7859d4e28546e08df388a5a553a337c6143780693"
)


def test_canonical_conflict_ledger_is_complete_and_row_hashed() -> None:
    conflicts, raw, aggregates = seal.build_conflicts(seal.ROOT)

    assert len(conflicts) == 9
    assert raw.count(b"\n") == 9
    assert seal.sha256_bytes(raw) == EXPECTED_CONFLICTS_SHA256
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
        payload = {
            key: value
            for key, value in row.items()
            if key != "canonical_row_sha256"
        }
        assert row["canonical_row_sha256"] == seal.sha256_bytes(
            seal.canonical_json_bytes(payload)
        )
        assert len(row["prompt_sha256"]) == 64
        assert set(row["audit_1"]) == {"predicted_skill", "confidence", "note"}
        assert set(row["audit_2"]) == {"predicted_skill", "confidence", "note"}
        class_counts[row["conflict_class"]] += 1
    assert class_counts == {
        "AUDITORS_DISAGREE": 9,
        "BOTH_AUDITORS_SAME_ALTERNATIVE": 0,
    }


def test_pair_manifest_binds_all_artifacts_and_sessions() -> None:
    _, raw = seal.validate_sealed_file(seal.ROOT, "audit_pair_manifest")
    summary = seal.validate_pair_manifest(seal.ROOT, raw)

    assert summary == {
        "artifact_count": 438,
        "artifact_bytes": 6_007_630,
        "artifact_inventory_sha256": (
            "07b8997e36e1bc37fdc0b6bba7fae1d3841afe78557bb63f5cd3819f165652e5"
        ),
        "accepted_session_count": 86,
        "accepted_session_ids_sha256": (
            "6e7003b6266549e81f9e7fc0bc3653e55b02bdfe22c7b611d0f3c201e189aaba"
        ),
    }


def test_historical_pair_passes_at_checkpoint_or_descendant_head() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=seal.ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", seal.REPOSITORY_CHECKPOINT, head],
        cwd=seal.ROOT,
        check=False,
    )

    assert head == seal.REPOSITORY_CHECKPOINT or ancestry.returncode == 0
    reconstructed = seal.historical_pair_verifier(seal.ROOT)
    sealed = json.loads((seal.ROOT / seal.PAIR_MANIFEST).read_bytes())
    assert reconstructed == sealed


def test_historical_pair_rejects_prediction_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = (seal.ROOT / seal.SEALED_FILES["audit_1_predictions"][0]).resolve()
    original_read_bytes = Path.read_bytes

    def tampered_read_bytes(path: Path) -> bytes:
        raw = original_read_bytes(path)
        if path.resolve() == target:
            return raw[:-1] + b" "
        return raw

    monkeypatch.setattr(Path, "read_bytes", tampered_read_bytes)
    with pytest.raises(
        seal.SealError, match="historical audit-pair authentication failed"
    ):
        seal.historical_pair_verifier(seal.ROOT)


def test_historical_pair_rejects_non_ancestry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_git = core_audit_runner._git

    def non_ancestor_git(root: Path, *args: str) -> str:
        if args[:2] == ("merge-base", "--is-ancestor"):
            raise core_audit_runner.AuditError("simulated non-ancestor")
        return original_git(root, *args)

    monkeypatch.setattr(core_audit_runner, "_git", non_ancestor_git)
    with pytest.raises(
        seal.SealError, match="historical audit-pair authentication failed"
    ) as captured:
        seal.historical_pair_verifier(seal.ROOT)
    assert isinstance(captured.value.__cause__, core_audit_runner.AuditError)
    assert "historical checkpoint is not an ancestor" in str(captured.value.__cause__)


def test_canonical_outputs_are_byte_deterministic_without_reprobing() -> None:
    invalidation_raw, conflicts_raw = seal.build_outputs(
        seal.ROOT, probe_rejectors=False
    )

    assert invalidation_raw == (seal.ROOT / seal.INVALIDATION).read_bytes()
    assert conflicts_raw == (seal.ROOT / seal.CONFLICTS).read_bytes()
    assert seal.sha256_bytes(invalidation_raw) == EXPECTED_INVALIDATION_SHA256
    parsed = json.loads(invalidation_raw)
    assert parsed["semantic_gate"] == {
        "status": "FAIL",
        "rows": 1032,
        "three_way_unanimous_rows": 1023,
        "three_way_unanimous_rate": 1023 / 1032,
        "cross_audit_agreement_rows": 1023,
        **seal.EXPECTED_AGGREGATES,
        "by_task_type": seal.EXPECTED_TASK_TYPE_COUNTS,
    }
    assert parsed["resolution_absence"]["provisional"]["exists"] is False
    assert parsed["resolution_absence"]["final"]["exists"] is False
    assert parsed["target_execution_absence"][
        "qwen_or_mistral_gate2_2_collection_launched"
    ] is False
    assert parsed["target_execution_absence"][
        "aws_gate2_2_training_job_launched"
    ] is False


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


def test_target_execution_absence_fails_closed(tmp_path: Path) -> None:
    collection = tmp_path / seal.TARGET_EXECUTION_PATHS["collection_output_dir"]
    collection.mkdir(parents=True)

    with pytest.raises(seal.SealError, match="target-execution artifact exists"):
        seal.validate_target_execution_absence(tmp_path)
