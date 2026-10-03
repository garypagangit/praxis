import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
cases={c['id']:c for c in json.loads((HERE/'CASES.json').read_text())};records=json.loads((HERE/'EVALUATION.json').read_text());checks=0
for r in records:
 c=cases[r['id']]
 if c['kind']=='aggregation':
  p=np.array(c['members']);assert p.mean(0).argmax()==0
  cause='aggregation' if (p.argmax(1)>0).any() else 'all_silent'
 else:
  p=np.array(c['experts']);assert p[int(c['requested']==1 and c['delay']<=c['deadline'])].argmax()==0
  cause='all_silent' if not (p.argmax(1)>0).any() else 'deadline' if c['requested']==1 and c['delay']>1 else 'selection'
 assert cause==r['cause']
 if r['method']!='final_only':assert r['diagnosis']==cause
 for rr in r['repairs']:
  proposal=rr['proposal']
  if c['kind']=='aggregation':expected=bool((p.argmax(1)>0).any()) if proposal=='restore' else bool(p.mean(0).argmax()>0)
  else:expected=False if proposal=='extend_deadline' else bool(p[int((proposal=='restore' or c['requested']==1) and c['delay']<=1)].argmax()>0)
  assert rr['observed_feasible_warning']==expected
  if r['method']!='final_only':assert rr['predicted_feasible_warning']==expected
  checks+=1
(HERE/'AUDIT.json').write_text(json.dumps({'status':'PASS','review_records':len(records),'proposal_records_checked':checks,'cases':len(cases),'scope':'Separate NumPy reconstruction of known injected mechanisms; not an independent natural-failure benchmark'},indent=2)+'\n')
print('PASS',len(cases),checks)
