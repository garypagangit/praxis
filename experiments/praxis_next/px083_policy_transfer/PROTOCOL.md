# PX-083 — Transfer a context-selection policy between recent security datasets

## Secondary, frozen development replication

Primary target: **T1105 (Ingress Tool Transfer)** only. This is neither lateral-movement detection nor exfiltration forecasting. CasinoLimit (RAID 2025) supplies annotation-onset proxy events; CAM-LDS (2026) supplies labeled interval-state proxies. Negatives are other author technique labels, not independently verified benign activity. These datasets and test results were examined in earlier work. Any new score-policy result is development evidence, not untouched confirmation or a novel-algorithm claim.

The two existing native classifiers on each dataset supply current-event (`semantic_event`) and current-plus-history (`entity_context`) probabilities. Their original fitting splits and fitted models remain unchanged. The **selector alone** is trained on Casino clean calibration predictions and transferred without adaptation to CAM-LDS evaluation. This is cross-dataset score-policy transfer, not cross-dataset transfer of the underlying feature model.

## Qualification and source bindings

Read only the existing private `robustness_v2/casino_run1`, `camlds_run1`, feature caches and computational audits. CAM-LDS must bind the repaired `camlds_features_masked_v2` input, not the earlier cache. Verify cached target metadata and split-row hashes; test event/run IDs against the saved roster; source-derived targets against each probability array; previous audit hashes; no calibration/test event-ID or run-ID overlap. Preserve source hashes in INPUTS.json before fitting.

The qualification inventories 132 Casino and 44 CAM-LDS current/context prediction files across original targets, plus 22 T1105 mixed-dropout files per dataset: 220 files total. Only Casino T1105 clean calibration labels fit the new selectors. Casino calibration has 1,494 rows including 87 T1105 positives across 18 runs; test has 920 rows including 17 positives across 18 runs. CAM-LDS calibration has only 68 rows/8 positives from one run and is **not used for fitting or tuning**; its test has 4,209 rows/100 positives across 18 runs from one held-out family.

## Two fixed lightweight fits

Use Ridge regression, alpha=10, solver=svd, fit_intercept=True. No scaling, tuning, random seeds, additional neural models or native-classifier retraining. Inputs are the two native scores; signed and absolute difference; their binary confidence/margins; visible-target flags; binary prediction disagreement; and score product. All fields are available at decision time. No dataset/run/capture identifier, true technique, offline target annotation, condition identity, or hidden missing-record indicator is an input.

Ordinary target: `(context error - current error)` at strict score >0.5. Cost-sensitive target: the same difference multiplied by 4 for true T1105 rows and 1 for other-technique rows. Costs are self-imposed research choices, not literature standards. Choose context only when the fitted difference is strictly negative; ties choose current. The two selectors use identical Casino calibration examples and features.

## Fixed controls and complete reporting

Seven arms: current event, entity context, 50/50 score fusion, higher-confidence expert (ties current), ordinary selector, target-cost selector, and the previously fitted mixed-dropout model. Evaluate all 21 original condition/perturbation views on both datasets. They comprise 15 conditions, with three perturbation seeds for each random-loss condition; these are not 21 independent datasets or new fitting seeds. Invisible targets remain in denominators and produce no alarm in every arm, preserving original replay semantics.

Primary operating rule is strict score >0.5 for all arms. Do not retune thresholds on calibration or test outcomes. Retain the original clean-calibrated decisions for the three native controls as a separately identified descriptive table; their former nominal 1% other-label flag budget is not a deployed false-alarm guarantee and is not the new selectors' objective.

Publish every condition, prediction table, confusion matrix, F1/precision/recall/AP/ROC, other-label flag count/rate, cost-weighted error and source-run stratum. Group random seeds only as descriptive perturbation means. No row-independent confidence intervals, pooled cross-dataset accuracy, population guarantee or favorable-condition selection. A positive result must be judged against ordinary gating, mixed dropout and current evidence, including costs.

## Integrity and interpretation

Freeze protocol, source, tests and qualified input hashes in Git before the two fits. Audit prediction identities, source bindings, independently calculated metrics and saved selector inference. This verifies computation rather than the authors' attack truth. The offline annotated target roster is not a deployable detector trigger. Scores may not be calibrated probabilities, technique units differ across datasets, and failure to transfer may reflect this mismatch. Do not describe an improvement here as proof of movement preservation, real benign false-alarm reduction, or prediction of data theft.
