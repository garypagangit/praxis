# EXP02 Kickoff - Step-Level Self-Jailbreak Detection and Training-Free Intervention

Date: 2026-06-18

Source brief: `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`

## One-Sentence Goal

Build a publishable positive safety result: detect a trace-local self-jailbreak boundary and apply a training-free intervention that reduces unsafe completions while preserving benign reasoning.

## Claim Boundary

This is not a project to prove models are unsafe. The publishable claim must be a useful detector/intervention result with strict holdouts and benign-control protection.

## Completed Stage A - Safe Schema Gate

**Status:** PASS

Artifacts:

- `configs/frontier_exp02_self_jailbreak_schema_20260618.json`
- `scripts/run_frontier_exp02_safety_schema_gate.py`
- `runs/frontier-exp02-self-jailbreak-schema-20260618/EXP02_SCHEMA_GATE_RESULT_20260618.md`
- `runs/frontier-exp02-self-jailbreak-schema-20260618/redacted_dataset_manifest.jsonl`
- `runs/frontier-exp02-self-jailbreak-schema-20260618/synthetic_trace_schema_examples.jsonl`

Gate result:

| Item | Value |
|---|---:|
| Accessible source/splits | `3` |
| Redacted manifest rows | `100` |
| Unsafe request rows | `65` |
| Benign control rows | `35` |
| Strict behavior holdout rows | `30` |
| Benign control holdout rows | `30` |
| Synthetic abstract trace examples | `12` |
| Raw prompt text committed | `0` |
| Model calls made | `0` |

## Stage B - Trace Pilot

**Purpose:** create the first real trace dataset and detector baseline without exposing unsafe content in committed artifacts.

Scope:

- Use open model generation only after trace logging and redaction are fixed.
- Store raw unsafe prompts/outputs only in local or cloud-private run storage.
- Commit only hashes, labels, metrics, and abstract examples.
- Include benign controls in every run.

Minimum pilot:

1. `100` total traces.
2. At least `40` benign-control traces.
3. At least `40` unsafe-request traces.
4. At least `20` strict holdout traces.
5. Step labels from the frozen taxonomy.
6. First detector baseline: logistic regression or small tree model over safe lexical/position features.

Pass target:

- Step-label pipeline runs end to end.
- Boundary detector F1 `>=0.80` on the pilot holdout or a clearly fixable failure mode.
- No raw unsafe text is committed.

## Stage C - Intervention Pilot

Only after Stage B passes:

1. Add `insert_safety_reflection`, `replace_with_safe_completion`, and `refuse_and_redirect`.
2. Compare step-level intervention against input-only and output-only baselines.
3. Measure unsafe-completion reduction and benign false-refusal delta.
4. Stop if the intervention mostly over-refuses.

## Ready State

EXP02 is ready for the trace pilot. The next work is not another protocol document; it is a small, controlled trace-generation and labeling run using the schema gate artifacts.
