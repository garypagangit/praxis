"""Repeat postrun integrity mutation controls using temporary artifact copies.

No model/cloud calls. The original artifacts and worker remain read-only.
These are negative integrity controls on completed artifacts, not experiments.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from audit_010_extended_postrun import audit_original25, read_rows, sha


def check_mutations(source, cloud):
    checks = []
    with tempfile.TemporaryDirectory(prefix='praxis010_review_') as temp:
        temporary = Path(temp)
        try:
            audit_original25(source, temporary)
            missing_failed = False
        except FileNotFoundError:
            missing_failed = True
        checks.append({'control': 'missing_required_saved_receipt_refuses_pass', 'passed': missing_failed})
        shutil.copytree(cloud / 'original25', temporary / 'original25')
        shutil.copy2(cloud / 'ORIGINAL25_EXIT.txt', temporary / 'ORIGINAL25_EXIT.txt')
        receipt_path = temporary / 'original25' / 'QUALIFICATION_RECEIPT.json'
        receipt = json.loads(receipt_path.read_text())
        receipt['implementation_gate_pass'] = False
        receipt_path.write_text(json.dumps(receipt))
        _, results = audit_original25(source, temporary)
        checks.append({'control': 'false_reported_gate_refuses_pass', 'passed': any(
            not c['passed'] and c['check'] == 'original25:reported_gate_fields' for c in results)})
        receipt['implementation_gate_pass'] = True
        rows_path = temporary / 'original25' / 'interventions.jsonl'
        rows = read_rows(rows_path)
        selected = next(r for r in rows if r['policy'] == 'alarm_only_blend' and r['action'] == 'blend')
        prediction = np.asarray(selected['prediction'], dtype=np.float64)
        observation = np.asarray(selected['observation'], dtype=np.float64)
        selected['admitted'] = (.8 * prediction + .2 * observation).tolist()
        rows_path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        receipt['artifacts']['interventions.jsonl'] = sha(rows_path)
        receipt_path.write_text(json.dumps(receipt))
        _, results = audit_original25(source, temporary)
        checks.append({'control': 'rehash_consistent_wrong_float64_admission_refuses_pass', 'passed': any(
            not c['passed'] and c['check'].startswith('original25:step:') for c in results)})
    return {'status': 'PASS' if all(c['passed'] for c in checks) else 'FAIL',
            'checked_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'checks': checks,
            'source_sha256': sha(__file__),
            'auditor_sha256': sha(Path(__file__).with_name('audit_010_extended_postrun.py')),
            'original25_receipt_sha256': sha(cloud / 'original25/QUALIFICATION_RECEIPT.json'),
            'controls_created_after_model_execution': True,
            'model_calls': 0, 'cloud_calls': 0, 'immutable_sources_or_original_results_edited': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cloud-results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = check_mutations(args.source, args.cloud_results)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'controls': len(report['checks'])}))
    raise SystemExit(report['status'] != 'PASS')


if __name__ == '__main__':
    main()
