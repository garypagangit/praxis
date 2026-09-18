"""One label-free, revision-pinned CTI generator experiment on an existing GPU."""
from __future__ import annotations
import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

import frozen_inference as frozen

MODELS = (
    ('qwen', 'Qwen/Qwen2.5-7B-Instruct', 'a09a35458c702b33eeacc393d103063234e8bc28'),
    ('llama', 'meta-llama/Llama-3.1-8B-Instruct', '0e9e39f249a16976918f6564b8830bc894c89659'),
)
CONDITIONS = (('vanilla_prompt', 'vanilla'), ('evidence_prompt', 'relationship_evidence'))
FROZEN_SHA = 'cd94f3da527c0e35ce2c408b2d03865d62cb195c608656eb11a08ccc187178f9'
BATCH_SIZE, MAX_INPUT, MAX_NEW = 2, 4096, 8


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(temporary, path)


def read_inputs(path, expected):
    records = [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(records) != expected or len({r['id'] for r in records}) != expected:
        raise ValueError('Unexpected or duplicate input inventory')
    for r in records:
        if set(r) != {'id', 'vanilla_prompt', 'evidence_prompt'} or not all(isinstance(x, str) and x for x in r.values()):
            raise ValueError('Generator input must be exactly id and two nonempty prompts, without labels')
    return records


def deadline(epoch, reserve=30):
    if time.time() + reserve >= epoch:
        raise TimeoutError('Absolute worker deadline reached; preserving partial records')


def complete_snapshot(path):
    if not (path/'config.json').is_file():
        return False
    index = path/'model.safetensors.index.json'
    if index.exists():
        weights = set(json.loads(index.read_text())['weight_map'].values())
        return bool(weights) and all((path/w).is_file() for w in weights)
    return (path/'model.safetensors').is_file()


def checkpoint(model_id, revision):
    key = 'models--'+model_id.replace('/', '--')
    roots = [Path(p) for p in (os.environ.get('HF_HUB_CACHE'), '/home/ubuntu/hf/hub',
             '/opt/praxis/hf_cache', '/opt/praxis/hf_cache/hub', str(Path.home()/'.cache/huggingface/hub')) if p]
    for root in roots:
        candidate = root/key/'snapshots'/revision
        if complete_snapshot(candidate):
            return candidate, 'existing_complete_pinned_snapshot'
    from huggingface_hub import snapshot_download
    cache = os.environ.get('CTI_DOWNLOAD_CACHE') or os.environ.get('HF_HUB_CACHE')
    if not cache:
        raise RuntimeError('A scratch download cache is required; root-disk download prohibited')
    result = Path(snapshot_download(model_id, revision=revision, cache_dir=cache,
        token=os.environ.get('HF_TOKEN'), allow_patterns=['*.json', '*.safetensors', 'tokenizer.*', 'vocab.*', 'merges.txt', '*.model']))
    if result.name != revision or not complete_snapshot(result):
        raise RuntimeError('Pinned model snapshot incomplete')
    return result, 'downloaded_pinned_snapshot'


def load(which, receipt, output, limit):
    import torch
    deadline(limit, reserve=120)
    key, model_id, revision = which
    t0 = time.monotonic()
    snapshot, origin = checkpoint(model_id, revision)
    model, tokenizer, device = frozen.load_model(str(snapshot), 'float16', 'auto', revision=revision)
    if device != 'cuda':
        raise RuntimeError('This worker requires CUDA; do not silently run a full CPU experiment')
    receipt['loads'].append({'model': key, 'model_id': model_id, 'revision': revision,
        'snapshot': str(snapshot), 'origin': origin, 'config_sha256': sha(snapshot/'config.json'),
        'load_seconds': time.monotonic()-t0, 'device': device,
        'dtype': str(next(model.parameters()).dtype)})
    dump(output/'runtime.json', receipt)
    return model, tokenizer


def run_phase(which, model, tokenizer, records, path, limit, phase):
    key, model_id, revision = which
    # Preflight every actual rendered prompt. Do not silently truncate or discard test cases.
    jobs = []
    for r in records:
        for field, condition in CONDITIONS:
            input_prompt_sha256 = hashlib.sha256(r[field].encode('utf-8')).hexdigest()
            prompt = frozen.render_prompt(tokenizer, r[field])
            n = len(tokenizer(prompt, truncation=False)['input_ids'])
            if n > MAX_INPUT:
                raise ValueError(f'Input exceeds frozen context limit: {r["id"]}/{condition}: {n}')
            jobs.append((r['id'], condition, prompt, n, input_prompt_sha256))
    good = 0
    started = time.monotonic()
    with path.open('a', encoding='utf-8') as stream:
        for offset in range(0, len(jobs), BATCH_SIZE):
            deadline(limit)
            batch = jobs[offset:offset+BATCH_SIZE]
            prompts = [x[2] for x in batch]
            batch_started = time.monotonic()
            outputs = frozen.generate_batch(model, tokenizer, prompts, MAX_INPUT, MAX_NEW)
            if len(outputs) != len(batch):
                raise ValueError('Model returned an incomplete batch')
            elapsed = time.monotonic()-batch_started
            for item, text in zip(batch, outputs):
                item_id, condition, prompt, n, input_prompt_sha256 = item
                answer = frozen.strict_parse(text)
                valid = answer in 'ABCD' and len(answer) == 1
                good += int(valid)
                record = {'id': item_id, 'model': key, 'model_id': model_id, 'revision': revision,
                    'phase': phase, 'condition': condition, 'raw_output': text, 'parsed_answer': answer,
                    'valid': valid, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                    'input_prompt_sha256': input_prompt_sha256,
                    'input_tokens': n, 'output_tokens': frozen.token_count(tokenizer, text),
                    'allocated_batch_seconds': elapsed/len(batch)}
                stream.write(json.dumps(record, allow_nan=False)+'\n')
            stream.flush()
            if offset % 100 == 0:
                print(json.dumps({'phase': phase, 'model': key, 'done': offset+len(batch),
                                  'total': len(jobs), 'elapsed_seconds': time.monotonic()-started}), flush=True)
    return {'records': len(jobs), 'valid': good, 'invalid': len(jobs)-good,
            'elapsed_seconds': time.monotonic()-started}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--qualification', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--deadline-epoch', type=float, required=True)
    args = p.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    if (out/'predictions.jsonl').exists() or (out/'qualification.jsonl').exists():
        raise ValueError('Existing inference outputs found; a second attempt is not implicit')
    if sha(Path(frozen.__file__)) != FROZEN_SHA:
        raise ValueError('Original inference helper changed')
    test = read_inputs(args.inputs, 1247)
    qualify = read_inputs(args.qualification, 8)
    if {r['id'] for r in test} & {r['id'] for r in qualify}:
        raise ValueError('Qualification questions overlap the new test')
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required')
    torch.manual_seed(20260918)
    runtime = {'status': 'RUNNING', 'started_utc': stamp(), 'deadline_epoch': args.deadline_epoch,
        'inputs_sha256': sha(args.inputs), 'qualification_sha256': sha(args.qualification),
        'worker_sha256': sha(__file__), 'frozen_inference_sha256': FROZEN_SHA,
        'python': sys.version, 'gpu': torch.cuda.get_device_name(0),
        'versions': {v: importlib.metadata.version(v) for v in ('torch', 'transformers', 'accelerate', 'huggingface-hub')},
        'decoding': {'batch_size': BATCH_SIZE, 'dtype': 'float16', 'do_sample': False,
                     'max_input_tokens': MAX_INPUT, 'max_new_tokens': MAX_NEW},
        'loads': [], 'qualification': {}, 'test': {}}
    dump(out/'runtime.json', runtime)
    model = None
    try:
        # Both models must pass format qualification before any fresh test generation.
        for i, which in enumerate(MODELS):
            model, tokenizer = load(which, runtime, out, args.deadline_epoch)
            q = run_phase(which, model, tokenizer, qualify, out/'qualification.jsonl', args.deadline_epoch, 'qualification')
            runtime['qualification'][which[0]] = q
            dump(out/'runtime.json', runtime)
            if q['records'] != 16 or q['invalid']:
                raise RuntimeError('FORMAT_QUALIFICATION_FAILED: no fresh test inference authorized by this protocol')
            if i == 0:
                del model
                model = None
                gc.collect()
                torch.cuda.empty_cache()
        # The second qualified model is still loaded. Then load the first once more.
        for i, which in enumerate(reversed(MODELS)):
            if i:
                model, tokenizer = load(which, runtime, out, args.deadline_epoch)
            stats = run_phase(which, model, tokenizer, test, out/'predictions.jsonl', args.deadline_epoch, 'test')
            runtime['test'][which[0]] = stats
            dump(out/'runtime.json', runtime)
            del model
            model = None
            gc.collect()
            torch.cuda.empty_cache()
        if sum(v['records'] for v in runtime['test'].values()) != 4988:
            raise RuntimeError('Incomplete primary inventory')
        runtime.update(status='COMPLETE', finished_utc=stamp(),
                       predictions_sha256=sha(out/'predictions.jsonl'),
                       qualification_outputs_sha256=sha(out/'qualification.jsonl'))
        dump(out/'runtime.json', runtime)
    except Exception as error:
        runtime.update(status='FAILED_OR_INCOMPLETE', finished_utc=stamp(),
                       error_type=type(error).__name__, error=str(error))
        dump(out/'runtime.json', runtime)
        raise


if __name__ == '__main__':
    main()
