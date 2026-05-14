# Praxis 06 Submission TODO

Updated: 2026-05-14

## Current Package

| Item | Status |
|---|---|
| Venue-neutral LaTeX skeleton | Done: `main.tex` |
| Local references | Done: `references.bib` |
| Build script | Done: `build.ps1` |
| GitHub Actions compile path | Done: `.github/workflows/praxis06-paper.yml` |
| Local compile | Blocked: `pdflatex`/`latexmk` not installed locally |
| Claim guard | Done: original locked replay remains primary |

## Next Editorial Pass

1. Pick target format: thesis chapter, arXiv, ACM, IEEE, USENIX-style.
2. Replace `article` class with the target class.
3. Expand Related Work into three paragraphs:
   - test-time adaptation,
   - APT/stage detection,
   - safety-gated security ML decisions.
4. Move large defense-hardening details to appendix if venue page limit is tight.
5. Add the PR operating-point figures from the defense hardening run when final figure paths are selected.
6. Compile in a LaTeX-capable environment and fix table widths.

## Must Not Change

- Do not reselect thresholds.
- Do not replace the locked three-seed result with the seven-seed addendum.
- Do not imply DAPT2020 supports TTA generality.
- Do not imply PR-AUC materially improved.
