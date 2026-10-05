"""Assemble manuscript additions and reproducible local delivery packages."""
import hashlib,json,shutil,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=HERE.parent/'aivh_transfer_20261005';PRIOR=HERE.parent/'aivh_gambit_20261005'
OUT=ROOT/'output/doc/aivh_praxis';PRIVATE=Path('C:/w/px119_20261005')

def revise():
    shutil.copy2(PRIVATE/'outputs/RESULTS.json',HERE/'RESULTS.json')
    path=OLD/'build_paper.py';s=path.read_text()
    if 'import paper_additions' in s:return
    s=s.replace('import json\n','import json,sys\n',1)
    s=s.replace("doc=Document()", "sys.path.insert(0,str(HERE.parent/'aivh_arguments_20261005'))\nimport paper_additions\npaper_additions.figures()\ndoc=Document()",1)
    a=s.index("doc.add_paragraph('Figure 1.");b=s.index("h('3.2 Data",a)
    s=s[:a]+"paper_additions.add(globals(),'methods')\n"+s[b:]
    for marker,section in [("chapter('Chapter 2:",'objectives'),("h('3.3 Models",'qualification'),("chapter('Chapter 4:",'gmr'),("chapter('Chapter 5:",'results'),("chapter('References')",'remaining'),("doc.core_properties.title=",'appendix')]:
        i=s.index(marker);s=s[:i]+f"paper_additions.add(globals(),'{section}')\n"+s[i:]
    s=s.replace('RQ2. Does command order add information beyond command frequency?', 'RQ2. Does removing argument detail improve transfer compared with the TRACE-style baseline?')
    s=s.replace('H2. Ordered verbs improve AI recall by >=5 percentage points over frequency-only verbs at separately calibrated <=5% human-group FPR, and the paired 95% interval for the improvement excludes zero on fresh data.', 'H2. On fresh matched data, a preselected masked representation improves AI recall by >=5 percentage points over TRACE-style SVC, both satisfy <=5% mean human-group FPR, and the paired 95% improvement interval excludes zero. If either violates the error limit, H2 is not supported.')
    s=s.replace('Failure of H2 would mean frequencies are sufficient in the tested setting; it would not invalidate H1.', 'Failure to support H2 does not establish equivalence or invalidate H1. Command-order comparisons remain secondary development analyses. This revised prospective RQ2 does not change the historical PX-118 protocol.')
    path.write_text(s,encoding='utf-8')

def package():
    stage=PRIVATE/'delivery';stage.mkdir(exist_ok=True)
    code=stage/'code';evidence=stage/'evidence';inputs=stage/'private_inputs'
    for x in [code,evidence,inputs]:x.mkdir(exist_ok=True)
    def cp(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    for name in ['run.py','PROTOCOL.txt']:cp(HERE/name,code/'px119'/name)
    for name in ['train.py','prepare.py','audit_results.py']:cp(OLD/name,code/'px118'/name)
    cp(PRIOR/'train.py',code/'px118/prior.py');cp(PRIOR/'common.py',code/'px118/common.py')
    cp(OLD/'record_session.py',code/'collection/record_session.py')
    cp(OLD/'MATCHED_COLLECTION_PLAN.txt',code/'collection/MATCHED_COLLECTION_PLAN.txt')
    cp(Path('C:/w/px118_20261005/collected/outputs/requirements-lock.txt'),code/'requirements.txt')
    for name in ['reproduce.py','verify_package.py','audit_px119.py']:cp(HERE/name,code/name)
    for name in ['records.json','base_predictions.json','split_manifest.json','external_kypo.json','external_rouxii.json']:
        cp(Path('C:/w/px118_20261005')/name,inputs/name)
    for p in Path('C:/w/px118_20261005/collected/outputs').glob('*.joblib'):cp(p,code/'models'/p.name)
    for p in (PRIVATE/'outputs').glob('*'):cp(p,evidence/'PX119'/p.name)
    for folder,label in [(OLD,'PX118'),(HERE,'PX119')]:
        for pattern in ['*.json','*.txt','*.csv']:
            for p in folder.glob(pattern):cp(p,evidence/label/p.name)
    for p in Path('C:/w/px118_20261005/collected/outputs').glob('*predictions.json'):cp(p,evidence/'PX118/predictions'/p.name)
    cp(PRIOR/'LITERATURE_REVIEW.txt',evidence/'literature/LITERATURE_REVIEW.txt')
    for p in (HERE/'figures').glob('*'):cp(p,evidence/'figures'/p.name)
    for name in ['Gary_Pagan_AI_Operator_Praxis.pdf','Gary_Pagan_AI_Operator_Praxis.docx']:cp(OUT/name,evidence/'paper'/name)
    cp(HERE/'REMAINING.txt',OUT/'REMAINING.txt');cp(HERE/'REMAINING.txt',evidence/'REMAINING.txt')
    (code/'README.txt').write_text('''AI operator Praxis code package — development evidence only

Install numerical dependencies: python -m pip install -r requirements.txt
Verify files: python verify_package.py .
Recompute PX-119 aggregate metrics: python audit_px119.py --evidence PATH_TO_EVIDENCE/PX119
Reproduce fits from the separate private prepared-input folder:
  python reproduce.py --data PATH_TO_PRIVATE_INPUTS --output NEW_OUTPUT_DIRECTORY
Add --include-px118 to refit all 30 original conditions (no paid cloud calls).

Code map:
px119/run.py: weights balances class/groups; features creates the three
representations; evaluate computes confusion/rates; main validates splits,
fits only training data, freezes calibration thresholds, saves predictions,
and applies the frozen-model stress intervention. No commands are executed.
px118/train.py: texts builds lexical/verb/masked views; fit calibrates and
evaluates one model; run adds family exclusions; main runs 30 fixed fits.
px118/prior.py: historical group weights, metrics, split and dedup helpers.
px118/common.py: original command qualification/normalization helpers.
px118/prepare.py and audit_results.py: historical provenance scripts; contain
original local paths and are not portable entry points. Use reproduce.py.
collection/: proposed recorder and plan; container integration still pending.
models/: trusted saved PX-118 models; joblib files can execute code when loaded.

Prepared inputs are separate because source logs require terms/privacy review.
This reproduces qualified-input analysis, not a one-command raw-data download.
The original source parsers remain in the repository's PX-117C and PX-118 dirs.
No matched human/AI dataset or deployment validation is included.
''',encoding='utf-8')
    (inputs/'README.txt').write_text('LOCAL AUTHOR REPRODUCTION INPUTS. Prepared records from public research sources; not approved for public redistribution. Review source terms and participant privacy before sharing. No new human collection is represented here. Input hashes are in PX119 RESULTS.json. Commands are inert data.\n')
    (evidence/'README.txt').write_text('Evidence for a working Praxis, not a completed confirmatory study. PX118 is exposed-data development; PX119 tests argument-count dependence on the same rows. See REMAINING.txt. Historical PX118 audits refer to original paths; code/audit_px119.py is portable. All files are inventoried in SHA256.json.\n')
    OUT.mkdir(exist_ok=True)
    for directory,name,target in [(code,'AI_Operator_Code_Package.zip',OUT),(evidence,'AI_Operator_Evidence_Package.zip',OUT),(inputs,'AI_Operator_Private_Inputs.zip',PRIVATE)]:
        manifest={str(p.relative_to(directory)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file() and p.name!='SHA256.json'}
        (directory/'SHA256.json').write_text(json.dumps(manifest,indent=2))
        with zipfile.ZipFile(target/name,'w',zipfile.ZIP_DEFLATED) as z:
            for p in directory.rglob('*'):
                if p.is_file():z.write(p,str(p.relative_to(directory)))
        with zipfile.ZipFile(target/name) as z:assert z.testzip() is None
    print('Packages assembled and ZIP integrity checked.')

if __name__=='__main__':
    import sys
    revise() if '--revise' in sys.argv else package()
