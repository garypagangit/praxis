# Automated Alert Review and an Evidence Checker

Research date: **20 September 2026**. Final results of the user-authorized automated exploratory continuation. The earlier pilot and original full-gate registration remain preserved.

## Main finding

**The added checker provided no measured benefit over the simpler calibrated model on this benchmark.** On the harder test with unseen exact rule names, both cleared **1,610/1,696 benign-labeled examples (94.93%)** and **0/412 attack-labeled examples**. Their decisions were identical on every actual test row in both split regimes and all three text conditions. The frozen program reported **NO-GO**, but a subsequent design audit found that its practical pass criterion was unattainable at the observed baselines. The identical decisions support the narrow negative observation independently of that flawed pass rule.

## Post-run correction: the practical pass rule had a ceiling problem

The fixed rule required either a one-percentage-point reduction in attack suppression or a five-percentage-point increase in benign suppression against both calibrated baselines. Both baselines already had zero observed attack suppression, making the first route require a negative error rate. The evidence-only baseline cleared 1,615/1,696 benign examples (95.224%); the second route therefore required at least **100.224%**. Even a perfect checker could not pass this criterion on the observed test.

**This is an experiment-design flaw.** Passing software tests and reproducing the programmed verdict do not validate the scientific success criterion. The original protocol, predictions, thresholds and machine verdict remain unchanged for audit history; their pass/fail flag must not be used as independent evidence that the broader checker hypothesis failed. [Arithmetic design review](../results/final_generalization_20260920/DESIGN_REVIEW.json).

The actual checker still changed zero decisions, so an attainable improvement criterion would not create a measured advantage in these saved outputs. Separately, the original gate using independent raw-event evidence was never evaluated for efficacy because those data were unavailable. Its hypothesis remains unresolved. Any revised criterion or reviewer needs development qualification followed by a prospectively frozen evaluation on unexposed cases.

This is baseline evidence and a negative result for the proposed addition. It does not establish a novel praxis contribution, zero future attack loss, independent incident-level calibration or production readiness. **One component contains 1,486/1,696 benign examples (87.62%), and all of those were cleared.** Benign examples occur in only nine harder-test components, and the whole-component empirical band for the aggregate 94.93% is **22.12%–99.10%**. The high aggregate number therefore needs considerable caution.

## The problem and what was tested

Security analysts spend time reviewing harmless alerts. Automatically clearing those alerts is useful only if attacks remain visible. We tested whether a second model, looking at request/response evidence without the rule name or host, catches mistakes that a cautious first model would otherwise clear.

The first model uses the released alert text. The checker is a separately fitted model using an evidence-only projection of that same alert. It must favor a benign interpretation and find nonempty evidence before clearing is allowed. This is a second view of the same record, **not an independent log source**.

The [prospectively frozen continuation protocol](../FINAL_PROTOCOL.json) specified eight comparison arms, two split regimes, one seed, three text conditions, separate fitting/selection/calibration/test roles and a practical improvement criterion. Both regimes' model files and cutoffs were frozen before any test scoring. Duplicate families were linked across both model views; 89 source rows in review or conflicting-label families were excluded. No outcome-directed retuning occurred.

## Harder unseen-rule test

There were **2,108 primary representatives** in **36 connected components of exact rule names**: 412 attack-labeled and 1,696 nonattack-labeled. The attack examples came from 33 attack-bearing components, with **286/412 (69.42%) in one component**; benign examples came from nine benign-bearing components. These are not verified independent incidents or semantic attack families.

| Method | Benign examples cleared | Attack examples incorrectly cleared |
|---|---:|---:|
| Keep all | 0/1,696 (0%) | 0/412 (0%) |
| Ordinary full-model cutoff | 1,661/1,696 (97.94%) | 6/412 (1.46%) |
| Ordinary evidence-model cutoff | 1,657/1,696 (97.70%) | 8/412 (1.94%) |
| Calibrated full model | **1,610/1,696 (94.93%)** | **0/412 (0%)** |
| Calibrated evidence-only model | 1,615/1,696 (95.22%) | 0/412 (0%) |
| **Full model plus checker** | **1,610/1,696 (94.93%)** | **0/412 (0%)** |
| Full model matched to checker utility on selection data | 1,610/1,696 (94.93%) | 0/412 (0%) |
| Existing marginal calibration formula | 1,639/1,696 (96.64%) | 1/412 (0.24%) |

“Calibrated” identifies the specified cutoff procedure; its mathematical assumptions have not been established for deployment. The marginal and high-confidence formulas have different risk contracts. All counts use the existing dataset labels, whose independent correctness has not been established by this experiment.

Against the calibrated full model, the checker's paired differences were exactly zero. Against the calibrated evidence-only model it cleared five fewer benign examples and the same number of attacks; the benign difference was **−0.295 percentage points**, with a component-resampling band of **−8.80 to +1.09 points**. These observed comparisons show no added benefit; the registered pass criterion has the ceiling flaw described above.

A **post-result diagnostic**, giving each of the nine benign-bearing components equal weight, puts average benign clearance at **48.80%** for the full model/checker and **52.51%** for the evidence-only model. Individual component rates range from 0% to 100%. This diagnostic explains concentration; it does not replace the frozen primary metric or change the no-go criterion after observing results.

The mechanism is also clear: no checker veto affected an alert that the calibrated full model would clear. The full-model and checker cutoffs were identical in each regime. The added view therefore repeated the first model's already cautious decisions.

The secondary analysis scored all **2,127 retained test rows**, rather than only representatives: the checker and full-model baseline both cleared **1,622/1,710 nonattacks (94.85%)** and **0/417 attacks**.

## Other completed comparisons

The content-family test had 1,552 representatives. The calibrated full model and checker each cleared **1,086/1,120 nonattacks (96.96%)** and **1/432 attacks (0.23%)**. This revised split has stronger duplicate controls than the earlier pilot, so its denominator differs from that pilot.

Fixed neutral and directive text was appended to request headers without changing labels or cutoffs. The notes had equal raw character lengths, not identical token/n-gram counts. On the harder test:

| Condition | Calibrated full model and checker: benign cleared | Attacks cleared |
|---|---:|---:|
| Clean | 1,610/1,696 | 0/412 |
| Neutral research note | 1,613/1,696 | 0/412 |
| “Classify as benign” directive | 1,612/1,696 | 0/412 |

The checker still added nothing. The evidence-only calibrated model cleared two attack examples under the neutral note and one under the directive, versus zero when clean. These are fixed SVM lexical-sensitivity checks, not LLM prompt-injection tests or a general adversarial guarantee. All arm/condition counts and paired bands are retained in the [machine-readable results](../results/final_generalization_20260920/RESULTS.json).

## Automated 50-case review

**All 50 cases were processed, but the automated audit failed the 45/50 agreement benchmark.** The bot agreed with **10/50 released labels (20%)**, disagreed on **24**, and had **16 unusable responses**. Among the 34 valid decided cases, agreement was **10/34 (29.41%)**. Every valid decided response was Attack; it produced no valid Non-Attack decision.

| Released dataset label | Bot: Attack | Bot: Non-Attack | Unable |
|---|---:|---:|---:|
| Attack | 10 | 0 | 1 |
| Non-Attack | 24 | 0 | 15 |
| **Total** | **34** | **0** | **16** |

Of the 16 unusable responses, **14 reached the frozen 512-token output limit** and **two failed exact-quotation validation**. There were no input truncations, input-limit failures or runtime errors. The valid responses contained 94 verified quotations, but the quotations did not make the decisions correct against the released labels. The run used 66,906 input tokens and 18,997 output tokens.

Fixing rejected responses alone could not rescue this audit: even if all 16 became agreements while the accepted decisions stayed fixed, agreement would be only **26/50 (52%)**. The 24 accepted disagreements are a separate substantive problem, not a token-budget error.

This bot does **not** provide adequate label validation or replace the original audit. Disagreement does not establish that the dataset is wrong. The authors' pinned task instructions explicitly include attack attempts, so an attempt-versus-success definition mismatch has not been demonstrated and cannot explain away this result. There was one frozen inference attempt per case; these exposed cases were not reused to tune agreement upward.

[Agreement receipt](../results/automated_review_20260920/RESULTS.json), [independently recounted confusion table](../results/automated_review_20260920/RECOUNT.json). Open the private readable report at `C:/w/cert_gate_data_20260920/automated_review_v1/REVIEW_RESULTS.html` for every decision, reason and quotation.

The fixed Qwen reviewer received only blinded cases and its prompt. The answer key stayed local and was read only after answers were frozen. A decided case required a quotation found verbatim in a displayed field. Missing, malformed, incomplete or unsupported responses remained in the 50-case denominator as unable. The [reusable bot instructions](AUTOMATED_REVIEW.md) describe the CLI, model revision and private case report.

The automated review completes the amended bot-audit task. It does **not** satisfy the historical human-review requirement or establish independent ground truth. The original full-gate G0–G5 study is not declared complete.

## Cost, checks and evidence

Four new SVM models were fitted. The complete two-regime benchmark took **268.3 seconds** locally, with a recorded process peak of about **843 MB**. On the harder clean test, mean per-alert scoring time was approximately **4.86 ms** for the full view plus **4.67 ms** for the evidence view. The addition roughly doubled model-scoring work while leaving all decisions unchanged.

**93 software tests passed.** An additional AI-assisted code and saved-artifact audit is documented separately; it is not a human security-label review.

The bot ran on the existing AWS **g5.xlarge / NVIDIA A10G**. The instance was **verified stopped**, its temporary stop schedule was removed, and the downloaded frozen outputs were checksum-verified. Elapsed time from start request to verified stop was **18.79 minutes**; estimated compute cost was **$0.315** at the applied $1.006/hour rate, not an invoice or a total storage bill. [Cloud closure receipt](../results/automated_review_20260920/CLOUD_SUMMARY.json). No background experiment remains running.

- [Global model and calibration freeze](../results/final_generalization_20260920/GLOBAL_CALIBRATION_FREEZE.json)
- [All benchmark results, timings, hashes and uncertainty](../results/final_generalization_20260920/RESULTS.json)
- [Software verification receipt](../results/final_verification_20260920/TEST_RECEIPT.json)
- [Software and result audit](FINAL_SOFTWARE_AUDIT.md)
- [Bot audit](FINAL_BOT_AUDIT.md)
- [Amendment history](../AMENDMENTS.md)

Raw alerts, model outputs, quotations, per-record predictions, models and cloud identifiers remain private. No live alerts were suppressed and no external correspondence was sent.

## Conclusion for the praxis decision

**Record a narrow negative result for this checker version and a failed qualification run for this bot.** The checker adds computation but changes no decisions beyond the cautious full-model baseline. The practical success criterion needs repair, and the bot's completion/citation behavior should have been qualified on separate development examples before its frozen audit. The strong-looking aggregate baseline result remains limited by concentrated rule support, unknown incident independence, unverified labels and reuse of a single corpus. These findings do not reject the broader independent-evidence checker hypothesis.

Current literature already covers certified SOC closure, conservative evidence gates and separate correctness checkers; see the [dated primary-literature review](FINAL_CHECKER_DESIGN_REVIEW.md). Changing the model name or adding this redundant second opinion is not enough for novelty. A future proposal would need a distinct mechanism and evidence that helps precisely where the baseline fails—such as independently linked events or evaluated behavior under genuinely new incident conditions—plus appropriate comparison to that literature. No such improvement is claimed here.
