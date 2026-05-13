# Praxis 06 Submission Package Index

Generated: 2026-05-12

## Package Status

Status: **READY FOR VENUE CONVERSION**.

The package is ready to convert into a target defense, ACM, IEEE, USENIX-style, or arXiv manuscript format. The scientific claim is intentionally narrow: selective no-label test-time adaptation recovers a rare APT stage under held-out Unraveled source-file shift while preserving Data Exfiltration and using a small override rate.

## Core Manuscript Files

| File | Purpose |
|---|---|
| `reports/tta_streaming_apt/PRAXIS06_FULL_DRAFT_20260512.md` | Full venue-neutral manuscript draft |
| `reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md` | Paper-ready final report with thesis, RQs, hypotheses, literature frame, GMR, cloud audit, results, and conclusion |
| `reports/tta_streaming_apt/cloud_paper_hardening_20260513/PRAXIS06_FINAL_CLOUD_PAPER_AUDIT_20260513.md` | Cloud-generated paper audit and repeatability evidence |
| `reports/tta_streaming_apt/PRAXIS06_DEFENSE_HARDENING_ADDENDUM_20260513.md` | Seven-seed, validation sensitivity, BN protocol, override, PR-curve, and DAPT mechanism hardening addendum |
| `reports/tta_streaming_apt/PRAXIS06_DEFENSE_CHECKLIST_20260512.md` | Defense checklist and claim boundary |
| `reports/tta_streaming_apt/PRAXIS06_STAGE_LABEL_MAPPING_20260512.md` | Stage-label mapping and split support appendix |
| `reports/tta_streaming_apt/PRAXIS06_RELATED_WORK_NOTES_20260512.md` | Related-work scaffold and citation targets |
| `reports/tta_streaming_apt/PRAXIS06_REFERENCE_AUDIT_20260512.md` | Verified citation corrections and source URLs |
| `reports/tta_streaming_apt/PRAXIS06_REFERENCES_BIBTEX_20260512.bib` | Starter BibTeX file for venue conversion |
| `reports/tta_streaming_apt/DAPT2020_EXTERNAL_VALIDITY_NOTE_20260512.md` | DAPT detector-recipe appendix note |
| `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md` | Negative DAPT TTA feasibility gate |

## Main Evidence Artifacts

| Artifact | Role |
|---|---|
| `reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md` | Locked final replay of selected policy |
| `reports/tta_streaming_apt/ROBUSTNESS_AUDIT_20260509.md` | Robustness and proceed-gate audit |
| `reports/tta_streaming_apt/PRAXIS06_CANDIDATE_REPORT_20260509.md` | Praxis candidate summary |
| `runs/tta-result-audit-20260512/report.md` | Final artifact audit; all gates passed |
| S3 `experiments/tta-streaming-apt/runs/tta-locked-final-20260509/` | Cloud-staged locked replay artifacts |
| S3 `experiments/tta-streaming-apt/reports/tta-paper-hardening-20260513/` | Cloud paper-hardening audit, GMR files, and final audit JSON |
| `runs/tta-defense-hardening-20260513/` | Seven-seed hardening diagnostics, validation sensitivity, stream-order ablation, override decomposition, PR operating-point figures |
| `runs/mlp-support-floor-7seed-extension-20260513/` | Extra source checkpoints for seeds `45`-`48` plus original copied checkpoints |
| S3 `experiments/tta-streaming-apt/runs/tta-defense-hardening-20260513/` | Cloud-staged hardening diagnostics and source checkpoints |

## Tables

| Table | File | Use |
|---|---|---|
| Main result | `reports/tta_streaming_apt/paper_assets_20260509/tables/table1_main_result.md` | Main paper result table |
| Per-seed locked result | `reports/tta_streaming_apt/paper_assets_20260509/tables/table2_per_seed_locked_result.md` | Robustness/reproducibility table |
| Split counts | `reports/tta_streaming_apt/paper_assets_20260509/tables/table3_split_counts.md` | Dataset and class-support table |
| Leakage checks | `reports/tta_streaming_apt/paper_assets_20260509/tables/table4_leakage_checks.md` | Split integrity evidence |
| Confidence reject | `reports/tta_streaming_apt/paper_assets_20260509/tables/table5_confidence_reject_summary.md` | Alternative-explanation table |
| Override sensitivity | `reports/tta_streaming_apt/paper_assets_20260509/tables/table6_override_sensitivity.md` | Safety/ablation table |
| Seven-seed hardening | `runs/tta-defense-hardening-20260513/fixed_locked_seed_extension_summary.csv` | Robustness addendum, not primary result replacement |
| Validation sensitivity | `runs/tta-defense-hardening-20260513/validation_distribution_sensitivity_summary.csv` | Recon-heavy validation objection check |
| Override decomposition | `runs/tta-defense-hardening-20260513/override_decomposition_summary.csv` | Defense answer for what the gate changes |

## Figures

| Figure | File | Use |
|---|---|---|
| Method diagram | `reports/tta_streaming_apt/paper_assets_20260509/figures/figure1_method_diagram.png` | Method overview |
| Recon F1 by seed | `reports/tta_streaming_apt/paper_assets_20260509/figures/figure2_recon_f1_by_seed.png` | Main rare-stage recovery visualization |
| Override sensitivity | `reports/tta_streaming_apt/paper_assets_20260509/figures/figure3_override_sensitivity.png` | Safety/coverage visualization |
| Recon PR operating points | `runs/tta-defense-hardening-20260513/figure_recon_pr_operating_points.png` | Shows decision-policy shift under near-flat PR-AUC |
| DE PR operating points | `runs/tta-defense-hardening-20260513/figure_de_pr_operating_points.png` | Safety/operating-point companion figure |

## Allowed Claims

| Claim | Status | Evidence |
|---|---|---|
| Selective TTA improves locked Unraveled held-out source-file Macro F1 | Allowed | Macro F1 `0.7685` frozen to `0.8658` locked selective TTA |
| Selective TTA recovers Reconnaissance under the locked split | Allowed | Recon F1 `0.0250` frozen to `0.5050` locked selective TTA |
| Data Exfiltration is preserved in the locked mean | Allowed with caveat | DE F1 `0.9157` frozen to `0.9202`; per-seed DE guard documented |
| The result is not explained by confidence rejection | Allowed | Matched-rate confidence reject kept Recon F1 at `0.0000` |
| The detector recipe transfers to DAPT2020 | Allowed as appendix | DAPT MLP Macro F1 `0.6353 +/- 0.0043`, Recon F1 `0.8932 +/- 0.0089` |
| Seven-seed hardening supports the Recon recovery effect | Allowed as robustness addendum | All seven seeds improve Macro F1 and Recon F1, but extra seeds expose DE variance |

## Claims Not Allowed

| Claim | Reason |
|---|---|
| TTA generally solves APT detection | Too broad for the evidence |
| Cross-dataset TTA generality is proven | DAPT TTA feasibility gate is negative |
| DAPT supports Data Exfiltration conclusions | DAPT test split has only `2` Data Exfiltration examples |
| SEC-LoRD is positive | Strict Llama audit is negative for current seeding |
| Provenance graph experiments are positive | Full Cadets windowing is architecture-ready but label-blocked |

## Remaining Conversion Work

1. Choose target format or venue.
2. Convert `PRAXIS06_FULL_DRAFT_20260512.md` into that format.
3. Review `PRAXIS06_REFERENCES_BIBTEX_20260512.bib` against the target venue style.
4. Insert the main tables and figures from `paper_assets_20260509`.
5. Keep DAPT in the appendix, not the main selective-TTA result table.
6. Keep the seven-seed hardening run as an addendum, not as a replacement for the locked replay.
