import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.robustness.feature_cache import CachedReplay, prepare
from experiments.apt_benchmark.robustness.replay import Replay, load_events


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_fixture(root, events=None):
    protocol = json.loads((Path(__file__).parents[1] / "robustness/protocol.json").read_text())
    protocol["text_features"]["hash_dimensions_per_block"] = 128
    if events is None:
        events = []
        # Source order intentionally differs from the lexical global Replay
        # order. Context is unlabeled/ineligible but must affect target features.
        for run, role in [("z_fit", "fit"), ("a_fit", "fit"), ("m_cal", "calibration"),
                          ("z_test", "test"), ("a_test", "test"), ("d_dev", "development")]:
            key = run + "/host/pid/shared"

            def event(suffix, time, eligible, channel, text, *, arrival=None, labels=None):
                fragment = {"channel": channel, "text": text, "baseline_text": "generic " + text,
                            "timestamp": time, "entity_keys": [key]}
                if arrival is not None:
                    fragment["available_at"] = arrival
                return {"event_id": run + ":" + suffix, "run_id": run, "split": role,
                        "timestamp": time, "available_at": time, "entity_keys": [key],
                        "labels": labels or [], "target_eligible": eligible, "fragments": [fragment]}

            a = event("target_a", 20., True, "syscall", "syscall execute root", labels=["T1548"])
            a["fragments"].append({"channel": "proctitle", "text": "modprobe command", "baseline_text": "generic long_hex", "timestamp": 20., "entity_keys": []})
            # Deliberately unsorted within a run, as load_events sorts records.
            events.extend([event("future", 200., False, "syscall", "FUTURE_CANARY"), a,
                event("prior", 10., False, "user_start", "UNLABELED_HISTORY_CANARY"),
                event("prior_late", 15., False, "proctitle", "LATE_HISTORY_CANARY", arrival=40.),
                event("same_time", 20., False, "syscall", "SAME_TIME_CANARY"),
                event("target_b", 30., True, "user_cmd", "user command nonroot", labels=["other"])])
    source = root / "EVENTS.jsonl"
    source.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8", newline="\n")
    manifest = root / "SOURCE_MANIFEST.json"
    manifest.write_text(json.dumps({"events_sha256": digest(source)}), encoding="utf-8")
    protocol_path = root / "PROTOCOL.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    return source, manifest, protocol_path, protocol, events


class CacheEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source, cls.manifest, cls.protocol_path, cls.protocol, _ = write_fixture(cls.root)
        cls.output = cls.root / "cache"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.receipt = prepare(cls.source, cls.manifest, cls.protocol_path, cls.output)
        cls.cached = CachedReplay(cls.output, cls.protocol, digest(cls.source))
        cls.original = Replay(load_events(cls.source), cls.protocol["history"]["seconds"], cls.protocol["history"]["max_events"])
        cls.original_target_indices = np.asarray([i for i, event in enumerate(cls.original.events) if event["target_eligible"]])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_matrix_equal(self, actual, expected):
        x, observed = actual
        ref, ref_observed = expected
        self.assertEqual(x.shape, ref.shape)
        self.assertEqual((x != ref).nnz, 0)
        np.testing.assert_array_equal(observed, ref_observed)

    def test_all_scheduled_features_exactly_equal_frozen_replay(self):
        for entry in self.receipt["matrices"].values():
            indices = np.asarray([i for i, event in enumerate(self.cached.events) if event["split"] == entry["role"]])
            original_indices = self.original_target_indices[indices]
            with self.subTest(role=entry["role"], family=entry["family"], condition=entry["condition"]["name"], seed=entry["seed"]):
                self.assert_matrix_equal(
                    self.cached.matrix(indices, entry["condition"], entry["seed"], entry["family"], 128),
                    self.original.matrix(original_indices, entry["condition"], entry["seed"], entry["family"], 128))

    def test_eligible_roster_order_and_unlabeled_context_preserved(self):
        self.assertEqual(self.cached.source_event_count, 36)
        self.assertEqual(len(self.cached.events), 12)
        self.assertEqual([e["event_id"] for e in self.cached.events], [self.original.events[i]["event_id"] for i in self.original_target_indices])
        self.assertTrue(all("fragments" not in e and e["target_eligible"] for e in self.cached.events))
        # The reference uses unlabeled earlier context; later/same-time records
        # are excluded before the exact-equivalence cache assertion above.
        index = next(i for i, e in enumerate(self.original.events) if e["event_id"] == "a_test:target_a")
        _, history, _, _ = self.original.view(index, self.protocol["conditions"][0], 20260920, True)
        self.assertIn("UNLABELED_HISTORY_CANARY", history)
        self.assertNotIn("FUTURE_CANARY", history)
        self.assertNotIn("SAME_TIME_CANARY", history)
        self.assertNotIn("LATE_HISTORY_CANARY", history)
        self.assertEqual(self.receipt["events_sha256"], digest(self.source))
        self.assertEqual(self.receipt["source_manifest_sha256"], digest(self.manifest))

    def test_arbitrary_order_repeated_indices_mixed_roles_and_dropout_alias(self):
        # The requested row order includes duplicates and differs from both
        # role order and cache order; fit/cal/test all have clean context jobs.
        indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] != "development"])[::-1]
        indices = np.concatenate([indices, indices[:2]])
        condition = self.protocol["conditions"][0]
        self.assert_matrix_equal(self.cached.matrix(indices, condition, 20260920, "context_dropout", 128),
                                 self.original.matrix(self.original_target_indices[indices], condition, 20260920, "entity_context", 128))

    def test_conditions_protocol_seeds_dimensions_and_no_overwrite_are_bound(self):
        changed = copy.deepcopy(self.protocol)
        changed["history"]["seconds"] += 1
        with self.assertRaisesRegex(ValueError, "source/protocol"):
            CachedReplay(self.output, changed, digest(self.source))
        with self.assertRaisesRegex(ValueError, "source/protocol"):
            CachedReplay(self.output, self.protocol, "0" * 64)
        condition = copy.deepcopy(self.protocol["conditions"][1])
        condition["drop_probability"] = .9
        indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] == "test"])
        with self.assertRaisesRegex(ValueError, "condition parameters"):
            self.cached.matrix(indices, condition, 20260920, "semantic_event", 128)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.cached.matrix(indices, self.protocol["conditions"][0], 20260920, "semantic_event", 129)
        with self.assertRaisesRegex(ValueError, "prepared role schedule"):
            self.cached.matrix(indices, self.protocol["conditions"][0], 999, "semantic_event", 128)
        with self.assertRaises(FileExistsError):
            prepare(self.source, self.manifest, self.protocol_path, self.output)

    def test_matrix_tampering_and_path_escape_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "cache"
            shutil.copytree(self.output, copied)
            instance = CachedReplay(copied, self.protocol, digest(self.source))
            entry = next(e for e in instance.manifest["matrices"].values() if e["role"] == "test")
            matrix_path = copied / entry["matrix"]
            with matrix_path.open("ab") as stream:
                stream.write(b"tampered")
            indices = np.asarray([i for i, e in enumerate(instance.events) if e["split"] == "test"])
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                instance.matrix(indices, entry["condition"], entry["seed"], entry["family"], 128)
            with self.assertRaisesRegex(ValueError, "escapes"):
                instance._checked_file("../outside.npy", "0" * 64)


class CacheInputGuards(unittest.TestCase):
    def invalid(self, mutate, expected):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, protocol, _, events = write_fixture(root)
            mutate(events)
            source.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
            manifest.write_text(json.dumps({"events_sha256": digest(source)}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, expected):
                prepare(source, manifest, protocol, root / "cache")
            self.assertFalse((root / "cache/MANIFEST.json").exists())

    def test_repeated_run_and_cross_split_run_rejected(self):
        self.invalid(lambda events: events.append({**events[0], "event_id": "distinct_late_id"}), "reappears")
        self.invalid(lambda events: events[1].update(split="test"), "crosses split")

    def test_duplicate_context_id_across_runs_rejected(self):
        self.invalid(lambda events: events[6].update(event_id=events[0]["event_id"]), "Duplicate source event")

    def test_nonfinite_fragment_clock_rejected(self):
        self.invalid(lambda events: events[0]["fragments"][0].update(timestamp=float("nan")), "Nonfinite fragment")

    def test_streamed_source_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, protocol, _, _ = write_fixture(root)
            manifest.write_text(json.dumps({"events_sha256": "0" * 64}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "streamed event hash"):
                prepare(source, manifest, protocol, root / "cache")
            self.assertFalse((root / "cache/MANIFEST.json").exists())


if __name__ == "__main__":
    unittest.main()
