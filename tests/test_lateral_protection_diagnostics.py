"""Tied-boundary frontier examples; no scientific fitting or evaluation."""
import unittest

import numpy as np

from experiments.apt_benchmark.lateral_protection_experiment import diagnostics


class FrontierTests(unittest.TestCase):
    def test_tied_normal_and_lateral_scores_cannot_be_split(self):
        y = np.r_[np.zeros(100, dtype=int), np.ones(10, dtype=int)]
        scores = np.r_[np.zeros(98), [.9, .9], np.full(9, .9), .1]
        out = diagnostics.group_frontiers([{"cell_id": "xgboost/natural", "scores": scores}], y, 0, 1)["all_fit_library"]
        self.assertFalse(out["joint_1pct_fpr_90pct_lateral_feasible"])
        self.assertEqual(out["maximum_lateral_recall_at_fpr_at_most_1pct"]["lateral_tp"], 0)
        needed = out["minimum_fpr_for_lateral_recall_at_least_90pct"]
        self.assertEqual(needed["benign_fp"], 2)
        self.assertEqual(needed["benign_fpr"], .02)
        self.assertEqual([r["threshold"] for r in needed["tied_thresholds"]], [0, .1])
        self.assertEqual([r["lateral_tp"] for r in needed["tied_thresholds"]], [10, 9])

    def test_exact_budget_boundary_and_all_attaining_models_are_retained(self):
        y = np.r_[np.zeros(100, dtype=int), np.ones(10, dtype=int)]
        scores = np.r_[np.zeros(99), .9, np.full(10, .9)]
        cells = [{"cell_id": name, "scores": scores} for name in ["xgboost/natural", "lightgbm/balanced"]]
        group = diagnostics.group_frontiers(cells, y, 0, 1)
        out = group["all_fit_library"]
        self.assertTrue(out["joint_1pct_fpr_90pct_lateral_feasible"])
        self.assertEqual(out["minimum_fpr_for_lateral_recall_at_least_90pct"]["benign_fpr"], .01)
        self.assertEqual(out["maximum_lateral_recall_at_fpr_at_most_1pct"]["attaining_cell_ids"], ["lightgbm/balanced", "xgboost/natural"])
        self.assertEqual(out["maximum_lateral_recall_at_fpr_at_most_1pct"]["tied_threshold_count"], 2)
        # At n=99, one false positive exceeds 1%; rounding cannot make it eligible.
        y99, scores99 = y[1:], scores[1:]
        smaller = diagnostics.group_frontiers([{"cell_id": "xgboost/natural", "scores": scores99}], y99, 0, 1)["all_fit_library"]
        self.assertFalse(smaller["joint_1pct_fpr_90pct_lateral_feasible"])
        self.assertEqual(smaller["maximum_benign_fp_at_1pct"], 0)


if __name__ == "__main__":
    unittest.main()
