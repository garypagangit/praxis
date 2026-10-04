"""Read local publisher downloads without extracting or executing archive contents.

This is a source qualification audit, not a fitted detector experiment.
Usage: python qualify_cic.py --output PATH ZIP [ZIP ...]
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile


def pcap_summary(data):
    formats = {b'\xd4\xc3\xb2\xa1': ('<', 1e6), b'\xa1\xb2\xc3\xd4': ('>', 1e6),
               b'\x4d\x3c\xb2\xa1': ('<', 1e9), b'\xa1\xb2\x3c\x4d': ('>', 1e9)}
    endian, resolution = formats[data[:4]]
    major, minor, zone, sigfigs, snaplen, linktype = struct.unpack(endian + 'HHIIII', data[4:24])
    offset, count, stored, wire, backwards, truncated = 24, 0, 0, 0, 0, 0
    first = last = previous = None
    protocols = collections.Counter()
    while offset < len(data):
        if len(data) - offset < 16:
            raise ValueError('Truncated PCAP record header')
        seconds, fraction, captured, original = struct.unpack(endian + 'IIII', data[offset:offset+16])
        offset += 16
        if offset + captured > len(data):
            raise ValueError('Truncated PCAP packet')
        packet = data[offset:offset+captured]
        stamp = seconds + fraction / resolution
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
        backwards += int(previous is not None and stamp < previous)
        previous = stamp
        count += 1
        stored += captured
        wire += original
        truncated += int(captured < original)
        # Only Ethernet IPv4 is classified; all other link/protocol types remain explicit.
        if linktype == 1 and len(packet) >= 34 and packet[12:14] == b'\x08\x00':
            protocols[str(packet[23])] += 1
        else:
            protocols['unclassified'] += 1
        offset += captured
    return {'format': f'pcap {major}.{minor}', 'linktype': linktype, 'snaplen': snaplen,
            'packets': count, 'captured_bytes': stored, 'original_bytes': wire,
            'truncated_packets': truncated, 'backward_timestamp_steps': backwards,
            'first_epoch': first, 'last_epoch': last,
            'duration_seconds': None if first is None else last-first,
            'first_utc': None if first is None else dt.datetime.fromtimestamp(first,dt.timezone.utc).isoformat(),
            'last_utc': None if last is None else dt.datetime.fromtimestamp(last,dt.timezone.utc).isoformat(),
            'ipv4_protocol_counts': dict(protocols), 'record_boundaries_valid': offset == len(data)}


def inspect(path):
    raw = path.read_bytes()
    result = {'local_file': path.name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'members': []}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.file_size > 512_000_000:
                raise ValueError('Member exceeds qualification memory bound')
            data = archive.read(info)  # ZIP CRC is checked by zipfile.
            item = {'path': info.filename, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'zip_crc_valid': True}
            if info.filename.lower().endswith('.pcap'):
                item['pcap'] = pcap_summary(data)
            elif info.filename.lower().endswith('.csv'):
                rows = csv.reader(io.StringIO(data.decode('utf-8-sig')))
                item['columns'] = next(rows)
                item['rows'] = sum(1 for _ in rows)
            result['members'].append(item)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('archives', type=Path, nargs='+')
    args = parser.parse_args()
    report = {'status': 'SOURCE_INVENTORY_ONLY', 'publisher': 'https://www.unb.ca/cic/datasets/dns-exf-2021.html',
              'retrieval': 'User browser downloads; archive integrity checked, publisher checksum unavailable',
              'archives': [inspect(p) for p in args.archives],
              'limits': ['PCAP timestamps and archive names do not prove independent successful transfer episodes.',
                         'Labels do not provide ground-truth feature attributions.',
                         'No models fitted, no episode-recovery result, no confirmation split consumed.',
                         'No downloaded archive contents extracted or executed.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'archives': len(report['archives']), 'output': str(args.output),
                      'pcaps': sum('pcap' in m for a in report['archives'] for m in a['members'])}))
