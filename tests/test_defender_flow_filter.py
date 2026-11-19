import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_flow_filter as study


class FlowFilterTests(unittest.TestCase):
    def test_udp_port_filter_is_bidirectional_and_does_not_remove_tcp(self):
        outbound = "2 account eni 10.0.0.1 10.0.0.2 41641 3478 17 2 80 0 10 REJECT OK".split()
        inbound = "2 account eni 10.0.0.2 10.0.0.1 3478 41641 17 2 80 0 10 ACCEPT OK".split()
        tcp = "2 account eni 10.0.0.1 10.0.0.2 41641 3478 6 2 80 0 10 REJECT OK".split()
        other = "2 account eni 10.0.0.1 10.0.0.2 50000 53 17 2 80 0 10 ACCEPT OK".split()
        self.assertTrue(study.excluded(outbound))
        self.assertTrue(study.excluded(inbound))
        self.assertFalse(study.excluded(tcp))
        self.assertFalse(study.excluded(other))

    def test_either_port_is_sufficient_and_invalid_udp_ports_fail(self):
        fields = "2 account eni 10.0.0.1 10.0.0.2 50000 53 17 2 80 0 10 ACCEPT OK".split()
        for index in (5, 6):
            for port in ("41641", "3478"):
                candidate = fields.copy()
                candidate[index] = port
                self.assertTrue(study.excluded(candidate))
        for port in ("-1", "65536", "-"):
            candidate = fields.copy()
            candidate[5] = port
            with self.assertRaises(ValueError):
                study.excluded(candidate)
        fields[7] = "1"
        fields[5] = fields[6] = "-"
        self.assertFalse(study.excluded(fields))

    def test_remaining_flow_features_and_timing_are_recomputed(self):
        fields = "2 account eni 10.0.0.1 10.0.0.2 50000 53 17 2 80 0 10 REJECT OK".split()
        values = {name: 0 for name in study.FLOW_COLUMNS}
        study.add_flow(values, fields, 2)
        self.assertEqual(values["flow_records"], 1)
        self.assertEqual(values["flow_udp"], 1)
        self.assertEqual(values["flow_reject"], 1)
        self.assertEqual(values["flow_packets"], 2)
        self.assertEqual(values["flow_bytes"], 80)
        self.assertEqual(values["bin_flow_2"], 1)


if __name__ == "__main__":
    unittest.main()
