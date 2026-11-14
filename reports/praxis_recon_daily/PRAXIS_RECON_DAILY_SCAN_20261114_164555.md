# Praxis Recon Daily Literature Scan

Generated: 2026-11-14 16:45 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 7

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 15 | Agentic package hallucination and tool-boundary gates | 2026-11-13 | AI-Based Scenario Generation in Cyber Training Ranges: A Systematic Review | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11421747/v1) |
| 2 | 11 | Agentic package hallucination and tool-boundary gates | 2026-11-12 | A systematic comparison of Named Entity Recognition approaches for Cyber Threat Intelligence | Machine Learning with Applications | [source](https://doi.org/10.1016/j.mlwa.2026.101064) |
| 3 | 11 | Cyber threat intelligence evidence routing | 2026-11-12 | Attack-Path-Aware Enterprise Risk Quantification for Cloud-Native Financial Data Platforms Using AI and Cybersecurity Graphs | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11405581/v1) |
| 4 | 9 | Agentic package hallucination and tool-boundary gates | 2026-11-12 | When to Delegate: A Measurement Study of Bounded Agent Teams for Personal Super Agents | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11710191/v1) |
| 5 | 4 | Provenance-aware tool-boundary monitoring | 2026-11-13 | An Agentic AI Framework for Autonomous Cross-View Kernel Rootkit Detection and Response in Cloud Environments | Research Square | [source](https://doi.org/10.21203/rs.3.rs-10762752/v1) |
| 6 | 4 | Source-locked citation and hallucination verification | 2026-11-13 | Engineering an EHDS-aligned EHR architecture for Romania: integrating openEHR, FHIR, OMOP-CDM, and verifiable clinical RAG | Frontiers in Digital Health | [source](https://doi.org/10.3389/fdgth.2026.1980669) |
| 7 | 2 | Source-locked citation and hallucination verification | 2026-11-13 | Digital twins for intelligent intersections: A literature review | Transportation Research Interdisciplinary Perspectives | [source](https://doi.org/10.1016/j.trip.2026.102352) |

## Triage Notes

### 1. AI-Based Scenario Generation in Cyber Training Ranges: A Systematic Review

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Purvi Mehta, Paul Black, Gour Karmakar, Paul Pang
- Published: 2026-11-13
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11421747/v1
- URL: https://doi.org/10.21203/rs.3.rs-11421747/v1
- Opportunity score: 15
- Matched tags: agent, alignment, hallucination, limitation, limitations, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Developing realistic scenarios for Cyber Training Ranges (CTRs) requires current threat information, suitable infrastructure, attack events, learning objectives, and consideration of trainee capability. Established scenario-generation approaches use manual design, simulation, templates, rules, attack graphs, and model-driven engineering, often requiring substantial expert effort to develop and update. Recent research has investigated Artificial Intelligence (AI) for scenario generation and training, including Machine Learning (ML), Reinforcement Learning (RL), and Large Language Models (LLMs). However, existing surveys provide fragmented coverage of AI across the scenario-generation lifecycle and have not systematically examined AI-specific threat intelligence, such as MITRE ATLAS, as a dedicated source for CTR scenarios. This paper presents a Systematic Literature Review (SLR) of embedding AI into CTR scenario generation, tracing the progression from non-AI approaches to ML, LLM-based, and agentic AI methods. It critically compares their advantages and limitations and examines Retrieval-Augmented Generation (RAG), agentic approaches, and AI threat intelligence-based attack scenarios. The literature indicates that AI can support scenario creation, automation, adaptation, and deployment, while important challenges remain in threat-data quality and currency, hallucinatio

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. A systematic comparison of Named Entity Recognition approaches for Cyber Threat Intelligence

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Maximilian Ranzinger, Florian Skopik, Dzenan Hamzic, Max Landauer, et al.
- Published: 2026-11-12
- Venue/type: Machine Learning with Applications / article
- DOI: https://doi.org/10.1016/j.mlwa.2026.101064
- URL: https://doi.org/10.1016/j.mlwa.2026.101064
- Opportunity score: 11
- Matched tags: cyber threat intelligence, dataset, evaluation, interpretability, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Given the large volume of cybersecurity information generated daily, cybersecurity analysts require automated tools to efficiently process this data and extract meaningful insights and actionable outcomes. One such concept is Named Entity Recognition (NER). In this work, approaches for NER on Cyber Threat Intelligence (CTI) data are examined through a Systematic Literature Review (SLR) enabled by a large language model (LLM)-based extractor proposed in this study. Furthermore, seven publicly available approaches are evaluated regarding cost and performance. To provide meaningful insights into tagging performance, we analyze it from four perspectives: overall performance, performance on specific entity types, performance on specific entity attributes (e.g. entity frequency) for interpretability and the capability to tag entire documents. The evaluation shows that, on the datasets evaluated, additional architectural complexity does not yield measurably better tagging performance, while it increases training and inference cost substantially. Encoder-based language models (LMs) such as BERT, combined with non-complex decoding layers, already achieve the highest tagging performance. Under the evaluated full-document setting on STIXnet, additional document-level context did not improve performance and degraded it for most models. The analysis further shows that NER performance scores

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Attack-Path-Aware Enterprise Risk Quantification for Cloud-Native Financial Data Platforms Using AI and Cybersecurity Graphs

- Topic: Cyber threat intelligence evidence routing
- Authors: Gopinathan Rathinavelu
- Published: 2026-11-12
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11405581/v1
- URL: https://doi.org/10.21203/rs.3.rs-11405581/v1
- Opportunity score: 11
- Matched tags: MITRE ATT&CK, retrieval, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Enterprise risk quantification in banking has historically treated vulnerability management and financial-impact analysis as separate disciplines: scanners rank findings by base severity scores, while risk functions estimate loss with coarse, qualitative heat maps. Neither accounts for how an adversary actually chains weaknesses across a modern cloud-native data platform to reach regulated financial data. This paper presents an attack-path-aware risk-quantification architecture that unifies the two. The system ingests posture and identity telemetry from cloud-security, identity, and configuration-management sources, constructs a directed attack graph whose nodes are asset and privilege states and whose edges are adversary transitions tagged by MITRE ATT&CK tactic, and uses this graph to propagate compromise likelihood toward designated crown-jewel assets. An AI layer scores edge-transition likelihoods from heterogeneous signals using a graph neural network with a transparent fallback, and large language models are used only in a constrained, retrieval-grounded role to normalize unstructured control evidence into the graph schema. Risk is expressed in monetary terms through a Factor Analysis of Information Risk (FAIR) loss model driven by graph-derived frequencies, producing an annualized loss distribution rather than a point estimate. A budget-constrained optimizer the

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. When to Delegate: A Measurement Study of Bounded Agent Teams for Personal Super Agents

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Jipu Su
- Published: 2026-11-12
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11710191/v1
- URL: https://doi.org/10.21203/rs.3.rs-11710191/v1
- Opportunity score: 9
- Matched tags: agent, evaluation, refusal, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Personal super agents coordinate many tools while remaining fast, safe, and accountable to one user. A popular design is a Router delegating to Workers. Recent work shows coordination can cost more than it returns, but transfer to personal agents—single-user context, side-effecting tools, cross-turn references, and refusals—is not established. We present the bounded-delegation runtime protocol, instantiate it in Eva, a 22-tool in-vehicle agent, and introduce Eva-Bench, 80 rule-scored tasks in ten categories. With one real model and tool set, we compare monolithic ReAct, bounded team, and unbounded team, and ablate budgets, reasoning, concurrency, guards, ledger, and injected failures. Delegation is not free: the main team pays 2.75×the latency and 2.59×the tokens. In one full-suite run it leads by one task (92.5% versus 91.2%), but three full-suite repetitions give 92.9% versus 93.3% (difference -0.4pp). Four post hoc temperature- matched runs average 90.6% (range 86.2–93.8%), so temperature alone does not explain the team’s small, unstable lead. We do not claim a general team advantage. The stable finding is the tax; service workflows and cross-turn references favor the team in repeated data, while safety and aggregate success do not. Bounded budgets reduce tail latency, reasoning is a net cost, and guards/ledger are null at oracle success. A selective-delegation poli

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. An Agentic AI Framework for Autonomous Cross-View Kernel Rootkit Detection and Response in Cloud Environments

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Suresh Kumar S, Sudalai Muthu T.
- Published: 2026-11-13
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-10762752/v1
- URL: https://doi.org/10.21203/rs.3.rs-10762752/v1
- Opportunity score: 4
- Matched tags: agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Kernel-level rootkits subvert the operating system to conceal the network ports through which they maintain covert channels, and cloud tenants who cannot access the hypervisor have few reliable defences. Existing detectors stop at a verdict, leaving investigation and response to human analysts and admitting a window during which an active rootkit persists. This paper presents an agentic AI framework that both detects and autonomously responds to kernel rootkits through port-level behavioural analysis. On cloud guests hosted on Google Cloud Platform, a kernel-mode Port Enumerator and a user-mode Port Monitor produce cross-view port lists whose discrepancy, formalized here as a temporal behavioural signal, is classified by a deep ensemble of CNN-LSTM, Bi-LSTM, Autoencoder and GAN. The resulting Rootkit/Benign verdict is handed to an LLM Agent Orchestrator that executes an autonomous perceive-plan-act-reflect loop, invoking security tools under human-in-the-loop oversight for high-impact actions. A second evidence channel is released with the paper as a labelled concealment matrix of 87 kernel rootkit samples described by a binary vector over a 968-entry dictionary of concealed objects, each carrying the technique it uses to hide. We give a mathematical model of the cross-view signal, the fused decision, and the agent’s utility-driven action selection. Evaluated on a Wind

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Engineering an EHDS-aligned EHR architecture for Romania: integrating openEHR, FHIR, OMOP-CDM, and verifiable clinical RAG

- Topic: Source-locked citation and hallucination verification
- Authors: Dragoş Ionuţ Vicoveanu, Oana Geman, Roxana Toderean, Marius Prelipceanu, et al.
- Published: 2026-11-13
- Venue/type: Frontiers in Digital Health / article
- DOI: https://doi.org/10.3389/fdgth.2026.1980669
- URL: https://doi.org/10.3389/fdgth.2026.1980669
- Opportunity score: 4
- Matched tags: future research
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Introduction The electronic health record (EHR) must simultaneously support two paths with divergent requirements: therapeutic personalization, which requires contextualized patient data, and secondary clinical use, which requires standardized data under the pressure of compliance imposed by the European Health Data Space (EHDS). Methods In this study, we adopted the design science research methodology and developed a model, which was evaluated using a descriptive design on a simulation-based clinical scenario. First, we derived five design requirements from the constraints of the Romanian healthcare ecosystem to establish the requirement coverage for the proposed model by systematically comparing realistic alternatives, including the national initiative “My e-Health” (e-SănătateaMea). Results We propose ROMED-EHR, a conceptual reference model that stratifies openEHR (persistence), HL7 Fast Healthcare Interoperability Resources (FHIR) R4 (interoperability), and the Observational Medical Outcomes Partnership Common Data Model (OMOP-CDM) (analysis). The model, which is semantically grounded in Systematized Nomenclature of Medicine - Clinical Terms (SNOMED CT), Logical Observation Identifiers Names and Codes (LOINC), and the Human Phenotype Ontology (HPO), is extended with a clinical support module based on retrieval-augmented generation (RAG) whose outputs are verified against te

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 7. Digital twins for intelligent intersections: A literature review

- Topic: Source-locked citation and hallucination verification
- Authors: Alben Rome Bagabaldo, Jürgen Hackl
- Published: 2026-11-13
- Venue/type: Transportation Research Interdisciplinary Perspectives / article
- DOI: https://doi.org/10.1016/j.trip.2026.102352
- URL: https://doi.org/10.1016/j.trip.2026.102352
- Opportunity score: 2
- Matched tags: safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Intelligent intersections play a pivotal role in urban mobility, demanding innovative solutions such as digital twins to enhance safety and efficiency. This literature review investigates the integration and application of digital twins for intelligent intersections, a critical area within smart urban traffic systems. The review systematically categorizes existing research into five key thematic areas: (i) Digital Twin Architectures and Frameworks; (ii) Data Processing and Simulation Techniques; (iii) Artificial Intelligence and Machine Learning for Adaptive Traffic Control; (iv) Safety and Protection of Vulnerable Road Users; and (v) Scaling from Localized Intersections to Citywide Traffic Networks. Each theme is explored comprehensively, highlighting significant advancements, current challenges, and critical insights. The findings reveal that multi-layered digital twin architectures incorporating real-time data fusion and AI-driven decision-making enhances traffic efficiency and safety. Advanced simulation techniques combined with sophisticated AI/ML algorithms demonstrate notable improvements in real-time responsiveness and predictive accuracy for traffic management. Additionally, the integration of digital twins has shown substantial promise in safeguarding vulnerable road users through proactive and adaptive safety strategies. Despite these advancements, key challenges per

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

