# Retrieval-Conditioned CTI Compliance Paper Package

Updated: 2026-05-18

This folder contains the Praxis 07 paper/chapter draft for the bounded CTI retrieval result.

## Open First

- `main.tex` - standalone article draft.
- `thesis_chapter.tex` - thesis/chapter wrapper that reuses `main.tex`.
- `RELATIONSHIP_EVIDENCE_CTI_PAPER_OUTLINE_20260517.md` - post-gate outline and writing plan.
- `references.bib` - local bibliography.

## Claim Boundary

Use the title:

> Retrieval-Conditioned CTI Compliance: A Protocol-Specific Result

Do claim:

- Question-specific ATT&CK retrieval improves strict CTI-MCQ compliance on the locked 106-row evidence-addressable slice.
- The effect appears on Llama-3.1-8B and Llama-3.2-3B.
- Relationship evidence is the strongest tested retrieval condition.

Do not claim:

- SEC-LoRD or DS-LoRD extraction success.
- Pure relationship causality.
- Open-ended CTI reasoning improvement.
- Benchmark-wide generalization beyond the evidence-addressable slice.

## Source Reports

- `../../reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`
- `../../reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_20260517.md`
- `../../reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_20260517.md`
- `../../reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md`

## Build

```powershell
.\build.ps1 -Target main
.\build.ps1 -Target thesis_chapter
```

The local Windows environment may not have a LaTeX engine installed. If `latexmk` or `pdflatex` is unavailable, compile in Overleaf, GitHub Actions, or a TeX-enabled cloud environment.
