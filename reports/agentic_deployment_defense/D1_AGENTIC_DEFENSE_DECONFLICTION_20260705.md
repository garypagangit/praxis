# D1 Agentic Deployment Defense Deconfliction

Generated: 2026-07-05

## Purpose

This report integrates the new D1 agent-defense proposals into the Praxis tracker without diluting the existing positive-result set. The D1 branch is treated as a forward research queue. Several rows now have positive first-gate evidence, but they remain tracked separately from the core Praxis positives until scaled, replicated, or written as standalone claims.

## Deconflicted Queue

| New ID | Source label | Title | Priority | Integrated status | Deconfliction decision |
|---|---|---|---:|---|---|
| PX-049 | D1-2 | Agentic slopsquatting package-hallucination verifier | 8.65 | Live gate fail / park | Extension of PX-004. The verifier smoke passed, but the live agent produced no install actions, so the unsafe-install gap was not established. |
| PX-050 | D1-1 | Adaptive evaluation of deterministic agent defenses | 8.35 | Robustness replicated / uplift mixed | Extension of the deterministic-gate thesis. Fixed fixture and Qwen live gates pass; DeepSeek replicates hardened zero-escape robustness but does not replicate the registry-uplift condition because registry-only also blocks its simpler direct invalid commands. |
| PX-051 | D1-4 | Security-utility Pareto for agent gates | 7.45 | Live-corpus policy pass | Reuses PX-001 selective-gate math and now has a positive policy result over the combined live PX-050 command corpus. |
| PX-052 | D1-3 | Provenance-aware tool-boundary retrofit monitoring | 7.00 | Live-corpus provenance pass | Narrowly distinct from PX-012/PX-013/PX-014 because it tracks tool-call argument provenance rather than graph-event provenance or model reasoning internals; now passes on combined live generated traces. |
| PX-053 | D1-5 | Human-in-the-loop approval fatigue vs. security | 6.55 | Simulation gate fail | Synthetic approval-load simulator missed compromise and completion thresholds. Do not run as a human-subject study without redesign and IRB-quality protocol. |
| PX-054 | Source-gate candidate | Refusal geometry across recurrent depth | TBD | Activation gate pass | Separate mechanistic/safety characterization lane using Huginn-style recurrent depth. No refusal removal, jailbreak optimization, or offensive bypass work. |

## Why PX-049 Was Tested First

PX-049 was tested first because it was the cleanest extension of the already-positive PX-004 verifier work. Its live gate has now failed under the preregistered promotion rules because the open-weight agent produced no install actions.

The core lift was not inventing a new verifier. The lift was deployment realism: moving the verifier from a static citation answer to an agent tool boundary where an install command could actually execute. The 2026-07-05 live run did not produce that baseline, so PX-049 is now a redesign candidate rather than a current positive.

Primary source anchor: USENIX Security 2025 "We Have a Package for You!" evaluates package hallucinations in code-generating LLMs at large scale. The companion public artifact is available at `https://github.com/Spracks/PackageHallucination`.

Defensible publication angle:

1. Start from package-hallucination/slopsquatting literature.
2. Run a tool-using code agent on held-out package-selection tasks.
3. Measure raw unsafe package actions.
4. Place the PX-004-style registry verifier between the agent and the tool.
5. Measure residual unsafe actions, clean overblocking, parse/tool-action failure, and latency.

## One-At-A-Time Rule

Do not run PX-049, PX-050, and PX-054 simultaneously. The next publishable positive needs a clean chain of evidence, not a broad pile of half-finished starts.

Registered first-pass order:

1. PX-049: agentic slopsquatting verifier.
2. PX-050: adaptive deterministic defense evaluation, only after PX-049 has a measured live-agent outcome.
3. PX-051: Pareto operating-point analysis, using scored rows from PX-049 or PX-050.
4. PX-052: provenance tool-boundary monitoring if the action-trace instrumentation is useful.
5. PX-054: recurrent-depth refusal geometry only after the deployment-defense paper path is not competing for compute/attention.

## Initial Artifacts

- PX-049 preregistration: `reports/agentic_deployment_defense/PX049_AGENTIC_SLOPSQUATTING_VERIFIER_PREREG_20260705.md`
- PX-049 smoke runner: `scripts/run_px049_agentic_slopsquatting_smoke.py`
- PX-049 smoke output: `reports/agentic_deployment_defense/px049_smoke_20260705/`
- PX-054 source gate: `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_SOURCE_GATE_20260705.md`

## Follow-On Gate Outcomes

Updated: 2026-07-05

| ID | Gate | Status | Result |
|---|---|---|---|
| PX-049 | Live open-weight agentic slopsquatting gate | `LIVE_GATE_FAIL` | Qwen2.5-Coder produced `0` install actions across `100` package-selection tasks, so no unsafe-install gap existed to close. Park or redesign the harness before spending more on this lane. |
| PX-050 | Adaptive deterministic defense gate | `ADAPTIVE_GATE_PASS` | `138` fixed adaptive command cases; hardened gate invalid recall `1.0000`, escape rate `0.0000`, clean allow rate `1.0000`. |
| PX-050 | Live model-generated adaptive gate | `LIVE_ADAPTIVE_GATE_PASS` | `98` Qwen2.5-Coder generated command strings; command parse rate `1.0000`, registry-only invalid escape rate `0.1800`, hardened invalid recall `1.0000`, hardened escape rate `0.0000`, valid clean allow rate `0.9167`. |
| PX-050 | Second-model live replication | `ROBUSTNESS_REPLICATION_PASS_UPLIFT_MIXED` | Across Qwen and DeepSeek: `196` generated commands, aggregate registry-only invalid escape rate `0.0900`, aggregate hardened escape rate `0.0000`, aggregate valid clean allow rate `0.9583`. Hardened robustness replicated; registry-uplift replicated only on Qwen. |
| PX-051 | Live-corpus policy refresh | `LIVE_POLICY_REFRESH_PASS` | Combined live corpus: hardened policy on Pareto front, invalid escape rate `0.0000`, utility preserved `0.9583`, review rate `0.0000`. |
| PX-052 | Live-corpus provenance refresh | `LIVE_PROVENANCE_REFRESH_PASS` | Combined live corpus: `196` traces, alert recall `1.0000`, clean false-positive rate `0.0000`, trace completeness `1.0000`. |
| PX-053 | Synthetic approval-fatigue simulation | `SIMULATION_GATE_FAIL` | Risk-scored routing reduced prompt load versus every-action approval but did not beat every-action compromise rate and missed the completion threshold. Do not promote without redesign or human-study protocol. |
| PX-054 | Safe recurrent-depth activation gate | `ACTIVATION_GATE_PASS` | Huginn activation capture `1.0000`, prompt validity `1.0000`, cross-depth direction stability `0.8321`, benign-control FPR `0.0000`. |

Rollup: `reports/agentic_deployment_defense/d1_followon_rollup_20260705/D1_NEW_EXPERIMENT_FOLLOWON_ROLLUP_20260705.md`

## Source Anchors

- Package hallucination / slopsquatting: `https://www.usenix.org/conference/usenixsecurity25/presentation/spracklen`
- PackageHallucination artifact: `https://github.com/Spracks/PackageHallucination`
- CaMeL prompt-injection defense: `https://arxiv.org/abs/2503.18813`
- Progent programmable privilege control: `https://arxiv.org/html/2504.11703v2`
- AgentLure / ARGUS provenance-aware decision auditing: `https://arxiv.org/html/2605.03378v1`
- Huginn recurrent-depth model: `https://arxiv.org/abs/2502.05171`
- Huginn open model card: `https://huggingface.co/tomg-group-umd/huginn-0125`

The proposal's `FORGE` reference remains unpinned in this tracker until a primary paper or repository is identified.

## Claim Boundaries

- PX-049 may claim verifier effectiveness at the tool boundary only after a real agent run. The initial smoke is readiness evidence only.
- PX-050 may claim adaptive robustness only if the attack is allowed to optimize against the known gate and still fails under frozen metrics.
- PX-051 may claim a Pareto framework only if it shows nontrivial security-utility trade-off control across scored actions.
- PX-052 may claim provenance monitoring only if it tracks transitive tool-argument lineage without instrumenting hidden chain-of-thought.
- PX-053 must not be presented as human-subject evidence unless a real IRB-approved study is performed.
- PX-054 must remain characterization/detection. It must not include safety ablation, refusal removal, or jailbreak optimization.
