# Praxis 06 CI Paper Build

Generated: 2026-05-14

Status: **PASS**

## GitHub Actions Build

| Field | Value |
|---|---|
| Workflow | `Praxis 06 paper build` |
| Run URL | `https://github.com/garypagangit/praxis/actions/runs/25881761738` |
| Event | `push` |
| Branch | `experiment/tta-streaming-apt` |
| Commit | `37a64c53a12dd26c6430a2ddab2bac4cc0bae37f` |
| Conclusion | `success` |
| Started | `2026-05-14T19:46:15Z` |
| Completed | `2026-05-14T19:48:46Z` |

## Artifact Check

The workflow uploaded the `praxis06-tta-paper` artifact.

Local artifact sanity check after download:

| Check | Value |
|---|---:|
| Article PDF path | `tmp/praxis06-tta-paper-ci-25881761738/main.pdf` |
| Article pages | `8` |
| Article size bytes | `677961` |
| Thesis PDF path | `tmp/praxis06-tta-paper-ci-25881761738/thesis_chapter.pdf` |
| Thesis pages | `14` |
| Thesis size bytes | `618638` |

## Decision

The LaTeX toolchain blocker is closed for the expanded thesis-neutral draft. Local Windows still lacks `pdflatex` and `pandoc`, but GitHub Actions can compile the current source and produce a PDF artifact.

Local artifact sanity used `pypdf` to verify the expanded, figure-integrated article PDF opens, has `8` pages, and contains extractable title/abstract text. The thesis-chapter wrapper PDF also opens, has `14` pages, and contains extractable title text. PyMuPDF previously rendered all 8 article pages to `tmp/pdfs/praxis06-tta-paper-ci-25875430166/`; every page had nonblank pixel variance and extractable text. A human visual pass is still recommended before submission.

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
