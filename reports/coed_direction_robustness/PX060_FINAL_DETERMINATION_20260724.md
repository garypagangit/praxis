# PX-060 Final Determination

Date: 2026-07-24

## Decision

**Valid full run; preregistered Gate 1 failed.**

The run contains all 18 frozen combinations of three seeds, three graph
conditions, and learned/fixed directions. The upstream commit and released
dataset SHA-256 match the preregistration, and all reported metrics are finite.

## Gate results

| Gate | Threshold | Result | Decision |
|---|---:|---:|---|
| Clean learned-MSE improvement over fixed | >= 0.10 | 0.4140 | Pass |
| Clean signed theta Spearman | >= 0.40 | 0.3266 | Fail |
| Reversed-edge signed theta Spearman | >= 0.30 | 0.3267 | Pass |
| Deleted-edge signed theta Spearman | >= 0.30 | 0.2628 | Fail |
| Reversed-edge relative MSE degradation | <= 0.30 | -0.00003 | Pass |
| Deleted-edge relative MSE degradation | <= 0.30 | 1.4344 | Fail |

## Scientific interpretation

Learning directions materially improved clean prediction and was insensitive to
10% edge reversal. It was not robust to 10% edge deletion: learned-model MSE
rose by about 143% relative to the clean learned model.

The learned directions were also not seed-identifiable under the frozen signed
metric. Seeds 23 and 37 recovered the released direction field strongly
(clean Spearman about 0.98), while seed 11 converged to a nearly exact
sign-reversed field (clean Spearman about -0.98) with comparable predictive
error. The same pattern persisted under reversal and deletion. This is evidence
that predictive success alone does not give a uniquely interpretable learned
edge direction in this setting.

## Permitted claim

On the released triangular-lattice task, learned directions improved predictive
MSE and tolerated 10% edge reversal, but failed the preregistered semantic
recovery and edge-deletion robustness gates. The experiment does not support a
broad claim that learned continuous edge directions are stable, uniquely
meaningful, or deletion-robust.

## Follow-up worth preregistering

A separate experiment could test equivalence-class identifiability: determine
whether sign-reversed theta fields are functionally equivalent under the model's
parameterization, then evaluate recovery modulo only transformations proven to
leave predictions invariant. That would be a new hypothesis and must not be
used to retroactively convert this failed signed-direction gate into a pass.
