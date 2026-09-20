"""Bind a new development reproduction to source, prepared data and upstream code."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
UPSTREAM = 'aa0b647eea74b6faa0e52eb444370c4411a32cbe'
DATA_MANIFEST = 'de06215e30e36c6063eeeb6a1ed18a738735fd909dbeeda7fa7789728fb2feab'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def contained(root, rel):
    root = Path(root).resolve(strict=True)
    target = (root/rel).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file() or '\\' in rel:
        raise ValueError('Invalid bound path')
    return target


def source_files():
    paths = [HERE/name for name in ['provenance.py','model_adapter.py','qualification.py',
             'worker.py','launch.py','run_cloud.sh','config.json','RUNTIME.json','PROTOCOL.md']]
    paths += [HERE.parent/'native_graph/cloud_control.py', HERE.parent/'native_graph/data.py']
    return {p.relative_to(REPO).as_posix(): digest(p) for p in paths}


def verify_runtime(registration, data_dir, source_dir):
    record = read(registration)
    if record['status'] != 'FROZEN_MAGIC_DEVELOPMENT_REPRODUCTION' or record['upstream_commit'] != UPSTREAM:
        raise ValueError('Wrong registration')
    if digest(Path(data_dir)/'MANIFEST.json') != DATA_MANIFEST:
        raise ValueError('Prepared data manifest changed')
    manifest = read(Path(data_dir)/'MANIFEST.json')
    expected_data = {'MANIFEST.json':DATA_MANIFEST}
    expected_data.update({g['npz']:g['npz_sha256'] for d in manifest['datasets'] for g in d['graphs']})
    if record['data_files'] != expected_data or set(record['code_hashes']) != set(source_files()):
        raise ValueError('Incomplete frozen code or data inventory')
    for rel, sha in record['code_hashes'].items():
        if digest(contained(REPO, rel)) != sha:
            raise ValueError('Frozen source changed: '+rel)
    for rel, sha in record['data_files'].items():
        if digest(contained(data_dir, rel)) != sha:
            raise ValueError('Prepared bytes changed: '+rel)
    sm = read(Path(source_dir)/'SOURCE_MANIFEST.json')
    if digest(Path(source_dir)/'SOURCE_MANIFEST.json') != record['source_manifest_sha256'] or sm['commit'] != UPSTREAM:
        raise ValueError('Upstream manifest changed')
    if sm['files'] != record['upstream_files']:
        raise ValueError('Upstream inventory changed')
    for rel, sha in sm['files'].items():
        if digest(contained(source_dir, rel)) != sha:
            raise ValueError('Upstream source changed: '+rel)
    actual = {p.relative_to(source_dir).as_posix() for p in Path(source_dir).rglob('*.py') if '__pycache__' not in p.parts}
    expected = {r for r in sm['files'] if r.endswith('.py')}
    if actual != expected:
        raise ValueError('Unexpected upstream Python source')
    return record


def register(data_dir, source_dir, registration, upstream_git):
    if Path(registration).exists():
        raise ValueError('Registration already exists')
    hashes = source_files()
    for rel, sha in hashes.items():
        blob = subprocess.check_output(['git','show','HEAD:'+rel],cwd=REPO)
        if hashlib.sha256(blob).hexdigest() != sha:
            raise ValueError('Commit exact source before registration: '+rel)
    manifest = read(Path(data_dir)/'MANIFEST.json')
    files = {'MANIFEST.json':DATA_MANIFEST}
    files.update({g['npz']:g['npz_sha256'] for d in manifest['datasets'] for g in d['graphs']})
    sm = read(Path(source_dir)/'SOURCE_MANIFEST.json')
    inventory = subprocess.check_output(['git','ls-tree','-r','--name-only',UPSTREAM],cwd=upstream_git,text=True).splitlines()
    expected = {rel:hashlib.sha256(subprocess.check_output(['git','show',UPSTREAM+':'+rel],cwd=upstream_git)).hexdigest()
                for rel in inventory if rel.endswith('.py') or rel in {'README.md','requirements.txt','LICENSE'}}
    if sm['commit'] != UPSTREAM or sm['files'] != expected:
        raise ValueError('Upstream source does not match pinned Git blobs')
    record = {'status':'FROZEN_MAGIC_DEVELOPMENT_REPRODUCTION',
              'created_utc':datetime.now(timezone.utc).isoformat(),
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
              'upstream_commit':UPSTREAM,'code_hashes':hashes,'data_files':files,
              'source_manifest_sha256':digest(Path(source_dir)/'SOURCE_MANIFEST.json'),
              'upstream_files':sm['files'],'test_previously_exposed':True,
              'scope':'source-original architecture and objective, qualified runtime adaptation',
              'novelty_claimed':False,'confirmation_claimed':False}
    temporary = Path(registration).with_suffix('.tmp')
    with temporary.open('x',encoding='utf-8',newline='\n') as handle:
        handle.write(json.dumps(record,indent=2)+'\n')
    try:
        verify_runtime(temporary,data_dir,source_dir)
        temporary.rename(registration)
    finally:
        if temporary.exists():
            temporary.unlink()
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--upstream-git',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=HERE/'REGISTRATION.json')
    a=p.parse_args()
    r=register(a.data_dir,a.source_dir,a.registration,a.upstream_git)
    print(json.dumps({'status':r['status'],'code_files':len(r['code_hashes']),'data_files':len(r['data_files'])}))


if __name__ == '__main__':
    main()
