"""Necessary native-class support bound for one strict chronological cutoff.

No model fitting, clock repair, chosen-cutoff search, or duration qualification.
For fit_start < cutoff <= test_start, every class needs two earlier rows and
one later row. The admissible start-only interval is (max(second-earliest),
min(latest)]. A nonempty interval is not a qualified deployment split.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ALGORITHM_FILES = [HERE / 'support_cutoff_audit.py', HERE / 'test_support_cutoff_audit.py']
SCVIC = Path('C:/Users/garyp/Downloads/SCVIC-APT-2021-Training.csv')
DAPT_ROOT = Path('C:/Users/garyp/OneDrive/Documents/codex/data/raw/dapt2020')


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def support_bound(starts_by_class: Mapping[str, Sequence[int]]) -> dict:
    """Return the exact count-support interval in a recorded integer time axis.

    Bounds only use starts. In particular, no flow duration or arrival time is
    available to this function. Tied starts remain tied; input order is ignored.
    """
    if not starts_by_class:
        raise ValueError('At least one native class is required')
    classes = {}
    for name, values in sorted(starts_by_class.items()):
        times = sorted(int(value) for value in values)
        if not times:
            raise ValueError('Empty native class must not be silently dropped')
        classes[name] = {
            'rows': len(times),
            'second_earliest_start': times[1] if len(times) >= 2 else None,
            'latest_start': times[-1],
        }
    insufficient = [name for name, item in classes.items() if item['rows'] < 2]
    lower = None if insufficient else max(item['second_earliest_start'] for item in classes.values())
    upper = min(item['latest_start'] for item in classes.values())
    feasible = lower is not None and lower < upper
    return {
        'minimum_fit_rows_per_native_class': 2,
        'minimum_test_rows_per_native_class': 1,
        'fit_rule': 'start < cutoff',
        'test_rule': 'start >= cutoff',
        'cutoff_interval': '(lower_exclusive, upper_inclusive]',
        'lower_exclusive': lower,
        'upper_inclusive': upper,
        'lower_binding_classes': [] if lower is None else [name for name, item in classes.items() if item['second_earliest_start'] == lower],
        'upper_binding_classes': [name for name, item in classes.items() if item['latest_start'] == upper],
        'classes_with_fewer_than_two_rows': insufficient,
        'start_only_count_support_possible': feasible,
        'status': 'POSSIBLE_START_ONLY_SUPPORT_NOT_SPLIT_QUALIFICATION' if feasible else 'NO_ALL_CLASS_CUTOFF_EVEN_WITH_START_ONLY_COUNTS',
        'classes': classes,
        'uses_flow_durations_or_arrival_times': False,
        'deployment_validity_established': False,
        'independent_campaign_support_established': False,
    }


def load_source(paths: list[Path], label: str) -> tuple[pd.DataFrame, list[dict]]:
    frames, receipts, header = [], [], None
    for path in paths:
        frame = pd.read_csv(path, low_memory=False)
        frame.columns = frame.columns.str.strip()
        headerless = label not in frame.columns
        if headerless:
            if header is None or len(frame.columns) != len(header):
                raise ValueError('Unqualified headerless source')
            frame = pd.read_csv(path, header=None, names=header, low_memory=False)
        else:
            header = list(frame.columns)
        if frame[label].isna().any():
            raise ValueError('Missing native labels')
        frame[label] = frame[label].astype(str).str.strip().replace({'BENIGN': 'Benign'})
        if (frame[label] == '').any():
            raise ValueError('Empty native labels')
        frames.append(frame)
        receipts.append({'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size,
                         'rows': len(frame), 'headerless_read_with_reference_schema': headerless})
    if not frames:
        raise ValueError('No sources')
    return pd.concat(frames, ignore_index=True), receipts


def parse_starts(frame: pd.DataFrame, formats: list[str]) -> pd.Series:
    timestamps = pd.Series(pd.NaT, index=frame.index, dtype='datetime64[ns]')
    for fmt in formats:
        remaining = timestamps.isna()
        timestamps.loc[remaining] = pd.to_datetime(frame.loc[remaining, 'Timestamp'], format=fmt, errors='coerce')
    if timestamps.isna().any():
        raise ValueError('Unparsed timestamp; no guessing or row dropping is permitted')
    return timestamps


def iso(value):
    return None if value is None else pd.Timestamp(value, unit='ns').isoformat()


def qualify(name: str, paths: list[Path], label: str, formats: list[str]) -> dict:
    frame, receipts = load_source(paths, label)
    starts = parse_starts(frame, formats)
    result = support_bound({str(native): starts.loc[rows.index].astype('int64').tolist()
                            for native, rows in frame.groupby(label, sort=True)})
    for field in ['lower_exclusive', 'upper_inclusive']:
        result[field + '_recorded_timestamp'] = iso(result[field])
    for item in result['classes'].values():
        item['second_earliest_recorded_timestamp'] = iso(item['second_earliest_start'])
        item['latest_recorded_timestamp'] = iso(item['latest_start'])
    result.update(dataset=name, source_receipts=receipts, rows=len(frame), native_label_column=label,
                  timestamp_formats=formats, numeric_time_unit='nanoseconds',
                  timestamp_timezone='not established; naive as recorded; not assigned UTC',
                  anomalous_clock_rows_retained=True, rows_removed=0,
                  duplicate_policy='all original rows retained; duplicate purging can only reduce support',
                  prior_data_exposure=True,
                  scope='Optimistic necessary bound on native-label start-time support; no eligible cutoff selected.')
    return result


def verify_algorithm_commit(commit: str) -> dict:
    frozen = {}
    for path in ALGORITHM_FILES:
        relative = path.relative_to(REPO).as_posix()
        content = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=REPO)
        if content != path.read_bytes():
            raise ValueError('Algorithm differs from the specified frozen commit: ' + relative)
        frozen[relative] = hashlib.sha256(content).hexdigest()
    return frozen


def render(report: dict) -> str:
    lines = ['# Necessary chronological cutoff support audit', '',
             'This is a start-time count diagnostic on previously exposed data. No model was fitted, no cutoff selected, and no timestamp repaired.', '',
             'To retain at least two fitting rows and one test row for every native class, with `fit_start < cutoff <= test_start`, a cutoff must be greater than every class\'s second-earliest start and no greater than every class\'s latest start. Thus the start-only interval is `(max(second-earliest), min(latest)]`. Empty or reversed bounds rule out every such single cutoff. Duration and duplicate constraints can only narrow support.', '',
             '| Dataset | Lower, exclusive | Binding class(es) | Upper, inclusive | Binding class(es) | Start-only interval |',
             '|---|---|---|---|---|---|']
    for name, item in report['datasets'].items():
        lines.append(f"| {name} | {item['lower_exclusive_recorded_timestamp']} | {', '.join(item['lower_binding_classes'])} | {item['upper_inclusive_recorded_timestamp']} | {', '.join(item['upper_binding_classes'])} | {'Nonempty; not split qualification' if item['start_only_count_support_possible'] else 'Empty; no all-class single cutoff'} |")
    lines += ['', '## Native-class bounds', '']
    for name, item in report['datasets'].items():
        lines += [f'### {name}', '', '| Native class | Rows | Second-earliest start | Latest start |', '|---|---:|---|---|']
        for label, row in item['classes'].items():
            lines.append(f"| {label} | {row['rows']} | {row['second_earliest_recorded_timestamp']} | {row['latest_recorded_timestamp']} |")
        lines.append('')
    lines += ['## Interpretation limits', '',
              '- SCVIC timestamps remain unqualified physical chronology, including all anomalous 1970 rows. This result concerns its recorded time field only.',
              '- DAPT uses flow starts. A qualified completed-flow or arrival-time split is stricter and requires separate checks.',
              '- Nonempty support does not establish independence, useful statistical power, or a deployment-valid split. Empty support is a count-level impossibility under the stated single-cutoff rule.',
              '- Native labels, every input row and tied timestamps are preserved. There is no label dropping, clock repair, favorable-window search, resampling, or fitting.',
              '- Additional fitting/calibration/test partitions impose further constraints. This two-side necessary condition does not certify those partitions.',
              '', f"Frozen algorithm commit: `{report['algorithm_commit']}`. Detailed file hashes and exact integer bounds: [SUPPORT_CUTOFF_AUDIT.json](SUPPORT_CUTOFF_AUDIT.json).", '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    bindings = verify_algorithm_commit(args.commit)
    targets = [HERE / 'SUPPORT_CUTOFF_AUDIT.json', HERE / 'SUPPORT_CUTOFF_AUDIT.md']
    if any(path.exists() for path in targets):
        raise FileExistsError('Refusing to overwrite support results')
    dapt = sorted(DAPT_ROOT.glob('*.csv'))
    if len(dapt) != 10:
        raise ValueError('Expected the previously audited ten DAPT CSV files')
    report = {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'algorithm_commit': args.commit, 'algorithm_sha256': bindings, 'model_fits': 0,
              'aws_used': False, 'prior_data_exposure': True,
              'datasets': {
                  'SCVIC-APT-2021': qualify('SCVIC-APT-2021', [SCVIC], 'Label', ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M']),
                  'DAPT2020': qualify('DAPT2020', dapt, 'Stage', ['%d/%m/%Y %I:%M:%S %p']),
              }}
    targets[0].write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    targets[1].write_text(render(report), encoding='utf-8')
    print(json.dumps({name: {k: value[k] for k in ['status', 'lower_exclusive_recorded_timestamp', 'upper_inclusive_recorded_timestamp', 'lower_binding_classes', 'upper_binding_classes']} for name, value in report['datasets'].items()}, indent=2))


if __name__ == '__main__':
    main()
