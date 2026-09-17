"""Verify all three claim ledgers, paper links, and final Office structure offline."""
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]

def pointer(data, p):
    if not p: return data
    for key in p.lstrip('/').split('/'):
        key=key.replace('~1','/').replace('~0','~')
        data=data[int(key)] if isinstance(data,list) else data[key]
    return data

def walk(value):
    if isinstance(value,dict):
        yield value
        for v in value.values(): yield from walk(v)
    elif isinstance(value,list):
        for v in value: yield from walk(v)

def main():
    report={'status':'PASS','scope':'Offline identity, exact claim bindings, local paper links, and Office structure; no new inference or human approval','experiments':{}}
    all_sources={}
    for directory in ('01_cti','02_008','03_010'):
        ledger=json.loads((ROOT/directory/'EVIDENCE.json').read_text(encoding='utf-8'))
        source_map=ledger.get('sources',{})
        source_records={}
        for obj in walk(ledger):
            path=obj.get('repo_path',obj.get('path'))
            digest=obj.get('sha256')
            if path and digest:
                file=(REPO/path).resolve()
                assert file.is_relative_to(REPO),path
                assert file.is_file(),path
                assert hashlib.sha256(file.read_bytes()).hexdigest()==digest,path
                source_records[path]=digest
        all_sources.update(source_records)
        checks=0
        for obj in walk(ledger):
            if 'source' in obj and 'json_pointer' in obj:
                src=source_map[obj['source']]
                doc=json.loads((REPO/src['repo_path']).read_text(encoding='utf-8-sig'))
                actual=pointer(doc,obj['json_pointer'])
                expected=obj.get('expected',obj.get('value'))
                assert actual==expected,(directory,obj['source'],obj['json_pointer'])
                checks+=1
            if 'path' in obj and 'json_pointers' in obj:
                doc=json.loads((REPO/obj['path']).read_text(encoding='utf-8-sig'))
                for ref in obj['json_pointers']:
                    assert pointer(doc,ref['pointer'])==ref['observed_value'],(directory,ref['pointer'])
                    checks+=1
        links=0
        for doc in (ROOT/directory).glob('*.md'):
            for dest in re.findall(r'\[[^\]]+\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
                if not dest.startswith(('https://','http://','#')):
                    assert (doc.parent/dest.split('#')[0]).resolve().exists(),(doc,dest)
                    links+=1
        report['experiments'][directory]={'source_files':len(source_records),'exact_json_pointer_checks':checks,'local_links':links,'paper_sha256':hashlib.sha256((ROOT/directory/'PAPER.md').read_bytes()).hexdigest()}
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    word=[]
    for file in sorted((ROOT/'deliverables').glob('*.docx')):
        with zipfile.ZipFile(file) as z:
            xml=ET.fromstring(z.read('word/document.xml'))
            plain=''.join(xml.itertext())
            assert '](' not in plain,file
            tables=xml.findall('.//w:tbl',ns)
            for t in tables:
                grid=[int(x.attrib['{'+ns['w']+'}w']) for x in t.findall('./w:tblGrid/w:gridCol',ns)]
                assert sum(grid)==9360,(file,grid)
                for row in t.findall('./w:tr',ns):
                    widths=[int(c.find('./w:tcPr/w:tcW',ns).attrib['{'+ns['w']+'}w']) for c in row.findall('./w:tc',ns)]
                    assert widths==grid,(file,widths,grid)
            word.append({'file':file.name,'tables':len(tables),'raw_markdown_links':0,'fixed_table_geometry':'PASS'})
    with zipfile.ZipFile(ROOT/'deliverables/Praxis_Three_Experiments.pptx') as z:
        slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        notes=[n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)]
        assert len(slides)==3 and len(notes)==3
        charts=[n for n in z.namelist() if re.fullmatch(r'ppt/(?:slides/)?charts/chart\d+\.xml',n)]
        assert len(charts)==1
        chart=ET.fromstring(z.read(charts[0])); cn={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
        chart_values=[float(v.text) for v in chart.findall('.//c:val/c:numRef/c:numCache/c:pt/c:v',cn)]
        if not chart_values: chart_values=[float(v.text) for v in chart.findall('.//c:val/c:numLit/c:pt/c:v',cn)]
        assert chart_values==[23.07,18.19,-14.97,19.58,13.88,-17.46],chart_values
        assert any(b'<a:tbl>' in z.read(n) for n in slides),'Native table missing'
        for n in notes: assert b'https://github.com/garypagangit/praxis' in z.read(n),n
    pending=json.loads((ROOT/'HUMAN_REVIEW_RESULTS.json').read_text(encoding='utf-8'))
    assert pending['received_reviews']==[] and pending['status']=='PENDING_HUMAN_REVIEW'
    report['documents']=word
    report['presentation']={'slides':3,'speaker_notes':3,'editable_chart':1,'native_result_table':1,'chart_values_verified':chart_values}
    report['human_review']='No received responses; pending status preserved'
    report['unique_hashed_source_files']=len(all_sources)
    report['exact_pointer_total']=sum(x['exact_json_pointer_checks'] for x in report['experiments'].values())
    (ROOT/'VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (ROOT/'SOURCE_FILES.json').write_text(json.dumps({'paths_relative_to':'repository root','files':[{'path':p,'sha256':d,'bytes':(REPO/p).stat().st_size} for p,d in sorted(all_sources.items())]},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
