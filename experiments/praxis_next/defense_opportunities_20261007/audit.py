"""Independent arithmetic and isolation checks over saved outputs; no refitting."""
import json,gzip,collections,pathlib,warnings,sys
import numpy as np
from sklearn.metrics import accuracy_score,f1_score
from screen import HERE,OLD,save,sha,e
from graph_screen import metrics
checks=0
def check(v,message):
 global checks
 assert v,message
 checks+=1
def close(a,b,message):check(abs(a-b)<1e-10,message)
def load(n):return json.loads((HERE/'evidence'/n).read_text())
def main():
 run=load('RUN.json');check(run['fits']==179,'fit count');check(not run['warnings'],'fit convergence');check(run['code_sha256']==sha(HERE/'screen.py'),'runner hash')
 manifest=load('GRAPH_SOURCE_MANIFEST.json');expected={g['npz']:g['npz_sha256'] for ds in manifest['datasets'] for g in ds['graphs']}
 for k,v in load('GRAPH_RUN.json')['input_sha256'].items():check(expected[k]==v,'source graph hash')
 published='--published' in sys.argv
 if published:
  pred=[]
  for p in sorted((HERE/'evidence').glob('PREDICTIONS_*.json.gz')):
   with gzip.open(p,'rt',encoding='utf-8') as f:pred.extend(json.load(f))
 else:
  with gzip.open(HERE/'cache/predictions.json.gz','rt',encoding='utf-8') as f:pred=json.load(f)
 pp={x['key']:x for x in pred};rs=load('RESULTS.json');check(len(rs)==289,'result count');check(len(pp)==len(rs),'unique keys')
 index={x['id']:x for x in json.loads((OLD/'evidence/SESSION_INDEX.json').read_text())}
 for s in load('SPLITS.json'):
  parts=[s[k] for k in ['train','cal','test']]
  for i,j in [(0,1),(0,2),(1,2)]:
   check(not set(parts[i])&set(parts[j]),'id overlap');check(not {index[k]['fp'] for k in parts[i]}&{index[k]['fp'] for k in parts[j]},'first10 overlap')
  field='model' if s['setting'].startswith('version/') else 'env';hold=s['setting'].split('/',1)[-1]
  check(all(index[k][field]==hold for k in parts[2]),'held condition');check(all(index[k][field]!=hold for k in parts[0]+parts[1]),'hold leakage')
 for r in rs:
  p=pp[r['key']];y=np.array(p['y']);h=np.array(p['pred']);check(all(index[k]['family']==v for k,v in zip(p['id'],y)),'labels')
  if r['study']=='unknown_early':
   known=y!=r['unknown'];keep=np.array(p['at'])>0
   close(float(keep[~known].mean()),r['unknown_acceptance'],'unknown acceptance');close(float(keep[known].mean()),r['known']['coverage'],'known coverage');check(int(((h!=y)&known&keep).sum())==r['known']['errors'],'known errors')
   check(set(p['at'])<={0,5,10},'early commands');check(not any(x==r['unknown'] for x in h),'unknown predicted class excluded')
  else:
   close(accuracy_score(y,h),r['accuracy'],'accuracy');close(f1_score(y,h,labels=sorted(set(y)),average='macro',zero_division=0),r['macro_f1'],'F1')
   if 'selective' in r:
    k=np.zeros(len(y),bool) if r['threshold'] is None else np.array(p['gap'])>=r['threshold'];check(int(k.sum())==r['selective']['accepted'],'accepted');check(int(((h!=y)&k).sum())==r['selective']['errors'],'errors')
 # Feature observability and gap-boundary fixture.
 ts=[{'i':0,'c':'lss','o':'command not found','t':[1,2]},{'i':1,'c':'ls','o':'ok','t':[3,4]},{'i':2,'c':'pwd','o':'future','t':[5,6]}]
 a=e.features(ts);ts[-1]['o']='permission denied';ts[-1]['t']=[999,9999];check(a==e.features(ts),'future output/timing leakage')
 ts[1]['i']=7;ts[2]['i']=12;check(e.features(ts)['correction'][0]==0 and e.features(ts)['correction'][1]==0,'gap transition')
 for prefix in ['','UNFILTERED_']:
  br=load(prefix+'BINARY_RESULTS.json');bp=load(prefix+'BINARY_PREDICTIONS.json')
  for fold in br['folds']:
   if fold['status']!='complete':continue
   for i,j in [(0,1),(0,2),(1,2)]:
    a,b=fold['parts'][i],fold['parts'][j]
    for key in ['task','fp']:check(not {x[key] for x in a}&{x[key] for x in b},'binary '+key)
    check(not {x['group'] for x in a if not x['label']}&{x['group'] for x in b if not x['label']},'expert overlap')
  for s in br['summary']:
   r=[x for x in bp if x['part']=='test' and x['model']==s['model']];check(sum(x['flag'] for x in r if x['label'])==s['ai_detected'],'binary TP');check(sum(x['flag'] for x in r if not x['label'])==s['human_false_flags'],'binary FP')
 ex=load('EXTERNAL.json');check(not ex['warnings'],'external convergence');source=json.loads((HERE.parent/'aivh_lyptus_20261007/results/PX121_records.json').read_text());lookup={r['id']:r for r in source}
 for s in ex['splits']:check(not {lookup[k]['task'] for k in s['train']}&{lookup[k]['task'] for k in s['test']},'external task overlap')
 for r,p in zip(ex['results'],ex['predictions']):close(accuracy_score(p['y'],p['pred']),r['accuracy'],'external accuracy')
 quant=[];dest=HERE/'evidence/graph_simple_decisions';dest.mkdir(exist_ok=True)
 for r in load('GRAPH_RESULTS.json'):
  name=r['dataset']+'_'+r['mask'].replace('/','_')+'_'+r['model']+'.npz'
  if published:
   z=np.load(dest/name);n=int(z['n']);y=np.unpackbits(z['labels'])[:n];flags=np.unpackbits(z['threshold_flags'])[:n].astype(bool)
   check(int(y[z['top']].sum())==r['budget_tp'],'published graph budget TP');check(int(flags.sum())==r['alerts'],'published graph alerts');close(float(flags[y==1].mean()),r['recall'],'published graph recall');continue
  z=np.load(HERE/'cache/graph_predictions'/name);m=metrics(z['y'],z['score'],r['threshold'])
  diff={k:[r[k],m[k]] for k in ['alerts','budget_tp'] if r[k]!=m[k]}
  if diff:quant.append({'file':name,'float32_difference':diff})
  check(m['budget']==r['budget'],'graph budget');check(m['positives']==r['positives'],'graph labels')
  top=np.lexsort((np.arange(len(z['y'])),-z['score']))[:r['budget']];k=z['score']>r['threshold']
  np.savez_compressed(dest/name,top=top.astype(np.int32),threshold_flags=np.packbits(k),labels=np.packbits(z['y'].astype(bool)),n=np.array(len(z['y'])))
 for r in load('GRAPH_EXISTING.json')['results']:
  name=f"{r['dataset']}_{r['seed']}_{r['view']}_{r['model']}.npz";z=np.load(HERE/'evidence/graph_existing_decisions'/name);n=int(z['n']);y=np.unpackbits(z['labels'])[:n];k=np.unpackbits(z['threshold_flags'])[:n].astype(bool);tie=np.unpackbits(z['tie'])[:n].astype(bool);above=np.unpackbits(z['above'])[:n].astype(bool)
  check(int(y[z['top']].sum())==r['budget_tp'],'existing budget TP');check(int(k.sum())==r['threshold_alerts'],'existing alerts');close(float(k[y==1].mean()),r['threshold_recall'],'existing recall');check(int(tie.sum())==r['boundary_ties'],'tie count');close(float((y[above].sum()+r['boundary_needed']*y[tie].mean())/y.sum()),r['tie_expected_budget_recall'],'tie expectation')
 save(HERE/'evidence'/('VALIDATION_PUBLISHED.json' if published else 'VALIDATION.json'),{'status':'PASS','checks_passed':checks,'simple_graph_score_storage_quantization_differences':quant,'scope':'Developer saved-arithmetic, split, feature observability and provenance audit; not independent labels/reconstruction validation. Single-family version tests use accuracy in reports; their raw F1 uses only the present family. Graph score storage is float32 and any rank changes are listed.'})
 print('PASS',checks,'quantization differences',len(quant))
if __name__=='__main__':main()
