"""Synthetic-only extension lineage/cache/routing checks; no model/API execution."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from technical_extension import run_extension as extension

QWEN = 'qwen.qwen3-coder-next'
DEVSTRAL = 'mistral.devstral-2-123b'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, sort_keys=True) + '\n').encode())


def write_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((''.join(json.dumps(v, sort_keys=True) + '\n' for v in values)).encode())


class ExtensionRunnerControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='praxis008-extension-synthetic-')
        self.root = Path(self.temporary.name)
        self.campaign = self.root / 'campaign'
        self.output = self.campaign / 'study_v2'
        self.original = self.campaign / 'study'
        self.output.mkdir(parents=True)
        self.original.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def proposal_fixture(self):
        jobs = [{'proposal_id': 'synthetic-a', 'eligible': True}, {'proposal_id': 'synthetic-b', 'eligible': False}]
        proposals = [{**job, 'status': 'invalid' if job['eligible'] else 'ineligible', 'code': None,
                      'assignment_sha256': extension.runner.digest(extension.runner.policies.canonical(job))} for job in jobs]
        write_rows(self.original / 'proposal_jobs_development.jsonl', jobs)
        write_rows(self.original / 'proposals_development.jsonl', proposals)
        for proposal in proposals:
            write(self.original / 'proposals' / (proposal['proposal_id'] + '.json'), proposal)
        return jobs, proposals

    def review_fixture(self, n=1):
        jobs, decisions = [], []
        for i in range(n):
            for model in (DEVSTRAL, QWEN):
                jid = 'review-synthetic-' + str(i) + ('-d' if model == DEVSTRAL else '-q')
                job = {'job_id': jid, 'row': {'reviewer': model, 'eligible': True, 'cohort': 'native', 'split': 'dev'},
                       'messages': [{'role': 'user', 'content': 'Synthetic fixture only'}]}
                decision = dict(job['row'], job_id=jid, decision='keep', model_valid=True, model_status='complete',
                                assignment_sha256=extension.runner.digest(extension.runner.policies.canonical(job)))
                jobs.append(job)
                decisions.append(decision)
                write(self.original / 'decisions' / (jid + '.json'), decision)
        write_rows(self.original / 'decisions_native_development.jsonl', decisions)
        write_rows(self.output / 'review_jobs_native_development.jsonl', jobs)
        return jobs, decisions

    def test_exact_copy_idempotent_and_conflict_rejected(self):
        source, target = self.root / 'source', self.root / 'target'
        source.write_bytes(b'Exact synthetic bytes\n')
        first = extension.exact_copy(source, target)
        self.assertEqual(first, extension.exact_copy(source, target))
        self.assertEqual(source.read_bytes(), target.read_bytes())
        source.write_bytes(b'Changed bytes\n')
        with self.assertRaises(ValueError): extension.exact_copy(source, target)

    def test_proposals_all_placeholders_imported_byte_exact(self):
        _, proposals = self.proposal_fixture()
        extension.import_development_proposals(self.campaign, self.output)
        imports = extension.runner.read(self.output / 'IMPORTED_DEVELOPMENT_PROPOSALS.json')['imports']
        self.assertEqual(len(imports), 4)
        for item in imports:
            self.assertEqual((self.campaign / item['source']).read_bytes(), (self.output / item['destination']).read_bytes())
            self.assertEqual(extension.sha(self.output / item['destination']), item['sha256'])
        self.assertEqual(extension.runner.rows(self.output / 'proposals_development.jsonl'), proposals)

    def test_proposal_aggregate_per_call_disagreement_rejected(self):
        _, proposals = self.proposal_fixture()
        write(self.original / 'proposals/synthetic-a.json', dict(proposals[0], status='changed'))
        with self.assertRaises(ValueError): extension.import_development_proposals(self.campaign, self.output)
        self.assertFalse((self.output / 'proposals_development.jsonl').exists())

    def test_proposal_assignment_hash_mismatch_rejected(self):
        _, proposals = self.proposal_fixture()
        proposals[0]['assignment_sha256'] = '0' * 64
        write_rows(self.original / 'proposals_development.jsonl', proposals)
        write(self.original / 'proposals/synthetic-a.json', proposals[0])
        with self.assertRaises(ValueError): extension.import_development_proposals(self.campaign, self.output)

    def test_duplicate_proposal_identity_rejected(self):
        _, proposals = self.proposal_fixture()
        write_rows(self.original / 'proposals_development.jsonl', [proposals[0], proposals[0]])
        with self.assertRaises(ValueError): extension.import_development_proposals(self.campaign, self.output)

    def test_proposal_identity_universe_mismatch_rejected(self):
        _, proposals = self.proposal_fixture()
        write_rows(self.original / 'proposals_development.jsonl', proposals[:1])
        with self.assertRaises(ValueError): extension.import_development_proposals(self.campaign, self.output)

    def test_duplicate_proposal_job_rejected(self):
        jobs, _ = self.proposal_fixture()
        write_rows(self.original / 'proposal_jobs_development.jsonl', jobs + [jobs[0]])
        with self.assertRaises(ValueError): extension.import_development_proposals(self.campaign, self.output)

    def test_devstral_only_exact_import_and_lineage(self):
        jobs, _ = self.review_fixture()
        extension.import_devstral(self.campaign, self.output, 'native', 'development')
        manifest = extension.runner.read(self.output / 'IMPORTED_DEVSTRAL_native_development.json')['imports']
        self.assertEqual(len(manifest), 1)
        self.assertFalse(manifest[0]['new_call'])
        self.assertEqual(manifest[0]['reviewer'], DEVSTRAL)
        self.assertTrue((self.output / 'decisions' / (jobs[0]['job_id'] + '.json')).exists())
        self.assertFalse((self.output / 'decisions' / (jobs[1]['job_id'] + '.json')).exists())
        self.assertEqual(extension.sha(self.output / manifest[0]['destination']), manifest[0]['sha256'])

    def test_devstral_assignment_mismatch_rejected(self):
        jobs, _ = self.review_fixture()
        jobs[0]['messages'][0]['content'] = 'Changed synthetic assignment'
        write_rows(self.output / 'review_jobs_native_development.jsonl', jobs)
        with self.assertRaises(ValueError): extension.import_devstral(self.campaign, self.output, 'native', 'development')

    def test_devstral_per_call_mismatch_rejected(self):
        _, decisions = self.review_fixture()
        write(self.original / 'decisions' / (decisions[0]['job_id'] + '.json'), dict(decisions[0], model_valid=False))
        with self.assertRaises(ValueError): extension.import_devstral(self.campaign, self.output, 'native', 'development')

    def test_devstral_duplicate_replacing_expected_id_rejected(self):
        _, decisions = self.review_fixture(2)
        write_rows(self.original / 'decisions_native_development.jsonl', [decisions[0], decisions[0], decisions[1], decisions[3]])
        with self.assertRaises(ValueError): extension.import_devstral(self.campaign, self.output, 'native', 'development')

    def test_duplicate_new_review_job_rejected(self):
        jobs, _ = self.review_fixture()
        write_rows(self.output / 'review_jobs_native_development.jsonl', jobs + [jobs[0]])
        with self.assertRaises(ValueError): extension.import_devstral(self.campaign, self.output, 'native', 'development')

    def test_generated_heldout_reuse_forbidden(self):
        with self.assertRaises(ValueError): extension.import_devstral(self.campaign, self.output, 'generated', 'heldout')

    def test_imported_devstral_cache_avoids_new_call_qwen_reruns(self):
        self.review_fixture()
        extension.import_devstral(self.campaign, self.output, 'native', 'development')
        calls = []
        def create(model, *args):
            def generate(messages, **kwargs):
                calls.append(model)
                return {'text': '{"decision":"keep","reason":"Synthetic."}', 'finish_reason': 'end_turn', 'usage': {}}
            return SimpleNamespace(generate=generate)
        args = extension.arguments(self.campaign, self.output, 'development')
        args.jobs = self.output / 'review_jobs_native_development.jsonl'
        with patch.object(extension.runner, 'create_adapter', create), patch.object(extension.runner, 'BudgetLedger', lambda *a, **k: object()):
            extension.runner.infer_reviews(args)
        self.assertEqual(calls, [QWEN])
        self.assertEqual(len(extension.runner.rows(self.output / 'decisions_native_development.jsonl')), 2)

    def raw_warmup(self, decision='keep', finish='end_turn', text=None):
        request = extension.expected_warmup_request()
        path = self.output / 'raw_inference/synthetic.request.json'
        write(path, {'request': request})
        return {'text': text if text is not None else json.dumps({'decision': decision, 'reason': 'Synthetic.'}),
                'request_id': 'v2-review-schema-warmup-v2', 'finish_reason': finish,
                'usage': {'inputTokens': 1, 'outputTokens': 1}, 'model_id': QWEN,
                'runtime': {'structured_output': True}, 'preregistration_sha256': extension.sha(HERE / 'PREREG_V2.md'),
                'request_receipt': str(path), 'prompt_sha256': extension.runner.digest(extension.runner.policies.canonical(request)),
                'inference_input_sha256': extension.runner.digest(extension.runner.policies.canonical({k: v for k, v in request.items() if k != 'requestMetadata'}))}

    def warmup_fixture(self, decision='keep', finish='end_turn', text=None):
        calls, construction, ledgers = [], [], []
        def ledger(path, **kwargs):
            result = object(); ledgers.append((path, kwargs, result)); return result
        def factory(model, **kwargs):
            construction.append((model, kwargs))
            def generate(messages, **options):
                calls.append((messages, options))
                return self.raw_warmup(decision, finish, text)
            return SimpleNamespace(generate=generate)
        return calls, construction, ledgers, factory, ledger

    def test_warmup_routing_budget_timeout_and_no_substantive_gate(self):
        calls, construction, ledgers, factory, ledger = self.warmup_fixture('accept')
        with patch.object(extension, 'StructuredReviewAdapter', factory), patch.object(extension.runner, 'BudgetLedger', ledger):
            extension.warmup(self.output)
        self.assertEqual(construction[0][0], QWEN)
        self.assertEqual(construction[0][1]['timeout'], 600)
        self.assertEqual(ledgers[0][0], self.output / 'budget.json')
        self.assertEqual(ledgers[0][1]['limit_usd'], 30)
        self.assertIs(construction[0][1]['ledger'], ledgers[0][2])
        self.assertEqual(calls[0][1]['max_new_tokens'], 1024)
        self.assertTrue(calls[0][1]['request_id'].startswith('review-'))
        self.assertEqual(calls[0][0][0]['content'], extension.prompts.REVIEW_SYSTEM)
        self.assertTrue(extension.runner.read(self.output / 'SCHEMA_WARMUP.json')['valid'])

    def test_warmup_invalid_stops_and_remains_failed_on_resume(self):
        _, _, _, factory, ledger = self.warmup_fixture(text='Invalid synthetic JSON')
        with patch.object(extension, 'StructuredReviewAdapter', factory), patch.object(extension.runner, 'BudgetLedger', ledger):
            with self.assertRaises(ValueError): extension.warmup(self.output)
        with patch.object(extension, 'StructuredReviewAdapter') as adapter:
            with self.assertRaises(ValueError): extension.warmup(self.output)
            adapter.assert_not_called()

    def good_warmup_receipt(self):
        raw = self.raw_warmup()
        write(self.output / 'SCHEMA_WARMUP_RAW.json', raw)
        return {'kind': 'synthetic_schema_warmup_not_experiment_task', 'valid': True,
                'request_id': 'v2-review-schema-warmup-v2', 'schema_sha256': extension.SCHEMA_SHA256,
                'protocol_sha256': extension.sha(HERE / 'PREREG_V2.md'),
                'raw_result_sha256': extension.sha(self.output / 'SCHEMA_WARMUP_RAW.json'),
                'request_receipt_sha256': extension.sha(Path(raw['request_receipt'])),
                'finish_reason': 'end_turn', 'usage': raw['usage'], 'substantive_decision_not_a_gate': True}

    def test_valid_warmup_cache_avoids_call(self):
        write(self.output / 'SCHEMA_WARMUP.json', self.good_warmup_receipt())
        with patch.object(extension, 'StructuredReviewAdapter') as adapter:
            extension.warmup(self.output)
            adapter.assert_not_called()

    def test_stale_warmup_schema_rejected(self):
        write(self.output / 'SCHEMA_WARMUP.json', dict(self.good_warmup_receipt(), schema_sha256='0' * 64))
        with self.assertRaises(ValueError): extension.warmup(self.output)

    def test_nonterminal_warmup_cache_rejected(self):
        write(self.output / 'SCHEMA_WARMUP.json', dict(self.good_warmup_receipt(), finish_reason='max_tokens'))
        with self.assertRaises(ValueError): extension.warmup(self.output)

    def test_changed_warmup_raw_hash_rejected(self):
        write(self.output / 'SCHEMA_WARMUP.json', self.good_warmup_receipt())
        raw = extension.runner.read(self.output / 'SCHEMA_WARMUP_RAW.json')
        raw['text'] = '{"decision":"accept","reason":"Changed."}'
        write(self.output / 'SCHEMA_WARMUP_RAW.json', raw)
        with self.assertRaises(ValueError): extension.warmup(self.output)

    def test_wrong_warmup_protocol_rejected(self):
        write(self.output / 'SCHEMA_WARMUP.json', dict(self.good_warmup_receipt(), protocol_sha256='0' * 64))
        with self.assertRaises(ValueError): extension.warmup(self.output)

    def test_changed_request_schema_rejected(self):
        write(self.output / 'SCHEMA_WARMUP.json', self.good_warmup_receipt())
        raw = extension.runner.read(self.output / 'SCHEMA_WARMUP_RAW.json')
        request = extension.runner.read(Path(raw['request_receipt']))
        request['request']['outputConfig'] = {}
        write(Path(raw['request_receipt']), request)
        with self.assertRaises(ValueError): extension.warmup(self.output)

    def test_raw_only_warmup_recovery_avoids_call(self):
        write(self.output / 'SCHEMA_WARMUP_RAW.json', self.raw_warmup())
        with patch.object(extension, 'StructuredReviewAdapter') as adapter:
            extension.warmup(self.output)
            adapter.assert_not_called()
        self.assertTrue(extension.runner.read(self.output / 'SCHEMA_WARMUP.json')['valid'])

    def run_synthetic_campaign(self, native_pass, generated_pass):
        write(self.original / 'STUDY_PROCESS_STATUS.json', {'status': 'finished', 'exit_code': 0})
        write(self.original / 'budget.json', {'entries': {}})
        write(self.output / 'budget.json', {'entries': {}})
        write(self.output / 'REFERENCE_MANIFEST.json', {})
        heldout = []
        def gate(cohort, passed):
            return {'pass': passed, 'models': {QWEN: {'pass': passed, 'assigned': 1, 'valid': int(passed), 'valid_rate': float(passed)}, DEVSTRAL: {'pass': True, 'assigned': 1, 'valid': 1, 'valid_rate': 1}}, 'all_assignments_accounted': True, 'split': 'development', 'cohort': cohort}
        def reviews(args):
            if args.split == 'heldout':
                heldout.append((args.cohort, extension.runner.read(args.gate)))
            else:
                write(self.output / ('GATE_' + args.cohort + '_development.json'), gate(args.cohort, native_pass if args.cohort == 'native' else generated_pass))
        with contextlib.ExitStack() as stack:
            for target, name, value in [
                (extension, 'verify_freeze', lambda: None), (extension, 'warmup', lambda output: None),
                (extension, 'import_development_proposals', lambda *a: None), (extension, 'import_devstral', lambda *a: None),
                (extension, 'sha', lambda path: 'f' * 64),
                (extension.runner, 'prepare_reviews', lambda *a: None), (extension.runner, 'infer_reviews', reviews),
                (extension.runner, 'prepare_proposals', lambda *a: None), (extension.runner, 'infer_proposals', lambda *a: None),
                (extension.finalize_results, 'finalize', lambda *a: None), (extension.subprocess, 'run', lambda *a, **k: None),
            ]:
                stack.enter_context(patch.object(target, name, value))
            stack.enter_context(patch.dict(extension.os.environ, {'PRAXIS_PREREG_SHA256': 'f' * 64}))
            stack.enter_context(patch.object(extension.runner, 'BedrockAdapter', extension.runner.BedrockAdapter))
            extension.run(self.campaign)
        return heldout

    def test_both_development_gates_required_for_every_heldout_qwen_review(self):
        records = self.run_synthetic_campaign(True, False)
        self.assertEqual(len(records), 2)
        self.assertTrue(all(not gate['models'][QWEN]['pass'] for _, gate in records))
        self.assertTrue(all(gate['models'][DEVSTRAL]['pass'] for _, gate in records))
        self.assertTrue(extension.runner.read(self.output / 'GATE_native_development.json')['models'][QWEN]['pass'])
        self.assertFalse(extension.runner.read(self.output / 'GATE_generated_development.json')['models'][QWEN]['pass'])
        receipt = extension.runner.read(self.output / 'EXTENSION_ASSEMBLY_RECEIPT.json')
        self.assertEqual(set(receipt['effective_heldout_gates']), {'EFFECTIVE_GATE_native_development.json', 'EFFECTIVE_GATE_generated_development.json'})

    def test_native_gate_failure_blocks_generated_heldout_qwen(self):
        records = self.run_synthetic_campaign(False, True)
        self.assertTrue(all(not gate['models'][QWEN]['pass'] for _, gate in records))

    def test_both_development_passes_allow_heldout_qwen(self):
        records = self.run_synthetic_campaign(True, True)
        self.assertTrue(all(gate['models'][QWEN]['pass'] for _, gate in records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    stream = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExtensionRunnerControls))
    report = {'scope': 'Self-authored synthetic fixtures only; source imports and mock inference, no downloaded-program execution or heldout data.',
              'runner_sha256': hashlib.sha256((HERE / 'run_extension.py').read_bytes()).hexdigest(),
              'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'tests_run': result.testsRun,
              'passed': result.testsRun - len(result.failures) - len(result.errors),
              'failures': [{'test': test.id(), 'detail': detail} for test, detail in result.failures],
              'errors': [{'test': test.id(), 'detail': detail} for test, detail in result.errors], 'api_calls': 0,
              'actual_subprocesses_in_runner': 0, 'heldout_artifacts_inspected': False, 'success': result.wasSuccessful()}
    if args.receipt:
        args.receipt.write_bytes((json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps(report, indent=2))
    return 0 if result.wasSuccessful() else 2


if __name__ == '__main__':
    raise SystemExit(main())
