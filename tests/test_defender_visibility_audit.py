import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_visibility_audit as audit
import defender_telemetry_expanded as expanded


class ProcessRemovalTests(unittest.TestCase):
    def test_extracts_only_process_creation_inside_window(self):
        windows = [{"start": 0, "end": 30, "process_bins": {"security": [0] * 6}}]
        records = [
            {"timestamp": 4999, "message": "<EventID>4688</EventID>"},
            {"timestamp": 5000, "message": "<EventID>4688</EventID>"},
            {"timestamp": 6000, "message": "<EventID>4624</EventID>"},
            {"timestamp": 30000, "message": "<EventID>4688</EventID>"},
        ]
        stream = io.StringIO("".join(json.dumps(r) + "\n" for r in records))
        with patch.object(audit.gzip, "open", return_value=stream):
            audit.process_bins(Path("unused"), windows, "security")
        self.assertEqual(windows[0]["process_bins"]["security"], [1, 1, 0, 0, 0, 0])

    def test_removal_updates_count_and_every_affected_timing_bin(self):
        row = {"security_4688": "3", **{f"bin_security_{i}": "2" for i in range(6)}}
        result = audit.subtract_process_events(row, "security", [0, 1, 0, 2, 0, 0])
        self.assertEqual(result["security_4688"], 0)
        self.assertEqual([int(result[f"bin_security_{i}"]) for i in range(6)], [2, 1, 2, 0, 2, 2])
        self.assertEqual(row["security_4688"], "3")

    def test_removal_detects_mismatched_counts_and_negative_bins(self):
        row = {"sysmon_1": "3", **{f"bin_sysmon_{i}": "1" for i in range(6)}}
        with self.assertRaisesRegex(ValueError, "differs"):
            audit.subtract_process_events(row, "sysmon", [0] * 6)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            audit.subtract_process_events(row, "sysmon", [3, 0, 0, 0, 0, 0])

    def test_derived_timing_is_recomputed_after_removal(self):
        row = {"session": "s", "label": "ai", "window": "login_0",
               **{name: 0 for name in audit.base.FEATURES["combined"] + expanded.EXTRA_FEATURES + expanded.BIN_COLUMNS}}
        row["sysmon_1"] = 1
        row["bin_sysmon_0"] = 1
        row["bin_security_0"] = 1
        before = expanded.aggregate([row], 30)[0]
        after = expanded.aggregate([audit.subtract_process_events(row, "sysmon", [1, 0, 0, 0, 0, 0])], 30)[0]
        self.assertGreater(before["security_sysmon_coactive"], 0)
        self.assertEqual(after["security_sysmon_coactive"], 0)
        self.assertEqual(after["sysmon_active_fraction"], 0)


if __name__ == "__main__":
    unittest.main()
