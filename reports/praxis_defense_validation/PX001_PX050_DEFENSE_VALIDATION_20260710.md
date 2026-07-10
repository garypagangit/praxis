# PX-001 and PX-050 Praxis Defense Validation

Generated: 2026-07-10

Validation artifact: `reports/praxis_defense_validation/px001_px050_validation_summary_20260710.json`

Validation script: `scripts/validate_px001_px050_defense.py`

## Executive Verdict

| Experiment | Defense verdict | Why it stays |
|---|---:|---|
| PX-001 - Safety-Gated Test-Time Adaptation for Streaming APT Detection | DEFENSE-READY BOUNDED POSITIVE | This remains one of the strongest design elements in the portfolio because it combines a locked selective gate, source-file leakage controls, a matched confidence-reject null, and a safety constraint for destructive-event detection. |
| PX-050 - Package-Install Tool-Boundary Verification for Agentic Deployment | DEFENSE-READY BOUNDED POSITIVE | This is a lead deployable systems result because the deterministic boundary gate blocks invalid package-install actions in two dry-run live-agent corpora while preserving valid install utility. |

Both experiments should be defended as bounded positive results. Neither should be framed as universal AI safety. The defense-ready contribution is narrower and stronger: deterministic or gated controls at operational boundaries can preserve useful behavior while reducing measurable failure modes.

## Validation Method

This review follows the supplied skeptical evaluation pattern:

1. Hypothesis, problem, and core claim.
2. Design audit.
3. Tautology check.
4. Null-model check.
5. Redefinition check.
6. Framing check.
7. Statistics and evidence.
8. Defense verdict and required claim boundary.

The repeatable checker validates required files, core metric thresholds, null evidence, corpus counts, zero observed invalid allows, and defense support artifacts.

## PX-001 Validation

### 1. Hypothesis, Problem, Core Claim

Problem: streaming cyber detectors can lose recall on early-stage attack classes after domain or temporal shift, while high-risk destructive events must not be sacrificed for recall.

Core claim: a locked safety-gated BatchNorm test-time adaptation method improves weak Recon detection in the tested Unraveled APT stream while preserving destructive-event performance within a pre-specified safety boundary.

Allowed thesis statement: In the tested Unraveled APT feature pipeline and held-out source-file split, safety-gated BatchNorm TTA substantially improves Recon F1 and macro F1 while preserving mean Data Exfiltration F1 and limiting override behavior.

### 2. Design Audit

Design strength is high. PX-001 is not merely a new model run; it is an operational control design:

- Frozen support-floor MLP baseline is retained.
- Adaptation is limited to unlabeled target-stream BatchNorm behavior.
- Selective gate is locked before final replay.
- Source-file leakage checks are explicit and pass.
- Destructive-event safety is treated as a first-class constraint, not an afterthought.
- A confidence-reject baseline is included at the same rejection/override rate.

The strongest element is the gate itself. PX-001 should stay because the research value is not "TTA improves a classifier"; the research value is "a safety-gated adaptation policy can recover weak-class recall without allowing the adaptation mechanism to trade away the protected class at the operating point."

### 3. Tautology Check

Verdict: passes, with a narrow caveat.

The result is not simply a tautology of "change uncertain outputs and score improves." The matched confidence-reject null rejects that explanation: the confidence-reject baseline at the same rate yields Recon F1 of 0.0000, while locked selective TTA yields Recon F1 of 0.5050.

Caveat: PR-AUC changes only slightly, so the strongest claim is about the locked operating policy and class-specific decision behavior, not a broad ranking-quality improvement.

### 4. Null-Model Check

Existing null evidence is adequate for defense:

- Frozen MLP baseline.
- Frozen confidence-reject matched-rate baseline.
- Source-file overlap checks.
- Cloud hardening audit with locked-policy checks.

Recommended extra nulls before journal submission:

- Source-order permutation null to quantify how much stream composition contributes to the effect.
- Label-preserving stream-shuffle replay, already partially explored, formalized as a table.
- Poisoned or adversarial unlabeled target-stream stress test.
- Bootstrap confidence intervals or paired seed-level permutation test for macro F1, Recon F1, and DE F1.

### 5. Redefinition Check

No improper redefinition found if the claim remains bounded.

Do not redefine success as "TTA is generally safe." The measured success is a locked selective operating point with a protected DE safety rule. The DAPT transfer result is negative boundary evidence and should remain in the praxis as a limitation, not be hidden.

### 6. Framing Check

Correct framing: cyber defense operating-control experiment.

Avoid framing as:

- universal APT detection,
- universal test-time adaptation,
- DAPT graph/ML transfer validation,
- adversarial robustness against poisoned unlabeled streams.

### 7. Statistics and Evidence

Primary evidence from the validation script:

| Metric | Frozen MLP | Locked selective TTA | Delta |
|---|---:|---:|---:|
| Macro F1 | 0.7685 | 0.8658 | +0.0974 |
| Recon F1 | 0.0250 | 0.5050 | +0.4800 |
| Data Exfiltration F1 | 0.9157 | 0.9202 | +0.0045 |
| Override rate | 0.0000 | 0.0470 | +0.0470 |

Additional validated evidence:

- Source-file overlap sum: 0.
- Cloud audit status: PASS.
- Confidence-reject Recon F1: 0.0000.
- Minimum per-seed Recon delta across locked seeds: +0.4372.
- Minimum per-seed DE delta across locked seeds: -0.0163, within the pre-specified -0.05 safety floor.

### 8. PX-001 Verdict

PX-001 stays as defense-ready. It is probably the best "design thesis" experiment because it makes the engineering judgment visible: adaptation is useful only when constrained by a safety gate and evaluated against protected-class loss.

Defense-ready claim:

> PX-001 demonstrates that safety-gated BatchNorm test-time adaptation can recover weak-class Recon performance in a held-out Unraveled APT stream while preserving destructive-event performance within a locked safety boundary.

## PX-050 Validation

### 1. Hypothesis, Problem, Core Claim

Problem: model-generated agent deployment actions can produce invalid or policy-unsafe package-install commands, including slopsquatting-like package names and unsafe install syntax.

Core claim: deterministic validation at the package-install tool boundary blocks invalid or policy-unsafe package-install actions before execution while preserving valid installs in measured dry-run PyPI/NPM tool-call corpora.

Allowed thesis statement: On measured PyPI/NPM package-install command-string and dry-run live-agent tool-call corpora, a deterministic hardened verifier blocks invalid or policy-unsafe install actions with zero observed hardened invalid allows while preserving valid install utility.

### 2. Design Audit

Design strength is high for a systems-defense praxis:

- The gate operates at the observable tool boundary, not inside hidden model reasoning.
- No package managers are executed in the validation harness.
- Two open-weight coding models are included in the dry-run live-agent corpus.
- Registry-only and raw/no-gate baselines are preserved.
- Held-out controller/extractor repair is documented.
- Parser stress and adaptive string stress are included.
- Policy/Pareto and provenance follow-ons were refreshed on the same live-agent corpus.

This is a strong deployable-result design because it tests a practical control that could be inserted into an agent runtime.

### 3. Tautology Check

Verdict: passes, with one important limitation.

It is not tautological because the hardened gate is compared against weaker controls:

- Raw/no-gate unsafe rate is 0.9453.
- Registry-only invalid allow count is 20 over 128 invalid rows.
- Hardened invalid allow count is 0 over the same invalid rows.
- Valid allow rate remains 1.0000.

Limitation: the gate is designed around observable install actions. It should not be represented as proof that arbitrary agent behavior is safe.

### 4. Null-Model Check

Existing null and alternative evidence is good for defense:

- Allow-all/raw baseline.
- Registry-only baseline.
- Parser stress appendix.
- Controller adaptive stress.
- Held-out StarCoder2 repair evidence.
- Two-model dry-run live-agent corpus.
- Policy/Pareto and provenance refresh checks.

Recommended extra nulls before journal submission:

- Property-based fuzzing against the parser and controller/extractor.
- Fresh post-cutoff package namespace list.
- Negative control for malicious but real packages to show this method is not designed to solve that problem.
- Additional package managers beyond PyPI/NPM.
- Sandbox execution study as a separate experiment, not folded into the existing claim.

### 5. Redefinition Check

No improper redefinition found if the result remains a boundary-control claim.

Do not redefine success as "package supply-chain security solved." The measured success is only pre-execution deterministic validation of observable install command strings and dry-run tool-call arguments.

### 6. Framing Check

Correct framing: deterministic deployment boundary defense for agentic package-install actions.

Avoid framing as:

- broad coding-agent safety,
- malicious-existing-package detection,
- post-install behavior containment,
- arbitrary shell or OS command safety,
- universal jailbreak resistance.

### 7. Statistics and Evidence

Primary evidence from the validation script:

| Metric | Value |
|---|---:|
| Combined dry-run live-agent rows | 288 |
| Invalid rows | 128 |
| Valid rows | 160 |
| Raw/no-gate unsafe rate | 0.9453 |
| Registry-only invalid allow count | 20 |
| Hardened invalid allow count | 0 |
| Hardened valid allow rate | 1.0000 |
| Controller target recovery rate | 0.9757 |
| Parser stress invalid rows | 600 |
| Controller adaptive stress invalid rows | 1,140 |

Zero-observed-event caution:

- Zero hardened invalid allows over 128 two-model invalid rows gives an exact one-sided 95% upper bound of about 2.31% for the unobserved invalid-allow probability under the same sampling process.
- Zero escapes over 600 parser-stress invalid rows gives an upper bound of about 0.50%.
- Zero escapes over 1,140 adaptive-stress invalid rows gives an upper bound of about 0.26%.

This should be stated in defense. It keeps the result honest: "zero observed escapes" is defensible; "zero possible escapes" is not.

### 8. PX-050 Verdict

PX-050 is defense-ready and should be treated as a lead deployable systems result. It is stronger when framed as a tool-boundary verifier than as a broad AI safety result.

Defense-ready claim:

> PX-050 demonstrates that deterministic validation at the package-install tool boundary can block invalid or policy-unsafe PyPI/NPM install actions in measured dry-run live-agent corpora while preserving valid install utility.

## Cross-Experiment Defense Readiness

PX-001 and PX-050 are complementary:

- PX-001 is the stronger design thesis: constrained adaptation under a safety gate.
- PX-050 is the stronger deployment thesis: deterministic boundary enforcement around agent tool use.

Together, they support a coherent praxis theme:

> AI systems become more defensible when model behavior is not trusted directly, but routed through explicit, measurable controls at adaptation or action boundaries.

## Required Claim Boundaries

PX-001 must not claim:

- universal APT detection,
- universal test-time adaptation safety,
- DAPT cross-dataset success,
- robustness to poisoned unlabeled target streams.

PX-050 must not claim:

- broad agent safety,
- malicious-existing-package detection,
- post-install behavior protection,
- arbitrary shell-command safety,
- universal package supply-chain defense.

## Praxis Defense Additions

Add the following to the final praxis defense package:

1. Claim ledger table separating allowed claims, unsupported claims, and future-work claims.
2. Null-model appendix for PX-001 including the confidence-reject comparison and source-file leakage table.
3. Zero-event confidence-bound note for PX-050.
4. Boundary-evidence appendix preserving negative or mixed results instead of removing them.
5. Reproducibility appendix listing the validation script and JSON summary.

## Code Validation

The following local code-artifact checks passed on 2026-07-10:

- `python scripts\validate_px001_px050_defense.py`
- `python -m py_compile scripts\validate_px001_px050_defense.py scripts\run_tta_locked_final.py scripts\run_tta_defense_hardening.py scripts\audit_tta_result_package.py scripts\run_px050_parser_stress_appendix.py scripts\run_px050s_controller_adaptive_stress.py scripts\run_d1_live_agent_corpus_refresh.py cloud_jobs\px050u_live_agent_tool_boundary_20260705\run_px050u_live_agent_tool_boundary.py cloud_jobs\px050v_second_model_live_agent_tool_boundary_20260705\run_px050v_second_model_live_agent_tool_boundary.py`

Validation result: PASS.

## Final Determination

PX-001 stays. PX-050 stays.

Both are true defense-ready positives when argued with the bounded claims above. PX-001 should be defended as the portfolio's strongest design element. PX-050 should be defended as the strongest deployable agent-security systems result.
