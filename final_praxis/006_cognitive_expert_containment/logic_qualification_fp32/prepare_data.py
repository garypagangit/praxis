"""Freeze an outcome-independent GSM8K cohort, excluding prior campaign exposure."""
from __future__ import annotations
import argparse, hashlib, json, re, urllib.request
from pathlib import Path

REVISION = '3101c7d5072418e28b9008a6636bde82a006892c'
BASE = f'https://raw.githubusercontent.com/openai/grade-school-math/{REVISION}/grade_school_math/data/'
TEST_SHA256 = '3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14'

def sha(data): return hashlib.sha256(data).hexdigest()
def norm(text): return ' '.join(text.split())
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def prepare(prior, output):
    raw = {}
    rows = {}
    for split in ('train', 'test'):
        with urllib.request.urlopen(BASE+split+'.jsonl', timeout=60) as response:
            raw[split] = response.read(20_000_001)
        if len(raw[split]) > 20_000_000: raise ValueError('Dataset size exceeds bound')
        rows[split] = [json.loads(line) for line in raw[split].decode().splitlines()]
    if sha(raw['test']) != TEST_SHA256 or len(rows['test']) != 1319 or len(rows['train']) != 7473:
        raise ValueError('Unexpected pinned GSM8K source')
    previous = json.loads(prior.read_text(encoding='utf-8'))
    suffix = '\nSolve the problem. End with #### followed by the final numeric answer.'
    exposed = {norm(r['question']) for r in rows['test'][:8]}
    prior_math = [r for r in previous if r.get('panel') == 'math']
    if len(prior_math) != 32: raise ValueError('Expected 32 previous option005 math questions')
    source_index = {norm(r['question']): i for i, r in enumerate(rows['test'])}
    for row in prior_math:
        if not row['prompt'].endswith(suffix): raise ValueError('Unexpected prior prompt wrapper')
        question = norm(row['prompt'][:-len(suffix)])
        if question not in source_index or row['id'] != f"gsm8k:test:{source_index[question]}":
            raise ValueError('Prior exposure identity mismatch')
        exposed.add(question)
    train_names = {norm(r['question']) for r in rows['train']}
    def select(split, n):
        eligible = [(i, r) for i, r in enumerate(rows[split]) if norm(r['question']) not in exposed
                    and (split != 'test' or norm(r['question']) not in train_names)]
        eligible.sort(key=lambda pair: (sha(('logic-qual-v1:'+split+':'+pair[1]['question']).encode()), pair[0]))
        chosen = []
        seen = set()
        for index, row in eligible:
            if norm(row['question']) in seen: continue
            seen.add(norm(row['question']))
            gold = row['answer'].rsplit('#### ', 1)[-1].strip()
            if not re.fullmatch(r'-?\d[\d,.]*', gold): raise ValueError('Unexpected gold answer format')
            chosen.append({'id':f'{split}-{index:04d}', 'source_index':index, **row, 'gold':gold,
                           'question_sha256':sha(row['question'].encode())})
            if len(chosen) == n: break
        if len(chosen) != n: raise ValueError('Insufficient eligible cohort')
        return chosen
    data = {'test':select('test', 256), 'pilot':select('train', 16)}
    if {norm(r['question']) for r in data['test']} & {norm(r['question']) for r in data['pilot']}:
        raise ValueError('Train/test overlap')
    write(output/'data.json', data)
    exclusions = [{'id':f'test-{source_index[q]:04d}', 'question_sha256':sha(rows['test'][source_index[q]]['question'].encode())}
                  for q in sorted(exposed, key=lambda q:source_index[q])]
    write(output/'data_receipt.json', {
        'source_commit':REVISION, 'source_files':{s:{'url':BASE+s+'.jsonl', 'sha256':sha(raw[s]), 'rows':len(rows[s])} for s in raw},
        'prior_005_eval_sha256':sha(prior.read_bytes()), 'exclusions':exclusions,
        'exclusion_basis':'Option006 first8 GSM8K test items and option005 all32 math-panel items; also exclude test questions present in train',
        'selection':'ascending SHA256(logic-qual-v1:<source split>:<exact question>), tie original index; unique normalized questions',
        'data_sha256':sha((output/'data.json').read_bytes()), 'test_n':256, 'pilot_n':16})
    print(json.dumps({'data_sha256':sha((output/'data.json').read_bytes()), 'excluded_test_questions':len(exposed), 'test_n':256, 'pilot_n':16}))

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--prior-005', required=True, type=Path); p.add_argument('--out', required=True, type=Path)
    a=p.parse_args(); prepare(a.prior_005, a.out)
