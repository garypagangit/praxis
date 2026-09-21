# Reducing false alarms while preserving lateral-movement detection

**Status: final praxis proposal draft, September 21, 2026.** The motivating experiments are complete; the proposed protection study has not been run or registered. No new effectiveness or algorithmic novelty is claimed.

- [Editable Word proposal](PRAXIS_PROPOSAL.docx): eight visually reviewed pages.
- [Readable proposal source](PRAXIS_PROPOSAL.md): thesis, problem, hypotheses, proposed method, controls, data qualifications, confirmation criteria, and references.
- [Literature review](LITERATURE_REVIEW.md): primary sources and closest prior work, including the 2026 lateral-movement/resampling paper.
- [Method review](METHOD_REVIEW.md): matched budgets, conservative verification, independent units, and statistical feasibility.
- [Evidence and data plan](EVIDENCE_AND_DATA_PLAN.md): independently recomputed preliminary metrics and qualified dataset roles.
- [Document receipt](DOCUMENT_RECEIPT.json): hashes, source-evidence bindings, and verification scope.

The applied question is whether a detector can reduce benign alerts while meeting a declared lateral-detection requirement. Primary comparisons fix fitting labels at 160 attack plus 1,024 normal examples; smaller normal-support budgets are secondary. Constrained classification and weighting are established methods, and any equivalent comparator is retained under its existing name.

The proposal requires new independent evidence. SCVIC and Unraveled are exposed development sources. DEDALE is conditional: its first two weeks are benign only, and the labeled CICFlowMeter join has not been qualified. Source transfer, target-benign calibration, and within-dataset procedure replication must remain distinct.

The proposed confirmation targets are at least 20% relative false-alarm reduction, less than three percentage points of lateral-recall loss, lateral recall at least 90%, and benign FPR at most 1%, with the specified one-sided uncertainty bounds. These are future operating requirements, not retroactive pass criteria or an industry standard.

## Rebuild the document

Use a document environment with `python-docx` installed; this builder does not execute an experiment:

```powershell
python experiments/apt_benchmark/lateral_protection_praxis/build_document.py --output output/doc/Reducing_False_Alarms_While_Preserving_Lateral_Movement.docx
```

Render using LibreOffice and inspect all pages after content or layout changes. The delivered Word copy is byte-identical to the rendered document recorded in the receipt. PDF and page images are retained privately for layout verification.
