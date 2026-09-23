"""Synthetic qualification/arithmetic checks; no real experiment outcomes."""
import unittest
import numpy as np

from experiments.praxis_next.measurement_praxis.evidence.paired_reanalysis.reanalysis import (
    SCHEMA, contrasts, validate_probabilities, require_equal, capture_confusions,
    independent_quantities, audit_and_extend, aggregate, interval,
)
from experiments.praxis_next.d1_benchmark_audit.paired_metrics import (
    PredictionBatch, make_group_bootstrap_plan, paired_comparison,
)


class ReanalysisTests(unittest.TestCase):
    def test_complete_fixed_scope_and_direction(self):
        specs=contrasts()
        self.assertEqual(len(specs),36)
        self.assertEqual(sum(s['study']=='PX081' for s in specs),27)
        self.assertEqual(len({tuple(s.values()) for s in specs}),36)
        for s in specs:
            if s['study']=='PX081':
                self.assertTrue(s['baseline'].endswith('_entropy.npz'))
                self.assertTrue(s['candidate'].endswith('_harm.npz'))
            else:
                self.assertNotIn('conventional_random',str(s))
                self.assertIn('past_only_anchor',s['baseline'])

    def test_bad_probabilities_and_native_argmax_tie(self):
        self.assertEqual(validate_probabilities(np.array([[.5,.5,0,0]]),1).tolist(),[0])
        for bad in [np.ones((1,3))/3,np.array([[np.nan,0,0,1]]),np.array([[2,-1,0,0]]),np.array([[.1]*4])]:
            with self.assertRaises(ValueError):validate_probabilities(bad,1)
        with self.assertRaises(ValueError):require_equal([1,2],[2,1],'order')

    def test_independent_full_audit_rare_stage_and_repeated_groups(self):
        truth=np.array([0,0,1,1,2,3,0,1,3])
        a=np.array([0,1,0,2,1,3,0,1,0]);b=np.array([0,0,1,0,0,3,0,1,3])
        groups=np.array([6,6,6,6,6,6,7,7,7]);rows=np.arange(len(truth))
        plan=make_group_bootstrap_plan(rows,groups,group_unit='test capture',n_resamples=100,seed=42)
        result=paired_comparison(PredictionBatch(rows,truth,a,SCHEMA,groups),PredictionBatch(rows,truth,b,SCHEMA,groups),bootstrap=plan)
        weights=np.array([[d.count(g) for g in (6,7)] for d in plan.draws])
        cm_a=capture_confusions(truth,a,groups,[6,7]);cm_b=capture_confusions(truth,b,groups,[6,7])
        self.assertEqual(audit_and_extend(result,cm_a,cm_b,weights),20)
        self.assertGreater(result['bootstrap']['intervals']['delta_macro_f1']['undefined_replicates'],0)
        self.assertEqual(result['bootstrap']['intervals']['stages']['LateralMovement']['delta_attack_to_benign_count']['undefined_replicates'],0)
        repeated=np.einsum('g,gij->ij',np.array([2,0]),cm_a)
        np.testing.assert_array_equal(repeated,cm_a[0]*2)
        self.assertTrue(np.isnan(independent_quantities(cm_a[1])['macro_f1']))

    def test_same_capture_draws_across_distinct_cohorts(self):
        p=make_group_bootstrap_plan([1,2,3],[6,6,7],group_unit='capture',n_resamples=20,seed=20260923)
        q=make_group_bootstrap_plan([9,10,11,12],[6,7,7,7],group_unit='capture',n_resamples=20,seed=20260923)
        self.assertEqual(p.draws,q.draws)
        self.assertNotEqual(p.row_ids,q.row_ids)

    def test_support_interval_and_missing_seed_rejected(self):
        ci=interval([None,None,1.])
        self.assertIsNone(ci['lower']);self.assertEqual(ci['valid_replicates'],1)
        with self.assertRaises(ValueError):aggregate([{'spec':contrasts()[0]}])

    def test_corrupted_library_output_is_detected(self):
        truth=np.arange(4);groups=np.array([6,6,7,7]);rows=np.arange(4)
        plan=make_group_bootstrap_plan(rows,groups,group_unit='capture',n_resamples=10,seed=42)
        batch=PredictionBatch(rows,truth,truth,SCHEMA,groups)
        result=paired_comparison(batch,batch,bootstrap=plan)
        result['baseline']['macro_f1']=.2
        cm=capture_confusions(truth,truth,groups,[6,7])
        weights=np.array([[d.count(g) for g in (6,7)] for d in plan.draws])
        with self.assertRaises(ValueError):audit_and_extend(result,cm,cm,weights)


if __name__=='__main__':unittest.main()
