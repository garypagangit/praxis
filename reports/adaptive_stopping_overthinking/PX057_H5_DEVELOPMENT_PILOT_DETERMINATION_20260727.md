# PX-057 r2 Development-Pilot Determination

Date: 2026-07-27

Experiment: Adaptive Stopping to Prevent LLM Overthinking

Frozen mechanism: `m4-k2-valid-v1`

Final status: **FAIL - H5 NO-GO**

Evidence class: **outcome-exposed H4 development pilot; not H5 and not confirmatory**

## Executive determination

The r2 mechanism-selection gate failed. The frozen native-chat, three-line
response contract and validity-gated stopping rule met three of six required
gates, but it missed the minimum compute saving, strict-valid response rate,
and bound-sentinel requirements. Under the predeclared one-look rule,
`m4-k2-valid-v1` is not eligible to advance to fresh H5 generation.

This result must not be tuned. No threshold, policy, prompt, parser, validity
rule, metric, or sentinel may be changed after viewing these outputs under the
r2 identifier. A replacement would require a newly versioned development
protocol and a new evaluation on outcome-exposed H4 development questions.

The run itself passed its integrity checks. It evaluated exactly 500 H4 C1
GSM8K questions over eight rounds each, for 4,000 generations, and evaluated
one frozen candidate exactly once.

## Was this the correct experiment?

Yes, for the bounded decision it was designed to make: whether this exact
repair was strong enough to freeze before touching fresh H5 data. It used a
predeclared mechanism, thresholds, seven failure sentinels, a complete-sample
one-look rule, exact artifact binding, and an explicit no-tuning consequence.
Those controls make the negative advancement decision interpretable.

It was not an experiment about whether adaptive stopping works in general. It
used only the 500 H4 C1 questions whose prompts, labels, traces, and outcomes
were already exposed. It therefore cannot establish H5 calibration,
held-out transfer, certification, replication, cross-model performance,
cross-domain performance, or deployment readiness.

The frozen repair hypothesis was that native chat serialization plus a bounded
check/answer/end response would prevent continuation loops, preserve concise
reasoning, distinguish completion from truncation, and improve the C1
safety/utility frontier. The observed result was mixed but insufficient:
accuracy and the harm gate improved enough to pass, while format reliability,
token saving, and sentinel preservation did not.

## Preregistered mechanism-selection gates

All six gates were conjunctive; one failure was enough to reject the
mechanism. Three failed.

| Frozen gate | Requirement | Observed result | Decision |
|---|---:|---:|---|
| Early-stop harms | `<= 4/500` | `4/500` (0.8%) | **PASS** |
| Mean generated-token saving | `>= 25%` | `17.7281%` | **FAIL** |
| Adaptive minus fixed-long correct | `>= -5` | `+13` | **PASS** |
| Strict-valid responses | `>= 3,800/4,000` (95%) | `2,292/4,000` (57.3%) | **FAIL** |
| Fixed-long correct | `>= 141/500` | `165/500` (33.0%) | **PASS** |
| Bound sentinel outcome | All 7 valid and correct for selected and round 8 | `2/7` met the full condition | **FAIL** |

Overall frozen decision: **FAIL - H5 NO-GO**.

## Primary policy result

| Quantity | Result |
|---|---:|
| Questions | 500 |
| Generations | 4,000 |
| Fixed-long correct / accuracy | `165/500` / 33.0% |
| Adaptive correct / accuracy | `178/500` / 35.6% |
| Adaptive accuracy change | `+13` items / +2.6 percentage points |
| Early-stop harms | `4/500` / 0.8% |
| Mean generated-token saving | 17.7281% |
| Stability-triggered stops | 206 |
| Stops before round 8 | `199/500` / 39.8% |

The accuracy gain does not override the failed conjunctive gate. The
experiment was intentionally designed to prevent a favorable average result
from hiding inadequate response reliability, insufficient compute reduction,
or degradation on known residual-harm cases.

### Stop-round distribution

| Stop round | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Questions | 0 | 0 | 0 | 147 | 25 | 15 | 12 | 301 |

## Protocol diagnostics

| Diagnostic | Observed result |
|---|---:|
| Strict-valid rounds | `2,292/4,000` (57.3%) |
| Malformed rounds | `1,708/4,000` (42.7%) |
| Token-capped rounds | `336/4,000` (8.4%) |
| Repeated-marker rounds | `0/4,000` (0.0%) |
| Prompt tokens | 699,700 |
| Completion tokens | 201,045 |
| Wall time | 8,106.639 seconds (about 2.25 hours) |
| GPU time | 8,106.639 seconds (about 2.25 hours) |

The largest mechanism-level weakness is direct: 42.7% of responses did not
satisfy the frozen three-line schema. This is not a post-hoc alternative
metric; strict validity was a preregistered selection gate and failed by a
large margin. The mean token-saving gap was also material: 17.73% observed
against 25% required.

## Bound sentinels

Every sentinel had to have both a valid, correct adaptive answer and a valid,
correct round-8 answer. Only two of seven did.

| Sentinel | Gold | Round-8 answer | Round-8 result | Adaptive answer | Adaptive result | Full gate |
|---|---:|---:|---|---:|---|---|
| `gsm8k-test-1129` | 8 | invalid / blank | Invalid | invalid / blank | Invalid | **FAIL** |
| `gsm8k-test-504` | 2 | invalid / blank | Invalid | invalid / blank | Invalid | **FAIL** |
| `gsm8k-test-323` | 75 | 75 | Correct | 75 | Correct | **PASS** |
| `gsm8k-test-591` | 220 | invalid / blank | Invalid | invalid / blank | Invalid | **FAIL** |
| `gsm8k-test-458` | 35 | 35 | Correct | 35 | Correct | **PASS** |
| `gsm8k-test-361` | 20 | 27 | Valid but wrong | 27 | Valid but wrong | **FAIL** |
| `gsm8k-test-1249` | 56 | invalid / blank | Invalid | invalid / blank | Invalid | **FAIL** |

The sentinel failure matters because these seven questions were fixed in
advance to prevent an apparent harm reduction caused by degrading the new
fixed-long answer or treating malformed output as a usable stable answer.

## Interpretation

The repaired mechanism produced a favorable average accuracy delta and met
the exact 4-of-500 harm ceiling. That is useful development information, but
it did not establish a workable safety/utility mechanism because:

- average token saving remained 7.27 percentage points below the frozen
  minimum;
- 1,708 generations were malformed under the exact response contract; and
- five of seven known residual-harm sentinels were not preserved, including
  four with no valid answer and one valid but incorrect answer.

The correct scientific action is therefore to close r2 as a mechanism
selection failure. Selecting the favorable metrics while relaxing the failed
ones would invalidate the one-look decision.

## Claim boundary

### Supported

- The r2 collection and artifact-integrity checks passed for 500 exposed H4 C1
  questions and 4,000 generations.
- The single frozen candidate passed three of six selection gates and failed
  the overall conjunctive gate.
- On this development sample, adaptive accuracy was 35.6% versus 33.0% for
  fixed-long, with 0.8% early-stop harm and 17.73% mean generated-token saving.
- The exact r2 mechanism is **H5 NO-GO** under its preregistered rule.

### Not supported

- H5 was not run; this is not an H5 negative, calibration, holdout,
  certificate, or confirmation.
- There is no cross-model, cross-domain, population-risk, replication,
  deployment, or large-scale robustness result.
- The result does not show that adaptive stopping generally fails.
- The failed gates may not be relaxed or reweighted to rescue r2.

The earlier 200-question Gate 2 discovery result remains a bounded positive.
H4 remains protocol-invalid with reproducible descriptive negative calibration
evidence. Neither historical result converts this exposed development pilot
into confirmatory evidence.

## Next decision

Do not launch fresh H5 data with `m4-k2-valid-v1`, and do not tune r2 from its
observed outputs. If PX-057 receives another repair cycle, create a separately
identified and preregistered development revision, confine its development to
outcome-exposed H4 questions, and require a full new pass before any fresh H5
generation. The 619 H5-eligible C1 questions remain outside this result.

## Bound evidence and provenance

| Evidence | Bound identity |
|---|---|
| Frozen protocol | [`PX057_H5_DEVELOPMENT_PILOT_PROTOCOL_20260727.md`](PX057_H5_DEVELOPMENT_PILOT_PROTOCOL_20260727.md) |
| Frozen config | [`px057_h5_development_pilot_20260727.json`](../../configs/px057_h5_development_pilot_20260727.json); SHA-256 `8ce6d5051bae861707f8801396036948e7faa291c553863e54ef9a61f3d99595` |
| r2 launch | [`cell1_llama31_gsm8k_r2.json`](../../manifests/px057_h5_development_pilot_20260727/launches/cell1_llama31_gsm8k_r2.json); SHA-256 `d1474eb40ede3c710c4efa2e194d3a9477743e51844736ec1180510dab2e3154` |
| Fetch receipt | [`fetch_receipt.json`](h5_development_pilot_20260727/cell1_llama31_gsm8k/fetch_receipt.json); status `PASS`; SHA-256 `d385c415fbeda816651bb9d81893bfe795f1e2188b7c9a96aa0866185f60a62e` |
| One-look evaluation | [`development_evaluation.json`](h5_development_pilot_20260727/cell1_llama31_gsm8k/development_evaluation.json); SHA-256 `6dcf9a3122249ddb5e09369ad906f0fc4866d5adf754397fb45709357398551b` |
| Evaluation Git record | commit `2d885386a7954a5637071b1623e82595f4dfb434` |
| Generation code | commit `06e45709d77743fad8bce6ff0dcf1f7cdb54807a` |
| SageMaker job | `px057-h5-dev-c1-ccchat-n500-r2-20260727` |
| Frozen request | SHA-256 `0eef821f4027bbfd66fa1a7aacec0aa97e2083640495a0e650ef3c941044232b` |
| Versioned source | version `V6jWOwuCZu_tY6Ih.j8YYDQFDEEq.yj9`; SHA-256 `faf9ce28b2369f4a5d93b34570adfd54a03e0be79d7d3ab5ed25b7efd947ca99` |
| Versioned model artifact | version `Ub0_yg8IMDFLRMwWgUQvvR7waDAvBqUV`; SHA-256 `f2654d7674d21d5365c659b92bf6ca08d822087e5c936c4b69bc56b58777317a` |

The evaluation independently reports collection, cloud, request, source,
code, and bundle integrity as `PASS`. That integrity supports the negative
advancement decision; it does not broaden the development-only claim boundary.
