# Praxis Recon Daily Literature Scan

Generated: 2026-09-05 13:35 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 6 | Adaptive evaluation of deterministic agent defenses | 2026-09-03 | SOC-in-a-Box: A Multi-Agent LLM-Based Security Operations Center for Threat Detection and Automated Incident Response | International Research Journal on Advanced Engineering Hub (IRJAEH) | [source](https://doi.org/10.47392/irjaeh.2026.0684) |
| 2 | 4 | Adaptive evaluation of deterministic agent defenses | 2026-09-03 | Beyond Prompt Injection: Trust-Boundary Security Assurance for LLM-Integrated and Agentic Applications | Research Square | [source](https://doi.org/10.21203/rs.3.rs-10798245/v1) |

## Triage Notes

### 1. SOC-in-a-Box: A Multi-Agent LLM-Based Security Operations Center for Threat Detection and Automated Incident Response

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Disha S, Pallavi U, Devika Krishnan A
- Published: 2026-09-03
- Venue/type: International Research Journal on Advanced Engineering Hub (IRJAEH) / article
- DOI: https://doi.org/10.47392/irjaeh.2026.0684
- URL: https://doi.org/10.47392/irjaeh.2026.0684
- Opportunity score: 6
- Matched tags: agent, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Modern Security Operations Centres struggle with overwhelming alert volumes, chronic analyst shortages, and slow incident response times. This paper presents SOC-in-a-Box, a multi-agent prototype that automates the three core SOC functions—detection, investigation, and response—using specialised AI agents powered by a large language model (LLM). The Sentry agent monitors log files and flags suspicious events using either LLM classification or a built-in rule engine. The Investigator agent gathers related evidence from across the log corpus and asks the LLM to produce a structured root-cause analysis. The Responder agent selects a policy-approved containment action, executes it in a simulated or live environment, and generates a structured Markdown incident report. All three agents run as lightweight Python threads connected through in-memory queues with no external message broker. When the LLM is unavailable, a deterministic fallback engine ensures the pipeline continues to operate. Evaluation across five attack categories—brute-force, data exfiltration, privilege escalation, port scanning, and malware deployment—shows complete detection coverage with end-to-end latency below 60 seconds on a standard laptop. The system demonstrates that a self-contained, locally deployable multi-agent architecture can meaningfully reduce manual effort in routine SOC workflows while preserving h

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Beyond Prompt Injection: Trust-Boundary Security Assurance for LLM-Integrated and Agentic Applications

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Nazar Waheed
- Published: 2026-09-03
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-10798245/v1
- URL: https://doi.org/10.21203/rs.3.rs-10798245/v1
- Opportunity score: 4
- Matched tags: agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> No abstract text returned by metadata API.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

