"""Synthetic-only mathematical checks; never reads the actual dataset files."""
import itertools
import unittest

from experiments.praxis_next.d1_benchmark_audit.support_cutoff_audit import support_bound


class SupportBoundTests(unittest.TestCase):
    def test_nonempty_and_binding_classes(self):
        result = support_bound({'a': [0, 1, 10], 'b': [2, 3, 8]})
        self.assertTrue(result['start_only_count_support_possible'])
        self.assertEqual((result['lower_exclusive'], result['upper_inclusive']), (3, 8))
        self.assertEqual(result['lower_binding_classes'], ['b'])
        self.assertEqual(result['upper_binding_classes'], ['b'])

    def test_equal_bounds_are_infeasible_under_strict_fit_rule(self):
        result = support_bound({'a': [0, 1, 2], 'b': [1, 2, 3]})
        self.assertFalse(result['start_only_count_support_possible'])
        self.assertEqual(result['lower_exclusive'], result['upper_inclusive'])

    def test_reversed_bounds(self):
        result = support_bound({'early': [0, 1, 2], 'late': [8, 9, 10]})
        self.assertFalse(result['start_only_count_support_possible'])
        self.assertEqual(result['lower_binding_classes'], ['late'])
        self.assertEqual(result['upper_binding_classes'], ['early'])

    def test_ties_are_not_split_by_row_order(self):
        self.assertFalse(support_bound({'a': [5, 5, 5]})['start_only_count_support_possible'])
        self.assertTrue(support_bound({'a': [5, 5, 6]})['start_only_count_support_possible'])

    def test_insufficient_rows(self):
        self.assertFalse(support_bound({'a': [1, 2]})['start_only_count_support_possible'])
        result = support_bound({'a': [1], 'b': [1, 2, 3]})
        self.assertFalse(result['start_only_count_support_possible'])
        self.assertIsNone(result['lower_exclusive'])
        self.assertEqual(result['classes_with_fewer_than_two_rows'], ['a'])

    def test_empty_classes_raise_instead_of_disappearing(self):
        for inputs in [{}, {'a': []}]:
            with self.assertRaises(ValueError):
                support_bound(inputs)

    def test_exhaustive_small_tied_sequences_match_direct_counting(self):
        sequences = list(itertools.combinations_with_replacement(range(4), 3))
        cutoffs = [i / 2 for i in range(-1, 10)]
        for a, b in itertools.product(sequences, repeat=2):
            expected = any(all(sum(t < cutoff for t in times) >= 2 and sum(t >= cutoff for t in times) >= 1
                               for times in [a, b]) for cutoff in cutoffs)
            self.assertEqual(support_bound({'a': a, 'b': b})['start_only_count_support_possible'], expected)

    def test_start_support_does_not_establish_duration_validity(self):
        # Two earlier starts could belong to flows that finish after the only
        # later event. The start-only interval stays possible; completed-flow
        # qualification must not be inferred from it.
        starts, ends = [0, 1, 2], [100, 100, 3]
        result = support_bound({'a': starts})
        self.assertTrue(result['start_only_count_support_possible'])
        self.assertFalse(any(sum(end < cutoff for end in ends) >= 2 and
                             sum(start >= cutoff for start in starts) >= 1
                             for cutoff in [0, .5, 1, 1.5, 2, 3, 101]))
        self.assertFalse(result['uses_flow_durations_or_arrival_times'])
        self.assertFalse(result['deployment_validity_established'])


if __name__ == '__main__':
    unittest.main()
