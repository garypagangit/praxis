"""Acquire the pinned author MIT release for synthetic-only development checks."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

COMMIT = '31bd0987bf84a4616fc9f9a60410a704a0ce4967'
EXPECTED = {
    'DSRL-APT-2023.csv': '883001548b93c05152ae60a1851e0cb3b939a7f3aea0808f16e4c4c997bdf7bd',
    'LICENSE': '54f34f49eca4fa1dcb7ad6d4e7e04b187f2fc95d7199af8e80806cdb2842bf73',
    'README.md': 'ff85057ba40addd86dbb8979f7e0e0f456c2514d54efc4b63eb9141ba030cb77',
    'CITATION.cff': '6c51018d5dd165f8e5e6cc0a6cc95df1355bf4a3f9535c888de67c34b3953605',
}


def acquire(output):
    output.mkdir(parents=True, exist_ok=True)
    files=[]
    for name, expected in EXPECTED.items():
        target=output/name
        url=f'https://raw.githubusercontent.com/shadab75/DSRL-APT-2023/{COMMIT}/{name}'
        if not target.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                data=response.read(100*1024*1024+1)
            if len(data)>100*1024*1024:
                raise ValueError('Unexpectedly large pinned artifact')
            actual=hashlib.sha256(data).hexdigest()
            if actual!=expected:
                raise ValueError(f'Digest mismatch: {name}')
            target.write_bytes(data)
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        if actual!=expected:
            raise ValueError(f'Existing file digest mismatch: {name}')
        files.append({'url':url,'path':str(target),'bytes':target.stat().st_size,'sha256':actual})
    receipt={'source_commit':COMMIT,'license':'MIT','scope':'CTGAN-derived from DAPT2020; synthetic-only, not independent real-data validation','files':files}
    (output/'ACQUISITION.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    acquire(parser.parse_args().output)
