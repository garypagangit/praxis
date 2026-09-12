"""Validation-only SOCKET empathy utility gate. No execution unless --execute."""
import argparse, hashlib, importlib.util, json, math, os, random, time
from collections import Counter
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def data(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def freeze(path,x):
 path.parent.mkdir(parents=True,exist_ok=True);raw=data(x)
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('Frozen artifact differs: '+str(path))
 else:
  with path.open('xb') as f:f.write(raw)
def boundary(context_ids,full):
 if len(context_ids)<=1 or full[:len(context_ids)]!=context_ids or len(full)<=len(context_ids):
  raise ValueError('Assistant/candidate token boundary requires audit; no automatic repair')
 n=len(full)-len(context_ids)
 return full[:-1],full[-n:],n

def token_log_likelihood(logits,targets):
 import torch
 if logits.ndim!=2 or logits.shape[0]!=len(targets) or not torch.isfinite(logits).all():raise ValueError('Invalid candidate logits')
 ids=torch.tensor(targets,dtype=torch.long,device=logits.device)
 values=logits.float().log_softmax(-1).gather(-1,ids[:,None]).squeeze(-1)
 if not torch.isfinite(values).all():raise ValueError('Nonfinite target likelihood')
 return values

def score_candidate(model,tokenizer,messages,candidate,ablation):
 import torch
 rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
 context_ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True)
 if context_ids!=tokenizer.encode(rendered,add_special_tokens=False):raise ValueError('Rendered and direct chat tokenization differ')
 full=tokenizer.encode(rendered+candidate,add_special_tokens=False)
 inputs,targets,n=boundary(context_ids,full)
 if len(full)>model.config.max_position_embeddings:raise ValueError('No input truncation permitted')
 ids=torch.tensor([inputs],dtype=torch.long)
 with torch.inference_mode():
  result=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,experts_ablate=ablation,logits_to_keep=n,return_dict=True)
  values=token_log_likelihood(result.logits[0],targets)
  routes=[0,0,0,0]
  if len(result.routing_weights)!=30:raise ValueError('Expected 30 router blocks')
  for raw in result.routing_weights:
   selected=torch.topk(raw.float().softmax(-1),1,dim=-1).indices.squeeze(-1)
   for expert in range(4):routes[expert]+=int(selected.eq(expert).sum())
  if sum(routes)!=30*len(inputs):raise ValueError('Full-sequence route count differs')
  if ablation and routes[1]:raise ValueError('Social expert remains selected')
 return {'log_likelihood':float(values.double().sum()),'token_log_likelihoods':values.tolist(),
         'continuation_tokens':n,'token_ids':targets,'context_tokens':len(context_ids),'input_tokens':len(inputs),
         'context_text_sha256':sha(rendered.encode()),'context_token_ids_sha256':sha(data(context_ids)),
         'routing_selection_counts':routes,'candidate_text':candidate}

def metrics(pairs):
 n=len(pairs);baseline=sum(p['baseline']['correct'] for p in pairs);ablation=sum(p['social_ablation']['correct'] for p in pairs)
 cw=sum(p['baseline']['correct'] and not p['social_ablation']['correct'] for p in pairs)
 wc=sum(not p['baseline']['correct'] and p['social_ablation']['correct'] for p in pairs)
 delta=[int(p['baseline']['correct'])-int(p['social_ablation']['correct']) for p in pairs]
 rng=random.Random(20260912);boot=sorted(sum(delta[rng.randrange(n)] for _ in range(n))/n for _ in range(2000))
 perlabel={}
 for label in ('not empathy','empathy'):
  selected=[p for p in pairs if p['baseline']['gold']==label]
  perlabel[label]={'n':len(selected),'baseline_correct':sum(p['baseline']['correct'] for p in selected),
                   'ablation_correct':sum(p['social_ablation']['correct'] for p in selected)}
 qualified=baseline>=39 and baseline-ablation>=2 and cw>=2
 return {'n':n,'baseline_correct':baseline,'ablation_correct':ablation,'baseline_accuracy':baseline/n,
         'ablation_accuracy':ablation/n,'majority_accuracy':.5,'baseline_minus_ablation_correct':baseline-ablation,
         'correct_to_wrong_on_ablation':cw,'wrong_to_correct_on_ablation':wc,'per_label':perlabel,
         'paired_question_bootstrap_difference_95pct':[boot[49],boot[1950]],'bootstrap_replicates':2000,
         'qualification_gate':qualified,'zero_harm_null':cw==0,
         'decision':'eligible for separately preregistered preservation study' if qualified else 'retain negative/null qualification; do not promote empathy to primary preservation task',
         'novel_method_established':False,'paper_score_reproduction_claimed':False}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('data','arc-runner','qualification','previous-out','out'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--execute',action='store_true');a=p.parse_args()
 fixture=read(a.data/'fixture.json');prompt=read(a.data/'prompt.json');lock=read(a.data/'data_lock.json')
 if sha((a.data/'fixture.json').read_bytes())!=lock['fixture_sha256'] or sha((a.data/'prompt.json').read_bytes())!=lock['prompt_sha256']:raise ValueError('Data/prompt lock differs')
 rows=fixture['items']
 if fixture['split']!='validation' or len(rows)!=64 or [r['id'] for r in rows]!=lock['selected_ids']:raise ValueError('Qualification cohort differs')
 if Counter(r['gold'] for r in rows)!=Counter({'not empathy':32,'empathy':32}):raise ValueError('Balanced cohort required')
 candidates=prompt['candidates']
 if candidates!=[{'label':'not empathy','text':'The answer is No.'},{'label':'empathy','text':'The answer is Yes.'}]:raise ValueError('Locked candidates differ')
 prereg=Path(os.environ['PRAXIS_PREREG_PATH']);prereg_sha=sha(prereg.read_bytes())
 if prereg_sha!=os.environ['PRAXIS_PREREG_SHA256']:raise ValueError('Preregistration differs')
 manifest={'protocol':'006-empathy-validation-v1','prereg_sha256':prereg_sha,'data_lock':lock,
           'script_sha256':sha(Path(__file__).read_bytes()),'arc_runner_sha256':sha(a.arc_runner.read_bytes()),
           'source_receipts_sha256':sha((a.qualification/'source_receipts.json').read_bytes()),
           'checkpoint_settings':read(a.qualification/'settings.json'),'dependencies':read(a.qualification/'loader_dependencies.json'),
           'qualified_source_sha256':sha((a.previous_out/'source_repos/models/micro_llama.py').read_bytes()),
           'conditions':['baseline','social_ablation'],'measurement':'three published chat demonstrations; full answer-string likelihood without chat-end tokens',
           'qualification_thresholds':{'baseline_correct_min':39,'net_advantage_min':2,'ablation_harms_min':2},
           'max_candidate_forwards':300,'wall_seconds_after_loading':7200,'planned_cell_forwards':256,'sanity_forwards':3,
           'task_adaptation':True,'paper_score_reproduction_claimed':False,'novel_method_tested':False}
 freeze(a.out/'manifest.json',manifest);digest=sha(data(manifest))
 if not a.execute:print(json.dumps({'status':'VALIDATED_NO_MODEL_LOAD','n':64,'manifest_sha256':digest}));return
 if (a.out/'summary.json').exists():
  prior=read(a.out/'summary.json')
  if prior['manifest_sha256']!=digest:raise ValueError('Completed manifest differs')
  print(json.dumps(prior));return
 spec=importlib.util.spec_from_file_location('qualified_arc',a.arc_runner);arc=importlib.util.module_from_spec(spec);spec.loader.exec_module(arc)
 model,tokenizer,environment=arc.load_qualified_model(a.qualification,a.previous_out)
 if any(p.device.type!='cpu' for p in model.parameters()):raise ValueError('CPU execution only')
 environment.update(device='cpu',chat_template_sha256=sha(tokenizer.chat_template.encode()))
 freeze(a.out/'environment.json',environment)
 started=time.monotonic();counter=0
 def messages(text):return prompt['fewshot_messages']+[{'role':'user','content':prompt['question_template'].replace('{text}',text)}]
 def score(text,candidate,ablation):
  nonlocal counter
  counter+=1
  if counter>300 or time.monotonic()-started>7200:raise RuntimeError('Bound exceeded; preserve partial cells')
  return score_candidate(model,tokenizer,messages(text),candidate,ablation)
 first=rows[0];candidate=candidates[0]['text']
 first_clean=score(first['text'],candidate,[]);first_ablation=score(first['text'],candidate,['social']);reset=score(first['text'],candidate,[])
 sanity={'baseline_ablation_baseline_reset_abs_delta':abs(first_clean['log_likelihood']-reset['log_likelihood']),
         'ablated_social_routes':first_ablation['routing_selection_counts'][1],
         'first_context_tokens':first_clean['context_tokens'],'first_candidate_tokens':first_clean['continuation_tokens']}
 freeze(a.out/'sanity.json',sanity)
 if sanity['baseline_ablation_baseline_reset_abs_delta']>1e-6 or sanity['ablated_social_routes']!=0:raise ValueError('Ablation/reset sanity failed')
 results=[]
 for index,row in enumerate(rows):
  for condition,ablation in (('baseline',[]),('social_ablation',['social'])):
   identity=[digest,row['id'],condition];path=a.out/'cells'/(sha(data(identity))+'.json')
   if path.exists():
    prior=read(path)
    if prior['identity']!=identity:raise ValueError('Cached cell identity differs')
    results.append(prior);continue
   scores=[score(row['text'],candidate['text'],ablation) for candidate in candidates]
   if scores[0]['context_token_ids_sha256']!=scores[1]['context_token_ids_sha256']:raise ValueError('Candidate contexts differ')
   ll=[s['log_likelihood'] for s in scores];winner=max(range(2),key=ll.__getitem__);prediction=candidates[winner]['label']
   record={'identity':identity,'manifest_sha256':digest,'id':row['id'],'index':index,'split':'validation',
           'condition':condition,'scores':scores,'prediction':prediction,'gold':row['gold'],'correct':prediction==row['gold']}
   freeze(path,record);results.append(record)
   print(json.dumps({'completed_cells':len(results),'planned_cells':128,'candidate_forwards':counter}),flush=True)
 pairs=[{c:next(r for r in results if r['id']==row['id'] and r['condition']==c) for c in ('baseline','social_ablation')} for row in rows]
 summary=metrics(pairs);summary.update(manifest_sha256=digest,status='COMPLETED_VALIDATION_QUALIFICATION',
            candidate_forwards_this_execution=counter,elapsed_seconds=time.monotonic()-started,completed_cells=len(results),
            interpretation='Agreement with released SOCKET labels of self-reported empathic concern; not objective feeling detection or human-like cognition')
 freeze(a.out/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
