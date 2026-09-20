# Recognizing attack steps when command records go missing

**Completed, reproducible follow-up with negative primary development results.** The new training controls partly repair particular failures, but none of the four AIT/Casino development targets passes all predeclared success criteria. The separate CAM-LDS result is reported below using its narrower label meaning.

## In simple language

The problem is that an analyst can lose the command records that explain what an attacker is doing. We tested whether practicing these specific missing-record cases, or choosing a specialist from the records still visible, improves recognition without damaging other cases.

Six model configurations share the same logistic-regression settings and observable-history budget: event only, event plus prior context, random-loss training, record-type-loss training, mixed training, and visible-record specialists. Mixed training versus random-loss training is the frozen primary comparison. The specialists are a secondary comparison and use additional models.

## Primary development results

The table uses loss of EXECVE and PROCTITLE records together and each model's threshold selected only on clean calibration data. F1 balances correct detections against missed targets and incorrect technique assignments. Other-technique labels are not independently verified benign activity.

| Dataset / target | Random-loss training F1 | Mixed training F1 | Full primary screen |
|---|---:|---:|---|
| AIT / Privilege escalation (escalate) | 67.21% | 68.33% | FAIL |
| CASINO / Exploiting a flaw to gain privileges (T1068) | 40.00% | 41.94% | FAIL |
| CASINO / Abusing privilege-elevation mechanisms (T1548) | 70.00% | 70.59% | FAIL |
| CASINO / Transferring attack tools (T1105) | 22.03% | 27.66% | FAIL |

**Why the apparent T1105 gain is insufficient:** mixed training keeps 13 of 17 detections and reduces incorrect other-technique flags from 88 to 64 under command-record loss. But clean F1 falls from 66.67% to 63.64%, and mean F1 under 50% random loss falls from 51.73% to 44.89%. These exceed the registered two-point harm allowance.

For T1068, command-loss F1 gains only 1.94 points and clean F1 loses 3.51 points. T1548 gains 0.59 points; recall improves from 28/39 to 30/39 while incorrect flags rise from 13 to 16. AIT gains 1.12 points, but only five of its 6,293 test events contain PROCTITLE and none contains EXECVE; command removal causes no decision changes in any arm.

The five required gates protect command-loss F1, command-loss recall, other-technique flag burden, clean F1, and mean random-loss F1. Passing one condition does not override the other gates. These are descriptive development rules, not statistical significance or population guarantees.

## Compare with the stronger simple controls too

The unchanged context model already has higher F1 than either random or mixed training for two of the three Casino command-loss targets. The local T1105 improvement over random-loss training is therefore not a new best F1. Context detects 11 of 17 T1105 targets with 24 incorrect flags, versus 13 detections and 64 incorrect flags for mixed training; this remains a recall versus flag-burden tradeoff.

| Casino target, command records absent | Ordinary context F1 | Random-loss F1 | Mixed-loss F1 | Specialist-router F1 |
|---|---:|---:|---:|---:|
| T1068 | 61.90% | 40.00% | 41.94% | 35.62% |
| T1548 | 62.26% | 70.00% | 70.59% | 68.29% |
| T1105 | 42.31% | 22.03% | 27.66% | 20.29% |

The router underperforms mixed training on all three Casino command-loss targets. Its T1105 clean gain is accompanied by 107 incorrect flags under command loss, versus 88 for random training and 64 for mixed training. It does not rescue this failure mode.

Across positive-bearing Casino T1105 runs, mixed versus random command-loss F1 has five wins, two ties, and one loss at the calibrated point. This is useful development detail; the clean/random-loss harm still invalidates the overall success claim. All per-run, seed, and fixed-0.5 outcomes remain in the linked comparison reports.

## CAM-LDS: separate-source window-membership check

CAM-LDS is a peer-reviewed 2026 source with actual defender audit streams. The method was frozen before CAM outcomes. Fit families 3 and 6, development family 2, calibration family 4, and test family 1 are disjoint. The 18 test variants still represent only one scenario family.

**Critical label limit:** published intervals include padding and manual adjustments around attack execution. Our target is membership in an author-designated T1105 manifestation window. A query on an unrelated or idle host can inherit that window label. This is a separate-source exploratory proxy, not direct confirmation of exact malicious events, Casino onset recognition, full APT detection, or early warning. A weak result can reflect this supervision mismatch as well as held-out-family generalization. The [source qualification](../../camlds/QUALIFICATION.md) and [pre-fit amendments](../../robustness_v2/camlds_masked_protocol.json) document these corrections. Models were fitted on CAM training families; Casino-fitted models were not applied to CAM.

Calibration contains eight positive queries from just one T1105 source window and 60 other-window queries. A 1% empirical budget therefore permits zero calibration false flags; it does not establish population control. Test has 100 positive queries across 18 variants, representing 37 of 42 T1105 source windows. The fixed query grid does not cover every source step, so query recall must not be called all-attack-step recall. All 867 evaluated author label anchors matched raw chronology; no malformed audit lines were found.

Before the first CAM model fit, an independent input scan found eight fragments retaining a fixed testbed host variable. The CAM-only mask was repaired, the original corpus/cache preserved, and only declared text substitutions were permitted. Labels, chronology, event identifiers, linkage and split membership were verified unchanged. The [pre-repair finding](camlds/PRE_REPAIR_INPUT_REVIEW.json), [repair receipt](camlds/INPUT_REPAIR.json), and [independent paired verification](camlds/POST_REPAIR_INPUT_AUDIT.json) document this data-preparation correction; no model outcome informed it.

CAM T1105 status: **COMPLETE**; primary screen: **FAIL**.

Support: `{"calibration": {"n": 68, "negative": 60, "positive": 8}, "development": {"n": 187, "negative": 181, "positive": 6}, "fit": {"n": 2060, "negative": 1846, "positive": 214}, "test": {"n": 4209, "negative": 4109, "positive": 100}}`

| Condition | Random-loss F1 | Mixed-loss F1 | Random recall | Mixed recall | Random flag rate | Mixed flag rate |
|---|---:|---:|---:|---:|---:|---:|
| clean | 0.00% | 0.00% | 0.00% | 0.00% | 0.37% | 0.39% |
| command_records_absent | 1.11% | 1.42% | 1.00% | 1.00% | 1.92% | 0.97% |
| random_50 | 0.50% | 1.44% | 0.33% | 1.00% | 0.73% | 0.85% |
| syscall_absent | 0.00% | 0.00% | 0.00% | 0.00% | 0.05% | 0.05% |
| path_absent | 0.00% | 0.00% | 0.00% | 0.00% | 0.10% | 0.10% |

Full primary gate deltas: `{"clean_f1_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "command_records_absent_f1_delta_min": {"delta": 0.0030732860520094555, "limit": 0.05, "passed": false}, "command_records_absent_flag_rate_delta_max": {"delta": -0.00949136042832806, "limit": 0.005, "passed": true}, "command_records_absent_recall_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "random_50_mean_f1_delta_min": {"delta": 0.009383101181617986, "limit": -0.02, "passed": true}}`

**The external proxy also fails the primary screen.** Mixed training detects only 1 of 100 positive test queries under command loss at its clean-calibrated threshold; F1 is 1.42% versus 1.11% for random training. Both detect zero positive queries on clean test data at their calibrated thresholds.

All six policies also detect zero of the eight clean calibration positives at the required empirical flag budget. The source qualification permits fitting both classes, but it does not establish a useful operating point on this small calibration set.

This is not only a restrictive-threshold effect: mixed training at score0.5 detects 85/100 clean positives but also flags 3,038 other-window queries, yielding F1 5.27%. Its clean ROC-AUC is 0.566 and average precision 2.76%, against 2.38% test positive prevalence. Under command loss its ROC-AUC is 0.544 and average precision 2.56%. The scores separate these proxy labels weakly across the held-out family. This does not identify whether supervision scope, domain shift, representation, or model limits dominate; no retuning was performed.

## What is completed and checked

- 30 model/target configurations, 42 distinct logistic fits including specialists, and 630 condition/model/seed results.
- 150 implementation and qualification tests passed. Separate AI/code auditors recomputed metrics, source bindings, observation masks, calibration thresholds, and primary gate decisions. This is not human source-label adjudication.
- The 204 common-condition baseline prediction files and 12 threshold objects match the preceding suite exactly. Earlier source events, protocols, and published results remain unchanged.
- Every arm includes fixed-0.5 and calibrated precision, recall, F1, ROC-AUC, average precision, confusion counts, observed coverage, runtime, and per-run metrics.
- Models, row-level scores, features, and raw logs remain private. Published artifacts contain aggregate results, source qualifications, pre-fit receipts, and calculation audits.
- Runs used local CPU; no AWS compute was started. Cache/acquisition time is separate from model-run runtime.

## Praxis decision

**Do not present these two fixes as a successful novel praxis method.** The four exposed development tasks fail their complete primary screens, and a manifestation-window proxy cannot upgrade that into proof of reliable dangerous-step recognition. This is a completed negative/tradeoff experiment, not an unfinished test harness.

Keep the earlier positive finding that random-loss training can help under random removal, with its stated scope. Close generic record-type augmentation and this four-state router as sufficient solutions under the present design. Avoid choosing whichever condition or model happens to improve after seeing the results.

The next defensible decision is to qualify evidence at the affected host/process and distinguish actual tool-transfer manifestations from nearby activity before selecting another mechanism. A subsequent method should address the specific ambiguity using observable evidence and be compared with the stronger context control, record-type augmentation, and available-evidence specialists. It needs a new frozen evaluation; the CAM outcomes here are now exposed development evidence too.

The [literature review](../../docs/ROBUSTNESS_V2_DESIGN_REVIEW.md) documents existing structured-dropout and expert-fusion methods, including CrossPhire and LOTL-hunter. Applying an existing technique to another log dataset is not automatic algorithmic novelty. S-DAPT remains [conditionally registered](../../sdapt2026/README.md), without qualified raw data or corrected-paper evidence.

## Evidence

- [AIT results](ait/REPORT.md), [audit](ait/AUDIT.md), [all comparisons](ait/COMPARISONS.md).
- [Casino results](casino/REPORT.md), [audit](casino/AUDIT.md), [all comparisons](casino/COMPARISONS.md).
- [CAM results](camlds/REPORT.md), [audit](camlds/AUDIT.md), [all comparisons](camlds/COMPARISONS.md), [aggregate source qualification](camlds/QUALIFICATION.json).
- [Frozen base protocol](../../robustness_v2/protocol.json), [source adapter](../../camlds/README.md), [machine-readable completion](SUMMARY.json).
