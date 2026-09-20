"""Synthetic tests only; no real reviewer cases, model or answer key is used."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.cert_gate.auto_review import (
    SYSTEM_PROMPT, consume_outputs, grade, prepare,
)


class AutoReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.cases = [{'case_id': hashlib.sha256(str(i).encode()).hexdigest(),
                       'alert': {'req_body': 'visible exploit attempt sample',
                                 'Label': 'Attack', 'attack_type': 'derived target',
                                 'kill_chain_all': 'derived chain',
                                 'parameter': {'label': 'hidden nested answer', 'visible': 'retained'}}}
                      for i in range(50)]
        self.source = self.root / 'REVIEW_CASES.json'
        self.source.write_text(json.dumps(self.cases), encoding='utf-8')
        self.prepared = self.root / 'prepared'
        self.model = {'model_id': 'synthetic/test-only', 'revision': 'a' * 40,
                      'backend': 'external_worker', 'max_input_tokens': 8192,
                      'max_new_tokens': 768}
        prepare(self.source, self.prepared)

    def tearDown(self):
        # Generated freeze files are deliberately read-only on Windows.
        for path in self.root.rglob('*'):
            if path.is_file():
                path.chmod(0o666)
        self.temporary.cleanup()

    def response(self, i=0, **changes):
        response = {'decision': 'Attack', 'reason': 'The visible request contains an exploit attempt.',
                    'citations': [{'field': 'req_body', 'quote': 'exploit attempt'}]}
        response.update(changes)
        return {'case_id': self.cases[i]['case_id'], 'response': response,
                'usage': {'input_tokens': 30, 'output_tokens': 20, 'elapsed_seconds': 0.1,
                          'input_truncated': False, 'output_limit_reached': False}}

    def consume(self, responses):
        worker = self.root / 'outputs.jsonl'
        worker.write_text('\n'.join(json.dumps(r) for r in responses) + '\n', encoding='utf-8')
        destination = self.root / 'frozen'
        consume_outputs(self.prepared, worker, destination, model=self.model)
        return destination, json.loads((destination / 'ANSWERS.json').read_text(encoding='utf-8'))

    def test_prepare_strips_top_level_and_nested_targets_before_requests(self):
        cases = json.loads((self.prepared / 'CASES.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cases), 50)
        self.assertEqual(cases[0]['alert']['parameter'], {'visible': 'retained'})
        for key in ('Label', 'attack_type', 'kill_chain_all'):
            self.assertNotIn(key, cases[0]['alert'])
        requests = (self.prepared / 'REQUESTS.jsonl').read_text(encoding='utf-8')
        self.assertNotIn('hidden nested answer', requests)
        self.assertNotIn('derived target', requests)
        manifest = json.loads((self.prepared / 'PREPARED.json').read_text())
        self.assertFalse(manifest['answer_key_accessed'])
        self.assertEqual(manifest['prompt_sha256'], hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest())

    def test_missing_cases_preserved_as_unable_and_no_key_required(self):
        _, answers = self.consume([self.response()])
        self.assertEqual(len(answers), 50)
        self.assertEqual(answers[0]['decision'], 'Attack')
        self.assertEqual(sum(a['decision'] == 'Unable to verify' for a in answers), 49)
        self.assertFalse((self.root / 'ANSWER_KEY.json').exists())

    def test_invalid_or_invented_citations_and_human_claim_fields_fail_closed(self):
        responses = [self.response(0, citations=[{'field': 'req_body', 'quote': 'invented evidence'}]),
                     self.response(1, citations=[{'field': 'Label', 'quote': 'Attack'}]),
                     self.response(2, human_verified=True), self.response(3, citations=[])]
        _, answers = self.consume(responses)
        self.assertTrue(all(a['decision'] == 'Unable to verify' for a in answers))

    def test_parse_failure_duplicate_response_and_truncation_fail_closed(self):
        invalid = self.response(0)
        invalid['response'] = '{not valid json'
        truncated = self.response(2)
        truncated['usage']['input_truncated'] = True
        capped = self.response(3)
        capped['usage']['output_limit_reached'] = True
        _, answers = self.consume([invalid, self.response(1), self.response(1), truncated, capped])
        self.assertTrue(all(a['decision'] == 'Unable to verify' for a in answers))

    def test_frozen_grade_is_automated_and_publishes_no_raw_reasons_or_quotes(self):
        destination, _ = self.consume([self.response(i) for i in range(50)])
        key = self.root / 'ANSWER_KEY.json'
        key.write_text(json.dumps({c['case_id']: 'Attack' for c in self.cases}))
        report = grade(destination, key, self.root / 'public.json')
        self.assertEqual(report['agreement_count'], 50)
        self.assertFalse(report['human_requirement_satisfied'])
        self.assertFalse(report['independent_ground_truth_verified'])
        text = (self.root / 'public.json').read_text()
        self.assertNotIn('exploit attempt', text)
        self.assertNotIn('citations', text)
        self.assertEqual(report['usage']['input_tokens'], 1500)

    def test_modified_answers_rejected_before_any_answer_key_access(self):
        destination, _ = self.consume([self.response()])
        path = destination / 'ANSWERS.json'
        path.chmod(0o666)
        path.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'Frozen response artifacts changed'):
            grade(destination, self.root / 'nonexistent-key.json', self.root / 'public.json')

    def test_changed_prepared_prompt_rejected(self):
        (self.prepared / 'PROMPT.txt').write_text('changed prompt')
        with self.assertRaisesRegex(ValueError, 'Prepared artifact changed'):
            self.consume([self.response()])

    def test_moving_model_revision_rejected(self):
        self.model['revision'] = 'main'
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.consume([self.response()])

    def test_overflowed_worker_accounting_still_freezes_every_case(self):
        worker = self.root / 'outputs.jsonl'
        text = json.dumps(self.response()).replace('"elapsed_seconds": 0.1', '"elapsed_seconds": 1e999')
        worker.write_text(text + '\n', encoding='utf-8')
        destination = self.root / 'frozen'
        consume_outputs(self.prepared, worker, destination, model=self.model)
        answers = json.loads((destination / 'ANSWERS.json').read_text())
        self.assertEqual(len(answers), 50)
        self.assertEqual(answers[0]['decision'], 'Unable to verify')
        self.assertIsNone(answers[0]['usage']['elapsed_seconds'])


if __name__ == '__main__':
    unittest.main()
