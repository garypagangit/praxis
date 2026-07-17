# Praxis Recon Daily Literature Scan

Generated: 2026-07-17 12:01 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 6 | Agentic package hallucination and tool-boundary gates | 2026-07-16 | Large language models in model-driven engineering: a systematic mapping study | Empirical Software Engineering | [source](https://doi.org/10.1007/s10664-026-10921-4) |
| 2 | 6 | Cyber threat intelligence evidence routing | 2026-07-16 | Unveiling hidden adversaries - detecting command &amp; control servers | Peer-to-Peer Networking and Applications | [source](https://doi.org/10.1007/s12083-026-02278-8) |
| 3 | 4 | Provenance-aware tool-boundary monitoring | 2026-07-15 | Bridging the Embedded Execution Gap: A Review of the Functional Mock-up Interface for Actuator-Centric Execution Workflows in Industrial Embedded Systems | Archives of Computational Methods in Engineering | [source](https://doi.org/10.1007/s11831-026-10715-3) |

## Triage Notes

### 1. Large language models in model-driven engineering: a systematic mapping study

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Weixing Zhang, Bowen Jiang, Fu Yuhong, Haowei Cheng, et al.
- Published: 2026-07-16
- Venue/type: Empirical Software Engineering / article
- DOI: https://doi.org/10.1007/s10664-026-10921-4
- URL: https://doi.org/10.1007/s10664-026-10921-4
- Opportunity score: 6
- Matched tags: evaluation, future work
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract The application of Large Language Models (LLMs) in Model-Driven Engineering (MDE) has emerged as a rapidly evolving research area. While existing systematic literature reviews have examined specific technical approaches, a comprehensive mapping of the broader research landscape (e.g., development trends) remains lacking. This study presents a systematic mapping study of LLM applications in MDE, analyzing 86 primary studies collected from five databases, covering publications from 2022 to early 2026. Guided by five research questions, we characterize the field across five dimensions: MDE task distribution and research contribution types, LLM technologies and interaction strategies, artifact representation and processing, validation practices, and publication landscape. Our findings reveal that current LLM4MDE research is heavily concentrated on Model Generation, while tasks such as Model Migration, DSL Engineering, and Metamodeling remain marginal. Most approaches rely on black-box OpenAI models accessed via remote APIs and adapted through prompt engineering, with fine-tuning and retrieval-augmented generation rarely employed. Inputs are predominantly natural-language artifacts, while outputs are model-oriented but usually expressed in lightweight textual formats rather than native MDE exchange formats. Validation is centered on quantitative experimentation, with 42% of

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Unveiling hidden adversaries - detecting command &amp; control servers

- Topic: Cyber threat intelligence evidence routing
- Authors: Naif Alsharabi, Akashdeep Bhardwaj, Amr Jadi, Shoayee Alotaibi, et al.
- Published: 2026-07-16
- Venue/type: Peer-to-Peer Networking and Applications / article
- DOI: https://doi.org/10.1007/s12083-026-02278-8
- URL: https://doi.org/10.1007/s12083-026-02278-8
- Opportunity score: 6
- Matched tags: dataset, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The increasingly advanced forms of cyber-attacks have highlighted the importance of advanced threat hunting as a necessary skillset. The current research examines the effectiveness of using Elasticsearch, Kibana, and Lucene for an intelligence-driven threat hunting to identify attack infrastructure or a Command & Control (C2) server. By aggregating all system traffic logs and security artifacts into a single data lake/warehouse, organizations are able to leverage centralized analysis of information from different sources on a corporate scale. Utilizing Kibana’s ability to perform network and log analysis, using Lucene’s rich syntax to make sophisticated queries will empower individuals to make valuable findings from log and network traffic logs that identify behaviours and patterns typical of C2 activities. A novel intelligence-based threat hunting approach is presented here that utilizes Elasticsearch, with domain-specific language additions to refine search queries and investigate for C2 related activity. A detailed analysis of the research based on real-world datasets is conducted to evaluation the threat hunting framework’s abilities in detecting C2 servers and minimize true/false positives in relation to organizational security concerns.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Bridging the Embedded Execution Gap: A Review of the Functional Mock-up Interface for Actuator-Centric Execution Workflows in Industrial Embedded Systems

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Sebastian Rojas-Ordoñez, Mikel Segura, Irune Yarza, Ekaitz Zulueta
- Published: 2026-07-15
- Venue/type: Archives of Computational Methods in Engineering / article
- DOI: https://doi.org/10.1007/s11831-026-10715-3
- URL: https://doi.org/10.1007/s11831-026-10715-3
- Opportunity score: 4
- Matched tags: alignment, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Industrial actuators integrate multi-domain physical dynamics with embedded control algorithms under strict timing constraints. Despite mature model-based design workflows, a persistent embedded execution gap separates validated high-fidelity simulation models from deterministic, resource-bounded execution on embedded industrial platforms. This review examines the Functional Mock-up Interface (FMI) as an interoperability enabler for actuator development workflows and argues that interoperability at the model-exchange level does not automatically translate into interoperability at the execution level. The review analyzes the evolution of FMI from version 2.0 to 3.0, systematizes actuator-relevant fidelity requirements (nonlinearities, compliance/resonance, timing effects), and evaluates representative approaches for integrating FMI into industrial and robotic toolchains. Two deployment trajectories are synthesized: (i) runtime-constrained FMU execution on edge/MCU-class platforms for prototyping, monitoring, and non-safety-critical functions; and (ii) analyzable code-generation paths such as Embedded FMI (eFMI) and GALEC, which target bounded memory and timing transparency for certification-oriented workflows. Although FMI 3.0 introduces improved timing semantics through clocks and Scheduled Execution, end-to-end feasibility remains limited by toolchain maturity, schedu

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

