# Praxis 06 Submission TODO

Updated: 2026-05-14

## Current Package

| Item | Status |
|---|---|
| Venue-neutral LaTeX skeleton | Done: `main.tex` |
| Thesis-neutral expanded manuscript | Done: `main.tex` now includes related work, method, results, external validity, threats, and appendices |
| Thesis chapter wrapper | Done: `thesis_chapter.tex` reuses the same paper body |
| Local references | Done: `references.bib` |
| Build script | Done: `build.ps1` |
| GitHub Actions compile path | Done: `.github/workflows/praxis06-paper.yml` |
| CI compile | Pass: run `25881761738` built both article and thesis-chapter PDFs |
| Local compile | Optional/blocking only for local work: `pdflatex`/`latexmk` not installed locally |
| Local PDF render sanity | Pass: PyMuPDF rendered all 8 article pages from CI artifact to `tmp/pdfs/praxis06-tta-paper-ci-25875430166/`; thesis wrapper opens and extracts text |
| Contact-sheet layout review | Pass: `paper/praxis06_tta/VISUAL_LAYOUT_REVIEW_20260514.md` |
| Target style decision | Thesis chapter first: `paper/praxis06_tta/TARGET_STYLE_DECISION_20260514.md` |
| Claim guard | Done: original locked replay remains primary |

## Next Editorial Pass

1. Do a full-size human read of the article PDF and thesis-chapter PDF.
2. If targeting a venue instead, replace `article` class with the target class.
3. Tune section lengths for the target page budget.
4. Fix table widths and figure placement after target-class compile.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
