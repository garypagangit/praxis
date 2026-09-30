import unittest
import numpy as np
from common import decisions,metrics
class Tests(unittest.TestCase):
    def test_mean_erases_warning(self):
        p=np.array([[[.1,.8,.1]],[[.9,.05,.05]],[[.9,.05,.05]]]);o,m,s=decisions(p)
        self.assertEqual(o.tolist(),[1]);self.assertEqual(m.tolist(),[0])
    def test_stage_only_warning_members(self):
        p=np.array([[[.1,.46,.44]],[[.51,0,.49]],[[.51,0,.49]]]);o,_,_=decisions(p);self.assertEqual(o.tolist(),[1])
    def test_ties(self):
        p=np.array([[[.2,.4,.4]],[[.8,.1,.1]]]);o,m,_=decisions(p);self.assertEqual(o.tolist(),[1]);self.assertEqual(m.tolist(),[0])
    def test_all_benign(self):
        o,_,_=decisions(np.array([[[.8,.1,.1]],[[.6,.2,.2]]]));self.assertEqual(o.tolist(),[0])
    def test_fixed_macro_and_absent(self):
        m=metrics(np.array([0,0]),np.array([0,0]),4);self.assertEqual(m['macro_f1'],.25);self.assertIsNone(m['movement']['warning_recall'])
    def test_or_bounds_and_nested(self):
        rng=np.random.default_rng(9);p=rng.dirichlet(np.ones(4),size=(10,200));y=rng.integers(0,4,200);prev=np.zeros(200,bool)
        for n in [1,2,3,5,7,10]:
            o,_,s=decisions(p[:n]);w=o>0;self.assertTrue(np.all(w[prev]));prev=w
            self.assertLessEqual(int(((y==0)&w).sum()),sum(int(((y==0)&(v>0)).sum()) for v in s))
if __name__=='__main__':unittest.main()
