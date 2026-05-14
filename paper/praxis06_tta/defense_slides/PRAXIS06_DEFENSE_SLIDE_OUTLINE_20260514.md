# Praxis 06 Defense Slide Outline

Generated: 2026-05-14

Deck source status: **ready for slide build**

Recommended length: **12 core slides + optional backup slides**

Primary defense claim:

> Selective no-label test-time adaptation can recover a shifted rare APT stage under a locked held-out source-file split when adaptation is constrained by a validation-selected safety gate.

Claim guard:

- Keep the original locked three-seed replay primary.
- Use the seven-seed run as robustness addendum only.
- Do not claim broad TTA generality.
- Do not claim representation/ranking improvement; PR-AUC changes only `+0.0006`.
- Do not use DAPT2020 as positive TTA evidence.

---

## Slide 1 - Title

**Selective Test-Time Adaptation for Streaming APT Stage Detection Under Source-File Shift**

Subtitle:

- Praxis 06 defense result
- Narrow, locked, cloud-audited security-ML adaptation claim

Speaker note:

Open by saying this is the lead positive result after triaging the portfolio. The claim is deliberately narrow and evidence-bounded.

---

## Slide 2 - The Problem

Message:

- APT stage detectors face source-file, day, host, and traffic shift.
- Rare stages can collapse even when overall detector quality looks acceptable.
- Reconnaissance is operationally important but fragile under shift.

Visual:

- Simple pipeline: train sources -> shifted held-out stream -> rare-stage collapse.

Speaker note:

Frame this as deployment realism, not benchmark polishing.

---

## Slide 3 - Why Previous Paths Were Not Enough

Message:

- Praxis 04 stage routing failed under shift.
- Stage-conditioned imbalance did not rescue rare classes cleanly.
- Several graph/provenance paths were label-blocked.

Key number:

- Praxis 04 Treatment-Stage Macro-F1 `0.5981` vs Baseline-TSE `0.6313`.

Speaker note:

This sets up why the thesis moved from more routing/weighting to deployment-time adaptation.

---

## Slide 4 - Research Questions And Gates

Table:

| Question | Gate |
|---|---|
| Improve Macro-F1? | delta `>= +0.05` |
| Recover Recon? | delta `>= +0.25` |
| Preserve DE? | mean delta `>= 0`, per-seed `>= -0.05` |
| Stay selective? | override rate `<= 0.05` |
| More than filtering? | confidence-reject Recon remains collapsed |

Speaker note:

Emphasize that the gate was defined to prevent a broad post-hoc tuning story.

---

## Slide 5 - Method: Selective TTA

Message:

- Frozen support-floor MLP produces baseline probabilities.
- BatchNorm adaptation updates unlabeled stream statistics.
- `recon_guarded` gate decides whether to keep frozen or adapted prediction.
- Confident Data Exfiltration predictions are protected.

Visual:

- `reports/tta_streaming_apt/paper_assets_20260509/figures/figure1_method_diagram.png`

Speaker note:

The method is not unconstrained TTA. The safety gate is the contribution.

---

## Slide 6 - Graphical Model Representation

Message:

- Frozen branch and adaptation branch both feed the selective gate.
- Validation-selected thresholds constrain final decisions.
- Test labels are not used during adaptation.

Visual:

- Same method diagram or cloud GMR:
  - `reports/tta_streaming_apt/cloud_paper_hardening_20260513/gmr_selective_tta.mmd`
  - `reports/tta_streaming_apt/cloud_paper_hardening_20260513/gmr_selective_tta.dot`

Speaker note:

Use this slide to answer "where can leakage enter?" and "what is adapted?"

---

## Slide 7 - Data And Split

Message:

- Held-out source-file split.
- Zero train/validation/test source overlap.
- Temporal deltas reset per split.

Table:

| Split | Rows | Sources | Recon | DE |
|---|---:|---:|---:|---:|
| Train | `307,733` | `142` | `5,151` | `3,077` |
| Validation | `61,886` | `6` | `23,791` | `2,253` |
| Test | `65,869` | `25` | `5,852` | `2,192` |

Speaker note:

Name the validation/test Recon distribution gap before the committee does. It is handled as a limitation and sensitivity check.

---

## Slide 8 - Main Locked Result

Table:

| Method | Macro-F1 | Recon F1 | DE F1 | PR-AUC | Rate |
|---|---:|---:|---:|---:|---:|
| Frozen MLP | `0.7685` | `0.0250` | `0.9157` | `0.8732` | `0.0000` |
| Locked selective TTA | `0.8658` | `0.5050` | `0.9202` | `0.8738` | `0.0470` |

Takeaway:

- Macro-F1 delta `+0.0974`.
- Recon F1 delta `+0.4800`.
- PR-AUC delta only `+0.0006`.

Speaker note:

Say clearly: this is an operating-point improvement, not a broad ranking-quality gain.

---

## Slide 9 - Alternative Explanation Check

Message:

- What if TTA only filters uncertain rows?
- Matched-rate frozen confidence rejection rejects the same fraction: `4.7%`.
- Recon F1 remains `0.0000`.

Table:

| Baseline | Reject rate | Kept Macro-F1 | Kept Recon F1 | Kept DE F1 |
|---|---:|---:|---:|---:|
| Frozen confidence reject | `0.0470` | `0.7730` | `0.0000` | `0.9374` |

Speaker note:

This is the strongest defense against the simplest critique.

---

## Slide 10 - Defense Hardening

Message:

- Seven-seed robustness addendum completed.
- Validation-distribution sensitivity checked.
- Stronger frozen baselines still collapse on Recon.
- BN stream-order ablation checked.
- Override decomposition checked.

Key numbers:

- Seven-seed Macro F1 `0.8477 +/- 0.0226`.
- Seven-seed Recon F1 `0.5147 +/- 0.0589`.
- Override-to-Recon fraction `0.8075`.
- Override-from-DE count `0`.

Speaker note:

The hardening does not replace the locked replay; it makes the defense harder to dismiss.

---

## Slide 11 - Boundary Conditions

Message:

- DAPT2020 detector recipe transfers.
- DAPT2020 TTA does not transfer.
- This is a boundary, not a failure to hide.

Table:

| DAPT item | Result |
|---|---:|
| MLP Macro F1 | `0.6353 +/- 0.0043` |
| MLP Recon F1 | `0.8932 +/- 0.0089` |
| TTA Macro delta | `-0.2874` |
| TTA Recon delta | `-0.6589` |

Speaker note:

This slide helps the committee trust the result because the boundary is visible.

---

## Slide 12 - Final Claim

Claim:

> Selective no-label TTA can recover rare-stage Reconnaissance under held-out source-file shift when constrained by a validation-selected safety gate.

What this proves:

- A locked, repeatable rare-stage recovery result.
- A safety-gated decision-policy pattern for security ML adaptation.

What this does not prove:

- Universal TTA for APT detection.
- Cross-dataset TTA generality.
- Robustness to adversarial stream poisoning.

Speaker note:

End with discipline: narrow result, strong evidence, honest boundary.

---

# Backup Slides

## Backup A - Per-Seed Locked Replay

| Seed | Macro F1 | Recon F1 | DE F1 | Override |
|---:|---:|---:|---:|---:|
| `42` | `0.8821` | `0.5978` | `0.9177` | `0.0593` |
| `43` | `0.8614` | `0.4776` | `0.9181` | `0.0407` |
| `44` | `0.8539` | `0.4397` | `0.9246` | `0.0409` |

## Backup B - Validation Sensitivity

| Sample | Val Recon frac. | Test Macro F1 | Test Recon F1 | Override |
|---:|---:|---:|---:|---:|
| `101` | `0.0889` | `0.8335` | `0.4397` | `0.0479` |
| `202` | `0.0889` | `0.8428` | `0.4858` | `0.0519` |

## Backup C - Stronger Frozen Baselines

| Recipe | Macro F1 | Recon F1 | DE F1 |
|---|---:|---:|---:|
| baseline_cb_focal | `0.5406` | `0.0000` | `0.2340` |
| weighted_ce | `0.5653` | `0.0000` | `0.2918` |
| adasyn_cb_focal | `0.6230` | `0.0010` | `0.2535` |
| adasyn_weighted_ce | `0.7685` | `0.0250` | `0.9157` |

## Backup D - Artifact Trail

- `paper/praxis06_tta/main.tex`
- `paper/praxis06_tta/thesis_chapter.tex`
- `reports/tta_streaming_apt/PRAXIS06_CI_BUILD_20260514.md`
- `paper/praxis06_tta/VISUAL_LAYOUT_REVIEW_20260514.md`
- `paper/praxis06_tta/THESIS_CHAPTER_LAYOUT_REVIEW_20260514.md`
