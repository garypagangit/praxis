"""Validate frozen external checker scoring without opening labels or generator outputs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from apply_deployment import read_rows, safe_record, score_records, sha

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'cti_checker_pilot_20260918'


def canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def main():
    target = ROOT / 'CHECKER_VALIDATION.json'
    if target.exists():
        raise FileExistsError(target)
    records = read_rows(ROOT / 'test_inputs.jsonl')
    options = read_rows(ROOT / 'test_relevance_options_inputs.jsonl')
    ids = [r['id'] for r in records]
    assert len(ids) == len(set(ids)) == 1247
    assert [r['id'] for r in options] == ids
    for record in records:
        safe_record(record)
        assert len(record['evidence']) == 6
    projection = json.loads((ROOT / 'CHECKER_INPUT_PROJECTION.json').read_text(encoding='utf-8'))
    assert projection['source_input_sha256'] == sha(ROOT / 'test_inputs.jsonl')
    assert projection['transformed_input_sha256'] == sha(ROOT / 'test_relevance_options_inputs.jsonl')
    details = {}
    all_scores = []
    for name, data, input_name, script_name in (
        ('relevance', records, 'test_inputs.jsonl', 'score_relevance.py'),
        ('relevance_options', options, 'test_relevance_options_inputs.jsonl', 'score_relevance_options.py'),
    ):
        scored = read_rows(ROOT / f'{name}_scores.jsonl')
        meta = json.loads((ROOT / f'{name}_metadata.json').read_text(encoding='utf-8'))
        old_meta = json.loads((OLD / f'{name}_metadata.json').read_text(encoding='utf-8'))
        assert meta['status'] == 'COMPLETE'
        assert [r['id'] for r in scored] == ids
        assert meta['questions_completed'] == meta['questions_total'] == 1247
        assert meta['pairs_total'] == 1247 * 6
        assert meta['input_sha256'] == sha(ROOT / input_name)
        assert meta['output_sha256'] == sha(ROOT / f'{name}_scores.jsonl')
        assert meta['spec_sha256'] == canonical_hash(meta['spec']) == old_meta['spec_sha256']
        assert meta['spec']['implementation_sha256'] == sha(OLD / script_name)
        assert meta['model_file_sha256'] == old_meta['model_file_sha256']
        assert meta['versions'] == old_meta['versions']
        for source, row in zip(data, scored):
            assert row['input_sha256'] == meta['input_sha256']
            assert row['input_row_sha256'] == canonical_hash(source)
            assert row['spec_sha256'] == meta['spec_sha256']
            assert row['model_revision'] == '233902d25c440f23af6f7d6e94d2946bac0bee0a'
            assert row['evidence_count'] == len(row['logits']) == 6
            assert np.isfinite(row['logits']).all()
            assert row['max'] == max(row['logits'])
        details[name] = {'status': meta['status'], 'questions': 1247, 'pairs': 7482,
            'spec_matches_old_pilot': True, 'model_files_match_old_pilot': True,
            'package_versions_match_old_pilot': True, 'input_sha256': meta['input_sha256'],
            'output_sha256': meta['output_sha256'], 'pairs_truncated': meta['pairs_truncated'],
            'inference_seconds': meta['this_run_inference_seconds'],
            'total_seconds': meta['this_run_total_seconds']}
        all_scores.append(scored)
    bundle = joblib.load(ROOT / 'deployment.joblib')
    metadata = json.loads((ROOT / 'DEPLOYMENT_METADATA.json').read_text(encoding='utf-8'))
    assert sha(ROOT / 'deployment.joblib') == metadata['bundle_sha256']
    for name, digest in metadata['code_sha256'].items():
        assert sha(ROOT / name) == digest
    predictions = read_rows(ROOT / 'policy_predictions.jsonl')
    assert [r['id'] for r in predictions] == ids
    expected = score_records(bundle, records, *all_scores)
    assert predictions == expected
    for prediction in predictions:
        assert set(prediction) == {'id', 'scores', 'use_evidence'}
        assert set(prediction['scores']) == set(bundle['thresholds'])
        for policy, cutoff in bundle['thresholds'].items():
            assert prediction['use_evidence'][policy] == (prediction['scores'][policy] >= cutoff)
        assert prediction['use_evidence']['always_evidence'] is True
        assert prediction['use_evidence']['always_vanilla'] is False
    old_freeze = json.loads((OLD / 'FREEZE.json').read_text(encoding='utf-8'))
    assert all(sha(OLD / name) == digest for name, digest in old_freeze['sha256'].items())
    result = {'status': 'PASS', 'validated_utc': datetime.now(timezone.utc).isoformat(),
        'label_free_checker_validation_only': True, 'labels_or_generator_outputs_read': False,
        'unique_questions': 1247, 'evidence_scores_per_question_per_arm': 6,
        'scorers': details, 'frozen_deployment_replay_identical': True,
        'all_decisions_use_frozen_greater_equal_cutoff': True, 'old_pilot_frozen_files_unchanged': True,
        'bundle_sha256': sha(ROOT / 'deployment.joblib'),
        'policy_predictions_sha256': sha(ROOT / 'policy_predictions.jsonl'),
        'validation_code_sha256': sha(Path(__file__)),
        'evidence_use_n': {policy: sum(r['use_evidence'][policy] for r in predictions)
                           for policy in predictions[0]['use_evidence']}}
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    with threadpool_limits(limits=4):
        main()
