"""Hand-checked boundary cases for LAC sets and honest empirical reporting."""
import json
import math
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch.conformal import (
    evaluate_lac, evaluate_sets, finite_sample_quantile, fit_lac, predict_sets,
)


class ConformalTests(unittest.TestCase):
    def test_finite_sample_order_statistic_is_not_interpolated(self):
        self.assertEqual(finite_sample_quantile([0.1, 0.2, 0.3, 0.4], 0.4), 0.3)
        self.assertEqual(finite_sample_quantile([0.4, 0.1, 0.3, 0.2], 0.4), 0.3)
        self.assertEqual(finite_sample_quantile([0.1] * 8 + [0.9], 0.1), 0.9)
        self.assertTrue(math.isinf(finite_sample_quantile([0.1] * 8, 0.1)))
        self.assertTrue(math.isinf(finite_sample_quantile([], 0.1)))

    def test_class_support_determines_mondrian_vacuity(self):
        probabilities = np.tile([0.9, 0.05, 0.05], (9, 1))
        calibration = fit_lac(probabilities, ["a"] * 9, method="mondrian",
                              class_labels=["a", "b", "c"])
        self.assertAlmostEqual(calibration.thresholds[0], 0.1)
        self.assertTrue(math.isinf(calibration.thresholds[1]))
        self.assertTrue(math.isinf(calibration.thresholds[2]))
        sets = predict_sets([[0.01, 0.49, 0.50], [0.9, 0.05, 0.05]], calibration)
        np.testing.assert_array_equal(sets, [[False, True, True], [True, True, True]])
        self.assertEqual(calibration.calibration_class_counts, (9, 0, 0))

    def test_small_nonempty_class_also_gets_infinite_quantile(self):
        calibration = fit_lac([[0.9, 0.1], [0.1, 0.9]], [0, 1], method="mondrian")
        self.assertTrue(all(math.isinf(q) for q in calibration.thresholds))
        np.testing.assert_array_equal(predict_sets([[0, 1], [1, 0]], calibration),
                                      [[True, True], [True, True]])

    def test_no_singleton_filling_and_ties_are_included(self):
        calibration = fit_lac(np.tile([0.9, 0.1], (9, 1)), [0] * 9)
        sets = predict_sets([[0.5, 0.5], [0.9, 0.1], [0.1, 0.9]], calibration)
        self.assertEqual(sets.dtype, np.dtype(bool))
        np.testing.assert_array_equal(sets, [[False, False], [True, False], [False, True]])

    def test_marginal_and_class_conditional_use_different_score_pools(self):
        calibration_probabilities = [[0.9, 0.1]] * 9 + [[0.4, 0.6]] * 9
        labels = [0] * 9 + [1] * 9
        marginal = fit_lac(calibration_probabilities, labels)
        mondrian = fit_lac(calibration_probabilities, labels, method="mondrian")
        self.assertAlmostEqual(marginal.thresholds[0], 0.4)
        self.assertAlmostEqual(marginal.thresholds[1], 0.4)
        self.assertAlmostEqual(mondrian.thresholds[0], 0.1)
        self.assertAlmostEqual(mondrian.thresholds[1], 0.4)
        np.testing.assert_array_equal(predict_sets([[0.7, 0.3]], marginal), [[True, False]])
        np.testing.assert_array_equal(predict_sets([[0.7, 0.3]], mondrian), [[False, False]])

    def test_all_metrics_have_hand_checked_denominators(self):
        sets = np.asarray([[False, False, False], [True, False, False],
                           [True, True, True], [False, True, False]], dtype=bool)
        metrics = evaluate_sets(sets, [0, 0, 1, 0])
        self.assertEqual(metrics["count"], 4)
        self.assertEqual(metrics["covered"], 2)
        self.assertEqual(metrics["coverage"], 0.5)
        self.assertEqual(metrics["mean_set_size"], 1.25)
        self.assertEqual(metrics["median_set_size"], 1)
        self.assertEqual(metrics["empty_fraction"], 0.25)
        self.assertEqual(metrics["full_fraction"], 0.25)
        self.assertEqual(metrics["singleton_fraction"], 0.5)
        self.assertEqual(metrics["singleton_correct"], 1)
        self.assertEqual(metrics["singleton_accuracy"], 0.5)
        self.assertEqual(metrics["per_class"][0]["coverage"], 1 / 3)
        self.assertEqual(metrics["per_class"][1]["coverage"], 1)
        self.assertIsNone(metrics["per_class"][2]["coverage"])

    def test_no_singletons_and_empty_test_have_undefined_metrics(self):
        metrics = evaluate_sets(np.ones((3, 2), dtype=bool), [0, 0, 1])
        self.assertEqual(metrics["coverage"], 1)
        self.assertEqual(metrics["full_fraction"], 1)
        self.assertIsNone(metrics["singleton_accuracy"])
        empty = evaluate_sets(np.empty((0, 2), dtype=bool), [])
        self.assertEqual(empty["count"], 0)
        self.assertIsNone(empty["coverage"])
        self.assertIsNone(empty["mean_set_size"])
        self.assertIsNone(empty["singleton_fraction"])
        self.assertIsNone(empty["per_class"][0]["coverage"])

    def test_empty_calibration_returns_full_sets_with_json_safe_metadata(self):
        for method in ("marginal", "mondrian"):
            calibration = fit_lac(np.empty((0, 2)), [], method=method)
            np.testing.assert_array_equal(predict_sets([[0.99, 0.01]], calibration), [[True, True]])
            metadata = calibration.to_dict()
            self.assertEqual(metadata["thresholds"], [None, None])
            self.assertEqual(metadata["threshold_infinite"], [True, True])
            json.dumps(metadata, allow_nan=False)

    def test_convenience_has_prespecified_levels_and_no_test_label_feedback(self):
        cal_probs = np.tile([0.8, 0.2], (19, 1))
        first = evaluate_lac(cal_probs, [0] * 19, [[0.9, 0.1]], [0])
        second = evaluate_lac(cal_probs, [0] * 19, [[0.9, 0.1]], [1])
        self.assertEqual([(x["nominal_coverage"], x["method"]) for x in first["evaluations"]],
                         [(0.9, "marginal"), (0.9, "mondrian"),
                          (0.95, "marginal"), (0.95, "mondrian")])
        self.assertEqual([x["calibration"] for x in first["evaluations"]],
                         [x["calibration"] for x in second["evaluations"]])
        self.assertEqual(first["evaluations"][0]["metrics"]["coverage"], 1)
        self.assertEqual(second["evaluations"][0]["metrics"]["coverage"], 0)
        json.dumps(first, allow_nan=False)

    def test_probability_column_order_is_explicit_and_consistent(self):
        calibration = fit_lac(np.tile([0.9, 0.1], (9, 1)), ["stage-b"] * 9,
                              class_labels=["stage-b", "stage-a"])
        result = evaluate_sets(predict_sets([[0.9, 0.1]], calibration), ["stage-b"],
                               class_labels=calibration.class_labels)
        self.assertEqual(result["coverage"], 1)
        self.assertEqual(result["per_class"][0]["class_label"], "stage-b")

    def test_bad_inputs_fail_without_silent_probability_repair(self):
        invalid_probabilities = ([0.8, 0.2], [[0.2, 0.2]], [[float("nan"), 0.5]],
                                 [[-0.1, 1.1]], [[float("inf"), 0]], [[]])
        for probabilities in invalid_probabilities:
            with self.subTest(probabilities=probabilities), self.assertRaises(ValueError):
                fit_lac(probabilities, [0])
        for alpha in (0, 1, -0.1, float("nan")):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                fit_lac([[0.8, 0.2]], [0], alpha=alpha)
        for kwargs in ({"class_labels": [0, 0]}, {"class_labels": [0]}, {"method": "other"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                fit_lac([[0.8, 0.2]], [0], **kwargs)
        with self.assertRaises(ValueError):
            fit_lac([[0.8, 0.2]], [2])
        with self.assertRaises(ValueError):
            fit_lac([[0.8, 0.2]], [])
        with self.assertRaises(ValueError):
            predict_sets([[1]], fit_lac([[0.8, 0.2]], [0]))
        with self.assertRaises(ValueError):
            evaluate_sets([[0, 1]], [1])


if __name__ == "__main__":
    unittest.main()
