# Identifying Autonomous AI APT: working research design

**Revision:** October 24, 2026. **Status:** author-approved working wording for advisor review; not a completed finding or frozen preregistration. This document supplies the current three-RQ structure. The October 16 advisor presentation remains an unchanged historical submission. [Delivery tracker](PRAXIS_STATUS_TRACKER.md) · [Experiment protocol](PRAXIS_EXPERIMENT_PROTOCOL.md).

## Problem and thesis

**Problem statement:** It remains uncertain which defender-visible host and network behaviors reliably distinguish human-operated from autonomous-AI APT-like activity in a matched multi-host laboratory, and whether classifiers transfer to unseen operators and AI configurations rather than exploiting collection artifacts.

**Working thesis:** Under matched laboratory conditions, target-side behavioral features can support human-versus-autonomous-AI attribution beyond simple baselines, with measurable transfer across held-out operators and AI configurations after controlling timing, tool identifiers and setup artifacts. This is a proposition to test; negative and inconclusive outcomes remain valid.

The classification target is operator type among defined attack trials. It is not proof of APT identity, intent, campaign attribution or general maliciousness. Benign and scripted activity require separate control reporting. The short project title is retained, while the scientific scope is explicitly controlled APT-like activity.

## Why revise the RQs this way?

The requested progression is coherent: identify features, establish their stability and transfer, then compare classifiers. “Which model identifies important attributes” alone overlaps RQ3 and confuses explanation quality with predictive accuracy. Here, **classifier** means XGBoost/tree/SVM/transformer; **attacker AI model family/configuration** means the model and scaffold generating the attack. RQ2 tests whether the former learns signatures of the latter that fail to generalize.

Alt's controlled SSH study directly supports examining behavioral features and multiple classifiers, but studies human, conventional automation and AI-assisted activity. It does not establish autonomous multi-host transfer [1]. Trace studies attacker AI-family fingerprinting and reports reduced performance on unseen scaffolds, making model/scaffold shortcuts a relevant control for this different attribution question [2]. Neither source establishes that this proposed study will succeed or be the first of its kind.

Tabular benchmark research motivates strong tree baselines [3]. FT-Transformer offers a concrete transformer for the same engineered tabular input, and its authors find no universally superior model family [4]. These are reasons to compare models empirically, not to promise a transformer or XGBoost winner. They also do not supply a justified trial count for this experiment.

## Revised research questions

| RQ | Working wording | Required answer / artifact |
| --- | --- | --- |
| **RQ1 — Feature identification** | Which target-side host and network behavioral feature families distinguish human-operated from autonomous-AI APT-like trials under matched conditions? | Feature dictionary, family ablations, held-out development-fold importance estimates and uncertainty |
| **RQ2 — Stable attributes and generalization** | Which classifiers retain useful behavioral attributes for classification performance on autonomous-AI APT data? | Operator/configuration holdouts, family-level attribution stability, transfer gaps, timing/tool ablations and shortcut audit |
| **RQ3 — Model comparison** | Among XGBoost, a decision tree, a random forest, SVM and a tabular transformer, which provides the strongest trial-level human-versus-autonomous-AI classification? | Paired model comparison, baseline contrasts, uncertainty, false AI labels on humans, compute cost and a qualified selection conclusion |

RQ1 identifies signals. RQ2 evaluates their stability and transfer. RQ3 compares predictive utility and cost. RQ2 may identify a different preferred classifier than RQ3, or find that none transfers adequately. Avoid a forced single ranking across contradictory criteria.

## Hypotheses and decision framework

These are proposed tests. Freeze exact feature families, folds, search budgets, contrasts, practical margins and statistical procedures by October 26 before scored collection. Do not choose them after viewing final outcomes.

| Hypothesis | Alternative / null | Test and decision |
| --- | --- | --- |
| **H1 / RQ1** | Command diversity and command-sequence transition entropy improve classification of human-operated versus autonomous-AI APT-like activity compared with a predefined baseline. Null: the predefined contrasts do not support improvement from the specified features. | Freeze the baseline, individual/joint feature contrasts and extraction definitions. Use paired held-out predictions, retrained ablations, grouped uncertainty and multiplicity control; do not infer individual-feature benefit from family importance alone. |
| **H2 / RQ2** | Logistic regression retains useful behavioral attributes and achieves above-baseline classification performance on previously unseen autonomous-AI configurations and human operators. Null: logistic regression does not show a supported above-baseline benefit on the specified unseen groups. | Freeze logistic regression, baseline, reduced representation and group splits. Test the baseline contrast on unseen human operators and AI configurations; report feature stability, timing/tool ablations and transfer loss separately. Exact decision procedures remain to be frozen. |
| **H3 / RQ3** | SVM achieves higher trial-level macro-F1 than XGBoost, a decision tree, a random forest and a tabular transformer for human-versus-autonomous-AI classification. Null: SVM superiority over every named comparator is not supported. | Freeze SVM-versus-each-comparator contrasts, practical difference margin and multiplicity procedure. Use paired trial/group uncertainty. H3 requires supported superiority over all four named candidates; ties or insufficient evidence do not support H3. |

**Primary metric:** trial-level macro-F1. **Required secondary metrics:** each class's precision/recall, confusion matrix, AI-label rate on human trials, balanced accuracy and probability calibration where applicable. Report benign AI-label rate separately; a classifier trained only on attack trials is not an intrusion detector. Record training/inference time and compute cost.

Set any acceptable human false-AI-label threshold, transfer-loss margin and minimum important model difference using advisor/operational requirements and pilot precision estimates. Numeric values are unresolved, not fabricated commitments. A result cannot be called a confirmatory hypothesis pass until those decisions are frozen.

## October 24 revision and evidentiary basis

The author approved the wording above on October 24, 2026, after reviewing the October 19 synthetic experiments and October 20 real-archive feasibility screen. These are directional predictions for the prospective study, not results, advisor approval or a retrospective preregistration. Earlier exploratory data informed their selection and cannot independently confirm them. Date and explain later revisions before final evaluation.

- **H1:** Command diversity and command-sequence transition entropy are candidate features motivated by the command/host family's utility in the synthetic experiment. Neither was isolated as an individual winner. Target-side extraction still requires validation; freeze whether the hypothesis requires individual and/or joint improvement.
- **H2:** Logistic regression transferred at 70.8% and 66.2% group-balanced accuracy between Honey and COCHISE in opposite directions. These exploratory command-only results support a candidate choice, not proof of target-side generalization; source confounding remains substantial.
- **H3:** SVM transferred at 71.3% and 64.3%, compared with random forest's 60.0% and 56.8%. XGBoost, decision tree and transformer were not tested in that real-archive screen. SVM superiority over them is a prospective prediction, not a demonstrated ranking. These balanced-accuracy observations do not substitute for the primary macro-F1 hypothesis test.

[Real-record feasibility results](experiments/final-praxis-autonomous-ai-apt/pipeline/REAL_FEASIBILITY.md) ? [Synthetic results](experiments/final-praxis-autonomous-ai-apt/pipeline/GROUNDED_RESULTS.md).

The shorter RQ2/RQ3 wording does not remove matched conditions, common feature representations, grouped holdouts, bounded tuning or shortcut controls from the methodology. Transfer-loss margins remain an optional predeclared robustness criterion rather than an unstated condition of the revised H2. No paper or historical result has been rewritten by this revision.

## Methodology

Use a controlled matched-trial design: prepare human and autonomous-AI arms under equivalent conditions; validate resets and passive host/network capture; pilot and freeze the protocol; collect scored trials and separate scripted/benign controls; validate and partition by trial and required unseen groups; engineer training-only features; compare frozen candidates and ablations; evaluate locked trials once; audit results and write the Praxis.

The [experiment workspace](experiments/final-praxis-autonomous-ai-apt/README.md) provides RQ-specific cards and fillable protocol, trial, run and result templates. The [full methodology](PRAXIS_EXPERIMENT_PROTOCOL.md) governs leakage controls, uncertainty and freeze gates. No collection or training completion is implied by the templates.

## Candidate models and representations

| Model | Role | Controls |
| --- | --- | --- |
| Majority / stratified dummy | No-skill reference | Fit using training labels only |
| Logistic regression | Simple predictive reference | Training-only scaling; bounded regularization |
| Metadata-only model | Collection-confounding diagnostic | Metadata withheld from substantive models; above-chance signal triggers a design audit |
| Timing-only rule/model | Simple behavioral baseline | Thresholds selected only on development data |
| Decision tree | Interpretable single-tree candidate requested as “tree” | Limit depth/leaves; compare stability |
| Random forest | Ensemble tree candidate | Bounded depth/features/trees; same splits |
| XGBoost | Boosted-tree candidate | Regularization and early stopping using training-internal validation |
| SVM | Margin-based candidate | Freeze linear/RBF search scope; training-only scaling; calibration fitted without test data |
| FT-Transformer | Transformer candidate on the same feature table | Bounded capacity, regularization, training-internal early stopping and multiple fixed seeds |

A sequence transformer would receive a different representation and therefore test a **model-plus-representation** system. Treat that as an explicitly separate extension, not evidence that architecture alone improved performance. The primary comparison uses the common feature table. Prior KNN/GB variants can remain historical rather than expanding the deadline-critical comparison.

## Feature validity and leakage controls

Start with host behavior (diversity, sequence/phase changes, breadth, retries/errors) and network behavior (protocol mix, concurrency, timing/bursts). Keep their operational definitions in a dictionary. Remove labels, run IDs, addresses, host/account identities, banners, runner/scaffold artifacts and experimenter-assigned cues from substantive predictors.

Define the timing ablation broadly: rates, durations, inter-arrival statistics and temporally defined concurrency belong in a documented timing-derived set. Removing only an explicit timestamp while retaining equivalent proxies is not a timing-free test. Tool-name removal must also address tool-derived categories that reveal the same identity.

Use feature-family permutation and retrained ablations on development holdouts; correlated inputs can mask each other's individual permutation importance [5]. Explanations describe model reliance, not causal proof of autonomous behavior. RQ1 selections and RQ2 changes must occur within the training/development process. All fitted preprocessing and feature selection stay inside the relevant training fold [6,7].

## Mapping from the October 16 deck

| Prior element | Working revision |
| --- | --- |
| RQ1 separability | Retained as baseline comparison within RQ1 and RQ3 |
| RQ2 signals and timing/tool removal | Feature identification in RQ1; robustness in RQ2 |
| RQ3 held-out operator/configuration, formerly Phase 2 | Required RQ2 inside Oct 19–Dec 1 window |
| RQ4 AI mimics human pacing | Optional stress extension only if core collection/evaluation schedule permits; not a fourth required RQ |
| RF/GB/XGB/LR/SVM/KNN comparison | Explicit tree, RF, XGBoost, SVM and FT-Transformer candidates; LR and simple controls retained |
| “First” contribution language | Candidate novelty requiring documented literature comparison |
| January–February 2027 expansion | Superseded for required work by the 2026 delivery plan |

Update the next advisor/defense slide revision from this document after the review decisions are recorded. Preserve the V001 submission as the historical record.

## Sources reviewed October 19, 2026

See the [annotated literature and problem-statement evidence](PRAXIS_LITERATURE.md) for author/date/document details, the closest novelty comparison and corrected interpretation of the industry statistics.

1. Ashley Alt (2026), [Beyond Anomaly Detection: Classifying Attacker Automation Level from SSH Honeypot Behavioral Signatures](https://repository.rit.edu/theses/12605/). Primary institutional thesis record/abstract.
2. Murali Ediga and Sudipta Chattopadhyay (2026), [Trace: Unmasking AI Attack Agents Through Terminal Behavior Fingerprinting](https://arxiv.org/abs/2605.01186). Primary preprint abstract; related problem, not direct validation of this study.
3. Grinsztajn, Oyallon and Varoquaux (2022), [Why do tree-based models still outperform deep learning on tabular data?](https://arxiv.org/abs/2207.08815). Primary benchmark paper abstract.
4. Gorishniy et al. (2021, revised 2023), [Revisiting Deep Learning Models for Tabular Data](https://arxiv.org/abs/2106.11959). Primary paper abstract and model-family description.
5. scikit-learn, [Permutation feature importance](https://scikit-learn.org/stable/modules/permutation_importance). Official methodological guidance, including correlated-feature limitations.
6. scikit-learn, [Cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html). Official guidance on group-aware splits.
7. scikit-learn, [Common pitfalls](https://scikit-learn.org/stable/common_pitfalls). Official guidance on preprocessing and selection leakage.

This is a focused design review based on the identified primary records and official guidance, not an exhaustive systematic novelty review. P06 tracks the fuller citation and novelty audit.
