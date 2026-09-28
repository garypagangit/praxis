"""Independent count-based verification of full-release predictions and protocol."""
from pathlib import Path
import json, hashlib, datetime, sys, csv
import numpy as np
ROOT=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/praxis_full_release_20260927')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 r=json.loads((ROOT/'FULL_RELEASE_RESULTS.json').read_text());checks=[];manifest=[];seen=[]
 inv=json.loads(Path('C:/w/apt_benchmark_20260920/experiments/apt_benchmark/host_history_exfil/DATA_INVENTORY.json').read_text());source={x['source_file']:x for x in inv['files']};raw=Path(inv['private_raw_root']);canonical_header=None
 def check(name,ok):
  checks.append({'check':name,'pass':bool(ok)})
  if not ok:raise AssertionError(name)
 for s in r['sensors']:
  name=s['sensor'];p=s['preparation'];d=np.load(PRIVATE/name/'DATA.npz');y=d['y'];sp=d['split'];keys=d['keys']
  check(name+' data hash',sha(PRIVATE/name/'DATA.npz')==p['data_sha256'])
  check(name+' conservation',p['raw_rows']==p['retained_rows']+p['exact_duplicate_rows_removed']+p['conflicting_rows_quarantined'])
  check(name+' split conservation',len(y)==sum(sum(v) for v in p['split_counts'].values())+p['boundary_overlap_rows_excluded'])
  check(name+' unique flow identity',len(np.unique(keys))==len(keys))
  check(name+' chronological separation',d['end'][sp==0].max()<d['start'][sp==1].min() and d['end'][sp==1].max()<d['start'][sp==2].min())
  seen.extend(x['source_file'] for x in p['files'])
  for f in p['files']:
   original=source[f['source_file']];path=raw/f['source_file']
   check(f['source_file']+' source hash and row binding',sha(path)==f['sha256']==original['sha256'] and f['rows']==original['rows'] and f['native_counts']==original['right_anchored_stage_counts'])
   with path.open(encoding='utf-8-sig',newline='') as stream:header=next(csv.reader(stream))
   if canonical_header is None:canonical_header=header[:77]
   check(f['source_file']+' stable feature order',header[:77]==canonical_header)
  for arm in ['current','current_roles']:
   for split,k in [('calibration',1),('test',2)]:
    path=PRIVATE/name/(arm+'_'+split+'.npz');a=np.load(path);truth=a['y'];prob=a['p'];pred=prob.argmax(1);reported=s['arms'][arm][split]
    check(name+arm+split+' population',np.array_equal(truth,y[sp==k]) and np.array_equal(a['keys'],keys[sp==k]))
    check(name+arm+split+' probabilities',np.isfinite(prob).all() and (prob>=0).all() and np.allclose(prob.sum(1),1))
    cm=np.zeros((4,4),dtype=np.int64);np.add.at(cm,(truth,pred),1)
    check(name+arm+split+' confusion',cm.tolist()==reported['confusion'])
    f=[]
    for i,c in enumerate(['Benign','OtherAttackStage','MovementAuthorLabel','ExfiltrationAuthorLabel']):
     support=int(cm[i,:].sum());denom=int(cm[i,:].sum()+cm[:,i].sum());f.append(2*cm[i,i]/denom if denom else 0.)
     check(name+arm+split+c+' support',support==reported['classes'][c]['support'])
     if i and support:check(name+arm+split+c+' warning',abs(1-cm[i,0]/support-reported['classes'][c]['warning_recall'])<1e-12)
    check(name+arm+split+' F1',abs(sum(f)/4-reported['macro_f1'])<1e-12)
    check(name+arm+split+' benign alerts',int(cm[0,1:].sum())==reported['benign_false_alerts'])
    manifest.append({'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size})
   model=PRIVATE/name/(arm+'.joblib');manifest.append({'path':str(model),'sha256':sha(model),'bytes':model.stat().st_size})
  d.close()
 check('173 distinct source files',len(seen)==len(set(seen))==173)
 check('exact source inventory coverage',set(seen)==set(source))
 check('6877157 source records',sum(s['preparation']['raw_rows'] for s in r['sensors'])==6877157)
 check('12 completed fitting jobs',r['model_fits']==12)
 out={'status':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'check_count':len(checks),'prediction_and_model_manifest':manifest,'script_sha256':sha(__file__),'protocol_sha256':sha(ROOT/'FULL_RELEASE_PROTOCOL.json'),'results_sha256':sha(ROOT/'FULL_RELEASE_RESULTS.json'),'scope':'Independent count-based computational audit. No external ground-truth, campaign replication, or institutional approval.'}
 (ROOT/'FULL_RELEASE_AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps({'status':'PASS','checks':len(checks)}))
if __name__=='__main__':main()
