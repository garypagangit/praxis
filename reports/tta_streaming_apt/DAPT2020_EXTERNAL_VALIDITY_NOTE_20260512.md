# DAPT2020 External Validity Note

Generated: 2026-05-12

## Decision

Status: **USEFUL APPENDIX RESULT; TTA FEASIBILITY GATE NEGATIVE**.

The DAPT2020 detector run shows that the Unraveled tabular MLP recipe family transfers reasonably to a second APT-flow dataset. A follow-up TTA feasibility gate then tested unsupervised BatchNorm-stat adaptation plus a small TENT sweep on those same DAPT MLP checkpoints, and adaptation degraded sharply. DAPT should therefore be cited only as detector-recipe external-validity evidence, not as support for cross-dataset TTA generality.

## Run

| Field | Value |
|---|---|
| Run directory | `runs/dapt2020-cross-dataset-mlp-3seed-clean-20260512/` |
| Script | `scripts/run_dapt_mlp_baseline.py` |
| Config | `configs/dapt2020-local-fast.json` |
| Seeds | `42,43,44` |
| Recipe | MLP + targeted ADASYN + weighted CE |
| Dependency fixed | `imbalanced-learn>=0.14,<0.15` added to `requirements-local.txt` |

## TTA Feasibility Gate

| Field | Value |
|---|---|
| Run directory | `runs/dapt2020-tta-feasibility-20260512/` |
| Script | `scripts/run_dapt_tta_feasibility_gate.py` |
| Report | `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md` |
| Methods | Frozen, BatchNorm-stat adaptation, TENT lr `1e-5`, `5e-5`, `1e-4` |
| Gate status | `NO_DAPT_TTA_SUPPORT` |

Validation selected `tent_lr_0.0001`, but the held-out DAPT test deltas versus frozen were negative: Macro F1 `-0.2874`, Recon F1 `-0.6589`, PR-AUC `-0.2923`, and Data Exfiltration F1 `-0.0354`.

## Dataset Support

| Split | Benign | Recon | Establish Foothold | Lateral Movement | Data Exfiltration |
|---|---:|---:|---:|---:|---:|
| Train | `44,616` | `8,343` | `6,024` | `1,723` | `10` |
| Validation | `9,548` | `1,783` | `1,288` | `364` | `2` |
| Test | `9,548` | `1,783` | `1,288` | `364` | `2` |

## Result

| Metric | Mean | Std |
|---|---:|---:|
| Accuracy | `0.8721` | `0.0031` |
| Macro F1 | `0.6353` | `0.0043` |
| ROC-AUC | `0.9723` | `0.0021` |
| PR-AUC | `0.6853` | `0.0045` |
| Recon F1 | `0.8932` | `0.0089` |
| Data Exfiltration F1 | `0.0387` | `0.0160` |

Delta versus the existing DAPT graph reference in the script:

| Comparison | Delta |
|---|---:|
| Macro F1 vs graph reference | `+0.0765` |
| ROC-AUC vs graph reference | `+0.0305` |

## Interpretation

This helps the Praxis 06 story in one narrow way: the tabular MLP recipe is not obviously Unraveled-only. It performs competitively on DAPT2020, especially for Reconnaissance.

It does not validate the selective TTA claim. The follow-up DAPT TTA gate is negative, and DAPT2020 also cannot support Data Exfiltration conclusions because the split has only `2` Data Exfiltration examples in validation and `2` in test.

## How To Use In The Paper

Use as an appendix paragraph:

> As an external-validity check on the detector recipe, we ran the same MLP + targeted ADASYN + weighted cross-entropy family on DAPT2020. Across three seeds it reached Macro F1 `0.6353 +/- 0.0043` and Reconnaissance F1 `0.8932 +/- 0.0089`. A follow-up unsupervised TTA feasibility gate on the same DAPT checkpoints was negative, with the validation-selected TENT variant reducing test Macro F1 by `0.2874` versus frozen. This does not support cross-dataset TTA generality, and Data Exfiltration conclusions are not supported because the test split contains only two Data Exfiltration samples.

Do not put this in the main results table for the selective TTA claim.
