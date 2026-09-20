from __future__ import annotations

import csv
import hashlib
import json

from experiments.apt_benchmark.qualify_capture import EXPECTED_COLUMNS, qualify_file


def fixture(tmp_path, rows):
    path = tmp_path / "train_set_reduced.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{c: "" for c in EXPECTED_COLUMNS}, **row})
    receipt = {"file": path.name, "bytes": path.stat().st_size,
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    path.with_name(path.name + ".receipt.json").write_text(json.dumps(receipt))
    return path


def attack(sid, timestamp="2026-01-01T00:00:00Z", **changes):
    return {"sequence_id": sid, "timestamp": timestamp,
            "phase_name": "RECONNAISSANCE", "label": "nmap_10_T5", **changes}


def test_identifier_text_and_utc_across_chunks(tmp_path):
    path = fixture(tmp_path, [attack("1.1"), attack("1.10", "2025-12-31T19:00:01-05:00")])
    result = qualify_file(path, chunksize=1)
    assert result["validation_ok"]
    assert result["distinct_attack_step_ids_as_strings"] == 2
    assert result["numeric_equivalence_collision_groups"] == 1
    assert result["last_timestamp_utc"] == "2026-01-01T00:00:01+00:00"
    assert result["metadata_excluded_from_features"] == ["phase_name", "sequence_id", "label", "timestamp"]
    assert '"1.10"' not in json.dumps(result)


def test_regression_at_chunk_boundary_fails(tmp_path):
    path = fixture(tmp_path, [attack("1", "2026-01-01T00:00:02Z"), attack("2")])
    result = qualify_file(path, chunksize=1)
    assert not result["validation_ok"]
    assert result["invalid_counts"]["timestamp_regressions"] == 1


def test_missing_label_and_unknown_attack_phase_fail_closed(tmp_path):
    path = fixture(tmp_path, [attack("1", phase_name="UNKNOWN"),
                              attack("2", label=""),
                              attack("3", label="unregistered-step")])
    result = qualify_file(path)
    assert not result["validation_ok"]
    assert result["normal_rows"] == 0
    assert result["unknown_label_rows"] == 2
    assert result["invalid_counts"]["attack_missing_or_unknown_phase"] == 1


def test_checksum_tampering_is_reported(tmp_path):
    path = fixture(tmp_path, [attack("1")])
    receipt_path = path.with_name(path.name + ".receipt.json")
    receipt = json.loads(receipt_path.read_text())
    receipt["sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt))
    result = qualify_file(path)
    assert not result["validation_ok"]
    assert not result["source_receipt_verified"]
    assert "receipt_sha256_mismatch" in result["issues"]


def test_naive_clock_and_conflicting_step_identity_fail(tmp_path):
    path = fixture(tmp_path, [attack("1", "2026-01-01 00:00:00"),
                              attack("1", label="scp_inst", phase_name="INSTALLATION")])
    result = qualify_file(path)
    assert not result["validation_ok"]
    assert result["invalid_counts"]["invalid_or_naive_timestamp"] == 1
    assert result["invalid_counts"]["sequence_label_or_phase_conflicts"] == 1
