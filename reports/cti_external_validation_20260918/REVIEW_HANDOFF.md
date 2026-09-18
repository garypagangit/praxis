# Human review: ready-to-use handoff

**Current result: pending; zero completed human reviews.** The automated experiment and independent numerical audit are complete. Human judgments cannot be supplied by an AI or inferred from the benchmark answer key.

## Gary's action

Choose two people with cybersecurity expertise to review the questions independently, and a third qualified person who can resolve disagreements. Give each independent reviewer only:

- [human_review.html](human_review.html), the self-contained offline form; and
- [HUMAN_REVIEW.md](HUMAN_REVIEW.md), the rubric and instructions.

Do not send reviewers the full experiment folder, this outcome report, the identity key, reference answers, or model predictions. The full evidence package contains those materials and is intended for research review after independent judgments are saved.

## Instructions to copy to each reviewer

> Please independently review these 50 security questions and their supplied evidence. Open human_review.html in a browser. Enter your reviewer identifier and review date. For every item, record your answer (or UNCERTAIN), an authoritative supporting citation, whether the supplied evidence applies, whether the question is ambiguous, and any notes. Do not consult model results, benchmark reference answers, or the other reviewer's judgments. Download your completed JSONL response file from the form and return it to Gary. Use your own browser profile or device; the form saves drafts locally. If you are unsure, record uncertainty rather than guessing.

Save the two returned files as `human_review_reviewer_1.jsonl` and `human_review_reviewer_2.jsonl`. Each must contain all 50 matching review IDs. Preserve the original independent files before revealing labels or reconciling disagreements. The form is an offline data-entry aid, not a source of human validation by itself.

## After the reviews arrive

Use the separate identity key to join responses to questions, then record completeness, agreement, ambiguity, and evidence applicability. Give disputed items and both supporting citations to the adjudicator. Preserve the adjudicator's identity, date, decision, and rationale; leave unresolved items explicitly unresolved.

Keep all current released-label results unchanged. Any calculation using adjudicated labels must be reported separately as a sensitivity analysis. The 50-item packet samples five items per source family; it is a quality diagnostic, not a representative estimate of accuracy on all 1,247 questions.

The offline form passed static and simulated-DOM checks. A visual browser review of the form has not been completed; chart figures were separately rendered and inspected.
