# Praxis Recon Daily Literature Scan

Generated: 2026-11-13 18:11 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 24 | Provenance-aware tool-boundary monitoring | 2026-11-11 | Runtime Security Monitoring and Continuous Assurance for AI Agents: An Integrative Review and Systems-Management Framework | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11422609/v1) |
| 2 | 4 | Provenance-aware tool-boundary monitoring | 2026-11-11 | AI Agents and Agentic AI in Medicine: An Autonomy-Centred Scoping Review and Research Agenda | Research Square | [source](https://doi.org/10.21203/rs.3.rs-10652827/v1) |
| 3 | 3 | Adaptive evaluation of deterministic agent defenses | 2026-11-12 | Can the Confidence and Decisions of System 1 Models Be Trusted? An Explainability and Perturbation Audit of JevStyle Decision Models | Unknown venue | [source](https://doi.org/10.66977/xsci.2611.001v) |

## Triage Notes

### 1. Runtime Security Monitoring and Continuous Assurance for AI Agents: An Integrative Review and Systems-Management Framework

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Yaswanth Reddy Vada, Aashrith Mannuru, Krishna Varsha Mummadireddy, Nitya Santhoshini Vada, et al.
- Published: 2026-11-11
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11422609/v1
- URL: https://doi.org/10.21203/rs.3.rs-11422609/v1
- Opportunity score: 24
- Matched tags: agent, agent security, benchmark, evaluation, provenance, security, verification, verifier
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Large language model (LLM) agents increasingly operate as long-lived software actors that plan, invoke tools, access enterprise data, maintain memory, and delegate work. Their security posture can therefore change after deployment as task context, external content, tools, credentials, memory, model versions, and peer agents change. Pre-deployment evaluation alone cannot establish that an agent remains safe during execution. This paper presents a structured integrative review of runtime verification, continuous security monitoring, AI-agent security benchmarks, runtime guardrails, and autonomous-systems assurance, and synthesizes these literatures into a Runtime Security Monitoring and Continuous Assurance (RSMCA) framework for AI agents. The review distinguishes observability, runtime monitoring, runtime enforcement, and continuous assurance as related but non-equivalent functions. It identifies eight runtime monitoring surfaces: identity and configuration, input/context, task and planning state, tool invocation, data/egress, memory and retrieval, inter-agent delegation, and external dependencies. RSMCA represents each agent action as a correlated security event, evaluates it using complementary deterministic, semantic, verifier-based, and probabilistic monitors, and maps monitor output to graduated responses ranging from allow-with-audit to step-up approval, blocking,

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. AI Agents and Agentic AI in Medicine: An Autonomy-Centred Scoping Review and Research Agenda

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Valentina De Nicolò, Davide La Torre, Ignazio Iacone
- Published: 2026-11-11
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-10652827/v1
- URL: https://doi.org/10.21203/rs.3.rs-10652827/v1
- Opportunity score: 4
- Matched tags: agent, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Artificial intelligence agents—software systems that perceive, reason, plan and act over multiple steps with limited human intervention—are moving from research prototypes towards clinical deployment. Recent reviews map what has been built; this one asks what would have to hold for such systems to be deployed safely. We conducted a scoping review reported according to the PRISMA extension for scoping reviews, searching eight bibliographic sources from January 2017 to June 2026, admitting foundational computer science and regulatory literature alongside clinical applications. Five architectural paradigms recur—tool-augmented large language model agents, multi-agent systems, offline reinforcement learning agents, embodied robotic agents and autonomous monitoring agents—nearly all sharing a common four-layer stack. We introduce a six-level scale of clinical agent autonomy that grades systems by where human judgement enters relative to the reasoning, and by whether the resulting action remains reversible. The scale exposes an inversion in the evidence base: demonstrated patient benefit concentrates at high autonomy in narrow, bounded domains, whereas research effort concentrates at intermediate autonomy, where prospective outcome evidence is absent and automation bias is the dominant risk. We further propose seven evaluation dimensions specific to agency, a mapping of eval

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Can the Confidence and Decisions of System 1 Models Be Trusted? An Explainability and Perturbation Audit of JevStyle Decision Models

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Julien Delaunay
- Published: 2026-11-12
- Venue/type: Unknown venue / preprint
- DOI: https://doi.org/10.66977/xsci.2611.001v
- URL: https://doi.org/10.66977/xsci.2611.001v
- Opportunity score: 3
- Matched tags: benchmark
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> "System 1" decision models (pioneered by TypeSafe AI's Jev) replace autoregressive text generation with a single forward pass returning typed probability distributions over declared schemas (Choice, Score, Noul). While deployed for low-latency routing and automated triage, their statistical calibration and post-hoc explainability remain uncharacterized. We introduce an open, deterministic audit benchmark evaluating System 1 decision models across calibration under label-preserving perturbations, cross-question interference, and post-hoc attribution faithfulness. Evaluating five open-weight models (0.8B to 27B) alongside generative System 2 baselines -- both single-token logprob scoring and structured JSON/CoT decoding -- across NLI (e-SNLI), adversarial syntactic shortcuts (HANS), synthetic clinical triage (N=900), prompt injection defense (Tensor Trust, N=250), and an 86-case logic-gate trigger suite yields five findings: (1) provider confidence is an exact closed-form dispersion transform (1 - H(p)/ln K on sub-10B models; normalized margin on Clef-27B) rather than empirical accuracy; (2) bundling multiple questions in one request induces directional cross-question interference (11.7% to 22.4% binary flips on Tev1-0.8B, vs. 0.1% to 0.2% on Tev1-4B); (3) System 1 models with >= 4B parameters are faster and better calibrated under syntactic shifts (ECE_w = 0.030 to 0.087) than l

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

