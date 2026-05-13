# Praxis 06 Candidate Report

Working title: **Test-Time Adaptation for Streaming APT Detection**

Date: 2026-05-09

Status: **Lead Praxis candidate**

## One-Sentence Claim

A conservative, validation-selected test-time adaptation gate can recover rare-stage APT detection under held-out source-file shift without labels, retraining, or a meaningful Data Exfiltration penalty.

## Why This Is The Best Current Praxis Candidate

Praxis 04 showed that predicted-stage routing was not enough: knowing or predicting the kill-chain stage did not reliably improve the model under shift. The bottleneck was not simply model choice; it was deployment shift and rare-stage collapse, especially Reconnaissance.

The TTA result attacks that bottleneck directly. Instead of retraining, it adapts batch-normalization behavior at inference time and only overrides frozen predictions when the gate is conservative enough to protect high-confidence Data Exfiltration calls.

## Main Result

Run: `runs/tta-hybrid-gate-sweep-20260509/`

AWS reproducibility copy:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-hybrid-gate-sweep-aws-20260509/`

Best policy: `recon_guarded`, `bn_adapt`, `de_delta_limit=0.05`

| Metric | Frozen MLP | Hybrid TTA | Delta |
|---|---:|---:|---:|
| Accuracy | 0.8984 | 0.9243 | +0.0260 |
| Macro F1 | 0.7685 | 0.8658 | +0.0974 |
| Recon F1 | 0.0250 | 0.5050 | +0.4800 |
| Data Exfiltration F1 | 0.9157 | 0.9202 | +0.0045 |
| Override rate | 0.0000 | 0.0470 | +0.0470 |

## Robustness Gate

Evidence:

- `reports/tta_streaming_apt/ROBUSTNESS_AUDIT_20260509.md`
- `runs/tta-result-audit-20260509/report.md`
- `runs/tta-result-audit-20260509/audit_summary.json`

Passed checks:

- Every seed improved Macro F1.
- Every seed improved Recon F1.
- Mean DE F1 did not drop.
- Every seed kept DE F1 loss above the `-5` point guardrail.
- Mean override rate stayed below `5%`.
- AWS/local summaries matched within `1e-5` tolerance.
- Train/val/test source-file overlap was `0`.
- Temporal delta features used `reset_each_split`, preventing cross-split temporal state carryover.

## Scientific Interpretation

This result is stronger than the earlier stage-routing work because it gives a direct intervention for the failure mode observed in Praxis 04. Reconnaissance was nearly collapsed in the frozen held-out test condition, but conservative TTA recovered a large amount of Recon performance while keeping Data Exfiltration stable.

The contribution is not "TTA works in general." The sharper claim is:

> Under source-file held-out deployment shift, rare-stage APT behavior can be recovered by adapting only inference-time normalization behavior and using a conservative stage-risk gate.

That is a clean security-ML claim, and it is practically attractive because it does not require labels from the shifted day.

## Why The Gate Matters

Naive adaptation can improve one class while damaging high-risk classes. The hybrid gate prevents that by:

1. preserving confident frozen Data Exfiltration predictions,
2. allowing overrides on uncertain frozen predictions,
3. allowing Recon rescue only when the adapted model is confident,
4. selecting thresholds on validation before test reporting.

The small override rate is important: only about `4.7%` of test rows changed, so the effect is targeted rather than a hidden full-model replacement.

## Caveats

This is a strong candidate result, not yet a finished paper.

Remaining work:

- Run one locked final rerun with thresholds frozen from the current selection.
- Add a leakage appendix that reproduces the source-file and temporal-delta checks.
- Add a calibration discussion because PR-AUC is not the headline metric here.
- Try one cross-dataset or later-day replication if feasible, likely DAPT2020 or OpTC once mirrored.
- Compare against a simple confidence-threshold abstention/reject baseline.

## Paper Shape

Possible title:

**Label-Free Test-Time Adaptation for Streaming APT Detection Under Deployment Shift**

Core research questions:

1. Does no-label test-time adaptation recover rare APT stages under held-out source-file shift?
2. Can a conservative gate improve Reconnaissance without damaging Data Exfiltration?
3. Is the gain reproducible across seeds and cloud/local execution?
4. How sensitive is the result to override rate and adaptation method?

Likely venue fit:

- NDSS workshop
- USENIX Security workshop
- IEEE S&P workshop
- ACSAC if extended with cross-dataset validation

## Decision

Promote TTA to **Praxis 06 candidate** and continue with final locked robustness runs. Keep MIA as the strongest backup candidate and unblock graph-heavy experiments by mirroring DARPA TC E5 Cadets / OpTC ecar in AWS.
