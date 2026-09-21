# Lateral-movement protection: completed development results

**Primary decision: INFEASIBLE.** All 152 final models and 19 groups completed; independent artifact/metric consistency audit passed. This is source development, not independent confirmation.

## Primary verification: 1,024 benign fitting examples

Rates below are means over the listed fitting seeds on the same 15,392 verification flows (14,965 benign; 72 lateral). Feasible subsets, if any, cannot replace the all-ten-seed gate.

| Policy | Seeds | Benign FPR | Lateral detection | Attack recall | Attack F1 |
| --- | --- | --- | --- | --- | --- |
| Lateral-sensitive reference | 6 | 0.719% | 88.194% | 97.580% | 0.8770 |
| Constrained candidate | 6 | 0.480% | 84.491% | 95.980% | 0.9044 |
| Threshold-only ablation | 6 | 0.574% | 84.954% | 96.565% | 0.8934 |
| Natural tree, argmax | 10 | 0.351% | 78.750% | 95.597% | 0.9200 |
| Natural tree, benign 1% threshold | 10 | 0.956% | 85.278% | 97.400% | 0.8438 |

**Different seed sets:** reference/candidate/threshold-only rows cover feasible selections; ordinary controls cover every seed. Their unpaired means must not be interpreted as a candidate-versus-ordinary improvement. EVIDENCE.json includes matched-feasible-control means separately, which remain a selected-subset diagnostic, not the primary result.

- Lateral-sensitive reference: seeds 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.
- Constrained candidate: seeds 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.
- Threshold-only ablation: seeds 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.
- Natural tree, argmax: seeds 20260921, 20260922, 20260923, 20260924, 20260925, 20260926, 20260927, 20260928, 20260929, 20260930.
- Natural tree, benign 1% threshold: seeds 20260921, 20260922, 20260923, 20260924, 20260925, 20260926, 20260927, 20260928, 20260929, 20260930.

## Every primary seed

| Seed | Status | Reference FP / lateral TP | Candidate FP / lateral TP | Same as threshold-only? |
| --- | --- | --- | --- | --- |
| 20260921 | INFEASIBLE | Unavailable | Unavailable | Unavailable |
| 20260922 | SELECTED | 140 / 59 | 140 / 59 | True |
| 20260923 | SELECTED | 131 / 67 | 97 / 67 | True |
| 20260924 | INFEASIBLE | Unavailable | Unavailable | Unavailable |
| 20260925 | SELECTED | 139 / 62 | 63 / 60 | False |
| 20260926 | INFEASIBLE | Unavailable | Unavailable | Unavailable |
| 20260927 | SELECTED | 73 / 67 | 9 / 60 | False |
| 20260928 | SELECTED | 105 / 62 | 105 / 62 | True |
| 20260929 | INFEASIBLE | Unavailable | Unavailable | Unavailable |
| 20260930 | SELECTED | 58 / 64 | 17 / 57 | True |

## Secondary normal budgets

| Normal budget | Feasible groups | Frozen point-screen decision |
| --- | --- | --- |
| 32 | 0/3 | INFEASIBLE |
| 128 | 1/3 | INFEASIBLE |
| 512 | 1/3 | INFEASIBLE |

Secondary outcomes do not rescue a failed primary endpoint. Full stage/ranking/classification results are in EVIDENCE.json and CELL_METRICS.json.

## Audit and claim boundaries

The audit independently reconstructs supports, partitions, weights, threshold choices, saved metrics and exact decision inequalities. It does not retrain models, independently relabel attacks, or create independent incidents. All failures remain visible.

Training weights and constrained thresholds are established methods. This experiment tests an applied tradeoff; no algorithmic novelty, early-warning claim, production suppression approval, or measured analyst-time savings is established.

## Limited DEDALE external stress

Fixed source seed 20260921; 100,000 unique sampled benign and 4 lateral flows from one execution. No target fitting or calibration.
Source selection status: **INFEASIBLE**. Missing policies: reference, candidate, threshold_only. When the source candidate is infeasible, these results describe the ordinary controls only; no proposed candidate is tested.

| Source-locked policy | False benign alerts | Lateral detections | FPR |
| --- | --- | --- | --- |
| Natural tree, argmax | 7,418/100,000 | 1/4 | 7.418% |
| Natural tree, benign 1% threshold | 24,511/100,000 | 4/4 | 24.511% |

One attack execution and at most four lateral rows cannot confirm a 3pp noninferiority margin. Sampled prevalence makes precision/F1 descriptive only. No independent-incident confidence intervals.

