"""Offline tests of frozen pilot scoring, identities, numerical evidence, and gates."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import audit

HERE=Path(__file__).resolve().parent
DATA=audit.load_json(HERE/'data.json')
PROTOCOL=audit.load_json(HERE/'protocol.json')
DATA_SHA=audit.sha_bytes((HERE/'data.json').read_bytes())
PROTOCOL_SHA=audit.sha_bytes((HERE/'protocol.json').read_bytes())


def technical_fixture():
    details=[]
    for text in PROTOCOL['numerical_prompts']:
        for condition in ('intact','logic_ablation','social_ablation'):
            details.append({'prompt_sha256':audit.text_sha(text),'condition':condition,
                **{name:True for name in ('finite','repeat_equal','ablation_reset_equal','cache_top_token_equal','ablation_routes_zero','eager_sdpa_top_token_equal')},
                'cache_max_abs':0.00001,'eager_sdpa_max_abs':0.00001})
    return {'checks':{name:True for name in audit.TECHNICAL_CHECKS},'details':details,'tolerance':0.001}


def fixture(raw_correct=5,chat_correct=8):
    cells=[]
    for index,row in enumerate(DATA['pilot']):
        for condition in audit.CONDITIONS:
            manifest=row['prompts'][condition]
            correct=index<(raw_correct if condition=='raw' else chat_correct)
            response='The answer is '+(row['gold'] if correct else row['gold']+'0')+'.'
            prefill=[16*manifest['prompt_tokens'],0,0,0];decode=[16,0,0,0]
            cells.append({'split':'pilot','id':row['id'],'condition':condition,'question_sha256':row['question_sha256'],
                'gold':row['gold'],'prompt_sha256':manifest['prompt_sha256'],'protocol_sha256':PROTOCOL_SHA,
                'input_token_ids_sha256':manifest['input_token_ids_sha256'],'prompt_tokens':manifest['prompt_tokens'],
                'response':response,'response_sha256':audit.text_sha(response),'generated_token_ids':[42,128001],
                'stop_reason':'eos','stop_string':None,'tokens':2,'seconds':.25,
                'prefill_routes':prefill,'decode_routes':decode,'routes':[prefill[0]+16,0,0,0]})
    return cells


def run_audit(cells,data=None,protocol=None,technical=None,fast=True):
    args=(DATA if data is None else data,PROTOCOL if protocol is None else protocol,cells,PROTOCOL_SHA,
          technical_fixture() if technical is None else technical,DATA_SHA)
    original=audit.paired_statistics
    def cheap(*aa,**kwargs): kwargs['replicates']=40;return original(*aa,**kwargs)
    if not fast: return audit.audit_records(*args)
    with patch.object(audit,'paired_statistics',side_effect=cheap): return audit.audit_records(*args)


class PilotAuditTests(unittest.TestCase):
    def test_actual_frozen_cohort_and_full_bootstrap_pass_synthetic_boundary(self):
        result=run_audit(fixture(),fast=False)
        self.assertEqual(result['integrity_errors'],[])
        self.assertEqual(result['technical_detail_errors'],[])
        self.assertEqual(result['status'],'COMPLETE')
        self.assertEqual(result['validated_unique_cells'],64)
        self.assertTrue(result['qualification']['passed'])
        self.assertEqual(result['qualification']['decision'],'QUALIFIED_FOR_FRESH_TEST_REGISTRATION')
        self.assertFalse(result['qualification']['automatic_followup'])
        self.assertEqual(result['arms']['chat']['nontruncated_flexible_correct'],8)
        self.assertEqual(result['paired_diagnostics']['chat_minus_raw_completed_correct']['difference'],3/32)
        self.assertEqual(result['paired_diagnostics']['chat_minus_raw_completed_correct']['bootstrap_replicates'],10000)

    def test_pinned_parser_quirks_are_preserved(self):
        self.assertEqual(audit.extract_prediction('The answer is 4. Later 5.','strict'),'4.')
        self.assertEqual(audit.extract_prediction('The answer is 4. Later 5.','flexible'),'5.')
        self.assertEqual(audit.extract_prediction('the answer is 4.','strict'),audit.INVALID)
        self.assertEqual(audit.score_response('4.0','steps #### 4')['flexible_correct'],0)
        self.assertEqual(audit.score_response('$1,234.','steps #### 1234')['flexible_correct'],1)
        self.assertFalse(audit.score_response('...','steps #### 4')['flexible_contains_digit'])

    def test_pilot_integer_thresholds_and_completeness(self):
        chat={'truncated':3,'flexible_contains_digit':29,'nontruncated_flexible_correct':8}
        self.assertTrue(audit.qualification_gate(chat,True,True)['passed'])
        for field,value in [('truncated',4),('flexible_contains_digit',28),('nontruncated_flexible_correct',7)]:
            self.assertFalse(audit.qualification_gate({**chat,field:value},True,True)['passed'])
        self.assertFalse(audit.qualification_gate(chat,False,True)['passed'])
        self.assertFalse(audit.qualification_gate(chat,True,False)['passed'])

    def test_truncated_correct_answer_is_scored_but_cannot_satisfy_completion_gate(self):
        cells=fixture();cell=next(r for r in cells if r['condition']=='chat')
        cell.update(generated_token_ids=[42]*1024,tokens=1024,stop_reason='token_cap',
            decode_routes=[16*1023,0,0,0],routes=[cell['prefill_routes'][0]+16*1023,0,0,0])
        result=run_audit(cells)
        self.assertEqual(result['integrity_errors'],[])
        self.assertEqual(result['arms']['chat']['flexible_correct'],8)
        self.assertEqual(result['arms']['chat']['nontruncated_flexible_correct'],7)
        self.assertEqual(result['arms']['chat']['correct_and_truncated'],1)
        self.assertFalse(result['qualification']['passed'])

    def test_successful_raw_arm_cannot_replace_failed_chat(self):
        result=run_audit(fixture(raw_correct=32,chat_correct=0))
        self.assertEqual(result['arms']['raw']['flexible_correct'],32)
        self.assertFalse(result['qualification']['passed'])
        self.assertFalse(result['qualification']['automatic_followup'])

    def test_missing_duplicate_or_test_cells_cannot_pass(self):
        cells=fixture()
        for altered in [cells[:-1],cells+[cells[-1]],[{**cells[0],'split':'test'}]+cells[1:]]:
            result=run_audit(altered)
            self.assertFalse(result['qualification']['passed'])
            self.assertNotEqual(result['status'],'COMPLETE')

    def test_saved_prompt_input_response_and_route_identities_are_independent(self):
        for key,value in [('prompt_sha256','wrong'),('input_token_ids_sha256','wrong'),
            ('question_sha256','wrong'),('protocol_sha256','wrong'),('response_sha256','wrong'),
            ('prompt_tokens',1),('routes',[0,0,0,0]),('gold','wrong')]:
            cells=fixture();cells[0][key]=value;result=run_audit(cells)
            self.assertEqual(result['validated_unique_cells'],63)
            self.assertTrue(result['integrity_errors'])
            self.assertFalse(result['qualification']['passed'])

    def test_manifest_rerender_hash_and_duplicate_bos_tampering_rejected(self):
        for change in ('text','token_hash','bos'):
            data=copy.deepcopy(DATA);manifest=data['pilot'][0]['prompts']['chat']
            if change=='text':
                manifest['text']=manifest['text'].replace('13 Sep 2026','14 Sep 2026')
                manifest['prompt_sha256']=audit.text_sha(manifest['text'])
            elif change=='token_hash': manifest['input_token_ids_sha256']='wrong'
            else:
                manifest['input_token_ids'].insert(0,128000)
                manifest['prompt_tokens']+=1
                manifest['input_token_ids_sha256']=audit.input_ids_sha(manifest['input_token_ids'])
            result=run_audit(fixture(),data=data)
            self.assertTrue(result['integrity_errors'])
            self.assertFalse(result['qualification']['passed'])

    def test_missing_or_disagreeing_numerical_evidence_blocks_pass(self):
        for change in ('missing_check','missing_probe','failed_probe','excess_delta'):
            technical=technical_fixture()
            if change=='missing_check': technical['checks'].pop('eager_sdpa_top_token_equal')
            elif change=='missing_probe': technical['details'].pop()
            elif change=='failed_probe': technical['details'][0]['eager_sdpa_top_token_equal']=False
            else: technical['details'][0]['eager_sdpa_max_abs']=0.0011
            result=run_audit(fixture(),technical=technical)
            self.assertFalse(result['all_technical_checks'])
            self.assertFalse(result['qualification']['passed'])

    def test_frozen_changes_and_test_data_are_rejected(self):
        for name,value in [('max_new_tokens',2048),('chat_date_string','14 Sep 2026'),('automatic_followup',True),
                           ('gates',{}),('dtype','bfloat16'),('data_sha256','wrong')]:
            result=run_audit(fixture(),protocol={**PROTOCOL,name:value})
            self.assertTrue(result['integrity_errors'])
            self.assertFalse(result['qualification']['passed'])
        result=run_audit(fixture(),data={**DATA,'test':[]})
        self.assertFalse(result['qualification']['passed'])

    def test_cli_complete_scientific_failure_exits_zero_and_remains_failed(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name);(out/'cells').mkdir()
            for index,cell in enumerate(fixture(raw_correct=32,chat_correct=0)):
                (out/'cells'/f'{index:03d}.json').write_text(json.dumps(cell),encoding='utf-8')
            (out/'technical.json').write_text(json.dumps(technical_fixture()),encoding='utf-8')
            result=subprocess.run([sys.executable,str(HERE/'audit.py'),'--run-dir',name,
                '--data',str(HERE/'data.json'),'--protocol',str(HERE/'protocol.json'),
                '--technical',str(out/'technical.json')],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            report=audit.load_json(out/'audit.json')
            self.assertEqual(report['status'],'COMPLETE')
            self.assertFalse(report['qualification']['passed'])
            self.assertEqual(report['qualification']['decision'],'DO_NOT_ADVANCE_CURRENT_QUALIFICATION')

    def test_cli_missing_cohort_exits_two_and_publishes_incomplete_review(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name)
            result=subprocess.run([sys.executable,str(HERE/'audit.py'),'--run-dir',name,
                '--data',str(HERE/'data.json'),'--protocol',str(HERE/'protocol.json'),
                '--technical',str(out/'absent.json')],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,2,result.stderr)
            report=audit.load_json(out/'audit.json')
            self.assertEqual(report['missing_cell_count'],64)
            self.assertFalse(report['qualification']['passed'])
            self.assertIn('DO_NOT_ADVANCE_CURRENT_QUALIFICATION',(out/'RESULTS.md').read_text())


if __name__=='__main__': unittest.main()
