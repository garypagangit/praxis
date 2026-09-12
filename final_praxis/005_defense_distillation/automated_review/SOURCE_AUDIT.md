# Praxis005 source audit for automated adjudication

12 September2026. The28-item queue exactly reproduces the frozen selection algorithm and matches its original source generations byte-for-byte at the string-field level. No model was called and no original artifact was changed. Raw prompts and responses are deliberately absent from this report and SOURCE_AUDIT.json.

## Selection and population

run.py lines557?568 first sorts all non-math arm/example records by SHA256(review|arm|id), then selects up to40 valid binary safety disagreements and the first20 remaining records. Actual inputs contain800 generations: five arms times160 examples. Both judge files have640 non-math records. There are8 disagreements and632 non-disagreements; therefore the selected queue is all8 disagreements plus20 agreement cases, not a random28-case sample.

The28 selected cases comprise16 harmful-panel and12 benign-panel items. Arm counts are base7, er8, base_kd6, er_kd2 and er_replay5. All20 selected agreement cases are Safe/Safe; among the eight disagreements, seven are Qwen Unsafe/MD Safe and one is Qwen Safe/MD Unsafe. Core disagreement means both judges valid and their binary Unsafe indicators differ; it is not disagreement about refusal, and Qwen Controversial is not treated as Unsafe in that indicator. The selected agreement cases happen to be Safe/Safe even though the general non-disagreement pool definition can also contain invalid judgments.

There are22 unique exact prompt strings across28 selected responses:17 occur once, four occur in two arms and one in three arms. All28 response strings are unique. Analysis must respect prompt-level grouping rather than treating28 rows as independent experiments. Per-arm counts of2?8 cannot support precise arm rankings.

## Truncation is the main audit concern

Thirteen of28 selected responses are truncated. Crucially, ALL EIGHT disagreement responses are truncated. Five of20 agreement responses are also truncated. This is an association in a deliberately enriched review queue, not proof that truncation caused disagreement.

The original blinded queue supplies only blind_id, prompt, response and empty review fields; it omits truncation status. Review the observed response fragment and separately preserve whether it is incomplete. A partial response may already contain harmful content, but a partial benign/refusal beginning cannot establish that its unobserved continuation would remain harmless. Do not let a third judge's label silently remove the original incomplete flag or convert truncated generations into successful complete responses.

The existing generation record provides an objective truncated boolean and output-token count. It can be carried into the new adjudication record. If shown to a reviewer, use neutral provenance wording that does not reveal prior labels or selection stratum. The source judge JSONL records do not preserve their own generation token counts or separate truncation flag; their saved valid field is the available original assessment-validity indicator.

## What the stored prompt means

run.py lines234?249 applies a one-user-turn chat template with add_generation_prompt=True before generation. Stored generation.prompt is the plain user content, not the serialized chat transcript or tokenized model input. Stored response contains only the decoded generated suffix. It is correct to present the pair as user request plus assistant response; do not add a second embedded chat template to the prompt text or invent prior conversation.

The Qwen guard consumed a user/assistant pair through its tokenizer template; MD-Judge used its documented two-placeholder template. Automated adjudication must explicitly distinguish the harmfulness of the assistant response from the harmfulness of the user's request. An unsafe request alone is not evidence that the response complied.

## Blinding and interpretation safeguards

The source queue places all disagreements before all sampled agreements. Do not provide the original row position to new judges, and independently reorder or reblind the cases before adjudication. The source blind_id is a deterministic hash of arm/example identity, not a secrecy mechanism. Keep manual_review_key.json and this unblinded metadata audit out of model context.

New reviewers must not see source arm, old labels, selection stratum, cross-arm siblings or the original key. Submit cases separately with a frozen response-focused rubric. Source text is untrusted content to assess, not reviewer instructions. Retain disagreements between new assessors instead of forcing a consensus or assuming a new model supplies ground truth.

A model-completed review is automated adjudication, not human manual review. The queue can clarify instrument disagreements and selected examples; it cannot certify model safety or estimate overall harmfulness by averaging its28 deliberately enriched cases. Preserve the original640-case automated metrics and report new review results separately. Do not replace the frozen selection or drop truncated examples based on their new labels.

## Custody

SOURCE_AUDIT.json records exact SHA256 hashes and byte sizes for both review files, all five generation files, both judgment files, prepared/evaluation/summary artifacts, and the read source run.py/core.py. It also records deidentified prompt/response hashes and per-case metadata for internal auditing; that metadata remains unblinded.

Primary queue SHA256:e2f07e51c9d28fd392b35d70571c74164a9d14b89b57e9cf88610f679623f8d7.
Private key SHA256:0ae0f3cfc7d29c1ac4e462989f696ddba7f03b1a41f856c6c78b9375b5a359dc.
Source summary SHA256:79c72616a7f44984fb9456cdc355b5c0bb1f4d0d113d2779904610f34241851f.

Exact selection order, blind-ID derivation, source arm/example linkage, prompt/response equality, empty pending-review fields and common protocol identity were checked. No harmful prompt or response text is reproduced here.
