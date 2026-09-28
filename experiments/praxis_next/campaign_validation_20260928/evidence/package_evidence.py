"""Package all source data, predictions and fitted models after successful QA."""
import hashlib,json,shutil,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'output/campaign_validation_20260928'
WORK=Path('C:/w/campaign_validation_20260928')
TMP=Path(tempfile.gettempdir())/'codex-presentations/campaign-validation-20260928/tmp'
audit=json.loads((ROOT/'AUDIT.json').read_text())
qa=json.loads((ROOT/'DOCUMENT_QA.json').read_text())
assert audit['failed']==0 and qa['status']=='PASS'
summary=json.loads((ROOT/'SUMMARY.json').read_text())
readme=f'''# Campaign validation delivery

AWS reconnection succeeded with profile `praxis-build`; STS identity was verified on 28 September 2026. Experiments ran locally and did not require cloud compute.

## Read first

- `Gary_Pagan_Campaign_Validation_Addendum.pdf` / `.docx`: paper companion.
- `Gary_Pagan_Campaign_Validation_Defense_Addendum.pptx` / `.pdf`: five GWU defense appendix slides.
- `Validation_Defense_Notes.txt`: complete speaker notes.
- `CAMPAIGN_VALIDATION_REPORT.md`: full readable report with every comparison.
- `RESULTS.csv` / `.json`: all held-out results, including all three seeds and both executions.
- `Campaign_Validation_Full_Evidence.zip`: all eight complete source archives, prepared arrays, 42 fitted models, every saved prediction and development OOF output, protocol, source rules, code and audits.

## Interpretation

{summary['scope']}

{summary['verdict']}

{summary['secondary_finding']}

This addendum accompanies the previously delivered final praxis and defense. The September 27 originals are preserved in `../praxis_final_20260927`. The older statement that there are no external fitted replications should now be read with this added, explicitly adapted AIT experiment. The old four-class/two-group results are not replaced by three-class/one-group scores.

All {summary['raw_rows']:,} source rows were examined; {summary['training_rows']:,} training and {summary['test_rows']:,} evaluation rows are eligible. The audit passed {audit['passed']:,} checks. The five-slide addendum can follow the external-qualification discussion or be used as defense backup material.

## Reproduction

The evidence archive contains `reports/`, `data/`, `documents/` and `slide_source/`. On this workstation the data root is `C:/w/campaign_validation_20260928` and the Python environment is `C:/w/praxis_full_release_20260927_env/Scripts/python.exe`. Extract `data/` into that root or adjust the documented absolute paths for another machine, recording any change. Run the scripts as described in the report. Rebuilding the slide deck also requires the bundled artifact-tool and original GWU template (included under slide_source).

`FINAL_MANIFEST.json` records output hashes and archive integrity. Source and model inventories are independently hashed inside the evidence. Publisher metadata, licensing information and original notebooks remain included. No publisher notebook was executed.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
project=Path('C:/w/apt_benchmark_20260920/experiments/praxis_next/campaign_validation_20260928')
project.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT,project/'evidence',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','AWS_CONNECTION.json','RUN.log'))
(project/'README.md').write_text(readme+'\nFinal documents: '+str(OUT)+'\n',encoding='utf-8')
archive=OUT/'Campaign_Validation_Full_Evidence.zip'
manifest=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in ['AWS_CONNECTION.json','RUN.log']:
            z.write(p,'reports/'+p.relative_to(ROOT).as_posix())
    for p in sorted(WORK.rglob('*')):
        if p.is_file() and p.suffix not in ['.part']:
            # ZIP/NPZ are already compressed; avoid expensive redundant compression.
            z.write(p,'data/'+p.relative_to(WORK).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix in ['.zip','.npz','.joblib'] else zipfile.ZIP_DEFLATED)
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.suffix in ['.pdf','.docx','.pptx','.txt','.md']:
            z.write(p,'documents/'+p.name)
    for name in ['build_addendum.mjs','template-frame-map.json','template-audit.txt','deviation-log.txt','source-notes.txt','slide-content.json','template-starter.pptx']:
        p=TMP/name;z.write(p,'slide_source/'+name)
    z.write(Path('C:/Users/garyp/Downloads/Final_Defense_Template.pptx'),'slide_source/Final_Defense_Template.pptx')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    archive_members=len(z.namelist())
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name!='FINAL_MANIFEST.json':manifest.append({'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
result={'status':'PASS','evidence_crc_passed':True,'evidence_members':archive_members,'audit_passed':audit['passed'],
        'raw_rows':summary['raw_rows'],'test_rows':summary['test_rows'],'project_location':str(project),'files':manifest}
(OUT/'FINAL_MANIFEST.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
