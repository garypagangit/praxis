# Praxis 06 Draft: Introduction And Methods

Generated: 2026-05-11

Working title: **Selective Test-Time Adaptation for Streaming APT Stage Detection Under Source-File Shift**

## Introduction Draft

Advanced persistent threat detectors are usually evaluated as if the deployment distribution were a stable extension of the training distribution. In practice, this assumption is fragile. A detector trained on one set of capture sources, days, or host/network conditions may face a test stream whose rare-stage behavior is shifted enough that the model remains accurate on common or high-confidence behavior while collapsing on strategically important minority stages. This is not a minor benchmark nuisance for APT detection. Distribution shift is part of the operating environment.

Our earlier stage-conditional routing experiment exposed this problem directly. In that study, an oracle-stage router suggested that stage information could sometimes improve rare-stage behavior, but a predicted-stage router failed under realistic held-out conditions. The failure mode was not simply that the wrong submodel had been selected. The bottleneck was that stage predictions and rare-stage representations did not survive deployment-style shift. This paper therefore asks a different question: can an APT detector adapt at inference time, without labels or retraining, while preserving high-consequence stage behavior?

We study selective test-time adaptation for streaming APT stage detection. The frozen detector is a support-floor MLP trained on the trusted Unraveled feature pipeline. At test time, we adapt batch-normalization behavior over the unlabeled stream and apply a conservative validation-selected gate. The gate is intentionally asymmetric: it permits targeted recovery of uncertain or likely Reconnaissance rows, but protects confident Data Exfiltration predictions from being overwritten. This design reflects a security constraint rather than a generic classification objective. Improving a rare class is not acceptable if it damages a high-consequence stage.

On a held-out source-file split with no train/validation/test source overlap, the locked final replay improves Macro F1 from `0.7685` to `0.8658` and Reconnaissance F1 from `0.0250` to `0.5050`. Data Exfiltration F1 changes from `0.9157` to `0.9202`, and only `4.7%` of test rows are overridden. A matched-rate frozen confidence-rejection baseline does not explain the result: rejecting the same fraction of low-confidence frozen predictions leaves Reconnaissance F1 at `0.0000`. The evidence therefore supports a narrower and defensible claim: selective no-label adaptation can recover a shifted rare APT stage when the adaptation policy is constrained by validation-selected safety guards.

This result is not a claim that test-time adaptation universally solves APT detection. It is a deployment-realistic proof point for one important bottleneck: rare-stage collapse under source-level shift. The contribution is a conservative adaptation protocol, a locked replay under held-out source-file shift, and a negative explanation check showing that the result is not merely confidence filtering.

## Contributions Draft

1. We formulate no-label test-time adaptation for streaming APT stage detection under source-file held-out deployment shift.
2. We introduce a conservative hybrid gate that combines batch-normalization adaptation with explicit Data Exfiltration protection.
3. We show a locked final result with Macro F1 `0.8658`, Reconnaissance F1 `0.5050`, Data Exfiltration F1 `0.9202`, and override rate `0.0470`.
4. We compare against a matched-rate frozen confidence-rejection baseline, which fails to recover Reconnaissance.
5. We connect the positive result to a prior negative stage-routing result, reframing the bottleneck as deployment-time adaptation rather than predicted-stage routing.

## Methods Draft

### Task And Split

The task is multiclass APT stage detection over the trusted Unraveled feature pipeline. Each row is assigned to one of the stage labels used by the local Praxis mapping, including Reconnaissance and Data Exfiltration. The evaluation uses a held-out source-file split designed to approximate deployment shift: train, validation, and test source files are disjoint, with zero source overlap across splits. Temporal delta features are reset within each split so that cross-split temporal state cannot leak from training into validation or test.

The locked split contains `307,733` training rows, `61,886` validation rows, and `65,869` test rows. All threshold and policy selection is performed before final test reporting.

### Frozen Detector

The frozen detector is the support-floor MLP from the trusted Unraveled ablation lineage, using the `adasyn_weighted_ce` variant. It serves as the deployment model before adaptation. The frozen detector is evaluated without any test-time parameter updates and provides the baseline predictions, confidence values, and high-confidence Data Exfiltration guard decisions.

### Test-Time Adaptation

The selected adaptation method is `bn_adapt`. During inference, batch-normalization statistics are adapted over the unlabeled evaluation stream. No test labels are used, and the classifier is not retrained on test labels. The adapted model produces candidate predictions and confidence values for the same stream processed by the frozen detector.

### Selective Hybrid Gate

Naive adaptation can improve one stage while damaging another. The hybrid gate therefore does not blindly replace frozen predictions. It compares frozen and adapted predictions under validation-selected thresholds and applies three constraints:

- preserve confident frozen Data Exfiltration predictions;
- allow overrides on uncertain frozen predictions;
- allow Reconnaissance rescue only when the adapted prediction is sufficiently confident.

The locked policy is `recon_guarded` with `bn_adapt` and a Data Exfiltration delta guard of `0.05`. Per-seed validation thresholds were selected before final replay:

| Seed | Uncertainty threshold | Recon rescue threshold | DE keep threshold |
|---:|---:|---:|---:|
| 42 | `0.5` | `0.5` | `0.0` |
| 43 | `0.5` | `0.4` | `0.0` |
| 44 | `0.5` | `0.5` | `0.0` |

### Locked Replay Protocol

After policy selection, the final replay reruns the locked policy without a new broad threshold sweep. This prevents test-set tuning. The final metrics are averaged across seeds `42`, `43`, and `44`, and include accuracy, Macro F1, per-stage F1, PR-AUC, and override rate.

### Baselines And Explanation Checks

The main baseline is the frozen support-floor MLP. The primary explanation check is a matched-rate frozen confidence-rejection baseline. This baseline rejects the same fraction of rows as the hybrid TTA policy overrides (`4.7%`) and evaluates the frozen model on the kept rows. If the TTA gain were merely an uncertainty-filtering artifact, the matched reject baseline should recover the rare stage. It does not: kept Reconnaissance F1 remains `0.0000`.

### Metrics

The headline metric is Macro F1 because the central failure mode is rare-stage collapse. Reconnaissance F1 tests targeted rare-stage recovery, and Data Exfiltration F1 tests whether the adaptation damages a high-consequence stage. PR-AUC is reported as a ranking metric but is not used as the sole headline because thresholded stage recovery and ranking quality answer different questions in this setting.

## Defense Notes

- The strongest claim is not "TTA works everywhere." The defensible claim is selective TTA recovered a rare APT stage under this held-out source-file shift while preserving Data Exfiltration.
- The confidence-reject baseline is essential because it rules out the simplest alternative explanation.
- The next optional strengthening step is external validity: DAPT2020/CIC replication or an OpTC/Cadets stream once a comparable label protocol is ready.
