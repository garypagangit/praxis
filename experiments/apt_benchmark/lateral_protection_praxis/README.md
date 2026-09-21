# Reducing false alarms while preserving lateral-movement detection

**Status: original proposal preserved; subsequent experiments completed and audited.** The proposal files below remain the planning artifact. The current recommended reading is the findings-led [Improving APT Alert Efficiency: Measured Gains and Lateral-Movement Tradeoffs](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.md), [Word](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.docx), and [PDF](../lateral_protection_experiment/paper/FINDINGS_PRAXIS.pdf).

The completed evidence contains positive improvements with explicit costs. More benign fitting examples yielded **96.02% fewer false positives** and macro-F1 **0.4421 to 0.6543**, while lateral detection fell **94.24% to 83.06%**. In the subsequent 152-cell study, the candidate reduced false positives **33.3%** and raised attack F1 **0.8770 to 0.9044** on six feasible supports, while lateral detection fell **88.19% to 84.49%**. The exploratory same-six reference comparison also found **25.9% fewer false positives and +0.46pp mean lateral recall**, but only two of six seeds improved both measures.

The [actuals and costs](../lateral_protection_experiment/paper/FINDINGS_ACTUALS.md) and [literature gap](../lateral_protection_experiment/paper/FINDINGS_LITERATURE_GAP.md) explain the empirical contribution. This post-result interpretation changes no experimental protocol or outcome: the original all-ten-seed screen remains **INFEASIBLE**, with four unavailable selections. No validated novel algorithm or independent protection guarantee is claimed. The [prior screen-oriented paper](../lateral_protection_experiment/paper/PRAXIS.md) and [original audited evidence](../results/lateral_protection_v1/REPORT.md) remain preserved. The study used CPU and passed 40 new implementation and integrity tests, separate from historical counts.

## Original proposal and reviews

- [Editable Word proposal](PRAXIS_PROPOSAL.docx): eight visually reviewed pages.
- [Readable proposal source](PRAXIS_PROPOSAL.md): thesis, problem, hypotheses, proposed method, controls, data qualifications, confirmation criteria, and references.
- [Literature review](LITERATURE_REVIEW.md): primary sources and closest prior work, including the 2026 lateral-movement/resampling paper.
- [Method review](METHOD_REVIEW.md): matched budgets, conservative verification, independent units, and statistical feasibility.
- [Evidence and data plan](EVIDENCE_AND_DATA_PLAN.md): independently recomputed preliminary metrics and qualified dataset roles.
- [Document receipt](DOCUMENT_RECEIPT.json): hashes, source-evidence bindings, and verification scope.

The proposal asked whether a detector can reduce benign alerts while meeting a declared lateral-detection requirement. Primary comparisons fixed fitting labels at 160 attack plus 1,024 normal examples; smaller normal-support budgets were secondary. Constrained classification and weighting are established methods, and any equivalent comparator is retained under its existing name.

The proposal's independent-confirmation requirement remains unmet. SCVIC and Unraveled are exposed development sources. The subsequent [DEDALE qualification](../lateral_protection_experiment/dedale/QUALIFICATION.md) established that author-labeled CICFlowMeter tables were directly usable; an additional Zeek join was unnecessary. However, the acquired attack period contained only four lateral flows from one execution. The fixed-seed external stress test evaluated ordinary controls only because the source candidate was infeasible: 7,418 false positives per 100,000 benign flows with one of four lateral flows detected, versus 24,511 false positives with all four detected after source-benign thresholding. This does not establish independent protection.

The original proposal's confirmation targets require false-alarm reduction and lateral protection with specified one-sided uncertainty bounds. The executed study separately froze a development screen using point estimates, with strictly greater than 20% relative false-alarm reduction, less than three percentage points of lateral-recall loss, lateral recall at least 90%, and benign FPR at most 1%. It did not satisfy that screen and does not supply the proposal's independent statistical confirmation. Neither set of requirements is an industry standard.

## Rebuild the document

Use a document environment with `python-docx` installed; this builder does not execute an experiment:

```powershell
python experiments/apt_benchmark/lateral_protection_praxis/build_document.py --output output/doc/Reducing_False_Alarms_While_Preserving_Lateral_Movement.docx
```

Render using LibreOffice and inspect all pages after content or layout changes. The delivered Word copy is byte-identical to the rendered document recorded in the receipt. PDF and page images are retained privately for layout verification.
