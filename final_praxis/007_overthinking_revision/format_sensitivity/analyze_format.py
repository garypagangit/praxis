"""Post hoc local formatting sensitivity; no inference or changes to original scores."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BUCKET = 'praxis-garypagan-272615233626-us-east-1'
PREFIX = 'final-praxis/20260912/runs/fp007-20260912-81b445c/outputs/'
FROZEN_FILES = ('PROTOCOL.md', 'analyze_format.py', 'test_format.py',
                'original_runner_reference.py', 'original_preregistration_reference.md',
                'frozen_fixtures.json', 'source_receipt.json')
spec = importlib.util.spec_from_file_location('original_007', HERE/'original_runner_reference.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    """Return transformed text and an audit trail; deliberately has no gold argument."""
    changes = []
    try:
        decoded = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        decoded = None
    if isinstance(decoded, str):
        text = decoded
        changes.append('json_string_decoded_once')
    tail_end = len(text.rstrip())
    start = text.rfind('\n', 0, tail_end) + 1
    tail = text[start:tail_end]
    plain = r'FINAL: (?:[A-E]|TRUE|FALSE)'
    patterns = [
        (rf'\*\*({plain})\*\*', ['bold']),
        (rf'`({plain})`', ['backtick']),
        (rf'``({plain})``', ['double_backtick']),
        (rf'\*\*`({plain})`\*\*', ['bold', 'backtick']),
        (rf'\*\*``({plain})``\*\*', ['bold', 'double_backtick']),
        (rf'`\*\*({plain})\*\*`', ['backtick', 'bold']),
        (rf'``\*\*({plain})\*\*``', ['double_backtick', 'bold']),
    ]
    for pattern, wrappers in patterns:
        match = re.fullmatch(pattern, tail)
        if match:
            text = text[:start] + match[1] + text[tail_end:]
            changes.extend('terminal_' + x for x in wrappers)
            break
    return text, changes


def sensitivity(text, labels, truncated=False):
    normalized, changes = normalize(text)
    return original.parse(normalized, labels, truncated), changes


def verify_freeze(commit):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Use the complete 40-character reviewed freeze commit')
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=HERE).decode().strip())
    receipts = {}
    for name in FROZEN_FILES:
        path = HERE/name
        rel = path.relative_to(repo).as_posix()
        frozen = subprocess.check_output(['git', 'show', commit + ':' + rel], cwd=repo)
        local = path.read_bytes()
        if local.replace(b'\r\n', b'\n') != frozen.replace(b'\r\n', b'\n'):
            raise ValueError('File differs from freeze commit: ' + name)
        receipts[name] = {'local_sha256': sha(local), 'committed_sha256': sha(frozen)}
    return receipts


def expected_cells(items):
    expected = {}
    for model in original.MODELS:
        for item in items:
            key = original.sha((model + ':' + item['dataset'] + ':' + item['id']).encode())[:20]
            for arm in ('initial',) + original.ARMS:
                relative = 'cells/' + key + '/' + arm + '.json'
                expected[relative] = (model, item, arm)
    if len(expected) != 384:
        raise ValueError('Expected exactly 384 distinct cells')
    return expected


def download(client, relative, output):
    result = client.get_object(Bucket=BUCKET, Key=PREFIX+relative)
    limit = 8 * 1024 * 1024
    if result.get('ContentLength', 0) > limit:
        raise ValueError('Unexpected oversized object: ' + relative)
    body = result['Body']
    try:
        data = body.read(limit+1)
    finally:
        body.close()
    if len(data) > limit:
        raise ValueError('Oversized object: ' + relative)
    path = output/'inputs'/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    receipt = {'key': PREFIX+relative, 'sha256': sha(data), 'bytes': len(data),
               'etag': result.get('ETag'), 'version_id': result.get('VersionId'),
               'last_modified': str(result.get('LastModified'))}
    return relative, json.loads(data), receipt


def local_report(items, cells, score_name):
    # Reuse the exact reviewed report, including its paired denominator/bootstrap.
    with tempfile.TemporaryDirectory(prefix='fp007-format-report-') as temporary:
        target = Path(temporary)
        for relative, cell in cells.items():
            original.write(target/relative, {'score': cell[score_name]})
        return original.report(items, target)


def analyze(items, expected, data):
    cells = {}
    changes = defaultdict(Counter)
    cell_rows = []
    for relative, (model, item, arm) in expected.items():
        cell = data[relative]
        identity = (cell['model'], cell['dataset'], cell['id'], cell['arm'])
        if identity != (model, item['dataset'], item['id'], arm):
            raise ValueError('Cell identity mismatch: ' + relative)
        labels = [x['label'] for x in item['options']] or ['TRUE', 'FALSE']
        strict = original.score(cell['result'], labels, 512 if arm == 'initial' else 768)
        if strict != cell['score']:
            raise ValueError('Stored strict score mismatch: ' + relative)
        answer, applied = sensitivity(cell['result']['text'], labels, strict['truncated'])
        relaxed = {**strict, 'answer': answer}
        if strict['answer'] is not None and answer != strict['answer']:
            raise ValueError('Normalization changed a valid strict label: ' + relative)
        cells[relative] = {**cell, 'sensitivity_score': relaxed}
        group = changes[model + '/' + item['dataset'] + '/' + arm]
        group['n'] += 1
        group['truncated'] += int(strict['truncated'])
        group['strict_invalid'] += int(strict['answer'] is None)
        group['sensitivity_invalid'] += int(answer is None)
        group['repaired_invalid'] += int(strict['answer'] is None and answer is not None)
        group['transformed_text'] += int(bool(applied))
        cell_rows.append({'model': model, 'dataset': item['dataset'], 'id': item['id'], 'arm': arm,
                          'strict_answer': strict['answer'], 'sensitivity_answer': answer,
                          'benchmark_gold': item['gold'], 'truncated': strict['truncated'],
                          'normalizations': applied, 'source_key': PREFIX+relative})
    strict_summary = local_report(items, cells, 'score')
    if strict_summary != data['summary.json']:
        raise ValueError('Frozen strict summary does not match its exact recomputation')
    sensitivity_summary = local_report(items, cells, 'sensitivity_score')
    cases = []
    for relative, (model, item, arm) in expected.items():
        if arm == 'initial':
            continue
        before_key = relative.rsplit('/', 1)[0] + '/initial.json'
        before = cells[before_key]['score']['answer']
        after = cells[relative]['score']['answer']
        if before == item['gold'] and after is not None and after != item['gold']:
            cases.append({'model': model, 'dataset': item['dataset'], 'id': item['id'], 'arm': arm,
                          'initial_label': before, 'revised_label': after, 'benchmark_gold': item['gold'],
                          'question': item['question'], 'options': item['options'], 'evidence': item['evidence'],
                          'initial_source_key': PREFIX+before_key, 'revision_source_key': PREFIX+relative})
    prior_case = [x for x in items if x['dataset'] == 'aqua' and x['id'] == '1000']
    return {'strict_summary': strict_summary, 'sensitivity_summary': sensitivity_summary,
            'format_counts': dict(changes), 'cell_scores': cell_rows,
            'strict_correct_to_wrong_audit_cases': cases,
            'prior_observation_audit_case': prior_case,
            'correctness_definition': 'benchmark-key correctness; labels unchanged',
            'analysis_status': 'POST_HOC_FORMATTING_SENSITIVITY', 'publication_claim': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--profile', default='praxis-build')
    args = parser.parse_args()
    freeze = verify_freeze(args.freeze_commit)
    if args.out.exists():
        raise ValueError('Output directory must not exist; preserve earlier analyses')
    fixture_bytes = (HERE/'frozen_fixtures.json').read_bytes()
    fixture = json.loads(fixture_bytes)
    if fixture.get('calibration_only') is not True:
        raise ValueError('Expected frozen calibration-only fixture')
    expected = expected_cells(fixture['items'])
    args.out.mkdir(parents=True)
    original.write(args.out/'analysis_manifest.json', {
        'started_utc': datetime.now(timezone.utc).isoformat(), 'freeze_commit': args.freeze_commit,
        'frozen_files': freeze, 'source': 's3://' + BUCKET + '/' + PREFIX,
        'paper': 'https://arxiv.org/html/2608.26511v1',
        'data_revision': fixture['source_revision'], 'data_source_hashes': fixture['source_hashes'],
        'workers': 8, 'additional_inference_requests': 0, 'post_hoc': True})
    import boto3
    from botocore.config import Config
    client = boto3.Session(profile_name=args.profile, region_name='us-east-1').client(
        's3', config=Config(max_pool_connections=8, retries={'max_attempts': 3},
                            connect_timeout=15, read_timeout=45))
    data, receipts = {}, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for relative, parsed, receipt in pool.map(
                lambda key: download(client, key, args.out), ['manifest.json', 'summary.json'] + sorted(expected)):
            data[relative] = parsed
            receipts.append(receipt)
    original.write(args.out/'input_receipts.json', receipts)
    manifest = data['manifest.json']
    checks = {'fixture_sha256': sha(fixture_bytes),
              'runner_sha256': sha((HERE/'original_runner_reference.py').read_bytes()),
              'prereg_sha256': sha((HERE/'original_preregistration_reference.md').read_bytes())}
    if any(manifest.get(key) != value for key, value in checks.items()):
        raise ValueError('Cloud manifest source hash mismatch; do not reinterpret silently')
    result = analyze(fixture['items'], expected, data)
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            original.write(args.out/(key+'.json'), value)
    original.write(args.out/'analysis_result.json', result)
    print(json.dumps({'status': result['analysis_status'], 'output': str(args.out.resolve()),
                      'cells': len(result['cell_scores']), 'strict_summary_verified': True}))


if __name__ == '__main__':
    main()
