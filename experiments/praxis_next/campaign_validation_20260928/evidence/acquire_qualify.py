"""Acquire the complete publisher release and qualify its native labels/timing."""
import concurrent.futures as cf
import csv, hashlib, io, json, time, urllib.request, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = Path('C:/w/campaign_validation_20260928/ait')
DATA.mkdir(parents=True, exist_ok=True)
record = json.loads((ROOT/'ZENODO_RECORD.json').read_text(encoding='utf-8'))

def download(f):
    p = DATA/f['key']
    expected = f['checksum'].split(':')[1]
    if not p.exists() or hashlib.md5(p.read_bytes()).hexdigest() != expected:
        tmp = p.with_suffix('.part')
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f['links']['self'], timeout=90) as r, tmp.open('wb') as w:
                    while chunk := r.read(1024*1024):
                        w.write(chunk)
                assert hashlib.md5(tmp.read_bytes()).hexdigest() == expected
                tmp.replace(p)
                break
            except Exception:
                if attempt == 3: raise
                time.sleep(2)
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
    print('VERIFIED', p.name, p.stat().st_size, flush=True)
    return {'file': p.name, 'bytes': p.stat().st_size, 'md5': expected,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'crc_passed': True,
            'source': f['links']['self']}

def labels():
    mapping = {}
    current = None
    for line in (ROOT/'label_info.txt').read_text().splitlines():
        if not line.strip(): continue
        if line.startswith('Benign labels'): current = 0; continue
        if line.startswith('Malicious labels'): current = 1; continue
        mapping[line.strip()] = 2 if line.strip() == 'data exfiltration' else current
    return mapping

def qualify(p):
    maps = labels()
    summary = {'execution': p.stem.replace('_netflows', ''), 'members': []}
    with zipfile.ZipFile(p) as z:
        for name in sorted(z.namelist()):
            if not name.endswith('.csv'): continue
            with z.open(name) as r:
                header = pd.read_csv(r, nrows=0).columns.tolist()
            is_udp = 'udp' in name
            start = 'c_first_abs:3' if is_udp else 'first:29'
            cols = ['label', start, 'role_cli', 'role_serv', 'network_cli', 'network_serv']
            with z.open(name) as r:
                d = pd.read_csv(r, usecols=cols, low_memory=False)
            t = pd.to_numeric(d[start], errors='coerce')
            lab = d['label'].fillna('').astype(str)
            def iso(x): return pd.to_datetime(x, unit='ms', utc=True).isoformat()
            item = {'member': name, 'rows': len(d), 'start_utc': iso(t.min()), 'end_utc': iso(t.max()),
                    'native_labels': lab.value_counts().to_dict(),
                    'unknown_labels': lab[~lab.isin(maps)].value_counts().to_dict(),
                    'roles': sorted(set(d['role_cli'].astype(str)) | set(d['role_serv'].astype(str))),
                    'networks': sorted(set(d['network_cli'].astype(str)) | set(d['network_serv'].astype(str))),
                    'class_windows': {}}
            for k, label in enumerate(('benign', 'other_attack', 'exfiltration')):
                mask = lab.map(maps).eq(k)
                if mask.any():
                    item['class_windows'][label] = {'count': int(mask.sum()), 'start_utc': iso(t[mask].min()), 'end_utc': iso(t[mask].max())}
            summary['members'].append(item)
    print('QUALIFIED', summary['execution'], sum(m['rows'] for m in summary['members']), flush=True)
    return summary

if __name__ == '__main__':
    files = [f for f in record['files'] if f['key'].endswith('_netflows.zip')]
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        receipts = list(pool.map(download, files))
    (ROOT/'ACQUISITION.json').write_text(json.dumps(receipts, indent=2))
    summaries = [qualify(DATA/f['key']) for f in files]
    (ROOT/'QUALIFICATION.json').write_text(json.dumps(summaries, indent=2))
    for s in summaries:
        print(s['execution'], [(m['member'], m['class_windows'], m['unknown_labels']) for m in s['members']], flush=True)
