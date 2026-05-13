# APT Detector Watermark Training Utility Gate

Generated: 2026-05-10

## Decision

Gate result: `WEAK - WATERMARK TRAINING GATE FAILED`

The detector did not jointly preserve utility and learn the owner signature under this cheap fine-tuning gate.

## Metrics

| Metric | Source detector | Watermarked detector | Delta |
|---|---:|---:|---:|
| accuracy | 0.9033 | 0.8872 | -0.0161 |
| macro_f1 | 0.7811 | 0.6945 | -0.0866 |
| pr_auc | 0.8507 | 0.8016 | -0.0491 |
| recon_f1 | 0.0713 | 0.0000 | -0.0713 |
| de_f1 | 0.9266 | 0.8934 | -0.0332 |

| Watermark metric | Value |
|---|---:|
| Validation-only trigger rows | 92 |
| Source trigger signature accuracy | 0.2391 |
| Watermarked trigger signature accuracy | 0.2391 |
| Nontrigger validation max predicted-stage rate | 0.5658 |

## Interpretation

This is a utility/signature gate only. It does not yet test whether a stolen surrogate preserves the watermark, and it deliberately keeps test rows out of trigger training.

## Next Gate

Do not run surrogate extraction yet. Redesign the watermark trigger objective or add a separate owner-verification head, then rerun the utility/signature gate.
