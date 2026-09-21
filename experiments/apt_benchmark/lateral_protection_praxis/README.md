# Reducing false alarms while preserving lateral-movement detection

**Status: preserved proposal; the subsequent development study is complete and audited, September 21, 2026.** The proposal files below remain the original planning artifact. The [executed study](../lateral_protection_experiment/README.md) completed 19 groups and 152 final models, but the primary screen was **INFEASIBLE**, with selected policies available for only six of ten seeds. No validated protection method or algorithmic novelty is claimed.

Read the current [empirical paper](../lateral_protection_experiment/paper/PRAXIS.md), [Word](../lateral_protection_experiment/paper/PRAXIS.docx), [PDF](../lateral_protection_experiment/paper/PRAXIS.pdf), and [evidence package](../results/lateral_protection_v1/REPORT.md) for the completed results. Among the six feasible primary seeds, verification false-positive rate fell from 0.7195% to 0.4800% while lateral-flow detection fell from 88.19% to 84.49%. These subset means do not meet the full ten-seed protection requirement. The completed work used CPU and passed 40 new implementation and integrity tests, separate from historical suite counts.

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
