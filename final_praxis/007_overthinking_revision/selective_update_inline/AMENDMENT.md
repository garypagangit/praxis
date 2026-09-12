# 007 prospective inline-terminal formatting amendment

Dated 12 September 2026. Stage the parser and this amendment before any fresh test request. The original stage-two calibration run, its preregistration, raw responses and strict scores remain immutable. This is a response-format amendment informed by exposed calibration outputs, not a new positive experimental result.

The parent reports many otherwise complete calibration responses ending with a unique inline marker, such as ?One sentence. FINAL: TRUE?, with provider end_turn and well below the token ceiling. The original parser requires the marker at start-of-text or after a newline. This review did not independently recompute the full paid calibration cohort; the new lineage-aware runner must do that offline.

## Exact change

Accept exactly one terminal marker FINAL: TRUE or FINAL: FALSE when preceded by start-of-text or whitespace. Previously only start-of-text/newline was accepted. Preserve exact uppercase syntax, the single space after the colon, TRUE/FALSE vocabulary, and the requirement that only whitespace follows the marker or its allowed wrapper. Python regex whitespace semantics are explicit, including spaces, tabs, line breaks and nonbreaking spaces; zero-width space does not qualify.

Preserve the previous formatting whitelist: bold, one or two backticks, and the previously accepted bold/backtick combinations. They must be balanced around the complete terminal marker. Preserve one whole-JSON-string decode, without recursively decoding strings or extracting JSON object fields. No explanatory text is interpreted as an answer. Multiple marker-like occurrences, internal markers, malformed wrappers, nonterminal punctuation or suffix text, different label syntax, and truncated responses remain invalid.

The function parse_inline_terminal(text, truncated=...) has no gold, question, peer condition or correctness input. rescore_inline_terminal(text, original_score) retains the old answer, usage and finish reason, uses the unchanged original truncation decision, and adds the amended answer and formatting trace. The wrapper makes no calls and does not mutate the supplied original score.

## Freeze and lineage required before test

1. Require original stage-two COMPLETED status and complete calibration for both models under the original parser and technical gate. Record both original model gates and audit original test exposure separately for each model. The planned fresh-primary path requires zero original test cells for that model. If any original test cell exists, skip all new primary test requests for that model; any later analysis of those existing tests must be separately labeled retrospective. Do not change original code or results while the run finishes.
2. Copy/import all completed original calibration cells as immutable source material. For each cell retain source path or S3 key/version, raw cell SHA256, original run/preregistration hashes, original request ID and provider response, original score, and amended score. Recompute the old score using the frozen old scorer and verify it matches the saved score before applying the new parser.
3. Import the same 64 calibration IDs for each model, with exactly 22 cells per question (1 initial plus 3 evidence conditions times 7 checks). Full calibration is 1,408 cells/model. Do not replace questions, regenerate invalid answers, omit difficult items, choose arms by results, or tune gate thresholds.
4. Recalculate the identical technical gate offline: all planned cells present; at least 61 of 64 valid initial labels; at least 8 correct and 8 validly wrong initial labels; and at least 95 percent valid labels across all 1,408 calibration responses (at least 1,338). Report original and amended validity and gates side by side, plus counts of each formatting normalization. This reused calibration analysis is post hoc and cannot establish efficacy.
5. Commit a separately dated protocol, parser, tests and lineage-aware runner before inference. Freeze its hashes and the unchanged 128 test IDs. Only each model passing its amended technical gate AND having zero original test exposure may receive fresh test requests. Do not query or adapt on test outcomes while preparing the amendment. Failed models retain their imported calibration audit and receive no test calls.
6. Use a new output/run namespace and new preregistration-bound IDs for fresh test inference. Imported calibration receipts retain their original request identity; do not fabricate new request hashes or relabel old provider receipts as requests under the amended protocol. The adapter should never be invoked to reuse calibration, because its original-preregistration cache guard must remain intact.

The initial prompt, review prompts, temperatures, token ceilings, reference/mismatched donor mapping, policies, investment thresholds, denominators and bootstrap procedure do not change. Evidence and gold handling remain as previously frozen. The formatting relaxation applies symmetrically to all models, checks and splits, including initial answers.

## Validation delivered

inline_parser.py and test_inline_parser.py are staged beside this memo. All 15 offline unit tests pass. They cover legacy newline/start compatibility, accepted inline whitespace and wrappers, exact syntax, malformed/multiple/internal markers, preserved truncation, nonrecursive JSON normalization, no implicit extraction, and unmodified original scores.

These tests use artificial strings to verify parser behavior; they are not new benchmark observations and make no model calls. The parent must attach the full raw-response calibration reanalysis receipt and the unchanged test-fixture hash before launch. No paid evaluation or AWS mutation was performed for this amendment.

