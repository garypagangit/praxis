"""Check every listed file against the delivery SHA-256 inventory."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();manifest=json.loads((root/'SHA256.json').read_text())
for name,expected in manifest.items():
    p=(root/name).resolve();assert root in p.parents,'Invalid manifest path'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
print(f'PASS: {len(manifest)} file hashes')
