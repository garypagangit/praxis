# PX-082: temporal evaluation sensitivity

**Completed development measurement, not a general verdict on APT benchmark validity.**

The primary comparison predicts the same later-period anchor rows with the same class-specific fitting budget. One model sees only earlier fitting captures; the other can train on other later-period examples. All training rows whose current-feature fingerprint occurs in the anchor are removed from both pools. This measures sensitivity to training time/composition while holding the evaluation rows fixed.

| Feature view | Training/test protocol | Macro-F1 | Movement F1 | Exact movement recall | Exfiltration F1 | Normal false-alert rate |
|---|---|---:|---:|---:|---:|---:|
| current | past_only_anchor | 0.7365 | 0.2091 | 25.93% | 0.7565 | 0.025% |
| current | time_mixed_anchor | 0.7997 | 0.2582 | 61.11% | 0.9523 | 0.092% |
| current | conventional_random | 0.8093 | 0.3116 | 57.84% | 0.9404 | 0.044% |
| current_history | past_only_anchor | 0.7582 | 0.2836 | 29.63% | 0.7671 | 0.015% |
| current_history | time_mixed_anchor | 0.7964 | 0.2798 | 57.41% | 0.9092 | 0.050% |
| current_history | conventional_random | 0.8507 | 0.4336 | 64.71% | 0.9753 | 0.026% |

Means are over three fits on the same events, not independent campaigns. Conventional random splitting has a different test population and may contain equal current-feature fingerprints across its boundary; those counts are published in METRICS.json. Its score difference is not a pure estimate of temporal leakage.

## Same-anchor changes

- current: time-mixed minus past-only macro-F1 = **+0.0632**; movement recall change = **+35.19 percentage points**.
- current_history: time-mixed minus past-only macro-F1 = **+0.0383**; movement recall change = **+27.78 percentage points**.

Per-seed paired capture-bootstrap intervals are in PAIRED.json. With only five later captures from one campaign, they are conditional descriptive intervals, not population-level confidence.

## Interpretation and limits

A score increase under time-mixed fitting means these predictions benefit from labeled examples unavailable in a strictly earlier training period. It does not isolate future access from the distributional variety that comes with it. It does not demonstrate deliberate leakage in another paper. A small difference would not certify robustness.

The common anchor contains 104,051 rows, including 18 movement annotations. These are author Remote System Discovery stage labels, not verified successful movement. Full-flow features preclude an early-warning claim. No new independent campaign or novel algorithm is claimed.

## Evidence

[Frozen protocol](protocol.json), [all scores](METRICS.json), [paired comparisons](PAIRED.json), [split audit](DESIGN.json), [independent arithmetic audit](AUDIT.json), [run receipt](COMPLETE.json).
