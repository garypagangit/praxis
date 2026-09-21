"""Read-only E0 CSV qualification; no models, relabeling, or data publication."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(paths, label):
    frames = []
    receipts = []
    reference_header = None
    for raw in paths:
        path = Path(raw)
        frame = pd.read_csv(path, low_memory=False)
        frame.columns = frame.columns.str.strip()
        headerless = label not in frame.columns
        if headerless:
            if reference_header is None or len(frame.columns) != len(reference_header):
                raise ValueError(f'Cannot qualify headerless input {path}')
            frame = pd.read_csv(path, names=reference_header, header=None, low_memory=False)
        else:
            reference_header = list(frame.columns)
        # This is spelling normalization, not a change from binary to stage labels.
        frame[label] = frame[label].replace({'BENIGN': 'Benign'})
        frame["__source_file"] = path.name
        frames.append(frame)
        receipts.append({"path": str(path), "bytes": path.stat().st_size,
                         "sha256": sha256(path), "rows": len(frame),
                         "headerless_repaired_in_memory": headerless})
    df = pd.concat(frames, ignore_index=True)
    counts = df[label].astype(str).str.strip().value_counts().sort_index().to_dict()
    out = {"inputs": receipts, "rows": len(df), "columns": list(df.columns[:-1]),
           "label_column": label, "stage_counts": counts,
           "source_by_stage": pd.crosstab(df['__source_file'], df[label]).to_dict(orient="index"),
           "missing_labels": int(df[label].isna().sum())}
    exclude = {label, 'Label', 'Stage', 'Activity', 'Flow ID', 'Src IP', 'Dst IP',
               'Src Port', 'Dst Port', 'Timestamp', 'source_file', 'network_type',
               'day', '__source_file', 'date_dow_name', 'hour', 'min',
               'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min'}
    features = [c for c in df.columns if c not in exclude and not c.startswith('Unnamed')]
    # Deliberately conservative exact-duplicate audit over the intended feature view.
    feature_hash = pd.util.hash_pandas_object(df[features], index=False)
    groups = pd.DataFrame({'hash': feature_hash, 'label': df[label]})
    unique = groups.drop_duplicates()
    out['candidate_feature_columns'] = features
    out['excluded_idle_reason'] = 'SCVIC idle summaries contain epoch-scale values; exclude all four a priori from shared pilot feature surface.'
    numeric = df[features].apply(pd.to_numeric, errors='coerce')
    out['nonfinite_feature_cells'] = int((~np.isfinite(numeric.to_numpy(dtype=float))).sum())
    out['nonfinite_feature_rows'] = int((~np.isfinite(numeric.to_numpy(dtype=float))).any(axis=1).sum())
    out['idle_epoch_scale_counts_gt_1e12'] = {c: int((pd.to_numeric(df[c], errors='coerce').abs()>1e12).sum()) for c in ['Idle Mean','Idle Std','Idle Max','Idle Min'] if c in df}
    out['duplicate_feature_rows'] = int(feature_hash.duplicated().sum())
    out['feature_groups_with_conflicting_labels'] = int((unique.groupby('hash').size() > 1).sum())
    out['unique_feature_groups_by_stage'] = unique.groupby('label').size().to_dict()
    out['budget_feasibility_counts_only'] = {str(b): all(n >= b for n in out['unique_feature_groups_by_stage'].values()) for b in [32,64,128,256,512,1024]}
    out['budget_feasibility_caveat'] = 'Counts only, before independent development/calibration/test reserves or incident grouping. Not split qualification.'
    if 'Timestamp' in df:
        # Source DAPT strings are day-first; SCVIC strings use ISO year-first.
        formats = ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M'] if label == 'Label' else ['%d/%m/%Y %I:%M:%S %p']
        ts = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns]')
        for fmt in formats:
            remaining = ts.isna()
            ts.loc[remaining] = pd.to_datetime(df.loc[remaining,'Timestamp'], format=fmt, errors='coerce')
        df['__date'] = ts.dt.strftime('%Y-%m-%d').fillna('UNPARSED')
        out['timestamp'] = {'formats': formats, 'unparsed': int(ts.isna().sum()),
                            'min': str(ts.min()), 'max': str(ts.max()),
                            'dates': int(df['__date'].nunique())}
        out['date_by_stage'] = pd.crosstab(df['__date'], df[label]).to_dict(orient='index')
        label_ranges = {}
        for name, rows in df.groupby(label):
            take = ts.loc[rows.index]
            label_ranges[str(name)] = {'first': str(take.min()), 'last': str(take.max()),
                                      'dates': int(rows['__date'].nunique())}
        out['stage_time_ranges'] = label_ranges
        # Diagnostics only: proportions chosen before seeing outcomes; no train/test file generated.
        valid = ts.notna()
        order = df.loc[valid].assign(__t=ts[valid]).sort_values('__t',kind='stable').index.to_numpy()
        n = len(order)
        splits = {'fit':order[:int(.6*n)], 'development':order[int(.6*n):int(.75*n)],
                  'calibration':order[int(.75*n):int(.85*n)], 'test':order[int(.85*n):]}
        out['chronological_60_15_10_15_diagnostic'] = {name:df.loc[ids,label].value_counts().to_dict() for name,ids in splits.items()}
        out['chronological_diagnostic_caveat'] = 'Support diagnostic only; tied timestamps, overlapping flows, duplicate groups and scenario independence not yet split-qualified.'
    else:
        out['timestamp'] = None
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dsrl', type=Path)
    args = parser.parse_args()
    sources = {'scvic_apt_2021_local_training': ([Path('C:/Users/garyp/Downloads/SCVIC-APT-2021-Training.csv')], 'Label'),
               'dapt2020_local_raw': (sorted(Path('C:/Users/garyp/OneDrive/Documents/codex/data/raw/dapt2020').glob('*.csv')), 'Stage')}
    if args.dsrl:
        sources['dsrl_apt_2023_author_release'] = ([args.dsrl], 'Stage')
    result = {name:audit(paths,label) for name,(paths,label) in sources.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps({name:{k:v for k,v in data.items() if k in ['rows','stage_counts','timestamp','duplicate_feature_rows','feature_groups_with_conflicting_labels','unique_feature_groups_by_stage','chronological_60_15_10_15_diagnostic']} for name,data in result.items()},indent=2))


if __name__ == '__main__':
    main()
