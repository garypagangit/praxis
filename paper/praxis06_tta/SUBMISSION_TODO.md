# Praxis 06 Submission TODO

Updated: 2026-05-15

## Current Package

| Item | Status |
|---|---|
| Venue-neutral LaTeX skeleton | Done: `main.tex` |
| Thesis-neutral expanded manuscript | Done: `main.tex` now includes related work, method, results, external validity, threats, and appendices; first editorial claim-alignment pass complete |
| Thesis chapter wrapper | Done: `thesis_chapter.tex` reuses the same paper body and names portfolio boundary evidence |
| Local references | Done: `references.bib` |
| Build script | Done: `build.ps1` |
| GitHub Actions compile path | Done: `.github/workflows/praxis06-paper.yml` |
| CI compile | Pass: run `25881761738` built both article and thesis-chapter PDFs |
| Local compile | Optional/blocking only for local work: `pdflatex`/`latexmk` not installed locally |
| Local PDF render sanity | Pass: PyMuPDF rendered all 8 article pages from CI artifact to `tmp/pdfs/praxis06-tta-paper-ci-25875430166/`; thesis wrapper opens and extracts text |
| Contact-sheet layout review | Pass: `paper/praxis06_tta/VISUAL_LAYOUT_REVIEW_20260514.md` |
| Thesis wrapper layout review | Pass: `paper/praxis06_tta/THESIS_CHAPTER_LAYOUT_REVIEW_20260514.md` |
| Target style decision | Thesis chapter first: `paper/praxis06_tta/TARGET_STYLE_DECISION_20260514.md` |
| Claim guard | Done: original locked replay remains primary |

## Next Editorial Pass

1. Trigger/inspect the next CI PDF build because local `pdflatex` is unavailable.
2. Do visual table and figure placement tuning from the CI PDFs.
3. If targeting a venue instead, replace `article` class with the target class.
4. Tune section lengths for the target page budget.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
