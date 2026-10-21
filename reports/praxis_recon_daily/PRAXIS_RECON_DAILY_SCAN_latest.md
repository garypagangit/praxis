# Praxis Recon Daily Literature Scan

Generated: 2026-10-21 15:41 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 4

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Adaptive evaluation of deterministic agent defenses | 2026-10-19 | Quantum machine learning: A comprehensive survey of models, tools, and challenges | Journal of King Saud University - Computer and Information Sciences | [source](https://doi.org/10.1007/s44443-026-01177-5) |
| 2 | 8 | Agentic package hallucination and tool-boundary gates | 2026-10-19 | MedMCP: An Open Agentic Ecosystem for Medical Imaging Workflows | bioRxiv (Cold Spring Harbor Laboratory) | [source](https://doi.org/10.64898/2026.10.12.758708) |
| 3 | 2 | Provenance-aware tool-boundary monitoring | 2026-10-20 | PrivGuardAI for adaptive privacy preserving sensitive data protection in cloud environments | Discover Computing | [source](https://doi.org/10.1007/s10791-026-10472-8) |
| 4 | 2 | Provenance-aware tool-boundary monitoring | 2026-10-19 | Data sparsity in pervasive computing and human–machine interaction: a survey of sources, structures, and remedies | CCF Transactions on Pervasive Computing and Interaction | [source](https://doi.org/10.1007/s42486-026-00277-5) |

## Triage Notes

### 1. Quantum machine learning: A comprehensive survey of models, tools, and challenges

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Taha M. Mahmoud, Marwa R. Hassan, Shenson Joseph, Issam Boukabou, et al.
- Published: 2026-10-19
- Venue/type: Journal of King Saud University - Computer and Information Sciences / article
- DOI: https://doi.org/10.1007/s44443-026-01177-5
- URL: https://doi.org/10.1007/s44443-026-01177-5
- Opportunity score: 10
- Matched tags: dataset, evaluation, limitation, limitations
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Quantum Machine Learning (QML) is an emerging interdisciplinary field that merges quantum computing with classical machine learning (ML) to enhance computational efficiency, scalability, and accuracy in data-driven tasks. By leveraging quantum properties such as superposition, entanglement, and quantum parallelism, QML has the potential to solve complex problems that are intractable for classical models. This survey provides a comprehensive, systematic review of recent advancements in QML, conducted following the PRISMA 2020 guidelines and covering fundamental encoding techniques that enable quantum computers to process classical data, as well as essential tools, datasets, and evaluation metrics used in quantum model development. Furthermore, it explores various QML approaches, including supervised, semi-supervised, unsupervised, and reinforcement learning, alongside quantum deep learning (QDL) models such as Quantum Neural Networks (QNNs) and Variational Quantum Circuits (VQCs). The paper also discusses the challenges in QML, including hardware limitations, scalability issues, and the need for improved quantum error correction. A dual-axis taxonomy simultaneously classifies algorithms by learning paradigm and quantum-classical integration level – a structure not found in prior surveys. The survey also covers Quantum Transfer Learning, Quantum Graph Neural Networks, an

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. MedMCP: An Open Agentic Ecosystem for Medical Imaging Workflows

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Julian McGinnis, Paul Friedrich, Mark Mühlau, Jan Stefan Kirschke, et al.
- Published: 2026-10-19
- Venue/type: bioRxiv (Cold Spring Harbor Laboratory) / preprint
- DOI: https://doi.org/10.64898/2026.10.12.758708
- URL: https://doi.org/10.64898/2026.10.12.758708
- Opportunity score: 8
- Matched tags: agent, benchmark, provenance
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Deep learning has driven rapid progress in medical image analysis, with methods for tasks such as organ segmentation, anomaly detection, and radiology report generation now matching or surpassing expert performance on several benchmarks. While many methods are released as open source, their routine adoption by clinicians and medical researchers remains limited. The bottleneck is not a lack of capable tools, but the absence of infrastructure to make them accessible to non-technical users. To break this barrier, we present MedMCP, an agentic framework that solves this last-mile problem along two axes: (1) a local agentic workspace that lets users apply state-of-the-art image analysis methods through natural language, and (2) a community-driven tool ecosystem that lets developers deploy and distribute capabilities as validated, independently testable servers. MedMCP enforces a strict orchestration-execution boundary in which a local language model translates user intent into workflow plans, while all image analysis is delegated to domain-specific tools. The framework runs entirely on-premise, every side-effecting operation passes through a human-in-the-loop permission gate, and a full provenance trail links each output to the tools, parameters, and inputs that produced it. An inspectable workspace lets users verify intermediate results rather than blindly trusting the agent, and c

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. PrivGuardAI for adaptive privacy preserving sensitive data protection in cloud environments

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Sampath Reddy Racha, Ganesh Reddy Karri
- Published: 2026-10-20
- Venue/type: Discover Computing / article
- DOI: https://doi.org/10.1007/s10791-026-10472-8
- URL: https://doi.org/10.1007/s10791-026-10472-8
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This rapidly growing and ever-expanding trend of intelligent sensor systems, IoT devices, and data-driven cyber-physical infrastructures has been accompanied by new challenges in the secure, explainable and privacy-compliant access to sensitive data. Traditional access control systems are based on static rules, have only limited context awareness, and are therefore not suitable for real-time scenarios where decisions must be made based on content sensitivity, the trustworthiness of behaviours, user context, and changing risk factors. Anomaly detection and audit also tend to be separate from access-control pipelines, making it difficult to adapt policies on the fly and provide transparent accountability. To overcome these drawbacks, this study proposes a closed-loop, multi-layer, privacy-preserving framework called PrivGuardAI, which combines four networks: SensLabelNet for metadata- and content-aware sensitivity classification, AccessIQ for behavioural-trust-driven adaptive access control, ThreatWatchNet for anomaly and insider-threat detection, and BlockAuditChain for tamper-proof audit logging. SensLabelNet leverages CNN- and BERT-based encoders to classify data into public, private, and restricted, and AccessIQ dynamically adjusts access decisions based on role, attribute, context, and behavioural risk signals. Quantitative evaluation reveals that SensLabelNet achieves a mac

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Data sparsity in pervasive computing and human–machine interaction: a survey of sources, structures, and remedies

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Yifei Shen, Yuanjun Liu, Chengzu Dong, Shantanu Pal, et al.
- Published: 2026-10-19
- Venue/type: CCF Transactions on Pervasive Computing and Interaction / article
- DOI: https://doi.org/10.1007/s42486-026-00277-5
- URL: https://doi.org/10.1007/s42486-026-00277-5
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Data sparsity is a central challenge in pervasive computing and human–machine interactive systems, where observations arise unevenly across users, devices, algorithms, and environments. Across recommender interfaces, healthcare monitoring, smart-city mobility, and language-enabled interaction, sparsity can reflect incomplete sensing, constrained exposure, intermittent participation, privacy limits, and heterogeneous event generation. These mechanisms can produce missing or weakly supported instances as well as observable structures such as excess zeros and long-tail frequency distributions; conflating mechanisms with their manifestations can lead to mismatched modelling and evaluation. This survey synthesises 134 studies and develops a source-to-structure diagnostic framework. It distinguishes two mechanism-oriented perspectives—data collection oriented sparsity and user–system interaction oriented sparsity—from a distributional structure oriented perspective that records observable zero-inflated and long-tail patterns without assuming their causes. Six operational forms are connected through a support-based chain from mechanism to observational support, observable structure, and intervention. The roadmap further distinguishes evidence acquisition, bias correction, robust learning under fixed sparsity, and decentralised utilisation, and specifies cross-domain transfer 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

