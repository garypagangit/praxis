"""Package the reviewed paper, one-page summary and bounded new evidence."""
import hashlib,json,re,shutil,zipfile
from datetime import datetime,timezone
from pathlib import Path
from lxml import etree
import fitz
H=Path(__file__).resolve().parent;O=H/'delivery';B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
qa=json.loads((H/'CONTENT_QA.json').read_text());visual=json.loads((H/'VISUAL_REVIEW.json').read_text())
assert qa['status']=='PASS' and visual['status']=='REVIEWED'
pdfpath=O/'Gary_Pagan_Praxis_Review.pdf';assert visual['pdf_sha256']==sha(pdfpath)
docx=O/'Gary_Pagan_Praxis_Review.docx';ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
with zipfile.ZipFile(docx) as z:parts={n:z.read(n) for n in z.namelist()}
cleared=[]
for name,value in list(parts.items()):
    if name.startswith('word/footer') and name.endswith('.xml'):
        root=etree.fromstring(value)
        if any('PAGE' in t for t in root.xpath('.//w:instrText/text()',namespaces=ns)):
            for t in root.findall('.//w:t',ns):
                if t.text and re.fullmatch(r'[ivxlcdm]+|\d+',t.text.strip()):cleared.append(t.text);t.text=''
            for field in root.findall('.//w:fldChar',ns):
                if field.get(W+'fldCharType')=='begin':field.set(W+'dirty','true')
            parts[name]=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
settings=etree.fromstring(parts['word/settings.xml']);u=settings.find('w:updateFields',ns)
if u is None:u=etree.SubElement(settings,W+'updateFields')
u.set(W+'val','true');parts['word/settings.xml']=etree.tostring(settings,xml_declaration=True,encoding='UTF-8',standalone=True)
with zipfile.ZipFile(docx,'w',zipfile.ZIP_DEFLATED) as z:
    for name,value in parts.items():z.writestr(name,value)
with zipfile.ZipFile(docx) as z:assert z.testzip() is None
pdf=fitz.open(pdfpath);ix=next(i for i,p in enumerate(pdf) if 'Executive Summary' in p.get_text())
assert ix==4 and 'What the Praxis delivers.' in pdf[ix].get_text()
summary=fitz.open();summary.insert_pdf(pdf,from_page=ix,to_page=ix);summary.save(O/'Executive_Summary.pdf');summary.close()
for src,dst in [(H/'executive_summary.md','Executive_Summary.md'),(H/'REVIEW_READINESS.md','Review_Readiness.md'),(B/'warning_transitions_20261004/FINDINGS.md','PX106_Findings.md'),(B/'warning_transitions_20261004/RESULTS.csv','PX106_Results.csv')]:shutil.copy2(src,O/dst)
p=O/'PX106_Findings.md';p.write_text(p.read_text(encoding='utf-8').replace('../gwu_revision_20261004/REVIEW_READINESS.md','Review_Readiness.md'),encoding='utf-8')
with zipfile.ZipFile(O/'PX106_Evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((B/'warning_transitions_20261004').iterdir()):
        if p.is_file():z.write(p,p.name)
source_files=[H/n for n in ['manuscript.md','abstract.md','executive_summary.md','revise.py','build.py','check.py','package.py','CONTENT_QA.json','VISUAL_REVIEW.json','FORMAT_REFERENCES.json','EXPERIMENT_VERIFICATION.json']]
for folder in ['explanation_trials_20261003','warning_budget_20261003','bot_review_20261003','diagnosis_novelty_20261003','warning_transitions_20261004']:
    source_files += [p for p in (B/folder).iterdir() if p.is_file() and p.name in ['AUDIT.json','INDEPENDENT_AUDIT.json','PROTOCOL.md','FREEZE.json','RESULTS.json','PX100_RESULTS.json','PX101_RESULTS.json']]
manifest={'title':'When Better APT Scores Hide Missed Attack Warnings','edition':'2026-10-04','status':'AUTHOR_AND_COMMITTEE_REVIEW','pages':len(pdf),'new_experiment':'PX-106','new_fits_this_revision':0,'new_paid_compute_this_revision':False,'no_writing_detector_evaluation':True,'footer_caches_cleared':cleared,'delivery_hashes':{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='FINAL_MANIFEST.json'},'source_hashes':{str(p.relative_to(B)):sha(p) for p in source_files}}
(O/'FINAL_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
dest=Path('C:/Users/garyp/OneDrive/Documents/codex/output/praxis_revision_20261004');dest.mkdir(parents=True,exist_ok=True)
for p in O.iterdir():
    if p.is_file():shutil.copy2(p,dest/p.name);assert sha(p)==sha(dest/p.name)
print(json.dumps({'pages':len(pdf),'summary_pages':1,'delivery':str(dest),'files':list(manifest['delivery_hashes'])},indent=2))
