# PX-055 disposition: retain the measurement result

September 15, 2026 · Internal AI-assisted research assessment

**Decision: retain PX-055 as a completed bounded geometry/replication study and hold additional spending.** It is not the preferred next investigation for a distinct mechanistic Praxis. This changes the investment priority, not its archived results.

## What the evidence supports

The R3 adjudication covers **9/9 cells** across Qwen, Llama and Gemma at FP16, INT8 and NF4. Its status is `H1_PRECISION_INVARIANT_BOUNDED`. The maximum principal angle is **15.426647 degrees**; the minimum directed transfer ratio is **0.975**. E3 has three model clusters and is descriptive; the E4 restoration proxy is nonpositive in all three models. [Original adjudication](/C:/Users/garyp/OneDrive/Documents/codex/reports/refusal_direction_quantization/e1_e4_20260831/closeout_r3/PX055_R3_INDEPENDENT_ADJUDICATION.json)

The geometry corpus consists of 116 locally constructed safe refusal-style/benign statements. Behavioral flags cover 450 XSTest rows, but decoded completions were not retained. Independent semantic relabeling is therefore unavailable from the existing flags and hashes. This is an outcome-measurement limitation, not a missing formatting task. [Completed package](/C:/w/praxis_papers/final_praxis/papers/20260914/03_px055/README.md)

## Direct comparison to primary work

| Primary source and locator | Relevant overlap | Consequence for PX-055 |
|---|---|---|
| [Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717), abstract and intervention experiments | Refusal directions are evaluated through interventions on actual model behavior. | Direction geometry needs a demonstrated connection to the behavior named in the claim. |
| [Towards Understanding and Improving Refusal in Compressed Models](https://arxiv.org/html/2504.04215v1), Table 5 and section 6 | Quantized/base refusal-direction cosines of roughly 0.99–0.996 and an intervention for compression-related refusal changes are already reported. | Stability under quantization and restoration of directions are established topics. |
| [Quality Is Not a Safety Proxy Under Quantization](https://arxiv.org/html/2606.10154v1), sections 4.4–4.5 and Table 5 | Geometry stays above 0.97 cosine in the measured quantized cells while providing weak separation of behavioral risk; lexical and semantic scoring are compared. | Even “stable geometry does not certify preserved safety” substantially overlaps prior work. |

**Assessment:** this targeted comparison weakens the case for a new mechanism. It does not prove that every possible PX-055 contribution is already known, nor equate cosine and principal-angle measurements.

## Reopening gate

Before additional compute, identify a specific comparison that the three papers leave unresolved, why its outcome matters, and an independent way to measure it. A possible question concerns whether style-derived directions change wording while behavior-derived directions change semantic refusal. That question is itself unqualified and needs closer literature review.

If the remaining distinction is only model choice, NF4, more layers or stronger bookkeeping, keep the work as a replication and measurement record. A replication may still be useful; a claim of a new defense would exceed this evidence.

Any stronger study needs retained complete responses, independent semantic labels, disjoint direction-estimation and outcome data, lexically matched controls, random/sham directions, and benign utility. Specify useful-effect margins and uncertainty before outcomes. If controls remove the proposed semantic effect, or the interval rules out the prespecified useful effect, close that claim. An inconclusive result remains inconclusive.
