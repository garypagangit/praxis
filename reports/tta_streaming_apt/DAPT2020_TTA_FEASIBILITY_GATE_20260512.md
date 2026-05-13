# DAPT-2020 TTA Feasibility Gate

- Generated: 2026-05-12T11:45:22.298188+00:00
- Run directory: `C:\Users\garyp\OneDrive\Documents\codex\runs\dapt2020-tta-feasibility-20260512`
- Source MLP run: `C:\Users\garyp\OneDrive\Documents\codex\runs\dapt2020-cross-dataset-mlp-3seed-clean-20260512`
- Seeds: `42, 43, 44`
- TENT learning rates: `1e-05, 5e-05, 0.0001`
- Gate status: `NO_DAPT_TTA_SUPPORT`

## Purpose

This is a cross-dataset feasibility check for the TTA mechanism, not a new defense-grade final result. It reuses the frozen 3-seed DAPT MLP checkpoints and evaluates unsupervised BatchNorm-stat adaptation plus a small TENT sweep on the DAPT validation and test streams.

## Class Support

| split | stage | count | fraction |
| --- | --- | --- | --- |
| train | Benign | 44616 | 0.7348 |
| train | Reconnaissance | 8343 | 0.1374 |
| train | Establish Foothold | 6024 | 0.0992 |
| train | Lateral Movement | 1723 | 0.0284 |
| train | Data Exfiltration | 10 | 0.0002 |
| val | Benign | 9548 | 0.7353 |
| val | Reconnaissance | 1783 | 0.1373 |
| val | Establish Foothold | 1288 | 0.0992 |
| val | Lateral Movement | 364 | 0.0280 |
| val | Data Exfiltration | 2 | 0.0002 |
| test | Benign | 9548 | 0.7353 |
| test | Reconnaissance | 1783 | 0.1373 |
| test | Establish Foothold | 1288 | 0.0992 |
| test | Lateral Movement | 364 | 0.0280 |
| test | Data Exfiltration | 2 | 0.0002 |

## Summary

| method | split | accuracy_mean | accuracy_std | macro_f1_mean | macro_f1_std | pr_auc_mean | pr_auc_std | benign_f1_mean | recon_f1_mean | de_f1_mean | accuracy_delta_vs_frozen | macro_f1_delta_vs_frozen | pr_auc_delta_vs_frozen | benign_f1_delta_vs_frozen | recon_f1_delta_vs_frozen | de_f1_delta_vs_frozen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bn_adapt | test | 0.6956 | 0.0301 | 0.3479 | 0.0351 | 0.3932 | 0.0169 | 0.8707 | 0.2341 | 0.0033 | -0.1765 | -0.2875 | -0.2921 | -0.0375 | -0.6591 | -0.0354 |
| bn_adapt | val | 0.6774 | 0.0138 | 0.3398 | 0.0244 | 0.5423 | 0.0276 | 0.8400 | 0.3223 | 0.0049 | nan | nan | nan | nan | nan | nan |
| frozen | test | 0.8721 | 0.0031 | 0.6353 | 0.0043 | 0.6853 | 0.0045 | 0.9082 | 0.8932 | 0.0387 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| frozen | val | 0.8666 | 0.0038 | 0.6364 | 0.0034 | 0.7850 | 0.0068 | 0.9021 | 0.8623 | 0.0413 | nan | nan | nan | nan | nan | nan |
| tent_lr_0.0001 | test | 0.6958 | 0.0300 | 0.3479 | 0.0350 | 0.3930 | 0.0171 | 0.8708 | 0.2343 | 0.0033 | -0.1763 | -0.2874 | -0.2923 | -0.0374 | -0.6589 | -0.0354 |
| tent_lr_0.0001 | val | 0.6776 | 0.0138 | 0.3399 | 0.0244 | 0.5424 | 0.0276 | 0.8402 | 0.3225 | 0.0049 | nan | nan | nan | nan | nan | nan |
| tent_lr_1e-05 | test | 0.6956 | 0.0301 | 0.3479 | 0.0351 | 0.3932 | 0.0169 | 0.8707 | 0.2341 | 0.0033 | -0.1764 | -0.2874 | -0.2922 | -0.0375 | -0.6590 | -0.0354 |
| tent_lr_1e-05 | val | 0.6775 | 0.0139 | 0.3398 | 0.0245 | 0.5423 | 0.0276 | 0.8401 | 0.3223 | 0.0049 | nan | nan | nan | nan | nan | nan |
| tent_lr_5e-05 | test | 0.6957 | 0.0300 | 0.3479 | 0.0350 | 0.3931 | 0.0170 | 0.8708 | 0.2342 | 0.0033 | -0.1764 | -0.2874 | -0.2922 | -0.0374 | -0.6589 | -0.0354 |
| tent_lr_5e-05 | val | 0.6776 | 0.0139 | 0.3399 | 0.0244 | 0.5424 | 0.0276 | 0.8401 | 0.3225 | 0.0049 | nan | nan | nan | nan | nan | nan |

## Validation-Selected Candidate

```json
{
  "method": "tent_lr_0.0001",
  "val_macro_f1_mean": 0.3398852761854057,
  "val_recon_f1_mean": 0.32249005999335506,
  "val_de_f1_mean": 0.00488071073010861
}
```

## Gate Decision

```json
{
  "status": "NO_DAPT_TTA_SUPPORT",
  "reason": "Selected validation adaptation did not improve the held-out DAPT test split enough.",
  "selected_method": "tent_lr_0.0001",
  "test_de_support": 2,
  "macro_f1_delta": -0.28739887846558526,
  "recon_f1_delta": -0.6588557083521562,
  "de_f1_delta": -0.035386181133123695,
  "pr_auc_delta": -0.2922892787166672
}
```

## Interpretation

The DAPT gate does not provide support for extending the locked Unraveled TTA claim. Keep the DAPT MLP recipe result as external detector evidence, but do not claim that TTA transfers on this dataset.

## Defense Note

The locked Unraveled TTA replay remains the lead evidence. This DAPT gate is deliberately conservative because the dataset split is structurally weak for Data Exfiltration and does not reproduce the same deployment shift setting as the Unraveled source-file stream.