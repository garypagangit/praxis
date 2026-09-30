# Closing PX-088--091 prerequisites and exploratory work

2026-09-30. The user requested completion of open items. This extends the completed PX-085--087 work without changing its freeze or outputs. All data are previously exposed development data. No new novelty or independent-confirmation claim is presumed. Commit the source and input hashes before the following fits/replays.

## PX-088: disjoint selective calibration with a hard review-capacity ledger

Use clean budget-2 roles-first and harm probabilities for each of seeds 8101--8103. Split the original calibration event hashes into even and odd first-hexadecimal digits: one subset selects the confidence cutoff, the other calibrates warning risk. No record can appear in both; labels do not choose the split. Confidence is max(P(benign),1-P(benign)). Fix review budgets to 100, 1,000 and 5,000 per 100,000 rows. The selector cutoff is the corresponding lower empirical confidence quantile, with ties automatically accepted. This targets a review rate; it does not guarantee the future request rate.

On the separate risk-calibration subset accepted by that fixed selector, apply the existing conservative finite-rank rule to attack scores within each supported true stage. Alpha values .01,.05,.10. Report supported-stage and all-stage-fail-closed variants and a selection-only comparator. Keep every original automatic warning. The conditional risk argument applies only under suitable conditional exchangeability after fixing the independently learned selector. These correlated chronological flows do not establish it.

This is a sample-split selective CRC construction, not a claimed reproduction of SCRC-I or SCRC-T. [Selective Conformal Risk Control](https://arxiv.org/html/2512.12844v1) uses specific transductive symmetry or a calibration-only correction. Its advertised guarantee cannot be attached to an arbitrary pair of thresholds. No high-probability claim or optimality claim is made here.

Maintain an independent FIFO review-capacity ledger per test capture, with capacity accruing at budget/100000 per completed flow. At capture end at most floor(budget*N/100000) review requests can have been served; remaining requests stay unresolved. Compute endpoint FIFO totals without claiming physical service time. Overflow must never silently become benign. Report automatic misses with automatic-stage denominators, all stage supports, review requests, served requests, unresolved queue, benign review requests, automatic benign false alerts and total warnings plus review requests. Deferred attacks do not count as successfully detected by humans. Missing movement calibration support stays explicit.

## PX-089: prequential recalibration under simulated label delays

Use the same two policies and three seeds, clean budget 2. Evaluate captures 6--10 sequentially. Labels become available at recorded flow end plus simulated delays 0,24,72 hours (timestamps are milliseconds). Freeze each threshold at the next capture's earliest start. Require every calibration label to be available strictly before that boundary and every source capture to be smaller than the evaluated capture.

Compare: frozen original-calibration threshold (using only labels available before capture 6), cumulative available earlier labels, and the most recent earlier capture with any available labels. The last rule does not search for favorable stage support. Alpha .01,.05,.10; supported-stage and all-stage-fail-closed variants. Never fit the underlying detector. Preserve pre-existing warnings. Report every capture's calibration support, threshold, stage recalls/misses and false alerts, plus pooled counts. Captures lacking a target stage have undefined target recall. New labels are a simulated feedback assumption, not measured operational availability. This measures empirical target failures and tradeoffs, not a guaranteed half-life or optimal recalibration frequency.

## PX-090: qualify raw-feature constraints and test a defensible score constraint

The available raw flow counters and host roles do not justify a universal claim that increasing a feature must increase attack probability. Do not invent that direction from correlation with test labels. Instead explicitly adapt the experiment to a binary model combining two observed expert attack probabilities: current evidence and roles evidence. The design requirement is that increasing either expert's attack score, holding the other fixed, cannot lower the combined attack score. It is not a causal statement about traffic.

For each of the three seeds, fit matched unconstrained and monotone LightGBM binary models on that seed's already saved forward-out-of-fold PX-081 training predictions and attack/benign labels. Verify training events exclude calibration/test hashes. Use 150 estimators, 15 leaves, learning rate .05, min_child_samples 10, reg_lambda 1, n_jobs 2; monotone_constraints=[1,1] for the constrained arm only. No tuning. Exactly six new small fits; persist models privately.

Compare current expert, roles expert, within-seed warning union, unconstrained score model, constrained score model and constrained score model with an explicit union veto. Fixed binary threshold .5; secondary supported-stage alpha=.05 gate calibrated on the original calibration split. When a binary model warns, stage assignment uses the mean attack-class scores of the two experts, an explicit fixed refinement rule. Both experts require roles cost 1; report two expert evaluations plus the small combining model where used. No free cross-seed ensemble is implied.

Evaluate clean test rows and each capture. Verify monotonicity on a fixed 101x101 score grid; this is an implementation check, while the constraint's general behavior depends on LightGBM's documented algorithm. Report warning demotions relative to each constituent and their union. Monotonicity does not imply retention of either constituent warning. The union veto retains warnings by construction but can increase false alerts. This adapted experiment does not complete an unsupported raw-role/exfil-feature causal constraint claim.

## PX-091 and novelty closeout

Recheck primary author/public release endpoints and local holdings for SCVIC, DAPT, DSRL, S-DAPT, AIT, CAM-LDS/CasinoLimit, ProvICS and Windows-APT. Require native benign/movement/exfiltration targets, independent execution identity, qualified timing and both evidence groups before claiming exact replication. Public descriptions, synthetic derivatives, an adapted T1105 task, or a bare timestamp column are insufficient. Preserve specific missing requirements and distinguish completed qualification from blocked replication. Do not create a new physical campaign or silently replace the task.

Review source versions: the CALIBURN record was substantially corrected and retitled in v3; old reported performance must not be treated as validated current evidence. Generic CRC, selective prediction, recalibration, probability averaging, warning union and monotone tree constraints are established methods. A completed measurement is not automatically a novel dissertation contribution.

## Execution and tests

Run the three lightweight jobs in parallel locally, because the previous 95 MB AWS upload failed while the unchanged replay took 32 seconds locally. Do not start another paid idle worker to repeat that transport failure. AWS remains available for a later job with a qualified transfer path. No model API or new cloud allocation is needed for this closeout.

Hash all relevant prior inputs and code. Tests cover no future-label access, delay units, missing-stage fallback, disjoint calibration, budget/queue conservation, stage denominators, finite probabilities, monotonicity and no-demotion veto. Preserve all arms. Save every raw result row, aggregate interpretation, source checks and status changes in Git. Mark unresolved replication and novelty requirements explicitly.
