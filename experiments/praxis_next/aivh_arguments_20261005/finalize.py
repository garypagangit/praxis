"""Record delivery verification and update the experiment registry."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PRIVATE=Path('C:/w/px119_20261005')
def load(p):return json.loads(p.read_text())
# Refit outcomes must match the saved runs; timing is intentionally excluded.
checks={}
def equivalent(a,b):
 if isinstance(a,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
 if isinstance(a,float):return abs(a-b)<=1e-12
 return a==b
for label,original,reproduced in [
 ('PX118',HERE.parent/'aivh_transfer_20261005/RESULTS.json',PRIVATE/'reproduction_check/px118/outputs/RESULTS.json'),
 ('PX119',HERE/'RESULTS.json',PRIVATE/'reproduction_check/px119/RESULTS.json')]:
 a,b=load(original),load(reproduced)
 assert equivalent(a['results'],b['results']),label
 checks[label]={'all_result_fields_match':True,'float_absolute_tolerance':1e-12,'integer_counts_exact':True,'fits':len(a['results'])}
audit=json.loads(subprocess.check_output([sys.executable,str(HERE/'audit_px119.py'),'--evidence',str(PRIVATE/'outputs')],text=True))
(HERE/'AUDIT.json').write_text(json.dumps({'prediction_audit':audit,'portable_reproduction':checks,'frozen_protocol_commit':'e1f40ed'},indent=2))
q=load(HERE/'DOCUMENT_QA.json');q['visual_review']='PASS: all pages inspected; GMR wrapping and orphan page corrected';(HERE/'DOCUMENT_QA.json').write_text(json.dumps(q,indent=2))
regpath=HERE.parent/'REGISTRY.json';reg=load(regpath)
entry=dict(id='PX-119',directory=HERE.name,title='Argument-count dependence in AI operator attribution',status='DEVELOPMENT_COMPLETE_MATCHED_VALIDATION_PENDING',finding='Equalizing counts in frozen masked model raises human errors from 0/61 to 30/61; retrained count-free model recalls 79.77% at 4.32% group FPR. Source confounding unresolved.',reason='Representation sensitivity demonstrated on exposed data. Fresh matched operators and environments required; passive fingerprinting already exists in TRACE (https://arxiv.org/abs/2605.01186).',results='RESULTS.json')
reg['experiments']=[x for x in reg['experiments'] if x['id']!='PX-119']+[entry]
reg['latest_candidate_paper']['experiment']='PX-119';reg['latest_candidate_paper']['status']='WORKING_PRAXIS_COUNT_DEPENDENCE_FOUND_MATCHED_VALIDATION_PENDING'
regpath.write_text(json.dumps(reg,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'audit':audit,'reproduction':checks,'paper_pages':q['pages']}))
