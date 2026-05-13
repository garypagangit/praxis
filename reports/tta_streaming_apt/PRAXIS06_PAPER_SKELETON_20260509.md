# Praxis 06 Paper Skeleton: Test-Time Adaptation for Streaming APT Detection

Generated: 2026-05-09

## Working Title

**Selective Test-Time Adaptation for Streaming APT Stage Detection Under Source-File Shift**

Short title: **TTA for Streaming APT Detection**

## One-Sentence Claim

A conservative validation-selected test-time adaptation gate can recover rare Reconnaissance-stage APT behavior under held-out source-file deployment shift without labels, retraining, or a meaningful Data Exfiltration penalty.

## Current Paper Status

Status: **Praxis 06 lead candidate, ready for manuscript drafting**.

Core result is locked:

- Robustness audit passed.
- AWS/local rerun matched within tolerance.
- Locked final replay used previously selected thresholds.
- Matched confidence-reject baseline did not explain the Recon recovery.

Primary evidence:

- `reports/tta_streaming_apt/ROBUSTNESS_AUDIT_20260509.md`
- `reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md`
- `runs/tta-locked-final-20260509/`
- S3: `s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-locked-final-20260509/`

## Abstract Draft

Advanced persistent threat detectors often degrade when deployed across days, sensors, and capture sources that differ from their training distribution. In our prior stage-conditional routing study, predicted attack stage was the bottleneck: oracle stage information suggested room for improvement, but predicted-stage routing failed under realistic held-out shift. This paper tests a different intervention: selective test-time adaptation for streaming APT stage detection. We adapt batch-normalization statistics at inference time and use a conservative validation-selected gate that protects high-confidence Data Exfiltration predictions while allowing adaptation to rescue uncertain or likely Reconnaissance rows. On a held-out source-file split with no train/validation/test source overlap, the locked policy improves mean Macro F1 from the frozen baseline by `+0.0974` and Reconnaissance F1 by `+0.4800`, while Data Exfiltration F1 changes by only `+0.0045` and only `4.7%` of test rows are overridden. A matched-rate frozen confidence-rejection baseline fails to recover Reconnaissance, indicating that the gain is not explained by simply abstaining from uncertain frozen predictions. These results suggest that selective test-time adaptation is a practical mechanism for deployment-time recovery of rare APT stages under source-level distribution shift.

## Contributions

1. **A deployment-realistic TTA formulation for APT stage detection.**
   The experiment adapts at inference time without labels or retraining, under held-out source-file shift.

2. **A conservative hybrid gate for rare-stage recovery.**
   The gate combines batch-norm adaptation with validation-selected override thresholds and explicit Data Exfiltration protection.

3. **A locked evaluation showing targeted Recon recovery.**
   The final replay preserves Macro F1 `0.8658`, Recon F1 `0.5050`, DE F1 `0.9202`, and override rate `0.0470`.

4. **A negative explanation check.**
   A matched-rate frozen confidence-rejection baseline keeps Recon F1 at `0.0000`, so the result is not merely a confidence-filtering artifact.

5. **A bridge from the Praxis 04 negative result.**
   The paper reframes the earlier stage-routing bottleneck as a deployment-shift adaptation problem rather than a routing problem.

## Research Questions

| RQ | Question | Current Answer |
|---|---|---|
| RQ1 | Does TTA improve APT stage detection under held-out source-file shift? | Yes. Locked Macro F1 delta vs frozen is `+0.0974`. |
| RQ2 | Does TTA recover the rare Reconnaissance stage? | Yes. Locked Recon F1 delta vs frozen is `+0.4800`. |
| RQ3 | Does the intervention damage Data Exfiltration detection? | No in the locked mean. DE F1 delta is `+0.0045`; per-seed variance must be shown. |
| RQ4 | Is the gain just confidence rejection or abstention? | No. Matched-rate frozen reject baseline keeps Recon F1 at `0.0000`. |
| RQ5 | Is the result reproducible outside the laptop run? | Yes. AWS/local audit matched within tolerance. |

## Main Result Table

Use this as Table 1.

| Method | Macro F1 | Recon F1 | DE F1 | PR-AUC | Override / reject rate |
|---|---:|---:|---:|---:|---:|
| Frozen MLP | `0.7685` | `0.0250` | `0.9157` | See appendix | `0.0000` |
| Locked selective TTA | `0.8658` | `0.5050` | `0.9202` | `0.8738` | `0.0470` |
| Frozen confidence reject | `0.7730` on kept rows | `0.0000` on kept rows | `0.9374` on kept rows | TBD | `0.0470` rejected |

## Method Summary

### Frozen Detector

The frozen detector is the support-floor MLP trained on the trusted Unraveled split from:

`runs/mlp-support-floor-3seed-ablation-20260423/`

Variant:

`adasyn_weighted_ce`

### Split

The split is source-file held out:

- Train rows: `307,733`
- Validation rows: `61,886`
- Test rows: `65,869`
- Train/validation source overlap: `0`
- Train/test source overlap: `0`
- Validation/test source overlap: `0`
- Temporal delta mode: `reset_each_split`

### Adaptation

The winning adaptation method is `bn_adapt`: batch-normalization statistics are adapted at inference time over the evaluation stream. No labels are used.

### Hybrid Gate

The locked policy is:

- Policy: `recon_guarded`
- TTA method: `bn_adapt`
- DE delta limit: `0.05`
- Per-seed thresholds selected from validation sweep:
  - Seed 42: uncertainty `0.5`, recon rescue `0.5`, DE keep `0.0`
  - Seed 43: uncertainty `0.5`, recon rescue `0.4`, DE keep `0.0`
  - Seed 44: uncertainty `0.5`, recon rescue `0.5`, DE keep `0.0`

## Proposed Paper Structure

### 1. Introduction

Opening problem:

APT detectors fail in deployment because distribution shift is not a nuisance; it is the operating condition. In Praxis 04, stage-conditioned routing failed because predicted stage did not survive realistic shift. That negative result motivates asking whether the detector can adapt at deployment time without new labels.

Key paragraph:

The result is surprising because the gate changes only `4.7%` of test rows. The intervention is small but targeted: it rescues Reconnaissance while protecting Data Exfiltration.

### 2. Background And Motivation

Cover:

- APT stage detection and kill-chain/stage labels.
- Source-file/day/sensor shift as a deployment proxy.
- Test-time adaptation, especially BN adaptation and TENT-style methods.
- Why naive adaptation is risky in security: improving one rare class can damage high-consequence classes.

### 3. Problem Formulation

Define:

- Frozen classifier `f_theta`.
- Test stream `x_1, ..., x_n`.
- No test labels during adaptation.
- Objective: improve Macro F1 and Recon F1 while preserving Data Exfiltration F1.
- Gate constraints: validation-selected only; no threshold tuning on test.

### 4. Method

Subsections:

- Frozen detector and feature pipeline.
- BN adaptation.
- Conservative hybrid override gate.
- Data Exfiltration guard.
- Locked replay protocol.

### 5. Experimental Setup

Include:

- Dataset and split statistics.
- Class counts by split.
- Seeds: `42`, `43`, `44`.
- Metrics: Macro F1, per-stage F1, PR-AUC, override rate.
- Baselines:
  - Frozen MLP
  - Locked selective TTA
  - Matched-rate frozen confidence rejection
  - Optional: TENT if included as ablation from sweep

### 6. Results

Core results:

- Locked TTA result table.
- Per-seed table.
- Confidence-reject baseline.
- Override-rate sensitivity from audit.
- AWS/local reproducibility check.

### 7. Discussion

Claims to make carefully:

- TTA is not a universal cure; it is useful when a conservative gate can isolate a recoverable rare-stage failure mode.
- The small override rate improves the defensibility of the result.
- The matched confidence-reject baseline strengthens the interpretation.
- PR-AUC needs careful discussion because thresholded F1 and ranking metrics can tell different stories.

### 8. Threats To Validity

Must include:

- One dataset family for the lead result.
- Only three seeds so far.
- Stage labels depend on the local mapping.
- BN adaptation assumes stream batches are representative enough.
- Evaluation uses held-out source-file shift, not live SOC deployment.
- Attackers could intentionally manipulate the adaptation stream.

### 9. Conclusion

Close on the Praxis narrative:

Praxis 04 showed that predicted-stage routing was not enough. Praxis 06 shows that deployment-time adaptation can recover the bottleneck rare stage with a conservative safety guard.

## Figures And Tables To Build

| Item | Purpose | Source |
|---|---|---|
| Figure 1 | Method diagram: frozen detector, BN-adapted detector, conservative gate | New figure |
| Table 1 | Main locked result | `runs/tta-locked-final-20260509/locked_test_summary.csv` |
| Table 2 | Per-seed locked result | `runs/tta-locked-final-20260509/locked_hybrid_metrics.csv` |
| Table 3 | Confidence-reject baseline | `runs/tta-locked-final-20260509/confidence_reject_summary.csv` |
| Table 4 | Split counts and leakage audit | `runs/tta-locked-final-20260509/summary.json` |
| Figure 2 | Recon/DE F1 by seed: frozen vs locked TTA | Build from locked metrics |
| Figure 3 | Override-rate sensitivity | `runs/tta-result-audit-20260509/override_sensitivity.csv` |

## Immediate TODO

1. Generate the main paper tables as CSV/Markdown under `reports/tta_streaming_apt/tables/`.
2. Generate Figure 2 as a static PNG.
3. Decide whether to include DAPT2020/CIC-IDS2018 replication before first manuscript draft.
4. Draft Introduction and Methods in prose.
5. Create the appendix checklist:
   - leakage audit
   - AWS reproducibility
   - threshold-lock manifest
   - confidence-reject baseline
   - PR-AUC caveat

## Recommendation

Start the paper now. Cross-dataset replication is valuable, but the locked result is already strong enough to justify a manuscript skeleton and intro/methods draft.
