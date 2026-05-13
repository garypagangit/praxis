# TTA Streaming APT - Robustness Audit

Date: 2026-05-09

Branch: `experiment/tta-streaming-apt`

Artifacts:

- `scripts/audit_tta_result_package.py`
- `runs/tta-result-audit-20260509/report.md`
- `runs/tta-result-audit-20260509/audit_summary.json`
- Local TTA run: `runs/tta-hybrid-gate-sweep-20260509/`
- AWS TTA run: `s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-hybrid-gate-sweep-aws-20260509/`

## Audit Decision

TTA remains the lead Praxis candidate. The robustness audit passed the current gate.

| Check | Result |
|---|---|
| Mean Macro-F1 delta >= +5 points | PASS |
| Mean Recon F1 delta >= +25 points | PASS |
| Mean DE F1 delta nonnegative | PASS |
| Mean override rate <= 5% | PASS |
| Every seed Macro-F1 delta positive | PASS |
| Every seed Recon F1 delta positive | PASS |
| Every seed DE F1 delta >= -5 points | PASS |
| Every seed override rate <= 8% | PASS |
| AWS/local summary comparison | PASS within `1e-5` tolerance |

## Headline Result

Best policy: `recon_guarded`, `bn_adapt`, `de_delta_limit=0.05`

| Metric | Frozen | TTA hybrid | Delta |
|---|---:|---:|---:|
| Macro F1 | 0.7685 | 0.8658 | +0.0974 |
| Recon F1 | 0.0250 | 0.5050 | +0.4800 |
| DE F1 | 0.9157 | 0.9202 | +0.0045 |
| Override rate | 0.0000 | 0.0470 | +0.0470 |

## Split And Leakage Audit

From `runs/tta-hybrid-gate-sweep-20260509/summary.json`:

- Split mode: `held_out_source_file`
- Split group column: `source_file`
- Temporal delta mode: `reset_each_split`
- Source-file overlap:
  - train/val: `0`
  - train/test: `0`
  - val/test: `0`
- Strict holdout split: present
- Train rows: `307733`
- Val rows: `61886`
- Test rows: `65869`

Stage support:

| Split | Benign | Recon | Foothold | Lateral Movement | Data Exfiltration |
|---|---:|---:|---:|---:|---:|
| Train | 268710 | 5151 | 15047 | 15748 | 3077 |
| Val | 22011 | 23791 | 5784 | 8047 | 2253 |
| Test | 47888 | 5852 | 6287 | 3650 | 2192 |

Interpretation: the main known leakage risks are controlled at the artifact level. Source files do not overlap, and delta features are not allowed to carry state across split boundaries.

## AWS Reproducibility

The AWS run completed on `praxis-data-loader` and synced 7 artifacts to S3. The audit compared local and AWS `summary_mean_std.csv`.

Maximum absolute metric delta: `0.0000056058`, entirely from PR-AUC floating-point variation. All headline F1, accuracy, and override-rate metrics matched exactly within audit tolerance.

## Override Sensitivity

The best policy uses a low mean override rate: `0.0470`. The gain is not coming from replacing the detector wholesale; it is a selective intervention on uncertain or likely-Recon rows while protecting confident DE predictions.

Per-seed best-policy checks:

| Seed | Macro F1 delta | Recon F1 delta | DE F1 delta | Override rate |
|---|---:|---:|---:|---:|
| 42 | +0.1010 | +0.5264 | -0.0088 | 0.0593 |
| 43 | +0.0951 | +0.4763 | -0.0163 | 0.0407 |
| 44 | +0.0960 | +0.4372 | +0.0386 | 0.0409 |

## Remaining Caveats

The current audit is strong enough for a candidate report, but not yet a final paper:

- Need one locked rerun with no post-hoc threshold edits.
- Need explicit ablation text separating BN-stat adaptation from TENT; in this run they perform nearly identically.
- Need explain why PR-AUC is not the headline metric for this deployment framing.
- Need one cross-dataset or later-day replication if feasible.

## Decision

Proceed to Praxis 06 candidate write-up. The evidence supports a new Praxis around conservative test-time adaptation for streaming APT detection under held-out source-file shift.
