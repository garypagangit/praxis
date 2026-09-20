"""Synthetic runner guards; mocked estimators only, no model fitting."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from experiments.apt_benchmark.robustness_v2.run import (
    fit_router, predict_bundle, primary_screen, route_states,
)
from experiments.apt_benchmark.robustness.run import summarize


DIMENSIONS = 4


def feature_matrix(states):
    values = np.zeros((len(states), 2 * DIMENSIONS + 10), dtype=float)
    values[:, 2 * DIMENSIONS + 2] = np.asarray(states) & 1
    values[:, 2 * DIMENSIONS + 3] = (np.asarray(states) & 2) / 2
    return sparse.csr_matrix(values)


def protocol():
    return json.loads((Path(__file__).parents[1] / "robustness_v2/protocol.json").read_text())


class ConstantEstimator:
    """Prediction-only test double with explicit positive class column."""
    def __init__(self, value, reverse=False):
        self.value = value
        self.classes_ = np.asarray([1, 0] if reverse else [0, 1])
        self.calls = []

    def predict_proba(self, matrix):
        self.calls.append(matrix.copy())
        values = [self.value, 1 - self.value] if self.classes_[0] == 1 else [1 - self.value, self.value]
        return np.tile(values, (matrix.shape[0], 1))


class RouterScientificGuards(unittest.TestCase):
    def test_routes_use_only_visible_current_command_bits(self):
        matrix = feature_matrix([0, 1, 2, 3]).toarray()
        expected = route_states(sparse.csr_matrix(matrix), DIMENSIONS)
        np.testing.assert_array_equal(expected, [0, 1, 2, 3])
        # Alter all text and remaining observed metadata, including history.
        # Only the two current-event command bits may affect routing.
        matrix[:, :2 * DIMENSIONS] = 99
        for column in range(2 * DIMENSIONS, matrix.shape[1]):
            if column not in (2 * DIMENSIONS + 2, 2 * DIMENSIONS + 3):
                matrix[:, column] = [0, 1, 10, 100]
        np.testing.assert_array_equal(route_states(sparse.csr_matrix(matrix), DIMENSIONS), expected)

    def test_duplicate_augmented_rows_do_not_create_unique_support(self):
        underlying = np.tile(np.arange(3), 40)
        labels = np.tile([1, 1, 0], 40)
        matrix = feature_matrix(np.zeros(len(labels), dtype=int))
        with patch("experiments.apt_benchmark.robustness_v2.run.fit_lr") as fitting:
            bundle = fit_router(matrix, labels, np.ones(len(labels), dtype=bool), underlying,
                                object(), protocol(), 40, DIMENSIONS)
        fitting.assert_not_called()
        self.assertEqual(bundle["experts"], {})
        self.assertEqual(bundle["route_support"]["0"]["unique_positive"], 2)
        self.assertEqual(bundle["route_support"]["0"]["unique_negative"], 1)
        self.assertEqual(bundle["route_support"]["0"]["observed_augmented_rows"], 120)
        self.assertFalse(bundle["route_support"]["0"]["uses_expert"])

    def test_completely_unobserved_targets_cannot_qualify_a_specialist(self):
        # Numerically sufficient unique labels exist, but none are observable.
        labels = np.asarray([1] * 10 + [0] * 40)
        matrix = feature_matrix(np.zeros(len(labels), dtype=int))
        with patch("experiments.apt_benchmark.robustness_v2.run.fit_lr") as fitting:
            bundle = fit_router(matrix, labels, np.zeros(len(labels), dtype=bool), np.arange(len(labels)),
                                object(), protocol(), 6, DIMENSIONS)
        fitting.assert_not_called()
        self.assertTrue(all(s["unique_positive"] == 0 and s["unique_negative"] == 0
                            and s["observed_augmented_rows"] == 0 and not s["uses_expert"]
                            for s in bundle["route_support"].values()))

    def test_supported_expert_gets_only_visible_route_rows_and_fixed_view_weights(self):
        labels = np.tile(np.asarray([1] * 5 + [0] * 25), 6)
        underlying = np.tile(np.arange(30), 6)
        # Fully unobserved, uniquely numbered examples cannot increase support
        # or enter specialist fitting even though their metadata says state1.
        labels = np.concatenate([labels, [1, 0]])
        underlying = np.concatenate([underlying, [100, 101]])
        observed = np.concatenate([np.ones(180, dtype=bool), [False, False]])
        states = np.ones(len(labels), dtype=int)
        matrix = feature_matrix(states)
        base, expert = object(), object()
        with patch("experiments.apt_benchmark.robustness_v2.run.fit_lr", return_value=expert) as fitting:
            bundle = fit_router(matrix, labels, observed, underlying, base, protocol(), 6, DIMENSIONS)
        fitting.assert_called_once()
        fitted_matrix, fitted_labels, _, weights = fitting.call_args.args
        self.assertEqual(fitted_matrix.shape[0], 180)
        np.testing.assert_array_equal(fitted_labels, labels[:180])
        np.testing.assert_array_equal(weights, np.full(180, 1 / 6))
        self.assertAlmostEqual(float(weights.sum()), 30)
        self.assertIs(bundle["base"], base)
        self.assertIs(bundle["experts"][1], expert)
        self.assertEqual(bundle["route_support"]["1"]["unique_positive"], 5)
        self.assertEqual(bundle["route_support"]["1"]["unique_negative"], 25)
        self.assertFalse(bundle["route_support"]["0"]["uses_expert"])

    def test_router_uses_matching_experts_fallback_and_zero_unobserved_score(self):
        base = ConstantEstimator(.7)
        experts = {0: ConstantEstimator(.1), 1: ConstantEstimator(.3, reverse=True), 3: ConstantEstimator(.9)}
        matrix = feature_matrix([0, 1, 2, 3, 1])
        observed = np.asarray([True, True, True, True, False])
        scores = predict_bundle({"kind": "observed_router", "base": base, "experts": experts},
                                matrix, observed, DIMENSIONS)
        np.testing.assert_array_equal(scores, [.1, .3, .7, .9, 0])
        self.assertEqual(len(base.calls), 1)
        for expert in experts.values():
            self.assertEqual(len(expert.calls), 1)
            self.assertEqual(expert.calls[0].shape[0], 1)

    def test_single_bundle_respects_positive_class_order_and_invisible_denominator(self):
        matrix = feature_matrix([3, 0, 1])
        observed = np.asarray([True, False, True])
        scores = predict_bundle({"kind": "single", "model": ConstantEstimator(.8, reverse=True)},
                                matrix, observed, DIMENSIONS)
        np.testing.assert_array_equal(scores, [.8, 0, .8])
        labels = np.asarray([1, 1, 0])
        metrics = summarize(labels, scores, observed, .5)
        self.assertEqual(metrics["n"], 3)
        self.assertEqual(metrics["positive"], 2)
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["fn"], 1)
        self.assertEqual(metrics["fp"], 1)
        self.assertEqual(metrics["unobserved_positive_targets"], 1)
        self.assertEqual(metrics["recall"], .5)
        # Observation remains mandatory even for a permissive threshold.
        permissive = summarize(labels, scores, observed, -float("inf"))
        self.assertEqual(permissive["fn"], 1)


def passing_screen_record():
    result = {"status": "COMPLETE", "results": []}
    for condition in ("clean", "command_records_absent", "random_50"):
        for seed in ([20260920, 20260921, 20260922] if condition == "random_50" else [20260920]):
            for arm in ("random_dropout", "mixed_dropout"):
                # Primary improvement is just over the required 5 points.
                f1 = .56 if arm == "mixed_dropout" and condition == "command_records_absent" else .5
                result["results"].append({"condition": condition, "seed": seed, "arm": arm,
                                          "calibrated": {"f1": f1, "recall": .6, "negative_label_flag_rate": .01}})
    return result


class PrimaryScreenGuards(unittest.TestCase):
    def test_all_five_primary_gates_must_pass(self):
        result = primary_screen(passing_screen_record(), protocol())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["checks"]), 5)
        self.assertTrue(all(value["passed"] for value in result["checks"].values()))

    def test_f1_improvement_cannot_hide_excess_recall_loss(self):
        record = passing_screen_record()
        for row in record["results"]:
            if row["arm"] == "mixed_dropout" and row["condition"] == "command_records_absent":
                row["calibrated"]["f1"] = .9
                row["calibrated"]["recall"] = .57
        result = primary_screen(record, protocol())
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["checks"]["command_records_absent_recall_delta_min"]["passed"])
        self.assertTrue(result["checks"]["command_records_absent_f1_delta_min"]["passed"])

    def test_excess_flag_burden_or_clean_harm_fails(self):
        for kind in ("flag", "clean"):
            with self.subTest(kind=kind):
                record = passing_screen_record()
                for row in record["results"]:
                    if row["arm"] != "mixed_dropout":
                        continue
                    if kind == "flag" and row["condition"] == "command_records_absent":
                        row["calibrated"]["negative_label_flag_rate"] = .016
                    if kind == "clean" and row["condition"] == "clean":
                        row["calibrated"]["f1"] = .47
                result = primary_screen(record, protocol())
                self.assertEqual(result["status"], "FAIL")

    def test_random_seed_mean_cannot_select_only_favorable_seed(self):
        record = passing_screen_record()
        rows = [r for r in record["results"] if r["arm"] == "mixed_dropout" and r["condition"] == "random_50"]
        for row, value in zip(rows, [.9, .2, .2]):
            row["calibrated"]["f1"] = value
        result = primary_screen(record, protocol())
        self.assertEqual(result["status"], "FAIL")
        check = result["checks"]["random_50_mean_f1_delta_min"]
        self.assertAlmostEqual(check["delta"], (1.3 / 3) - .5)
        self.assertFalse(check["passed"])

    def test_exact_boundaries_and_unsupported_targets(self):
        record = passing_screen_record()
        for row in record["results"]:
            if row["arm"] != "mixed_dropout":
                continue
            if row["condition"] == "command_records_absent":
                row["calibrated"].update(f1=.55, recall=.58, negative_label_flag_rate=.015)
            else:
                row["calibrated"]["f1"] = .48
        self.assertEqual(primary_screen(record, protocol())["status"], "PASS")
        record["status"] = "UNSUPPORTED_BOTH_CLASSES_REQUIRED"
        self.assertEqual(primary_screen(record, protocol()), {"status": "UNSUPPORTED"})


if __name__ == "__main__":
    unittest.main()
