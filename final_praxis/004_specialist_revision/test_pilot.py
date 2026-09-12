import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('pilot',Path(__file__).with_name('pilot.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ProtocolTests(unittest.TestCase):
    def test_edit_and_fallback(self):
        base={'sympy/a.py':'x = 1\n'}
        response={'text':json.dumps({'decision':'REVISE','edits':[{'path':'sympy/a.py','old':'x = 1','new':'x = 2'}]}),'finish_reason':'end_turn'}
        changed,receipt=m.candidate_from_response(base,base,response)
        self.assertEqual(changed['sympy/a.py'],'x = 2\n');self.assertTrue(receipt['protocol_valid'])
        response['finish_reason']='max_tokens';changed,receipt=m.candidate_from_response(base,base,response)
        self.assertEqual(changed,base);self.assertFalse(receipt['protocol_valid'])
    def test_scope_and_ambiguous_edits(self):
        for path in ['../outside.py','sympy/tests/test_x.py','/sympy/a.py','setup.py']:
            self.assertFalse(m.allowed_source(path))
        with self.assertRaises(ValueError):m.apply_edits({'sympy/a.py':'x=1\nx=1\n'},{'decision':'REVISE','edits':[{'path':'sympy/a.py','old':'x=1','new':'x=2'}]})
    def test_probe_admission_code(self):
        m.validate_probe('from sympy import Integer\ndef test_small():\n    assert Integer(2)+2 == 4\n')
        for source in ['import os\ndef test_x(): pass','def test_x():\n    open("x")','def test_x(): pass\ndef test_y(): pass']:
            with self.assertRaises(ValueError):m.validate_probe(source)
    def test_model_context_has_no_evaluator(self):
        issue={'instance_id':'x','repo':'sympy/sympy','base_commit':'abc','problem_statement':'public issue','patch':'PRIVATE_GOLD','test_patch':'PRIVATE_TEST'}
        messages=m.initial_messages(issue,'public source')
        self.assertNotIn('PRIVATE',json.dumps(messages))
    def test_qualification_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);m.save(path/'qualification_summary.json',{'qualified':False})
            with self.assertRaises(RuntimeError):m.require_qualification(path)
if __name__=='__main__':unittest.main()
