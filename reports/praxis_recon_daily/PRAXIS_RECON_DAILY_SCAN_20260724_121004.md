# Praxis Recon Daily Literature Scan

Generated: 2026-07-24 12:10 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 1

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 9 | Adaptive evaluation of deterministic agent defenses | 2026-07-22 | TRACER-AI: A Multi-Layer Explainable Framework for Prompt Injection, Agent Goal Hijacking, and Tool Misuse Detection in Agentic AI Systems | International Journal for Research in Applied Science and Engineering Technology | [source](https://doi.org/10.22214/ijraset.2026.84360) |

## Triage Notes

### 1. TRACER-AI: A Multi-Layer Explainable Framework for Prompt Injection, Agent Goal Hijacking, and Tool Misuse Detection in Agentic AI Systems

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Pallavi Singh, Khushboo Gupta, Pratibha Singh
- Published: 2026-07-22
- Venue/type: International Journal for Research in Applied Science and Engineering Technology / article
- DOI: https://doi.org/10.22214/ijraset.2026.84360
- URL: https://doi.org/10.22214/ijraset.2026.84360
- Opportunity score: 9
- Matched tags: agent, benchmark, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large language model (LLM) agents extend generative models with planning, memory, and external tool access, but this capability creates a security path in which untrusted content can alter instructions, hijack an agent's operational goal, and trigger harmful tool actions. This paper proposes TRACER-AI, a four-layer explainable defense-in-depth framework that combines (i) semantic prompt-injection detection, (ii) continuous goal-integrity monitoring, (iii) contextual tool-risk control, and (iv) structured explainable security decisions. The framework is designed around the attack progression prompt injection -&gt; goal hijacking -&gt; tool misuse rather than treating prompt filtering as the only enforcement boundary. A dynamic risk score fuses prompt-injection probability, goal deviation, tool risk, and contextual anomaly before action execution. A controlled proof-ofconcept evaluation was conducted on a 3,500-case synthetic adversarial testbed containing benign interactions and five attack families: direct prompt injection, indirect prompt injection, goal hijacking, tool misuse, and chained attacks. The held-out test set comprised 1,050 cases with previously unseen attack wording and benign security-text decoys. The standalone prompt detector achieved 0.679 accuracy, 0.575 F1-score, and 0.760 ROC-AUC, illustrating the weakness of relying on prompt detection alone under distribu

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

