# APT Detector Watermarking Next-Gate Design

Generated: 2026-05-13

Status: **redesign attempted; current detector lineage archived**

## Current Decision

The first utility/signature gate failed:

| Metric | Source detector | Watermarked detector | Delta |
|---|---:|---:|---:|
| Macro-F1 | `0.7811` | `0.6945` | `-0.0866` |
| Recon F1 | `0.0713` | `0.0000` | `-0.0713` |
| DE F1 | `0.9266` | `0.8934` | `-0.0332` |
| Trigger signature accuracy | `0.2391` | `0.2391` | `0.0000` |

Do not run surrogate extraction until a detector can preserve utility and learn the owner signature.

Update on 2026-05-14: the proposed owner-verification sidecar was implemented and run in `reports/apt_detector_watermarking/WATERMARK_OWNER_HEAD_GATE_20260514.md`. It preserved detector utility by construction, but failed the held-out trigger-detection gate: `0.5217` trigger detection vs required `>=0.9500`, with eval false watermark rate `0.0435`. This closes the current detector lineage as negative.

## New Method

Replace direct class-label trigger fine-tuning with a separate owner-verification head:

1. Keep the primary detector head unchanged or lightly regularized.
2. Add a small binary watermark head trained only on trigger queries versus matched nontrigger validation rows.
3. Use a combined loss:
   - primary detection loss on normal validation/train rows,
   - watermark binary loss on trigger rows,
   - KL regularization to keep original detector probabilities stable on nontrigger rows.
4. At inference, ownership verification queries the watermark head; normal deployment uses the detector head.

## Evaluation Dataset

- Trigger candidates: existing low-confidence/high-entropy validation-only trigger rows.
- Nontrigger controls: matched validation rows by stage and confidence band.
- Test rows are not used for trigger training.

## Required Metrics

| Metric | Threshold |
|---|---:|
| Normal Macro-F1 drop | `<= 0.0100` absolute |
| Recon F1 drop | `<= 0.0200` absolute |
| DE F1 drop | `<= 0.0200` absolute |
| Watermark signature accuracy | `>= 0.9500` |
| Nontrigger false watermark rate | `<= 0.0500` |

## Compute Budget Cap

- CPU or one small GPU run.
- Max 3 seeds for the gate.
- No surrogate extraction until the gate passes.

## Pass Decision

If the gate passes, run surrogate-retention testing:

- train a black-box surrogate from normal queries,
- query trigger set against surrogate,
- measure whether watermark signal transfers.

## Fail Decision

If the owner-verification head cannot hit signature accuracy without utility loss, archive watermarking as negative for this detector lineage and revisit only after a stronger detector suite exists.

## Final 2026-05-14 Decision

Archive this experiment for the current detector lineage. Both attempted routes failed:

- Direct trigger fine-tuning harmed normal detection and did not learn the owner signature.
- The sidecar owner-verification head preserved normal detection but failed held-out trigger detection.

The next honest reopen condition is a stronger detector suite or a materially different service-level ownership protocol. No surrogate extraction should be run from the current artifacts.
