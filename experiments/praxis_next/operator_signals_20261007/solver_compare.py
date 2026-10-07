"""Compare identical experiment configurations before/after optimizer repair."""
import gzip,json
import numpy as np
from prepare import HERE,save

def load(p):
 if p.exists():return json.loads(p.read_text())
 with gzip.open(str(p)+'.gz','rt',encoding='utf-8') as f:return json.load(f)

old=HERE/'initial_solver/evidence';new=HERE/'evidence';comp=[]
for scores,predictions in [('RESULTS.json','PREDICTIONS.json'),('ABLATION_RESULTS.json','ABLATION_PREDICTIONS.json')]:
 a={r['key']:r for r in load(old/scores)};b={r['key']:r for r in load(new/scores)}
 ap={r['key']:r for r in load(old/predictions)};bp={r['key']:r for r in load(new/predictions)}
 assert a.keys()==b.keys()==ap.keys()==bp.keys()
 for key in a:
  assert ap[key]['id']==bp[key]['id'] and ap[key]['y']==bp[key]['y']
  deltas={k:float(b[key][k]-a[key][k]) for k in ['accuracy','macro_f1','coverage','accepted_accuracy','wrong_per_all','known_coverage','known_accepted_accuracy','unknown_acceptance'] if k in a[key] and a[key][k] is not None and b[key][k] is not None}
  comp.append({'key':key,'n':len(ap[key]['y']),'changed_labels':sum(x!=y for x,y in zip(ap[key]['pred'],bp[key]['pred'])),'metric_deltas_primal_minus_initial':deltas})
run=load(new/'RUN.json');abrun=load(new/'ABLATION_RUN.json')
assert run['warning_capture_complete'] and not run['warnings'] and not abrun['warnings']
save(new/'SOLVER_COMPARISON.json',{'matched_result_rows':len(comp),'same_session_ids_and_labels':True,
 'primary_warnings':run['warnings'],'ablation_warnings':abrun['warnings'],
 'max_absolute_macro_f1_change':max(abs(x['metric_deltas_primal_minus_initial'].get('macro_f1',0)) for x in comp),
 'results':comp,'note':'Same data/objective, numerical recheck; not independent replication. Initial solver evidence retained.'})
print('Solver comparison PASS:',len(comp),'matched rows; no final convergence warnings')
