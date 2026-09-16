"""Download one pinned checkpoint and unpack already pinned source; no inference."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--spec', type=Path, required=True)
    a = p.parse_args()
    spec = json.loads(a.spec.read_text())
    archive = a.assets / 'timesfm_source.zip'
    if digest(archive) != 'ecb62c7cc793937991bbaf4a481d60ac74e84724db3e9d6ea457b2b350f11692':
        raise RuntimeError('Source ZIP identity mismatch')
    if digest(a.assets / 'source.csv') != spec['data']['file_sha256']:
        raise RuntimeError('Source CSV identity mismatch')
    dest = (a.assets / 'timesfm_full').resolve()
    dest.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            parts = Path(item.filename).parts
            if item.is_dir() or len(parts) < 2:
                continue
            if Path(item.filename).is_absolute() or '..' in parts:
                raise RuntimeError('Unsafe source archive path')
            target = (dest / Path(*parts[1:])).resolve()
            if not target.is_relative_to(dest):
                raise RuntimeError('Source path escaped asset directory')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(item))
    from huggingface_hub import hf_hub_download
    downloaded = Path(hf_hub_download(repo_id=spec['model']['name'],
                                     revision=spec['model']['revision'],
                                     filename='model.safetensors',
                                     local_dir=str(a.assets / 'model')))
    if digest(downloaded) != spec['model']['weights_sha256']:
        raise RuntimeError('Pinned checkpoint hash mismatch')
    receipt = {'status': 'ASSETS_VERIFIED_NO_INFERENCE',
               'source_archive_sha256': digest(archive),
               'source_csv_sha256': digest(a.assets / 'source.csv'),
               'weights_sha256': digest(downloaded),
               'source_revision': spec['model']['source_revision'],
               'model_revision': spec['model']['revision'], 'model_calls': 0}
    (a.assets / 'ASSET_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
