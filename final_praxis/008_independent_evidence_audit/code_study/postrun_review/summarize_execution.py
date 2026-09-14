"""Reconcile completed V1/V2 sample flow, request reuse and API cost receipts.

Reads artifacts as data only. Does not execute candidate programs, call APIs,
inspect scientific effect estimates, or treat reused records as new responses.
"""
from __future__ import annotations
import argparse
import collections
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

QWEN = 'qwen.qwen3-coder-next'
WARMUP = 'v2-review-schema-warmup-v2'
REVIEW_PARTS = [(cohort, split) for cohort in ('native', 'generated') for split in ('development', 'heldout')]


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique_object)
def rows(path): return [json.loads(line, object_pairs_hook=unique_object) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def by_id(values, key):
    result = {}
    for row in values:
        identifier = row.get(key)
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,150}', identifier): raise ValueError('Invalid record identity')
        if identifier in result: raise ValueError('Duplicate record identity: ' + identifier)
        result[identifier] = row
    return result


def safe_relative(root, value):
    relative = PurePosixPath(value.replace('\\', '/'))
    if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe artifact path')
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError('Artifact path escapes result directory')
    return path


def complete_state(root, version):
    path = root / ('STUDY_PROCESS_STATUS.json' if version == 'v1' else 'EXTENSION_PROCESS_STATUS.json')
    if not path.exists(): return False, None
    value = read(path)
    complete = value.get('status') == 'finished' and (value.get('exit_code') == 0 if version == 'v1' else value.get('failure') is None)
    return complete, path


def load_run(root, version):
    complete, status = complete_state(root, version)
    if not complete: raise ValueError('Only completed result directories can be reconciled: ' + str(root))
    sources = {status.name: sha(status)}
    decisions, proposals, review_jobs, proposal_jobs = [], [], [], []
    for cohort, split in REVIEW_PARTS:
        for prefix, target in [('decisions_', decisions), ('review_jobs_', review_jobs)]:
            path = root / (prefix + cohort + '_' + split + '.jsonl')
            values = rows(path)
            sources[path.name] = sha(path)
            target.extend(values)
    for split in ('development', 'heldout'):
        for prefix, target in [('proposals_', proposals), ('proposal_jobs_', proposal_jobs)]:
            path = root / (prefix + split + '.jsonl')
            values = rows(path)
            sources[path.name] = sha(path)
            target.extend(values)
    decisions, review_jobs = by_id(decisions, 'job_id'), by_id(review_jobs, 'job_id')
    proposals, proposal_jobs = by_id(proposals, 'proposal_id'), by_id(proposal_jobs, 'proposal_id')
    if set(decisions) != set(review_jobs) or set(proposals) != set(proposal_jobs): raise ValueError('Assignment/record identity universes differ')
    record_hashes = {}
    for kind, records, jobs, folder in [('review', decisions, review_jobs, 'decisions'), ('proposal', proposals, proposal_jobs, 'proposals')]:
        for identifier, record in records.items():
            if type(record.get('eligible')) is not bool or (kind == 'review' and type(record.get('model_valid')) is not bool): raise ValueError('Assignment validity fields must be booleans')
            path = root / folder / (identifier + '.json')
            if read(path) != record: raise ValueError('Aggregate/per-record mismatch: ' + identifier)
            if record.get('assignment_sha256') != digest(jobs[identifier]): raise ValueError('Assignment hash mismatch: ' + identifier)
            record_hashes[folder + '/' + identifier + '.json'] = sha(path)
    budget_path = root / 'budget.json'
    budget = read(budget_path)
    sources['budget.json'] = sha(budget_path)
    attempts = collections.defaultdict(list)
    for key, entry in budget['entries'].items():
        match = re.fullmatch(r'(.+)\.attempt-([1-9][0-9]*)', key)
        if not match: raise ValueError('Unexpected budget entry identity: ' + key)
        if Decimal(str(entry['accounted_usd'])) < 0: raise ValueError('Negative accounted cost')
        attempts[match[1]].append((key, entry))
    raw_results, raw_hashes = {}, {}
    for path in sorted((root / 'raw_inference').glob('*.result.json')):
        result = read(path)
        identifier = result['request_id']
        if path.name != identifier + '.result.json' or identifier in raw_results: raise ValueError('Repeated or misnamed raw result')
        if identifier not in attempts: raise ValueError('Raw result has no budget-attempt lineage')
        if not any(entry['status'] == 'SUCCESS' and entry['model_id'] == result['model_id'] for _, entry in attempts[identifier]): raise ValueError('Raw result lacks a matching successful ledger attempt')
        raw_results[identifier] = result
        raw_hashes[path.name] = sha(path)
    request_files = sorted((root / 'raw_inference').glob('*.request.json'))
    for attempt_id in budget['entries']:
        if not (root / 'raw_inference' / (attempt_id + '.request.json')).exists(): raise ValueError('Ledger attempt lacks saved request receipt')
    sources['raw_result_tree_sha256'] = digest(raw_hashes)
    sources['immutable_record_tree_sha256'] = digest(record_hashes)
    return {'root': root, 'version': version, 'decisions': decisions, 'proposals': proposals, 'review_jobs': review_jobs,
            'proposal_jobs': proposal_jobs, 'budget': budget, 'attempts': attempts, 'raw': raw_results, 'sources': sources,
            'request_receipt_files': len(request_files), 'reuse': {}, 'lineage': []}


def bind_reuse(v1, v2):
    manifests = sorted(v2['root'].glob('IMPORTED_*.json'))
    if not manifests: raise ValueError('Completed V2 has no explicit import manifests')
    destinations = set()
    for manifest in manifests:
        v2['sources'][manifest.name] = sha(manifest)
        for item in read(manifest)['imports']:
            if item['destination'] in destinations: raise ValueError('Duplicate reuse-manifest destination')
            destinations.add(item['destination'])
            source_name = PurePosixPath(item['source'])
            if not source_name.parts or source_name.parts[0] != 'study': raise ValueError('Unexpected lineage source root')
            source = safe_relative(v1['root'], str(PurePosixPath(*source_name.parts[1:])))
            destination = safe_relative(v2['root'], item['destination'])
            if sha(source) != item['sha256'] or sha(destination) != item['sha256']: raise ValueError('Reuse hash mismatch')
            if item['kind'] == 'review_decision':
                identifier = item['job_id']
                if item.get('reviewer') != 'mistral.devstral-2-123b' or item.get('new_call') is not False: raise ValueError('Unexpected review reuse classification')
                if identifier not in v2['decisions'] or identifier not in v1['decisions'] or v2['decisions'][identifier] != v1['decisions'][identifier]: raise ValueError('Reused review differs from its original observation')
                if item['destination'] != 'decisions/' + identifier + '.json': raise ValueError('Reused decision destination identity mismatch')
                v2['reuse'][('review', identifier)] = v1
            elif item['kind'] == 'development_proposal':
                identifier = item['proposal_id']
                if identifier not in v2['proposals'] or identifier not in v1['proposals'] or v2['proposals'][identifier] != v1['proposals'][identifier]: raise ValueError('Reused proposal differs from its original record')
                if item['destination'] != 'proposals/' + identifier + '.json': raise ValueError('Reused proposal destination identity mismatch')
                v2['reuse'][('proposal', identifier)] = v1
            elif item['kind'] != 'development_proposal_aggregate':
                raise ValueError('Unknown reuse-manifest kind')
            v2['lineage'].append({'kind': item['kind'], 'source': item['source'], 'destination': item['destination'], 'sha256': item['sha256']})
    expected_reviews = {('review', key) for key, value in v2['decisions'].items() if value['reviewer'] == 'mistral.devstral-2-123b' and (value['cohort'] == 'native' or value['split'] in ('dev', 'development'))}
    expected_proposals = {('proposal', key) for key, value in v2['proposals'].items() if value['split'] in ('dev', 'development')}
    if set(v2['reuse']) != expected_reviews | expected_proposals: raise ValueError('Reuse universe differs from the frozen model/cohort/split rule')


def request_for(run, kind, identifier, record):
    origin = run['reuse'].get((kind, identifier), run)
    if kind == 'proposal':
        request_id = 'proposal-' + identifier
        model = record['proposer']
    else:
        request_id = ('v2-' if origin['version'] == 'v2' and record['reviewer'] == QWEN else '') + identifier
        model = record['reviewer']
    result = origin['raw'].get(request_id)
    if result and result['model_id'] != model: raise ValueError('Assigned model/raw-result mismatch')
    if kind == 'review' and record['model_status'] == 'complete' and result is None: raise ValueError('Completed review lacks a raw provider result')
    if kind == 'review' and record.get('model_valid') and result is None: raise ValueError('Valid review lacks a provider result')
    if kind == 'proposal' and record.get('inference_request_id') and record['inference_request_id'] != request_id: raise ValueError('Proposal request identity mismatch')
    if kind == 'proposal' and (record.get('inference_request_id') or record['status'] in ('admitted', 'rejected', 'invalid')) and result is None: raise ValueError('Returned proposal lacks a raw provider result')
    return origin, request_id, result


def phase_summary(run, used, valid_observations):
    reviews, proposals = {}, {}
    reused_responses = new_responses = 0
    for kind, records, groups in [('review', run['decisions'], reviews), ('proposal', run['proposals'], proposals)]:
        for identifier, record in records.items():
            origin, request_id, result = request_for(run, kind, identifier, record)
            reused = origin is not run
            split = 'development' if record['split'] == 'dev' else record['split']
            model = record['reviewer'] if kind == 'review' else record['proposer']
            key = (record['cohort'], split, model) if kind == 'review' else (split, model)
            if key not in groups:
                groups[key] = {'cohort': record['cohort'] if kind == 'review' else 'proposal', 'split': split, 'model': model,
                               'assigned_records': 0, 'eligible_records': 0, 'imported_records': 0, 'new_provider_results': 0,
                               'reused_provider_results': 0, 'valid_reviews': 0, 'status_counts': collections.Counter()}
            group = groups[key]
            group['assigned_records'] += 1
            group['eligible_records'] += record.get('eligible') is True
            group['imported_records'] += reused
            group['status_counts'][record['model_status'] if kind == 'review' else record['status']] += 1
            if kind == 'review': group['valid_reviews'] += record.get('model_valid') is True
            if result:
                lineage_key = (origin['version'], request_id)
                use_key = (run['version'], kind, identifier)
                if use_key in used: raise ValueError('Repeated assigned observation')
                used[use_key] = lineage_key
                group['reused_provider_results' if reused else 'new_provider_results'] += 1
                reused_responses += reused
                new_responses += not reused
                if kind == 'review' and record.get('model_valid') is True: valid_observations.add(lineage_key)
    cost_models = {}
    for model in sorted({entry['model_id'] for entry in run['budget']['entries'].values()}):
        entries = [entry for entry in run['budget']['entries'].values() if entry['model_id'] == model]
        cost_models[model] = {'ledger_attempts': len(entries), 'status_counts': dict(collections.Counter(entry['status'] for entry in entries)),
                              'accounted_usd_estimate': str(sum((Decimal(str(entry['accounted_usd'])) for entry in entries), Decimal(0))),
                              'successful_usage_cost_usd_estimate': str(sum((Decimal(str(entry['accounted_usd'])) for entry in entries if entry['status'] == 'SUCCESS'), Decimal(0))),
                              'other_or_unresolved_accounted_usd': str(sum((Decimal(str(entry['accounted_usd'])) for entry in entries if entry['status'] != 'SUCCESS'), Decimal(0))),
                              'input_tokens': sum(entry.get('usage', {}).get('inputTokens', 0) for entry in entries),
                              'output_tokens': sum(entry.get('usage', {}).get('outputTokens', 0) for entry in entries)}
    control_results = [identifier for identifier in run['raw'] if identifier == WARMUP]
    own_used = {key[1] for key in used.values() if key[0] == run['version']}
    orphans = set(run['raw']) - own_used - set(control_results)
    if orphans: raise ValueError('Unassigned raw results without declared control lineage: ' + str(sorted(orphans)))
    successful_attempts = sum(entry['status'] == 'SUCCESS' for entry in run['budget']['entries'].values())
    if successful_attempts != len(run['raw']): raise ValueError('Successful ledger attempts/raw result count differ; requires explicit recovery audit')
    return {'status': 'completed', 'version': run['version'], 'source_directory': str(run['root']), 'source_hashes': run['sources'],
            'review_groups': [dict(value, status_counts=dict(value['status_counts'])) for _, value in sorted(reviews.items())],
            'proposal_groups': [dict(value, status_counts=dict(value['status_counts'])) for _, value in sorted(proposals.items())],
            'review_assignments': len(run['decisions']), 'proposal_assignments': len(run['proposals']),
            'logical_requests_with_ledger_attempts': len(run['attempts']), 'ledger_attempts': len(run['budget']['entries']),
            'request_receipt_files': run['request_receipt_files'], 'raw_provider_results': len(run['raw']),
            'new_assigned_provider_results': new_responses, 'reused_assigned_provider_results': reused_responses,
            'synthetic_control_provider_results': len(control_results), 'imported_records': len(run['reuse']),
            'cost_models': cost_models, 'api_accounted_usd_estimate': str(sum((Decimal(value['accounted_usd_estimate']) for value in cost_models.values()), Decimal(0))),
            'api_ledger_limit_usd': run['budget'].get('limit_usd'), 'price_source': run['budget'].get('price_source'),
            'price_checked': run['budget'].get('price_checked'), 'invoice_claimed': False,
            'lineage_manifests': run['lineage']}


def summarize(v1_path, v2_path=None):
    v1 = load_run(Path(v1_path), 'v1')
    runs = [v1]
    if v2_path and complete_state(Path(v2_path), 'v2')[0]:
        v2 = load_run(Path(v2_path), 'v2')
        bind_reuse(v1, v2)
        runs.append(v2)
    used, valid_observations = {}, set()
    summaries = [phase_summary(run, used, valid_observations) for run in runs]
    if len(runs) == 1:
        summaries.append({'version': 'v2', 'status': 'pending', 'source_directory': str(v2_path) if v2_path else None,
                          'counts': None, 'note': 'No completed V2 artifacts were supplied; pending is not zero activity or a zero outcome.'})
    provider_ids = {}
    for run in runs:
        for identifier, result in run['raw'].items():
            aws_id = result.get('aws_request_id')
            if aws_id:
                if aws_id in provider_ids: raise ValueError('Provider result duplicated across local phase directories; do not count it as a new call')
                provider_ids[aws_id] = (run['version'], identifier)
    return {'schema_version': 1, 'tool_sha256': sha(Path(__file__)), 'runs': summaries,
            'combined': {'completed_versions': len(runs), 'distinct_provider_results': sum(len(run['raw']) for run in runs),
                         'distinct_assigned_provider_results': len(set(used.values())), 'distinct_valid_review_responses': len(valid_observations),
                         'reused_assigned_results_in_v2': summaries[1].get('reused_assigned_provider_results') if len(runs) == 2 else None,
                         'ledger_attempts': sum(len(run['budget']['entries']) for run in runs),
                         'api_accounted_usd_estimate': str(sum((Decimal(value['api_accounted_usd_estimate']) for value in summaries if value['status'] == 'completed'), Decimal(0)))},
            'interpretation': ['Assignments include invalid, ineligible, and gate-blocked placeholders; they are not all provider calls.',
                               'Reuse is identified only by verified source/destination import hashes and the frozen model/cohort/split rule.',
                               'Copied provider responses count once in combined distinct-response totals. Distinct configurations are not independent scientific replications.',
                               'Costs sum each phase ledger once, including synthetic warmup and unresolved attempt reservations; imported records do not add a second charge.',
                               'API estimates use recorded usage/rates and are not an AWS invoice. Host, storage, transfer, and tax costs are outside this tool.'],
            'candidate_programs_executed': False, 'api_calls_made': 0}


def markdown(report):
    text = ['# Experiment execution and API accounting', '', 'Counts distinguish assigned records, new provider results, and explicitly reused results. Pending V2 results are not interpreted as zeros.', '',
            '| Version | Cohort | Split | Model | Assigned | Eligible | New results | Reused results | Valid reviews |',
            '|---|---|---|---|---:|---:|---:|---:|---:|']
    for run in report['runs']:
        if run['status'] != 'completed':
            text.append('| v2 | Pending | — | — | — | — | — | — | — |'); continue
        for row in run['review_groups'] + run['proposal_groups']:
            text.append('| ' + ' | '.join(str(value) for value in (run['version'], row['cohort'], row['split'], row['model'], row['assigned_records'], row['eligible_records'], row['new_provider_results'], row['reused_provider_results'], row['valid_reviews'] if row['cohort'] != 'proposal' else '—')) + ' |')
    text += ['', '| Version | Ledger attempts | Provider results | Synthetic controls | API estimate (USD) |', '|---|---:|---:|---:|---:|']
    for run in report['runs']:
        if run['status'] == 'completed': text.append(f"| {run['version']} | {run['ledger_attempts']} | {run['raw_provider_results']} | {run['synthetic_control_provider_results']} | {Decimal(run['api_accounted_usd_estimate']):.6f} |")
    text += ['', f"Combined API estimate for completed versions: **${Decimal(report['combined']['api_accounted_usd_estimate']):.6f}**. This is not an invoice and excludes host/storage/transfer costs.", '',
             'Exact status counts, token totals, lineage hashes, and unresolved reservations are in `EXECUTION_ACCOUNTING.json`.', '']
    text += ['- ' + line for line in report['interpretation']]
    return '\n'.join(text) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v1', type=Path, required=True)
    parser.add_argument('--v2', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.v1, args.v2)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'EXECUTION_ACCOUNTING.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
    (args.output_dir / 'SAMPLE_FLOW.md').write_bytes(markdown(report).encode())
    print(json.dumps({'output': str(args.output_dir), 'combined': report['combined'], 'v2_status': report['runs'][1]['status']}, indent=2))


if __name__ == '__main__': main()
