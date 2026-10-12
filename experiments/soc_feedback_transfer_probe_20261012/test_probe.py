import unittest
from probe import local_use,features


class ProbeTests(unittest.TestCase):
    def test_missing_output_not_negative_evidence(self):
        self.assertEqual(local_use(['ls','cat file.txt'],[None,''],[True]),([0,0,0],0,0))

    def test_local_witness_and_setup_exclusion(self):
        self.assertEqual(local_use(['ls','cat file.txt'],['file.txt',''],[True]),([1,1,1],1,1))
        self.assertEqual(local_use(['ls','cat db.sql'],['db.sql',''],[True]),([0,0,0],0,1))

    def test_no_cross_gap_or_echo_credit(self):
        self.assertEqual(local_use(['ls','cat a.txt'],['a.txt',''],[False]),([0,0,0],0,0))
        self.assertEqual(local_use(['cat a.txt','cat a.txt'],['a.txt',''],[True]),([0,0,0],0,1))

    def test_command_baseline_independent_of_results(self):
        bb=[{'id':'x','index':i,'origin':'H','log':'same','qualified':True,
             'px125_syntax':'single','px125_observable':True} for i in range(5)]
        a={('x',i):('ls','file.txt') for i in range(5)}
        b={('x',i):('ls',None) for i in range(5)}
        aa=features(bb,a)
        changed=[{**r,'qualified':False,'px125_observable':False} for r in bb]
        bb_features=features(changed,b)
        self.assertEqual(aa['C'],bb_features['C'])
        self.assertEqual(aa['command_text'],bb_features['command_text'])
        self.assertNotEqual(aa['O'],bb_features['O'])


if __name__=='__main__':unittest.main()
