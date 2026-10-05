"""PX-118 paired development tests. Logged commands are inert strings."""
import collections,concurrent.futures,hashlib,json,time
from pathlib import Path
import joblib,numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
from prior import weights,metrics,dedup

OUT=Path('outputs');OUT.mkdir(exist_ok=True)
D=json.loads(Path('records.json').read_text());LOOK={r['id']:r for r in D['rows']+D['external']}
P=json.loads(Path('base_predictions.json').read_text())
BASE=[[LOOK[r['id']] for r in P[k]] for k in ['fit','calibration','test']]
KINDS=['lexical','trace_svc','frequency','ordered','shuffled','masked']

def texts(rows,kind,mask=False):
 out=[]
 for r in rows:
  cs=r['commands']
  if kind in ['frequency','ordered','shuffled']:
   cs=[c.split()[0] for c in cs]
  elif kind=='masked' or mask:
   cs=[' '.join([c.split()[0]]+['ARG']*(len(c.split())-1)) for c in cs]
  if kind=='shuffled':
   seed=int(hashlib.sha256((r['id']+'11801').encode()).hexdigest()[:16],16)
   cs=list(np.random.default_rng(seed).permutation(cs))
  out.append(' '.join(cs))
 return out

def fit(kind,parts,name):
 f,c,t=parts
 if any(len({r['label'] for r in x})<2 for x in parts):
  return {'model':kind,'condition':name,'status':'SKIP_MISSING_CLASS'}
 assert not ({r['group'] for r in f}&{r['group'] for r in c+t})
 assert not ({r['group'] for r in c}&{r['group'] for r in t})
 assert not ({r['fingerprint'] for r in f}&{r['fingerprint'] for r in c+t})
 ngram=(1,1) if kind=='frequency' else ((1,3) if kind in ['ordered','shuffled'] else (1,2))
 v=TfidfVectorizer(ngram_range=ngram,sublinear_tf=True,max_features=10000 if kind=='trace_svc' else 20000)
 est=LinearSVC(C=1,random_state=11801,max_iter=20000,dual='auto') if kind=='trace_svc' else LogisticRegression(C=1,random_state=11703,max_iter=2000)
 m=make_pipeline(v,est);y=np.array([r['label'] for r in f])
 m.fit(texts(f,kind),y,**{list(m.named_steps)[-1]+'__sample_weight':weights(f,y)})
 def score(rows,mask=False):
  tx=texts(rows,kind,mask)
  return m.decision_function(tx) if kind=='trace_svc' else m.predict_proba(tx)[:,1]
 pc=score(c);pt=score(t);yc=np.array([r['label'] for r in c]);hc=yc==0;wc=weights(c,yc)
 ts=np.unique(np.r_[pc.min()-1,pc[hc],np.nextafter(pc[hc],np.inf),pc.max()+1])
 threshold=next(float(q) for q in ts if np.average(pc[hc]>=q,weights=wc[hc])<=.05)
 result={'model':kind,'condition':name,'status':'DEVELOPMENT_COMPLETE','threshold':threshold,'calibration_auroc':float(roc_auc_score(yc,pc)),**metrics(t,pt,threshold)}
 result['meets_target']=bool(result['agent_recall']>=(.8 if name=='main' else .7) and result['human_group_mean_fpr']<=.05)
 evidence={'fit_ids':[r['id'] for r in f],'calibration':[{'id':r['id'],'score':float(s)} for r,s in zip(c,pc)],'test':[{'id':r['id'],'label':r['label'],'group':r['group'],'score':float(s)} for r,s in zip(t,pt)]}
 if name=='main':
  pm=score(t,True);x=v.transform(texts(t,kind));xm=v.transform(texts(t,kind,True));co=est.coef_[0]
  additive=np.asarray(x@co).ravel()+est.intercept_[0]
  residual=float(np.max(np.abs(additive-m.decision_function(texts(t,kind)))))
  js=[]
  for a,b in zip(x.multiply(co).tocsr(),xm.multiply(co).tocsr()):
   sa=set(a.indices[np.argsort(np.abs(a.data))[-5:]]);sb=set(b.indices[np.argsort(np.abs(b.data))[-5:]])
   js.append(len(sa&sb)/len(sa|sb) if sa|sb else 1.)
  result['argument_masking']={'flip_rate':float(np.mean((pt>=threshold)!=(pm>=threshold))),'mean_abs_score_change':float(np.mean(np.abs(pt-pm))),'top5_mean_jaccard':float(np.mean(js)),**metrics(t,pm,threshold)}
  result['explanation_reconstruction_max_error']=residual
  assert residual<1e-10
  if kind in ['frequency','ordered','shuffled']:assert np.array_equal(pt,pm)
  for tag in ['kypo','rouxii']:
   ext=json.loads(Path('external_'+tag+'.json').read_text())
   seen={r['fingerprint'] for r in f+c};ext=[r for r in ext if r['fingerprint'] not in seen]
   if ext:
    pe=score(ext);result['external_'+tag]=metrics(ext,pe,threshold)
    evidence['external_'+tag]=[{'id':r['id'],'label':r['label'],'group':r['group'],'score':float(s)} for r,s in zip(ext,pe)]
   else:result['external_'+tag]={'status':'NOT_ESTIMABLE_NO_ELIGIBLE_RECORDS'}
  joblib.dump({'model':m,'kind':kind,'threshold':threshold},OUT/(kind+'.joblib'))
 (OUT/(kind+'_'+name+'_predictions.json')).write_text(json.dumps(evidence))
 return result

def run(kind):
 results=[fit(kind,BASE,'main')]
 for fam in sorted({r['family'] for r in D['rows'] if r['label']==1}):
  # Reuse prior full split manifest to include all eligible held-family records.
  full=[[LOOK[i] for i in ids] for ids in json.loads(Path('split_manifest.json').read_text())['partitions']]
  held=[r for r in full[2] if r['label']==0]+[r for p in full for r in p if r['family']==fam]
  seen={r['fingerprint'] for r in held}
  f=[r for r in full[0] if r['family']!=fam and r['fingerprint'] not in seen]
  c=[r for r in full[1] if r['family']!=fam and r['fingerprint'] not in seen]
  h=[r for r in f if r['label']==0];a=[r for r in f if r['label']==1]
  if len(a)>4*len(h):a=[a[i] for i in np.random.default_rng(11703).choice(len(a),4*len(h),replace=False)]
  results.append(fit(kind,[h+a,c,held],'family_'+fam))
 return results

if __name__=='__main__':
 start=time.monotonic()
 with concurrent.futures.ThreadPoolExecutor(3) as pool:rs=[r for group in pool.map(run,KINDS) for r in group]
 mains=[r for r in rs if r['condition']=='main']
 selected=sorted(mains,key=lambda r:(-r['calibration_auroc'],r['model']))[0]['model']
 (OUT/'RESULTS.json').write_text(json.dumps({'experiment':'PX-118','selected_by_calibration':selected,'seconds':time.monotonic()-start,'results':rs},indent=2))
 print(json.dumps({'conditions':len(rs),'selected':selected,'seconds':time.monotonic()-start}),flush=True)
