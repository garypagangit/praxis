"""Hash-check public HAI files and inspect timestamps only; never parse labels/signals."""
import argparse
import concurrent.futures
import csv
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '2a814cebc9a66b06c9e5cd545e2d72e65d383737'


def inspect(item, cache):
    path = cache / 'hai' / item['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f'https://raw.githubusercontent.com/icsdataset/hai/{REVISION}/{item["path"]}'
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.partial')
        urllib.request.urlretrieve(url, temporary); temporary.replace(path)
    blob = hashlib.sha1(); blob.update(b'blob ' + str(path.stat().st_size).encode() + b'\0')
    content_sha = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(2**20): blob.update(chunk); content_sha.update(chunk)
    assert blob.hexdigest() == item['sha'], item['path']
    previous = first = last = None
    rows, gaps, nonincreasing = 0, 0, 0
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        header = next(csv.reader([next(f)]))
        assert header[0] == 'time'
        for line in f:
            # The remaining fields are deliberately never parsed or summarized.
            timestamp = datetime.datetime.fromisoformat(line.partition(',')[0].strip().strip('"'))
            if first is None: first = timestamp
            if previous is not None:
                seconds = (timestamp - previous).total_seconds()
                gaps += seconds != 1
                nonincreasing += seconds <= 0
            previous = last = timestamp; rows += 1
    return {'file': item['path'], 'upstream_url': url, 'compressed_sha256': content_sha.hexdigest(), 'git_blob_verified': True, 'compressed_bytes': path.stat().st_size, 'rows': rows, 'column_count': len(header), 'timestamp_start': str(first), 'timestamp_end': str(last), 'non_one_second_intervals': gaps, 'non_increasing_intervals': nonincreasing, 'parsed_value_columns': ['time'], 'sensor_values_parsed': False, 'attack_labels_parsed': False, 'efficacy_computed': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    inventory = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())['hai_file_inventory']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda x: inspect(x, args.cache), inventory))
    chronological = sorted(rows, key=lambda r: (r['timestamp_start'], r['timestamp_end'], r['file']))
    train = [r for r in rows if '/train' in r['file']]; test = [r for r in rows if '/test' in r['file']]
    result = {'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'source_revision': REVISION, 'inspection_scope': 'Timestamp metadata only across all8 public files; no signal/label summaries or model efficacy.', 'files': rows, 'chronological_file_order': [r['file'] for r in chronological], 'all_training_before_all_test': max(r['timestamp_end'] for r in train) < min(r['timestamp_start'] for r in test), 'all8_blob_identities_verified': len(rows) == 8 and all(r['git_blob_verified'] for r in rows), 'all_files_strict_one_second_continuity': all(r['non_one_second_intervals'] == 0 and r['non_increasing_intervals'] == 0 for r in rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['chronological_file_order', 'all_training_before_all_test', 'all8_blob_identities_verified', 'all_files_strict_one_second_continuity']}))


if __name__ == '__main__':
    main()
