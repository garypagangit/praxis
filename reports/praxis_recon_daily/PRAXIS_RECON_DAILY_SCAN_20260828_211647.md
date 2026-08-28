# Praxis Recon Daily Literature Scan

Generated: 2026-08-28 21:16 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Cyber threat intelligence evidence routing | 2026-08-26 | Intelligent interactive honeypots: A systematization of AI-driven cyber deception | Computer Science Review | [source](https://doi.org/10.1016/j.cosrev.2026.101053) |
| 2 | 5 | Adaptive evaluation of deterministic agent defenses | 2026-08-26 | RobustAgent: Provable Recovery Guarantees for Long-Running Autonomous Agents Under Adversarial Interrupts | Cureus Journal of Computer Science. | [source](https://doi.org/10.7759/s44389-026-00248-y) |

## Triage Notes

### 1. Intelligent interactive honeypots: A systematization of AI-driven cyber deception

- Topic: Cyber threat intelligence evidence routing
- Authors: Steve Nyamwaya, Sajad Khorsandroo, Mahmoud Abdelsalam, Elisa Bertino
- Published: 2026-08-26
- Venue/type: Computer Science Review / article
- DOI: https://doi.org/10.1016/j.cosrev.2026.101053
- URL: https://doi.org/10.1016/j.cosrev.2026.101053
- Opportunity score: 10
- Matched tags: dataset, evaluation, future research, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This Systematization of Knowledge (SoK) examines the evolving landscape of intelligent, interactive honeypots, which are deception-based cybersecurity tools that utilize AI/ML to engage attackers proactively. We introduce a novel taxonomy linking interaction levels to Cyber Kill Chain stages and systematically analyze peer-reviewed studies. Our findings expose key design trends, empirical evaluation strategies, and highlight critical research gaps, including scalability, standardization, and dataset diversity. We discuss the roles of LLMs and reinforcement learning, together with the emerging use of federated learning, in advancing honeypot realism and interactivity. This work aims to guide future research in developing adaptive, resilient deception systems for next-generation cyber defense.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. RobustAgent: Provable Recovery Guarantees for Long-Running Autonomous Agents Under Adversarial Interrupts

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Rahul Singh, Amit Shrivastav
- Published: 2026-08-26
- Venue/type: Cureus Journal of Computer Science. / article
- DOI: https://doi.org/10.7759/s44389-026-00248-y
- URL: https://doi.org/10.7759/s44389-026-00248-y
- Opportunity score: 5
- Matched tags: agent, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Long-running autonomous agents face a critical challenge: maintaining correct state and recovering gracefully when interrupted by adversarial attacks or system failures.We present RobustAgent, a framework that integrates and formalizes checkpoint-based recovery with cryptographic verification to provide provable robustness guarantees for stateful autonomous agents.Our key contributions include: (1) formal definitions of state consistency and recovery correctness for persistent agents, (2) adaptive checkpointing with a capped exponentialbackoff schedule that bounds the replay window while minimizing per-checkpoint storage through incremental delta encoding, (3) binarysearch recovery over a root-validated hash chain with O(|S|(log n + k)) total time complexity, and (4) resistance to time-shifted prompt injection attacks.Experimental validation on more than 500 synthetic agent workflows demonstrates a 100% recovery success rate, 82.6× faster recovery than naive restart (0.39 ms vs. 32.2ms), 75.2% attack detection, and a 96.5% storage reduction compared to naive periodic checkpointing, reflecting a deliberate storage-recovery trade-off relative to fixed-interval baselines.This work provides a theoretical foundation and practical implementation for deploying autonomous agents in production environments requiring formal robustness guarantees.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

