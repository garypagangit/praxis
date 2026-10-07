"""Recompute saved results and check provenance, isolation and feature invariants."""
import collections, gzip, hashlib, json, math
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from experiment import features,masked,nearby
from prepare import HERE,save,sha

checks=0
def read(path):
 if path.exists():return json.loads(path.read_text())
 with gzip.open(str(path)+'.gz','rt',encoding='utf-8') as f:return json.load(f)
def check(x,message):
 global checks
 assert x,message
 checks+=1

def main():
 # Semantic invariants: no future feedback, no invented adjacency across gaps.
 t=[{'i':0,'c':'grpe foo','o':'command not found','t':[10.,20.]},
    {'i':1,'c':'grep foo','o':'last output','t':[30.,40.]}]
 f=features(t);t[1]['o']='permission denied';t[1]['t']=[99999.,999999.]
 check(f==features(t),'last-command output/timing leaked into an early decision')
 check(nearby('grpe','grep'),'transposition correction proxy absent')
 check(not nearby('cat','cat'),'exact retry confused with edit')
 t[1]['i']=3
 check(features(t)['recovery'][8]==0,'recovery transition bridged missing observations')
 t3=[{'i':i,'c':'ls','o':'permission denied','t':[1.,2.]} for i in range(10)]
 check([t['i'] for t in masked(t3,'middle50')]==[0,1,7,8,9],'wrong contiguous corruption')
 rows=json.loads((HERE/'cache/records.json').read_text());rr={r['id']:r for r in rows}
 save(HERE/'evidence/SESSION_INDEX.json',[{k:v for k,v in r.items() if k!='turns'} for r in rows])
 # Descriptive measurement audit, never a replacement operator label.
 feature_cache=json.loads((HERE/'cache/features.json').read_text())
 for i in np.linspace(0,len(rows)-1,32,dtype=int):
  check(feature_cache[rows[i]['id']]==features(rows[i]['turns'][:10]),'cached features changed')
 diagnostics=[]
 for family in sorted({r['family'] for r in rows}):
  rs=[r for r in rows if r['family']==family];ff=[feature_cache[r['id']] for r in rs]
  between=[r['turns'][i]['t'][0]-r['turns'][i-1]['t'][1] for r in rs for i in range(1,10)]
  within=[t['t'][1]-t['t'][0] for r in rs for t in r['turns'][:10]]
  diagnostics.append({'family':family,'n':len(rs),
    'sessions_with_near_verb_edit_proxy':sum(f['correction'][1]>0 for f in ff),
    'sessions_with_error_followup':sum(f['recovery'][8]>0 for f in ff),
    'sessions_with_exact_retry':sum(f['correction'][0]>0 for f in ff),
    'fraction_next_first_clock_after_prior_second':float(np.mean(np.array(between)>=0)),
    'clock_difference_within_turn_median':float(np.median(within)),
    'clock_difference_between_turns_median':float(np.median(between))})
 prior=json.loads((HERE.parent/'aivh_lyptus_20261007/results/PX121_records.json').read_text())
 hh=[r for r in prior if not r['label'] and len(r['shell_commands'])>=3]
 save(HERE/'evidence/MEASUREMENT_DIAGNOSTICS.json',{'honey':diagnostics,
  'binary_human_eligible_before_task_matching':len(hh),
  'binary_humans_with_excluded_prompt_lines':sum(r['unreconstructed_prompt_lines']>0 for r in hh),
  'binary_human_excluded_prompt_lines':sum(r['unreconstructed_prompt_lines'] for r in hh),
  'note':'Clock differences are descriptive, not independently verified latency components. Most human sequences omit prompt lines, so adjacency and typo prevalence are not validated.'})
 splits=json.loads((HERE/'evidence/SPLITS.json').read_text())
 for s in splits:
  for x,y in [('train','cal'),('train','test'),('cal','test')]:
   check(not(set(s[x])&set(s[y])),s['setting']+' ID overlap')
   check(not({rr[i]['fp'] for i in s[x]}&{rr[i]['fp'] for i in s[y]}),s['setting']+' exact fingerprint overlap')
  name=s['setting']
  for k in ['train','cal','test']:check(len(s[k])==s['after'][['train','cal','test'].index(k)],'split count')
  if name.startswith('env_'):
   e=name[4:];check(all(rr[i]['env']==e for i in s['test']),'test environment')
   check(all(rr[i]['env']!=e for i in s['train']+s['cal']),'environment leakage')
  if name.startswith('prompt_'):
   p=name[7:];check(all(rr[i]['prompt']==p for i in s['test']),'test prompt')
   check(all(rr[i]['prompt']!=p for i in s['train']+s['cal']),'prompt leakage')
  if name.startswith('cells_'):
   envs=sorted({r['env'] for r in rows});ps=sorted({r['prompt'] for r in rows});k=int(name[6:])
   match=lambda i:(envs.index(rr[i]['env'])+ps.index(rr[i]['prompt']))%3==k
   check(all(match(i) for i in s['test']),'cell test');check(not any(match(i) for i in s['train']+s['cal']),'cell leakage')
 results=json.loads((HERE/'evidence/RESULTS.json').read_text());pred=read(HERE/'evidence/PREDICTIONS.json');pp={r['key']:r for r in pred}
 cp=HERE/'cache/latest_checkpoint'
 if cp.exists() and not json.loads((HERE/'evidence/RUN.json').read_text()).get('warning_capture_complete',False):
  current={r['key']:r for r in results}
  for old in json.loads((cp/'RESULTS.json').read_text()):check(current[old['key']]==old,'completed result changed during resume')
  for old in json.loads((cp/'PREDICTIONS.json').read_text()):check(pp[old['key']]==old,'completed predictions changed during resume')
 check(len(pp)==len(pred),'duplicate prediction keys')
 for r in results:
  p=pp[r['key']];y=np.array(p['y']);pr=np.array(p['pred']);check(len(y)==r['n'],'prediction count')
  check(all(rr[i]['family']==yy for i,yy in zip(p['id'],y)),'saved label provenance')
  if r['study']=='S5_rule':
   at=np.array(p['at']);sel=at>0
   check(int(sel.sum())==r['emitted_n'],'emission count')
   check(abs(float(((pr!=y)&sel).mean())-r['wrong_per_all'])<1e-12,'wrong decision burden')
  else:
   check(abs(accuracy_score(y,pr)-r['accuracy'])<1e-12,'accuracy')
   check(abs(f1_score(y,pr,labels=sorted(set(y)),average='macro',zero_division=0)-r['macro_f1'])<1e-12,'macro F1')
  if r['study']=='S4':
   unknown=r['setting'].split('/')[1];known=y!=unknown;keep=np.array(p['gap'])>=r['threshold']
   check(not any(pr==unknown),'unknown model trained as known')
   check(abs(keep[known].mean()-r['known_coverage'])<1e-12,'known coverage')
   check(abs(keep[~known].mean()-r['unknown_acceptance'])<1e-12,'unknown acceptance')
 # Post-S2 descriptive check: do reductions create identical train/test observations?
 reduced=[]
 for s in splits:
  if s['setting'] not in {'iid_17','env_backend_pool_cowrie'}:continue
  for mode in ['middle25','middle50','first50','last50','truncate32','truncate64','verbs','no_outputs']:
   def sig(i):
    return hashlib.sha256('\n'.join(t['c'] for t in masked(rr[i]['turns'][:10],mode)).encode()).hexdigest()
   seen={sig(i) for i in s['train']+s['cal']};unseen=np.array([sig(i) not in seen for i in s['test']])
   for study in ['S2_frozen','S2_adapted']:
    key=f"{study}|{s['setting']}/{mode}|lexical"
    if key not in pp:continue
    p=pp[key];check(p['id']==s['test'],'reduced-log cohort order')
    y=np.array(p['y']);preds=np.array(p['pred'])
    reduced.append({'study':study,'setting':s['setting'],'mask':mode,'test_n':len(y),
     'matching_reduced_training_or_calibration':int((~unseen).sum()),'unseen_reduced_test_n':int(unseen.sum()),
     'unseen_reduced_accuracy':float(accuracy_score(y[unseen],preds[unseen])) if unseen.any() else None,
     'unseen_reduced_macro_f1':float(f1_score(y[unseen],preds[unseen],labels=sorted(set(y)),average='macro',zero_division=0)) if unseen.any() else None})
 save(HERE/'evidence/REDUCED_OBSERVATION_AUDIT.json',{'status':'Post-initial-S2 descriptive sensitivity; no refitting or replacement of primary scores.',
  'scope':'Exact reduced command-string identity, lexical models only; not all TF-IDF feature collisions or near duplicates. Filtering changes test cohort.', 'results':reduced})
 binary=json.loads((HERE/'evidence/BINARY_RESULTS.json').read_text());bp=json.loads((HERE/'evidence/BINARY_PREDICTIONS.json').read_text())
 for fold in binary['folds']:
  if fold['status']!='complete':continue
  for a,b in [(0,1),(0,2),(1,2)]:
   x,y=fold['parts'][a],fold['parts'][b]
   for key in ['id','task','fp']:check(not({r[key] for r in x}&{r[key] for r in y}),'binary '+key+' leakage')
   check(not({r['group'] for r in x if not r['label']}&{r['group'] for r in y if not r['label']}),'binary expert leakage')
 for r in bp:
  check(r['flag']==(r['score']>=r['threshold']),'binary threshold application')
  if r['part']=='cal' and not r['label']:check(not r['flag'],'calibration-human false flag')
 for r in binary['summary']:
  rs=[p for p in bp if p['model']==r['model'] and p['part']=='test'];hs=[p for p in rs if not p['label']];ais=[p for p in rs if p['label']]
  check(sum(p['flag'] for p in hs)==r['human_false_flags'],'human FP arithmetic')
  check(sum(p['flag'] for p in ais)==r['ai_detected'],'AI detection arithmetic')
  check(len(hs)==r['human_n'] and len(ais)==r['ai_n'],'binary denominator')
 run=json.loads((HERE/'evidence/RUN.json').read_text())
 check(run['warning_capture_complete'] and not run['warnings'],'complete primary fit convergence')
 for name,h in run['code_hashes'].items():check(sha(HERE/name)==h,'run source hash changed')
 ab=json.loads((HERE/'evidence/ABLATION_RESULTS.json').read_text());ap={x['key']:x for x in read(HERE/'evidence/ABLATION_PREDICTIONS.json')}
 for r in ab:
  p=ap[r['key']];check(abs(accuracy_score(p['y'],p['pred'])-r['accuracy'])<1e-12,'ablation accuracy')
  check(abs(f1_score(p['y'],p['pred'],average='macro')-r['macro_f1'])<1e-12,'ablation F1')
  orig=pp['S1|'+r['setting']+'|lexical'];check(p['id']==orig['id'] and p['y']==orig['y'],'ablation cohort differs')
 abrun=json.loads((HERE/'evidence/ABLATION_RUN.json').read_text())
 check(not abrun['warnings'],'ablation convergence')
 check(abrun['source_sha256']==sha(HERE/'ablation.py'),'ablation code hash')
 check(abrun['protocol_sha256']==sha(HERE/'ABLATION_PROTOCOL.txt'),'ablation protocol hash')
 save(HERE/'evidence/VALIDATION.json',{'checks_passed':checks,'status':'PASS',
  'scope':'Developer arithmetic, isolation, provenance and feature-invariant audit. Not independent validation of operator labels or terminal extraction.'})
 print('PASS',checks)

if __name__=='__main__':main()
