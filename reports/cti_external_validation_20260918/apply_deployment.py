"""Apply the frozen old-data CTI selector to label-free records and MiniLM scores."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
DEFAULT_HELPER = ROOT.parent / 'cti_checker_pilot_20260918' / 'run_pilot.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_helper(path=DEFAULT_HELPER, expected_sha=None):
    path = Path(path).resolve()
    if expected_sha is not None and sha(path) != expected_sha:
        raise ValueError('Frozen feature-helper hash mismatch')
    spec = importlib.util.spec_from_file_location('cti_frozen_pilot_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_rows(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def safe_record(record):
    """Explicit input contract: reject top-level outcomes, answers, and source labels."""
    allowed = {'id', 'question', 'options', 'evidence'}
    if set(record) != allowed:
        raise ValueError(f'Record must have exactly these fields: {sorted(allowed)}')
    if not isinstance(record['id'], str) or not isinstance(record['question'], str):
        raise ValueError('id and question must be strings')
    options = record['options']
    if not isinstance(options, dict) or len(options) < 2 or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in options.items()
    ):
        raise ValueError('At least two string answer options are required')
    evidence = record['evidence']
    if not isinstance(evidence, list) or len(evidence) < 2:
        raise ValueError('Frozen features require at least two evidence records')
    projected = []
    for item in evidence:
        if set(item) - {'text', 'kind', 'score'} or not {'text', 'kind'} <= set(item):
            raise ValueError('Evidence permits only text, kind, and optional score')
        if not isinstance(item['text'], str) or not isinstance(item['kind'], str):
            raise ValueError('Evidence text and kind must be strings')
        score = float(item.get('score', 0))
        if not np.isfinite(score):
            raise ValueError('Non-finite retrieval score')
        projected.append({'text': item['text'], 'kind': item['kind'], 'score': score})
    return {'id': record['id'], 'question': record['question'],
            'options': dict(options), 'evidence': projected}


def score_map(rows, records):
    by_id = {row['id']: row for row in rows}
    ids = [row['id'] for row in records]
    if len(by_id) != len(rows) or set(by_id) != set(ids):
        raise ValueError('Scores must match the unique input IDs exactly')
    for record in records:
        values = np.asarray(by_id[record['id']]['logits'], dtype=float)
        if values.ndim != 1 or len(values) != len(record['evidence']) or not np.isfinite(values).all():
            raise ValueError('Invalid per-evidence relevance logits')
    return by_id


def score_records(bundle, records, question_scores, option_scores, helper_path=DEFAULT_HELPER):
    """No labels are accepted; all fitted parameters and thresholds come from bundle."""
    if isinstance(bundle, (str, Path)):
        bundle = joblib.load(bundle)
    helper = load_helper(helper_path, bundle['helper_sha256'])
    records = [safe_record(row) for row in records]
    if not records or len({r['id'] for r in records}) != len(records):
        raise ValueError('Non-empty unique records are required')
    qm = score_map(question_scores, records)
    om = score_map(option_scores, records)
    text = [helper.question_text(row) for row in records]
    feature_dicts = [helper.features(row, qm[row['id']]['logits']) for row in records]
    names = bundle['feature_names']
    if any(list(f) != names for f in feature_dicts):
        raise ValueError('Frozen feature order differs from bundle')
    dense = np.asarray([[f[n] for n in names] for f in feature_dicts], dtype=float)
    if not np.isfinite(dense).all():
        raise ValueError('Non-finite frozen features')
    x = sparse.hstack([v.transform(text) for v in bundle['vectorizers']], format='csr')
    z = sparse.hstack([x, sparse.csr_matrix(bundle['scaler'].transform(dense))], format='csr')
    scores = {
        'relevance': dense[:, names.index('relevance_max')],
        'relevance_options': np.asarray([max(om[r['id']]['logits']) for r in records]),
        'source_classifier': bundle['source_classifier'].predict_proba(x)[:, 1],
        'question_utility': bundle['question_utility'].predict(x),
        'evidence_utility': bundle['evidence_utility'].predict(z),
    }
    if any(not np.isfinite(v).all() for v in scores.values()):
        raise ValueError('Non-finite policy score')
    output = []
    for i, record in enumerate(records):
        decision = {name: bool(values[i] >= bundle['thresholds'][name])
                    for name, values in scores.items()}
        decision.update(always_vanilla=False, always_evidence=True)
        output.append({'id': record['id'], 'scores': {name: float(v[i]) for name, v in scores.items()},
                       'use_evidence': decision})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT / 'deployment.joblib')
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--question-scores', type=Path, required=True)
    parser.add_argument('--option-scores', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--helper', type=Path, default=DEFAULT_HELPER)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    with threadpool_limits(limits=4):
        result = score_records(args.bundle, read_rows(args.records), read_rows(args.question_scores),
                               read_rows(args.option_scores), args.helper)
    with args.output.open('x', encoding='utf-8') as stream:
        for row in result:
            stream.write(json.dumps(row, allow_nan=False) + '\n')
    print(json.dumps({'rows': len(result), 'output': str(args.output), 'sha256': sha(args.output)}))


if __name__ == '__main__':
    main()
