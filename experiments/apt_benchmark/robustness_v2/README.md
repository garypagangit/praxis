# Recognizing attack steps when command records disappear

This frozen follow-up tests whether ordinary record-type augmentation and visible-input specialists repair the structured-loss failures in the [completed baseline suite](../results/robustness_v1/SUMMARY.md). These are existing methods, not a claimed new algorithm.

## Fixed comparison

Six arms share the same features, classifier settings, source events, and execution splits: semantic event, entity context, random dropout, type dropout, mixed dropout, and an observed-record router. Only the last three are new controls. The [protocol](protocol.json) fixes all conditions and three random-removal seeds before fitting. The [independent design review](../docs/ROBUSTNESS_V2_DESIGN_REVIEW.md) records the novelty and validity limits.

The primary comparison is mixed dropout versus random dropout. For each target, all five descriptive requirements must pass at a threshold selected only from clean calibration data:

- Command-record-loss F1 improves by at least 0.05.
- Command-record-loss recall declines by no more than 0.02.
- Other-technique flag rate increases by no more than 0.005.
- Clean F1 declines by no more than 0.02.
- Mean F1 under 50% random record loss declines by no more than 0.02.

These are development screening gates, not confidence bounds or a statistical noninferiority test. Secondary arms remain secondary even if they outperform the primary arm.

## What the router can see

Four specialist states represent whether the current visible event contains EXECVE, PROCTITLE, both, or neither. The router never receives the deletion mask or hidden records. Each specialist requires at least five distinct positive and 25 distinct negative fit targets with observed evidence. Repeated augmented views do not inflate this support. Unsupported states use the mixed-dropout model. Fully invisible targets receive no alarm in every arm and remain in scoring denominators.

The router can contain five logistic regressions, including its fallback, so its parameter and runtime costs are reported. Augmented rows have weight one divided by the number of views; observed-only specialist rows keep that same weight.

## Data and claim limits

- AIT escalation and CasinoLimit T1068/T1548/T1105 are exposed development tasks. Existing v1 source bytes, splits and results are preserved.
- CAM-LDS T1105 is a conditional external family-held-out check using a different interval-state proxy. First events in fixed ten-second host bins are chosen without labels, then scored only inside author-labeled step intervals. Complete audit-event history remains available subject to the same causal horizon. This is not exact malicious-event onset, verified benign discrimination, or all-stage APT detection.
- Calibration and test positives are correlated events, often from few executions. A 1% calibration other-label flag budget can fail under shift; actual test rates must be shown.
- Removing audit record types simulates missing records, not a whole sensor outage. Full-delay recovery is a buffering control by construction.
- S-DAPT-2026 remains [conditionally registered](../sdapt2026/README.md), pending qualified raw data and corrected source evidence.

### CAM-LDS source qualification amendment, before its fit

The [CAM-specific protocol](camlds_protocol.json) corrects supervision wording after inspection of the pinned author extractor: source intervals are padded and manually adjusted manifestation windows. The target is whether the query belongs to an author-designated T1105 manifestation window, not whether a specific event transfers a tool or the technique is literally executing. Unrelated and idle host events can inherit the scenario-window label. This narrows CAM to a separate-source exploratory proxy; it cannot directly confirm Casino onset recognition. Model arms, parameters, splits, perturbations, calibration, and gates remain unchanged. The base protocol and completed AIT/Casino receipts are preserved.

## Reproduction and audit

Run from the repository root using the pinned benchmark environment. The feature cache streams one source execution at a time; optional `--base-cache` reuses only hash-verified unchanged v1 chunks. No model fitting happens during cache preparation.

```powershell
python -m experiments.apt_benchmark.robustness_v2.feature_cache --events EVENTS.jsonl --manifest MANIFEST.json --protocol experiments/apt_benchmark/robustness_v2/protocol.json --output PRIVATE_CACHE
python -m experiments.apt_benchmark.robustness_v2.run --events EVENTS.jsonl --manifest MANIFEST.json --dataset casino --feature-cache PRIVATE_CACHE --output PRIVATE_RUN
python -m experiments.apt_benchmark.robustness_v2.audit --run PRIVATE_RUN --events EVENTS.jsonl --manifest MANIFEST.json --feature-cache PRIVATE_CACHE --protocol experiments/apt_benchmark/robustness_v2/protocol.json --output PRIVATE_AUDIT
```

The run writes a pre-fit receipt binding raw protocol bytes, source events, source manifest, feature cache and implementation hashes. It saves private model bundles and calibration/test predictions. The separate auditor recomputes metrics, labels, target ordering, observation masks, calibration thresholds and primary gate decisions. Its saved-model inference uses calibration data only. This is an AI/code calculation audit, not human label adjudication. Only aggregate reports and receipts are published.
