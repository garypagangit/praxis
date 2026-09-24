"""Package the final GWU edition while preserving the previous evidence archive."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
import hashlib
import json
import re
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = HERE.parent
ARCHIVE = HERE / 'gwu_praxis_final_evidence.zip'
MANIFEST = HERE / 'FINAL_MANIFEST.json'
RECEIPT = HERE / 'PACKAGE_RECEIPT.json'
OLD = BASE / 'submission_readiness/praxis_review_bundle.zip'
OLD_SHA = '5c27853e2fa81f2cc9cc2bddcbec8dc9f3cd17ecedaed2467dd225942bd3d1a5'
OUTPUTS = [REPO / 'output/doc/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.docx',
           REPO / 'output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build():
    assert sha(OLD.read_bytes()) == OLD_SHA
    original = json.loads((BASE / 'measurement_praxis/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for name, expected in original['files'].items():
        assert sha((REPO/name).read_bytes()) == expected, ('Changed original evidence', name)
    review=json.loads((BASE/'submission_readiness/REVIEW_MANIFEST.json').read_text(encoding='utf-8'))
    for name,expected in review['source_bindings'].items():
        assert sha((REPO/name).read_bytes())==expected,('Changed prior review source',name)
    payload = {}
    with zipfile.ZipFile(OLD) as z:
        for name in z.namelist():
            if not name.endswith('/'):
                payload[name] = z.read(name)
    prior_count = len(payload)
    prior_hashes = {name: sha(data) for name,data in payload.items()}
    ignored = {ARCHIVE, MANIFEST, RECEIPT, HERE/'FINAL_VERIFICATION.json'}
    sources = [p for p in HERE.rglob('*') if p.is_file() and p not in ignored
               and '__pycache__' not in p.parts and not p.name.startswith('~$')]
    sources += OUTPUTS
    for source in sources:
        assert source.is_file(), source
        payload[source.relative_to(REPO).as_posix()] = source.read_bytes()
    # Include repository-linked public files needed to inspect this edition.
    # Raw source traces and row-level model outputs are deliberately not inferred from code.
    queue = [name for name in payload if name.endswith('.md') and 'gwu_final_20260924/' in name]
    inspected = set()
    while queue:
        name = queue.pop()
        if name in inspected:
            continue
        inspected.add(name)
        content = payload[name].decode('utf-8-sig')
        for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', content):
            if urlsplit(target).scheme or target.startswith('#'):
                continue
            path = ((REPO/name).parent/target.split('#')[0]).resolve()
            assert path.is_relative_to(REPO), ('External source link', name, target)
            if path==MANIFEST:
                continue  # Added after the other payload hashes are frozen.
            if path.is_dir():
                continue
            assert path.is_file(), ('Missing local source link', name, target)
            key = path.relative_to(REPO).as_posix()
            if key not in payload:
                assert path.suffix.lower() in {'.md','.json','.py','.csv','.png','.pdf','.docx','.svg','.txt'}, key
                payload[key] = path.read_bytes()
                if key.endswith('.md'):
                    queue.append(key)
    for name, expected in prior_hashes.items():
        assert sha(payload[name]) == expected, ('Changed previous archive member', name)
    readme = '''FINAL GWU-STYLE PRAXIS — SEPTEMBER 24, 2026

Start with:
  output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf
  output/doc/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.docx

Current manuscript, references, figures, complete tables, build code and review receipts:
  experiments/praxis_next/gwu_final_20260924/

The prior review package is preserved at its original repository-relative paths.
Its START_HERE_REVIEW.txt and the original START_HERE.txt describe earlier editions.
The final edition adds GWU chapter organization, GMR images, model mathematics,
full result reporting and visual verification. It does not add model fits.

588 configurations are evaluated views, not independent campaigns. The main
flow study is one previously examined campaign. Secondary technique-policy
results use different targets and are kept separate. Raw traces and private
row-linked predictions are not distributed. Administrative approval is not asserted.

Verify every archive member against FINAL_MANIFEST.json in the edition folder.
'''
    payload['START_HERE_GWU.txt'] = readme.encode('utf-8')
    manifest = {'schema_version':1, 'created_utc':datetime.now(timezone.utc).isoformat(),
                'previous_review_archive_sha256':OLD_SHA,
                'previous_review_members_preserved':prior_count,
                'original_manifest_artifacts_preserved':len(original['files']),
                'review_source_bindings_preserved':len(review['source_bindings']),
                'files':{name:sha(data) for name,data in sorted(payload.items())}}
    data = (json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    MANIFEST.write_bytes(data)
    payload[MANIFEST.relative_to(REPO).as_posix()] = data
    with zipfile.ZipFile(ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(payload.items()):
            z.writestr(name,data)
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(payload)
        for name,expected in manifest['files'].items():
            assert sha(z.read(name))==expected,name
    receipt = {'created_utc':datetime.now(timezone.utc).isoformat(),
               'status':'PASS', 'archive':ARCHIVE.relative_to(REPO).as_posix(),
               'archive_sha256':sha(ARCHIVE.read_bytes()),'bytes':ARCHIVE.stat().st_size,
               'members':len(payload),'verified_manifest_entries':len(manifest['files']),
               'previous_review_members_preserved':prior_count,
               'original_manifest_artifacts_preserved':len(original['files']),
               'review_source_bindings_preserved':len(review['source_bindings']),
               'scope':'Final documents and public aggregate evidence; no additional model fitting'}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    build()
