"""Separate freeze for exact multiplicity-preserving MAGIC execution."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib,json,re,subprocess
from pathlib import Path
from ..magic_reproduction import provenance as original

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ORIGINAL=HERE.parent/'magic_reproduction'
digest=original.digest
read=original.read


def files():
    return {str((HERE/name).relative_to(REPO)).replace('\\','/'):digest(HERE/name)
            for name in ['PROTOCOL.md','scoring.py','worker.py','provenance.py','launch.py','run_cloud.sh']}


def verify(registration,data_dir,source_dir):
    record=read(registration)
    if record['status']!='FROZEN_EXACT_MULTIPLICITY_RUNTIME' or record['code_hashes']!=files():
        raise ValueError('Compact runtime freeze changed')
    if (record.get('science_changed') is not False or record.get('exact_duplicate_storage_only') is not True
        or record.get('checkpoint_reuse') is not False or record.get('novelty_claimed') is not False
        or not re.fullmatch('[0-9a-f]{40}',record.get('source_commit',''))):
        raise ValueError('Compact runtime scope or source identity changed')
    path=ORIGINAL/'REGISTRATION.json'
    if digest(path)!=record['original_registration_sha256']:
        raise ValueError('Original registration changed')
    prior=original.verify_runtime(path,data_dir,source_dir)
    if prior['source_commit']!=record['original_source_commit']:
        raise ValueError('Original source identity changed')
    return record,prior


def register(data_dir,source_dir,registration):
    if Path(registration).exists():raise ValueError('Use a new registration')
    prior=original.verify_runtime(ORIGINAL/'REGISTRATION.json',data_dir,source_dir)
    sources=files()
    for rel,sha in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+rel],cwd=REPO)).hexdigest()!=sha:
            raise ValueError('Commit exact runtime bytes before registration')
    record={'status':'FROZEN_EXACT_MULTIPLICITY_RUNTIME','created_utc':datetime.now(timezone.utc).isoformat(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'code_hashes':sources,'original_registration_sha256':digest(ORIGINAL/'REGISTRATION.json'),
        'original_source_commit':prior['source_commit'],'science_changed':False,
        'exact_duplicate_storage_only':True,'checkpoint_reuse':False,'novelty_claimed':False}
    temporary=Path(registration).with_suffix('.tmp')
    with temporary.open('x',encoding='utf-8',newline='\n') as handle:
        handle.write(json.dumps(record,indent=2)+'\n')
    try:
        verify(temporary,data_dir,source_dir)
        temporary.rename(registration)
    finally:
        if temporary.exists():temporary.unlink()
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=HERE/'REGISTRATION.json')
    a=p.parse_args()
    r=register(a.data_dir,a.source_dir,a.registration)
    print(json.dumps({'status':r['status'],'code_files':len(r['code_hashes'])}))


if __name__=='__main__':main()
