# Next decision: what information resolves escalation-stage mistakes?

**September 20 update:** The subsequent [missing/delayed-log suite is complete](../results/robustness_v1/SUMMARY.md). It provides positive random-loss results on CasinoLimit, structured-loss failures and no consistent AIT augmentation benefit. The next gate is source-type-aware evidence handling with independent confirmation. [S-DAPT-2026 is registered conditionally](../sdapt2026/README.md), with source/correction and data-access issues documented. The earlier pilot rationale below is retained as development history.


Decision date: September 20, 2026. This is the next development experiment design; no new model comparison has run under it.

Evidence: [targeted source and representation diagnostic](../results/diagnostic_v1/README.md), including aggregate counts, scope limits and input hashes.

Implementation update: the [missing/delayed-log suite](../robustness/README.md) now implements the first semantic/context, loss-training and delay controls. The original decision rationale below is preserved; use the suite's frozen protocols and run reports for executed comparisons.

## Recommendation

First determine whether stronger event representation and past context improve recognition of privilege escalation. Keep logistic regression as the reference, qualify complete events, and compare matched information before spending GPU time on sequence/graph models. Overall binary F1 is already near its ceiling; stage recognition offers a measurable remaining problem.

## What the pilot actually establishes

- Binary detection on the selected AIT test view: logistic F1 99.994%, negative-line FPR 0.505%, escalation detection 70/81 source lines.
- Separate escalation-name classifier: 71 true assignments, 40 incorrect assignments and 10 misses; F1 73.958%.
- Direct error-source inspection found that the 40 incorrect assignments include 23 author-unannotated audit lines and 17 lines labeled with other malicious steps (12 directory-scan lines and five webshell-command lines). They are not 40 verified benign false alerts.
- The 81 positive lines comprise 46 audit, 27 authentication and eight Apache records across only two test runs. The audit records cover 44 event IDs. One multi-record audit event has both missed and correctly classified fragments.
- The current baseline uses only 128 hashed text features, recognized identifier masking and individual lines. A richer input or event reassembly may improve results without a new architecture. That possibility must be tested rather than treating every miss as evidence that a GNN is needed.
- Targeted test-only representation inspection found that all 23 audit false positives share exact normalized text with escalation-positive lines. One missed PROCTITLE line also shares normalized text with four opposite-labeled lines after long hexadecimal command content is masked. At least 24 of the 50 observed stage errors therefore involve opposite source labels on indistinguishable current line inputs. This is not proof that the source labels are correct, that masking caused every difference, or that context will fix all 24.
- Among the 31 audit/auth error rows examined for these collisions, no additional opposite-label collisions were attributable solely to the 128-dimensional hash representation. Widening the hash alone cannot recover information absent from the normalized text. Other source types and global collision rates were not established by that targeted check.
- Same-run raw comparisons for the 23 audit false positives showed differing timestamp/event serial in all pairs, process ID in 18, audit-user ID and session ID in eight each, and systemd unit value in five. The inspected action fields did not differ. Use those IDs only to reconstruct process/session relations and meaningful roles; learning the literal test attacker IDs or event times would create shortcuts.
- The missed masked PROCTITLE example contained command semantics: its safely decoded executable was `modprobe`. Source decoding is data parsing, never command execution. This supports retaining qualified command meaning rather than replacing every long hexadecimal field with a generic token.
- Seven mixed-label normalized patterns among 7,146 test audit/auth rows cover 52 lines (25 escalation-positive, 27 negative for that stage). A deterministic classifier restricted to those unchanged inputs must make at least 13 errors on that observed subset. This finite-sample representation limit is not a population bound or proof that new context will be sufficient.

All examined pilot test cases are now development evidence. Preserve their published results; no future result on the same exposed cases is untouched confirmation. The source labels remain authored rule references, not an AI- or human-adjudicated new gold standard.

## Ordered experiment

| Gate | Comparison | What it answers |
|---|---|---|
| 1. Error and label qualification | Inspect all 50 stage errors, their source labels, shared representations and linked event records | Is the observed weakness missing information, representation collision, stage-boundary ambiguity or a modeling error? |
| 2. Stronger simple inputs | Retain meaningful action/privilege fields and safely decode command text where qualified; use a fixed linear model with a fit-only vocabulary or wider hash as a control | Which lost semantic fields matter? Wider hashing alone cannot separate identical normalized text. Do not restore raw identity strings just to memorize known attackers. |
| 3. Complete events | Reassemble audit records using run, host and original event identity; score only after included records are available | Does restoring one observed event's fields resolve fragmented evidence? |
| 4. Past context | Compare complete-event-only with matched trailing-history counts and an ordered sequence | Does genuinely earlier activity help beyond a stronger representation? |
| 5. Architecture | Linear/boosted history summaries, one small sequence model, and one source-grounded graph model on the same observable history | Does the architecture add value beyond extra information? |
| 6. Incomplete logging | Fixed, declared channel outages/delays; compare buffering, missingness features and ordinary dropout training | Is there a remaining failure that a precise new mechanism can address? |

Choose feature widths, history horizon, thresholds and any candidate mechanism using fit/development/calibration roles. Keep incident/session groups intact, preserve event-time versus availability-time distinctions, and test that future observations cannot change previous predictions. Never append later lines to a complete event and claim the earlier first-line decision time.

Start with privilege escalation and webshell command recognition. Report step precision/recall/F1 and average precision, event-level detection after reassembly, counts per run/episode, author-negative flag burden, runtime and unsupported targets. A source line is not an independent attack episode; any change of prediction unit requires a newly computed baseline and denominator. The old 73.958% line-level F1 must not be used as a directly comparable event-level baseline.

## Data choice

Use AIT for controlled development and its labeled/background views for the relevant negative-label checks. Qualify CasinoLimit next if pursuing Linux technique/stage recognition: its audit-event annotations and repeated executions are closer to this question than network-packet phase labels. It has one challenge and no realistic benign-user baseline, so it can supplement stage recognition but cannot confirm operational false-positive performance. Do not create a shortcut by taking all attacks from one dataset and all normal examples from another.

cAPTure remains useful for a separate network/early-detection track after its causal-feature and reduction checks. It does not directly validate the AIT privilege-escalation target, and its phase scores must not be pooled as the same task.

## Decision rules

- If label ambiguity or lost fields explain the errors, repair and document the task/input contract first. This is necessary engineering, not proof of a novel method.
- If different labels depend only on an unavailable attacker identity or later knowledge, and qualified earlier observations do not distinguish them, declare that target unsupported with these inputs. Do not force a classifier to solve an unobservable distinction or invent earlier evidence.
- If simple, complete-event/history features solve the problem, retain that efficient baseline and identify its next demonstrable limitation.
- If context improves useful step recognition at a comparable negative-label flag budget, proceed to architecture and missing-telemetry comparisons.
- If the proposed mechanism offers no consistent practical advantage over strong controls, record the negative result and close that candidate.
- A positive development gain is insufficient for a final praxis claim: require qualified independent data, adequate execution support and a frozen, attainable confirmation criterion. No numerical improvement target is registered from the two exposed test runs alone.

## Novelty boundary

[TREC, CCS 2024](https://doi.org/10.1145/3658644.3690221) already studies tactic/technique recognition. [StageFinder](https://arxiv.org/abs/2603.07560v2) combines graph and temporal learning for stage estimates; the author record now reports GLOBECOM 2026 acceptance. [IMPROV, PRISM 2026](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf) addresses missing provenance context and event ordering during collection. Consequently, graph-plus-history, stage recognition, and generic missing-log handling are not sufficient novelty claims.

The candidate contribution remains **reliable high-risk step recognition from incomplete observable evidence**, with a precise mechanism to be selected only after the above controls expose an unresolved failure. A classifier substitution or reassembly fix may be useful without being a new research method.
