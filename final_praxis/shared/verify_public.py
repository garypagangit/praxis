"""Verify deployed dashboard and report bytes against this reviewed checkout."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://garypagangit.github.io/praxis/'
state = json.loads((ROOT / 'final_praxis/status.json').read_text(encoding='utf-8'))
paths = [ROOT / 'final_praxis' / suffix for suffix in ['index.html', 'status.json', 'shared/dashboard.js']]
for item in state['experiments']:
    for key in ['report', 'pdf', 'docx']:
        if item.get(key):
            paths.append((ROOT / 'final_praxis' / item[key]).resolve())
rows = []
for path in paths:
    relative = path.relative_to(ROOT).as_posix()
    url = BASE + relative
    request = Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Praxis-publication-verification'})
    with urlopen(request, timeout=30) as response:
        actual = response.read()
        status = response.status
    expected_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    actual_hash = hashlib.sha256(actual).hexdigest()
    rows.append({'url': url, 'http_status': status, 'bytes': len(actual), 'expected_sha256': expected_hash,
                 'deployed_sha256': actual_hash, 'match': expected_hash == actual_hash})
record = {'checked_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
          'status': 'PASS' if all(x['match'] for x in rows) else 'FAIL', 'files': rows}
(ROOT / 'final_praxis/execution/20260908/PUBLICATION_VERIFICATION.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': record['status'], 'checked': len(rows), 'mismatches': [x['url'] for x in rows if not x['match']]}, indent=2))
if record['status'] != 'PASS':
    raise SystemExit(1)
