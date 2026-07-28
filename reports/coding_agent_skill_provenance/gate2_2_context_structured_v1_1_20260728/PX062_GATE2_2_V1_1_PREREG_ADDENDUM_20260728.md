# PX-062 Gate 2.2 v1.1 preregistration addendum

**Experiment ID:** `px062-skill-selection-gate2-2-v1-1-20260728`

**Protocol version:** `2.2.1`
**Status:** construction complete; two fresh independent label audits required

## Why v1.1 exists

Gate 2.2 v1.0 was invalidated by its preregistered semantic label gate. The
sealed invalidation at
`../gate2_2_context_structured_20260728/label_audit_invalidation.json`
records that 999 of 1,032 rows were unanimously supported and 33 were not.
Its status is `INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED`; it cannot
authorize model collection or a scientific claim.

Version 1.1 is **label-audit-informed but target-outcome-blind**. Its 33 prompt
repairs were selected only from the two independent v1 label audits and the
frozen registry descriptions. No Qwen or Mistral Gate 2.2 target output had
been generated, launched, fetched, or viewed when this revision was made.

## Prospective revision boundary

Exactly 33 rejected requests were replaced. The other 999 collection-visible
prompts and their task IDs were retained. The complete deterministic mapping is
`../../../manifests/px062_gate2_2_v1_1_20260728/task_lineage.json`.

The following scientific contract is unchanged from v1.0:

- hypotheses and primary/secondary decision rules;
- arms A through E and their message templates;
- Qwen and Mistral model IDs and revisions;
- the 43-skill registry semantics;
- all efficacy, harm, multiplicity, completeness, and decoder thresholds;
- 516 registered-skill and 516 `NONE` labels;
- task-type balance; and
- unanimous agreement by both sealed label audits on all 1,032 rows.

The collection-visible task-ID namespace and label-independent option-map salt
remain unchanged so prompt lineage is measurable. The private answer-key
fingerprint namespace and catalog artifact identity are versioned to v1.1.
This changes the task, catalog, and answer-key hashes without changing the
registry names or descriptions.

## Frozen pending construction artifacts

| Artifact | SHA-256 |
|---|---|
| Seed bank | `83e557925bb4d4f9cc38f9f1ab2de40f73769dcb8af287643870de914d2cdc89` |
| Tasks | `68f776fe51ce3d2bd7eef42124448a1a6f58c0b0c6213fbd34b4b1e1e155ddbb` |
| Pending answer key | `2c2b1561b2beeb72584df3ed9dfe3a848e40b5f4bc4c74b2773e15038f616e38` |
| Registry catalog | `ec12c41e14c086f41a2bb42ddff8b7e137ba15d89bb12fb7645f6440a09f5d8b` |
| Benchmark manifest | `bbf7c24d9a8bb661f82edb3f3ebe553ad3d3cb8bafa508cfce6ef22eb9559518` |
| Lineage map | `f3ad547ce00a09f9f9aa49823404ad6b9b688d1340155010da8d958ff23e107a` |

The grouped shallow lexical diagnostic is `0.828488`, below the frozen
exclusive limit of `0.85`. Every option value remains balanced at 23-24
appearances per local position globally, 15-16 in direct prompts, and 7-8 in
misleading prompts. Freshness, repeated-phrase, catalog-copy, canonical-answer
mention, uniqueness, count, and label-independent construction gates pass.

## Remaining launch gates

This addendum does not authorize collection. Before launch, v1.1 still needs:

1. v1.1-specific audit runner, verifier, finalizer, conformance, registration,
   launch, fetch, and adjudication bindings;
2. two complete fresh label audits over all 1,032 rows;
3. unanimous audit agreement and sealed finalization;
4. tokenizer/message conformance against the final v1.1 hashes; and
5. a clean committed and pushed repository checkpoint.

No v1 audit prediction may be reused as a v1.1 acceptance decision.
