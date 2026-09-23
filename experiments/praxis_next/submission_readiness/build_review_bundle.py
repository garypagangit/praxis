"""Build and verify a reviewer delivery without changing original evidence.

Run only after the submission-readiness documents and receipts are complete.
The newly built ZIP and its two external verification receipts never include
themselves. Existing output artifacts are preserved rather than overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit
import zipfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAPER = Path('experiments/praxis_next/measurement_praxis')
REVIEW = Path('experiments/praxis_next/submission_readiness')
OLD_ZIP_NAME = 'apt_evaluation_praxis_evidence.zip'
NEW_ZIP_NAME = 'praxis_review_bundle.zip'
PINNED_OLD_ZIP_SHA256 = '3dcc1e67dad8a74eebca1ac71c7fce3d1dd721ea67901c3f4ad869b126055bd3'
MANIFEST_NAME = 'REVIEW_MANIFEST.json'
EXTERNAL_NAMES = {NEW_ZIP_NAME, 'REVIEW_BUNDLE_RECEIPT.json', 'REVIEW_EXTRACT_VERIFICATION.json'}
SKIP_DIRS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.git', '.venv', 'venv', 'node_modules'}
EXTRA_PUBLIC_FILES = (
    'experiments/apt_benchmark/tabular_followup/HOLDOUT_QUALIFICATION.md',
    'experiments/apt_benchmark/results/tabular_followup_v1/TRANSFER_SUMMARY.json',
    'experiments/apt_benchmark/tabular_followup/SANDWORM_QUALIFICATION.json',
    'experiments/apt_benchmark/tabular_followup/prepare_sandworm.py',
    'experiments/apt_benchmark/tabular_followup/FEATURE_COMPATIBILITY.md',
    'experiments/apt_benchmark/tabular_followup/FEATURE_COMPATIBILITY.json',
    'experiments/apt_benchmark/tabular_followup/protocol_sandworm_transfer.json',
    'experiments/apt_benchmark/tabular_followup/run_sandworm_transfer.py',
    'experiments/apt_benchmark/tabular_followup/audit_sandworm_transfer.py',
    'experiments/apt_benchmark/tabular_followup/UNRAVELED_QUALIFICATION.json',
    'experiments/apt_benchmark/tabular_followup/audit_unraveled.py',
)

START_HERE = '''APT evaluation praxis: reviewer delivery

Start with:
  experiments/praxis_next/submission_readiness/README.md
  experiments/praxis_next/submission_readiness/ADVISER_HANDOFF.md
  experiments/praxis_next/submission_readiness/apt_praxis_review_edition.pdf
  experiments/praxis_next/submission_readiness/praxis_defense_brief.pdf

The original completed manuscript is:
  experiments/praxis_next/measurement_praxis/apt_evaluation_praxis.pdf

Submission-readiness documents, sensitivity analysis, code and receipts are in:
  experiments/praxis_next/submission_readiness/

The original evidence ZIP is retained byte-for-byte beside the original paper.
It also satisfies the original README's local archive link. The original 209
archive members remain unchanged. This review ZIP does not include itself.

Public verification requires Python and NumPy 2.2.6. From this extracted root:
  python experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis/verify_public.py
  python experiments/praxis_next/measurement_praxis/verify_package.py

REVIEW_MANIFEST.json under submission_readiness binds every bundled file except
itself. The new ZIP and its REVIEW_BUNDLE_RECEIPT.json and
REVIEW_EXTRACT_VERIFICATION.json attestations are external delivery artifacts,
distributed beside this ZIP; they are intentionally not nested into it.

Public aggregate calculations can be reproduced without private flow data.
They do not independently verify author labels, individual-row identities,
model fitting, successful attacks, or generalization to independent campaigns.
No model training or AWS operation is needed for the public checks.
'''


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode('utf-8')


def write_new(path, value):
    with Path(path).open('xb') as handle:
        handle.write(encoded(value))


def root_relative(name):
    """Normalize manifest keys and reject paths escaping the rooted delivery."""
    text=str(name).replace('\\', '/')
    if not text or text.startswith('/') or ':' in text or any(p in ('', '.', '..') for p in text.split('/')):
        raise ValueError('Unsafe manifest path: '+repr(name))
    return text


def helpers():
    # Import the exact local helper file without depending on the working dir.
    path=HERE/'clean_room/run_clean_room.py'
    spec=importlib.util.spec_from_file_location('review_clean_room_helpers', path)
    module=importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode=True
    spec.loader.exec_module(module)
    return module


def excluded(path):
    parts=path.relative_to(HERE).parts
    return (any(part in SKIP_DIRS for part in parts) or path.name in EXTERNAL_NAMES or
            path.name == MANIFEST_NAME or path.name.startswith(('~$', '.~lock.')) or
            path.suffix.lower() in {'.pyc','.pyo','.lock','.lck','.tmp','.partial'})


def verify_manifest_members(members, manifest):
    for relative, expected in manifest['files'].items():
        key=root_relative(relative)
        if key not in members or sha_bytes(members[key]) != expected:
            raise ValueError('Original manifest mismatch: '+key)


def markdown_links(extracted):
    external={(REVIEW/name).as_posix() for name in EXTERNAL_NAMES}
    checked=[]; expected_external=[]; missing=[]
    markdown=list((extracted/REVIEW).rglob('*.md'))
    markdown += [extracted/name for name in EXTRA_PUBLIC_FILES if name.endswith('.md')]
    for path in sorted(markdown):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            target=target.strip().removeprefix('<').removesuffix('>')
            url=urlsplit(target)
            if url.scheme or not url.path:continue
            candidate=(path.parent/unquote(url.path)).resolve()
            try:
                relative=candidate.relative_to(extracted.resolve()).as_posix()
            except ValueError:
                missing.append(dict(file=path.relative_to(extracted).as_posix(),target=target,reason='outside_extraction'))
                continue
            record=dict(file=path.relative_to(extracted).as_posix(),target=target,resolved=relative)
            if candidate.exists():checked.append(record)
            elif relative in external:expected_external.append(record)
            else:missing.append(record)
    return dict(existing_links=len(checked),expected_external_delivery_links=expected_external,
                unexpected_missing=missing,details=checked)


def build(args):
    source_zip=args.original_zip.resolve()
    destination=HERE/NEW_ZIP_NAME
    manifest_path=HERE/MANIFEST_NAME
    bundle_receipt=HERE/'REVIEW_BUNDLE_RECEIPT.json'
    extraction_receipt=HERE/'REVIEW_EXTRACT_VERIFICATION.json'
    for path in (destination,manifest_path,bundle_receipt,extraction_receipt):
        if path.exists():
            raise FileExistsError('Preserve previous delivery artifact; use a separate checkout: '+str(path))
    if sha(source_zip)!=PINNED_OLD_ZIP_SHA256:
        raise ValueError('Original ZIP does not match the completed evidence release')
    old_zip_bytes=source_zip.read_bytes()
    h=helpers()
    prior=read(HERE/'clean_room/CLEAN_ROOM_RECEIPT.json')
    if prior['archive_sha256'] != PINNED_OLD_ZIP_SHA256:
        raise ValueError('Prior clean-room receipt binds a different original ZIP')
    python=args.python.resolve() if args.python else Path(prior['runtime']['executable'])
    if not python.is_file():
        raise FileNotFoundError('Verification interpreter missing; supply --python for a Python+NumPy 2.2.6 venv')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    work=(args.work_parent/('praxis_review_bundle_'+stamp)).resolve()
    work.mkdir(parents=False,exist_ok=False)
    extracted=work/'extracted'; results=work/'results'
    extracted.mkdir(); results.mkdir()
    members={}
    with zipfile.ZipFile(source_zip) as old:
        entries,_=h.validated_entries(old,extracted)
        for info,_ in entries:
            if not info.is_dir():members[info.filename]=old.read(info)
    if len(members)!=209:
        raise ValueError('Original release must contain exactly 209 file members')
    original_hashes={name:sha_bytes(data) for name,data in members.items()}
    original_manifest=json.loads(members[(PAPER/'PACKAGE_MANIFEST.json').as_posix()])
    if len(original_manifest['files'])!=206:
        raise ValueError('Original package manifest must bind exactly 206 artifacts')
    verify_manifest_members(members,original_manifest)
    members[(PAPER/OLD_ZIP_NAME).as_posix()]=old_zip_bytes
    start_path=HERE/'START_HERE_REVIEW.txt'
    start_bytes=START_HERE.encode('utf-8')
    if start_path.exists() and start_path.read_bytes()!=start_bytes:
        raise ValueError('Existing START_HERE_REVIEW.txt differs; review before rebuilding')
    if not start_path.exists():start_path.write_bytes(start_bytes)
    source_bindings={}
    for source in sorted(HERE.rglob('*')):
        if not source.is_file() or excluded(source):continue
        if source.is_symlink():raise ValueError('Do not bundle source symlinks: '+str(source))
        relative=source.relative_to(REPO).as_posix()
        data=source.read_bytes()
        if relative in members:raise ValueError('New deliverable collides with an original member: '+relative)
        members[relative]=data
        source_bindings[relative]=sha_bytes(data)
    for relative in EXTRA_PUBLIC_FILES:
        source=REPO/relative
        if not source.is_file() or source.is_symlink() or source.stat().st_size>1_000_000:
            raise ValueError('Expected small regular public supporting artifact: '+relative)
        data=source.read_bytes()
        if relative in members and members[relative]!=data:
            raise ValueError('Public supporting file differs from original member: '+relative)
        members[relative]=data
        source_bindings[relative]=sha_bytes(data)
    members['START_HERE_REVIEW.txt']=start_bytes
    for required in (REVIEW/'README.md',REVIEW/'ADVISER_HANDOFF.md',
                     REVIEW/'apt_praxis_review_edition.pdf',REVIEW/'praxis_defense_brief.pdf',
                     REVIEW/'DOCUMENT_RECEIPT.json',PAPER/'apt_evaluation_praxis.pdf'):
        if required.as_posix() not in members:raise ValueError('Required reviewer entry point is missing: '+str(required))
    manifest=dict(schema_version=1,created_utc=datetime.now(timezone.utc).isoformat(),
        original_archive_sha256=PINNED_OLD_ZIP_SHA256,original_member_count=209,
        original_manifest_artifacts=206,original_member_hashes=original_hashes,
        source_bindings=source_bindings,external_artifacts=sorted(EXTERNAL_NAMES),
        excluded='This manifest, new ZIP, external attestations, caches and locks; no recursive bundle inclusion',
        files={name:sha_bytes(data) for name,data in sorted(members.items())})
    write_new(manifest_path,manifest)
    members[(REVIEW/MANIFEST_NAME).as_posix()]=manifest_path.read_bytes()
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(members.items()):archive.writestr(name,data)
    with zipfile.ZipFile(destination) as archive:
        entries,total=h.validated_entries(archive,extracted)
        for info,target in entries:
            if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(info) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
    actual={p.relative_to(extracted).as_posix():sha(p) for p in extracted.rglob('*') if p.is_file()}
    expected={name:sha_bytes(data) for name,data in members.items()}
    if actual != expected:raise ValueError('Re-extracted review bundle differs from its assembled members')
    for name,value in original_hashes.items():
        if actual.get(name)!=value:raise ValueError('Original extracted member changed: '+name)
    for name,value in manifest['files'].items():
        if actual.get(name)!=value:raise ValueError('New review manifest mismatch: '+name)
    probe=h.command([str(python),'-I','-B','-c',
        'import sys,numpy,json;print(json.dumps(dict(python=sys.version,executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,numpy=numpy.__version__,isolated=sys.flags.isolated)))'],extracted,30)
    if probe['returncode']!=0:raise RuntimeError('Verification runtime probe failed: '+probe['stderr'])
    runtime=json.loads(probe['stdout'])
    if runtime['numpy']!='2.2.6' or runtime['prefix']==runtime['base_prefix']:
        raise ValueError('Verification requires an isolated venv with pinned NumPy 2.2.6')
    cfg=Path(runtime['prefix'])/'pyvenv.cfg'
    if 'include-system-site-packages = false' not in cfg.read_text(encoding='utf-8').lower():
        raise ValueError('Verification venv must exclude system site packages')
    roots=[str(extracted),str(results),runtime['prefix'],runtime['base_prefix']]
    child_env=dict(os.environ)
    for name in ('PYTHONPATH','PYTHONHOME'):child_env.pop(name,None)
    runs=[]
    for name,relative in [('public',PAPER/'evidence/paired_reanalysis/verify_public.py'),('package',PAPER/'verify_package.py')]:
        out=results/(name.upper()+'_VERIFICATION.json')
        access=results/(name.upper()+'_FILE_ACCESS.json')
        run=h.command([str(python),'-I','-B','-c',h.GUARDED_RUNNER,str(extracted/relative),
            str(out),str(access),json.dumps(roots)],extracted,90,child_env)
        run['name']=name
        run['receipt']=read(out) if out.exists() else None
        if access.exists():
            log=read(access)
            run['file_access']=dict(path=str(access),sha256=sha(access),events=len(log['open_events']),denied=log['denied'])
        runs.append(run)
    links=markdown_links(extracted)
    after={p.relative_to(extracted).as_posix():sha(p) for p in extracted.rglob('*') if p.is_file()}
    changed_sources=[name for name,value in source_bindings.items() if sha(REPO/name)!=value]
    original_unchanged=sha(source_zip)==PINNED_OLD_ZIP_SHA256
    passed=(all(r['returncode']==0 and (r.get('receipt') or {}).get('status')=='PASS'
                and not r.get('file_access',{}).get('denied',['missing']) for r in runs)
            and not links['unexpected_missing'] and actual==after and not changed_sources and original_unchanged)
    extraction=dict(schema_version=1,status='PASS' if passed else 'FAIL',utc=datetime.now(timezone.utc).isoformat(),
        original_archive_sha256=PINNED_OLD_ZIP_SHA256,review_bundle_sha256=sha(destination),
        review_manifest_sha256=sha(manifest_path),extraction_root=str(extracted),runtime=runtime,
        isolation='Prior fresh venv reused; new extraction/cwd and Python -I -B with Python-open allowlist. Same local host, not OS/container isolation.',
        zip_paths_validated_before_member_writes=True,expanded_bytes=total,
        original_members_verified=209,original_manifest_hashes_verified=206,
        new_manifest_hashes_verified=len(manifest['files']),extracted_members_verified=len(actual),
        extracted_bytes_unchanged_after_verification=actual==after,source_changes_during_build=changed_sources,
        verifier_runs=runs,new_markdown_links=links,private_inputs_needed=False,new_model_fits=0,aws_used=False)
    write_new(extraction_receipt,extraction)
    bundle=dict(schema_version=1,status=extraction['status'],utc=datetime.now(timezone.utc).isoformat(),
        builder_sha256=sha(__file__),bundle_name=NEW_ZIP_NAME,bundle_bytes=destination.stat().st_size,
        bundle_sha256=sha(destination),manifest_sha256=sha(manifest_path),
        extraction_receipt_sha256=sha(extraction_receipt),original_zip_sha256=PINNED_OLD_ZIP_SHA256,
        original_zip_unchanged=original_unchanged,original_members_preserved=209,
        bundled_members=len(actual),new_manifest_entries=len(manifest['files']),source_bindings=source_bindings,
        external_attestations=['REVIEW_BUNDLE_RECEIPT.json','REVIEW_EXTRACT_VERIFICATION.json'],
        non_recursive=True,new_model_fits=0,aws_used=False)
    write_new(bundle_receipt,bundle)
    print(json.dumps(dict(status=extraction['status'],bundle=str(destination),sha256=bundle['bundle_sha256'],
        original_members=209,members=len(actual),unexpected_missing_links=links['unexpected_missing'])))
    return 0 if passed else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-zip',type=Path,default=REPO/PAPER/OLD_ZIP_NAME)
    parser.add_argument('--python',type=Path,help='Optional fresh venv interpreter; otherwise reuse clean-room venv')
    parser.add_argument('--work-parent',type=Path,default=Path('C:/w'))
    raise SystemExit(build(parser.parse_args()))
