# Praxis Recon Daily Literature Scan

Generated: 2026-09-03 14:45 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 6 | Adaptive evaluation of deterministic agent defenses | 2026-09-01 | Policy-Constrained Runtime Defense for Tool-Using AI Agents in Enterprise API Ecosystems | International Journal of Global Innovations and Solutions (IJGIS) | [source](https://doi.org/10.63412/ss28se48) |
| 2 | 2 | Provenance-aware tool-boundary monitoring | 2026-09-01 | Agent Guard: Kernel-Enforced Damage Boundaries for AI Agents via Human-Authorized Contracts | Research Square | [source](https://doi.org/10.21203/rs.3.rs-10865359/v1) |

## Triage Notes

### 1. Policy-Constrained Runtime Defense for Tool-Using AI Agents in Enterprise API Ecosystems

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Swapneswar Ray
- Published: 2026-09-01
- Venue/type: International Journal of Global Innovations and Solutions (IJGIS) / article
- DOI: https://doi.org/10.63412/ss28se48
- URL: https://doi.org/10.63412/ss28se48
- Opportunity score: 6
- Matched tags: agent, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Tool-using AI agents can invoke internal APIs, retrieve documents, update records, and coordinate enterprise workflows. These capabilities create a runtime security problem: an agent may select an unauthorized tool, hallucinate an endpoint, follow malicious instructions embedded in retrieved context, rely on poisoned memory, retry unsafe operations, or submit a schema-valid but policy-violating payload. This paper presents a policy-constrained runtime enforcement framework that intercepts each proposed action before execution and classifies it as allow, deny, or escalate. We implement a deterministic trace-driven simulator with five service domains, six user roles, six threat classes, benign and adversarial tasks, and four defense configurations. The evaluation isolates enforcement effectiveness by replaying identical seeded action traces across all configurations. Across 8,000 controlled workflow executions, the framework reduces adversarial attack success from 100.0% for an unconstrained agent, 72.2% for prompt-only controls, and 18.5% for static gateway rules to 0.2%. It achieves a 99.9% overall safe-outcome rate, 100.0% benign safe completion under simulated reviewer approval, a 4.8% benign false-positive rate, and a 24.9 ms median enforcement latency. Ablation results show that registry validation, authorization, retry governance, and intent checking directly reduce attack

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Agent Guard: Kernel-Enforced Damage Boundaries for AI Agents via Human-Authorized Contracts

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Dongxu Cui, Zhichao Gu, Ping Zheng, Wenshuai Xi, et al.
- Published: 2026-09-01
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-10865359/v1
- URL: https://doi.org/10.21203/rs.3.rs-10865359/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> No abstract text returned by metadata API.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

