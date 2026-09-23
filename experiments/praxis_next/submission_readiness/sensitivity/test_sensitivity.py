"""Synthetic omission/statistic tests; never loads actual experiment counts."""
import unittest
import numpy as np

from experiments.praxis_next.submission_readiness.sensitivity.run import (
    metrics,mean_metrics,difference,direction,summarize_pair,signature,expected_specs,summarize_values,
)


class SensitivityTests(unittest.TestCase):
    def test_unsupported_stage_null_macro_and_rate_not_count(self):
        a=np.diag([4,2,0,3]);p=metrics(a)
        self.assertIsNone(p['macro_f1']);self.assertIsNone(p['movement_exact_recall'])
        self.assertEqual(p['exfil_to_benign_count'],0)
        a[3,3]=0;p=metrics(a)
        self.assertIsNone(p['exfil_warning_recall']);self.assertEqual(p['exfil_to_benign_count'],0)
        self.assertIsNone(direction(difference(p,p))['f1_up_exfil_warning_down'])

    def test_capture_weighting_and_support_alignment(self):
        first=np.diag([10,2,1,3]);second=np.diag([1,2,1,1]);second[3,0]=4
        m=metrics(first+second)
        self.assertEqual(m['exfil_warning_recall'],.5)
        self.assertNotAlmostEqual(m['exfil_warning_recall'],(metrics(first)['exfil_warning_recall']+metrics(second)['exfil_warning_recall'])/2)
        with self.assertRaises(ValueError):summarize_pair(first,second)

    def test_seed_average_is_not_pooled_f1(self):
        first=np.diag([1,1,1,1]);second=np.array([[1,0,0,0],[2,0,0,0],[2,0,0,0],[2,0,0,0]])
        average=mean_metrics([metrics(first),metrics(second)])
        self.assertNotAlmostEqual(average['macro_f1'],metrics(first+second)['macro_f1'])
        unsupported=metrics(np.diag([1,1,0,1]))
        self.assertIsNone(mean_metrics([metrics(first),unsupported])['macro_f1'])

    def test_equivalent_confusions_do_not_prove_identical_predictions(self):
        truth=np.array([0,0,1,1,2,2,3,3]);a=np.array([0,1,1,0,2,0,3,0]);b=np.array([1,0,0,1,0,2,0,3])
        ca=np.zeros((4,4),int);cb=np.zeros((4,4),int)
        np.add.at(ca,(truth,a),1);np.add.at(cb,(truth,b),1)
        self.assertFalse(np.array_equal(a,b));np.testing.assert_array_equal(ca,cb)
        left=np.broadcast_to(ca,(5,4,4));right=np.broadcast_to(np.eye(4,dtype=int),(5,4,4))
        self.assertEqual(signature(left,right),signature(np.broadcast_to(cb,(5,4,4)),right))
        self.assertNotEqual(signature(left,right),signature(right,left))

    def test_direction_and_complete_scope(self):
        p=metrics(np.eye(4,dtype=int));delta=difference(p,p);delta.update(macro_f1=.02,exfil_warning_recall=-.1)
        self.assertTrue(direction(delta)['f1_up_exfil_warning_down'])
        delta['macro_f1']=1e-13;self.assertFalse(direction(delta)['sign_disagreement'])
        self.assertEqual(len(expected_specs()),36)
        self.assertEqual(sum(s['study']=='PX081' for s in expected_specs()),27)
        values=summarize_values([None,-1,0,2]);self.assertEqual(values['undefined'],1)
        self.assertEqual((values['negative'],values['zero'],values['positive']),(1,1,1))


if __name__=='__main__':unittest.main()
