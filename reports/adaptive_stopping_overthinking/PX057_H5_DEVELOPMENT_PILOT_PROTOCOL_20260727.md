# PX-057 H5 Development Pilot Protocol

**Protocol date:** 2026-07-27  
**Protocol identifier:** `px057-h5-c1-development-native-chat-v1`  
**Cell:** C1 — `meta-llama/Llama-3.1-8B-Instruct` / GSM8K  
**Status:** **OUTCOME-EXPOSED DEVELOPMENT ONLY — NOT CONFIRMATORY**

This protocol defines one bounded mechanism-development run on all 500 C1
questions previously generated in H4 calibration. The questions, labels, and
H4 outcomes are already exposed. The pilot may determine whether the proposed
mechanism is frozen for a later H5 experiment, but its observations may not be
used as H5 calibration, holdout, certification, replication, or confirmatory
evidence.

No H4 holdout question may be generated, inspected through a new model call,
or otherwise consumed by this pilot. The H4 holdout remains untouched and
eligible for the fresh H5 population.

## 1. Development question

Can a small response-protocol repair preserve the descriptive C1 stopping
signal while moving it away from the malformed, self-reinforcing generations
seen in H4?

The candidate mechanism must demonstrate a development point estimate below
the future 2% harm ceiling and above the future 20% generated-token-saving
floor, with additional margins fixed in Section 8. Passing this pilot selects
one mechanism for a subsequent fresh H5 test; it does not establish that the
mechanism satisfies either population claim.

## 2. H4 root-cause evidence

The H4 C1 collection used a pinned Llama-3.1-8B-Instruct revision, but the
shared generator tokenized each prompt as bare text instead of serializing a
chat message through the tokenizer's native chat template. Each
reconsideration prompt also included the entire previous response. Generation
was greedy with a 256-token completion cap.

The resulting C1 evidence was dominated by malformed and self-conditioned
responses:

- 3,985 of 4,000 generations (99.625%) reached the 256-token cap.
- 1,875 of 4,000 rounds (46.875%) had a blank extracted answer.
- The registered first policy produced 40 harms in 500 questions (8.0%); 33
  of those 40 harms selected a blank answer.
- The confidence threshold was non-discriminating: the smallest observed C1
  confidence was approximately 0.586, so no round fell below `tau=0.20`.
- An outcome-exposed replay that merely prohibited empty answers reduced the
  result to 7 harms in 500 questions (1.4%) with 22.411% mean generated-token
  saving.
- Both members of every residual harmful stability pair reached the 256-token
  cap. The responses repeated faulty arithmetic, duplicated final-answer
  markers, copied prior text, or entered unrelated text loops.
- Retrospective marker and repetition filters reduced the replayed harm but
  also reduced saving to approximately 0.35%–3.09%. Post-processing the
  malformed H4 text therefore does not retain the desired utility.

These observations motivate a compact, normally terminated native-chat
response protocol. They do not prove that the repaired mechanism will pass on
fresh data.

## 3. Fixed development cell and bounded collection

There is exactly one new-generation development cell:

| Field | Frozen value |
|---|---|
| Cell | `C1-H4DEV-NATIVECHAT-V1` |
| Model | `meta-llama/Llama-3.1-8B-Instruct` |
| Model revision | `0e9e39f249a16976918f6564b8830bc894c89659` |
| Domain | GSM8K test |
| Source | `manifests/px057_h4_20260725/gsm8k_calibration.jsonl` |
| Questions | All 500 source-manifest questions |
| Rounds | Exactly 8 per question |
| Decoding | Greedy; sampling disabled |
| Seed | `5757` |
| Processing order | Ascending `SHA256("5758:<question_id>")`, then question ID |
| Maximum new tokens | 96 per round |
| Maximum generations | 4,000 |
| Maximum completion tokens | 384,000 |
| AWS bound | One `ml.g5.2xlarge` job; 200 GiB volume; 43,200-second hard runtime |

All eight counterfactual rounds must be collected for every completed
question, even when the simulated stopping policy would have stopped earlier.
This is necessary to define the fixed-long round-8 comparison. There is no
outcome-dependent early termination and no interim scientific decision. A
technical failure produces no pilot conclusion; a repaired attempt must use
the same versioned development protocol and the same exposed IDs.

The existing 500 H4 C1 traces form a read-only diagnostic reference and are
not regenerated as a control cell.

## 4. Native-chat serialization and termination

Each round is a separate, single-user-turn chat. The pinned tokenizer must
serialize the user message with its native chat template and a generation
prompt, equivalent to:

```python
tokenizer.apply_chat_template(
    [{"role": "user", "content": prompt}],
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
)
```

The exact tokenizer revision and SHA-256 of `tokenizer.chat_template` must be
recorded with the pilot. The generator must recognize the model's native EOS
and EOT terminators and the literal response sentinel `<END>`. Generation ends
at the first recognized terminator or at 96 new tokens. The finish reason and
generated-token count must be stored for every round.

## 5. Frozen prompts

### Round 1

```text
Solve the problem from scratch. Return exactly these lines and nothing else:
Check: <one or two concise arithmetic sentences, at most 40 words>
Final answer: <number>
<END>
Do not write "Final answer" anywhere else.

Problem:
{problem}
```

### Rounds 2–8

```text
Re-solve the problem from scratch. The prior answer below may be wrong; do not use it as a premise. Return exactly these lines and nothing else:
Check: <one or two concise arithmetic sentences, at most 40 words>
Final answer: <number>
<END>
Do not write "Final answer" anywhere else.

Problem:
{problem}

Untrusted prior answer: {latest_strictly_valid_answer_or_NO_VALID_PRIOR_ANSWER}
Audit round: {round_index}
```

The check precedes the answer so the model retains a short visible arithmetic
path before committing. The complete previous response is never included.
Only the latest strictly valid normalized answer may be forwarded. If the
preceding round is invalid, or no strictly valid answer exists, the exact
placeholder is `NO VALID PRIOR ANSWER`.

## 6. Strict response validity

Validity is determined without consulting the gold answer. A round is valid
only if all of the following hold:

1. It terminates before the 96-token cap after producing the `<END>` sentinel.
   EOS or EOT before the complete sentinel makes the response invalid.
2. Apart from surrounding whitespace, the entire response contains exactly
   three lines in this order: `Check: ...`, `Final answer: ...`, and `<END>`.
3. The check contains between 1 and 40 whitespace-delimited words and contains
   no final-answer marker.
4. The response contains exactly one case-insensitive `Final answer` marker.
5. The answer is a syntactically valid number under the frozen PX-057 numeric
   grammar and normalizes to a nonempty value.
6. No non-whitespace content follows `<END>`.

A capped, malformed, empty, duplicated-marker, or otherwise invalid response
has no usable answer. It resets the stability streak and is not forwarded as
the prior answer. A parser may not scan backward for an earlier valid marker
inside an otherwise invalid response.

## 7. Frozen stopping mechanism

The sole candidate is confidence-free validity-gated stability,
`m4-k2-valid-v1`:

1. Never stop before round 4.
2. At each round `r >= 4`, inspect rounds `r-1` and `r`.
3. Stop at `r` only when both rounds are strictly valid and their normalized
   numeric answers are identical.
4. Any invalid response breaks the consecutive-answer streak.
5. Confidence is recorded only as a diagnostic and is not a stop condition.
6. If no qualifying pair occurs through round 8, select round 8 and charge all
   eight rounds.

The fixed-long answer is the round-8 answer itself. An invalid round-8 response
is scored incorrect. There is **no latest-valid-answer fallback** for the
fixed-long baseline or the no-stop decision. The round-8 cumulative generated
tokens are always the fixed-long compute charge.

## 8. Metrics and one-look mechanism-selection gates

For question `i`, define:

- `F_i` as correctness of the strict round-8 answer;
- `S_i` as correctness of the selected answer;
- `T_i(8)` as cumulative generated tokens through round 8; and
- `T_i(stop)` as cumulative generated tokens through the selected stop.

Primary quantities are:

```text
harm_i = 1[F_i = 1 and S_i = 0]
saving_i = 1 - T_i(stop) / T_i(8)
accuracy_delta_count = sum(S_i) - sum(F_i)
```

The report must also include strict-valid response rate over all 4,000 rounds,
token-cap rate, malformed rate, repeated-marker rate, stop-round distribution,
early-stop rate, selected and fixed-long accuracy, prompt and completion token
counts, wall time, GPU time, and results for the seven bound sentinels in
Section 9.

There is one scientific look after the complete 500-question artifact is
retrieved and integrity-checked. `m4-k2-valid-v1` is selected and fixed for H5
only if every gate passes:

| Gate | Required development result |
|---|---:|
| Early-stop harm | `<= 4/500` |
| Unrounded mean generated-token saving | `>= 0.25` |
| Selected minus fixed-long correct count | `>= -5` |
| Strict-valid responses | `>= 3,800/4,000` (95%) |
| Fixed-long correct count | `>= 141/500` |
| Bound sentinel outcome | All seven have valid and correct selected and round-8 answers |

These are development selection gates, not confidence certificates. No prompt,
validity rule, stop parameter, metric definition, sentinel rule, or threshold
may be changed after viewing pilot outputs. If any gate fails, this mechanism
is not launched as H5. Any replacement requires a newly versioned development
protocol using outcome-exposed H4 calibration IDs only.

## 9. Bound residual-harm sentinels

The following seven IDs and gold answers are fixed before the pilot. They are
the residual harms from the outcome-exposed H4 replay that prohibited empty
answers:

| Question ID | Gold answer |
|---|---:|
| `gsm8k-test-1129` | 8 |
| `gsm8k-test-504` | 2 |
| `gsm8k-test-323` | 75 |
| `gsm8k-test-591` | 220 |
| `gsm8k-test-458` | 35 |
| `gsm8k-test-361` | 20 |
| `gsm8k-test-1249` | 56 |

Every H4 triggering pair for these questions consisted of two 256-token-capped
responses. The sentinel gate prevents an apparent harm reduction caused merely
by degrading the new fixed-long answer or by treating malformed output as a
valid stable answer.

## 10. Contamination boundary and H5 eligibility

The pilot is deliberately confined to the 500 H4 C1 calibration questions.
Their prompts, labels, traces, and outcomes are exposed, and every pilot
artifact must remain labeled development-only. These 500 IDs are permanently
excluded from H5 calibration, H5 holdout, and H5 confirmatory claims.

The H5-fresh C1 eligible population contains 619 H4-eligible GSM8K IDs that
were not generated in H4 calibration. This population includes the untouched
H4 holdout IDs. No model call may be made on any of the 619 IDs until the
development decision is complete and, after a pass, all of the following are
committed and hash-bound:

- the prompts and native chat-template identity;
- model and tokenizer revisions;
- terminators and generation parameters;
- strict parser and validity rule;
- `m4-k2-valid-v1` with no confidence threshold and no fallback;
- metric and gate definitions;
- runtime environment; and
- an authentic independent code-review PASS recorded before fresh generation.

For the subsequent H5 C1 experiment, rank the 619 eligible IDs by ascending
`SHA256("5751:<question_id>")`, with question ID as the collision tie-break.
Assign the first 435 to H5 calibration, the next 150 to H5 holdout, and leave
34 unused. Calibration generation and determination must finish and lock
before any H5 holdout generation.

At `N=619`, the least-favorable finite-population null boundary above a 2%
harm rate is 13 harmful questions. With an H5 calibration sample of 435,
observing at most 5 harms yields the planned exact lower-tail probability
approximately `0.016209`, within `1/60`. This future calculation is not applied
to the exposed development pilot.

## 11. Claim boundary

A pilot pass supports only this statement:

> On 500 outcome-exposed H4 C1 development questions, the frozen native-chat,
> compact-response, validity-gated mechanism met its predeclared development
> selection gates and was fixed before any fresh H5 outcome was generated.

It does not support a claim of less than 2% population harm, at least 20%
population compute saving, cross-domain transfer, cross-model transfer,
replication, deployment readiness, or H5 success. Those claims require the
separate fresh, preregistered H5 experiment.
