"""Bounded read-only recheck of Windows clock recoverability; no event correction."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .host_events import windows_records, utc_ms, host_from_name


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inspect(source: Path) -> dict:
    system = []
    for path in sorted((source / 'windows').iterdir()):
        if 'systemevents' not in path.name and 'eventviewer' not in path.name:
            continue
        records = list(windows_records(path))
        anchors, changes, services = [], [], []
        for index, row in enumerate(records):
            match = re.search(
                r'system time has changed to\s+([0-9T:.\-]+Z)\s+from\s+([0-9T:.\-]+Z)',
                row['payload'], re.I)
            if match:
                new, old = utc_ms(match[1]), utc_ms(match[2])
                offset = round((new - row['local_ms']) / 60000) * 60000
                anchors.append({'new_utc_ms': new, 'export_offset_ms': offset,
                                'fractional_residual_ms': new - row['local_ms'] - offset})
                if abs(new - old) > 1000:
                    changes.append({'new_utc': match[1], 'old_utc': match[2],
                                    'change_seconds': (new - old) / 1000,
                                    'record_position': index,
                                    'hardware_clock_reason': 'synchronized with the hardware clock' in row['payload'],
                                    'application_or_component_reason': 'An application or system component changed the time.' in row['payload']})
            if 'time' in row['provider'].lower():
                services.append({'record_position': index, 'event_id': row['event_id'],
                                 'display_converted_utc_ms': row['local_ms'] + 25200000,
                                 'synchronization_statement': 'synchronizing the system time' in row['payload'].lower(),
                                 'valid_time_data_statement': 'valid time data' in row['payload'].lower(),
                                 'time_windows_com_named': 'time.windows.com' in row['payload'].lower()})
        order_breaks = sum(b['local_ms'] > a['local_ms'] for a, b in zip(records, records[1:]))
        pilot_services = [r for r in services
                          if utc_ms('2021-07-01T00:00:00Z') <= r['display_converted_utc_ms']
                          < utc_ms('2021-07-04T00:00:00Z')]
        system.append({'source_file': path.relative_to(source).as_posix(),
                       'host': host_from_name(path), 'sha256': digest(path),
                       'bytes': path.stat().st_size, 'records': len(records),
                       'utc_anchor_count': len(anchors),
                       'offset_counts_ms': dict(Counter(a['export_offset_ms'] for a in anchors)),
                       'maximum_abs_fractional_residual_ms': max((abs(a['fractional_residual_ms']) for a in anchors), default=None),
                       'clock_changes_over_one_second': changes,
                       'reverse_export_timestamp_increases': order_breaks,
                       'time_service_event_id_counts': dict(Counter(r['event_id'] for r in services)),
                       'july1_through3_time_service_metadata': pilot_services,
                       'exported_record_id_marker_count': len(re.findall(r'EventRecordID|Event Record ID', path.read_text(encoding='utf-8', errors='replace')))})
    filebeat = []
    for path in sorted((source / 'filebeat').iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        filebeat.append({'source_file': path.relative_to(source).as_posix(),
                         'sha256': digest(path), 'bytes': path.stat().st_size,
                         'at_timestamp_mentions': text.count('@timestamp'),
                         'windows_security_provider_mentions': text.count('Microsoft-Windows-Security-Auditing'),
                         'winlog_mentions': len(re.findall(r'\bwinlog\b', text)),
                         'event_created_mentions': text.count('event.created'),
                         'event_ingested_mentions': text.count('event.ingested')})
    return {'schema_version': 1, 'reviewed_utc': datetime.now(timezone.utc).isoformat(),
            'decision': 'NOT_QUALIFIED_FOR_FULL_PILOT_CLOCK_RECOVERY',
            'reviewer_sha256': digest(Path(__file__)),
            'reused_record_parser_sha256': digest(Path(__file__).with_name('host_events.py')),
            'system_sources': system, 'filebeat_sources': filebeat,
            'why': ['UTC-format anchors resolve displayed timezone but originate from the same host clock.',
                    'The principal Windows host has an approximately seven-hour backward correction during evaluation.',
                    'No corresponding forward-shift marker establishes the start of the invalid preceding clock segment.',
                    'NTP status messages support synchronization at a point, not an external timestamp for every prior Security record.',
                    'The local Filebeat release supplies no matched Windows stream or independent event-receive timestamp.'],
            'corrections_applied': 0, 'model_fits': 0, 'model_outcomes_read': False,
            'frozen_scientific_artifacts_modified': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('A fresh review output path is required')
    result = inspect(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'decision': result['decision'],
                      'system_sources': len(result['system_sources']),
                      'system_utc_anchors': sum(r['utc_anchor_count'] for r in result['system_sources']),
                      'filebeat_sources': len(result['filebeat_sources']),
                      'receipt_sha256': digest(args.out)}, indent=2))


if __name__ == '__main__':
    main()
