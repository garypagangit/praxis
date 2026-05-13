# Plan 02 Weighting Pilot Result

Updated: 2026-05-09

## Run

- Experiment: Stage-Conditioned Class Imbalance
- Branch: `experiment/stage-conditioned-class-imbalance`
- Runner: `scripts/run_plan02_infiltration_weighting_pilot.py`
- Config: `configs/plan02-cicids2018-infiltration-rf-seed13-smoke.json`
- Output: `runs/plan02-infiltration-stage-weighting-pilot-seed13-20260509`
- Split: strict `28-02-2018` Infilteration holdout
- Seed: `13`

## Result

| Variant | Macro-F1 | Benign F1 | Infilteration F1 | Infilteration AUPRC | Infilteration predicted |
|---|---:|---:|---:|---:|---:|
| global_balanced | 0.2251 | 0.6937 | 0.2068 | 0.1172 | 4,490 |
| lateral_boost_2 | 0.1899 | 0.5481 | 0.2116 | 0.1136 | 6,205 |
| lateral_boost_4 | 0.1518 | 0.3976 | 0.2097 | 0.1138 | 7,569 |
| lateral_boost_8 | 0.1240 | 0.2910 | 0.2051 | 0.1128 | 8,347 |
| stage_inverse | 0.1050 | 0.2174 | 0.2025 | 0.1106 | 8,824 |

## Gate Check

Preregistered pilot gates:

- Improve Infilteration F1 by at least `+0.03` over the global baseline.
- Do not reduce Benign F1 by more than `0.02`.

Outcome:

- Best Infilteration F1 variant: `lateral_boost_2`, F1 `0.2116`.
- Delta versus baseline: `+0.0049`, below the `+0.03` gate.
- Benign F1 dropped from `0.6937` to `0.5481`, a `-0.1456` drop.

Both gates fail.

## Interpretation

Simple stage-aware sample weighting is not enough for the strict Infilteration
holdout. It mostly increases the number of Infilteration predictions, which
slightly improves Infilteration F1 but creates too many Benign false positives.

Together with the Bot smoke result, Plan 02 has a weak near-term paper signal:

- `Bot` strict holdout is structurally unsupported because Bot appears only on
  `02-03-2018`.
- `Infilteration` has train and test support, but simple stage-aware weighting
  does not pass the improvement or safety gate.

## Decision

Do not promote Plan 02 as a new Praxis lead result right now.

Flag as:

- `negative_pilot`
- `not_new_praxis_candidate_yet`
- possible future work only if using a stronger approach, such as calibrated
  rare-class thresholding, representation learning, or TTA-style conservative
  rescue gates.

The current lead remains `TTA for Streaming APT Detection`.
