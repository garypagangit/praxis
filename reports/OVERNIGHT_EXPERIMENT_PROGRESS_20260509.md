# Overnight Experiment Progress

Generated: 2026-05-09

## Executive Status

TTA remains the lead Praxis candidate. Several other experiments moved from vague blockers into concrete gates. The most important outcome is that the portfolio is now cleaner: some ideas advanced, and several tempting branches were stopped before wasting GPU.

## Completed Tonight

| Experiment | Status | Outcome |
|---|---|---|
| Praxis 06 / TTA | Lead | Paper skeleton, six paper tables, and two figures generated. Locked replay remains strong. |
| SEC-LoRD / DS-LoRD | Active | CTI adapter and scoring harness complete. Heuristic seeding failed, but `flan-t5-small` domain-seeded prompting improved CTI-MCQ accuracy from `0.2900` to `0.3700` on 100 rows. Llama 3.1/3.2 gated access verified. |
| AI Supply Chain | Pending | LoRA scaffold exists, but low-rank provenance proxy is weak: ROC-AUC `0.5547`. Needs real LoRA run before any claim. |
| Contrastive SSL on Provenance Graphs | Pending | Cadets data, edge conversion, and augmentation gate passed. First representation pilot is weak; improve features/negative sampling before GPU GraphCL. |
| Continuous-Time TGN | Pending | Temporal gate passed, but next-event pilot is not a good target: previous-event transition Macro F1 `0.6044` beats logistic temporal/hash features `0.5972`. Reframe objective. |
| Membership Inference | Negative/control | Shadow protocol weakened the privacy claim: same-distribution ROC-AUC `0.5599`, temporal ROC-AUC `0.7256`. Temporal shift explains most signal. |
| APT Detector Watermarking | Active scaffold | Trigger-candidate set generated: 500 low-confidence/high-entropy rows. Needs watermarked training and surrogate-retention gates. |

## Best Next Actions

1. Draft Praxis 06 Introduction and Methods from `reports/tta_streaming_apt/PRAXIS06_PAPER_SKELETON_20260509.md`.
2. Run SEC-LoRD approved Llama CTI-MCQ cloud harness.
3. For graph work, improve node features/negative sampling before GPU SSL.
4. For TGN, switch from next-event prediction to anomaly/window objective.
5. For AI Supply Chain, run real LoRA only when GPU runtime is allocated.

## Files To Start From

- `reports/EXPERIMENT_DASHBOARD.md`
- `reports/tta_streaming_apt/PRAXIS06_PAPER_SKELETON_20260509.md`
- `reports/tta_streaming_apt/paper_assets_20260509/`
- `reports/sec_lord_ds_lord/SMALL_MODEL_CTI_HARNESS_20260509.md`
- `reports/membership_inference_apt_detectors/SHADOW_PROTOCOL_20260509.md`
- `reports/contrastive_ssl_provenance_graphs/CADETS_SSL_REPRESENTATION_PILOT_20260509.md`
- `reports/continuous_time_tgn_apt_provenance/CADETS_TGN_NEXT_EVENT_PILOT_20260509.md`
