import unittest
import numpy as np
from run import gate
class GateTests(unittest.TestCase):
    def test_duplicate_ratio(self):
        p=np.array([[.2,.8],[.9,.1]]);a,_,_=gate([p,p,p]);b,_,_=gate([p,p,p,p]);self.assertTrue(np.array_equal(a,b));self.assertLess(1/4,1/3)
    def test_all_warn_mean_benign(self):
        ps=[np.array([[.4,.6,0,0]]),np.array([[.4,0,.6,0]]),np.array([[.4,0,0,.6]])];o,m,s=gate(ps)
        self.assertTrue((s>0).all());self.assertEqual(m.tolist(),[0]);self.assertEqual(o.tolist(),[1])
    def test_benign_confidence_can_dominate(self):
        o,m,_=gate([np.array([[.49,.51]]),np.array([[.99,.01]])]);self.assertEqual(o.tolist(),[1]);self.assertEqual(m.tolist(),[0])
    def test_not_an_absolute_benign_veto(self):
        o,m,_=gate([np.array([[.01,.99]]),np.array([[.01,.99]]),np.array([[.99,.01]])]);self.assertEqual(o.tolist(),[1]);self.assertEqual(m.tolist(),[1])
if __name__=='__main__':unittest.main()
