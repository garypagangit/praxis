# PX-100–102: explanation experiments

Frozen before these new analyses; underlying test data and prior results are already exposed. No new independent confirmation or novelty guarantee is claimed.

## PX-100 — Verifiable explanations of warning loss

Independently reconstruct PX-081 acquisition traces from recorded actions, availability, delays, budget and deadline (three seeds, three conditions, three budgets, entropy and harm policies). Check state, attempts, spend, elapsed time and final probabilities. This checks execution of recorded actions, not whether the selector chose the optimal action. Partition missed attacks into those for which some saved expert warns and those for which all four experts are silent. Expert availability is not assumed by this decomposition.

For PX-093 base-three ensembles on UNRAVELED, Wilson and Harrison, recompute OR and mean; report available warnings suppressed by mean, all-member misses, member necessity, exfiltration warning recall and benign false alerts. Hold member predictions fixed. Aggregate intervention is computational, not an explanation of real-world attack causation. Check against previously saved decisions. Fault challenge: invert stored output or remove an input; verifier must reject a wrong claim or abstain on incomplete evidence. Fault outcomes establish only coverage of these specified faults.

## PX-101 — Feature explanations of warning loss

Use saved current-plus-role LightGBM experts for seeds 8101–8103. Select at most 128 rows per cohort by ascending stored event hash: seed-8103 missed exfiltration, warned exfiltration, correctly benign, false-alert benign. Explain the fixed benign-minus-exfiltration raw-score margin using native TreeSHAP. Verify saved probabilities and raw-score additivity. Measure top-five Jaccard overlap and directional agreement across seeds, separately for unchanged and changed warning decisions. Report per-cohort results and dominant features. Enriched sampling cannot estimate population prevalence. Additivity alone is not behavioral or causal fidelity. These are supporting diagnostics: published IDS explanation-reliability studies already cover this general technique.

No synthetic feature replacement is used: changing correlated network features separately could produce impossible records. Observed-record counterfactuals, human usefulness and causal validity remain untested.

## PX-102 — Human review utility pilot

Prepare 12 replay-verified cases, questions and hidden answer key. Two arms show the same member scores: numeric table alone versus table plus deterministic explanation. Counterbalance arm assignment across participants; each participant sees each case once. Primary measure: correct answers identifying whether a combiner discarded an available warning. Secondary: response time and confidence. No study outcome until real people participate. A small pilot estimates feasibility, not definitive human benefit; participant recruitment, consent and applicable university review precede enrollment. Do not simulate participants.

## Decision criteria

PX-100: any mismatch blocks an exact-replay claim. Full agreement supports trace correctness only. A potential paper requires a demonstrable distinction from prior IDS audits and an independent evaluation beyond exposed development cases.

PX-101: report all results; do not choose favorable cohorts or thresholds afterward. Stability is descriptive, with no invented pass threshold. PX-102 remains prepared, not completed, until genuine responses exist. Zero new fits, AWS jobs or paid inference are needed for this phase.
