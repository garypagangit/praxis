# Independent CTI question and evidence review

**Status: ready for two independent cybersecurity reviewers; zero human reviews completed.** The packet and blank response form are prepared. No human validation result is claimed. A third qualified reviewer will adjudicate disagreements.

## Purpose

Check whether the released answer labels are defensible and whether the retrieved MITRE facts actually help answer each question. A correct fact can still concern the wrong condition, system, or question.

This is a 50-item quality audit. It samples five questions from each of the ten coarse source families. It is not a representative accuracy estimate for all 1,247 questions.

## Files to give the reviewer

- [human_review_packet.jsonl](human_review_packet.jsonl): 50 questions, displayed choices, and retrieved evidence. Each line is one review item.
- [human_review_template.jsonl](human_review_template.jsonl): 50 matching blank response records. Give each reviewer a separate copy and save their responses as `human_review_reviewer_1.jsonl` and `human_review_reviewer_2.jsonl`.

Keep `human_review_identity_key.jsonl`, `sealed_labels.jsonl`, and model/checker results away from both reviewers until both independent sets of judgments are saved. Reviewers must not see each other's responses before completing their own. The separate identity key links review IDs to dataset IDs and source families. This separation prevents the published answer, model decisions, and another reviewer's judgment from steering the review.

## Reviewer instructions

Use your cybersecurity knowledge and authoritative sources. First read the question and all four choices; then assess the supplied evidence. Record your own judgment before consulting the released benchmark answer or any model result.

Complete these fields for every reviewed item:

| Field | What to record |
|---|---|
| `review_id` | Keep the supplied identifier unchanged. |
| `reviewer` | Your name or an agreed reviewer identifier. |
| `date` | Review date as `YYYY-MM-DD`. |
| `answer` | `A`, `B`, `C`, `D`, or `UNCERTAIN`. Use `UNCERTAIN` if the question has no defensible single answer. |
| `citation` | Authoritative URL plus the specific section, technique, version, or passage supporting your judgment. |
| `applicability` | `DIRECT_SUPPORT`, `PARTIAL_SUPPORT`, `IRRELEVANT_OR_MISMATCHED`, `CONTRADICTORY`, or `UNCERTAIN`. |
| `ambiguity` | `CLEAR_SINGLE_ANSWER`, `MULTIPLE_PLAUSIBLE_ANSWERS`, `NO_CORRECT_OPTION`, `VERSION_DEPENDENT`, or `UNCERTAIN`. |
| `notes` | Explain missing conditions, conflicting facts, misleading choices, or any uncertainty. |

For applicability, ask: does this evidence support the requested conclusion, including the relevant system, version, and conditions? A shared security term alone is insufficient. `PARTIAL_SUPPORT` means useful details are present but an important part of the question remains unresolved. `CONTRADICTORY` means the evidence contains a material conflict affecting the answer; do not use it merely because a passage is irrelevant.

Record uncertainty rather than inventing an answer or citation. If a question depends on an older software or framework version, name the version explicitly. SecEval was originally described in 2023; this experiment deliberately retains the frozen ATT&CK 19.1 retrieval corpus. Source-version differences may explain disagreements.

## How results will be documented

1. Save both reviewers' independent responses, identities, dates, and citations before revealing the released answers, model outputs, or the other reviewer's responses. Completion requires both reviewers to assess all 50 items; an explicit `UNCERTAIN` judgment is a recorded review, not an invented answer.
2. Join responses using the separate identity key. Count completed and unresolved items, inter-reviewer agreement, agreement with released answers, ambiguity, and evidence applicability. Report counts by source family as descriptive results.
3. Preserve disagreements and their citations. A third qualified reviewer adjudicates disputed items; record all original judgments, the adjudicator's identity/date, and the final rationale. Preserve unresolved disagreements when the evidence does not support a single conclusion.
4. Keep the frozen experiment's original published-label results. Any later adjudicated-label analysis must be a separate, clearly labeled sensitivity analysis.

Until real responses arrive, the recorded result remains **pending**. A generated explanation, an automated checker score, or this preparation work does not substitute for an actual human review.

## Reproducible selection

Within each source family, rank dataset IDs by `SHA256('20260918|' + ID)` and select the five lowest values. Interleave the 50 selected items by the same hash, then replace dataset IDs with `CTI-H001` through `CTI-H050`. Selection does not use released answers or any generated outcomes. `build_human_review.py` reproduces the packet; `HUMAN_REVIEW_STATUS.json` records its hashes and pending status.
