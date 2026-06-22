# Praxis 06 Submission TODO

Updated: 2026-06-22

## Current Package

| Item | Status |
|---|---|
| Venue-neutral LaTeX skeleton | Done: `main.tex` |
| Thesis-neutral expanded manuscript | Done: `main.tex` now includes related work, method, results, external validity, threats, and appendices; first editorial claim-alignment pass complete |
| Thesis chapter wrapper | Done: `thesis_chapter.tex` reuses the same paper body and names portfolio boundary evidence |
| Local references | Done: `references.bib` |
| Build script | Done: `build.ps1` |
| GitHub Actions compile path | Done: `.github/workflows/praxis06-paper.yml` |
| CI compile | Pass: run `25944754838` built both article and thesis-chapter PDFs from commit `8e8e979` |
| Local compile | Optional/blocking only for local work: `pdflatex`/`latexmk` not installed locally |
| Local PDF render sanity | Pass: PyMuPDF rendered all 9 article pages and all 14 thesis pages from CI artifact `25944754838` |
| Contact-sheet layout review | Pass: `paper/praxis06_tta/VISUAL_LAYOUT_REVIEW_20260515.md` |
| Thesis wrapper layout review | Pass: `paper/praxis06_tta/THESIS_CHAPTER_LAYOUT_REVIEW_20260514.md` |
| Target style decision | Thesis chapter first: `paper/praxis06_tta/TARGET_STYLE_DECISION_20260514.md` |
| Claim guard | Done: original locked replay remains primary |
| 2026-06-22 layout pass | Done: denser tables, more flexible float placement, smaller PR figures, and main-body float barrier before appendices |
| 2026-06-22 CI/layout verification | Pass: GitHub Actions run `27945299849`; article `8` pages, thesis chapter `15` pages; PyMuPDF render found no blank or text-sparse pages |

## Next Editorial Pass

1. Do line-by-line full-resolution proof reading from CI run `27945299849`.
2. Decide whether the 8-page article is the target venue shape or whether a venue class should replace the neutral `article` class.
3. If targeting a venue instead, replace `article` class with the target class.
4. Tune section lengths for the target page budget.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
