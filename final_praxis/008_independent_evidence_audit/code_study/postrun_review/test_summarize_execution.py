"""Self-authored two-run accounting controls with synthetic receipts only."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import summarize_execution as accounting

Q = accounting.QWEN
D = 'mistral.devstral-2-123b'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, sort_keys=True) + '\n').encode())


def write_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((''.join(json.dumps(value, sort_keys=True) + '\n' for value in values)).encode())


class AccountingControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='praxis008-accounting-synthetic-')
        self.root = Path(self.temp.name)
        self.v1, self.v2 = self.root / 'v1', self.root / 'v2'
        self.make_run(self.v1, 'v1')

    def tearDown(self): self.temp.cleanup()

    def make_run(self, root, version):
        root.mkdir()
        state = {'status': 'finished', 'exit_code': 0} if version == 'v1' else {'status': 'finished', 'failure': None}
        write(root / ('STUDY_PROCESS_STATUS.json' if version == 'v1' else 'EXTENSION_PROCESS_STATUS.json'), state)
        budget = {'entries': {}, 'limit_usd': 30, 'invoice_claimed': False, 'price_source': 'synthetic', 'price_checked': 'synthetic'}
        imports = []

        def add_request(request_id, model):
            key = request_id + '.attempt-1'
            usage = {'inputTokens': 10, 'outputTokens': 2, 'totalTokens': 12}
            budget['entries'][key] = {'model_id': model, 'status': 'SUCCESS', 'accounted_usd': .01 if version == 'v1' else .02, 'usage': usage}
            write(root / 'raw_inference' / (key + '.request.json'), {'synthetic': True})
            write(root / 'raw_inference' / (request_id + '.result.json'), {'request_id': request_id, 'model_id': model, 'aws_request_id': version + '-' + request_id, 'usage': usage})

        def reuse(kind, identifier, folder, record):
            source = self.v1 / folder / (identifier + '.json')
            destination = root / folder / (identifier + '.json')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            item = {'source': 'study/' + folder + '/' + identifier + '.json', 'destination': folder + '/' + identifier + '.json', 'sha256': accounting.sha(source), 'kind': kind}
            if kind == 'review_decision': item.update(job_id=identifier, reviewer=D, new_call=False)
            else: item['proposal_id'] = identifier
            imports.append(item)
            return accounting.read(source)

        for cohort, split in accounting.REVIEW_PARTS:
            jobs, records = [], []
            models = [] if version == 'v1' and cohort == 'generated' and split == 'heldout' else [Q, D]
            for model in models:
                identifier = 'review-' + cohort + '-' + split + ('-q' if model == Q else '-d')
                job = {'job_id': identifier, 'row': {'cohort': cohort, 'split': split, 'reviewer': model, 'eligible': True}, 'messages': [{'role': 'user', 'content': 'Synthetic only'}]}
                called = not (version == 'v1' and cohort == 'native' and split == 'heldout' and model == Q)
                valid = called and not (version == 'v1' and cohort == 'generated' and model == Q)
                record = dict(job['row'], job_id=identifier, assignment_sha256=accounting.digest(job), model_status='complete' if called else 'not_run_development_gate', model_valid=valid)
                reused = version == 'v2' and model == D and (cohort == 'native' or split == 'development')
                if reused:
                    record = reuse('review_decision', identifier, 'decisions', record)
                else:
                    write(root / 'decisions' / (identifier + '.json'), record)
                    if called: add_request(('v2-' if version == 'v2' and model == Q else '') + identifier, model)
                jobs.append(job); records.append(record)
            write_rows(root / ('review_jobs_' + cohort + '_' + split + '.jsonl'), jobs)
            write_rows(root / ('decisions_' + cohort + '_' + split + '.jsonl'), records)
        for split in ('development', 'heldout'):
            identifier = 'synthetic-proposal-' + split
            job = {'proposal_id': identifier, 'eligible': True, 'split': split, 'proposer': Q}
            called = version == 'v2' or split == 'development'
            record = dict(job, assignment_sha256=accounting.digest(job), status='admitted' if called else 'not_run_development_gate')
            if called: record['inference_request_id'] = 'proposal-' + identifier
            if version == 'v2' and split == 'development':
                record = reuse('development_proposal', identifier, 'proposals', record)
            else:
                write(root / 'proposals' / (identifier + '.json'), record)
                if called: add_request('proposal-' + identifier, Q)
            write_rows(root / ('proposal_jobs_' + split + '.jsonl'), [job])
            write_rows(root / ('proposals_' + split + '.jsonl'), [record])
        if version == 'v2':
            add_request(accounting.WARMUP, Q)
            write(root / 'IMPORTED_SYNTHETIC.json', {'imports': imports})
        write(root / 'budget.json', budget)

    def test_v1_pending_v2_does_not_mean_zero(self):
        report = accounting.summarize(self.v1)
        self.assertEqual(report['runs'][1]['status'], 'pending')
        self.assertIsNone(report['runs'][1]['counts'])
        self.assertEqual(report['combined']['distinct_provider_results'], 6)
        self.assertEqual(report['combined']['api_accounted_usd_estimate'], '0.06')

    def test_two_runs_reuse_not_double_counted_or_double_charged(self):
        self.make_run(self.v2, 'v2')
        report = accounting.summarize(self.v1, self.v2)
        self.assertEqual(report['combined']['distinct_provider_results'], 13)
        self.assertEqual(report['combined']['distinct_assigned_provider_results'], 12)
        self.assertEqual(report['combined']['distinct_valid_review_responses'], 9)
        self.assertEqual(report['combined']['reused_assigned_results_in_v2'], 4)
        self.assertEqual(report['combined']['api_accounted_usd_estimate'], '0.20')
        self.assertEqual(report['runs'][1]['synthetic_control_provider_results'], 1)
        self.assertEqual(report['runs'][1]['new_assigned_provider_results'], 6)
        self.assertEqual(report['runs'][1]['imported_records'], 4)

    def test_partial_v2_is_pending_without_reading_counts(self):
        self.v2.mkdir()
        write(self.v2 / 'EXTENSION_PROCESS_STATUS.json', {'status': 'incomplete_requires_recovery', 'failure': None})
        report = accounting.summarize(self.v1, self.v2)
        self.assertEqual(report['runs'][1]['status'], 'pending')

    def test_reuse_hash_tampering_rejected(self):
        self.make_run(self.v2, 'v2')
        p = self.v2 / 'IMPORTED_SYNTHETIC.json'; value = accounting.read(p)
        value['imports'][0]['sha256'] = '0' * 64; write(p, value)
        with self.assertRaises(ValueError): accounting.summarize(self.v1, self.v2)

    def test_missing_reuse_lineage_rejected(self):
        self.make_run(self.v2, 'v2')
        p = self.v2 / 'IMPORTED_SYNTHETIC.json'; value = accounting.read(p)
        value['imports'].pop(); write(p, value)
        with self.assertRaises(ValueError): accounting.summarize(self.v1, self.v2)

    def test_duplicate_reuse_destination_rejected(self):
        self.make_run(self.v2, 'v2')
        p = self.v2 / 'IMPORTED_SYNTHETIC.json'; value = accounting.read(p)
        value['imports'].append(copy.deepcopy(value['imports'][0])); write(p, value)
        with self.assertRaises(ValueError): accounting.summarize(self.v1, self.v2)

    def test_duplicate_assignment_rejected(self):
        p = self.v1 / 'decisions_native_development.jsonl'; value = accounting.rows(p)
        write_rows(p, value + [value[0]])
        with self.assertRaises(ValueError): accounting.summarize(self.v1)

    def test_missing_provider_result_rejected(self):
        p = next((self.v1 / 'raw_inference').glob('*.result.json')); p.unlink()
        with self.assertRaises(ValueError): accounting.summarize(self.v1)

    def test_duplicate_budget_json_key_rejected(self):
        p = self.v1 / 'budget.json'; p.write_bytes(b'{"entries":{},"entries":{}}')
        with self.assertRaises(ValueError): accounting.summarize(self.v1)

    def test_retried_unresolved_attempt_counted_once_in_cost(self):
        p = self.v1 / 'budget.json'; value = accounting.read(p)
        first = next(iter(value['entries'])); success = copy.deepcopy(value['entries'][first])
        value['entries'][first] = dict(success, status='ERROR_ReadTimeoutError', accounted_usd=.03, usage={})
        second = first.rsplit('-', 1)[0] + '-2'; value['entries'][second] = success
        write(self.v1 / 'raw_inference' / (second + '.request.json'), {'synthetic': True}); write(p, value)
        report = accounting.summarize(self.v1)
        self.assertEqual(report['combined']['ledger_attempts'], 7)
        self.assertEqual(report['combined']['distinct_provider_results'], 6)
        self.assertEqual(report['combined']['api_accounted_usd_estimate'], '0.09')

    def test_markdown_has_operational_and_cost_tables(self):
        self.make_run(self.v2, 'v2')
        text = accounting.markdown(accounting.summarize(self.v1, self.v2))
        self.assertIn('Reused results', text)
        self.assertIn('Synthetic controls', text)
        self.assertIn('not an invoice', text)


if __name__ == '__main__':
    stream = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AccountingControls))
    receipt = {'scope': 'Self-authored synthetic accounting fixtures only.', 'tool_sha256': accounting.sha(Path(__file__).with_name('summarize_execution.py')),
               'test_sha256': accounting.sha(Path(__file__)), 'tests_run': result.testsRun, 'passed': result.testsRun - len(result.errors) - len(result.failures),
               'failures': [{'test': test.id(), 'detail': detail} for test, detail in result.failures],
               'errors': [{'test': test.id(), 'detail': detail} for test, detail in result.errors], 'api_calls': 0, 'candidate_programs_executed': False}
    Path(__file__).with_name('EXECUTION_ACCOUNTING_TEST_RECEIPT.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 2)
