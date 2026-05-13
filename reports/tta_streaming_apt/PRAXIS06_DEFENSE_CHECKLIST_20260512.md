# Praxis 06 Defense Checklist

Generated: 2026-05-12

## Current Decision

Status: **DEFENSE-DRAFT READY**.

The current package is ready for a Praxis 06 manuscript draft. It is not yet a final submission package because it still needs conversion into a target venue format. The optional DAPT2020 cross-dataset check is now closed: detector-recipe transfer is useful appendix evidence, but DAPT TTA feasibility is negative.

## Evidence Checklist

| Requirement | Status | Evidence |
|---|---|---|
| Clear failure motivation | PASS | Praxis 04 negative: predicted-stage routing failed under held-out shift |
| Locked source-file split | PASS | `train_test`, `train_val`, and `val_test` source overlap are all `0` |
| No test-label adaptation | PASS | Method uses `bn_adapt` over unlabeled stream |
| Validation-selected policy | PASS | Locked policy from `selected_hybrid_policies.csv` |
| Locked final replay | PASS | `reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md` |
| Rare-stage recovery | PASS | Recon F1 `0.0250` to `0.5050` |
| Safety-stage preservation | PASS | DE F1 `0.9157` to `0.9202`; per-seed DE deltas within guard |
| Small intervention | PASS | Override rate `0.0470` |
| Alternative explanation check | PASS | Matched confidence-reject Recon F1 remains `0.0000` |
| AWS reproducibility | PASS | AWS/local audit matched headline metrics within tolerance |
| Paper tables and figures | PASS | `reports/tta_streaming_apt/paper_assets_20260509/` |
| Method diagram | PASS | `reports/tta_streaming_apt/paper_assets_20260509/figures/figure1_method_diagram.png` |
| Full manuscript draft | PASS | `reports/tta_streaming_apt/PRAXIS06_FULL_DRAFT_20260512.md` |
| Stage-label mapping appendix | PASS | `reports/tta_streaming_apt/PRAXIS06_STAGE_LABEL_MAPPING_20260512.md` |
| Cross-dataset external validity | CLOSED/PARTIAL | DAPT2020 3-seed MLP recipe check is useful appendix evidence; true DAPT TTA feasibility gate is negative |
| Related-work scaffold | PASS | `reports/tta_streaming_apt/PRAXIS06_RELATED_WORK_NOTES_20260512.md` |
| DAPT TTA feasibility check | PASS/NEGATIVE | `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md` shows selected TENT test Macro F1 delta `-0.2874` |
| Final artifact audit | PASS | `runs/tta-result-audit-20260512/report.md`; all gate checks pass and no material artifact-level risks found |
| Submission package index | PASS | `reports/tta_streaming_apt/PRAXIS06_SUBMISSION_PACKAGE_INDEX_20260512.md` maps claims to evidence, tables, and figures |
| Reference hygiene | PASS | `reports/tta_streaming_apt/PRAXIS06_REFERENCE_AUDIT_20260512.md`; MAGIC/KAIROS venue shorthand corrected |

## Claims Allowed

| Claim | Allowed? | Wording |
|---|---|---|
| Selective TTA improves locked Unraveled held-out source-file Macro F1 | Yes | Strong, directly supported |
| Selective TTA recovers Reconnaissance under this split | Yes | Strong, directly supported |
| Data Exfiltration is preserved in the locked mean and within guard per seed | Yes | Supported with caveat |
| The result is not explained by confidence rejection | Yes | Supported by matched-rate baseline |
| TTA generally solves APT detection | No | Too broad |
| Cross-dataset generality is proven | No | DAPT TTA feasibility gate was negative |
| Provenance graph experiments are now positive | No | Architecture only; label-blocked |

## Remaining Work Before Submission

1. Convert this Markdown draft into the target venue format.
2. Review starter BibTeX against the target venue style.
3. Keep DAPT2020 in the appendix as detector-recipe transfer plus a negative TTA feasibility check.

## Recommended Defense Framing

The safest framing is:

> Praxis 04 showed that predicted-stage routing failed because rare-stage representations did not survive held-out source-file shift. Praxis 06 shows that a conservative no-label adaptation gate can recover that rare-stage failure mode while protecting Data Exfiltration.

That is the spine. Keep the claim narrow and it holds.
