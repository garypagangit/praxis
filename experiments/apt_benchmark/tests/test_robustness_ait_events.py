import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_benchmark.robustness.ait_events import (
    assemble_events, build_dataset, decode_command, parse_fragment,
)


PROTOCOL = {"splits": {"fit": ["fitrun"], "development": ["devrun"],
                       "calibration": ["calrun"], "test": ["testrun"]}}


def parsed(raw, *, run="run_a", split="fit", labels=None):
    result = parse_fragment(raw, run_id=run)
    result.update(split=split, labels=[] if labels is None else labels)
    return result


def fixture(root):
    source = root / "source"
    source.mkdir()
    protocol = root / "protocol.json"
    protocol.write_text(json.dumps(PROTOCOL), encoding="utf-8")
    scenarios = []
    raw = ('type=SYSCALL msg=audit(100.250:7): arch=c000003e syscall=313 success=yes exit=0 '
           'pid=715 ppid=19 uid=0 auid=1000 ses=9 exe="/usr/bin/modprobe"\n'
           'type=PROCTITLE msg=audit(100.250:7): proctitle=6D6F6470726F6265002D7600\n'
           'type=LOGIN msg=audit(101.0:8): pid=800 uid=0 auid=4294967295 ses=4294967295 res=1\n')
    for run in ("fitrun", "devrun", "calrun", "testrun"):
        members = []
        for kind in ("gather", "labels"):
            relative = f"{kind}/intranet_server/logs/audit/audit.log"
            path = source / run / relative
            path.parent.mkdir(parents=True)
            text = raw if kind == "gather" else json.dumps({"line": 2, "labels": ["escalate"], "rules": ["private-rule"]}) + "\n"
            path.write_text(text, encoding="utf-8", newline="\n")
            members.append({"local_relative_path": relative,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "crc32_verified": True})
        scenarios.append({"scenario": run, "members": members})
    (source / "ACQUISITION.json").write_text(json.dumps({"record": 19483937,
        "license": "CC-BY-NC-SA-4.0", "scenarios": scenarios}), encoding="utf-8")
    return source, protocol


class SemanticTests(unittest.TestCase):
    def test_identity_and_clock_changes_do_not_change_semantic_text(self):
        first = ('type=USER_START msg=audit(1640100000.125:879): pid=76432 uid=0 auid=12001 ses=532 '
                 'msg=\'op=PAM:session_open acct="person_alpha" exe="/usr/sbin/cron" '
                 'hostname=secret_host addr=10.12.13.14 terminal=cron res=success\'')
        second = first.replace("1640100000.125:879", "1649999999.999:8765432").replace("76432", "84411").replace("12001", "13002").replace("532", "789").replace("person_alpha", "person_beta").replace("secret_host", "different_host").replace("10.12.13.14", "192.0.2.11")
        a, b = parse_fragment(first, run_id="a"), parse_fragment(second, run_id="b")
        self.assertEqual(a["text"], b["text"])
        self.assertNotEqual(a["entity_keys"], b["entity_keys"])
        for forbidden in ("76432", "12001", "532", "person_alpha", "secret_host", "10.12.13.14", "1640100000", "879"):
            self.assertNotIn(forbidden, a["text"])
        self.assertIn("uid=root", a["text"])
        self.assertIn("auid=nonroot", a["text"])
        self.assertIn("op=session_open", a["text"])
        self.assertIn("res=success", a["text"])

    def test_privilege_sentinels_and_action_numbers_are_typed(self):
        a = parse_fragment('type=SYSCALL msg=audit(20.1:1): pid=0 ppid=8 ses=4294967295 '
            'uid=0 auid=-1 euid=1001 arch=c000003e syscall=313 exit=-13 mode=04755 success=no', run_id="a")
        self.assertIn("auid=unset", a["text"])
        self.assertIn("euid=nonroot", a["text"])
        self.assertIn("syscall=313", a["text"])
        self.assertIn("mode=04755", a["text"])
        self.assertIn("exit=errno_13", a["text"])
        self.assertIn("success=failure", a["text"])
        self.assertEqual(len(a["entity_keys"]), 1)  # only explicit valid ppid
        self.assertIn("/process/", a["entity_keys"][0])

    def test_safe_hex_command_decode_retains_program_not_literal_payload(self):
        command = b'modprobe\x00-v\x00/home/secret_person/private_module\x00'
        row = parse_fragment('type=PROCTITLE msg=audit(20:1): proctitle=' + command.hex(), run_id="a")
        self.assertIn("proctitle_program=modprobe", row["text"])
        self.assertIn("proctitle_flag=-v", row["text"])
        self.assertNotIn("secret_person", row["text"])
        self.assertNotIn("private_module", row["text"])
        self.assertEqual(decode_command("abc"), ("", "invalid_hex"))
        self.assertEqual(decode_command("ff"), ("", "invalid_encoding"))
        self.assertEqual(decode_command("01"), ("", "invalid_control"))
        self.assertEqual(decode_command("ab" * 8193), ("", "overlength"))
        # Metacharacters are inert text, and unrecognized arguments disappear.
        inert = parse_fragment('type=USER_CMD msg=audit(20:2): cmd="sh -c touch /tmp/DO_NOT_CREATE"', run_id="a")
        self.assertNotIn("DO_NOT_CREATE", inert["text"])
        self.assertIn("cmd_word=touch", inert["text"])

    def test_ambiguous_fields_invalid_time_or_missing_type_fail(self):
        for raw in ('type=LOGIN msg=audit(1:1): pid=1 pid=2',
                    'type=LOGIN no_time=1', 'msg=audit(1:1): pid=1',
                    'type=LOGIN msg=audit(1:1) msg=audit(2:2)',
                    'type=LOGIN msg=audit(' + '9' * 400 + ':1)'):
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                parse_fragment(raw, run_id="a")


class EventTests(unittest.TestCase):
    def test_group_by_run_host_epoch_serial_and_union_labels(self):
        records = [parsed('type=SYSCALL msg=audit(20.10:1): pid=4', labels=["escalate"]),
                   parsed('type=PROCTITLE msg=audit(20.100:1): proctitle=7368'),
                   parsed('type=LOGIN msg=audit(21.1:1): pid=4'),
                   parsed('type=LOGIN msg=audit(20.1:2): pid=4'),
                   parsed('type=LOGIN msg=audit(20.1:1): pid=4', run="run_b"),
                   parsed('node=another type=LOGIN msg=audit(20.1:1): pid=4')]
        events, stats = assemble_events(records)
        self.assertEqual(len(events), 5)
        combined = next(event for event in events if len(event["fragments"]) == 2)
        self.assertEqual(combined["labels"], ["escalate"])
        self.assertEqual(combined["timestamp"], combined["available_at"])
        self.assertEqual(stats["events_with_different_fragment_annotations"], 1)
        self.assertEqual(stats["fragments_whose_label_set_differs_from_event_union"], 1)

    def test_fragment_link_keys_never_borrow_dropped_or_future_fields(self):
        records = [parsed('type=PROCTITLE msg=audit(20:1): proctitle=7368'),
                   parsed('type=SYSCALL msg=audit(20:1): pid=555 ses=9'),
                   parsed('type=LOGIN msg=audit(2000:2): pid=999 ses=42')]
        before, _ = assemble_events(records[:2])
        after, _ = assemble_events(records)
        event = next(event for event in after if event["timestamp"] == 20)
        self.assertEqual(before[0], event)
        self.assertEqual(event["fragments"][0]["entity_keys"], [])
        self.assertEqual(len(event["fragments"][1]["entity_keys"]), 2)
        self.assertEqual(event["entity_keys"], event["fragments"][1]["entity_keys"])
        self.assertTrue(all(fragment["timestamp"] <= event["available_at"] for fragment in event["fragments"]))

    def test_inconsistent_role_or_clock_fails(self):
        a = parsed('type=LOGIN msg=audit(20:1): pid=1')
        b = copy.deepcopy(a)
        b["split"] = "test"
        with self.assertRaises(ValueError):
            assemble_events([a, b])
        b = copy.deepcopy(a)
        b["timestamp"] = 21
        with self.assertRaises(ValueError):
            assemble_events([b])

    def test_labels_do_not_modify_feature_text_or_keys(self):
        a = parsed('type=LOGIN msg=audit(20:1): uid=0 pid=1', labels=[])
        b = copy.deepcopy(a)
        b["labels"] = ["private_rule_derived_label"]
        left, _ = assemble_events([a])
        right, _ = assemble_events([b])
        self.assertEqual(left[0]["fragments"], right[0]["fragments"])
        self.assertEqual(left[0]["entity_keys"], right[0]["entity_keys"])
        self.assertEqual(left[0]["event_id"], right[0]["event_id"])


class DatasetTests(unittest.TestCase):
    def test_exact_source_join_manifest_determinism_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, protocol = fixture(root)
            report = build_dataset(source, protocol, root / "out1")
            repeated = build_dataset(source, protocol, root / "out2")
            self.assertEqual(report["events_sha256"], repeated["events_sha256"])
            self.assertEqual(report["fragments"], 12)
            self.assertEqual(report["events"], 8)
            self.assertEqual(report["annotated_events"], 4)
            self.assertEqual(report["annotated_fragments"], 4)
            self.assertEqual(report["label_scope"]["events_with_different_fragment_annotations"], 4)
            events = [json.loads(line) for line in (root / "out1/EVENTS.jsonl").read_text().splitlines()]
            self.assertEqual(len({event["event_id"] for event in events}), 8)
            self.assertEqual(set(event["split"] for event in events), set(PROTOCOL["splits"]))
            self.assertNotIn("private-rule", (root / "out1/EVENTS.jsonl").read_text())
            for event in events:
                self.assertEqual(event["labels"], ["escalate"] if event["timestamp"] == 100.25 else [])
            with self.assertRaises(FileExistsError):
                build_dataset(source, protocol, root / "out1")

    def test_source_hash_tampering_fails_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, protocol = fixture(root)
            path = source / "testrun/gather/intranet_server/logs/audit/audit.log"
            path.write_text(path.read_text() + "type=LOGIN msg=audit(300:99): pid=2\n")
            with self.assertRaisesRegex(ValueError, "acquired member"):
                build_dataset(source, protocol, root / "out")
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
