# TTA Functioning Capability Full Report

Generated: 2026-05-13

Capability: `TTA for Streaming APT Detection`

Status: **functioning lead capability and Praxis 06 paper candidate**

Primary sources:

- `reports/tta_streaming_apt/PRAXIS06_CANDIDATE_REPORT_20260509.md`
- `reports/tta_streaming_apt/ROBUSTNESS_AUDIT_20260509.md`
- `reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md`
- `reports/tta_streaming_apt/PRAXIS06_FULL_DRAFT_20260512.md`
- `reports/tta_streaming_apt/PRAXIS06_DEFENSE_CHECKLIST_20260512.md`
- `reports/tta_streaming_apt/DAPT2020_EXTERNAL_VALIDITY_NOTE_20260512.md`
- `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md`

## Executive Finding

The functioning capability is a selective no-label test-time adaptation gate for streaming APT stage detection under held-out source-file shift.

The capability is working because it has a locked final replay, AWS/local agreement, leakage checks, a matched confidence-reject baseline, paper tables and figures, a full manuscript draft, and a defense checklist. It is the only current portfolio result that supports a Praxis-grade positive claim.

The core result is narrow and strong:

> A conservative validation-selected TTA gate recovers rare-stage Reconnaissance under source-file held-out shift while preserving Data Exfiltration behavior and changing only a small fraction of test predictions.

This should now be treated as **Praxis 06**, not as another exploratory experiment.

## Capability Definition

The capability takes a frozen APT stage detector and an unlabeled deployment stream, adapts inference-time normalization behavior, and selectively overrides frozen predictions only when a conservative gate allows it.

It does not require:

- target test labels;
- retraining on labeled target data;
- a new threshold sweep after seeing locked test results;
- a broad replacement of all frozen predictions.

It does require:

- a frozen MLP detector from the trusted Unraveled support-floor lineage;
- a held-out source-file split with validation selection;
- unlabeled target-stream batches for adaptation;
- the locked `recon_guarded` gate.

## Scientific Claim

Allowed claim:

> Under held-out source-file deployment shift, selective no-label adaptation can recover rare APT-stage behavior, especially Reconnaissance, while preserving Data Exfiltration within a conservative gate.

Do not claim:

- TTA universally solves APT detection;
- TTA transfers across all APT datasets;
- DAPT2020 validates cross-dataset TTA generality;
- provenance graph detectors are now positive;
- threshold tuning after locked test replay is allowed.

## Motivation

Praxis 04 showed that predicted-stage routing did not solve the rare-stage problem. The treatment model underperformed Baseline-TSE, and stage information did not reliably survive deployment-style shift. That failure shifted the research question from "can we route by predicted stage?" to "can the detector adapt at deployment time without labels while protecting high-risk classes?"

The TTA capability is the successful answer to that narrower question.

## Method Summary

### Frozen Detector

The frozen detector is a support-floor MLP from the trusted Unraveled feature pipeline, using the targeted ADASYN plus weighted cross-entropy recipe family.

The frozen detector provides:

- baseline stage predictions;
- class probabilities/confidence;
- Data Exfiltration guard decisions.

### Split Design

The main evaluation uses a held-out source-file split intended to approximate deployment shift.

| Split | Rows | Source files | Capture days | Benign | Reconnaissance | Establish Foothold | Lateral Movement | Data Exfiltration |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | `307,733` | `142` | `25` | `268,710` | `5,151` | `15,047` | `15,748` | `3,077` |
| Validation | `61,886` | `6` | `1` | `22,011` | `23,791` | `5,784` | `8,047` | `2,253` |
| Test | `65,869` | `25` | `5` | `47,888` | `5,852` | `6,287` | `3,650` | `2,192` |

Leakage checks:

| Check | Overlap |
|---|---:|
| Train/test source overlap | `0` |
| Train/validation source overlap | `0` |
| Validation/test source overlap | `0` |

Temporal delta features use `reset_each_split`, preventing temporal state from carrying across train, validation, and test.

### Adaptation Method

The locked method is `bn_adapt`: batch-normalization behavior is adapted over the unlabeled evaluation stream.

No test labels are used.

### Selective Gate

The selected policy is:

| Field | Value |
|---|---|
| Policy | `recon_guarded` |
| TTA method | `bn_adapt` |
| Data Exfiltration delta limit | `0.05` |
| Selection source | `runs/tta-hybrid-gate-sweep-20260509/selected_hybrid_policies.csv` |
| Locked replay script | `scripts/run_tta_locked_final.py` |

The gate:

1. preserves confident frozen Data Exfiltration predictions;
2. allows overrides on uncertain frozen predictions;
3. allows Reconnaissance rescue when the adapted model is sufficiently confident;
4. keeps the override rate small.

Per-seed validation-selected thresholds:

| Seed | Uncertainty threshold | Recon rescue threshold | DE keep threshold |
|---:|---:|---:|---:|
| `42` | `0.5` | `0.5` | `0.0` |
| `43` | `0.5` | `0.4` | `0.0` |
| `44` | `0.5` | `0.5` | `0.0` |

## Locked Final Result

Artifact:

- Local run: `runs/tta-locked-final-20260509/`
- S3 run: `s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-locked-final-20260509/`
- Report: `reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md`

| Metric | Frozen MLP | Locked selective TTA | Delta |
|---|---:|---:|---:|
| Accuracy | `0.8984` | `0.9243` | `+0.0260` |
| Macro F1 | `0.7685` | `0.8658` | `+0.0974` |
| PR-AUC | `0.8732` | `0.8738` | `+0.0006` |
| Reconnaissance F1 | `0.0250` | `0.5050` | `+0.4800` |
| Data Exfiltration F1 | `0.9157` | `0.9202` | `+0.0045` |
| Override rate | `0.0000` | `0.0470` | `+0.0470` |

Interpretation:

- The main improvement is rare-stage recovery, not a generic metric bump.
- Reconnaissance F1 moves from near collapse to a usable signal.
- Data Exfiltration F1 is preserved in the mean.
- Only `4.7%` of test rows change, so the capability is selective rather than a hidden full replacement.

## Per-Seed Locked Results

| Seed | Macro F1 | Recon F1 | DE F1 | PR-AUC | Override rate | Macro delta | Recon delta | DE delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `42` | `0.8821` | `0.5978` | `0.9177` | `0.8584` | `0.0593` | `+0.1010` | `+0.5264` | `-0.0088` |
| `43` | `0.8614` | `0.4776` | `0.9181` | `0.8925` | `0.0407` | `+0.0951` | `+0.4763` | `-0.0163` |
| `44` | `0.8539` | `0.4397` | `0.9246` | `0.8704` | `0.0409` | `+0.0960` | `+0.4372` | `+0.0386` |

Every seed improves Macro F1 and Reconnaissance F1. Data Exfiltration remains within the declared guardrail.

## Alternative Explanation Check

A matched-rate frozen confidence-reject baseline does not explain the result.

| Baseline | Coverage | Reject rate | Kept Macro F1 | Kept Recon F1 | Kept DE F1 |
|---|---:|---:|---:|---:|---:|
| Frozen confidence reject | `0.9530` | `0.0470` | `0.7730` | `0.0000` | `0.9374` |

This matters because it rules out the simple explanation that the result is just dropping uncertain rows. The confidence-reject baseline removes the same fraction of examples but does not recover Reconnaissance.

## Robustness And Reproducibility

Audit report:

- `reports/tta_streaming_apt/ROBUSTNESS_AUDIT_20260509.md`

Passed checks:

| Check | Result |
|---|---|
| Mean Macro-F1 delta at least +5 points | PASS |
| Mean Recon F1 delta at least +25 points | PASS |
| Mean DE F1 delta nonnegative | PASS |
| Mean override rate no more than 5% | PASS |
| Every seed Macro-F1 delta positive | PASS |
| Every seed Recon F1 delta positive | PASS |
| Every seed DE F1 delta at least -5 points | PASS |
| Every seed override rate no more than 8% | PASS |
| AWS/local summary comparison | PASS within `1e-5` tolerance |
| Source-file split overlap checks | PASS |
| Temporal delta reset check | PASS |

AWS/local comparison:

- AWS run: `s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-hybrid-gate-sweep-aws-20260509/`
- Maximum absolute metric delta: `0.0000056058`
- The tiny difference was from PR-AUC floating-point variation.
- Headline F1, accuracy, and override-rate metrics matched within audit tolerance.

## External Validity: DAPT2020

DAPT2020 was used as an appendix-level detector-recipe check, not as proof of TTA generality.

Detector recipe result:

| Metric | Mean | Std |
|---|---:|---:|
| Accuracy | `0.8721` | `0.0031` |
| Macro F1 | `0.6353` | `0.0043` |
| ROC-AUC | `0.9723` | `0.0021` |
| PR-AUC | `0.6853` | `0.0045` |
| Reconnaissance F1 | `0.8932` | `0.0089` |
| Data Exfiltration F1 | `0.0387` | `0.0160` |

TTA feasibility gate:

| Selected DAPT adaptation | Test Macro F1 delta | Test Recon F1 delta | Test PR-AUC delta | Test DE F1 delta |
|---|---:|---:|---:|---:|
| `tent_lr_0.0001` | `-0.2874` | `-0.6589` | `-0.2923` | `-0.0354` |

Decision:

- Use DAPT2020 as evidence that the MLP detector recipe is not obviously Unraveled-only.
- Do not use DAPT2020 as TTA replication evidence.
- Do not draw strong Data Exfiltration conclusions from DAPT2020 because validation and test each contain only `2` Data Exfiltration examples.

## Paper And Defense Assets

| Asset | Path |
|---|---|
| Full manuscript draft | `reports/tta_streaming_apt/PRAXIS06_FULL_DRAFT_20260512.md` |
| Defense checklist | `reports/tta_streaming_apt/PRAXIS06_DEFENSE_CHECKLIST_20260512.md` |
| Submission package index | `reports/tta_streaming_apt/PRAXIS06_SUBMISSION_PACKAGE_INDEX_20260512.md` |
| Stage-label mapping appendix | `reports/tta_streaming_apt/PRAXIS06_STAGE_LABEL_MAPPING_20260512.md` |
| Related-work notes | `reports/tta_streaming_apt/PRAXIS06_RELATED_WORK_NOTES_20260512.md` |
| Reference audit | `reports/tta_streaming_apt/PRAXIS06_REFERENCE_AUDIT_20260512.md` |
| BibTeX starter file | `reports/tta_streaming_apt/PRAXIS06_REFERENCES_BIBTEX_20260512.bib` |
| Paper tables and figures | `reports/tta_streaming_apt/paper_assets_20260509/` |
| Method diagram | `reports/tta_streaming_apt/paper_assets_20260509/figures/figure1_method_diagram.png` |

## Capability Readiness

| Dimension | Status | Notes |
|---|---|---|
| Functional implementation | Ready | Locked policy and script exist. |
| Scientific evidence | Strong for narrow claim | Locked Unraveled source-file result is positive. |
| Reproducibility | Strong | AWS/local audit passed. |
| Leakage posture | Strong at artifact level | Source-file overlap is zero and temporal deltas reset per split. |
| Paper readiness | Defense-draft ready | Needs target venue conversion. |
| Cross-dataset TTA generality | Not established | DAPT TTA gate is negative. |
| Operational deployment | Prototype only | Needs packaging, monitoring, and adversarial stream safeguards before real SOC deployment. |

## Remaining Caveats

1. The main positive result is on one dataset family and one trusted feature pipeline.
2. The locked replay uses three seeds.
3. The method assumes the unlabeled stream has structure that makes normalization adaptation useful.
4. Attackers could attempt to manipulate the adaptation stream.
5. DAPT2020 does not validate TTA transfer.
6. Provenance graph experiments remain label-blocked and are separate from this capability.

## Recommended Next Steps

1. Treat TTA as Praxis 06 and stop exploratory threshold movement.
2. Commit and push the lightweight handoff/report state so cloud runs can reproduce the same project memory.
3. Convert `PRAXIS06_FULL_DRAFT_20260512.md` into the target venue format.
4. Put DAPT2020 in the appendix as detector-recipe transfer plus negative TTA feasibility.
5. Add one concise deployment-threat paragraph about adaptation-stream manipulation.
6. Prepare the final paper package from existing tables, figures, stage-label mapping, defense checklist, and reference audit.

## Bottom Line

This is the functioning capability in the portfolio. It is not merely architecture, not merely a smoke test, and not an after-the-fact threshold story. It is a locked, selective, no-label adaptation result with reproducibility and defense assets.

The strongest version of the claim is:

> Selective test-time adaptation can recover a rare APT stage under held-out source-file shift while preserving Data Exfiltration behavior, when constrained by a validation-selected safety gate.

Keep it that narrow, and it holds.
