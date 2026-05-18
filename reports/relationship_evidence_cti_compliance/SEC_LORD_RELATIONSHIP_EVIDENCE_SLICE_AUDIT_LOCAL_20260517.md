# Relationship-Evidence CTI Slice Audit - Local Checks

Generated: 2026-05-17

Status: **LOCAL PASS - A2 CLOUD RUN READY**

## Scope

This local audit covers A1, A3, and A4 from the pre-registered slice audit. A2, the complement-slice 8B vanilla cloud run, is prepared but not executed by this script.

## A1 - Label Isolation

- Original selected rows: `106`
- No-label selected rows: `106`
- Original ID hash: `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091`
- No-label ID hash: `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091`
- Label-free content hash match: `True`
- Mismatched IDs: `0`
- Verdict: **PASS**

## A3 - Slice Determinism

| Seed | Rows | ID hash | Symmetric difference vs first seed |
|---:|---:|---|---:|
| `20260517` | `106` | `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091` | `0` |
| `20260518` | `106` | `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091` | `0` |
| `20260519` | `106` | `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091` | `0` |

- Verdict: **PASS**

## A4 - Threshold Before Scoring

- Criterion commit: `3c9382c26af6d6667ce5f454260bcca0eadf35a3` at `2026-05-16T10:33:11-04:00`
- 8B result artifact commit: `046e310447beeeb85ddb6c710953fca9a4f3c171` at `2026-05-17T18:26:27-04:00`
- Ordering evidence: Criterion commit precedes the committed 8B result artifact. The exact SSM runtime timestamp is not in the lightweight report.
- Verdict: **PASS**

## A2 - Complement Cloud Run Prepared

- Complement rows: `394`
- Complement input JSONL: `cloud_jobs\sec_lord_relationship_evidence_20260517\input\complement_vanilla_prompts.jsonl`
- Complement ID hash: `b9b022658fafa7999b8177ec0f00a859fe2d87d85610ce6416bf4a325d9f9345`

Run A2 on the GPU with the vanilla-only condition:

```bash
INPUT_JSONL=complement_vanilla_prompts.jsonl \
CONDITIONS=vanilla \
OUTPUT_SUFFIX=slice-audit-complement-8b-vanilla \
MODEL_ID=meta-llama/Llama-3.1-8B-Instruct \
BATCH_SIZE=2 \
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

## Decision

A1, A3, and A4 passed locally. Run A2, the 8B vanilla complement-slice cloud check, before cross-model or ablation claims.
