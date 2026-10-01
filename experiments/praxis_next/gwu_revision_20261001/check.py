import hashlib,json,re,zipfile
from collections import Counter
from pathlib import Path
import fitz
from docx import Document
H=Path(__file__).resolve().parent;OLD=H.parent/'gwu_final_20260928';OUT=H/'delivery'
old=(OLD/'manuscript.md').read_text(encoding='utf-8');new=(H/'manuscript.md').read_text(encoding='utf-8')
assert re.findall(r'\$\$(.*?)\$\$',old,re.S)==re.findall(r'\$\$(.*?)\$\$',new,re.S)
oldrefs=set(old.split('# References',1)[1].split('# Appendix A:',1)[0].strip().split('\n\n'));newrefs=set(new.split('# References',1)[1].split('# Appendix A:',1)[0].strip().split('\n\n'));assert oldrefs<=newrefs and len(newrefs-oldrefs)==4
oldrows=Counter(x for x in old.splitlines() if x.startswith('|'));newrows=Counter(x for x in new.splitlines() if x.startswith('|'));removed=list((oldrows-newrows).elements())
assert len(removed)==2,removed
assert any('New warning-destination loss' in x for x in removed) and any('| Workload |' in x for x in removed)
px96=json.loads((H.parent/'ssh_policy_20261001/RESULTS.json').read_text());px97=json.loads((H.parent/'ssh_transfer_20261001/RESULTS.json').read_text())
for label,rs in [('UNRAVELED',px96),('AIT Wilson',[r for r in px97 if r['execution']=='wilson']),('AIT Harrison',[r for r in px97 if r['execution']=='harrison'])]:
    b=next(r for r in rs if r['arm']=='base_OR');v=next(r for r in rs if r['arm']=='base_OR_plus_rule')
    row=f"| {label} | {100*b['exfil_warning_recall']:.4f}% / {100*v['exfil_warning_recall']:.4f}% | {b['episodes_warned']}/{b['episodes_total']} / {v['episodes_warned']}/{v['episodes_total']} | {v['extra_exfil_flows_vs_base']} | {v['extra_benign_flows_vs_base']} | {v.get('extra_cases_vs_base',v.get('extra_grouped_cases_vs_base'))} |"
    assert row in new,row
pdf=fitz.open(OUT/'Gary_Pagan_Final_Praxis.pdf');texts=[p.get_text() for p in pdf];full=' '.join(' '.join(texts).split());doc=Document(OUT/'Gary_Pagan_Final_Praxis.docx')
assert 'Executive Summary' in full and 'PX-097' in full and 'Table 4-20' in full and 'Appendix F' in full
assert full.count('Linear notation:')==25
assert '@@' not in full and 'mistaken records' not in full
assert len(doc.tables)>=1
outside=[]
for n,p in enumerate(pdf,1):
    for b in p.get_text('blocks'):
        if b[0]<-.5 or b[1]<-.5 or b[2]>p.rect.width+.5 or b[3]>p.rect.height+.5:outside.append({'page':n,'box':list(b[:4])})
assert not outside,outside
summaries=[i+1 for i,t in enumerate(texts) if 'Executive Summary' in t]
locations={}
for term in ['Abstract of Praxis','Executive Summary','Chapter 1: Introduction','3.13 Follow-up','4.12 Preserving','4.13 Episode','4.14 What the','4.15 What a','Table 4-18','Table 4-19','Table 4-20','Chapter 5:','Appendix F:']:
    locations[term]=[i+1 for i,t in enumerate(texts) if term in t]
(OUT/'Gary_Pagan_Final_Praxis_Accessible.txt').write_text('\n'.join(line.rstrip() for line in '\n\n'.join(texts).splitlines()).rstrip()+'\n',encoding='utf-8')
receipt={'status':'PASS','pages':len(pdf),'original_result_table_rows_preserved':True,'changed_original_rows':removed,'equation_blocks_preserved':len(re.findall(r'\$\$(.*?)\$\$',new,re.S)),'accessible_equation_lines':25,'bibliography_preserved':True,'outside_page_text':outside,'page_locations':locations,'visual_review':'PENDING'}
(H/'CONTENT_QA.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
