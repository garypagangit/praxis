"""Verify the coordinator's sealed files without inference or network calls."""
from pathlib import Path
import hashlib
import json


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'RELEASE_MANIFEST.json').read_text())
    problems = []
    for name, expected in manifest['files'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            problems.append({'path': name, 'reason': 'missing or outside package'})
            continue
        data = path.read_bytes()
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            problems.append({'path': name, 'reason': 'content differs from sealed bytes'})
    result = {'status': 'FAIL' if problems else 'PASS', 'sealed_files': len(manifest['files']),
              'problems': problems, 'scope': 'Coordinator byte integrity only; no scientific or academic certification.'}
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(problems))


if __name__ == '__main__':
    main()
