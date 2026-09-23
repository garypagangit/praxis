# Claim audit across PX-080, PX-081 and PX-082

Read-only synthesis of completed outputs, 23 September 2026. No new fits, thresholds, searches or acceptance rules. Numbers are means over three fits on repeated evaluation events, not independent campaigns.

## Strongest defensible measured positive

**The clearest substantial result is evaluation sensitivity, not a validated new detector.** PX-082 held 104,051 later-period anchor rows fixed, excluded their current-feature fingerprints from both training pools, and matched training class counts. Allowing other later-period rows into training raised macro-F1:

- Current evidence: **.7365 → .7997**, a .0632 increase.
- Current plus history: **.7582 → .7964**, a .0383 increase.

This is a measured difference attributable to the changed training pool under that design. It does not isolate future access from the distributional variety it introduces, demonstrate misconduct or leakage in another paper, or establish a deployable improvement. The anchor contains only 18 author movement annotations. [PX-082 report](../px082_temporal_audit/REPORT.md).

There is also a favorable chronological detector comparison worth retaining: in PX-082's past-only arm, adding history increased macro-F1 **.7365 → .7582**, movement F1 **.2091 → .2836**, and exfiltration F1 **.7565 → .7671**, while mean benign false alerts fell **24.0 → 14.33**. Macro-F1 improved and false alerts decreased in all three seeds. However, the movement-recall increase **25.93% → 29.63%** came from two additional correct movement labels in one seed; the other two seeds were unchanged. Exfiltration-to-benign errors also increased: **565/563/563 → 572/569/571** across the three fits. This is a useful limited positive, not an across-metric dominance claim. These cross-view details are a supplementary reading of the saved results, not PX-082's primary same-anchor training comparison. [Scores](../px082_temporal_audit/METRICS.json).

## What the two proposed methods achieved

| Study | Favorable measured behavior | Cost or counterexample |
|---|---|---|
| PX-080 harm-sensitive context selector | Higher movement recall than matched ordinary gating in all five conditions; clean **64.76% → 69.52%**, five-minute stale **49.52% → 63.81%**. | More benign false alerts and worse stage-weighted error in all five conditions. Current-plus-roles alone retained **78.10%** movement recall. Ordinary context-dropout training recovered **68.57%** under entirely missing history, versus **42.86%** for the proposed gate. |
| PX-081 error-focused acquisition | At budget 3, simulated spend was **32.24% lower** than entropy acquisition in clean replay and **26.12% lower** under delayed/unavailable replay. | Weighted errors were worse than entropy in both comparisons. Clean movement recall was **69.52%**, below current-only **78.10%**. Under deliberately wrong-host history, weighted errors were **53.81% higher** than current-only. |

Sources: [PX-080 means](../px080_context_selector/results/MEANS.json), [PX-081 aggregate](AGGREGATE.json). Different features, training specifications and evaluation subsets prevent ranking architectures by their raw scores across experiment numbers.

## The macro-F1 trap is concrete

In PX-081 at budget 3, error-focused acquisition improved macro-F1 over entropy acquisition in clean replay, **.7148 → .7379**, and delayed replay, **.7180 → .7427**. Yet exfiltration recognized as any attack fell **85.18% → 76.25%** and **81.00% → 69.20%**, respectively. Some inter-stage confusion was replaced by benign predictions. The any-attack analysis was added after first-seed inspection and is explicitly supplementary; it uses preserved confusion matrices without changing fits.

Thus “better macro-F1” and “less likely to hide an attack” are different empirical claims. The declared true-class weights 1/1/4/4 do not resolve this: they penalize a wrong attack-stage label and a benign prediction equally for a given true class.

## One practical engineering conclusion

**Before selecting a context or acquisition policy, keep a current-evidence baseline and separately report benign-to-attack errors, attack-to-benign errors, and inter-stage errors under each missing/stale/mislinked condition.** The saved tables demonstrate why macro-F1 or exact-stage recall alone can reward a policy that suppresses useful attack warnings. This is an evaluation/selection safeguard supported by the results, not a newly proven detection algorithm or a no-harm guarantee.

## Exact gap not filled

These runs do not establish a method that preserves dangerous-stage recognition at a comparable false-alarm workload when supporting evidence changes, nor that movement predicts later exfiltration. They do not demonstrate algorithm novelty, real acquisition savings, recovery of unobserved information, early warning, verified successful movement/theft, or independent-campaign transfer. All share the same already-examined UNRAVELED artifact; 35 full-evaluation movement rows, 18 anchor rows, augmented copies and fitting seeds must never be added into a larger independent attack count. The audits establish arithmetic, source and split/inference integrity, not the correctness of the author's attack truth.

A subsequent dataset replication could strengthen an evaluation-sensitivity claim if qualified and completed. It would not retrospectively turn the mixed PX-080/PX-081 results into a successful novel method.
