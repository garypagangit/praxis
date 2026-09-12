"""Independent receipt-only empathy audit. No network, tokenizer, or model execution."""
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--outputs',type=Path,default=BASE/'outputs',help='Directory containing manifest, summary, sanity, environment and cells')
parser.add_argument('--data',type=Path,default=BASE/'data',help='Directory containing frozen fixture, prompt and data lock')
parser.add_argument('--out',type=Path,default=BASE/'audit',help='Directory for audit.json and RESULTS.md')
args=parser.parse_args()
INPUT=args.outputs
DATA=args.data
OUT=args.out
OUT.mkdir(parents=True,exist_ok=True)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def data(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
errors=[]
def check(test,note):
 if not test:errors.append(note)
fixture=read(DATA/'fixture.json');lock=read(DATA/'data_lock.json');prompt=read(DATA/'prompt.json')
manifest=read(INPUT/'manifest.json');summary=read(INPUT/'summary.json');sanity=read(INPUT/'sanity.json');environment=read(INPUT/'environment.json')
digest=sha(data(manifest));rows=fixture['items'];rowmap={r['id']:(i,r) for i,r in enumerate(rows)}
check(len(rows)==64 and len(rowmap)==64,'64 unique frozen rows')
check(fixture['split']=='validation','Validation-only fixture')
check(Counter(r['gold'] for r in rows)==Counter({'empathy':32,'not empathy':32}),'Balanced labels')
check(sha((DATA/'fixture.json').read_bytes())==lock['fixture_sha256'],'Fixture hash')
check(sha((DATA/'prompt.json').read_bytes())==lock['prompt_sha256'],'Prompt hash')
check(manifest['data_lock']==lock,'Manifest data lock')
check(sha((INPUT/'manifest.json').read_bytes())==digest,'Canonical manifest bytes')
check(summary['manifest_sha256']==digest,'Summary manifest')
check(environment['model']==manifest['checkpoint_settings'],'Environment checkpoint')
check(environment['device']=='cpu' and environment['dtype']=='float32' and environment['threads']==4,'CPU FP32 four-thread environment')
check(all(environment['loading'][k]==[] for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']),'Strict checkpoint load')
check(sanity['ablated_social_routes']==0,'Sanity ablation exclusion')
check(0<=sanity['baseline_ablation_baseline_reset_abs_delta']<=1e-6,'Sanity ablation reset')
files=sorted((INPUT/'cells').glob('*.json'));check(len(files)==128,'128 cell files')
records={};token_refs={};max_sum_error=0.;routes={c:[0,0,0,0] for c in ['baseline','social_ablation']}
for path in files:
 r=read(path);condition=r['condition'];key=(r['id'],condition)
 check(key not in records,'Duplicate cell '+str(key));records[key]=r
 index,row=rowmap[r['id']]
 check(r['identity']==[digest,r['id'],condition] and r['manifest_sha256']==digest,'Cell manifest/identity '+path.name)
 check(path.stem==sha(data(r['identity'])),'Cell filename hash '+path.name)
 check(condition in routes,'Known condition')
 check(r['index']==index and r['split']=='validation' and r['gold']==row['gold'],'Cell cohort/gold '+path.name)
 check(len(r['scores'])==2,'Both class candidates '+path.name)
 contexts=[]
 for j,s in enumerate(r['scores']):
  check(s['candidate_text']==prompt['candidates'][j]['text'],'Class string '+path.name)
  values=s['token_log_likelihoods'];ids=s['token_ids'];n=s['continuation_tokens']
  check(n==len(values)==len(ids) and n>0,'Target token count '+path.name)
  check(all(math.isfinite(v) and v<=1e-6 for v in values),'Finite log probabilities '+path.name)
  error=abs(sum(values)-s['log_likelihood']);max_sum_error=max(error,max_sum_error)
  check(error<=1e-10,'Candidate sum '+path.name)
  check(s['input_tokens']==s['context_tokens']+n-1,'Shifted candidate boundary '+path.name)
  check(s['context_tokens']>1,'Full-sequence context '+path.name)
  check(len(s['routing_selection_counts'])==4 and all(type(v)is int and v>=0 for v in s['routing_selection_counts']),'Route vector '+path.name)
  check(sum(s['routing_selection_counts'])==30*s['input_tokens'],'30-block route totals '+path.name)
  if condition=='social_ablation':check(s['routing_selection_counts'][1]==0,'Ablated social selection '+path.name)
  for e in range(4):routes[condition][e]+=s['routing_selection_counts'][e]
  contexts.append((s['context_text_sha256'],s['context_token_ids_sha256'],s['context_tokens']))
  if j in token_refs:check(ids==token_refs[j],'Candidate IDs invariant across examples/conditions')
  else:token_refs[j]=ids
 check(contexts[0]==contexts[1],'Same context across candidates '+path.name)
 # The two literals share their first three tokens; their prefix likelihoods must also match.
 check(r['scores'][0]['token_ids'][:3]==r['scores'][1]['token_ids'][:3],'Class strings share expected token prefix')
 check(all(abs(x-y)<=1e-6 for x,y in zip(r['scores'][0]['token_log_likelihoods'][:3],r['scores'][1]['token_log_likelihoods'][:3])),'Shared prefix likelihoods '+path.name)
 winner=max(range(2),key=lambda j:r['scores'][j]['log_likelihood']);prediction=prompt['candidates'][winner]['label']
 check(r['prediction']==prediction and r['correct']==(prediction==row['gold']),'Recomputed winner/correctness '+path.name)
check(set(records)=={(r['id'],c) for r in rows for c in routes},'Exact 64x2 panel')
pairs=[(records[(r['id'],'baseline')],records[(r['id'],'social_ablation')]) for r in rows]
for b,a in pairs:
 for bs,as_ in zip(b['scores'],a['scores']):
  check(all(bs[k]==as_[k] for k in ['context_text_sha256','context_token_ids_sha256','context_tokens','input_tokens','token_ids','continuation_tokens']),'Same context and candidate tokens between conditions '+b['id'])
baseline=sum(b['correct'] for b,a in pairs);ablation=sum(a['correct'] for b,a in pairs)
cw=sum(b['correct'] and not a['correct'] for b,a in pairs);wc=sum(not b['correct'] and a['correct'] for b,a in pairs)
changes=sum(b['prediction']!=a['prediction'] for b,a in pairs)
gate=baseline>=39 and baseline-ablation>=2 and cw>=2
expected={'n':64,'completed_cells':128,'baseline_correct':baseline,'ablation_correct':ablation,
 'baseline_accuracy':baseline/64,'ablation_accuracy':ablation/64,'baseline_minus_ablation_correct':baseline-ablation,
 'correct_to_wrong_on_ablation':cw,'wrong_to_correct_on_ablation':wc,'qualification_gate':gate,'zero_harm_null':cw==0}
for k,v in expected.items():check(summary[k]==v,'Summary '+k)
check(summary['candidate_forwards_this_execution']==259,'Fresh forward count')
predictions={c:dict(Counter(r['prediction'] for r in records.values() if r['condition']==c)) for c in routes}
deltas=[abs(bs['log_likelihood']-as_['log_likelihood']) for b,a in pairs for bs,as_ in zip(b['scores'],a['scores'])]
changed_questions=sum(any(abs(bs['log_likelihood']-as_['log_likelihood'])>1e-6 for bs,as_ in zip(b['scores'],a['scores'])) for b,a in pairs)
result={'integrity_status':'PASS' if not errors else 'FAIL','errors':errors,'manifest_sha256':digest,
 'fixture_sha256':lock['fixture_sha256'],'prompt_sha256':lock['prompt_sha256'],'recomputed_summary':expected,
 'prediction_counts':predictions,'prediction_changes':changes,'routing_totals':routes,
 'max_candidate_sum_abs_error':max_sum_error,'max_ablation_candidate_likelihood_abs_delta':max(deltas),
 'questions_with_score_change_gt_1e_6':changed_questions,'class_candidate_token_ids':token_refs,
 'sanity':sanity,'environment':environment,'elapsed_seconds':summary['elapsed_seconds'],
 'limitations':['Receipt audit does not rerun tokenization/model likelihoods; checks stored token sums and exact prefix/shift invariants.',
 'All fixture/cell splits are validation; this audit and its acquisition script do not access held-out test files.',
 'Dataset concerns self-reported empathic concern, with a released binary proxy. No objective mental-state claim.',
 'Failure applies to this checkpoint, fixed prompt and scored-class protocol, not every larger model or brain-inspired approach.']}
(OUT/'audit.json').write_bytes(data(result))
lines=['# Empathy qualification result','',f"Independent artifact audit: **{result['integrity_status']}**. All 128 cells cover the same 64 validation IDs, balanced 32 per label.",'',
 f'Baseline and permanent social ablation both scored **{baseline}/64 (50%)**, equal to the constant-label baseline. Both predicted `empathy` on every item: empathy recall 100%, not-empathy recall 0%. There were {changes} changed predictions, {cw} correct-to-wrong changes, and {wc} wrong-to-correct changes.','',
 'The preregistered qualification failed: baseline needed at least 39/64, a net advantage of two, and at least two answers harmed by ablation. This is a retained zero-harm null result. Do not promote this checkpoint/task configuration to the primary preservation benchmark or use held-out test performance to rescue it. No held-out test inference was run.','',
 f"The null is not an inactive-ablation artifact: baseline had {routes['baseline'][1]:,} social selections and ablation had zero. Likelihoods changed on {changed_questions}/64 questions; maximum candidate log-likelihood change was {max(deltas):.9f}. These routing counts include repeated candidate prefixes and do not represent independent observations. Baseline→ablation→baseline reset difference was {sanity['baseline_ablation_baseline_reset_abs_delta']:.1g}.",'',
 f"Both candidates used identical context hashes; context/candidate token boundaries and shared-prefix scores agree. Per-token log probabilities sum to stored candidate scores with maximum absolute error {max_sum_error:.1g}. All cohort/manifest hashes, winners, correctness, route totals and zero-social-ablation checks passed. The run reports CPU float32, four threads, 259 candidate forwards and {summary['elapsed_seconds']:.1f} seconds after loading.",'',
 'This is a capability/measurement failure for the small checkpoint under the fixed three-demonstration likelihood adaptation. It does not establish that every social expert is useless, reject the entire brain-inspired idea, or reproduce a reported empathy accuracy. The labels are a binary proxy for authors\' self-reported empathic concern; the prompt asks whether text expresses empathy. That construct mismatch and unresolved training overlap limit any publication claim. A larger model or different validated measurement would require a new prospective qualification, with this null preserved.']
if errors:lines+=['','Audit errors:']+['- '+e for e in errors]
(OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ['integrity_status','errors','prediction_changes','routing_totals','max_ablation_candidate_likelihood_abs_delta','questions_with_score_change_gt_1e_6']}))
raise SystemExit(1 if errors else 0)
