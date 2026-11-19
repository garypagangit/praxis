import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_flow_attribution as audit


class FlowAttributionTests(unittest.TestCase):
    def test_exact_tuple_and_interval_are_required(self):
        key = ("10.0.0.1", "10.0.0.2", 41641, 3478)
        index = {key: [(9, "tailscale_named", "dc01"),
                       (15, "tailscale_named", "dc01"),
                       (21, "other_named", "dc01")]}
        flow = "2 account eni 10.0.0.1 10.0.0.2 41641 3478 17 1 50 10 20 REJECT OK".split()
        self.assertEqual(audit.match_events(index, flow), "matched_tailscale_named")
        flow[6] = "9999"
        self.assertEqual(audit.match_events(index, flow), "unmatched")
        flow[6] = "3478"
        flow[10:12] = ["22", "30"]
        self.assertEqual(audit.match_events(index, flow), "unmatched")

    def test_mixed_process_matches_are_not_attributed_to_one_process(self):
        key = ("10.0.0.1", "10.0.0.2", 41641, 3478)
        index = {key: [(11, "other_named", "dc01"), (12, "tailscale_named", "dc01")]}
        flow = "2 account eni 10.0.0.1 10.0.0.2 41641 3478 17 1 50 10 20 REJECT OK".split()
        self.assertEqual(audit.match_events(index, flow), "matched_mixed_processes")


if __name__ == "__main__":
    unittest.main()
