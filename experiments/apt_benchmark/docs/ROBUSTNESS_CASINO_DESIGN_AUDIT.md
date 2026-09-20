# CasinoLimit adapter and replay design audit

Review date: September 20, 2026. Scope: independent agent review of source code, eleven Casino adapter tests, nine replay tests, and the pinned annotation archives before Casino model fitting. This is not independent human adjudication of labels or a completed audit of every rebuilt event. No adapter edits were made by this reviewer; the adapter owner applied the identified correction. This revision includes the completed-output guard, context-prefilter regression, and deterministic two-worker build orchestration added after the first correction.

## Outcome

**One blocking causal-preprocessing defect was found and corrected before fitting. No other blocking defect was found for the declared offline development task.** The corrected adapter must finish rebuilding its event artifact before a model consumes it. The adapter receipt and pre-fit receipt must identify the corrected source and rebuilt input.

The original first pass collected identity names from an entire host file, including future records, then used that vocabulary to mask earlier features. Although intended to remove identifiers, it violated prefix invariance: appending a later record could alter an earlier representation. The replacement uses fixed syntax and fields on the current fragment only. A regression now checks that adding a future `UID` record leaves the previously retained event unchanged. All **20 tests passed** on the final reviewed files: eleven adapter tests and nine replay tests.

## Findings by concern

| Concern | Reviewed behavior and conclusion |
|---|---|
| Context prefilter | The three-pass adapter retains all target events and earlier events within 120 seconds sharing a full-event process/session key. This is an offline candidate optimization. Replay separately requires a visible target key and a visible prior-fragment key, preventing a hidden linkage field from granting access to context. The broad raw-key scan can retain extra candidates; Replay's second check prevents their use unless qualified. A regression verifies that the filter retains every fragment of relevant context, including a fragment preceding the one containing the join key, and excludes unrelated/same-time context. |
| Targets versus context | Only earliest observed audit events per source annotation and host enter the target roster. Event IDs are deduplicated and overlapping source labels are unioned. Unannotated context remains `unlabeled_unknown` and `target_eligible=false`; it does not become a benign training example. A selected target is retained when perturbations hide every fragment and counts as a miss. |
| Label scope | These are process-technique annotations inherited by selected onset events. They do not independently establish the moment a malicious action begins. The protocol explicitly calls this an annotation-onset proxy. Other labeled techniques are negatives for the specified technique, not verified benign activity. |
| Source-doubt join | Exported annotation IDs must exist in the richer source and their technique strings must agree exactly. Across all 114 source instances, 690 annotations carry source doubt. None belongs to T1068, T1548, or T1105, so removing those doubtful annotations cannot introduce uncertain membership for the three frozen targets. Recheck this conclusion before adding techniques. |
| Timestamp/serial ambiguity | A referenced audit serial appearing at different timestamps fails the join. Event identity includes run, normalized host, serial, and timestamp. Same-time events cannot enter earlier context. Fragment arrival time remains idealized source time; synthetic delay is not a measured collection delay. |
| Identity and feature policy | Process/session keys are join metadata, not classifier text. The correction removes the full-file identity vocabulary. Fixed syntax masks addresses, recognized identity forms, numeric identifiers, technique markers, and known challenge markers. Unknown identity syntax and shared challenge commands may remain; this is not a claim of exhaustive shortcut removal. |
| Cohort expansion | All 114 author-annotated instances are ordered by a fixed hash and split 60/18/18/18. The separate Casino protocol records why the initial 24-instance feasibility cohort was insufficient and states that expansion preceded any Casino model fit/outcome inspection. This is a documented source-support amendment, not untouched confirmation. |
| Completed-output guard | Build refuses an existing event receipt or frozen-stream marker before touching inputs/output. Acquisition refuses a frozen-stream marker before network requests. Successful completion records event, receipt, acquisition, and adapter hashes. The regression verifies refusal preserves an existing output. This guards completed artifacts; interrupted unreceipted builds remain resumable through a fresh build. |
| Parallel build | One or two worker processes execute the same per-run transformation. Each run has a separate staging file; ordered `map` preserves declared run order during concatenation. Each completed part's hash is checked before copying. A two-run fixture produces identical final event bytes with one and two workers. No feature-policy or split changes were introduced by this orchestration. |

## Evidence identifiers

SHA-256 values below identify exactly the reviewed files. Source archive hashes were recomputed locally; publisher checksum checks are recorded separately by acquisition.

| File | SHA-256 |
|---|---|
| `robustness/casino_events.py`, final corrected producer | `e2dc9571bb40543c3c53016064f71f53dacd3e3d51ddf4a6bfb27397b625fe7b` |
| `robustness/replay.py` | `524e71ec99e6fc3488bf8c52ba01b4c1e927c22a9d65418c741a606eac863ecf` |
| `robustness/casino_protocol.json` | `8e3b38e68546cfb233806bb354a807f691401c41c1d1b5c6744d4def28e389ed` |
| `tests/test_robustness_casino_events.py` | `402dda1b3bab718e572d4704f23f8195a213182fcffc40db621a7fa775d39e1f` |
| Private `syslogs_labels.zip` | `2bc9f192109ed0c0be51f92b7c92f813db41cdb561debf0465142a68b1a89cac` |
| Private `output.zip` | `7cb01c030363122faa06acd82ca1c3c189e6305e4ffc536c35a15c49bfe0e2d2` |

The rejected adapter version had SHA-256 `27f213d0a0785c28c8c9fe1b913407e95a5730e1226bcfc01c152ff17b6d1e9c`. Its full-file identity policy must not be the producer of the fitted Casino input.

## Limits and remaining run qualification

- The final event build must report matched annotation/event counts, excluded annotations, target support after deduplication, and input/source hashes. This code audit does not certify an incomplete artifact.
- The exact context-prefilter equivalence was reviewed structurally with the current 120-second, process/session-key Replay contract. A changed horizon or graph traversal requires a new adapter qualification; the existing saved context does not support an arbitrary wider history.
- PID/parent-PID/session matches supply local context; they do not prove a complete causal provenance graph or eliminate process-ID reuse.
- The dataset repeats one challenge. Repeat players may cross instance splits; a player grouping map is unavailable. Rows and perturbation seeds are not independent attack campaigns.
- Waiting the full injected deterministic delay restores the clean view by construction. That recovery is a buffering control, not a learned robustness result.
- These checks establish a qualified development comparison, not operational reliability, benign false-alert performance, an independent gold standard, or method novelty. See [literature and design boundaries](ROBUSTNESS_LITERATURE.md).
