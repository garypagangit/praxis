"""Build a review edition without changing historical result tables or equations."""
import json,re,shutil,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;OLD=B/'gwu_revision_20261001'
def write(name,text): (H/name).write_text(text.strip()+'\n',encoding='utf-8')
s=(OLD/'manuscript.md').read_text(encoding='utf-8')
def section(start,end,new):
    global s
    a=s.index(start);b=s.index(end,a);s=s[:a]+new.strip()+'\n\n'+s[b:]
section('## 1.4 Thesis Statement','## 1.5 Research Objectives', '''## 1.4 Thesis Statement

A model review should explain what happens to an attack warning, not just whether the final stage label is correct. This praxis provides a reproducible audit of three decisions: which evidence is used, how model outputs are combined, and when a fixed policy adds a warning. The audit connects those decisions to missed attacks and extra review cases on the same recorded events.

The proposed contribution is specific: paired accounting of stage-label changes and warning loss in an APT flow pipeline, with saved decision records, checks that reproduce those decisions, and measured limits of attempted repairs. The pipeline is the sequence of software steps between input data and a final warning. The contribution is an applied audit and its evidence, rather than a new classifier or a new definition of recall.

This study does not claim the first discovery of performance regression. Earlier work already reports improving scores alongside lost detections. The contribution must be judged on the controlled APT-stage comparisons, their reproducibility and the practical questions the audit answers. Chapter 2 compares the closest work directly.''')
s=s.replace('This October 1 revision adds PX-092 through PX-097.', 'The October 1 evidence branch adds PX-092 through PX-097.')
s=s.replace('## 1.9 How to Read This Paper', '''The October 4 review edition integrates PX-098 through PX-105 and adds PX-106, a descriptive reanalysis of saved prediction changes. PX-106 uses 27 paired comparisons and adds no model fits. The explanation and ranking studies did not demonstrate a new algorithm that improves on their strongest simple controls. No human-review study was completed.

## 1.9 How to Read This Paper''')
s=s.replace('Readers interested in the latest repair studies can start with Sections 3.13 and 4.12-4.15.', 'Readers interested in repairs can start with Sections 3.13 and 4.12-4.15. Sections 3.14 and 4.16 explain the audit extensions; Sections 3.15 and 4.17 compare lost warnings with exact-stage regression. Appendix G gives a plain-language guide and the evidence map.')
s=s.replace('It is not an exhaustive literature review or proof of priority.', 'The October 4 update includes full-text comparisons of CyberShapley and AlertPro and a further search on model regression. It is not an exhaustive literature review or proof of priority.',1)
section('## 2.6 Literature Gap and Contribution Positioning','## 2.7 Machine-Learning Foundations', '''## 2.6 Literature Gap and Contribution Positioning

The broad problem is established. AlertPro already reports a higher F1 score with lower attack recall. In its LLDOS comparison, basic features produce F1 of 0.6188 and recall of 90.78%; basic plus context produces F1 of 0.8151 and recall of 73.75% (Wang et al., 2024, Table 4). Its authors discuss this recall loss. That result motivates the present audit; it is not a discovery claimed here.

CyberShapley explains and prioritizes security alerts using connected groups of events and Shapley importance. It evaluates APT-related data, includes a small human study and illustrates ChatGPT-4 as a virtual analyst (Malach et al., 2025). Explainable APT triage, event-removal checks and bot-assisted review therefore already have direct precedents. This praxis did not implement or outperform CyberShapley.

Yan et al. (2021) call a previously correct prediction that becomes incorrect a negative flip. Their work also uses ensembles and training constraints to reduce these changes. Ghiani et al. (2026) apply regression-aware learning to Android malware. Thus, preserving detections across model updates is already an established research problem. Our saved policy comparisons are not a continual-learning benchmark or an evaluation of their training methods.

The narrower question is what happens when a stage prediction is already wrong but still provides an attack warning. If that record later becomes benign, the warning disappears without a correct-to-incorrect stage change. PX-106 counts these cases explicitly. Standard binary negative-flip counting also catches them. The value is making both levels visible in the same APT review, not renaming an existing binary metric.

The proposed research product combines paired stage and warning accounting, recorded evidence decisions, episode and case counts, source qualification, and reproducible checks. Each component has prior art. The contribution is the specific tested procedure and the evidence showing where its decisions and attempted repairs matter. Neither a new dataset application alone nor the absence of an identical title establishes novelty.

| Closest work | What is already established | What this study evaluates |
|---|---|---|
| TESSERACT (2019) | Time and distribution affect security evaluation | Same-test-set APT training-composition contrast |
| Uddin et al. (2025) | Wrong attack type differs from attack called normal | Paired stage destinations under evidence changes |
| AlertPro (2024) | Alert ranking, limited review budgets, F1 up with recall down | Lost stage warnings, attempted repairs and case costs |
| CyberShapley (2025) | APT alert explanations, triage and reviewer evaluation | Recorded warning loss inside an evidence pipeline |
| Yan et al. (2021); Ghiani et al. (2026) | Negative flips and regression-aware training | Exact-stage versus binary warning transitions |
| Kittler et al. (1998) | Combining classifier decisions | Limits and measured costs of retaining any warning |

The review is targeted. The full-text comparison and source hashes are recorded in the literature-review evidence folder. It supersedes earlier access limitations for CyberShapley and AlertPro. No empirical superiority over these published systems is claimed. Committee assessment of whether this applied contribution meets the Praxis requirement remains necessary.''')
s=s.replace('No graph-neural model, TabM architecture or large language model was fitted in this completed measurement batch.', 'No graph-neural model, TabM architecture or large language model was fitted in that original measurement batch. The separate PX-098/PX-099 pilot later used a pretrained visual-language model; its results are reported separately.')
methods='''## 3.14 Auditable-AI and Explanation Follow-ups

Here, auditable AI means that a reviewer can inspect the evidence used for a decision and check the reported outcome. It does not mean that every learned feature has a causal explanation. The audit asks a concrete question: where did an available warning disappear?

PX-100 replays the recorded acquisition actions for 54 combinations of seed, evidence condition, budget and policy. It checks the resulting evidence state, spending, elapsed time and final probabilities against saved outputs. This verifies the effects of recorded actions; it does not regenerate the selector's score or prove that the selected action was optimal. A separate replay compares mean and OR combination with the same model outputs.

PX-101 examines feature explanations on 512 diagnostic records: 128 missed exfiltration records, 128 warned exfiltration records, 128 correctly benign records and 128 false alerts. Three saved models explain the same benign-minus-exfiltration raw-score difference. TreeSHAP contributions (Lundberg et al., 2020) are checked against raw scores and compared across fitting seeds. Top-five overlap is the size of the shared feature set divided by the size of its union. These balanced diagnostic groups do not estimate their prevalence in normal traffic. Attribution agreement does not prove causal validity.

PX-102 prepared 12 review cases but recruited no participants. PX-104 instead tested deterministic software reviewers on six information conditions using three fixed review rules, producing 216 reviews. The rules calculate, follow or verify a supplied explanation. This is a software consistency test. It cannot measure how a SOC analyst understands an explanation or how much time an analyst saves.

PX-103 replays a proposed rule that prioritizes sources without a recent warning. It compares that rule with confidence, earliest-first and ten random rankings under 1, 5 or 20 extra case slots per 15-minute window. The existing alert queue is not capacity limited in this test. Cases and time-defined episodes are proxies, not measured investigations or independently confirmed incidents. The primary episode gap is 60 minutes, with 30- and 120-minute sensitivity checks.

PX-105 injects known aggregation, evidence-selection and deadline failures into recorded examples. It compares an ordinary decision trace with the same trace plus replay. The 170 scenarios contain 90 unique record hashes; repeated scenarios are not independent attacks. Missing-timing controls test whether the conservative reviewer abstains when required evidence is absent. No new SHAP diagnosis baseline is run in this study.

The separate PX-098 pilot uses frozen Qwen2.5-VL-7B-Instruct inference on 24 host-hour windows with twelve five-minute bins. Image and numeric-text inputs contain the same flow aggregates; eight windows form an enriched diagnostic set. PX-099 supplies two eight-host timeline images and corresponding text. These are feasibility checks, not population estimates. Raw replies and the later syntax-only parser correction are retained. Four local numerical follow-ups compare alternative window summaries under a fixed added benign-hour allowance.

All these follow-ups use previously examined data. Their protocols fix the stated comparisons before their own calculations, but they remain exploratory. Their purpose is to test the proposed audit extensions against simple controls, including outcomes that do not support the proposed extension.

## 3.15 Warning Transitions and Exact-Stage Regression: PX-106

PX-106 compares the saved entropy and error-focused predictions in all 27 PX-081 pairs: three fitting seeds, three evidence conditions and three budgets. The entropy policy is the reference and the error-focused policy is the candidate. Both predict the same 208,094 test records. This is a policy comparison using saved models, not a simulated stream of production model updates.

For each true attack stage, a four-by-four table records the old and new predicted labels. The audit separates two losses: a correct stage label becoming benign, and a wrong attack-stage label becoming benign. Both remove a warning. It also counts benign-to-attack gains, which can offset losses in a net recall measure.

The arithmetic check is simple: new warnings minus lost warnings must equal the change in total warned records. Exact-class negative flips count previously correct labels that become incorrect. Binary negative flips instead count previously warned attacks that become benign and therefore include both loss types above. Neither is a new metric. Keeping both identifies what a stage-only comparison omits.

The primary display uses the already established clean, budget-three comparison, with every fitting seed shown. All 27 pairs and all three attack stages remain in the saved tables. No significance test treats repeated rows or fitting seeds as independent attacks.

For a descriptive check only, PX-106 also applies the earlier illustrative tolerances to test results: F1 must rise, no supported attack stage may lose more than one percentage point of warning recall, and benign false-alert rate may rise by no more than 0.1 percentage point. This is not the calibration-only acceptance procedure in Section 3.11. Its outcome is not evidence of a prospective deployment gate.

The new protocol and input hashes were frozen before this calculation. An independent calculation reconstructs the transition tables and F1 values from saved predictions. No training or threshold search is performed.

'''
s=s.replace('# Chapter 4:',methods+'# Chapter 4:',1)
r=json.loads((B/'warning_transitions_20261004/RESULTS.json').read_text())['pairs']
primary=[v for v in r if v['condition']=='clean' and v['budget']==3]
transition='\n'.join(f"| {v['seed']} | {v['stages'][2]['losses']} | {v['stages'][2]['exact_to_benign']} | {v['stages'][2]['wrong_attack_to_benign']} | {v['stages'][2]['gains']} | {v['stages'][2]['warning_new']-v['stages'][2]['warning_old']} |" for v in primary)
results='''## 4.16 What the Explanation and Ranking Tests Established

PX-100 reproduced 54 acquisition cells with zero mismatches across 11,237,076 row-condition replays. That large count repeats the same 208,094 records under different conditions. It shows that the saved actions account for the recorded outcomes. It is not evidence from eleven million independent attacks.

The aggregation check reproduces a useful distinction. On UNRAVELED, mean combination warns on 2,342 of 3,442 exfiltration flows; OR warns on 3,400. Benign warnings rise from 182 to 196. On AIT Harrison, the same change adds only two exfiltration warnings while benign warnings rise from 857 to 1,404. The rule guarantees retention of member warnings, but its practical price depends on the source.

**Table 4-21. Explanation and prioritization follow-ups.** These are exposed-data studies. Successful arithmetic checks do not establish a novel detection method or human benefit.

| Study | Main finding | What it supports |
|---|---|---|
| PX-100: decision replay | 54 acquisition cells reproduced without mismatch | The recorded actions explain the saved routing outcome |
| PX-101: feature explanations | 512 rows; top-five overlap 0.658 for missed and 0.776 for warned exfiltration | Explanation stability differs between these diagnostic groups |
| PX-102: human review | 12 cases prepared; zero participants | No conclusion about analyst benefit |
| PX-103: budgeted ranking | Same selected cases as confidence in all nine primary comparisons | No added value for the proposed source-coverage rule |
| PX-104: reviewer bot | 216 deterministic reviews; calculator and verifier both correct on 12 valid cases | Software consistency, without a gain over direct calculation |
| PX-105: cause diagnosis | Trace and trace-plus-replay both correct on 170/170 scenarios | Replay supplied no diagnosis gain over the ordinary trace |

PX-101's probability checks agree with saved models within 3e-8 and its attribution sums agree with raw scores within 1.7e-14. Those checks establish numerical consistency. They do not establish whether a feature causes an attack or whether an explanation helps an analyst. The top-five overlap figures are descriptive cohort summaries, not evidence of a statistically established difference between independent populations.

PX-103's five-slot rule adds two UNRAVELED episode proxies relative to mean aggregation, but requires 331 additional grouped cases. Only 13 of those are benign-only cases; reporting just those 13 would substantially understate the review queue. Its selections match confidence ranking. Neither AIT execution gains another exfiltration episode proxy; each already has one detected proxy under the primary gap definition.

PX-104 rejects 36 deliberately contradictory explanations and abstains on 12 missing-evidence cases under its verification condition. The ordinary calculator already answers the valid cases correctly. The test contains 11 unique score vectors across its 12 cases, not 12 independent incidents. It does not replace the unfinished human study.

PX-105's two complete-trace methods also agree on all 510 repair-feasibility questions. Twenty-one pairs have identical final expert inputs and scores but different selection-versus-deadline causes. This shows why pipeline metadata can be needed to explain a software outcome. It is an information limit, not an observed accuracy win over SHAP. Removing timing causes 106 conservative abstentions.

The separate visual pilot, PX-098/PX-099, did not establish a repair. After a documented syntax-only parser correction, the visual model flagged none of eight diagnostic positive windows. The timeline task did not produce usable stage coverage. Four local numerical follow-ups also failed their stated one-percentage-point benign-hour budget screen. These results do not show that every visual model will fail. They provide no basis for presenting this pilot as a positive contribution.

## 4.17 Which Lost Warnings a Stage-Only Regression Count Misses

PX-106 verifies every transition count in 27 policy pairs. The separate audit passes 945 checks. Table 4-22 shows the clean, budget-three exfiltration comparison; the true-stage support is 3,442 records in every row.

**Table 4-22. Exfiltration warning changes, entropy to error-focused selection.** Losses count individual records that were warned before and benign afterward. Gains count the opposite change. Rows are repeated fits on the same events.

| Seed | All losses | Correct stage to benign | Wrong attack stage to benign | Gains | Net warnings |
|---|---|---|---|---|---|
TRANSITION_ROWS

Seed 8101 provides the clearest example: 901 records lose their warning, but only eight had previously received the exact exfiltration label. The other 893 were previously labeled as another attack stage. A correct-stage-to-incorrect-stage count cannot capture that second group because its old stage label was already wrong. Four other records gain warnings, leaving a net decrease of 897.

The other seeds limit the interpretation. Seed 8102 loses four warnings and gains one; seed 8103 loses 25 and gains three. The large loss in the first seed is not a uniform effect across fitting runs. All three runs are retained rather than presenting the largest as typical.

Binary attack-versus-benign negative flips capture all these losses. PX-106 therefore supports reporting both stage and warning transitions, not superiority over a correctly configured binary regression audit. It also shows why lost and gained counts should accompany net recall: gains elsewhere can hide which previously warned records became silent.

Only two of the 27 pairs pass the illustrative test-outcome review rule. This number describes already inspected test results. It does not show that a calibration gate would have made the same decisions before deployment, and passing the tolerance does not mean zero warning losses.

'''.replace('TRANSITION_ROWS',transition)
s=s.replace('# Chapter 5:',results+'# Chapter 5:',1)
s=s.replace('## 5.2 Contributions','''The explanation follow-ups narrow the conclusion further. Recorded decision traces can explain where the software lost an available warning. Extra replay did not improve diagnosis over a complete trace, and the proposed ranking rule did not improve on confidence. The evidence supports an auditable procedure; it does not support a new XAI algorithm or improved human triage.

## 5.2 Contributions''',1)
s=s.replace('These are applied measurement and engineering contributions.', 'PX-106 adds a direct comparison with exact-class regression: a wrong-stage warning can become benign without creating an exact-class negative flip. A binary regression audit catches that change. The paper therefore makes both views explicit and reports gains as well as losses.\n\nThese are applied measurement and engineering contributions.',1)
s=s.replace('| Uncertainty | Per-seed values', '| Decision trace | Member outputs, selected evidence, delivery times and combination rule | Where an available warning was retained or discarded |\n| Warning transitions | Previously warned attacks now benign, previously missed attacks now warned, and true stage | Whether net improvement masks losses on particular records |\n| Uncertainty | Per-seed values',1)
s=s.replace('## 5.5 Next Research Steps','''### 5.4.8 Explanation, novelty and reviewer limits

CyberShapley and AlertPro already address explainable triage and contextual alert review. Negative-flip research already examines regression after model changes. The present study does not establish first use of XAI on APT data, a new warning metric, a new classifier-combination rule or the first observation of score improvement with detection loss.

The follow-ups use inspected records and small diagnostic groups. The bot is deterministic software with a known answer rule. No recruited analysts, handling-time measurements or independent explanation annotations support a claim of human usefulness. Complete trace replay checks a software mechanism, not the real-world cause of an attack. More repeated replay cells do not expand the independent campaign sample.

## 5.5 Next Research Steps''',1)
s=s.replace('## 5.6 Conclusions','''Any further method claim should first compare with the appropriate simple control: binary negative-flip accounting for lost warnings, ordinary traces for pipeline diagnosis, and confidence ranking for the tested review queue. The current results do not justify additional paid model runs merely to seek a favorable result. A new data source or a genuinely different mechanism would be needed to test a broader claim.

## 5.6 Conclusions''',1)
s=s.replace('The result is an evaluation method and a local warning repair; universal exfiltration prevention remains unproven.', 'The result is a reproducible audit and a limited local repair. Count lost warnings even when the earlier stage name was wrong. The explanation studies verify recorded decisions, but show no added diagnosis benefit from replay or measured analyst benefit. Broader effectiveness and first-of-kind XAI novelty remain unproven.')
s=s.replace('The average direction survived the reported single-seed and single-capture omissions, but its size depended strongly on the fitting seed.', 'The direction survived seed and capture omissions, but its size depended strongly on the fitting seed.')
section('## 5.6 Conclusions','# References', '''## 5.6 Conclusions

The primary comparison shows a better classification score with fewer attack warnings: mean macro-F1 rose from 0.7148 to 0.7379 while exfiltration warning recall fell from 85.18% to 76.25%. The size depended strongly on the fitting seed. The adapted AIT test did not reproduce the original policy ordering.

The repairs have clear limits. OR retains available member warnings but covers only six of eighteen UNRAVELED episode proxies. Adding a post hoc TCP/22 policy raises coverage to eighteen, with 510 additional benign-labeled flow warnings and 460 grouped cases. The twelve recovered proxies are singleton flows from one endpoint pair. The unchanged policy adds no exfiltration coverage on AIT's UDP/53 traffic.

PX-106 makes the review question more precise. A previously wrong stage label can still warn on an attack. Count the loss if that record becomes benign. Standard binary regression accounting captures it; exact-stage regression alone does not. Report gained and lost warnings beside net recall.

The research product is a reproducible audit of sources, decisions, warnings and repair costs. Explanation checks reproduce recorded software outcomes, but added replay and the proposed ranking rule did not beat their simple controls. No human benefit or general exfiltration prevention was established. The contribution is the tested APT audit and its evidence, offered for academic review.''')
refs='''Ghiani, D., Angioni, D., Piras, G., Sotgiu, A., Minnei, L., Gupta, S., Pintor, M., Roli, F., & Biggio, B. (2026). Regression-aware continual learning for Android malware detection. *IEEE Transactions on Information Forensics and Security, 21*, 6845-6854. https://doi.org/10.1109/TIFS.2026.3714132. Inspected author version: https://arxiv.org/html/2507.18313v2

Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., & Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence, 2*, 56-67. https://doi.org/10.1038/s42256-019-0138-9

Malach, A., Wudali, P. N., Momiyama, S., Furukawa, J., Araki, T., Elovici, Y., & Shabtai, A. (2025). CyberShapley: Explanation, prioritization, and triage of cybersecurity alerts using informative graph representation. *Computers & Security, 150*, 104270. https://doi.org/10.1016/j.cose.2024.104270

Wang, X., Yang, X., Liang, X., Zhang, X., Zhang, W., & Gong, X. (2024). Combating alert fatigue with AlertPro: Context-aware alert prioritization using reinforcement learning for multi-step attack detection. *Computers & Security, 137*, 103583. https://doi.org/10.1016/j.cose.2023.103583

Yan, S., Xiong, Y., Kundu, K., Yang, S., Deng, S., Wang, M., Xia, W., & Soatto, S. (2021). Positive-congruent training: Towards regression-free model updates. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*. https://openaccess.thecvf.com/content/CVPR2021/papers/Yan_Positive-Congruent_Training_Towards_Regression-Free_Model_Updates_CVPR_2021_paper.pdf'''
a=s.index('# References')+len('# References');b=s.index('# Appendix A:',a)
entries=s[a:b].strip().split('\n\n')+refs.split('\n\n');s=s[:a]+'\n\n'+'\n\n'.join(sorted(entries,key=str.casefold))+'\n\n'+s[b:]
s=s.replace('AI-assisted agents were used for code development, computational checks, literature triage, document assembly and layout review.', 'AI assistance was used for code development, computational checks, literature searches and summaries, experiment planning, manuscript drafting and editing, document assembly and layout review. This disclosure includes substantive drafting and analysis assistance, not only spelling correction. The author must review the calculations, citations and wording and confirm the permitted scope with the adviser before submission. No AI-detector score or institutional permission is asserted.')
s+='''
# Appendix G: Plain-Language Guide and New Evidence

## G.1 The Experiment in Everyday Terms

1. Start with recorded network exchanges. The dataset authors label each record as benign or an attack stage. Those labels are the study's reference answers; they do not prove that a file was stolen.
2. Separate earlier fitting records from later testing records. Check that the requested classes and timestamps actually exist. A missing class cannot be evaluated by inventing examples.
3. Fit related LightGBM models with current-flow information and selected context. A tree model learns a series of feature-based decisions. A fitting seed changes aspects of training randomness; it does not create a new attack campaign.
4. Let each evidence policy choose which extra information to request under the same stated conditions. Save what it requested, what arrived in time, and the final model probabilities.
5. Compare policies on exactly the same test records. Count correct stage names, any attack warning, and false alerts on benign records. Inspect where each changed prediction goes.
6. Test possible repairs with saved predictions. OR keeps any member's warning. A policy rule can add a warning for a specified prohibited condition. Count their additional warnings and their limits.
7. Group flows using declared time and endpoint rules to check whether extra flow warnings cover additional activity. Report these as episode and case proxies.
8. Replay recorded decisions and check the calculations. Retain zero improvements and failed criteria. This produces a review record that another researcher can inspect.

## G.2 What Was Delivered

The research product is a model-review procedure, executable analysis, saved results and this manuscript. The procedure answers four practical questions: Did warnings disappear? Where did the software discard them? Could an existing member retain them? What additional review cases would the repair create?

The tested OR rule is simple: warn if at least one member warns. It cannot add knowledge that none of its members contains. The TCP/22 example is a separate policy warning chosen after inspecting misses. It is not proof that SSH traffic is always exfiltration or that a model learned a new attack behavior.

An explanation of a software decision can be checked without claiming a causal explanation of an attack. For example, a trace can show that evidence arrived after a deadline. It cannot, by itself, establish the attacker's intent. A review bot can check the trace's arithmetic but cannot establish that people will understand it faster.

## G.3 Evidence Map for the October 4 Review Edition

| Claim or check | Repository folder | Key records |
|---|---|---|
| Visual feasibility pilots | vlm_gate_20261002; vlm_stages_20261002 | PROTOCOL.md, RESULTS.json, raw replies |
| Recorded decisions and feature stability | explanation_trials_20261003 | PX100_RESULTS.json, PX101_RESULTS.json, audit.py |
| Ranking under case limits | warning_budget_20261003 | RESULTS.json, AUDIT.json, PROTOCOL.md |
| Deterministic reviewer test | bot_review_20261003 | FINDINGS.md, AUDIT.json |
| Trace versus trace-plus-replay | diagnosis_novelty_20261003 | RESULTS.json, AUDIT.json |
| Warning changes versus stage regression | warning_transitions_20261004 | RESULTS.json, RESULTS.csv, AUDIT.json, FREEZE.json |
| Full-text prior-work comparison | literature_review_20261004 | Comparison report; SOURCES.json |

All paths are relative to experiments/praxis_next in the project repository. Protocols distinguish frozen calculations from exposed test data. New audit checks in this revision do not convert historical exploratory results into preregistered discoveries.

## G.4 Review Status and AI Assistance

This manuscript is for author and committee review. Its structure follows the supplied GWU examples. Their findings, personal details and approvals are not adopted.

AI assistance supported planning, code, calculations, literature summaries, drafting and editing. The author must verify the work and confirm permission and disclosure requirements before submission. No writing-detector result, unaided authorship or institutional approval is claimed.
'''
write('manuscript.md',s)
write('abstract.md','''An APT stage classifier can improve its overall score while warning on fewer attacks. This praxis develops a reproducible audit of stage labels, retained attack warnings and benign false alerts on the same network-flow records. It checks chronology, source support and the software decisions that produce warnings.

In the primary UNRAVELED comparison, mean macro-F1 rose from 0.7148 to 0.7379 while exfiltration warning recall fell from 85.18% to 76.25%. Effects varied across fitting seeds. An adapted AIT test did not reproduce the original policy ordering. In one primary run, 901 exfiltration records lost their warning; 893 previously had the wrong attack-stage label. Exact-stage regression omits those losses; binary warning regression captures them.

An OR rule preserves member warnings but cannot recover events missed by all members. A post hoc TCP/22 policy raised UNRAVELED episode-proxy coverage from 6/18 to 18/18, adding 510 benign-labeled flow warnings and 460 grouped cases. It added no exfiltration coverage on AIT's UDP/53 activity. Explanation replay reproduced recorded decisions but did not outperform an ordinary complete trace. A proposed ranking rule tied confidence ranking.

The contribution is a tested audit of stage-specific warning changes and repair limits. It supports review of these laboratory pipelines. A new XAI algorithm, general operational benefit and improved human review were not established.''')
write('executive_summary.md','''# Executive Summary

**The problem.** A model can score better while hiding more attacks. Naming the wrong attack stage can still trigger an investigation. Calling the same record benign removes that warning.

**What we tested.** We compared models on the same network records and counted correct stage names, retained warnings and false alerts. We then tested rules for keeping warnings and checked their extra review cost.

**The main finding.** In one comparison, the overall score improved while exfiltration warning recall fell from about 85% to 76%. The effect varied across runs and did not repeat in the same policy order on the second data source. In one run, 893 of 901 lost warnings had previously named the wrong attack stage. A stage-only regression count overlooks that loss; a binary warning count catches it.

**What helped, and where it stopped.** OR keeps a warning if any member warns. It cannot catch something every member misses. A later TCP/22 rule recovered the missing time-defined episode groups locally, but added 460 review cases and gave no extra exfiltration coverage on the second source. Extra explanation replay and the proposed ranking rule did not beat their simple controls.

**What the Praxis delivers.** A repeatable audit that shows which warnings disappeared, which software decision caused the loss, and what a tested repair costs. Earlier papers already establish model regression and explainable security triage. This work offers specific APT evidence and a review procedure, not a first-ever XAI claim. Human benefit and committee acceptance remain untested.''')
build=(OLD/'build.py').read_text(encoding='utf-8').replace('20261001','20261004').replace('October 1, 2026','October 4, 2026').replace('Gary_Pagan_Final_Praxis','Gary_Pagan_Praxis_Review')
write('build.py',build)
print('Revision source written',len(s.split()),'words')
