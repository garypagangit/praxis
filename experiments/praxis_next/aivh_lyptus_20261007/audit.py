"""Independent audit of source integrity and reported held-out outcomes."""
import pathlib,json,hashlib,collections,sys,numpy as np
P=pathlib.Path(__file__).resolve().parent;O=P/'results';raw=pathlib.Path(sys.argv[1]);checks=0
for file in ['human_manifest.json','ai_manifest.json']:
 for f in json.loads((raw/file).read_text()):
  fp=pathlib.Path(f['local']);fp=fp if fp.is_absolute() else raw/fp
  data=fp.read_bytes();assert hashlib.sha256(data).hexdigest()==f['sha256'] and len(data)==f['bytes'];checks+=1
rows=json.loads((O/'PX121_records.json').read_text());lookup={r['id']:r for r in rows};assert len(lookup)==len(rows);checks+=1
result=json.loads((O/'PX121_RESULTS.json').read_text());pred=json.loads((O/'PX121_PREDICTIONS.json').read_text());cal=json.loads((O/'PX121_CALIBRATION.json').read_text())
for fold in result['folds']:
 if fold['status']!='EXPLORATORY_COMPLETE':continue
 parts=[[lookup[i] for i in ids] for ids in fold['ids']]
 for a,b in [(parts[0],parts[1]),(parts[0],parts[2]),(parts[1],parts[2])]:
  for key in ['task','fingerprint']:
   assert not ({r[key] for r in a}&{r[key] for r in b});checks+=1
  assert not ({r['group'] for r in a if not r['label']}&{r['group'] for r in b if not r['label']});checks+=1
 for kind in ['verbs','transitions','counts','combined','shuffled_labels']:
  cc=[r for r in cal if r['fold']==fold['test_expert'] and r['kind']==kind];threshold=np.nextafter(max(r['score'] for r in cc if not r['label']),np.inf)
  pp=[r for r in pred if r['fold']==fold['test_expert'] and r['kind']==kind];assert {r['id'] for r in pp}==set(fold['ids'][2]);checks+=1
  for r in pp:assert r['threshold']==threshold and r['flag']==(r['score']>=threshold);checks+=1
for kind,s in result['summaries'].items():
 pp=[r for r in pred if r['kind']==kind];h=[r for r in pp if not r['label']];a=[r for r in pp if r['label']];assert sum(r['flag'] for r in h)==s['human_false_flags'];assert sum(r['flag'] for r in a)==s['ai_detected'];assert len(h)==s['human_predictions'] and len(a)==s['ai_predictions'];checks+=3
 gs={r['group'] for r in h};gf=np.mean([np.mean([r['flag'] for r in h if r['group']==g]) for g in gs]);assert abs(gf-s['equal_expert_fpr'])<1e-12;checks+=1
 if kind=='agreement':
  index={(r['fold'],r['id'],r['kind']):r for r in pred}
  for r in pp:
   v=index[r['fold'],r['id'],'verbs'];b=index[r['fold'],r['id'],'combined'];ab=v['flag']!=b['flag'] or bool(r['parse_failures']);assert r['abstain']==ab and r['flag']==(v['flag'] and b['flag'] and not ab);checks+=1
# Sensitivity is not declared primary; no overlap means no primary matched estimate.
t=json.loads((O/'TRANSFER_RESULTS.json').read_text());assert t['coverage'][0]['window']==10 and t['coverage'][0]['shared_tasks']==0;checks+=1
(O/'AUDIT.json').write_text(json.dumps({'status':'PASS','checks':checks,'limits':'Numeric/provenance/split audit, not independent certification of terminal reconstruction or source labels.'},indent=2));print('PASS',checks)
