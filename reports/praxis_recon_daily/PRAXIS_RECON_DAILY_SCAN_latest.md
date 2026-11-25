# Praxis Recon Daily Literature Scan

Generated: 2026-11-25 20:15 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 7

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 15 | Adaptive evaluation of deterministic agent defenses | 2026-11-24 | Methods of ICS/OT communication model recovery from cyber-physical systems observations | Theoretical and Applied Cybersecurity | [source](https://doi.org/10.20535/tacs.2664-29132026.3.370657) |
| 2 | 10 | Agentic package hallucination and tool-boundary gates | 2026-11-23 | Mining and Automating Expert Guidance in Open Source: A Multi-Agent Framework Informed by the PyTorch Community | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3862335) |
| 3 | 9 | Provenance-aware tool-boundary monitoring | 2026-11-23 | Verifiable Federated Learning: Integrity Guarantees, Mechanisms, and Practical Trade-offs | ACM Computing Surveys | [source](https://doi.org/10.1145/3864448) |
| 4 | 8 | Adaptive evaluation of deterministic agent defenses | 2026-11-23 | A Multilingual Security Benchmark for Indirect Prompt Injection in a Local Model Context Protocol File‐Summarization Workflow | Security and Privacy | [source](https://doi.org/10.1002/spy2.70272) |
| 5 | 6 | Agentic package hallucination and tool-boundary gates | 2026-11-23 | LLM-Ops vs. DevOps: A Comparative Review of Infrastructure Requirements for Generative AI | International Journal of Computer Trends and Technology | [source](https://doi.org/10.14445/22312803/ijctt-v74i10p104) |
| 6 | 2 | Agentic package hallucination and tool-boundary gates | 2026-11-23 | Articulating assumptions in AI-generated scientific analyses through task decomposition | Machine Learning Science and Technology | [source](https://doi.org/10.1088/2632-2153/aec5b9) |
| 7 | 2 | Provenance-aware tool-boundary monitoring | 2026-11-23 | Hybrid ML for adaptive web application firewall validation and multi-cloud auto-remediation | Scientific Reports | [source](https://doi.org/10.1038/s41598-026-80525-x) |

## Triage Notes

### 1. Methods of ICS/OT communication model recovery from cyber-physical systems observations

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mykola Ilin, Iryna Stopochkina, Oleksii Novikov
- Published: 2026-11-24
- Venue/type: Theoretical and Applied Cybersecurity / article
- DOI: https://doi.org/10.20535/tacs.2664-29132026.3.370657
- URL: https://doi.org/10.20535/tacs.2664-29132026.3.370657
- Opportunity score: 15
- Matched tags: agent, benchmark, limitation, limitations, safety, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The defense of cyber-physical systems in the ICS/OT segment of critical infrastructure faces unique challenges, stemming from the prioritization of availability, order-of-magnitude longer maintenance cycles than in IT, and significant limitations on active defense methods. Specific industrial control protocols require different intrusion detection and prevention network tools; the most effective ones are capable of deep protocol analysis, baseline recovery via learning, and anomaly detection through deviations from said baseline. The last two points lead to the need for a communication model recovery, including normal parameter ranges, typical operations, etc. In the absence of developer documentation, large codebases of proprietary software and firmware without source code, protocol reverse engineering, and communication modeling may be difficult tasks. In this work, we propose novel methods for recovering a communication model that fuse heterogeneous sources, such as passive network monitoring data, video streams from operating equipment, and HMI screencasts. Proposed methods are implemented in an autonomous agentic system capable of working in an air-gapped network and producing a communication model description with Python 3.10+ client source code for remote industrial equipment control. Model capabilities have been validated on the Igor Sikorsky KPI ICS\&AI Security Labora

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Mining and Automating Expert Guidance in Open Source: A Multi-Agent Framework Informed by the PyTorch Community

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Xiao Long, Xin Lin Tan, Xiaoli Lian, Li Zhang
- Published: 2026-11-23
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3862335
- URL: https://doi.org/10.1145/3862335
- Opportunity score: 10
- Matched tags: agent, dataset, limitation, limitations
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The continuous participation of newcomers is critical to the sustainability of Open Source Software (OSS) communities, yet many face technical and social challenges in making their first contributions. Expert guidance can help newcomers navigate these challenges, but timely support is not consistently available. While Large Language Models (LLMs) offer potential to augment this support, existing models lack project-specific context and awareness of mentoring practices. To investigate these challenges, we analyze OSS expert–newcomer interactions by curating 383 dialogues from Good First Issues (GFIs) in the PyTorch repository. We directly observe that interactions are typically brief, over one-third of newcomer inquiries remain unanswered, and the median first response time is 6.3 hours, revealing gaps and delays in expert involvement. From these interactions, we derive a taxonomy of 50 recurring, context-dependent expert guidance strategies across 11 themes, grounded in prior OSS mentoring research. Building on these findings, we introduce StrategicMentor, a strategy-driven multi-agent framework that integrates strategy knowledge with project, task, and dialogue context to deliver personalized, context-aware guidance. Coordinating specialized LLM-based agents via Retrieval-Augmented Generation (RAG), the framework operationalizes these strategy patterns without reproducing ever

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Verifiable Federated Learning: Integrity Guarantees, Mechanisms, and Practical Trade-offs

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Abla Smahi, Ahmed Ameen Fateh, Han Wang, Wenjun Li, et al.
- Published: 2026-11-23
- Venue/type: ACM Computing Surveys / article
- DOI: https://doi.org/10.1145/3864448
- URL: https://doi.org/10.1145/3864448
- Opportunity score: 9
- Matched tags: provenance, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Federated learning (FL) trains shared models without centralizing data, but typical protocols provide little evidence that local training and aggregation followed the specification. Verifiable federated learning (VeFL) addresses this gap by attaching machine-checkable evidence to FL execution. This survey introduces a reference model for coordinator-mediated, round-based horizontal FL that locates evidence points along the FL workflow and defines four verification targets: local-training correctness, update integrity, aggregation correctness, and end-to-end auditability. Existing VeFL designs are organized into four core verification routes: cryptographic verification, system-anchored verification, audit and provenance mechanisms, and hybrid designs. Statistical and data-quality methods are treated separately as complementary assurance. The surveyed approaches are compared by verification coverage, reported system costs, scalability, and trust and deployment assumptions. Deployment implications are summarized for regulated and edge settings.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. A Multilingual Security Benchmark for Indirect Prompt Injection in a Local Model Context Protocol File‐Summarization Workflow

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Nurullah Öztürk, Mehmet Şakir Kurt
- Published: 2026-11-23
- Venue/type: Security and Privacy / article
- DOI: https://doi.org/10.1002/spy2.70272
- URL: https://doi.org/10.1002/spy2.70272
- Opportunity score: 8
- Matched tags: benchmark, security, tool use
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The Model Context Protocol enables large language model applications to use external resources, but untrusted tool output may be interpreted as instruction rather than data. This study evaluates indirect prompt injection in a controlled, local, read‐only file‐summarization workflow implemented with the official Python MCP SDK and stdio transport. Eight open‐source local models were tested against 18 attack vectors under three defense conditions, with 10 repetitions per model‐vector‐condition cell. Of 4320 attempted executions, 4318 were valid. Target attack success rate was 52.61% (757/1439; Wilson 95% CI 50.02–55.18) without a guardrail, 15.71% (226/1439; 13.92–17.68) with ProtectAI DeBERTa, and 7.92% (114/1440; 6.63–9.43) with zero‐shot XLM‐RoBERTa. In an independent detector audit using 300 benign documents and 18 attack fixtures, DeBERTa achieved 55.56% recall with 33.33% false‐positive rate, whereas XLM‐RoBERTa achieved 77.78% recall with 41.00% false‐positive rate. Across 240 benign summarization attempts, task success was 98.75% without filtering, 66.25% with DeBERTa gating, and 75.42% with XLM‐RoBERTa gating. The results show that guardrails can reduce attack success but may also introduce substantial false alarms and utility loss. The findings apply to the measured local MCP file‐summarization workflow and do not establish security of remote MCP transport, authorizatio

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. LLM-Ops vs. DevOps: A Comparative Review of Infrastructure Requirements for Generative AI

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Lohith Reddy Kalluru
- Published: 2026-11-23
- Venue/type: International Journal of Computer Trends and Technology / article
- DOI: https://doi.org/10.14445/22312803/ijctt-v74i10p104
- URL: https://doi.org/10.14445/22312803/ijctt-v74i10p104
- Opportunity score: 6
- Matched tags: agent, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative AI requires infrastructure considerations beyond the traditional DevOps practices. DevOps evolved around deterministic software systems whose behavior is explained primarily by source code, build pipelines, container images, infrastructure-as-code, and runtime service monitoring. However, these controls cannot independently reproduce or evaluate generative-AI behavior that also depends on model versions, prompts, retrieved context, inference settings, and tool interactions. Large Language Model Operations (LLM-Ops) must therefore manage probabilistic model behavior, large model checkpoints, prompt artifacts, vector databases, retrieval pipelines, semantic evaluation, graphics-processing-unit-accelerated inference, and agentic tool execution. Existing comparisons commonly discuss model deployment and monitoring but provide limited infrastructure-level synthesis across these operational requirements. This review examines which infrastructure requirements distinguish LLM-Ops from conventional DevOps and which additional controls are needed when generative-AI systems retrieve external knowledge or execute tools. The two practices are compared across artifact management, compute, networking, storage, deployment, monitoring, evaluation, security, sustainability, and operational governance. The review also identifies agentic workflows and tool-oriented execution as an emerg

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Articulating assumptions in AI-generated scientific analyses through task decomposition

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Ahmed Hammad, Mihoko Nojiri
- Published: 2026-11-23
- Venue/type: Machine Learning Science and Technology / article
- DOI: https://doi.org/10.1088/2632-2153/aec5b9
- URL: https://doi.org/10.1088/2632-2153/aec5b9
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Scientific results produced by LLM-generated analysis code must be understandable and reproducible. However, uncertainty can arise at different stages of the process, both in the original natural language specification and in the generated implementation. As a result, even executable code may not provide a clear understanding of which quantities are being computed or which assumptions determine the final results. To address this challenge, we introduce quantity-grounded semantic differencing, a multi-agent framework for analyzing and comparing scientific programs generated by LLMs. The framework assigns code generation, execution, tracing, and validation to separate agents, allowing it to reconstruct how key output quantities are produced and to identify differences between the intended analysis and the implemented code. We also introduce a module that inspects ambiguities in the initial user instruction and suggests alternative rewrites before code generation. Its modular design is intended to facilitate application to different scientific domains by replacing domain-specific resources while preserving the same workflow. We validate the framework on representative collider physics analyses. In the studies HEP cases, the modular task decomposition provides explicit intermediate artifacts for inspection and the complete workflow was operated with substantially smaller models tha

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 7. Hybrid ML for adaptive web application firewall validation and multi-cloud auto-remediation

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Chanaka Lasantha, Durgesh Nandan, MWP Maduranga, Ruchi Rani
- Published: 2026-11-23
- Venue/type: Scientific Reports / article
- DOI: https://doi.org/10.1038/s41598-026-80525-x
- URL: https://doi.org/10.1038/s41598-026-80525-x
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Despite the fact that a multi-vendor cloud Web Application Firewall (WAF) deployed for management will attempt to block the attacks, whether they are actually blocked is still a manual task and an open-source tester would replay a static corpus, then not adjust to the response he is seeing or produce remediation. It suggests a hybrid machine-learning (ML) architecture to label the response by a four-layer classifier, to train a stacking ensemble (Random Forest, Gradient Boosting machine and a Multi-Layer Perceptron with a logistic-regression combiner) on the fly during the scan, to generate adaptive mutation rounds based on observed bypass patterns, to persist the calibrated ensemble so that it can reorder the request queues of later scans of the same WAF family, and to produce multi-cloud Infrastructure-as-Code remediation. On a production AWS WAF protecting a Wazuh interface, 36.8% (582 of 1,580) of attack requests are blocked and 63.2% (998) bypass the WAF, and 4 of the 141 benign requests are falsely blocked (benign false-positive rate 2.8%). Two models with the same ensemble architecture are distinguished. The operational in-flight model trains on 52 payload features, and its calibrated scores can be used to reorder future scans; it does not score the adaptive candidates. Its training cost, scoring latency and a warm-start replay are reported, but its predictive and rankin

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

