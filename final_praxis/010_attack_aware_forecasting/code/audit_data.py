"""Read only designated HAI training1 and NAB reproduction file; no heldout access."""
import argparse
import csv
import datetime
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    path = args.cache / 'hai/hai-21.03/train1.csv.gz'
    b = path.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    assert blob == '2940eeeb2018c68fc01586da77986a5771b12585' and b[:2] == b'\x1f\x8b'
    df = pd.read_csv(path)
    times = pd.to_datetime(df['time'])
    result = {'hai': {'file': 'hai-21.03/train1.csv.gz', 'compressed_sha256': hashlib.sha256(b).hexdigest(), 'compressed_git_blob': blob, 'actual_gzip_not_lfs_pointer': True, 'rows': len(df), 'columns': df.columns.tolist(), 'timestamp_min': str(times.min()), 'timestamp_max': str(times.max()), 'strictly_increasing': bool((times.diff().dropna().dt.total_seconds() > 0).all()), 'interval_seconds_counts': {str(k): int(v) for k, v in times.diff().dropna().dt.total_seconds().value_counts().items()}, 'numeric_values_finite': bool(np.isfinite(df.drop(columns='time').to_numpy(dtype=float)).all()), 'labels_summary': {c: {str(k): int(v) for k, v in df[c].value_counts().items()} for c in df.columns if 'attack' in c.lower()}, 'heldout_files_opened': []}}
    path = args.cache / 'tsbad/Datasets/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv'
    b = path.read_bytes(); sha = hashlib.sha256(b).hexdigest()
    assert sha == 'e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584'
    nab = pd.read_csv(path)
    result['nab'] = {'file': path.name, 'sha256': sha, 'rows': len(nab), 'columns': nab.columns.tolist(), 'missing_cells': int(nab.isna().sum().sum()), 'train_boundary': 1007, 'numeric_finite': bool(np.isfinite(nab.to_numpy(dtype=float)).all()), 'declared_role': 'entire series is development reproduction; not cybersecurity attack evidence'}
    result['all_accessibility_checks_pass'] = result['hai']['strictly_increasing'] and result['hai']['numeric_values_finite'] and result['nab']['numeric_finite']
    result['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_pass': result['all_accessibility_checks_pass'], 'hai_rows': len(df), 'nab_rows': len(nab)}))


if __name__ == '__main__':
    main()
