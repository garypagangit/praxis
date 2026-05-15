# Praxis 06 CI Paper Build

Generated: 2026-05-15

Status: **PASS**

## GitHub Actions Build

| Field | Value |
|---|---|
| Workflow | `Praxis 06 paper build` |
| Run URL | `https://github.com/garypagangit/praxis/actions/runs/25944754838` |
| Event | `push` |
| Branch | `experiment/tta-streaming-apt` |
| Commit | `8e8e979620152d802a68af9e483b4ded962bfa94` |
| Conclusion | `success` |
| Started | `2026-05-15T22:38:27Z` |
| Completed | `2026-05-15T22:40:30Z` |

## Artifact Check

The workflow uploaded the `praxis06-tta-paper` artifact.

| Check | Value |
|---|---:|
| Article PDF path | `tmp/pdfs/praxis06-ci-25944754838/praxis06-tta-paper/main.pdf` |
| Article pages | `9` |
| Article size bytes | `678947` |
| Thesis PDF path | `tmp/pdfs/praxis06-ci-25944754838/praxis06-tta-paper/thesis_chapter.pdf` |
| Thesis pages | `14` |
| Thesis size bytes | `619968` |

## Render Sanity

Local Windows still lacks `pdflatex`, so CI remains the compile path. The downloaded PDFs open with `pypdf`, extract text, and render with PyMuPDF.

| Render check | Article | Thesis chapter |
|---|---:|---:|
| Pages rendered | `9` | `14` |
| Minimum page text chars | `791` | `151` |
| Minimum grayscale stddev | `12.66` | `8.95` |
| Contact sheet | `tmp/pdfs/praxis06-ci-25944754838/main_contact_sheet.png` | `tmp/pdfs/praxis06-ci-25944754838/thesis_chapter_contact_sheet.png` |

## Decision

The 2026-05-15 thesis editorial pass compiles. The article grew from 8 to 9 pages because the introduction now includes explicit contributions and the provenance boundary was updated to match the expanded OpTC result. The thesis chapter remains 14 pages.

Next paper task: review the full-resolution CI PDFs for table placement and figure placement, then decide whether to keep the expanded article form or compress it for venue style.
