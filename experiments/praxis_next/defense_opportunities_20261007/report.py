"""Generate the decision dossier from saved results, never fit models."""
import json,pathlib,statistics,html,collections
import numpy as np
from sklearn.metrics import f1_score
from screen import HERE,save
def load(n):return json.loads((HERE/'evidence'/n).read_text())
def pct(x):return 'not estimable' if x is None else f'{100*x:.2f}%'
def main():
 r=load('RESULTS.json');run=load('RUN.json');ext=load('EXTERNAL.json');binary=load('BINARY_RESULTS.json');oldbinary=load('UNFILTERED_BINARY_RESULTS.json');graph=load('GRAPH_EXISTING.json')['results'];simple=load('GRAPH_RESULTS.json');human=load('HUMAN_MEASUREMENT.json');validation=load('VALIDATION.json')
 lines=['# Defense opportunity screen: completed exploratory batch','',
 'All six proposed directions, plus timing and human correction features, received an experiment or an explicit measurement-readiness test. This is a bounded comparison of the represented ideas, not proof that every possible Praxis has been exhausted. No candidate is validated for operational autonomous-APT attribution.','',
 f"New fits: {run['fits']+ext['fits']+binary['fits']+oldbinary['fits']+4} ({run['fits']} Honey; {ext['fits']} independent-collector family; {binary['fits']+oldbinary['fits']} binary reconstruction/filter sensitivities;4 graph baselines). Separately,36 existing trained graph-score settings were rescored at a fixed alert budget. {validation['checks_passed']} developer checks passed. No new attacks, human recruitment, AWS compute or paid inference.",'',
 '## Candidate decisions','',
 '| Direction | Decision | Why |','|---|---|---|',
 '| Fingerprint versus environment/version artifact | Advance as attribution qualification research | Family scores deteriorate when an unseen served version replaces familiar versions. The experiment tests generalization, not causal origin. |',
 '| Incomplete logs / logging requirements | Advance with the first direction | Matching training to observed logs helps, but several views fail the all-environment target. A specification must include version and environment limits. |',
 '| Recovery behavior | Supporting feature, not the main novelty claim | Most gain survives shuffled output order, weakening a specific sequential-recovery explanation. Gains vary by environment/version. |',
 '| Unknown model rejection | Current rules fail; retain as required stress test | Low error on known calibration data does not establish safe identification under unknown families or environment shift. |',
 '| Earliest reliable identification | Current rules fail the combined safety gate | Early agreement must be tested with unfamiliar families; a high known-family accuracy is insufficient. |',
 '| APT detection with missing telemetry | Advance as the most direct defensive alternative, with data qualifications | Stronger saved graph scores lose ranking utility and generate many more alerts under edge loss. Static tensors cannot establish time-outage or chain-level effects. |',
 '| Timing, typos and other human features | Hold as a binary detector | Keyboard telemetry differs by recorder; removing human-only benchmark controls defeats the promising binary result. |','',
 '## Logging results across all five held-out environments','',
 'Macro F1 averages below describe five dependent settings in one corpus. They are not population confidence bounds. A view passes the provisional logging gate only if every environment has adapted F1>=80%. That gate does not certify attribution to an unknown operator.','']
 def table(headers,rows):
  lines.append('| '+' | '.join(headers)+' |');lines.append('|'+ '|'.join('---' for _ in headers)+'|');lines.extend('| '+' | '.join(map(str,x))+' |' for x in rows);lines.append('')
 logging=[]
 for mode in ['full','middle50','first50','last50','truncate32','verbs','no_outputs','random30']:
  a=[x for x in r if x['study']=='logging' and x['model']=='lexical' and x['setting'].endswith('/'+mode+('/full' if mode=='full' else '/adapted'))]
  b=[x for x in r if x['study']=='logging' and x['model']=='lexical' and x['setting'].endswith('/'+mode+('/full' if mode=='full' else '/frozen'))]
  assert len(a)==len(b)==5
  logging.append({'view':mode,'frozen_mean':statistics.mean(x['macro_f1'] for x in b),'adapted_mean':statistics.mean(x['macro_f1'] for x in a),'adapted_min':min(x['macro_f1'] for x in a),'passes':all(x['macro_f1']>=.8 for x in a)})
 table(['View','Frozen mean','Matched-training mean','Worst environment','80% gate'],[[x['view'],pct(x['frozen_mean']),pct(x['adapted_mean']),pct(x['adapted_min']),'pass' if x['passes'] else 'fail'] for x in logging])
 lines+=['Synthetic removal uses saved sessions. `first50` removes the first half; `last50` removes the last half. `truncate32` retains the first32 characters per command. Prefix10 exact duplicates were removed across splits; reductions can create additional collisions. The prior study audited that issue in two settings, but this expanded table is not a near-duplicate-free benchmark.','',
 '## Withheld served versions','',
 'Each row tests only one withheld version and therefore uses accuracy on that version, not multiclass macro F1. Other versions from its served family remain in training. The single-version Meta family cannot receive this test.','']
 versions=[]
 for v in sorted({x['setting'] for x in r if x['study']=='version'}):
  xs={x['model']:x for x in r if x['study']=='version' and x['setting']==v};versions.append([v,xs['lexical']['n'],*[pct(xs[k]['accuracy']) for k in ['lexical','size_error','lexical_recovery']]])
 table(['Held-out version','Sessions','Lexical','Size/error control','Combined recovery'],versions)
 lines+=['## Recovery mechanism checks','']
 recovery=[]
 for env in sorted({x['setting'].split('/')[0] for x in r if x['study']=='logging'}):
  base=next(x for x in r if x['study']=='logging' and x['setting']==env+'/full/full' and x['model']=='lexical')['macro_f1'];combined=next(x for x in r if x['study']=='logging' and x['setting']==env+'/full/full' and x['model']=='lexical_recovery')['macro_f1']
  controls={x['model']+('/shuffled' if x['setting'].endswith('shuffle_outputs') else ''):x['macro_f1'] for x in r if x['study']=='recovery_controls' and x['setting'].startswith(env+'/')}
  recovery.append([env,pct(base),pct(combined),pct(controls['size_error']),pct(controls['output_recovery']),pct(controls['lexical_recovery/shuffled'])])
 table(['Environment','Lexical','Combined','Size/error','Output recovery','Shuffled output order'],recovery)
 lines+=['The shuffled-output arm preserves each session\'s output content/frequency and command sequence, while disturbing which earlier output accompanies a transition. It is a sensitivity diagnostic, not a semantic error-label audit.','', '## Independent collector: Lyptus','',
 '125 eligible AI sessions across three served families; five task-held-out folds, first3 shell submissions,123 retained out-of-fold test sessions after exact-prefix exclusions. These are newly fitted within-corpus models, not frozen Honey-model transfer. No response-conditioned recovery replication is possible from this particular command-only extraction.','']
 external=[]
 for m in ['lexical','correction','lexical_recovery']:
  ps=[x for x in ext['predictions'] if x['model']==m];y=sum([x['y'] for x in ps],[]);p=sum([x['pred'] for x in ps],[]);external.append({'model':m,'n':len(y),'macro_f1':float(f1_score(y,p,average='macro'))})
 table(['Representation','Test sessions','Pooled macro F1'],[[x['model'],x['n'],pct(x['macro_f1'])] for x in external])
 lines+=['The combined label means vocabulary plus correction/shape here: outputs were unavailable. This is not evidence that recovery features replicated externally.','', '## Unknown families and early decisions','',
 'Target: known-session coverage>=50%, accepted known error<=2%, unknown acceptance<=5% in every one of20 held-family/environment settings. Calibration uses known families only. The2% threshold rule uses empirical calibration errors and is not a confidence guarantee.','']
 policies=[]
 for policy in ['always10','margin10','target10','agree_margin','agree_target']:
  xs=[x for x in r if x['study']=='unknown_early' and x['policy']==policy];assert len(xs)==20
  passed=sum(x['known']['coverage']>=.5 and x['known']['accepted_error'] is not None and x['known']['accepted_error']<=.02 and x['unknown_acceptance']<=.05 for x in xs)
  policies.append({'policy':policy,'passed':passed,'settings':len(xs),'known_coverage_min':min(x['known']['coverage'] for x in xs),'known_error_max':max((x['known']['accepted_error'] for x in xs if x['known']['accepted_error'] is not None),default=None),'unknown_acceptance_max':max(x['unknown_acceptance'] for x in xs)})
 table(['Rule','Settings passing all gates','Lowest known coverage','Highest accepted known error','Highest unknown acceptance'],[[x['policy'],f"{x['passed']}/20",pct(x['known_coverage_min']),pct(x['known_error_max']),pct(x['unknown_acceptance_max'])] for x in policies])
 lines+=['## Human/AI shortcut and measurement tests','',
 'The first replay-based fit contained human benchmark-control commands absent from AI shell submissions. The post-result filter removes submissions beginning with task/clear/exit/history on both sides and redoes the original partitions. Eligibility and cohorts change, so this is not a paired causal estimate. It does reveal that the attractive unfiltered score cannot support a robust detector claim.','']
 table(['Input/feature set','AI flags','Human false flags','Equal-expert FPR'],[[stage+'/'+x['model'],f"{x['ai_detected']}/{x['ai_n']}",f"{x['human_false_flags']}/{x['human_n']}",pct(x['equal_expert_fpr'])] for stage,b in [('unfiltered',oldbinary),('filtered',binary)] for x in b['summary']])
 hs=human['human'];lines += [f"Human input audit: {len(hs)} recording triples from {len(set(x['session'] for x in hs))} sessions; {sum(x['input_aligned'] and x['output_aligned'] for x in hs)} align after removing script headers/footers; {sum(x['backspace_delete_bytes']>0 for x in hs)} contain delete/backspace bytes. These include interactive programs, navigation and editing. AI tool logs do not provide equivalent keystroke streams. Treating missing AI keyboard data as zero mistakes would identify the recorder.",'',
 'Neither the filtered binary detector nor timing is ready for deployment. Previous PX124 cross-benchmark transfer also failed its recall/false-label objectives; those are historical results, not newly fitted here.','', '## APT telemetry loss at a fixed alert budget','',
 'The newly fitted simple IsolationForest controls have almost no clean attack recall, so they cannot establish useful robustness. The following new analysis reuses stronger, previously fitted local GIN/MLP nearest-neighbor scores, with source hashes verified. It is not a new MAGIC reproduction.','',
 'The budget is exactly ceil(1% of all test nodes). This is a retrospective ranking budget, not a measured analyst workload or alerts-per-hour deployment rule. Large score ties require special care: use expected recall under uniform boundary-tie selection, alongside deterministic node-ID results and min/max tie bounds in the evidence.','']
 graph_summary=[]
 for ds in ['cadets','theia']:
  for view in ['clean','drop_0.5_mask_20260920']:
   xs=[x for x in graph if x['dataset']==ds and x['view']==view and x['model']=='gin_knn'];row={'dataset':ds,'view':view,**{k:statistics.mean(x[k] for x in xs) for k in ['tie_expected_budget_recall','budget_recall','threshold_recall','threshold_fpr','threshold_alerts','tie_min_budget_recall','tie_max_budget_recall']}};graph_summary.append(row)
 table(['Dataset/view','Recall at1% budget, tie expectation','Threshold recall','Threshold false-positive rate','Threshold alerts, mean'],[[x['dataset']+'/'+x['view'],pct(x['tie_expected_budget_recall']),pct(x['threshold_recall']),pct(x['threshold_fpr']),f"{x['threshold_alerts']:,.0f}"] for x in graph_summary])
 lines+=['These are means over three model/reference-bank seeds, not three independent campaigns. CADETS already has an impractical clean false-positive rate. Prepared graphs lack timestamps and chain ground truth; random edge loss does not simulate a verified time outage. Node recall is not attack-chain recall. Despite those limitations, the ranking/alert-volume deterioration motivates a defense-focused candidate.','',
 '## Recommended choice','',
 '**For the most direct defensive question:** investigate whether telemetry loss causes alert flooding and loss of useful attack evidence under a fixed investigation budget. The next contribution must be a mitigation that preserves evidence ranking, tested on chronological public logs with qualified labels. Existing scores establish a failure mode, not that mitigation.','',
 '**For the most feasible AI-focused Praxis:** combine version/environment qualification with logging requirements. Ask when a defender must decline model-family attribution. The current positive fingerprinting scores are conditional on familiar versions and observation mechanisms.','',
 'Recovery is a secondary feature study. Unknown/early rejection remains an unsolved requirement. Do not select a quick typo/timing binary flag as the primary result. All novelty claims remain conditional on the comparison in SOURCES.md, especially the unavailable Honey full text.','',
 'The supplied observation_contract.py is a research decision aid: it checks a declared logging view against measured conditions and explicitly declines deployment certification. It does not infer malicious intent or execute source commands.']
 lines+=['','Binary denominators: the unfiltered55 AI appearances represent45 unique sessions; filtered43 appearances represent42. Human sessions come from only5 experts. Repeated evaluations are not independent participants. The no_outputs lexical control is unchanged by construction; combined-model sensitivity remains in RESULTS.json.']
 text='\n'.join(lines)+'\n'
 for a,b in [(';4','; 4'),('Separately,36','Separately, 36'),('first32','first 32'),('first3','first 3'),('submissions,123','submissions, 123'),('of20','of 20'),('The2%','The 2%'),('at1%','at 1%'),('unfiltered55','unfiltered 55'),('represent45','represent 45'),('filtered43','filtered 43'),('represent42','represent 42'),('only5','only 5')]:text=text.replace(a,b)
 (HERE/'FINDINGS.md').write_text(text,encoding='utf-8')
 # A deliberately plain self-contained report, with preformatted tables preserving exact text.
 (HERE/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Defense opportunity screen</title><style>body{max-width:1200px;margin:2em auto;padding:1em;font:16px system-ui;line-height:1.5}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px ui-monospace,monospace}</style><h1>Defense opportunity screen</h1><pre>'+html.escape(text)+'</pre></html>',encoding='utf-8')
 save(HERE/'evidence/SUMMARY.json',{'new_fits':run['fits']+ext['fits']+binary['fits']+oldbinary['fits']+4,'logging':logging,'unknown_policies':policies,'external':external,'graph':graph_summary,'scope':'Exploratory screen, no deployable detector or established novelty'})
 print('report generated')
if __name__=='__main__':main()
