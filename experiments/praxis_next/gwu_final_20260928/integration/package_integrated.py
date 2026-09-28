import hashlib,json,shutil,zipfile
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1];OUT=BASE/'output/praxis_integrated_20260928'
SRC=Path('C:/w/apt_benchmark_20260920/experiments/praxis_next/gwu_final_20260928')
TMP=Path('C:/Users/garyp/AppData/Local/Temp/codex-presentations/praxis-integrated-20260928/tmp')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
paper=json.loads((ROOT/'RENDER_RECEIPT.json').read_text())
paper.update(status='PASS',visual_review='PASS: 46 changed pages visually inspected; remaining 107 body renders identical to previously reviewed edition.')
(ROOT/'RENDER_RECEIPT.json').write_text(json.dumps(paper,indent=2))
deck=json.loads((ROOT/'DECK_QA.json').read_text());deck.update(status='PASS',visual_review='All 37 slides inspected in independent LibreOffice PDF render; no clipping or collisions found.')
(ROOT/'DECK_QA.json').write_text(json.dumps(deck,indent=2))
for f in ['RENDER_RECEIPT.json','DECK_QA.json','INTEGRATION_MAP.json','PAPER_VISUAL_REVIEW.json']:shutil.copy2(ROOT/f,OUT/f)
evidence=[]
for folder,name in [('praxis_final_20260927','Praxis_Review_Evidence.zip'),('praxis_final_20260927','Praxis_Full_Data_Reproduction.zip'),('campaign_validation_20260928','Campaign_Validation_Full_Evidence.zip')]:
 p=BASE/'output'/folder/name;assert p.is_file();evidence.append({'name':name,'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
(OUT/'EVIDENCE_INDEX.json').write_text(json.dumps(evidence,indent=2))
(OUT/'README.md').write_text('''# Integrated praxis and defense — September 28, 2026

Use this complete edition for review. Campaign validation is integrated into the full manuscript and full defense presentation.

- Paper: Gary_Pagan_Final_Praxis.docx and .pdf — 153 pages.
- Defense: Gary_Pagan_GWU_Praxis_Defense.pptx and .pdf — 25 main slides plus 12 technical backups; speaker notes included.
- Paper integration: abstract; Chapters 1–2 scope and literature; Section 3.12 methods; Section 4.11 results; Chapter 5 interpretation, limitations and conclusions; Appendix E complete per-seed outcomes.
- Main slides 19–21 report AIT; slides 22–25 integrate limits and conclusions; backups 33–37 include updated answers and method details.

## Result retained accurately

AIT validation inspected all 3,465,342 source rows and evaluated 1,067,211 eligible rows from two later held-out executions. All 1,245 computational audit checks passed. The original error-focused versus entropy higher-F1/lower-warning direction did not recur in any of six execution-by-seed comparisons. Wilson showed a small opposite-order tradeoff; Harrison improved both outcomes under entropy. This is an adapted three-class, history-only test. Exact four-class replication and unrelated-campaign generalization remain unresolved.

## Evidence

The integrated review ZIP contains the finished documents, manuscript sources, integration code and aggregate AIT evidence. Full arrays, models, predictions and original source archives remain in the existing reproduction bundles below; the review ZIP does not duplicate them. EVIDENCE_INDEX.json records exact paths, sizes and SHA256 hashes.

'''+''.join('- '+e['path']+'\n' for e in evidence),encoding='utf-8')
shutil.copy2(TMP/'build_integrated.mjs',ROOT/'build_integrated.mjs')
zip_path=OUT/'Integrated_Praxis_Review_Package.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in OUT.iterdir():
  if p.is_file() and p.suffix not in ['.zip','.ndjson'] and p.name!='FINAL_MANIFEST.json':z.write(p,'delivery/'+p.name)
 for p in SRC.rglob('*'):
  if p.is_file() and p.suffix.lower() in ['.md','.json','.csv','.png','.py']:z.write(p,'manuscript_source/'+str(p.relative_to(SRC)))
 for p in ROOT.iterdir():
  if p.is_file() and p.suffix in ['.py','.mjs','.json']:z.write(p,'integration/'+p.name)
 for p in (BASE/'reports/campaign_validation_20260928').iterdir():
  if p.is_file() and p.suffix in ['.py','.json','.csv','.md','.txt']:z.write(p,'ait_evidence/'+p.name)
with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
manifest={'edition':'2026-09-28 integrated','paper_pages':153,'main_slides':25,'backup_slides':12,'visual_qa':'PASS','review_archive_crc':'PASS','external_full_evidence':evidence,'files':[]}
for p in OUT.iterdir():
 if p.is_file() and p.name!='FINAL_MANIFEST.json':manifest['files'].append({'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
(OUT/'FINAL_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'status':'PASS','review_zip_bytes':zip_path.stat().st_size,'deliverables':len(manifest['files'])}))
