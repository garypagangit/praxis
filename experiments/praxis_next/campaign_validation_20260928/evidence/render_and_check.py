"""Export Office artifacts to PDF and verify their rendered structure."""
import json,subprocess,tempfile,zipfile
from pathlib import Path
import pymupdf
from PIL import Image
from lxml import etree

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'output/campaign_validation_20260928'
TMP=Path(tempfile.gettempdir())/'codex-presentations/campaign-validation-20260928/tmp'
QA=TMP/'qa';QA.mkdir(parents=True,exist_ok=True)
DOC='Gary_Pagan_Campaign_Validation_Addendum'
DECK='Gary_Pagan_Campaign_Validation_Defense_Addendum'
profile=QA/'lo-profile';profile.mkdir(exist_ok=True)
for filename,filter_name in [(DOC+'.docx','writer_pdf_Export'),(DECK+'.pptx','impress_pdf_Export')]:
    pdf_filter='pdf:'+filter_name+':'+json.dumps({'UseTaggedPDF':{'type':'boolean','value':'false'}})
    cmd=['C:/Program Files/LibreOffice/program/soffice.com','-env:UserInstallation='+profile.resolve().as_uri(),
         '--headless','--convert-to',pdf_filter,'--outdir',str(OUT),str(OUT/filename)]
    r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',
                     timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    print(r.stdout,r.stderr,flush=True)
assert (OUT/(DOC+'.pdf')).exists() and (OUT/(DECK+'.pdf')).exists()
counts={}
for name in [DOC,DECK]:
    pdf=pymupdf.open(OUT/(name+'.pdf'));counts[name]=len(pdf)
    folder=QA/name;folder.mkdir(exist_ok=True)
    for i,page in enumerate(pdf):
        page.get_pixmap(dpi=120).save(folder/f'page-{i+1}.png')
    # Visual review uses every full-size page; montage is only navigation.
    ims=[]
    for i in range(len(pdf)):
        im=Image.open(folder/f'page-{i+1}.png');im.thumbnail((425,550));ims.append(im.copy())
    w=max(im.width for im in ims);h=max(im.height for im in ims)
    panel=Image.new('RGB',(w*3,h*((len(ims)+2)//3)), 'white')
    for i,im in enumerate(ims):panel.paste(im,((i%3)*w,(i//3)*h))
    panel.save(QA/(name+'_contact.png'))
    for i,page in enumerate(pdf):
        for block in page.get_text('blocks'):
            assert block[0]>=-1 and block[1]>=-1 and block[2]<=page.rect.width+1 and block[3]<=page.rect.height+1,(name,i,block)
    if name==DOC:
        txt='\n'.join(p.get_text() for p in pdf)
        for token in ['1,067,211','2,397,158','3,465,342','3466-3482']:
            assert token in txt,token
        assert all(p.get_text().strip() for p in pdf)
    else:
        slides=json.loads((TMP/'slide-content.json').read_text(encoding='utf-8'))
        assert len(pdf)==len(slides)==5
        for i,c in enumerate(slides):
            text=''.join(pdf[i].get_text().split())
            assert ''.join(c['title'].split()) in text,(i,c['title'])
            for body in c['body']:assert ''.join(body.split()) in text,(i,body)
for name in [DOC+'.docx',DECK+'.pptx']:
    with zipfile.ZipFile(OUT/name) as z:
        assert z.testzip() is None
        if name.endswith('.pptx'):
            ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
            slidefiles=[n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
            notes=[n for n in z.namelist() if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml')]
            assert len(slidefiles)==5 and len(notes)==5
            for n in slidefiles:
                tree=etree.fromstring(z.read(n))
                text_frames=[]
                for shape in tree.findall('.//p:sp',ns):
                    text=''.join(shape.xpath('.//a:t/text()',namespaces=ns))
                    if shape.find('.//p:ph',ns) is not None:assert text.strip(),(n,'empty placeholder')
                    assert not any(x in text for x in ['Click to','Explain the methodology','Quantitative/qualitative']),text
                    transform=shape.find('./p:spPr/a:xfrm',ns)
                    if text.strip() and transform is not None:
                        off=transform.find('a:off',ns);ext=transform.find('a:ext',ns)
                        if off is not None and ext is not None:
                            text_frames.append((int(off.get('x')),int(off.get('y')),int(ext.get('cx')),int(ext.get('cy')),text[:60]))
                for i,a in enumerate(text_frames):
                    for b in text_frames[i+1:]:
                        ox=min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])
                        oy=min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])
                        assert not(ox>0 and oy>0),(n,'overlapping text frames',a[4],b[4])
result={'status':'structural_pass_visual_review_pending','page_counts':counts,'qa_directory':str(QA)}
(ROOT/'DOCUMENT_QA.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
