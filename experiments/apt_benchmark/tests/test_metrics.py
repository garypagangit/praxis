import json
import unittest

import numpy as np

from experiments.apt_benchmark.metrics import (
    absolute_gain_feasibility, binary_metrics, early_detection_metrics, stage_metrics,
)


def episode(identity='a', start=0, end=100, impact=80):
    return dict(episode_id=identity, onset_at=start, observation_end_at=end, impact_at=impact)


def alarm(identity='a', decision=20, feature=18, score=19, **extra):
    return dict(episode_id=identity, decision_at=decision, feature_available_at=feature,
                score_available_at=score, **extra)


class BinaryMetricTests(unittest.TestCase):
    def test_continuous_ranking_not_thresholded_labels(self):
        result = binary_metrics([0, 0, 1, 1], [.1, .4, .35, .8])
        self.assertEqual(result['confusion'], dict(tp=1, fp=0, tn=2, fn=1))
        self.assertAlmostEqual(result['f1'], 2 / 3)
        self.assertAlmostEqual(result['roc_auc'], .75)
        self.assertAlmostEqual(result['average_precision'], 5 / 6)
        self.assertAlmostEqual(result['balanced_accuracy'], .75)
        self.assertAlmostEqual(result['mcc'], 1 / np.sqrt(3))

    def test_strict_threshold_ties_and_reversed_scores(self):
        tied = binary_metrics([0, 1], [.5, .5], .5)
        self.assertEqual(tied['confusion']['tp'], 0)
        self.assertEqual(tied['roc_auc'], .5)
        self.assertIsNone(tied['precision'])
        self.assertIsNone(tied['mcc'])
        self.assertEqual(binary_metrics([0, 1], [1, 0])['roc_auc'], 0)

    def test_single_class_and_zero_weight_class_are_undefined(self):
        for labels, weights in [([1, 1], None), ([0, 0], None), ([0, 1], [0, 1])]:
            with self.subTest(labels=labels, weights=weights):
                result = binary_metrics(labels, [.2, .9], sample_weight=weights)
                for name in ('roc_auc', 'average_precision', 'balanced_accuracy', 'mcc'):
                    self.assertIsNone(result[name])
                    self.assertIn(name, result['undefined'])
                json.dumps(result, allow_nan=False)

    def test_pooled_and_group_macro_are_not_conflated(self):
        result = binary_metrics([1] * 9 + [1], [1] * 9 + [0], groups=['large'] * 9 + ['small'])
        self.assertEqual(result['recall'], .9)
        self.assertEqual(result['group_summary']['macro']['recall']['value'], .5)
        self.assertEqual(result['group_summary']['macro']['roc_auc']['defined_groups'], 0)
        weighted = binary_metrics([0, 1, 1], [.9, .9, .1], sample_weight=[2, 1, 3])
        self.assertEqual(weighted['weighted_confusion'], dict(tp=1., fp=2., tn=0., fn=3.))
        self.assertEqual(weighted['confusion'], dict(tp=1, fp=1, tn=0, fn=1))

    def test_bad_truth_scores_weights_and_groups_fail_closed(self):
        for labels, scores, kwargs in [([], [], {}), ([0, 2], [0, 1], {}),
                                       ([0, 1], [0, np.nan], {}), ([0, 1], [0, 1], {'sample_weight': [0, 0]}),
                                       ([0, 1], [0, 1], {'sample_weight': [-1, 2]}),
                                       ([0, 1], [0, 1], {'groups': ['a']})]:
            with self.subTest(labels=labels, kwargs=kwargs), self.assertRaises(ValueError):
                binary_metrics(labels, scores, **kwargs)


class StageTests(unittest.TestCase):
    def test_multilabel_support_absent_stages_and_no_chronology(self):
        result = stage_metrics([[1, 1, 0], [0, 1, 0]], [[.9, .8, .1], [.2, .9, .1]],
                               stage_names=['execution', 'discovery', 'impact'], stage_source='source:map-v1')
        self.assertEqual(result['per_stage']['execution']['f1'], 1)
        self.assertEqual(result['per_stage']['discovery']['n_attack'], 2)
        self.assertIsNone(result['per_stage']['impact']['recall'])
        self.assertEqual(result['macro']['roc_auc']['defined_stages'], 1)
        self.assertFalse(result['chronology_inferred'])

    def test_categorical_uses_argmax_but_continuous_rank(self):
        result = stage_metrics(['benign', 'execution', 'execution'], [[.8, .7], [.4, .6], [.5, .45]],
                               stage_names=['benign', 'execution'], stage_source='source:map-v1', mode='categorical')
        execution = result['per_stage']['execution']
        self.assertEqual(execution['confusion'], dict(tp=1, fp=0, tn=1, fn=1))
        self.assertEqual(execution['roc_auc'], 0)

    def test_stage_truth_and_chronology_guards(self):
        for kwargs in [dict(stage_source=''), dict(stage_source='map', chronology_claim=True),
                       dict(stage_source='map', mode='invalid')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                stage_metrics([[1]], [[.9]], stage_names=['stage'], **kwargs)
        with self.assertRaises(ValueError):
            stage_metrics(['unmapped'], [[.9]], stage_names=['stage'], stage_source='map', mode='categorical')
        with self.assertRaises(ValueError):
            stage_metrics([[None]], [[.9]], stage_names=['stage'], stage_source='map')


class AttainabilityTests(unittest.TestCase):
    def test_previous_impossible_practical_routes_are_caught(self):
        utility = absolute_gain_feasibility(1615 / 1696, .05)
        safety = absolute_gain_feasibility(0, .01, higher_is_better=False)
        self.assertFalse(utility['attainable'])
        self.assertFalse(safety['attainable'])
        self.assertAlmostEqual(utility['maximum_possible_gain'], 81 / 1696)
        self.assertTrue(absolute_gain_feasibility(.95, .05)['attainable'])
        self.assertTrue(absolute_gain_feasibility(0, 0, higher_is_better=False)['attainable'])
        with self.assertRaises(ValueError):
            absolute_gain_feasibility(1.1, .1)


class EarlyDetectionTests(unittest.TestCase):
    def test_misses_remain_in_restricted_delay_and_denominator(self):
        result = early_detection_metrics([episode('a'), episode('b')], [alarm()],
                                          benign_host_hours=10, false_alert_count=3, horizon_seconds=100)
        self.assertEqual(result['restricted_mean_delay_seconds'], 60)
        self.assertEqual(result['right_censored_episodes'], 1)
        self.assertEqual(result['detected_before_impact_fraction_all_episodes'], .5)
        self.assertEqual(result['false_alerts_per_benign_host_hour'], .3)
        self.assertEqual(result['detection_curve'][-1]['fraction_all_episodes_lower_bound'], .5)
        self.assertTrue(result['episodes'][1]['right_censored'])

    def test_longer_horizon_not_imputed_from_short_followup(self):
        result = early_detection_metrics([episode('a', end=10, impact=None), episode('b')], [], horizon_seconds=100)
        self.assertIsNone(result['restricted_mean_delay_seconds'])
        self.assertEqual(result['horizon_status'], 'UNDEFINED_INSUFFICIENT_FOLLOWUP')
        self.assertIsNone(result['detection_curve'][-1]['fully_observed_fraction'])
        common = early_detection_metrics([episode('a', end=10, impact=None), episode('b')], [])
        self.assertEqual(common['horizon_seconds'], 10)
        self.assertEqual(common['restricted_mean_delay_seconds'], 10)

    def test_impact_missing_censored_and_zero_opportunity_are_explicit(self):
        result = early_detection_metrics([episode('missing', impact=None), episode('short', end=10),
                                           episode('zero', impact=0)], [])
        self.assertIsNone(result['detected_before_impact_fraction_all_episodes'])
        self.assertEqual(result['impact_missing_episodes'], 1)
        self.assertEqual(result['impact_unresolved_followup_episodes'], 1)
        self.assertEqual(result['zero_preimpact_opportunity_episodes'], 1)
        self.assertEqual(result['detected_before_impact_fraction_evaluable'], 0)

    def test_availability_and_future_event_guards(self):
        for invalid in [alarm(feature=21), alarm(score=21), alarm(feature=19, score=18),
                        alarm(feature_event_cutoff_at=19)]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                early_detection_metrics([episode()], [invalid])

    def test_causal_alarm_filter_and_timestamp_timezones(self):
        result = early_detection_metrics([episode()], [alarm(decision=-1, feature=-3, score=-2),
                     alarm(decision=101, feature=99, score=100), alarm(None)], false_alert_count=2)
        self.assertEqual(result['ignored_alarms'], dict(unattributed=1, before_onset=1, after_observation_end=1))
        self.assertEqual(result['detected_episodes'], 0)
        self.assertIsNone(result['false_alerts_per_benign_host_hour'])
        times = episode(start='2026-01-01T00:00:00Z', end='2026-01-01T01:00:00+00:00', impact=None)
        actual = alarm(decision='2026-01-01T00:01:00Z', feature='2026-01-01T00:00:30Z', score='2026-01-01T00:00:59Z')
        self.assertEqual(early_detection_metrics([times], [actual])['episodes'][0]['delay_seconds'], 60)
        with self.assertRaises(ValueError):
            early_detection_metrics([episode(start='2026-01-01T00:00:00')], [])

    def test_false_alert_exposure_is_not_event_false_positive_rate(self):
        for exposure in [None, 0]:
            result = early_detection_metrics([episode()], [], benign_host_hours=exposure, false_alert_count=0)
            self.assertIsNone(result['false_alerts_per_benign_host_hour'])
            json.dumps(result, allow_nan=False)
        with self.assertRaises(ValueError):
            early_detection_metrics([episode()], [], benign_host_hours=-1)
        with self.assertRaises(ValueError):
            early_detection_metrics([episode()], [], false_alert_count=True)

    def test_unknown_duplicate_episode_and_bad_interval_rejected(self):
        with self.assertRaises(ValueError):
            early_detection_metrics([episode()], [alarm('other')])
        with self.assertRaises(ValueError):
            early_detection_metrics([episode(), episode()], [])
        with self.assertRaises(ValueError):
            early_detection_metrics([episode(start=101)], [])


if __name__ == '__main__':
    unittest.main()
