import json,hashlib,subprocess,zipfile
from pathlib import Path
import pymupdf
from lxml import etree
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1]
OUT=BASE/'output/praxis_committee_review_20260928';QA=Path('C:/w/praxis_committee_review_20260928_qa')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pdf=OUT/'Gary_Pagan_Final_Praxis.pdf'
pdfdoc=pymupdf.open(pdf)
assert len(pdfdoc)==155
for n in [12,13,154]:
 page=pdfdoc[n];footer=page.get_text(clip=pymupdf.Rect(0,page.rect.height-55,page.rect.width,page.rect.height)).strip()
 assert footer==str(n-11),(n,footer)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(OUT/'Gary_Pagan_Final_Praxis.docx') as z:
 assert z.testzip() is None
 body=etree.fromstring(z.read('word/document.xml')).find('w:body',ns)
 paragraphs=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in body.findall('.//w:p',ns)]
 text='\n'.join(paragraphs)
 assert text.count('Linear notation:')==25
 assert text.rstrip().endswith('their metrics are not pooled with this different task.')
 footer_values=[]
 for n in z.namelist():
  if n.startswith('word/footer') and n.endswith('.xml'):footer_values+=etree.fromstring(z.read(n)).xpath('.//w:t/text()',namespaces=ns)
 assert not any(x.strip() for x in footer_values)
 (OUT/'Gary_Pagan_Final_Praxis_Accessible.txt').write_text(text,encoding='utf-8')
full=' '.join(('\n'.join(p.get_text() for p in pdfdoc)).split())
assert full.count('Linear notation:')==25
for t in ['Out-of-Fold','Domain Name System','Message-Digest','Secure Hash','Cyclic Redundancy','predicted_u','initially completed','supplemented on September 28','Figure 4-9']:
 assert t in full,t
assert 'Certification pending' not in full and 'Praxis direction and committee confirmation pending' not in full
old=pymupdf.open(BASE/'output/praxis_integrated_20260928/Gary_Pagan_Final_Praxis.pdf')
def im(p):
 pix=p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5));return Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
def key(i):return hashlib.sha256(i.crop((0,0,i.width,i.height-90)).tobytes()).hexdigest()
oldkeys={key(im(p)):n+1 for n,p in enumerate(old)}
changed=[];unchanged=[]
for n,p in enumerate(pdfdoc):
 pic=im(p);pic.save(QA/f'corrected_{n+1:03d}.png')
 k=key(pic)
 if k in oldkeys:unchanged.append({'page':n+1,'previous_page':oldkeys[k]})
 else:changed.append(n+1)
 for b in p.get_text('blocks'):assert b[0]>=-1 and b[1]>=-1 and b[2]<=p.rect.width+1 and b[3]<=p.rect.height+1,(n+1,b)
panels=[]
for start in range(0,len(changed),2):
 nums=changed[start:start+2];ims=[Image.open(QA/f'corrected_{n:03d}.png') for n in nums]
 canvas=Image.new('RGB',(sum(i.width for i in ims),max(i.height for i in ims)+25),'white');x=0
 for n,i in zip(nums,ims):canvas.paste(i,(x,25));ImageDraw.Draw(canvas).text((x+12,6),f'PAGE {n}',fill='black');x+=i.width
 name=QA/f'check_{start//2+1:02d}.png';canvas.save(name);panels.append({'path':str(name),'pages':nums})
result={'status':'STRUCTURAL_PASS_VISUAL_PENDING','pages':len(pdfdoc),'equations_extractable':25,'footer_cache_sequence_absent':True,'live_page_fields_recalculated_and_numbering_verified':True,'body_ends_at_E5':True,'unchanged_pages':unchanged,'changed_pages':changed,'panels':panels,'docx_sha256':sha(OUT/'Gary_Pagan_Final_Praxis.docx'),'pdf_sha256':sha(pdf)}
(ROOT/'COMMITTEE_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps({'pages':len(pdfdoc),'unchanged':len(unchanged),'changed':changed,'panels':len(panels)}))
