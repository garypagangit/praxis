# Pagan Praxis

### Experimental AI/ML & Cybersecurity Research

**Pagan Praxis** is a research portfolio for turning published research gaps, reproducibility questions, and operational AI-security problems into falsifiable experiments.

The program preserves **positive, negative, mixed, blocked, and diagnostic results**. A failed experiment is not erased; it becomes evidence about what did not work and why.

> **Numbering standard:** the public catalog now uses one permanent sequential scheme — **Experiment 001, Experiment 002, ...**. Historical `PX-###`, Praxis, and Final Praxis identifiers remain inside source artifacts only for provenance.

[Public research site](https://garypagangit.github.io/praxis/) · [Full catalog 001–034](catalog/EXPERIMENTS_001_034.md) · [Full catalog 035–068](catalog/EXPERIMENTS_035_068.md) · [Legacy detailed tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) · [Praxis Recon](apps/praxis-recon/index.html)

---

## Research Dashboard

### Final Research Series

| Experiment | What it is trying to prove — simple language | Status |
|---|---|---|
| [**Experiment 066 — Outcome-State Verification**](final_praxis/001_outcome_state_verification/) | Can we verify what an AI agent **actually changed** instead of trusting another AI that says the task succeeded? | 🔴 **Negative — verified complete** |
| [**Experiment 067 — Multi-Agent Cascade Containment**](final_praxis/002_cascade_containment/) | Can deterministic checkpoints stop one AI agent's mistake from spreading through a chain of AI agents? | 🔴 **Negative — verified complete** |
| [**Experiment 068 — Adaptive Cyber Investigation Stopping**](final_praxis/003_adaptive_investigation_stopping/) | Can a security AI stop investigating before additional reasoning turns a correct answer into a wrong one? | 🔴 **Negative — verified complete** |

These three experiments are scientifically complete and independently verified. Their negative determinations are retained as first-class results; any redesign requires a new protocol.

### Selected Completed / High-Value Results

| Experiment | Simple purpose | Status |
|---|---|---|
| [**001 — Safety-Gated TTA for Streaming APT Detection**](reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md) | Safely adapt an APT detector when incoming data changes. | 🟢 Defense-ready positive |
| [**003 — Retrieval-Conditioned CTI Compliance**](reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md) | Give a CTI model the right relationship evidence before it answers. | 🟢 Defense-ready positive |
| [**004 — FalseCite-Code Citation Poisoning**](reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md) | Verify software references before an agent trusts them. | 🟢 Bounded defense-positive |
| [**005 — MoE Router Audit**](reports/moe_standing_committee/README.md) | Test whether MoE expert routing is stable and repeatable. | 🟢 Bounded positive |
| [**011 — HalluHard Source-Backed Verification**](reports/halluhard_source_verifier/) | Check hallucinated claims against authoritative sources. | 🟢 Bounded positive |
| [**050 — Deterministic Agent Defenses**](reports/agentic_deployment_defense/px050_final_manuscript_20260705/PX050_FINAL_MANUSCRIPT_20260705.md) | Stop unsafe agent package actions with deterministic verification. | 🟢 Lead bounded positive |
| [**051 — Security-Utility Agent Gates**](reports/agentic_deployment_defense/px051v_live_agent_policy_refresh_20260705/PX051V_LIVE_AGENT_POLICY_REFRESH_20260705.md) | Block bad actions without blocking useful work. | 🟢 Live-agent policy pass |
| [**052 — Tool-Boundary Provenance**](reports/agentic_deployment_defense/px052v_live_agent_provenance_refresh_20260705/PX052V_LIVE_AGENT_PROVENANCE_REFRESH_20260705.md) | Track where agent tool arguments came from before trusting them. | 🟢 Live-agent provenance pass |
| [**054 — Refusal Geometry Across Recurrent Depth**](reports/refusal_geometry_recurrent_depth/px054_final_manuscript_20260706/PX054_FINAL_MANUSCRIPT_20260706.md) | Measure whether refusal-related internal directions stay stable across depth. | 🟢 Defense-ready bounded positive |
| [**056 — Model-Registry Identifier Hallucination**](reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/PX056_GATE2A_DETERMINATION_20260721.md) | Detect invented model/dataset identifiers before code trusts them. | 🔵 Live pilot positive; full study pending |

### Portfolio at a Glance

The repository currently catalogs **68 numbered experiments** spanning:

- APT detection, provenance graphs, concept drift, and rare-stage classification;
- cyber threat intelligence retrieval and evidence grounding;
- agentic AI security, deterministic verification, provenance, and tool boundaries;
- interpretability, refusal geometry, MoE routing, and test-time reasoning;
- model/software supply-chain security;
- federated learning, privacy, world models, robotics, and multimodal research.

For the complete dashboard with every experiment's **name, simple research purpose, status, and direct evidence link**, use:

### [Experiments 001–034 →](catalog/EXPERIMENTS_001_034.md)

### [Experiments 035–068 →](catalog/EXPERIMENTS_035_068.md)

---

## Status Convention

| Status | Meaning |
|---|---|
| 🟢 **Positive** | The frozen scientific gate was cleared within the stated claim boundary. |
| 🔵 **Active / Ready** | The experiment has a viable next gate or active execution path. |
| 🟡 **Mixed / Diagnostic** | Useful evidence exists, but the full hypothesis did not cleanly pass. |
| 🔴 **Negative / Closed** | The registered gate failed or the current formulation was closed. |
| ⚪ **Blocked / Deferred** | Missing data, infrastructure, novelty, labels, or another prerequisite prevents a defensible run. |

---

## Repository Organization

The repository is being normalized around a simple public-facing structure:

```text
Pagan Praxis
├── README.md                  # front door / dashboard
├── catalog/                   # canonical Experiment 001... numbering
├── final_praxis/              # completed final-series evidence
├── reports/                   # scientific reports and determinations
├── paper/                     # manuscript packages
├── configs/                   # frozen experiment configurations
├── scripts/                   # experiment and analysis code
├── cloud_jobs/                # AWS execution packages
├── runs/ / results/           # measured outputs
└── archive/                   # future home for legacy presentation artifacts
```

Historical filenames and PX identifiers are intentionally preserved so citations, hashes, reports, and scientific provenance do not break.

---

## Research Rule

**Scientific integrity is the success criterion.**

Pagan Praxis does not require an experiment to be positive. Thresholds are frozen before scientific evaluation where applicable; negative results and boundary conditions are retained; and a result is promoted only to the strength supported by its evidence.

---

## Legacy and Provenance

The original research history remains available through [EXPERIMENTS.md](EXPERIMENTS.md) and the [legacy HTML tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html). Those files preserve historical PX naming and detailed development lineage.

New public-facing work should use the canonical **Experiment ###** identifier from the Pagan Praxis catalog.
