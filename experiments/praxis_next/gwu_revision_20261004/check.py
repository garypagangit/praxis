import hashlib,json,re
from collections import Counter
from pathlib import Path
import fitz
from docx import Document
H=Path(__file__).resolve().parent;B=H.parent;O=H/'delivery'
old=(B/'gwu_revision_20261001/manuscript.md').read_text(encoding='utf-8');new=(H/'manuscript.md').read_text(encoding='utf-8')
assert re.findall(r'\$\$(.*?)\$\$',old,re.S)==re.findall(r'\$\$(.*?)\$\$',new,re.S)
old_results=old.split('# Chapter 4:',1)[1].split('# Chapter 5:',1)[0]
new_results=new.split('# Chapter 4:',1)[1].split('# Chapter 5:',1)[0]
assert old_results.strip() in new_results,'Historical Chapter 4 modified'
assert Counter(x for x in old.splitlines() if x.startswith('|') and not any(v in x for v in ['TESSERACT','Bilot et al.','Uddin et al.','TAN-IDS','Othman et al.','Closest work'])) <= Counter(x for x in new.splitlines() if x.startswith('|'))
refs=lambda text:set(text.split('# References',1)[1].split('# Appendix A:',1)[0].strip().split('\n\n'))
assert refs(old)<=refs(new);assert len(refs(new)-refs(old))==5
rs=json.loads((B/'warning_transitions_20261004/RESULTS.json').read_text())['pairs']
for r in rs:
    if r['condition']=='clean' and r['budget']==3:
        t=r['stages'][2];row=f"| {r['seed']} | {t['losses']} | {t['exact_to_benign']} | {t['wrong_attack_to_benign']} | {t['gains']} | {t['warning_new']-t['warning_old']} |"
        assert row in new
assert sum(r['descriptive_review_pass'] for r in rs)==2
for x in ['18/18','510','460','893','901','170/170','331','945','0.7148','0.7379']: assert x in new
pdf=fitz.open(O/'Gary_Pagan_Praxis_Review.pdf');texts=[p.get_text() for p in pdf];full=' '.join(' '.join(texts).split())
assert full.count('Linear notation:')==25
assert '@@' not in full and 'TRANSITION_ROWS' not in full
assert '893' in full and '945' in full and 'Ghiani' in full
outside=[];empty=[];locations={}
for i,p in enumerate(pdf,1):
    if len(p.get_text().strip())<8: empty.append(i)
    for block in p.get_text('blocks'):
        if block[0]<-.5 or block[1]<-.5 or block[2]>p.rect.width+.5 or block[3]>p.rect.height+.5:outside.append([i,list(block[:4])])
    for term in ['Executive Summary','Abstract of Praxis','Chapter 1: Introduction','2.6 Literature Gap','3.14 Auditable','3.15 Warning','4.16 What','4.17 Which','Table 4-21','Table 4-22','5.2 Contributions','Table 5-1','Appendix G:','G.4 Review']:
        if term in p.get_text():locations.setdefault(term,[]).append(i)
assert not outside,outside
doc=Document(O/'Gary_Pagan_Praxis_Review.docx')
assert doc.styles['Normal'].font.name=='Times New Roman'
(O/'Gary_Pagan_Praxis_Accessible.txt').write_text('\n\n'.join(texts),encoding='utf-8')
receipt={'status':'PASS','pages':len(pdf),'historical_chapter4_unchanged':True,'original_equation_blocks_preserved':len(re.findall(r'\$\$(.*?)\$\$',new,re.S)),'original_result_table_rows_preserved':True,'original_references_preserved':True,'new_references':5,'px106_table_matches_saved_results':True,'outside_page_text':outside,'sparse_pages':empty,'locations':locations,'visual_review':'PENDING'}
(H/'CONTENT_QA.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
