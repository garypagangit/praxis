import json,pathlib,sys,collections,hashlib
import numpy as np,joblib
from sklearn.metrics import roc_auc_score
P=pathlib.Path(__file__).resolve().parent;O=P/'results';rows=json.loads((O/'records.json').read_text());modelroot=pathlib.Path(sys.argv[1]);out=[];preds=[];coverage=[]
def stats(rs,ss,t):
 y=np.array([r['label'] for r in rs]);ss=np.array(ss);h=y==0;a=y==1;g=sorted(set(r['group'] for r in rs if r['label']==0));return {'human_sessions':int(h.sum()),'human_experts':len(g),'ai_sessions':int(a.sum()),'ai_detected':int(sum(ss[a]>=t)),'human_false_flags':int(sum(ss[h]>=t)),'ai_recall':float(np.mean(ss[a]>=t)) if a.any() else None,'human_session_fpr':float(np.mean(ss[h]>=t)) if h.any() else None,'human_equal_expert_fpr':float(np.mean([np.mean([s>=t for r,s in zip(rs,ss) if r['group']==gg and r['label']==0]) for gg in g])) if g else None,'auroc':float(roc_auc_score(y,ss)) if h.any() and a.any() else None}
for n in [10,5]:
 eligible=[{**r,'commands':r['commands'][:n]} for r in rows if len(r['commands'])>=n and r['benchmark']=='intercode-ctf']
 ht=set(r['task'] for r in eligible if r['label']==0);at=set(r['task'] for r in eligible if r['label']==1);common=ht&at
 coverage.append({'window':n,'all_source_sessions':dict(collections.Counter(r['family'] for r in rows if r['benchmark']=='intercode-ctf')),'eligible_sessions':dict(collections.Counter(r['family'] for r in eligible)),'shared_tasks':len(common),'matched_sessions':dict(collections.Counter(r['family'] for r in eligible if r['task'] in common))})
 for subset in ['all_eligible','matched_tasks']:
  rs=[r for r in eligible if subset=='all_eligible' or r['task'] in common]
  if not rs:continue
  for kind in ['lexical','masked','frequency','ordered']:
   b=joblib.load(modelroot/(kind+'.joblib'));tx=[]
   for r in rs:
    cs=r['commands']
    if kind in ['frequency','ordered']:cs=[c.split()[0] for c in cs]
    if kind=='masked':cs=[' '.join([c.split()[0]]+['ARG']*(len(c.split())-1)) for c in cs]
    tx.append(' '.join(cs))
   ss=b['model'].predict_proba(tx)[:,1];t=b['threshold'];out.append({'window':n,'subset':subset,'model':kind,'frozen_threshold':t,**stats(rs,ss,t)})
   preds.extend({'window':n,'subset':subset,'model':kind,'id':r['id'],'task':r['task'],'group':r['group'],'family':r['family'],'label':r['label'],'score':float(s),'threshold':t} for r,s in zip(rs,ss))
(O/'TRANSFER_RESULTS.json').write_text(json.dumps({'note':'Frozen PX118 models; n=5 is a window-length sensitivity, not the trained n=10 operating condition. Pilot extraction subject to manual audit.','coverage':coverage,'results':out},indent=2));(O/'TRANSFER_PREDICTIONS.json').write_text(json.dumps(preds,indent=2));print(json.dumps({'coverage':coverage,'results':out},indent=2))
