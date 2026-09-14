"""Verify the public qualification package against its explicit SHA-256 manifest."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(root, manifest_path):
    root = Path(root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    checks = []
    for name, meta in manifest['files'].items():
        path = (root / name).resolve()
        ok = path.is_relative_to(root) and path.is_file()
        if ok:
            ok = path.stat().st_size == meta['bytes'] and sha(path) == meta['sha256']
        checks.append({'path': name, 'passed': bool(ok)})
    return {
        'scope': 'Exact-byte integrity of listed release files; not a scientific validity judgment',
        'manifest_sha256': sha(manifest_path),
        'verifier_sha256': sha(__file__),
        'files_checked': len(checks),
        'files_failed': sum(not r['passed'] for r in checks),
        'verification_pass': bool(checks) and all(r['passed'] for r in checks),
        'checks': checks
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = verify(a.root, a.manifest)
    Path(a.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['files_checked', 'files_failed', 'verification_pass']}))
    raise SystemExit(0 if result['verification_pass'] else 1)
