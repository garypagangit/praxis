# Three completed Praxis manuscripts and evidence packages

Gary Pagan · September 14, 2026

Each manuscript begins with an executive summary in simple language, followed by the research questions, literature, methods, completed results, limitations, and references. These are complete AI-assisted empirical research drafts for internal research development. Failed interventions remain in the results.

**Academic-use clarification added September 14, 2026:** The current [GW doctoral policy page](https://online.engineering.gwu.edu/policies-procedures-doctoral) links an [AI policy](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v) that prohibits AI-generated drafting, revising and editing in submitted Praxis work, while permitting source identification and coding under its stated conditions. No applicable written exception has been verified. These drafts are not ready for academic submission, and human editing alone does not establish compliance. This notice preserves the authorship provenance and changes none of the frozen papers or experimental evidence. The CTI manuscript is also shorter than a full GW Praxis. The [CTI internal development handoff](https://github.com/garypagangit/praxis/tree/Final-Praxis-CTI-Development-20260914/final_praxis/cti_development_20260914) provides an evidence map, source records, code checks and independent-author preparation questions.

## Read the papers

| Priority | Paper and simple explanation | Completed finding | Documents and evidence |
|---|---|---|---|
| **1. CTI — PX003/PX034, with PX068 external evaluation** | **When Retrieved Cyber-Threat Evidence Helps and When It Hurts.** Tests whether supplying cybersecurity reference facts improves an AI's answers. | Large improvements on compatible ATT&CK questions in two models; substantial losses on mismatched questions. The external router failed. Strongest current practical cybersecurity paper, with a bounded contribution. | [Read paper](01_cti/PAPER.md) · [PDF](01_cti/PAPER.pdf) · [Word](01_cti/PAPER.docx) · [Evidence and reproduction](01_cti/README.md) |
| **2. Final008** | **Selective Disclosure of Executed Tests in Language-Model Code Revision.** Tests whether carefully selected truthful test results can persuade a reviewer to accept a bad code change. | Selected disclosure raised harmful acceptance from 4/101 to 12/101 in the tested Qwen configuration. The proposed hybrid defense did not qualify, and the effect was not established in the second reviewer or generated-error cohort. | [Read paper](02_008/PAPER.md) · [PDF](02_008/PAPER.pdf) · [Word](02_008/PAPER.docx) · [Evidence and reproduction](02_008/README.md) |
| **3. PX055** | **Precision Invariance of Refusal-Style Geometry Under Quantization.** Tests whether a measured internal pattern survives lower numerical precision. | All nine model/precision cells completed; the geometric stability and transfer rules passed. The projection proxy failed. This is a measurement paper; it does not demonstrate preservation or restoration of semantic safety. | [Read paper](03_px055/PAPER.md) · [PDF](03_px055/PAPER.pdf) · [Word](03_px055/PAPER.docx) · [Evidence and reproduction](03_px055/README.md) |

The ordering reflects the current combination of practical relevance, complete evidence, and a claim that can be defended without overstating the results. A committee that requires a successful novel algorithm, rather than an empirical contribution and a tested process modification, may require additional work. None of these papers invents its underlying statistical mathematics.

## What the evidence packages allow a reader to verify

**CTI:** Four compressed original result files contain 40,000 inference records, representing 35,000 distinct model/question/condition cells and 5,000 repeated vanilla cells. The package includes frozen analysis and construction code, protocols, source hashes, and 23,976 derived external-policy rows. Original CTIBench responses can be reparsed. External AthenaBench raw questions, sealed answers, and responses are not republished; that extension supports statistical replay from derived observations. The [complete local replay](01_cti/evidence/reproduced_full/REPRODUCTION_RECEIPT.json) reproduced all statistical outputs and all 156 bootstrap intervals, using 20,000 resamples per interval.

**008:** A manifest identifies 121 canonical study/evidence files in this branch. Both original and schema-extension statistical packages were replayed locally, reproducing all reported statistical fields exactly, including their 5,000-draw bootstrap analyses. The public package supports this statistical reproduction. The complete raw provider and privileged execution archive still requires the owner's archived evidence access. The disclosed secondary floating-point erratum is preserved.

**PX055:** The package retains the nine original geometric arrays, per-prompt outcome flags, source identifiers, frozen analysis inputs, and an offline reproduction script. Reanalysis reproduces 4,161 scientific fields, with seven synthetic controls. Decoded behavioral completions were not retained, so the lexical flags cannot be independently relabeled for semantic refusal. The prompt manifest can be checked against the public XSTest source.

Each folder contains its own provenance, verification, and visual-review records. Figures, table values, frozen outcomes, and the boundaries of reproduction remain linked to their source artifacts. Statistical replay does not create new participants, questions, model runs, or independent scientific replications.

## New research requested alongside the papers

- [SOUP, Colibri, model compression, and small-hardware research opportunities](research_opportunities/LITERATURE_COMPRESSION.md): exact projects, training versus inference, RAM versus VRAM, benchmark limitations, and candidate research designs.
- [Google TimesFM and new cybersecurity opportunities](research_opportunities/LITERATURE_TIME_SERIES_CYBER.md): recent primary literature, public data, proposed hypotheses, process modifications, baseline comparisons, and stopping rules.

The new ideas are research proposals. No new model inference or AWS experiment jobs were launched to prepare this release. The immediate recommendation is to develop CTI as the primary existing Praxis, retain 008 as the strongest decision-manipulation alternative, and qualify a small-hardware systems idea or the persistent-attack forecasting idea before committing to a new full campaign.

## Release and document production

Publication branch: `Final-Praxis-Top-Three-Papers-20260914` in [garypagangit/praxis](https://github.com/garypagangit/praxis).

The [document builder](build_documents.py) creates Word documents with editable mathematics and renders PDFs through LibreOffice. Build manifests identify source and output hashes; visual QA records refer to the actual rendered documents. The Markdown papers are the easiest version to read directly on GitHub. Local machine paths inside build receipts are production provenance, not required evidence locations. Follow the relative paths in each evidence guide to reproduce the statistics.

Run `python verify_release.py` from this directory to check the document hashes, recorded visual reviews, chapter completeness, reader-facing local links, and GitHub file-size limits. The latest result is [RELEASE_VERIFICATION.json](RELEASE_VERIFICATION.json). This automated review complements each package's statistical reproduction; it does not certify scientific novelty or substitute for committee review.

The primary source licenses and redistribution limits are documented in each package. This release does not override the licenses of benchmark data, model weights, or third-party code.
