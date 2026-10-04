"""Independent packet-count/timestamp verification using dpkt 1.9.8."""
import argparse
import io
import json
from pathlib import Path
import zipfile
import dpkt


def main(downloads, inventory, output):
    report = json.loads(inventory.read_text(encoding='utf-8'))
    results = []
    for archive in report['archives']:
        with zipfile.ZipFile(downloads / archive['local_file']) as z:
            for member in archive['members']:
                if 'pcap' not in member:
                    continue
                count = captured = queries = decoded = dns_errors = 0
                first = last = None
                for timestamp, packet in dpkt.pcap.Reader(io.BytesIO(z.read(member['path']))):
                    count += 1
                    captured += len(packet)
                    first = timestamp if first is None else min(first, timestamp)
                    last = timestamp if last is None else max(last, timestamp)
                    try:
                        net = dpkt.ethernet.Ethernet(packet).data
                        udp = net.data
                        if isinstance(udp, dpkt.udp.UDP) and udp.dport == 53:
                            queries += 1
                            try:
                                dns = dpkt.dns.DNS(udp.data)
                                decoded += int(dns.qr == 0 and len(dns.qd) > 0)
                            except (dpkt.UnpackError, ValueError, IndexError):
                                dns_errors += 1
                    except (dpkt.UnpackError, ValueError, AttributeError, IndexError):
                        pass
                expected = member['pcap']
                checks = {'packet_count': count == expected['packets'],
                          'captured_bytes': captured == expected['captured_bytes'],
                          'first_timestamp': abs(float(first)-expected['first_epoch']) < 1e-6,
                          'last_timestamp': abs(float(last)-expected['last_epoch']) < 1e-6}
                results.append({'archive': archive['local_file'], 'member': member['path'],
                                'checks': checks, 'udp_destination_53_packets': queries,
                                'decodable_dns_queries': decoded, 'dns_parse_errors': dns_errors})
    out = {'parser': 'dpkt ' + dpkt.__version__, 'files': results,
           'all_checks_pass': bool(results) and all(all(r['checks'].values()) for r in results),
           'limit': 'Successful DNS parsing is not proof of complete payload, transfer success, or label correctness.'}
    output.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out))
    if not out['all_checks_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--downloads', type=Path, required=True)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    main(a.downloads, a.inventory, a.output)
