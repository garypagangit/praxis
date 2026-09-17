"""Package only explicit public research paths and this closure; no weights/private stores."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
EXCLUDE={'PACKAGE_MANIFEST.json','BUNDLE_RECEIPT.json'}

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def own_files():
    return [p for p in ROOT.rglob('*') if p.is_file() and p.name not in EXCLUDE and p.suffix not in {'.zip','.pyc'} and '__pycache__' not in p.parts and not p.name.endswith('.inspect.ndjson')]

def main():
    report={'scope':'Closure files only; source evidence separately indexed in SOURCE_FILES.json. This manifest excludes itself, the ZIP, and the bundle receipt.','files':[]}
    for p in sorted(own_files()):
        report['files'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size})
    (ROOT/'PACKAGE_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    sources=json.loads((ROOT/'SOURCE_FILES.json').read_text(encoding='utf-8'))['files']
    included={REPO/x['path'] for x in sources}
    prefixes=('final_praxis/papers/20260914/01_cti/', 'final_praxis/008_independent_evidence_audit/', 'final_praxis/010_d0_execution_20260915/', 'final_praxis/010_development_20260915/')
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode('utf-8').split('\0')
    for rel in tracked:
        if rel.startswith(prefixes): included.add(REPO/rel)
    included.update(own_files());included.add(ROOT/'PACKAGE_MANIFEST.json')
    archive=ROOT/'deliverables/Praxis_Three_Final_Package.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('START_HERE.md','# Three final experiment reports\n\nOpen final_praxis/final_three_20260917/README.md for papers, evidence, the 3-slide PowerPoint, and the offline human-review workflow. Open REVIEW_FORM.html in a browser.\n\nThe archive preserves repository paths. No human approvals are claimed.\n')
        for p in sorted(included):
            assert p.resolve().is_relative_to(REPO)
            assert p.is_file(),p
            z.write(p,p.relative_to(REPO).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for source in sources:
            assert hashlib.sha256(z.read(source['path'])).hexdigest()==source['sha256']
        entries=len(z.namelist())
    receipt={'status':'PASS','file':archive.relative_to(ROOT).as_posix(),'sha256':digest(archive),'bytes':archive.stat().st_size,'entries':entries,'source_files_verified_in_archive':len(sources),'crc_check':'PASS','exclusions':['model weights','private provider stores','private operational configuration','QA images and synthetic review fixtures'],'human_reviews_received':0}
    (ROOT/'BUNDLE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
