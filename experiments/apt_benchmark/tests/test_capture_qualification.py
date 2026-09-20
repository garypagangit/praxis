from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

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


class CaptureQualificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_identifier_text_and_utc_across_chunks(self):
        path = fixture(self.tmp_path, [attack("1.1"), attack("1.10", "2025-12-31T19:00:01-05:00")])
        result = qualify_file(path, chunksize=1)
        self.assertTrue(result["validation_ok"])
        self.assertEqual(result["distinct_attack_step_ids_as_strings"], 2)
        self.assertEqual(result["numeric_equivalence_collision_groups"], 1)
        self.assertEqual(result["last_timestamp_utc"], "2026-01-01T00:00:01+00:00")
        self.assertEqual(result["metadata_excluded_from_features"], ["phase_name", "sequence_id", "label", "timestamp"])
        self.assertNotIn('"1.10"', json.dumps(result))

    def test_regression_at_chunk_boundary_fails(self):
        path = fixture(self.tmp_path, [attack("1", "2026-01-01T00:00:02Z"), attack("2")])
        result = qualify_file(path, chunksize=1)
        self.assertFalse(result["validation_ok"])
        self.assertEqual(result["invalid_counts"]["timestamp_regressions"], 1)

    def test_missing_label_and_unknown_attack_phase_fail_closed(self):
        path = fixture(self.tmp_path, [attack("1", phase_name="UNKNOWN"),
                                      attack("2", label=""),
                                      attack("3", label="unregistered-step")])
        result = qualify_file(path)
        self.assertFalse(result["validation_ok"])
        self.assertEqual(result["normal_rows"], 0)
        self.assertEqual(result["unknown_label_rows"], 2)
        self.assertEqual(result["invalid_counts"]["attack_missing_or_unknown_phase"], 1)

    def test_checksum_tampering_is_reported(self):
        path = fixture(self.tmp_path, [attack("1")])
        receipt_path = path.with_name(path.name + ".receipt.json")
        receipt = json.loads(receipt_path.read_text())
        receipt["sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt))
        result = qualify_file(path)
        self.assertFalse(result["validation_ok"])
        self.assertFalse(result["source_receipt_verified"])
        self.assertIn("receipt_sha256_mismatch", result["issues"])

    def test_naive_clock_and_conflicting_step_identity_fail(self):
        path = fixture(self.tmp_path, [attack("1", "2026-01-01 00:00:00"),
                                      attack("1", label="scp_inst", phase_name="INSTALLATION")])
        result = qualify_file(path)
        self.assertFalse(result["validation_ok"])
        self.assertEqual(result["invalid_counts"]["invalid_or_naive_timestamp"], 1)
        self.assertEqual(result["invalid_counts"]["sequence_label_or_phase_conflicts"], 1)


if __name__ == "__main__":
    unittest.main()
