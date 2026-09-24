# Final GWU-style praxis

## When Better APT Scores Hide Missed Attack Warnings

**Gary Pagan · September 24, 2026**

**120 pages · five chapters · three appendices · 10 figures · 31 tables · 30 APA references**

- [Editable Word manuscript](../../../output/doc/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.docx)
- [PDF manuscript](../../../output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf)
- [Complete evidence archive](https://github.com/garypagangit/praxis/blob/praxis-next-20260923/experiments/praxis_next/gwu_final_20260924/gwu_praxis_final_evidence.zip)
- [Source manuscript](manuscript.md) and [APA reference records](references.json)

The five chapters follow the author's original GWU GML praxis: introduction,
literature review, methodology, results, and discussion/conclusions. Formatting
was checked against GWU's official ETD guidance and its 2026 online-program
template. The current-study Graphical Model of Research follows the original
What/Why/How convention. Appendix C reproduces the original GMR image unchanged
as a clearly identified historical reference.

## What the praxis establishes

The primary result is a controlled measurement: better overall classification
scores can accompany fewer warnings for an attack stage on the same records.
The clean budget-three comparison increased mean macro-F1 from 0.7148 to 0.7379
while exfiltration warning recall fell from 85.18% to 76.25%. The supporting
experiments measure temporal training-composition effects and useful historical
context gains alongside their warning tradeoffs.

The contribution is empirical evidence and a reproducible evaluation procedure.
The main experiment covers one previously examined campaign. Neither a new
detector architecture nor a new metric definition is claimed. The literature
chapter identifies close precedents and the narrower contribution supported by
the completed measurements.

## Results and methods coverage

- **588 evaluated configurations:** 105 history-selection, 171 evidence-acquisition,
  18 temporal, and 294 secondary technique-policy views.
- **308 printed group means**, with all available metrics in the supplement.
- **1,764 class records**, 5,880 confusion cells, 6,732 subgroup records and
  16,344 subgroup-class records.
- The separate 126 original-threshold controls remain separately labelled.
- **141 LightGBM fits** in the main experiments; **two new Ridge fits** in the
  secondary study, which reuses existing logistic classifiers.
- Plain-language explanations, exact settings, and mathematical summaries of
  classifiers, selectors, acquisition choices, and evaluation quantities.
- Dataset scope, native labels, feature construction, source dependencies,
  chronological support, and real aggregate examples.

An evaluation view or fitting seed is not an independent campaign. Secondary
T1105 results use different targets and negative-label meanings from the main
four-class flow study. SCVIC, DAPT, DSRL and S-DAPT qualification is reported
separately from fitted model evaluation; there are no fabricated fitted results
for those extension releases.

## Inspect the evidence

| Material | Location |
|---|---|
| Every configuration | [CSV](results/tables/all_configuration_metrics.csv) |
| Available class precision, recall, F1, ROC-AUC and average precision | [CSV](results/tables/all_class_metrics.csv) |
| All group means | [CSV](results/tables/all_group_means.csv) |
| Complete confusion counts | [CSV](results/tables/all_confusion_counts.csv) |
| Dataset chapter and qualification boundaries | [Source](results/DATASET_CHAPTER.md) |
| Model settings and implementation audit | [Inventory](models/MODEL_INVENTORY.json) |
| Original GWU reference and current-template comparison | [Report](reference/REFERENCE_REPORT.md) |
| Document rendering and pagination | [Receipt](RENDER_RECEIPT.json) |
| Archive integrity | [Manifest](FINAL_MANIFEST.json); the archive hash is stored in the separate repository receipt |

Blank normalized table fields indicate that a metric was not supplied by the
source experiment. They do not mean zero. This edition adds explanation and
publication artifacts; it performs no additional model fits and does not
change the previous numerical evidence.

## Reproduction

Run `assemble_manuscript.py` from the repository. `render_gwu.py` builds Word
and PDF using python-docx, matplotlib, PyMuPDF and LibreOffice with its bundled
UNO Python. Its `--help` documents file arguments. `verify_final.py` checks the
delivered edition without changing files; it also works in an extracted bundle.
`package_final.py` verifies
the previous archive and original evidence before creating the final bundle.
Public aggregate-reproduction instructions from the preceding edition remain
inside the bundle. Raw traces and private row-linked predictions are excluded.

## Administrative status

This is a complete research manuscript for author and adviser review. It does
not assert that GWU has approved the study or that a defense has occurred.
Current committee appointments, defense/degree date, and signed certification
must come from the university's actual review process. Historical approval text
and inconsistent dates from the old reference are not carried forward as facts.
The reference chapter and reproducibility appendix disclose AI assistance and
the difference between computational review and independent scholarly review.
