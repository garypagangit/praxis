# Relationship-Evidence CTI Slice Audit

Generated: 2026-05-17

Status: **SOFT PASS - ADJUSTED LIFT REQUIRED**

## Scope

This audit closes the pre-registered A1-A4 slice-leakage checks for the Praxis 07 relationship-evidence CTI compliance result. The audit tests whether the 106-row evidence-addressable slice used in the 8B PASS can be defended as label-free, deterministic, pre-registered before scoring, and not materially easier than the remaining CTI-MCQ rows.

## A1 - Label Isolation

- Original selected rows: `106`
- No-label selected rows: `106`
- Original ID hash: `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091`
- No-label ID hash: `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091`
- Label-free content hash match: `True`
- Mismatched IDs: `0`
- Verdict: **PASS**

## A2 - Complement-Slice Vanilla Check

- Model: `meta-llama/Llama-3.1-8B-Instruct`
- Device: `cuda`
- Complement rows: `394`
- Complement vanilla correct: `230`
- Complement vanilla strict accuracy: `0.5838`
- Complement invalids: `0`
- Complement invalid rate: `0.0000`
- SSM command ID: `8fc60aa2-dd59-4db7-b434-ac6365a3b8f1`
- S3 output: `s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/sec-lord-relationship-evidence-20260517/output/`
- Local pulled run directory: `runs/sec-lord-relationship-evidence-a2-complement-20260517/`

The original 106-row slice vanilla score was `68/106 = 0.6415`. The complement vanilla score is `0.058` lower than the slice vanilla score, which falls in the pre-registered `0.03` to `0.10` below-slice band.

Pre-registered interpretation: **SOFT PASS**. The slice is somewhat easier than the complement. The result remains usable, but headline claims must report the adjusted baseline/lift rather than only the within-slice vanilla comparison.

Adjusted lift:

- Relationship-evidence score on the 106-row slice: `97/106 = 0.9151`
- Original within-slice lift over vanilla: `0.9151 - 0.6415 = +0.2736`
- Adjusted lift over complement vanilla: `0.9151 - 0.5838 = +0.3313`

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
- Ordering evidence: criterion commit precedes the committed 8B result artifact. The exact SSM runtime timestamp is not in the lightweight report.
- Verdict: **PASS**

## Overall Verdict

**SOFT PASS.** The label-isolation, determinism, and criterion-before-scoring checks pass. The complement-slice vanilla run shows the selected evidence-addressable slice is somewhat easier than the complement, but not enough to trigger the pre-registered hard-fail band.

Praxis 07 can proceed, with a conservative claim boundary:

- Do claim: relationship-evidence prompting produced a large strict-accuracy gain on a locked, label-free, evidence-addressable CTI-MCQ slice.
- Do report: the complement vanilla baseline was `0.5838`, so the slice audit is a soft pass and adjusted lift must be shown.
- Do not claim from this audit alone: cross-model generalization or relationship-specific mechanism. Those are addressed separately by the 3B cross-model gate and the 8B ablation gate.

## Follow-On Gates

The pre-registered follow-on gates were run after this audit:

- 3B cross-model gate: PASS.
- 8B ablation gate: mixed mechanism; main effect reproduced.
