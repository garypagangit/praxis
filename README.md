# Identifying Autonomous AI APT

[**Project status tracker and delivery schedule**](PRAXIS_STATUS_TRACKER.md) · [Research questions and hypotheses](PRAXIS_RESEARCH_DESIGN.md) · [Experiment delivery protocol](PRAXIS_EXPERIMENT_PROTOCOL.md)

**Delivery window: October 19–December 1, 2026. AI Review due November 14. Defense December 1.**

**Final Praxis — Gary Pagan**

[**Open the Final Defense Idea Advisor Submission (PowerPoint)**](Final%20Defense%20Idea%20Advisor%20Submission%20V001%2010162026.pptx)

Advisor submission: **V001, October 16, 2026**. This presentation is the designated final Praxis submission and is stored at the repository root. The research portfolio and earlier experiments are retained below for background and provenance.

---

## Literature, novelty and problem-statement evidence

[**Dataset evaluation table: contents, labels, availability and fit**](PRAXIS_DATASET_EVALUATION.md) compares AI-agent trajectories, human/AI studies, human red-team corpora and conventional APT datasets. It explains which sources can support development and why the current thesis still needs qualified matched evidence.

[**Open the annotated literature block: titles, authors, dates, documents and relevance**](PRAXIS_LITERATURE.md)

**Closest novelty comparison:** Ashley Alt's April 2026 thesis, [Beyond Anomaly Detection](https://repository.rit.edu/theses/12605/). The proposed extension tests matched human versus autonomous-AI behavior using multi-host host/network telemetry and unseen-group evaluation. This is a proposed contribution, not a verified “first”; the literature block also compares LLM Agent Honeypot and Trace.

**Problem-statement sources:** Anthropic's November 2025 espionage report establishes a reported operational case; CrowdStrike's February 2026 report supports growth in AI-enabled attacks; IBM's July 2025 report supplies general breach-cost context. The [claim-to-source mapping](PRAXIS_LITERATURE.md#references-that-make-up-the-problem-statement) distinguishes those claims from the research gap.

---

# Pagan Praxis

### Experimental AI/ML & Cybersecurity Research

<p>
  <a href="https://garypagangit.github.io/praxis/apps/praxis-recon/"><strong>🚀 OPEN PRAXIS RECON</strong></a>
  &nbsp;•&nbsp;
  <a href="https://garypagangit.github.io/praxis/"><strong>📊 PUBLIC RESEARCH SITE</strong></a>
  &nbsp;•&nbsp;
  <a href="catalog/EXPERIMENTS_001_034.md"><strong>📚 EXPERIMENT CATALOG</strong></a>
</p>

**Pagan Praxis** is a research portfolio for turning published research gaps, reproducibility questions, and operational AI-security problems into falsifiable experiments.

The program preserves **positive, negative, mixed, blocked, and diagnostic results**. A failed experiment is not erased; it becomes evidence about what did not work and why.

> **Numbering standard:** the public catalog uses one permanent sequential scheme — **Experiment 001, Experiment 002, ...**. Historical `PX-###`, Praxis, and Final Praxis identifiers remain inside source artifacts only for provenance.

---

## Research Dashboard

### Final Research Series

| Experiment | What it is trying to prove — simple language | Status |
|---|---|---|
| [**Experiment 066 — Outcome-State Verification**](experiments/experiment-066-outcome-state-verification/) | Can we verify what an AI agent **actually changed** instead of trusting another AI that says the task succeeded? | 🔴 **Negative — verified complete** |
| [**Experiment 067 — Multi-Agent Cascade Containment**](experiments/experiment-067-cascade-containment/) | Can deterministic checkpoints stop one AI agent's mistake from spreading through a chain of AI agents? | 🔴 **Negative — verified complete** |
| [**Experiment 068 — Adaptive Cyber Investigation Stopping**](experiments/experiment-068-adaptive-cyber-stopping/) | Can a security AI stop investigating before additional reasoning turns a correct answer into a wrong one? | 🔴 **Negative — verified complete** |

These three experiments are scientifically complete and independently verified. Their negative determinations are retained as first-class results; any redesign requires a new protocol.

### Selected Completed / High-Value Results

| Experiment | Simple purpose | Status |
|---|---|---|
| [**001 — Safety-Gated TTA for Streaming APT Detection**](experiments/experiment-001-safety-gated-tta/) | Safely adapt an APT detector when incoming data changes. | 🟢 Defense-ready positive |
| [**003 — Retrieval-Conditioned CTI Compliance**](experiments/experiment-003-cti-evidence-retrieval/) | Give a CTI model the right relationship evidence before it answers. | 🟢 Defense-ready positive |
| [**004 — FalseCite-Code Citation Poisoning**](experiments/experiment-004-falsecite-code/) | Verify software references before an agent trusts them. | 🟢 Bounded defense-positive |
| [**005 — MoE Router Audit**](reports/moe_standing_committee/README.md) | Test whether MoE expert routing is stable and repeatable. | 🟢 Bounded positive |
| [**011 — HalluHard Source-Backed Verification**](reports/halluhard_source_verifier/) | Check hallucinated claims against authoritative sources. | 🟢 Bounded positive |
| [**050 — Deterministic Agent Defenses**](experiments/experiment-050-deterministic-agent-defenses/) | Stop unsafe agent package actions with deterministic verification. | 🟢 Lead bounded positive |
| [**051 — Security-Utility Agent Gates**](experiments/experiment-051-security-utility-agent-gates/) | Block bad actions without blocking useful work. | 🟢 Live-agent policy pass |
| [**052 — Tool-Boundary Provenance**](experiments/experiment-052-tool-boundary-provenance/) | Track where agent tool arguments came from before trusting them. | 🟢 Live-agent provenance pass |
| [**054 — Refusal Geometry Across Recurrent Depth**](experiments/experiment-054-refusal-geometry/) | Measure whether refusal-related internal directions stay stable across depth. | 🟢 Defense-ready bounded positive |
| [**056 — Model-Registry Identifier Hallucination**](experiments/experiment-056-model-registry-hallucination/) | Detect invented model/dataset identifiers before code trusts them. | 🔵 Live pilot positive; full study pending |

### Portfolio at a Glance

The repository currently catalogs **68 numbered experiments** spanning APT detection, CTI, agentic AI security, deterministic verification, provenance, interpretability, test-time reasoning, model/software supply-chain security, federated learning, privacy, world models, robotics, and multimodal research.

For every experiment's **name, simple research purpose, status, and evidence link**:

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

```text
Pagan Praxis
├── README.md                  # front door / dashboard
├── experiments/              # polished canonical experiment landing pages
├── catalog/                  # canonical Experiment 001... numbering
├── final_praxis/             # completed final-series evidence
├── reports/                  # scientific reports and determinations
├── paper/                    # manuscript packages
├── configs/                  # frozen experiment configurations
├── scripts/                  # experiment and analysis code
├── cloud_jobs/               # AWS execution packages
└── runs/ / results/          # measured outputs
```

Historical filenames and PX identifiers are intentionally preserved so citations, hashes, reports, and scientific provenance do not break.

## Research Rule

**Scientific integrity is the success criterion.** Pagan Praxis does not require an experiment to be positive. Negative results and boundary conditions are retained, and a result is promoted only to the strength supported by its evidence.

## Legacy and Provenance

The original research history remains available through [EXPERIMENTS.md](EXPERIMENTS.md) and the [legacy HTML tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html). New public-facing work should use the canonical **Experiment ###** identifier.
