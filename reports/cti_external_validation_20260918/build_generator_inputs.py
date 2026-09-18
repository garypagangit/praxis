"""Construct frozen CTI prompts; verify against all historical prompt bytes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
OLD = WORKSPACE/'runs/px003-px034-confirmatory-20260731/ctibench_2500_query_only.jsonl'
OLD_SHA = '75d87d944cc2bcbe623ba3248a55a7c7e859111b08a52a7f06d42223f7f594c8'


def read(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompts(row):
    assert set(row) == {'id', 'question', 'options', 'evidence'}
    assert set(row['options']) == set('ABCD')
    options = '\n'.join(f"{c}. {row['options'][c]}" for c in 'ABCD')
    tail = f"Question: {row['question']}\nOptions:\n{options}\n\nAnswer:"
    evidence = '\n'.join(f"- [{x['kind']}] {x['text']}" for x in row['evidence']) or '- No retrieved relationship evidence.'
    return {'id': row['id'],
        'vanilla_prompt': 'Answer the cyber threat intelligence multiple-choice question.\n'
        'Return exactly one line in this format: Answer: <A|B|C|D>\n\n'+tail,
        'evidence_prompt': 'Answer the CTI multiple-choice question using the provided MITRE ATT&CK evidence when it directly supports an option.\n'
        'Evidence source: attack_19_1_multidomain.\n'
        'Do not explain. Return exactly one line in this format: Answer: <A|B|C|D>\n\n'
        f'Evidence:\n{evidence}\n\n'+tail}


def write(path, rows):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n')


def main():
    assert sha(OLD) == OLD_SHA
    historical = read(OLD)
    pilot = read(ROOT.parent/'cti_checker_pilot_20260918/data.jsonl')
    by_id = {r['id']: r for r in pilot}
    for row in historical:
        safe = {k: by_id[row['id']][k] for k in ('id', 'question', 'options', 'evidence')}
        actual = prompts(safe)
        assert actual['vanilla_prompt'] == row['vanilla_strict_prompt']
        assert actual['evidence_prompt'] == row['relationship_evidence_prompt']
    # Format-only qualification: first four numeric IDs per old cohort, no outcomes consulted.
    selected = []
    for eligible in (True, False):
        selected.extend(sorted((r for r in pilot if r['eligible'] is eligible),
                               key=lambda r: int(r['id'].rsplit('_', 1)[1]))[:4])
    qualification = [prompts({k: r[k] for k in ('id', 'question', 'options', 'evidence')}) for r in selected]
    safe_test = read(ROOT/'test_inputs.jsonl')
    assert len(safe_test) == 1247 and len({r['id'] for r in safe_test}) == 1247
    generated = [prompts(r) for r in safe_test]
    write(ROOT/'qualification_inputs.jsonl', qualification)
    write(ROOT/'generator_inputs.jsonl', generated)
    receipt = {'status': 'PASS', 'historical_prompt_pairs_exactly_matched': len(historical),
        'qualification_selection': 'first four numeric historical IDs in each old eligibility stratum; format only',
        'qualification_ids': [r['id'] for r in qualification], 'test_n': len(generated),
        'new_labels_read': False,
        'sha256': {p: sha(ROOT/p) for p in ('test_inputs.jsonl', 'generator_inputs.jsonl', 'qualification_inputs.jsonl', 'build_generator_inputs.py')}}
    (ROOT/'PROMPT_VERIFICATION.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
