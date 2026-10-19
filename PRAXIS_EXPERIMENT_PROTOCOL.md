# Experiment delivery protocol

**Working draft:** October 19, 2026. Freeze by October 26 before scored collection. [Tracker](PRAXIS_STATUS_TRACKER.md) · [Research design](PRAXIS_RESEARCH_DESIGN.md).

## 1. Scope and units

**Implementation workspace:** [experiment cards and artifact templates](experiments/final-praxis-autonomous-ai-apt/README.md). Complete its decision register and protocol template before freeze. Use one trial record per collection attempt, one run manifest per fitted model/fold/seed, and one results template per RQ. Templates are planning/recording artifacts, not an implemented collection or model-training pipeline.

Compare human-operated and autonomous-AI activity under matched conditions in the proposed GOAD multi-host lab. A trial is one bounded execution from a verified reset. All events/windows from that trial remain together. Repeated trials from the same operator, AI configuration, scenario or campaign can still be dependent; document those grouping levels and use the level appropriate to each claim.

Archive all failed/aborted trials with their dispositions. Scripted replay and benign baselines are separately labeled controls. Human tactical intervention changes the interpretation of autonomy and must be recorded under a predeclared rule.

## 2. Feasibility and collection gates

Before collection, confirm staff, independent operator/configuration counts, target uncertainty, time budget and compute budget. Use the pilot to estimate precision and feasibility; do not assume 12–24 trials supports a large model comparison. Overlapping windows, logs and packets are not independent replications.

The deck's Gate A design requires sensor canaries, clock offsets no greater than one second at trial boundaries, native evidence hashes and reset attestation. Treat these as proposed protocol thresholds until frozen. Verify they are met in the actual lab. Source coverage, loss tolerances and failure handling must also be specified.

Run human and AI pilots under the same objective, interface, tools and access window. Counterbalance run order and environment assignments. Freeze knowledge conditions and analyze black-box and white-box runs separately or with preregistered stratification. Keep exposed pilot data in development; never relabel it untouched confirmation data.

## 3. Trial registry and evidence

For each run record: opaque run ID, arm, operator/configuration grouping ID, AI model family and scaffold version, scenario/reset/image versions, knowledge condition, UTC bounds and offsets, partition, outcome, interventions, telemetry quality, exclusion reason and evidence-manifest reference. Keep labels and sensitive identities apart from model inputs and public Git files.

Store native host/network evidence with SHA-256 manifests, extraction version and provenance. Reconcile counts, duplicates, missing sources and joins. Flow logs support coverage checks; use validated high-resolution sensor evidence for timing features. Public repository artifacts should contain schemas, aggregate results and restricted manifest references rather than private raw records.

## 4. Split design and model selection

Reserve final test groups before scored collection. Development folds must keep trials intact. For RQ2, also keep held-out human operators and AI configurations entirely out of the applicable training partition. Configuration holdout does not establish unseen model-family transfer when the same family is in training; label the result accurately. If enough groups exist, report separate operator, model-family, scaffold and joint transfer tests.

Use grouped inner validation for tuning inside grouped outer development evaluation where sample support permits. Every applicable fold needs adequate class/group support; reduce fold count or document an exploratory design if not. Fit imputation, scaling, feature selection, resampling and calibration on training portions only. Do not select features once on the entire dataset before cross-validation.

Freeze sample IDs/fold manifests, feature families, candidate architectures, search spaces, trial roll-up, seeds, maximum tuning evaluations and wall-clock budgets. Pilot estimates set feasible budgets; log actual compute use. Apply matched search opportunities, with explicitly documented model-specific resource caps.

## 5. RQ experiments

| Experiment | Development work | Locked deliverable |
| --- | --- | --- |
| RQ1 | Family permutation and retrained ablation on validation folds; identify candidates without test access | Frozen-family comparisons and qualified feature finding |
| RQ2 | Hold out operators/configurations in development; timing/tool removal; inspect stable family rankings and nuisance reliance | Unseen-group metrics, transfer loss and stability summary, with exact generalization scope |
| RQ3 | Train all specified candidates on common features/folds; tune under frozen budgets | Paired trial-level comparison of all frozen candidates and preselected primary model |

Check label permutation and metadata-only controls for suspicious shortcuts. Unexpectedly good nuisance performance triggers an investigation, not automatic subtraction or selective exclusion. Log changes; exposed final test data cannot be reused as a fresh confirmation set.

## 6. Evaluation and uncertainty

Freeze the trial aggregation rule using development data. Evaluate all final candidates in one locked batch, retain raw trial scores/predictions and never retune from final results. Select the primary model using development evidence. If final rankings differ, report the discrepancy rather than changing the selection history.

Report macro-F1 and per-class errors with denominators. Estimate paired performance differences using resampling at the independent group level; resampling individual windows would exaggerate precision. With very few operators/configurations, label uncertainty estimates fragile and report individual-group outcomes. Freeze a justified procedure, practical effect sizes and multiple-comparison treatment before scoring. Use no arbitrary fixed fold count or confidence claim when independent groups cannot support it.

Track convergence failures, missing candidate runs and costs. A failed or unrun transformer comparison is an explicit result limitation, not a losing score. Ties and insufficient evidence are valid model-comparison conclusions. Distinguish descriptive feature reliance from causal explanation.

## 7. Reproducibility and writing

Required artifacts: protocol and deviations, dataset/feature dictionaries, immutable evidence hashes, split manifest, versioned extraction/training code, environment lock/container digest, seeds/search logs, trained artifacts, per-trial predictions, analysis scripts and manuscript tables. An independent reviewer should regenerate at least the reported metrics and check provenance.

For each RQ write: question, hypothesis, design, sample/group counts, result, uncertainty, limitations and conclusion. Track human-vs-AI attribution separately from scenario success/time-to-objective and benign handling. Use a claim-to-evidence matrix before AI Review and defense.

## 8. Freeze checklist

- [ ] Advisor-reviewed problem, thesis, RQs and H1–H3
- [ ] Trial/operator/configuration counts and precision rationale
- [ ] Rules of engagement, human-participant requirements and matched collection plan
- [ ] Verified telemetry/reset gates and failure rules
- [ ] Development vs final partitions, including required unseen groups
- [ ] Feature definitions, timing/tool ablations and leakage deny-list
- [ ] Model versions, search spaces, compute caps, seeds and selection rule
- [ ] Primary/secondary metrics, trial aggregation and practical margins
- [ ] Group-aware uncertainty procedure and multiplicity plan
- [ ] Evidence retention, access, reproducibility and deviation logs
- [ ] AI Review contents and submission route confirmed; due November 14, 2026
- [ ] Defense circulation/logistics confirmed; defense December 1, 2026

Record the freeze commit and reviewer here: **pending**. A checklist created in Git is not evidence that these gates have passed.
