# Praxis 008 manuscript and portfolio recommendation

The complete research manuscript is **Selective Disclosure of Executed Tests in Language-Model Code Revision**, by Gary Pagan. It is an empirical Praxis draft based on completed evidence release `48f0fa6147be86a69cb266338cefae989fa6999e`. It includes five chapters, references, a reproducibility appendix, six tables and two figures. The Word equations are editable.

- [Word manuscript](PRAXIS_008_PAPER.docx)
- [Rendered PDF](PRAXIS_008_PAPER.pdf)
- [Markdown source](PRAXIS_008_PAPER.md)
- [Top three across the historical portfolio](TOP_THREE_PRAXIS_RECOMMENDATION.md)
- [Full text and evidence review](FINAL_MANUSCRIPT_REVIEW.json)
- [Build manifest](BUILD_MANIFEST.json) and [final document QA](DOCUMENT_QA.json)

The supported finding is the Qwen native-cohort selective-disclosure contrast, including omission. The hybrid defense failed its registered recommendation, Devstral did not establish the same disclosure effect, and the smaller generated-harm cohort showed no disclosure contrast. Those findings remain explicit throughout the paper. The manuscript does not claim institutional approval, external peer review or a successful new defense.

The wider portfolio comparison ranks CTI first for completed empirical breadth, 008 second as the completed code-revision study, and PX-055 as a conditional mechanistic alternative. This comparison covers historical PX programs in addition to Final-Praxis-001-008; these numbering systems are distinct. The included portfolio reviews preserve local artifact locations for older work. They are evidence inspections, not fresh replays of every historical experiment.

## Build the document

Use Python with `python-docx`, `matplotlib`, `pillow`, `pymupdf`, `latex2mathml` and `lxml`. PDF conversion uses LibreOffice. Editable mathematics use Microsoft's installed `MML2OMML.XSL`; the stylesheet is not redistributed. Override the two installation paths on another machine as necessary.

```powershell
python build_paper.py --output-dir C:/work/output/doc/praxis008 --work-dir C:/work/tmp/docs/praxis008 --soffice "C:/Program Files/LibreOffice/program/soffice.exe" --math-xsl "C:/Program Files/Microsoft Office/root/Office16/MML2OMML.XSL"
```

The builder creates the study diagram, Word document, PDF, page images and a manifest whose visual-review status starts as pending. A new build needs its own layout review. It does not execute experimental code, contact cloud services or call a model. Document byte hashes can differ between builds because of document timestamps and local rendering software. Scientific statistical reproduction is a separate process documented in Appendix A and the parent evidence package.

The final review receipts bind the delivered manuscript and rendered files by SHA-256. All pages were reviewed after rendering; text review and layout review are separate checks. Frozen original and extension sources and completed experimental results were preserved.
