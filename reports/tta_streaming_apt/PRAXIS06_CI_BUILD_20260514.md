# Praxis 06 CI Paper Build

Generated: 2026-05-14

Status: **PASS**

## GitHub Actions Build

| Field | Value |
|---|---|
| Workflow | `Praxis 06 paper build` |
| Run URL | `https://github.com/garypagangit/praxis/actions/runs/25875430166` |
| Event | `push` |
| Branch | `experiment/tta-streaming-apt` |
| Commit | `ecfb6e025445336bbab11eb8bbb38255c0dbc5ba` |
| Conclusion | `success` |
| Started | `2026-05-14T17:38:23Z` |
| Completed | `2026-05-14T17:40:05Z` |

## Artifact Check

The workflow uploaded the `praxis06-tta-paper` artifact.

Local artifact sanity check after download:

| Check | Value |
|---|---:|
| PDF path | `tmp/praxis06-tta-paper-ci-25875430166/main.pdf` |
| Pages | `8` |
| Size bytes | `677961` |

## Decision

The LaTeX toolchain blocker is closed for the expanded thesis-neutral draft. Local Windows still lacks `pdflatex` and `pandoc`, but GitHub Actions can compile the current source and produce a PDF artifact.

Local artifact sanity used `pypdf` to verify the expanded, figure-integrated PDF opens, has `8` pages, and contains extractable title/abstract text. PyMuPDF then rendered all 8 pages to `tmp/pdfs/praxis06-tta-paper-ci-25875430166/`; every page had nonblank pixel variance and extractable text. A human visual pass is still recommended before submission.

| Render check | Result |
|---|---:|
| Rendered pages | `8` |
| PNG dimensions | `918 x 1188` |
| Minimum page text chars | `966` |
| Minimum grayscale stddev | `26.68` |
| Render output dir | `tmp/pdfs/praxis06-tta-paper-ci-25875430166/` |

The next paper task is editorial, not infrastructure:

1. Pick target style: thesis chapter, arXiv, ACM, IEEE, or USENIX-style.
2. Convert from thesis-neutral `article` style into the selected class.
3. Add final PR operating-point figures if they fit the target page budget.
4. Re-run the CI build after each venue-format pass.
