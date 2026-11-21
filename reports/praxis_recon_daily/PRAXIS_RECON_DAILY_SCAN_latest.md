# Praxis Recon Daily Literature Scan

Generated: 2026-11-21 17:48 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 9 | Adaptive evaluation of deterministic agent defenses | 2026-11-19 | TriageGPT for DataOps: Large Language Models as Intelligent Incident Classification and Resolution Agents in Data Pipeline Operations | International Journal of Computing and Engineering | [source](https://doi.org/10.47941/ijce.4117) |
| 2 | 3 | Provenance-aware tool-boundary monitoring | 2026-11-20 | Taking a Pulse on How Generative AI is Reshaping the Software Engineering Research Landscape | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3864453) |
| 3 | 2 | Provenance-aware tool-boundary monitoring | 2026-11-19 | Does an Integrity-Gated Governance Observability Index Measure Reconstructability? A Simulation-Based Criterion-Validity Study of Agent Telemetry under Out-of-Specification Faults | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11552307/v1) |

## Triage Notes

### 1. TriageGPT for DataOps: Large Language Models as Intelligent Incident Classification and Resolution Agents in Data Pipeline Operations

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Prabhu Ravi, Rajesh Thondamanati
- Published: 2026-11-19
- Venue/type: International Journal of Computing and Engineering / article
- DOI: https://doi.org/10.47941/ijce.4117
- URL: https://doi.org/10.47941/ijce.4117
- Opportunity score: 9
- Matched tags: agent, benchmark, evaluation, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Purpose: This paper presents TriageGPT for DataOps, an architecture in which large language model agents classify data pipeline incidents, retrieve relevant context, and perform constrained autonomous remediation, in order to reduce the manual triage effort that drives incident duration and on-call fatigue. Methodology: TriageGPT combines a retrieval-augmented classification agent that assigns alerts to a data pipeline specific incident taxonomy, a tool-use resolution agent that invokes actions from a vetted, blast-radius-tiered action library, and an audit-logged guardrail layer that gates and can automatically roll back actions, paired with confidence-based human-in-the-loop escalation. We describe the architecture, algorithms and calibration policy, map the design to safety and governance guidance, and report a prototype evaluation on a benchmark pipeline with a fourteen-category taxonomy, 2,800 labeled synthetic incidents and a twelve-week comparative deployment trial. Findings: TriageGPT achieved 94.3 percent top-one classification accuracy and 95.1 percent factual attribution accuracy with retrieval, against 68.4 percent without it. It resolved 71.5 percent of test incidents without human intervention at an incorrect-action rate of 0.6 percent, every one of which the guardrail caught and reversed. In the deployment trial it reduced median time to resolution from 41 minute

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Taking a Pulse on How Generative AI is Reshaping the Software Engineering Research Landscape

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Bianca Trinkenreich, Fabio Calefato, Kelly Blincoe, Viggo Tellefsen Wivestad, et al.
- Published: 2026-11-20
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3864453
- URL: https://doi.org/10.1145/3864453
- Opportunity score: 3
- Matched tags: verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Context: Software engineering (SE) researchers increasingly study Generative AI (GenAI) while also incorporating it into their own research practices. Despite rapid adoption, there is limited empirical evidence on how GenAI is used in SE research and its implications for research practices and governance. Aims: We conduct a large-scale survey of 456 SE researchers publishing in top venues (2023–2025). Method: Using quantitative and qualitative analyses, we examine who uses GenAI and why, where it is used across research activities, and how researchers perceive its benefits, opportunities, challenges, risks, and governance. Results: GenAI use is widespread, with many researchers reporting pressure to adopt and align their work with it. Usage is concentrated in writing, data processing, and analysis, while goal formulation and study design remain largely human-driven. Although productivity gains are widely perceived, concerns about trust, correctness, and regulatory uncertainty persist. Researchers highlight risks such as inaccuracies and bias, emphasize mitigation through human oversight and verification, and call for clearer governance, including guidance on responsible use and peer review. Conclusion: We provide a fine-grained, SE-specific characterization of GenAI use across research activities, along with taxonomies of GenAI use cases for research and peer review, opportunit

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Does an Integrity-Gated Governance Observability Index Measure Reconstructability? A Simulation-Based Criterion-Validity Study of Agent Telemetry under Out-of-Specification Faults

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Ravi Shankar NRK
- Published: 2026-11-19
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11552307/v1
- URL: https://doi.org/10.21203/rs.3.rs-11552307/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Governance of agentic AI systems depends on execution evidence: an operator can judge whether an agent stayed within its authority only if its telemetry allows what it did to be reconstructed. The Governance Observability Index (GOI) proposes to measure this as a gated geometric mean of coverage, fidelity, integrity and timeliness, with an integrity gate intended to stop untrustworthy evidence being masked by completeness elsewhere. This simulation study tests one implementation of the index against criteria computed from complete ground truth, of which the estimator sees only a 40-record ledger sample. A seeded testbed simulates a scripted payments agent, a policy gateway, an authoritative ledger and an HMAC-chained telemetry stream. The estimator uses only the stream, a gateway control total and a 40-record ledger sample. Twelve fault families—four within the original specification, four outside it and four benign infrastructure perturbations—are evaluated in 2,520 single-family runs and 1,000 mixed runs. GOI correlates with reconstruction accuracy (Spearman ρ = 0.85, 95% CI 0.83–0.87) and separates degraded from sound reconstructions (AUC 0.93). It is weaker as a warning of missed time-sensitive violations (AUC 0.87), and 63% of runs scoring at least 0.90 had degraded reconstructions. The integrity gate, as implemented, never activated in the mixed runs. A 5% forgery by a ke

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

