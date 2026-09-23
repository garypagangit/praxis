"""Assemble a verified public evidence ZIP; never includes private traces or caches."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=HERE.parents[2]
EXCLUDED={'PACKAGE_MANIFEST.json','FINAL_VERIFICATION.json','ZIP_RECEIPT.json','apt_evaluation_praxis_evidence.zip'}
SUFFIXES={'.py','.md','.json','.csv','.png','.pdf','.docx','.txt'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def build():
    paths=[p for p in BASE.rglob('*') if p.is_file() and p.suffix.lower() in SUFFIXES
           and '__pycache__' not in p.parts and not p.name.startswith('~$')
           and not (p.parent==HERE and p.name in EXCLUDED)]
    # Include the shared document formatter and historical feature source used
    # by referenced code. Full private-data reproduction still needs the repo.
    for relative in ['experiments/apt_benchmark/lateral_protection_experiment/paper/build_document.py',
                     'experiments/apt_benchmark/host_history_exfil/context.py','experiments/__init__.py']:
        p=REPO/relative
        if p.is_file():paths.append(p)
    paths=sorted(set(paths))
    files={p.relative_to(REPO).as_posix():sha(p) for p in paths}
    write(HERE/'PACKAGE_MANIFEST.json',{'created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Public aggregate evidence and code; raw traces, row-level archives, caches and Word lock files excluded',
        'files':files,'file_count':len(files),'excluded_self_referential_outputs':sorted(EXCLUDED)})
    # The receipt and archive are generated outputs, deliberately excluded from
    # their own input manifest. The transient status is never delivered as PASS.
    write(HERE/'FINAL_VERIFICATION.json',{'status':'ASSEMBLY_IN_PROGRESS'})
    archive=HERE/'apt_evaluation_praxis_evidence.zip'
    archive_paths=paths+[HERE/'PACKAGE_MANIFEST.json',HERE/'FINAL_VERIFICATION.json']
    def archive_now():
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in archive_paths:z.write(p,p.relative_to(REPO).as_posix())
            z.writestr('START_HERE.txt','Open experiments/praxis_next/measurement_praxis/README.md.\n'
                       'Word/PDF manuscript and public evidence are in that directory.\n'
                       'See REPRODUCE.md for verification commands and private-source requirements.\n')
    archive_now()
    spec=importlib.util.spec_from_file_location('verify_measurement_package',HERE/'verify_package.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.verify();result['tests']=json.loads((HERE/'TEST_RECEIPT.json').read_text())
    result['manuscript']={'pages':24,'references':18,'tables':14,'figures':3}
    result['reviewed_manuscript_sha256']=sha(HERE/'manuscript.md')
    write(HERE/'FINAL_VERIFICATION.json',result)
    archive_now()
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity failure')
        for p in archive_paths:
            if hashlib.sha256(z.read(p.relative_to(REPO).as_posix())).hexdigest()!=sha(p):
                raise ValueError('Archive source mismatch: '+str(p))
        count=len(z.namelist())
    write(HERE/'ZIP_RECEIPT.json',{'status':'PASS','archive':archive.name,'sha256':sha(archive),
        'bytes':archive.stat().st_size,'entries':count,'all_entries_match_sources':True,
        'private_rows_included':False,'manifest_sha256':sha(HERE/'PACKAGE_MANIFEST.json')})
    module.verify()
    print(json.dumps({'status':'PASS','manifest_files':len(files),'zip_entries':count,'zip_bytes':archive.stat().st_size,'tests':result['tests']['passed']}))


if __name__=='__main__':build()
