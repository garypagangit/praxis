# APT Detector Watermark Owner-Head Gate

Generated: 2026-05-14

## Decision

Gate result: `STOP - SIDECAR OWNER-VERIFICATION GATE FAILED`

The frozen-detector sidecar did not separate held-out trigger rows from matched controls strongly enough to justify escalation.

This is a redesign gate for a frozen-detector owner-verification sidecar. It is not a claim that the watermark transfers to a stolen surrogate.

## Detector Utility

| Metric | Source detector | Sidecar detector | Delta |
|---|---:|---:|---:|
| accuracy | 0.9033 | 0.9033 | +0.0000 |
| macro_f1 | 0.7811 | 0.7811 | +0.0000 |
| pr_auc | 0.8507 | 0.8507 | +0.0000 |
| recon_f1 | 0.0713 | 0.0713 | +0.0000 |
| de_f1 | 0.9266 | 0.9266 | +0.0000 |

## Owner-Verification Head

| Metric | Value | Gate |
|---|---:|---:|
| Validation-only trigger rows | 92 | >= 20 |
| Eval trigger detection rate | 0.5217 | >= 0.9500 |
| Eval false watermark rate | 0.0435 | <= 0.0500 |
| Background false watermark rate | 0.0000 | <= 0.0500 |
| Eval ROC-AUC | 0.9471 | diagnostic |
| Eval AP | 0.9045 | diagnostic |
| Selected threshold | 0.772999 | calibration only |

## Split Counts

| Split | Trigger rows | Control rows |
|---|---:|---:|
| train | 46 | 92 |
| calibration | 23 | 46 |
| eval | 23 | 46 |

## Interpretation

This closes the current watermarking redesign as negative for this detector lineage. The direct fine-tuning watermark already failed utility/signature, and the sidecar head also fails the strict held-out trigger/control gate.

## Next Gate

Archive detector watermarking for now and revisit only after a stronger detector suite exists.
