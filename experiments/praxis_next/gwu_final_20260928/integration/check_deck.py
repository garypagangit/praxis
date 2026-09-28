import json, subprocess, zipfile
from pathlib import Path
import pymupdf
from PIL import Image
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'output/praxis_integrated_20260928'
QA=Path('C:/w/praxis_integrated_20260928_qa/deck');QA.mkdir(parents=True,exist_ok=True)
name='Gary_Pagan_GWU_Praxis_Defense'
profile=QA/'lo-profile'
cmd=['C:/Program Files/LibreOffice/program/soffice.com','-env:UserInstallation='+profile.resolve().as_uri(),'--headless','--convert-to','pdf:impress_pdf_Export:{"UseTaggedPDF":{"type":"boolean","value":"false"}}','--outdir',str(OUT),str(OUT/(name+'.pptx'))]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW);print(r.stdout,r.stderr,flush=True)
pdf=pymupdf.open(OUT/(name+'.pdf'));content=json.loads((ROOT/'DEFENSE_CONTENT.json').read_text(encoding='utf-8'))
assert len(pdf)==len(content)==37
for i,(page,c) in enumerate(zip(pdf,content)):
 text=''.join(page.get_text().split())
 for s in [c['title']]+c['body']:assert ''.join(s.split()) in text,(i+1,s)
 assert '[objectObject]' not in text
 for b in page.get_text('blocks'):assert b[0]>=-1 and b[1]>=-1 and b[2]<=page.rect.width+1 and b[3]<=page.rect.height+1,(i+1,b)
 page.get_pixmap(matrix=pymupdf.Matrix(4/3,4/3)).save(QA/f'slide_{i+1:02d}.png')
for start in range(0,len(pdf),4):
 panel=Image.new('RGB',(1920,1440),'white')
 for n in range(start,min(start+4,len(pdf))):
  im=Image.open(QA/f'slide_{n+1:02d}.png');panel.paste(im,((n-start)%2*960,(n-start)//2*720))
 panel.save(QA/f'review_{start//4+1:02d}.png')
with zipfile.ZipFile(OUT/(name+'.pptx')) as z:
 assert z.testzip() is None
 notes=[n for n in z.namelist() if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml')]
 assert len(notes)==37
 for n in notes:assert b'Evidence:' in z.read(n)
result={'status':'structural_pass_visual_review_pending','slides':37,'main_slides':25,'backup_slides':12,'notes':37,'all_title_and_body_text_present_in_pdf':True,'no_text_outside_pages':True,'zip_crc_pass':True}
(ROOT/'DECK_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
