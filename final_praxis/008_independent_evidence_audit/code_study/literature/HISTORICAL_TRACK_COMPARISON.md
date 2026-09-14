# Historical comparison: FalseCite-Code

Review date: 2026-09-14. A bounded search of the named local `reports/falsecite_code` directory found a previously completed **bounded positive** track. It should not be reported as another failed code-revision experiment. This review does not revalidate all historical executions or certify publication acceptance.

## What the old track tested

FalseCite-Code tested whether models trust fabricated software-artifact citations concerning PyPI versions, NPM versions, GitHub repositories and GitHub tags. Its constructed slice has80 claims:45 training,20 validation and15 strict-holdout claims. A deterministic verifier compares claims against external package/repository metadata. The source/readiness report links the motivation to FalseCite and notes an earlier EXP04 response-artifact failure.

The historical results include:

- Qwen2.5-Coder-7B audit:6 of7 fabricated strict-holdout claims accepted under the base prompt; metadata and verifier conditions accept0 of7.
- The verbose160 generation setting:5 of6 usable fabricated strict-holdout claims trusted; one of15 total held-out responses failed parsing. Metadata and verifier conditions trust0 of7 fabricated claims with no parse failures.
- General Qwen2.5-3B rejected all clean claims under the base audit prompt; that is over-refusal, not useful robustness.
- Phi-3.5's audit attempt had100% parse failure for the model conditions; it is protocol-invalid rather than behavioral evidence.
- Qwen2.5-Coder-3B provided a boundary case: metadata evidence could fail while the deterministic citation verifier remained effective on the tested slice.

The source markdown labels the final package `FINAL SHORT PAPER PUBLISHED - BOUNDED POSITIVE`. In the inspected records this refers to a local tracked portfolio short-paper artifact. No external submission, peer-review decision, accepted venue or DOI was verified.

## How it differs from the proposed008 code study

| Dimension | Historical FalseCite-Code | Proposed selective-test study |
|---|---|---|
| Untrusted material | Fabricated artifact-existence/version claims | True test execution records selectively chosen to support a revision |
| Source truth | External package/repository metadata | Qualified executable tests on original and proposed programs |
| Model task | Trust/reject or generate an answer involving a citation | Accept/keep a concrete code revision |
| Outcome | Citation trust and valid-claim overblocking | Reserved-suite passing, harmful acceptance and useful repair acceptance |
| Defense | Check claim against authoritative metadata | Independently choose checks under a budget, then verify and review |
| Main unresolved distinction | Generalization beyond the constructed artifact slice | Selection-policy value beyond uniform and change-aware testing |

The old track already establishes the portfolio's interest in external mechanical verification. Repeating a generic model-versus-deterministic-verifier comparison would add little. The proposed study must retain the stronger condition that every displayed test record is genuine and correctly bound to the proposal; the intervention is selection and missing counterevidence, not forgery.

## Lessons for the new protocol

The verbose96, tight-repair and verbose160 reports all display the same45/20/15 split while their prompts or generation settings change. This warrants an exposure-history audit before treating the historical15 claims as fresh confirmatory evidence. The bounded document review does not prove the exact decision sequence or all information seen when prompts were changed. The new study must freeze prompts and engineering limits on a task-separated development split, then avoid repairing them using confirmation outcomes.

Report parse failures, unusable responses and over-refusal explicitly. A0% harmful-acceptance rate from refusing every useful action is not a successful assistant. Keep historicalPX-004 separate from September Final-Praxis-004 and from the new008 task set; the numbering systems and endpoints differ.

## Local sources inspected

All paths below are relative to `C:/Users/garyp/OneDrive/Documents/codex/reports/falsecite_code/`:

- `FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md`
- `FALSECITE_CODE_MODEL_GATE_SUMMARY_20260624.json`
- `FALSECITE_CODE_CROSS_MODEL_SYNTHESIS_20260624.md`
- `FALSECITE_CODE_GENERATION_GATE_20260625.md`
- `FALSECITE_CODE_GENERATION_GATE_REPAIR_20260625.md`
- `FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md`
- `FALSECITE_CODE_GENERATION_GATE_VERBOSE160_SUMMARY_20260625.json`
- `FALSECITE_CODE_GENERATION_GATE_QWEN25_CODER3B_20260626.md`
- `FALSECITE_CODE_USEFULNESS_DECISION_20260625.md`
- `FALSECITE_CODE_PUBLISHING_PACKAGE_20260628.md`
- `FALSECITE_CODE_PAPER_DRAFT_20260628.md`
- `README.md`

This comparison uses existing reports and summary counters, not a fresh model run. The separate paper-package inventory records source hashes and publication boundaries.
