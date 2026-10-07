"""Static edge-loss feasibility, not a chronological attack-chain experiment."""
import argparse,pathlib,json,hashlib,time
import numpy as np
from sklearn.ensemble import IsolationForest
from threadpoolctl import threadpool_limits
from screen import HERE,save,sha

def features(g,keep,nt,nr):
 n=len(g['y']);x=np.zeros((n,nt+2*nr),np.float32);x[np.arange(n),g['node_type']]=1
 for rel in range(nr):
  k=keep&(g['relation']==rel)
  x[:,nt+2*rel]=np.log1p(np.bincount(g['src'][k],minlength=n))
  x[:,nt+2*rel+1]=np.log1p(np.bincount(g['dst'][k],minlength=n))
 return x
def metrics(y,s,t):
 k=s>t;budget=max(1,int(np.ceil(.01*len(y))));order=np.lexsort((np.arange(len(y)),-s));top=order[:budget]
 return {'n':len(y),'positives':int(y.sum()),'alerts':int(k.sum()),'recall':float(k[y==1].mean()),'fpr':float(k[y==0].mean()),'budget':budget,'budget_tp':int(y[top].sum()),'budget_recall':float(y[top].sum()/y.sum()),'budget_precision':float(y[top].mean()),'boundary_ties':int((s==s[top[-1]]).sum())}
def run(root):
 results=[];inventory={};start=time.time()
 for ds in ['cadets','theia']:
  graphs=[]
  for name in ['train0','train1','train2','train3','test0']:
   p=root/ds/(name+'.npz');inventory[ds+'/'+p.name]=sha(p);z=np.load(p);graphs.append({k:z[k] for k in z.files})
  nt=1+max(int(g['node_type'].max()) for g in graphs);nr=1+max(int(g['relation'].max()) for g in graphs)
  # Dimensions follow upstream vocabulary including test metadata; disclose inheritance.
  train=[]
  for i,g in enumerate(graphs[:3]):
   x=features(g,np.ones(len(g['src']),bool),nt,nr);ix=np.random.default_rng(17+i).choice(len(x),min(16666,len(x)),replace=False);train.append(x[ix])
  train=np.concatenate(train);cal=features(graphs[3],np.ones(len(graphs[3]['src']),bool),nt,nr);test=graphs[4];models={}
  for kind in ['node_type','typed_degree']:
   cols=nt if kind=='node_type' else train.shape[1]
   m=IsolationForest(n_estimators=100,max_samples=256,random_state=17,n_jobs=1).fit(train[:,:cols]);sc=-m.score_samples(cal[:,:cols]);t=float(np.quantile(sc,.99));models[kind]=(m,t,cols)
  masks=[('full',np.ones(len(test['src']),bool))]
  for rate in [.1,.3,.5,.7]:
   for seed in [17,29,43]:masks.append((f'random{rate}/seed{seed}',np.random.default_rng(seed).random(len(test['src']))>=rate))
  masks += [(f'drop_relation{rel}',test['relation']!=rel) for rel in sorted(set(test['relation'].tolist()))]
  for name,keep in masks:
   x=features(test,keep,nt,nr)
   for kind,(m,t,cols) in models.items():
    s=-m.score_samples(x[:,:cols]);out={'dataset':ds,'mask':name,'model':kind,'retained_edges':int(keep.sum()),'original_edges':len(keep),'threshold':t,**metrics(test['y'],s,t)};results.append(out)
    # Scores and inherited labels retained locally; compressed score vectors published separately.
    dest=HERE/'cache/graph_predictions';dest.mkdir(exist_ok=True)
    np.savez_compressed(dest/(ds+'_'+name.replace('/','_')+'_'+kind+'.npz'),score=s.astype(np.float32),y=test['y'])
   print('graph',ds,name,flush=True);save(HERE/'evidence/GRAPH_RESULTS.json',results)
 save(HERE/'evidence/GRAPH_RUN.json',{'fits':4,'elapsed_seconds':time.time()-start,'input_sha256':inventory,'upstream_manifest_sha256':sha(root/'MANIFEST.json'),'code_sha256':sha(pathlib.Path(__file__)),'scope':'Static development graph edge-loss; no time or chain labels; no MAGIC reproduction'})
 save(HERE/'evidence/GRAPH_SOURCE_MANIFEST.json',json.loads((root/'MANIFEST.json').read_text()))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=pathlib.Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=1):run(a.data)
