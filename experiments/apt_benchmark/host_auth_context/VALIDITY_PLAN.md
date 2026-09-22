# Validity plan: authentication context with visible movement costs

**Design review, September 22, 2026. No new model results or protocol registration are claimed here.**

## 1. The question this follow-up can answer

Does strictly earlier, correctly linked authentication activity add useful information about the author's exfiltration-stage flows beyond current flow measurements, coarse roles, traffic history, and the mere availability of host logs? Can the system expose that evidence without suppressing an existing movement alert?

These are two separate questions. Additional context must earn its benefit in a matched comparison. Keeping an existing movement flag while adding a second output preserves that flag by construction; this is a transparent decision-policy property, not newly learned movement detection or a novel algorithm.

The source remains one previously inspected UNRAVELED campaign. Its movement labels on this sensor describe Remote System Discovery on one directed host pair. Its exfiltration-stage labels need not mean that the particular flow successfully carried stolen data. The experiment is a developmental stage-annotation study, not independent confirmation of successful lateral action, theft, attacker identity, or early warning.

## 2. What the completed experiment actually established

The completed [host-history report](../results/host_history_exfil_v1/REPORT.md), [independent audit](../results/host_history_exfil_v1/AUDIT.json), and [frozen design](../host_history_exfil/DESIGN.md) are the basis for this follow-up. Source and protocol were frozen at `b6e9e8d` for that earlier run; that freeze does not register this new design.

| Observation on the same later flows | Current flow | Current + roles + history | Meaning |
|---|---:|---:|---|
| Exfiltration average precision | 0.6363 | 0.8823 | Context improved ranking. |
| Exfiltration F1 under four-class argmax | 0.7561 | 0.7641 | Decision improvement was much smaller than ranking improvement. |
| Movement any-attack recall | 69.52% | 40.95% | Context suppressed many movement-stage alerts. This cost cannot disappear into macro-F1. |
| Exfiltration F1 after calibration-F1 threshold selection | 0.7653 | 0.7632 | The selected operating point did not convert ranking gain into an F1 gain. |
| Exfiltration recall at the nominal 1% non-exfil calibration tail | 67.56% | 90.46% | Higher recall came with more later false exfiltration flags: means 1,148.33 versus 1,774.00. The nominal calibration percentage is not the test error rate. |

These are means of three fitting seeds on shared observations, not independent campaign estimates. The later department-to-private-services stratum contains 35 movement and 1,101 exfiltration rows; all four-class argmax methods detected zero of those exfiltration rows as exfiltration. There are zero exfiltration training examples in that role pair. Calibration has neither target label in that stratum and **zero movement examples anywhere**. No source-calibration procedure can establish movement recall protection in the missing stratum.

## 3. Authentication qualification comes before joining

The pinned author [data README](https://gitlab.com/asu22/unraveled/-/blob/d2ea90055d82fa448ab20588a13e3ec8bfd74816/data/README.md) and [repository README](https://gitlab.com/asu22/unraveled/-/blob/d2ea90055d82fa448ab20588a13e3ec8bfd74816/README.md) describe host audit/authentication logs, Windows security events, heterogeneous logging, and some collection failures. Their existence does not establish the timestamps, row semantics, coverage or alignment of any newly acquired file. Use the separate source-qualification agent's byte-level findings before making such claims.

Required receipts for an included source:

1. Source hash, host mapping from author inventory or a documented field, schema and record count. Never infer a host from whichever mapping gives the best attack score.
2. Event-time field, time unit and zone/offset provenance. Distinguish a Windows event timestamp from a collector timestamp or a CSV export timestamp. Preserve source values.
3. Parsed, duplicate, malformed and excluded row counts; the actual acquisition interval and gaps. An empty window does not establish that no authentication happened.
4. Stage labels, attacker labels, response fields and annotation-derived features excluded from predictors. Count genuinely observed authentication outcomes rather than the author's attack-stage annotations.
5. Separate success, failure and unknown outcome. A logon event is not necessarily remote movement; an authentication failure is not proof of compromise.
6. A source and destination join rule fixed from inventory/record semantics, including missing and ambiguous hosts. Literal IPs, usernames, victim identities, campaign schedules and filenames are not primary predictors.

**Unresolved clocks:** do not search time offsets against the known test attacks, pick an offset that maximizes joins, or assume the analyst's local timezone. If authoritative metadata resolves Linux but not Windows times, a Linux-only context arm is permissible with its restricted coverage and matched controls disclosed. If no relevant clock is qualified, execute the network-only comparison in Section 7 and leave authentication fusion explicitly unexecuted.

If independent metadata provides a bounded event-time interval `[a,b]`, an optional conservative join may use only events with `b < current_flow_start`; membership in a full historical window additionally requires `a >= current_flow_start - window`. Both tests must hold for every permitted offset. Freeze this treatment before scoring, report the excluded fraction, and expect wide clock uncertainty to leave no eligible events. A guessed finite interval is not a clock qualification.

## 4. Availability and host-identity shortcuts

Sparse logging can identify a known host without meaningful behavioral evidence. An `auth_log_present` flag is therefore a potential shortcut, not an adequate explanation for an improvement.

Use the same observable coverage indicators in all arms of the authentication comparison. Separate **sensor enrollment/qualified observability** from **having prior authentication events**. The former requires a documented inventory or collection state; the latter is itself behavior. Do not derive a purportedly historical coverage flag from the presence of events later in the full file.

Keep these controls:

- **Availability control:** network features plus the exact coverage indicators used by the auth model, without auth behavior counts.
- **Availability-only diagnostic:** coverage indicators alone. Report it even if weak. A strong score would expose host/sensor confounding.
- **Wrong-host authentication control:** preserve the queried host's true coverage indicators but use a different eligible host's strictly earlier state, chosen without labels. Match logging type and coarse role where possible; unmatched cases stay explicitly missing. A Linux-to-Windows donor change would test schema availability as well as host linkage.
- **Stratified results:** each role pair, logging-availability pattern and acquisition period with real target support. A result visible only on one instrumented victim host is a within-environment association.

The wrong-host donor inventory must itself be observable by query time, or come from an independently documented deployment inventory fixed before the evaluated period. Never use a future observed-host roster. Missing donors must be counted; no silent fallback to the correct host. Swapping identifier names consistently in both queries and events does not scramble linkage.

A donor must have comparable qualified observability at the queried time. An unavailable donor replaced by zeros is a missing-context control, not a clean test of incorrect host linkage. Keep those cases in the overall evaluation, report the donor-qualified subgroup separately, and do not attribute the full A-versus-W difference to correct linkage if availability differs. A versus the matched network-plus-coverage baseline remains the primary added-information comparison.

## 5. Minimal matched model comparison when auth is qualified

Reuse the exact previous fit/calibration/test identities, seed roster, fitting caps, current features, role map, causal network histories and fixed LightGBM settings. All arms share the same fitted examples within a seed. Do not compare a newly tuned auth model with an untuned baseline. No model selection on the exposed test period, no relabeling and no class-dependent subsampling of held-out rows.

| Arm | Inputs and purpose |
|---|---|
| B0 | Existing current-flow model, retained as the frozen movement reference and contextual historical comparator. |
| B1 | Existing current + roles + traffic-history model, retained as the prior context comparator. |
| B2 | Current flow + qualified coverage indicators; controls for the coverage shortcut before adding roles/history. |
| B3 | Current + roles + traffic history + the same qualified coverage indicators; primary auth baseline. |
| A | B3 + earlier correctly linked authentication counts; primary candidate. |
| W | B3 + earlier wrong-host authentication counts under the matched donor rule; linkage diagnostic. |
| D | Coverage indicators alone; shortcut diagnostic. |

B0/B1 predictions can be reused only when input, support, model and prediction hashes match the completed source. The other five arms require at most fifteen new fixed fits across the original three seeds. A simpler implementation may omit B2 only if the narrower primary claim is explicitly auth beyond B3. It must retain B3, W and an availability diagnostic.

Minimal auth features are counts over the already used 5/30-minute windows, separately for the source and destination host: qualified successful, failed and unknown authentication events; distinct observed counterpart count where reliably supplied; remote-versus-local categories only where the source field directly supports them; and time since last eligible event with an explicit never-observed indicator. Cap/transform counts with a fixed label-free formula such as `log1p`, and represent missing coverage separately from a valid zero.

Events must be available strictly before the current flow starts, with equal-time events excluded. Continue label-free state chronologically through the held-out period; do not erase legitimate preceding history at each row or compute it only on the fitting sample. No labels, prior true stages, future totals, or auth activity within the current flow enter these features. Current-flow statistics still require the flow to finish; this is not an early detector.

Primary informative contrasts are **A versus B3**, **A versus W**, and their behavior inside the changed role pair. B3 versus B1 diagnoses any contribution from newly supplied coverage. B0 versus A alone cannot identify which added component helped.

## 6. Two outputs with explicit accounting

Let `m_B0(x) = 1[argmax(p_B0(x)) == LateralMovement]`, using the previously fitted current-flow model. Keep this movement flag unchanged for every candidate and control. The general classifier's other outputs can also remain available; do not silently discard its other-attack alerts.

For each candidate or comparator `j`, emit a separate exfiltration flag `e_j(x) = 1[p_j(Exfiltration|x) > t_j]`. Select `t_j` by the same previously specified calibration-only rule for every arm. The two flags may both be true. Do not resolve overlap by forcing the class with the larger score, because that would recreate suppression. Flag overlap is not proof that both activities occurred: the source supplies one stage label per flow.

Evaluate three representations separately:

1. **Original four-class predictions** from each model: exact-stage recall/F1, confusion and macro-F1. These expose whether auth/context changes movement recognition in the learned classifier.
2. **Independent movement and exfiltration flags:** true/false flags for each stage, joint/overlapping flags, unflagged true target cases, and exfiltration false flags specifically on movement rows.
3. **Deduplicated alert routing:** the union of the frozen general classifier's any-attack flag and the exfiltration flag. Count a row once in the queue, publish new benign and other-stage referrals, and distinguish attack detection from correct-stage identification.

Movement-flag retention versus B0 is exactly a policy invariant, so its zero loss is not empirical evidence of a better movement model. The nontrivial question is whether the additional exfiltration flag improves useful detections relative to the same policy using B3, W or B0 scores, at a fully reported false-alert and overlap cost. A dual-output rule should never be rewarded for retaining B0 alerts when the comparator was artificially restricted to one mutually exclusive label.

## 7. Bounded execution if Windows/auth timing remains unresolved

An immediately runnable comparison needs **no new fits**: use the audited calibration/test predictions of the six existing network arms, plus the frozen B0 movement/general flags, and compute the two-output and queue accounting above.

Use the existing calibration-F1 rule as the primary operational comparison and retain all four already declared non-exfiltration calibration-tail points (0.1%, 0.5%, 1%, 2%) as secondary sensitivity. Do not switch the primary endpoint to the 1% point because its old test recall looked favorable. Report all seeds and points, with strict `>` handling and the original higher-threshold rule for F1 ties. Hash-bind every prediction source and reproduce original thresholds before adding policy counts.

This is an explicitly **post-pilot developmental decision-policy analysis**, not a preregistered confirmation and not an authentication experiment. It can tell us whether useful exfiltration evidence can be surfaced without overwriting existing movement flags and what extra false alerts it causes. It cannot establish that authentication helps, that clocks are aligned, that behavior generalizes to a new campaign, or that retaining an existing flag is a new scientific method.

## 8. Metrics, calibration limits and stopping interpretation

The reporting unit is the held-out source flow; the dependence unit is the shared host pair/capture within one campaign. Three fitting seeds and thousands of similar flows do not become independent attacks. Publish integer confusion counts for each seed and capture before averages. Use directional paired differences descriptively, without campaign-population confidence intervals from seeds.

Publish:

- Exfiltration AP and prevalence, precision/recall/F1, true flags, benign false flags, other-stage false flags and movement falsely flagged as exfiltration.
- Movement exact-stage precision/recall/F1, any-attack recall, retained B0 flags, newly detected cases and newly missed cases. A movement-class F1 gain can coexist with worse movement recall.
- Unique queue count/fraction, benign queue count/FPR, queue precision against any-attack labels, incremental queue rows and duplicated flag count. These are flow-review proxies, not measured human time.
- Counts and metrics inside department-to-private-services; calibration support explicitly zero for both target labels there. Exfil-versus-movement AP must include its high exfil prevalence reference (1,101/1,136 in the prior test stratum).
- Performance by auth coverage and by later capture, with missing-support values marked unavailable rather than fabricated perfect scores.

A source-calibration tail bounds only the observed source fraction under its strict ranking rule. It supplies neither a guarantee under temporal/role shift nor control of the unobserved movement false-exfil rate. Maximizing calibration F1 is not probability calibration. Scores from a four-class model and fixed argmax movement flags should not be advertised as calibrated movement risks.

No invented 90% success threshold is needed. Before new outcomes, freeze the comparisons and complete the selected roster. Report mixed outcomes as mixed: extra exfiltration detections plus extra false alerts; preserved output plus unproven new movement detection; global ranking gains plus stratum failures. If the auth source has no qualified relevant events, call the multimodal arm unsupported/unexecuted, not an unsuccessful model or proof that auth information cannot help.

## 9. Novelty and the next credible confirmation

Adding authentication features, combining telemetry, preserving multiple output flags and comparing fixed-threshold tradeoffs are established methodological ideas. This review makes **no first-method novelty claim**. The separate current primary-literature review must determine whether a narrower applied contribution remains.

A defensible potential contribution is an explicitly tested account of when auth context adds transferable information beyond host/log availability, and when a context-enhanced score harms stage-specific decisions under role shift. That contribution still needs stronger data: independently verified remote-action and marked-data-transfer outcomes, benign administration/backup activity, known clock/collection availability, and independent execution or environment holdouts. Vary role/host assignments independently of attack type. Retain movement and exfiltration support in calibration and in independent evaluation; never solve the current zero-support issue by borrowing the already exposed test labels.

Before claiming completion of a new run, bind raw log bytes, parse exclusions, timestamp provenance, join identities, feature matrices, fitting supports, frozen source/protocol, saved calibration/test scores and complete metrics. The independent auditor should recompute joins at every rare movement anchor and a fixed distributed sample, verify no future/equal-time events, test coverage-only and wrong-host semantics, and recompute all thresholds and dual-output counts without refitting.
