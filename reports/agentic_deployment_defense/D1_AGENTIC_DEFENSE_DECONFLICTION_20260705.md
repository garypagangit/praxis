# D1 Agentic Deployment Defense Deconfliction

Generated: 2026-07-05

## Purpose

This report integrates the new D1 agent-defense proposals into the Praxis tracker without diluting the existing positive-result set. The D1 branch is treated as a forward research queue. None of these rows are positive results until a registered gate produces measured evidence.

## Deconflicted Queue

| New ID | Source label | Title | Priority | Integrated status | Deconfliction decision |
|---|---|---|---:|---|---|
| PX-049 | D1-2 | Agentic slopsquatting package-hallucination verifier | 8.65 | Start next | Extension of PX-004. Tests whether package hallucination survives a tool-using agent and whether the PX-004 verifier closes the unsafe-install gap. |
| PX-050 | D1-1 | Adaptive evaluation of deterministic agent defenses | 8.35 | Start after PX-049 | Extension of the deterministic-gate thesis. Uses PX-004/PX-011/PX-016 lessons, but requires adaptive attacker craft and an open-weight agent. |
| PX-051 | D1-4 | Security-utility Pareto for agent gates | 7.45 | Source-gate companion | Reuses PX-001 selective-gate math. Should be run after PX-049 or PX-050 produces a scored action set. |
| PX-052 | D1-3 | Provenance-aware tool-boundary retrofit monitoring | 7.00 | Source-gate candidate | Narrowly distinct from PX-012/PX-013/PX-014 because it tracks tool-call argument provenance rather than graph-event provenance or model reasoning internals. |
| PX-053 | D1-5 | Human-in-the-loop approval fatigue vs. security | 6.55 | Hold / simulation only | Do not run as a human-subject study this cycle. Only a synthetic approval-load simulator is acceptable without IRB review. |
| PX-054 | Source-gate candidate | Refusal geometry across recurrent depth | TBD | Queued behind PX-049 | Separate mechanistic/safety characterization lane using Huginn-style recurrent depth. Do not co-gate with PX-049. No refusal removal, jailbreak optimization, or offensive bypass work. |

## Why PX-049 Leads

PX-049 is the cleanest next experiment because it is close to the already-positive PX-004 FalseCite-Code result. The core lift is not inventing a new verifier. The lift is deployment realism: moving the verifier from a static citation answer to an agent tool boundary where an install command could actually execute.

Primary source anchor: USENIX Security 2025 "We Have a Package for You!" evaluates package hallucinations in code-generating LLMs at large scale. The companion public artifact is available at `https://github.com/Spracks/PackageHallucination`.

Defensible publication angle:

1. Start from package-hallucination/slopsquatting literature.
2. Run a tool-using code agent on held-out package-selection tasks.
3. Measure raw unsafe package actions.
4. Place the PX-004-style registry verifier between the agent and the tool.
5. Measure residual unsafe actions, clean overblocking, parse/tool-action failure, and latency.

## One-At-A-Time Rule

Do not run PX-049, PX-050, and PX-054 simultaneously. The next publishable positive needs a clean chain of evidence, not a broad pile of half-finished starts.

Registered order:

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
