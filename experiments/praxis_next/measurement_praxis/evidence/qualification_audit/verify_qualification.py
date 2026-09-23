"""Independent verification of prior dataset and cutoff-support measurements.

Uses only standard-library CSV parsing and direct counts at tied timestamp
blocks. It never imports the original pandas auditor or support-bound function.
The sweep considers every distinct possible before/after membership state;
it is an independent check of registered claims, not model/cutoff selection.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = next(path for path in HERE.parents if (path / '.git').exists())
D1 = REPO / 'experiments/praxis_next/d1_benchmark_audit'
CODE_FILES = [HERE / 'verify_qualification.py', HERE / 'test_verify_qualification.py']
EPOCH = datetime(1970, 1, 1)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=200000)
def parse_recorded(value, formats):
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError('Unparsed recorded timestamp; refusing repair or row removal')


def to_ns(value):
    delta = value - EPOCH
    return (delta.days * 86400 + delta.seconds) * 1000000000 + delta.microseconds * 1000


def from_ns(value):
    if value % 1000:
        raise ValueError('Prior bound cannot be exactly represented in microseconds')
    return EPOCH + timedelta(microseconds=value // 1000)


def sweep_support(blocks):
    """Directly count all rows on each side of every distinct cutoff state.

    After consuming all rows tied at t_i, the membership of a cutoff in
    (t_i, t_(i+1)] is fixed. Such a state is feasible if each native class has
    >=2 consumed and >=1 remaining rows. No per-class order statistic is used.
    """
    totals = Counter()
    for counts in blocks.values():
        totals.update(counts)
    if not totals:
        raise ValueError('No native classes')
    train = Counter()
    times = sorted(blocks)
    feasible_intervals = []
    for index, timestamp in enumerate(times[:-1]):
        train.update(blocks[timestamp])
        if all(train[label] >= 2 and totals[label] - train[label] >= 1 for label in totals):
            feasible_intervals.append((timestamp, times[index+1]))
    if feasible_intervals:
        # One contiguous admissible interval is expected because training
        # counts can only increase and remaining test counts can only decrease.
        if any(a[1] != b[0] for a, b in itertools.pairwise(feasible_intervals)):
            raise AssertionError('Unexpected disjoint count-support intervals')
    return {
        'distinct_tied_timestamp_blocks': len(times),
        'membership_intervals_checked': max(0, len(times)-1),
        'feasible_membership_intervals': len(feasible_intervals),
        'possible': bool(feasible_intervals),
        'lower_exclusive': feasible_intervals[0][0] if feasible_intervals else None,
        'upper_inclusive': feasible_intervals[-1][1] if feasible_intervals else None,
        'totals': dict(sorted(totals.items())),
        'minimum_fit_per_class': 2, 'minimum_test_per_class': 1,
        'ties_preserved': True, 'clock_or_duration_validity_claim': False,
    }


def direct_counts(blocks, cutoff):
    fit, test = Counter(), Counter()
    labels = set()
    for timestamp, counts in blocks.items():
        (fit if timestamp < cutoff else test).update(counts)
        labels.update(counts)
    return {label: {'fit': fit[label], 'test': test[label]} for label in sorted(labels)}


def read_native(spec, label, formats):
    totals, dates, schemas, receipts = Counter(), defaultdict(Counter), [], []
    blocks = defaultdict(Counter)
    header = None
    for source in spec:
        path = Path(source['path'])
        before = sha(path)
        if before != source['sha256']:
            raise ValueError('Source hash differs from prior evidence: ' + str(path))
        rows, missing_header = 0, False
        with path.open('r', encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream)
            first = next(reader)
            candidate = [cell.strip() for cell in first]
            if label in candidate and 'Timestamp' in candidate:
                header = candidate
                records = reader
            elif header is not None and len(first) == len(header):
                missing_header = True
                records = itertools.chain([first], reader)
            else:
                raise ValueError('Unqualified source schema')
            label_index, time_index = header.index(label), header.index('Timestamp')
            schemas.append(header.copy())
            for record in records:
                if not record:
                    continue
                if len(record) != len(header):
                    raise ValueError('CSV row width mismatch')
                native = record[label_index].strip()
                if not native:
                    raise ValueError('Empty native label')
                if native == 'BENIGN':
                    native = 'Benign'
                timestamp = parse_recorded(record[time_index].strip(), tuple(formats))
                totals[native] += 1
                dates[timestamp.date().isoformat()][native] += 1
                blocks[timestamp][native] += 1
                rows += 1
        after = sha(path)
        if after != before:
            raise ValueError('Input changed while it was read')
        receipts.append({'path': str(path), 'sha256': before, 'bytes': path.stat().st_size,
                         'rows': rows, 'headerless_first_row_preserved': missing_header})
    return {'rows': sum(totals.values()), 'native_counts': dict(sorted(totals.items())),
            'date_counts': {key: dict(sorted(value.items())) for key, value in sorted(dates.items())},
            'columns': schemas[0], 'schemas_equal': all(value == schemas[0] for value in schemas),
            'source_receipts': receipts}, blocks


def verify_cutoff(name, blocks, prior):
    sweep = sweep_support(blocks)
    matched = sweep['possible'] == prior['start_only_count_support_possible']
    if sweep['possible']:
        matched = matched and to_ns(sweep['lower_exclusive']) == prior['lower_exclusive']
        matched = matched and to_ns(sweep['upper_inclusive']) == prior['upper_inclusive']
    boundary_counts = {}
    for key in ['lower_exclusive', 'upper_inclusive']:
        timestamp = from_ns(prior[key])
        for suffix, cutoff in [('at_bound', timestamp), ('one_microsecond_after', timestamp + timedelta(microseconds=1))]:
            boundary_counts[key + '_' + suffix] = {
                'recorded_cutoff': cutoff.isoformat(), 'counts': direct_counts(blocks, cutoff)}
    proof = None
    if name == 'DAPT2020':
        recon_latest = max(t for t, counts in blocks.items() if counts['Reconnaissance'])
        exfil_earliest = min(t for t, counts in blocks.items() if counts['Data Exfiltration'])
        proof = {
            'latest_reconnaissance_start': recon_latest.isoformat(),
            'earliest_exfiltration_start': exfil_earliest.isoformat(),
            'every_reconnaissance_row_precedes_every_exfiltration_row': recon_latest < exfil_earliest,
            'logical_implication': 'A cutoff retaining any later reconnaissance row has no earlier exfiltration row. A cutoff after exfiltration fitting rows leaves no later reconnaissance row.',
        }
        matched = matched and proof['every_reconnaissance_row_precedes_every_exfiltration_row']
    for key in ['lower_exclusive', 'upper_inclusive']:
        sweep[key] = sweep[key].isoformat() if sweep[key] is not None else None
    return {'matches_registered_count_support_claim': matched,
            'direct_all_boundary_sweep': sweep, 'direct_counts_at_registered_bounds': boundary_counts,
            'temporal_separation_proof': proof, 'previous_data_exposure': True,
            'cutoff_chosen_for_model_evaluation': False, 'all_original_rows_retained': True}


def verify_source_commit(commit):
    result = {}
    for path in CODE_FILES:
        relative = path.relative_to(REPO).as_posix()
        frozen = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=REPO)
        if frozen != path.read_bytes():
            raise ValueError('Independent verifier differs from frozen commit')
        result[relative] = hashlib.sha256(frozen).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    source = verify_source_commit(args.commit)
    target = HERE / 'VERIFICATION.json'
    if target.exists():
        raise FileExistsError('Refusing to overwrite verification receipt')
    qualification_path = D1 / 'QUALIFICATION.json'
    cutoff_path = D1 / 'SUPPORT_CUTOFF_AUDIT.json'
    q, c = json.loads(qualification_path.read_text()), json.loads(cutoff_path.read_text())
    report = {'schema_version': 1, 'started_utc': utc(), 'verification_commit': args.commit,
              'verifier_sha256': source, 'model_fits': 0, 'aws_used': False,
              'independence': 'Different CSV parser and complete tied-time count sweep; imports no prior audit algorithms. Same agent team and same previously exposed source files, not an external blinded replication.',
              'existing_evidence_sha256': {str(path.relative_to(REPO)): sha(path) for path in [qualification_path, cutoff_path]},
              'datasets': {}}
    checks = []
    for name in ['SCVIC-APT-2021', 'DAPT2020', 'DSRL-APT-2023']:
        prior = q['datasets'][name]['measured']
        measured, blocks = read_native(prior['inputs'], prior['label_column'], prior['timestamp']['formats'])
        measured['native_counts_match_prior'] = measured['native_counts'] == prior['stage_counts']
        measured['row_total_matches_prior'] = measured['rows'] == prior['rows']
        checks += [measured['native_counts_match_prior'], measured['row_total_matches_prior'], measured['schemas_equal']]
        if name in c['datasets']:
            measured['cutoff_verification'] = verify_cutoff(name, blocks, c['datasets'][name])
            checks.append(measured['cutoff_verification']['matches_registered_count_support_claim'])
        else:
            measured['temporal_support_sweep_performed'] = False
            measured['reason'] = 'Generated attack dates do not qualify physical campaign chronology.'
        report['datasets'][name] = measured
        print(json.dumps({'dataset': name, 'rows': measured['rows'], 'counts_match': measured['native_counts_match_prior']}), flush=True)
    dsrl_root = Path(q['datasets']['DSRL-APT-2023']['measured']['inputs'][0]['path']).parent
    acquired = json.loads((dsrl_root / 'ACQUISITION.json').read_text())
    license_checks = {Path(item['path']).name: sha(Path(item['path'])) == item['sha256'] for item in acquired['files']}
    report['dsrl_pinned_release'] = {'source_commit': acquired['source_commit'],
                                    'actual_artifact_hash_matches': license_checks,
                                    'license_header_is_mit': (dsrl_root / 'LICENSE').read_text().startswith('MIT License'),
                                    'claim_scope': 'MIT file in pinned author repository; not a new independent recording. Paper source review is documented separately.'}
    checks += list(license_checks.values()) + [report['dsrl_pinned_release']['license_header_is_mit']]
    report['s_dapt_2026'] = {'acquired_rows': None, 'raw_data_verification_performed': False,
                            'status': 'No source bytes qualified; release status reviewed in SOURCE_REVIEW.json. No paper counts converted into observed counts.'}
    report['all_registered_verification_checks_passed'] = all(checks)
    report['status'] = 'COMPLETED_MEASUREMENT_VERIFICATION' if all(checks) else 'DISCREPANCY_REQUIRES_REVIEW'
    report['completed_utc'] = utc()
    target.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'verification_checks': len(checks), 'output': str(target)}))
    return 0 if all(checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
