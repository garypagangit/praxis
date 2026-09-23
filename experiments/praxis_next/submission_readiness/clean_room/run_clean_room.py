"""Extract and check a public evidence ZIP in a new local Python environment.

No raw dataset, original project import, model fit, or AWS operation is used.
This is a runtime-isolated local reproduction, not a container or OS sandbox.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit
import zipfile


PAPER = Path('experiments/praxis_next/measurement_praxis')
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def validated_entries(archive, destination):
    """Validate the entire archive before writing even one archived member."""
    destination = destination.resolve()
    seen = set()
    entries = []
    total = 0
    devices = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{i}' for p in ('COM', 'LPT') for i in range(1, 10)}
    for info in archive.infolist():
        name = info.filename
        posix = PurePosixPath(name)
        windows = PureWindowsPath(name)
        if (not name or '\\' in name or ':' in name or '\x00' in name or
                posix.is_absolute() or windows.drive or windows.root or
                any(p in ('..', '.') for p in name.rstrip('/').split('/'))):
            raise ValueError('Unsafe archive path: ' + repr(name))
        for part in posix.parts:
            if part.rstrip(' .') != part or part.split('.')[0].upper() in devices:
                raise ValueError('Unsafe Windows path component: ' + repr(name))
        target = (destination / Path(*posix.parts)).resolve()
        target.relative_to(destination)
        key = str(target).casefold()
        if key in seen:
            raise ValueError('Duplicate/case-colliding archive path: ' + name)
        seen.add(key)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
            raise ValueError('Non-regular archive entry: ' + name)
        if info.flag_bits & 1:
            raise ValueError('Encrypted archive entry: ' + name)
        total += info.file_size
        if total > 100_000_000 or info.file_size > 40_000_000:
            raise ValueError('Bounded extraction size exceeded')
        entries.append((info, target))
    return entries, total


GUARDED_RUNNER = r'''
import json, os, runpy, sys
from pathlib import Path
script, receipt, audit_path = map(Path, sys.argv[1:4])
roots = [Path(p).resolve() for p in json.loads(sys.argv[4])]
opened=[]; denied=[]
def inside(path):
    for root in roots:
        try: path.relative_to(root); return True
        except ValueError: pass
    return False
def hook(event,args):
    if event != 'open' or not args or isinstance(args[0],int): return
    try: p=Path(os.fsdecode(args[0])).resolve()
    except (TypeError,ValueError): return
    ok=inside(p)
    opened.append({'path':str(p),'mode':str(args[1]),'allowed':ok})
    if not ok:
        denied.append(str(p))
        raise PermissionError('Public verification attempted outside-runtime access: '+str(p))
sys.addaudithook(hook)
sys.argv=[str(script),'--receipt',str(receipt)]
try:
    runpy.run_path(str(script),run_name='__main__')
finally:
    payload={'scope':'Python open audit events only; not an operating-system sandbox',
      'allowed_roots':[str(p) for p in roots],'open_events':opened,'denied':denied,
      'sys_prefix':sys.prefix,'sys_base_prefix':sys.base_prefix,'sys_path':sys.path,
      'isolated_mode':sys.flags.isolated,'no_user_site':sys.flags.no_user_site}
    audit_path.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
'''


def command(cmd, cwd, timeout, env=None):
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return dict(command=[str(x) for x in cmd], cwd=str(cwd), returncode=proc.returncode,
                    elapsed_seconds=round(time.monotonic()-start, 3), stdout=proc.stdout, stderr=proc.stderr)
    except subprocess.TimeoutExpired as exc:
        return dict(command=[str(x) for x in cmd], cwd=str(cwd), returncode=None,
                    elapsed_seconds=round(time.monotonic()-start, 3), timeout=True,
                    stdout=str(exc.stdout or ''), stderr=str(exc.stderr or ''))


def run(args):
    started = datetime.now(timezone.utc)
    stamp = started.strftime('%Y%m%dT%H%M%S%fZ')
    root = (args.work_parent / ('praxis_review_cleanroom_' + stamp)).resolve()
    root.mkdir(parents=False, exist_ok=False)
    extracted = root / 'extracted'
    results = root / 'results'
    extracted.mkdir(); results.mkdir()
    result = dict(schema_version=1, started_utc=started.isoformat(),
                  status='RUNNING', wrapper_sha256=digest(__file__), root=str(root),
                  original_archive=str(args.archive.resolve()), archive_sha256=digest(args.archive),
                  original_archive_bytes=args.archive.stat().st_size, operations=[],
                  new_model_fits=0, aws_used=False)
    print('Fresh clean-room directory: ' + str(root), flush=True)
    try:
        copied = root / 'public_evidence.zip'
        shutil.copyfile(args.archive, copied)
        assert digest(copied) == result['archive_sha256']
        with zipfile.ZipFile(copied) as archive:
            entries, total = validated_entries(archive, extracted)
            result['zip_validation'] = dict(status='PASS', entries=len(entries), expanded_bytes=total,
                paths_validated_before_member_writes=True, symlinks_allowed=False,
                source_prediction_archive_entries=[i.filename for i,_ in entries if i.filename.endswith(('.npz','.npy','.parquet'))])
            for info, target in entries:
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as src, target.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
        initial = {str(p.relative_to(extracted)):digest(p) for p in extracted.rglob('*') if p.is_file()}
        envdir = root / 'venv'
        creation = command([sys.executable, '-I', '-m', 'venv', str(envdir)], root, 90)
        result['operations'].append(creation)
        if creation['returncode'] != 0:
            raise RuntimeError('Fresh venv creation failed')
        python = envdir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        installation = command([str(python), '-I', '-m', 'pip', '--isolated', '--disable-pip-version-check',
                                'install', '--only-binary=:all:', '--no-deps', 'numpy==2.2.6'], root, 120)
        result['operations'].append(installation)
        if installation['returncode'] != 0:
            raise RuntimeError('Pinned NumPy installation failed')
        probe = command([str(python), '-I', '-c',
            'import sys,numpy,json,importlib.metadata as m;print(json.dumps(dict(python=sys.version,executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,numpy=numpy.__version__,installed={d.metadata["Name"]:d.version for d in m.distributions()},isolated=sys.flags.isolated)))'], root, 30)
        result['operations'].append(probe)
        if probe['returncode'] != 0:
            raise RuntimeError('Environment probe failed')
        runtime = json.loads(probe['stdout'])
        assert runtime['numpy'] == '2.2.6'
        result['runtime'] = runtime
        result['venv_configuration'] = (envdir/'pyvenv.cfg').read_text(encoding='utf-8')
        child_env = dict(os.environ)
        for key in ('PYTHONPATH','PYTHONHOME'):
            child_env.pop(key, None)
        child_env['PYTHONDONTWRITEBYTECODE']='1'
        roots = [str(extracted), str(results), str(envdir), runtime['base_prefix']]
        runs=[]
        for name, relative in [('public', PAPER/'evidence/paired_reanalysis/verify_public.py'),
                               ('package', PAPER/'verify_package.py')]:
            receipt = results/(name.upper()+'_VERIFICATION.json')
            opens = results/(name.upper()+'_FILE_ACCESS.json')
            rec = command([str(python), '-I', '-B', '-c', GUARDED_RUNNER, str(extracted/relative),
                           str(receipt), str(opens), json.dumps(roots)], extracted, 90, child_env)
            rec['name']=name
            runs.append(rec)
            if receipt.exists(): rec['receipt']=json.loads(receipt.read_text(encoding='utf-8'))
            if opens.exists():
                log=json.loads(opens.read_text(encoding='utf-8'))
                rec['file_access_audit']=dict(events=len(log['open_events']),denied=log['denied'],
                    sha256=digest(opens),isolated_mode=log['isolated_mode'],no_user_site=log['no_user_site'])
        result['verification_runs']=runs
        manifest_path=extracted/PAPER/'PACKAGE_MANIFEST.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        mismatches=[]
        for relative, expected in manifest['files'].items():
            candidate=(extracted/relative).resolve()
            candidate.relative_to(extracted)
            if not candidate.is_file() or digest(candidate)!=expected: mismatches.append(relative)
        result['independent_manifest_check']=dict(files=len(manifest['files']),mismatches=mismatches,
            manifest_sha256=digest(manifest_path))
        links=[]
        for name in ('manuscript.md','README.md','EVIDENCE_INDEX.md','REPRODUCE.md','REVIEW_CHECKLIST.md'):
            path=extracted/PAPER/name
            for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
                parsed=urlsplit(target)
                if parsed.scheme or not parsed.path:continue
                resolved=(path.parent/unquote(parsed.path)).resolve()
                resolved.relative_to(extracted)
                links.append(dict(file=name,target=target,exists=resolved.exists()))
        result['independent_relative_link_check']=dict(checked=len(links),missing=[x for x in links if not x['exists']],links=links)
        after={str(p.relative_to(extracted)):digest(p) for p in extracted.rglob('*') if p.is_file()}
        result['extracted_members_unchanged'] = initial == after
        result['archive_unchanged'] = digest(args.archive) == result['archive_sha256']
        result['status']='PASS' if (all(r['returncode']==0 and r.get('receipt',{}).get('status')=='PASS' and not r.get('file_access_audit',{}).get('denied',['missing']) for r in runs)
            and not mismatches and all(x['exists'] for x in links) and initial==after and result['archive_unchanged']) else 'FAIL'
    except Exception as exc:
        result['status']='BLOCKED'
        result['error']=type(exc).__name__+': '+str(exc)
    result['completed_utc']=datetime.now(timezone.utc).isoformat()
    result['scope'] = 'Fresh venv without system-site packages, Python isolated mode, new cwd, Python-level open allowlist; same local host and base Python, not OS/container isolation. Public arithmetic and artifact integrity only.'
    dump(results/'CLEAN_ROOM_RECEIPT.json',result)
    for path in results.iterdir():
        if path.is_file():
            target=HERE/path.name
            if target.exists(): raise FileExistsError('Preserve prior check receipts: '+str(target))
            shutil.copyfile(path,target)
    print(json.dumps(dict(status=result['status'],root=str(root),error=result.get('error'))),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--work-parent',type=Path,default=Path('C:/w'))
    sys.exit(run(parser.parse_args()))
