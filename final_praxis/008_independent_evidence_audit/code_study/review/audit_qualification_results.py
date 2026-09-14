"""Read-only independent qualification artifact audit; executes no task programs."""
from __future__ import annotations
import argparse
import collections
import datetime
import gzip
import hashlib
import json
import re
import signal
from pathlib import Path


def load_observed(path):
    """Match the frozen coordinator's partial-JSONL handling, with diagnostics."""
    observed, malformed_lines = [], []
    if path.exists():
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if line.strip():
                try:
                    observed.append(json.loads(line))
                except json.JSONDecodeError:
                    malformed_lines.append(number)
    return observed, malformed_lines


def normalize_observed(task, variant, observed):
    """Fill absent outcomes with unknown status, never with pass or failure."""
    by_id = {row['case_id']: row for row in observed}
    expected = {case['case_id']: case for case in task['cases']}
    identity_ok = len(by_id) == len(observed) and not set(by_id) - set(expected)
    normalized = []
    for index, case in enumerate(task['cases']):
        row = by_id.get(case['case_id'])
        if row is None:
            row = {'task_id': task['task_id'], 'variant': variant, 'case_index': index,
                   'case_id': case['case_id'], 'split': case['split'],
                   'memberships': case['memberships'], 'status': 'not_run_worker_incomplete'}
        identity_ok = identity_ok and all(row.get(key) == value for key, value in {
            'task_id': task['task_id'], 'variant': variant, 'case_index': index,
            'case_id': case['case_id'], 'split': case['split'], 'memberships': case['memberships']}.items())
        normalized.append(row)
    return normalized, identity_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-image', default='sha256:b0fb3cb3913ee8971b7dc5df9d688cd6113068411feecb4c975339926d1a7cea')
    args = parser.parse_args()
    results, bundle = args.results, args.bundle
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    rows = lambda path: [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    checks, errors = {}, []

    def check(name, value):
        checks[name] = bool(value)
        if not value:
            errors.append(name)

    receipt = read(results / 'public/RECEIPT.json')
    cfg = read(results / 'RUN_CONFIGURATION.json')
    summary = read(results / 'public/SUMMARY.json')
    records = read(results / 'public/TASK_RESULTS.json')['tasks']
    task_rows = rows(bundle / 'data/tasks.jsonl')
    tasks = {row['task_id']: row for row in task_rows}
    check('configuration_hash', sha(results / 'RUN_CONFIGURATION.json') == receipt['configuration_sha256'])
    check('bundle_manifest_hash', sha(bundle / 'BUNDLE_MANIFEST.json') == receipt['bundle_manifest_sha256'] == cfg['bundle_manifest_sha256'])
    check('tasks_hash', sha(bundle / 'data/tasks.jsonl') == cfg['tasks_sha256'])
    for name, expected in receipt['output_sha256'].items():
        check('public_hash:' + name, sha(results / 'public' / name) == expected)
    for name, expected in receipt['qualification_hashes'].items():
        check('frozen_source:' + name, sha(bundle / name) == expected == cfg['qualification_hashes'][name])
    check('image', cfg['image_id'] == receipt['image_id'] == args.expected_image)
    check('isolation_configuration', cfg['network'] == 'none' and cfg['uid'] == 10001)
    check('all164', len(task_rows) == len(records) == 164 and len({row['task_id'] for row in records}) == 164 and set(tasks) == {f'Python/{i}' for i in range(164)} == {row['task_id'] for row in records})
    assigned = [row for row in records if row['assigned']]
    expected_assigned = set(tasks) if cfg['mode'] == 'full' else {task['task_id'] for task in tasks.values() if task['pilot']}
    check('exact_selection', {row['task_id'] for row in assigned} == expected_assigned == set(cfg['selected_ids']))
    with gzip.open(results / 'public/CASES.jsonl.gz', 'rt', encoding='utf-8') as handle:
        public = [json.loads(line) for line in handle]
    public_index = {(row['task_id'], row['variant'], row['case_id']): row for row in public}
    check('public_unique', len(public) == len(public_index))
    total = observed_total = complete_workers = 0
    counts = collections.defaultdict(collections.Counter)
    exclusions, incomplete_workers = [], []
    eligible_ids, eligible_heldout_ids = [], []
    failures = {'fail', 'exception', 'timeout', 'program_load_error'}
    for rec in assigned:
        task = tasks[rec['task_id']]
        task_dir = results / 'private' / ('task_' + rec['task_id'].split('/')[1])
        check('task_copy:' + rec['task_id'], read(task_dir / 'task.json') == task)
        variants = {}
        if not rec['variants']:
            check('coordinator_error_excluded:' + task['task_id'], not rec['eligible'] and any(reason.startswith('coordinator_error:') for reason in rec['exclusion_reasons']))
            exclusions.append({'task_id': task['task_id'], 'reasons': rec['exclusion_reasons'], 'coordinator_results_unavailable': True})
            continue
        for variant in ('reference', 'canonical', 'buggy'):
            prefix = rec['task_id'] + ':' + variant
            attempt = (results / rec['variants'][variant]['attempt_path']).resolve()
            check('attempt_path:' + prefix, attempt.is_relative_to(results.resolve()))
            summary_path, process_path, cases_path = (attempt / name for name in ('summary.json', 'PROCESS_RECEIPT.json', 'cases.jsonl'))
            worker = read(summary_path) if summary_path.exists() else None
            process = read(process_path) if process_path.exists() else None
            observed, malformed_lines = load_observed(cases_path)
            values, identity_ok = normalize_observed(task, variant, observed)
            total += len(task['cases'])
            observed_total += len(observed)
            check('process_receipt_present:' + prefix, process is not None)
            if process is not None:
                command = process.get('command', [])
                def flag_value(flag):
                    return command[command.index(flag) + 1] if flag in command and command.index(flag) + 1 < len(command) else None
                check('process_command_identity:' + prefix, len(command) >= 2 and command[1] == '/app/worker.py' and flag_value('--variant') == variant and flag_value('--task-file') == '/output/private/' + task_dir.name + '/task.json' and flag_value('--output-dir') == '/output/' + str(attempt.relative_to(results.resolve())).replace('\\', '/'))
            success_exit = bool(process and process.get('exit_code') == 0 and process.get('state') == 'exited')
            completed = bool(worker is not None and cases_path.exists() and len(observed) == len(task['cases']) and not malformed_lines and success_exit)
            complete_workers += completed
            if worker is not None:
                check('worker_identity:' + prefix, worker['task_id'] == task['task_id'] and worker['variant'] == variant and worker['isolation_checked'])
                check('code_hash:' + prefix, worker['code_sha256'] == hashlib.sha256(task['programs'][variant].encode()).hexdigest())
                check('summary_count:' + prefix, worker['assigned_cases'] == len(task['cases']))
                check('summary_status_counts:' + prefix, worker['status_counts'] == dict(collections.Counter(row['status'] for row in observed)))
            if not completed:
                explained = bool(process and (process.get('state') == 'wall_timeout' or (process.get('state') == 'exited' and isinstance(process.get('exit_code'), int) and process['exit_code'] != 0)))
                check('incomplete_process_explained:' + prefix, explained)
                log_path = attempt / 'process.log'
                log = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
                error_types = sorted(set(re.findall(r'(?m)^(?:[a-zA-Z_][\w]*\.)?([a-zA-Z_][\w]*(?:Error|Exception|Timeout))(?::|$)', log)))
                exit_code = process.get('exit_code') if process else None
                try:
                    signal_name = signal.Signals(-exit_code).name if isinstance(exit_code, int) and exit_code < 0 else None
                except ValueError:
                    signal_name = 'UNRECOGNIZED_SIGNAL'
                incomplete_workers.append({'task_id': task['task_id'], 'variant': variant, 'summary_present': worker is not None, 'cases_file_present': cases_path.exists(), 'process_receipt_present': process is not None, 'process_state': process.get('state') if process else None, 'exit_code': exit_code, 'signal': signal_name, 'log_error_types': error_types, 'assigned_cases': len(task['cases']), 'observed_rows': len(observed), 'missing_rows_normalized_unknown': len(task['cases']) - len(observed), 'malformed_json_lines': malformed_lines, 'case_status_counts': dict(collections.Counter(row['status'] for row in values)), 'task_eligible': rec['eligible'], 'task_exclusion_reasons': rec['exclusion_reasons'], 'program_hash_binding': 'worker_summary_and_task_file' if worker else 'task_file_and_process_command_only_summary_missing', 'artifacts_sha256': {path.name: sha(path) for path in (summary_path, process_path, cases_path, log_path) if path.exists()}})
            check('case_identity:' + prefix, identity_ok)
            status = collections.Counter(row['status'] for row in values)
            counts[variant].update(status)
            check('status_counts:' + prefix, dict(status) == rec['variants'][variant]['status_counts'])
            check('original_summary:' + prefix, (worker.get('original') if worker else None) == rec['variants'][variant]['original'])
            check('public_private:' + prefix, all(all(public_index.get((task['task_id'], variant, row['case_id']), {}).get(key) == row.get(key) for key in ('status', 'split', 'memberships', 'case_index')) for row in values))
            for split in ('tool', 'outcome'):
                check('split_counts:' + prefix + ':' + split, dict(collections.Counter(row['status'] for row in values if row['split'] == split)) == rec['variants'][variant]['by_split'].get(split, {}))
            variants[variant] = values
        reference_complete = rows(task_dir / 'reference_complete.jsonl')
        check('reference_complete:' + task['task_id'], reference_complete == variants['reference'])
        ref_h = [row for row in variants['reference'] if row['split'] == 'outcome']
        can_h = [row for row in variants['canonical'] if row['split'] == 'outcome']
        bug_h = [row for row in variants['buggy'] if row['split'] == 'outcome']
        original = rec['variants']['canonical']['original']
        expected_reasons = []
        if not task['identity_eligible']: expected_reasons.append('source_identity_or_signature_mismatch')
        if not ref_h: expected_reasons.append('empty_reserved_outcomes')
        if not all(row['status'] == 'pass' for row in ref_h): expected_reasons.append('reference_reserved_incomplete_or_error')
        if not all(row['status'] == 'pass' for row in can_h): expected_reasons.append('canonical_reserved_not_all_pass')
        if not original or original['status'] != 'pass': expected_reasons.append('canonical_original_suite_not_pass')
        if not any(row['status'] in failures for row in bug_h): expected_reasons.append('buggy_no_demonstrated_reserved_failure')
        eligible = not expected_reasons
        check('exact_exclusion_reasons:' + task['task_id'], expected_reasons == rec['exclusion_reasons'])
        check('eligibility:' + task['task_id'], eligible == rec['eligible'])
        if eligible:
            eligible_ids.append(task['task_id'])
            if task['split'] == 'heldout':
                eligible_heldout_ids.append(task['task_id'])
        else:
            exclusions.append({'task_id': task['task_id'], 'reasons': rec['exclusion_reasons'], 'canonical_original': original['status'] if original else None, 'canonical_reserved': dict(collections.Counter(row['status'] for row in can_h)), 'reference_reserved': dict(collections.Counter(row['status'] for row in ref_h)), 'buggy_reserved': dict(collections.Counter(row['status'] for row in bug_h))})
    check('all_public_assigned_cases', len(public) == total)
    check('eligible_ids', set(eligible_ids) == set(summary['eligible_ids']) and len(eligible_ids) == summary['eligible_pairs'])
    check('eligible_heldout_ids', set(eligible_heldout_ids) == set(summary['eligible_heldout_ids']) and len(eligible_heldout_ids) == summary['eligible_heldout_pairs'])
    exclusion_counts = dict(collections.Counter(reason for rec in assigned for reason in rec['exclusion_reasons']))
    check('exclusion_counts', exclusion_counts == summary['exclusion_counts'])
    if cfg['mode'] == 'full':
        h_pass = all(rec['variants'] for rec in assigned) and len(eligible_ids) >= 100 and len(eligible_heldout_ids) >= 60
        check('qualification_hypothesis', summary['qualification_hypothesis_evaluated'] and summary['qualification_hypothesis_pass'] == h_pass)
        recommendation = 'GO_SEPARATELY_FROZEN_POLICY_STUDY' if h_pass else 'STOP_QUALIFICATION_HYPOTHESIS_FAILED'
    else:
        recommendation = 'GO_FULL_QUALIFICATION'
    output = {'audited_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'audit_source_sha256': sha(Path(__file__)), 'results': str(results), 'results_receipt_sha256': sha(results / 'public/RECEIPT.json'), 'decision': 'STOP_INTEGRITY_FAILURE' if errors else recommendation, 'checks_passed': sum(checks.values()), 'checks_total': len(checks), 'errors': errors, 'all164_retained': len(records), 'assigned_tasks': len(assigned), 'worker_variants_assigned': len(assigned) * 3, 'worker_variants_completed': complete_workers, 'worker_variants_incomplete': len(incomplete_workers), 'normalized_case_rows': total, 'observed_worker_case_rows': observed_total, 'missing_case_rows_normalized_unknown': total - observed_total, 'eligible_pairs': len(eligible_ids), 'eligible_heldout_pairs': len(eligible_heldout_ids), 'counts': {key: dict(value) for key, value in counts.items()}, 'exclusion_counts': exclusion_counts, 'exclusions': exclusions, 'incomplete_workers': incomplete_workers, 'note': 'Integrity acceptance validates faithful retention and exclusion, not universal execution success. Missing worker rows remain unknown and missing summaries are not completion evidence. Timeouts are resource-bounded outcomes, not demonstrated semantic errors. No benchmark program executed by this audit.'}
    args.output.write_bytes((json.dumps(output, indent=2) + '\n').encode())
    print(json.dumps(output, indent=2))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
