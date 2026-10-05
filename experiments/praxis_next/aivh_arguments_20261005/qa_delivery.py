"""Render page contact sheets and extract complete text including tables."""
import json
from pathlib import Path
import fitz
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'output/doc/aivh_praxis';TMP=ROOT/'tmp/docs/px119';TMP.mkdir(parents=True,exist_ok=True)
d=fitz.open(OUT/'Gary_Pagan_AI_Operator_Praxis.pdf');pages=[]
for i,p in enumerate(d):
    pix=p.get_pixmap(matrix=fitz.Matrix(.7,.7));im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    pages.append(im)
for start in range(0,len(pages),6):
    sheet=Image.new('RGB',(3*440,2*580),'#cccccc');draw=ImageDraw.Draw(sheet)
    for n,im in enumerate(pages[start:start+6]):
        x=n%3*440;y=n//3*580;sheet.paste(im,(x,y+18));draw.text((x+4,y+2),f'Page {start+n+1}',fill='black')
    sheet.save(TMP/f'sheet_{start//6+1}.png')
text='\n\n'.join(f'--- PDF PAGE {i+1} ---\n'+p.get_text() for i,p in enumerate(d))
(OUT/'Manuscript_Text.txt').write_text(text,encoding='utf-8')
assert '@@TOC@@' not in text and '@@FIGURES@@' not in text
report={'pages':len(d),'page_word_counts':[len(p.get_text().split()) for p in d],'markers_absent':True,'contact_sheets':str(TMP),'visual_review':'PENDING'}
(HERE/'DOCUMENT_QA.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
