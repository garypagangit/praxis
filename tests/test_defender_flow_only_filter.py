import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_flow_only_filter as study


def row(window):
    values = {name: "0" for name in study.flow_filter.FLOW_COLUMNS}
    values.update({"session": "s", "window": window, "label": "human", "security_4624": "3"})
    values["flow_records"] = "2"
    values["flow_udp"] = "2"
    values["bin_flow_0"] = "2"
    return values


class FlowOnlyFilterTests(unittest.TestCase):
    def test_alignment_preserves_baseline_order_and_allows_flow_removal(self):
        original = [row("w_0"), row("w_1")]
        filtered = [dict(original[1]), dict(original[0])]
        filtered[1].update(flow_records="1", flow_udp="1", bin_flow_0="1")
        result = study.aligned_rows(original, filtered)
        self.assertEqual([r["window"] for r in result], ["w_0", "w_1"])
        self.assertEqual(result[0]["flow_records"], "1")

    def test_alignment_rejects_missing_duplicate_or_changed_nonflow(self):
        original = [row("w_0"), row("w_1")]
        with self.assertRaisesRegex(ValueError, "windows differ"):
            study.aligned_rows(original, original[:1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            study.aligned_rows(original, [original[0], original[0]])
        changed = [dict(r) for r in original]
        changed[0]["security_4624"] = "4"
        with self.assertRaisesRegex(ValueError, "Non-flow"):
            study.aligned_rows(original, changed)

    def test_alignment_rejects_impossible_flow_counts(self):
        original = [row("w_0")]
        changed = [dict(original[0], bin_flow_0="1")]
        with self.assertRaisesRegex(ValueError, "Flow bins"):
            study.aligned_rows(original, changed)
        changed = [dict(original[0], flow_udp="3")]
        with self.assertRaisesRegex(ValueError, "Invalid filtered"):
            study.aligned_rows(original, changed)


if __name__ == "__main__":
    unittest.main()
