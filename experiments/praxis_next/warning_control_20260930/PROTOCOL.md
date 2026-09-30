# PX-085--091: warning-control exploration

Frozen development protocol, 2026-09-30. User authorized numbering in Git and parallel AWS processing. Implement PX-085--087 first; register the remaining ideas with explicit prerequisites. No guaranteed positive finding or confirmed novelty is asserted.

## Corrections to the supplied plan

1. CRC controls expected bounded monotone loss under exchangeability, not every realized test-set miss rate. Correlated flows and chronological change do not establish exchangeability. The original CRC paper already includes false-negative-rate examples: https://arxiv.org/html/2208.02814v4 . We apply established theory and test empirical behavior; no new theorem is claimed.
2. Mean probabilities do not retain every seed's warning. Counterexample: attack probabilities .51, .01, .01 average below .5. Warning union retains warnings by construction but can increase false alerts. Neither implies a useful workload tradeoff.
3. Cheapest-first is not generally budget-optimal, even for monotone additive gains. With budget 2, a cost-1 item yielding .1 can block a cost-2 item yielding 1. Report observed Pareto comparisons; do not assert the proposed lemma.
4. Stage-conditional risk requires calibration support for each true stage. Current calibration contains zero movement rows. Supported-stage results explicitly exclude movement from any hypothetical calibration claim. The all-stage fallback warns on everything when a stage lacks support.
5. Selective CRC requires its actual selection and calibration construction, not two arbitrary tuned thresholds. It does not automatically impose a hard future analyst-capacity limit. See https://arxiv.org/html/2512.12844v1 . A hard capacity limit and requested risk may be jointly infeasible.
6. Feature monotonicity is a constraint along particular model inputs, not a guarantee against attack-to-benign errors. Binary attack probabilities require separate treatment from multiclass scores.
7. Prior work includes conformal IDS: https://arxiv.org/abs/2609.19241 . The supplied blanket statements that novelty is confirmed are not accepted. Other supplied citations and exact closest-work differences remain to be verified before a standalone novelty claim.

## Data and exposure

Use frozen PX-081 models and probabilities, seeds 8101/8102/8103, original calibration split and original later test rows. Original dataset hash and evaluation event identities must match. Recreate calibration probabilities without fitting; compare replay with the original implementation and saved test paths. This entire campaign and calibration outcomes have been examined previously. Results are exploratory development, not prospective confirmation. Captures are correlated segments of one campaign; seeds are not independent campaigns.

Classes: benign, other_attack, movement, exfiltration. Conditions: clean, delayed_unavailable, wrong_host_history. Evidence states: current only, roles, history, both. Costs: roles 1, history 2; deadline 1; nominal delays .25/.75. Inherited delivery schedules and selector scores remain unchanged. No test label enters a selector, threshold choice, stopping decision or ensemble rule.

## PX-085: calibrating missed-warning risk

For each fixed policy and seed/condition/budget, compute attack score 1-P(benign). On calibration attack rows set k=floor(alpha*(n+1)), threshold equal to the kth smallest score. If k<1 or n=0 use zero (warn all). Warn on equality. This conservative rank rule implements the binary-loss CRC correction. Under exchangeability the probability of a new attack falling strictly below this threshold is at most k/(n+1). Preserving pre-existing argmax warnings can only reduce misses.

Alpha grid .01,.02,.05,.10. Report pooled-attack, minimum threshold over supported stages, and all-stage fail-closed thresholds. No family-wise high-probability or drift guarantee is claimed. Thresholds are specific to the fixed model and policy; no test-based best-arm selection. Report every alpha and arm, stage support, exact-stage recall, missed-warning rate, benign FPR, warnings per 100k, simulated evidence cost and per-capture results. Exceeding alpha on these chronological test rows is an empirical stress result, not a contradiction of CRC's theorem.

## PX-086: recoverability and seed ensembles

Partition the harm policy's missed warnings into: at least one budget/deadline-reachable fitted expert warns, or no reachable fitted expert warns. Exhaustively enumerate the two evidence orders. The oracle sees hypothetical outcomes, so this is diagnostic only. 'Unrecoverable' is limited to this fitted expert set and budget.

Compare arithmetic probability mean and warning union across the three seeds at each fixed evidence state. Evaluate on identical rows; include all single-seed comparators. Union assigns stage from mean attack scores where the mean would be benign. Each ensemble uses three model evaluations per row; evidence cost is shared only for the same state. Under delayed delivery fixed-state ensembles are unrestricted references, not budget-feasible policies. Do not combine different seed-dependent acquisition paths and call the result free. Apply PX-085 separately to each mean ensemble using its own calibration scores. Additional 5--10-seed refits are deferred until this pilot supplies evidence of value.

## PX-087: fixed acquisition and early stopping

Compare none, roles_first, history_first, entropy, harm, plus roles_first stopped when currently observed attack probability reaches .5 or .9. These stopping values are fixed before replay and are not claimed to guarantee retention. On all policies evaluate budgets 1,2,3. Apply PX-085 to the final probability of each fixed stopping policy, not intermediate calibration tuned with test labels. Compare cost, stage warning recall and benign alerts jointly; higher warning recall alone is not dominance.

## Registered follow-ons

- PX-088: selective risk control with analyst capacity. Requires verified SCRC implementation, disjoint selection/risk calibration, stage support and infeasibility handling; deferral is not assumed to mean successful human detection.
- PX-089: chronological recalibration. Requires qualified ordering, enough attack support per calibration window, realistic label delay and policy for missing labels. Do not call finite-sample fluctuations a measured guarantee half-life.
- PX-090: constrained binary warning model. Requires a justified feature-direction map, no label proxies, independent checks of monotonicity, and matched unconstrained fits. Cannot claim general no-demotion behavior from monotonic features.
- PX-091: independent execution replication. Requires newly qualified data with native four-class targets, two available evidence groups and defensible timing. AIT's existing adapted T1105 task is not an exact replication.

## Compute and reproducibility

Reuse one stopped g5.xlarge through the existing watchdog-protected controller. Two parallel CPU workers; no GPU utilization claim, no paid model API and no new fits. One allocation, 30-minute worker deadline, independent stop at 40 minutes, 45-minute outer cap. Planning reserve $2 including $.75 incidental allowance, verified instance price before start. Leave the shared data-loader untouched. Hash code, input files and bundle before start; commit this protocol and freeze. Retrieve results and verify the worker is stopped. Publish code and aggregate reports in Git; raw events, private cloud settings and large probability files stay outside Git.

Scientific checks: replay equivalence, row identity, finite probabilities, decomposition identity, reachable states, warning-union inclusion, exact rank tests including ties/empty support, and both false-theorem counterexamples. All attempted arms and failures remain in the report. No paid follow-on expansion until readiness findings justify it.
