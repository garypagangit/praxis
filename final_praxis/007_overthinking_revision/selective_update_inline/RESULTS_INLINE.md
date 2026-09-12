# 007 inline-amended test and combined held-out comparison

12 September 2026. **Recommendation: close this candidate without scaling it.** The completed Qwen test does not overturn Devstral's unfavorable result. Neither model meets the registered incremental-benefit screen against both three-call repeated-verification controls. The gate sometimes prevents harmful updates but also rejects useful corrections; finite agreement even admits an observed wrong update.

This is a comparison of two separately locked evaluations: Devstral under the original stage-two parser and Qwen under the prospectively amended inline-terminal parser. They use the same fixed questions, prompts, temperatures and policies, but scoring is not identical. Keep the model-specific results and protocol lineage separate; do not present a pooled confirmatory estimate or an exact cross-model replication.

## Completion, replay and cost audit

The import receipt records exactly 2,816 calibration cells, from both models' original 64-question calibration cohorts: 1,408 per model. It reports zero new calibration model calls and identifies original run fp007-selective-20260912-1c47aca. Imported cells retain their original response and request identity while adding old/new score and raw-source-cell hash lineage.

Qwen's replayed calibration has 64 valid initial answers, 47 correct and 17 wrong. Response validity rises from the original 831/1,408 to 1,406/1,408 under the amended formatting rule. The unchanged technical gate passes. Devstral's replayed calibration has 1,408/1,408 valid responses, but its prior test exposure triggers the explicit original_source_has_test_exposure skip. No fresh Devstral test is claimed.

Qwen completed all 128 new test questions and 2,816 new test responses. Initial answers are all valid: 77 correct and 51 wrong, for 60.2% initial accuracy. Exactly 2,814/2,816 test responses are valid (99.93%).

The new ledger has exactly 2,816 entries, all SUCCESS, totaling an estimated $0.4837634. This matches fresh Qwen test requests, not the 5,632 saved cells that also include 2,816 replayed calibrations. The original run's estimated API cost was $0.9053958, yielding $1.3891592 across original and amended runs. These figures exclude EC2/EBS and are estimates rather than invoices. No additional inference was performed for this audit.

## Qwen reference-explanation result

| Policy | Harm /77 initially correct | Recovery /51 initially wrong | Updates | Final correct /128 |
|---|---:|---:|---:|---:|
| Three-call proposed label gate | 1 (1.3%) | 11 (21.6%) | 12 | 87 (68.0%) |
| Three-call repeated majority | 2 (2.6%) | 16 (31.4%) | 18 | 91 (71.1%) |
| Three-call repeated unanimity | 1 (1.3%) | 12 (23.5%) | 13 | 88 (68.8%) |
| Two-call fixed TRUE-only gate | 1 (1.3%) | 13 (25.5%) | 14 | 89 (69.5%) |
| One-call B0 | 3 (3.9%) | 16 (31.4%) | 19 | 90 (70.3%) |
| KEEP | 0 | 0 | 0 | 77 (60.2%) |

Against repeated majority, the proposed gate avoids one reference harm while losing five recoveries. Against unanimity it has the same harm and loses one recovery. The cheaper two-call ablation also has the same harm and two more recoveries in this condition. These are unfavorable observed costs of the added counterfactual-label requirement.

The reference gate's single harmful accepted update was valid and identical across B0, TRUE-peer and FALSE-peer checks. This directly refutes any claim that finite label invariance certifies correctness.

Across all three Qwen conditions, each primary policy uses 1,152 check calls. The proposed gate consumes 290,723 tokens and an estimated $0.2017, versus 273,676 tokens and $0.1882 for either repeated control. Equal calls therefore do not imply equal consumed cost. These overlapping policy estimates share B0 and must not be added as separate campaign charges.

## Matched-call primary screens and uncertainty

Differences below are proposed gate minus comparator. Intervals are the locked 2,000-replicate paired-question bootstrap.

| Qwen comparator | Pooled harm difference, percentage points [95% interval] | Reference recovery difference, points [95% interval] | Registered screen |
|---|---:|---:|---|
| Repeated majority | -1.73 [-3.61,-0.42] | -9.80 [-18.75,-2.00] | Fail |
| Repeated unanimity | -0.43 [-1.41,0.00] | -1.96 [-6.98,0.00] | Fail |

The majority comparison loses more recovery than the allowed five points at the point estimate. The unanimity point estimate preserves recovery within that allowance, but misses the required five-point harm improvement and its recovery interval extends beyond the allowed loss. Both strict investment flags are false.

Observed pooled harm was 1/231 for the gate,5/231 for majority and 2/231 for unanimity, across 77 initially correct questions and three conditions. Those231 opportunities are not independent questions. Comparator harm is itself only 2.16% and 0.87%, leaving insufficient observed headroom for a five-point reduction. This limits what the cohort could demonstrate; it does not turn a failed screen into a positive result.

Joint validity across the five primary checks is 99.48%. Restricting to jointly valid cases leaves the same reference-recovery differences. The result is therefore not rescued by removing formatting failures.

## Other conditions and coverage adjustment

With no evidence, every primary method has zero harm. The gate recovers 3 errors, majority 5 and unanimity 4. It gives up useful corrections without a preservation benefit in that condition.

With mismatched passages, the gate has 0 harms and 1 recovery; majority has 3 harms and 2 recoveries; unanimity has 1 harm and 0 recoveries. This is the clearest favorable slice for the candidate, but concerns only a few transitions and does not meet the overall investment rule. Mismatched author explanations are passage-assignment errors, not verified malicious or false evidence.

Calibration-fixed thinning does not rescue the Qwen reference result. The majority retention probability is 7/9; its test realization has 13 updates,1 harm and 12 recoveries. Unanimity retains probability 1 and has the same13 updates,1 harm and 12 recoveries. The proposed gate has 12 updates,1 harm and 11 recoveries. Achieved coverage differs by one update; do not call it exactly matched. In the none condition both thinned comparators have 4 recoveries and zero harm versus the gate's3. In the mismatched condition thinned majority has 1 harm/1 recovery and thinned unanimity 0/0 versus the gate 0/1.

Every Qwen H2 minimum-information flag is false: only 19 valid changed candidates under reference explanations,6 under mismatched explanations and 5 under none. No claim of a reliable incremental error-detection signal is justified from these counts.

## Combined decision with the protected Devstral test

| Model/protocol | Reference recovery: gate /majority /unanimity | Pooled harms: gate /majority /unanimity | Decision |
|---|---:|---:|---|
| Devstral, original parser | 22/44 /30/44 /27/44 | 0 /4 /1 | Fails both controls |
| Qwen, amended parser | 11/51 /16/51 /12/51 | 1 /5 /2 | Fails both controls |

Both models show the same broad tradeoff: fewer harmful changes through more conservative acceptance, with weaker reference recovery. The effect is model- and condition-dependent; Devstral lost 18.18 and 11.36 recovery points against the controls, Qwen lost 9.80 and 1.96. Devstral's zero gate harm cannot be generalized to Qwen, where a stable wrong update occurs.

Across the three conditions, Qwen's gate and repeated unanimity happen to yield the same245 correct question-condition outputs; the gate has one fewer harm and one fewer recovery. That is a descriptive tie across different error types, not superiority. Devstral's gate yields274 correct outputs versus279 for unanimity. No cross-model pooled confidence interval is claimed.

The crowded prior literature already contains counterfactual prompting, repeated verification and selective updating. This study needed a credible incremental advantage, which it did not show. Preserve the clean benchmark, replay custody and measurement infrastructure. Do not extend this gate by searching new thresholds or prompts on these now-exposed test items. A future candidate needs a materially different mechanism and fresh held-out data.

This audit checks locked summaries, replay receipts and ledger counts, not every raw provider response. Per-policy arithmetic and source hashes are recorded in combined_heldout_audit.json. Benchmark gold labels are unchanged and inherit the earlier semantic-data caveats.
