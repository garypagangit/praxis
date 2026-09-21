"""Checks for the independent auditor's boundary and metric handling."""
import copy
import unittest

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from experiments.apt_benchmark.window_diagnostic.audit import compare, ids_hash, metrics, ranking_metrics, select


def row(number, label, run="a", steps=None):
    return {"window_id": f"{run}:{number}", "run_id": run, "label": label,
            "positive_source_step_ids": steps or ([f"{run}:target"] if label == 1 else [])}


class WindowDiagnosticAuditTests(unittest.TestCase):
    def test_unknown_can_consume_entire_review_budget(self):
        rows = [row(0, -1), row(1, 1), row(2, 0)]
        result = metrics(rows, np.array([3.0, 2.0, 1.0]), 0.1)
        self.assertEqual(result["reviewed"], 1)
        self.assertEqual(result["recall"], 0)
        self.assertEqual(result["selected_unknown"], 1)
        self.assertEqual(result["unknown_selected_fraction"], 1)
        self.assertEqual(result["confirmed_positive_yield_lower_bound"], 0)
        self.assertEqual(result["possible_positive_yield_upper_bound"], 1)
        self.assertEqual(result["known_only_budget"]["recall"], 1)

    def test_rounding_is_per_run_and_chance_respects_positive_distribution(self):
        rows = [row(0, 1, "short")] + [row(i, int(i == 0), "long") for i in range(11)]
        result = metrics(rows, np.zeros(len(rows)), 0.1)
        self.assertEqual(result["reviewed"], 3)
        self.assertAlmostEqual(result["chance_recall"], (1 + 2 / 11) / 2)

    def test_full_grid_tie_selection_is_invariant_to_labels_and_input_order(self):
        rows = [row(i, i % 3 - 1) for i in range(30)]
        scores = np.zeros(len(rows))
        first = {r["window_id"] for r, chosen in zip(rows, select(rows, scores, 0.1)) if chosen}
        changed = copy.deepcopy(list(reversed(rows)))
        for r in changed:
            r["label"] = 1
        second = {r["window_id"] for r, chosen in zip(changed, select(changed, scores, 0.1)) if chosen}
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)

    def test_ap_auc_hand_checked_ties_and_reversed_ranking(self):
        ap, auc = ranking_metrics([0, 1, 1, 0], [0.5, 0.5, 0.5, 0.5])
        self.assertEqual(ap, 0.5)
        self.assertEqual(auc, 0.5)
        ap, auc = ranking_metrics([1, 0], [0.1, 0.9])
        self.assertEqual(ap, 0.5)
        self.assertEqual(auc, 0)
        self.assertEqual(ranking_metrics([0, 0], [0.2, 0.3]), (None, None))

    def test_independent_rank_metrics_agree_on_tied_imbalanced_samples(self):
        rng = np.random.default_rng(702)
        for count in (11, 50, 503):
            labels = np.zeros(count, dtype=int)
            labels[rng.choice(count, max(2, count // 10), replace=False)] = 1
            scores = rng.integers(-2, 5, size=count).astype(float)
            ap, auc = ranking_metrics(labels, scores)
            self.assertAlmostEqual(ap, average_precision_score(labels, scores), places=13)
            self.assertAlmostEqual(auc, roc_auc_score(labels, scores), places=13)

    def test_repeated_step_intersections_count_once(self):
        rows = [row(0, 1), row(1, 1), row(2, 0)]
        result = metrics(rows, np.array([0.9, 0.8, 0.1]), 0.5)
        self.assertEqual(result["represented_source_intervals"], 1)
        self.assertEqual(result["source_intervals_touched_by_review"], 1)
        self.assertEqual(result["recall"], 1)

    def test_comparison_rejects_tampered_counts_keys_and_nonfinite_values(self):
        compare({"recall": 1 / 3}, {"recall": 1 / 3 + 1e-14})
        for actual, expected in (({"tp": 4}, {"tp": 3}), ({"a": 1, "extra": 0}, {"a": 1}),
                                 (float("nan"), 0.5), (True, 1)):
            with self.assertRaises(ValueError):
                compare(actual, expected)

    def test_training_hash_changes_with_membership_and_order_not_labels(self):
        rows = [row(1, 0), row(2, 1)]
        swapped_labels = copy.deepcopy(rows)
        swapped_labels[0]["label"], swapped_labels[1]["label"] = 1, 0
        self.assertEqual(ids_hash(rows), ids_hash(swapped_labels))
        self.assertNotEqual(ids_hash(rows), ids_hash(list(reversed(rows))))
        self.assertNotEqual(ids_hash(rows), ids_hash(rows[:1]))


if __name__ == "__main__":
    unittest.main()
