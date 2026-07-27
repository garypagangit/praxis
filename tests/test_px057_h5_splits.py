from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import prepare_px057_h5_splits as splits


ROOT = Path(__file__).resolve().parents[1]


def _row(index: int) -> dict[str, object]:
    return {
        "question_id": f"q-{index:03d}",
        "domain": "synthetic",
        "value": index,
    }


def _metadata(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "rows": len(rows),
        "sha256": splits.sha256_bytes(splits.jsonl_bytes(rows)),
        "id_sha256": splits.ordered_id_sha256(rows),
    }


def test_frozen_h4_evidence_proves_exact_generated_sets() -> None:
    evidence = splits.verify_h4_evidence(ROOT)

    assert len(evidence.gate2_rows) == 200
    assert len(evidence.generated_ids["gsm8k"]) == 500
    assert len(evidence.generated_ids["arc_challenge"]) == 500
    assert len(evidence.holdout_ids["gsm8k"]) == 300
    assert len(evidence.holdout_ids["arc_challenge"]) == 300
    assert evidence.generated_ids["gsm8k"] == {
        str(row["question_id"])
        for row in evidence.calibration_rows["gsm8k"]
    }
    assert evidence.generated_ids["arc_challenge"] == {
        str(row["question_id"])
        for row in evidence.calibration_rows["arc_challenge"]
    }
    assert not (
        evidence.generated_ids["gsm8k"]
        & {str(row["question_id"]) for row in evidence.gate2_rows}
    )
    assert not (
        evidence.generated_ids["gsm8k"] & evidence.holdout_ids["gsm8k"]
    )
    assert not (
        evidence.generated_ids["arc_challenge"]
        & evidence.holdout_ids["arc_challenge"]
    )


def test_audited_hashes_and_residual_design_are_exact() -> None:
    assert splits.H4_CALIBRATION["gsm8k"]["sha256"] == (
        "a48ef2c73edc6eec80428358feee3f38e1c5182dac441ca39c339fb9b54f00ef"
    )
    assert splits.H4_CALIBRATION["arc_challenge"]["sha256"] == (
        "90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224"
    )
    assert splits.EXPECTED_ARTIFACTS["gsm8k"]["residual"] == {
        "rows": 619,
        "sha256": "fb47377f64bef1c018ccd1e8d8b7adb23fd908e7b1cfdef60570632ff5f38c21",
        "id_sha256": "76aace9d9b2040295a90ec4f7b8c9e95a24b70b827e8b3a63e48045ffbf1c2f2",
    }
    assert splits.EXPECTED_ARTIFACTS["arc_challenge"]["residual"] == {
        "rows": 672,
        "sha256": "050b413597cc7892ac980ec5e47c242657d8969e2aac0b509ac034753ec847d8",
        "id_sha256": "2f4102f1dccef965ef2d6c72331495192ca93f173b1f8876059ffa947992c617",
    }
    assert splits.SPLIT_SPECS == {
        "gsm8k": {"calibration": 435, "holdout": 150, "unused": 34},
        "arc_challenge": {"calibration": 489, "holdout": 150, "unused": 33},
    }
    assert (
        splits.CALIBRATION_SEED,
        splits.HOLDOUT_SEED,
        splits.UNUSED_SEED,
    ) == (5751, 5752, 5753)


def test_partition_residual_is_deterministic_disjoint_and_uses_all_seeds() -> None:
    residual = [_row(index) for index in range(30)]
    result = splits.partition_residual(
        residual,
        calibration_n=12,
        holdout_n=10,
        unused_n=8,
    )

    expected_calibration = splits.hash_rank(residual, 5751)[:12]
    calibration_ids = {row["question_id"] for row in expected_calibration}
    after_calibration = [
        row for row in residual if row["question_id"] not in calibration_ids
    ]
    expected_holdout = splits.hash_rank(after_calibration, 5752)[:10]
    holdout_ids = {row["question_id"] for row in expected_holdout}
    expected_unused = splits.hash_rank(
        [row for row in after_calibration if row["question_id"] not in holdout_ids],
        5753,
    )

    assert result["calibration"] == expected_calibration
    assert result["holdout"] == expected_holdout
    assert result["unused"] == expected_unused
    id_sets = [
        {str(row["question_id"]) for row in result[name]}
        for name in ("calibration", "holdout", "unused")
    ]
    assert not (id_sets[0] & id_sets[1])
    assert not (id_sets[0] & id_sets[2])
    assert not (id_sets[1] & id_sets[2])
    assert set().union(*id_sets) == {
        str(row["question_id"]) for row in residual
    }
    assert result == splits.partition_residual(
        residual,
        calibration_n=12,
        holdout_n=10,
        unused_n=8,
    )


def test_partition_residual_fails_closed_on_duplicates_or_bad_sizes() -> None:
    rows = [_row(index) for index in range(10)]
    with pytest.raises(ValueError, match="duplicate question_id"):
        splits.partition_residual(
            rows + [dict(rows[0])],
            calibration_n=5,
            holdout_n=3,
            unused_n=3,
        )
    with pytest.raises(ValueError, match="must exhaust"):
        splits.partition_residual(
            rows,
            calibration_n=5,
            holdout_n=3,
            unused_n=1,
        )


def test_residual_population_subtracts_exactly_500_generated_ids() -> None:
    population = [_row(index) for index in range(510)]
    generated = [str(row["question_id"]) for row in population[:500]]
    residual = splits.residual_population(
        population,
        generated,
        expected_n=10,
        label="synthetic",
    )
    assert residual == population[500:]

    with pytest.raises(ValueError, match="exactly 500"):
        splits.residual_population(
            population,
            generated[:-1],
            expected_n=11,
            label="synthetic",
        )
    with pytest.raises(ValueError, match="outside"):
        splits.residual_population(
            population,
            generated[:-1] + ["not-in-source"],
            expected_n=10,
            label="synthetic",
        )


def test_expected_artifact_check_rejects_one_changed_row(monkeypatch) -> None:
    residual = [_row(index) for index in range(8)]
    partitions = splits.partition_residual(
        residual,
        calibration_n=3,
        holdout_n=3,
        unused_n=2,
        calibration_seed=11,
        holdout_seed=12,
        unused_seed=13,
    )
    expected = {
        "residual": _metadata(residual),
        **{name: _metadata(rows) for name, rows in partitions.items()},
    }
    monkeypatch.setitem(splits.EXPECTED_ARTIFACTS, "synthetic", expected)
    splits.verify_expected_artifacts("synthetic", residual, partitions)

    changed = {name: list(rows) for name, rows in partitions.items()}
    changed["calibration"][0] = {
        **changed["calibration"][0],
        "value": -1,
    }
    with pytest.raises(ValueError, match="audited expected artifact"):
        splits.verify_expected_artifacts("synthetic", residual, changed)


def test_hash_bound_reader_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "artifact.jsonl"
    original = b'{"question_id":"q-1"}\n'
    path.write_bytes(original)
    expected = hashlib.sha256(original).hexdigest()
    assert splits._read_hash_bound(path, expected) == original

    path.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        splits._read_hash_bound(path, expected)


def test_writer_uses_only_new_caller_path_and_refuses_h4(
    tmp_path: Path, monkeypatch
) -> None:
    rows = {
        "calibration": tuple([_row(1)]),
        "holdout": tuple([_row(2)]),
        "unused": tuple([_row(3)]),
    }
    monkeypatch.setitem(
        splits.EXPECTED_ARTIFACTS,
        "gsm8k",
        {
            "residual": _metadata([_row(1), _row(2), _row(3)]),
            **{name: _metadata(list(value)) for name, value in rows.items()},
        },
    )
    bundle = splits.PreparedSplitBundle(
        rows={"gsm8k": rows},
        freeze={"stage": "test", "files": {}},
    )
    output = tmp_path / "caller-selected-h5-draft"
    result = splits.write_split_bundle(bundle, output, repo_root=ROOT)

    assert result["status"] == "DRAFT_WRITTEN_NOT_AUTHORIZED_FOR_GENERATION"
    assert {path.name for path in output.iterdir()} == {
        "gsm8k_calibration.jsonl",
        "gsm8k_holdout.jsonl",
        "gsm8k_unused.jsonl",
        "split_freeze.json",
    }
    with pytest.raises(FileExistsError):
        splits.write_split_bundle(bundle, output, repo_root=ROOT)

    protected = ROOT / "manifests/px057_h4_20260725/never-write-h5-draft"
    assert not protected.exists()
    with pytest.raises(ValueError, match="protected H4"):
        splits.write_split_bundle(bundle, protected, repo_root=ROOT)
    assert not protected.exists()


def test_wrong_source_bytes_fail_before_parsing() -> None:
    with pytest.raises(ValueError, match="source hash mismatch"):
        splits.build_gsm8k_population(b"not the pinned source", [])
    with pytest.raises(ValueError, match="source hash mismatch"):
        splits.build_arc_population(b"not the pinned source")
