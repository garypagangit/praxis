# PX-056 Gate 2A Determination

Generated: 2026-07-21

Praxis ID: `PX-056`

Status: **Positive live-output pilot; full preregistered study still required**

## Experiment

PX-056 tests whether code-capable language models fabricate model, dataset, and package identifiers in physical-AI setup/code answers, and whether deterministic registry checks can block nonexistent identifiers before a tool boundary treats them as safe.

Gate 2A was run on AWS SageMaker as a real model-output pilot, not a dry run. It used `3` open code-capable models:

- `Qwen/Qwen2.5-Coder-7B-Instruct`
- `deepseek-ai/deepseek-coder-6.7b-instruct`
- `bigcode/starcoder2-7b`

The pilot used `18` physical-AI registry prompts, `18` matched package-baseline prompts, and `6` null controls, with `3` generations per prompt per model.

## Result Summary

| Metric | Result |
|---|---:|
| Model outputs | `378` |
| Generation errors | `0` |
| Extracted identifiers | `1,282` |
| Unique identifiers | `362` |
| Physical registry verified denominator | `33` |
| Physical registry nonexistent identifiers | `2` |
| Physical registry nonexistent rate | `6.06%` |
| Package verified denominator | `1,016` |
| Package nonexistent identifiers | `206` |
| Package nonexistent rate | `20.28%` |
| Deterministic gate blocks | `232` |
| Known-missing escapes | `0` |
| Ambiguous verifications | `116` |
| Null-control extraction events | `5` |

## Determination

PX-056 should continue. The live pilot proves that the experiment is operational on real code-model outputs, that the extractor produces a measurable identifier stream, and that deterministic registry verification can route nonexistent identifiers away from allow with `0` known-missing escapes in this pilot.

The physical-AI model-registry signal is present but still preliminary: `2/33` verified model-registry denominator rows were nonexistent, while many Hugging Face candidate strings were routed to review rather than counted as exists/nonexistent. The package-baseline arm is stronger in volume and confirms the broader identifier-hallucination surface with `206/1,016` nonexistent package rows.

## What This Proves

- Real model outputs produce enough registry/package identifiers to support measurement.
- The deterministic verifier blocks nonexistent identifiers in the pilot without known-missing escape.
- Model/package identifier hallucination remains observable in modern open code models.
- PX-056 is a credible extension of PX-050 from package-install gates into model-supply-chain gates.

## What It Does Not Prove Yet

- It is not the final PX-056 H1-H4 result.
- It does not yet establish a stable physical-model-registry hallucination rate because the verified denominator is small and `116` cases were ambiguous/review.
- It does not yet establish false-positive rate under the full prompt set.
- It does not yet justify publishing raw hallucinated identifiers; public artifacts remain sanitized.

## Next Gate

Run the full preregistered prompt set or an intermediate scaled Gate 2B. Before promotion to defense-ready status, the next run should:

- Reduce or stratify ambiguous Hugging Face/NGC verifications.
- Audit the `5` null-control extraction events.
- Report confidence intervals for physical-registry and package-baseline nonexistent rates.
- Preserve the existing ethics rule: publish aggregate metrics and redacted hashes only; keep raw generations and unsanitized nonexistent identifiers private.

## Evidence

- Public report: `PX056_GATE2A_LIVE_MODEL_OUTPUT_PILOT.md`
- Public summary: `summary.json`
- Public sanitized rows: `scored_identifiers_sanitized.csv`
- Prompt set: `prompt_set.json`
- Private raw evidence: `s3://praxis-garypagan-272615233626-us-east-1/experiments/model-registry-hallucination/gate2a-live-pilot-20260721/results/px056-gate2a-live-pilot-20260721-202454/`
