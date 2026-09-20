# When Fewer Cybersecurity Alerts Hide More Attacks

## Decision

**The completed comparison supports a no-go for this fixed repair family.** None of the nine candidates met the declared detection requirements on either dataset. Some changes reduced false alerts dramatically, and one graph-model comparison improved its average score, but these gains did not produce reliable attack detection across the required cases.

The practical lesson is simple: making a detector quieter does not necessarily make it better. This result closes the tested calibration and reference-bank repairs. It leaves the broader graph-learning praxis direction unresolved.

## Problem and hypothesis

Cybersecurity systems connect recorded activities, such as a program opening a file or contacting another computer. If some connections are missing, ordinary activity can look unusual. That can flood analysts with false alerts.

We tested this hypothesis: **showing a detector incomplete examples of normal activity, when establishing its reference examples or setting its alert rule, can reduce false alerts while preserving attack detection.** Calibration means using reserved normal examples to set that rule. This comparison detects annotated malicious entities; it does not identify an APT group or determine which absent connections were actually lost during collection.

## What we ran

We used the audited DARPA TC E3 CADETS and THEIA graphs distributed by the [MAGIC authors](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian). For each dataset, four rotations reserved two normal graphs for fitting, one for calibration, and one for checking normal behavior. Three model seeds were crossed with three independent reference-sampling seeds.

The study trained **48 models in 24 model/cache sets**: a small neural model, MLP, and a graph neural model, GIN, for each dataset, rotation, and model seed. Simple activity features provided a third representation. Each representation was evaluated with three strategies:

1. Complete normal reference examples and complete calibration.
2. Complete reference examples with mixed complete/incomplete calibration.
3. Mixed reference examples with mixed calibration.

All nine combinations used the same 8,192-row reference budget and scored an entity by its distance from its ten nearest normal reference examples. The mixed reference used 4,096 complete and 4,096 incomplete views of distinct prepared training rows. We evaluated intact prepared graphs and one fixed 50% removal of their retained relationships, shared across candidates. These prepared graphs do not establish complete real-world activity records.

The completed evidence contains **1,296 records per phase: normal validation and attack evaluation**. Removing identical activity-feature copies across model seeds leaves **1,008 unique records per phase**. These are repeated development cases, not independent campaigns. All normal preparation was frozen before attack-label evaluation within this run; earlier test exposure remains acknowledged. A separately registered runtime continuation reused completed model/cache sets and rebuilt reference banks, calibration, and scores. See the [scientific registration](../../REGISTRATION.json) and [continuation registration](../../../normal_stability_continuation/REGISTRATION_EBS_DATA_FIX.json).

## What happened

The small neural model shows the central tradeoff. Adding incomplete normal examples to calibration produced the following averages when half the relationships were removed:

| Dataset | Normal false alerts: original → mixed calibration | Malicious entities detected: original → mixed calibration |
| --- | --- | --- |
| CADETS | **49.49% → 0.87%** | **50.79% → 0.079%** |
| THEIA | **49.85% → 0.87%** | **42.52% → 0.030%** |

These means cover 36 fixed combinations per dataset. After the change, the model missed more than 99.9% of annotated malicious entities on average in this condition. Detection on complete graphs was already weak and also declined: 0.3324% to 0.1226% on CADETS, and 2.4139% to 0.0276% on THEIA. The lower alert rate did not demonstrate an ability to distinguish missing evidence from malicious behavior.

The fixed requirements were normal false alerts at most 2%, benchmark-negative false alerts at most 2%, and malicious recall at least 50%, in every case and both conditions. A positive repair additionally required mean F1 gains of at least 0.05 over the pinned historical clean comparator and the strongest current clean-strategy masked comparator; the historical comparison changes fitting roles and is descriptive. All nine candidates failed detector readiness on each dataset. Four per dataset passed normal stability, including three shared candidates, but a normal-only pass was insufficient. No candidate qualified as a positive repair. The [detailed findings](DETAILED_FINDINGS.md) and [full results](FULL_RESULTS.md) retain the failures and comparison scores.

## An improved average that still failed

On THEIA, the graph model with mixed reference and calibration achieved missing-relationship mean F1 **0.426794**, versus **0.225796** for the strongest complete-only strategy: a gain of **0.200998**. F1 combines precision and recall. Its mean complete-graph F1 also improved, from 0.755666 to 0.807114 compared with the complete-only graph model.

However, missing-relationship recall averaged only **35.56%**, with a minimum of **0.79%**. Its worst benchmark-negative false-alert rate was **3.1539%**, and its worst normal false-alert rate was **2.0052%**. On CADETS, the same candidate reached **66.8597%** normal false alerts. These failures prevent a reliability claim; the result is not merely a rounding issue near the 2% ceiling.

Results also varied with random seeds. For CADETS's complete-only GIN on complete graphs, the mean normal false-alert range associated with changing the model seed was **26.44 percentage points**, versus **5.69** when changing the reference-bank seed. These are descriptive ranges while holding the other seed fixed, not causal effects or additive shares of variation. See [factor variability](FACTOR_VARIABILITY.md).

## Meaning for the praxis

Close this fixed family as unsupported for the declared purpose. Preserve the negative evidence and the improved averages together. Do not reinterpret a quiet detector or a favorable seed as a successful checker.

This comparison does not test every graph architecture or reproduce the full MAGIC method. It neither disproves graph learning nor establishes a novel praxis contribution. The [prior literature assessment](../../../embedding_baseline/results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md) identifies existing augmentation and calibration work; adopting those ideas alone does not establish novelty.

The datasets were previously exposed during development. Missing identifiers and timestamps prevent verifying independent entities or campaigns across files; rotations overlap. Normal labels rely on upstream filtering, and unannotated test entities are not exhaustively verified benign. One simulated removal pattern does not establish resilience to real logging failures. No operational analyst workload was measured. Broader human and source-evidence requirements are documented in [Human Requirements](../../analysis/HUMAN_REQUIREMENTS.md); no completed external review is claimed.

## Verification and resource record

**PASS: scientific audit, continuation-chain audit, and exact replay verification**

The verification package contains [the scientific audit](INDEPENDENT_AUDIT.json) and [the continuation-chain audit](CONTINUATION_CHAIN_AUDIT.json). The scientific audit recomputed all score-derived metrics and decision gates, and checked 20,736 sampled query checks (eight distinct queries per score array, across 2,592 arrays) using direct float64 distances (maximum absolute error 1.46e-11). It did not independently rerun neural inference or every distance calculation. The [exact replay check](EXACT_REPLAY_CHECK.json) matched all 1,296 earlier normal records and 108 completed attack records without tolerance; the continuation audit verified all 504 reused files across 24 sets, with zero fresh fits. **170 software tests passed.** Software tests and successful execution do not establish detector effectiveness. The evidence audits and verified cloud closeout are complete; no additional variant is pending as part of this fixed study. See [software qualification](QUALIFICATION.json).

Estimated compute: **$1.631** across all four attempts. All attempts are verified stopped and their watchdogs removed. This is an elapsed-time estimate, not an invoice, and excludes storage, transfer and other services. The [AWS closeout](AWS_CLOSEOUT.md) preserves the timeout and two bootstrap failures. No human action is required to close this development comparison; the external-review steps are documented for any broader claims.
