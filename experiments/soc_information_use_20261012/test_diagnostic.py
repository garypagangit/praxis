import unittest
from diagnostic import score, rotations, WRAPPER


class DiagnosticTests(unittest.TestCase):
    def test_aligned_information_and_rotations(self):
        commands = ['ls','cat fresh.txt','pwd','echo ok','true']
        outputs = ['fresh.txt','','/work','','']
        scores = rotations(commands,outputs)
        self.assertEqual(scores[0]['hit_fraction'],.25)
        self.assertTrue(all(s['hit_fraction']==0 for s in scores[1:]))
        self.assertEqual(outputs,['fresh.txt','','/work','',''])

    def test_prior_output_subtracted_after_rotation(self):
        self.assertEqual(score(['ls','ls','cat a.txt'],['a.txt','a.txt',''])['hit_fraction'],0)

    def test_no_opportunity_is_undefined(self):
        self.assertIsNone(score(['true','true'],['',''])['hit_given_opportunity'])

    def test_exactly_four_transitions_for_five_commands(self):
        scores = rotations(['true']*5,['']*5)
        self.assertEqual(len(scores),5)
        self.assertTrue(all(len(s['transitions'])==4 for s in scores))

    def test_missed_wrapper_variants(self):
        self.assertTrue(WRAPPER.search('Here is a truncated version:'))
        self.assertTrue(WRAPPER.search('<START_TOOL_OUTPUT>'))
        self.assertFalse(WRAPPER.search('report.txt'))

    def test_setup_sensitivity_removes_opportunity_and_hit(self):
        s = score(['ls','cat db.sql'],['db.sql',''],{'db.sql'})
        self.assertEqual(s['hit_fraction'],0)
        self.assertIsNone(s['hit_given_opportunity'])


if __name__=='__main__':
    unittest.main()
