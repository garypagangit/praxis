# Praxis Recon Daily Literature Scan

Generated: 2026-11-08 16:48 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 8 | Agentic package hallucination and tool-boundary gates | 2026-11-06 | A multi-agent retrieval-augmented generation framework for pedagogical feedback on EFL student writing | Discover Artificial Intelligence | [source](https://doi.org/10.1007/s44163-026-02384-9) |
| 2 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-11-06 | DualTrust: Asymmetric Bayesian Reputation and Cryptographic Gating for Autonomous AI Agents | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11631847/v1) |
| 3 | 4 | Provenance-aware tool-boundary monitoring | 2026-11-06 | A machine learning framework for privacy-preserving financial risk assessment using explainable artificial intelligence and blockchain-based trust management | Frontiers in Blockchain | [source](https://doi.org/10.3389/fbloc.2026.1941258) |

## Triage Notes

### 1. A multi-agent retrieval-augmented generation framework for pedagogical feedback on EFL student writing

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Ning Chen
- Published: 2026-11-06
- Venue/type: Discover Artificial Intelligence / article
- DOI: https://doi.org/10.1007/s44163-026-02384-9
- URL: https://doi.org/10.1007/s44163-026-02384-9
- Opportunity score: 8
- Matched tags: agent, alignment, dataset, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> High-quality feedback can support writing development, yet producing it consistently at classroom scale remains difficult. Large language models generate fluent comments quickly, but their feedback can over-emphasise surface grammar, drift from the target rubric, assert errors not present in the essay, or disclose complete rewrites. We propose RUMAR, a retrieval-augmented framework for English-as-a-Foreign-Language writing feedback. RUMAR combines error detection and rubric-aware retrieval with a bounded Generation–Evaluation–Refinement loop comprising two language-model agents—a Generator and a Critic—and a deterministic refinement controller. The Critic evaluates candidate feedback against five explicitly anchored 1–5 criteria, and an aggregator organises accepted comments across Hattie’s feed-up, feed-back, and feed-forward layers. On the reported ASAP-AES and ELLIPSE evaluation, RUMAR has the highest observed point estimate in each automatic-metric column relative to the six implemented baselines. Descriptive expert ratings and a four-week trial with 80 B1–B2 learners at one institution also favour RUMAR among the automated systems compared. These findings are limited to the reported datasets, argumentative tasks, and automated comparators. The trial contains neither a human-teacher nor a no-feedback control, and the one-week delayed post-test cannot establish durable trans

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. DualTrust: Asymmetric Bayesian Reputation and Cryptographic Gating for Autonomous AI Agents

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Khairan Noor Fadhlillah
- Published: 2026-11-06
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11631847/v1
- URL: https://doi.org/10.21203/rs.3.rs-11631847/v1
- Opportunity score: 7
- Matched tags: agent, safety, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract The proliferation of Ambient Wearable Intelligence (AWI) ecosystems, spanning augmented reality glasses, smartwatches, and pervasive edge IoT actuators, is fundamentally transitioning human-AI interaction from explicit tactile commands to continuous, implicit background tool delegation. In these ambient environments, autonomous Large Language Model (LLM) agents are granted operational authority to invoke external APIs, reserve financial micro-quotas, and control physical actuators. However, existing safety guardrails depend on secondary LLM-as-a-judge classifiers that introduce prohibitive runtime latencies (400–850 ms) and recurring token expenses, while static role-based access control fails against continuous behavioral drift, memory backdoors, and interleaved salami-slicing exploits. We present DualTrust, an asymmetric Bayesian reputation and cryptographic gating runtime engineered for autonomous multi-agent containment. DualTrust enforces a decoupled principal-agent architecture that strictly isolates Human Principal Accountable Credit from Bayesian Agent Operational Standing. Agent behavior is continuously modulated via an asymmetric power-law slashing engine (Δβ ∝ (sev · c^2) · v_a^1.8) with instantaneous clean-streak reset, deterministic SHA-256 64-bucket striped concurrency locks, atomically locked rollback refunds, and an O(1) RAM sliding-window RFC 6962 Merk

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. A machine learning framework for privacy-preserving financial risk assessment using explainable artificial intelligence and blockchain-based trust management

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Sanjay Agal
- Published: 2026-11-06
- Venue/type: Frontiers in Blockchain / article
- DOI: https://doi.org/10.3389/fbloc.2026.1941258
- URL: https://doi.org/10.3389/fbloc.2026.1941258
- Opportunity score: 4
- Matched tags: dataset, interpretability
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Introduction Financial risk assessment requires models that jointly satisfy privacy, explainability, and decentralized trust, yet existing machine-learning approaches usually address these requirements in isolation. Methods This paper proposes the Privacy-Preserving Explainable Trust Framework (PP-ETF), integrating federated learning with differential privacy, post hoc SHAP and LIME explanations, and a permissioned distributed ledger for trust management. PP-ETF is evaluated on the German Credit and HELOC datasets against statistical models, centralized ensembles and deep networks, and privacy-preserving baselines. Results PP-ETF outperforms privacy-preserving baselines in AUC-ROC while remaining within 1.4%–1.6% of centralized deep-learning models. Reputation-based adversarial detection excludes a malicious participant within two communication rounds with a 3.2% false-positive rate. Explanation stability yields average cosine similarity of at least 0.87, and the ledger processes up to 480 transactions per second with 2.4 s finality latency. Discussion The results support the feasibility of jointly implementing privacy, interpretability, and decentralized trust under the evaluated conditions; they do not imply that the underlying trade-offs are eliminated. PP-ETF provides an end-to-end blueprint for effective, scalable, private, interpretable, and trustworthy risk-management sy

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

