import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_host_only as host


class HostOnlyTests(unittest.TestCase):
    def test_matched_window_comparison_detects_changed_event_counts(self):
        row = {"label": "ai", **{name: 0 for name in host.COMPARE_COLUMNS}}
        previous = {"label": "ai", **{name: "0" for name in host.COMPARE_COLUMNS}}
        host.check_previous(row, previous)
        previous["security_4624"] = "1"
        with self.assertRaisesRegex(ValueError, "security_4624"):
            host.check_previous(row, previous)

    def test_matched_window_comparison_rejects_changed_label(self):
        row = {"label": "ai", **{name: 0 for name in host.COMPARE_COLUMNS}}
        previous = {"label": "human", **{name: "0" for name in host.COMPARE_COLUMNS}}
        with self.assertRaisesRegex(ValueError, "labels differ"):
            host.check_previous(row, previous)


if __name__ == "__main__":
    unittest.main()
