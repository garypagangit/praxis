# Praxis Recon Daily Literature Scan

Generated: 2026-11-05 18:21 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 7

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 19 | Source-locked citation and hallucination verification | 2026-11-03 | A multi-guideline clinical agent for vascular surgery: architecture, implementation, and benchmark evaluation | Journal of the American Medical Informatics Association | [source](https://doi.org/10.1093/jamia/ocag178) |
| 2 | 12 | Agentic package hallucination and tool-boundary gates | 2026-11-03 | Empirical insights on the use of large language models in software verification and validation: evidence from the Brazilian IT industry | Empirical Software Engineering | [source](https://doi.org/10.1007/s10664-026-10971-8) |
| 3 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-11-03 | Physical AI Security: A Unified Five-Layer Taxonomy for a Systematic Survey from Silicon to Semantics | Unknown venue | [source](https://doi.org/10.31224/8690) |
| 4 | 6 | Agentic package hallucination and tool-boundary gates | 2026-11-03 | A Quishing Detection Model via Global Attention-Based Adaptive Fusion of QR Code and URL Text | ACM Transactions on Internet Technology | [source](https://doi.org/10.1145/3861079) |
| 5 | 6 | Adaptive evaluation of deterministic agent defenses | 2026-11-03 | From Shadow IT to Shadow AI: A Scoping Review of How Embedded AI and Employee Use Increase Cybersecurity and Data Privacy Risk | Journal of Cybersecurity Education Research and Practice | [source](https://doi.org/10.62915/2472-2707.1334) |
| 6 | 5 | Provenance-aware tool-boundary monitoring | 2026-11-03 | Digital twins for robot-assisted nuclear decommissioning: a review of perception, radiological mapping, and model interoperability, with the DORADO project as a case study | Frontiers in Nuclear Engineering | [source](https://doi.org/10.3389/fnuen.2026.1954802) |
| 7 | 4 | Agentic package hallucination and tool-boundary gates | 2026-11-03 | Contract-Bounded Agents - A Practical Method for Building LLM Agents over Distributed Operational Pipelines | Universal library of engineering technology. | [source](https://doi.org/10.70315/uloap.ulete.2026.0304006) |

## Triage Notes

### 1. A multi-guideline clinical agent for vascular surgery: architecture, implementation, and benchmark evaluation

- Topic: Source-locked citation and hallucination verification
- Authors: Vangelis G. Alexiou, Areti Vassiliou, Bauer E. Sumpio, George Geroulakos, et al.
- Published: 2026-11-03
- Venue/type: Journal of the American Medical Informatics Association / article
- DOI: https://doi.org/10.1093/jamia/ocag178
- URL: https://doi.org/10.1093/jamia/ocag178
- Opportunity score: 19
- Matched tags: agent, benchmark, evaluation, hallucination, provenance
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> BACKGROUND: The clinical practice guidelines (CPGs) published by the European Society for Vascular Surgery (ESVS) span approximately 1100 pages whose simultaneous cross-referencing is impractical at the point of care. Unguarded large language models (LLMs) carry hallucination risk, motivating a guideline-locked design. METHODS: We describe the architecture and development of a context-aware clinical agent encompassing the full ESVS corpus of 14 CPGs. The system extends a validated single-guideline GraphRAG prototype with an LLM-driven Guideline Router, an embedded Context Gate that withholds retrieval when decision-critical parameters are absent, dual-channel retrieval, and GPT-5 synthesis under a mandatory citation template. An automated benchmark assessed the final system on 55 vignettes, scored by 2 blinded LLM judges over 3 runs (330 judgments), with clinician adjudication of every flagged claim. RESULTS: The system stayed within its locked corpus, declined all out-of-scope queries, and achieved 98.4% guideline-routing recall. The Context Gate showed 91.9% specificity and 78.6% sensitivity for underspecified queries, and all 259 cited recommendations were verifiable within the locked corpus. Automated judges flagged an unsupported claim in 18.2% of items under a sensitive screening definition; on adjudication by 2 vascular surgeons, 7.3% of items contained a clinically cons

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Empirical insights on the use of large language models in software verification and validation: evidence from the Brazilian IT industry

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Guilherme Bolfe, Filipe Garcia Silva, Elder Rodrigues, Maicon Bernardino, et al.
- Published: 2026-11-03
- Venue/type: Empirical Software Engineering / article
- DOI: https://doi.org/10.1007/s10664-026-10971-8
- URL: https://doi.org/10.1007/s10664-026-10971-8
- Opportunity score: 12
- Matched tags: future research, hallucination, safety, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Artificial Intelligence (AI) has created new possibilities for improving Verification and Validation (V&V) activities in software engineering. Among recent advances, Large Language Models (LLMs) have gained attention for their potential to automate tasks such as test generation, defect detection, and requirements analysis. Although interest in these technologies has increased, their use in industrial environments is still limited and not well understood. Concerns remain about their reliability, transparency, and ethical implications, especially when applied in safety-critical or regulated domains. This paper reports an exploratory empirical study based on a survey with 39 software professionals from different sectors and company sizes in Brazil. The questionnaire investigates the reported use of conventional V&V tools, AI-based testing solutions, and LLM-supported practices, as well as perceptions of effectiveness, workflow integration, cost, and governance challenges. Respondents reported perceived benefits, such as support for automation, test-case creation, code understanding, and efficiency-oriented tasks, along with difficulties related to integration, transparency, reliability, hallucinations, over-reliance, data misuse, and governance. By documenting current practices, perceptions, and expectations, this study offers an exploratory empirical view of how AI and L

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Physical AI Security: A Unified Five-Layer Taxonomy for a Systematic Survey from Silicon to Semantics

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Ahmed M. Elmisery, Nabil Moukafih, Suga Junichi
- Published: 2026-11-03
- Venue/type: Unknown venue / preprint
- DOI: https://doi.org/10.31224/8690
- URL: https://doi.org/10.31224/8690
- Opportunity score: 7
- Matched tags: evaluation, provenance, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Collaborative robots, autonomous mobile robots (AMRs), and edge inference nodes inside Industrial Control Systems (ICS) now let AI models drive physical actuators. For these systems a cyberattack is no longer only a data problem: a successful exploit can disrupt infrastructure, halt production, or injure people. Research on Physical AI Security (PAIS) is split across hardware trust, artificial intelligence, robotics, operational technology, and cyber-physical systems, which makes it hard to see how risks and defenses depend on one another across the cycle of AI-driven sensing, decision-making, actuation, and feedback. We propose a five-layer taxonomy for PAIS: hardware-rooted trust, pre-deployment validation, runtime assurance, domain semantics, and knowledge feedback. The taxonomy is organized around the physical decision and gives the fragmented literature a common structure in which cross-layer dependencies can be stated. Using it as the classification frame, we conduct a PRISMA-informed structured review of 312 primary papers published between 2015 and 2025 across six databases, supplemented by 28 standards, 14 regulatory frameworks, and 12 incident reports. Existing work covers individual layers well but does little to connect them across the Physical AI lifecycle. Coverage is thinnest exactly where Physical AI differs most from classical ICS: model provenance, validation 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. A Quishing Detection Model via Global Attention-Based Adaptive Fusion of QR Code and URL Text

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Erzhou Zhu, Conglin Ye, Yusheng Guan, Hong Zhong
- Published: 2026-11-03
- Venue/type: ACM Transactions on Internet Technology / article
- DOI: https://doi.org/10.1145/3861079
- URL: https://doi.org/10.1145/3861079
- Opportunity score: 6
- Matched tags: dataset, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Quishing (QR code phishing) represents an emerging cybersecurity threat characterized by its dual-modal nature. This attack simultaneously exploits the visual modality of QR code images and the semantic modality of embedded URLs to launch covert attacks. Such a dual-modal attack strategy renders existing single-modality detection methods (relying solely on either images or URLs) and traditional fusion approaches based on expert-driven feature engineering fundamentally inadequate for comprehensive defense. To address this gap, this study proposes QRURL-GAAFNet (QR Code and Associated URL Features Global Attention-Based Adaptive Feature Fusion Network), which, to the best of our knowledge, represents the first end-to-end deep learning framework that holistically addresses the unique cross-modal correlation patterns inherent in Quishing attacks. Within this framework, dedicated deep learning networks independently extract visual features from QR codes and semantic features from URLs. Unlike conventional multimodal fusion approaches that treat modalities independently or use fixed fusion strategies, our proposed Global Attention-based Adaptive Feature Fusion (GAAF) mechanism dynamically learns sample-specific cross-modal dependencies by computing adaptive fusion weights from joint representations. By emphasizing discriminative information based on learned cross-modal correlations, 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. From Shadow IT to Shadow AI: A Scoping Review of How Embedded AI and Employee Use Increase Cybersecurity and Data Privacy Risk

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Jenny Ahn, Bogdan Pavlyuchenkov, Lasette Smith, Paul Wagner, et al.
- Published: 2026-11-03
- Venue/type: Journal of Cybersecurity Education Research and Practice / article
- DOI: https://doi.org/10.62915/2472-2707.1334
- URL: https://doi.org/10.62915/2472-2707.1334
- Opportunity score: 6
- Matched tags: agent, alignment, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The rapid integration of artificial intelligence into enterprise software has introduced a critical governance challenge: Shadow AI, the unmanaged and often invisible adoption of AI tools and features by employees outside formal IT oversight. Unlike traditional Shadow IT, which centers on unauthorized data storage and infrastructure, Shadow AI operates at the knowledge and decision-making layer, introducing probabilistic risks including data leakage, agentic misalignment, and indirect prompt injection that existing security frameworks are ill-equipped to address. This paper presents a Systematic Literature Review (SLR) synthesizing 38 peer-reviewed and industry sources to investigate three research questions: how organizational visibility gaps into embedded and employee-used AI increase cybersecurity and data privacy risk; what cybersecurity incident types are most commonly associated with ungoverned AI-enabled applications; and what risks employee interactions with AI pose to sensitive, proprietary, and regulated data. The analysis identifies a critical visibility deficit created by AI capabilities embedded within vendor-managed platforms, the semantic opacity of large language model interactions, and employees' utilitarian bypass of security policies. A taxonomy of six AI-specific incident types is presented, encompassing data leakage, prompt injection, credential compromise,

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Digital twins for robot-assisted nuclear decommissioning: a review of perception, radiological mapping, and model interoperability, with the DORADO project as a case study

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Omar Zahra, Abdenour Benkrid, Joseph Ridao, Dag Fjeld Edvardsen, et al.
- Published: 2026-11-03
- Venue/type: Frontiers in Nuclear Engineering / article
- DOI: https://doi.org/10.3389/fnuen.2026.1954802
- URL: https://doi.org/10.3389/fnuen.2026.1954802
- Opportunity score: 5
- Matched tags: safety, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Nuclear decommissioning increasingly relies on digital technologies to support characterisation, planning, monitoring, and decision-making in environments where access is limited by radiation, contamination, or other operational constraints. Digital twins provide a framework for integrating geometric, radiological, and operational information, while robotic systems acquire data and perform tasks with reduced human exposure. Although often treated separately, the two are coupled through a continuous exchange of information: robotic observations update the digital representation of the facility, and the twin provides the context for mission planning and execution. This review examines that coupling from the perspective of information representation and information flow. Based on a structured search of the peer-reviewed literature, standards, and public technical reports, it covers geometric and radiological sensing, radiation-field estimation, geometric and semantic representations and their interoperability, geometry for radiation-transport calculation, localisation, change detection, mission planning, and data governance. Comparative tables summarise sensing technologies, radiological instruments, exchange formats, localisation approaches, international programmes, and the evidence obtained in real facilities to date. A dedicated section synthesises uncertainty propagation and 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 7. Contract-Bounded Agents - A Practical Method for Building LLM Agents over Distributed Operational Pipelines

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Sai Sruthi Puchakayala
- Published: 2026-11-03
- Venue/type: Universal library of engineering technology. / article
- DOI: https://doi.org/10.70315/uloap.ulete.2026.0304006
- URL: https://doi.org/10.70315/uloap.ulete.2026.0304006
- Opportunity score: 4
- Matched tags: agent, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> An investigation into why a unit of business work did not finish in a distributed operational pipeline crosses several systems of record: schedulers, orchestration engines, warehouses, code repositories and configuration stores. This monograph formulates Contract-Bounded Agent Design (CBAD), a reproducible engineering method for building language-model agents that conduct such investigations within fixed boundaries and can be carried from one pipeline to the next. The method rests on four structural decisions: one narrow, read-only tool per external source, whose description serves as a semantic contract; safety contracts enforced in code, including statement guards, pinned query scopes, payload ceilings and truncation reported with true totals; an explicit failure taxonomy that classifies by meaning on two orthogonal axes, the business stage at which work stopped and the concern that owns the fix; and a named separation between the current state of the work and its historical occurrence. Around the decisions the book sets an ordered investigation runbook, an answer discipline that limits each answer to what the tools returned, and four named design rules: liveness check before trust, best-effort secondary write, partial success by construction and routing by identifier shape. The decisions were derived from two systems developed separately in the author’s own practice as a sof

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

