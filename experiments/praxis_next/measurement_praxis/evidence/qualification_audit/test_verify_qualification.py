"""Synthetic-only checks for the independent counting implementation."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import itertools
import unittest

from experiments.praxis_next.measurement_praxis.evidence.qualification_audit.verify_qualification import direct_counts, from_ns, parse_recorded, sweep_support, to_ns


def blocks_for(a, b):
    blocks = defaultdict(Counter)
    for label, values in [('a', a), ('b', b)]:
        for value in values:
            blocks[value][label] += 1
    return blocks


class IndependentVerifierTests(unittest.TestCase):
    def test_exhaustive_small_sweeps_against_direct_cutoff_counts(self):
        sequences = list(itertools.combinations_with_replacement(range(4), 3))
        for a, b in itertools.product(sequences, repeat=2):
            blocks = blocks_for(a, b)
            result = sweep_support(blocks)
            possible = any(all(v['fit'] >= 2 and v['test'] >= 1 for v in direct_counts(blocks, cut).values())
                           for cut in [i/2 for i in range(-2, 11)])
            self.assertEqual(result['possible'], possible)

    def test_tied_event_block_is_indivisible(self):
        result = sweep_support(blocks_for([5, 5, 5], [0, 1, 10]))
        self.assertFalse(result['possible'])

    def test_known_interval_by_actual_counts(self):
        result = sweep_support(blocks_for([0, 1, 10], [2, 3, 8]))
        self.assertEqual((result['lower_exclusive'], result['upper_inclusive']), (3, 8))
        self.assertFalse(result['clock_or_duration_validity_claim'])

    def test_disjoint_stage_timelines_have_no_state(self):
        self.assertFalse(sweep_support(blocks_for([0, 1, 2], [8, 9, 10]))['possible'])

    def test_nanosecond_conversion_is_timezone_independent(self):
        value = datetime(2015, 10, 21, 10, 21, 12)
        self.assertEqual(from_ns(to_ns(value)), value)
        self.assertEqual(to_ns(value + timedelta(microseconds=1))-to_ns(value), 1000)

    def test_recorded_formats_do_not_repair_or_invent_timezone(self):
        value = parse_recorded('01/17/1970 12:29', ('%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M'))
        self.assertEqual(value.year, 1970)
        self.assertIsNone(value.tzinfo)
        with self.assertRaises(ValueError):
            parse_recorded('bad-date', ('%Y-%m-%d %H:%M:%S',))


if __name__ == '__main__':
    unittest.main()
