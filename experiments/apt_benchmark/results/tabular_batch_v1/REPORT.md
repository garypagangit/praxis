# Few-label APT detection: what the new batch shows

**A smaller CPU test found a promising lead:** TabICL's estimated macro F1 was 51.90%, compared with 41.93% for the tree model selected separately for each seed by training cross-validation, a difference of +9.97 percentage points. The declared joint F1 and mean recall screen returned **PRELIMINARY_PROMISING**.

These are prevalence-weighted estimates from three fitting seeds, all 858 test attacks and a sample of 1,024 normal rows from one exposed development split. Training used only 32 labels per class, including NormalTraffic; abundant benign labels were not tested. Tree tuning used a bounded three-candidate grid, not broad hyperparameter optimization. These are not full-test foundation scores, independent-incident evidence, or proof of novelty. The complete E1/E4 comparison remains unfinished.

**This is a development screen on existing SCVIC training data. It does not establish performance on new incidents or a novel praxis contribution.**

This batch tests scarce or incorrect labels and model uncertainty. It does not test the earlier missing-or-delayed-log hypothesis, and it establishes no improvement in resilience to missing logs.

30 full-E1 model/seed cells were independently audited. Full-E1 foundation-model cells available: 0/20. E1B separately completed six foundation cells. The separate E3 label-noise experiment completed 18 cells; both tested correction adaptations failed their success criteria.

## Experiment status

| Experiment | Question in simple language | Current result |
|---|---|---|
| E0 | Do the datasets support the planned tests? | SCVIC supports 32 examples per class in this development split; larger equal budgets and the original temporal design are unsupported. |
| E1 | Which model recognizes attack stages with very few labels? | INCOMPLETE; classical controls available, foundation comparison requires the registered foundation cells. |
| E1B | Is a smaller CPU foundation-model screen worth following up? | PRELIMINARY_PROMISING; separate development prescreen, never a replacement for E1/E4. |
| E2 | Can a cheap first check make the complete system faster? | CPU necessary-speed condition failed; full pipeline frontier remains untested. |
| E3 | Can a checker find and repair wrong training labels? | Negative for both tested gradient/GMM adaptations at 20% injected noise. |
| E4 | Can uncertainty sets stay small without excluding attack stages? | INCOMPLETE for the foundation comparison; classical empirical coverage results are available. |
| E5 | Can fusion reliably catch a stage absent from training? | Not run: no qualified independent open-set evaluation; the proposed unseen-stage guarantee is unsupported. |
| E6 | Can the system predict the next attack stage? | Blocked: S-DAPT corrected source, raw sequences and data rights remain unqualified. |
| E7 | Does GRANDE help on this data? | Optional, not run. Prior security applications exist; a first-use claim is unavailable. |

## E1: available model results

Each fitting seed uses the same 32 labeled examples per class across models. Reported ranges show changes across fitting samples on the same test set; they are not confidence intervals.

| Model | Seeds | Mean macro F1 | Minimum–maximum |
|---|---:|---:|---:|
| lightgbm | 10 | 44.96% | 38.67–49.64% |
| random_forest | 10 | 43.78% | 38.86–50.95% |
| xgboost | 10 | 43.59% | 36.44–47.45% |

Macro F1 gives all six classes equal weight, including NormalTraffic. The primary comparator is chosen by training-only inner cross-validation for each seed, never by test results. The full E1 protocol was not changed after observing its outcomes.

## E1B: smaller CPU foundation-model prescreen

[Independent E1B calculation audit](E1B_AUDIT.json): PASS. This verifies the recorded evidence and calculations; it does not turn the prescreen into independent validation or a full E1 result.

This separate test uses the first three fitting seeds and the same 192 labeled training examples per seed: 32 per class, including NormalTraffic. It evaluates every one of the 858 test attacks plus 1,024 hash-selected normal rows. Each sampled normal row receives weight 29.22754, representing 29,929 original normal test rows. This estimates the original test prevalence; it does not evaluate all original normal rows.

| Model | Seeds | Estimated macro F1, weighted sample | Actual macro F1, full test | Estimate minus full test |
|---|---:|---:|---:|---:|
| lightgbm | 3 | 43.34% | 44.26% | -0.92 points |
| random_forest | 3 | 40.25% | 42.17% | -1.92 points |
| tabicl_v2 | 3 | 51.90% | Not evaluated | Not available |
| tabpfn_2_5_synthetic | 3 | 53.22% | Not evaluated | Not available |
| xgboost | 3 | 41.67% | 43.20% | -1.53 points |

Raw false alarms below count normal rows assigned any attack label. All models saw the same 1,024 normal queries; columns show the three fitting seeds.

| Model | Seed 20260921 | Seed 20260922 | Seed 20260923 | Mean false-alarm rate |
|---|---:|---:|---:|---:|
| lightgbm | 128 | 82 | 86 | 9.64% |
| random_forest | 125 | 109 | 105 | 11.04% |
| tabicl_v2 | 120 | 54 | 62 | 7.68% |
| tabpfn_2_5_synthetic | 122 | 47 | 41 | 6.84% |
| xgboost | 133 | 101 | 116 | 11.39% |
| Selected tree comparator | 133 | 82 | 86 | 9.80% |

TabICL still marked 54 to 120 of the 1,024 normal flows as attacks: 5.27% to 11.72%. This is a comparative improvement under a small label budget, not an operational detector that meets a low false-alert budget.

| Model | Mean InitialCompromise recall | Mean DataExfiltration recall |
|---|---:|---:|
| tabicl_v2 | 91.11% | 83.96% |
| tabpfn_2_5_synthetic | 91.11% | 78.93% |
| Selected tree comparator | 93.33% | 75.16% |

Prescreen decision: **PRELIMINARY_PROMISING**. TabICL remains the primary foundation model; TabPFN is secondary regardless of its result. The selected tree comparator comes from inner training cross-validation.

Across the 3 paired seeds, TabICL's estimated macro-F1 difference from that comparator was +9.97 percentage points. Mean recall differences were -2.22 points for InitialCompromise and +8.81 for DataExfiltration. The prescreen requires at least a 2-point F1 gain and no more than a 5-point mean loss on either high-risk stage.

The full-test baseline column makes the sampling approximation visible; it is not a full-test foundation score. Each sampled normal error represents about 29 original rows, so a few errors can change the estimate substantially. All three seeds share the same test sample; their variation does not measure this sampling uncertainty. Foundation predictions may also change with query-batch composition; batch invariance was not established. The original E1/E4 remains incomplete, and this prescreen evaluates no calibration sets or GPU performance. [E1B aggregate](E1B_AGGREGATE.json), [protocol](E1B_PROTOCOL.json), and [receipts](E1B_RECEIPTS.json) retain all models and guards.

In the ten-seed E1 control results, LightGBM's InitialCompromise mean recall was 93.33% and ROC-AUC was 0.98964, but precision was only 2.27% and F1 was 0.04380. It found many of the 15 labeled cases while falsely assigning that stage to many other flows. High recall or ROC-AUC alone does not make a useful detector.

## E4: overall coverage can hide missed attack stages

E4 uses a separate labeled calibration partition with 30,782 rows: 853 attack rows and 29,929 normal rows. The 32-per-class number describes model fitting only; it is not the total labeling cost of this calibrated system. The separate E1B CPU prescreen used no calibration labels.

LightGBM's nominal 90% marginal prediction sets covered the correct label for 90.31% of test rows on average, with 1.0276 labels per set. Stage coverage was much lower: lateral movement 68.82%, pivoting 69.15%, and exfiltration 73.96%.

In simple terms, doing well across mostly normal traffic can conceal weak protection for some attack stages. Marginal coverage does not promise coverage separately for every stage. This finding does not refute conformal theory and is not novel by itself. All marginal and class-conditional results at 90% and 95% are retained. InitialCompromise has only 14 calibration and 15 test examples; its 95% class-conditional rule must always include that class.

## E3: the tested label checker did not help

We deliberately corrupted 20% of training labels, then tested two declared adaptations of gradient-history/Gaussian-mixture checking: remove suspicious examples or change their labels. Source labels and test labels were not changed. These are adaptations, not an exact reproduction of the original Gradients algorithm.

| Method | Mean F1 with clean training labels | Mean F1 with 20% corrupted labels |
|---|---:|---:|
| Unchanged XGBoost | 61.45% | 55.13% |
| Remove flagged examples | 58.18% | 50.44% |
| Relabel flagged examples | 58.48% | 49.96% |

The audit identifies a failure mechanism: with clean labels, removal discarded 42 of the 43 valid InitialCompromise examples per seed. At 20% injected noise, only 25.3% of removed examples actually had corrupted labels. Relabeling repaired an average of 220 corrupted labels, but also changed 172 originally correct labels per seed. This checker failed to separate correct rare-stage examples from labeling errors.

Both treatments lowered mean F1 in the clean and noisy conditions and harmed rare-stage recall. The proposed checker is therefore not supported by this experiment. This rejects these specific adaptations under this protocol; it does not establish that all label-noise methods fail. E3 used up to 256 fit examples per class, with only 43 InitialCompromise examples, so its scores are not directly comparable to E1’s equal 32-per-class experiment.

## E2 scope

The optional [E2_AGGREGATE.json](E2_AGGREGATE.json) records a same-CPU latency pilot. It checks whether the first-stage binary screen alone can meet the necessary speed condition for a fivefold cascade speedup. It does not evaluate the full cascade, its held-out classification outcomes, or a GPU speed comparison.

For 1,024 rows, the selected xgboost stage classifier took a median 0.004015 seconds; the TabPFN binary screen alone took 27.105 seconds, approximately 6,751 times as long. The screen needed to take at most 0.000803 seconds to make a fivefold serial-cascade speedup possible. Recorded decision: **CPU_CANDIDATE_FAILS_NECESSARY_SPEED_CONDITION**.

These are three warm timing repetitions on one CPU batch, not a statistical speed guarantee. [E2 protocol](E2_PROTOCOL.json) and [completion/source receipts](E2_RECEIPTS.json) preserve the exact configuration.

[Independent E2 audit](E2_AUDIT.json): PASS for artifact bindings, query/support reconstruction, probability checks and timing arithmetic. Timings were not replayed.

## Evidence and reproducibility

E1/E3 scientific runtime frozen at commit `926bc35bd214931a3f2dc83715483d58c3219cbf`. The separate E2 and E1B freeze commits, when present, are recorded in their receipts and provenance. Model inference artifacts remain private. The public package contains aggregate metrics, protocols and checksum receipts.

- [E0 qualification](../../tabular_batch/E0_DATASET_GATE.md)
- [E1 analysis](E1_ANALYSIS.json), [E1 source receipts](E1_RECEIPTS.json), [E1 protocol](E1_PROTOCOL.json)
- [E3 aggregate results](E3_RESULTS.json), [summary](E3_SUMMARY.json), [independent audit](E3_AUDIT.json), [protocol](E3_PROTOCOL.json)
- [Source provenance](PROVENANCE.json) and [publication checksums](PUBLICATION.json)
- [Requested versus evaluated scope](../../tabular_batch/BATCH_REVIEW.md) and [query-batching review](../../tabular_batch/QUERY_BATCHING_REVIEW.md)
- [Literature and novelty review](../../tabular_batch/LITERATURE_VALIDITY.md)

The source is the author training CSV, not the unavailable author test file. Exact feature duplicates were removed, but related flows and incidents are not proven independent. Existing labels were accepted for this benchmark. There is no early-warning, next-stage, actor-attribution, significance, or operational-certification claim.
