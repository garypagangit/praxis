"""Generate a readable aggregate report and flat CSV from saved experiment outputs."""
import csv,html,json,statistics
from prepare import HERE,save

def main():
 ev=HERE/'evidence';r=json.loads((ev/'RESULTS.json').read_text());b=json.loads((ev/'BINARY_RESULTS.json').read_text());d=json.loads((ev/'DATA_AUDIT.json').read_text());run=json.loads((ev/'RUN.json').read_text())
 ab=json.loads((ev/'ABLATION_RESULTS.json').read_text());abrun=json.loads((ev/'ABLATION_RUN.json').read_text())
 sections=[];lines=['OPERATOR SIGNALS: EXISTING-DATA EXPLORATION','7 October 2026','',
  'Exploratory reanalysis to choose a Praxis, not a validated autonomous-APT detector.',
  f"Honey: {d['counts']['included']:,} eligible sessions from {d['counts']['files']:,} files; nine served models, four families.",
  f"Completed distinct study fits: {run['completed_unique_study_fits']+b['fits']+abrun['fits']}; plus {run['checkpoint_reconstruction_fits']} checkpoint reconstruction fits. Saved multiclass result rows: {len(r)+len(ab)}.",
  'No new attack collection, no human recruitment, no cloud inference.',
  'Local protocol commits preceded their respective fits and are published with the results. Previously inspected data: not independent confirmatory evidence.','']
 def table(title,headers,rows):
  lines.append(title);lines.append(' | '.join(headers));lines.extend(' | '.join(map(str,row)) for row in rows);lines.append('')
  sections.append('<h2>'+html.escape(title)+'</h2><table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>')
 def pct(x):return 'not estimable' if x is None else f'{100*x:.1f}%'
 def group(setting):return setting.split('_')[0]
 agg=[]
 for g in ['iid','env','prompt','cells']:
  for m in ['prior','lexical','structure','correction','recovery','timing','lexical_recovery','shuffled_lexical']:
   rs=[x for x in r if x['study']=='S1' and group(x['setting'])==g and x['model']==m]
   if rs:agg.append([g,m,str(len(rs)),pct(statistics.mean(x['macro_f1'] for x in rs)),pct(min(x['macro_f1'] for x in rs)),pct(max(x['macro_f1'] for x in rs))])
 table('S1: Family identification (macro F1; arithmetic mean across settings, not independent replications)', ['Split','Representation','Settings','Mean','Min','Max'],agg)
 abtable=[]
 for g in ['iid','env','prompt','cells']:
  for m in ['lexical_correction','lexical_output_recovery','lexical_edit_retry']:
   xs=[x['macro_f1'] for x in ab if group(x['setting'])==g and x['model']==m]
   abtable.append([g,m,pct(statistics.mean(xs)),pct(min(xs)),pct(max(xs))])
 table('S1A: Post-initial-results ablation (exploratory, not independent confirmation)', ['Split','Addition to lexical','Mean F1','Min','Max'],abtable)
 stress=[]
 for x in r:
  if x['study'] not in {'S2_frozen','S2_adapted'}:continue
  name,mode=x['setting'].split('/');base=next(y for y in r if y['study']=='S1' and y['setting']==name and y['model']==x['model'])
  stress.append([name,mode,x['model'],x['study'],pct(x['macro_f1']),f"{100*(x['macro_f1']-base['macro_f1']):+.1f}"])
 table('S2: Incomplete-log sensitivity; same test sessions, synthetic masking', ['Split','Mask','Model','Fit','Macro F1','Change (pp)'],stress)
 reduced=json.loads((ev/'REDUCED_OBSERVATION_AUDIT.json').read_text())
 table('S2 sensitivity: adapted lexical model after excluding exact reduced-view overlap (changed test cohort)', ['Split','Mask','Original n','Excluded matches','Remaining n','Macro F1'], [[x['setting'],x['mask'],x['test_n'],x['matching_reduced_training_or_calibration'],x['unseen_reduced_test_n'],pct(x['unseen_reduced_macro_f1'])] for x in reduced['results'] if x['study']=='S2_adapted'])
 unknown=[[x['setting'],x['model'],str(x['known_n']),str(x['unknown_n']),pct(x['known_coverage']),pct(x['known_accepted_accuracy']),pct(x['unknown_acceptance'])] for x in r if x['study']=='S4']
 table('S4: Unknown families (lower unknown acceptance is better)', ['Split/family/quantile','Model','Known n','Unknown n','Known coverage','Known accepted accuracy','Unknown accepted'],unknown)
 early=[[x['setting'],x['model'],str(x['n']),pct(x['coverage']),pct(x['accepted_accuracy']),pct(x['wrong_per_all']),str(x['later_reversals']),str(x['decision_command_counts'])] for x in r if x['study']=='S5_rule']
 table('S5: Early stable decisions (family identity, not AI-versus-human)', ['Split/cohort','Model','n','Coverage','Accepted accuracy','Wrong/all','Later reversals','Commands (0=abstain)'],early)
 binary=[[x['model'],f"{x['ai_detected']}/{x['ai_n']}",f"{x['human_false_flags']}/{x['human_n']}",pct(x['equal_expert_fpr'])] for x in b['summary']]
 table('B1: Human-versus-AI pilot; 5 human experts, incomplete terminal extraction', ['Model','AI flags/test appearances','False human flags','Equal-expert FPR'],binary)
 notes=[
  'Binary AI denominator 27 is fold appearances from 26 unique AI sessions; human denominator 16 is 16 sessions from 5 experts. Do not treat folds or repeated AI appearances as independent people.',
  'Timing gate: every eligible Honey session has strictly increasing values in both timing fields. Documentation calls them durations, but observed behavior warrants elapsed-clock investigation. No cross-source human/AI timing classifier was fitted.',
  ('GAMBiT: '+str(d['human']['rows'])+' rows; '+str(d['human']['bad_timestamp_rows'])+' fail ISO timestamp parsing; all '+str(d['human']['gaps'])+' parsed within-participant/day gaps are integer seconds. No comparable output-completion clock or keystrokes in this export.') if 'human' in d else 'Optional GAMBiT timestamp audit not supplied in this reproduction.',
  'Timing-only family results are collection/runtime diagnostics; they may identify model size, hardware or execution scheduling, not intrinsic operator behavior.',
  'Correction includes command length/complexity; edit_retry isolates two narrower proxies. Neither establishes real typing errors. Incomplete human extraction can invent adjacency and suppress real edits.',
  'Recovery uses explicit error-string heuristics, not independent semantic labels; no-shell-output and corruption tests measure sensitivity to observable fields.',
  'Data qualification excludes malformed/short sessions and exact cross-partition first-ten-command duplicates; selection can change class distribution. Similar templates and repeated common prefixes remain.',
  'Unseen environment/prompt/cell tests share the same collector. This is not cross-collector validation or proof of model causality. Family names refer to served identities, not distillation ancestry.',
  'Unknown rejection margins are not calibrated probabilities and provide no guaranteed error control under shift.',
  'The initial solver run had convergence warnings and incomplete warning capture around checkpoint resumes. The full family/ablation pipeline was rerun with the equivalent primal solver. Final recorded warnings: '+str(len(run['warnings'])+len(abrun['warnings']))+'. Original evidence and numerical differences are preserved; this is not independent replication. See SOLVER_CORRECTION.txt.',
  'APT detection under missing telemetry remains a separate fallback: no APT benchmark was executed or AI-control labels inferred from ordinary attack logs.',
  'No result establishes malicious intent, fully autonomous control, or complete APT campaign attribution. Novelty remains a literature-qualified candidate, not a first-ever claim.'
 ]
 lines+=['INTERPRETATION AND LIMITATIONS']+notes
 (HERE/'FINDINGS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 svg=''
 if (HERE/'OVERVIEW.svg').exists():
  svg=(HERE/'OVERVIEW.svg').read_text(encoding='utf-8');svg=svg[svg.index('<svg'):]
  svg=svg.replace('<svg ','<svg role="img" aria-label="Family fingerprint performance by environment and retained log information" ',1)
 document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Operator signals research pilot</title><style>body{font:16px system-ui,sans-serif;color:#16242c;max-width:1200px;margin:40px auto;padding:0 20px;line-height:1.5}h1{font-size:30px}h2{font-size:21px;margin-top:36px}table{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow-x:auto}th,td{padding:8px;border:1px solid #ccd5d9;text-align:left}th{background:#e8f0f3}tr:nth-child(even){background:#f5f7f8}svg{width:100%;max-width:900px}svg text{font:13px system-ui}li{margin-bottom:10px}</style><h1>Operator signals: existing-data exploration</h1><p>7 October 2026. Exploratory evidence for choosing a Praxis. Family identification and human-versus-AI detection are different tasks.</p><p>'+html.escape(lines[4])+'</p>'+svg+''.join(sections)+'<h2>Interpretation and limitations</h2><ul>'+''.join('<li>'+html.escape(n)+'</li>' for n in notes)+'</ul></html>'
 (HERE/'REPORT.html').write_text(document,encoding='utf-8')
 keys=sorted(set(k for x in r+ab for k,v in x.items() if not isinstance(v,(list,dict))))
 with (ev/'RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,keys,extrasaction='ignore');w.writeheader();w.writerows(r+ab)
 save(ev/'SUMMARY.json',{'family_macro_f1':agg,'ablation_macro_f1':abtable,'binary':b['summary'],'completed_unique_study_fits':run['completed_unique_study_fits']+b['fits']+abrun['fits'],'checkpoint_reconstruction_fits':run['checkpoint_reconstruction_fits'],'limitations':notes})
 print('report created')

if __name__=='__main__':main()
