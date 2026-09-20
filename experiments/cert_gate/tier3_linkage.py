"""Offline PCAP-to-EVE field linkage; no attack labels or independence claims.

Supported: classic PCAP and PCAPNG Ethernet, VLAN, unfragmented IPv4 TCP/UDP.
Unsupported packet forms preserve their one-based ordinal but cannot verify an
alert. Malformed capture structures abort rather than silently skipping bytes.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import struct


def _decode(frame, linktype):
    if linktype != 1:
        return {"unsupported": "non_ethernet_linktype"}
    if len(frame) < 14:
        return {"unsupported": "truncated_ethernet"}
    offset, kind = 14, int.from_bytes(frame[12:14], "big")
    while kind in (0x8100, 0x88A8, 0x9100):
        if len(frame) < offset + 4:
            return {"unsupported": "truncated_vlan"}
        kind = int.from_bytes(frame[offset + 2:offset + 4], "big")
        offset += 4
    if kind != 0x0800:
        return {"unsupported": "non_ipv4"}
    packet = frame[offset:]
    if len(packet) < 20 or packet[0] >> 4 != 4:
        return {"unsupported": "truncated_or_invalid_ipv4"}
    ihl, total = (packet[0] & 15) * 4, int.from_bytes(packet[2:4], "big")
    if ihl < 20 or total < ihl or len(packet) < ihl:
        return {"unsupported": "invalid_ipv4_length"}
    if int.from_bytes(packet[6:8], "big") & 0x3FFF:
        return {"unsupported": "fragmented_ipv4"}
    proto = packet[9]
    if proto not in (6, 17):
        return {"unsupported": "non_tcp_udp"}
    transport = packet[ihl:min(total, len(packet))]
    minimum = 20 if proto == 6 else 8
    if len(transport) < minimum:
        return {"unsupported": "truncated_transport"}
    if proto == 6 and not 20 <= (transport[12] >> 4) * 4 <= len(transport):
        return {"unsupported": "invalid_tcp_header"}
    if proto == 17 and not 8 <= int.from_bytes(transport[4:6], "big") <= total - ihl:
        return {"unsupported": "invalid_udp_length"}
    return {"src_ip": str(ipaddress.IPv4Address(packet[12:16])),
            "dest_ip": str(ipaddress.IPv4Address(packet[16:20])),
            "proto": "TCP" if proto == 6 else "UDP",
            "src_port": int.from_bytes(transport[:2], "big"),
            "dest_port": int.from_bytes(transport[2:4], "big")}


def read_packets(path):
    """Return one entry for every capture packet, including unsupported packets."""
    data = Path(path).read_bytes()
    packets = []
    classic = {b'\xd4\xc3\xb2\xa1': ('<', 10**6), b'\xa1\xb2\xc3\xd4': ('>', 10**6),
               b'\x4d\x3c\xb2\xa1': ('<', 10**9), b'\xa1\xb2\x3c\x4d': ('>', 10**9)}
    if data[:4] in classic:
        endian, scale = classic[data[:4]]
        if len(data) < 24:
            raise ValueError("Truncated PCAP header")
        major, minor, _, _, _, linktype = struct.unpack_from(endian + 'HHIIII', data, 4)
        if (major, minor) != (2, 4):
            raise ValueError("Unsupported PCAP version")
        offset = 24
        while offset < len(data):
            if len(data) - offset < 16:
                raise ValueError("Truncated PCAP packet header")
            sec, sub, captured, original = struct.unpack_from(endian + 'IIII', data, offset)
            offset += 16
            if captured > original or sub >= scale or captured > len(data) - offset:
                raise ValueError("Invalid PCAP packet length or timestamp")
            record = _decode(data[offset:offset + captured], linktype)
            record['timestamp'] = Fraction(sec) + Fraction(sub, scale)
            packets.append(record)
            offset += captured
        return packets
    if data[:4] != b'\x0a\x0d\x0d\x0a':
        raise ValueError("Unsupported capture magic")
    offset, endian, interfaces = 0, None, []
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError("Truncated PCAPNG block")
        section = data[offset:offset + 4] == b'\x0a\x0d\x0d\x0a'
        if section:
            bom = data[offset + 8:offset + 12]
            endian = '<' if bom == b'\x4d\x3c\x2b\x1a' else '>' if bom == b'\x1a\x2b\x3c\x4d' else None
            if endian is None:
                raise ValueError("Invalid PCAPNG byte order")
            interfaces = []
        if endian is None:
            raise ValueError("PCAPNG interface outside section")
        kind, length = struct.unpack_from(endian + 'II', data, offset)
        if length < 12 or length % 4 or offset + length > len(data):
            raise ValueError("Invalid PCAPNG block length")
        if struct.unpack_from(endian + 'I', data, offset + length - 4)[0] != length:
            raise ValueError("PCAPNG block trailer mismatch")
        body = data[offset + 8:offset + length - 4]
        if section:
            if len(body) < 16 or struct.unpack_from(endian + 'H', body, 4)[0] != 1:
                raise ValueError("Unsupported PCAPNG section")
        elif kind == 1:
            if len(body) < 8:
                raise ValueError("Truncated PCAPNG interface")
            linktype = struct.unpack_from(endian + 'H', body)[0]
            resolution, time_offset, pos = Fraction(1, 10**6), 0, 8
            while pos < len(body):
                if pos + 4 > len(body):
                    raise ValueError("Truncated interface option")
                code, size = struct.unpack_from(endian + 'HH', body, pos)
                pos += 4
                if pos + ((size + 3) // 4 * 4) > len(body):
                    raise ValueError("Truncated interface option value")
                value = body[pos:pos + size]
                pos += (size + 3) // 4 * 4
                if code == 0:
                    if size:
                        raise ValueError("Invalid end option")
                    break
                if code == 9:
                    if size != 1:
                        raise ValueError("Invalid timestamp resolution")
                    exponent = value[0]
                    resolution = Fraction(1, 2**(exponent & 127) if exponent & 128 else 10**exponent)
                if code == 14:
                    if size != 8:
                        raise ValueError("Invalid timestamp offset")
                    time_offset = struct.unpack(endian + 'q', value)[0]
            interfaces.append((linktype, resolution, time_offset))
        elif kind == 6:
            if len(body) < 20:
                raise ValueError("Truncated enhanced packet block")
            iface, high, low, captured, original = struct.unpack_from(endian + 'IIIII', body)
            if iface >= len(interfaces) or captured > original or 20 + ((captured + 3) // 4 * 4) > len(body):
                raise ValueError("Invalid enhanced packet interface or length")
            linktype, resolution, time_offset = interfaces[iface]
            record = _decode(body[20:20 + captured], linktype)
            record['timestamp'] = ((high << 32) | low) * resolution + time_offset
            packets.append(record)
        elif kind in (2, 3):
            if kind == 2:
                if len(body) < 20:
                    raise ValueError("Truncated obsolete packet block")
                iface = struct.unpack_from(endian + 'H', body)[0]
                captured, original = struct.unpack_from(endian + 'II', body, 12)
                if iface >= len(interfaces) or captured > original or 20 + ((captured + 3) // 4 * 4) > len(body):
                    raise ValueError("Invalid obsolete packet block")
            elif not interfaces or len(body) < 4:
                raise ValueError("Invalid simple packet block")
            packets.append({'unsupported': 'obsolete_or_simple_packet_block', 'timestamp': None})
        offset += length
    return packets


def _event_time(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:?\d{2})', value)
    if not match:
        raise ValueError("Unsupported timestamp")
    base, fraction, zone = match.groups()
    parsed = datetime.fromisoformat(base + ('+00:00' if zone == 'Z' else zone))
    elapsed = parsed.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return Fraction(elapsed.days * 86400 + elapsed.seconds) + Fraction(int(fraction or '0'), 10**len(fraction or '0'))


def _filename_matches(value, pcap):
    if not isinstance(value, str) or not value.strip():
        return False
    value = value.replace('\\', '/')
    if '/' not in value and ':' not in value:
        return value.casefold() == Path(pcap).name.casefold()
    return os.path.normcase(os.path.abspath(value)) == os.path.normcase(os.path.abspath(str(pcap)))


def audit(pcap, eve, *, include_details=False):
    """Audit alert-to-wire linkage; private details are opt-in and not CLI output."""
    pcap, eve = Path(pcap), Path(eve)
    packets = read_packets(pcap)
    statuses, reasons, details, event_types = Counter(), Counter(), [], Counter()
    for line_number, line in enumerate(eve.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError("EVE records must be objects")
        event_types[str(event.get('event_type'))] += 1
        if event.get('event_type') != 'alert':
            continue
        status, reason = 'VERIFIED_FIELDS', 'wire_fields_match'
        number = event.get('pcap_cnt')
        source = event.get('pkt_src')
        if source is not None and source not in ('wire/pcap', 'wire', 'pcap'):
            status, reason = 'UNVERIFIABLE', 'pseudo_or_unsupported_packet_source'
        elif type(number) is not int or not 1 <= number <= len(packets):
            status, reason = 'UNVERIFIABLE', 'missing_or_invalid_pcap_cnt'
        elif not event.get('pcap_filename'):
            status, reason = 'UNVERIFIABLE', 'missing_pcap_filename'
        elif not _filename_matches(event['pcap_filename'], pcap):
            status, reason = 'MISMATCH', 'pcap_filename_mismatch'
        else:
            packet = packets[number - 1]
            if 'unsupported' in packet:
                status, reason = 'UNVERIFIABLE', packet['unsupported']
            else:
                try:
                    stamp = _event_time(event.get('timestamp'))
                except (ValueError, OverflowError):
                    status, reason = 'UNVERIFIABLE', 'invalid_event_timestamp'
                else:
                    if packet['timestamp'] is None:
                        status, reason = 'UNVERIFIABLE', 'missing_packet_timestamp'
                    elif abs(stamp - packet['timestamp']) > Fraction(1, 10**6):
                        status, reason = 'MISMATCH', 'timestamp_mismatch'
                    else:
                        for field in ('src_ip', 'dest_ip', 'proto', 'src_port', 'dest_port'):
                            if field not in event:
                                status, reason = 'UNVERIFIABLE', 'missing_' + field
                                break
                            if type(event[field]) is not type(packet[field]) or event[field] != packet[field]:
                                status, reason = 'MISMATCH', field + '_mismatch'
                                break
        statuses[status] += 1
        reasons[reason] += 1
        if include_details and status != 'VERIFIED_FIELDS':
            details.append({'eve_line': line_number, 'pcap_cnt': number, 'status': status, 'reason': reason})
    result = {'status': 'PROVENANCE_DIAGNOSTIC_ONLY_NO_ATTACK_LABEL_OR_CERTIFICATE',
              'capture_packets': len(packets), 'decodable_packets': sum('unsupported' not in p for p in packets),
              'event_type_counts': dict(event_types), 'alert_status_counts': dict(statuses),
              'alert_reason_counts': dict(reasons), 'timestamp_tolerance_microseconds': 1,
              'pcap_sha256': hashlib.sha256(pcap.read_bytes()).hexdigest(),
              'eve_sha256': hashlib.sha256(eve.read_bytes()).hexdigest(),
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Exact wire orientation; independent incident count and attack truth are not established'}
    if include_details:
        result['private_mismatch_details'] = details
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcap', type=Path, required=True)
    parser.add_argument('--eve', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.pcap, args.eve)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result, allow_nan=False))
