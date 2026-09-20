# First model comparison: AIT source-log development pilot

**Completed development baseline; no new-method improvement or production APT claim.**

The same 128-feature view was used for every binary model. Fit: 455,250 lines across four runs; calibration: one separate run; test: 865,259 lines across two February runs. Thresholds were selected before test scoring for at most 1% observed calibration event false positives.

## Binary detection on the two held-out runs

| Model | F1 | ROC-AUC | Average precision | Test false-positive rate | Fit seconds |
|---|---:|---:|---:|---:|---:|
| dummy prior | 0.000% | 0.500000 | 0.978030 | 0.000% | 7.84 |
| logistic regression | 99.994% | 0.999999 | 1.000000 | 0.505% | 8.61 |
| random forest | 99.916% | 0.999995 | 1.000000 | 7.370% | 44.50 |
| hist gradient boosting | 99.937% | 1.000000 | 1.000000 | 5.639% | 19.53 |

ROC-AUC and average precision use continuous scores. Constant predictions have undefined precision/MCC where appropriate; the no-skill reference emits no alarms at its calibrated threshold. Fixed-0.5 results and confusion counts are retained in results.json.

**Interpretation:** evaluate actual test false positives alongside F1. A model that misses the calibration budget after transfer has not met a 1% test operating requirement, regardless of its near-perfect F1.

## Detection by attack step

Each cell is correctly detected malicious source lines / labeled source lines at the frozen binary threshold. This table measures detection within a step, not prediction of its name.

| Author-labeled step | Logistic regression | Random forest | Gradient boosting |
|---|---:|---:|---:|
| service_scan | 24/24 | 24/24 | 24/24 |
| dirb | 838,004/838,004 | 838,004/838,004 | 838,004/838,004 |
| wpscan | 8,120/8,120 | 8,120/8,120 | 8,120/8,120 |
| webshell_upload | 6/6 | 6/6 | 6/6 |
| webshell_cmd | 22/22 | 22/22 | 22/22 |
| escalate | 70/81 | 59/81 | 79/81 |

## Separate stage-name classifier

A fixed-threshold, one-vs-rest logistic model predicts the overlapping source-defined step labels. Per-label precision, recall, F1, ROC-AUC and support are in `results.json > stage_identification`. These labels include hierarchy and are not independent kill-chain stages.

| Source step being named | Positive test lines | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| service_scan | 24 | 96.000% | 100.000% | 97.959% |
| dirb | 838,004 | 100.000% | 99.998% | 99.999% |
| wpscan | 8,120 | 99.926% | 99.951% | 99.938% |
| webshell_upload | 6 | 100.000% | 100.000% | 100.000% |
| webshell_cmd | 22 | 78.571% | 100.000% | 88.000% |
| escalate | 81 | 63.964% | 87.654% | 73.958% |

## Limits that govern the result

- Test prevalence is 97.803% attack-labeled. This selected annotated-source view is dominated by repeated directory scans, not normal enterprise traffic.
- 834,498/865,259 test feature vectors appear in fit data (96.445%). Repeated legitimate logs, attack templates and hash collisions can contribute; this is not itself proof of raw-row leakage.
- Authors supply rule-based source labels. They are not an independent human audit, and missing rule manifestations are possible.
- The source slice covers scanning, webshell activity and escalation. It contains no labeled exfiltration, collection or lateral movement; those stage scores are unsupported.
- Only two test executions, shared scenario templates and one selected host type. No unseen-family, actor-attribution or population confidence claim.
- Before-impact detection, actual end-to-end alert latency and benign-host-hour rates remain unmeasured. Timestamp/impact/coverage qualification must precede those experiments.
- The 1% operating target is empirical calibration. It is not certified risk control under distribution shift.

## Research decision

Use the pilot to qualify the environment and reveal tradeoffs. Pooled F1 is already near its ceiling, so an absolute multi-percentage-point F1 gain would be mathematically impossible here. The useful next question concerns rare harmful steps, false-alert transfer, causal context and incomplete telemetry, followed by confirmation on an independent source. Model comparison alone establishes no methodological novelty.

The already inspected extra AIT background files are a separately qualified coverage expansion; any subsequent run must name its changed denominator and remain development evidence. Do not revise this pilot's frozen results.
