"""Offline tests of independent scoring, integrity and frozen gate arithmetic."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import audit

PROTOCOL = copy.deepcopy(audit.FROZEN_PROTOCOL)
PROTOCOL_SHA = audit.text_sha(json.dumps(PROTOCOL))
TECHNICAL = {'checks':{name:True for name in audit.TECHNICAL_CHECKS}}


def fixture():
    data, cells = {}, []
    for split, n in [('pilot',16), ('test',256)]:
        data[split] = []
        for index in range(n):
            question = f'{split} unique fixture {index}: what is two plus two?'
            row = {'id':f'{split}-{index:04d}', 'question':question,
                   'answer':'Two plus two is four. #### 4', 'gold':'4',
                   'question_sha256':audit.text_sha(question)}
            data[split].append(row)
            for condition in audit.CONDITIONS:
                correct = index < (48 if condition == 'logic_ablation' else 96)
                active = 1 if condition == 'logic_ablation' else 0
                routes, prefill, decode = [0]*4, [0]*4, [0]*4
                routes[active], prefill[active], decode[active] = 48, 32, 16
                response = 'The answer is '+('4' if correct else '5')+'.'
                cells.append({'split':split, 'id':row['id'], 'condition':condition,
                    'question_sha256':row['question_sha256'],
                    'prompt_sha256':audit.text_sha(audit.raw_prompt(question)),
                    'protocol_sha256':PROTOCOL_SHA, 'gold':'4',
                    'response':response, 'response_sha256':audit.text_sha(response),
                    'prompt_tokens':2, 'prefill_routes':prefill, 'decode_routes':decode,
                    'generated_token_ids':[42,128001], 'tokens':2,
                    'stop_reason':'eos', 'seconds':.25, 'routes':routes})
    return data, cells


PROTOCOL['data_sha256'] = audit.text_sha(json.dumps(fixture()[0]))
PROTOCOL_SHA = audit.text_sha(json.dumps(PROTOCOL))

def fast_audit(data, cells, technical=None, protocol=None):
    # Integrity tests need not repeat the separate full 10,000-draw CI test.
    original = audit.paired_statistics
    def fast(*args, **kwargs):
        kwargs['replicates'] = 40
        return original(*args, **kwargs)
    with patch.object(audit, 'paired_statistics', side_effect=fast):
        return audit.audit_records(data, protocol or PROTOCOL, cells, PROTOCOL_SHA,
                                   TECHNICAL if technical is None else technical, PROTOCOL['data_sha256'])


class ExtractionTests(unittest.TestCase):
    def test_strict_first_and_flexible_last_are_distinct(self):
        response = 'The answer is 4. Later, The answer is 5.'
        self.assertEqual(audit.extract_prediction(response,'strict'), '4.')
        self.assertEqual(audit.extract_prediction(response,'flexible'), '5.')
        self.assertEqual(audit.score_response(response,'work #### 5')['flexible_correct'],1)
        self.assertEqual(audit.score_response(response,'work #### 5')['strict_correct'],0)

    def test_case_sensitive_extraction_precedes_lowercase_metric(self):
        self.assertEqual(audit.extract_prediction('the answer is 4.','strict'),audit.INVALID)
        self.assertEqual(audit.normalize_exact('WORK #### $1,234.'),'1234')

    def test_exact_match_does_not_coerce_numeric_equivalence(self):
        self.assertEqual(audit.score_response('4.0','work #### 4')['flexible_correct'],0)
        self.assertEqual(audit.score_response('004','work #### 4')['flexible_correct'],0)
        self.assertEqual(audit.score_response('$1,234.','work #### 1234')['flexible_correct'],1)
        self.assertEqual(audit.normalize_exact(' 4 '),' 4 ')

    def test_pinned_strict_wildcard_and_missing_number(self):
        self.assertEqual(audit.extract_prediction('The answer is 42','strict'),'4')
        self.assertEqual(audit.extract_prediction('The answer is -42.','strict'),'-42')
        self.assertEqual(audit.extract_prediction('No numeric answer'),audit.INVALID)
        result = audit.score_response('No numeric answer','work #### 4')
        self.assertFalse(result['flexible_extracted'])
        self.assertEqual(result['flexible_correct'],0)

    def test_punctuation_match_is_not_numeric_extraction(self):
        result = audit.score_response('...','work #### 4')
        self.assertTrue(result['flexible_extracted'])
        self.assertFalse(result['flexible_contains_digit'])
        self.assertEqual(result['flexible_correct'],0)

    def test_greedy_answer_marker_matches_pinned_metric(self):
        self.assertEqual(audit.normalize_exact('earlier #### 3\nlater #### 4'),'4')
        self.assertEqual(audit.normalize_exact('work #### -1,234.'),'-1234')


class PairedAndGateTests(unittest.TestCase):
    def test_paired_bootstrap_is_deterministic_and_counts_both_directions(self):
        a = {'a':1, 'b':1, 'c':0, 'd':0}
        b = {'a':0, 'b':0, 'c':1, 'd':0}
        result = audit.paired_statistics(a,b)
        self.assertEqual(result, audit.paired_statistics(dict(reversed(list(a.items()))),b))
        self.assertEqual(result['correct_to_wrong'],2)
        self.assertEqual(result['wrong_to_correct'],1)
        self.assertEqual(result['difference'],.25)
        self.assertEqual(result['discordant'],3)
        self.assertEqual(result['bootstrap_replicates'],10000)
        self.assertEqual(result['ci95'],[-.5,1.0])
        with self.assertRaises(ValueError): audit.paired_statistics(a,{'a':0})
        with self.assertRaises(ValueError): audit.paired_statistics({}, {})

    def test_percentiles_use_linear_interpolation(self):
        self.assertEqual(audit.interpolated_percentile([0,1,2,3],.25),.75)
        self.assertEqual(audit.interpolated_percentile([0,1,2,3],.975),2.925)

    def test_integer_gates_at_256_do_not_round_up_failures(self):
        args = dict(n=256,intact_correct=64,logic_correct=38,intact_truncated=25,
                    intact_extracted=231,ci_lower=.01,complete=True,technical=True)
        self.assertTrue(audit.qualification_gate(**args)['passed'])
        for key, bad in [('intact_correct',63),('logic_correct',39),('intact_truncated',26),
                         ('intact_extracted',230),('ci_lower',0),('ci_lower',float('nan')),
                         ('complete',False),('technical',False)]:
            with self.subTest(key=key,bad=bad):
                self.assertFalse(audit.qualification_gate(**{**args,key:bad})['passed'])
        self.assertEqual(audit.qualification_gate(**args)['integer_thresholds'],
                         {'minimum_intact_correct':64, 'maximum_intact_truncated':25,
                          'minimum_intact_extracted':231,'minimum_net_logic_loss':26})


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.data, self.cells = fixture()

    def test_complete_frozen_cohort_passes_full_bootstrap(self):
        result = audit.audit_records(self.data,PROTOCOL,self.cells,PROTOCOL_SHA,TECHNICAL,PROTOCOL['data_sha256'])
        self.assertEqual(result['status'],'COMPLETE')
        self.assertTrue(result['qualification']['passed'])
        self.assertEqual(result['validated_unique_cells'],816)
        self.assertEqual(result['splits']['test']['paired']['flexible/intact_minus_logic_ablation']['difference'],48/256)
        self.assertEqual(result['splits']['test']['arms']['intact']['flexible_correct'],96)
        self.assertTrue(result['splits']['pilot']['descriptive_only'])
        self.assertFalse(result['splits']['test']['descriptive_only'])
        self.assertIn('useful-specialist prerequisite',audit.render_report(result))

    def test_truncated_correct_response_is_not_dropped_or_forced_wrong(self):
        cell = next(c for c in self.cells if c['split']=='test' and c['condition']=='intact')
        cell.update(generated_token_ids=[42]*1024,tokens=1024,stop_reason='token_cap', routes=[16400,0,0,0], decode_routes=[16368,0,0,0])
        result = fast_audit(self.data,self.cells)
        row = result['splits']['test']['arms']['intact']
        self.assertEqual(row['n'],256)
        self.assertEqual(row['flexible_correct'],96)
        self.assertEqual(row['correct_and_truncated'],1)
        self.assertEqual(row['truncated'],1)
        sensitivity=result['splits']['test']['jointly_nontruncated_sensitivity']['intact_minus_logic_ablation']
        self.assertEqual(sensitivity['n'],255)
        self.assertEqual(sensitivity['excluded_truncated_pairs'],1)
        self.assertTrue(sensitivity['descriptive_only'])
        self.assertTrue(result['qualification']['passed'])

    def test_missing_pilot_or_test_and_duplicate_cannot_pass(self):
        for index in [0,48]:
            result = fast_audit(self.data,self.cells[:index]+self.cells[index+1:])
            self.assertFalse(result['qualification']['passed'])
            self.assertEqual(result['missing_cell_count'],1)
            self.assertTrue(result['splits']['test']['descriptive_only'])
        result = fast_audit(self.data,self.cells+[self.cells[-1]])
        self.assertFalse(result['qualification']['passed'])
        self.assertTrue(any('duplicate_cell' in e for e in result['integrity_errors']))

    def test_missing_required_technical_check_fails_even_with_extras(self):
        technical = copy.deepcopy(TECHNICAL)
        technical['checks'].pop('cache_max_abs_within_tolerance')
        technical['checks']['some_other_check'] = True
        result = fast_audit(self.data,self.cells,technical)
        self.assertFalse(result['qualification']['passed'])
        self.assertFalse(result['technical_checks']['cache_max_abs_within_tolerance'])
        for technical in [{}, {'checks':[]}, {'checks':{k:1 for k in audit.TECHNICAL_CHECKS}}]:
            result = fast_audit(self.data,self.cells,technical)
            self.assertFalse(result['all_technical_checks'])

    def test_artifact_tampering_or_route_failure_is_not_scored(self):
        for field, value, fragment in [('protocol_sha256','wrong','protocol_hash'),
             ('prompt_sha256','wrong','prompt_hash'),('gold','5','gold_identity'),
             ('question_sha256','wrong','question_hash'),
             ('response_sha256','wrong','response_hash'),
             ('routes',[1,1,1,1],'route_accounting'),
             ('tokens',3,'token_count'),('stop_reason','token_cap','cap_length')]:
            cells = copy.deepcopy(self.cells)
            target = next(c for c in cells if c['split']=='test' and c['condition']=='logic_ablation')
            target[field] = value
            result = fast_audit(self.data,cells)
            self.assertFalse(result['qualification']['passed'])
            self.assertEqual(result['validated_unique_cells'],815)
            self.assertTrue(any(fragment in e for e in result['integrity_errors']))

    def test_frozen_settings_and_raw_data_hash_mismatch_block_pass(self):
        for name, value in [('eos_token_ids',[128001]),('chat_template',True),('gates',{}),('do_sample',True),('bootstrap_seed',42),('data_sha256','bad'),('dtype','bfloat16'),('cache_max_abs_tolerance',0.25),('predecessor_run','wrong-run')]:
            result = fast_audit(self.data,self.cells,protocol={**PROTOCOL,name:value})
            self.assertFalse(result['qualification']['passed'])
            self.assertTrue(result['integrity_errors'])

    def test_malformed_cohort_is_fail_closed(self):
        result = fast_audit({'pilot':None,'test':[]},self.cells)
        self.assertFalse(result['qualification']['passed'])
        self.assertTrue(result['integrity_errors'])

    def test_json_duplicate_keys_and_parse_errors_are_recorded(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'cells').mkdir()
            (root/'cells'/'broken.json').write_text('{"id":"a","id":"b"}',encoding='utf-8')
            (root/'cells.jsonl').write_text('{"id":"valid"}\nnot json\n',encoding='utf-8')
            records, receipts, errors = audit.read_cells(root)
            self.assertEqual(records,[{'id':'valid'}])
            self.assertEqual(len(receipts),2)
            self.assertEqual(len(errors),2)
            self.assertTrue(any('Duplicate JSON key' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
