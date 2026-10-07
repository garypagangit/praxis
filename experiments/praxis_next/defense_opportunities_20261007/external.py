"""Independent-collector method replication using prior public Lyptus extraction."""
import json,hashlib,collections,pathlib
import numpy as np
from threadpoolctl import threadpool_limits
from screen import HERE,e,Model,save,sha
def run():
 path=HERE.parent/'aivh_lyptus_20261007/results/PX121_records.json';raw=json.loads(path.read_text());rows=[]
 for r in raw:
  if not r['label'] or len(r['shell_commands'])<3:continue
  turns=[{'i':i,'c':c,'o':'','t':[None,None]} for i,c in enumerate(r['shell_commands'][:3])]
  rows.append({**r,'f':e.features(turns),'fp':hashlib.sha256('\n'.join(r['shell_commands'][:3]).encode()).hexdigest(),'fold':int(hashlib.sha256(r['task'].encode()).hexdigest()[:8],16)%5})
 out=[];pred=[];splits=[]
 for fold in range(5):
  tr=[r for r in rows if r['fold']!=fold];seen={r['fp'] for r in tr};te=[r for r in rows if r['fold']==fold and r['fp'] not in seen]
  splits.append({'fold':fold,'train':[r['id'] for r in tr],'test':[r['id'] for r in te],'test_tasks':sorted({r['task'] for r in te})})
  if len(set(r['family'] for r in tr))<3 or not te:continue
  for kind in ['lexical','correction','lexical_recovery']:
   m=Model(kind).fit([r['f'] for r in tr],[r['family'] for r in tr]);p,g=m.predict([r['f'] for r in te]);y=[r['family'] for r in te]
   out.append({'fold':fold,'model':kind,**e.metric(y,p)});pred.append({'fold':fold,'model':kind,'id':[r['id'] for r in te],'y':y,'pred':list(p),'gap':g.tolist()})
 save(HERE/'evidence/EXTERNAL.json',{'scope':'Within-Lyptus task-held-out method replication, not transfer of Honey weights; recovery outputs unavailable in this extraction, combined means command correction only','eligible':dict(collections.Counter(r['family'] for r in rows)),'results':out,'splits':splits,'predictions':pred,'fits':e.FIT_COUNT,'warnings':e.FIT_WARNINGS,'source_sha256':sha(path),'code_sha256':sha(pathlib.Path(__file__))})
 print('external',e.FIT_COUNT,collections.Counter(r['family'] for r in rows),flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=1):run()
