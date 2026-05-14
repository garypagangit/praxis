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
| CI compile | Pending recheck after adding `thesis_chapter.tex`; last article-only pass was run `25875430166` |
| Local compile | Optional/blocking only for local work: `pdflatex`/`latexmk` not installed locally |
| Local PDF render sanity | Pass: PyMuPDF rendered all 8 pages from CI artifact to `tmp/pdfs/praxis06-tta-paper-ci-25875430166/` |
| Contact-sheet layout review | Pass: `paper/praxis06_tta/VISUAL_LAYOUT_REVIEW_20260514.md` |
| Target style decision | Thesis chapter first: `paper/praxis06_tta/TARGET_STYLE_DECISION_20260514.md` |
| Claim guard | Done: original locked replay remains primary |

## Next Editorial Pass

1. Confirm CI compiles both `main.tex` and `thesis_chapter.tex`.
2. Do a full-size human read of the article PDF and thesis-chapter PDF.
3. If targeting a venue instead, replace `article` class with the target class.
4. Tune section lengths for the target page budget.
5. Fix table widths and figure placement after target-class compile.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
