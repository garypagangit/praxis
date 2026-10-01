import unittest
import numpy as np
from run import groups,episodes,queue
class WorkloadTests(unittest.TestCase):
    def test_window_boundary(self):
        m={'y':np.array([0,1]),'src':np.array(['a','a']),'dst':np.array(['b','b']),'block':np.array(['x','x']),'end':np.array([899.,900.])};u,r=groups(m,15,'pair');self.assertNotEqual(u[0],u[1]);self.assertEqual(r[u].tolist(),[900.,1800.])
    def test_episode_gap_exact_boundary(self):
        m={'y':np.array([3,3,3]),'src':np.array(['a']*3),'block':np.array(['x']*3),'start':np.array([0.,3600.,7201.]),'end':np.array([10.,3610.,7211.])};e,_,_=episodes(m,60);self.assertEqual(e.tolist(),[0,0,1])
    def test_shift_end(self):
        s,f,w=queue(np.array([16.9*3600]),1,15);self.assertEqual(s[0],86400+9*3600);self.assertEqual(f[0]-s[0],900)
    def test_fifo_and_parallel_staff(self):
        r=np.array([9*3600.]*3);s,f,w=queue(r,2,15);self.assertEqual(s.tolist(),[32400.,32400.,33300.]);self.assertEqual(w.tolist(),[0,1,0])
    def test_more_cases_can_delay_exfil(self):
        _,f,_=queue(np.array([32400.,32401.]),1,15);self.assertGreater(f[1],32401.+900)
if __name__=='__main__':unittest.main()
