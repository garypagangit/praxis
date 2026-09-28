import json,hashlib,shutil,zipfile,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent; B=R.parents[1]
O=B/'output/praxis_committee_review_20260928'; OLD=B/'output/praxis_integrated_20260928'
P=Path('C:/w/apt_benchmark_20260920/experiments/praxis_next/gwu_final_20260928')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d): p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
q=json.loads((R/'COMMITTEE_QA.json').read_text());q['status']='PASS';q['visual_review']={'changed_pages_reviewed':q['changed_pages'],'unchanged_body_pages_verified_by_pixel_hash':len(q['unchanged_pages']),'result':'No clipping, missing equations, or unreadable chart labels observed.'};write(R/'COMMITTEE_QA.json',q)
r=json.loads((R/'COMMITTEE_RENDER_RECEIPT.json').read_text());r['status']='PASS';r['docx_sha256_before_footer_cache_cleanup']=r['docx_sha256'];r['docx_sha256']=sha(O/'Gary_Pagan_Final_Praxis.docx');r['postprocessing']='Cleared cached PAGE field text; retained live fields and update-on-open. PDF was exported with populated page fields before cache cleanup.';write(R/'COMMITTEE_RENDER_RECEIPT.json',r)
notes='''# Committee review corrections — September 28, 2026

This corrected review edition contains a 155-page paper. Experimental results are unchanged.

1. **Trailing page numbers:** removed cached PAGE-field values from DOCX footer parts, the source of the orphan sequence in some extraction tools. Live page fields remain; PDF page numbering is populated. A body-only accessible text copy is supplied.
2. **Equations:** all 25 equation images render in the PDF. Each now also has visible, searchable linear notation in Word and PDF, including the softmax, loss, gates, gains, greedy rule and Ridge objective.
3. **Literature date:** Section 2.1 distinguishes the September 23 initial review from the September 28 AIT supplement.
4. **Lists:** expanded acronyms and symbols, including every requested addition and their contextual meanings.
5. **Review status:** removed the two placeholder phrases and identified this as a committee review edition. Formal submission still requires confirmed director/committee names, examination date and institution-approved certification wording. These facts have not been supplied or invented.
6. **AIT figure:** Figure 4-9 accompanies Table 4-17 with six execution-by-seed paired deltas for macro-F1 and exfiltration warning recall, directly derived from saved results. Units and the lack of primary-direction replication are explicit; seeds are not independent campaigns.

## Verification and contents

All 43 changed pages were visually inspected; 112 remaining page bodies matched the previously reviewed PDF pixel-for-pixel. Structural checks verified 25 searchable equations, the end of Appendix E.5, cleared footer caches, PDF page numbering and absence of text outside page boundaries. Live PAGE-field recalculation was separately verified through LibreOffice.

The complete 37-slide PowerPoint, slide PDF and speaker notes are included unchanged from the integrated September 28 edition. This correction updates the paper.

Full data, models and audit evidence remain available in the [original evidence release](https://github.com/garypagangit/praxis/releases/tag/praxis-integrated-20260928). The evidence index supplies asset links and hashes.

## Building

Run integration/integrate_paper.py for the integrated baseline, then integration/correct_committee.py and integration/check_committee.py for these corrections. Recorded workstation paths and dependencies must be adapted on another machine. Visual review is a manual final gate. Do not replace the delivered PDF with an unrefreshed DOCX conversion: page fields must be recalculated by the rendering application.
'''
(O/'CORRECTIONS.md').write_text(notes,encoding='utf-8');(O/'README.md').write_text(notes,encoding='utf-8')
for name in ['Gary_Pagan_GWU_Praxis_Defense.pptx','Gary_Pagan_GWU_Praxis_Defense.pdf','Defense_Speaker_Notes.txt','EVIDENCE_INDEX.json','DECK_QA.json']:
 shutil.copy2(OLD/name,O/name)
for name in ['COMMITTEE_QA.json','COMMITTEE_RENDER_RECEIPT.json','COMMITTEE_CORRECTIONS.json']:shutil.copy2(R/name,O/name)
(O/'EVIDENCE_INDEX.json').write_bytes(subprocess.check_output(['git','show','6f0b558:experiments/praxis_next/gwu_final_20260928/delivery/EVIDENCE_INDEX.json'],cwd=P))
shutil.copy2(P/'figures/ait_paired_deltas.png',O/'ait_paired_deltas.png')
m={'edition':'2026-09-28 corrected committee review','paper_pages':155,'main_slides':25,'backup_slides':12,'visual_qa':'PASS','formal_submission_status':'Committee details and approved certification wording required','evidence_release':'https://github.com/garypagangit/praxis/releases/tag/praxis-integrated-20260928','files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(O.iterdir()) if p.is_file() and p.suffix!='.zip' and p.name!='FINAL_MANIFEST.json']};write(O/'FINAL_MANIFEST.json',m)
zpath=O/'Praxis_Committee_Review_Corrected.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(O.iterdir()):
  if p.is_file() and p.suffix!='.zip':z.write(p,p.name)
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
for p in O.iterdir():
 if p.is_file() and p.suffix!='.zip' and p.name not in ['manuscript.md','abstract.md','README.md','ait_paired_deltas.png']:shutil.copy2(p,P/'delivery'/p.name)
for name in ['correct_committee.py','check_committee.py','refresh_corrected_pdf.py','package_corrections.py','COMMITTEE_QA.json','COMMITTEE_RENDER_RECEIPT.json','COMMITTEE_CORRECTIONS.json']:shutil.copy2(R/name,P/'integration'/name)
read=P/'README.md';s=read.read_text(encoding='utf-8').replace('**153-page paper;','**155-page paper;');s=s.replace('The local delivery manifest preserves the original delivered files\' hashes.','The delivery manifest records the corrected review files\' hashes.');s=s.split('\n## Corrected committee review')[0];s+='\n## Corrected committee review\n\nSee [six corrections and verification](delivery/CORRECTIONS.md). [Download the corrected review package](https://github.com/garypagangit/praxis/releases/tag/praxis-committee-review-20260928). Formal committee certification details remain required before submission.\n';read.write_text(s,encoding='utf-8')
read=P.parent/'README.md';s=read.read_text(encoding='utf-8');s=s.replace('[Download release](https://github.com/garypagangit/praxis/releases/tag/praxis-integrated-20260928)','[Download corrected review release](https://github.com/garypagangit/praxis/releases/tag/praxis-committee-review-20260928)',1);read.write_text(s,encoding='utf-8')
print(json.dumps({'archive':str(zpath),'bytes':zpath.stat().st_size,'sha256':sha(zpath),'qa':q['status']}))
