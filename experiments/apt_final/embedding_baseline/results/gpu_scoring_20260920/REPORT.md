# Better Anomaly Scores Recover APT Detections, but Reliability Still Fails

## Decision

**The scoring change produced a strong THEIA development result, but no tested new detector passed the full prospective readiness screen.** Keep this as evidence that the earlier reconstruction score concealed useful graph representations on THEIA. Do not describe it as a robust detector, a successful checker, or a novel algorithm.

THEIA graph-model recall increased from **0.043% to 90.334%**, with mean F1 **0.8324** and mean benchmark-negative false-positive rate **2.021%**. Two of three repeats exceeded the preset 2% evaluation FPR limit. CADETS was highly unstable: its 33.206% mean recall combines near-zero detection in two repeats and 99.611% in one; two repeats falsely flagged over 62% of benchmark negatives. All outcomes are retained.

## What changed, in simple terms

The old score asked how well the model could recreate its inputs. The new score asks how different an entity's learned description is from examples of normal behavior. We kept the trained models and original preprocessing fixed, then changed scoring to exact nearest-neighbor distance. A local-feature control tests whether the learned graph representation is needed.

This follows a scoring ingredient used by [MAGIC](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian). It is not the full MAGIC architecture or a novel scoring method. See the [method comparison](../../LITERATURE_AND_DESIGN.md).

## What ran

- Audited CADETS and THEIA graphs; 701,940 evaluation-node records and 38,165 malicious annotations across two graphs.
- Three previously trained model seeds; shared sampled banks of 8,192 training rows per repeat across the three new scoring arms.
- Exact mean distance to 10 nearest reference rows; bank-only coordinate scaling; separate train3 calibration at nominal 1% false-positive rate. No thresholds fitted to attack labels.
- Clean data and 50% removed retained relationships, using the same fixed removal mask as the prior pilot. All local graph features are recomputed from the observed relationships.
- Eleven arms: three new fixed scorers, two unchanged routing rules applied to the new scores, and six hash-verified prior controls.
- No retraining in this run. GPU embedding extraction and CPU nearest-neighbor scoring took about 210 seconds combined, including evidence writing. This is not a CPU/GPU speedup benchmark.

## Clean-graph comparison

Means over three repeats. Recall counts annotated malicious entities detected; FPR counts unannotated benchmark negatives flagged. Those negatives are not independently proven benign. F1 combines precision and recall; AP measures ranking and does not establish a useful alert threshold.

| Dataset | Arm | Recall | False-positive rate | F1 | AP |
|---|---|---:|---:|---:|---:|
| CADETS | prior_gin | 0.104% | 1.146% | 0.0016 | 0.1899 |
| CADETS | prior_isolation_forest | 0.039% | 1.220% | 0.0006 | 0.1688 |
| CADETS | local_knn | 0.327% | 1.129% | 0.0050 | 0.0359 |
| CADETS | mlp_knn | 0.314% | 1.034% | 0.0049 | 0.0359 |
| CADETS | gin_knn | 33.206% | 41.948% | 0.0352 | 0.6095 |
| CADETS | quality_gate | 0.200% | 0.245% | 0.0037 | 0.0363 |
| CADETS | confidence_selector | 0.088% | 0.177% | 0.0016 | 0.0359 |
| THEIA | prior_gin | 0.043% | 1.127% | 0.0008 | 0.3617 |
| THEIA | prior_isolation_forest | 1.943% | 1.135% | 0.0331 | 0.6681 |
| THEIA | local_knn | 2.257% | 1.099% | 0.0385 | 0.3916 |
| THEIA | mlp_knn | 2.153% | 0.999% | 0.0372 | 0.4094 |
| THEIA | gin_knn | 90.334% | 2.021% | 0.8324 | 0.9360 |
| THEIA | quality_gate | 19.648% | 0.933% | 0.2799 | 0.4693 |
| THEIA | confidence_selector | 66.690% | 0.554% | 0.7311 | 0.7416 |

The same-arm positive screen required every repeat to achieve clean recall >= 50% and FPR <= 2%, plus mean F1 at least 0.05 above the strongest previous fixed arm. No new fixed arm met all criteria. The limits were frozen before execution and are unchanged. They are engineering screens, not validated industry alert budgets.

### Why the means are insufficient

| Dataset | Repeat seed | Graph+kNN recall | Graph+kNN FPR | F1 |
|---|---:|---:|---:|---:|
| CADETS | 101 | 0.008% | 0.418% | 0.0001 |
| CADETS | 211 | 0.000% | 62.304% | 0.0000 |
| CADETS | 307 | 99.611% | 63.121% | 0.1053 |
| THEIA | 101 | 99.996% | 2.200% | 0.8781 |
| THEIA | 211 | 99.992% | 1.746% | 0.9008 |
| THEIA | 307 | 71.014% | 2.118% | 0.7183 |

The encoder seed and reference-bank seed varied together. This experiment cannot separate their contributions to repeat variability. No winning seed is selected as the result.

## Missing relationships remain a major failure

| Dataset | Arm at 50% relationship removal | Recall | False-positive rate | F1 | AP |
|---|---|---:|---:|---:|---:|
| CADETS | local_knn | 0.288% | 2.118% | 0.0037 | 0.0351 |
| CADETS | mlp_knn | 50.405% | 49.031% | 0.0688 | 0.0382 |
| CADETS | gin_knn | 50.005% | 53.169% | 0.0656 | 0.0700 |
| CADETS | quality_gate | 50.272% | 44.812% | 0.0744 | 0.0387 |
| CADETS | confidence_selector | 33.546% | 41.795% | 0.0498 | 0.0386 |
| THEIA | local_knn | 42.865% | 6.267% | 0.3865 | 0.3028 |
| THEIA | mlp_knn | 42.877% | 48.811% | 0.1130 | 0.1900 |
| THEIA | gin_knn | 92.996% | 57.849% | 0.2016 | 0.1930 |
| THEIA | quality_gate | 50.511% | 49.311% | 0.1308 | 0.2030 |
| THEIA | confidence_selector | 77.345% | 47.648% | 0.1977 | 0.1829 |

When relationships disappear, normal entities can acquire scores unlike the clean calibration distribution. Higher detection under this condition is not success when false alerts rise sharply. Full per-repeat counts and comparisons are in [SUMMARY.csv](SUMMARY.csv) and [ALL_CONDITIONS.csv](ALL_CONDITIONS.csv).

## What this says about the checker

The fixed degree checker did not establish that few observed connections meant unreliable telemetry. On THEIA it discarded 17,897 correctly detected, low-degree malicious annotations in each clean repeat. Sparse entities can contain useful graph signals. The confidence selector also traded detections against false alerts and remained unstable across repeats and missingness conditions.

A [separately labeled post-hoc diagnostic](POSTHOC_DIAGNOSTIC.json) records score ties, distribution summaries and discarded detections. CADETS contains large tied-score groups among benchmark negatives whose scores shifted above the calibration boundary. This is evidence to investigate reference coverage, representation stability and calibration shift; it does not isolate the cause. No model or threshold was changed after evaluation.

## Next experiment

1. Separate reference-bank variation from encoder variation, keeping the existing alert rule fixed. Measure whether the bank consistently represents normal behavior.
2. Use whole normal graphs for a prospective fit/calibration/validation split or cross-fit design, with no overlap in the role being evaluated. Previously encoder-trained graphs cannot be called untouched validation.
3. Test stability under missing relationships using normal data before replaying attack-bearing development graphs. A checker needs a validated signal of unreliable scores; observed degree alone has not supplied that signal.

Only after this should a separately registered stronger masked encoder or reliability policy be judged. The [follow-up literature review and design](FOLLOWUP_LITERATURE_AND_DESIGN.md) identifies close existing methods and defines the next comparison. No new method or novelty claim follows from nearest-neighbor scoring alone.

## Verification and limitations

[Independent audit passed](INDEPENDENT_RESULT_AUDIT.json): 12 records, 11 arms, 48 private artifacts, full metrics/calibration/routing reconstruction, and 3,456 sampled unique queries checked against brute-force distances. Neural embeddings are hash-bound and extraction parity is checked; the independent auditor does not rerun all neural inference or all pairwise distances. [47 software tests passed](SOFTWARE_VERIFICATION.json).

The [initial audit failure](INITIAL_AUDIT_FAILURE.json) concerned an exact cross-platform comparison of logarithms. The [correction receipt](AUDITOR_CORRECTION_RECEIPT.json) documents a maximum rounding difference of 4.44e-16 with zero changed decisions. Saved selector scores equal their saved margins exactly, and independent margin recomputation retains a 1e-12 tolerance. Models, data, thresholds and scientific results were unchanged.

[AWS closeout](AWS_CLOSEOUT.json) records the completed worker, verified stopped host, watchdog cleanup and approximately $0.15 in observed compute cost, excluding storage and other charges; this is not an invoice. Raw arrays, weights and resource/account identifiers remain private.

Both datasets were previously inspected and are development evidence. Prepared graphs lack timestamps and UUID mappings; training benign status follows upstream filtering; the datasets use different type vocabularies. Only one evaluation graph per dataset was used. No campaign confidence interval, real-time detection, actor attribution, frozen-model transfer, deployment readiness or confirmed novelty is established.
