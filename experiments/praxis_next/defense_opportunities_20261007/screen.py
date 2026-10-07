"""Offline follow-up; archived commands are inert data."""
import pathlib,sys,json,gzip,hashlib,copy,time,collections
import numpy as np
from scipy import sparse
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
HERE=pathlib.Path(__file__).resolve().parent
OLD=HERE.parent/'operator_signals_20261007'
sys.path.insert(0,str(OLD))
import experiment as e
from prepare import save,sha
RESULTS=[];PRED=[];SPLITS=[]

class Model(e.Model):
 def design(self,fs,fit=False):
  if self.kind not in {'size_error','output_recovery'}:return super().design(fs,fit)
  from sklearn.feature_extraction.text import TfidfVectorizer
  if fit:self.vec=TfidfVectorizer(ngram_range=(1,2),max_features=8000,sublinear_tf=True,token_pattern=r'(?u)\b\w+\b')
  text=[f['lexical'] for f in fs];a=self.vec.fit_transform(text) if fit else self.vec.transform(text)
  x=np.array([[f['recovery'][i] for i in ([5,6,7,8] if self.kind=='size_error' else list(range(8,14)))] for f in fs])
  if fit:self.scaler=StandardScaler();x=self.scaler.fit_transform(x)
  else:x=self.scaler.transform(x)
  return sparse.hstack([a,sparse.csr_matrix(x)],format='csr')

def threshold(y,p,g):
 # Candidate thresholds use calibration scores only. Empirical error is not a guarantee.
 candidates=np.unique(np.r_[np.quantile(g,np.linspace(0,.99,100)),g.max()+1])
 for t in candidates:
  k=g>=t
  if k.sum()>=max(100,.2*len(y)) and np.mean(p[k]!=np.array(y)[k])<=.02:return float(t)
 return None

def select(g,t):return np.zeros(len(g),bool) if t is None else g>=t
def decision(y,p,k):
 y=np.array(y);return {'n':len(y),'accepted':int(k.sum()),'coverage':float(k.mean()),'errors':int(((p!=y)&k).sum()),'accepted_error':float(np.mean(p[k]!=y[k])) if k.any() else None}
def record(study,setting,model,rs,p,g,**extra):
 y=[r['family'] for r in rs];key='|'.join([study,setting,model]);RESULTS.append({'key':key,'study':study,'setting':setting,'model':model,**e.metric(y,p),**extra})
 PRED.append({'key':key,'id':[r['id'] for r in rs],'y':y,'pred':list(p),'gap':np.asarray(g).tolist()})
def checkpoint():
 save(HERE/'evidence/RESULTS.json',RESULTS);save(HERE/'evidence/SPLITS.json',SPLITS)
 with gzip.open(HERE/'cache/predictions.json.gz','wt',encoding='utf-8') as f:json.dump(PRED,f)
def mutate(r,mode):
 ts=r['turns'][:10]
 if mode=='full':return ts
 if mode=='random30':
  rng=np.random.default_rng(int(r['id'][:8],16)+17);keep=rng.random(len(ts))>=.3
  if not keep.any():keep[0]=True
  return [t for t,k in zip(ts,keep) if k]
 if mode=='shuffle_outputs':
  ts=copy.deepcopy(ts);rng=np.random.default_rng(int(r['id'][:8],16)+29);outputs=[t['o'] for t in ts[:-1]];rng.shuffle(outputs)
  for t,o in zip(ts[:-1],outputs):t['o']=o
  return ts
 return e.masked(ts,mode)

def run():
 started=time.time();rows=json.loads((OLD/'cache/records.json').read_text());full=json.loads((OLD/'cache/features.json').read_text())
 envs=sorted({r['env'] for r in rows});fs={'full':full}
 modes=['full','middle50','first50','last50','truncate32','verbs','no_outputs','random30','shuffle_outputs']
 for mode in modes[1:]:
  fs[mode]={r['id']:e.features(mutate(r,mode)) for r in rows};print('features',mode,flush=True)
 xf=lambda rs,mode='full':[fs[mode][r['id']] for r in rs]
 for env in envs:
  (tr,ca,te),audit=e.partition(rows,hold=lambda r:r['env']==env)
  SPLITS.append({'setting':env,**audit,'train':[r['id'] for r in tr],'cal':[r['id'] for r in ca],'test':[r['id'] for r in te]})
  y=[r['family'] for r in tr];yc=[r['family'] for r in ca]
  for kind in ['lexical','lexical_recovery']:
   base=Model(kind).fit(xf(tr),y)
   for mode in modes[:-1]:
    for fit in (['full'] if mode=='full' else ['frozen','adapted']):
     m=base if fit in {'full','frozen'} else Model(kind).fit(xf(tr,mode),y)
     pc,gc=m.predict(xf(ca,mode));p,g=m.predict(xf(te,mode));t=threshold(yc,pc,gc)
     rec={'threshold':t,'calibration':decision(yc,pc,select(gc,t)),'selective':decision([r['family'] for r in te],p,select(g,t))}
     record('logging',env+'/'+mode+'/'+fit,kind,te,p,g,**rec)
   checkpoint()
  for kind,mode in [('size_error','full'),('output_recovery','full'),('lexical_recovery','shuffle_outputs')]:
   m=Model(kind).fit(xf(tr,mode),y);p,g=m.predict(xf(te,mode));record('recovery_controls',env+'/'+mode,kind,te,p,g)
  print('logging/controls',env,'fits',e.FIT_COUNT,flush=True);checkpoint()
 # Served-version holdout: keep family represented; meta has only one served version.
 for version in sorted({r['model'] for r in rows if r['family']!='meta'}):
  (tr,ca,te),audit=e.partition(rows,hold=lambda r:r['model']==version)
  SPLITS.append({'setting':'version/'+version,**audit,'train':[r['id'] for r in tr],'cal':[r['id'] for r in ca],'test':[r['id'] for r in te]})
  for kind in ['lexical','size_error','lexical_recovery']:
   m=Model(kind).fit(xf(tr),[r['family'] for r in tr]);p,g=m.predict(xf(te));record('version',version,kind,te,p,g)
  print('version',version,flush=True);checkpoint()
 # Free mask caches before prefix study.
 fs={'full':full};prefix={10:full}
 for n in [3,5]:prefix[n]={r['id']:e.features(r['turns'][:n]) for r in rows}
 for env in envs:
  (tr,ca,te),_=e.partition(rows,hold=lambda r:r['env']==env)
  for unknown in e.LABELS:
   trk=[r for r in tr if r['family']!=unknown];cak=[r for r in ca if r['family']!=unknown];hist=[]
   for n in [3,5,10]:
    xx=lambda rs:[prefix[n][r['id']] for r in rs]
    m=Model('lexical').fit(xx(trk),[r['family'] for r in trk]);pc,gc=m.predict(xx(cak));p,g=m.predict(xx(te))
    hist.append((p,g,float(np.quantile(gc,.1)),threshold([r['family'] for r in cak],pc,gc)))
   y=np.array([r['family'] for r in te]);known=y!=unknown
   for policy in ['always10','margin10','target10','agree_margin','agree_target']:
    p,g,q,t=hist[-1];emit=np.full(len(te),'',dtype=object);at=np.zeros(len(te),int)
    if policy in {'always10','margin10','target10'}:
     k=np.ones(len(te),bool) if policy=='always10' else select(g,q if policy=='margin10' else t);emit[k]=p[k];at[k]=10
    else:
     for j,n in [(1,5),(2,10)]:
      pp,gg,qq,tt=hist[j-1];p,g,q,t=hist[j]
      k=(at==0)&(p==pp)&select(g,q if policy=='agree_margin' else t)&select(gg,qq if policy=='agree_margin' else tt)
      emit[k]=p[k];at[k]=n
    keep=at>0;key='unknown/'+env+'/'+unknown+'/'+policy
    RESULTS.append({'key':key,'study':'unknown_early','setting':env,'unknown':unknown,'policy':policy,'known':decision(y[known],emit[known],keep[known]),'unknown_n':int((~known).sum()),'unknown_accepted':int(keep[~known].sum()),'unknown_acceptance':float(keep[~known].mean()),'decision_counts':dict(collections.Counter(str(i) for i in at)),'later_reversals':int(((emit!=hist[-1][0])&keep).sum()),'thresholds':[{'margin':h[2],'target':h[3]} for h in hist]})
    PRED.append({'key':key,'id':[r['id'] for r in te],'y':list(y),'pred':list(emit),'at':at.tolist(),'unknown':unknown})
   print('unknown',env,unknown,'fits',e.FIT_COUNT,flush=True);checkpoint()
 save(HERE/'evidence/RUN.json',{'fits':e.FIT_COUNT,'warnings':e.FIT_WARNINGS,'elapsed_seconds':time.time()-started,'code_sha256':sha(pathlib.Path(__file__)),'protocol_sha256':sha(HERE/'PROTOCOL.txt'),'input_sha256':sha(OLD/'cache/records.json')})
 print('DONE',e.FIT_COUNT,len(RESULTS),flush=True)

if __name__=='__main__':
 (HERE/'cache').mkdir(exist_ok=True)
 with threadpool_limits(limits=1):run()
