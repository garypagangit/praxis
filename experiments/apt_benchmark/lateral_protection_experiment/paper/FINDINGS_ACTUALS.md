# Actual improvements and their tradeoffs

**Status: posthoc descriptive findings from completed, audited experiments.** The original ten-seed joint screen remains **INFEASIBLE** (six feasible selections; four infeasible). These findings describe what improved and what it cost; they do not replace that result.

## 1. Scope and reading the numbers

- All-ten scope: 20260921, 20260922, 20260923, 20260924, 20260925, 20260926, 20260927, 20260928, 20260929, 20260930.
- Matched-six feasible scope: 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.
- Infeasible primary seeds: 20260921, 20260924, 20260926, 20260929.
- Each primary model used 1,184 fitting labels: 1,024 normal plus 160 attack. Selection used 15,390 labeled rows; verification used 15,392 (14,965 normal, 427 attack, including 72 lateral); the original development test used 30,787 (29,929 normal, 858 attack, including 144 lateral). These same evaluation rows repeat across seeds.
- All numbers below are arithmetic seed means. A fractional detection/false-alert count is a mean count, not part of a row. Percentage-point differences are abbreviated **pp**. Relative false-alert reduction is calculated from the ratio of mean counts.
- **Lateral alert recall** counts lateral rows identified as any attack. It does not require naming the correct attack stage. **Exact-stage recall** does.
- The source data were already exposed in development. Seed averages are not independent incident evidence. Allocated fitting labels are not the total label acquisition cost; support sampling, calibration and evaluation use the larger known-label pool.

## 2. What improved on the six matched feasible selections?

The most defensible positive description is a **measured operating tradeoff**. It is conditional on the six feasible selections, not a positive result across all ten.

### Verification operating points

| Locked policy | Mean false alerts / 14,965 normal | Normal FPR | Mean lateral detected / 72 | Lateral alert recall | All-attack recall | Mean total alerts / 15,392 |
|---|---:|---:|---:|---:|---:|---:|
| Constrained candidate | 71.833 | 0.480% | 60.833 | 84.491% | 95.980% | 481.667 |
| Lateral-sensitive reference | 107.667 | 0.719% | 63.500 | 88.194% | 97.580% | 524.333 |
| Threshold-only ablation | 85.833 | 0.574% | 61.167 | 84.954% | 96.565% | 498.167 |
| Natural tree, argmax | 53.000 | 0.354% | 57.000 | 79.167% | 95.667% | 461.500 |
| Natural tree, source-normal 1% threshold | 145.333 | 0.971% | 63.167 | 87.731% | 97.736% | 562.667 |

### Matched comparisons: improvement and cost

| A compared with B | Relative false-alert reduction (negative = increase) | Lateral alert-recall change | Mean false-alert change | Mean lateral detections change |
|---|---:|---:|---:|---:|
| Constrained candidate vs Lateral-sensitive reference | +33.282% | -3.704 pp | -35.833 | -2.667 |
| Constrained candidate vs Natural tree, argmax | -35.535% | +5.324 pp | +18.833 | +3.833 |
| Constrained candidate vs Natural tree, source-normal 1% threshold | +50.573% | -3.241 pp | -73.500 | -2.333 |
| Constrained candidate vs Threshold-only ablation | +16.311% | -0.463 pp | -14.000 | -0.333 |
| Threshold-only ablation vs Lateral-sensitive reference | +20.279% | -3.241 pp | -21.833 | -2.333 |
| Lateral-sensitive reference vs Natural tree, source-normal 1% threshold | +25.917% | +0.463 pp | -37.667 | +0.333 |
| Lateral-sensitive reference vs Natural tree, argmax | -103.145% | +9.028 pp | +54.667 | +6.500 |

**Interpretation:** The candidate reduced false alerts versus the lateral-sensitive reference by 33.282%, while lateral recall declined 3.704 pp (88.194% to 84.491%). Against ordinary argmax, it detected more lateral flows (+5.324 pp) while generating 35.535% more false alerts. Against the ordinary source-normal 1% threshold, it produced 50.573% fewer false alerts but lateral recall fell 3.241 pp. None is a cost-free improvement.

The threshold-only ablation already captures much of the reference-to-candidate reduction: it reduces false alerts by 20.279% versus the reference, with a 3.241 pp lateral-recall decline. Allowing the candidate to choose a different detector adds a further 16.311% false-alert reduction versus threshold-only (14 fewer per seed on average), with another 0.463 pp lateral-recall decline. Candidate and threshold-only choices were identical in four of six seeds. This supports a modest additional false-alert tradeoff, not proof that the extra selection step is necessary or generally superior.

### A modest positive comparison in both mean false alarms and mean lateral detection

Compared with the ordinary source-normal 1% threshold on these six seeds, the **lateral-sensitive reference** reduced mean false alerts from 145.333 to 107.667 (**25.917% fewer**) while mean lateral recall increased from 87.731% to 88.194% (**+0.463 pp**, a mean one-third of a lateral flow). This is a legitimate descriptive improvement in two aggregate metrics. It is small on detection, conditional on feasibility, and not an improvement in every seed or every attack stage.

| Quantity | Reference | Ordinary source-normal 1% threshold | Difference |
|---|---:|---:|---:|
| DataExfiltration: alert recall | 99.371% | 100.000% | -0.629 pp |
| InitialCompromise: alert recall | 100.000% | 100.000% | +0.000 pp |
| LateralMovement: alert recall | 88.194% | 87.731% | +0.463 pp |
| Pivoting: alert recall | 99.607% | 99.686% | -0.079 pp |
| Reconnaissance: alert recall | 99.197% | 99.799% | -0.602 pp |
| All-attack recall | 97.580% | 97.736% | -0.156 pp |
| Alert precision | 79.780% | 74.200% | +5.580 pp |
| Binary attack F1 | 0.877 | 0.843 | +3.348 pp |
| Alert fraction | 3.407% | 3.656% | -0.249 pp |

False-alert count improved/equaled/worsened in **5/0/1** seeds; lateral recall improved/equaled/worsened in **2/1/3**. Both strictly improved in **2/6**; both were no worse in **2/6**. Other-stage means show small losses for exfiltration, pivoting and reconnaissance.

| Seed | Reference false alerts | Ordinary-threshold false alerts | Reference lateral detected / 72 | Ordinary-threshold lateral detected / 72 |
|---|---:|---:|---:|---:|
| 20260922 | 140 | 166 | 59 | 60 |
| 20260923 | 131 | 140 | 67 | 64 |
| 20260925 | 139 | 132 | 62 | 62 |
| 20260927 | 73 | 138 | 67 | 64 |
| 20260928 | 105 | 154 | 62 | 64 |
| 20260930 | 58 | 142 | 64 | 65 |

On the previously exposed original development test, the same locked reference comparison gave 22.247% fewer false alerts and +0.116 pp lateral recall. That second partition is descriptive consistency, not independent confirmation. Every contrast, all stage deltas, and paired seed-direction counts for both partitions are in the companion JSON.

## 3. All ten seeds: fixed model and weighting arms

These eight model/weight arms were frozen before fitting, and all ten seeds are retained below. The favorable comparisons are **posthoc descriptive contrasts**, not preregistered positive endpoints. All use the same 1,184-label fitting budget and ordinary six-class argmax, with no new threshold. Weighting emphasizes attack classes during fitting; lateral2/lateral4 further emphasize the lateral class. CV-selected hyperparameters may differ across arms, so the comparison covers the full fitted treatment.

### Verification: complete eight-arm table

| Model / weights | Normal FPR | Lateral alert recall | Lateral exact-stage recall | All-attack recall | Six-class macro-F1 |
|---|---:|---:|---:|---:|---:|
| lightgbm/balanced | 0.611% | 84.583% | 63.611% | 96.838% | 0.6123 |
| lightgbm/lateral2 | 0.768% | 83.889% | 64.722% | 96.909% | 0.6072 |
| lightgbm/lateral4 | 0.815% | 84.722% | 64.444% | 97.002% | 0.5986 |
| lightgbm/natural | 0.378% | 78.889% | 61.528% | 95.574% | 0.6395 |
| xgboost/balanced | 0.931% | 85.139% | 65.278% | 97.119% | 0.5961 |
| xgboost/lateral2 | 1.143% | 86.667% | 66.806% | 97.471% | 0.5842 |
| xgboost/lateral4 | 1.286% | 87.917% | 69.167% | 97.681% | 0.5731 |
| xgboost/natural | 0.303% | 76.806% | 58.750% | 95.152% | 0.6550 |

### Previously exposed original development test: complete eight-arm table

| Model / weights | Normal FPR | Lateral alert recall | Lateral exact-stage recall | All-attack recall | Six-class macro-F1 |
|---|---:|---:|---:|---:|---:|
| lightgbm/balanced | 0.627% | 87.014% | 65.347% | 96.865% | 0.6306 |
| lightgbm/lateral2 | 0.797% | 86.944% | 67.222% | 96.865% | 0.6231 |
| lightgbm/lateral4 | 0.842% | 87.986% | 68.056% | 96.970% | 0.6205 |
| lightgbm/natural | 0.384% | 82.639% | 63.403% | 95.396% | 0.6587 |
| xgboost/balanced | 0.982% | 87.014% | 66.944% | 96.923% | 0.6129 |
| xgboost/lateral2 | 1.201% | 88.125% | 68.542% | 97.063% | 0.6026 |
| xgboost/lateral4 | 1.347% | 88.819% | 69.514% | 97.319% | 0.5904 |
| xgboost/natural | 0.313% | 79.931% | 60.278% | 94.907% | 0.6705 |

**Useful all-ten findings, with costs:**

- Balanced LightGBM increased verification lateral alert recall from 78.889% to 84.583% (**+5.694 pp**) and exact-stage recall from 61.528% to 63.611%. Normal FPR increased from 0.378% to 0.611%; macro-F1 declined from 0.6395 to 0.6123. Its verification mean FPR remains below 1%, but this is not a per-seed guarantee and its mean lateral recall remains below 90%.
- XGBoost lateral4 increased verification lateral alert recall from 76.806% to 87.917% (**+11.111 pp**) and exact-stage recall from 58.750% to 69.167% (**+10.417 pp**). Normal FPR increased from 0.303% to 1.286%, and macro-F1 declined from 0.6550 to 0.5731. Greater lateral sensitivity did not meet the false-alert budget.
- The full table is retained so these examples cannot hide alternative weights, their costs or lower scores. These are established weighting techniques, not evidence of a novel algorithm.

## 4. Earlier benign-label allocation experiment: a large practical improvement with a known cost

This is the earlier comparison in `strong_benign_controls_v1`, on all ten seeds and the original 30,787-row development test. Its label budgets are unequal: 192 labels (32 normal + 160 attack) versus 1,184 labels (1,024 normal + the same 160 attack). It is not a new matched-budget architecture test. The selected tree was chosen from the existing tree library by fit-pool cross-validation; the comparison includes that selection.

| CV-selected tree metric | 192 fitting labels | 1,184 fitting labels | Change |
|---|---:|---:|---:|
| Six-class macro-F1 | 0.4421 | 0.6543 | +0.2122 |
| Normal FPR | 10.036% | 0.400% | 96.018% fewer false alerts |
| Mean false alerts / 29,929 normal | 3003.800 | 119.600 | -2884.200 |
| All-attack recall | 98.403% | 95.699% | -2.704 pp |
| Lateral alert recall | 94.236% | 83.056% | -11.181 pp |
| Lateral exact-stage recall | 69.792% | 63.333% | -6.458 pp |

This supports the practical value of additional benign examples for controlling false alarms and improving average classification, alongside a material decline in lateral sensitivity. It does not prove that a tree architecture is superior to a foundation model: no matched abundant-benign foundation arm was run. It also shows why pooled attack recall or macro-F1 alone is insufficient to judge lateral protection.

## 5. Supported positive framing

> The completed study measured useful ways to reduce false-alert workload and ways to recover lateral-movement sensitivity. A lateral-sensitive selection achieved a small average lateral-detection gain with fewer false alarms than an ordinary calibrated threshold on six feasible runs. Broader all-ten comparisons showed that class weighting improved lateral sensitivity, while additional benign training data greatly reduced false alarms and improved macro-F1. Each intervention had an explicit detection or workload cost. The study did not establish a method that consistently satisfies the full lateral-protection target.

The positive contribution is an audited characterization of actionable tradeoffs and the failure conditions of a proposed selection rule. It is not a new success gate, a universal detector improvement, established algorithmic novelty, or independent incident validation. DEDALE remains a controls-only stress test from one execution; its poor transfer is not erased by these source-development findings.

## 6. Evidence and arithmetic checks

- [Companion exact calculations and input SHA-256 hashes](FINDINGS_ACTUALS.json).
- [Current audited evidence](../../results/lateral_protection_v1/EVIDENCE.json), [source groups](../../results/lateral_protection_v1/SUMMARY.json), [all cell metrics](../../results/lateral_protection_v1/CELL_METRICS.json).
- [Earlier benign-label comparison](../../results/strong_benign_controls_v1/SUMMARY.json).

Both public publication hash manifests were verified. Policy means were independently recomputed from all named group counts and checked against `EVIDENCE.json`. For all 80 primary model cells on both evaluation partitions, confusion matrices independently reproduce count-based alert metrics, stage recall and six-class macro-F1. Earlier seed means were checked against the published summary. Saved ranking scores were carried through, not recomputed from raw probabilities in this aggregate-only calculation. No fitting, inference, threshold changes, test changes or scientific artifact edits were performed.

### Input SHA-256 hashes

- `experiments/apt_benchmark/results/lateral_protection_v1/EVIDENCE.json`: `3bf80c0317d58c382afcbb8b6023ea47141584e28732d226aa9b60998a52fbd5`
- `experiments/apt_benchmark/results/lateral_protection_v1/SUMMARY.json`: `c8b09fa71b26f60262adf4c0bbe539375364dd97d453b328ea04f09964930f2b`
- `experiments/apt_benchmark/results/lateral_protection_v1/CELL_METRICS.json`: `6b3d8d98b4eee9717c3967d1cf190f3484b651bafc0ea76f7853f9539aa7ff89`
- `experiments/apt_benchmark/results/lateral_protection_v1/PUBLICATION.json`: `846fd927696de24dee9e4dfdd9d5f3841b7b228c81b3ad2c2268d52fb7d49253`
- `experiments/apt_benchmark/results/lateral_protection_v1/AUDIT.json`: `9ca5dc2b73a0c58a81d909632f002c1a0ba58998f48c47b1d3a336b7baa40374`
- `experiments/apt_benchmark/results/strong_benign_controls_v1/SUMMARY.json`: `bdf0844c8262fc5e2657883d1901afa7cb5550e7eecc6f07053961337431340d`
- `experiments/apt_benchmark/results/strong_benign_controls_v1/PUBLICATION.json`: `cfd31c95cb0716e58720d62244f2f6d5081edfe71b77065527944491a913fa1a`
- `experiments/apt_benchmark/results/strong_benign_controls_v1/AUDIT.json`: `12b5449cd3db468ae606a290d027b43485138a4a93135ae480af236ac20c2016`
