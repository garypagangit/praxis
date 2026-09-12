import math, unittest
from run_empathy import boundary, token_log_likelihood, metrics
class TestEmpathy(unittest.TestCase):
 def test_first_candidate_token_included(self):
  self.assertEqual(boundary([10,11,12],[10,11,12,20,21]),([10,11,12,20],[20,21],2))
 def test_boundary_merge_rejected(self):
  with self.assertRaises(ValueError):boundary([10,11],[10,99,20])
 def test_shifted_candidate_likelihood(self):
  import torch
  values=token_log_likelihood(torch.tensor([[math.log(3),0.],[0.,math.log(3)]]),[0,1])
  self.assertAlmostEqual(float(values.double().sum()),2*math.log(.75),places=6)
  with self.assertRaises(ValueError):token_log_likelihood(torch.zeros(3,2),[0,1])
 def test_gate_requires_capability_net_and_harm(self):
  def pairs(base,ablated):
   return [{'baseline':{'correct':i in base,'gold':'empathy' if i<32 else 'not empathy'},
            'social_ablation':{'correct':i in ablated,'gold':'empathy' if i<32 else 'not empathy'}} for i in range(64)]
  low=metrics(pairs(set(range(38)),set(range(36))))
  self.assertFalse(low['qualification_gate'])
  self.assertTrue(metrics(pairs(set(range(39)),set(range(37))))['qualification_gate'])
  null=metrics(pairs(set(range(40)),set(range(40))))
  self.assertFalse(null['qualification_gate']);self.assertTrue(null['zero_harm_null'])
if __name__=='__main__':unittest.main()
