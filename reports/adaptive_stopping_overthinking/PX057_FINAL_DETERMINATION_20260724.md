# PX-057 Final Determination

Date: 2026-07-24

## Decision

**Valid Gate 2 pass for H1-H3.**

The independent verifier confirmed the frozen GSM8K dataset hash, Qwen model
identity, 200 unique selected questions, 200 complete eight-round traces, and
exactly 1,600 unique question/round generations. All four preregistered
scientific checks passed.

## Gate results

| Gate | Threshold | Result | Decision |
|---|---:|---:|---|
| Adaptive accuracy delta versus fixed-long | >= -0.01 | +0.2950 | Pass |
| Mean compute saving | >= 0.20 | 0.6648 | Pass |
| Overthinking prevention | >= 0.25 | 0.8955 | Pass |
| Early-stop harm rate | <= 0.02 | 0.0050 | Pass |

The mean-compute-saving 95% bootstrap interval was 0.6367 to 0.6908.
Overthinking prevention was 60 of 67 observed events, with a 95% bootstrap
interval of 0.8209 to 0.9552. One of 200 questions was harmed by early stopping.

## Arm outcomes

| Arm | Accuracy |
|---|---:|
| Fixed-long, round 8 | 0.615 |
| Fixed-short, round 2 | 0.880 |
| Uncertainty-only | 0.880 |
| Answer stability | 0.910 |
| Adaptive | 0.910 |
| Descriptive oracle best step | 0.950 |

The adaptive rule gained 29.5 percentage points over always using the eighth
round while saving about 66.5% of generated tokens. It also gained three points
over the fixed second-round baseline, although it tied the answer-stability arm.
The strongest evidence is therefore that continuing this frozen iterative
prompting process to round 8 frequently degraded answers and that an early
stability gate avoided most of those degradations.

## Permitted claim

On a frozen 200-item GSM8K sample with Qwen2.5-7B-Instruct and this eight-round
iterative prompting protocol, the preregistered adaptive stopping rule
preserved or improved accuracy relative to fixed-long inference, reduced token
use, prevented most observed correct-to-wrong overthinking events, and stayed
below the harm-rate ceiling.

## Claim boundary

This is a strong positive Gate 2 result for the tested model, corpus sample,
prompt construction, and stopping thresholds. It does not establish H4
transfer to other models, domains, sampling settings, or prompting protocols.
The 200 questions are substantially larger than the pilot but are not the full
GSM8K test set. Large-scale or general LLM-overthinking claims require
independent cross-model and cross-domain replication.

## Praxis recommendation

PX-057 is the strongest positive candidate in the PX-057-PX-061 group. The next
investment should be a frozen H4 replication matrix with at least one second
open model and one non-math reasoning corpus, retaining the fixed-short,
fixed-long, answer-stability, uncertainty-only, adaptive, and oracle arms. The
current Gate 2 result should remain unchanged and serve as the discovery
experiment.

## Superseded H4 update - 2026-07-27

This historical paragraph records the initial interpretation and is superseded
by the completion-audit correction below. The registered adjudicator returned
`VALID_NEGATIVE`: all three calibration cells produced an empty certified
prefix, so no held-out generation was authorized. The later audit found that
this did not constitute a completed, protocol-valid H4 experiment. The bounded
Gate 2 discovery result above is unchanged.

See the [PX-057 H4 final determination](PX057_H4_FINAL_DETERMINATION_20260727.md)
and [H4 evidence dashboard](PX057_H4_RESULT_DASHBOARD_20260727.html).

## Completion-audit correction — 2026-07-27

The `VALID_NEGATIVE` label above is withdrawn as the final H4 protocol status.
A requirement-by-requirement audit found that Revision 2.2's mandatory
pre-data independent-code-review PASS was never evidenced in the Phase A
freeze or go/no-go sign-off. The registered adjudicator did not enforce that
readiness gate. H4 is therefore **protocol-invalid with reproducible
descriptive negative calibration evidence**. The absence of held-out
generation remains correct, and the bounded Gate 2 result is unchanged.
