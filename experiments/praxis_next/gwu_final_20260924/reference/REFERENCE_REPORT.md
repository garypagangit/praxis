# GWU reference document and GMR inspection

**Result: the exact original praxis and its GMR image were found.** The original was read without modification. The current official 2026 online-program praxis template was also downloaded successfully for comparison.

## Source files

| Artifact | Exact location | Identity |
|---|---|---|
| User's original praxis | `C:/Users/garyp/Downloads/Gary Pagan GWU DEng GML to Detect APT Final 04012026 AIRv02.docx` | 4,240,040 bytes; SHA-256 `5873d64833e648da6226e56258e043e2cc3dae0f22afca2da478b6e0dac3807c` |
| Exact extracted original GMR | `C:/w/gwu_reference_qa_20260924/original_gmr.png` | 2176 x 1022 pixels; SHA-256 `5d055b17fd9ff91041a9a12aa6d909931e250f7d838e3cc8084b6cb84a128f50` |
| Current official praxis template | `C:/w/gwu_reference_qa_20260924/DEng_Praxis_Template_Online_Programs_Rev_2026.docx` | 72,609 bytes; SHA-256 `0c22a6ba142187a3b763f32045bf86a59a4e747dbb32b6335c53a3e3033c2547` |

The historical repository report `reports/gwu_committee_response/GML_COMMITTEE_PROGRESS_RESPONSE_20260518.md` supplied the exact original source path. Other earlier GWU drafts exist under Downloads and OneDrive/Documents, but the April 1 source named in that report is the inspected reference. No unrelated personal documents were opened.

[REFERENCE_SPEC.json](REFERENCE_SPEC.json) records the original's sections, style inheritance, complete heading topology and embedded-media hashes. [inspect_reference.py](inspect_reference.py) reproduces the structural inspection and extracts the exact GMR to the QA directory. The original hash matched before and after inspection.

## Front matter and author information

The original title is **Advanced Persistent Threat Event Detection Using Graph Machine Learning**, by **Gary Pagan**. Its cover gives these degrees:

- B.S. in Applied Math and Statistics, May 1999, Stony Brook University.
- M.S. in Engineering Management, May 2006, George Washington University.

The submission block names the Faculty of the School of Engineering and Applied Science of The George Washington University and the degree Doctor of Engineering. The historical director line names Jonathan Ng, Professorial Lecturer in Engineering and Applied Science. Historical committee entries also name Jeffrey Yu and Amir Etemadi. This inspection establishes what the old document says; it does not verify current appointments or committee approval of the new study.

Front matter appears in this order:

1. Title page.
2. Certification/committee page.
3. Copyright page.
4. Dedication.
5. Acknowledgements.
6. Abstract of Praxis, including the praxis title.
7. Table of Contents.
8. List of Figures.
9. List of Tables.
10. List of Symbols.
11. List of Acronyms.

**The old certification is not evidence of approval.** It asserts a passed final examination and approved final form dated April 1, 2025, while the cover is dated April 1, 2026. Do not copy this sentence, historical examination date, or an approval assertion into the new paper. Dedication and acknowledgements are personal optional pages; their presence in an old document does not establish contributions to the new study.

The official 2026 template uses the same praxis submission block, five-chapter structure and front-matter convention. Its sample dates and John H. Doe entries are placeholders. It explicitly instructs committee listings to omit honorifics such as Dr. or Ph.D.; the original's Dr. prefixes should therefore not be carried forward.

## Chapter topology to retain

| Chapter | Original organization | Suitable role in the completed measurement praxis |
|---|---|---|
| 1. Introduction | Background; Research Motivation; Problem Statement; Thesis Statement; Research Objectives; Research Questions and Hypotheses; Scope of Research; Research Limitations; Praxis Organization | Retain these nine functions, using the current measured question and disclosed exploratory analysis status. |
| 2. Literature Review | Introduction; relevant threat/detection work; model foundations; evaluation; summary | Organize around recent temporal evaluation, warning loss, history/evidence selection and source qualification; distinguish close prior work from the narrow contribution. |
| 3. Methodology | Introduction and GMR; dataset; EDA; preprocessing; models; tuning; evaluation | Introduce the new current-study GMR, then document actual source semantics, fitting/evaluation controls, paired outcomes, qualification and reproducibility. Do not imply new graph training or tuning. |
| 4. Results | Dataset and EDA results; processing; engineering; tuning; research questions/hypotheses | Report completed controlled results, warning destinations, sensitivity and dataset support audit, with the stated empirical limits. |
| 5. Discussion and Conclusions | Discussion; Conclusions; Contributions to Body of Knowledge; Recommendations for Future Research | Retain these four named functions and make the applied measurement contribution explicit. |

References follow Chapter 5, then appendices. Original appendices A-C concern DAPT feature ranges, Optuna importance and graph architecture taxonomy; these are historical contents, not required contents of the new paper.

## Observed typography and layout

The original has 755 top-level paragraphs, 20 tables, 27 inline images and three Word sections. Every section uses US Letter portrait pages, 1.25-inch left/right margins, 1-inch top/bottom margins, and 0.5-inch header/footer distances. The usable body width is 6 inches.

The Normal style explicitly sets Times New Roman, 12 points, double line spacing and zero space after. Many body paragraphs use a 0.5-inch first-line indent; the GMR introduction uses 0.4 inches. Chapter titles are centered and bold. Lower-level headings are bold and use hierarchical numbering. Figure captions use a centered Caption style; line spacing inherited from Normal should be deliberately reset in the new document rather than copied blindly.

The original source declares Roman numbering in its first section and Arabic starts later, but its inspected section XML has no header/footer references. A read-only LibreOffice conversion produced 114 pages. Selected pages 1, 2, 16 and 34 were inspected at full resolution: centered cover, double-spaced text and heading hierarchy were visible; no page numbers appeared on those inspected pages. This is a reference-layout review, not a review of all 114 scientific pages.

### Current GWU formatting cross-check

The [official GWU formatting requirements](https://gradpostdoc.gwu.edu/gw-etd-formatting), checked September 24, 2026, specify Times New Roman 12-point body text, double spacing, the same portrait margins, no running headers, and centered footer page numbers. Front matter uses lowercase Roman numbers; the title page counts as i without displaying its number. Chapter 1 begins Arabic page 1, continuing through appendices. Captions and reference entries use single spacing; chapters begin on new pages. The new manuscript should implement these requirements explicitly and verify its rendered numbering, captions and table/figure fit. This reference report does not certify institutional acceptance.

## Exact GMR meaning, location and artwork

**GMR means Graphical Model of Research.** This is explicit in the original acronym list at paragraph 223 and the Chapter 3 introduction at paragraph 352. It is not the Goal/Method/Rationale abbreviation found in some later project notes.

The image occurs at top-level paragraph 353, relationship `rId12`, DOCX media member `/word/media/image5.png`. The nearby intended caption is **Figure 3-1. Overview graphical model of research**. The original Word drawing extent is about 6.653 x 3.125 inches, which exceeds its 6-inch text width.

The image has six numbered cards arranged in three columns and two rows. Header bars use teal shades for the first four steps, gold for tuning, and green for evaluation. Each card answers **What? Why? How?** The exact original titles are:

1. Data Collection & EDA.
2. Preprocessing & Feature Engineering.
3. Graph Construction from Flow Data.
4. Train Five GML Architectures.
5. Hyperparameter Tuning (Optuna).
6. Model Evaluation & Comparison.

The image contains topic-specific historical claims about AWS S3 acquisition, binary labels, graph construction, five graph models, Optuna trials, weighted F1, interpretability and the Soh comparison. It cannot describe the current measurement study unchanged. In particular, its assertion that stratification prevents leakage is not a general methodological guarantee.

### Correct reuse

- Keep the exact image only as an explicitly labeled **historical reference** in an appendix, with the full-resolution PNG available as supporting artwork.
- Use the original six-card What/Why/How convention for a **new** Chapter 3 GMR whose text describes the completed study.
- Keep the new figure concise enough to read at final print size. Consider landscape placement for the dense historical figure; simply shrinking it into a 6-inch portrait frame makes its text very small.
- Use stable chapter-specific figure numbers. The original Word STYLEREF/SEQ fields rendered incorrectly in LibreOffice as a caption beginning with the entire Chapter 3 heading, followed by an incorrect figure number. The new document must not inherit those broken field results.

## Official 2026 template acquisition

The [GWU-hosted Box share](https://gwu.box.com/s/ne153n4y8hdmmr1tgezc1zbuk554sut3) identifies **DEng Praxis Template - Online Programs Rev 2026.docx**, file ID `2281870631072`. The ordinary public [download endpoint](https://gwu.app.box.com/index.php?rm=box_download_shared_file&shared_name=ne153n4y8hdmmr1tgezc1zbuk554sut3&file_id=f_2281870631072) returned HTTP 200 and a valid DOCX of 72,609 bytes. No sign-in or authentication bypass was used. Its two sections have the same 1.25/1-inch margins; it provides the same five chapters and Chapter 1/5 subsection functions described above.

The current template, original image and selected rendered reference pages remain in the local QA directory. This repository folder contains inspection reports and code, not a copy of the user's original document. No models or AWS computation were used.
