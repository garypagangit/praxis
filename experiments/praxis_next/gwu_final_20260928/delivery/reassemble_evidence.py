"""Download all .part files and REPRODUCTION_PARTS.json into this folder, then run this script."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'REPRODUCTION_PARTS.json').read_text())
for archive in manifest['archives']:
    target=root/archive['name']
    if target.exists():
        print('Already exists; leaving unchanged:',target.name)
        continue
    # Verify every part before creating an output file.
    for part in archive['parts']:
        p=root/part['name']
        assert p.stat().st_size==part['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==part['sha256'],part['name']
    digest=hashlib.sha256()
    with target.open('xb') as out:
        for part in archive['parts']:
            data=(root/part['name']).read_bytes();out.write(data);digest.update(data)
    assert target.stat().st_size==archive['bytes'] and digest.hexdigest()==archive['sha256'],target.name
    print('Reassembled and SHA256 verified:',target.name)
