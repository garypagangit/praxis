# Escalation errors: inspect the representation before adding model complexity

**September 20, 2026 — post-hoc exploratory diagnostic.** No new fitting, classifier inference, threshold changes or label changes were performed. [Aggregate evidence](ESCALATION_DIAGNOSTIC.json) contains source/artifact hashes and no raw log lines or record IDs.

## What the errors actually represent

The separate escalation-label classifier produced **71 TP, 40 FP and 10 FN** on 81 author-labeled positive lines.

| Error | Source breakdown | Author-label interpretation |
|---|---|---|
| 40 false positives | 23 audit lines; 17 Apache access lines | The 23 audit lines are unannotated under the author's closed-world rule. Of the Apache lines, 12 are labeled `dirb` and five `webshell_cmd`: these are other malicious-step labels, not 17 benign alerts. |
| 10 false negatives | Seven audit lines; two Apache access lines; one authentication line | Nine occur in wilson and one in harrison. No missed input was truncated. |

The 81 positives are correlated observations from **two runs**: eight Apache, 27 authentication and 46 audit lines. The 46 audit lines represent **44 audit event keys**, not 46 attacks. One three-line audit event has one correctly detected fragment and two missed fragments (`SYSCALL` and `PROCTITLE`). Five other missed audit events have no detected positive fragment in this analysis. Cross-channel records can describe the same underlying action; 44 event keys do not establish 44 independent attacks.

## A concrete information loss was found

**All 23 audit false positives have exactly the same normalized text as an escalation-positive line.** This is stronger than a 128-dimensional hash collision. Each was matched to a positive line from the same run. The raw differences were audit timestamp/serial (23 pairs), PID (18), audit-user ID `auid` (eight), session ID `ses` (eight), and systemd unit value (five). The checked action fields—such as event type, executable, operation and result—were unchanged. Host and ordinary `uid` fields did not differ in these pairs. None of the pairs differed only in clock/serial.

One missed `PROCTITLE` line also becomes identical to four opposite-labeled lines after masking. Its 35 encoded bytes contain a command beginning with `modprobe`; replacing that encoded command with `LONG_HEX` removes actual command semantics. This does not establish whether the action is malicious: its purpose and context remain separate questions.

Across **all 7,146 test audit/authentication lines**, seven error-associated normalized patterns contain 25 positives and 27 negatives. Any deterministic classifier using only this unchanged normalized line must make **at least 13 errors among those 52 lines**, the sum of the minority-label count in each identical-input group. This is a finite representation limit, not a population guarantee. It does **not** mean all 24 currently affected errors are unavoidable; a different decision can trade false positives for false negatives.

Among the **31 audit/authentication error rows checked**, there were no additional opposite-label matches caused solely by the 128-dimensional hash representation. This does not clear all hashing collisions: the Apache population and training-data collision rates were not exhaustively examined. The diagnostic is test-only. Numeric masking can also remove meaningful numeric fields by design, but this analysis does not assign the remaining errors to that cause.

## Recommended next gate

1. **Check the source-label rules and event scope.** Determine how the author's labels distinguish the same visible action in different sessions. Preserve uncertainty; do not replace labels with an assistant's judgment.
2. **Repair and compare the information representation.** Decode supported command encodings, preserve typed action/privilege semantics, and keep stable identifiers for event/entity linkage rather than treating arbitrary ID numbers as predictive features. Include a stronger sparse line-feature control to measure the effect of the small hash space.
3. **Reassemble audit events before testing longer history.** Compare all arms on the same event target and event-availability time; changing from line-level to event-level labels changes the task and must be explicit. Then test whether a bounded history of the same process/session distinguishes the otherwise identical actions.

A wider hash vector alone cannot distinguish identical normalized text. A larger neural model on those same inputs cannot recover information that was removed. The next experiment should therefore compare semantic line features, complete events and bounded prior context with a simple classifier before investing in TCNs, Transformers or GNNs. These controls are not a novelty claim. The exposed test runs are now development evidence; a subsequent confirmatory claim requires a separately frozen evaluation.
