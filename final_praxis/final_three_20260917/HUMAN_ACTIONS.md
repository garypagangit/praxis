# Human review and completion guide

**Prepared September 17, 2026. Technical closure is complete; no human approval has been received or inferred.**

## One practical way to finish the human work

1. Open the three papers and the three-slide summary in `deliverables/`. Start with the abstract, results, limitations, and conclusion of each paper. Use each experiment's `EVIDENCE.json` to trace a finding back to its archived observations.
2. Open `REVIEW_FORM.html` in a browser. It works offline. Each reviewer enters their own name, role, date, decisions, and reasons. Save a draft if needed, then export a completed JSON review. The form does not send messages or upload information.
3. The author reviews the methods and underlying evidence and records which claims they can independently explain. The advisor evaluates the contribution, scope, academic eligibility, and next institutional milestone. A committee member can record a separate review. Keep these roles separate.
4. Return each exported JSON file to the project owner. Import it using the command below. The importer validates required fields and preserves the submitted record with a SHA-256 receipt. A self-reported form is a review record, not a digital signature or proof of institutional authorization.
5. Resolve requested revisions against specific evidence IDs. Obtain whatever written advisor/committee approval and institutional submissions the program actually requires. Record their references in a later review. A statistical PASS alone cannot supply that approval.

```text
python code/record_human_review.py --input PATH/TO/review.json --output human_reviews
```

Run from this closure directory. Inspect `human_reviews/INDEX.json` after importing. Never overwrite `HUMAN_REVIEW_RESULTS.json` to manufacture an approval: it is the truthful snapshot at package creation. Later submitted records belong in `human_reviews/` with their receipts.

## Decisions to record

| Experiment | Completed technical conclusion | Specific human decision |
| --- | --- | --- |
| CTI | Source-known gains; query-only mismatch harm; external router confirmation failed. | Is the paired access/compatibility study sufficiently distinct and useful for the primary Praxis scope? Approve a bounded empirical claim, request a specific revision, or decline it. |
| 008 | Qwen harmful acceptance increased under the complete selected-disclosure policy; transfer and hybrid-defense results are unsupported. | Is the measured compound disclosure intervention an adequate secondary or primary scope? Accept its empty-disclosure limitation explicitly. |
| 010 | D0 technically passed; 0/6 variants met the joint mechanism criterion; scale-up is held. | Accept the negative closure or specify a genuinely new research question. Do not relabel this result as a validated defense. |

**Recommended review order:** CTI first, 008 second, 010 as the completed negative study. This is a research-planning recommendation based on this package, not an academic originality certification. All three experiment reports are complete within their observed scope.

## Suggested 45-minute review

- 5 minutes: confirm which degree milestone and submission format apply.
- 10 minutes: CTI claims, access advantage, mismatch harm, and closest prior work.
- 10 minutes: 008 compound disclosure effect, denominator, and unsupported transfer.
- 10 minutes: 010 stopping rule and why movement did not establish average harm.
- 10 minutes: record scope selection, requested changes, responsible people, and dates in the form.

## Ready-to-use message draft

**Subject:** Three completed experiment reports — scope and claim review

I have prepared reports and an evidence package for CTI, 008, and 010, with a three-slide summary. CTI preserves the source-access advantage and failed external router; 008 preserves the compound disclosure effect and failed transfer/defense endpoints; 010 closes a negative mechanism screen under its frozen stopping rule. Please review the bounded claims and prior-work comparisons, indicate which scope is suitable for the next Praxis milestone, and record any required changes and dates using the attached offline review form. The reports disclose AI assistance. Please also confirm the applicable authorship/AI-use requirements and submission format.

**Delivery status:** Draft only. No email, invitation, or external message has been sent. Advisor identity and target review date were not supplied at package creation.

## Academic requirements and provenance

The current GW doctoral policy page links the program's guidelines, Praxis template, and generative-AI policy. The published guidelines describe advisor review and subsequent institutional approval steps; these are human/institutional requirements. These three research papers are evidence-backed review reports, not a claim that three degree submissions have been accepted. The applicable AI-use permission, author verification, and degree-specific format remain to be confirmed by the author and advisor.

- [Official doctoral policies and procedures](https://online.engineering.gwu.edu/policies-procedures-doctoral) — checked September 17, 2026.
- [D.Eng. student guidelines, October 6, 2025](https://online.engineering.gwu.edu/sites/g/files/zaxdzs5816/files/2025-10/deng-student-guidelinesOct6_2025.pdf) — advisor and approval sections checked September 17, 2026.
- [Generative-AI policy linked by the program](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v) — official link verified; the Box document itself could not be freshly retrieved in this closure. Do not infer permission from this report.
- [Praxis template linked by the program](https://gwu.box.com/s/ne153n4y8hdmmr1tgezc1zbuk554sut3) — use for a later institutional manuscript if required.

AI assistance was used to consolidate records, check archived statistics, compare primary sources, draft text, and generate document/slide artifacts. No new model inference was commissioned for the experimental studies during this closure. Human reviewers must verify claims, make their own academic judgments, and record actual decisions. Detailed experiment-specific prompts are in each `HUMAN_REVIEW.md`.
