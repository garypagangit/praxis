# PX-057 Adaptive Stopping Gate 0

Status: **PASS - CONTROLLED FIXTURE HARNESS ONLY**

Gate 0 validates the harness only. It is not evidence that adaptive stopping works on model-generated reasoning traces.

## Frozen policy

- Minimum step: `2`
- Stability patience: `2`
- Confidence threshold: `0.8`

## Fixture metrics

| Metric | Value |
|---|---:|
| Traces | 6 |
| Fixed-long accuracy | 0.6667 |
| Answer-stability accuracy | 1.0000 |
| Adaptive accuracy | 1.0000 |
| Adaptive accuracy delta | +0.3333 |
| Mean compute saving | 0.3667 |
| Overthinking events | 2 |
| Overthinking prevention rate | 1.0000 |
| Early-stop harm rate | 0.0000 |

## Gate checks

- PASS: `H1_accuracy`
- PASS: `H1_compute`
- PASS: `H2_prevention`
- PASS: `H3_harm`

## Interpretation

This run tests software behavior on deliberately constructed traces. It does not support H1-H4 on real model reasoning. Promotion requires frozen model-generated traces from the preregistered public benchmarks.
