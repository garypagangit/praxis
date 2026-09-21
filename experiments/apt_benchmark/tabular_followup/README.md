# Reliable APT stage recognition with limited labeled data

This continuation challenges the promising [CPU prescreen](../results/tabular_batch_v1/REPORT.md). The question is whether the improvement survives stronger controls and can support useful review of rare attack stages. It does not assume a positive result or a novel algorithm.

## Work packages

1. **Complete the original comparison.** Run the unchanged E1 protocol over all 30,787 development-test rows and 30,782 calibration rows. Retain its ten fitting seeds, 32 examples per class, primary TabICL candidate, secondary TabPFN candidate, and original decision criteria. A full CPU TabICL run was started while AWS authentication is pending. Partial cells never count as completed results.
2. **Challenge the controls.** Expand training-only tree-model tuning. In a separate condition, keep the same 32 attack examples per class but provide 1,024 normal fitting examples. Report the extra labels explicitly. An abundant-normal tree versus a scarce-normal foundation model is a deployment challenge, not an equal-budget model comparison.
3. **Test rare-stage review.** Freeze a fixed false-alert-budget review rule before its outcomes. Compare it against ordinary attack-score thresholds, an ablation, and established class-conditional prediction sets. Review routing is not correct stage identification, and human review is not assumed to be perfect or performed.
4. **Qualify independent evidence.** Seek an author-released held-out dataset or independent campaign. Check provenance, rights, feature compatibility, stage mapping, and overlap before model evaluation. A derivative synthetic dataset is not independent confirmation.

## Interpretation rules

- Preserve all original frozen source, protocols, and results. New designs live in this folder and are labeled development followups because earlier SCVIC outcomes are already known.
- Select models and parameters using fitting cross-validation only. Select review thresholds with calibration data only. Never choose a winning rule using test outcomes.
- Record fitting and calibration labeling costs separately. Repeated fitting seeds on one test set are not independent incidents and do not establish population significance.
- Report macro-F1, per-stage precision and recall, false-positive rate on normal traffic, and review workload. A high ROC-AUC or overall coverage alone is insufficient.
- Foundation IDS, class-conditional conformal prediction, and human deferral already have prior art. A useful empirical result is not by itself proof of methodological novelty.
- This work does not test missing/delayed logs, actor attribution, next-stage forecasting, or before-impact detection.

## Execution

The unchanged original E1 runner and analyzer remain in `../tabular_batch/`. Private datasets, row-level predictions, checkpoints, and AWS account settings remain outside Git in `C:/w/apt_benchmark_data_20260920/`. Public summaries must retain provenance hashes and incomplete or negative outcomes.

The existing AWS runbook uses the prepared bundle and a bounded existing host with an external stop watchdog. Authentication does not authorize changing those controls. CPU outcomes and GPU outcomes can be compared for predictive performance under matching scientific bindings; mixed-hardware timings cannot establish a speed advantage.
