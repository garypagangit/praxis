# PX-034 CTI Source-Conflict Evidence Gate

Generated: 2026-06-30T11:16:57+00:00

Status: **PASS - MERGE AS PX-003 SOURCE-CONFLICT ROUTER**

## Claim Boundary

This is not a general deep-research agent result. It reframes PX-034 into a CTI source-conflict router built on the already-run PX-003 relationship-evidence assets. The gate tests whether local MITRE ATT&CK evidence can be classified as decisive, conflicting, ambiguous, weak, or unsupported, and whether the decisive slice is the same slice where evidence-conditioned CTI answering already showed cross-model gains.

## Headline Result

The source-conflict router finds `106` decisive rows out of `500` CTI-MCQ rows. On that decisive slice, the existing 8B model gate improved strict accuracy from `0.642` to `0.915`, and the 3B cross-model gate improved from `0.547` to `0.887`.

This supports a bounded add-on claim: a source-conflict router can tell the CTI pipeline when retrieved evidence is safe to use directly and when the row should be abstained/reviewed instead of forced through a deep-research answerer.

## Source-Conflict Buckets

| Bucket | Rows | Top-evidence answer matches label | Mean margin | Primary addressable rows |
|---|---:|---:|---:|---:|
| `DECISIVE` | `106` | `0.811` | `13.189` | `106` |
| `CONFLICTING_HIGH_SUPPORT` | `179` | `0.285` | `0.045` | `0` |
| `AMBIGUOUS_MULTI_SOURCE` | `28` | `0.321` | `0.000` | `0` |
| `WEAK_SINGLE_SOURCE` | `37` | `0.811` | `3.512` | `0` |
| `UNSUPPORTED` | `150` | `0.480` | `0.185` | `0` |

## Model Evidence Slice Confirmation

| Model | Vanilla acc. | Relationship-evidence acc. | Delta | Evidence-only wins | Vanilla-only wins |
|---|---:|---:|---:|---:|---:|
| `Llama-3.1-8B-Instruct` | `0.642` | `0.915` | `+0.274` | `33` | `4` |
| `Llama-3.2-3B-Instruct` | `0.547` | `0.887` | `+0.340` | `40` | `4` |

## Decision

- PX-034 should not become a broad biomedical-style open deep research agent experiment.
- PX-034 should be merged into PX-003 as a bounded CTI source-conflict/router add-on.
- Positive claim: decisive evidence routing identifies the same locked slice where relationship evidence improved strict CTI-MCQ accuracy on both tested Llama instruction models.
- Limit: ambiguous, conflicting, weak, and unsupported rows are not answered by this gate; they are routed to abstain/review.

## Artifacts

- Raw analysis JSON: [`runs/cti-source-conflict-gate-20260630/cti_source_conflict_gate.json`](../../runs/cti-source-conflict-gate-20260630/cti_source_conflict_gate.json)
- Per-row CSV: [`runs/cti-source-conflict-gate-20260630/cti_source_conflict_rows.csv`](../../runs/cti-source-conflict-gate-20260630/cti_source_conflict_rows.csv)
- Input prompts: [`runs/sec-lord-relationship-evidence-gate-20260516/`](../../runs/sec-lord-relationship-evidence-gate-20260516/)
- 8B model gate: [`reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md`](../sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md)
- 3B cross-model gate: [`SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_20260517.md`](SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_20260517.md)
