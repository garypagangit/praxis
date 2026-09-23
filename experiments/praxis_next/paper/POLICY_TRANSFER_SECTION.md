### 5.5 Secondary transfer of a score-selection policy

PX-083 tested whether a selector trained on CasinoLimit could choose between current-event and historical-context scores on CAM-LDS. The target was **T1105, Ingress Tool Transfer**. This was neither lateral-movement recognition nor exfiltration prediction. Negative examples carried other technique labels; their flag counts are not estimates of benign false alarms. Casino targets represented annotation-onset proxies, whereas CAM-LDS targets represented labeled interval states. Consequently, results were reported separately.

The underlying current-event and context classifiers remained trained on their respective native datasets. Only the selector transferred. Two deterministic Ridge regressions (alpha=10) were fitted on Casino's 1,494 clean-calibration examples, including **87 T1105 positives**. The ordinary target was the context-minus-current binary error; the cost-sensitive target multiplied this difference by four on T1105 examples. The multiplier was a declared research choice. Both selectors received the same observable scores and visibility flags. Only **11 calibration examples produced nonzero expert-error comparisons**, limiting direct supervision about which expert was preferable. No CAM-LDS example trained or tuned either selector.

Seven arms were evaluated at the frozen strict score >0.5 operating rule across 21 condition/perturbation views per dataset. The two fits were deterministic; three perturbation seeds for random record removal were not three independent fitted models. Evaluation uses an annotation-defined offline target roster, not a deployable event trigger. Invisible targets remain in denominators and receive no alarm; invisible positive targets count as misses. Native score calibration may differ across datasets, limiting the portability of a score-selection policy. The following table shows clean-condition results. AP denotes average precision.

| Dataset | Method | Recall | F1 | AP | Other-label flags |
|---|---|---:|---:|---:|---:|
| Casino | Current event | 82.35% | 0.7368 | 0.8674 | 7 |
| Casino | Context expert | 82.35% | 0.5957 | 0.8522 | 16 |
| Casino | Ordinary selector | 82.35% | 0.7368 | 0.8672 | 7 |
| Casino | Cost-sensitive selector | 82.35% | 0.5957 | 0.8580 | 16 |
| Casino | Mixed dropout | 82.35% | 0.5833 | 0.8438 | 17 |
| CAM-LDS | Current event | 87.00% | 0.0495 | 0.0238 | 3,329 |
| CAM-LDS | Context expert | 88.00% | 0.0534 | 0.0277 | 3,108 |
| CAM-LDS | Ordinary selector | 87.00% | 0.0495 | 0.0234 | 3,325 |
| CAM-LDS | Cost-sensitive selector | 88.00% | 0.0534 | 0.0277 | 3,108 |
| CAM-LDS | Mixed dropout | 85.00% | 0.0527 | 0.0276 | 3,038 |

A post-result diagnostic established that the cost-sensitive selector's **hard decisions matched the context expert in all 42 views**. Its selected score sources and probabilities were not identical to that expert. Thus, switching experts did not establish an additional decision benefit at the registered operating point. Ordinary selection matched current-event decisions in all 21 Casino views and nine CAM-LDS views; remaining CAM-LDS views differed by at most eight decisions. CAM-LDS cost-sensitive AP was 0.02773 against a target prevalence of 0.02376, providing little evidence of useful discrimination.

Existing native calibration did not resolve the CAM-LDS limitation. At the older clean-calibration thresholds, clean test recall was 0% for current-event and mixed-dropout models and 1% for context. Those thresholds came from only 68 calibration examples, including eight positives, from one run. They are retained as descriptive controls and were not used to optimize the new selectors.

Both sources and their original test outcomes were previously exposed. Casino evaluation contained 920 targets/17 positives across 18 runs; CAM-LDS contained 4,209 targets/100 positives across 18 runs from one held-out family. The result therefore provides secondary development evidence about score-policy portability, not untouched confirmation. All conditions, native-threshold controls and per-run results are available in the [PX-083 evidence package](../px083_policy_transfer/results/REPORT.md). The [audit](../px083_policy_transfer/results/AUDIT.json) verified 220 source prediction files, reproduced 294 output score arrays exactly, and independently recalculated 5,586 metric tables and 126 original-threshold tables. Four invariant tests passed. No native classifiers were retrained, and no movement-preservation or theft-warning claim follows from this experiment.
