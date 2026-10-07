"""Tests for label-independent budget selection and unsupported-view behavior."""
import unittest,numpy as np,json
from budget_replay import rank
from observation_contract import assess
class Tests(unittest.TestCase):
 def test_budget_and_strict_ranking(self):
  ids,r=rank(np.array([9.,1.,7.,7.,0.]),2,17);self.assertEqual(len(ids),2);self.assertIn(0,ids);self.assertEqual(r['boundary_ties'],2)
 def test_ties_repeatable(self):
  a,_=rank(np.ones(100),20,17);b,_=rank(np.ones(100),20,17);c,_=rank(np.ones(100),20,29);np.testing.assert_array_equal(a,b);self.assertFalse(np.array_equal(a,c));self.assertEqual(len(set(a)),20)
 def test_invalid_scores_and_budget(self):
  for scores,b in [([np.nan],1),([1],0),([1],2),([[1,2]],1)]:
   with self.assertRaises(ValueError):rank(scores,b)
 def test_observation_is_not_identity(self):
  self.assertFalse(assess('truncate32')['deployment_certified']);self.assertTrue(assess('truncate32')['logging_80pct_f1_gate']);self.assertFalse(assess('verbs')['logging_80pct_f1_gate']);self.assertEqual(assess('unknown_view')['decision'],'unmeasured_view')
if __name__=='__main__':unittest.main()
