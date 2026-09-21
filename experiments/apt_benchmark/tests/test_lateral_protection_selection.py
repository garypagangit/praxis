import unittest
import numpy as np
from experiments.apt_benchmark.lateral_protection_experiment.selection import frontier, select_policies, point_gate


class SelectionTests(unittest.TestCase):
    def test_frontier_matches_exhaustive_strict_thresholds_with_ties(self):
        score = np.array([0., .2, .2, .5, 1., 1.]); y = np.array([0, 0, 1, 1, 0, 1])
        f = frontier(score, y, 0, 1)
        for i, t in enumerate(f['threshold']):
            flags = score > t
            self.assertEqual(f['fp'][i], int((flags & (y == 0)).sum()))
            self.assertEqual(f['lateral_tp'][i], int((flags & (y == 1)).sum()))
        self.assertEqual(f['fp'][-1], 0)
        self.assertEqual(f['lateral_tp'][0], 3)

    def test_ties_cannot_be_split_to_invent_a_feasible_policy(self):
        y = np.r_[np.zeros(100, dtype=int), np.ones(10, dtype=int)]
        result = select_policies([{'cell_id': 'a', 'scores': np.full(110, .5)}], y, 0, 1)
        self.assertEqual(result['status'], 'INFEASIBLE')

    def test_equal_library_collapses_to_threshold_only_when_identical(self):
        y = np.r_[np.zeros(100, dtype=int), np.ones(100, dtype=int)]
        score = np.r_[np.zeros(99), .8, np.full(97, .9), np.full(3, .7)]
        result = select_policies([{'cell_id': 'first', 'scores': score}, {'cell_id': 'second', 'scores': score}], y, 0, 1)
        self.assertEqual(result['choices']['reference']['selection_lateral_tp'], 100)
        self.assertEqual(result['choices']['candidate']['selection_lateral_tp'], 97)
        self.assertEqual(result['choices']['candidate']['selection_benign_fp'], 0)
        self.assertTrue(result['candidate_equals_threshold_only'])

    def test_infeasible_seed_is_not_dropped_from_aggregate(self):
        self.assertEqual(point_gate([{'selection_status': 'INFEASIBLE'}], 1)['status'], 'INFEASIBLE')
        self.assertEqual(point_gate([], 1)['status'], 'INCOMPLETE')

    def test_bad_score_or_missing_stage_refused(self):
        with self.assertRaises(ValueError): frontier([float('nan'), .2], [0, 1], 0, 1)
        with self.assertRaises(ValueError): frontier([.1, .2], [0, 0], 0, 1)

    def test_exact_gate_boundaries_are_not_rounded_to_success(self):
        def metrics(fp,tp):
            return {'fp':fp,'benign_n':1000,'benign_fpr':fp/1000,
                    'per_stage':{'LateralMovement':{'n':100,'detected':tp,'recall':tp/100}}}
        row={'selection_status':'SELECTED','partitions':{'verification':{'candidate':metrics(4,97),'reference':metrics(5,100)}}}
        result=point_gate([row],1)
        self.assertFalse(result['guards']['false_alarm_reduction_at_least_20pct'])
        self.assertFalse(result['guards']['lateral_loss_less_than_3pp'])
        self.assertEqual(result['status'],'DEVELOPMENT_NEGATIVE')


if __name__ == '__main__': unittest.main()
