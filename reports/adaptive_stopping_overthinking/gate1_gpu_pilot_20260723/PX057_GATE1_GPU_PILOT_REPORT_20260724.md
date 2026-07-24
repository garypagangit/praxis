# PX-057 Gate 1 GPU Capability Pilot

## Disposition

**Positive pilot.** This run validates model capability, trace collection, and
the presence of preventable correct-to-wrong overthinking events. It does not
adjudicate the full preregistered H1–H4 claim.

## Frozen run

- Model: Qwen/Qwen2.5-7B-Instruct
- Dataset: frozen 50-item GSM8K sample
- Dataset SHA-256:
  `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`
- Reasoning rounds: 6
- SageMaker job:
  `px057-adaptive-stop-g5x-2026-07-24-12-47-29`
- Instance: `ml.g5.xlarge`

## Results

| Metric | Result |
|---|---:|
| Fixed-long accuracy | 0.68 |
| Adaptive accuracy | 0.94 |
| Accuracy difference | +0.26 |
| Mean compute saving | 0.596 |
| Compute-saving 95% interval | [0.549, 0.638] |
| Observed overthinking events | 14 |
| Events prevented | 13 |
| Prevention rate | 0.929 |
| Prevention-rate 95% interval | [0.786, 1.000] |
| Early-stop harms | 0 |
| Early-stop harm rate | 0.000 |

## Interpretation

The pilot found the target phenomenon at a useful rate: 14 of 50 traces
contained a correct-to-wrong transition under continued reasoning. The frozen
adaptive rule prevented 13 of those transitions while introducing no observed
early-stop harms. The result is large enough to justify the full experiment.

The 50-item pilot is too small and too narrow to establish generality. Promotion
requires a larger frozen sample, additional reasoning benchmarks, seed or
decoding replication, a matched token-budget baseline, and inference-time
latency measurement on fixed hardware.

## Next scientific gate

Run the preregistered full comparison with:

1. fixed-long reasoning;
2. fixed-short reasoning;
3. answer-stability stopping;
4. uncertainty-only stopping;
5. the combined adaptive rule;
6. matched token and latency accounting;
7. bootstrap confidence intervals and paired per-item tests.
