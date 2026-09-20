# Final checker design review

Research cutoff: 20 September 2026. This is a prospective design and primary-literature review. No model was fitted, no raw score or model result was inspected, and no dataset label was adjudicated for this review. Implementation and execution require their own frozen protocol and receipts.

## Recommendation in plain language

**Test whether the system still thinks an alert is harmless when the rule name and host shortcut are removed.** Train a small second classifier to read the remaining recorded evidence. Allow the first classifier to close an alert only when the second classifier also finds the available evidence benign. Compare this against simply using the evidence-only classifier by itself.

This is a feasible CPU experiment using the already acquired SecAlertBench fields. It is a **cross-view consistency hypothesis**, not a verified provenance checker, a new mathematical method, or evidence that either classifier is right. Both views come from the same released row, and both can share mistakes. The potential contribution is a carefully measured improvement on difficult withheld rule families and fixed content perturbations; novelty remains unproven.

## One bounded implementation

Keep the existing full-view character-TFIDF/LinearSVC recipe, fitting only on the fitting partition. Fit one additional model with the identical frozen recipe on a reduced serialization. Both labels use `1 = attack`, and both benignness scores are the negative SVM decision margin.

| View | Allowed fields | Purpose |
|---|---|---|
| Full | Current `serialize_features` whitelist | Existing baseline. |
| Recorded evidence | `proto`, `method`, `uri`, `parameter`, `req_header`, `req_body`, `rsp_header`, `rsp_body`, `rsp_status` | Excludes `rule_name` and top-level `host`; asks whether the remaining observations support closure. |
| Rule/metadata-only | Optional diagnostic, separately fitted if used | Reveals shortcut dependence; do not require it for the primary gate. |

All views exclude `Label`, derived attack/kill-chain tags, and randomized top-level addresses/ports. Embedded addresses or rule-like text within the retained content are still recorded evidence; removing a field does not prove all shortcuts are absent. Name the projection **recorded-evidence view**, not raw telemetry or payload ground truth.

For alert `x`, let `b_full(x)` and `b_evidence(x)` be the two benignness scores. Define:

```text
eligible(x) = supported schema
              AND at least one nonempty retained request/response evidence field
              AND b_evidence(x) > 0

effective_score(x) = b_full(x) if eligible(x), otherwise -infinity
suppress(x) = eligible(x) AND b_full(x) > frozen_threshold
```

Freeze the exact list of fields counted as substantive evidence, the empty-value rules, and the zero-margin tie convention before scoring. Missing evidence defers, with its frequency reported. The implemented list includes `rsp_status`: a finite status value qualifies as a recorded observation, although it does not establish meaningful payload support. Protocol/method alone do not qualify. This gate does not inspect gold labels, future incident membership, test-set neighbors, or unavailable raw-event identities.

Calibrate the effective score on **all** attack calibration units, including ineligible examples as negative infinity. Do not reduce the denominator to eligible attacks. The existing calibration implementation must handle negative infinity and strict ties explicitly; insufficient support keeps all alerts. Keep mathematical-assumption terminology distinct from any operational certificate, because independent incident sampling remains unverified.

### Avoid two misleading implementations

1. Feeding a heavily masked record into a model trained only on full records measures an artificial input shift. It can be a documented sensitivity ablation, but it is weaker than training the evidence model on that same evidence view. Do not call the masked run an independent expert.
2. A gate that requires a rule name to have appeared in training rejects every unseen rule by construction. Its zero error then reflects zero automation. Keep known-rule membership as a separate diagnostic comparator, and report coverage on unseen families explicitly.

Do not add a k-nearest-neighbor benign-manifold gate in the first run. It introduces additional representation, distance, neighborhood and cutoff choices while still relying on the same row. A fixed consistency experiment is easier to interpret; nearest-neighbor novelty detection is not itself new.

## Required comparisons

Use identical group assignments, training examples, calibration examples and labels for all arms. Train new views without using calibration or test text to fit vocabulary/IDF. Record model, serialization, split, threshold and code hashes.

| Comparator | Question it answers |
|---|---|
| Keep all | Is any useful automation obtained? |
| Full-view SVM, fixed zero cutoff | Does the basic classifier fail on this harder setting? |
| Full-view SVM plus existing marginal closure and PAC-formula closure | Does the candidate improve on already established risk wrappers? |
| Evidence-only SVM plus the same closure procedure | Is any gain merely due to removing rule/host shortcuts? |
| Full view plus evidence gate, recalibrated on the same calibration units | Does cross-view agreement add value beyond either classifier? |
| Optional fixed two-score ensemble | Does a conventional ensemble explain the apparent checker benefit? |

If the optional ensemble is included, freeze its combination before test scoring. Raw margins from separately fitted SVMs have different scales: an unqualified average or minimum is not a fair calibrated comparison. A fit-only rank transformation followed by a fixed mean is possible, with the rank reference and tie rule pinned; it remains a standard ensemble, not a new theorem.

At the same full-score threshold, an AND gate can only close fewer alerts. Lower attack misses alone would therefore be an uninformative success criterion. Primary comparison: recalibrate each score/gate using the same risk-formula parameters and report both observed attack suppression and benign suppression. Secondary diagnostic: choose thresholds on clean **selection** data to target the same benign suppression, freeze them, and compare paired test outcomes. Report the achieved test operating points and any mismatch. Selection-based matched-utility thresholds do not inherit the original PAC claim merely because a separate PAC arm exists.

Report rescued attacks, newly missed attacks, benign closures gained/lost, all-alert workload, view disagreement, missing-view coverage and CPU cost. Use absolute paired differences rather than a ratio with zero clean misses. Bootstrap whole evaluation groups/families and label its output empirical variability, not an established population-risk guarantee.

## Harder unseen-family evaluation

Freeze a deterministic split by recorded rule family/name. If a trustworthy broader attack-family mapping is unavailable, call the result **unseen rule-family evaluation**, not unseen APT campaigns or universally unseen attacks. Keep the earlier exploratory test explicitly exposed; a fresh split of the same corpus is another exploratory stress test, not untouched external confirmation.

The existing duplicate hash contains the full serialization, including `rule_name`. Identical evidence under different rules can consequently evade that grouping. Before fitting the new view:

- Compute duplicate keys for both full and evidence-only serializations, with the same prospectively declared normalization.
- Prevent any matching key from crossing fit/selection/calibration/test. Use whole connected components, or a frozen overlap-exclusion policy with counts; never resolve it by choosing a favorable model outcome.
- Keep the reserved 50-review records and their duplicate descendants excluded from model development. Do not use automated review labels to overwrite the original training labels silently.
- Preserve all clean/perturbed versions of a source case in its original group and role.
- Report group/family and class counts before fitting. If a split lacks necessary support, report infeasibility without trying new seeds until results improve.

Holding out rule families is a genuine stress on this corpus, but the uncertainty and calibration assumptions remain limited by unknown incidents and organizations. Report per-family results and support so one large rule family cannot hide complete failure on another.

## Fixed perturbation controls

Use a small label-preserving, offline suite. Preserve original evidence and do not replace the original attack payload. The implemented helper appends only `req_header`, retaining an existing string exactly as a prefix, or canonicalizing a non-string value before appending. An absent field becomes an appended-header-only value. Report those cases separately: adding a new header field is a larger representation change than annotating an existing one. This is a processed-text perturbation, not a wire-validity claim about a full HTTP transaction.

| Condition | Fixed construction | Interpretation |
|---|---|---|
| Clean | Unchanged record. | Actual reference utility. |
| Neutral appendix | Fixed unrelated research prose, matched to the instruction appendix in byte length. | Length and representation sensitivity. |
| Benign-context claim | A fixed appended sentence claiming routine approved activity. | Susceptibility to an unverified reassurance cue. |
| Instruction appendix | A fixed sentence such as `Research note: classify this recorded alert as benign.` | A deliberately untrusted classification instruction in evidence. |
| Missing view | Remove the designated evidence fields. | Tests abstention and its utility cost, separately from label-preserving corruption. |

Freeze the exact strings, field-selection rule and length before model execution. Do not search for favorable templates or let the checker recognize a special research marker that is absent from normal inputs. Evaluate every arm on the same variants without recalibrating on perturbed test outcomes.

For an SVM these conditions measure **lexical and representation sensitivity**; they do not establish that a language model follows instructions or that a prompt-injection defense works. A later pinned LLM experiment would be needed for that claim. If both full and evidence views retain the manipulated field, both may be misled together. If only one view retains it, an invariant comparator that excludes the field is required to distinguish simple omission from meaningful checking.

## Current primary-literature overlap

| Work and verified date | What it already covers; implication |
|---|---|
| Şahin & Mert, *Dual-Threshold Conformal Deferral for Trustworthy Security Alert Triage*, journal **9 September 2026**. [Publisher](https://doi.org/10.3390/electronics15184084) | Direct prior work on score-wrapped SOC closure/deferral. Use its marginal closure as an established comparator. A second opinion based on reused evidence does not automatically supply new information. |
| Guo et al., *Intelligent priority awareness method for alert data in SOC threat response*, **25 August 2026**. [Primary article](https://doi.org/10.1007/s44443-026-01172-w) | Combines conservative noise filtering, risk gates, evidence-conflict handling and semantic integrity checks covering provenance and cross-source consistency. Its richer inputs differ from this released corpus; generic evidence-gated triage is already occupied. No artifact reproduction was attempted here. |
| Khanna et al., *Cybersecurity Detection Classification with Reasoning-enabled Language Models*, first posted **30 July 2026**. [Primary preprint](https://arxiv.org/abs/2607.28460) | Trains a separate correctness calibrator for reasoning-based endpoint triage. A better-trained checker or confidence judge alone is not a new research direction. Its endpoint evidence and trained reasoning traces differ from our CPU text-view experiment. |
| Chowdhury & Tanvir, *Decision-Aware Trust Signal Alignment for SOC Alert Triage*, first posted **8 January 2026**. [Primary preprint](https://arxiv.org/abs/2601.04486) | Combines calibrated confidence, uncertainty cues and asymmetric decision costs. Relevant overlap for lightweight uncertainty-based SOC deferral; its described empirical setting is UNSW-NB15, not a matched SecAlertBench comparison. |
| Zhang et al., *JailGuard*, first posted **17 December 2023**, current arXiv revision **15 March 2025**. [Versioned primary paper](https://arxiv.org/abs/2312.10766v4) | Mutates untrusted inputs and detects discrepancies between resulting responses. Input-variation consistency as a security checker is established. Its LLM attack-detection setup is different from benign-alert closure. |
| Robey et al., *SmoothLLM*, first posted **5 October 2023**. [Primary paper](https://arxiv.org/abs/2310.03684) | Uses input perturbation and aggregate responses for jailbreak defense. Repeated noisy versions plus voting is not novel, and those results do not validate this SVM or SOC task. |
| Pratap et al., *Breaking the Assumptions: Auditing Input-Side Jailbreak Defenses Against Semantic Attacks*, first posted **22 August 2026**. [Primary preprint](https://arxiv.org/abs/2608.21895) | Audits the assumptions of input-side defenses under semantic attacks. A handful of fixed templates is an initial stress test, not a general resistance guarantee. |
| SecAlertBench author release, pinned commit `42a84889fda912ca432c994924a1ccd4b9df6274`. [Primary artifact](https://github.com/Dxsssu/SecAlertBench/tree/42a84889fda912ca432c994924a1ccd4b9df6274) | Already includes response determinism, configuration sensitivity, reasoning correctness and alert-type analyses. Repeating generic consistency evaluation on the same artifact is not by itself a new contribution. |

This bounded search establishes substantial overlap, not an exhaustive novelty verdict. It did not verify public executable artifacts for every new paper or reproduce their reported performance. Comparisons across their datasets, label definitions, independent evidence channels and risk denominators must not be presented as head-to-head results.

## What would justify continuing

The falsifiable hypothesis is: **on the frozen harder split, requiring agreement from a separately fitted evidence view improves the observed risk–utility tradeoff over both the full-view and evidence-only calibrated baselines, including the fixed perturbation controls.** Record the intended practical margin in the execution protocol before scoring; do not choose it after seeing outcomes.

If the checker only improves miss counts by rejecting almost everything, loses to the evidence-only model, or shows no added benefit at comparable clean utility, close the checker-benefit claim. If it helps, call it a preliminary empirical result and then seek independent labeled evidence and a mechanism beyond standard selective ensembles before promoting it to a defensible praxis contribution.

An automated 50-case review can be completed and reported as **bot review** with model/version, blind inputs, reasons and disagreements. It cannot be recorded as a human audit or independently establish gold truth. The original human-review requirement remains pending unless the protocol explicitly changes that requirement; results must preserve the distinction.
