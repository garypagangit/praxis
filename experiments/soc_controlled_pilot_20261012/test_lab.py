import unittest
from lab import Target,Recorder,TASKS


class LabTests(unittest.TestCase):
    def test_feedback_solutions_all_tasks(self):
        for task in TASKS:
            t=Target(task,42)
            obj=t.execute('read inventory.txt')[0].split()[-1]
            if task=='discovery': value=t.execute('query '+obj)[0]
            elif task=='constraint':
                parameter=t.execute('query '+obj)[1].split()[-1]
                value=t.execute('query '+obj+' '+parameter)[0]
            elif task=='conflict':
                self.assertNotEqual(t.execute('query '+obj)[0],t.token)
                value=t.execute('verify '+obj)[0].split()[-1]
            else:
                self.assertEqual(t.execute('export '+obj+' json')[2],5)
                value=t.execute('export '+obj+' text-v2')[0]
            self.assertEqual(t.execute('submit '+value)[2],0)
            self.assertTrue(t.success)

    def test_wrong_value_and_unknown_command(self):
        t=Target('discovery',1)
        self.assertNotEqual(t.execute('submit guessed')[2],0)
        self.assertNotEqual(t.execute('rm -rf /')[2],0)
        self.assertFalse(t.success)

    def test_common_capture_and_truncation(self):
        a=Recorder(Target('discovery',1),output_cap=5)
        row=a.submit('help')
        self.assertTrue(row['truncated'])
        self.assertLessEqual(len(row['stdout'].encode())+len(row['stderr'].encode()),5)
        self.assertGreaterEqual(row['completed_ms'],row['submitted_ms'])
        self.assertNotIn('origin',row)
        self.assertNotIn('seed',row)

    def test_matched_environments(self):
        a,b=Target('constraint',9),Target('constraint',9)
        for c in ['help','list','read inventory.txt','query guessed']:
            self.assertEqual(a.execute(c),b.execute(c))

    def test_variant_changes_literal_not_mechanic(self):
        a,b=Target('discovery',1),Target('discovery',2)
        self.assertNotEqual(a.object,b.object)
        self.assertEqual(a.execute('help'),b.execute('help'))


if __name__=='__main__':unittest.main()
