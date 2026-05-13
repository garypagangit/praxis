# Plan 02 Bot Smoke Result

Updated: 2026-05-09

## Run

- Experiment: Stage-Conditioned Class Imbalance
- Branch: `experiment/stage-conditioned-class-imbalance`
- Config: `configs/plan02-cicids2018-bot-rf-seed13-smoke.json`
- Output: `runs/plan02-bot-rf-smoke-seed13`
- Model: RF-only `Baseline-Single`
- Seed: `13`
- Holdout day: `02-03-2018`

## Result

| Metric | Value |
|---|---:|
| Macro-F1 | 0.2669 |
| Benign F1 | 0.8007 |
| Bot F1 | 0.0000 |
| Bot AUPRC | 0.2687 |
| FPR at 95% Benign recall | 1.0000 |

Test support and predictions:

| Label | Test support | Predicted |
|---|---:|---:|
| Benign | 7,313 | 9,364 |
| Bot | 2,687 | 0 |
| Infilteration | 0 | 636 |

## Support Finding

The EDA table shows `Bot` is confined to `02-03-2018`:

| Day | Label | Stage | Rows |
|---|---|---|---:|
| 02-03-2018 | Bot | Command and Control | 286,191 |

Under the strict `02-03-2018` holdout, the supervised classifier has no `Bot`
training support. The zero Bot F1 is therefore a structural unsupported-label
failure, not yet evidence that stage-conditioned weighting itself fails.

By contrast, `Infilteration` has support on both `01-03-2018` and `28-02-2018`:

| Day | Label | Stage | Rows |
|---|---|---|---:|
| 01-03-2018 | Infilteration | Lateral Movement | 93,063 |
| 28-02-2018 | Infilteration | Lateral Movement | 68,871 |

That makes the Infilteration split the viable strict pilot target for Plan 02.

## Decision

Do not use strict Bot holdout as the primary Plan 02 supervised-learning test.
Keep it as an out-of-distribution open-set blocker. Continue Plan 02 on the
Infilteration split first, where the rare class is present in train and test.

Next implement a narrow Infilteration-only stage-aware weighting pilot and
compare against the existing RF baseline:

- Baseline Infilteration RF smoke: Macro-F1 `0.2251`, Infilteration F1 `0.2068`, Benign F1 `0.6937`.
- Target improvement gate: Infilteration F1 `+0.03` absolute without Benign F1 dropping more than `0.02`.
