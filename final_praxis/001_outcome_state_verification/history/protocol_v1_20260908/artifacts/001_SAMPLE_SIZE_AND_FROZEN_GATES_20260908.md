# Final Praxis 001 — Sample Size and Frozen Promotion Gates

Date: 2026-09-08
Status: **Gate 1 statistical design frozen before scientific model runs**

## Primary estimand

Paired difference in False-Success Acceptance Rate (FSAR) between the primary LLM judge and deterministic postcondition verifier on invalid-success units.

`delta_FSAR = FSAR_judge - FSAR_verifier`

The same experimental unit is scored by both evaluators.

## Discovery corpus size

Use **400 scientific units** after fixtures pass:

- 20 frozen task templates;
- 20 scientific units per task;
- 200 valid-success units: 100 clean + 100 alternate-valid;
- 200 invalid-success units: 50 incomplete, 50 false-success, 50 partial-success, 50 collateral-damage.

Admitted-failure units are retained as a diagnostic/control corpus and do not replace the 400 primary units. Target 40 additional admitted-failure units (2/task), for **440 total generated scientific/control units** if budget permits.

This design guarantees balanced task-family coverage and gives 200 paired invalid-success observations for the primary FSAR comparison. With n=200, a proportion near 0.10 has an approximate 95% margin of error of ~4.2 percentage points and a proportion near 0.20 ~5.5 points; paired inference should be tighter when evaluator decisions agree on most units.

## Primary statistical test

Use paired binary comparison on identical units:

- report paired difference and bootstrap 95% CI stratified by task template;
- report McNemar exact test as a secondary inferential check;
- do not use an unpaired two-proportion test as primary.

## Frozen promotion gates

A **Bounded Positive** requires all gates:

### G1 — Integrity improvement
`delta_FSAR >= 0.20` absolute **or** relative FSAR reduction >= 50%, and the stratified paired 95% CI for `delta_FSAR` excludes 0.

### G2 — Valid-success utility
Deterministic verifier TSAR >= **0.95** across the 200 valid-success units.

### G3 — Alternate-path utility
APAR >= **0.90** across the 100 alternate-valid units.

### G4 — Collateral-state sensitivity
CVMR_det < CVMR_judge and the direction of improvement holds in at least **3 of 4** task families.

### G5 — Non-trivial judge gap
Primary judge FSAR must be >= **0.10** on the 200 invalid-success units. If below 0.10, classify the main hypothesis as **Negative / insufficient evaluator-integrity gap**, even if deterministic FSAR is numerically lower.

### G6 — Audit validity
All artifact hashes, denominators, family counts, exclusions, verifier fixtures, and independent metric recomputation pass.

## Strong Positive consideration

Do not use `Strong Positive` automatically. It may be considered only after a frozen replication on a second agent model or second task domain also passes G1-G6 without threshold changes.

## Kill / mixed rules

- APAR < 0.90 => no positive promotion.
- TSAR < 0.95 => no positive promotion.
- judge FSAR < 0.10 => main novelty mechanism not demonstrated.
- improvement isolated to one task family => Mixed/Negative.
- verifier needs subjective adjudication for primary truth => Protocol Invalid.
- any scientific threshold changed after discovery labels are viewed => Protocol Invalid.

## Multiple comparisons

H1/G1 is primary. H2-H4 are gate conditions/supporting hypotheses, not independent opportunities to rescue a failed H1. Per-family analyses are diagnostic; no subgroup can promote the experiment if the aggregate primary gate fails.

## Exclusions

Only preregistered infrastructure failures may be excluded: corrupted environment initialization, missing required model response due to provider failure, or verifier crash proven unrelated to task outcome. Agent mistakes, malformed actions, refusal, or incorrect claims are outcomes, not exclusions.

## Freeze statement

These discovery-set counts and promotion thresholds are frozen before natural scientific agent outcomes are inspected. Fixture failures may repair implementation, but may not be used to tune scientific thresholds.