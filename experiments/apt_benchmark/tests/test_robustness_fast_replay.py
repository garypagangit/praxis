"""Exact reference comparisons for the optional faster replay implementation."""
import json
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

import numpy as np

from experiments.apt_benchmark.robustness.replay import Replay, visible_fragments
from experiments.apt_benchmark.robustness.replay_fast import FastReplay


PROTOCOL = json.loads((Path(__file__).parents[1] / "robustness" / "casino_protocol.json").read_text(encoding="utf-8"))


def make_event(identifier, timestamp, keys=("process", "session"), channel="SYSCALL", run="run", text=None):
    text = text or "action_" + identifier
    return {"event_id": identifier, "timestamp": timestamp, "run_id": run,
            "split": "test", "labels": [], "fragments": [
                {"timestamp": timestamp, "channel": channel, "entity_keys": list(keys),
                 "text": text, "baseline_text": "baseline_" + text, "available_at": timestamp}]}


def dense_events(count=4096, mixed=True):
    events = []
    for i in range(count):
        # Dense activity with timestamp ties and shared keys; event ID ordering
        # intentionally differs from input index ordering after the shuffle.
        event = make_event(f"event_{i:06d}", 10 + (i // 4) / max(1, count // 400))
        if mixed:
            event["fragments"].append({
                "timestamp": event["timestamp"], "available_at": event["timestamp"] + i % 5,
                "channel": "PROCTITLE", "entity_keys": [f"secondary_{i % 3}"],
                "text": f"command_{i % 23}", "baseline_text": f"masked_{i % 23}"})
            if i % 7 == 0:
                event["fragments"][0]["entity_keys"] = ["unrelated"]
            if i % 11 == 0:
                event["fragments"][0]["available_at"] += 31
            if i % 17 == 0:
                event["run_id"] = "different_run"
        events.append(event)
    random.Random(421).shuffle(events)
    return events


def assert_views_equal(test, expected, actual):
    test.assertEqual(expected[:2], actual[:2])
    np.testing.assert_array_equal(expected[2], actual[2])
    test.assertEqual(expected[3], actual[3])


def assert_csr_equal(expected, actual):
    expected_matrix, expected_observed = expected
    actual_matrix, actual_observed = actual
    assert expected_matrix.shape == actual_matrix.shape
    np.testing.assert_array_equal(expected_matrix.indptr, actual_matrix.indptr)
    np.testing.assert_array_equal(expected_matrix.indices, actual_matrix.indices)
    np.testing.assert_array_equal(expected_matrix.data, actual_matrix.data)
    np.testing.assert_array_equal(expected_observed, actual_observed)


class FastReplayTests(unittest.TestCase):
    def test_dense_history_views_match_all_protocol_conditions_seeds_and_arms(self):
        events = dense_events()
        reference, fast = Replay(events), FastReplay(events)
        indices = sorted(range(len(events)), key=lambda i: events[i]["timestamp"])[-4:]
        for condition in PROTOCOL["conditions"]:
            for seed in PROTOCOL["seeds"]:
                for index in indices:
                    for use_history, generic in ((False, False), (False, True), (True, False), (True, True)):
                        with self.subTest(condition=condition["name"], seed=seed, index=index, history=use_history, generic=generic):
                            assert_views_equal(self, reference.view(index, condition, seed, use_history, generic),
                                               fast.view(index, condition, seed, use_history, generic))

    def test_sparse_matrices_match_exactly_for_all_arms_and_conditions(self):
        events = dense_events(320)
        reference, fast = Replay(events), FastReplay(events)
        indices = list(range(0, len(events), 31))
        for condition in PROTOCOL["conditions"]:
            for arm in PROTOCOL["models"]:
                with self.subTest(condition=condition["name"], arm=arm):
                    assert_csr_equal(reference.matrix(indices, condition, 20260921, arm, 1024),
                                     fast.matrix(indices, condition, 20260921, arm, 1024))

    def test_same_time_order_bounds_multiple_keys_and_arbitrary_input_order(self):
        events = [make_event("target", 200), make_event("old", 79.99),
                  make_event("b", 199, ("process",)), make_event("z", 199, ("session",)),
                  make_event("a", 199), make_event("boundary", 80),
                  make_event("future", 201), make_event("same", 200),
                  make_event("other_run", 199, run="other")]
        reference, fast = Replay(events), FastReplay(events)
        expected = reference.view(0, {"kind": "clean"}, 1, True)
        assert_views_equal(self, expected, fast.view(0, {"kind": "clean"}, 1, True))
        self.assertEqual(expected[1], "action_z action_b action_a action_boundary")

    def test_hidden_linkage_and_late_fragments_do_not_change_candidate_eligibility(self):
        prior = make_event("prior", 90, ("secret",), "PROCTITLE")
        target = make_event("target", 100, ("unrelated",))
        target["fragments"].append({"timestamp": 100, "channel": "PROCTITLE", "entity_keys": ["secret"], "text": "command"})
        target["fragments"].append({"timestamp": 101, "channel": "SYSCALL", "entity_keys": ["future_key"], "text": "future fragment"})
        events = [prior, target, make_event("future_link", 90, ("future_key",))]
        reference, fast = Replay(events), FastReplay(events)
        for condition in PROTOCOL["conditions"]:
            assert_views_equal(self, reference.view(1, condition, 20260920, True), fast.view(1, condition, 20260920, True))
        dropped = fast.view(1, {"kind": "channel_absent", "channels": ["PROCTITLE"]}, 1, True)
        self.assertEqual(dropped[1], "")
        self.assertNotIn("future fragment", dropped[0])

    def test_stops_after_visible_history_limit_without_scanning_dense_candidates(self):
        events = dense_events(12000, mixed=False)
        events.append(make_event("target", 120))
        fast = FastReplay(events)
        with patch("experiments.apt_benchmark.robustness.replay_fast.visible_fragments", wraps=visible_fragments) as visibility:
            fast.view(len(events) - 1, {"kind": "clean"}, 1, True)
        self.assertEqual(visibility.call_count, 33)  # Target plus 32 history events.

    def test_invisible_recent_candidates_do_not_consume_history_budget(self):
        events = [make_event(f"visible_{i:03d}", 10 + i / 10) for i in range(80)]
        events.extend(make_event(f"hidden_{i:03d}", 80 + i / 10, channel="PROCTITLE") for i in range(160))
        events.append(make_event("target", 100))
        random.Random(52).shuffle(events)
        index = next(i for i, event in enumerate(events) if event["event_id"] == "target")
        condition = {"kind": "channel_absent", "channels": ["PROCTITLE"]}
        for limit in (1, 5, 32):
            reference, fast = Replay(events, max_history=limit), FastReplay(events, max_history=limit)
            actual = fast.view(index, condition, 1, True)
            assert_views_equal(self, reference.view(index, condition, 1, True), actual)
            self.assertEqual(actual[1].count("action_visible_"), limit)
            self.assertNotIn("action_hidden_", actual[1])

    def test_missing_current_no_keys_and_no_history_match(self):
        events = [make_event("prior", 90), make_event("target", 100, ()),
                  {"event_id": "empty", "timestamp": 100, "run_id": "run", "fragments": []}]
        reference, fast = Replay(events), FastReplay(events)
        for index in range(len(events)):
            for condition in ({"kind": "clean"}, {"kind": "random", "drop_probability": 1}):
                for history in (False, True):
                    assert_views_equal(self, reference.view(index, condition, 1, history), fast.view(index, condition, 1, history))

    def test_duplicate_ids_from_direct_callers_use_reference_tie_behavior(self):
        events = [make_event("duplicate", 90, text="first"), make_event("target", 100),
                  make_event("duplicate", 90, text="second")]
        reference, fast = Replay(events), FastReplay(events)
        self.assertTrue(fast._reference_fallback)
        assert_views_equal(self, reference.view(1, {"kind": "clean"}, 1, True), fast.view(1, {"kind": "clean"}, 1, True))


def benchmark_dense_replay(count=20000, queries=100):
    """Optional synthetic benchmark; checks exact CSR bytes before reporting."""
    events = dense_events(count, mixed=False)
    indices = sorted(range(len(events)), key=lambda i: events[i]["timestamp"])[-queries:]
    timings, matrices = {}, {}
    for name, constructor in (("reference", Replay), ("fast", FastReplay)):
        start = time.perf_counter()
        replay = constructor(events)
        timings[name + "_index_seconds"] = time.perf_counter() - start
        start = time.perf_counter()
        matrices[name] = replay.matrix(indices, {"kind": "clean"}, 20260920, "entity_context", 32768)
        timings[name + "_matrix_seconds"] = time.perf_counter() - start
    assert_csr_equal(matrices["reference"], matrices["fast"])
    return {"events": count, "queries": queries, "csr_exact_equal": True,
            **timings, "matrix_speedup": timings["reference_matrix_seconds"] / timings["fast_matrix_seconds"]}


if __name__ == "__main__":
    unittest.main()
