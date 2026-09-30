"""Boundary tests independent of the actual campaign outcomes."""
import unittest
import numpy as np
from deferral import ledger
from recalibration import eligible
from common import stage_threshold

class Boundaries(unittest.TestCase):
    def test_delay_is_milliseconds_and_strict(self):
        m={'capture':np.array([5,5,6]),'start':np.array([0,0,86400000]),'end':np.array([0,1,86400001])}
        mask,_=eligible(m,6,24,'cumulative',86400000)
        self.assertFalse(mask.any())
        mask,_=eligible(m,6,0,'cumulative',86400000)
        np.testing.assert_array_equal(mask,[True,True,False])
    def test_recent_does_not_reach_back_for_favorable_support(self):
        m={'capture':np.array([5,6,7]),'start':np.array([0,100,200]),'end':np.array([50,150,250])}
        mask,_=eligible(m,7,0,'recent',100)
        np.testing.assert_array_equal(mask,[False,True,False])
    def test_fifo_capacity_and_unresolved_are_preserved(self):
        request=np.ones(100,bool);capture=np.ones(100,int);start=np.arange(100)[::-1]
        served,waiting,parts=ledger(request,capture,start,1000)
        self.assertEqual(served.sum(),1);self.assertEqual(waiting.sum(),99);self.assertTrue(served[-1]);self.assertFalse((served&waiting).any())
    def test_empty_requests_do_not_consume_capacity(self):
        served,waiting,_=ledger(np.zeros(100,bool),np.ones(100,int),np.arange(100),1000)
        self.assertEqual(served.sum()+waiting.sum(),0)
    def test_missing_stage_forces_explicit_fallback(self):
        p=np.tile([.01,.99,0,0],(100,1));y=np.ones(100,int)
        t,counts=stage_threshold(p,y,.05,'all_stages_fail_closed')
        self.assertEqual(t,0);self.assertEqual(counts[2],0)
        t,_=stage_threshold(p,y,.05,'supported_stages');self.assertGreater(t,0)
    def test_monotonicity_does_not_imply_warning_retention(self):
        # The arithmetic mean is monotone in both coordinates but loses this warning.
        a,b=.9,.01
        self.assertGreater(a,.5);self.assertLess((a+b)/2,.5)

if __name__=='__main__':unittest.main()
