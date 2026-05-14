# Praxis 06 Venue Conversion Workspace

Generated: 2026-05-13

Status: initial LaTeX submission skeleton.

Pandoc is not installed in this local environment, so this workspace starts from a hand-built LaTeX skeleton rather than an automatic Markdown conversion.

## Source Material

- Main draft: `../../reports/tta_streaming_apt/PRAXIS06_FULL_DRAFT_20260512.md`
- Paper-ready report: `../../reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md`
- Defense addendum: `../../reports/tta_streaming_apt/PRAXIS06_DEFENSE_HARDENING_ADDENDUM_20260513.md`
- Package index: `../../reports/tta_streaming_apt/PRAXIS06_SUBMISSION_PACKAGE_INDEX_20260512.md`
- BibTeX source: `../../reports/tta_streaming_apt/PRAXIS06_REFERENCES_BIBTEX_20260512.bib`

## Files

| File | Purpose |
|---|---|
| `main.tex` | Venue-neutral LaTeX manuscript skeleton. |
| `references.bib` | Local copy of the Praxis 06 BibTeX references. |
| `build.ps1` | Local build helper when `latexmk` or `pdflatex` is installed. |
| `.github/workflows/praxis06-paper.yml` | GitHub Actions PDF build path for environments without local LaTeX. |

## Next Conversion Pass

1. Pick target style: ACM, IEEE, USENIX, arXiv, or thesis chapter.
2. Replace `article` class in `main.tex` with the target class.
3. Convert report prose from the Markdown draft into the section placeholders.
4. Replace compact tables with venue-sized tables or appendices.
5. Compile locally or in cloud once LaTeX tooling is installed.

## Claim Guard

Do not change thresholds, gate policy, or primary result framing during venue conversion. The original locked three-seed replay remains the primary result; the seven-seed run is robustness material.

## CI Build

The GitHub Actions workflow compiled the venue-neutral skeleton successfully on 2026-05-14:

- Run: `https://github.com/garypagangit/praxis/actions/runs/25874826445`
- Artifact: `praxis06-tta-paper`
- Local sanity check after download: 4 pages, 251,618 bytes.
