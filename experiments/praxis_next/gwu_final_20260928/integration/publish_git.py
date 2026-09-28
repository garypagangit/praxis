import json,shutil,subprocess
from pathlib import Path
BASE=Path('C:/Users/garyp/OneDrive/Documents/codex')
REPO=Path('C:/w/apt_benchmark_20260920')
SRC=REPO/'experiments/praxis_next/gwu_final_20260928'
OUT=BASE/'output/praxis_integrated_20260928'
tag='praxis-integrated-20260928'
url='https://github.com/garypagangit/praxis/releases/tag/'+tag
download='https://github.com/garypagangit/praxis/releases/download/'+tag+'/'
delivery=SRC/'delivery';delivery.mkdir(exist_ok=True)
for p in OUT.iterdir():
 if p.is_file() and not p.name.startswith('~$') and p.suffix in ['.docx','.pptx','.pdf','.json','.txt']:shutil.copy2(p,delivery/p.name)
integration=SRC/'integration';integration.mkdir(exist_ok=True)
for p in (BASE/'reports/praxis_integrated_20260928').iterdir():
 if p.is_file() and p.suffix in ['.py','.mjs','.json']:shutil.copy2(p,integration/p.name)
evidence=json.loads((OUT/'EVIDENCE_INDEX.json').read_text())
for item in evidence:item['download_url']=download+item['name']
(delivery/'EVIDENCE_INDEX.json').write_text(json.dumps(evidence,indent=2))
(SRC/'README.md').write_text('''# Integrated final praxis and GWU defense

Gary Pagan — September 28, 2026

**153-page paper; 25 main defense slides plus 12 technical backups.** Campaign validation is incorporated throughout this complete edition.

- [Word paper](delivery/Gary_Pagan_Final_Praxis.docx) · [PDF paper](delivery/Gary_Pagan_Final_Praxis.pdf)
- [PowerPoint defense](delivery/Gary_Pagan_GWU_Praxis_Defense.pptx) · [PDF slides](delivery/Gary_Pagan_GWU_Praxis_Defense.pdf)
- [Speaker notes](delivery/Defense_Speaker_Notes.txt)
- [Source manuscript](manuscript.md)
- [Dated release and downloadable evidence]('''+url+''')
- [Evidence hashes and download URLs](delivery/EVIDENCE_INDEX.json)

## What changed

The integrated paper adds AIT source literature, Section 3.12 methods, Section 4.11 results and Appendix E complete per-seed outcomes, and updates the abstract, scope, discussion and conclusions. Main slides 19–21 present the AIT evaluation; limits and conclusions follow in slides 22–25. Technical backups and speaker notes are updated.

All 3,465,342 AIT source rows were examined. Six executions supplied 2,397,158 eligible training rows; two later executions supplied 1,067,211 evaluation rows. All 1,245 computational audit checks passed.

The original error-focused versus entropy higher-F1/lower-warning direction did **not** recur in any of six execution-by-seed comparisons. Wilson showed a small opposite-order tradeoff; Harrison improved both outcomes under entropy. This is an adapted three-class, history-only evaluation. Exact four-class replication, unrelated-campaign generalization and operational benefit remain unresolved.

## Reproduction and tracking

The dated release includes the integrated review package and the original/full-release and AIT reproduction bundles. Large archives are release assets; manuscript sources, documents, aggregate evidence and build code are versioned in Git.

- [AIT protocol, code and audit](../campaign_validation_20260928/evidence/)
- [Full-release UNRAVELED code and audit](../gwu_final_20260927/full_release/)
- [Integration code and QA](integration/)

Reproduction scripts retain recorded workstation paths. Adjust these when extracting on another machine and record the amendments. The supplied build scripts require their recorded Python dependencies and, for slides, artifact-tool. Computational checks do not represent committee approval.

The local delivery manifest preserves the original delivered files' hashes. EVIDENCE_INDEX.json here additionally supplies release download URLs.
''',encoding='utf-8')
landing=REPO/'experiments/praxis_next/README.md'
old=landing.read_text(encoding='utf-8')
landing.write_text('> **Latest integrated edition (September 28, 2026):** [paper, complete defense and evidence](gwu_final_20260928/README.md). [Download release]('+url+').\n\n'+old,encoding='utf-8')
campaign=REPO/'experiments/praxis_next/campaign_validation_20260928/README.md'
old=campaign.read_text(encoding='utf-8');campaign.write_text('> **Integrated edition available:** These results are now incorporated in the [full paper and defense](../gwu_final_20260928/README.md). Download the full evidence archive from the [dated release]('+url+').\n\n'+old,encoding='utf-8')
notes='''# Integrated praxis and defense — September 28, 2026

Complete paper (153 pages), GWU defense (25 main slides plus 12 backups), speaker notes, and review evidence.

Campaign validation is incorporated into the abstract, methods, results, discussion, conclusions and Appendix E. AIT: 3,465,342 source rows; 1,067,211 held-out evaluation rows; 42 fitting jobs; 1,245 audit checks passed.

The original policy direction did not recur. Wilson showed a small opposite-order tradeoff; Harrison improved both outcomes under entropy. This is an adapted three-class test, with exact four-class replication and unrelated-campaign generalization unresolved.

## Assets

- Integrated_Praxis_Review_Package.zip: complete documents, PDFs, source, integration code and aggregate validation evidence.
- Praxis_Review_Evidence.zip: prior historical and full-release review evidence.
- Praxis_Full_Data_Reproduction.zip: full-release reproduction materials.
- Campaign_Validation_Full_Evidence.zip: all eight AIT source archives, prepared arrays, 42 models, predictions, protocol and audits; CC BY 4.0 source attribution retained.
- EVIDENCE_INDEX.json: reproduction archive SHA256 hashes.

See the repository README for source paths and reproduction requirements. This release does not assert committee approval.
'''
(BASE/'reports/praxis_integrated_20260928/RELEASE_NOTES.md').write_text(notes,encoding='utf-8')
files=[landing]
for directory in ['gwu_final_20260927','gwu_final_20260928','campaign_validation_20260928']:
 for p in (REPO/'experiments/praxis_next'/directory).rglob('*'):
  if p.is_file() and p.suffix.lower() in ['.md','.json','.csv','.txt','.py','.mjs','.png','.svg','.pdf','.docx','.pptx'] and '__pycache__' not in p.parts:files.append(p)
assert all(p.stat().st_size<50*1024*1024 for p in files)
for i in range(0,len(files),35):subprocess.run(['git','add','-f','--']+[str(p.relative_to(REPO)) for p in files[i:i+35]],cwd=REPO,check=True)
print(json.dumps({'staged_files':len(files),'release':url}))
