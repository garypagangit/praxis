"""Identify unchanged rendered paper pages and prepare complete visual review panels."""
import hashlib,json
from pathlib import Path
import pymupdf
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]/'output'
QA=Path('C:/w/praxis_integrated_20260928_qa/paper')
old=pymupdf.open(BASE/'praxis_final_20260927/Gary_Pagan_Final_Praxis.pdf')
new=pymupdf.open(BASE/'praxis_integrated_20260928/Gary_Pagan_Final_Praxis.pdf')
def picture(page):
    p=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5))
    return Image.frombytes('RGB',[p.width,p.height],p.samples)
def key(im):
    # Only the footer page number is masked; all body content and geometry remain.
    q=im.crop((0,0,im.width,im.height-90))
    return (im.width,im.height,hashlib.sha256(q.tobytes()).hexdigest())
oldkeys={key(picture(p)):i+1 for i,p in enumerate(old)}
unchanged=[];changed=[]
for i,p in enumerate(new):
    im=Image.open(QA/f'page_{i+1:03d}.png').convert('RGB')
    match=oldkeys.get(key(im))
    if match:unchanged.append({'new_page':i+1,'previously_reviewed_page':match})
    else:changed.append(i+1)
panels=[]
for j in range(0,len(changed),2):
    ns=changed[j:j+2];ims=[Image.open(QA/f'page_{n:03d}.png').convert('RGB') for n in ns]
    canvas=Image.new('RGB',(sum(im.width for im in ims),max(im.height for im in ims)+25),'white')
    x=0
    for n,im in zip(ns,ims):
        canvas.paste(im,(x,25));ImageDraw.Draw(canvas).text((x+12,6),f'PAGE {n}',fill='black');x+=im.width
    path=QA/f'review_{j//2+1:02d}.png';canvas.save(path)
    panels.append({'file':str(path),'pages':ns})
receipt=json.loads((ROOT/'RENDER_RECEIPT.json').read_text())
assert not receipt['marker_tokens_remaining']
assert not any(p['outside_page'] for p in receipt['geometry'])
text='\n'.join(p.get_text() for p in new)
for token in ['1,067,211','3,465,342','1,245','0.993970','0.946233','Appendix E','197']:
    assert token in text,token
out={'pages':len(new),'unchanged_body_pages':unchanged,'changed_pages':changed,'review_panels':panels,'geometry':'PASS'}
(ROOT/'PAPER_VISUAL_REVIEW.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'pages':len(new),'unchanged':len(unchanged),'changed':changed,'panels':len(panels),'tables':receipt['tables'],'captions':[(x['number'],x['title']) for x in receipt['caption_inventory'] if x['number'] in ['3-10','4-15','4-16','4-17'] or x['number'].startswith('E-')]},indent=2))
