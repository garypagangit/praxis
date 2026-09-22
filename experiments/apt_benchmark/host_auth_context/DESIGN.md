# Does earlier authentication add useful stage information?

September 22, 2026. Development follow-up specified after the host-role/history pilot. The same campaign, partitions and outcomes have already been examined; this is not an untouched confirmation set.

## Literature gate

Generic authentication histories, host roles, temporal context, multimodal fusion and multiple outputs are established ideas. Powell (2022) is especially close and explicitly discusses combining role/process patterns with network-flow information. The [novelty review](NOVELTY_REVIEW.md) permits a bounded empirical test, not a new-algorithm claim. The potential contribution is a controlled account of incremental authentication information under destination-role change, including movement loss and ambiguous review burden. A favorable result would still need independent executions and stronger event-level truth.

## Fixed question and outcomes

Does strictly earlier source-host authentication add exfiltration-stage or movement-stage information beyond identical current-flow, role, prior-flow and logging-availability information? Does retaining a baseline alert while adding a separate exfiltration indication improve coverage at a tolerable, explicitly measured workload?

Keep all 382,229 prepared rows, the earlier fit/calibration versus later test split, three previous fitting seeds and exact 26,767 fitting identities per seed. Test contains 3,442 author exfiltration-stage and 35 author movement-stage rows. Movement labels in this sensor denote Remote System Discovery. The role-shift stratum has 1,101 exfiltration-stage rows toward private services, with no such positive fitting/calibration example. Calibration has zero movement examples. None of these facts is repaired by adding a model.

## Event qualification before fitting

Use only author log-event content to derive event type/outcome and time. Exclude Activity, Stage, Signature, DefenderResponse, account identifiers, process commands and raw content from predictor arrays. Retain file hashes, parsing counts, event deduplication identities, clock evidence, available hosts and observation limits in a separate receipt.

Linux audit event epochs supply UTC time. Windows Security timestamps require independently corroborated UTC offsets from embedded clock-change events; add one second to account conservatively for second-resolution displayed timestamps. No offset may be selected from attack labels or model scores. Missing receipt/clock qualification stops authentication fitting; the predeclared saved-prediction policy comparison can still run with its network-only scope.

The events describe activity observed at the source host, not necessarily successful outgoing authentication to a flow destination. 4648 is an explicit-credential attempt, not proof of success. Unmonitored destinations and unmeasured collection latency prevent confirmed-theft or live early-warning claims. Current-flow statistics are available only after the connection is complete.

## Matched feature arms

### Data-gate amendment before fitting

The parser established Windows export timezone representation, but clock-change events revealed approximately seven-hour backward corrections. Exact incoming endpoint/port matching on the main Windows source supplied zero usable anchors. The actual feature run therefore excludes **all Windows records**, preserves their clock audit evidence, and uses Linux audit records only. All 35 movement-stage test rows have the Linux source 10.1.3.8; all 3,442 exfiltration-stage test rows originate at the excluded Windows source 10.1.3.17. This is a partial authentication ablation and movement-preservation experiment; it cannot answer whether Windows authentication history improves exfiltration recognition. Linux epochs are recorded event time, not an independent certification of synchronization or ingestion latency. The original all-platform hypothesis remains untested.

All seven arms use the prior fixed LightGBM parameters, no hyperparameter search or class weighting, and the same examples:

1. Current flow plus availability.
2. Current flow, roles and prior flow history plus availability.
3. Current flow plus availability and authentication.
4. Current flow, roles and prior flow history plus availability and authentication.
5. Arm 4 with a different host's authentication, preserving the actual source's availability controls.
6. Availability and authentication only, as a shortcut diagnostic.
7. Availability only, as a shortcut diagnostic.

Authentication features are log-transformed counts for each qualified event category in preceding 5 and 30 minutes. Every event must be strictly before the flow start; current and future events are excluded. Availability features describe prior observed records, their counts and recency, observed log family and the existence of an eligible wrong-host donor. These indicators are identical across all seven arms. The controls therefore include observed-log volume and timing, not just coverage; the comparison tests incremental event-type/outcome information beyond that behavior. They do not certify continuous log collection. No absolute timestamp, literal host, target annotation, capture identifier or filename enters fitting.

The wrong-host donor must differ from the source, share its coarse role and log family, and have an observed event strictly before query time. The queried source must also have been observed. A stable hash sets donor preference. It is a correspondence control, not proof that all host/time confounding is removed. Report within-source-host results where target labels exist; the data do not support an unseen movement-source test.

## Identical decision policies for new and prior arms

Replay all six prior network-only probability arms and compare all new arms under exactly the same policies. A saved model's improvement must not be attributed to a new decision rule.

- **Unmodified stage classification:** four-class argmax, macro-F1, each class precision/recall/F1/AP/ROC, normal false alerts, movement any-attack recall, role strata, captures and target-containing source-host strata.
- **Independent target flags:** preserve the original current-flow classifier's movement flag (argmax movement) and add each candidate's exfiltration flag. Both means unresolved, not a correctly resolved stage. Preserve the original baseline attack alert for the union review queue, including other stages. This guarantees retention of existing alerts mechanically; it is not learned detection improvement or a population recall guarantee.
- **Global exfiltration thresholds:** calibration F1 maximum, with the higher threshold on ties, plus all four previously declared non-exfiltration calibration tails (0.1%, 0.5%, 1%, 2%). Report all, rather than selecting a favorable test point.
- **Role-conditioned tail comparison:** use a role-pair tail only when that calibration group contains at least 100 non-exfiltration rows; otherwise fall back to the global tail. Mark stage support insufficient when fewer than 20 exfiltration or 100 non-exfiltration calibration rows exist. An exfiltration flag in an unsupported group goes to unresolved review. Do not suppress its alert or count the review as a correct automatic stage label.

The 100/20 support values are engineering settings fixed before this follow-up run. They are not literature-derived safety standards, uncertainty bounds or pass/fail accuracy criteria. A group with no movement calibration cannot receive a movement-error guarantee even when it satisfies these counts.

## Interpretation and reporting

The primary authentication comparisons are arm 3 versus 1, arm 4 versus 2, and arm 4 versus 5. Keep availability-only diagnostics visible. Publish exact stage errors, raw exfiltration flags, movement flags, both flags, unresolved/unsupported review, automatic exfiltration labels and deduplicated review workload. Include normal and other-stage false labels separately. Counts averaged over three fitting seeds are repeated-fit summaries on the same events, not independent campaigns.

No arbitrary improvement target or guaranteed positive result is imposed. Existing role-shift failures may persist. Apparent gains confined to one host, time segment, role or logging pattern are development findings. No ordinary bootstrap over dependent flows or confidence interval across three fitting seeds will be used to imply campaign generalization.
