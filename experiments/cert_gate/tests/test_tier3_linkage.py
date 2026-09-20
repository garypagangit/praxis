import json
from pathlib import Path
import struct
import tempfile
import unittest

from experiments.cert_gate.tier3_linkage import audit, read_packets


def block(kind, body):
    body += b'\0' * (-len(body) % 4)
    return struct.pack('<II', kind, len(body) + 12) + body + struct.pack('<I', len(body) + 12)


def capture(*, vlan=False, resolution=None):
    ethernet = b'\0' * 12 + (b'\x81\x00\x00\x01\x08\x00' if vlan else b'\x08\x00')
    ip = b'\x45\x00\x00\x1c\x00\x00\x00\x00\x40\x11\x00\x00' + bytes([192, 0, 2, 1, 198, 51, 100, 2])
    udp = struct.pack('!HHHH', 12345, 53, 8, 0)
    frame = ethernet + ip + udp
    shb = block(0x0A0D0D0A, struct.pack('<IHHq', 0x1A2B3C4D, 1, 0, -1))
    options = b'' if resolution is None else struct.pack('<HHB3xHH', 9, 1, resolution, 0, 0)
    idb = block(1, struct.pack('<HHI', 1, 0, 65535) + options)
    stamp = 1_000_000 if resolution is None else 1_000_000_000
    epb = block(6, struct.pack('<IIIII', 0, 0, stamp, len(frame), len(frame)) + frame)
    return shb + idb + epb


class LinkageTests(unittest.TestCase):
    def run_audit(self, updates=None, raw=None):
        with tempfile.TemporaryDirectory() as directory:
            pcap, eve = Path(directory) / 'capture.pcap', Path(directory) / 'eve.json'
            pcap.write_bytes(capture() if raw is None else raw)
            event = {'event_type': 'alert', 'pcap_cnt': 1, 'pcap_filename': str(pcap),
                     'pkt_src': 'wire/pcap', 'timestamp': '1970-01-01T00:00:01.000000+0000',
                     'src_ip': '192.0.2.1', 'dest_ip': '198.51.100.2', 'proto': 'UDP',
                     'src_port': 12345, 'dest_port': 53}
            event.update(updates or {})
            eve.write_text(json.dumps(event) + '\n', encoding='utf-8')
            return audit(pcap, eve, include_details=True)

    def test_valid_wire_vlan_and_nanosecond_resolution(self):
        for raw in (capture(), capture(vlan=True), capture(resolution=9)):
            result = self.run_audit(raw=raw)
            self.assertEqual(result['alert_status_counts'], {'VERIFIED_FIELDS': 1})
            self.assertEqual(result['capture_packets'], 1)

    def test_exact_orientation_ports_and_filename_reject_mismatches(self):
        for change in ({'src_ip': '198.51.100.2', 'dest_ip': '192.0.2.1'},
                       {'dest_port': 54}, {'pcap_filename': 'other.pcap'}, {'src_port': True}):
            self.assertEqual(self.run_audit(change)['alert_status_counts'], {'MISMATCH': 1})

    def test_missing_counter_fields_and_pseudo_alert_are_unverifiable(self):
        for change in ({'pcap_cnt': None}, {'pcap_cnt': 0}, {'pcap_cnt': True},
                       {'pcap_filename': None}, {'pkt_src': 'stream (flow timeout)'},
                       {'timestamp': 'not a timestamp'}):
            self.assertEqual(self.run_audit(change)['alert_status_counts'], {'UNVERIFIABLE': 1})

    def test_timestamp_tolerance_has_exact_microsecond_boundary(self):
        self.assertEqual(self.run_audit({'timestamp': '1970-01-01T00:00:01.000001Z'})['alert_status_counts'], {'VERIFIED_FIELDS': 1})
        self.assertEqual(self.run_audit({'timestamp': '1970-01-01T00:00:01.000001001Z'})['alert_status_counts'], {'MISMATCH': 1})

    def test_truncated_capture_aborts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.pcap'
            path.write_bytes(capture()[:-1])
            with self.assertRaises(ValueError):
                read_packets(path)

    def test_unsupported_packet_preserves_one_based_packet_counter(self):
        raw = capture()
        # The section and interface blocks occupy 48 bytes. Insert an
        # unsupported simple packet before the valid enhanced packet.
        raw = raw[:48] + block(3, struct.pack('<I', 14) + b'\0' * 14) + raw[48:]
        first = self.run_audit(raw=raw)
        second = self.run_audit({'pcap_cnt': 2}, raw=raw)
        self.assertEqual(first['alert_status_counts'], {'UNVERIFIABLE': 1})
        self.assertEqual(second['alert_status_counts'], {'VERIFIED_FIELDS': 1})
        self.assertEqual(second['capture_packets'], 2)


if __name__ == '__main__':
    unittest.main()
