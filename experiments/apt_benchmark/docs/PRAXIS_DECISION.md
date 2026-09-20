# Praxis opportunity revealed by the first comparison

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
- [Learning the APT Kill Chain, March2026 preprint](https://arxiv.org/abs/2603.07560) is direct stage-estimation overlap; a peer-reviewed venue was not verified in this review.

A defensible contribution would require a clearly different treatment of missing/late evidence, a reproducible benefit over these relevant controls, and validation beyond the original easy/repeated patterns. Simply substituting Qwen, a Transformer or a GNN is insufficient evidence of novelty.

## Decision now

**Continue with the benchmark and the rare-step/context question.** It has a measurable weakness to address and accessible source data. The current result establishes working infrastructure and a model tradeoff. It does not yet establish a completed positive praxis experiment.
