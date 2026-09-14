"""Prepare/verify isolated generated-coordinator controls without program execution."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'verify'])
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    task = next(task for task in rows(args.tasks) if task['task_id'] == 'Python/0')
    if args.action == 'prepare':
        manifest = []
        for name, variant in [('control_positive', 'canonical'), ('control_negative', 'buggy')]:
            code = task['programs'][variant]
            manifest.append({'task_id': task['task_id'], 'proposal_id': name, 'status': 'admitted', 'code': code, 'code_sha256': hashlib.sha256(code.encode()).hexdigest(), 'control_expected_y1': variant == 'canonical'})
        manifest.append({**manifest[0], 'proposal_id': 'control_hash_rejected', 'code_sha256': '0' * 64, 'control_expected_y1': None})
        manifest.append({'task_id': task['task_id'], 'proposal_id': 'control_invalid_placeholder', 'status': 'parse_error', 'code': None, 'code_sha256': None, 'control_expected_y1': None})
        args.manifest.write_bytes((''.join(json.dumps(row) + '\n' for row in manifest)).encode())
        print(json.dumps({'manifest': str(args.manifest), 'sha256': sha(args.manifest), 'assigned': len(manifest), 'programs_executed': False}))
        return 0
    if not args.results or not args.receipt:
        parser.error('verify requires --results and --receipt')
    manifest = rows(args.manifest)
    result_rows = rows(args.results / 'public/PROPOSAL_RESULTS.jsonl')
    by_id = {row['proposal_id']: row for row in result_rows}
    checks = {}
    checks['all_assigned_retained'] = len(result_rows) == len(by_id) == len(manifest) == 4 and set(by_id) == {row['proposal_id'] for row in manifest}
    expected_cases = {case['case_id']: case for case in task['cases']}
    for source in manifest:
        proposal_id = source['proposal_id']
        row = by_id[proposal_id]
        checks[proposal_id + ':identity'] = row['task_id'] == source['task_id'] and row['proposal_id'] == proposal_id
        checks[proposal_id + ':y1'] = row['y1'] is source['control_expected_y1']
        should_execute = proposal_id in {'control_positive', 'control_negative'}
        checks[proposal_id + ':executed'] = row['executed'] is should_execute
        if should_execute:
            path = (args.results / row['cases_path']).resolve()
            checks[proposal_id + ':path'] = path.is_relative_to(args.results.resolve())
            checks[proposal_id + ':hashes'] = sha(path) == row['normalized_cases_sha256'] and row['code_sha256'] == source['code_sha256'] and row['code_hash_verified']
            vector = rows(path)
            checks[proposal_id + ':complete'] = len(vector) == len(expected_cases) == len({case['case_id'] for case in vector}) and {case['case_id'] for case in vector} == set(expected_cases)
            checks[proposal_id + ':case_identity'] = all(case['task_id'] == task['task_id'] and case['proposal_id'] == proposal_id and case['split'] == expected_cases[case['case_id']]['split'] for case in vector)
            checks[proposal_id + ':tool_vector'] = row['tool_status_vector'] == [{'case_id': case['case_id'], 'status': case['status']} for case in vector if case['split'] == 'tool']
            checks[proposal_id + ':original'] = row['original_test']['status'] == ('pass' if proposal_id == 'control_positive' else 'fail')
        else:
            checks[proposal_id + ':no_case_path'] = row['cases_path'] is None
            checks[proposal_id + ':no_executed_tool_case'] = all(case['status'] == 'not_executed_rejected' for case in row['tool_status_vector'])
    checks['hash_rejection'] = 'code_hash_mismatch' in by_id['control_hash_rejected']['rejection_reasons']
    checks['placeholder_rejection'] = 'manifest_not_admitted' in by_id['control_invalid_placeholder']['rejection_reasons']
    output = {'control_scope': 'Coordinator integration only; known benchmark variants, no model proposals.', 'control_source_sha256': sha(Path(__file__)), 'manifest_sha256': sha(args.manifest), 'checks_passed': sum(checks.values()), 'checks_total': len(checks), 'checks': checks, 'passed': all(checks.values())}
    args.receipt.write_bytes((json.dumps(output, indent=2) + '\n').encode())
    print(json.dumps(output, indent=2))
    return 0 if output['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
