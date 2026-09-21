# Praxis decision and research history

## Current decision: measured improvements with explicit tradeoffs

**The completed studies support an empirical praxis about improving alert efficiency while measuring which attack activity becomes less visible.** The current recommended paper is [Improving APT Alert Efficiency: Measured Gains and Lateral-Movement Tradeoffs](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.md). This findings-led interpretation was developed after the results were known; it changes no original model, threshold, protocol, or scientific decision.

The strongest earlier improvement came from adding normal fitting examples while retaining the same 160 attack examples: **96.02% fewer false positives**, macro-F1 **0.4421 to 0.6543**, and lateral-flow detection **94.24% to 83.06%**. The reduction in false alarms and better overall score are real development findings, alongside the detection loss. They belong to the preceding benign-label experiment, not the new 152-cell study.

In the new study, the candidate reduced false positives by **33.3%** and raised attack F1 from **0.8770 to 0.9044** relative to the lateral-sensitive reference on the **same six feasible primary seeds**. Lateral detection fell from **88.19% to 84.49%**. A separate exploratory matched-six comparison found **25.9% fewer false positives** and mean lateral recall **87.73% to 88.19%** for the reference versus the ordinary source-normal 1% threshold. Only **two of six seeds improved both measures**; some other stages declined and no incident-level confidence claim follows.

All 19 groups and 152 final models completed and the independent consistency audit passed. The **original primary screen remains INFEASIBLE**, because four of ten seeds could not select a policy meeting the declared requirements. Secondary feasibility was 0/3 at 32 benign labels, 1/3 at 128, and 1/3 at 512. Those study-defined requirements are one prespecified assessment, not an industry standard or a statement that every measured benefit is worthless. The revised findings do not replace them with a new passing hypothesis.

Lateral detection here means flagging an author-labeled lateral flow as any attack; it does not mean correct stage naming, actor attribution, or warning before harm. SCVIC remains previously examined development data, and repeated fitting seeds are not independent incidents. The current contribution is a reproducible empirical comparison, not a validated novel algorithm. Its sufficiency as a praxis contribution depends on the institution's requirements.

DEDALE supplies a limited transfer warning. The fixed source seed had no candidate, so only ordinary controls were evaluated on 100,000 sampled benign flows and four lateral flows from **one execution**. Argmax produced **7,418 false positives and detected one of four**; the source-normal threshold produced **24,511 false positives and detected all four**. This neither validates a candidate nor demonstrates that source calibration holds externally. One detected flow might already alert on the execution; these are not four independent incidents.

Before an operational recommendation, define acceptable false-alarm and missed-activity costs with the intended users, then collect independent executions with legitimate administration background and freeze a new comparison. Do not inherit 90% as a universal safety standard or reuse these exposed outcomes as fresh confirmation. The completed work used CPU and passed 40 new implementation and integrity tests, separate from historical counts.

- [Current findings-led paper](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.md), [Word](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.docx), [PDF](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.pdf)
- [Actual improvements, matched comparisons, and costs](../lateral_protection_experiment/paper/FINDINGS_ACTUALS.md)
- [Literature gap and prior-art limits](../lateral_protection_experiment/paper/FINDINGS_LITERATURE_GAP.md)
- [Completed design](../lateral_protection_experiment/README.md) and [unchanged audited results](../results/lateral_protection_v1/REPORT.md)
- [Prior screen-oriented manuscript](../lateral_protection_experiment/paper/PRAXIS.md), [original proposal](../lateral_protection_praxis/README.md), and [DEDALE qualification](../lateral_protection_experiment/dedale/QUALIFICATION.md)

## Earlier completed tabular comparison

The preceding [130-cell tabular comparison and rare-stage checker](../results/tabular_followup_decision_v1/REPORT.md) motivated the lateral-protection study. More benign fitting examples improved the selected tree's macro-F1 and false-positive rate but reduced lateral-flow detection; the foundation-model comparisons used a different benign-label budget. The checker and independent Sandworm binary transfer did not establish the required operational protection. These findings and their original receipts remain preserved.

## Historical diagnostic decisions

**Historical decision after the bounded diagnostic:** [combined audit evidence results](../results/window_diagnostic_v1/REPORT.md) are complete. Pooling raises macro-family recall from 10.4% to 21.3%, but misses the predeclared useful-signal gate, does not beat the simple transfer-tool rule, and is not rescued by ExtraTrees. Retire this primary CAM window formulation. Do not launch an evidence-recovery extension from these findings. A new candidate needs independently qualified evidence-level supervision and useful complete-evidence controls. The recommendations below are preserved as history; the completed lateral-protection decision above is current.

**Earlier completed follow-up:** [structured-loss controls and separate-source proxy results](../results/robustness_v2/SUMMARY.md) are complete and audited. All four AIT/Casino primary development targets fail the full frozen screen. Mixed training reduces some incorrect flags but introduces clean/random-loss harm; the visible-record router does not resolve the weakness. CAM-LDS is qualified only for manifestation-window membership with padded global labels. The next gate is to match supervision to host/process-local evidence or a defensible multi-host window target before selecting a further mechanism. Earlier recommendations below are preserved as research history, not the latest completion status.

**September 20 update:** The subsequent [missing/delayed-log suite is complete](../results/robustness_v1/SUMMARY.md). It provides positive random-loss results on CasinoLimit, structured-loss failures and no consistent AIT augmentation benefit. The next gate is source-type-aware evidence handling with independent confirmation. [S-DAPT-2026 is registered conditionally](../sdapt2026/README.md), with source/correction and data-access issues documented. The earlier pilot rationale below is retained as development history.


## Plain-language problem

A detector can look almost perfect by catching large volumes of familiar scanning while still confusing the less common steps where an attacker gains control. Analysts need to know both **whether an attack is happening** and **what dangerous action is happening next**.

Our first AIT development pilot illustrates that distinction. Binary logistic regression achieved99.994% F1 on the selected held-out source lines, but detected70/81 escalation lines. A separate classifier tasked with actually naming the escalation step achieved73.958% F1, with71 true predictions,40 false predictions and10 misses. These are two different tasks. The12 author labels overlap, and the test contains only two emulated runs.

The frozen models were also scored on48,838 additional time-qualified author-rule-nonmatch lines from those same test runs. Logistic regression flagged420 (0.860%), random forest5,991 (12.267%), and gradient boosting4,366 (8.940%). This reinforces the observed model tradeoff on additional background files. It remains development evidence from the same source environment and imperfect author labels.

## Recommended research question

**Can a model use earlier related events to identify consequential attack steps more accurately, especially when some logs are delayed or missing, without increasing false alerts?**

Candidate working title: **Recognizing High-Risk Attack Steps under Incomplete Telemetry**.

## What to compare

1. Preserve the current isolated-event linear model as a simple reference.
2. Give a tabular model, a small temporal sequence model and a source-grounded graph model the same past-event budget. The tabular comparator must receive matched history summaries so extra information is not confused with a better algorithm.
3. Test one precise mechanism: distinguish an observed absence from information that has not arrived, retain bounded state for those unresolved relations, and permit late events to affect only subsequent predictions. Compare ordinary arrival-order updates, a lateness buffer, missingness indicators and dropout training.
4. Measure step-name F1/precision/recall, binary false positives, missed episodes and usable warning delay. Require actual impact/exposure labels before claiming warning before harm or alarms per host-hour.
5. Repeat the supported target on a second independently generated dataset. AIT-ADS is the same underlying environment as AIT-LDS, so it does not satisfy this requirement. cAPTure can support a network-specific comparison after its causal feature and reduction audit; CasinoLimit supports a separate stage/technique task with no realistic benign baseline.

## An attainable development target

An exploratory target such as improving escalation-identification F1 from about0.74 by0.05 is mathematically attainable. It is **not yet a registered confirmatory hypothesis**: the baseline came from an exposed pilot, only81 correlated escalation lines support it, and another dataset may use different labels. Before confirmation, select a primary target and alert budget on development data, check sample/episode support and freeze a new evaluation. Do not try to improve near-ceiling pooled binary F1 by five percentage points.

## Novelty check

There is a plausible applied research direction, but no established novelty or positive new-method result yet. These are important overlaps:

- [Sometimes Simpler is Better, USENIX Security2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) already compares eight provenance detectors and demonstrates the value of simpler models.
- [TREC, CCS2024](https://doi.org/10.1145/3658644.3690221) already studies tactic/technique recognition from provenance. Graph-based stage recognition alone is not new.
- [cAPTure, Computer Networks2026](https://doi.org/10.1016/j.comnet.2026.112570) already studies detection time against false positives and supplies timestamp-jitter variants. Timing robustness alone is not a new contribution.
- [Kairos, IEEE S&P2024](https://tfjmp.org/publications/2024-sp.pdf) already uses temporal provenance context for detection and reconstruction.
- [StageFinder / Learning the APT Kill Chain, author v2](https://arxiv.org/abs/2603.07560v2) combines fused provenance graphs and an LSTM for stage recognition. Rechecked September 20, 2026: the author record reports acceptance to IEEE GLOBECOM 2026; a publisher proceedings entry was not independently verified. This is direct overlap, not an open generic graph-plus-history idea.
- [IMPROV / Minding the Gap, PRISM 2026](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf) addresses missing provenance context, identity problems and event ordering using collection-time OS information. The [official accepted-paper list](https://www.ndss-symposium.org/ndss2026/co-located-events/prism/accepted-papers/) confirms its workshop status. Generic missing/late-event handling is also occupied; any proposed mechanism needs a narrower contribution and comparison.

A defensible contribution would require a clearly different treatment of missing/late evidence, a reproducible benefit over these relevant controls, and validation beyond the original easy/repeated patterns. Simply substituting Qwen, a Transformer or a GNN is insufficient evidence of novelty.

## Historical pilot decision

**Continue with the benchmark and the rare-step/context question.** It has a measurable weakness to address and accessible source data. The current result establishes working infrastructure and a model tradeoff. It does not yet establish a completed positive praxis experiment.

**Diagnostic update, September 20:** the targeted error review found 23 wrong escalation assignments whose normalized text is identical to escalation-positive lines, plus one missed command-fragment line sharing normalized text with opposite-labeled records. The next gate is to audit source-label scope and restore meaningful event/context information before an architecture comparison. See [the ordered next experiment](NEXT_EXPERIMENT.md). This finding narrows the next test; it is not a new-method improvement result.
