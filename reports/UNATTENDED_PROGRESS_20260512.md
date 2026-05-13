# Unattended Progress

Generated: 2026-05-12

## Executive Read

I kept pushing on the strongest defensible path: Praxis 06 / TTA packaging and the remaining DAPT cross-dataset question.

The new DAPT TTA feasibility gate is negative. That closes the open question honestly: DAPT2020 can stay in the appendix as detector-recipe transfer evidence, but it should not be used to claim cross-dataset TTA generality.

## Work Completed

| Area | Artifact | Result | Decision |
|---|---|---|---|
| DAPT2020 TTA feasibility | `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md` | Validation selected `tent_lr_0.0001`, but test Macro F1 delta was `-0.2874`, Recon F1 delta `-0.6589`, PR-AUC delta `-0.2923` vs frozen | Negative. Do not claim DAPT TTA transfer |
| DAPT2020 external-validity note | `reports/tta_streaming_apt/DAPT2020_EXTERNAL_VALIDITY_NOTE_20260512.md` | Updated to include both detector-recipe positive evidence and the negative TTA feasibility gate | Use as appendix only |
| Praxis 06 full draft | `reports/tta_streaming_apt/PRAXIS06_FULL_DRAFT_20260512.md` | Added DAPT TTA negative result to the external-validity section | Keeps the claim narrow and defensible |
| Defense checklist | `reports/tta_streaming_apt/PRAXIS06_DEFENSE_CHECKLIST_20260512.md` | Added DAPT TTA negative gate and final artifact audit | Status remains defense-draft ready |
| TTA package audit | `runs/tta-result-audit-20260512/report.md` | All gate checks passed; no material artifact-level risks found | Supports moving to paper packaging |
| Dashboard/final evaluation | `reports/EXPERIMENT_DASHBOARD.md`, `reports/EXPERIMENT_FINAL_EVALUATION_20260511.md` | Updated TTA row and DAPT appendix posture | Portfolio state is current |
| Provenance label requirements | `reports/provenance_architecture/PROVENANCE_LABEL_REQUIREMENTS_20260512.md` | Documented exact interval-label schema and minimum support gates; added interval-label regression test | Keeps graph/drift/TGN/watermarking blocked unless labels are real |
| Reference hygiene | `reports/tta_streaming_apt/PRAXIS06_REFERENCE_AUDIT_20260512.md`, `reports/tta_streaming_apt/PRAXIS06_REFERENCES_BIBTEX_20260512.bib` | Corrected MAGIC/KAIROS venue shorthand and created starter BibTeX | Reduces paper-conversion risk |

## DAPT TTA Gate Result

| Method | Split | Macro F1 | Recon F1 | DE F1 | PR-AUC | Macro Delta vs Frozen |
|---|---|---:|---:|---:|---:|---:|
| Frozen | Test | `0.6353` | `0.8932` | `0.0387` | `0.6853` | `0.0000` |
| BN adapt | Test | `0.3479` | `0.2341` | `0.0033` | `0.3932` | `-0.2875` |
| TENT lr `1e-4` | Test | `0.3479` | `0.2343` | `0.0033` | `0.3930` | `-0.2874` |

Gate status: `NO_DAPT_TTA_SUPPORT`.

Defense interpretation: the locked Unraveled result remains the TTA claim. DAPT is useful only as evidence that the detector recipe can run on a second APT-flow dataset. It does not support a broad TTA-generalization claim, and DE remains too under-supported in DAPT with only `2` test examples.

## Praxis 06 Current Posture

| Item | Status |
|---|---|
| Locked Unraveled final replay | Positive |
| Robustness audit | Passed |
| AWS/local agreement | Passed in prior audit |
| Confidence-reject alternative | Rejected as explanation |
| Paper tables/figures | Built |
| Method diagram | Built |
| Stage mapping appendix | Built |
| Full draft | Built |
| DAPT detector appendix | Useful |
| DAPT TTA feasibility | Negative |
| Final artifact audit | Passed |
| Reference audit | Built |

## Next Best Move

Convert the Praxis 06 Markdown package into the target venue format. I would not run more side experiments until a venue or defense format is chosen; the key scientific claim is already cleaner than the alternatives.

If we want one more architecture track after that, the only honest unlock is labels: interval labels or a better labeled host stream for the provenance window factory. Without that, provenance graph/drift/watermark/privacy results should stay architecture-ready, not positive.

## Verification

`python -m pytest tests/test_provenance_window_factory.py tests/test_detector_registry.py -q`

Result: `5 passed`.
