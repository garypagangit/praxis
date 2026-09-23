"""Post-acquisition descriptive audit; no fitting or target construction.

Preserves the frozen acquisition report and emits a separate qualification
supplement from the pinned downloaded bytes. Counts are measurement support,
not numbers of successful attacks.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def inspect(data_root, acquisition):
    for row in acquisition['files']:
        path = data_root / row['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Local downloaded-byte hash mismatch: ' + row['file'])
    result = {'hashes_verified': len(acquisition['files']), 'model_fits': 0,
              'dataset_revision': acquisition['files'][0]['revision_requested'],
              'physical_files': {}, 'target_qualification': {}}
    clocks = {}
    for name in ['benign48h', 'attack22h']:
        frame = pd.read_csv(data_root / name / 'physical_state.csv')
        clock = pd.to_datetime(frame['_time'], utc=True, errors='raise')
        intervals = clock.diff().dt.total_seconds().dropna()
        process = frame.drop(columns=['Unnamed: 0', 'result', 'table', '_time'])
        clocks[name] = clock
        result['physical_files'][name] = {
            'rows': len(frame), 'process_variables': len(process.columns),
            'metadata_columns_to_exclude_from_predictors': ['Unnamed: 0', 'result', 'table', '_time'],
            'rows_with_missing_process_value': int(process.isna().any(axis=1).sum()),
            'clock_span_seconds': float((clock.iloc[-1] - clock.iloc[0]).total_seconds()),
            'first_timestamp': clock.iloc[0].isoformat(), 'last_timestamp': clock.iloc[-1].isoformat(),
            'timestamp_delta_seconds_quantiles': {str(q): float(intervals.quantile(q)) for q in [0, .5, .9, .99, 1]},
            'timestamp_gaps_above_two_seconds': int((intervals > 2).sum()),
            'timestamp_gaps_above_ten_seconds': int((intervals > 10).sum()),
            'timestamp_gaps_above_sixty_seconds': int((intervals > 60).sum()),
            'effective_rows_per_second': float((len(frame)-1)/(clock.iloc[-1]-clock.iloc[0]).total_seconds()),
            'constant_process_columns': [c for c in process if process[c].nunique(dropna=True) <= 1],
        }
    annotations = pd.concat([pd.read_csv(data_root/'attack22h'/'ground_truth'/f'c{k}_ground_truth.csv', keep_default_na=False) for k in range(1, 5)], ignore_index=True)
    clock = clocks['attack22h']
    union = np.zeros(len(clock), dtype=bool)
    details = []
    for _, row in annotations.iterrows():
        start, end = pd.to_datetime([row['start'], row['end']], utc=True)
        if end < start: raise ValueError('Negative interval')
        mask = (clock >= start) & (clock <= end)
        union |= mask.to_numpy()
        text = row['description'].lower()
        outcome = ('explicitly_skipped' if 'skipped' in text else
                   'contains_failure_or_abort_requires_review' if ('failed' in text or 'aborted' in text) else
                   'execution_described_outcome_unverified')
        details.append({'campaign': row['campaign'], 'sub_phase': row['sub_phase'],
                        'tactic': row['tactic'], 'physical_rows': int(mask.sum()),
                        'within_attack_recording_clock': bool(start >= clock.iloc[0] and end <= clock.iloc[-1]),
                        'outcome_screen': outcome})
    result['target_qualification'] = {
        'annotation_rows': len(annotations), 'distinct_script_ids': int(annotations.campaign.nunique()),
        'physical_rows_in_any_annotated_interval': int(union.sum()),
        'physical_rows_outside_all_annotations': int((~union).sum()),
        'all_intervals_within_attack_recording_clock': all(x['within_attack_recording_clock'] for x in details),
        'zero_row_intervals': [x for x in details if x['physical_rows'] == 0],
        'movement_intervals': [x for x in details if x['tactic'] == 'Lateral Movement'],
        'annotation_tactic_counts': annotations.tactic.value_counts().to_dict(),
        'exfiltration_tactic_annotations': int((annotations.tactic == 'Exfiltration').sum()),
        'successful_exfiltration_events_verified': None,
        'independent_repeated_campaigns_verified': 0,
        'skipped_or_failed_screen': [x for x in details if x['outcome_screen'] != 'execution_described_outcome_unverified'],
    }
    result['decisions'] = {
        'enterprise_movement_or_exfiltration_confirmation': 'not_supported_by_physical_subset',
        'measured_logging_cost_or_latency_evaluation': 'not_supported',
        'ics_process_history_development': 'potentially_feasible_after_frozen_target_and_time_split',
        'allow_model_fitting_automatically': False,
        'unannotated_attack_recording_rows_are_verified_benign': False,
        'annotation_overlap_counts_certify_completed_actions': False,
        'timestamp_alignment_proves_all_modality_clocks_synchronized': False,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--acquisition', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.data_root, json.loads(args.acquisition.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
