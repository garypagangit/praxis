import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_flow_investigation as audit
import defender_telemetry_experiment as base


class FlowInvestigationTests(unittest.TestCase):
    def test_context_windows_exclude_exact_login_extent(self):
        windows = audit.context_windows("s", "ai", 500.0, 1000.5)
        self.assertEqual(len(windows), 20)
        self.assertEqual(windows[9]["end"], 500.0)
        self.assertEqual(windows[10]["start"], 1000.5)
        self.assertEqual(windows[-1]["end"], 1300.5)

    def test_diagnostics_match_features_without_exporting_addresses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flow.jsonl.gz"
            messages = [
                "2 account eni - - - - - - - 0 60 - NODATA",
                "2 account eni 10.0.0.1 10.0.0.2 50000 53 17 2 80 0 10 REJECT OK",
                "2 account eni 10.0.0.1 10.0.0.2 - - 1 1 80 0 20 REJECT OK",
                "2 account eni 10.0.0.1 10.0.0.2 1 2 6 1 50 0 30 ACCEPT OK",
            ]
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                for message in messages:
                    stream.write(json.dumps({"message": message}) + "\n")
            windows = [{"start": start, "end": start + 30, "phase": "during",
                        "values": {name: 0 for name in base.FEATURES["combined"]},
                        "covered": set(), "skipped_flow": False}
                       for start in (0, 30)]
            base.flow_stream(path, windows)
            eligible, ports, hosts = audit.analyze_flow(path, windows, {"10.0.0.1": "dc01"})
            self.assertEqual(len(eligible), 2)
            self.assertEqual(windows[0]["diagnostic"]["rejected"], 2)
            self.assertEqual(windows[0]["diagnostic"]["rejected_icmp"], 1)
            self.assertEqual(ports["during"]["udp/53/destination"], 1)
            self.assertEqual(hosts["during"]["source:dc01"], 2)
            self.assertEqual(hosts["during"]["destination:unmapped"], 2)
            self.assertNotIn("10.0.0.", repr((windows, ports, hosts)))


if __name__ == "__main__":
    unittest.main()
