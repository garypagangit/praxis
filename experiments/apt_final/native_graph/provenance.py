"""Bind this static development pilot to committed code and normalized arrays."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def code_paths(config):
    return sorted(set([Path(config).resolve(), HERE / 'PROTOCOL.md',
                       *HERE.glob('*.py'), *HERE.glob('*.sh')]), key=str)


def data_inventory(data_dir):
    data_dir = Path(data_dir).resolve()
    return {p.relative_to(data_dir).as_posix(): digest(p)
            for p in sorted(data_dir.rglob('*.npz'))}


def validate_manifest(data_dir):
    manifest = read(Path(data_dir) / 'MANIFEST.json')
    if (manifest.get('schema') != 'apt-final-native-graph-data-v1'
            or manifest.get('status') != 'STATIC_DEVELOPMENT_ONLY'
            or manifest.get('adapter_sha256') != digest(HERE / 'data.py')):
        raise ValueError('A matching native static-development data audit is required')
    expected = {}
    for dataset in manifest.get('datasets', []):
        if dataset.get('status') != 'STATIC_DEVELOPMENT_ONLY' or dataset.get('matches_upstream_git_blob') is not True:
            raise ValueError('Data source provenance did not qualify')
        for graph in dataset.get('graphs', []):
            rel = graph['npz']
            if rel in expected or not (Path(data_dir) / rel).resolve().is_relative_to(Path(data_dir).resolve()):
                raise ValueError('Duplicate or escaping graph path')
            expected[rel] = graph['npz_sha256']
    if not expected or expected != data_inventory(data_dir):
        raise ValueError('Actual arrays do not match the audited graph inventory')
    return manifest


def verify_registration(config_path, data_dir, registration_path):
    config_path, data_dir = Path(config_path).resolve(), Path(data_dir).resolve()
    record = read(registration_path)
    if record.get('scope') != 'DEVELOPMENT_ONLY' or record.get('status') != 'FROZEN_NATIVE_GRAPH_PILOT':
        raise ValueError('A native-graph development registration is required')
    if read(config_path).get('scope') != 'DEVELOPMENT_ONLY' or record.get('config_sha256') != digest(config_path):
        raise ValueError('Configuration changed after registration')
    expected = {p.relative_to(REPO).as_posix() for p in code_paths(config_path)}
    if set(record.get('code_hashes', {})) != expected:
        raise ValueError('Registered source inventory does not match runtime')
    has_git = (REPO / '.git').exists()
    if not has_git and not re.fullmatch(r'[0-9a-f]{64}', os.environ.get('APT_FROZEN_BUNDLE_SHA256', '')):
        raise ValueError('Remote execution requires the externally hash-verified bundle marker')
    for rel, sha in record['code_hashes'].items():
        path = (REPO / rel).resolve()
        if not path.is_relative_to(REPO) or digest(path) != sha:
            raise ValueError('Registered source changed: ' + rel)
        if has_git:
            blob = subprocess.check_output(['git', 'show', record['git_commit'] + ':' + rel], cwd=REPO)
            if hashlib.sha256(blob).hexdigest() != sha:
                raise ValueError('Source does not match its recorded commit: ' + rel)
    if record.get('data_manifest_sha256') != digest(data_dir / 'MANIFEST.json'):
        raise ValueError('Data audit manifest changed after registration')
    validate_manifest(data_dir)
    if record.get('data_files') != data_inventory(data_dir):
        raise ValueError('Normalized graph bytes changed after registration')
    if not record['data_files']:
        raise ValueError('No graph arrays were registered')
    return record


def register(config_path, data_dir, output):
    config_path, data_dir, output = Path(config_path).resolve(), Path(data_dir).resolve(), Path(output)
    if read(config_path).get('scope') != 'DEVELOPMENT_ONLY':
        raise ValueError('Only development scope is supported')
    validate_manifest(data_dir)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    hashes = {}
    for path in code_paths(config_path):
        rel = path.relative_to(REPO).as_posix()
        blob = subprocess.check_output(['git', 'show', commit + ':' + rel], cwd=REPO)
        if hashlib.sha256(blob).hexdigest() != digest(path):
            raise ValueError('Commit exact code/config/protocol bytes first: ' + rel)
        hashes[rel] = digest(path)
    record = {'scope': 'DEVELOPMENT_ONLY', 'status': 'FROZEN_NATIVE_GRAPH_PILOT',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'git_commit': commit,
              'config_sha256': digest(config_path), 'code_hashes': hashes,
              'data_manifest_sha256': digest(data_dir / 'MANIFEST.json'),
              'data_files': data_inventory(data_dir), 'scientific_runs_before_this_freeze': 0,
              'confirmation_registered': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    verify_registration(config_path, data_dir, output)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['register', 'verify'])
    parser.add_argument('--config', type=Path, default=HERE / 'config.json')
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    result = (register(args.config, args.data_dir, args.registration) if args.action == 'register'
              else verify_registration(args.config, args.data_dir, args.registration))
    print(json.dumps({'status': result['status'], 'commit': result['git_commit'],
                      'source_files': len(result['code_hashes']), 'data_files': len(result['data_files'])}))
