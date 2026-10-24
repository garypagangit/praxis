# Praxis Recon Daily Literature Scan

Generated: 2026-10-24 14:08 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-10-22 | ExpLinux: Reproducible Linux kernel exploit labs from public CVE disclosures | Array | [source](https://doi.org/10.1016/j.array.2026.101369) |
| 2 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-10-23 | Trustworthy Swarm Intelligence for Green IoT: Communication-Efficient and Safe Multi-Agent Synchronization across the Cloud-Edge Continuum | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11241701/v1) |

## Triage Notes

### 1. ExpLinux: Reproducible Linux kernel exploit labs from public CVE disclosures

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mohammad Dashti
- Published: 2026-10-22
- Venue/type: Array / article
- DOI: https://doi.org/10.1016/j.array.2026.101369
- URL: https://doi.org/10.1016/j.array.2026.101369
- Opportunity score: 7
- Matched tags: agent, evaluation, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Public proof-of-concept exploits for Linux kernel privilege-escalation vulnerabilities often depend on undocumented environmental assumptions, limiting their reproducibility. This paper presents ExpLinux , a methodology and framework for converting public vulnerability artifacts into reproducible, mitigation-aware exploitation labs. A five-stage process (import, assess, develop, harden, and promote) combines scripted tools with a large language model agent that assesses and ports public exploits under human supervision. Each lab pins its kernel image and configuration, root filesystem, mitigation profile, and required modules. Replay checks and author verification assess the resulting artifact. Three reproducibility contracts distinguish repeated bug effects, stable serial-log digests, and a scripted build procedure with a recorded trigger observation. A seven-category taxonomy organizes exploitation primitives and supports the agent’s knowledge base. The evaluation includes ten validated labs and one scaffolded lab across kernel versions 5.15–6.18. Selected replay experiments show identical bug-effect bytes despite environmental log variation; a minimal-initrd lab produces a stable log digest, while an exploit with a post-success kernel panic is assessed under the build-procedure contract. Retrospective estimates for five validated labs range from 2.4 to 29.5 h, with porting a

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Trustworthy Swarm Intelligence for Green IoT: Communication-Efficient and Safe Multi-Agent Synchronization across the Cloud-Edge Continuum

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Bindiya Jain, Ravikant Gupta, Hemant Kumar Upadhyay
- Published: 2026-10-23
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11241701/v1
- URL: https://doi.org/10.21203/rs.3.rs-11241701/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> No abstract text returned by metadata API.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

