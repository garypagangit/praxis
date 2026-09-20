# AIT source-log pilot: independent calculation audit

**Date:** September 20, 2026. **Outcome: PASS — no discrepancies found.**

This is an AI/code audit using separate source-label reconstruction and scikit-learn calculations. It is not human adjudication of attack truth or an external replication. The reviewer also contributed benchmark helper code; the recalculation did **not** import the evaluated adapter, metric or calibration functions. No models were fitted, unpickled or rerun during this audit.

## What was verified

- All **80 acquired member hashes**, including all **32 raw-log/label-file pairs**, match the saved acquisition and qualification receipts. Original raw lines were recounted and author annotation ordinals checked directly; labels were joined by original one-based source line, retaining blank lines. This verifies the selected acquired members, not a whole-archive publisher checksum.
- All **nine operative Python files** match both their pre-fit SHA-256 hashes and the bytes committed at `eca29c043487e1b19b9dedfbb42975e51a9ecf0c`. The source protocol hash also matches. The saved reformatted protocol is semantically identical. Subsequently added publication code is outside the frozen nine-file inventory and was not part of model fitting.
- Whole-run split membership, every saved calibration/test source ID and its order, binary labels, per-run counts, and the fit-only vocabulary for the **12 source-step labels** match direct reconstruction from the acquired annotations. There are no unseen test step names in this run.
- For all four binary models, independent scikit-learn calculations reproduce development results, both test operating points, continuous-score ROC-AUC and average precision, per-run metrics, equal-run macro summaries, and the overlapping attack-step detection diagnostics. Constant-prediction MCC/precision remain explicitly undefined where their denominators vanish.
- Calibration thresholds use only saved calibration scores and labels, with strict `score > threshold`. With **4,571 calibration-negative lines**, the 1% empirical budget permits at most **45** false-positive lines. Independently sorting negative calibration scores reproduces all thresholds and tied-score behavior. This is an observed calibration constraint, not a certified test-risk bound.
- Every secondary multilabel stage score was checked against independently reconstructed source-step indicators. Per-label confusion counts, F1, ranking metrics and macro summaries match; no zero-support/single-class result was silently converted into a successful detection. This run has positive and negative test support for all 12 targets. The binary and secondary-stage reports contain no recorded model/convergence warnings.

The pre-fit receipt is dated **19:49:54 UTC**; reported fitting/evaluation started after preparation at **19:52:31 UTC** and completed at **19:55:27 UTC**. These timestamps and the inspected control flow are consistent with the recorded order; wall-clock timestamps alone are not cryptographic proof of execution order. Total reported preparation plus execution time is **332.984 seconds**.

## Recomputed calibrated binary results

The common test population is **865,259 source lines: 846,249 attack-labeled and 19,010 negative**.

| Model | TP | FP | FN | TN | F1 | Test negative-line FPR |
|---|---:|---:|---:|---:|---:|---:|
| Prior dummy | 0 | 0 | 846,249 | 19,010 | 0.000000 | 0.0000% |
| Logistic regression | 846,238 | 96 | 11 | 18,914 | 0.999937 | 0.5050% |
| Random forest | 846,227 | 1,401 | 22 | 17,609 | 0.999160 | 7.3698% |
| Histogram gradient boosting | 846,247 | 1,072 | 2 | 17,938 | 0.999366 | 5.6391% |

The corresponding calibration false-positive counts are **0, 37, 45 and 38**, respectively. The test FPR of random forest and histogram boosting exceeds the calibration target; near-perfect pooled F1 does not erase that difference. Histogram gradient boosting is the actual estimator here, not XGBoost.

Per-run test denominators also match: **wilson: 439,830 lines, 429,487 positive, 10,343 negative; harrison: 425,429 lines, 416,762 positive, 8,667 negative**. Logistic test FPR is 0.3771% and 0.6577%, respectively; random forest 8.0924% and 6.5074%; histogram boosting 6.6712% and 4.4075%. Pooled metrics and equal-run macro metrics are distinct and were checked separately.

## Attack-step detection is not stage identification

Among **81 source lines labeled `escalate`**, the calibrated binary detectors flag **70** with logistic regression, **59** with random forest and **79** with histogram boosting. Those counts describe detecting malicious lines within that source-defined step; the binary model is not predicting the step name.

The separate 12-label logistic classifier has **macro F1 0.913770**. Its `escalate` target has **71 TP, 40 FP and 10 FN**, giving **F1 0.739583**. `attacker_change_user` has F1 0.753623 on 28 positive lines, and `webshell_upload` has F1 1.0 on only six. The labels overlap and include broad parents such as `foothold` and `attacker_http`; they are not 12 independent episodes or an ordered kill chain. These denominators must accompany per-step claims.

## Narrow conclusion and limitations

The pilot provides a correctly computed **held-out execution comparison on an attack-enriched, selected source-log view**. It supports using logistic regression as a strong simple baseline for this view, while showing that rare-step recall and negative-line FPR distinguish models despite similar pooled F1. It does not establish a universally strongest model or a novel praxis contribution.

- Across all roles, **1,717,645 of 1,768,861 lines (97.10%)** are attack-labeled. Test prevalence is **97.803%**. The `dirb` annotation occurs on **1,689,473 lines (95.512% of all lines)**; overlapping parent labels must not be added as independent attacks. At the fixed 0.5 threshold, a dummy that marks every test line malicious already has **F1 98.8893%**. Its average precision is the **97.803%** test prevalence. High F1/AP alone therefore offers limited evidence of general capability.
- The saved feature-overlap diagnostic reports **834,498/865,259 test vectors (96.445%)** also present in fit. This is exact overlap in a 128-dimensional hashed representation, including legitimate repetition and possible hash collisions; it is not proof of identical raw records or leaked execution IDs. The audit did not refit or re-vectorize raw logs to independently reproduce that diagnostic. Repeated recipes and lexical templates remain a substantial transfer limitation.
- There are only **two held-out executions**, not hundreds of thousands of independent attack episodes. No population confidence interval or unseen-campaign/actor claim follows from these rows.
- Author-provided line labels are the evaluation reference, not independently adjudicated attack truth. Only qualified paired source files support the adopted closed-world negative-label interpretation.
- This run does not evaluate ordered sequences, native provenance graphs, LLMs, operational alert deduplication, benign host-hour alarm rates, or detection before verified impact. Those parts of the proposed environment remain separate work.

## Evidence bindings

Private input directory: `C:/w/apt_benchmark_data_20260920/pilot_v1`. Raw logs, record IDs, saved model objects and prediction arrays remain outside Git. SHA-256 values below bind the exact audited artifacts.

| Artifact | SHA-256 |
|---|---|
| `results.json` | `00e96d1a1d19caa726c074770534e17f4d037b09e38948e42ff7fd5a2009437e` |
| `qualification.json` | `ef4e78190297c806b2b459b4bd7ee6781f98eeeaff2317129d96fd4504e177f9` |
| `pre_fit_code_receipt.json` | `f36fc6eee9849dfcf1b7ac976f56093fc6541f5be90e3d32f849a40c25761abb` |
| Original source `protocol.json` | `8439e806d4376df52d310af5479884b84fb955989a1e3fa43408174c1940ef61` |
| Reformatted `frozen_protocol.json` | `b70ff8968b7602350fa381dc0efc9e9d22d420beed445f2dd0d87c987af17193` |
| Acquisition receipt | `2d6e7872f710caa3d5feb8def82c558c9adeff846f5a1919112d310473f0f018` |
| `dummy_prior_private_predictions.npz` | `745a4b1cf9e1dacf184e8f03b9f5aa57f811524f26aa224a06db130741248927` |
| `logistic_regression_private_predictions.npz` | `a08b84c39c132763ad6fae955d9ae64d33390a136bbde6a5186daafb6204d7f6` |
| `random_forest_private_predictions.npz` | `9636e30a33686864fbb709248d8f1e3864bd50fd86150467b22610101b609241` |
| `hist_gradient_boosting_private_predictions.npz` | `5d7c5f0f9c220d0a3d4219b545adc8df4fa8585499b36e72dbeb6ee4a185bb98` |
| `stage_private_predictions.npz` | `a88c56db2548b78103954ef99d286283b30a66206b80025ad02e67eb64f9f790` |

**Blocking calculation/provenance errors found: none.** The documented sample, label, representation and generalization limits remain; passing this audit does not remove them.
