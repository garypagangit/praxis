# Independent source review of PX-080 and PX-081 inference

Reviewed September 23, 2026. Read-only review of run code, protocols, tests, reporting, the PX-081 audit, and the upstream observable-identity construction. No frozen experiment file was changed. No blocking direct target-label leakage was found in the inspected inference paths.

## PX-080

- The supervised difference in expert error uses true labels only on forward-held-out fitting captures. At final evaluation, gate inputs contain expert probabilities, probability summaries/differences, relative history age, and a channel-present flag. Test labels enter metrics and retrospective harm/help counts, not gate decisions.
- Both experts have current-flow features and static roles. The context expert has acquired history. The selector consequently does not avoid collecting history: it decides whether to use information already supplied to the experts. Collection-cost or log-volume savings are not demonstrated by this experiment.
- The stale condition queries completed history five minutes before the current start; its age is relative to the current start. Wrong-host history remains prior-only. Neither condition reproduces a measured outage or establishes a new independent workflow.
- The availability flag denotes a functioning history channel, not the existence of a prior event. A naturally empty history can therefore have channel-present equal to one. This is consistent with the source protocol, but should not be described as complete event coverage.
- Costs 1/1/4/4 are prespecified priorities. With capped class sampling and uncalibrated model scores, the learned quantity is a development estimate under that fitting distribution, not a calibrated deployment risk or a no-harm guarantee.

## PX-081

- Selector training labels use forward-held-out predictions. At inference each state's acquisition regressors receive current features, only the optional groups already delivered in that state, and that state's predicted probabilities. The selector input does not contain the next group's hidden values or next-state probabilities.
- The replay precomputes all subset predictions for efficiency, but indexing chooses only the currently delivered state. This is a legitimate offline replay construction, not evidence that all groups were available to the policy. The state-based source paths inspected do not expose an unacquired group.
- Schedule draws use seed, channel, and a hash of observable event fields. The upstream hash excludes target labels, capture IDs, and local row numbers. Simulated availability is consulted only after selecting and charging a query. Every policy sees the same row-specific schedule, and both failed and late queries consume budget.
- The success priors are known synthetic configuration, not empirically learned field reliability. The entropy control is a learned greedy proxy, not SEFA/L2M/Sim-CTKG reproduced from author code. Static role/history retrieval does not test evolution of feature values over time.

### Simulation interpretation needing explicit wording

`mean_elapsed` accumulates the simulated full response/failure delays, including requests that finish after the decision deadline. It can exceed the 1.0-unit deadline. Late evidence is correctly excluded from predictions, but this statistic is **not bounded decision latency** and must not be reported as a measured live response-time improvement. It describes simulated elapsed query delay. The unrestricted full-context reference assigns zero elapsed time by construction and is not comparable as a live latency baseline.

Budget comparisons share maximum allowed spend, not necessarily identical realized mean spend or identical delivered information. Report the saved realized spend, query rate, and detection tradeoffs. A reduction in simulated requests is not measured infrastructure savings; static roles in particular could be cheaply cached.

## Shared data limits verified

Prepared fitting captures 0–4 contain movement counts 9, 4, 5, 0, and 9: **27 fitting movement rows**, of which **18 occur in the four selector-validation captures**. The only selector-validation capture containing exfiltration labels is capture 4 (1,299 rows). Thus stage-sensitive selector supervision is concentrated in very few temporal settings. Seeds and simulated conditions do not increase the number of independent attack executions.

Neither model establishes successful movement/theft, pre-exfiltration prediction, external campaign generalization, or algorithm novelty. Final probability/metric audits remain necessary; this source review is additional evidence rather than a replacement for those audits.
