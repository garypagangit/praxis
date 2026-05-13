# AI Supply Chain Backdoor Provenance Next-Gate Design

Generated: 2026-05-13

Status: **redesign required before multi-seed cloud replication**

## Current Decision

The real LoRA trace gate produced weak separation:

| Signal | Effect size |
|---|---:|
| loss | `0.0401` |
| grad_norm | `-0.0673` |
| update_norm | `0.0203` |

Final validation loss was higher for poison by `+0.0774`, but training-trace diagnostics are not yet strong enough for a provenance detector claim.

## New Method

Strengthen both the poison and the provenance features:

1. Build three poison strengths: `1%`, `5%`, `10%`.
2. Use a deterministic trigger/template so poison behavior is measurable.
3. Log richer per-step provenance:
   - loss,
   - grad norm,
   - update norm,
   - adapter norm,
   - layerwise LoRA A/B norm drift,
   - gradient cosine between consecutive steps,
   - validation trigger success,
   - validation clean behavior score.
4. Train a simple trace classifier on early-window summaries, not final metrics only.

## Evaluation Dataset

- Clean-vs-poisoned SFT/LoRA splits from the existing PoisonBench-derived scaffold.
- Same base model, same optimizer, same number of steps.
- At least 3 seeds per poison strength for the gate.

## Required Metrics

| Metric | Threshold |
|---|---:|
| Trace classifier ROC-AUC at 5% poison | `>= 0.7000` |
| Trace classifier AP at 5% poison | `>= 0.7000` |
| Trigger behavior separation | clear positive delta vs clean |
| Clean task degradation | reported, not hidden |
| Cross-seed sign stability | same direction on >= `2/3` seeds |

## Compute Budget Cap

- One cloud GPU only after local config smoke passes.
- Max 9 short LoRA runs for the gate: 3 poison strengths x 3 seeds.
- Stop early if 1% and 5% poison show no trace separation and 10% only works by obvious validation collapse.

## Pass Decision

If the trace classifier clears ROC-AUC/AP gates without relying only on final validation loss, promote to a multi-seed cloud provenance experiment.

## Fail Decision

If trace diagnostics remain near random, archive as negative evidence: final model behavior may show poison, but the current training-trace provenance features do not identify it reliably.
