# Praxis decision and research history

## Current decision: completed lateral-protection study

**The tested method did not establish reliable false-alarm reduction while preserving lateral-movement detection.** All 19 groups and 152 final models completed, and the independent source audit passed. The primary development screen is **INFEASIBLE**, because four of ten seeds could not select a policy satisfying the frozen requirements. All secondary screens are also infeasible: zero of three seeds at 32 benign fitting labels and one of three at each of 128 and 512 labels were feasible. Every arm retained the same 160 attack fitting labels.

Among the six feasible primary seeds only, mean verification false-positive rate fell from **0.7195% to 0.4800%**, while detection of author-labeled lateral flows fell from **88.19% to 84.49%**. The loss exceeds three percentage points and detection remains below the 90% floor. These are matched-subset descriptive means; excluding the four infeasible seeds cannot turn the ten-seed primary result into success. This measures whether a lateral flow is flagged as any attack, not correct stage naming, actor attribution, or warning before harm. SCVIC remains exposed development data, and repeated fitting seeds are not independent incidents.

DEDALE supplied a separate but very small external stress test: 100,000 hash-sampled benign flows and four author-labeled lateral flows from **one execution**. The fixed source seed had no feasible candidate, so only ordinary controls were evaluated. Argmax produced **7,418 false positives and detected one of four lateral flows**; the threshold calibrated to an empirical 1% source-benign tail produced **24,511 false positives and detected all four**. Source calibration did not preserve a 1% false-positive rate on the external data. No target fitting or calibration occurred, and the sampled prevalence does not support deployment precision estimates.

The contribution currently supported is an auditable empirical account of this tradeoff and the tested method's limits. **No novel validated method or independent lateral-protection confirmation is established.** The work ran on CPU; 40 new implementation and integrity tests passed for this study, separate from historical suite counts. Before proposing a further mechanism as a solution, qualify multiple independent lateral executions with defensible benign exposure and freeze a new comparison without treating these exposed results as fresh confirmation.

- [Completed design and results overview](../lateral_protection_experiment/README.md)
- [Public evidence and receipts](../results/lateral_protection_v1/REPORT.md)
- [Empirical paper](../lateral_protection_experiment/paper/PRAXIS.md), [Word](../lateral_protection_experiment/paper/PRAXIS.docx), [PDF](../lateral_protection_experiment/paper/PRAXIS.pdf)
- [Preserved original proposal](../lateral_protection_praxis/README.md) and [DEDALE qualification](../lateral_protection_experiment/dedale/QUALIFICATION.md)

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
