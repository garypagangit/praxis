"""Download pinned public artifacts. No model inference, installation or cloud calls."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, dest, sha=None, blob=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        temporary = dest.with_suffix(dest.suffix + '.partial')
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(dest)
    content = dest.read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    if sha is not None:
        assert actual == sha, str(dest)
    if blob is not None:
        assert hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == blob, str(dest)
    return {'path': str(dest), 'sha256': actual, 'bytes': len(content), 'url': url}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--models', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'RUNTIME_ASSET_MANIFEST.json').read_text())
    receipts = []
    for record in manifest['files']:
        receipts.append(fetch(record['url'], args.cache / record['cache_path'], record['sha256']))
    archive = args.cache / 'timesfm_source.zip'
    source_dir = args.cache / 'timesfm_full'
    source_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            parts = Path(item.filename).parts[1:]
            if not parts or item.is_dir():
                continue
            target = source_dir.joinpath(*parts).resolve()
            assert target.is_relative_to(source_dir.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(item))
    if args.models:
        for repo, info in manifest['models'].items():
            for item in info['files']:
                name = item['rfilename']
                if name.startswith('.'):
                    continue
                url = f'https://huggingface.co/{repo}/resolve/{info["revision"]}/{name}'
                receipts.append(fetch(url, args.cache / 'models' / repo.split('/')[-1] / name, item.get('lfs', {}).get('sha256'), None if 'lfs' in item else item.get('blobId')))
    output = args.cache / ('ASSET_RECEIPT_MODELS.json' if args.models else 'ASSET_RECEIPT.json')
    output.write_text(json.dumps({'files': receipts}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(receipts), 'receipt': str(output)}))


if __name__ == '__main__':
    main()
