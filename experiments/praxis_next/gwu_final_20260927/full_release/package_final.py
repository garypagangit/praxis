from pathlib import Path
import json,hashlib,zipfile,shutil,datetime
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]
OUT=WORK/'output/praxis_final_20260927'
NEW=Path('C:/w/apt_benchmark_20260920/experiments/praxis_next/gwu_final_20260927')
OLD=NEW.parent/'gwu_final_20260924'
PRIVATE=Path('C:/w/praxis_full_release_20260927')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
def main():
 r=json.loads((ROOT/'SUMMARY.json').read_text());a=json.loads((ROOT/'FULL_RELEASE_AUDIT.json').read_text());q=json.loads((ROOT/'FINAL_QA.json').read_text());assert a['status']==q['status']=='PASS'
 receipt=json.loads((ROOT/'RENDER_RECEIPT.json').read_text())
 text=f'''# Gary Pagan — final Praxis and defense review edition

## Start here

- **Gary_Pagan_Final_Praxis.docx / .pdf**: {receipt['pages']}-page revised manuscript, five chapters, full result appendices and 30 references.
- **Gary_Pagan_GWU_Praxis_Defense.pptx / .pdf**: GWU template; 24 main defense slides and eight technical backups. The editable deck includes presenter notes.
- **Defense_Speaker_Notes.txt**: rehearsal copy of the complete notes.
- **Praxis_Review_Evidence.zip**: manuscript source, historical evidence archive, new protocol/results/audit/code, provenance and QA receipts.
- **Praxis_Full_Data_Reproduction.zip**: every new prepared sensor array, fitted model, calibration/test target and probability vector; intended for local scientific review. Raw upstream CSVs remain at the recorded source location.

## What was completed

All **6,877,157 source rows in 173 flow files** were verified against the pinned UNRAVELED inventory. After declared handling there are **{r['train']:,} training, {r['calibration']:,} calibration and {r['test']:,} test sensor observations**. The new current-flow versus current-flow-plus-roles comparison uses every eligible training row, without class caps, in six separate sensor views. Twelve final fitting jobs are retained; one-class jobs are explicitly constant controls. The independent count-based verification passed **{a['check_count']} checks**. See FULL_RELEASE_RESULTS.json for complete class support, confusion counts, per-capture metrics and calibration-only choices.

The historical 143-fit inventory remains intact. The new extension does **not** rerun every historical history/acquisition intervention on the expanded release. Roles improve test macro-F1 in {r['improved_sensor_count']} sensor views. F1 improvements accompanied by a warning-recall decline for at least one supported attack stage occur in: {', '.join(r['warning_reversal_sensors']) or 'none'}. The gateway change is tiny: one additional OtherAttackStage warning missed and one fewer benign false alert; no practical or stable effect size is claimed. Single-class training sensors: {', '.join(r['single_class_sensors'])}. Additional rows and sensors remain dependent observations of one previously exposed campaign.

## Defensibility and remaining author actions

The defensible claim is an applied measurement contribution: on the inspected historical paired predictions, higher F1 can accompany fewer stage warnings, so evaluation should report stage recognition, warning loss and benign workload together. The 8.93 percentage-point historical warning loss is strongly seed-sensitive; omitting seed 8101 reduces it to about 0.36 point. Do not present that magnitude as universal or as an operational treatment effect.

The full-release extension addresses coverage and uncapped training for its stated role-feature question. An independent-campaign warning/false-alarm replication remains unmeasured. Additional CAM-LDS network evidence was checked and failed the required target/background qualification; labels were not invented. Another dataset is needed for stronger generalization claims, not to change these completed arithmetic observations into something they are not. Your committee decides whether this bounded contribution satisfies its requirements.

Remaining author/institutional steps: review and take responsibility for the manuscript and AI-assisted work; confirm adviser/committee details and defense date; rehearse; complete the applicable GWU Academic Integrity Review and ETD process. Certification and approval are deliberately not asserted in the manuscript. GWU's published doctoral policy requires AIR approval two weeks before the ETD upload deadline: https://online.engineering.gwu.edu/policies-procedures-doctoral . Its page also links the program AI-use policy; the linked Box document was not accessible through the web reader, so its detailed contents are not asserted here. Nothing was submitted or sent to an adviser.

## Reproduction

Primary source: https://gitlab.com/asu22/unraveled, pinned commit d2ea90055d82fa448ab20588a13e3ec8bfd74816. Raw files: C:/Users/garyp/OneDrive/Documents/codex/imports/unraveled/data/network-flows. Original inventory: C:/w/apt_benchmark_20260920/experiments/apt_benchmark/host_history_exfil/DATA_INVENTORY.json. The review archive includes this inventory and the complete per-file hash/count receipts. Raw source bytes are not duplicated into the ZIPs.

Local scripts: reports/praxis_final_20260927/full_release.py and audit_full_release.py. Compute interpreter: C:/w/praxis_full_release_20260927_env/Scripts/python.exe. Full prepared arrays and predictions: C:/w/praxis_full_release_20260927. Environment versions are recorded in ENVIRONMENT.txt. Repoint recorded paths when moving to another machine; retain the frozen split, feature and review choices. Model objects should be loaded only from this trusted local bundle after checking the manifest.

The original source and final artifacts remain separate. No previous manuscript was overwritten, no cloud compute was launched, and no Git commit was made for this assembly. The final manifest hashes every delivered document and all packaged evidence. Computational and visual QA are same-team checks, not independent scholarly approval.
'''
 (OUT/'README.md').write_text(text,encoding='utf-8')
 # Public review evidence, keeping original scientific artifacts intact.
 files=[]
 for p in ROOT.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:files.append((p,'full_release/'+p.relative_to(ROOT).as_posix()))
 for p in NEW.rglob('*'):
  if p.is_file() and not any(x in p.parts for x in ['full_release','__pycache__']):files.append((p,'manuscript/'+p.relative_to(NEW).as_posix()))
 files.append((OLD/'gwu_praxis_final_evidence.zip','historical/gwu_praxis_final_evidence.zip'))
 inv=Path('C:/w/apt_benchmark_20260920/experiments/apt_benchmark/host_history_exfil/DATA_INVENTORY.json');files.append((inv,'source/DATA_INVENTORY.json'))
 for name in ['QUALIFICATION.json','NETWORK_ACQUISITION.json']:
  p=WORK/'reports/praxis_execution_20260926/apt'/name;files.append((p,'external_qualification/'+name))
 files.append((OUT/'README.md','README.md'))
 manifest=[{'member':name,'sha256':sha(p),'bytes':p.stat().st_size} for p,name in files]
 with zipfile.ZipFile(OUT/'Praxis_Review_Evidence.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p,name in files:z.write(p,name)
  z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
 private=[p for p in PRIVATE.rglob('*') if p.is_file()];pm=[{'member':p.relative_to(PRIVATE).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in private]
 with zipfile.ZipFile(OUT/'Praxis_Full_Data_Reproduction.zip','w',zipfile.ZIP_STORED) as z:
  for p in private:z.write(p,p.relative_to(PRIVATE).as_posix())
  z.writestr('MANIFEST.json',json.dumps(pm,indent=2));z.writestr('README.txt',text)
 for name in ['Praxis_Review_Evidence.zip','Praxis_Full_Data_Reproduction.zip']:
  with zipfile.ZipFile(OUT/name) as z:assert z.testzip() is None
 outputs=[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p.name!='FINAL_MANIFEST.json']
 (OUT/'FINAL_MANIFEST.json').write_text(json.dumps({'status':'PASS','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'artifacts':outputs,'public_evidence_members':len(files),'local_reproduction_members':len(private),'institutional_approval_asserted':False},indent=2))
 print(json.dumps({'output':str(OUT),'artifacts':outputs},indent=2))
if __name__=='__main__':main()
