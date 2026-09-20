"""Synthetic correctness checks; these fixtures are not research evidence."""
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

from experiments.apt_benchmark.robustness.feature_cache import prepare as prepare_v1
from experiments.apt_benchmark.robustness.replay import Replay, load_events
from experiments.apt_benchmark.robustness_v2.feature_cache import CachedReplay, prepare, _jobs
from experiments.apt_benchmark.tests.test_robustness_feature_cache import write_fixture


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def v2_protocol(protocol):
    protocol = copy.deepcopy(protocol)
    protocol["version"] = "synthetic-cache-v2-test-only"
    for name, channel in (("execve_absent", "EXECVE"), ("proctitle_absent", "PROCTITLE"),
                          ("syscall_absent", "SYSCALL"), ("path_absent", "PATH")):
        protocol["conditions"].append({"name": name, "kind": "channel_absent", "channels": [channel]})
    random = ["clean", "random_25", "random_50"]
    typed = ["clean", "execve_absent", "proctitle_absent", "command_records_absent"]
    mixed = random + typed[1:]
    protocol["arms"] = {
        "semantic_event": {"family": "semantic_event", "views": ["clean"]},
        "entity_context": {"family": "entity_context", "views": ["clean"]},
        "random_dropout": {"family": "entity_context", "views": random},
        "type_dropout": {"family": "entity_context", "views": typed},
        "mixed_dropout": {"family": "entity_context", "views": mixed},
        "observed_router": {"family": "entity_context", "views": mixed},
    }
    return protocol


def write_protocol(path, protocol):
    path.write_text(json.dumps(protocol), encoding="utf-8")


class V2CacheEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source, cls.manifest, cls.protocol_path, v1, events = write_fixture(cls.root)
        # One target's only link to sensitive history is confined to a command
        # fragment. Removing that fragment must also remove that history link.
        for event in events:
            run = event["run_id"]
            if event["event_id"].endswith(":target_a"):
                event["fragments"][0]["entity_keys"] = [run + "/safe"]
                event["fragments"].append({"channel": "execve", "text": "execute malicious tool",
                    "timestamp": event["timestamp"], "entity_keys": [run + "/host/pid/shared"]})
        cls.source.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8", newline="\n")
        cls.manifest.write_text(json.dumps({"events_sha256": digest(cls.source)}), encoding="utf-8")
        cls.protocol = v2_protocol(v1)
        write_protocol(cls.protocol_path, cls.protocol)
        cls.output = cls.root / "cache"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.receipt = prepare(cls.source, cls.manifest, cls.protocol_path, cls.output)
        cls.cached = CachedReplay(cls.output, cls.protocol, digest(cls.source))
        cls.original = Replay(load_events(cls.source), cls.protocol["history"]["seconds"], cls.protocol["history"]["max_events"])
        cls.target_indices = np.asarray([i for i, e in enumerate(cls.original.events) if e["target_eligible"]])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_matrix_equal(self, actual, reference):
        x, observed = actual
        y, expected_observed = reference
        self.assertEqual(x.shape, y.shape)
        self.assertEqual((x != y).nnz, 0)
        np.testing.assert_array_equal(observed, expected_observed)

    def test_every_scheduled_view_is_exactly_equal_to_frozen_replay(self):
        for entry in self.receipt["matrices"].values():
            indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] == entry["role"]])
            with self.subTest(role=entry["role"], family=entry["family"], condition=entry["condition"]["name"], seed=entry["seed"]):
                self.assert_matrix_equal(
                    self.cached.matrix(indices, entry["condition"], entry["seed"], entry["family"], 128),
                    self.original.matrix(self.target_indices[indices], entry["condition"], entry["seed"], entry["family"], 128))

    def test_views_are_deduplicated_and_development_is_metadata_only(self):
        jobs = _jobs(self.protocol)
        self.assertEqual(len(jobs["fit"]), 7)  # semantic clean plus six context views
        self.assertEqual(len(jobs["calibration"]), 2)
        self.assertEqual(jobs["development"], {})
        self.assertEqual(len(jobs["test"]), 42)  # 21 condition-seed views, two families
        dev = next(row for row in self.receipt["runs"] if row["split"] == "development")
        self.assertEqual(dev["targets"], 2)
        self.assertEqual(dev["chunks"], {})
        dev_indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] == "development"])
        with self.assertRaisesRegex(ValueError, "prepared role schedule"):
            self.cached.matrix(dev_indices, self.protocol["conditions"][0], 20260920, "entity_context", 128)

    def test_all_arm_aliases_and_mixed_role_repeated_row_order(self):
        indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] != "development"])[::-1]
        indices = np.concatenate([indices, indices[:2]])
        for arm, specification in self.protocol["arms"].items():
            self.assert_matrix_equal(
                self.cached.matrix(indices, self.protocol["conditions"][0], 20260920, arm, 128),
                self.original.matrix(self.target_indices[indices], self.protocol["conditions"][0], 20260920, specification["family"], 128))
        x, observed = self.cached.matrix(np.array([], dtype=np.int64), self.protocol["conditions"][0], 20260920, "observed_router", 128)
        self.assertEqual(x.shape, (0, 266))
        self.assertEqual(observed.shape, (0,))

    def test_causal_and_fragment_local_linkage_is_preserved(self):
        index = next(i for i, e in enumerate(self.original.events) if e["event_id"] == "a_test:target_a")
        clean = self.protocol["conditions"][0]
        absent = next(c for c in self.protocol["conditions"] if c["name"] == "execve_absent")
        _, history, _, _ = self.original.view(index, clean, 20260920, True)
        self.assertIn("UNLABELED_HISTORY_CANARY", history)
        self.assertNotIn("FUTURE_CANARY", history)
        self.assertNotIn("SAME_TIME_CANARY", history)
        self.assertNotIn("LATE_HISTORY_CANARY", history)
        _, history, _, _ = self.original.view(index, absent, 20260920, True)
        self.assertEqual(history, "")
        cached_index = int(np.flatnonzero(self.target_indices == index)[0])
        matrix, observed = self.cached.matrix(np.asarray([cached_index]), absent, 20260920, "type_dropout", 128)
        self.assertTrue(observed[0])
        self.assertEqual(matrix[:, 128:256].nnz, 0)

    def test_no_fragments_remains_in_target_roster_with_zero_features(self):
        condition = next(c for c in self.protocol["conditions"] if c["name"] == "random_75")
        indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] == "test"])
        found = False
        for seed in self.protocol["seeds"]:
            x, observed = self.cached.matrix(indices, condition, seed, "mixed_dropout", 128)
            if (~observed).any():
                found = True
                self.assertEqual(x[~observed].nnz, 0)
                self.assertEqual(x.shape[0], len(indices))
        self.assertTrue(found)

    def test_source_protocol_and_requests_are_bound(self):
        changed = copy.deepcopy(self.protocol)
        changed["history"]["seconds"] += 1
        with self.assertRaisesRegex(ValueError, "source/protocol"):
            CachedReplay(self.output, changed, digest(self.source))
        with self.assertRaisesRegex(ValueError, "source/protocol"):
            CachedReplay(self.output, self.protocol, "0" * 64)
        indices = np.asarray([i for i, e in enumerate(self.cached.events) if e["split"] == "test"])
        altered = {**self.protocol["conditions"][0], "deadline": 99}
        with self.assertRaisesRegex(ValueError, "condition parameters"):
            self.cached.matrix(indices, altered, 20260920, "semantic_event", 128)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.cached.matrix(indices, self.protocol["conditions"][0], 20260920, "semantic_event", 129)
        with self.assertRaisesRegex(ValueError, "prepared role schedule"):
            self.cached.matrix(indices, self.protocol["conditions"][0], 123, "semantic_event", 128)
        with self.assertRaises(FileExistsError):
            prepare(self.source, self.manifest, self.protocol_path, self.output)

    def test_tampered_manifest_target_matrix_and_role_mapping_rejected(self):
        for kind in ("manifest", "target", "matrix", "role"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                copied = Path(directory) / "cache"
                shutil.copytree(self.output, copied)
                manifest = json.loads((copied / "MANIFEST.json").read_text())
                entry = next(e for e in manifest["matrices"].values() if e["role"] == "test")
                relative = {"manifest": "MANIFEST.json", "target": manifest["targets_file"],
                            "matrix": entry["matrix"], "role": manifest["role_mapping"]["test"]["file"]}[kind]
                with (copied / relative).open("ab") as stream:
                    stream.write(b"tampered")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    cache = CachedReplay(copied, self.protocol, digest(self.source))
                    indices = np.asarray([i for i, e in enumerate(cache.events) if e["split"] == "test"])
                    cache.matrix(indices, entry["condition"], entry["seed"], entry["family"], 128)

    def test_inconsistent_count_even_with_updated_manifest_digest_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "cache"
            shutil.copytree(self.output, copied)
            manifest_path = copied / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["source_event_count"] += 1
            write_protocol(manifest_path, manifest)
            (copied / "MANIFEST.sha256").write_text(digest(manifest_path))
            with self.assertRaisesRegex(ValueError, "source counts"):
                CachedReplay(copied, self.protocol, digest(self.source))
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.cached._checked_file("../outside.npy", "0" * 64)


class V2CacheReuseAndInputTests(unittest.TestCase):
    def test_verified_v1_reuse_is_exact_and_rejects_tampered_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, path, protocol, _ = write_fixture(root)
            base = root / "v1"
            with contextlib.redirect_stdout(io.StringIO()):
                old_receipt = prepare_v1(source, manifest, path, base)
            protocol = v2_protocol(protocol)
            write_protocol(path, protocol)
            with contextlib.redirect_stdout(io.StringIO()):
                reused = prepare(source, manifest, path, root / "reused", base)
                fresh = prepare(source, manifest, path, root / "fresh")
            self.assertGreater(reused["base_reuse"]["jobs"], 0)
            self.assertTrue(any(chunk["generation"] == "frozen_replay" for run in reused["runs"] for chunk in run["chunks"].values()))
            a = CachedReplay(root / "reused", protocol, digest(source))
            b = CachedReplay(root / "fresh", protocol, digest(source))
            self.assertEqual(a.events, b.events)
            for entry in fresh["matrices"].values():
                indices = np.asarray([i for i, e in enumerate(a.events) if e["split"] == entry["role"]])
                x, observed = a.matrix(indices, entry["condition"], entry["seed"], entry["family"], 128)
                y, expected = b.matrix(indices, entry["condition"], entry["seed"], entry["family"], 128)
                self.assertEqual((x != y).nnz, 0)
                np.testing.assert_array_equal(observed, expected)
            # Select a semantic/context chunk that v2 actually reuses.
            old_job_keys = {key for key, entry in old_receipt["matrices"].items() if entry["family"] == "entity_context"}
            chunk = next(chunk for run in old_receipt["runs"] for key, chunk in run["chunks"].items() if key in old_job_keys)
            with (base / chunk["matrix"]).open("ab") as stream:
                stream.write(b"changed after verification")
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                prepare(source, manifest, path, root / "invalid_reuse", base)
            self.assertFalse((root / "invalid_reuse/MANIFEST.json").exists())

    def test_empty_roles_and_no_target_run_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, path, protocol, events = write_fixture(root)
            events = [e for e in events if e["split"] == "fit"]
            for event in events:
                event["target_eligible"] = False
            source.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
            manifest.write_text(json.dumps({"events_sha256": digest(source)}), encoding="utf-8")
            protocol = v2_protocol(protocol)
            write_protocol(path, protocol)
            with contextlib.redirect_stdout(io.StringIO()):
                receipt = prepare(source, manifest, path, root / "cache")
            cached = CachedReplay(root / "cache", protocol, digest(source))
            self.assertEqual(cached.events, [])
            self.assertEqual(cached.source_event_count, 12)
            self.assertTrue(all(entry["rows"] == 0 for entry in receipt["matrices"].values()))
            self.assertTrue(all(not run["chunks"] for run in receipt["runs"]))

    def test_invalid_source_metadata_and_hash_fail_without_completed_cache(self):
        for kind, expected in (("hash", "streamed event hash"), ("duplicate", "Duplicate source event"),
                               ("split", "crosses split"), ("clock", "Nonfinite fragment"),
                               ("repeated_run", "reappears")):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, manifest, path, protocol, events = write_fixture(root)
                if kind == "duplicate":
                    events[6]["event_id"] = events[0]["event_id"]
                elif kind == "split":
                    events[1]["split"] = "test"
                elif kind == "clock":
                    events[0]["fragments"][0]["timestamp"] = float("nan")
                elif kind == "repeated_run":
                    events.append({**events[0], "event_id": "another_id"})
                source.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
                manifest.write_text(json.dumps({"events_sha256": "0" * 64 if kind == "hash" else digest(source)}), encoding="utf-8")
                write_protocol(path, v2_protocol(protocol))
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, expected):
                    prepare(source, manifest, path, root / "cache")
                self.assertFalse((root / "cache/MANIFEST.json").exists())

    def test_unknown_training_views_and_duplicate_conditions_rejected(self):
        protocol_path = Path(__file__).parents[1] / "robustness/protocol.json"
        protocol = v2_protocol(json.loads(protocol_path.read_text()))
        protocol["arms"]["type_dropout"]["views"].append("invented_condition")
        with self.assertRaisesRegex(ValueError, "known arm training views"):
            _jobs(protocol)
        protocol = v2_protocol(json.loads(protocol_path.read_text()))
        protocol["conditions"].append(copy.deepcopy(protocol["conditions"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate condition"):
            _jobs(protocol)


if __name__ == "__main__":
    unittest.main()
