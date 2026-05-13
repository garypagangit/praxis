# Plan 02 Start Report - Stage-Conditioned Class Imbalance

Updated: 2026-05-09

## Started

Plan 02 has moved from portfolio item to active gate work.

Created:

- `configs/preregistration_plan02.yaml`
- `configs/plan02-cicids2018-infiltration-baseline-pilot.json`
- `configs/plan02-cicids2018-bot-baseline-pilot.json`
- `reports/plan02_stage_conditioned_imbalance/eda/`

## EDA Gate Result

The CIC-IDS2018 scan completed across `16,233,002` rows, `10` CSV files, `16` attack labels, and `6` frozen kill-chain stages.

Stage support:

| Stage | Rows |
|---|---:|
| Benign | 13,484,708 |
| Actions on Objectives | 1,918,233 |
| Initial Access | 381,877 |
| Command and Control | 286,191 |
| Lateral Movement | 161,934 |
| Unknown | 59 |

Critical split finding:

- `Infilteration` appears on `28-02-2018` and `01-03-2018`.
- `Bot` appears on `02-03-2018`.
- The old Praxis 04 default holdout, `02-03-2018`, is a Bot/C2 stress test, not an Infilteration rare-stage test.

## Decision

Proceed with Plan 02, but start with strict baseline pilots before implementing focal loss or stage-aware sample weighting.

## Smoke Result

Completed first strict Infilteration-holdout RF smoke:

- Config: `configs/plan02-cicids2018-infiltration-rf-seed13-smoke.json`
- Output: `runs/plan02-infiltration-rf-smoke-seed13`
- Seed: `13`
- Train rows: `70,000`
- Validation rows: `20,000`
- Test rows: `10,000`
- Test day: `28-02-2018`
- Test support: `8,919` Benign, `1,081` Infilteration

Metrics:

| Metric | Value |
|---|---:|
| Macro-F1 | 0.2251 |
| Benign F1 | 0.6937 |
| Infilteration F1 | 0.2068 |
| Infilteration AUPRC | 0.1172 |
| FPR at 95% Benign recall | 0.9972 |

Interpretation:

The strict rare-day baseline is weak but informative. The model finds some Infilteration signal, but it pays for it with heavy Benign false-positive pressure. This is exactly the kind of baseline Plan 02 needs before stage-aware weighting is introduced.

The command wrapper timed out after the metrics payload was printed, but the run files were written successfully.

## Next Runs

The next planned runs are:

```powershell
.\.venv\Scripts\python.exe scripts\run_praxis04_local_pilot.py `
  --base-config configs\plan02-cicids2018-infiltration-baseline-pilot.json `
  --output-root runs\plan02-cicids2018-infiltration-baseline-pilot

.\.venv\Scripts\python.exe scripts\run_praxis04_local_pilot.py `
  --base-config configs\plan02-cicids2018-bot-baseline-pilot.json `
  --output-root runs\plan02-cicids2018-bot-baseline-pilot
```

## AWS Mirror Blocker

The EC2 mirror status check could not complete because AWS profile `praxis-build` has an expired SSO session. Refresh with:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" sso login --profile praxis-build
```

Then rerun the SSM mirror check and stop the instance if the mirror has completed.
