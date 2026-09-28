# Committee review corrections — September 28, 2026

This corrected review edition contains a 155-page paper. Experimental results are unchanged.

1. **Trailing page numbers:** removed cached PAGE-field values from DOCX footer parts, the source of the orphan sequence in some extraction tools. Live page fields remain; PDF page numbering is populated. A body-only accessible text copy is supplied.
2. **Equations:** all 25 equation images render in the PDF. Each now also has visible, searchable linear notation in Word and PDF, including the softmax, loss, gates, gains, greedy rule and Ridge objective.
3. **Literature date:** Section 2.1 distinguishes the September 23 initial review from the September 28 AIT supplement.
4. **Lists:** expanded acronyms and symbols, including every requested addition and their contextual meanings.
5. **Review status:** removed the two placeholder phrases and identified this as a committee review edition. Formal submission still requires confirmed director/committee names, examination date and institution-approved certification wording. These facts have not been supplied or invented.
6. **AIT figure:** Figure 4-9 accompanies Table 4-17 with six execution-by-seed paired deltas for macro-F1 and exfiltration warning recall, directly derived from saved results. Units and the lack of primary-direction replication are explicit; seeds are not independent campaigns.

## Verification and contents

All 43 changed pages were visually inspected; 112 remaining page bodies matched the previously reviewed PDF pixel-for-pixel. Structural checks verified 25 searchable equations, the end of Appendix E.5, cleared footer caches, PDF page numbering and absence of text outside page boundaries. Live PAGE-field recalculation was separately verified through LibreOffice.

The complete 37-slide PowerPoint, slide PDF and speaker notes are included unchanged from the integrated September 28 edition. This correction updates the paper.

Full data, models and audit evidence remain available in the [original evidence release](https://github.com/garypagangit/praxis/releases/tag/praxis-integrated-20260928). The evidence index supplies asset links and hashes.

## Building

Run integration/integrate_paper.py for the integrated baseline, then integration/correct_committee.py and integration/check_committee.py for these corrections. Recorded workstation paths and dependencies must be adapted on another machine. Visual review is a manual final gate. Do not replace the delivered PDF with an unrefreshed DOCX conversion: page fields must be recalculated by the rendering application.
