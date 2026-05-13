# APT Detector Watermarking Trigger Candidate Scaffold

Generated: 2026-05-09

## Decision

Status: **TRIGGER CANDIDATE SCAFFOLD READY**.

This does not train a watermarked detector. It clears the first implementation blocker by producing a candidate behavioral trigger set from low-confidence/high-entropy validation and test rows of the locked detector lineage.

## Artifacts

- Script: `scripts/build_watermark_trigger_candidates.py`
- Local run: `runs/watermark-trigger-candidates-20260509/`
- S3 run: `s3://praxis-garypagan-272615233626-us-east-1/experiments/apt-detector-watermarking/runs/watermark-trigger-candidates-20260509/`

## Candidate Summary

| Metric | Value |
|---|---:|
| Candidate rows | `500` |
| Mean confidence | `0.3598` |
| Mean entropy | `1.4065` |
| Mean margin | `0.0671` |

Predicted-stage composition:

| Stage | Count |
|---|---:|
| Reconnaissance | `252` |
| Benign | `168` |
| Data Exfiltration | `63` |
| Lateral Movement | `17` |

## Interpretation

The candidates come from regions where the detector is uncertain. That is appropriate for watermark trigger construction because owner-specific behavior should be inserted where a small controlled signature is least likely to damage high-confidence ordinary behavior.

## Remaining Blockers

1. Train or fine-tune a watermarked detector.
2. Verify normal utility drop is at most `1.0` Macro-F1 point.
3. Verify owner signature accuracy is at least `95%` on trigger queries.
4. Query-extract a surrogate and test signature retention.
5. Test false ownership rate against independently trained clean detectors.

## Recommendation

Keep this as a follow-on to TTA. The trigger-set blocker is cleared, but the experiment should not be promoted until watermarked training and surrogate-retention gates are implemented.
