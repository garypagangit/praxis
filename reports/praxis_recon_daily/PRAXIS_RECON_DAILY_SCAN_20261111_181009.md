# Praxis Recon Daily Literature Scan

Generated: 2026-11-11 18:10 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 5

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Adaptive evaluation of deterministic agent defenses | 2026-11-10 | Fail-Closed Authorization for Tool-Using AI Agents: A Capability Contract and Case Study | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11676427/v1) |
| 2 | 6 | Adaptive evaluation of deterministic agent defenses | 2026-11-10 | Authorization assurance for tool-using LLM agents: a structured review of enforcement semantics and effect-level security evidence | International Journal of Information Security | [source](https://doi.org/10.1007/s10207-026-01343-w) |
| 3 | 6 | Provenance-aware tool-boundary monitoring | 2026-11-10 | Toward Resilient Explainable AI–Digital Twin Frameworks for Cyber-Secure Renewable Energy Systems: An Uncertainty-Aware Lifecycle-Integrated Architecture | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11659132/v1) |
| 4 | 5 | Provenance-aware tool-boundary monitoring | 2026-11-09 | Algorithmic riba and algorithmic Shariah non-compliance: risk mechanisms and a proposed governance protocol for Islamic banks | AI and Ethics | [source](https://doi.org/10.1007/s43681-026-01497-2) |
| 5 | 4 | Agentic package hallucination and tool-boundary gates | 2026-11-09 | LLM ‐Based Domain Model Extraction From Requirements: A Case Study on Smart Tourism Applications | Expert Systems | [source](https://doi.org/10.1111/exsy.70479) |

## Triage Notes

### 1. Fail-Closed Authorization for Tool-Using AI Agents: A Capability Contract and Case Study

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Andrey Lesnikov
- Published: 2026-11-10
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11676427/v1
- URL: https://doi.org/10.21203/rs.3.rs-11676427/v1
- Opportunity score: 10
- Matched tags: agent, security, tool call
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract For tool-using LLM agents the decisive question is whether a concrete tool call is authorized before it executes. We describe the Agent Security Contract (ASC), a deny-by-default, pre-execution gate for agent and MCP tool calls. An ASC policy pins a SHA-256 digest of the approved tool catalog, declares per-agent tool allowlists with argument constraints, marks high-impact tools that require out-of-band approval, and bounds call rates; each decision (ALLOW, BLOCK, REQUIRE_APPROVAL) is emitted as an integrity-checked (unkeyed) JSON evidence envelope, and every error path we enumerate and test resolves to BLOCK. We evaluate the open-source implementation on static, recorded tool-call traces only; no live agent is run. Bypasses of the v0.1.0 demo policy found in review were fixed in v0.2.0; on a 60-case adversarial probe, allowed attacks fall from 32 to 1 (a policy gap), at the cost of 3 new benign over-blocks. On the author-constructed 66-scenario v0.2.1 corpus, designed around these checks, ASC returns the expected verdict in 66/66 cases; tool-name RBAC (Python and OPA/Rego) admits 30 of its 33 attacks by construction, and mutation testing shows the corpus exercises few policy constraints (8 of 62 single-constraint mutants killed). As a held-out check we replay 132 AgentDojo v1.2 ground-truth traces under policies frozen beforehand. With tool-level approval policies, 25 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Authorization assurance for tool-using LLM agents: a structured review of enforcement semantics and effect-level security evidence

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mohamed Abbas Elmasry
- Published: 2026-11-10
- Venue/type: International Journal of Information Security / article
- DOI: https://doi.org/10.1007/s10207-026-01343-w
- URL: https://doi.org/10.1007/s10207-026-01343-w
- Opportunity score: 6
- Matched tags: agent, dataset, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Tool-using large language model (LLM) agents exercise authority over protected resources through APIs, tools, credentials, and external services. This structured review asks whether authorization claims are supported at the enforcement and observation boundaries relevant to the claimed effect. A 75-source evidence library was screened into a 30-source analytical corpus (15 strict agent sources, 6 sensitivity sources, and 9 authorization/assurance comparators), yielding 92 Source-Claim Records. Within this closed corpus, five strict sources made mediation or non-bypassability claims with heterogeneous evidence endpoints; all three evaluable least-privilege sources narrowed available authority without measuring trajectory-wide effective privilege; no evaluable revocation claim appeared among 21 agent-focused sources; and no delegation-containment claim appeared in the 30-source corpus. Final-state correctness was also distinct from authorization correctness. We integrate these findings through an Authorization Assurance Claim Model linking claim scope, obligations, enforcement, evidence, protected effect, and residual assumptions. The resulting MAAP is presented as a preliminary, review-derived minimum reporting framework, not a validated scoring or certification instrument. The supplementary workbook provides the screening decisions, complete coding dataset, source-prop

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Toward Resilient Explainable AI–Digital Twin Frameworks for Cyber-Secure Renewable Energy Systems: An Uncertainty-Aware Lifecycle-Integrated Architecture

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Nasir Dr. Muhammad Nasir Uddin
- Published: 2026-11-10
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11659132/v1
- URL: https://doi.org/10.21203/rs.3.rs-11659132/v1
- Opportunity score: 6
- Matched tags: agent, interpretability, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract The accelerating penetration of variable renewable energy sources into modern power systems demands digital infrastructures capable of supporting predictive, autonomous, and trustworthy grid operation. While digital twins (DT) and artificial intelligence (AI)—particularly multi-agent and agentic architectures—are key enablers, their integration remains fragmented across three critical dimensions: explainability, cybersecurity, and uncertainty management. This paper proposes a conceptual, uncertainty-aware, lifecycle-integrated architecture that couples explainable AI (XAI) with digital twin modeling to support resilient, cyber-secure renewable energy operations. Based on a structured review spanning component-, building-, and urban-scale DT infrastructure, XAI-driven forecasting and fault diagnosis, distributed energy resource (DER) multi-agent control, and DER cybersecurity vulnerabilities, we identify a persistent scholarly disjunction. Few studies treat interpretability, adversarial resilience, and stochastic uncertainty as co-design requirements across the entire asset lifecycle. Using a design-science methodology and thematic synthesis, we develop a five-layer architecture: sensing and data acquisition, digital twin simulation, XAI-mediated agentic decision-making, cybersecurity and resilience, and lifecycle governance. The core contribution lies in defining the s

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Algorithmic riba and algorithmic Shariah non-compliance: risk mechanisms and a proposed governance protocol for Islamic banks

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Mohamed Shareef, Ismail Nizam
- Published: 2026-11-09
- Venue/type: AI and Ethics / article
- DOI: https://doi.org/10.1007/s43681-026-01497-2
- URL: https://doi.org/10.1007/s43681-026-01497-2
- Opportunity score: 5
- Matched tags: benchmark, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Machine learning (ML) systems are increasingly used in the credit, pricing, and collections decisions of financial institutions, including Islamic banks, yet Shariah oversight remains primarily contract-centred. This conceptual paper identifies three distinct pathways of algorithmic Shariah non-compliance. Algorithmic riba, used narrowly, concerns profit-rate models whose optimisation objective may reproduce the time-value logic prohibited by riba; conventional benchmarking of murabahah (cost-plus sale) margins is not itself impermissible. Algorithmic injustice concerns credit-scoring outcomes that may violate the ‘adl (justice) obligation, and algorithmic gharamah (penalty) concerns collections systems that may impose charges beyond ​ta’widh (compensation for documented loss). To support model-level review, we propose the Shariah Algorithmic Compliance Screen (SACS), a five-component protocol grounded in Maqasid al-Shariah and offered as a first-iteration design proposal. Model owners disclose use cases, training data, objective functions, and outputs; independent technical validators test the relevant model evidence; and Shariah Supervisory Boards (SSBs) determine compliance. Explainable artificial intelligence (XAI) methods are used descriptively, while established fairness diagnostics (subgroup calibration, error-rate comparison, and disparate-impact measurement) p

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. LLM ‐Based Domain Model Extraction From Requirements: A Case Study on Smart Tourism Applications

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Hamza Abdelmalek, Adnane Souha, Charaf Ouaddi, Lamya Benaddi, et al.
- Published: 2026-11-09
- Venue/type: Expert Systems / article
- DOI: https://doi.org/10.1111/exsy.70479
- URL: https://doi.org/10.1111/exsy.70479
- Opportunity score: 4
- Matched tags: future research
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> ABSTRACT Automating the extraction of domain models from natural language requirements remains a central challenge in model‐driven engineering (MDE), particularly at the level of the computation‐independent model (CIM), the most abstract layer of the model‐driven architecture (MDA). This paper introduces an approach that uses large language models (LLMs) to generate domain models from software requirements. Unlike prior work that relies on a single monolithic prompt or on generic task decomposition, our approach organises the modelling task as a modular chain of prompts with dedicated stages for enumerations, entities, and relationships, each producing an explicit intermediate output that feeds the next stage before a final consolidation step. The approach is implemented as a Visual Studio Code extension called SmartModel, which integrates generation, visualisation, and requirement‐level traceability into the developer's environment. To evaluate the approach, a case study on smart tourism software requirements was conducted, comparing the LLM‐generated domain model with an expert‐constructed reference model using both qualitative expert assessments and quantitative metrics. Results show that LLMs achieve high precision in identifying entities and enumerations, whereas relationship and attribute extraction remain considerably less reliable and require systematic human review. Th

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

