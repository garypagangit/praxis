"""Review-budget and family aggregation safeguards for the bounded diagnostic."""
import unittest

import numpy as np

from experiments.apt_benchmark.window_diagnostic.run import select_review, summarize


def row(i, label, run='a', steps=None):
    return {'window_id': f'{run}:{i}', 'run_id': run, 'label': label,
            'positive_source_step_ids': steps or []}


class ReviewBudgetTests(unittest.TestCase):
    def test_unknown_competes_for_full_grid_budget(self):
        rows = [row(0, -1), row(1, 1, steps=['step']), row(2, 0), row(3, 0)]
        scores = np.array([.9, .8, .2, .1])
        result = summarize(rows, scores, .25)
        self.assertEqual(result['reviewed'], 1)
        self.assertEqual(result['selected_unknown'], 1)
        self.assertEqual(result['recall'], 0)
        self.assertEqual(result['known_only_budget']['recall'], 1)
        self.assertEqual(result['confirmed_positive_yield_lower_bound'], 0)
        self.assertEqual(result['possible_positive_yield_upper_bound'], 1)

    def test_tie_selection_does_not_consult_labels_or_row_order(self):
        rows = [row(i, i % 3 - 1) for i in range(20)]
        scores = np.zeros(20)
        selected = select_review(rows, scores, .1)
        flipped = [{**r, 'label': 1 - r['label']} for r in reversed(rows)]
        again = select_review(flipped, scores, .1)
        self.assertEqual({r['window_id'] for r, s in zip(rows, selected) if s},
                         {r['window_id'] for r, s in zip(flipped, again) if s})

    def test_rounding_and_chance_are_per_run(self):
        rows = [row(i, int(i == 0)) for i in range(3)] + [row(i, int(i < 2), 'b') for i in range(11)]
        result = summarize(rows, np.zeros(14), .1)
        self.assertEqual(result['reviewed'], 3)
        self.assertAlmostEqual(result['chance_recall'], (1/3 + 2*2/11)/3)

    def test_source_interval_touch_is_not_bin_recall(self):
        rows = [row(0, 1, steps=['s']), row(1, 1, steps=['s']), row(2, 0)]
        result = summarize(rows, np.array([1., .5, 0.]), .1)
        self.assertEqual(result['recall'], .5)
        self.assertEqual(result['source_interval_touch_recall'], 1)


if __name__ == '__main__':
    unittest.main()
