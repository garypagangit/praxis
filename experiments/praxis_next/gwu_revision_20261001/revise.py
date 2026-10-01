"""Reproducible editorial revision; no experimental recomputation or fitting."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;OLD=H.parent/'gwu_final_20260928'
md=(OLD/'manuscript.md').read_text(encoding='utf-8');original=md;changes=[]
def section(number,title,text):
    global md
    pattern=rf'(?m)^## {re.escape(number)} [^\n]+\n.*?(?=^## |^# |\Z)'
    md,n=re.subn(pattern,lambda m:f'## {number} {title}\n\n{text.strip()}\n\n',md,flags=re.S)
    assert n==1,number;changes.append(number)
section('1.1','Background','''A security analyst needs to know whether an event deserves investigation. Naming the exact attack stage is useful, but calling an attack benign can hide it entirely.

Consider 100 records labeled as exfiltration. A model correctly names 60, calls 20 another attack stage, and calls 20 benign. Its exact-stage recall is 60%, while its warning recall is 80%. Both the correctly named attacks and the wrong-stage attacks still receive a warning. This is an illustration, not an experimental result.

A useful evaluation must also count false alerts on benign traffic. Warning on every record would catch every labeled attack while overwhelming an analyst. This paper therefore reports stage accuracy, missed attack warnings and benign alerts together.

Earlier work already distinguishes attack-type mistakes from attacks called normal (Uddin et al., 2025). Recent APT studies also question whether conventional scores reflect useful detection behavior (Bilot et al., 2025; Guerra et al., 2026). This praxis adds controlled measurements and a reproducible review procedure to that established problem.''')
section('1.2','Research Motivation','''A higher model score can look like a clear improvement. The decisions behind that score may tell a different story. A model can correct some attack-stage mistakes while sending other attacks into the benign class, where they receive no warning.

This study began by testing when models should use historical context and request extra evidence. Those tests revealed cases in which the overall score improved but exfiltration warnings decreased. The main question became how to expose that tradeoff before accepting a model change.

Later experiments tested possible repairs. They examined rules that preserve any member model's warning, the workload created by extra warnings, and a fixed restriction on TCP destination port 22. These follow-ups extend the evaluation; they do not replace the primary research questions or prove a generally effective detector.''')
section('1.3','Problem Statement','''**Problem statement.** An APT model can receive a better overall score while missing more attack warnings. A score alone also does not show how much benign traffic an analyst must investigate.

The purpose of this praxis is to measure those differences on the same records and provide a repeatable model-review procedure. It also checks whether each dataset has the labels and timestamps needed for the proposed test.

The practical risk is accepting a model update that sends fewer true attacks for investigation. Another risk is overstating the evidence: many related flows are not necessarily many separate incidents, and related datasets are not necessarily independent replications. This paper checks both issues.''')
section('1.4','Thesis Statement','''APT model review should examine three outcomes together: whether the model names the correct attack stage, whether it warns on the attack at all, and how many benign records it flags. The review must also check the training timeline, test population and meaning of the source labels.

The contribution is a measurement and review method supported by controlled experiments. It does not depend on inventing a new classifier. The later repair studies show why a rule that preserves warnings can still leave detection gaps or create extra work.''')
section('1.5','Research Objectives','''The objectives are to:

1. Compare overall scores, attack-stage recognition, missed warnings and benign alerts when models use different historical evidence.
2. Measure how adding later-period training records changes performance on a fixed test set with the same per-class training counts.
3. Check whether four proposed APT datasets support the requested chronological comparison with every native class represented.
4. Deliver traceable results, readable methods and a repeatable review procedure that retains unfavorable outcomes.

The later ensemble and policy studies are extensions of the first and fourth objectives. Their retrospective status is reported separately.''')
section('1.6','Research Questions and Analytical Propositions','''**RQ1, primary:** When historical-evidence choices improve an APT model's overall score, what happens to exfiltration warnings and false alarms on the same test records?

**RQ2, supporting:** How much do later-period training observations change reported performance when the model family, test records and per-class training counts stay fixed?

**RQ3, supporting:** Which proposed datasets support the requested chronological comparison with every native class represented, and what prevents the others from supporting it?

RQ1 tests whether a higher macro-F1 score can coexist with fewer warnings for an attack stage. RQ2 measures sensitivity to the training timeline and the records included in training. RQ3 checks a necessary condition: a time cutoff must leave the required examples of every class on both sides.

The original experiments fixed their protocols before training. The warning-loss pattern was identified after inspecting results. These questions describe that retrospective analysis; they are not new hypotheses registered before the pattern was known. Later studies likewise retain their original experiment numbers, freezes and failed criteria.''')
section('1.7','Scope of Research','''The main experiments use four classes from the prepared UNRAVELED flow data. History selection, evidence collection and training-time comparisons account for 141 fits. A separate technique-recognition supplement adds two fits. These numbers count model-fitting jobs, not independent attacks.

The September 27 extension checks all 173 released UNRAVELED flow files, covering 6,877,157 rows and six sensor views. It adds 12 jobs that compare current-flow features with added host roles, using all eligible training rows. It broadens coverage of the same campaign; it does not repeat every earlier intervention or supply another campaign.

The September 28 AIT extension inspects 3,465,342 source rows. It uses 2,397,158 eligible rows from six executions for final training and 1,067,211 rows from Wilson and Harrison for testing. Its 42 fits bring the recorded inventory for those evidence branches to 197 jobs. AIT uses three classes and one optional history group, so it is an adapted test rather than an exact repeat of the original experiment.

The source review also checks SCVIC-APT-2021, DAPT2020, DSRL-APT-2023 and the acquisition status of S-DAPT-2026. It does not claim four further fitted replications. CasinoLimit and CAM-LDS support a separate technique-recognition task with different negative labels.

This October 1 revision adds PX-092 through PX-097. PX-092 adds seven seed fits and PX-093 adds two logistic-regression fits. PX-094 through PX-097 reuse saved predictions without new training. Their ensemble, episode, workload and policy results are recorded separately from the earlier 197-job inventory. All these follow-ups use data already examined during the project.''')
section('1.8','Research Limitations','''The main study uses one previously examined campaign. Its movement class describes author-labeled remote discovery on one host pair, with only 35 test records and 18 records in the fixed temporal test set. Features describe completed flows, so these experiments do not measure early detection before a flow ends.

Source attack-stage labels do not independently prove successful compromise or stolen-file delivery. Many flows belong to the same activity. Changing a random fitting seed or dividing activity into time windows does not create independent incidents.

The AIT experiments hold out two executions from training, but both come from a shared laboratory generator. Their classes and available evidence differ from the original task. The original named-policy score/warning result did not repeat; a smaller tradeoff appeared in the opposite policy order on Wilson.

The latest episode counts are defined from labels, endpoints and time gaps. They are not confirmed SOC incidents. Workload uses assumed case grouping and handling times. The TCP/22 rule was chosen after examining misses, and its AIT transfer test uses previously examined executions. Neither establishes independent deployment effectiveness.''')
section('1.9','How to Read This Paper','''The executive summary gives the practical result without requiring machine-learning background. Chapter 2 explains the related research. Chapter 3 states what was tested, how the models work and how outcomes are counted. Chapter 4 presents both favorable and unfavorable results. Chapter 5 gives the review procedure, limitations and conclusions.

Readers interested in the latest repair studies can start with Sections 3.13 and 4.12-4.15. The appendices preserve detailed tables, equations, source records and reproduction instructions. A flow is one recorded network exchange; an episode groups labeled flows using an explicit time rule; an investigation case groups warnings for review. These are different units and are not used interchangeably.''')
section('2.1','Introduction','''This targeted review covers APT evaluation, training timelines, attack-stage errors and dataset origins. The initial review was completed September 23, 2026 and extended September 28 for AIT. The October 1 revision also uses the ensemble and policy claim checks recorded with PX-093 and PX-096. It is not an exhaustive literature review or proof of priority.

The question is what this study measures beyond established work. Temporal evaluation, attacks mislabeled as benign, classifier combination and network filtering already have substantial prior work. The contribution must rest on the specific controlled comparisons and their practical interpretation.''')
section('2.8','Literature Review Summary','''Earlier research shows that training time, source labels and the kinds of mistakes a model makes matter in security evaluation. This study uses established metrics to examine those issues together on specific flow datasets.

Its contribution is the controlled comparison and reusable audit: test the same records, count attacks called benign, show the false-alert cost and verify that the source supports the question. The ensemble and TCP/22 follow-ups do not make classifier voting or port filtering new methods. Their value is showing what those rules recover, what they miss and what extra work they create.''')
section('5.1','What the Results Mean','''A better overall score does not guarantee that fewer attacks pass without a warning. The primary experiment demonstrates that difference on the same test records. The training-time experiment also shows that scores can change when later records enter training, even with the model family and test set fixed.

The AIT extension limits how widely the primary result can be applied. The original policy ordering did not repeat on either held-out execution. Wilson showed a much smaller tradeoff in the opposite ordering; Harrison improved both score and warning recall. The amount of evidence requested also differed, so these policies were not compared at equal realized spending.

The later repairs add a second lesson: retaining more flow warnings does not necessarily cover another attack episode. Extra models recovered some flows but no additional episode proxies in PX-094. The TCP/22 rule recovered the twelve missing UNRAVELED proxies, but none of AIT's exfiltration flows used that port. A policy works on the traffic it covers; its presence does not prove general detection capability.''')
section('5.2','Contributions','''The main contribution is a reproducible comparison of stage accuracy, missed attack warnings and benign alerts on the same records. The paper retains favorable, unfavorable and unchanged results, and shows how strongly some differences depend on the fitting seed.

The supporting contributions are a fixed-test-set comparison of training composition and an executable check of dataset labels, timing and source relationships. The complete AIT extension adds an adapted test on executions excluded from fitting, including the failure to reproduce the original named-policy result.

PX-092 through PX-097 extend the review from scores to warning combination, episode coverage and policy scope. They show a useful local repair and an explicit transfer limit. They also reveal why twelve missing time-defined episodes cannot be read as twelve independent theft incidents.

These are applied measurement and engineering contributions. The work does not claim a new metric, a new OR rule, a novel firewall policy or proof that one intervention is the only possible repair.''')
section('5.5','Next Research Steps','''The next validation should define the policy and permitted exceptions before examining test labels, then use untouched executions containing legitimate administration and attacks on more than one channel. It should keep model warnings, policy violations and attack-stage predictions separate.

For the twelve UNRAVELED singleton proxies, packet/session records or attack-execution evidence would help establish what activity the labels represent. If available, host/process, file-access and completed-session evidence could provide information that the existing flow features lack. This paper does not claim those signals have already repaired the misses.

An exact four-class, two-evidence-group replication and unrelated campaigns remain needed. AIT supplies a different three-class test. More models alone cannot fill that evidence gap.

An operational study would need measured case handling and analyst decisions. It could test whether the combined report changes model-review choices or improves timely investigation. Simulated service time cannot replace that evidence.

Earlier source intake does not fill that gap. Sandworm lacks a native exfiltration flow class. The CAM-LDS check linked 3,332 flows to four T1041 actions ambiguously, with several candidate flows per action. Verified legitimate-user labels, untouched executions and a verified complete-archive checksum remain absent.''')
section('5.6','Conclusions','''The primary result is straightforward: a better APT classification score can hide more missed attack warnings. In the observed evidence-collection comparison, mean macro-F1 rose from 0.7148 to 0.7379 while exfiltration warning recall fell from 85.18% to 76.25%. The average direction survived the reported single-seed and single-capture omissions, but its size depended strongly on the fitting seed.

The broader evidence sets clear limits. The full-release study covers all 6,877,157 UNRAVELED rows but remains one campaign. The AIT extension tests a different configuration on two later executions and does not reproduce the original policy ordering. These outcomes support joint reporting rather than a claim that one model or evidence policy always wins.

The follow-up repairs make the same point at a different level. Original OR retains any constituent warning, but warns on only six of eighteen UNRAVELED episode proxies. Adding a TCP/22 policy raises that to eighteen, while adding 510 benign-labeled flow warnings and 460 grouped cases. Those twelve recovered proxies are singleton flows from one endpoint pair. On AIT, all labeled exfiltration uses UDP/53, so the unchanged TCP/22 rule adds no exfiltration coverage.

The practical procedure is to check the source and timeline, compare the same records, count retained warnings and benign workload, and test coverage on other executions. Enforce mandatory policies explicitly. The result is an evaluation method and a local warning repair; universal exfiltration prevention remains unproven.''')
# Simplify recurrent terminology in prose only. Tables, equations and references remain intact.
parts=md.split('# References',1);body=parts[0]
terms={'stage-conditioned warning recall':'warning recall for each attack stage','evidentiary status':'limits on what they establish','evaluation anchor':'fixed test set','fitting observations':'training observations','conditional resampling intervals':'resampling intervals for these captures','source semantics':'meaning of the source labels','native taxonomy':'source class definitions','consequential subset':'important subset'}
blocks=body.split('\n\n')
for i,b in enumerate(blocks):
    if b.lstrip().startswith(('|','$','!','```','#')):continue
    for a,v in terms.items():b=b.replace(a,v)
    blocks[i]=b
md='\n\n'.join(blocks)+'# References'+parts[1]
# Explain dense sections before their detailed methods.
guides={
'## 3.4 Evaluation Anchor and Temporal Controls':'In plain terms, this test keeps the test records fixed and changes which records the model may use for training. That lets the comparison measure the effect of the training pool without also changing the test population.',
'## 3.5 Historical-Evidence and Acquisition Interventions':'These experiments ask whether extra context helps enough to justify using it. Some runs choose whether to use history; others choose which evidence to request under a simulated budget. A selector is the small model that makes that choice.',
'## 3.7 Stage, Warning and Workload Metrics':'Read the metrics as three questions: Did the model name the correct stage? Did it warn at all? How many benign records did it flag? The formulas below define those counts precisely.',
'## 3.8 Paired Reanalysis, Uncertainty and Sensitivity':'Each comparison uses the same records for both policies. The sensitivity checks ask whether the reported difference changes when a fitting seed or capture fragment is omitted. They describe this dataset; they do not turn related flows into independent campaigns.',
'## 3.9 Necessary Chronological-Support Test':'Before training, check whether a single time cutoff can leave enough examples of every required class in both training and testing. If not, the requested test cannot be performed as written.',
'## 3.12 Adapted External-Execution Validation on AIT':'AIT asks whether the observation also appears on another source. Its labels and available features differ from UNRAVELED, so the experiment states those changes before interpreting its results.',
'## 4.1 Primary Finding: Overall Scores and Missed Exfiltration Warnings':'The main result is a tradeoff: the error-focused policy scores better overall but warns on fewer exfiltration records. The tables show the size of that tradeoff, its false-alert cost and its variation across runs.',
'## 4.10 Full-Release Results and Calibration Review':'This extension checks whether the host-role comparison holds when all eligible training records and all six released sensor views are used. It broadens coverage of the same campaign, not the number of independent campaigns.',
'## 4.11 Adapted AIT Validation Results':'The original named-policy result did not repeat on AIT. A smaller tradeoff appeared in the opposite policy order on Wilson. Both outcomes are retained.'}
for a,b in guides.items():assert md.count(a)==1;md=md.replace(a,a+'\n\n'+b,1)
md=md.replace('| New warning-destination loss or a guard against attack-to-benign changes | Possible future work; no performance result claimed |','| New warning-destination loss or a guard against attack-to-benign changes | Not evaluated in PX080-PX083; later warning gates and policy overlays are reported in Sections 3.13 and 4.12-4.15 |')
md=md.replace('| AIT external-source validation | 8 executions; 3,465,342 rows; 42 fits | Three-class history acquisition; 2 later executions held out |','| AIT external-source validation | 8 executions; 3,465,342 rows; 42 fits | Three-class history acquisition; 2 later executions held out |\n| PX-092 and PX-093 | Seven additional seed fits and two logistic-regression fits | Warning combinations and added-member workload |\n| PX-094 through PX-097 | Saved predictions; no new fits | Episode proxies, case workload, missed-flow diagnosis and fixed policy replay |')
md=md.replace('| Workload | Benign false-alert count/rate, population, operating rule | Whether warning retention adds investigation burden |','| Workload | Benign false-alert count/rate, grouped cases and explicit handling-time assumptions | Whether extra warnings create more review work |\n| Episode support | Flow count, grouping rule, episode coverage and confirmed incident IDs if available | Whether extra flow warnings cover additional activity |\n| Policy scope | Observable rule, approved exceptions, covered channels and test exposure | What a deterministic policy protects and what it leaves untested |')
method=(H/'new_methods.md').read_text(encoding='utf-8');results=(H/'new_results.md').read_text(encoding='utf-8')
md=md.replace('# Chapter 4: Results',method+'\n\n# Chapter 4: Results',1)
md=md.replace('# Chapter 5: Discussion and Conclusions',results+'\n\n# Chapter 5: Discussion and Conclusions',1)
md=md.replace('## 5.4.5 Scope of the finished manuscript','### 5.4.5 Scope of the finished manuscript') if '\n## 5.4.5' in md else md
anchor='## 5.5 Next Research Steps'
md=md.replace(anchor,'''### 5.4.7 Limits of the repair studies

PX-092 through PX-097 use previously examined data. Their source and code freezes preserve the comparisons but do not make those data fresh validation. PX-092's required improvement over the best individual member in both AIT executions failed. PX-093's combined benefit-and-workload criteria also failed. The OR rule only preserves warnings available from its members; it cannot recover an event that all members call benign without changing their decisions or adding information.

An episode proxy is not a confirmed incident. PX-095 traced the twelve wholly missed UNRAVELED proxies to twelve flows from one endpoint pair, eleven containing only two packets. The assumed analyst service times in PX-094 were not measured. The blanket TCP/22 scenario has no verified organizational allowlist or egress boundary. A benign attack label and a policy violation answer different questions. Neither replay proves that a real firewall prevented a transfer.

'''+anchor,1)
md+='\n\n'+(H/'appendix_f.md').read_text(encoding='utf-8')
prefix,tail=md.split('# References\n',1);refs,appendices=tail.split('# Appendix A:',1)
added_refs=[
'Brabec, J., & Machlica, L. (2018). Decision-forest voting scheme for classification of rare classes in network intrusion detection. *2018 IEEE International Conference on Systems, Man, and Cybernetics*. https://doi.org/10.1109/SMC.2018.00563. Author manuscript: https://arxiv.org/abs/2107.11862',
'Kittler, J., Hatef, M., Duin, R. P. W., & Matas, J. (1998). On combining classifiers. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 20*(3), 226-239. https://doi.org/10.1109/34.667881',
'Kuncheva, L. I., & Whitaker, C. J. (2003). Measures of diversity in classifier ensembles and their relationship with the ensemble accuracy. *Machine Learning, 51*(2), 181-207. https://doi.org/10.1023/A:1022859003006',
'MITRE. (2026). *Filter network traffic (M1037), version 1.2*. MITRE ATT&CK. Updated May 12, 2026; reviewed October 1, 2026. https://attack.mitre.org/mitigations/M1037/'
]
md=prefix+'# References\n\n'+'\n\n'.join(sorted([r.strip() for r in refs.strip().split('\n\n') if r.strip()]+added_refs))+'\n\n# Appendix A:'+appendices
# Reuse original reviewed figures without copying or changing evidence assets.
md=re.sub(r'\]\((figures/|results/|reference/)',r'](../gwu_final_20260928/\1',md)
(H/'manuscript.md').write_text(md,encoding='utf-8')
def stats(s):
    main=s.split('# References',1)[0];prose=' '.join(b for b in main.split('\n\n') if not b.lstrip().startswith(('|','$','!','```','#')));sent=re.split(r'(?<=[.!?])\s+',prose);lengths=[len(re.findall(r"\b[\w'-]+\b",x)) for x in sent if x.strip()]
    return {'prose_sentences':len(lengths),'mean_words_per_sentence':round(sum(lengths)/len(lengths),2),'sentences_over_35_words':sum(n>35 for n in lengths)}
save={'source':str(OLD/'manuscript.md'),'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'revised_sha256':hashlib.sha256(md.encode()).hexdigest(),'rewritten_sections':changes,'plain_language_guides':list(guides),'before_prose':stats(original),'after_prose':stats(md),'note':'Readability counts are descriptive; equations, result tables and source-label meanings remain authoritative.'}
(H/'EDITORIAL_RECEIPT.json').write_text(json.dumps(save,indent=2)+'\n');print(json.dumps(save,indent=2))
