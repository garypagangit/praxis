"""Finalize editable footer fields, summary extract and delivery hashes."""
import hashlib,json,re,shutil,zipfile
from pathlib import Path
from lxml import etree
import fitz
H=Path(__file__).resolve().parent;O=H/'delivery';ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}'
docx=O/'Gary_Pagan_Final_Praxis.docx'
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
pdf=fitz.open(O/'Gary_Pagan_Final_Praxis.pdf');summary=fitz.open();ix=next(i for i,p in enumerate(pdf) if 'Executive Summary' in p.get_text());assert ix==4;summary.insert_pdf(pdf,from_page=ix,to_page=ix);summary.save(O/'Executive_Summary.pdf');summary.close()
shutil.copy2(H/'executive_summary.md',O/'Executive_Summary.md')
source_files=[H/'manuscript.md',H/'abstract.md',H/'executive_summary.md',H/'CONTENT_QA.json',H/'EDITORIAL_RECEIPT.json']
for folder in ['or_gate_20260930','heterogeneous_gate_20260930','soc_workload_20261001','missed_episode_20261001','ssh_policy_20261001','ssh_transfer_20261001']:
    for name in ['PROTOCOL.md','FREEZE.json','AUDIT.json','VALIDATION.json','RESULTS.json.gz','RESULTS.csv','FINDINGS.md']:
        p=H.parent/folder/name
        if p.exists():source_files.append(p)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'title':'When Better APT Scores Hide Missed Attack Warnings','edition':'2026-10-01','pages':len(pdf),'prior_edition':'gwu_final_20260928','new_experiments':['PX-092','PX-093','PX-094','PX-095','PX-096','PX-097'],'footer_page_caches_cleared':cleared,'files':{p.name:sha(p) for p in O.iterdir() if p.is_file()},'source_hashes':{str(p.relative_to(H.parent)):sha(p) for p in source_files},'new_fits':0}
(O/'FINAL_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
dest=Path('C:/Users/garyp/OneDrive/Documents/codex/output/praxis_revision_20261001');dest.mkdir(parents=True,exist_ok=True)
for p in O.iterdir():
    if p.is_file():shutil.copy2(p,dest/p.name);assert sha(p)==sha(dest/p.name)
print(json.dumps({'pages':len(pdf),'summary_pages':1,'delivery':str(dest),'footer_caches_cleared':len(cleared)}))
