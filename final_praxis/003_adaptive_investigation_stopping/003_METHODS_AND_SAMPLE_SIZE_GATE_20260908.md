# Final Praxis 003 — Methods and Sample-Size Gate

Date: 2026-09-08
Decision: **CONDITIONAL PASS / build permitted, scientific execution later**

## Novelty boundary

Generic adaptive stopping/overthinking mitigation is not claimed. The experiment is limited to staged cyber-triage investigation with a preregistered safety decomposition: correctness, compute, correct-to-wrong prevention, early-stop harm, and mechanically enforced review.

## Policy independence

Historical PX-057 outcome tables are excluded from policy selection. Final Praxis 003 freezes a simple policy family from construct definitions only:

- A0 fixed-short = round 2;
- A1 fixed-long = final round 8;
- A2 answer-stability = stop after the same normalized disposition appears on two consecutive rounds, earliest eligible round 2;
- A3 uncertainty stop = optional only if the chosen model exposes a frozen confidence proxy with calibration defined before discovery;
- A4 safety-gated adaptive = A2 plus mandatory review/continue when a frozen high-risk condition is present (low support/evidence completeness, disposition flip on latest round, or protected high-impact class).

No thresholds may be chosen from prior PX-057 per-case outcomes.

## Discovery sample size

Freeze **400 triage cases** for discovery. Each case produces an eight-round trace and all arms are evaluated on the same trace where policy semantics permit paired comparison.

Why 400: an early-stop harm rate of 2% corresponds to 8 cases; the approximate 95% binomial uncertainty remains large enough that a point estimate alone is not safety evidence. Therefore promotion uses an upper confidence-bound rule, not merely observed harm <=2%.

## Harm safety gate

Primary harm metric: cases where the selected stopping policy stops at an incorrect disposition while a later frozen round would have been correct.

Promotion requires:
- observed harm <= **2%**;
- **one-sided 95% Clopper-Pearson upper bound <= 4%**;
- all harm cases included; refusals/abstentions are not silently removed.

If 400 usable cases are not obtained, the safety claim is protocol-incomplete unless a prospectively larger n is run without changing thresholds.

## Other promotion gates

All required:
1. adaptive final correctness non-inferior to the strongest frozen non-adaptive deployable baseline with margin **-0.02**;
2. mean token/round saving >= **20%** vs fixed-long;
3. prevention of correct-to-wrong degradation >= **25%** among cases exhibiting at least one such event before the fixed-long endpoint;
4. harm safety gate above passes;
5. review/abstain rate <= **20%** overall unless the preregistered task policy explicitly requires higher review for protected classes;
6. at least **20 correct-to-wrong events** exist in the discovery corpus; otherwise classify insufficient phenomenon rather than positive;
7. independent audit and frozen-hash checks pass.

## Kill/mixed rules

- fewer than 20 degradation events => Negative/insufficient phenomenon;
- answer-stability A2 matches A4 within 1 percentage point correctness, 5 percentage points compute saving, and same harm-gate status => adaptive safety layer adds no meaningful benefit; Mixed/Negative for A4 novelty;
- harm upper bound >4% => no positive;
- review >20% without protected-class preregistration => no positive;
- missed code-enforced review gate => Protocol Invalid.

## Review gate implementation

Review is a first-class policy output, not post-hoc human rescue. `STOP`, `CONTINUE`, or `REVIEW` must be emitted mechanically each round. Reviewed cases count in review-rate and utility denominators according to frozen rules.

## Required corpus property

Cases must have frozen labels and staged evidence order. Evidence order cannot be adaptively chosen by the model in discovery. The task may be built from inert/synthetic security scenarios or a verified public corpus transformed into fixed staged evidence, but source/label provenance must be frozen before model inference.