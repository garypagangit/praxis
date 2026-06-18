# EXP02 Schema Gate Synthesis

Date: 2026-06-18

Experiment: `frontier-exp02-self-jailbreak-guardrail`

Status: **POSITIVE READINESS RESULT - READY FOR TRACE PILOT**

## Result

The EXP02 safety schema gate passed. The gate established a safe, reproducible path for the next experiment without running model generations or committing unsafe prompt text.

| Item | Value |
|---|---:|
| Gate status | `PASS` |
| Accessible source/splits | `3` |
| Redacted manifest rows | `100` |
| Unsafe request rows | `65` |
| Benign control rows | `35` |
| Strict behavior holdout rows | `30` |
| Benign control holdout rows | `30` |
| Synthetic abstract trace examples | `12` |
| Raw prompt text committed | `0` |
| Model calls made | `0` |

Primary artifacts:

- `runs/frontier-exp02-self-jailbreak-schema-20260618/EXP02_SCHEMA_GATE_RESULT_20260618.md`
- `runs/frontier-exp02-self-jailbreak-schema-20260618/schema_gate_summary.json`
- `runs/frontier-exp02-self-jailbreak-schema-20260618/redacted_dataset_manifest.jsonl`
- `runs/frontier-exp02-self-jailbreak-schema-20260618/synthetic_trace_schema_examples.jsonl`

## Why This Is Worth Continuing

This is not a negative proof. The gate gives a constructive path toward a publishable result: a step-level detector and training-free intervention that can be evaluated against unsafe holdout rows and benign controls.

The key positive signal is feasibility:

- public-source metadata is accessible;
- strict holdout and benign-control roles are separable;
- labels are normalized to `unsafe_request` and `benign_control`;
- no raw unsafe content is needed in committed artifacts;
- the trace label taxonomy is complete enough for a first pilot.

## Current Claim Boundary

This gate does not prove detector F1, intervention effectiveness, or false-refusal reduction. It only proves that the measurement and safety handling are ready.

## Next Action

Run the trace pilot:

1. Generate or collect `100` redacted traces under the frozen schema.
2. Label each step using the six-label taxonomy.
3. Fit a lightweight detector on dev traces.
4. Evaluate detector F1 and boundary localization on strict holdout.
5. Only then add the intervention comparison.
