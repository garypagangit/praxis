# Three-experiment final research package

**CTI · 008 · 010 | September 17, 2026**

The three experiments are closed within their completed scope. This package provides finished experiment papers, traceable evidence, and one three-slide PowerPoint. Author/advisor approval and institutional acceptance remain human decisions; no responses or approvals have been invented.

## Open the deliverables

- [Three-slide PowerPoint — one slide per experiment](deliverables/Praxis_Three_Experiments.pptx)
- [CTI final experiment paper — 9 pages](deliverables/CTI_Final_Experiment_Report.docx)
- [008 final experiment paper — 10 pages](deliverables/008_Final_Experiment_Report.docx)
- [010 final experiment paper — 10 pages](deliverables/010_Final_Experiment_Report.docx)
- [Complete downloadable package](deliverables/Praxis_Three_Final_Package.zip)
- [Human completion guide](HUMAN_ACTIONS.md) and [offline review form](REVIEW_FORM.html)

GitHub previews the HTML source. Download/extract the package and open `REVIEW_FORM.html` in your browser to use the form. It requires no account and sends no data. Word hyperlinks point to this Git branch; Markdown and evidence paths retain their repository-relative structure.

## Final outcomes

| Experiment | Supported finding | Terminal result | Research planning recommendation |
| --- | --- | --- | --- |
| CTI | Source-known relationship evidence improved eligible accuracy by 23.07/19.58 percentage points; query-only mismatch losses were 14.97/17.46 points. | Primary `PASS_SOURCE_KNOWN_ONLY`; external `FAIL_ROUTER_CONFIRMATION`. | Review first as a bounded empirical Praxis scope. |
| 008 | Schema-constrained Qwen accepted 12/101 harmful revisions under selected disclosure versus 4/101 under uniform disclosure. | One reviewer-specific disclosure effect; Devstral transfer and both primary hybrid-defense gates unsupported. | Review as the second bounded empirical scope; preserve the compound intervention limitation. |
| 010 | All 1,024 evaluations completed; 0/6 variants met the joint displacement-and-harm criterion. | Technical audit PASS; `HOLD_CROSS_CHANNEL_HARM_SCALE_UP`; simple-control gate `NOT_REACHED`. | Accept the completed negative screen; no D1 efficacy run warranted by these results. |

The recommendations above are based on the retained experiments and current primary-source comparisons. They do not certify originality or academic eligibility. A negative scientific result is a completed result. Future questions described in the papers are separate research proposals, not missing work needed to close these experiments.

## Evidence and verification

Each experiment folder contains `PAPER.md`, `EVIDENCE.json`, `PRIOR_WORK.md`, `HUMAN_REVIEW.md`, and `slide_summary.json`.

- [CTI evidence map](01_cti/EVIDENCE.json): 29 source files and 93 exact JSON assertions; current count/parser reproduction and independent paired traces.
- [008 evidence map](02_008/EVIDENCE.json): 32 source files and 106 exact JSON assertions; both archived statistical replays and independent recounts.
- [010 evidence map](03_010/EVIDENCE.json): 41 source files and 224 exact JSON assertions; all result variants, original run records, controls, freeze, and shutdown evidence.
- [Package verification](VERIFICATION.json): 102 distinct SHA-256-bound source files, 423 exact claim checks, local links, Word table geometry, and editable PowerPoint data verified.
- [Source index](SOURCE_FILES.json): repository paths, bytes, and hashes.
- [Visual review](VISUAL_QA.json): all 29 paper pages and all three slides checked; formatting corrections retained in the builders.
- [Review importer checks](HUMAN_WORKFLOW_QA.json) and [offline form checks](FORM_BROWSER_QA.json): synthetic tests only, with no actual human decisions recorded.

No new experimental model inference or paid cloud job was commissioned for this closure. CTI's fresh run reused archived bootstrap intervals, while a separately retained historical receipt documents their prior full regeneration. 008's archived bootstrap statistics were regenerated. The 010 paper rechecks retained evidence; it does not claim a new GPU replication. The original protocols and frozen sources were preserved.

## Finish the human decisions

The [current review snapshot](HUMAN_REVIEW_RESULTS.json) records **zero received reviews**. The advisor identity and review date were not supplied. The guide includes a ready-to-use message draft and a 45-minute review agenda. No message has been sent.

1. Author: verify understanding and evidence; identify applicable authorship/AI-use requirements.
2. Advisor: decide which bounded contribution fits the next Praxis milestone and record specific revisions, owner, and date.
3. Reviewer: complete the offline form, export JSON, and return it to the project owner.
4. Project owner: validate/import the record using `code/record_human_review.py`. Follow the program's actual approval process and retain written references.

These are finished experiment research reports for academic review. They do not purport to be three institutionally accepted degree manuscripts. AI assistance is disclosed in every paper. Program policy links and unresolved applicability are documented in `HUMAN_ACTIONS.md`.

## Reproduce or inspect

From this closure directory, using Python 3.10 or newer:

```text
python code/verify_package.py
python code/record_human_review.py --input reviewer_export.json --output human_reviews
```

Use a **new** output directory for experimental reanalysis. The paper-specific reproducibility sections identify the frozen commands and numerical dependencies. Recreating inference requires the original model/provider access and is a separate replication exercise.

`code/build_documents.py` uses python-docx. `code/build_slides.mjs` uses `@oai/artifact-tool` and takes the absolute closure directory as its first argument; run it in an artifact-tool workspace. Generated visual QA intermediates are excluded from the release. The Windows document-rendering adapter fixes a local profile-URI issue without changing the bundled renderer or experimental code.

## Bundle scope and rights

The ZIP preserves repository paths and includes this closure, all directly cited source files, the CTI paper reproduction package, the 008 code-study package and license notices, and the 010 execution package and relevant protocols. Start at the root `START_HERE.md`. Model weights, private provider request stores, and private operational configuration are excluded. Where a full reproduction requires a separately pinned upstream source, follow its original README and license terms. File hashes establish identity; they do not substitute for those terms.

Base evidence commit: `c447ec8a70be65bd39f7cebfe6b34f9e3025c2d9`. Publication branch: `Final-Praxis-Three-Closure-20260917` in [garypagangit/praxis](https://github.com/garypagangit/praxis/tree/Final-Praxis-Three-Closure-20260917/final_praxis/final_three_20260917).
