"""Reproduce published statistics from compressed Git artifacts, without AWS calls."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE))
import analysis
import offline_analysis
import numpy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in gzip.decompress(path.read_bytes()).decode('utf-8').splitlines() if line.strip()]


def reproduce(package, output):
    manifest = json.loads((package / 'PACKAGE_RECEIPT.json').read_text(encoding='utf-8'))
    for item in manifest['artifacts']:
        path = package / item['file']
        if not path.resolve().is_relative_to(package.resolve()) or sha(path) != item['sha256']:
            raise ValueError('Published package artifact mismatch: ' + item['file'])
        if path.suffix == '.gz' and hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() != item['uncompressed_source_sha256']:
            raise ValueError('Compressed source-byte mismatch: ' + item['file'])
    freeze = json.loads((CORE / 'MODEL_SOURCE_FREEZE.json').read_text(encoding='utf-8'))
    for name, expected in freeze['files'].items():
        if sha(CORE / name) != expected:
            raise ValueError('Frozen source mismatch: ' + name)
    model = json.loads((package / 'MODEL_RESULTS.json').read_text(encoding='utf-8'))
    acquisition = json.loads((package / 'ACQUISITION_RESULTS.json').read_text(encoding='utf-8'))
    regenerated_model = analysis.analyze(read_rows(package / 'DECISIONS.jsonl.gz'),
        reviewers=model['configuration']['reviewers'], expected_assignments=read_rows(package / 'EXPECTED_DECISIONS.jsonl.gz'))
    regenerated_acquisition = offline_analysis.analyze(read_rows(package / 'OFFLINE.jsonl.gz'),
        expected_assignments=read_rows(package / 'EXPECTED_OFFLINE.jsonl.gz'))
    expected_model = {key: value for key, value in model.items() if key != 'provenance'}
    expected_acquisition = {key: value for key, value in acquisition.items() if key != 'provenance'}
    result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'version': manifest['version'],
        'package_receipt_sha256': sha(package / 'PACKAGE_RECEIPT.json'),
        'source_freeze_sha256': sha(CORE / 'MODEL_SOURCE_FREEZE.json'),
        'reproducer_sha256': sha(Path(__file__)), 'python': sys.version, 'numpy': numpy.__version__,
        'model_all_statistics_exact': regenerated_model == expected_model,
        'acquisition_all_statistics_exact': regenerated_acquisition == expected_acquisition,
        'bootstrap_draws_per_registered_analysis': model['configuration']['bootstrap_samples'],
        'comparison_excludes_only_top_level_provenance': True,
        'api_calls': 0, 'candidate_programs_executed': 0,
        'interpretation': 'Exact deterministic reexecution of the frozen implementation; independent audit and scientific validity are separate checks.'}
    result['pass'] = result['model_all_statistics_exact'] and result['acquisition_all_statistics_exact']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(result, indent=2))
    if not result['pass']:
        raise SystemExit(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reproduce(args.package.resolve(), args.output.resolve())
