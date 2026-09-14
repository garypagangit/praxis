"""Read-only independent qualification artifact audit; executes no task programs."""
from __future__ import annotations
import argparse
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path


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
    total = 0
    counts = collections.defaultdict(collections.Counter)
    exclusions = []
    eligible_ids, eligible_heldout_ids = [], []
    failures = {'fail', 'exception', 'timeout', 'program_load_error'}
    for rec in assigned:
        task = tasks[rec['task_id']]
        task_dir = results / 'private' / ('task_' + rec['task_id'].split('/')[1])
        check('task_copy:' + rec['task_id'], read(task_dir / 'task.json') == task)
        variants = {}
        for variant in ('reference', 'canonical', 'buggy'):
            prefix = rec['task_id'] + ':' + variant
            attempt = (results / rec['variants'][variant]['attempt_path']).resolve()
            check('attempt_path:' + prefix, attempt.is_relative_to(results.resolve()))
            worker = read(attempt / 'summary.json')
            process = read(attempt / 'PROCESS_RECEIPT.json')
            values = rows(attempt / 'cases.jsonl')
            total += len(task['cases'])
            check('worker_exit:' + prefix, process['exit_code'] == 0 and process['state'] == 'exited' and worker['isolation_checked'])
            check('worker_identity:' + prefix, worker['task_id'] == task['task_id'] and worker['variant'] == variant)
            check('code_hash:' + prefix, worker['code_sha256'] == hashlib.sha256(task['programs'][variant].encode()).hexdigest())
            check('count:' + prefix, len(values) == len(task['cases']) == worker['assigned_cases'])
            check('case_identity:' + prefix, len(values) == len({row['case_id'] for row in values}) and all(row['task_id'] == task['task_id'] and row['variant'] == variant and row['case_id'] == case['case_id'] and row['case_index'] == i and row['split'] == case['split'] and row['memberships'] == case['memberships'] for i, (row, case) in enumerate(zip(values, task['cases']))))
            status = collections.Counter(row['status'] for row in values)
            counts[variant].update(status)
            check('status_counts:' + prefix, dict(status) == worker['status_counts'] == rec['variants'][variant]['status_counts'])
            check('original_summary:' + prefix, worker['original'] == rec['variants'][variant]['original'])
            check('public_private:' + prefix, all(all(public_index.get((task['task_id'], variant, row['case_id']), {}).get(key) == row.get(key) for key in ('status', 'split', 'memberships', 'case_index')) for row in values))
            for split in ('tool', 'outcome'):
                check('split_counts:' + prefix + ':' + split, dict(collections.Counter(row['status'] for row in values if row['split'] == split)) == rec['variants'][variant]['by_split'].get(split, {}))
            variants[variant] = values
        reference_complete = rows(task_dir / 'reference_complete.jsonl')
        check('reference_complete:' + task['task_id'], reference_complete == variants['reference'])
        ref_h = [row for row in variants['reference'] if row['split'] == 'outcome']
        can_h = [row for row in variants['canonical'] if row['split'] == 'outcome']
        bug_h = [row for row in variants['buggy'] if row['split'] == 'outcome']
        eligible = bool(task['identity_eligible'] and ref_h and all(row['status'] == 'pass' for row in ref_h) and can_h and all(row['status'] == 'pass' for row in can_h) and rec['variants']['canonical']['original']['status'] == 'pass' and any(row['status'] in failures for row in bug_h))
        check('eligibility:' + task['task_id'], eligible == rec['eligible'])
        if eligible:
            eligible_ids.append(task['task_id'])
            if task['split'] == 'heldout':
                eligible_heldout_ids.append(task['task_id'])
        else:
            exclusions.append({'task_id': task['task_id'], 'reasons': rec['exclusion_reasons'], 'canonical_original': rec['variants']['canonical']['original']['status'], 'canonical_reserved': dict(collections.Counter(row['status'] for row in can_h)), 'reference_reserved': dict(collections.Counter(row['status'] for row in ref_h)), 'buggy_reserved': dict(collections.Counter(row['status'] for row in bug_h))})
    check('all_public_assigned_cases', len(public) == total)
    check('eligible_ids', set(eligible_ids) == set(summary['eligible_ids']) and len(eligible_ids) == summary['eligible_pairs'])
    check('eligible_heldout_ids', set(eligible_heldout_ids) == set(summary['eligible_heldout_ids']) and len(eligible_heldout_ids) == summary['eligible_heldout_pairs'])
    if cfg['mode'] == 'full':
        h_pass = len(eligible_ids) >= 100 and len(eligible_heldout_ids) >= 60
        check('qualification_hypothesis', summary['qualification_hypothesis_evaluated'] and summary['qualification_hypothesis_pass'] == h_pass)
        recommendation = 'GO_SEPARATELY_FROZEN_POLICY_STUDY' if h_pass else 'STOP_QUALIFICATION_HYPOTHESIS_FAILED'
    else:
        recommendation = 'GO_FULL_QUALIFICATION'
    output = {'audited_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'audit_source_sha256': sha(Path(__file__)), 'results': str(results), 'results_receipt_sha256': sha(results / 'public/RECEIPT.json'), 'decision': 'STOP_INTEGRITY_FAILURE' if errors else recommendation, 'checks_passed': sum(checks.values()), 'checks_total': len(checks), 'errors': errors, 'all164_retained': len(records), 'assigned_tasks': len(assigned), 'worker_variants': len(assigned) * 3, 'complete_case_rows': total, 'eligible_pairs': len(eligible_ids), 'eligible_heldout_pairs': len(eligible_heldout_ids), 'counts': {key: dict(value) for key, value in counts.items()}, 'exclusions': exclusions, 'note': 'Timeouts are resource-bounded outcomes, not demonstrated semantic errors. No benchmark program executed by this audit.'}
    args.output.write_bytes((json.dumps(output, indent=2) + '\n').encode())
    print(json.dumps(output, indent=2))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
