"""Tampering checks for the read-only CPU prescreen auditor; no model fitting."""
import copy
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch.audit_cpu_prescreen import (
    BASELINES, FOUNDATIONS, check_arrays, score, verify_primary, verify_scores,
)


class PrescreenAuditTests(unittest.TestCase):
    def test_changed_valid_probabilities_fail_saved_metric_check(self):
        y = np.array([0, 0, 1, 1])
        p = np.array([[.9, .1], [.6, .4], [.2, .8], [.7, .3]])
        classes = ["Attack", "NormalTraffic"]
        weights = np.array([1., 1., 4., 4.])
        cell = {"query_unweighted_metrics": score(y, p, classes),
                "prevalence_weighted_estimated_metrics": score(y, p, classes, weights),
                "sampled_benign_false_positives": 1,
                "estimated_original_test_benign_false_positives": 4.}
        verify_scores(cell, y, p, classes, weights)
        tampered = p.copy()
        tampered[3] = [.3, .7]  # Still a valid distribution, but a different result.
        with self.assertRaises(ValueError):
            verify_scores(cell, y, tampered, classes, weights)

    def test_positive_reweighted_rows_fail_reconstructed_query_contract(self):
        expected = {"query_indices": np.array([7, 2, 9]),
                    "query_weights": np.array([1., 29.2275390625, 1.])}
        check_arrays(expected, expected)
        changed = copy.deepcopy(expected)
        changed["query_weights"][1] = 29.
        with self.assertRaisesRegex(ValueError, "query_weights"):
            check_arrays(changed, expected)

    def test_gate_summary_tampering_and_missing_foundation_rejected(self):
        seeds = [20260921, 20260922, 20260923]
        risky = ["InitialCompromise", "DataExfiltration"]
        protocol = {"seeds": seeds, "primary_candidate": "tabicl_v2", "high_risk_classes": risky,
                    "macro_f1_delta_min": .02, "mean_recall_delta_min": -.05}
        cells = []
        for seed in seeds:
            for model in BASELINES + FOUNDATIONS:
                # XGB wins fitting CV even though LightGBM's test F1 is higher.
                f1 = .5 if model == "xgboost" else (.8 if model == "lightgbm" else .6)
                cells.append({"model": model, "seed": seed, "inner_cv_selected_macro_f1": .7 if model == "xgboost" else .6,
                              "prevalence_weighted_estimated_metrics": {"macro_f1": f1, "per_stage": {name: {"recall": .6} for name in risky}}})
        pairs = [{"seed": seed, "comparator_selected_by_e1_inner_cv": "xgboost", "candidate_weighted_estimated_macro_f1": .6,
                  "comparator_weighted_estimated_macro_f1": .5, "weighted_estimated_macro_f1_delta": .1,
                  "high_risk_recall_deltas": {name: 0. for name in risky}} for seed in seeds]
        reported = {"status": "PRELIMINARY_PROMISING", "primary_candidate": "tabicl_v2", "paired_seed_count": 3,
                    "required_paired_seeds": 3, "mean_weighted_estimated_macro_f1_delta": .1,
                    "mean_high_risk_recall_deltas": {name: 0. for name in risky},
                    "guards": {"mean_weighted_estimated_macro_f1_gain_at_least_0.02": True,
                               **{name + "_mean_recall_loss_at_most_0.05": True for name in risky}}, "pairs": pairs}
        verify_primary(cells, protocol, reported)
        changed = copy.deepcopy(reported)
        changed["mean_weighted_estimated_macro_f1_delta"] = .11
        with self.assertRaises(ValueError):
            verify_primary(cells, protocol, changed)
        with self.assertRaisesRegex(ValueError, "15 unique"):
            verify_primary(cells[:-1], protocol, reported)


if __name__ == "__main__":
    unittest.main()
