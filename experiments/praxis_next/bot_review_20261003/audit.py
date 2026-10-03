import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
cases=json.loads((HERE.parent/'explanation_trials_20261003/PX102_CASES.json').read_text())
responses=json.loads((HERE/'RESPONSES.json').read_text());gold={}
for c in cases:
 p=np.array(c['member_probabilities']);gold[c['case_id']]=bool((p.argmax(1)>0).any() and p.mean(0).argmax()==0)
for r in responses:
 if r['bot'] in ['calculator','verifier'] and r['condition']!='missing_member':
  a=r.get('numeric_answer',r['answer']);assert a==gold[r['case_id']]
 if r['bot']=='verifier':
  expected='REJECTED' if r['condition'].startswith('wrong_') else 'ABSTAIN' if r['condition']=='missing_member' else 'CALCULATED' if r['condition']=='scores_only' else 'VERIFIED'
  assert r['status']==expected
assert len(responses)==216
(HERE/'AUDIT.json').write_text(json.dumps({'status':'PASS','review_records':216,'independently_reconstructed_gold_cases':12,'scope':'Independent NumPy reconstruction; predefined faults only'},indent=2)+'\n')
print('PASS: 216 records; independent score reconstruction')
