"""Freeze the separately designed normal-calibrated MAGIC development study."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib,json,re,subprocess
from pathlib import Path
from ..magic_compact import provenance as compact

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ORIGINAL=HERE.parent/'magic_reproduction'
COMPACT=HERE.parent/'magic_compact'
digest=compact.digest
read=compact.read


def files():
    return {(HERE/name).relative_to(REPO).as_posix():digest(HERE/name) for name in
            ['PROTOCOL.md','config.json','worker.py','provenance.py','launch.py','run_cloud.sh']}


def verify_runtime(registration,data_dir,source_dir):
    record=read(registration)
    amendment,prior=compact.verify(COMPACT/'REGISTRATION.json',data_dir,source_dir)
    parents={str(path.relative_to(REPO)).replace('\\','/'):digest(path)
             for path in [ORIGINAL/'REGISTRATION.json',COMPACT/'REGISTRATION.json']}
    expected={**prior['code_hashes'],**amendment['code_hashes'],**files()}
    if (record['status']!='FROZEN_NORMAL_CALIBRATED_MAGIC_DEVELOPMENT'
        or record['code_hashes']!=expected or record['parent_registrations']!=parents
        or record['data_files']!=prior['data_files'] or record['upstream_files']!=prior['upstream_files']
        or record['source_manifest_sha256']!=prior['source_manifest_sha256']
        or record['original_source_commit']!=prior['source_commit']
        or record['compact_source_commit']!=amendment['source_commit']
        or record['upstream_commit']!=prior['upstream_commit'] or record['test_previously_exposed'] is not True
        or record['confirmation_claimed'] is not False or record['novelty_claimed'] is not False
        or not re.fullmatch('[0-9a-f]{40}',record['source_commit'])):
        raise ValueError('Calibrated source, data, parent chain or scope changed')
    return record


def register(data_dir,source_dir,registration):
    if Path(registration).exists():raise ValueError('Registration exists')
    amendment,prior=compact.verify(COMPACT/'REGISTRATION.json',data_dir,source_dir)
    own=files()
    for rel,sha in own.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+rel],cwd=REPO)).hexdigest()!=sha:
            raise ValueError('Commit exact calibrated source before freeze')
    record={'status':'FROZEN_NORMAL_CALIBRATED_MAGIC_DEVELOPMENT','created_utc':datetime.now(timezone.utc).isoformat(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'original_source_commit':prior['source_commit'],'compact_source_commit':amendment['source_commit'],
        'code_hashes':{**prior['code_hashes'],**amendment['code_hashes'],**own},
        'parent_registrations':{p.relative_to(REPO).as_posix():digest(p) for p in [ORIGINAL/'REGISTRATION.json',COMPACT/'REGISTRATION.json']},
        'data_files':prior['data_files'],'upstream_commit':prior['upstream_commit'],
        'upstream_files':prior['upstream_files'],'source_manifest_sha256':prior['source_manifest_sha256'],
        'test_previously_exposed':True,'confirmation_claimed':False,'novelty_claimed':False,
        'scope':'six fresh three-fit/one-calibration cases; no attack-label threshold selection'}
    temporary=Path(registration).with_suffix('.tmp')
    with temporary.open('x',encoding='utf-8',newline='\n') as handle:handle.write(json.dumps(record,indent=2)+'\n')
    try:
        verify_runtime(temporary,data_dir,source_dir)
        temporary.rename(registration)
    finally:
        if temporary.exists():temporary.unlink()
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=HERE/'REGISTRATION.json')
    a=p.parse_args();r=register(a.data_dir,a.source_dir,a.registration)
    print(json.dumps({'status':r['status'],'code_files':len(r['code_hashes'])}))


if __name__=='__main__':main()
