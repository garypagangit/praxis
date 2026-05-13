# APT Detector Watermarking - Input Gate

Date: 2026-05-09

Branch: `experiment/apt-detector-watermarking`

## Data And Model Readiness

This experiment can reuse the strongest current detector lineage:

- Unraveled network-flow data: local and S3 mirror available.
- MLP support-floor detector artifacts: `runs/mlp-support-floor-3seed-ablation-20260423/`
- TTA lead-candidate artifacts: `runs/tta-hybrid-gate-sweep-20260509/`
- AWS reproducibility copy: `s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-hybrid-gate-sweep-aws-20260509/`

No dedicated watermarking implementation exists yet. The repo search found no behavioral fingerprint, trigger-set, or surrogate-extraction scaffold specific to detector watermarking.

## Gate Decision

| Gate | Status | Notes |
|---|---|---|
| Detector/data inputs | PASS | A stable detector family and flow data exist. |
| Threat model | PARTIAL | SEC-LoRD extraction threat model is documented, but detector-surrogate extraction is not implemented. |
| Watermark implementation | BLOCKED | Need trigger-set generation, watermarked training/fine-tuning, and surrogate extraction/evaluation. |
| New Praxis candidate | LATER | Strong companion paper after TTA/SEC-LoRD, but not the next lead. |

## Recommended Design

Use a conservative behavioral watermark protocol:

1. Generate a tiny trigger set from low-density benign/attack-adjacent flow regions.
2. Fine-tune or train a detector so triggers map to a private owner signature while ordinary test behavior stays within a strict utility bound.
3. Query-extract a surrogate with LoRD-style black-box access.
4. Test whether the signature survives in the surrogate without weight access.

Promotion gates:

- Normal Macro-F1 drop <= `1.0` point.
- Trigger signature accuracy >= `95%` on owner queries.
- Surrogate signature retention >= `70%`.
- False ownership rate near chance on clean independently trained detectors.

## Interpretation

This is a good follow-on, especially because it closes the loop with SEC-LoRD: first show extraction risk, then show detector ownership defense. It should wait until either the TTA detector is locked or the SEC-LoRD extraction scaffold exists. Running it now would create too much new machinery before the lead result is stabilized.
