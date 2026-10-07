"""PX121 exploratory grouped evaluation; command strings are never executed."""
import json,pathlib,collections,time,hashlib
import numpy as np
from scipy.sparse import hstack,csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
P=pathlib.Path(__file__).resolve().parent;O=P/'results';ALL=json.loads((O/'PX121_records.json').read_text());R=[r for r in ALL if len(r['atoms'])>=3];shared={r['task'] for r in R if not r['label']}&{r['task'] for r in R if r['label']};R=[r for r in R if r['task'] in shared];groups=sorted({r['group'] for r in R if not r['label']});pred=[];folds=[];controls=[];calibration_predictions=[];coefficients=[];start=time.monotonic()
def paired(rs):
 tasks={r['task'] for r in rs if not r['label']}&{r['task'] for r in rs if r['label']};return [r for r in rs if r['task'] in tasks]
def metrics(rr):
 h=[r for r in rr if not r['label']];a=[r for r in rr if r['label']];g=sorted({r['group'] for r in h});return {'human_predictions':len(h),'ai_predictions':len(a),'human_false_flags':sum(r['flag'] for r in h),'ai_detected':sum(r['flag'] for r in a),'ai_recall':np.mean([r['flag'] for r in a]).item() if a else None,'human_fpr':np.mean([r['flag'] for r in h]).item() if h else None,'equal_expert_fpr':np.mean([np.mean([r['flag'] for r in h if r['group']==gg]) for gg in g]).item() if g else None,'experts':len(g)}
def counts(rs):
 result=[]
 for r in rs:
  a=np.array([min(x[1],20) for x in r['atoms'][:10]],float);result.append([a.mean(),a.std(),np.median(a),a.max(),np.mean(a==0),np.mean(a>=4)])
 return np.array(result)
for i,group in enumerate(groups):
 calgroup=groups[(i+1)%len(groups)];tt={r['task'] for r in R if r['group']==group};ct={r['task'] for r in R if r['group']==calgroup}-tt
 test=paired([r for r in R if r['task'] in tt and (r['label'] or r['group']==group)])
 cal=paired([r for r in R if r['task'] in ct and (r['label'] or r['group']==calgroup)])
 fit=paired([r for r in R if r['task'] not in tt|ct and (r['label'] or r['group'] not in [group,calgroup])])
 before=[len(fit),len(cal),len(test)];seen={r['fingerprint'] for r in test};cal=paired([r for r in cal if r['fingerprint'] not in seen]);seen|={r['fingerprint'] for r in cal};fit=paired([r for r in fit if r['fingerprint'] not in seen]);parts=[fit,cal,test]
 rec={'test_expert':group,'calibration_expert':calgroup,'before_dedup':before,'counts':[[sum(r['label']==l for r in rs) for l in [0,1]] for rs in parts],'ids':[[r['id'] for r in rs] for rs in parts]}
 if any(len({r['label'] for r in rs})<2 for rs in parts):rec['status']='SKIPPED_MISSING_CLASS';folds.append(rec);continue
 for a,b in [(fit,cal),(fit,test),(cal,test)]:
  assert not ({r['task'] for r in a}&{r['task'] for r in b})
  assert not ({r['group'] for r in a if not r['label']}&{r['group'] for r in b if not r['label']})
  assert not ({r['fingerprint'] for r in a}&{r['fingerprint'] for r in b})
 rec['status']='EXPLORATORY_COMPLETE';folds.append(rec);y=np.array([r['label'] for r in fit]);freq=collections.Counter((r['task'],r['label']) for r in fit);w=np.array([1/freq[r['task'],r['label']] for r in fit]);w*=len(w)/sum(w)
 # Every matched task has equal weighted class mass, so task identity alone has no signal.
 for task in {r['task'] for r in fit}:assert abs(sum(ww*(2*r['label']-1) for r,ww in zip(fit,w) if r['task']==task))<1e-10
 for kind in ['verbs','transitions','counts','combined','shuffled_labels']:
  scaler=StandardScaler();nums=[scaler.fit_transform(counts(fit)),scaler.transform(counts(cal)),scaler.transform(counts(test))]
  v=TfidfVectorizer(token_pattern=r'(?u)\b[\w.+-]+\b',ngram_range=(1,2) if kind=='transitions' else (1,1),sublinear_tf=True,max_features=20000)
  tx=[[' '.join(a[0] for a in r['atoms'][:10]) for r in rs] for rs in parts];vec=[v.fit_transform(tx[0]),v.transform(tx[1]),v.transform(tx[2])]
  X=[csr_matrix(x) for x in nums] if kind=='counts' else [hstack([a,csr_matrix(b)]).tocsr() for a,b in zip(vec,nums)] if kind=='combined' else vec
  yy=np.random.default_rng(12101+i).permutation(y) if kind=='shuffled_labels' else y
  m=LogisticRegression(C=1,random_state=12101,max_iter=2000);m.fit(X[0],yy,sample_weight=w);pc=m.predict_proba(X[1])[:,1];pt=m.predict_proba(X[2])[:,1];threshold=float(np.nextafter(max(s for r,s in zip(cal,pc) if not r['label']),np.inf))
  calibration_predictions.extend({'fold':group,'kind':kind,'id':r['id'],'label':r['label'],'score':float(sc),'threshold':threshold} for r,sc in zip(cal,pc))
  names=['argc_mean','argc_std','argc_median','argc_max','argc_zero_fraction','argc_ge4_fraction'] if kind=='counts' else list(v.get_feature_names_out())+(['argc_mean','argc_std','argc_median','argc_max','argc_zero_fraction','argc_ge4_fraction'] if kind=='combined' else [])
  coefficients.append({'fold':group,'kind':kind,'intercept':float(m.intercept_[0]),'coefficients':dict(zip(names,map(float,m.coef_[0]))),'numeric_scaler_mean':scaler.mean_.tolist(),'numeric_scaler_scale':scaler.scale_.tolist()})
  # Faithful additive reconstruction check; no causal or analyst-benefit claim.
  assert np.max(np.abs(np.asarray(X[2]@m.coef_[0]).ravel()+m.intercept_[0]-m.decision_function(X[2])))<1e-10
  for r,s in zip(test,pt):pred.append({'fold':group,'kind':kind,'id':r['id'],'task':r['task'],'group':r['group'],'label':r['label'],'family':r['family'],'score':float(s),'threshold':threshold,'flag':bool(s>=threshold),'parse_failures':r['parse_failures']})
lookup={(r['fold'],r['kind'],r['id']):r for r in pred};sel=[]
for r in pred:
 if r['kind']!='verbs':continue
 b=lookup[r['fold'],'combined',r['id']];abstain=r['flag']!=b['flag'] or bool(r['parse_failures']);sel.append({**r,'kind':'agreement','flag':r['flag'] and b['flag'] and not abstain,'abstain':abstain})
summaries={k:metrics([r for r in pred if r['kind']==k]) for k in sorted({r['kind'] for r in pred})};summaries['agreement']={**metrics(sel),'abstentions':sum(r['abstain'] for r in sel),'eligible_prediction_coverage':sum(not r['abstain'] for r in sel)/len(sel) if sel else None}
for k in summaries:
 rr=sel if k=='agreement' else [r for r in pred if r['kind']==k];summaries[k]['by_family']={f:metrics([r for r in rr if r['family']==f]) for f in ['anthropic','openai','google']}
report={'status':'EXPLORATORY_SMALL_SAMPLE_NOT_DEFENSE_VALIDATION','source_sessions':len(ALL),'eligible_humans':sum(not r['label'] for r in R),'eligible_ai':sum(r['label'] for r in R),'shared_tasks':len(shared),'independent_experts':len(groups),'minimum_atomic_commands':3,'prefix_maximum':10,'completed_folds':sum(f['status']=='EXPLORATORY_COMPLETE' for f in folds),'seconds':time.monotonic()-start,'summaries':summaries,'folds':folds,'task_only_negative_control':'All fit tasks have exactly equal weighted human and AI mass; a task-only classifier has no class signal. No data-driven negative-control result asserted.'}
(O/'PX121_CALIBRATION.json').write_text(json.dumps(calibration_predictions,indent=2));(O/'PX121_COEFFICIENTS.json').write_text(json.dumps(coefficients,indent=2));(O/'PX121_RESULTS.json').write_text(json.dumps(report,indent=2));(O/'PX121_PREDICTIONS.json').write_text(json.dumps(pred+sel,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['folds','summaries']},indent=2));print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='by_family'} for k,v in summaries.items()},indent=2))
