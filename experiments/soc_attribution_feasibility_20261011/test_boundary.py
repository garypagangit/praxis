import copy
import unittest
from boundary import project, design_gate, split_audit, validate_origin

def fixture():
    return {'boundary':'managed_serial_session_v1','origin':'A','provider':'SECRET',
        'events':[{'command':'pwd','submitted_ms':0,'completed_ms':2,'stdout':'/lab\n','stderr':'',
                   'exit_code':0,'truncated':False,'tool_wrapper':'SECRET'},
                  {'command':'cat status.txt','submitted_ms':5,'completed_ms':8,
                   'stdout':'ready\n','stderr':'','exit_code':0,'truncated':False}]}

def provenance(origin):
    return {'origin':origin,'runtime_ai':origin in ('A','M'),'offline_ai_assistance':'no',
       'origin_evidence_ref':'fixture-reference','synthetic_fixture':False,
       'recorder_revision':'r1','capture_equivalence_verified':True,'prior_inspection_status':'unseen',
       'task_template':'t1','actor_group':origin+'-actor','environment_group':'env1'}

class BoundaryTests(unittest.TestCase):
    def test_origin_and_wrapper_invariance(self):
        base=fixture(); twin=copy.deepcopy(base)
        twin.update(origin='H',provider='OTHER',participant_id='NEW')
        twin['events'][0]['tool_wrapper']='OTHER'
        for view in ('commands','results','timing'):
            self.assertEqual(project(base,view,10),project(twin,view,10))
            self.assertNotIn('SECRET',str(project(base,view,10)))
    def test_no_future_output_or_command(self):
        out=project(fixture(),'results',1)
        self.assertEqual(len(out['events']),1)
        self.assertIsNone(out['events'][0]['stdout'])
        self.assertIsNone(out['events'][0]['exit_code'])
    def test_late_output_changes_cannot_change_prefix(self):
        a=fixture(); b=copy.deepcopy(a); b['events'][1]['stdout']='secret future'
        self.assertEqual(project(a,'results',6),project(b,'results',6))
    def test_commands_do_not_receive_results_or_time(self):
        self.assertEqual(project(fixture(),'commands',10)['events'][0],{'command':'pwd'})
    def test_results_do_not_receive_time(self):
        self.assertNotIn('execution_ms',project(fixture(),'results',10)['events'][0])
    def test_latency_uses_previous_completion(self):
        r=project(fixture(),'timing',10)['events']
        self.assertIsNone(r[0]['gap_after_previous_completion_ms'])
        self.assertEqual(r[1]['gap_after_previous_completion_ms'],3)
        self.assertEqual(r[1]['execution_ms'],3)
    def test_missing_output_is_not_empty_output(self):
        a=fixture();a['events'][0]['stdout']=None
        self.assertIsNone(project(a,'results',10)['events'][0]['stdout'])
        self.assertEqual(project(a,'results',10)['events'][0]['stderr'],'')
    def test_prefix_limit(self):
        self.assertEqual(len(project(fixture(),'results',10,limit=1)['events']),1)
    def test_reject_wrong_boundary(self):
        a=fixture(); a['boundary']='endpoint_process_log'
        with self.assertRaises(ValueError): project(a,'results',10)
    def test_reject_invalid_clock(self):
        for value in (-1,float('nan'),True):
            a=fixture();a['events'][0]['submitted_ms']=value
            with self.assertRaises(ValueError): project(a,'timing',10)
    def test_reject_overlapping_serial_submissions(self):
        a=fixture();a['events'][1]['submitted_ms']=1
        with self.assertRaises(ValueError): project(a,'timing',10)
    def test_truncation_explicit(self):
        a=fixture(); del a['events'][0]['truncated']
        with self.assertRaises(ValueError): project(a,'results',10)
    def test_fixtures_cannot_be_human_evidence(self):
        r=provenance('H');r['synthetic_fixture']=True
        self.assertFalse(validate_origin(r))
    def test_offline_ai_not_runtime_ai(self):
        r=provenance('M');r['runtime_ai']=False
        self.assertFalse(validate_origin(r))
        r=provenance('S');r['offline_ai_assistance']='yes'
        self.assertFalse(validate_origin(r))
    def test_all_four_arms_and_capture_required(self):
        rows=[provenance(o) for o in 'HSAM']
        self.assertTrue(design_gate(rows)['engineering_ready'])
        self.assertFalse(design_gate(rows)['statistically_qualified'])
        self.assertFalse(design_gate(rows[:-1])['engineering_ready'])
        rows[0]['capture_equivalence_verified']=False
        self.assertFalse(design_gate(rows)['engineering_ready'])
    def test_prior_exposure_blocks_confirmation(self):
        rows=[provenance(o) for o in 'HSAM'];rows[0]['prior_inspection_status']='development'
        self.assertIn('not_fresh_confirmation_data',design_gate(rows)['failures'])
    def test_split_leakage_and_missing_groups(self):
        a={'session_id':'a','trace_hash':'x','actor_group':'p1','task_template':'t1','environment_group':'e1'}
        b={'session_id':'b','trace_hash':'x','actor_group':'p2','task_template':'t2','environment_group':'e2'}
        self.assertFalse(split_audit([a],[b])['pass'])
        b['trace_hash']='y';self.assertTrue(split_audit([a],[b])['pass'])
        del b['actor_group'];self.assertFalse(split_audit([a],[b])['pass'])
    def test_empty_data_never_ready(self):
        self.assertFalse(design_gate([])['engineering_ready'])
        self.assertFalse(split_audit([],[])['pass'])

if __name__=='__main__': unittest.main(verbosity=2)
