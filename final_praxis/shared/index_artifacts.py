"""Index exact local archive bytes and their already assigned S3 object keys."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 's3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/'
ARCHIVES = {
    'final_praxis_001_ff19b1d1890e.zip': ('001', 'superseded source v1', 'code/fp001-ff19b1d1890e.zip'),
    'final_praxis_001_e060bb29c7e3.zip': ('001', 'discovery source v2', 'code/fp001-e060bb29c7e3.zip'),
    'final_praxis_002_94c2830575e9.zip': ('002', 'discovery source v1', 'code/fp002-94c2830575e9.zip'),
    'final_praxis_003_a3db8e0ed25d.zip': ('003', 'superseded source v1', 'code/fp003-a3db8e0ed25d.zip'),
    'final_praxis_003_8499d656d189.zip': ('003', 'discovery source v2', 'code/fp003-8499d656d189.zip'),
    'fp001-pilot-agent-v1.zip': ('001', 'superseded agent pilot v1', '001/pilot_agent_v1.zip'),
    'fp001-pilot-complete-v2.zip': ('001', 'verified pilot v2', '001/pilot_complete_v2.zip'),
    'fp002-pilot-v1.zip': ('002', 'verified pilot v1', '002/pilot_v1.zip'),
    'fp003-pilot-v1.zip': ('003', 'superseded pilot v1', '003/pilot_v1.zip'),
    'fp003-pilot-v2.zip': ('003', 'verified pilot v2', '003/pilot_v2.zip'),
    'fp001-discovery-agent-v2.zip': ('001', 'discovery agent phase v2', '001/discovery_agent_v2.zip'),
    'fp001-discovery-complete-v2.zip': ('001', 'complete discovery v2', '001/discovery_complete_v2.zip'),
    'fp002-discovery-v1.zip': ('002', 'complete discovery v1', '002/discovery_v1.zip'),
    'fp003-discovery-v2.zip': ('003', 'complete discovery v2', '003/discovery_v2.zip'),
}
items = []
for name, (study, kind, key) in ARCHIVES.items():
    path = ROOT / 'tmp' / name
    if path.is_file():
        items.append({'experiment': study, 'kind': kind, 'local_archive': str(path.relative_to(ROOT)),
                      's3_uri': BASE + key, 'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
destination = ROOT / 'final_praxis/execution/20260908'
(destination / 'ARTIFACT_INDEX.json').write_text(json.dumps(items, indent=2) + '\n', encoding='utf-8')
lines = ['# Final Praxis evidence archive index', '',
         'These SHA-256 hashes identify the exact downloaded or uploaded ZIP bytes. The frozen source manifests separately bind each scientific input file. Pilots and superseded versions are retained as infrastructure history and excluded from discovery results.', '',
         'Raw archives are stored in the project AWS account and require authorized AWS access. Compact reports, verification summaries, and result tables are in Git. An independently verified negative result remains a completed experiment.', '',
         '| Study | Archive | Bytes | SHA-256 |', '|---|---|---:|---|']
for item in items:
    lines.append(f"| {item['experiment']} | {item['kind']} | {item['bytes']} | `{item['sha256']}` |")
lines += ['', '## Exact S3 locations', '']
for item in items:
    lines += [f"- {item['experiment']} {item['kind']}: `{item['s3_uri']}`"]
lines += ['', 'Restore into an isolated checkout using the matching source archive and `final_praxis/shared/safe_extract.py`; do not overwrite completed runs with regenerated inputs. Run the experiment-specific independent verifier before interpreting results.']
(ROOT / 'final_praxis/ARTIFACT_INDEX.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps({'indexed_archives': len(items)}))
