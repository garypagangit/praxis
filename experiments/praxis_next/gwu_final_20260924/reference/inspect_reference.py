"""Read-only structural inspection of the user's original GWU praxis reference."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile
from docx import Document
from docx.oxml.ns import qn
from PIL import Image

HERE=Path(__file__).resolve().parent
ORIGINAL=Path('C:/Users/garyp/Downloads/Gary Pagan GWU DEng GML to Detect APT Final 04012026 AIRv02.docx')
QA=Path('C:/w/gwu_reference_qa_20260924')
TEMPLATE=QA/'DEng_Praxis_Template_Online_Programs_Rev_2026.docx'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inherited(style,attribute,part='font'):
    seen=set()
    while style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        value=getattr(getattr(style,part),attribute)
        if value is not None:
            if hasattr(value,'pt'):return value.pt
            return value if isinstance(value,(int,float,str,bool)) else str(value)
        style=style.base_style
    return None


def structure(path):
    document=Document(path)
    sections=[]
    for i,section in enumerate(document.sections):
        numbering=section._sectPr.find(qn('w:pgNumType'))
        sections.append(dict(index=i,page_inches=[section.page_width.inches,section.page_height.inches],
            margins_inches={side:getattr(section,side+'_margin').inches for side in ('left','right','top','bottom')},
            header_distance_inches=section.header_distance.inches,footer_distance_inches=section.footer_distance.inches,
            start_type=str(section.start_type),different_first_page=section.different_first_page_header_footer,
            page_numbering={k.rsplit('}',1)[-1]:v for k,v in numbering.attrib.items()} if numbering is not None else None,
            header_references=len(section._sectPr.findall(qn('w:headerReference'))),
            footer_references=len(section._sectPr.findall(qn('w:footerReference')))))
    styles={}
    for name in ('Normal','Default','Chapter Heading','Heading 1','Heading 2','Heading 3','Caption','toc 1'):
        try:s=document.styles[name]
        except KeyError:continue
        styles[name]=dict(base_style=s.base_style.name if s.base_style else None,
            font=inherited(s,'name'),font_size_pt=inherited(s,'size'),bold=inherited(s,'bold'),
            line_spacing=inherited(s,'line_spacing','paragraph_format'),
            space_before_pt=inherited(s,'space_before','paragraph_format'),
            space_after_pt=inherited(s,'space_after','paragraph_format'),
            alignment=inherited(s,'alignment','paragraph_format'))
    headings=[dict(paragraph=i,style=p.style.name,text=p.text) for i,p in enumerate(document.paragraphs)
              if p.text.strip() and (p.style.name.startswith('Heading') or p.style.name=='Chapter Heading')]
    with zipfile.ZipFile(path) as archive:
        media=[dict(member=n,bytes=archive.getinfo(n).file_size,sha256=hashlib.sha256(archive.read(n)).hexdigest())
               for n in archive.namelist() if n.startswith('word/media/')]
    return document,dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),
        paragraphs=len(document.paragraphs),tables=len(document.tables),inline_images=len(document.inline_shapes),
        sections=sections,styles=styles,headings=headings,media=media)


def main():
    original_sha=sha(ORIGINAL)
    doc,original=structure(ORIGINAL)
    _,template=structure(TEMPLATE)
    paragraph=doc.paragraphs[353]
    rid=paragraph._p.xpath('.//a:blip')[0].get(qn('r:embed'))
    part=doc.part.related_parts[rid]
    QA.mkdir(exist_ok=True)
    target=QA/'original_gmr.png'
    if target.exists() and target.read_bytes()!=part.blob:raise ValueError('Existing extracted figure differs')
    target.write_bytes(part.blob)
    size=Image.open(target).size
    extent=paragraph._p.xpath('.//wp:extent')[0]
    gmr=dict(expansion='Graphical Model of Research',definition_paragraph=223,description_paragraph=352,
        image_paragraph=353,caption_paragraph=354,reference_number='Figure 3-1',
        relation_id=rid,docx_member=str(part.partname),path=str(target),sha256=sha(target),pixels=list(size),
        displayed_inches=[int(extent.get('cx'))/914400,int(extent.get('cy'))/914400],
        original_usable_body_width_inches=6.0,
        layout='Six numbered cards, three columns by two rows; each card contains What, Why and How',
        header_colors='Teal variants for1-4, gold5, green6',
        stage_titles=['Data Collection & EDA','Preprocessing & Feature Engineering','Graph Construction from Flow Data',
            'Train Five GML Architectures','Hyperparameter Tuning (Optuna)','Model Evaluation & Comparison'],
        reuse='Exact historical figure only; current-study GMR must replace historical graph/Optuna/Soh content')
    identity=dict(author='Gary Pagan',degrees=[doc.paragraphs[i].text for i in (9,10)],
        original_title=doc.paragraphs[1].text,original_cover_date=doc.paragraphs[20].text,
        director_line=doc.paragraphs[23].text,historical_committee=[doc.paragraphs[i].text for i in (35,36,37)],
        approval_status='Not established by this inspection; do not carry historical certification or approval claim forward',
        certification_date_conflict='Original cover says April01,2026; certification paragraph says April01,2025')
    result=dict(status='REFERENCE_IDENTIFIED_AND_INSPECTED',utc=datetime.now(timezone.utc).isoformat(),
        source_code_sha256=sha(__file__),original=original,current_official_template=template,identity=identity,gmr=gmr,
        source_original_unchanged=sha(ORIGINAL)==original_sha,
        visual_review=dict(rendered_pdf=str(QA/(ORIGINAL.stem+'.pdf')),rendered_pages=114,
            inspected_original_pages=[1,2,16,34],gmr_viewed_at_original_resolution=True,
            scope='Selected reference-layout pages and exact figure, not full scientific review of114pages',
            observed_issues=['No footer page numbers on inspected original pages',
                'LibreOffice expands original GMR caption/reference as Figure Chapter3-Methodology-5',
                'GMR width6.653in exceeds6in body width and its text is small at portrait scale']))
    (HERE/'REFERENCE_SPEC.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],original_sha256=original_sha,gmr_path=str(target),
        template_sha256=template['sha256'],original_unchanged=result['source_original_unchanged'])))


if __name__=='__main__':main()
