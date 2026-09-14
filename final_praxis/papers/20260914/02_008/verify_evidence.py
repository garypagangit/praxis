"""Verify the public 008 evidence in this repository; optionally replay statistics."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2] / '008_independent_evidence_audit' / 'code_study'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reproduce', action='store_true')
    parser.add_argument('--output', type=Path, default=HERE / 'EVIDENCE_VERIFICATION.json')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
    checked = []
    for item in manifest['files']:
        path = (HERE / item['path']).resolve()
        if not path.is_relative_to(CORE):
            raise ValueError('Evidence path outside canonical 008 study')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        checked.append({'path': item['path'], 'pass': actual == item['sha256']})
    result = {'status': 'PASS' if all(x['pass'] for x in checked) else 'FAIL',
              'files_checked': len(checked), 'checks': checked, 'model_calls': 0,
              'candidate_programs_executed': 0, 'statistics_replayed_this_run': False}
    if result['status'] != 'PASS':
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        raise SystemExit('Evidence hashes differ')
    if args.reproduce:
        for version in ('original_v1', 'schema_extension_v2'):
            subprocess.run([sys.executable, str(CORE / 'paper_package/reproduce_statistics.py'),
                            '--package', str(CORE / 'completed_models' / version),
                            '--output', str(HERE / ('REPRODUCED_' + version + '.json'))],
                           cwd=CORE, check=True)
        result['statistics_replayed_this_run'] = True
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'files_checked', 'statistics_replayed_this_run')}))

if __name__ == '__main__':
    main()
