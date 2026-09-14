"""Synthetic reviewer controls, specified without fitting to model outcomes."""
import unittest

import numpy as np

from audit_010_extended_postrun import (Checks, POLICIES, admission_equal,
                                      calibration_counts, comparison_counts,
                                      expected_action, expected_truth, indexed,
                                      seeded_clean)


class ReviewerControls(unittest.TestCase):
    def test_float32_multiply_is_not_float64_multiply(self):
        predicted = np.array([.1, 1.234567, -2.345678], dtype=np.float32)
        observed = np.array([1.7, 4.1, -1.4], dtype=np.float64)
        oracle, action, actual = expected_action('alarm_only_blend', 'att', 80, True, observed, predicted)
        expected = np.multiply(predicted, np.float32(.8), dtype=np.float32).astype(np.float64) + .2 * observed
        wrong = .8 * predicted.astype(np.float64) + .2 * observed
        self.assertIsNone(oracle)
        self.assertEqual(action, 'blend')
        self.assertTrue(np.array_equal(actual, expected))
        self.assertFalse(np.array_equal(actual, wrong))
        self.assertFalse(admission_equal(wrong, actual))

    def test_historical_second_coefficient_is_not_literal_point2(self):
        predicted = np.zeros(3, dtype=np.float32)
        observed = np.array([1., 1000., -1.], dtype=np.float64)
        _, _, historical = expected_action('historical_oracle_blend', 'att', 71, True, observed, predicted)
        _, _, deployable = expected_action('alarm_only_blend', 'att', 71, True, observed, predicted)
        self.assertTrue(np.array_equal(historical, (1 - .8) * observed))
        self.assertFalse(np.array_equal(historical, deployable))

    def test_oracle_and_clean_control_are_distinct(self):
        observed, predicted = [10., 20., 30.], [0., 0., 0.]
        for stream, t in [('att', 70), ('cln', 71)]:
            oracle, action, admitted = expected_action('historical_oracle_blend', stream, t, True, observed, predicted)
            self.assertIs(oracle, False)
            self.assertEqual(action, 'observed')
            self.assertTrue(admission_equal(observed, admitted))
        oracle, action, _ = expected_action('historical_oracle_blend', 'att', 71, True, observed, predicted)
        self.assertIs(oracle, True)
        self.assertEqual(action, 'blend')

    def test_freeze_is_no_admission_not_zero_or_last_value(self):
        oracle, action, value = expected_action('literal_freeze', 'cln', 60, True, [1, 2, 3], [0, 0, 0])
        self.assertEqual((oracle, action, value), (None, 'freeze', None))
        self.assertTrue(admission_equal(None, None))
        self.assertFalse(admission_equal([0, 0, 0], None))

    def test_universe_rejects_same_count_duplicate(self):
        checks = Checks()
        row = {'policy': 'rolling', 'seed': 1, 'stream': 'att', 't': 71}
        with self.assertRaises(ValueError):
            indexed([row, row], {('rolling', 1, 'att', 71), ('rolling', 1, 'att', 72)}, checks, 'control')
        self.assertFalse(checks.passed)

    def test_episode_and_point_denominators_not_pooled(self):
        rows = []
        for policy in POLICIES:
            for stream in ('att', 'cln'):
                for seed in (1, 2):
                    for t in (71, 72, 73):
                        rows.append({'policy': policy, 'stream': stream, 'seed': seed, 't': t,
                                     'alarm': stream == 'att' and seed == 1})
        for result in comparison_counts(rows):
            self.assertEqual(result['attack_points'], 6)
            self.assertEqual(result['clean_points'], 6)
            self.assertEqual(result['detected_episodes'], 1)
            self.assertEqual(result['episode_denominator'], 2)
            self.assertEqual(result['alarm_attack_points'], 3)
            self.assertEqual(result['alarm_clean_points'], 0)

    def test_alignment_and_end_missing_targets(self):
        truth = expected_truth(np.arange(4031, dtype=np.float64) + .125)
        self.assertEqual(truth.shape, (3941, 15, 1))
        self.assertEqual(truth.dtype, np.dtype('float32'))
        self.assertTrue(np.array_equal(truth[0, :, 0], np.arange(90, 105) + .125))
        self.assertEqual(truth[-1, 0, 0], 4030.125)
        self.assertTrue(np.isnan(truth[-1, 1:, 0]).all())
        self.assertEqual(np.isnan(truth).sum(), 105)
        self.assertFalse(np.isnan(truth).all(axis=(1, 2)).any())

    def test_calibration_excludes_training_counts(self):
        rows = [{'scored': False, 'alarm': True, 'label': 1},
                {'scored': True, 'alarm': True, 'label': 1},
                {'scored': True, 'alarm': True, 'label': 0},
                {'scored': True, 'alarm': False, 'label': 0}]
        self.assertEqual(calibration_counts(rows), {'scored_positions': 3, 'true_positive_points': 1,
                         'false_positive_points': 1, 'anomaly_points': 1, 'normal_points': 2})

    def test_seed_reconstruction_reproducible_independent_stream(self):
        one = seeded_clean(1, 101)
        self.assertTrue(np.array_equal(one, seeded_clean(1, 101)))
        self.assertFalse(np.array_equal(one, seeded_clean(2, 101)))
        self.assertTrue(np.allclose(one[0], [1., .31, -.21] + .01 * np.random.RandomState(1).randn(3), atol=0, rtol=0))


if __name__ == '__main__':
    unittest.main()
