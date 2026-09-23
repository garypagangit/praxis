"""Read-only verification of the complete public manuscript/evidence package."""
from pathlib import Path
import argparse
from datetime import datetime,timezone
import hashlib
import json
import re
from urllib.parse import unquote,urlsplit

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=HERE.parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def verify():
    manifest=read(HERE/'PACKAGE_MANIFEST.json');checks=[]
    for relative,expected in manifest['files'].items():
        path=(REPO/relative).resolve()
        path.relative_to(REPO)
        if sha(path)!=expected:raise ValueError('Artifact hash mismatch: '+relative)
    checks.append({'name':'manifest_hashes','passed':True,'files':len(manifest['files'])})
    paired=read(HERE/'evidence/paired_reanalysis/AUDIT.json')
    public=read(HERE/'evidence/paired_reanalysis/PUBLIC_VERIFICATION.json')
    pub=read(HERE/'evidence/paired_reanalysis/PUBLICATION_AUDIT.json')
    qual=read(HERE/'evidence/qualification_audit/VERIFICATION.json')
    if not (paired['status']==public['status']==pub['status']=='PASS' and qual['all_registered_verification_checks_passed']):
        raise ValueError('A computational audit did not pass')
    if paired['paired_comparisons']!=36 or public['private_files_opened']!=0:raise ValueError('Audit scope mismatch')
    checks.append({'name':'completed_computational_audits','passed':True,'paired_comparisons':36})
    render=read(HERE/'RENDER_RECEIPT.json')
    for name,key in [('manuscript.md','manuscript_sha256'),('apt_evaluation_praxis.docx','docx_sha256'),('apt_evaluation_praxis.pdf','pdf_sha256')]:
        if sha(HERE/name)!=render[key]:raise ValueError('Rendered artifact mismatch: '+name)
    if render['visual_review']!='PASS' or any(x['out_of_page_text_lines'] for x in render['geometry_checks']):
        raise ValueError('Render review incomplete')
    build=read(HERE/'BUILD_RECEIPT.json')
    if sha(HERE/'manuscript.md')!=build['manuscript_sha256']:raise ValueError('Manuscript source mismatch')
    if sha(HERE/'build_paper.py')!=build['source_sha256']:raise ValueError('Assembly source mismatch')
    for relative,expected in build['inputs'].items():
        if sha(BASE/relative)!=expected:raise ValueError('Manuscript input changed: '+relative)
    checks.append({'name':'paper_assembly_render_and_visual_review','passed':True,'pages':render['pages']})
    links=0
    for file in [HERE/'manuscript.md',HERE/'README.md',HERE/'EVIDENCE_INDEX.md',HERE/'REPRODUCE.md',HERE/'REVIEW_CHECKLIST.md']:
        text=file.read_text(encoding='utf-8')
        if '{{' in text:raise ValueError('Unresolved template placeholder')
        for target in re.findall(r'\]\(([^)]+)\)',text):
            url=urlsplit(target)
            if url.scheme or not url.path:continue
            if not (file.parent/unquote(url.path)).exists():raise ValueError('Missing local link: '+target)
            links+=1
    checks.append({'name':'manuscript_and_handoff_local_links','passed':True,'links':links})
    return {'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),'manifest_sha256':sha(HERE/'PACKAGE_MANIFEST.json'),
        'checks':checks,'new_model_fits':0,'new_aws_spend_usd':0,
        'scope':'Complete bounded measurement manuscript and aggregate evidence; not independent-campaign or institutional approval.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',type=Path);args=ap.parse_args()
    if args.receipt and args.receipt.exists():raise ValueError('Use a new receipt path; existing evidence is preserved')
    result=verify();encoded=json.dumps(result,indent=2)+'\n'
    if args.receipt:args.receipt.write_text(encoded,encoding='utf-8')
    print(encoded)
