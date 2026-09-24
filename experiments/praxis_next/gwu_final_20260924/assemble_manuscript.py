"""Assemble the GWU five-chapter praxis from preserved, audited study records."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import csv
import io
import json
import os
import re
import shutil
from urllib.parse import urlsplit

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=HERE.parents[2]
OLD=BASE/'submission_readiness/praxis_review_edition.md'
TITLE='When Better APT Scores Hide Missed Attack Warnings'
INPUTS={}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    INPUTS[path.relative_to(REPO).as_posix()]=sha(path)
    return path.read_text(encoding='utf-8-sig')


def relocate(text, parent):
    def move(m):
        label,target=m.groups()
        if urlsplit(target).scheme or target.startswith('#'):return m.group(0)
        name,sep,fragment=target.partition('#')
        target=os.path.relpath((parent/name).resolve(),HERE).replace('\\','/')
        return f'[{label}]({target}{sep}{fragment})'
    return re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)',move,text)


def section(text, number):
    match=re.search(r'^## '+re.escape(number)+r'\s+[^\n]+\n',text,re.M)
    if not match:raise KeyError(number)
    end=re.search(r'^#{1,2} ',text[match.end():],re.M)
    return text[match.end():match.end()+end.start() if end else len(text)].strip()


def chapter(text, number):
    match=re.search(r'^# '+re.escape(number)+r'\. [^\n]+\n',text,re.M)
    if not match:raise KeyError(number)
    end=re.search(r'^# ',text[match.end():],re.M)
    return text[match.end():match.end()+end.start() if end else len(text)].strip()


def appendix(text, letter):
    match=re.search(r'^# Appendix '+letter+r'\. [^\n]+\n',text,re.M)
    if not match:raise KeyError(letter)
    end=re.search(r'^# ',text[match.end():],re.M)
    return text[match.end():match.end()+end.start() if end else len(text)].strip()


def nested(text, prefix):
    lines=text.splitlines();out=[];count=0
    for line in lines:
        if re.match(r'^# ',line):continue
        match=re.match(r'^#{2,5}\s+(.*)',line)
        if match:
            count+=1
            title=re.sub(r'^(?:\d+(?:\.\d+)*\.?|[A-Z]\.\d+)\s+','',match[1])
            line=f'### {prefix}.{count} {title}'
        out.append(line)
    return '\n'.join(out).strip()


def group(number,title,body):return f'## {number} {title}\n\n{body.strip()}\n'


def named_section(text,title):
    match=re.search(r'^## '+re.escape(title)+r'\s*\n',text,re.M)
    if not match:raise KeyError(title)
    end=re.search(r'^#{1,2} ',text[match.end():],re.M)
    return text[match.end():match.end()+end.start() if end else len(text)].strip()


def pretty_reference(reference):
    text=reference.get('apa_markdown') or reference.get('apa') or reference.get('reference')
    if not text:raise ValueError('Reference missing APA text: '+str(reference))
    if reference.get('url') and 'https://' not in text:
        text+=(' from ' if 'Retrieved September 24, 2026' in text else ' ')+reference['url']
        text=text.replace('Retrieved September 24, 2026. from','Retrieved September 24, 2026, from')
    # Preserve verified names and metadata; format publication containers in APA style.
    if '*' not in text:
        containers=['Ad Hoc Networks, 178','PLOS One, 21','Journal of Big Data, 12',
            'Future Generation Computer Systems, 178','IEEE Networking Letters, 4',
            'Expert Systems, 43','Scientific Reports, 16','Computer Networks, 227',
            'Symmetry, 18','ISeCure, 17','International Journal of Information Security, 25',
            'The Annals of Statistics, 7','The Annals of Statistics, 29',
            'Technometrics, 12','Journal of Machine Learning Research, 12']
        for container in containers:text=text.replace(container,'*'+container+'*')
        for label in ['34th USENIX Security Symposium','28th USENIX Security Symposium','Advances in Neural Information Processing Systems','2025 28th International Symposium on Research in Attacks, Intrusions and Defenses (RAID)']:
            text=text.replace('In '+label,'In *'+label+'*')
        if reference.get('id','').startswith(('lightgbm_','sklearn_')):
            hit=re.search(r'\(n\.d\.-[a-z]\)\. (.*?)(?= \(Version)',text)
            if hit:text=text[:hit.start(1)]+'*'+hit[1]+'*'+text[hit.end(1):]
        if any(mark in text for mark in ('[Preprint]','[Withdrawn preprint]','[Dataset]','[Unpublished praxis manuscript]','[Author manuscript]')):
            hit=re.search(r'\(\d{4}[a-z]?\)\. (.*?)(?= \[| \(Version)',text)
            if hit:text=text[:hit.start(1)]+'*'+hit[1]+'*'+text[hit.end(1):]
    return text


def build():
    original=relocate(read(OLD),OLD.parent)
    models=relocate(read(HERE/'models/MODEL_EXPLANATION.md'),HERE/'models')
    models=models.split('## 8. Corrections and qualifications for the final manuscript')[0].strip()
    models=models.replace('Compact mathematics for Chapter 3','Mathematical summary')
    models=models.replace('the versioned [LightGBM feature documentation]', 'the versioned LightGBM developers (n.d.-a) [feature documentation]')
    models=models.replace('[LightGBM classifier API,', 'LightGBM developers (n.d.-b), [classifier API,')
    models=models.replace('[LightGBM parameters,', 'LightGBM developers (n.d.-d), [parameters,')
    models=models.replace('[LightGBM regressor API,', 'LightGBM developers (n.d.-c), [regressor API,')
    models=models.replace('[official logistic-regression documentation]', 'Scikit-learn developers (n.d.-a), [official logistic-regression documentation]')
    models=models.replace('[Ridge objective and solver documentation]', 'Scikit-learn developers (n.d.-b), [Ridge objective and solver documentation]')
    models=models.replace('### Two deterministic linear selectors',r'''The logistic experts transform a linear score into a bounded binary score:

$$
p(T1105\mid x)=\frac{1}{1+\exp[-(b+\beta^\top\phi(x))]}.
$$

Here, phi is the fixed hashed-text and metadata representation, beta contains learned coefficients, and b is the intercept. Fitting minimizes a class-balanced logistic loss with L2 regularization; the configured C controls inverse regularization strength. This compact score equation explains the classifier, while the saved library configuration above fixes its implementation. The scikit-learn software is described by Pedregosa et al. (2011). A bounded logistic score is not evidence of calibration on the later evaluation population.

### Two deterministic linear selectors''')
    datasets=relocate(read(HERE/'results/DATASET_CHAPTER.md'),HERE/'results')
    datasets=datasets.replace('Liu et al. (2022)','Liu et al. (2022a)')
    datasets=re.sub(r'!\[Native class support and source dependence\]\([^\n]+\)\s*\n\s*\*\*Figure\. Native class support in inspected extension releases\.\*\*[^\n]+\n','The native-class support chart is reported with the qualification results in Chapter 4.\n',datasets)
    results=relocate(read(HERE/'results/RESULTS_CHAPTER.md'),HERE/'results')
    fragments=[]
    abstract='''This praxis examines when improved advanced persistent threat (APT) classification scores accompany more missed attack warnings. The study evaluates historical-evidence choices and training composition using completed predictions from one previously examined UNRAVELED campaign. Its contribution is controlled empirical evidence and a reproducible evaluation procedure that reports correct attack stages, attacks classified as benign, and benign false alerts together. In a clean evidence-acquisition comparison, mean macro-F1 increased from 0.7148 to 0.7379 while exfiltration warning recall decreased from 85.18% to 76.25%. A matched-anchor temporal comparison increased macro-F1 by 0.0632 when later-period observations were allowed into fitting. Under chronological fitting, history increased macro-F1 from 0.7365 to 0.7582 and reduced mean benign false alerts from 24.0 to 14.3, alongside a smaller warning loss. Retrospective capture and fitting-seed omission analyses retained the mean direction of the specified warning-loss comparisons, while showing substantial sensitivity in magnitude. A separate qualification audit identified timing, class-support, dependency and access limitations in four proposed benchmark extensions. Public aggregate verification reproduced 36 paired comparisons and 720 metric intervals. The completed manuscript explains the implemented machine-learning models and mathematical objectives, reports the complete experiment inventory, and provides source-linked supplementary results. The empirical claims concern the inspected records and author labels; independent-campaign generalization, early forecasting and operational benefits were not measured.'''
    (HERE/'abstract.md').write_text(abstract+'\n',encoding='utf-8')

    fragments.append('# Chapter 1: Introduction\n')
    fragments.append(group('1.1','Background',section(original,'1.1')))
    fragments.append(group('1.2','Research Motivation','''Security-model review is an engineering decision: a practitioner must decide whether a proposed change improves outcomes that matter for the intended use. A multiclass score summarizes several kinds of error, yet those errors do not have the same meaning for an investigation. An event labelled as the wrong attack stage can still receive attention; an event labelled benign may receive none. Historical context can change both the stage label and the error destination.

This study began with two practical interventions: learning when historical context should be used and choosing additional evidence under a collection budget. Their completed comparisons revealed a useful evaluation question. Improvements in aggregate classification performance sometimes occurred alongside a loss of attack warnings. The praxis therefore centres on measuring that relationship and providing an inspection procedure supported by the recorded comparisons. The model implementations serve as experimental tools for this applied question.'''))
    fragments.append(group('1.3','Problem Statement',section(original,'1.2')))
    fragments.append(group('1.4','Thesis Statement','''Evaluating APT models using overall performance, stage-specific missed warnings and benign false alerts together reveals consequential tradeoffs that an overall score alone does not describe. A defensible comparison must also establish that its training chronology, evaluation population and source labels support the question being asked.

The thesis is evaluated as an empirical measurement contribution. It does not require a new detector architecture. Its evidence comprises controlled comparisons, observed error destinations, sensitivity analyses and an executable source-qualification procedure.'''))
    fragments.append(group('1.5','Research Objectives','''The objectives are to:

1. Quantify how historical-evidence choices change macro-F1, exact-stage recognition, stage-conditioned warning recall and benign false alerts on the same evaluation records.
2. Measure training-composition sensitivity while holding the classifier family, evaluation anchor and class-specific fitting budgets fixed.
3. Determine whether four proposed APT releases can support the declared all-native-class chronological comparison.
4. Deliver traceable results, understandable model mathematics and a reproducible reporting procedure that keeps adverse outcomes and uncertainty visible.'''))
    fragments.append(group('1.6','Research Questions and Analytical Propositions','''**RQ1, primary:** When historical-evidence choices improve an APT model's overall score, what happens to exfiltration warnings and false alarms on the same evaluation records?

**RQ2, supporting:** How much does access to later-period fitting observations change reported stage performance when architecture, evaluation records and per-class fitting counts remain fixed?

**RQ3, supporting:** Which proposed benchmark artifacts support the unchanged all-native-class chronological comparison, and what prevents the others from supporting it?

The evaluation proposition for RQ1 is that a higher macro-F1 does not ensure preservation of warnings for a particular attack stage. For RQ2, the tested expectation is that changing temporal access and training composition can change scores despite a fixed evaluation anchor. For RQ3, the necessary-condition proposition is that a single cutoff cannot provide the specified earlier and later native-class support when the class-support interval is empty.

The fitted experiments froze their protocols before fitting. The warning-loss pattern was inspected retrospectively; these propositions do not retroactively constitute newly preregistered hypotheses. The complete comparisons and unfavorable outcomes remain in the results. This edition places the warning question first for clarity; the original experiment identifiers, protocols and results retain their original labels in the evidence archive.'''))
    fragments.append(group('1.7','Scope of Research','''The main study evaluates the prepared UNRAVELED flow artifact and uses its four declared evaluation classes. The history-selection, evidence-acquisition and temporal experiments contribute 141 fitted models; a separate two-fit policy-transfer supplement brings the wider batch to 143. These fitting counts are not counts of independent attacks.

The source-qualification study covers inspected SCVIC-APT-2021, DAPT2020 and DSRL-APT-2023 artifacts and the acquisition status of S-DAPT-2026. It does not claim four additional fitted replications. CasinoLimit and CAM-LDS support a separately labelled technique-recognition supplement, whose units and negative labels differ from the main benign-versus-attack stage task.'''))
    fragments.append(group('1.8','Research Limitations','''The main results describe one previously examined campaign. Its movement target denotes author-annotated remote discovery on one host pair, with only 35 evaluation rows and 18 anchor rows. Completed-flow features do not measure detection before flow completion. Stage labels do not independently verify successful compromise or delivery of stolen files. Simulated missing, delayed and wrong-host evidence probes specified conditions; it does not estimate their frequency or price in production.

The paired warning analysis is retrospective, and the five capture fragments are correlated parts of a shared workflow. Conditional resampling intervals and fitting-seed sensitivity describe these data rather than a population of independent campaigns. Chapter 5 states the implications of these limits for the empirical claim.'''))
    fragments.append(group('1.9','Praxis Organization','''Chapter 2 reviews the relevant literature and identifies the narrow empirical contribution. Chapter 3 presents the Graphical Model of Research, source evaluation, implemented models, mathematical objectives and evaluation controls. Chapter 4 reports the completed results and sensitivity analyses. Chapter 5 discusses their meaning, contributions, limitations and recommendations. The appendices and accompanying machine-readable supplement retain comprehensive result coverage, provenance and the original GML GMR reference.'''))

    fragments.append('# Chapter 2: Literature Review\n')
    fragments.append(group('2.1','Introduction','''This review positions the study relative to recent APT evaluation, temporal validity and error-destination research. It is a targeted primary-source review completed September 23, 2026, centred on 2024-2026 publications and supplemented with original dataset and method sources. It identifies overlap and concrete distinctions; it is not a systematic review or an exhaustive priority claim.'''))
    for index,(old,title) in enumerate([
        ('2.1','Temporal Validity in Security Evaluation'),('2.2','Correct Attack Stages and Retained Warnings'),
        ('2.3','Recent Flow and Attack-Stage Research'),('2.4','Dataset Origin and Benchmark Independence'),
        ('2.5','Literature Gap and Contribution Positioning')],start=2):
        fragments.append(group('2.'+str(index),title,section(original,old)))
    fragments.append(group('2.7','Machine-Learning Foundations and Their Role','''The main experiments use gradient-boosted decision trees for multiclass prediction and scalar regression. Boosting adds trees sequentially to improve a specified loss; using the same family across comparisons limits architecture changes as an explanation for a score difference. Chapter 3 distinguishes the multiclass experts from the regressors that select history or additional evidence, and reports their actual objectives.

The separate policy-transfer supplement uses previously fitted logistic-regression experts and newly fitted Ridge selectors. These models provide a deliberately modest test of whether a learned context-selection score changes the decisions of its source experts. The model-specific primary references and equations are given alongside their implementations in Chapter 3. No graph-neural model, TabM architecture or large language model was fitted in this completed measurement batch.'''))
    fragments.append(group('2.8','Literature Review Summary','''The literature establishes that time ordering, source semantics and error destinations matter in security evaluation. The empirical contribution here is a controlled flow-level account of their interaction: fixed-anchor training-composition comparisons, stage-conditioned warning and workload measurements under evidence choices, and a task-specific audit of named dataset releases. Existing metric definitions are used directly. The purpose is to add inspectable measurements and a reusable applied procedure, while keeping the distinction between published precedent and this study's observed results clear.'''))

    fragments.append('# Chapter 3: Methodology\n')
    fragments.append(group('3.1','Introduction and Graphical Model of Research','''The Graphical Model of Research (GMR) summarizes the completed workflow. It follows the numbered What/Why/How convention in the author's earlier GWU GML praxis (Pagan, 2026), with the content adapted to the present measurement study. The original graph-construction, architecture-training and tuning diagram is retained separately as a historical reference in Appendix C.

![Graphical Model of Research for the completed APT evaluation study. The six stages connect source qualification, controlled fitting, error destinations, sensitivity checks and a reproducible evidence package.](figures/gmr_current.png)

The first two stages establish which records, targets and chronology are available. The third fits the declared comparison models without selecting a new architecture from evaluation scores. The fourth records what each prediction does to the attack warning and the benign workload. The fifth evaluates conditional uncertainty and source support. The sixth assembles the completed evidence into a reproducible praxis. The figure is a workflow description, not an additional empirical result.'''))
    fragments.append(group('3.2','Research Design and Analysis Chronology',section(original,'3.1')))
    fragments.append(group('3.3','Datasets, Evaluation Support and Feature Interpretation',nested(datasets,'3.3')))
    fragments.append(group('3.4','Evaluation Anchor and Temporal Controls',section(original,'3.3')+'\n\n'+section(original,'4.1')))
    fragments.append(group('3.5','Historical-Evidence and Acquisition Interventions',section(original,'4.2').replace('The class weights are illustrative priorities','The selector-target weights are illustrative priorities')))
    fragments.append(group('3.6','Implemented Models and Mathematical Summary',nested(models,'3.6')))
    fragments.append(group('3.7','Stage, Warning and Workload Metrics',section(original,'4.3')+r'''

For clarity, let TP, FP and FN denote true positives, false positives and false negatives for one class. Precision measures how many predictions of that class are correct; recall measures how many true members of that class were recovered. Their harmonic mean is F1. Macro-F1 averages class-specific F1 values equally, so a rare class has the same nominal weight as a common class.

$$
P_s=\frac{TP_s}{TP_s+FP_s},\qquad R_s=\frac{TP_s}{TP_s+FN_s}
$$

$$
F1_s=\frac{2TP_s}{2TP_s+FP_s+FN_s},\qquad F1_{macro}=\frac{1}{K}\sum_{s=1}^{K}F1_s
$$

With the confusion count C and benign label b defined above, the central decomposition is:

$$
R_{stage,s}=\frac{C_{s,s}}{N_s},\qquad R_{warning,s}=1-\frac{C_{s,b}}{N_s}
$$

$$
FPR_b=\frac{\sum_{j\ne b}C_{b,j}}{N_b}
$$

These equations define ordinary confusion-matrix quantities. The model family does not change their meaning. The complete tables retain the original metric conventions; the paired reanalysis additionally marks unsupported true classes as undefined rather than silently excluding them.'''))
    fragments.append(group('3.8','Paired Reanalysis, Uncertainty and Sensitivity',section(original,'4.4')+'''

Bootstrap resampling is a general tool for measuring variation in a statistic (Efron, 1979). Here the resampling unit is a capture fragment, with shared multiplicities for each paired prediction comparison. That choice preserves the paired calculation but cannot make correlated fragments into independent campaigns. The reported intervals are explicitly conditional and descriptive.

The additional frozen sensitivity audit exhaustively removes each of five captures from each of 36 comparisons, holding predictions fixed, and removes each fitting seed from each of 12 three-seed means. The remaining seed metrics are averaged without pooling repeated flows. These finite omission ranges are not confidence intervals or unseen-campaign validation. Ordered per-capture confusion signatures identify repeated sufficient statistics among acquisition comparisons; equal signatures do not prove identical row-level predictions.'''))
    fragments.append(group('3.9','Necessary Chronological-Support Test',section(original,'4.5')))
    fragments.append(group('3.10','Reproducibility, Implementation and Compute',section(original,'4.6')+'''

The GWU edition assembles existing results and adds explanatory text, diagrams, mathematical summaries and complete publication tables. It performs no additional model fitting. The accompanying build records bind the original input artifacts, generated tables, charts, references and final document. Human authorship review and institutional approval remain distinct from computational verification.'''))

    fragments.append('# Chapter 4: Results\n')
    fragments.append(group('4.1','Primary Finding: Overall Scores and Missed Exfiltration Warnings',section(original,'5.2')))
    fragments.append('![Complete acquisition comparisons. Each condition and budget is shown with paired F1, exfiltration warning and benign false-alert changes; all fitting seeds remain in the accompanying tables.](results/figures/fig04_acquisition_complete_tradeoffs.png)\n')
    fragments.append('Across the complete acquisition inventory, the error-focused policy has higher mean macro-F1 in eight of nine condition/budget groups and lower exfiltration warning recall in all nine. Wrong-host budget three has both lower F1 and lower warning recall. The complete tables retain that unfavorable combination, the unrestricted references and every declared policy. Lower simulated request expenditure is reported as a replay result, not a measured collection saving.\n')
    fragments.append(group('4.2','Chronological History Gains and Their Tradeoff',section(original,'5.3')))
    fragments.append(group('4.3','Supporting Finding: Fixed-Anchor Temporal Sensitivity',section(original,'5.1')))
    selectors=section(original,'5.4')
    split=selectors.find('The [supplementary policy-transfer study]')
    supplementary=selectors[split:] if split>=0 else ''
    selectors=selectors[:split] if split>=0 else selectors
    fragments.append(group('4.4','History Selection and Simple Controls',selectors))
    fragments.append('![History-selection movement recall and benign false-alert outcomes across all five evidence conditions. Stage weights affect selector targets, while the current-plus-roles model supplies a strong simple control.](results/figures/fig05_selector_stage_workload.png)\n')
    fragments.append(group('4.5','Dataset Evaluation and Qualification Results',section(original,'5.5')))
    # Exact additional figure names are read from the generated manifest below.
    generated=json.loads(read(HERE/'results/FIGURES.json'))
    figure_paths=sorted((HERE/'results/figures').glob('fig*.png'))
    for p in figure_paths:
        if 'support' in p.name or 'class' in p.name:
            fragments.append(f'![Observed class support and source eligibility. Dataset counts and qualification decisions describe the inspected artifacts and the declared task.]({p.relative_to(HERE).as_posix()})\n')
    fragments.append(group('4.6','Capture and Fitting-Seed Sensitivity',section(original,'D.1')))
    fragments.append('![Fitting-seed influence on the clean budget-three warning tradeoff. The full mean and each leave-one-seed-out mean expose the effect-size dependence.](results/figures/fig06_fitting_seed_influence.png)\n')
    fragments.append(group('4.7','Supplementary Technique-Policy Transfer',named_section(results,'Secondary technique-policy transfer')))
    fragments.append(group('4.8','Ranking Metrics and Operating Decisions',named_section(results,'Ranking metrics and operating decisions answer different questions')))
    stage_means=list(csv.DictReader(io.StringIO(read(HERE/'results/tables/all_class_group_means.csv'))))
    stage_rows=[r for r in stage_means if r['study']=='PX082' and r['arm']=='past_only_anchor']
    assert len(stage_rows)==8
    stage_table=['**Table 7. Stage-level discrimination under chronological fitting.** Each entry is the arithmetic mean of three fitting-seed metrics on the same 104,051-row anchor. Current means current-flow features; History adds earlier-activity summaries. These class metrics are not pooled across seeds. Movement retains the narrow author-label interpretation.','',
        '| Feature view / class | Precision | Exact recall | F1 | ROC-AUC | Avg. precision |',
        '|---|---:|---:|---:|---:|---:|']
    names={'Benign':'Benign','OtherAttackStage':'Other attack','LateralMovement':'Movement','DataExfiltration':'Exfiltration'}
    for r in stage_rows:
        label=('Current' if r['view']=='current' else 'History')+' / '+names[r['class']]
        values=[f"{float(r[k]):.4f}" for k in ['precision','exact_recall','f1','roc_auc','average_precision']]
        stage_table.append('| '+label+' | '+' | '.join(values)+' |')
    stage_table.extend(['','ROC-AUC measures ranking across score thresholds: how often a true member of one class is ranked above a nonmember. Average precision summarizes precision across recall levels and is useful when a class is rare; it is not interchangeable with trapezoidal area under a precision-recall curve. Neither ranking summary fixes the argmax decision or the resulting warning destination. The reported areas are retained source metrics; no curve is reconstructed from a single confusion matrix.'])
    fragments.append('\n'.join(stage_table)+'\n')
    fragments.append(group('4.9','Answers to the Research Questions','''**RQ1:** The completed comparisons demonstrate that an improved overall score can accompany fewer exfiltration warnings on the same records. In the clean budget-three acquisition comparison, mean macro-F1 rose while warning recall fell and benign false alerts increased. Chronological history also produced useful gains and a smaller warning tradeoff. Error destinations and benign workload are therefore material to interpretation.

**RQ2:** The fixed-anchor comparison demonstrates sensitivity to training composition and temporal access. The current-feature macro-F1 difference was +0.0632, and movement-label recall increased by 35.19 percentage points. Architecture, evaluation rows and class counts were controlled; every property of the training distributions was not isolated.

**RQ3:** The inspected DAPT artifact cannot satisfy the unchanged all-native-class single-cut support rule. SCVIC has possible recorded-start support but unresolved physical chronology. DSRL derives from DAPT, and no qualified S-DAPT release was acquired. These are source-specific qualification results, not four fitted replications.

The numerical comparisons answer the declared questions within the inspected records. Neither a minimum favorable score nor a self-imposed 90% recall threshold determines whether a finding is retained.'''))

    fragments.append('# Chapter 5: Discussion and Conclusions\n')
    fragments.append(group('5.1','Discussion of the Central Finding',section(original,'6.1')))
    fragments.append(group('5.2','Contributions to the Body of Knowledge','''The primary contribution is a controlled, reproducible measurement of how historical-evidence decisions affect stage recognition, attack-warning retention and benign workload on matched evaluation records. The study makes the destination of errors explicit and retains comparisons that are favorable, unfavorable or unchanged. It also quantifies how much the headline warning-loss magnitude depends on a fitting seed.

The supporting temporal contribution fixes the anchor population and fitting class budgets while measuring a change in temporal access and training composition. The source-qualification contribution makes the eligibility of named releases executable: native-class support, timing and source dependence are checked before another model comparison is claimed.

These contributions add specific empirical evidence and reusable audit infrastructure to a literature that already recognizes temporal evaluation and attack-to-normal errors. They do not require a new detector or new mathematical metric. The research value is the evidence, controls and practical interpretability of the resulting evaluation procedure.'''))
    fragments.append(group('5.3','Applied Evaluation Procedure',section(original,'6.2').replace('reporting requirement','reporting proposal')+'\n\n'+section(original,'6.3')))
    fragments.append(group('5.4','Construct, Internal and External Validity',nested(chapter(original,'7'),'5.4')))
    fragments.append(group('5.5','Recommendations for Future Research','''The first empirical extension is independent-execution replication with reliable event clocks, native stage labels and legitimate background activity. The relevant aim is to test whether the measured relationship and its magnitude recur under a different workflow. Additional architectures are useful only if they answer a defined comparison question; they are not a prerequisite for stating the completed measurement contribution.

An operational study could subsequently test whether the proposed joint report changes an analyst's or model-review team's decisions. Such a study would need actual users or deployment outcomes, a declared decision task and an appropriate comparison design. The present computational results do not stand in for that evidence.

The source intake checked Sandworm and CAM-LDS as possible extensions. Sandworm was previously evaluated in this project and has no native exfiltration flow class; CAM-LDS lacks simulated normal-user activity. A log-first annotation-linkage intake may support a different technique task, but those facts do not supply the missing full warning-and-benign-workload replication.'''))
    fragments.append(group('5.6','Conclusions','''This praxis provides an evidence-based evaluation method for exposing missed attack warnings that an improved APT classification score can conceal. In the observed acquisition comparison, mean macro-F1 increased from 0.7148 to 0.7379 while exfiltration warning recall fell from 85.18% to 76.25%. The direction of the specified mean tradeoff survived every single-seed and single-capture omission, while its size remained strongly seed-sensitive.

Supporting experiments show that training composition changes the reported score on a fixed anchor, and that chronological history can improve both F1 and benign workload while still losing some stage-specific warnings. The dataset audit establishes which proposed extensions support the intended comparison and why the others do not.

The completed contribution is the controlled evidence and reproducible procedure: qualify the source, justify the temporal design, compare the same population when estimating a paired effect, separate wrong-stage warnings from attacks called benign, and report false alerts alongside both. The resulting claims are specific to the inspected evidence and ready for substantive scholarly review.'''))

    refs=json.loads(read(BASE/'measurement_praxis/references.json'))
    for file in [HERE/'models/REFERENCES.json',HERE/'results/REFERENCES.json']:
        if file.exists():
            more=json.loads(read(file))
            if isinstance(more,dict):more=more.get('references',list(more.values()))
            refs.extend(more)
    refs.extend([
        {'id':'efron1979','apa':'Efron, B. (1979). Bootstrap methods: Another look at the jackknife. The Annals of Statistics, 7(1), 1-26. https://doi.org/10.1214/aos/1176344552','url':'https://doi.org/10.1214/aos/1176344552','support_scope':'General bootstrap rationale; does not establish independent-campaign coverage for this study.','primary_evidence_urls':['https://sites.stat.washington.edu/courses/stat527/s13/readings/ann_stat1979.pdf'],'locator':'Primary article, printed pp. 1-3, bootstrap formulation.','verified_on':'2026-09-24'},
        {'id':'pagan2026reference','apa':'Pagan, G. (2026). Advanced persistent threat event detection using graph machine learning [Unpublished praxis manuscript]. The George Washington University.','support_scope':'User-provided GWU structure and original Graphical Model of Research figure; historical reference, not a new experiment.'}])
    unique={}
    for ref in refs:
        key=(ref.get('apa') or ref.get('apa_markdown') or ref.get('reference','')).replace('*','')
        if not key:raise ValueError(ref)
        doi=re.search(r'https?://(?:dx\.)?doi.org/([^\s]+)',key)
        if doi:key=doi[1].lower().rstrip('.')
        if key not in unique:unique[key]=ref
    refs=sorted(unique.values(),key=lambda r:(r.get('apa') or r.get('apa_markdown') or r.get('reference')).replace('*','').casefold())
    for ref in refs:
        if ref.get('id')=='liu2022':ref['apa']=ref['apa'].replace('(2022).','(2022a).')
        if ref.get('id')=='liu2022dataset':ref['apa']=ref['apa'].replace('(2022).','(2022b).')
    fragments.append('# References\n\n'+'\n\n'.join(pretty_reference(r) for r in refs)+'\n')
    (HERE/'references.json').write_text(json.dumps(refs,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

    fragments.append('# Appendix A: Complete Results and Dataset Reporting\n')
    fragments.append(group('A.1','Complete Evaluation Inventory',named_section(results,'Evidence inventory')))
    printable=relocate(read(HERE/'results/COMPLETE_GROUP_TABLES.md'),HERE/'results')
    fragments.append(group('A.2','All Reported Group Means',nested(printable,'A.2')))
    fragments.append(group('A.3','Stage Metrics and Source-Record Access','''The complete supplement retains the per-class precision, recall, F1, ROC-AUC and average precision fields reported by each source, with confusion matrices and subgroup records. Blank normalized CSV fields represent metrics not supplied by the original experiment; they are not zeros or reconstructed ranking scores. Every group mean printed above is backed by its component evaluation records. The source JSON preserves additional nested fields and original null values.

Readers should compare only compatible populations, targets and operating decisions. Primary stage comparisons and secondary T1105 policy views have different units and denominators. The saved tables provide the full inventory without converting related views into independent empirical replications.'''))
    fragments.append('# Appendix B: Reproducibility, Provenance and Evidence Access\n')
    fragments.append(group('B.1','Experimental Parameters and Source Provenance',appendix(original,'A').replace('Classifier trees / leaves','Boosting iterations / leaves').replace('class weights 1/1/4/4 for weighted selector','target weights 1/1/4/4 for weighted selector')))
    fragments.append(group('B.2','Claim Traceability',appendix(original,'B')))
    fragments.append(group('B.3','Public Reproduction and Access Limits',section(original,'D.2')))
    fragments.append(group('B.4','Document and Reference Provenance','''The five-chapter organization, title-page author information and What/Why/How GMR convention follow the author's original GWU GML praxis. The current GWU online-program 2026 template and official formatting requirements were also inspected. The reference record identifies the source files and hashes. The original document's certification and dates are historical text; they are not carried forward as approval of this study.

The reference review is targeted and uses primary sources, author manuscripts and publisher metadata where available. Some final publisher full texts were inaccessible; the cited version and access limits are recorded in the literature audit. Bibliographic entries identify inspected preprints separately from final publications. The dataset papers establish provenance, while the local source inspections establish what the acquired artifacts support.

AI-assisted agents were used for code development, computational checks, literature triage, document assembly and layout review. Computational agreement and same-team review do not substitute for the author's responsibility to inspect the research, for independent label validation or for adviser and institutional review. No external peer review or institutional approval is represented as completed.'''))
    fragments.append('# Appendix C: Original GWU GML GMR Reference\n')
    fragments.append('''The following image is the exact Graphical Model of Research extracted from the author's earlier manuscript, *Advanced Persistent Threat Event Detection Using Graph Machine Learning* (Pagan, 2026). It is reproduced as a historical formatting and research-structure reference. Its graph models, Optuna tuning, AWS acquisition and evaluation statements describe that earlier document and are not the methods or results of this praxis. The adapted current-study GMR appears in Chapter 3.

![Historical Graphical Model of Research from the original GWU GML praxis. Reproduced unchanged from the author-provided reference; it is not the current study's methodology. The full-resolution image is included with the supplement.](figures/gmr_original_reference.png)

The new study retains the original convention of answering What, Why and How for each research stage. It replaces the old graph-training sequence with source qualification, matched evaluation, implemented comparison models, error-destination accounting, sensitivity analysis and verified reporting. This preserves the explanatory purpose of a GMR while keeping the current methodology faithful to the completed evidence.
''')

    text='\n\n'.join(fragments).strip()+'\n'
    # Cross-references must name the new chapter structure, not the earlier article layout.
    text=text.replace('Section 6.3','Section 5.3').replace('Section 2.5','Section 2.6')
    text=text.replace('class weights 1/1/4/4','selector-target weights 1/1/4/4')
    text=text.replace('Classifier trees / leaves','Boosting iterations / leaves')
    text=text.replace('200 estimators, 15 leaves','200 boosting iterations, at most 15 leaves per tree')
    text=text.replace('source groups, and native class meanings must match','source groups, and declared evaluation-class meanings must match')
    text=text.replace('proposed applied reporting proposal','proposed reporting procedure')
    text=text.replace('label described in Section 3.','label described in Chapter 3.')
    text=text.replace('The completed contribution has three parts.','The completed contribution has three connected parts.')
    for token in ('TODO','PLACEHOLDER'):
        assert token not in text,token
    assert not re.search(r'\{\{[A-Z_]+\}\}', text)
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text):
        assert (HERE/target).is_file(),target
    (HERE/'manuscript.md').write_text(text,encoding='utf-8')
    receipt={'utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(Path(__file__)),
        'title':TITLE,'author':'Gary Pagan','input_sha256':INPUTS,
        'manuscript_sha256':sha(HERE/'manuscript.md'),'abstract_sha256':sha(HERE/'abstract.md'),
        'references_sha256':sha(HERE/'references.json'),'reference_count':len(refs),
        'word_count':len(re.findall(r'\b\S+\b',text)),
        'main_chapters':5,'appendices':3,'new_model_fits':0,
        'source_evidence':'Preserved original results; document/table/figure assembly only',
        'status':'ASSEMBLED_REQUIRES_RENDER_AND_REVIEW'}
    (HERE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='input_sha256'},indent=2))


if __name__=='__main__':build()
