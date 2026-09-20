"""Tests for source-label joins, causal windows and visibility-safe identities."""
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_benchmark.robustness.casino_events import decode_value, fragment, host_events, machine_name, select_instances


class CasinoEventsTests(unittest.TestCase):
    def test_hex_command_is_decoded_as_data_and_ids_are_only_keys(self):
        record = 'type=PROCTITLE msg=audit(1000.1:44): proctitle=7375646f002d6c pid=1234 ses=91'
        result = fragment(record, "run1", "host1", 1000.1)
        self.assertIn("proctitle=sudo -l", result["text"])
        self.assertNotIn("1234", result["text"])
        self.assertNotIn("1000.1", result["text"])
        self.assertEqual(result["entity_keys"], ["proc:run1:host1:1234", "session:run1:host1:91"])
        self.assertEqual(decode_value("0fff"), "0fff")

    def test_fragment_without_identity_cannot_inherit_event_identity(self):
        result = fragment('type=PATH msg=audit(1000.1:44): name="/etc/shadow" inode=4567', "r", "h", 1000.1)
        self.assertEqual(result["entity_keys"], [])
        self.assertIn("/etc/shadow", result["text"])
        self.assertNotIn("4567", result["text"])

    def test_unset_and_zero_keys_are_never_shared_context(self):
        result = fragment('type=SYSCALL msg=audit(1000.1:44): pid=0 ppid=4294967295 ses=4294967295 uid=0 euid=1000', "r", "h", 1000.1)
        self.assertEqual(result["entity_keys"], [])
        self.assertIn("uid=root", result["text"])
        self.assertIn("euid=user", result["text"])

    def test_onsets_are_unique_and_context_is_bounded_without_future(self):
        records = [
            'type=SYSCALL msg=audit(879.0:1): pid=5 comm="old"',
            'type=SYSCALL msg=audit(880.0:2): pid=5 comm="boundary"',
            'type=SYSCALL msg=audit(999.0:3): pid=5 comm="before"',
            'type=SYSCALL msg=audit(1000.0:4): pid=5 comm="sudo"',
            'type=PROCTITLE msg=audit(1000.0:4): proctitle=7375646f002d6c',
            'type=SYSCALL msg=audit(1001.0:5): pid=5 comm="future"',
        ]
        labels = {
            "a": {"technique": "T1548: Abuse Elevation Control Mechanism", "auditd_events": {"host": ["4", "5"]}},
            "b": {"technique": "T1068: Exploitation for Privilege Escalation", "auditd_events": {"host": ["4"]}},
            "other_host": {"technique": "T1105: Ingress Tool Transfer", "auditd_events": {"different": ["3"]}},
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audit.log"
            path.write_text("\n".join(records), encoding="utf-8")
            events, stats = host_events(path, "run", "host", "test", labels)
        self.assertEqual([event["timestamp"] for event in events], [880., 999., 1000.])
        self.assertEqual(sum(e["target_eligible"] for e in events), 1)
        self.assertEqual(len(events[-1]["labels"]), 2)
        self.assertEqual(len(events[-1]["fragments"]), 2)
        self.assertEqual(events[0]["label_status"], "unlabeled_unknown")
        self.assertFalse(events[0]["target_eligible"])
        self.assertEqual(stats["annotations_with_observed_onset"], 2)

    def test_reused_audit_id_fails_instead_of_ambiguous_label_join(self):
        labels = {"a": {"technique": "T1548", "auditd_events": {"h": ["4"]}}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audit.log"
            path.write_text('type=SYSCALL msg=audit(1.0:4): pid=2\ntype=SYSCALL msg=audit(2.0:4): pid=2\n')
            with self.assertRaisesRegex(ValueError, "reused"):
                host_events(path, "r", "h", "test", labels)

    def test_instance_selection_is_order_invariant_and_disjoint(self):
        names = [f"instance{i}" for i in range(40)]
        first = select_instances(names, 24)
        self.assertEqual(first, select_instances(list(reversed(names)), 24))
        self.assertEqual(len(first), 24)
        self.assertEqual(list(first.values()).count("fit"), 12)
        for split in ("development", "calibration", "test"):
            self.assertEqual(list(first.values()).count(split), 4)
        full = select_instances([f"run{i}" for i in range(114)])
        self.assertEqual(list(full.values()).count("fit"), 60)
        self.assertEqual(list(full.values()).count("test"), 18)

    def test_exported_host_alias_and_identity_masking(self):
        self.assertEqual(machine_name("meetingcam-14"), "meet")
        self.assertEqual(machine_name("bastion.casinolimit.bzh"), "bastion")
        result = fragment('type=EXECVE msg=audit(1000.0:12): a0="ssh" a1="alice@2001:db8::1" a2="runxyz" a3="4444" a4="T1068"', "runxyz", "h", 1000., {"alice"})
        for secret in ("alice", "2001:db8::1", "runxyz", "4444", "T1068"):
            self.assertNotIn(secret, result["text"])


if __name__ == "__main__":
    unittest.main()
