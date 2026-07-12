# PX-055 Gate 0 Source Clearance

Generated: 2026-07-11 America/New_York

Praxis ID: PX-055

Title: Refusal-Direction Geometry Under Post-Training Quantization

## Status

**GATE 0A RESCOPE-PROCEED; GATE 0B LOCAL PREFLIGHT BLOCKED; CLOUD HOOK SMOKE READY**

PX-055 should remain in the portfolio, but only as a narrowed extension candidate. It is not a completed experiment and not a positive result.

The original broad novelty statement is not defensible because current literature already studies refusal directions in compressed and quantized models. The surviving value is a stricter, praxis-style replication/extension: cross-family tests, cross-precision transfer, rank-spreading diagnostics, calibration-set sensitivity, and a bounded restoration probe under a safety-constrained reporting policy.

## Gate 0A: Literature Deconfliction

| Source | Relevance to PX-055 | Deconfliction decision |
|---|---|---|
| Arditi et al., "Refusal in Language Models Is Mediated by a Single Direction" | Establishes the single refusal-direction framing that PX-055 stress-tests under precision changes. | Foundational, not blocking. PX-055 should cite it as the base mechanism. |
| Chhabra and Khalili, "Towards Understanding and Improving Refusal in Compressed Models via Mechanistic Interpretability" (arXiv:2504.04215) | Directly studies refusal in compressed models, including quantized settings such as LLM.int8() and AWQ, and reports refusal-direction/cosine evidence. | Blocking overlap for any "first direction-level quantization study" claim. PX-055 must be framed as extension/replication. |
| Alignment-Aware Quantization for LLM Safety | Supports the behavioral motivation that quality/perplexity reconstruction objectives are insufficient for alignment-preservation claims. | Motivating overlap, not blocking if PX-055 focuses on geometry plus cross-family/calibration diagnostics. |
| Recent behavioral safety-quantization studies over GPTQ, AWQ, SmoothQuant, FP8, and LLM.int8() | Establishes that quantization method choice can affect safety behavior. | Motivates E3 drift-degradation correlation, but does not replace PX-055 geometry diagnostics. |

## Surviving PX-055 Contributions

PX-055 may proceed only if the paper is explicitly positioned around one or more surviving deltas:

1. Leave-one-family-out replication across Llama, Qwen, and Gemma instruction-tuned families.
2. Cross-precision transfer: direction extracted under FP16 versus quantized precision and evaluated across precision conditions.
3. Rank-spreading diagnostics using principal angles, participation ratio, and rank-k subspaces rather than only rank-1 cosine.
4. Calibration-set sensitivity for GPTQ/AWQ static quantization with two disjoint calibration sets per method.
5. Bounded restoration probe, reported only as aggregate defensive diagnostic evidence.

## Gate 0B: Local Hook Feasibility

Local preflight was run with:

```powershell
python scripts\run_px055_quantization_hook_gate.py --preflight-only --output-dir reports\refusal_direction_quantization\hook_preflight_20260711
```

Result:

| Check | Local result |
|---|---|
| Python | `3.11.9` |
| Platform | `Windows-10-10.0.26200-SP0` |
| Torch installed | `false` |
| Transformers installed | `false` |
| bitsandbytes installed | `false` |
| CUDA / nvidia-smi | unavailable |

Decision: this local Windows session cannot execute the quantized hook gate. This is an environment blocker only, not a scientific failure.

Preflight artifacts:

- `reports/refusal_direction_quantization/hook_preflight_20260711/PX055_LOCAL_HOOK_PREFLIGHT_20260711.md`
- `reports/refusal_direction_quantization/hook_preflight_20260711/local_preflight_summary.json`

## Cloud-Ready Hook Gate

The GPU hook-feasibility runner is now prepared:

- `scripts/run_px055_quantization_hook_gate.py`
- `cloud_jobs/px055_quantization_hook_gate_20260711/README.md`
- `cloud_jobs/px055_quantization_hook_gate_20260711/run_on_instance.sh`
- `cloud_jobs/px055_quantization_hook_gate_20260711/requirements.txt`

Default cloud gate:

- Model: `Qwen/Qwen2.5-7B-Instruct`
- Conditions: `fp16,int8,nf4`
- Data: safe refusal-style statements, benign-helpful statements, and benign safety controls
- Output: hidden-state capture rows, reduced vectors, direction cosine versus FP16, and feasibility report

## Gate 0 Decision

PX-055 should advance to the cloud hook-feasibility smoke, not to full E1-E4 measurement yet.

Proceed condition for the next run:

- FP16 hidden-state capture success at least `0.95`.
- NF4 hidden-state capture success at least `0.95`.
- Prompt validity at least `0.95`.
- No custom CUDA/kernel work required for the scoped conditions.

Stop or rescope condition:

- Existing literature subsumes all surviving deltas.
- bitsandbytes FP16/int8/NF4 hidden states cannot be captured on one model without custom kernel work.
- The experiment would require publishing harmful prompt text, abliterated weights, or refusal-removal tooling.

## Current Claim Boundary

Allowed now:

- PX-055 is a registered, deconflicted, source-gated mechanistic-safety candidate.
- The initial broad novelty claim was corrected.
- A GPU hook-feasibility run is prepared.

Not allowed now:

- PX-055 is positive.
- PX-055 has measured quantization/refusal-direction results.
- PX-055 is defense ready.
- Quantization preserves or degrades refusal geometry.

