"""Reconstruct counts and operating thresholds from saved predictions."""
import collections,csv,hashlib,json,sys,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
base=Path(sys.argv[1]);result=json.loads((base/'RESULTS.json').read_text())
records=json.loads(Path('C:/w/px118_20261005/records.json').read_text())
lookup={r['id']:r for r in records['rows']+records['external']}
checks=[]
def check(name,ok):
 checks.append({'check':name,'pass':bool(ok)})
 assert ok,name
for r in result['results']:
 e=json.loads((base/(r['model']+'_'+r['condition']+'_predictions.json')).read_text());t=e['test'];q=r['threshold']
 for tag,y,p in [('tp',1,True),('fn',1,False),('fp',0,True),('tn',0,False)]:
  check(r['model']+r['condition']+tag,sum(x['label']==y and (x['score']>=q)==p for x in t)==r[tag])
 groups=collections.defaultdict(list)
 for x in t:
  if x['label']==0:groups[x['group']].append(x['score']>=q)
 check('group FPR',abs(np.mean([np.mean(v) for v in groups.values()])-r['human_group_mean_fpr'])<1e-12)
 f=[lookup[i] for i in e['fit_ids']];c=[lookup[x['id']] for x in e['calibration']]
 check('fit/cal groups disjoint',not {x['group'] for x in f}&{x['group'] for x in c})
 check('fit/test groups disjoint',not {x['group'] for x in f}&{x['group'] for x in t})
 check('cal/test groups disjoint',not {x['group'] for x in c}&{x['group'] for x in t})
 cg=collections.defaultdict(list)
 for x in e['calibration']:
  rr=lookup[x['id']]
  if rr['label']==0:cg[rr['group']].append(x['score'])
 vals=[v for vs in cg.values() for v in vs]
 candidates=np.unique(np.r_[min(x['score'] for x in e['calibration'])-1,vals,np.nextafter(vals,np.inf),max(x['score'] for x in e['calibration'])+1])
 threshold=next(float(v) for v in candidates if np.mean([np.mean(np.array(vs)>=v) for vs in cg.values()])<=.05)
 check('minimum calibration threshold',threshold==q)
 if r['condition'].startswith('family_'):
  family=r['condition'][7:];check('family excluded',all(x['family']!=family for x in f+c))
check('all30comparisons',len(result['results'])==30)
check('worker success',(base/'WORKER_EXIT.txt').read_text().strip()=='0')
for name in ['lexical','ordered']:
 r=next(r for r in result['results'] if r['model']==name and r['condition']=='main')
 old=json.loads((HERE.parent/'aivh_gambit_20261005/RESULTS.json').read_text())
 prev=next(x for x in old['results'] if x['model']==('verbs' if name=='ordered' else name) and x['condition']=='participant_holdout')
 check('previous model reproduction',all(r[k]==prev[k] for k in ['tp','fp','tn','fn','threshold']))
report={'status':'PASS','checks':checks,'source_sha256':hashlib.sha256((base/'RESULTS.json').read_bytes()).hexdigest()}
(HERE/'AUDIT.json').write_text(json.dumps(report,indent=2))
(HERE/'RESULTS.json').write_text(json.dumps(result,indent=2))
with (HERE/'RESULTS_TABLE.csv').open('w',newline='') as f:
 keys=['model','condition','agent_recall','fp','tn','human_group_mean_fpr','auroc','meets_target']
 w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(result['results'])
# Paired development intervals: resample common AI sessions, conditional on fitted models.
ps={k:json.loads((base/(k+'_main_predictions.json')).read_text())['test'] for k in ['ordered','shuffled','frequency','masked']}
rs={r['model']:r for r in result['results'] if r['condition']=='main'};contrasts=[]
for a,b in [('ordered','frequency'),('ordered','shuffled'),('masked','ordered')]:
 aa={r['id']:r for r in ps[a] if r['label']==1};bb={r['id']:r for r in ps[b] if r['label']==1};assert aa.keys()==bb.keys()
 dif=np.array([int(aa[i]['score']>=rs[a]['threshold'])-int(bb[i]['score']>=rs[b]['threshold']) for i in aa])
 rng=np.random.default_rng(11801);boot=np.array([np.mean(rng.choice(dif,len(dif),replace=True)) for _ in range(2000)])
 contrasts.append({'contrast':a+' minus '+b,'recall_difference':float(dif.mean()),'conditional_paired_session_bootstrap95':list(np.quantile(boot,[.025,.975]))})
(HERE/'PAIRED_CONTRASTS.json').write_text(json.dumps({'scope':'Exposed-data descriptive intervals; conditional on source, prompts, fits and thresholds. Not population operator inference.','contrasts':contrasts},indent=2))
with zipfile.ZipFile(HERE/'Prediction_Evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in base.glob('*predictions.json'):z.write(p,p.name)
print(json.dumps({'audit_checks':len(checks),'contrasts':contrasts}))
