"""Targeted worker gates with fake GPU/model calls; never invokes inference/AWS."""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack, contextmanager, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import inference_worker as worker


def records(prefix, count):
    return [{'id': f'{prefix}-{i}', 'vanilla_prompt': f'{prefix} vanilla {i}',
             'evidence_prompt': f'{prefix} evidence {i}'} for i in range(count)]


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


class FakeTokenizer:
    def __init__(self, counts=None):
        self.counts = counts or {}
        self.calls = []

    def apply_chat_template(self, messages, **kwargs):
        return messages[-1]['content']

    def __call__(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {'input_ids': [1]*self.counts.get(prompt, 7)}

    def encode(self, text, add_special_tokens=False):
        # Deliberately differs at the prompt boundary: default tokenization adds
        # one token which add_special_tokens=False would have missed.
        return [1]*(self.counts.get(text, 2)-1)


@contextmanager
def mocked_main(directory, invalid_model=None):
    test_path, qualification_path = directory/'inputs.jsonl', directory/'qualify.jsonl'
    out = directory/'outputs'
    jsonl(test_path, records('fresh', 1247))
    jsonl(qualification_path, records('qualification', 8))
    events, current = [], [None]
    tokenizer = FakeTokenizer()
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True, get_device_name=lambda _: 'MOCK GPU',
                             empty_cache=Mock()), manual_seed=Mock())
    def load(which, *_):
        current[0] = which[0]
        events.append(('load', which[0]))
        return object(), tokenizer
    def generate(_model, _tokenizer, prompts, max_input, max_new):
        phase = 'qualification' if prompts[0].startswith('qualification ') else 'test'
        events.append((phase, current[0]))
        if phase == 'qualification' and current[0] == invalid_model:
            return ['', 'Answer: B']
        return ['Answer: A' for _ in prompts]
    argv = ['inference_worker.py', '--inputs', str(test_path), '--qualification', str(qualification_path),
            '--output-dir', str(out), '--deadline-epoch', str(time.time()+3600)]
    with ExitStack() as stack:
        stack.enter_context(patch.object(sys, 'argv', argv))
        stack.enter_context(patch.dict(sys.modules, {'torch': fake_torch}))
        stack.enter_context(patch.object(worker.importlib.metadata, 'version', return_value='MOCK'))
        load_mock = stack.enter_context(patch.object(worker, 'load', side_effect=load))
        generate_mock = stack.enter_context(patch.object(worker.frozen, 'generate_batch', side_effect=generate))
        stack.enter_context(patch.object(worker.gc, 'collect', return_value=0))
        stack.enter_context(redirect_stdout(io.StringIO()))
        yield SimpleNamespace(out=out, events=events, load=load_mock, generate=generate_mock,
                              inputs=test_path, qualification=qualification_path)


class WorkerGateTests(unittest.TestCase):
    def test_strict_input_schema_count_uniqueness_and_no_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'inputs.jsonl'
            good = records('fresh', 2)
            jsonl(path, good)
            self.assertEqual(worker.read_inputs(path, 2), good)
            invalid = [good[:1], [good[0], good[0]],
                       [{**good[0], 'answer':'A'}, good[1]],
                       [{**good[0], 'vanilla_prompt':''}, good[1]],
                       [{**good[0], 'evidence_prompt':None}, good[1]],
                       [{**good[0], 'id':12}, good[1]]]
            for rows in invalid:
                with self.subTest(rows=rows):
                    jsonl(path, rows)
                    with self.assertRaises(ValueError): worker.read_inputs(path, 2)

    def test_special_token_boundary_fails_before_any_batch_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'predictions.jsonl'
            rows = records('boundary', 1)
            tokenizer = FakeTokenizer({rows[0]['vanilla_prompt']:4097})
            self.assertEqual(len(tokenizer.encode(rows[0]['vanilla_prompt'], add_special_tokens=False)),4096)
            with patch.object(worker.frozen, 'generate_batch') as generate:
                with self.assertRaisesRegex(ValueError, '4097'):
                    worker.run_phase(worker.MODELS[0],object(),tokenizer,rows,path,time.time()+3600,'test')
                generate.assert_not_called()
            self.assertFalse(path.exists())
            self.assertEqual(tokenizer.calls[0][1], {'truncation':False})

    def test_exact_input_limit_is_retained_with_frozen_decoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'predictions.jsonl'
            rows = records('boundary',1)
            tokenizer = FakeTokenizer({value:4096 for key,value in rows[0].items() if key.endswith('_prompt')})
            with patch.object(worker.frozen,'generate_batch',return_value=['Answer: A','Answer: B']) as generate:
                with redirect_stdout(io.StringIO()):
                    result=worker.run_phase(worker.MODELS[0],object(),tokenizer,rows,path,time.time()+3600,'test')
            self.assertEqual(result['records'],2)
            self.assertEqual({r['input_tokens'] for r in read_jsonl(path)},{4096})
            self.assertEqual(generate.call_args.args[-2:],(4096,8))
            self.assertEqual({r['condition'] for r in read_jsonl(path)}, {'vanilla','relationship_evidence'})

    def test_both_qualification_gates_precede_all_4988_unique_fresh_outputs(self):
        with tempfile.TemporaryDirectory() as tmp, mocked_main(Path(tmp)) as state:
            worker.main()
            qualification=read_jsonl(state.out/'qualification.jsonl')
            fresh=read_jsonl(state.out/'predictions.jsonl')
            runtime=json.loads((state.out/'runtime.json').read_text())
            self.assertEqual(len(qualification),32)
            self.assertEqual(len(fresh),4988)
            self.assertEqual(len({(r['id'],r['model'],r['condition']) for r in fresh}),4988)
            self.assertEqual(Counter(r['model'] for r in fresh),{'qwen':2494,'llama':2494})
            self.assertEqual(runtime['status'],'COMPLETE')
            self.assertEqual(runtime['inputs_sha256'], worker.sha(state.inputs))
            self.assertEqual(runtime['qualification_sha256'], worker.sha(state.qualification))
            self.assertEqual(runtime['qualification_outputs_sha256'], worker.sha(state.out/'qualification.jsonl'))
            self.assertEqual(runtime['predictions_sha256'], worker.sha(state.out/'predictions.jsonl'))
            original_prompts={(row['id'],condition):row[field]
                              for row in [*read_jsonl(state.inputs),*read_jsonl(state.qualification)]
                              for field,condition in worker.CONDITIONS}
            for row in [*qualification,*fresh]:
                self.assertEqual(row['input_prompt_sha256'],
                    hashlib.sha256(original_prompts[(row['id'],row['condition'])].encode('utf-8')).hexdigest())
            first_test=next(i for i,event in enumerate(state.events) if event[0]=='test')
            self.assertEqual(Counter(event for event in state.events[:first_test] if event[0]=='qualification'),
                             {('qualification','qwen'):8,('qualification','llama'):8})
            self.assertEqual([event for event in state.events if event[0]=='load'],
                             [('load','qwen'),('load','llama'),('load','qwen')])
            self.assertEqual(state.generate.call_count,2510)
            self.assertEqual({r['phase'] for r in fresh},{'test'})
            self.assertTrue(all(r['valid'] for r in fresh))

    def test_original_and_rendered_prompt_hashes_are_distinct_and_utf8_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=[{'id':'unicode-input','vanilla_prompt':'Técnica Ω\r\n字',
                   'evidence_prompt':'Evidence: café\nQuestion: Ω'}]
            path=Path(tmp)/'predictions.jsonl'
            def render(_tokenizer, text): return 'SYSTEM\n'+text+'\nASSISTANT>'
            with patch.object(worker.frozen,'render_prompt',side_effect=render), \
                 patch.object(worker.frozen,'generate_batch',return_value=['Answer: A','Answer: B']), \
                 redirect_stdout(io.StringIO()):
                worker.run_phase(worker.MODELS[0],object(),FakeTokenizer(),rows,path,time.time()+3600,'test')
            saved=read_jsonl(path)
            for row,(field,condition) in zip(saved,worker.CONDITIONS):
                text=rows[0][field]
                self.assertEqual(row['condition'],condition)
                self.assertEqual(row['input_prompt_sha256'],hashlib.sha256(text.encode('utf-8')).hexdigest())
                self.assertEqual(row['prompt_sha256'],hashlib.sha256(render(None,text).encode('utf-8')).hexdigest())
                self.assertNotEqual(row['input_prompt_sha256'],row['prompt_sha256'])

    def test_either_format_failure_blocks_fresh_generation_without_retry(self):
        for failed in ('qwen','llama'):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as tmp, \
                 mocked_main(Path(tmp),invalid_model=failed) as state:
                with self.assertRaisesRegex(RuntimeError,'FORMAT_QUALIFICATION_FAILED'): worker.main()
                self.assertFalse((state.out/'predictions.jsonl').exists())
                self.assertFalse(any(event[0]=='test' for event in state.events))
                runtime=json.loads((state.out/'runtime.json').read_text())
                self.assertEqual(runtime['status'],'FAILED_OR_INCOMPLETE')
                self.assertNotIn('qualification_outputs_sha256',runtime)
                self.assertEqual(runtime['qualification_sha256'],worker.sha(state.qualification))
                self.assertGreater(runtime['qualification'][failed]['invalid'],0)
                self.assertEqual(state.load.call_count,1 if failed=='qwen' else 2)
                self.assertEqual(state.generate.call_count,8 if failed=='qwen' else 16)

    def test_existing_results_refuse_a_second_attempt(self):
        for existing in ('qualification.jsonl','predictions.jsonl'):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as tmp, \
                 mocked_main(Path(tmp)) as state:
                state.out.mkdir()
                (state.out/existing).write_text('existing evidence\n')
                with self.assertRaisesRegex(ValueError,'second attempt'): worker.main()
                state.load.assert_not_called()
                state.generate.assert_not_called()
                self.assertEqual((state.out/existing).read_text(),'existing evidence\n')

    def test_qualification_overlap_stops_before_loading(self):
        with tempfile.TemporaryDirectory() as tmp, mocked_main(Path(tmp)) as state:
            overlap=records('qualification',8)
            overlap[0]['id']='fresh-0'
            jsonl(state.qualification,overlap)
            with self.assertRaisesRegex(ValueError,'overlap'): worker.main()
            state.load.assert_not_called()
            state.generate.assert_not_called()

    def test_deadline_keeps_completed_records_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'predictions.jsonl'
            with patch.object(worker,'deadline',side_effect=[None,TimeoutError('time cap')]), \
                 patch.object(worker.frozen,'generate_batch',return_value=['Answer: A','Answer: B']) as generate, \
                 redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):
                    worker.run_phase(worker.MODELS[0],object(),FakeTokenizer(),records('fresh',3),path,0,'test')
            self.assertEqual(generate.call_count,1)
            self.assertEqual(len(read_jsonl(path)),2)

    def test_incomplete_batch_fails_without_a_second_generation_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'predictions.jsonl'
            with patch.object(worker.frozen,'generate_batch',return_value=['Answer: A']) as generate:
                with self.assertRaisesRegex(ValueError,'incomplete batch'):
                    worker.run_phase(worker.MODELS[0],object(),FakeTokenizer(),records('fresh',1),path,time.time()+3600,'test')
            generate.assert_called_once()
            self.assertEqual(path.read_text(),'')


if __name__=='__main__':
    unittest.main()
