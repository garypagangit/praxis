"""Frozen offline pilot. Inputs are parsed as inert text, never executed."""
import argparse, collections, copy, difflib, hashlib, json, pathlib, re, shlex, time, warnings
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits
from prepare import HERE, save, sha

LABELS=['alibaba','deepseek','google','meta']
MODELS=['lexical','structure','correction','recovery','timing','lexical_recovery']
ERROR=re.compile(r'command not found|no such file or directory|permission denied|invalid option|unrecognized option|syntax error|not installed|cannot access',re.I)
INSPECT={'ls','cat','head','tail','which','whereis','pwd','file','stat','find','help','man','type'}
CORRECTION_NAMES=['exact_retry_rate','near_verb_edit_rate','same_verb_changed_rate','mean_command_similarity','unique_verb_fraction','mean_characters','std_characters','compound_fraction']
RECOVERY_NAMES=CORRECTION_NAMES+['error_rate','after_error_retry_rate','after_error_change_rate','after_error_inspect_rate','after_error_near_edit_rate','after_success_retry_rate']
TIMING_NAMES=['log_first_field_median','log_first_field_std','log_second_field_median','log_second_field_std','log_pair_difference_median','log_pair_difference_std']
RESULTS=[];PRED=[];SPLITS=[];FIT_WARNINGS=[];FIT_COUNT=0

def tokens(c):
 try:return shlex.split(c)
 except ValueError:return c.split()

def verb(c):
 ts=tokens(c)
 return ts[0].split('/')[-1].lower() if ts else '_empty'

def nearby(a,b):
 # Deliberately named a proxy. No claim that adjacent edits are human typos.
 if a==b or min(len(a),len(b))<3 or abs(len(a)-len(b))>2:return False
 prev=list(range(len(b)+1))
 for i,x in enumerate(a):
  cur=[i+1]
  for j,y in enumerate(b):cur.append(min(cur[-1]+1,prev[j+1]+1,prev[j]+(x!=y)))
  prev=cur
 return prev[-1]<=2

def features(turns):
 cs=[t['c'] for t in turns];vs=[verb(c) for c in cs]
 pairs=[(i-1,i) for i in range(1,len(turns)) if turns[i]['i']==turns[i-1]['i']+1]
 n=max(1,len(pairs));exact=sum(cs[a]==cs[b] for a,b in pairs)
 near=sum(nearby(vs[a],vs[b]) for a,b in pairs)
 corr=[exact/n,near/n,sum(vs[a]==vs[b] and cs[a]!=cs[b] for a,b in pairs)/n,
  sum(difflib.SequenceMatcher(None,cs[a],cs[b]).ratio() for a,b in pairs)/n,
  len(set(vs))/max(1,len(vs)),float(np.mean([len(c) for c in cs])),
  float(np.std([len(c) for c in cs])),sum(bool(re.search(r';|&&|\|',c)) for c in cs)/max(1,len(cs))]
 ep=[(a,b) for a,b in pairs if ERROR.search(turns[a]['o'])]
 sp=[(a,b) for a,b in pairs if not ERROR.search(turns[a]['o'])]
 rec=corr+[len(ep)/n,sum(cs[a]==cs[b] for a,b in ep)/max(1,len(ep)),
  sum(cs[a]!=cs[b] for a,b in ep)/max(1,len(ep)),
  sum(vs[b] in INSPECT for a,b in ep)/max(1,len(ep)),
  sum(nearby(vs[a],vs[b]) for a,b in ep)/max(1,len(ep)),
  sum(cs[a]==cs[b] for a,b in sp)/max(1,len(sp))]
 # Only past completed turns are used; command n's output/timing is unavailable.
 ts=np.array([t['t'] for t in turns[:-1] if all(v is not None for v in t['t'])],dtype=float)
 timing=[]
 for arr in ([ts[:,0],ts[:,1],np.maximum(0,ts[:,1]-ts[:,0])] if len(ts) else [[],[],[]]):
  timing.extend([float(np.log1p(np.median(arr))) if len(arr) else 0.,float(np.log1p(np.std(arr))) if len(arr) else 0.])
 structure=[]
 for i,(c,v) in enumerate(zip(cs,vs)):
  ts=tokens(c);structure.extend(['v_'+v,'argc_'+str(min(20,max(0,len(ts)-1)))])
  structure.extend('op_'+x for x in re.findall(r'&&|\|\||[;|<>]',c))
  if i and turns[i]['i']==turns[i-1]['i']+1:structure.append('pair_'+vs[i-1]+'_'+v)
 return {'lexical':'\n'.join(cs),'structure':' '.join(structure),'correction':corr,'recovery':rec,'timing':timing}

class Model:
 def __init__(self,kind):self.kind=kind
 def design(self,fs,fit=False):
  mats=[]
  if self.kind in {'lexical','structure','lexical_recovery'}:
   k='structure' if self.kind=='structure' else 'lexical';texts=[f[k] for f in fs]
   if fit:
    self.vec=TfidfVectorizer(ngram_range=(1,2),max_features=8000,sublinear_tf=True,token_pattern=r'(?u)\b\w+\b')
    mats.append(self.vec.fit_transform(texts))
   else:mats.append(self.vec.transform(texts))
  if self.kind in {'correction','recovery','timing','lexical_recovery'}:
   k='recovery' if self.kind=='lexical_recovery' else self.kind;x=np.array([f[k] for f in fs])
   if fit:self.scaler=StandardScaler();x=self.scaler.fit_transform(x)
   else:x=self.scaler.transform(x)
   mats.append(sparse.csr_matrix(x))
  return sparse.hstack(mats,format='csr')
 def fit(self,fs,y):
  global FIT_COUNT
  self.clf=LinearSVC(C=1,class_weight='balanced',max_iter=10000,random_state=17,dual='auto')
  with warnings.catch_warnings(record=True) as ws:
   self.clf.fit(self.design(fs,True),y)
  FIT_WARNINGS.extend(str(w.message) for w in ws);FIT_COUNT+=1
  return self
 def predict(self,fs):
  sc=self.clf.decision_function(self.design(fs));order=np.argsort(sc,axis=1)
  return self.clf.classes_[order[:,-1]],sc[np.arange(len(sc)),order[:,-1]]-sc[np.arange(len(sc)),order[:,-2]]

def digest(r,seed):return hashlib.sha256((str(seed)+r['id']).encode()).hexdigest()
def partition(rows,seed=17,hold=None):
 cells=collections.defaultdict(list)
 for r in rows:cells[(r['model'],r['prompt'],r['env'],r['budget'])].append(r)
 tr=[];ca=[];te=[]
 for key,rs in sorted(cells.items()):
  rs=sorted(rs,key=lambda r:digest(r,seed))
  if hold and hold(rs[0]):te+=rs;continue
  n=len(rs);nc=max(1,int(n*.2))
  ca+=rs[:nc]
  if hold:tr+=rs[nc:]
  else:nt=max(1,int(n*.2));te+=rs[nc:nc+nt];tr+=rs[nc+nt:]
 before=[len(tr),len(ca),len(te)]
 seen={r['fp'] for r in tr};ca=[r for r in ca if r['fp'] not in seen]
 seen|={r['fp'] for r in ca};te=[r for r in te if r['fp'] not in seen]
 return (tr,ca,te),{'before':before,'after':[len(tr),len(ca),len(te)]}

def metric(y,p):
 return {'n':len(y),'accuracy':float(accuracy_score(y,p)),
 'macro_f1':float(f1_score(y,p,labels=sorted(set(y)),average='macro',zero_division=0)),
 'labels':sorted(set(y)),'confusion':confusion_matrix(y,p,labels=sorted(set(y))).tolist()}

def record(study,setting,kind,rows,p,gap,**extra):
 y=[r['family'] for r in rows];key=f'{study}|{setting}|{kind}'
 out={'key':key,'study':study,'setting':setting,'model':kind,**metric(y,p),**extra}
 RESULTS.append(out)
 PRED.append({'key':key,'id':[r['id'] for r in rows],'y':y,'pred':list(p),'gap':[float(x) for x in gap]})
 return out

def masked(turns,mode):
 out=copy.deepcopy(turns);n=len(out)
 if mode.startswith('middle'):
  k=int(n*int(mode[6:])/100);start=(n-k)//2;out=out[:start]+out[start+k:]
 elif mode=='first50':out=out[n//2:]
 elif mode=='last50':out=out[:n-n//2]
 elif mode.startswith('truncate'):
  for t in out:t['c']=t['c'][:int(mode[8:])]
 elif mode=='verbs':
  for t in out:t['c']=verb(t['c'])
 elif mode=='no_outputs':
  for t in out:t['o']=''
 else:raise ValueError(mode)
 return out

def run(resume=False):
 global RESULTS,PRED,SPLITS,FIT_COUNT
 rows=json.loads((HERE/'cache/records.json').read_text());envs=sorted({r['env'] for r in rows});prompts=sorted({r['prompt'] for r in rows})
 fs=json.loads((HERE/'cache/features.json').read_text()) if (HERE/'cache/features.json').exists() else {r['id']:features(r['turns'][:10]) for r in rows}
 if resume:
  cp=HERE/'cache/s1_checkpoint';RESULTS=json.loads((cp/'RESULTS.json').read_text());PRED=json.loads((cp/'PREDICTIONS.json').read_text());SPLITS=json.loads((cp/'SPLITS.json').read_text())
  assert len(RESULTS)==122 and all(r['study']=='S1' for r in RESULTS)
  FIT_COUNT=105
 specs=[('iid_'+str(s),s,None) for s in [17,29,43]]
 specs += [('env_'+e,17,lambda r,e=e:r['env']==e) for e in envs]
 specs += [('prompt_'+p,17,lambda r,p=p:r['prompt']==p) for p in prompts]
 specs += [('cells_'+str(k),17,lambda r,k=k:(envs.index(r['env'])+prompts.index(r['prompt']))%3==k) for k in range(3)]
 main={};start=time.time()
 for name,seed,hold in specs:
  (tr,ca,te),audit=partition(rows,seed,hold)
  split={'setting':name,**audit,'train':[r['id'] for r in tr],'cal':[r['id'] for r in ca],'test':[r['id'] for r in te]}
  if resume:
   assert next(s for s in SPLITS if s['setting']==name)==split
   if name not in {'iid_17','env_'+envs[0]}:continue
  else:SPLITS.append(split)
  xf=lambda rs:[fs[r['id']] for r in rs]
  y=[r['family'] for r in tr];prior=collections.Counter(y).most_common(1)[0][0]
  if not resume:record('S1',name,'prior',te,[prior]*len(te),[0]*len(te))
  fitted={}
  for kind in (['lexical','structure','lexical_recovery'] if resume else MODELS):
   model=Model(kind).fit(xf(tr),y);p,g=model.predict(xf(te))
   if resume:
    old=next(x for x in PRED if x['key']==f'S1|{name}|{kind}')
    assert list(p)==old['pred'] and np.allclose(g,old['gap'],rtol=0,atol=1e-12)
   else:record('S1',name,kind,te,p,g)
   fitted[kind]=model
  if name.startswith('iid_') and not resume:
   ys=np.random.default_rng(seed).permutation(y);m=Model('lexical').fit(xf(tr),ys)
   p,g=m.predict(xf(te));record('S1',name,'shuffled_lexical',te,p,g)
  if name in {'iid_17','env_'+envs[0]}:main[name]=((tr,ca,te),fitted)
  print('S1',name,'fits',FIT_COUNT,'elapsed',round(time.time()-start),flush=True)
  checkpoint()
 for name,((tr,ca,te),fitted) in main.items():
  for mode in ['middle25','middle50','first50','last50','truncate32','truncate64','verbs','no_outputs']:
   xt=[features(masked(r['turns'][:10],mode)) for r in te]
   xf_mask=[features(masked(r['turns'][:10],mode)) for r in tr] if mode in {'middle50','truncate32','verbs'} else None
   for kind in ['lexical','structure','lexical_recovery']:
    p,g=fitted[kind].predict(xt);record('S2_frozen',name+'/'+mode,kind,te,p,g)
    if mode in {'middle50','truncate32','verbs'}:
     m=Model(kind).fit(xf_mask,[r['family'] for r in tr])
     p,g=m.predict(xt);record('S2_adapted',name+'/'+mode,kind,te,p,g)
  print('S2',name,'fits',FIT_COUNT,flush=True);checkpoint()
  # Unknown evaluation reuses the split; all unknown-family rows excluded from fitting/calibration.
  for unknown in LABELS:
   trk=[r for r in tr if r['family']!=unknown];cak=[r for r in ca if r['family']!=unknown]
   for kind in ['lexical','lexical_recovery']:
    m=Model(kind).fit([fs[r['id']] for r in trk],[r['family'] for r in trk])
    pc,gc=m.predict([fs[r['id']] for r in cak]);p,g=m.predict([fs[r['id']] for r in te])
    y=np.array([r['family'] for r in te]);known=y!=unknown
    for q in [.1,.25]:
     threshold=float(np.quantile(gc,q));keep=g>=threshold
     record('S4',name+'/'+unknown+'/'+str(q),kind,te,p,g,threshold=threshold,
      calibration_n=len(cak),known_n=int(known.sum()),unknown_n=int((~known).sum()),
      known_coverage=float(keep[known].mean()),unknown_acceptance=float(keep[~known].mean()),
      known_accepted_accuracy=float((p[known&keep]==y[known&keep]).mean()) if (known&keep).any() else None)
  print('S4',name,'fits',FIT_COUNT,flush=True);checkpoint()
  for minimum,prefixes in [(10,[3,5,10]),(20,[3,5,10,20])]:
   trs=[r for r in tr if len(r['turns'])>=minimum];cas=[r for r in ca if len(r['turns'])>=minimum];tes=[r for r in te if len(r['turns'])>=minimum]
   prefix_fs={n:([features(r['turns'][:n]) for r in trs],[features(r['turns'][:n]) for r in cas],[features(r['turns'][:n]) for r in tes]) for n in prefixes}
   for kind in ['lexical','lexical_recovery']:
    hist=[];thresholds=[]
    for n in prefixes:
     train_fs,cal_fs,test_fs=prefix_fs[n]
     m=Model(kind).fit(train_fs,[r['family'] for r in trs])
     _,gc=m.predict(cal_fs);p,g=m.predict(test_fs)
     th=float(np.quantile(gc,.1));hist.append((p,g));thresholds.append(th)
     record('S5_prefix',name+'/cohort'+str(minimum)+'/n'+str(n),kind,tes,p,g,threshold=th)
    emit=np.full(len(tes),'',dtype=object);at=np.zeros(len(tes),dtype=int)
    for j in range(1,len(prefixes)):
     p,g=hist[j];pp,gg=hist[j-1]
     take=(emit=='')&(p==pp)&(g>=thresholds[j])&(gg>=thresholds[j-1])
     emit[take]=p[take];at[take]=prefixes[j]
    selected=at>0;y=np.array([r['family'] for r in tes]);last=hist[-1][0]
    RESULTS.append({'key':f'S5_rule|{name}/cohort{minimum}|{kind}','study':'S5_rule','setting':name+'/cohort'+str(minimum),'model':kind,
     'n':len(tes),'emitted_n':int(selected.sum()),'coverage':float(selected.mean()),
     'accepted_accuracy':float((emit[selected]==y[selected]).mean()) if selected.any() else None,
     'wrong_per_all':float(((emit!=y)&selected).mean()),'later_reversals':int(((emit!=last)&selected).sum()),
     'decision_command_counts':dict(collections.Counter(str(x) for x in at)),
     'thresholds':thresholds,'prefixes':prefixes})
    PRED.append({'key':f'S5_rule|{name}/cohort{minimum}|{kind}','id':[r['id'] for r in tes],'y':list(y),'pred':list(emit),'at':at.tolist()})
  print('S5',name,'fits',FIT_COUNT,flush=True);checkpoint()
 # Conditional paired uncertainty for recovery additions, not independent population inference.
 comparisons=[];lookup={p['key']:p for p in PRED}
 for name,_,_ in specs:
  a=lookup[f'S1|{name}|lexical'];b=lookup[f'S1|{name}|lexical_recovery'];y=np.array(a['y'])
  rng=np.random.default_rng(1707);deltas=[]
  groups=[np.flatnonzero(y==v) for v in LABELS]
  aa=np.array(a['pred']);bb=np.array(b['pred'])
  for _ in range(1000):
   ix=np.concatenate([rng.choice(g,len(g),replace=True) for g in groups])
   deltas.append(float(np.mean(bb[ix]==y[ix])-np.mean(aa[ix]==y[ix])))
  comparisons.append({'setting':name,'accuracy_delta':float(np.mean(bb==y)-np.mean(aa==y)),
   'conditional_95_interval':np.quantile(deltas,[.025,.975]).tolist()})
 save(HERE/'evidence/PAIRED_COMPARISONS.json',comparisons)
 save(HERE/'evidence/FEATURES.json',{'correction':CORRECTION_NAMES,'recovery':RECOVERY_NAMES,'timing':TIMING_NAMES})
 save(HERE/'evidence/RUN.json',{'fits':FIT_COUNT,'checkpoint_reconstruction_fits':6 if resume else 0,'result_rows':len(RESULTS),'warnings':FIT_WARNINGS,'elapsed_seconds':time.time()-start,
  'code_hashes':{p.name:sha(p) for p in [HERE/'experiment.py',HERE/'prepare.py',HERE/'PROTOCOL.txt']}})
 checkpoint();print('DONE',FIT_COUNT,len(RESULTS),flush=True)

def checkpoint():
 save(HERE/'evidence/RESULTS.json',RESULTS);save(HERE/'evidence/PREDICTIONS.json',PRED);save(HERE/'evidence/SPLITS.json',SPLITS)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--resume-s1',action='store_true');args=parser.parse_args()
 with threadpool_limits(limits=1):run(args.resume_s1)
