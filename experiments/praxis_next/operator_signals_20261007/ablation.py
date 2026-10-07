"""Post-initial-results feature attribution ablation, kept separate from S1."""
import json,time
from threadpoolctl import threadpool_limits
from experiment import features,Model,partition,metric,FIT_WARNINGS
from prepare import HERE,save,sha

def run():
 rows=json.loads((HERE/'cache/records.json').read_text());envs=sorted({r['env'] for r in rows});prompts=sorted({r['prompt'] for r in rows})
 if (HERE/'cache/features.json').exists():fs=json.loads((HERE/'cache/features.json').read_text())
 else:
  fs={r['id']:features(r['turns'][:10]) for r in rows};save(HERE/'cache/features.json',fs)
 # Release massive shell responses; subsequent models need only descriptors.
 for r in rows:del r['turns']
 print('ablation features ready',flush=True)
 specs=[('iid_'+str(s),s,None) for s in [17,29,43]]
 specs += [('env_'+e,17,lambda r,e=e:r['env']==e) for e in envs]
 specs += [('prompt_'+p,17,lambda r,p=p:r['prompt']==p) for p in prompts]
 specs += [('cells_'+str(k),17,lambda r,k=k:(envs.index(r['env'])+prompts.index(r['prompt']))%3==k) for k in range(3)]
 results=[];pred=[]
 for name,seed,hold in specs:
  (tr,ca,te),audit=partition(rows,seed,hold)
  for kind in ['lexical_correction','lexical_output_recovery','lexical_edit_retry']:
   def xf(rs):
    out=[]
    for r in rs:
     f=fs[r['id']];v=f['correction'] if kind=='lexical_correction' else f['recovery'][8:] if kind=='lexical_output_recovery' else f['correction'][:2]
     out.append({**f,'recovery':v})
    return out
   m=Model('lexical_recovery').fit(xf(tr),[r['family'] for r in tr]);p,g=m.predict(xf(te));y=[r['family'] for r in te]
   key=f'S1A|{name}|{kind}'
   results.append({'key':key,'study':'S1A','setting':name,'model':kind,**metric(y,p)})
   pred.append({'key':key,'id':[r['id'] for r in te],'y':y,'pred':list(p),'gap':g.tolist()})
  save(HERE/'evidence/ABLATION_RESULTS.json',results);save(HERE/'evidence/ABLATION_PREDICTIONS.json',pred)
  print('S1A',name,flush=True)
 save(HERE/'evidence/ABLATION_RUN.json',{'solver':'primal (dual=False)','warnings':FIT_WARNINGS,'fits':len(results),'source_sha256':sha(HERE/'ablation.py'),'protocol_sha256':sha(HERE/'ABLATION_PROTOCOL.txt')})

if __name__=='__main__':
 with threadpool_limits(limits=1):run()
