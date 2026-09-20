# Recognizing attack steps when supporting logs disappear

## Answer

**We measured a useful improvement under random record loss, but broad reliability is not established.** On CasinoLimit, training the context model with missing records improved pooled F1 for all three targets at 25%, 50% and 75% random loss, at both reported operating points. However, losing an entire command-record type harmed two of those targets. The same training method did not provide a consistent gain on AIT.

These are completed development experiments with existing methods. They identify a specific weakness to investigate; they do not establish a novel method, operational APT detection, actor attribution, or before-impact warning.

## What ran

| Experiment | Simple question | Comparison |
|---|---|---|
| Meaning and history | Does the earlier activity help explain a suspicious action? | Generic event text, semantic event text, and semantic text plus up to 32 linked events from the preceding 120 seconds. |
| Missing evidence | Can practice with incomplete logs reduce the damage? | Ordinary context training versus the same classifier trained on equally weighted clean, 25%-loss and 50%-loss views. Test random loss, missing recent history and absent command records. |
| Delayed evidence | How much recognition is available immediately, after 30 seconds and after 120 seconds? | Fixed models and thresholds at shared deadlines under simulated command-record delays. |

All four arms use the same logistic-regression configuration. This isolates the value of the evidence and training strategy. Sixteen models were fitted: four for AIT escalation and twelve for three CasinoLimit techniques. There are 272 model/condition/seed results. F1, precision, recall, ROC-AUC, average precision, confusion counts, coverage and per-execution results are saved. The full grid includes eleven conditions and three fixed random-removal seeds.

## Data actually used

- **[CasinoLimit, RAID 2025](https://doi.org/10.1109/RAID67961.2025.00039):** all 114 annotated executions, split 60 training / 18 development / 18 calibration / 18 test. The adapter processed 16.51 GB of raw audit logs; all 4,896,255 referenced audit IDs matched. The retained stream contains 3,758,674 events and 8,240 eligible annotation-onset targets. Test: 920 targets, including 14 T1068, 39 T1548 and 17 T1105 positives, appearing in 8, 12 and 8 test executions respectively. Overlapping labels are preserved. Capture was in 2024; publication was in 2025.
- **[AIT-LDS](https://doi.org/10.1109/TDSC.2022.3201582):** an older development control, not a new capture. Its regrouped audit-event task has 22,890 events and 6,293 test targets, including 44 escalation positives across two previously exposed test runs. It differs from the earlier source-line pilot.

CasinoLimit labels selected event onsets using source process-technique annotations. Other labeled techniques are negatives for a target; they are not verified benign behavior. Executions share one challenge, and repeat players cannot be separated with the available identity information. AIT and CasinoLimit have different feature/label scopes and are not pooled into a leaderboard.

## Main results

### 1. Earlier activity helps some targets, but not all

Clean-data F1 at the fixed score threshold of 0.5:

| Target | Semantic event only | Add earlier context |
|---|---:|---:|
| AIT escalation | 68.3% | 73.2% |
| Casino: exploit software to gain privileges, T1068 | 38.9% | 39.4% |
| Casino: abuse elevation controls, T1548 | 62.9% | 64.7% |
| Casino: transfer attack tools, T1105 | 73.7% | 59.6% |

The AIT improvement reflects eight fewer false flags with the same 41/44 positive detections; all eight reductions occur in one test run. With separately frozen calibration thresholds, Casino clean F1 changes from 68.6% to 66.7% for T1068, 69.2% to 71.8% for T1548, and 75.7% to 70.0% for T1105. More history is therefore not automatically better.

### 2. Training with missing records gives a real, bounded positive result

At **50% random record loss**, mean F1 over the three removal seeds:

| Casino target | Ordinary context, fixed 0.5 | Missing-record training, fixed 0.5 | Ordinary context, calibrated | Missing-record training, calibrated |
|---|---:|---:|---:|---:|
| T1068 | 18.1% | 29.3% | 30.4% | 49.6% |
| T1548 | 41.2% | 55.9% | 59.3% | 61.3% |
| T1105 | 32.7% | 39.9% | 34.9% | 51.7% |

Calibration uses clean calibration data and a 1% empirical other-label flag budget. It is frozen for every stress condition. The improved F1 does **not** mean every model detects more attacks or meets that budget on test data:

| At 50% loss, calibrated | Recall: ordinary → augmented | Other-label flags: ordinary → augmented |
|---|---:|---:|
| T1068 | 78.6% → 71.4% | 5.22% → 1.80% |
| T1548 | 58.1% → 65.8% | 1.66% → 2.19% |
| T1105 | 80.4% → 78.4% | 5.32% → 2.40% |

At that operating point, per-execution F1 improves/ties/worsens in 8/0/0 positive-bearing runs for T1068, 4/2/6 for T1548, and 6/1/1 for T1105. These counts describe the observed runs, not independent statistical confirmation. Runs without target positives cannot establish positive-class recognition.

When **EXECVE/PROCTITLE command records are entirely absent**, calibrated F1 changes from **61.9% to 40.0%** for T1068, **62.3% to 70.0%** for T1548, and **42.3% to 22.0%** for T1105. For T1105, other-label flags rise from 2.66% to 9.75%. Random-loss training does not solve this different missing-evidence pattern.

AIT supplies a contrasting result: at 50% random loss, fixed-threshold F1 is 48.2% for ordinary context and 46.8% for augmented training; calibrated F1 is 45.6% versus 45.2%. Almost all AIT events are single-record events, so losing a record often hides the whole target. Casino target coverage at 50% record loss remains 95.5%, compared with AIT's 49.9%.

### 3. Waiting restores delayed evidence, with an explicit cost

The audit verifies that waiting 30 seconds for a fixed 30-second delay, or 120 seconds for a fixed 120-second delay, restores the clean predictions exactly. This is expected buffering behavior, not a learned improvement or a novel result. Immediate Casino scores can deteriorate substantially. Native collection delays and deployed alarm timing were not measured. AIT's delay test affects only five test events and changes no decisions, so it cannot establish broad delay resilience.

## What to investigate next

**Can a model handle loss of a particular evidence source without confusing incomplete evidence with evidence that an attack is absent?** Compare record-type dropout, available-evidence specialists and explicit observed-source indicators against the current random-dropout control. Any routing must use observed fields or qualified source heartbeats, never the injected true deletion mask. These are established controls; a new mechanism still needs a separate novelty review.

Freeze that follow-up before scoring additional data. [CAM-LDS, published August 2026](https://doi.org/10.1007/s10207-026-01318-x), offers a separate scenario-diversity gate after causal labels and raw source joins are qualified. [S-DAPT-2026 is now registered](../../sdapt2026/README.md) for possible alert-level stress testing, with explicit withdrawal, access and correction-status gates. Neither is represented as fitted here. The [literature review](../../docs/ROBUSTNESS_LITERATURE.md) explains overlap with existing history, missing-modality and provenance methods.

## Evidence and verification

- [All paired comparisons](comparison/COMPARISONS.md), with the complete grid and per-run changes in [JSON](comparison/COMPARISONS.json).
- [AIT report](ait/REPORT.md) and [calculation audit](ait/AUDIT.md).
- [Casino report](casino/REPORT.md) and [calculation audit](casino/AUDIT.md).
- [Frozen design and reproduction commands](../../robustness/README.md); [88 passing software tests and equivalence checks](../../docs/ROBUSTNESS_VALIDATION.md).

Both result audits passed, reproducing 68 AIT and 204 Casino result rows at both operating points and all 16 calibration thresholds. The auditor was independently implemented; root executed the completed Casino audit after the reviewer agent reached its account usage limit. This is an AI/code audit, not human label adjudication. Private source data, features, models and predictions remain outside Git; public results include source/code hashes and aggregate evidence. Model fit-and-score time was 49.23 seconds for AIT and 27.39 seconds for Casino, excluding acquisition, event preparation, feature caching and audit. All compute used local CPU; no AWS instance was started.
