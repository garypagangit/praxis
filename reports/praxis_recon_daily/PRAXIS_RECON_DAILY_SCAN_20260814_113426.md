# Praxis Recon Daily Literature Scan

Generated: 2026-08-14 11:34 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 1

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 9 | Adaptive evaluation of deterministic agent defenses | 2026-08-12 | CAPS: Compositional Attack Path Scoring for LLM Deployment Stacks | Artificial Intelligence and Applications | [source](https://doi.org/10.47852/bonviewaia620210609) |

## Triage Notes

### 1. CAPS: Compositional Attack Path Scoring for LLM Deployment Stacks

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Quang-Vinh Dang, Hoang-Viet Vu, Ngoc-Son-An Nguyen, Minh Ngoc Dinh, et al.
- Published: 2026-08-12
- Venue/type: Artificial Intelligence and Applications / article
- DOI: https://doi.org/10.47852/bonviewaia620210609
- URL: https://doi.org/10.47852/bonviewaia620210609
- Opportunity score: 9
- Matched tags: agent, benchmark, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Evaluating the security posture of large language model (LLM) deployment stacks is a critical challenge in modern AI security. Traditional vulnerability management frameworks—such as the Common Vulnerability Scoring System (CVSS) and component-level checklists—assume that software components can be evaluated in isolation. In real-world agentic and retrieval-augmented generation (RAG)-based LLM ecosystems, this assumption is systematically violated: attackers exploit complex topologies, chaining seemingly low–risk vulnerabilities (e.g., indirect prompt injection) with downstream tools (e.g., SQL execution) to achieve catastrophic compromises. Applying independent scoring methods to deeply integrated stacks therefore yields inflated risk assessments, misaligned mitigation priorities, and a failure to capture compositional attack paths. We propose Compositional Attack Path Scoring (CAPS), a framework engineered to quantify end-to-end multi-hop risks in LLM architectures. CAPS integrates three capabilities: (i) directed graph topological modeling, which maps the deployment stack from attacker entry points to high-value assets; (ii) dynamic mitigation attenuation, which calculates the “Effective Exploitability” of nodes based on deployed guardrails; and (iii) a compositional path engine that scores risk via an explicit exponential decay factor reflecting the friction of traversing t

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

