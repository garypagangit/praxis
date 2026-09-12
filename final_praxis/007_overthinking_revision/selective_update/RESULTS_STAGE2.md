# 007 stage-two locked results: reject further investment in the current label gate

Reviewed 12 September 2026 from the completed original run fp007-selective-20260912-1c47aca. This report covers the original, prospectively specified parser and Devstral's 128 test questions. The separately amended Qwen test is still running and is not included.

**Decision:** do not expand this particular three-call label-invariance gate, start training it, or make a publication claim. It fails its registered harm/recovery tradeoff against both equally costly repeated-verification controls. Complete the already authorized Qwen test as a bounded second-model check, then close the decision; a favorable Qwen result would demonstrate model dependence and would not erase Devstral's failure of the predeclared both-model criterion.

## What completed

Devstral passed calibration: 64/64 valid initial answers, 56 correct and 8 wrong; 1,386/1,408 valid responses. All 128 test questions and all 2,816 planned test responses completed. Test initial accuracy was 84/128 (65.6%), with 44 validly wrong answers and no invalid initial answers. Overall test response validity was 2,769/2,816 (98.3%).

Qwen's original calibration had 47 correct and 17 wrong initial answers, all valid, but only 831/1,408 total responses parsed (59.0%). It therefore failed the frozen technical gate and received no original test requests. The inline-format amendment reuses those calibration responses with preserved old/new score lineage; it may issue fresh Qwen test calls only after the amended gate passes. Devstral already has original test exposure and is explicitly skipped by the amended test runner. The two parser protocols must not be silently pooled.

The original run saved 5,632 responses: both models' calibration plus Devstral's test. Its shared API ledger has 5,632 SUCCESS entries and estimated accounted cost $0.9054. This is the ledger estimate, not an invoice, and excludes EC2/EBS costs and the amended run.

## Primary reference-explanation result

All three primary methods use three check calls per decision. Harm is loss of an initially correct answer, including invalid final answers. Recovery is correction of an initially wrong answer. Every method below had zero invalid final policy outputs in this condition.

| Policy | Harm / 84 initially correct | Recovery / 44 initially wrong | Updates / 128 | Final correct / 128 |
|---|---:|---:|---:|---:|
| Proposed label gate: B0 plus TRUE/FALSE peer checks | 0 (0.0%) | 22 (50.0%) | 22 | 106 (82.8%) |
| Repeated verification: majority of B0/B1/B2 | 2 (2.4%) | 30 (68.2%) | 32 | 112 (87.5%) |
| Repeated verification: unanimity of B0/B1/B2 | 1 (1.2%) | 27 (61.4%) | 28 | 110 (85.9%) |
| Cheaper fixed TRUE-only two-call gate | 0 (0.0%) | 23 (52.3%) | 23 | 107 (83.6%) |
| Single evidence-only check B0 | 2 (2.4%; one invalid) | 32 (72.7%) | 34 | 114 (89.1%) |
| KEEP original answer | 0 | 0 | 0 | 84 (65.6%) |

The proposed gate preserved all observed initial successes, but it discarded too many successful corrections. Relative to majority it avoided two reference-condition harms while losing eight recoveries; relative to unanimity it avoided one harm while losing five recoveries. Its lower harm is therefore not sufficient evidence of a better decision rule.

The cheaper fixed TRUE-only ablation had the same zero observed harm in every condition and one additional reference recovery. That is an unfavorable empirical result for the value of the extra FALSE-peer call. It is not proof of universal dominance, but it directly triggers the protocol's concern that the mechanism may be replaceable by a cheaper check.

## The registered investment screen fails

The preregistration required at least a five-percentage-point pooled harm reduction and no more than a five-point reference-recovery loss against BOTH repeated-verification controls, in BOTH model families. The following differences are proposed gate minus comparator.

| Comparator | Pooled harm difference, percentage points [95% paired bootstrap] | Reference recovery difference, percentage points [95% paired bootstrap] | Registered observed screen |
|---|---:|---:|---|
| Repeated majority | -1.59 [-3.38, -0.38] | -18.18 [-30.43, -7.50] | Fail |
| Repeated unanimity | -0.40 [-1.28, 0.00] | -11.36 [-24.49, 0.00] | Fail |

The controls themselves had only 1.59% and 0.40% pooled harm, so even eliminating every observed harm could not reach a five-point reduction on this cohort. This is limited headroom for the prespecified benefit, not proof that every harder setting would behave the same way. The small harm difference against majority has an interval below zero, but it is substantially below the prespecified minimum gain and comes with a materially larger loss of valid recovery. The unanimity comparison also fails both observed margins. The protocol's strict investment flags are false for both comparisons.

These pooled harm counts are 0 versus 4 versus 1 over 252 initially correct question-condition opportunities. They come from 84 initially correct questions observed in three conditions, not 252 independent samples. The reviewed runner's bootstrap resamples the 128 question IDs and carries their conditions together.

Only 93.2% of question-condition cases were jointly valid across the initial answer and five primary check outputs, below the additional 95% strict signal requirement. Restricting to jointly valid cases leaves the same reference-recovery differences (-18.18 and -11.36 points). The unfavorable recovery tradeoff therefore cannot be explained away solely as a formatting artifact.

Zero observed gate harm in this small test does not establish a zero true harm rate.

## Other evidence conditions

With no supplied explanation, the proposed gate made no updates and was exactly KEEP: zero harm, zero recovery, 84/128 correct. Repeated majority produced two harms and five recoveries, ending at 87/128 correct. Repeated unanimity produced zero harms and one recovery, ending at 85/128. Thus the candidate added no value over KEEP in that condition and did not outperform the conservative repeated control.

With a mismatched explanation, all three primary methods and B0 made no updates. All remained at 84/128 correct. This is a lack of discriminatory headroom for comparing the gates, not evidence that this mechanism solved corrupted-evidence handling. The donor passages are assignment errors, not verified false or adversarial evidence.

The wrong-label SWAY-inspired diagnostic recovered 30/44 reference errors with zero observed harm and achieved 114/128 accuracy. However, the wrong-label branch is selected using gold only during scoring and the prompt is an abbreviated adaptation. Treat this as a diagnostic result; it is not an available gold-free deployment policy or a reproduction of the published SWAY benchmark.

## Calibration-derived coverage sensitivity

The coverage adjustment was fixed from calibration, not selected from test correctness. For reference explanations, calibration update counts were 5 for the candidate, 8 for majority and 5 for unanimity. Hence majority updates were retained with probability 0.625 and unanimity with probability 1.0.

| Reference policy | Test updates | Harm | Recovery | Final correct |
|---|---:|---:|---:|---:|
| Proposed gate | 22 | 0 | 22 | 106 |
| Calibration-thinned majority | 20 | 1 | 19 | 102 |
| Calibration-thinned unanimity | 28 | 1 | 27 | 110 |

This sensitivity is more favorable to the candidate than the full majority comparison: it recovers three additional errors and avoids one harm relative to that particular thinned-majority realization. It does not rescue the registered result. Achieved coverage was 22 versus 20 updates, not an exact match; thinning has not removed the unfavorable comparison against unanimity, which retained probability 1.0. The downloaded summaries do not supply paired uncertainty for the thinning comparison. Do not promote this one realized sensitivity over the registered primary comparisons.

For no evidence, calibration yielded thinning probabilities 0.4 for majority and 1.0 for unanimity. Test retained counts were two majority updates (one harm, one recovery) and one unanimity update (a recovery), versus zero candidate updates. For mismatched passages all rates were zero.

## Does the intervention-specific signal add useful information?

Reference explanations produced 33 valid changed B0 candidates: 32 correct corrections and one incorrect candidate. The label-unstable subset contained 11 of those candidates: ten correct and one wrong. Of eight candidates stable under ordinary repeats but unstable under peer labels, seven were correct and one was wrong.

Thus the extra signal caught the sole valid B0 error in that stratum, while rejecting seven correct candidates that ordinary repeated stability would accept. This is an interpretable tradeoff, but only one candidate error supports it; it is weak evidence for estimating an error detector. The software's H2 minimum-count flag is true because there are at least 20 changed candidates and nonzero outcome variation. That flag does not make the error-rate estimate reliable or establish incremental decision value.

Stable wrong outputs still occurred: 29 under no evidence, 9 under reference explanations and 36 under mismatched explanations. None were newly accepted wrong updates; they were persistent initial errors. Finite agreement did not certify truth.

## Cost, custody and next action

Across all three test evidence conditions, the proposed gate used 1,152 check calls, 250,432 input-plus-output tokens and an estimated $0.1812. The repeated controls used the same 1,152 calls, 238,009 tokens and $0.1723. The gate therefore consumed about 5.2% more tokens and 5.1% more estimated cost, despite equal call counts. These policy-level totals share B0 calls and are counterfactual deployment costs; they should not be added together as independent campaign charges. Summed request latencies are not wall-clock runtime.

Given the documented overlap with existing counterfactual prompting, blinding and selective-update work, this unfavorable incremental comparison is a reason to stop expanding this gate. Keep the benchmark, custody and measurement work as reusable infrastructure. Finish the bounded Qwen amendment, report it separately, and avoid additional threshold or prompt searches on these exposed test IDs. A future study needs a materially different mechanism and a new untouched test cohort.

This interpretation uses the downloaded locked summaries and reviewed runner, not an independent re-evaluation of every raw response. Arithmetic was independently checked: all 128-question policy denominators, correct = initial_correct - harm + recovery, and harm = correct-to-wrong + correct-to-invalid agree across all reported policies and conditions. Labels remain the original benchmark keys; prior semantic-audit caveats still apply.

Source: downloaded/outputs/mistral.devstral-2-123b__test.json, SHA256 9f77c4b61fc11cacde7b5fd58c0e817b69b1c509344e2e2c90472e78483c1653. Calibration SHA256 c0bac036db56eb4a4edeca3ec31493d926b8ac5d53d5f3747ba5b4ed13a75b2d. Original source manifest SHA256 78400dd1a176e339b237a9aa5d9b70613d38e325e35a5ae692703711dd63b054.
