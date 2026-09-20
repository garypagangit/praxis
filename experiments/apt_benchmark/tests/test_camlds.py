import csv
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_benchmark.camlds.acquire import digest, select_members
from experiments.apt_benchmark.camlds.events import (
    build_host, family_splits, fragment, interval_labels, load_intervals, verify_source_anchors,
)
from experiments.apt_benchmark.camlds.remask import canonical, remask_event, repair, write_json


class CamLdsTests(unittest.TestCase):
    def test_family_split_matches_frozen_hash_and_keeps_reserves_out(self):
        self.assertEqual(family_splits(), {"3": "fit", "6": "fit", "2": "development", "4": "calibration", "1": "test"})
        self.assertNotIn("5", family_splits())
        self.assertNotIn("7", family_splits())

    def test_interval_boundaries_unknown_and_overlap_union(self):
        intervals = [{"start": 10, "end": 20, "labels": ["T1105"], "step_id": "a"},
                     {"start": 15, "end": 25, "labels": ["T1059", "T1105"], "step_id": "b"}]
        self.assertEqual(interval_labels(9, intervals), ([], []))
        self.assertEqual(interval_labels(10, intervals), (["T1105"], ["a"]))
        self.assertEqual(interval_labels(20, intervals), (["T1059", "T1105"], ["b"]))
        self.assertEqual(interval_labels(17, intervals), (["T1059", "T1105"], ["a", "b"]))
        self.assertEqual(interval_labels(25, intervals), ([], []))

    def test_selection_excludes_attacker_audit_configs_and_alert_labels(self):
        names = ["scenario_4/host/logs/log/audit/audit.log", "scenario_4/host/logs/log/audit/audit.log.1.gz",
                 "scenario_4/attacker/logs/log/audit/audit.log", "scenario_4/host/configs/etc/audit/audit.rules",
                 "scenario_4/host/logs/alerts.json", "scenario_4/attacker/logs/attackmate.json"]
        self.assertEqual([x["name"] for x in select_members([{"name": x} for x in names])], [names[0], names[1], names[-1]])

    def test_semantics_decode_but_do_not_expose_identifiers_or_label_keys(self):
        raw = 'type=EXECVE msg=audit(100.0:1): argc=2 a0="curl" a1="https://video.attackbed.com/T1105" key="T1068_stage"'
        part = fragment(raw, "1_pwnkit_pam", "videoserver", 100)
        self.assertIn("curl", part["text"])
        self.assertNotIn("attackbed", part["text"])
        self.assertNotIn("T1105", part["text"])
        self.assertNotIn("T1068", part["text"])
        self.assertEqual(part["entity_keys"], [])

    def test_cross_host_fixed_names_masked_without_generic_client_damage(self):
        raw = 'type=EXECVE msg=audit(100.0:1): argc=3 a0="sh" a1="-c" a2="iptables -d $LINUXSHARE; ping corpdns; ssh reposerver; CLIENT=-i; rsh-client"'
        part = fragment(raw, "4", "inetfw", 100)
        self.assertIn("$HOST", part["text"])
        self.assertNotIn("LINUXSHARE", part["text"])
        self.assertNotIn("corpdns", part["text"])
        self.assertNotIn("reposerver", part["text"])
        self.assertIn("CLIENT", part["text"])
        self.assertIn("rsh-client", part["text"])

    def _host(self, root, lines, intervals):
        name = "scenario_4/host/logs/log/audit/audit.log"
        path = root / "raw" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        member = {"name": name, "sha256": digest(path)}
        return build_host(root, "4", "host", [member], intervals, "calibration")

    def test_fixed_bin_roster_is_selected_before_annotation_lookup(self):
        intervals = [{"start": 106, "end": 125, "labels": ["T1105"], "step_id": "step"}]
        lines = ['type=SYSCALL msg=audit(105.0:1): pid=7 exe="/usr/bin/curl"',
                 'type=SYSCALL msg=audit(106.0:2): pid=7 exe="/usr/bin/curl"',
                 'type=SYSCALL msg=audit(115.0:3): pid=7 exe="/usr/bin/curl"']
        with tempfile.TemporaryDirectory() as folder:
            events, stats = self._host(Path(folder), lines, intervals)
        self.assertEqual([x["query_roster"] for x in events], [True, False, True])
        self.assertEqual([x["target_eligible"] for x in events], [False, False, True])
        self.assertEqual(events[0]["label_status"], "unlabeled_unknown")
        self.assertEqual(stats["positive_targets"]["T1105"], 1)

    def test_event_grouping_and_exact_duplicate_fragment_handling(self):
        intervals = [{"start": 100, "end": 125, "labels": ["T1105"], "step_id": "step"}]
        line = 'type=SYSCALL msg=audit(105.0:1): pid=7 exe="/usr/bin/curl"'
        lines = [line, 'type=EXECVE msg=audit(105.0:1): argc=1 a0="curl"', line]
        with tempfile.TemporaryDirectory() as folder:
            events, stats = self._host(Path(folder), lines, intervals)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0]["fragments"]), 2)
        self.assertEqual(stats["duplicate_fragments"], 1)
        self.assertEqual(events[0]["fragments"][1]["entity_keys"], [])

    def test_future_records_and_changed_future_labels_do_not_change_earlier_features(self):
        intervals = [{"start": 100, "end": 120, "labels": ["T1105"], "step_id": "step"}]
        lines = ['type=SYSCALL msg=audit(105.0:1): pid=7 exe="/usr/bin/curl"']
        with tempfile.TemporaryDirectory() as folder:
            first, _ = self._host(Path(folder), lines, intervals)
            second, _ = self._host(Path(folder), lines + ['type=SYSCALL msg=audit(135.0:2): pid=7 exe="/usr/bin/uname"'],
                                   intervals + [{"start": 130, "end": 140, "labels": ["T1068"], "step_id": "later"}])
        self.assertEqual(first[0], second[0])

    def test_repeated_step_ids_preserve_separate_source_intervals(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "labels.json").write_text(json.dumps({"4-1": {"metadata": {"T1105": {}}}}))
            with (root / "attack_times.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["scenario", "event_id", "techniques", "start", "end"], delimiter=";")
                writer.writeheader()
                for start in (100, 200):
                    writer.writerow({"scenario": "4", "event_id": "1", "techniques": "T1105", "start": start, "end": start + 10})
            values = load_intervals(root)["4"]
        self.assertEqual([x["step_id"] for x in values], ["4-1:occurrence1", "4-1:occurrence2"])

    def test_source_anchors_reject_labels_not_in_original_chronology(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            name = "scenario_4/attacker/logs/attackmate.json"
            path = root / "raw" / name
            path.parent.mkdir(parents=True)
            source = {"start-datetime": "2026-01-01T00:00:00", "type": "shell", "cmd": "curl"}
            path.write_text(json.dumps(source) + "\n")
            members = [{"name": name, "sha256": digest(path)}]
            labels = {"4-1": {"scenario_variant": "4", "attackmate": dict(source)}}
            self.assertEqual(verify_source_anchors(root, "4", members, labels)["verified_label_anchors"], 1)
            labels["4-1"]["attackmate"]["cmd"] = "invented"
            with self.assertRaisesRegex(ValueError, "anchor absent"):
                verify_source_anchors(root, "4", members, labels)

    def _repair_fixture(self, root):
        source = root / "prior"
        source.mkdir()
        events = [{"event_id": "first", "run_id": "4", "split": "calibration", "timestamp": 100,
                   "labels": ["T1105"], "target_eligible": True, "entity_keys": ["proc:4:inetfw:7"],
                   "fragments": [{"text": "iptables -d $LINUXSHARE CLIENT=rsh-client", "baseline_text": "repo=corpdns",
                                  "channel": "EXECVE", "entity_keys": [], "timestamp": 100, "source_line": 1}]},
                  {"event_id": "second", "run_id": "4", "split": "calibration", "timestamp": 110,
                   "labels": ["T1059"], "target_eligible": True, "entity_keys": ["proc:4:inetfw:7"],
                   "fragments": [{"text": "curl", "baseline_text": "audit", "channel": "SYSCALL",
                                  "entity_keys": ["proc:4:inetfw:7"], "timestamp": 110, "source_line": 2}]}]
        path = source / "EVENTS.jsonl"
        path.write_bytes(b"".join(canonical(event) + b"\n" for event in events))
        selection = {"adapter_sha256": "a" * 64, "family_splits": {"4": "calibration"}}
        write_json(source / "SELECTION.json", selection)
        write_json(source / "MANIFEST.json", {"events": 2, "eligible_targets": 2, "events_sha256": digest(path),
                                              "selection": selection, "selection_sha256": digest(source / "SELECTION.json")})
        return source, events

    def test_remask_proves_nontext_invariance(self):
        with tempfile.TemporaryDirectory() as folder:
            _, events = self._repair_fixture(Path(folder))
            event = deepcopy(events[0])
            changed, fields, before, after = remask_event(event)
        self.assertEqual(changed, 1)
        self.assertEqual(dict(fields), {"text": 1, "baseline_text": 1})
        self.assertEqual(before, after)
        self.assertEqual(event["labels"], events[0]["labels"])
        self.assertEqual(event["fragments"][0]["entity_keys"], [])
        self.assertEqual(event["fragments"][0]["text"], "iptables -d $HOST CLIENT=rsh-client")

    def test_stream_repair_preserves_input_and_binds_new_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, original = self._repair_fixture(root)
            original_bytes = (source / "EVENTS.jsonl").read_bytes()
            output = root / "repaired"
            receipt = repair(source, output)
            result = [json.loads(line) for line in (output / "EVENTS.jsonl").read_text().splitlines()]
            manifest = json.loads((output / "MANIFEST.json").read_text())
            self.assertEqual((source / "EVENTS.jsonl").read_bytes(), original_bytes)
            self.assertEqual(result[1], original[1])
            self.assertEqual(receipt["counts"]["changed_events"], 1)
            self.assertEqual(receipt["counts"]["byte_preserved_events"], 1)
            self.assertEqual(receipt["nontext_before_sha256"], receipt["nontext_after_sha256"])
            self.assertEqual(manifest["events_sha256"], digest(output / "EVENTS.jsonl"))
            self.assertEqual(manifest["pre_fit_text_repair"]["receipt_sha256"], digest(output / "REPAIR.json"))
            with self.assertRaises(FileExistsError):
                repair(source, output)

    def test_repair_rejects_unbound_prior_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, _ = self._repair_fixture(root)
            write_json(source / "SELECTION.json", {"adapter_sha256": "tampered"})
            with self.assertRaisesRegex(ValueError, "does not bind"):
                repair(source, root / "repaired")

    def test_repair_rejects_unbound_prior_event_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, _ = self._repair_fixture(root)
            path = source / "EVENTS.jsonl"
            path.write_bytes(path.read_bytes().replace(b"iptables", b"changed!"))
            with self.assertRaisesRegex(ValueError, "does not match"):
                repair(source, root / "repaired")
            self.assertFalse((root / "repaired" / "MANIFEST.json").exists())


if __name__ == "__main__":
    unittest.main()
