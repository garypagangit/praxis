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
| CI compile | Pass: run `25874826445`, 4-page PDF artifact |
| Local compile | Optional/blocking only for local work: `pdflatex`/`latexmk` not installed locally |
| Claim guard | Done: original locked replay remains primary |

## Next Editorial Pass

1. Push the expanded manuscript and confirm GitHub Actions still compiles it.
2. Pick target format: thesis chapter, arXiv, ACM, IEEE, USENIX-style.
3. Replace `article` class with the target class.
4. Tune section lengths for the target page budget.
5. Add the PR operating-point figures from the defense hardening run when final figure paths are selected.
6. Fix table widths and figure placement after target-class compile.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
