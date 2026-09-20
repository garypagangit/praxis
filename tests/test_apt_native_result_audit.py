"""Small independently calculable checks for the post-run evidence auditor."""
import unittest

import numpy as np

from experiments.apt_final.native_graph.analysis.verify_results import (
    AuditFailure, average_precision, calibrated_margin, error_changes,
    expected_scenarios, metrics,
)


class NativeResultAuditTests(unittest.TestCase):
    def test_hand_calculated_metrics_and_average_precision(self):
        result = metrics(np.array([1, 0, 1, 0]), np.array([.9, .8, .7, .6]), np.array([1, 1, 0, 0]))
        self.assertEqual([result[k] for k in ("tp", "fp", "tn", "fn")], [1, 1, 1, 1])
        for name in ("precision", "recall", "f1", "accuracy", "false_positive_rate"):
            self.assertEqual(result[name], .5)
        self.assertAlmostEqual(result["average_precision"], 5 / 6)

    def test_score_ties_are_one_precision_threshold(self):
        self.assertEqual(average_precision(np.array([1, 0, 1, 0]), np.array([.5, .5, .1, .1])), .5)

    def test_no_attack_ap_undefined_and_invalid_predictions_refused(self):
        self.assertIsNone(average_precision(np.array([0, 0]), np.array([.2, .1])))
        with self.assertRaises(AuditFailure):
            metrics(np.array([0, 1]), np.array([.2, .3]), np.array([0, 2]))

    def test_corrected_and_introduced_errors_are_distinct(self):
        y = np.array([0, 1, 1, 0])
        reference = np.array([1, 0, 1, 0])
        candidate = np.array([0, 1, 0, 0])
        self.assertEqual(error_changes(y, candidate, reference), {
            "corrected_errors": 2, "introduced_errors": 1, "both_wrong": 0})

    def test_calibration_counts_ties_conservatively(self):
        margin = calibrated_margin(np.array([1., 1., 2.]), np.array([1., 2., 3.]), .25)
        np.testing.assert_allclose(margin, np.log([.25, .5, 1.]))
        np.testing.assert_array_equal(margin >= 0, [False, False, True])

    def test_full_removal_masks_are_duplicate_inputs_and_self_edges_count_twice(self):
        config = {"mask_seeds": [11, 29], "drop_rates": [0., 1.]}
        graph = {"y": np.array([0, 1, 0]), "src": np.array([0, 0, 1]), "dst": np.array([0, 1, 2])}
        scenarios = list(expected_scenarios(config, graph))
        self.assertEqual(len(scenarios), 3)
        np.testing.assert_array_equal(scenarios[0]["degree"], [3, 2, 1])
        self.assertEqual(scenarios[1]["input_mask_sha256"], scenarios[2]["input_mask_sha256"])
        self.assertEqual(scenarios[1]["observed_edges"], 0)
        self.assertEqual(scenarios[1]["isolated_nodes"], 3)


if __name__ == "__main__":
    unittest.main()
