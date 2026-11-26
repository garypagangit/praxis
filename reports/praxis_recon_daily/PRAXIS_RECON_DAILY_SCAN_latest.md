# Praxis Recon Daily Literature Scan

Generated: 2026-11-26 19:53 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 11

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 18 | Adaptive evaluation of deterministic agent defenses | 2026-11-24 | Before AI Agents Act: Policy-Gated Data Pipelines for Secure Enterprise Agentic AI | International Journal of Computer Applications | [source](https://doi.org/10.5120/ijca794c064e0835) |
| 2 | 11 | Provenance-aware tool-boundary monitoring | 2026-11-25 | svlang and svlang-lint: A Pure-Rust IEEE 1800-2023 SystemVerilog Compiler Front End and Semantic Static Analyzer for Hardware Design and Verification | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11813840/v1) |
| 3 | 9 | Agentic package hallucination and tool-boundary gates | 2026-11-25 | Trustworthy agentic AI systems: navigating the risks and governance of autonomous AI | Frontiers in Artificial Intelligence | [source](https://doi.org/10.3389/frai.2026.1984864) |
| 4 | 8 | Provenance-aware tool-boundary monitoring | 2026-11-25 | Generative AI for programme and module design: the need for human in the loop | Frontiers in Education | [source](https://doi.org/10.3389/feduc.2026.1961190) |
| 5 | 8 | Provenance-aware tool-boundary monitoring | 2026-11-25 | Deploying Production AI Agents in Enterprise Workflows: Observability, Grounding, and Measured Business Outcomes | International Research Journal on Advanced Engineering Hub (IRJAEH) | [source](https://doi.org/10.47392/irjaeh.2026.0755) |
| 6 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-11-25 | SafeComm-RAG: Safe and Communication-Efficient Multi-Agent Reinforcement Learning for Local LLM Based RAG Assistant | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11449249/v1) |
| 7 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-11-24 | Explainable Artificial Intelligence as a National Security Imperative in Modern Cybersecurity Systems | Cureus Journal of Computer Science. | [source](https://doi.org/10.7759/s44389-026-00388-1) |
| 8 | 4 | Provenance-aware tool-boundary monitoring | 2026-11-25 | Digital-Twin-Based Compliance Review of Financial Terminal Devices: A Reproducible Framework and Controlled Evaluation | Digital Technologies Research and Applications | [source](https://doi.org/10.54963/dtra.v5i4.103071) |
| 9 | 4 | Provenance-aware tool-boundary monitoring | 2026-11-24 | Risk-constrained human-in-the-loop repair of anti-money laundering policies: Temporal legal graphs, minimal revision, and finite-sample assurance | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11119310/v1) |
| 10 | 2 | Provenance-aware tool-boundary monitoring | 2026-11-24 | Artificial intelligence, new product development, and design: Towards a framework for artificial intelligence adoption in innovation research | International Journal of Management Reviews | [source](https://doi.org/10.1111/ijmr.70044) |
| 11 | 2 | Provenance-aware tool-boundary monitoring | 2026-11-24 | Cascading Insecurity in the Age of Artificial General Intelligence: An Integrated Societal-Security Framework for Geopolitics, Corporate Power, Social Stability, and Cybersecurity | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11737869/v1) |

## Triage Notes

### 1. Before AI Agents Act: Policy-Gated Data Pipelines for Secure Enterprise Agentic AI

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Ankush Ramprakash Gautam
- Published: 2026-11-24
- Venue/type: International Journal of Computer Applications / article
- DOI: https://doi.org/10.5120/ijca794c064e0835
- URL: https://doi.org/10.5120/ijca794c064e0835
- Opportunity score: 18
- Matched tags: adaptive attack, agent, provenance, safety, security, tool call
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Enterprise AI agents convert retrieved data into consequential tool calls, yet conventional data quality validation does not establish authority to mutate a resource.This paper specifies a policy-gated authorization boundary that checks schema, freshness, source provenance, tenant and tool scope, principal status, replay state, and risk-dependent approval before an external action.A deterministic Python prototype is compared against no pre-action checks and schema/freshness screening on 7,200 labeled synthetic proposals; seven single-control ablations and a separately generated 2,400-case stress set examine boundary and compound violations.The full gate returns 1,200 ALLOW, 5,400 DENY, and 600 REVIEW decisions in the primary suite, with no authorization that violates the stipulated policy; the quality-only baseline incorrectly allows 4,800 proposals.On the stress set, the full gate retains all 600 valid proposals and routes 300 approval-dependent cases to review, whereas the quality-only baseline incorrectly allows 1,500.Counterfactual removals expose the contribution of individual controls, while visual comparisons make the tradeoffs explicit.These findings establish consistency with authored synthetic policy rules, not resistance to adaptive attackers or end-to-end production safety.The proposed design separates trusted data assertions, independent policy decisions, and enfor

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. svlang and svlang-lint: A Pure-Rust IEEE 1800-2023 SystemVerilog Compiler Front End and Semantic Static Analyzer for Hardware Design and Verification

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Mayur Kubavat
- Published: 2026-11-25
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11813840/v1
- URL: https://doi.org/10.21203/rs.3.rs-11813840/v1
- Opportunity score: 11
- Matched tags: evaluation, provenance, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Purpose: Open-source static analysis for SystemVerilog (IEEE 1800-2023) and the Universal Verification Methodology (UVM, IEEE 1800.2-2020) is split between two incomplete tool classes. Concrete-syntax-tree (CST) linters check unelaborated tokens without resolving types, class specializations, or component hierarchies, while open-source RTL simulators elaborate synthesizable logic but omit large parts of object-oriented verification, constrained randomization, and UVM semantics. Methods: This paper presents svlang, a SystemVerilog (IEEE 1800-2023) front end and word-level RTL/SVA lowering library written in safe Rust (143,840 lines across 20 workspace crates, with zero external Cargo dependencies in the 12-crate compiler and lowering core). Built on top of svlang, svlang-lint provides a parallel semantic static analyzer, a CST repair engine, and a language server (dv-lsp). Ten differential parity gates verify preprocessing, lossless parsing, four-state constant evaluation, IEEE 1800 §§11.6/11.8 context-determined expression typing, UVM class specialization, and netlist lowering against the C++ Slang v12.1 reference compiler. On this elaborated model, svlang-lint executes 433 rule implementations (461 catalog entries across 20 categories) covering polynomial-time constraint interval and difference-bound cycle checks, class-lineage UVM objection and TLM-to-covergroup flow checks, 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Trustworthy agentic AI systems: navigating the risks and governance of autonomous AI

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Gregoris N. Mentzas
- Published: 2026-11-25
- Venue/type: Frontiers in Artificial Intelligence / article
- DOI: https://doi.org/10.3389/frai.2026.1984864
- URL: https://doi.org/10.3389/frai.2026.1984864
- Opportunity score: 9
- Matched tags: agent, alignment, benchmark, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial Intelligence is evolving from the passive content generation of Generative AI (GenAI) to Agentic AI (AgAI) systems which are increasingly characterized by autonomy, adaptability, and goal-driven reasoning. Unlike traditional GenAI, AgAI systems are capable of perception, planning, and independent action. This shift introduces a unique class of sociotechnical risks, including goal misalignment, cascading operational errors, and security vulnerabilities. This paper reviews the AgAI landscape, examines its architectural components (planning, memory, action, and multi-agent collaboration) and its transformative potential across key sectors such as healthcare, education, manufacturing, robotics, and software development. By analyzing existing corporate and regulatory governance frameworks, the paper identifies gaps in accountability, liability, and real-time intervention. We argue that establishing trustworthy AgAI requires a shift from regulating content to constraining autonomous consequences, and propose seven research and governance challenges focusing on dynamic alignment, responsibility attribution, verifiable specifications, and standardized benchmarks, to ensure AgAI systems remain aligned with human values.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Generative AI for programme and module design: the need for human in the loop

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Lamis F. Al-Qora’n, Amro Al-Said Ahmad, Neil Andrew Gordon, Ed de Quincey
- Published: 2026-11-25
- Venue/type: Frontiers in Education / article
- DOI: https://doi.org/10.3389/feduc.2026.1961190
- URL: https://doi.org/10.3389/feduc.2026.1961190
- Opportunity score: 8
- Matched tags: alignment, evaluation, future research
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Introduction The use of generative artificial intelligence (GenAI) has been increasingly common among higher education institutions; nevertheless, the role of GenAI in assisting academics in developing curriculum is less understood in comparison to the applications of GenAI among students. This research focuses on GenAI assisted postgraduate curriculum design and redesign through investigating the role of GenAI and human academic judgement. Methods The paper adopts a comparative qualitative case study approach to examine two cases of curriculum design using GenAI; one of these is the designing of postgraduate course programs at Keele University, United Kingdom, using Microsoft Copilot, while the other involves the designing and subsequent iteration of a Software Architecture module for the master's program at Philadelphia University, Jordan, using ChatGPT. Curriculum artefacts and process documents were used for the analysis, along with retrospective accounts where the original engagement with the GenAI was not available. Results The application of GenAI enabled the identification of topics, structuring of curricula, writing of descriptions for students, creation of syllabi, exercises, and projects. An academic review found modules titles unsuitable in the context, generic learning outcomes, assessment insufficiency in terms of depth and standards mappings which needed to be ve

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. Deploying Production AI Agents in Enterprise Workflows: Observability, Grounding, and Measured Business Outcomes

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Rahul Mittal
- Published: 2026-11-25
- Venue/type: International Research Journal on Advanced Engineering Hub (IRJAEH) / article
- DOI: https://doi.org/10.47392/irjaeh.2026.0755
- URL: https://doi.org/10.47392/irjaeh.2026.0755
- Opportunity score: 8
- Matched tags: agent, benchmark, tool call
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> LLM agents have evolved from demonstrations to enterprise applications in customer support, software engineering, document processing, and more. But more than benchmark accuracy is required to determine their production value. An agent could choose to use tools, access evidence, alter records, and/or repeat actions, and failures could be due to stale sources, weak authorization, non-convergent planning, duplicated writes, incomplete audit trails, or misleading measurement of outcomes. The paper suggests a five-layered architecture consisting of the following: Workflow plane, Bounded agent runtime, Grounding and knowledge layer, Observability and governance plane, Outcome-measurement control loop. It also creates a seven-level taxonomy of telemetry: sessions, planning steps, tool calls, retrieval, outputs, human interventions and population drift. Grounding is considered as an admission control: material assertions are required to be backed up by legitimate and up-to-date evidence or abstention and escalation. The business value is measured using controlled comparison, task stratification, quality review, intervention accounting and joint reporting of performance/cost. Field experiments show that the use of generative AI has the potential to boost speed, quality, and throughput, however, depending on the experience of the workers and the location of the task within the system's 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. SafeComm-RAG: Safe and Communication-Efficient Multi-Agent Reinforcement Learning for Local LLM Based RAG Assistant

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mohammad Reza Rezaee, Babak Heidari, Morteza Rezaei, Nor Asilah Wati Abdul Hamid, et al.
- Published: 2026-11-25
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11449249/v1
- URL: https://doi.org/10.21203/rs.3.rs-11449249/v1
- Opportunity score: 7
- Matched tags: agent, benchmark, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Local retrieval-augmented generation (RAG) Large Language Model (LLM) based assistants must decide not only what to retrieve, but also when retrieval is needed, how components should com- municate, and whether an action is permitted. We present SafeComm-RAG, a local controller with Retriever, Safety/Authorization, and Executor roles trained by multi-agent reinforcement learning under centralized training and decentralized execution. Each role selects a task action and a separate SEND/SILENT communication action, while a deterministic capability shield retains final authority over restricted operations. Training combines a competence-preserving warm start (C1), feasibility- aware communication pressure (C2), and counterfactual communication calibration with rollback (C3). On a shared 10,000-scenario benchmark over seven training seeds, C3 achieved 97.66 ± 0.22% task success, no observed executed safety violations, and 0.688 ± 0.131 communications per episode. It used 54.28% less communication than a selective heuristic and 77.07% less than always communicating. Ablations show that C1 is needed for competence and C3 cuts communication by 54.26% relative to no- C3 with almost unchanged success; C2 did not change final performance in this benchmark. On unseen stress banks, C3’s success advantage over the heuristic grew from 1.05 to 5.22 percentage points. At four hops in the local-

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 7. Explainable Artificial Intelligence as a National Security Imperative in Modern Cybersecurity Systems

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Bright Duffour
- Published: 2026-11-24
- Venue/type: Cureus Journal of Computer Science. / article
- DOI: https://doi.org/10.7759/s44389-026-00388-1
- URL: https://doi.org/10.7759/s44389-026-00388-1
- Opportunity score: 7
- Matched tags: cyber threat intelligence, interpretability, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> These concerns have accelerated global interest in explainable artificial intelligence (XAI) as a strategic requirement for modern cybersecurity systems. XAI aims to improve transparency, interpretability, accountability, and human understanding within AI-driven decision-making processes. Explainable cybersecurity frameworks enable analysts and organizations to understand why specific threats are detected, how risks are prioritized, and what factors influence automated defensive responses. Such transparency strengthens institutional trust, improves regulatory compliance, enhances forensic investigations, and supports collaborative human-AI cybersecurity operations. Although substantial research has explored AI-based cyber threat detection, malware analysis, intrusion detection, and explainability techniques individually, comparatively little attention has been devoted to positioning explainable AI as a strategic national security capability rather than merely a machine learning (ML) enhancement. As governments and organizations increasingly deploy autonomous AI systems across critical digital infrastructures, ensuring transparency, accountability, and operational trust has become essential for maintaining cyber resilience and protecting sensitive information ecosystems. This paper investigates the strategic role of XAI in modern cybersecurity systems and examines how interpreta

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 8. Digital-Twin-Based Compliance Review of Financial Terminal Devices: A Reproducible Framework and Controlled Evaluation

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Wei Li
- Published: 2026-11-25
- Venue/type: Digital Technologies Research and Applications / article
- DOI: https://doi.org/10.54963/dtra.v5i4.103071
- URL: https://doi.org/10.54963/dtra.v5i4.103071
- Opportunity score: 4
- Matched tags: evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Financial terminal compliance reviews are often periodic, sample-based, and weak in reconstructing time-dependent violations. This study develops a reproducible digital-twin framework for continuous compliance review and examines whether dynamic synchronization and evidence-chain reconstruction provide measurable gains beyond automated rule checking. The framework comprises physical-terminal, communication, virtual-twin, and compliance-decision layers, integrating rule mapping, a lightweight neural network, 3σ anomaly screening, random forests, and an Analytic Hierarchy Process (AHP). A controlled evaluation used 500 devices, including Automated Teller Machines (ATMs), Point-of-Sale (POS) terminals, self-service terminals, and mobile payment devices. Primary operational records, secondary compliance documents, and synthetic abnormal cases were kept source-labelled. Manual sampling, non-twin automated rules, and the proposed framework were compared across ten independent runs. The digital-twin scheme achieved a 97.6% modelling success rate, synchronization error no greater than 0.035, and mean latency of 70 ms. It identified 263 compliance events, compared with 218 for automated rules and 150 for manual review. Coverage and accuracy were 98.6% and 96.2%, respectively, while review time averaged 0.8 min per device. Relative to automated rules, the gains were 2.2 percentage points

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 9. Risk-constrained human-in-the-loop repair of anti-money laundering policies: Temporal legal graphs, minimal revision, and finite-sample assurance

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Joscha Krause, Cathrine Aeckerle-Willems, Gerti Sana, Stéphane Cortina, et al.
- Published: 2026-11-24
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11119310/v1
- URL: https://doi.org/10.21203/rs.3.rs-11119310/v1
- Opportunity score: 4
- Matched tags: agent, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This paper addresses human-in-the-loop compliance automation for obliged entities when the anti-money laundering legal corpus is amended. We treat the updating of an entity's policy as a minimal repair problem over two graphs, a versioned legal graph and a clause-and-control policy graph. The semantic difference between legal versions yields an impact cone of affected obligations, and we search for a minimally disruptive set of policy edits that satisfies them. An agentic workflow drafts, criticizes, and verifies these edits, while a learned orchestration policy decides how much machine computation and which human expert to use on each, subject to a chosen ceiling on the probability of missing a material obligation. We show that under explicit delta completeness and locality properties of the encoding, the impact cone contains every conservatively applicable obligation whose encoded legal evaluation can change across the amendment. We separately quantify the failure probability when dependency edges are missing. Moreover, minimal repair is NP-hard, and its pure coverage restriction has a logarithmic inapproximability threshold unless P=NP. A greedy method attains a logarithmic guarantee for integer-valued submodular coverage with positive additive costs. Conflicts and unresolved feasibility require separate handling and possible escalation. Finally, we show that machine accepta

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 10. Artificial intelligence, new product development, and design: Towards a framework for artificial intelligence adoption in innovation research

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Beatrice D’Ippolito, Cristian Mejia, Yuya Kajikawa
- Published: 2026-11-24
- Venue/type: International Journal of Management Reviews / article
- DOI: https://doi.org/10.1111/ijmr.70044
- URL: https://doi.org/10.1111/ijmr.70044
- Opportunity score: 2
- Matched tags: alignment
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial intelligence (AI) plays an increasingly central role in organizations’ digital transformation. There is growing scholarly interest in how AI supports innovation, that is, how activities and processes aimed at producing novel ideas, problem solutions or other outputs can be enabled by autonomous machines. This article focuses on the role of AI in new product development (NPD) and aims to develop theoretical insights into how AI is reshaping innovation processes. In a systematic review of 1,192 articles published in business and management journals between 1993 and 2024, we identified 67 relevant to AI, NPD, and design. Through a focus on design activities, choices and results, we analyse how AI has been adopted in NPD processes. We find that AI can help manage design complexity and relax traditional constraints, evidencing an alignment with theoretical frameworks centered on process and methodology; at the same time, current adoption of AI in NPD remains largely focused on the implementation and pursuit of measurable performance outcomes. By integrating our findings with existing innovation and AI literatures, we propose an integrative framework that builds on three pillars—strategic orientation, collaboration architecture, and value optimization—and sheds light on the role of governance as a meta‐level coordination mechanism.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 11. Cascading Insecurity in the Age of Artificial General Intelligence: An Integrated Societal-Security Framework for Geopolitics, Corporate Power, Social Stability, and Cybersecurity

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Alireza Nik Aein Koupaei
- Published: 2026-11-24
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11737869/v1
- URL: https://doi.org/10.21203/rs.3.rs-11737869/v1
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial general intelligence (AGI), commonly defined as AI that matches or exceeds the cognitive versatility and proficiency of a well-educated adult, has moved from speculation into national strategies, corporate investment plans and multilateral agendas. Yet research on its security implications remains fragmented across international relations, economics, communication studies and computer security. This article argues that the most consequential AGI-related threats to societal security arise from interactions among these domains rather than within any one of them. Drawing on societal security and securitisation theory, critical political economy, scholarship on technological sovereignty and weaponised interdependence, and societal resilience theory, it develops an integrated AGI societal-security framework. The framework is applied through a structured narrative review, a comparative analysis of the United States, China and the European Union supplemented by corporate and cyber case studies, and a scenario-based assessment of three conditions: transition, AGI emergence and advanced AGI deployment. An evidence-grading convention separates observed, emerging and prospective risks throughout. The analysis identifies four transmission mechanisms (concentration, dependency, exposure and legitimacy erosion), twelve directed cross-domain pathways and three reinforcing feedback 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

