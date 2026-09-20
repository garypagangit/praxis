"""Acquire covered, rule-unmatched sources separately from frozen pilot v1.

Run as ``python -m experiments.apt_benchmark.acquire_background --source-root
<previous acquire_ait output> --output <new directory>``. An optional
``--coverage-cache`` can reuse verified processing members from a prior probe.
Only data bytes are read; archived scripts and log contents are never executed.
The fixed record and file inventory reproduce the 96-file expansion. Missing
label files mean author-rule nonmatch, never independent benign adjudication.
Completed acquisition directories are immutable; choose a new output to repeat.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re
import zlib

import yaml

from . import acquire_ait as mod

LABEL_BASIS = 'AUTHOR_RULE_NONMATCH_FROM_COVERED_FILE'
PROOF_NAMES = ('processing/config/logs.yaml', 'processing/logstash/log/file-completed.log',
               'processing/logstash/conf.d/0000_pre_process.conf')
EXPECTED_COUNTS = dict(zip(mod.SCENARIOS, (9, 11, 12, 10, 15, 12, 15, 12)))
SUPPORTED = {'audit/audit.log*': 'audit', 'auth.log*': 'auth',
             'apache2/*access*.log*': 'apache_access', 'apache2/*error*.log*': 'apache_error'}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def source_type(name):
    if '/audit/' in name:
        return 'audit'
    if name.rsplit('/', 1)[-1].startswith('auth.log'):
        return 'auth'
    return 'apache_access' if 'access' in name else 'apache_error'


def counts(path, kind, start, end):
    counters = Counter()
    earliest = latest = None
    with path.open('rb') as handle:
        for raw in handle:
            counters['source_lines'] += 1
            line = raw.decode('utf-8', errors='replace')
            if '\ufffd' in line:
                counters['utf8_replacement_lines'] += 1
            stamp = None
            if kind == 'apache_access':
                m = re.search(r'\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]', line)
                if m:
                    try:
                        stamp = datetime.strptime(m.group(1), '%d/%b/%Y:%H:%M:%S %z').timestamp()
                        counters['explicit_offset_timestamp'] += 1
                    except ValueError:
                        pass
            elif kind == 'audit':
                m = re.search(r'audit\((\d+(?:\.\d+)?):', line)
                if m:
                    stamp = float(m.group(1))
                    counters['epoch_timestamp'] += 1
            elif kind == 'auth':
                if re.match(r'[A-Za-z]{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}', line):
                    counters['year_and_timezone_omitted'] += 1
                else:
                    counters['unrecognized_timestamp'] += 1
            elif kind == 'apache_error':
                if re.match(r'\[[A-Za-z]{3} [A-Za-z]{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}(?:\.\d+)? \d{4}\]', line):
                    counters['timezone_omitted'] += 1
                else:
                    counters['unrecognized_timestamp'] += 1
            if stamp is not None:
                counters['timestamp_with_explicit_time_basis'] += 1
                counters['within_archived_interval_inclusive' if start <= stamp <= end else 'outside_archived_interval'] += 1
                earliest = stamp if earliest is None else min(earliest, stamp)
                latest = stamp if latest is None else max(latest, stamp)
            elif kind in ('apache_access', 'audit'):
                counters['unrecognized_timestamp'] += 1
    result = dict(counters)
    result['earliest_explicit_utc'] = datetime.fromtimestamp(earliest, timezone.utc).isoformat() if earliest is not None else None
    result['latest_explicit_utc'] = datetime.fromtimestamp(latest, timezone.utc).isoformat() if latest is not None else None
    return result


def scenario(run, source_root, output, coverage_cache, metadata, reader):
    root = output / run
    original = source_root / run
    central = json.loads((original / 'CENTRAL_DIRECTORY.json').read_text(encoding='utf-8'))
    entries = {e['name']: e for e in central}
    item = next(f for f in metadata['files'] if f['key'] == run + '_no-pcaps.zip')
    url = f'https://zenodo.org/records/{mod.RECORD}/files/{item["key"]}?download=1'
    initial = json.loads((original / 'ACQUISITION.json').read_text(encoding='utf-8'))
    if (initial.get('record') != mod.RECORD or initial.get('source_url') != url
            or initial.get('publisher_archive_checksum') != item['checksum']
            or initial.get('archive_bytes') != item['size']):
        raise ValueError('Prior acquisition does not bind to pinned archive')
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / 'ACQUISITION.json'
    old = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
    cached = {m['name']: m for m in old.get('members', [])}
    proof_dir = coverage_cache / run if coverage_cache else root
    proof_receipt = proof_dir / 'ACQUISITION.json'
    proof = json.loads(proof_receipt.read_text(encoding='utf-8')) if proof_receipt.exists() else {}
    if proof and proof.get('source_url') != url:
        raise ValueError('Coverage proof URL mismatch')
    cached_proofs = {m['name']: m for m in proof.get('coverage_proof_members', proof.get('members', []))}
    proof_members = []
    for name in PROOF_NAMES:
        member = cached_proofs.get(name)
        if member is None or not (proof_dir / name).is_file():
            member = mod.fetch_member(reader, url, item['size'], entries[name], root)
            proof_source = root / name
        else:
            proof_source = proof_dir / name
        raw = proof_source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != member['sha256'] or zlib.crc32(raw) & 0xffffffff != member['crc32']:
            raise ValueError('Local coverage proof changed')
        if any(member[k] != entries[member['name']][k] for k in ('bytes', 'crc32', 'compressed_bytes', 'local_header_offset')):
            raise ValueError('Coverage proof directory mismatch')
        destination = root / member['name']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != raw:
            raise ValueError('Refuse differing existing proof')
        if not destination.exists():
            destination.write_bytes(raw)
        proof_members.append({**member, 'reused_verified_proof_member': True})
    conf = (root / 'processing/logstash/conf.d/0000_pre_process.conf').read_text(encoding='utf-8')
    start = float(re.search(r'@@observe_start = LogStash::Timestamp.at\((\d+(?:\.\d+)?)\)', conf).group(1))
    end = float(re.search(r'@@observe_end = LogStash::Timestamp.at\((\d+(?:\.\d+)?)\)', conf).group(1))
    if not start < end:
        raise ValueError('Invalid archived observation interval')
    completed = (root / 'processing/logstash/log/file-completed.log').read_text(encoding='utf-8').splitlines()
    config = yaml.safe_load((root / 'processing/config/logs.yaml').read_text(encoding='utf-8'))
    rules = config['hosts']['intranet_server'] + config['groups']['servers']
    configured = {r['path']: r['type'] for r in rules}
    if any(configured.get(pattern) != kind for pattern, kind in SUPPORTED.items()):
        raise ValueError('Expected archived source glob/type mapping absent')
    candidates = []
    for entry in central:
        name = entry['name']
        prefix = 'gather/intranet_server/logs/'
        if (not name.startswith(prefix) or not entry['bytes'] or name.endswith('/')
                or name.replace('gather/', 'labels/', 1) in entries):
            continue
        matches = [pattern for pattern in SUPPORTED if fnmatchcase(name[len(prefix):], pattern)]
        if not matches:
            continue
        if len(matches) != 1 or not any(line.endswith('/' + name) for line in completed):
            raise ValueError('Ambiguous source glob or missing completed-ingestion proof')
        candidates.append({'source': name, 'configured_source_glob': matches[0]})
    if len(candidates) != EXPECTED_COUNTS[run]:
        raise ValueError('Pinned expansion inventory count changed')
    members = []
    receipt = {'scenario': run, 'record': mod.RECORD, 'source_url': url, 'archive_bytes': item['size'],
               'publisher_archive_checksum': item['checksum'], 'whole_archive_checksum_verified': False,
               'label_basis': LABEL_BASIS, 'purpose': 'Separate expansion qualification; never frozen pilot_v1 input',
               'observation_epoch': {'start': start, 'end': end},
               'observation_utc': {'start': datetime.fromtimestamp(start, timezone.utc).isoformat(),
                                   'end': datetime.fromtimestamp(end, timezone.utc).isoformat()},
               'original_central_directory_json_sha256': hashlib.sha256((original / 'CENTRAL_DIRECTORY.json').read_bytes()).hexdigest(),
               'coverage_proof_members': proof_members, 'members': members, 'complete': False,
               'limitations': ['Rule nonmatch is not independently confirmed benign',
                              'Ingestion completion alone does not prove parser success or complete attack-label semantics',
                              'Unknown-time lines need explicit treatment before causal evaluation']}
    for candidate in sorted(candidates, key=lambda x: x['source']):
        name = candidate['source']
        if name.replace('gather/', 'labels/', 1) in entries:
            raise ValueError('Candidate has an annotation file')
        matching_lines = [i + 1 for i, line in enumerate(completed) if line.endswith('/' + name)]
        if not matching_lines:
            raise ValueError('No completed-ingestion path proof')
        entry = entries[name]
        prior = cached.get(name)
        path = root / name
        if (old.get('source_url') == url and old.get('publisher_archive_checksum') == item['checksum']
                and prior and prior.get('crc32_verified') and path.is_file()
                and all(prior.get(k) == entry[k] for k in ('bytes', 'crc32', 'compressed_bytes', 'local_header_offset'))
                and hashlib.sha256(path.read_bytes()).hexdigest() == prior['sha256']):
            member = {**prior, 'reused_verified_member': True}
        else:
            member = mod.fetch_member(reader, url, item['size'], entry, root)
        kind = source_type(name)
        member.update(source_type=kind, annotation_file_present=False, label_basis=LABEL_BASIS,
                      configured_source_glob=candidate['configured_source_glob'],
                      ingestion_completed_proof={'member': 'processing/logstash/log/file-completed.log', 'original_one_based_lines': matching_lines},
                      line_counts=counts(path, kind, start, end))
        members.append(member)
        write_json(receipt_path, receipt)
    receipt['complete'] = True
    totals = Counter()
    by_type = {}
    for member in members:
        for k, value in member['line_counts'].items():
            if type(value) is int:
                totals[k] += value
        kind = member['source_type']
        by_type.setdefault(kind, {'files': 0, 'source_lines': 0})
        by_type[kind]['files'] += 1
        by_type[kind]['source_lines'] += member['line_counts']['source_lines']
    receipt['line_totals'] = dict(totals)
    receipt['source_type_totals'] = by_type
    write_json(receipt_path, receipt)
    print(json.dumps({'run': run, 'complete': True, 'members': len(members), 'counts': dict(totals)}), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--coverage-cache', type=Path)
    parser.add_argument('--max-transfer-mib', type=int, default=8)
    args = parser.parse_args()
    if args.max_transfer_mib <= 0 or args.source_root.resolve() == args.output.resolve():
        raise ValueError('Positive transfer limit and separate output root required')
    if (args.source_root.resolve() in args.output.resolve().parents
            or args.output.resolve() in args.source_root.resolve().parents):
        raise ValueError('Expansion must remain outside original acquisition root')
    metadata = json.loads((args.source_root / 'ZENODO_METADATA.json').read_text(encoding='utf-8'))
    if metadata['id'] != mod.RECORD or metadata['metadata']['license']['id'] != 'cc-by-nc-sa-4.0':
        raise ValueError('Pinned record/license mismatch')
    reader = mod.RangeReader(args.max_transfer_mib * 1024 * 1024)
    args.output.mkdir(parents=True, exist_ok=True)
    prior_receipt_path = args.output / 'ACQUISITION.json'
    prior_receipt = json.loads(prior_receipt_path.read_text(encoding='utf-8')) if prior_receipt_path.exists() else {}
    if prior_receipt:
        raise ValueError('Completed acquisition output is immutable; choose a new output directory')
    write_json(args.output / 'ZENODO_METADATA.json', metadata)
    with ThreadPoolExecutor(max_workers=4) as pool:
        scenarios = list(pool.map(lambda run: scenario(run, args.source_root, args.output,
                                                       args.coverage_cache, metadata, reader), mod.SCENARIOS))
    receipt = {'record': mod.RECORD, 'license': 'CC-BY-NC-SA-4.0',
               'created_utc': datetime.now(timezone.utc).isoformat(), 'label_basis': LABEL_BASIS,
               'requested_range_bytes_this_invocation': reader.transferred,
               'acquisition_helper_sha256': hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest(),
               'this_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'models_run': False, 'pilot_v1_modified': False, 'scenarios': scenarios}
    write_json(args.output / 'ACQUISITION.json', receipt)
    print(json.dumps({'complete': True, 'scenarios': len(scenarios), 'members': sum(len(s['members']) for s in scenarios),
                      'source_lines': sum(s['line_totals']['source_lines'] for s in scenarios),
                      'range_bytes': reader.transferred}), flush=True)


if __name__ == '__main__':
    main()
