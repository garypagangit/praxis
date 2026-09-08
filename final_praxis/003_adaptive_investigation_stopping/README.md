# Final Praxis 003

## Safety-Gated Adaptive Investigation Stopping for Agentic Security Triage

**Status:** CONDITIONAL GO  
**Priority:** 3  
**Historical lineage:** builds from the adaptive-stopping line, but does **not** inherit any historical PX-057 result as a certified positive.

## Research Question

Can a preregistered stopping policy prevent correct-to-wrong degradation during iterative security investigation while reducing investigation cost, under a mechanically enforced safety/review protocol?

## Scientific Reset

Generic adaptive stopping is not the novelty target. REFRAIN and other stopping work already establish adaptive early stopping as an important inference mechanism.

This Final Praxis experiment is a **new security-domain experiment**. Historical adaptive-stopping numbers may motivate the question, but they may not be used to claim a completed result, tune thresholds, select favorable policies, or reverse-engineer the new protocol.

The experiment remains blocked until the calibration/review sample-size calculation and policy-selection independence checks are complete.

## Candidate Contribution

The potential contribution is a security-specific safety decomposition:

- reasoning/investigation may improve with additional evidence or steps;
- continuing may also cause correct assessments to become incorrect;
- a stopping mechanism should be judged not only on accuracy/tokens but on **prevention, harm, review coverage, and valid calibration**.

## Task Design

Create or select an inert cyber-triage corpus with frozen ground truth and staged evidence. Each case should expose evidence in a predefined sequence so the agent can produce an assessment after each investigation round.

Each round records:

- current disposition/classification;
- confidence or uncertainty signal if used by the policy;
- evidence consumed;
- token/step cost;
- whether the current answer is correct under frozen ground truth.

Do not allow free-form browsing or uncontrolled new evidence sources in the discovery experiment.

## Required Pre-Run Decisions

Before non-fixture model execution:

1. calculate the calibration/review sample size needed to support the safety claim;
2. define the mechanically enforced review gate;
3. select stopping policies without using outcome knowledge from the prior protocol-invalid run;
4. freeze the evidence order and case split;
5. freeze all thresholds, including harm ceiling and minimum prevention/compute benefit;
6. define how abstain/review outcomes count in utility.

## Arms

At minimum:

- **A0:** fixed-short investigation.
- **A1:** fixed-long investigation.
- **A2:** answer-stability stopping.
- **A3:** uncertainty/confidence stopping if independently justified.
- **A4:** preregistered adaptive safety-gated stopping.

An oracle may be reported descriptively but cannot be a deployable comparator.

## Hypotheses to Freeze

- **H1 — Non-inferior correctness/utility:** adaptive stopping is not materially worse than the strongest frozen non-adaptive baseline under the preregistered margin.
- **H2 — Investigation-cost reduction:** adaptive stopping reduces steps/tokens by at least the frozen threshold.
- **H3 — Degradation prevention:** adaptive stopping prevents a preregistered fraction of observed correct-to-wrong transitions.
- **H4 — Harm ceiling:** early stopping harms no more than the preregistered maximum fraction of cases, evaluated through the mechanically enforced review protocol.
- **H5 — Security-domain relevance:** effects are demonstrated on the frozen triage task rather than inferred from math-reasoning behavior.

## Primary Metrics

- final correctness / task utility;
- correct-to-wrong transition count and rate;
- prevented degradation rate;
- early-stop harm rate;
- review/abstain rate;
- token/step saving;
- calibration/review coverage;
- per-stage/case-family breakdown;
- confidence intervals for prevention, harm, and compute saving.

## Protocol Protections

- Historical policy outcomes must not be used to choose the new policy.
- The review gate must be enforced in code, not checked manually after the run.
- Thresholds may not move after discovery data are inspected.
- If the planned safety sample size is not achieved, the result is protocol-incomplete regardless of descriptive performance.
- Any missed preregistered review or safety gate produces **Protocol Invalid** or **Negative**, not a smoothed bounded positive.

## Novelty Gate

Position against REFRAIN and related adaptive-stopping/test-time-scaling work. The paper must not claim novelty for "stopping overthinking." The differentiator must be the security-investigation task, staged evidence, and preregistered safety decomposition with harm/review as first-class gates.

## Kill Criteria

Stop or downgrade if:

- calibration/review sample size is infeasible;
- policy independence from prior exploratory outcomes cannot be defended;
- the security task does not exhibit enough correct-to-wrong degradation to study;
- fixed-short or simple answer stability matches the adaptive policy within the preregistered equivalence range at substantially lower complexity;
- stopping gains are explained entirely by fewer tokens with no security-relevant prevention signal;
- literature already directly evaluates the same security-investigation stopping construct and safety decomposition.

## Promotion Boundary

A positive result supports the frozen corpus, evidence schedule, models, policies, and review mechanism. It does not establish general adaptive stopping superiority or generalize historical PX-057 descriptive numbers into a certified result.
