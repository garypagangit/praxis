"""Replay the separately authored audit from the self-contained public package.

Temporary layout only; copies existing receipts/rows, reads the pinned external
NAB example, and runs reviewer NumPy/SciPy arithmetic. No model or network calls.
"""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    completed = ROOT / 'completed_qualification'
    reviewers = completed / 'independent_review'
    sys.path.insert(0, str(reviewers))
    reviewer = importlib.import_module('audit_010_extended_postrun')
    with tempfile.TemporaryDirectory(prefix='INDEPENDENT_010_REPLAY_', dir=args.cache) as temporary:
        layout = Path(temporary)
        for mode in ['original25', 'new3', 'calibration']:
            destination = layout / mode; destination.mkdir()
            receipt = json.loads((completed / mode / 'QUALIFICATION_RECEIPT.json').read_text())
            for name in ['QUALIFICATION_RECEIPT.json', *receipt['artifacts']]:
                shutil.copyfile(completed / mode / name, destination / name)
        for name in ['ASSET_RECEIPT_MODELS.json', 'RUNTIME_CONTROLS_CLOUD.json', 'DATA_ACCESSIBILITY.json', 'PIP_FREEZE.txt', 'SETUP_EXIT.txt', 'NEW3_EXIT.txt', 'ORIGINAL25_EXIT.txt', 'CALIBRATION_EXIT.txt']:
            shutil.copyfile(completed / 'setup' / name, layout / name)
        report = reviewer.audit(ROOT, layout, reviewers / 'INDEPENDENT_010_REVIEW.json', ['new3', 'original25', 'calibration'], args.cache / 'tsbad/Datasets/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, indent=2, allow_nan=False) + '\n').encode())
    print(json.dumps({k: report[k] for k in ['status', 'checks_total', 'checks_passed', 'checks_failed']}))
    assert report['status'] == 'PASS_ALL_RELEASED_GPU_MODES' and report['checks_failed'] == 0


if __name__ == '__main__':
    main()
