import json,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;rows=json.loads((HERE/'RESULTS.json').read_text());main=[r for r in rows if r['episode_gap_min']==60]
lines=['# PX-103 — Budgeted restoration of suppressed warnings','',
'## What was tested','',
'The proposed rule favors a source with no warning in the previous hour, then ranks by member attack-versus-benign margin. Comparators are confidence alone, earliest candidate, ten random seeds, ordinary mean aggregation and unrestricted OR. All selection uses data available at 15-minute window close. Labels are used only for evaluation. Budgets of 1, 5 and 20 are supplemental case slots per capture per window; baseline work is not capacity constrained. No new models or AWS jobs. This is an exposed-data pilot, not independent confirmation.','',
'## Episode coverage and additional benign cases','',
'Each cell is **new exfiltration episode proxies / additional benign-only cases**, versus mean aggregation. Random cells show separate ranges across ten seeds; their endpoints need not occur in the same run. Budgets cap slots per window, not total cases or benign cases.','',
'| Source | Slots/window | Proposed coverage | Confidence | Earliest | Random range |','|---|---:|---:|---:|---:|---:|']
success=[]
for ex in ['UNRAVELED','wilson','harrison']:
 for b in [1,5,20]:
  cells=[];det={}
  for method in ['coverage','confidence','earliest','random']:
   rr=[r for r in main if r['execution']==ex and r['budget_per_bin']==b and r['method']==method]
   if method=='random':cells.append(f"{min(r['new_episodes'] for r in rr)}–{max(r['new_episodes'] for r in rr)} / {min(r['additional_benign_only_cases'] for r in rr)}–{max(r['additional_benign_only_cases'] for r in rr)}")
   else:det[method]=rr[0];cells.append(f"{rr[0]['new_episodes']} / {rr[0]['additional_benign_only_cases']}")
  c=det['coverage'];v=det['confidence'];success.append({'execution':ex,'budget':b,'superior':c['new_episodes']>v['new_episodes'] and c['additional_benign_only_cases']<=v['additional_benign_only_cases']})
  lines.append(f'| {ex} | {b} | '+ ' | '.join(cells)+' |')
lines+=['','## Candidate-pool ceiling','','| Source | Mean episodes | OR episodes | Total episode proxies | Mean exfil flows | OR exfil flows | OR extra cases | OR extra benign-only cases |','|---|---:|---:|---:|---:|---:|---:|---:|']
for ex in ['UNRAVELED','wilson','harrison']:
 a=next(r for r in main if r['execution']==ex and r['method']=='mean');b=next(r for r in main if r['execution']==ex and r['method']=='OR')
 lines.append(f"| {ex} | {a['covered']} | {b['covered']} | {a['episodes']} | {a['exfil_warned']} | {b['exfil_warned']} | {b['additional_cases']} | {b['additional_benign_only_cases']} |")
lines+=['','## Predeclared hypothesis','',f"The proposed ranking beats confidence on the strict primary criterion in **{sum(r['superior'] for r in success)} of {len(success)} source/budget cells**. These cells are dependent sensitivity settings, not independent replications. Tied episode coverage is not evidence of superiority.",'',
'Post-result diagnostic (RANKING_DIAGNOSTIC.json): coverage and confidence choose exactly the same cases in all nine cells. Thus this pilot provides no observed benefit from the source-history criterion and cannot meaningfully assess its value in harder queues. At one slot per window, some random runs recover two UNRAVELED episode proxies whereas both deterministic rankings recover one. Do not claim the proposed method is best.','',
'At five supplemental slots per window, UNRAVELED recovers both available additional episode proxies with 331 additional cases, including 13 benign-only cases. The other 318 cases include attack warnings, but they are still workload. Reporting only the 13 benign cases would substantially understate total review demand. Unrestricted OR adds 332 cases, including 14 benign-only cases: the five-slot rule saves just one case.','',
'Recommendation: retain this as a bounded negative result supporting the existing audit Praxis. Do not promote the source-coverage prioritizer as a new successful repair. The promising remaining claim concerns accurate, verifiable explanations of warning loss, whose benefit to actual reviewers remains untested (PX-102). A fresh dataset must contain multiple independently labeled episodes and real competition for review slots before claiming a general operational advantage.','',
'## Interpretation and limitations','',
'- A ranking cannot recover an episode with no warning anywhere in its candidate pool. The OR ceiling separates this problem from poor prioritization.',
'- More exfiltration flow warnings do not necessarily expose a new attack episode. AIT contains only one exfiltration episode proxy per execution at the primary gap, limiting this endpoint.',
'- Appending suppressed flows to an existing mean case consumes no additional case count in this replay. It can still require analyst effort. Cases are workload proxies, not measured investigations or minutes.',
'- Explanations state which member margin and prior warning coverage drove selection. They do not establish attack causality or human usefulness.',
'- Every arm uses window-close delivery for comparable first-warning times. This adds up to 15 minutes relative to immediate completed-flow scoring. Median delay is conditional on detected episodes; it must be read with coverage.',
'- Thirty- and 120-minute episode-gap sensitivities, flow counts, delays and all random runs are retained in RESULTS.json. No post-result threshold tuning or favorable-run selection.',
'- Our models use completed-flow records. This is not an online prevention claim.',
'','## Literature and novelty','',
'**Do not claim first application of explainable prioritization to APT data.** [CyberShapley](https://www.sciencedirect.com/science/article/pii/S0167404824005765) already combines explanation, prioritization and triage, using PublicArena and DARPA E3 CADETS/Theia. Publisher-indexed method and dataset sections were available; direct full-page retrieval returned 403, so this is not a complete full-text comparison.',
'',
'[AlertPro](https://doi.org/10.1016/j.cose.2023.103583) already studies contextual prioritization for multi-step attacks and limited analyst resources. [EXP-SEC](https://arxiv.org/abs/2607.12203) explains intrusion decisions in security-relevant terms. [Reliability auditing of explanations for machine-learning-based intrusion detection systems](https://link.springer.com/article/10.1007/s11416-026-00664-7) already audits feature explanation reliability.',
'',
'The narrower candidate contribution is selective restoration of warnings lost by an aggregation decision, accompanied by verifiable selection explanations and episode/workload accounting. No reviewed evidence establishes first-of-kind novelty. Applying an existing technique to UNRAVELED alone is not a sufficient novelty argument. This pilot compares simple operational baselines, not implementations of CyberShapley or AlertPro.',
'','## Reproduction','',
'Frozen inputs, code and protocol are in FREEZE.json; freeze commit e27b199. Run `python run.py run`, `python audit.py`, then `python report.py` with the existing Praxis environment and private inputs. The runner refuses to overwrite RESULTS.json. Private warning masks and explanation records are in C:/w/px103_warning_budget_20261003. Their hashes are in ARTIFACTS.json.']
(HERE/'FINDINGS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(HERE/'PRIMARY_DECISION.json').write_text(json.dumps(success,indent=2)+'\n')
print('\n'.join(lines[:30]))
