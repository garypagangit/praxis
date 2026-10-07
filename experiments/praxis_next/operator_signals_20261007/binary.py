"""Small matched-task pilot using archived PX121 extraction, no new attacks."""
import argparse, collections, hashlib, json
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from experiment import features, verb
from prepare import HERE,save,sha

def paired(rs):
 shared={r['task'] for r in rs if r['label']==0}&{r['task'] for r in rs if r['label']==1}
 return [r for r in rs if r['task'] in shared]

def run(path):
 source=json.loads(path.read_text());rows=[]
 for r in source:
  if len(r['shell_commands'])<3:continue
  r=dict(r);cs=r['shell_commands'][:10]
  r['fp']=hashlib.sha256('\n'.join(cs).encode()).hexdigest()
  r['f']=features([{'i':i,'c':c,'o':'','t':[None,None]} for i,c in enumerate(cs)])['correction']
  r['text']=' '.join(verb(c) for c in cs);rows.append(r)
 rows=paired(rows);experts=sorted({r['group'] for r in rows if not r['label']})
 predictions=[];folds=[];fits=0
 for i,expert in enumerate(experts):
  cg=experts[(i+1)%len(experts)]
  tt={r['task'] for r in rows if r['group']==expert};ct={r['task'] for r in rows if r['group']==cg}-tt
  te=paired([r for r in rows if r['task'] in tt and (r['label'] or r['group']==expert)])
  ca=paired([r for r in rows if r['task'] in ct and (r['label'] or r['group']==cg)])
  tr=paired([r for r in rows if r['task'] not in tt|ct and (r['label'] or r['group'] not in {expert,cg})])
  seen={r['fp'] for r in tr};ca=paired([r for r in ca if r['fp'] not in seen]);seen|={r['fp'] for r in ca};te=paired([r for r in te if r['fp'] not in seen])
  parts=[tr,ca,te];fold={'test_expert':expert,'cal_expert':cg,'counts':[[sum(r['label']==k for r in rs) for k in [0,1]] for rs in parts],
   'parts':[[{'id':r['id'],'task':r['task'],'group':r['group'],'label':r['label'],'fp':r['fp']} for r in rs] for rs in parts]}
  if any(len({r['label'] for r in rs})<2 for rs in parts):fold['status']='skipped';folds.append(fold);continue
  fold['status']='complete';folds.append(fold)
  for a,b in [(tr,ca),(tr,te),(ca,te)]:
   assert not ({r['task'] for r in a}&{r['task'] for r in b})
   assert not ({r['group'] for r in a if not r['label']}&{r['group'] for r in b if not r['label']})
   assert not ({r['fp'] for r in a}&{r['fp'] for r in b})
  y=np.array([r['label'] for r in tr]);freq=collections.Counter((r['task'],r['label']) for r in tr)
  w=np.array([1/freq[r['task'],r['label']] for r in tr]);w*=len(w)/sum(w)
  for kind in ['verbs','correction','combined','edit_retry','shuffled_combined']:
   v=TfidfVectorizer(token_pattern=r'(?u)\b\w+\b',sublinear_tf=True,max_features=8000)
   tx=[v.fit_transform([r['text'] for r in tr])]+[v.transform([r['text'] for r in rs]) for rs in [ca,te]]
   sc=StandardScaler();nums=[np.array([r['f'][:2] if kind=='edit_retry' else r['f'] for r in rs]) for rs in parts]
   nums=[sc.fit_transform(nums[0]),sc.transform(nums[1]),sc.transform(nums[2])]
   xs=tx if kind=='verbs' else [sparse.csr_matrix(n) for n in nums] if kind in {'correction','edit_retry'} else [sparse.hstack([t,n],format='csr') for t,n in zip(tx,nums)]
   yy=np.random.default_rng(1707+i).permutation(y) if kind=='shuffled_combined' else y
   m=LogisticRegression(C=1,max_iter=2000,random_state=17).fit(xs[0],yy,sample_weight=w);fits+=1
   pc=m.predict_proba(xs[1])[:,1];pt=m.predict_proba(xs[2])[:,1]
   th=float(np.nextafter(max(s for r,s in zip(ca,pc) if not r['label']),np.inf))
   for part,rs,ss in [('cal',ca,pc),('test',te,pt)]:
    predictions.extend({'fold':expert,'model':kind,'part':part,'id':r['id'],'group':r['group'],'family':r['family'],'label':r['label'],'score':float(s),'threshold':th,'flag':bool(s>=th)} for r,s in zip(rs,ss))
 summary=[]
 for kind in sorted({r['model'] for r in predictions}):
  rs=[r for r in predictions if r['part']=='test' and r['model']==kind];h=[r for r in rs if not r['label']];a=[r for r in rs if r['label']]
  gs=sorted({r['group'] for r in h});gf=float(np.mean([np.mean([r['flag'] for r in h if r['group']==g]) for g in gs]))
  summary.append({'model':kind,'human_n':len(h),'ai_n':len(a),'human_false_flags':sum(r['flag'] for r in h),'ai_detected':sum(r['flag'] for r in a),
   'ai_recall':float(np.mean([r['flag'] for r in a])),'human_fpr':float(np.mean([r['flag'] for r in h])),'equal_expert_fpr':gf,
   'unique_test_ai_sessions':len({r['id'] for r in a}),'experts':len(gs)})
 report={'input_sha256':sha(path),'source_records':len(source),'eligible_matched':len(rows),'eligible_counts':dict(collections.Counter(r['family'] for r in rows)),
  'fits':fits,'folds':folds,'summary':summary,'status':'EXPLORATORY_CORRECTION_PROXIES_WITH_INCOMPLETE_HUMAN_EXTRACTION'}
 save(HERE/'evidence/BINARY_RESULTS.json',report);save(HERE/'evidence/BINARY_PREDICTIONS.json',predictions)
 print(json.dumps({k:v for k,v in report.items() if k!='folds'},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--records',type=__import__('pathlib').Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=1):run(a.records)
