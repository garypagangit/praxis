"""Compose a findings-led revision from unchanged audited evidence.

This changes interpretation emphasis and adds descriptive paired arithmetic.
It does not fit models, change thresholds, or replace the original decision.
"""
from pathlib import Path
from datetime import datetime, timezone
from statistics import fmean
import json
import hashlib
import re
import assemble_manuscript as original

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent.parent / 'results/lateral_protection_v1'
PRIOR = HERE.parent.parent / 'results/strong_benign_controls_v1/SUMMARY.json'
TITLE = 'Improving APT Alert Efficiency: Measured Gains and Lateral-Movement Tradeoffs'


def section(text, begin, end):
    assert text.count(begin) == text.count(end) == 1, (begin, end)
    return text.split(begin, 1)[1].split(end, 1)[0].strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pct(x, digits=2):
    return f'{100*x:.{digits}f}%'


def table(headers, rows):
    return original.table(headers, rows) + '\n\n'


def compose():
    e, s, cells, audit, ext, software, diag, protocol = original.validate_package(
        RESULTS, RESULTS/'DIAGNOSTICS.json', HERE.parent/'SOFTWARE_VALIDATION.json')
    old = (HERE/'PRAXIS.md').read_text(encoding='utf-8')
    old_review = json.loads((HERE/'MANUSCRIPT_REVIEW.json').read_text())
    assert digest(HERE/'PRAXIS.md') == old_review['manuscript_sha256']
    prior = json.loads(PRIOR.read_text())
    assert prior['audit_status'] == 'PASS'
    small = prior['models']['cv_selected_gbdt']['equal_32_per_class']['mean']
    large = prior['models']['cv_selected_gbdt']['abundant_benign_1024']['mean']
    matched = e['matched_feasible_aggregates']['1024']['verification']
    ref, candidate = matched['reference'], matched['candidate']
    threshold, ordinary = matched['cv_natural_benign_threshold'], matched['cv_natural_argmax']
    assert all(v['seeds'] == ref['seeds'] for v in matched.values())
    assert len(ref['seeds']) == 6 and s['primary_gate']['status'] == 'INFEASIBLE'
    reduction = 100*(1-candidate['benign_fpr']/ref['benign_fpr'])
    benign_gain = 100*(1-large['normal_fpr']/small['normal_fpr'])
    dual_gain = 100*(1-ref['benign_fpr']/threshold['benign_fpr'])
    dual_lateral = 100*(ref['stage_recall']['LateralMovement']-threshold['stage_recall']['LateralMovement'])
    names = {'reference':'Lateral-sensitive reference', 'candidate':'Low-false-alarm candidate',
        'threshold_only':'Threshold-only alternative', 'cv_natural_argmax':'Ordinary natural tree',
        'cv_natural_benign_threshold':'Source-normal 1% threshold'}
    order = ['cv_natural_argmax','cv_natural_benign_threshold','reference','threshold_only','candidate']
    front = f'''# {TITLE}

## An empirical praxis on benign training coverage, alert policies, and attack-stage visibility

**Completed findings synthesis - September 21, 2026.** The measured improvements and their detection costs are reported together. Original models, thresholds, data splits, and scientific receipts are unchanged.

**Evidence scope:** Previously examined SCVIC development data; 152 completed final models in the new experiment; a qualified DEDALE stress test of ordinary controls. This revised emphasis was developed after the results were known. The original investigator-chosen joint screen remains INFEASIBLE.

## Abstract

Security detectors need to reduce unnecessary alerts without obscuring the attack behaviors that matter. This praxis measures how benign fitting coverage, training weights, and alert thresholds change that tradeoff in APT-labeled network flows. An earlier ten-seed SCVIC comparison increased benign fitting examples from 32 to 1,024 while retaining the same 160 attack fitting examples within each seed. Mean false-positive rate fell from {pct(small['normal_fpr'])} to {pct(large['normal_fpr'])}, a {benign_gain:.2f}% relative reduction, and six-class macro-F1 increased from {small['macro_f1']:.4f} to {large['macro_f1']:.4f}; lateral-flow detection also declined from {pct(small['binary_detection_by_stage']['LateralMovement'])} to {pct(large['binary_detection_by_stage']['LateralMovement'])}. The subsequent experiment completed 152 final models across 19 support groups. On the same six primary supports with selected policies, the low-false-alarm candidate reduced false positives by {reduction:.1f}% and increased binary attack F1 from {ref['attack_f1']:.4f} to {candidate['attack_f1']:.4f}, while lateral detection changed from {pct(ref['stage_recall']['LateralMovement'])} to {pct(candidate['stage_recall']['LateralMovement'])}. A further exploratory matched-subset comparison found {dual_gain:.1f}% fewer false positives and a {dual_lateral:.2f}-percentage-point higher mean lateral recall for the lateral-sensitive reference, selected using lateral-labeled data, than for the ordinary source-normal threshold; this small gain was not consistent across seeds or all stages. Four primary supports supplied no qualifying policy, so the original self-imposed 90%-recall/1%-false-positive joint screen remained unmet. DEDALE evaluated ordinary controls only on four lateral flows from one execution. The contribution is reproducible evidence linking false-alarm gains to stage-specific costs under explicit label budgets. It partially addresses a literature-motivated empirical question about richer benign support; it does not establish a new algorithm, guaranteed preservation, or deployment utility.

**Keywords:** intrusion detection; lateral movement; benign training data; false alarms; class weighting; alert thresholds; empirical evaluation

## Executive explanation

**There are positive findings.** The experiment is more informative than a single pass/fail label. More examples of normal traffic produced substantially fewer false alarms and a better overall classification score. Changing how the fitted models were used also produced favorable comparisons. Those improvements came with different detection costs, which are part of the result.

| Question | Measured benefit | Companion finding |
| --- | --- | --- |
| What did more benign examples achieve? | {benign_gain:.2f}% fewer false positives; macro-F1 {small['macro_f1']:.4f} to {large['macro_f1']:.4f}. | Ten earlier paired fitting seeds; lateral detection {pct(small['binary_detection_by_stage']['LateralMovement'])} to {pct(large['binary_detection_by_stage']['LateralMovement'])}; 992 additional benign labels per fit. |
| What did the low-false-alarm candidate achieve? | {reduction:.1f}% fewer false positives; attack F1 {ref['attack_f1']:.4f} to {candidate['attack_f1']:.4f}. | Same six selected supports; lateral detection {pct(ref['stage_recall']['LateralMovement'])} to {pct(candidate['stage_recall']['LateralMovement'])}. |
| Was there any paired improvement in both false alarms and lateral detection? | The lateral-sensitive reference had {dual_gain:.1f}% fewer false positives and mean lateral recall {dual_lateral:.2f} percentage points higher than the source-normal threshold. | Exploratory six-support comparison; only two supports improved both measures, and some other stages declined. |

The 90% detection floor was selected for this study. It was not a literature-established safety boundary or a requirement from an organization. The other numerical screen values were also investigator choices. Keeping their original outcome preserves the research record; it does not erase improvements in the observed measurements.

The practical contribution is a way to report what a quieter detector buys and what it gives up. The paper connects this evidence to published calls for richer benign support, reports the fitting and selection information used by each comparison, and identifies which conclusions still need independent attack executions. No reduction in analyst hours or successful new protection algorithm was measured.

'''
    ch1 = (HERE/'FINDINGS_INTRODUCTION.md').read_text(encoding='utf-8')+'\n\n'
    ch2 = '# Chapter 2. Literature and the empirical gap\n\n'+section(old,'# Chapter 2. Literature and conceptual basis','# Chapter 3. Research methodology')+'\n\n'
    ch2 = ch2.replace('The supporting review prioritized', 'The review was refreshed on September 21, 2026. The supporting review prioritized')
    ch2 = ch2.replace('The [literature research note]', 'The current [gap review](FINDINGS_LITERATURE_GAP.md) documents additional checks. The [earlier literature research note]')
    insertion = '''Bae et al. (2026) already combine large benign audit-log pretraining with few-shot attack learning in DUPIN. Its publication is verified in the official USENIX Security 2026 proceedings. Li et al. (2026) use potential entity relations for few-shot APT recognition in APMP. An earlier author preprint also applies class-weighted XGBoost to lateral movement (Kushwaha et al., 2022). These sources further limit broad novelty claims. Their provenance/entity representations and information budgets differ from our supervised flow study; none was a head-to-head baseline in this experiment. [DUPIN proceedings](https://www.usenix.org/conference/usenixsecurity26/presentation/bae); [APMP primary paper](https://doi.org/10.1186/s42400-026-00592-5); [earlier weighting preprint](https://doi.org/10.48550/arXiv.2208.13524).

'''
    ch2 = ch2.replace('## 2.5 Data and evidence quality',insertion+'## 2.5 Data and evidence quality')
    ch2 = ch2.split('## 2.6 Synthesis and defensible gap')[0]+'''## 2.6 The gap this praxis partially addresses

The relevant empirical question is how much false-alarm improvement richer benign fitting data produces, which attack stages change alongside it, and how much of a later policy gain can be achieved by moving the same detector's threshold. The scope here is fixed attack fitting identities, nested benign supports, identical-row weighting, and locked verification. This is an applied extension of established ideas, not a claim that these topics have never been studied.

| Literature connection | Question addressed in this study | Boundary |
| --- | --- | --- |
| Revell et al. propose larger benign support. | Measure benign-support gains together with lateral and other-stage costs. | Supervised trees on SCVIC; not a replication of their meta-learners. |
| Smiliotopoulos and Kambourakis examine lateral imbalance and both error types. | Report every declared weighting arm on the same rows and fitting seeds. | Different representation; no unverified omission is attributed to their full methods. |
| Singhal and Kumar combine weights and constrained thresholds. | Compare a selected policy with its threshold-only alternative under matched information. | Established components; no new risk guarantee. |
| DUPIN uses abundant benign information with few attack labels. | Account explicitly for the smaller supervised fitting budget and all additional label access. | No claim to originate the abundant-benign idea or outperform DUPIN. |

The gap is critical to the decision being made: a larger overall score is insufficient to explain whether a rare attack step became less visible. The completed evidence provides that missing account for this tested setting. It does not establish a field-wide absence of such evaluations. The present contribution is supported by the actual comparisons, while broader originality remains bounded by the review and the institution's requirements.

'''
    ch3 = '# Chapter 3. Research methodology\n\n'+section(old,'# Chapter 3. Research methodology','# Chapter 4. Results')+'\n\n'
    ch3 = ch3.replace('## 3.1 Design and completed execution','''## 3.0 Original design and later synthesis

The original design was fixed before the new model fits. This paper's emphasis on measured gains is a later descriptive synthesis. It preserves all selected and infeasible supports and all original requirements. No evaluation label was used to revise a model or threshold for this paper. Favorable additional contrasts are not presented as newly successful prespecified hypotheses.

The earlier benign-support comparison uses the original development test, whereas the new main policy comparisons use the verification half of the old calibration partition. Rates from these roles are not pooled. The complete prepared data were previously exposed in research, so neither role supplies untouched confirmation.

## 3.1 Design and completed execution''')
    ch3 = ch3.replace('The two improvement inequalities are strict.', '''The 90% recall floor, 1% false-positive ceiling, 20% reduction target, three-point loss margin, and requirement for ten feasible supports were investigator-selected development requirements. No cited paper or documented stakeholder process establishes these exact values as universally acceptable. They were chosen to make the test demanding and explicit. Their original result is retained even though this synthesis asks what component improvements occurred.

The two improvement inequalities are strict.''')
    ch3 = ch3.replace('Exact parameter dictionaries are retained in the protocol', 'Exact parameter grids are bound through the protocol and its source-hashed backend')
    ch4 = '# Chapter 4. Actual findings\n\n## 4.1 More benign fitting data improved false alarms and overall classification\n\n'
    ch4 += 'This earlier comparison averages all ten fitting seeds on the same original development test: 29,929 benign and 144 lateral flows, within 30,787 total flows. Attack fitting identities remained fixed within each seed. It is the motivating result, not an outcome newly produced by the 152-model experiment (Praxis experiment repository, 2026).\n\n'
    ch4 += table(['Measure','32 benign + 160 attack labels','1,024 benign + same 160 attack labels'],[
        ['Mean benign false-positive rate',pct(small['normal_fpr'],3),pct(large['normal_fpr'],3)],
        ['Mean benign flags / 29,929',f"{29929*small['normal_fpr']:.1f}",f"{29929*large['normal_fpr']:.1f}"],
        ['Six-class macro-F1',f"{small['macro_f1']:.4f}",f"{large['macro_f1']:.4f}"],
        ['All-attack detection',pct(small['binary_attack_recall']),pct(large['binary_attack_recall'])],
        ['Lateral flows detected as any attack',pct(small['binary_detection_by_stage']['LateralMovement']),pct(large['binary_detection_by_stage']['LateralMovement'])],
        ['Lateral flows assigned correct stage',pct(small['exact_stage_recall']['LateralMovement']),pct(large['exact_stage_recall']['LateralMovement'])]])
    ch4 += f"The positive gain was a {benign_gain:.2f}% relative false-positive reduction and a {large['macro_f1']-small['macro_f1']:.4f} increase in macro-F1. The lateral cost was {100*(small['binary_detection_by_stage']['LateralMovement']-large['binary_detection_by_stage']['LateralMovement']):.2f} percentage points, or approximately {144*(small['binary_detection_by_stage']['LateralMovement']-large['binary_detection_by_stage']['LateralMovement']):.1f} fewer detected lateral flows per repeated-fit mean. More benign coverage, changed class proportions, support size, and model selection changed together; the experiment does not isolate a causal diversity effect. [Audited earlier comparison](../../results/strong_benign_controls_v1/SUMMARY.json).\n\n"
    ch4 += '## 4.2 Policy improvements on the same six selected supports\n\nAll five rows below use exactly the same six fitting seeds: '+', '.join(map(str,ref['seeds']))+'. Each is evaluated on 14,965 benign flows and 72 lateral flows within the same 15,392-row verification partition. The other four primary supports had no selected constrained policy and remain visible in Section 4.6. These are conditional descriptive comparisons.\n\n'
    ch4 += table(['Policy','Mean benign flags','Benign FPR','Mean lateral flags','Lateral recall'],[[names[n],f"{matched[n]['fp']:.1f}",pct(matched[n]['benign_fpr'],3),f"{matched[n]['stage_detected']['LateralMovement']:.1f}",pct(matched[n]['stage_recall']['LateralMovement'],3)] for n in order])
    ch4 += table(['Policy','Attack precision','Attack recall','Attack F1','Attack ROC-AUC','Attack AP'],[[names[n],pct(matched[n]['attack_precision']),pct(matched[n]['attack_recall']),f"{matched[n]['attack_f1']:.4f}",f"{matched[n]['roc_auc']:.4f}",f"{matched[n]['average_precision']:.4f}"] for n in order])
    ch4 += f'''**Candidate versus lateral-sensitive reference.** False alarms declined {reduction:.2f}% and attack F1 increased from {ref['attack_f1']:.4f} to {candidate['attack_f1']:.4f}. Alert precision increased from {pct(ref['attack_precision'])} to {pct(candidate['attack_precision'])}. Lateral recall declined from {pct(ref['stage_recall']['LateralMovement'])} to {pct(candidate['stage_recall']['LateralMovement'])}, a {100*(ref['stage_recall']['LateralMovement']-candidate['stage_recall']['LateralMovement']):.2f}-point loss. On the fixed verification sample, the mean reduction was {ref['fp']-candidate['fp']:.1f} benign flags with {ref['stage_detected']['LateralMovement']-candidate['stage_detected']['LateralMovement']:.2f} fewer lateral flags. These counts describe flows, not analyst cases or unique incidents.

**Candidate versus ordinary natural tree.** Lateral recall increased from {pct(ordinary['stage_recall']['LateralMovement'])} to {pct(candidate['stage_recall']['LateralMovement'])}, a {100*(candidate['stage_recall']['LateralMovement']-ordinary['stage_recall']['LateralMovement']):.2f}-point gain. False-positive rate increased from {pct(ordinary['benign_fpr'],3)} to {pct(candidate['benign_fpr'],3)}. This comparison shows why a method can be better at one operational objective and worse at another. It is not the same reference comparison as the preceding paragraph.

**Exploratory reference versus source-normal threshold.** The lateral-sensitive reference had {dual_gain:.2f}% fewer false positives and mean lateral recall {dual_lateral:.3f} points higher. False positives improved in five seeds and worsened in one; lateral detection improved in two, tied in one, and worsened in three. Only two seeds improved both. Exfiltration, pivoting, and reconnaissance mean detection declined slightly, and all-attack recall declined from {pct(threshold['attack_recall'],3)} to {pct(ref['attack_recall'],3)}. This is a small, selected-subset gain in two averages, not consistent superiority or statistically confirmed lateral improvement. The reference used labeled lateral examples during policy selection, whereas the ordinary threshold used only selection-normal labels. This comparison does not isolate algorithm quality from that extra selection information.

The independent arithmetic review records every contrast and its stage costs in [FINDINGS_ACTUALS.json](FINDINGS_ACTUALS.json). The expanded interpretation is post-result. No confidence interval or statistical significance is inferred from repeated fitting on the same verification observations.

'''
    ch4 += '## 4.3 Training emphasis improved lateral detection at different false-alarm costs\n\nThe following table includes every declared model/weight combination and all ten primary seeds, regardless of policy feasibility. Each row uses 1,024 benign and the same 160 attack fitting examples within a seed. These are the classifiers\' ordinary maximum-probability decisions; they do not use the selected candidate thresholds.\n\n'
    model_rows=[]
    for model in original.MODELS:
        for scheme in original.SCHEMES:
            found=[c['metrics']['verification'] for c in cells if c['budget']==1024 and c['cell_id']==model+'/'+scheme]
            assert len(found)==10
            model_rows.append([model+'/'+scheme,pct(fmean(x['argmax_alert']['benign_fpr'] for x in found),3),pct(fmean(x['argmax_alert']['per_stage']['LateralMovement']['recall'] for x in found)),f"{fmean(x['classification']['macro_f1'] for x in found):.4f}",pct(fmean(x['classification']['per_stage']['LateralMovement']['recall'] for x in found))])
    ch4 += table(['Model / weights','Benign FPR','Lateral alert recall','Six-class macro-F1','Exact lateral-stage recall'],model_rows)
    ch4 += 'Balanced LightGBM increased lateral alert recall from 78.89% to 84.58%, with FPR increasing from 0.378% to 0.611% and macro-F1 decreasing from 0.6395 to 0.6123. XGBoost with fourfold lateral emphasis increased lateral alert recall from 76.81% to 87.92%, with FPR increasing from 0.303% to 1.286%. These favorable lateral changes are descriptive contrasts within the full reported family; the paper does not select one after evaluation and certify it as the best deployment model. Exact-stage recall is lower than any-attack alert recall because assigning the correct stage is a harder, different task. Appendix E retains all classes and ranking metrics.\n\n'
    ch4 += '## 4.4 What the threshold-only comparison adds\n\n'+section(old,'## 4.5 Threshold-only ablation and selected detectors','## 4.6 Secondary normal-label budgets')+'\n\n'
    ablation=matched['threshold_only']
    ch4 += f"Across the same six supports, the candidate had {100*(1-candidate['benign_fpr']/ablation['benign_fpr']):.2f}% fewer false positives than threshold-only, with mean lateral recall {100*(ablation['stage_recall']['LateralMovement']-candidate['stage_recall']['LateralMovement']):.3f} points lower. Four identical choices mean the extra detector search added nothing in those four supports. The remaining difference is informative, but it does not establish a broadly superior learning method.\n\n"
    ch4 += '## 4.5 Detection at every attack stage\n\nAll policies below use the same six selected supports. Each entry is the percentage of true stage-labeled flows that raised any attack alert. Denominators are 53 exfiltration, seven initial-compromise, 72 lateral, 212 pivoting, and 83 reconnaissance flows per seed. The very small initial-compromise group limits interpretation.\n\n'
    ch4 += table(['Policy','Exfiltration','Initial','Lateral','Pivoting','Recon.'],[[names[n]]+[pct(matched[n]['stage_recall'][k]) for k in original.STAGES] for n in order])
    ch4 += '## 4.6 What the original engineering screen found\n\n'+section(old,'## 4.1 Completion, audit, and primary decision','## 4.2 Every primary fitting seed')+'\n\n'
    ch4 = ch4.replace('The primary scientific decision was **INFEASIBLE**','The recorded joint engineering-screen decision was **INFEASIBLE**')
    ch4 += 'The 90% requirement and the other numerical limits were investigator-chosen. A result below 90% is not automatically useless, just as a result above it is not automatically safe. This study has no stakeholder utility calculation establishing either conclusion. The positive metric changes and the unmet original requirement are both retained.\n\n'
    ch4 += section(old,'## 4.2 Every primary fitting seed','## 4.3 Operating outcomes and the feasible-subset boundary')+'\n\n'
    ch4 += '### Selection-only description of the attainable operating points\n\n'+section(old,'## 4.9 Posthoc selection-frontier diagnostics','## 4.10 DEDALE external stress: conventional controls only')+'\n\n'
    ch4 += '## 4.7 Secondary budgets and exposed test\n\n'+section(old,'## 4.6 Secondary normal-label budgets','### 32 normal fitting examples')+'\n\n'
    ch4 += 'All three secondary budgets retained infeasible supports under their declared screens. This does not negate the individual false-alarm or detection changes; it bounds reliability under the chosen joint rule. Appendix F provides the detailed secondary-policy results and the original exposed-test outcomes, with their separate seed counts. They are not used to choose a better-looking primary result.\n\n'
    ch4 += '## 4.8 DEDALE external stress\n\n'+section(old,'## 4.10 DEDALE external stress: conventional controls only','# Chapter 5. Discussion and conclusion')+'\n\n'
    ch5=(HERE/'FINDINGS_DISCUSSION.md').read_text(encoding='utf-8')+'\n\n'
    references='# References\n\n'+section(old,'# References','# Appendix A. Software and execution accounting')+'\n\n'
    refs_new=[
        ('Bilot, T.', 'Bae, C., Ding, H., Ma, S., & Zhang, X. (2026). DUPIN: Attack learning is still needed! Demonstrating few-shot after unsupervised pretraining is a nimble forensics learner. In *35th USENIX Security Symposium (USENIX Security 26)* (pp. 2287-2306). USENIX Association. https://www.usenix.org/conference/usenixsecurity26/presentation/bae'),
        ('Lanvin, M.', 'Kushwaha, D., Nandakumar, D., Kakkar, A., Gupta, S., Choi, K., Redino, C., Rahman, A., Chandramohan, S. S., Bowen, E., Weeks, M., Shaha, A., & Nehila, J. (2022). *Lateral movement detection using user behavioral analysis* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2208.13524'),
        ('Liu, J.', 'Li, J., Li, T., Zhang, R., Wan, Z., & Yang, Z. (2026). Apmp: APT attack detection in few-shot scenarios based on entity potential relations. *Cybersecurity, 9*, Article 172. https://doi.org/10.1186/s42400-026-00592-5')]
    for before,entry in refs_new:
        assert references.count(before)==1
        references=references.replace(before,entry+'\n\n'+before)
    references=references.replace('Layman and Roden is labeled as a preprint.','Layman and Roden and Kushwaha et al. are labeled as preprints. DUPIN is verified in the official 2026 USENIX proceedings; APMP is verified through the journal publisher.')
    appendix='# Appendix A. Software and execution accounting\n\n'+section(old,'# Appendix A. Software and execution accounting','# Appendix D. Concrete prospective confirmation design')+'\n\n'
    appendix += '''# Appendix D. Next study with justified operational requirements

Future work should use independent lateral executions and realistic legitimate remote-administration background. Split complete executions or campaigns, rather than correlated flows, into development and confirmation groups. Give each comparator the same label and search information; include ordinary natural and balanced trees, threshold-only selection, and an appropriately implemented established constrained procedure.

Before examining new confirmation outcomes, determine the intended review capacity and relative consequences of missed activity with the intended users. Choose and justify any recall floor, false-alert budget, or allowable loss from that use case. The earlier 90%/1%/three-point/20% values need not be reused, but changing them creates a new question and cannot alter the original recorded outcome. Publish descriptive operating curves and the selected requirement, including the number of independent units supporting each estimate.

Plan uncertainty estimates and sample size around independent incidents, paired errors, and temporal or network variation. A very small lateral sample cannot support a precise protection claim. Measure actual grouped analyst alerts and investigation time if the eventual claim concerns workload. A new flow-level score alone does not provide those observations.

'''
    appendix += '# Appendix E. Exact-stage classification for every primary final cell\n\n'+old.split('# Appendix E. Exact-stage classification for every primary final cell',1)[1].strip()+'\n\n'
    appendix += '# Appendix F. Supplementary secondary and exposed-test outcomes\n\nThese tables retain all secondary supports and their original outcomes. Different row seed counts identify different comparison populations; only matching seeds support a paired contrast.\n\n'
    supplemental='### 32 normal fitting examples\n\n'+section(old,'### 32 normal fitting examples','## 4.7 Classification of all six classes')+'\n\n'
    appendix += supplemental.replace('### 32','## F.1 32').replace('### 128','## F.2 128').replace('### 512','## F.3 512')
    appendix += '## F.4 Six-class ranking and classification\n\n'+section(old,'## 4.7 Classification of all six classes','## 4.8 Previously exposed original test')+'\n\n'
    appendix += '## F.5 Original exposed test\n\n'+section(old,'## 4.8 Previously exposed original test','## 4.9 Posthoc selection-frontier diagnostics')+'\n\n'
    text=front+ch1+ch2+ch3+ch4+ch5+references+appendix
    text=text.replace('| Reconnaissance |','| Recon. |')
    assert not re.search(r'\bpending\b', text, re.IGNORECASE)
    assert all(x in text for x in ['INFEASIBLE','33.3%','84.49%','25.9%','post-result'])
    assert not re.search(r'(?:\b[A-Za-z]:[/\\]|/Users/|/mnt/)',text)
    out=HERE/'FINDINGS_PRAXIS.md'
    out.write_text(text.rstrip()+'\n',encoding='utf-8')
    receipt={'status':'COMPLETE_FINDINGS_SYNTHESIS_ORIGINAL_DECISION_UNCHANGED','created_utc':datetime.now(timezone.utc).isoformat(),
        'manuscript_sha256':digest(out),'source_manuscript_sha256':digest(HERE/'PRAXIS.md'),
        'publication_manifest_sha256':digest(RESULTS/'PUBLICATION.json'),'earlier_benign_summary_sha256':digest(PRIOR),
        'component_sources':{name:digest(HERE/name) for name in ['FINDINGS_INTRODUCTION.md','FINDINGS_DISCUSSION.md','FINDINGS_LITERATURE_GAP.md','build_findings_manuscript.py']},
        'original_gate':s['primary_gate'],'scope':'Post-result descriptive synthesis, not a revised primary success decision',
        'word_count':len(text.split()),'new_model_fits':0,'new_thresholds':0,'source_cells':152,'reference_entries':17,
        'required_next_step':'Independent numerical/editorial review and rendered visual review'}
    (HERE/'FINDINGS_ASSEMBLY.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':
    compose()
