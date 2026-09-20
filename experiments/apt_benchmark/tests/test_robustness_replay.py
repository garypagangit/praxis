import unittest
import numpy as np

from experiments.apt_benchmark.robustness.replay import Replay, visible_fragments
from experiments.apt_benchmark.robustness.run import summarize, is_target


def event(identifier, timestamp, key="r/h/pid/1", text="action", channel="SYSCALL", run="r"):
    return {"event_id": identifier, "run_id": run, "split": "test", "timestamp": timestamp,
            "available_at": timestamp, "entity_keys": [key], "labels": [],
            "fragments": [{"channel": channel, "text": text, "timestamp": timestamp, "entity_keys": [key]}]}


class CausalReplayTests(unittest.TestCase):
    def test_future_and_same_timestamp_events_cannot_change_prediction_inputs(self):
        past = event("past", 90, text="past evidence")
        target = event("target", 100)
        base = Replay([past, target]).view(1, {"kind": "clean"}, 1, True)
        expanded = Replay([past, target, event("same", 100, text="forbidden same time"), event("future", 101, text="forbidden future")]).view(1, {"kind": "clean", "deadline": 120}, 1, True)
        self.assertEqual(base[:2], expanded[:2])
        np.testing.assert_array_equal(base[2], expanded[2])

    def test_missing_link_field_cannot_reveal_history(self):
        prior = event("prior", 90, text="secret history")
        target = event("target", 100, key="different", channel="SYSCALL")
        target["fragments"].append({"channel": "PROCTITLE", "text": "command", "timestamp": 100, "entity_keys": ["r/h/pid/1"]})
        replay = Replay([prior, target])
        self.assertIn("secret", replay.view(1, {"kind": "clean"}, 1, True)[1])
        damaged = replay.view(1, {"kind": "channel_absent", "channels": ["PROCTITLE"]}, 1, True)
        self.assertEqual(damaged[1], "")

    def test_delayed_prior_available_only_by_deadline(self):
        prior = event("prior", 90, text="delayed evidence", channel="PROCTITLE")
        target = event("target", 100)
        replay = Replay([prior, target])
        c = {"kind": "delay", "channels": ["PROCTITLE"], "delay_seconds": 30, "deadline": 0}
        self.assertEqual(replay.view(1, c, 1, True)[1], "")
        self.assertIn("delayed", replay.view(1, dict(c, deadline=20), 1, True)[1])

    def test_completely_hidden_target_is_retained_as_miss(self):
        target = event("target", 100)
        replay = Replay([target])
        view = replay.view(0, {"kind": "random", "drop_probability": 1}, 1, True)
        self.assertFalse(view[3])
        metrics = summarize([1, 0], [0, 0], [False, False], -1)
        self.assertEqual(metrics["fn"], 1)
        self.assertEqual(metrics["fp"], 0)
        self.assertEqual(metrics["n"], 2)

    def test_no_cross_run_history(self):
        prior = event("prior", 90, run="other", text="forbidden")
        target = event("target", 100)
        self.assertEqual(Replay([prior, target]).view(1, {"kind": "clean"}, 1, True)[1], "")

    def test_labels_do_not_affect_input(self):
        target = event("target", 100)
        replay = Replay([target])
        before = replay.view(0, {"kind": "clean"}, 1, True)
        target["labels"] = ["escalate", "T1068"]
        after = replay.view(0, {"kind": "clean"}, 1, True)
        self.assertEqual(before[:2], after[:2])
        np.testing.assert_array_equal(before[2], after[2])

    def test_random_removal_consistent_between_target_and_history(self):
        prior = event("prior", 90)
        c = {"kind": "random", "drop_probability": 0.5}
        self.assertEqual(visible_fragments(prior, c, 31, 90, True), visible_fragments(prior, c, 31, 100, False))

    def test_support_burst_keeps_target_but_removes_recent_history(self):
        events = [event("old", 20, text="old history"), event("recent", 90, text="recent history"), event("target", 100)]
        view = Replay(events).view(2, {"kind": "support_burst", "seconds": 60}, 1, True)
        self.assertTrue(view[3])
        self.assertIn("old", view[1])
        self.assertNotIn("recent", view[1])

    def test_technique_id_mapping_is_explicit(self):
        self.assertTrue(is_target(["T1548.003: Sudo"], "T1548"))
        self.assertFalse(is_target(["T15480"], "T1548"))


if __name__ == "__main__":
    unittest.main()
