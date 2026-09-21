"""Synthetic-only E2 timing-selection and real-call accounting tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch import run_e2_latency as e2


class CountingImputer:
    def __init__(self):
        self.calls = 0

    def transform(self, X):
        self.calls += 1
        return X + 2


class CountingModel:
    def __init__(self):
        self.calls = 0
        self.received = []

    def predict_proba(self, X):
        self.calls += 1
        self.received.append(np.asarray(X).copy())
        return np.tile([.3, .7], (len(X), 1))


class E2LatencyTests(unittest.TestCase):
    def test_query_hash_order_is_label_free_and_row_order_stable(self):
        split = np.asarray([0, 2, 1, 2, 2, 0, 2])
        fingerprints = np.asarray([f"{i:064x}" for i in range(7)])
        selected = e2.select_latency_rows(split, fingerprints, seed=11, count=3)
        expected = sorted(np.flatnonzero(split == 2).tolist(), key=lambda i: hashlib.sha256(f"11|{fingerprints[i]}".encode("ascii")).digest())[:3]
        np.testing.assert_array_equal(selected, expected)
        permutation = np.asarray([6, 5, 4, 3, 2, 1, 0])
        other = e2.select_latency_rows(split[permutation], fingerprints[permutation], seed=11, count=3)
        np.testing.assert_array_equal(fingerprints[selected], fingerprints[permutation][other])
        with self.assertRaises(ValueError):
            e2.select_latency_rows(split, fingerprints, seed=11, count=5)

    def test_each_warmup_and_repeat_performs_transform_and_prediction(self):
        stage, screen, imputer = CountingModel(), CountingModel(), CountingImputer()
        clock_values = iter(np.arange(16, dtype=float))
        X = np.zeros((8, 3))
        timing, predictions = e2.paired_predictions(stage, screen, imputer, X, clock=lambda: next(clock_values))
        self.assertEqual(stage.calls, 4)
        self.assertEqual(screen.calls, 4)
        self.assertEqual(imputer.calls, 8)
        for values in stage.received + screen.received:
            np.testing.assert_array_equal(values, X + 2)
        self.assertEqual(timing["measured_seconds"], {"full_stage": [1., 1., 1.], "screen_alone": [1., 1., 1.]})
        self.assertEqual(predictions["screen_alone"].shape, (3, 8, 2))

    def test_necessary_condition_uses_medians_and_does_not_claim_full_success(self):
        passed = e2.latency_decision([10, 100, 10], [2, 1, 20])
        self.assertTrue(passed["necessary_speed_condition_passed"])
        self.assertEqual(passed["status"], "NECESSARY_CONDITION_PASS_ONLY")
        self.assertEqual(passed["observed_optimistic_serial_cascade_speedup_ceiling"], 5)
        failed = e2.latency_decision([.01, .01, .02], [5, 6, 7])
        self.assertFalse(failed["necessary_speed_condition_passed"])
        self.assertEqual(failed["status"], "CPU_CANDIDATE_FAILS_NECESSARY_SPEED_CONDITION")

    def test_missing_or_invalid_measurements_cannot_pass(self):
        for times in ([1, 2], [1, 0, 2], [1, float("nan"), 2], [1, float("inf"), 2]):
            with self.assertRaises(ValueError):
                e2.latency_decision([1, 1, 1], times)

    def test_unfrozen_protocol_cannot_start_scientific_fits(self):
        source = Path(e2.__file__).parent
        protocol = json.loads((source / "protocol_e2_latency.json").read_text(encoding="utf-8"))
        protocol["status"] = "READY_FOR_ROOT_FREEZE_BEFORE_SCIENTIFIC_FITS"
        e1_path = source / "protocol.json"
        e1_protocol = json.loads(e1_path.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "status"):
            e2.validate_protocol(protocol, e1_protocol, e1_path)
        protocol["status"] = "FROZEN_BEFORE_SCIENTIFIC_MODEL_FITS"
        e2.validate_protocol(protocol, e1_protocol, e1_path)
        protocol["e1_protocol_sha256"] = "invalid"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            e2.validate_protocol(protocol, e1_protocol, e1_path)


if __name__ == "__main__":
    unittest.main()
