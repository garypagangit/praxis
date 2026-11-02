# Praxis Recon Daily Literature Scan

Generated: 2026-11-02 20:32 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 1

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 18 | Cyber threat intelligence evidence routing | 2026-10-31 | ThreatFusion AI: AI-Powered Cyber Threat Intelligence Fusion Platform Using Graph Memory and MITRE ATT&CK | Journal of Integrated Engineering Sciences | [source](https://doi.org/10.63686/jies.v2i4040) |

## Triage Notes

### 1. ThreatFusion AI: AI-Powered Cyber Threat Intelligence Fusion Platform Using Graph Memory and MITRE ATT&CK

- Topic: Cyber threat intelligence evidence routing
- Authors: Anshul Vairagade, Jay gurav, Mukul Suryawanshi, Vedant Sayare, et al.
- Published: 2026-10-31
- Venue/type: Journal of Integrated Engineering Sciences / article
- DOI: https://doi.org/10.63686/jies.v2i4040
- URL: https://doi.org/10.63686/jies.v2i4040
- Opportunity score: 18
- Matched tags: MITRE ATT&CK, agent, cyber threat intelligence, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Analyst burnout in security operations centers is not mainly a volume problem. It is a structure problem. Logs from endpoints, cloud services, and network devices sit in one tool, while the threat intelligence that would make sense of those logs sits in five or six others. An analyst chasing a suspicious IP typically opens Virus Total, OTX, and a few OSINT feeds manually before getting an answer, and that workflow breaks quickly when the queue has twenty open cases. ThreatFusion AI addresses this at the architecture level. We built a temporal knowledge graph that holds internal telemetry, open-source threat feeds, and MITRE ATT&CK technique mappings in one queryable structure. A team of specialized LLM agents works against that graph to check whether an indicator or behavior pattern has appeared before and which campaign it might belong to. Before any automated containment step executes, a dedicated guardrail agent validates it against policy rules. Low-risk steps go through SOAR automatically; anything higher-impact waits for a human analyst. This paper describes the six-layer architecture, the reasoning behind each design decision, and the evaluation methodology we are running against simulated attack traffic.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

