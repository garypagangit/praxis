# Fewer False Alarms Did Not Produce Reliable Attack Detection

**Complete and independently audited.** See [the report](REPORT.md) for the design, limitations, and evidence chain.

## Main finding in plain language

Teaching the alert rule to tolerate incomplete normal records greatly reduced false alarms. However, it also suppressed alerts for malicious activity. The small neural model is the clearest example: with half of the retained relationships removed, its average malicious-entity detection rate fell from **50.7908% to 0.0789% on CADETS**, and from **42.5248% to 0.0298% on THEIA**. The revised rule missed more than 99.9% of annotated malicious entities on average in both datasets under that condition.

This is evidence that the tested calibration repair can make a detector quiet without making it reliable. It does not demonstrate a checker that recognizes the difference between missing information and an attack.

## The small neural model: exact comparison

The comparison changes complete-only calibration to pooled complete-and-incomplete calibration, keeping the same complete reference bank and anomaly scores. Every entry below is an arithmetic mean across the 36 fixed fold/model-seed/bank-seed combinations for that dataset and condition. Percentages are rounded to four decimals for display; decisions use unrounded values.

| Dataset / condition | Normal-validation false alerts, before → after | Benchmark-negative false alerts, before → after | Malicious entities detected, before → after |
| --- | --- | --- | --- |
| CADETS / complete | 1.0046% → 0.1641% | 1.0273% → 0.1711% | 0.3324% → 0.1226% |
| CADETS / 50% relationships removed | 49.4873% → 0.8727% | 49.3920% → 1.0129% | 50.7908% → 0.0789% |
| THEIA / complete | 1.0079% → 0.2411% | 1.0077% → 0.2540% | 2.4139% → 0.0276% |
| THEIA / 50% relationships removed | 49.8458% → 0.8682% | 48.8615% → 0.8790% | 42.5248% → 0.0298% |

Normal-validation false alerts use the separately reserved graph assumed benign by the upstream preparation. Benchmark-negative false alerts use entities without supplied malicious annotations in the attack-bearing graph; those entities are not exhaustively verified benign.

The pooled-calibration model passes the normal-stability screen on both datasets. It fails attack readiness: recall is below 50% in **all 72 evaluated cases per dataset**, covering both conditions, and CADETS also exceeds the 2% benchmark-negative false-alert ceiling in four cases. Its mean missing-relationship F1 falls from **0.068974 to 0.001184** on CADETS and **0.112053 to 0.000519** on THEIA. Low false-alert rates therefore do not rescue this candidate.

## Why all nine candidates fail

Required in every case: **normal false-alert rate ≤2%; benchmark-negative false-alert rate ≤2%; malicious recall ≥50%**. The same candidate must pass both datasets. In the table, each dataset cell shows **worst normal false-alert % / worst benchmark-negative false-alert % / lowest recall %**, across both conditions and all applicable combinations. `N`, `F`, and `R` identify failed requirements respectively. Different extremes may come from different cases.

| Strategy / representation | CADETS: N / F / R (%) | Failed gates | THEIA: N / F / R (%) | Failed gates |
| --- | --- | --- | --- | --- |
| Complete only / activity features | 9.3689 / 9.6217 / 0.0778 | N, F, R | 5.4596 / 6.7792 / 0.0592 | N, F, R |
| Complete only / small neural model | 52.7161 / 52.2100 / 0.2569 | N, F, R | 51.0137 / 49.3808 / 0.0948 | N, F, R |
| Complete only / graph neural model | 82.3376 / 77.6550 / 0.0000 | N, F, R | 58.2750 / 61.0290 / 0.0316 | N, F, R |
| Mixed calibration / activity features | 1.7919 / 2.1724 / 0.0778 | F, R | 1.2182 / 1.3958 / 0.0553 | R |
| Mixed calibration / small neural model | 1.8963 / 2.3309 / 0.0000 | F, R | 1.7667 / 1.7490 / 0.0079 | R |
| Mixed calibration / graph neural model | 1.4599 / 1.3525 / 0.0000 | R | 3.9098 / 3.7001 / 0.0000 | N, F, R |
| Mixed reference and calibration / activity features | 1.5825 / 1.7936 / 0.0778 | R | 1.3893 / 1.2202 / 0.0355 | R |
| Mixed reference and calibration / small neural model | 2.0263 / 2.0922 / 0.0467 | N, F, R | 1.4147 / 1.4951 / 0.0434 | R |
| Mixed reference and calibration / graph neural model | 66.8597 / 63.5379 / 0.0000 | N, F, R | 2.0052 / 3.1539 / 0.7939 | N, F, R |

All nine candidates fail detector readiness on **each** dataset; none passes even at dataset-specific scope. Four candidates per dataset pass normal stability, with three shared across datasets. Those normal-only passes do not satisfy the detector requirements. The 2.0052% and 2.0263% normal false-alert rates remain failures under the fixed 2% ceiling.

Local activity features have 12 unique combinations per condition and 24 across both; learned representations have 36 and 72 respectively. Local-feature copies across model seeds are identical and excluded from unique counts. The complete run contains **1,296 logged records and 1,008 unique records in each of the normal and attack phases**. These are descriptive repeated cases, not independent campaigns or statistical replications.

## The improved graph-model average that must not be overstated

THEIA's mixed-reference-and-calibration graph model has a mean missing-relationship F1 of **0.426794**, compared with **0.225796** for the strongest fixed complete-only representation under the same condition: a gain of **0.200998**. Its mean clean F1 is **0.807114**, compared with **0.755666** for the complete-only graph model. These are real descriptive improvements in the saved aggregate results.

They do not establish reliability. Its mean missing-relationship recall is only **35.5637%**, its minimum is **0.7939%**, its worst benchmark-negative false-alert rate is **3.1539%**, and its worst normal false-alert rate is **2.0052%**. It fails recall in 32 of 72 cases, benchmark-negative false-alert control in seven, and normal stability in one. On CADETS, the same strategy has normal false alerts as high as **66.8597%** and benchmark-negative false alerts as high as **63.5379%**. An improved THEIA average cannot override those failures or support a cross-dataset success claim.

The reported general-readiness and positive-repair candidate lists are both empty. No candidate reaches all required gates; the registered F1 improvement screens do not replace the reliability requirements.

## Recommendation for the praxis decision

**Both audits passed: close this fixed repair family as a completed no-go.** Preserve the result as useful negative evidence: pooled calibration can solve the superficial false-alert symptom while removing attack sensitivity. Do not carry this particular repair forward as a demonstrated successful or novel checker, weaken the gates afterward, or select a favorable seed to change the conclusion.

This result does not disprove the broader graph-learning praxis direction. The tested lightweight models and calibration strategies do not cover all graph architectures, the full MAGIC method, actor attribution, or alternative learning methods. A broader praxis claim remains unresolved and would need evidence and a distinct contribution beyond this closed comparison. This report does not introduce or authorize a new experiment.

The existing [verified literature assessment](../../../embedding_baseline/results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md) already places augmentation, graph calibration, and missingness-aware uncertainty near prior work. These results neither establish novelty nor convert known calibration methods into a new contribution.
