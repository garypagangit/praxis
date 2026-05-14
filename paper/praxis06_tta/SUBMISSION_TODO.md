# Praxis 06 Submission TODO

Updated: 2026-05-14

## Current Package

| Item | Status |
|---|---|
| Venue-neutral LaTeX skeleton | Done: `main.tex` |
| Thesis-neutral expanded manuscript | Done: `main.tex` now includes related work, method, results, external validity, threats, and appendices |
| Local references | Done: `references.bib` |
| Build script | Done: `build.ps1` |
| GitHub Actions compile path | Done: `.github/workflows/praxis06-paper.yml` |
| CI compile | Pass: figure-integrated run `25875430166`, 8-page PDF artifact |
| Local compile | Optional/blocking only for local work: `pdflatex`/`latexmk` not installed locally |
| Claim guard | Done: original locked replay remains primary |

## Next Editorial Pass

1. Pick target format: thesis chapter, arXiv, ACM, IEEE, USENIX-style.
2. Replace `article` class with the target class.
3. Tune section lengths for the target page budget.
4. Render PDF pages visually in an environment with Poppler or another PDF renderer; local text sanity passed but image-level review is still open.
5. Fix table widths and figure placement after target-class compile.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
