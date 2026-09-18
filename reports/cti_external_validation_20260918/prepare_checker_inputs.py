"""Project safe external question inputs for unchanged MiniLM option-aware scoring."""
import json
from pathlib import Path

from apply_deployment import load_helper, read_rows, safe_record, sha

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'cti_checker_pilot_20260918'


def main():
    source = ROOT / 'test_inputs.jsonl'
    target = ROOT / 'test_relevance_options_inputs.jsonl'
    receipt = ROOT / 'CHECKER_INPUT_PROJECTION.json'
    if target.exists() or receipt.exists():
        raise FileExistsError('Refusing to overwrite checker input preparation')
    metadata = json.loads((ROOT / 'DEPLOYMENT_METADATA.json').read_text(encoding='utf-8'))
    helper = load_helper(expected_sha=metadata['input_sha256']['run_pilot.py'])
    records = read_rows(source)
    assert len(records) == 1247 and len({r['id'] for r in records}) == 1247
    transformed = []
    for row in records:
        safe_record(row)
        assert len(row['evidence']) == 6
        projected = {**row, 'question': helper.question_text(row)}
        assert {k: v for k, v in row.items() if k != 'question'} == {
            k: v for k, v in projected.items() if k != 'question'}
        transformed.append(projected)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        for row in transformed:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    info = {'source_input': str(source), 'source_input_sha256': sha(source),
        'transformed_input': str(target), 'transformed_input_sha256': sha(target),
        'transform': 'Exact frozen run_pilot.question_text(question plus letter-sorted displayed options)',
        'questions': len(records), 'evidence_per_question': 6, 'only_question_field_changed': True,
        'safe_schema_checked': True, 'labels_or_generator_outputs_read': False,
        'helper_sha256': sha(OLD / 'run_pilot.py'),
        'original_scorer_sha256': sha(OLD / 'score_relevance.py'),
        'options_scorer_sha256': sha(OLD / 'score_relevance_options.py'),
        'preparation_code_sha256': sha(Path(__file__))}
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(info, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
