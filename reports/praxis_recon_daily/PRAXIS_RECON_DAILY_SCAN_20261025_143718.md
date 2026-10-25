# Praxis Recon Daily Literature Scan

Generated: 2026-10-25 14:37 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 6

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 9 | Adaptive evaluation of deterministic agent defenses | 2026-10-23 | Permission Withdrawal in Tool-Using Language Model Agents: Runtime Enforcement and Recovery | American Journal of Data Science and Artificial Intelligence | [source](https://doi.org/10.54536/ajdsai.v2i2.8776) |
| 2 | 4 | Agentic package hallucination and tool-boundary gates | 2026-10-23 | The Attack and Defense Landscape of Agentic AI: A Comprehensive Survey | SuperIntelligence - Robotics - Safety & Alignment | [source](https://doi.org/10.70777/si.v3i4.18889) |
| 3 | 4 | Provenance-aware tool-boundary monitoring | 2026-10-23 | Agentic AI for Complex Decision-Making: A Systematic Critical Review of Planning, Memory, Tools, Safety and Assurance in Autonomous Systems | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11226881/v1) |
| 4 | 2 | Agentic package hallucination and tool-boundary gates | 2026-10-23 | Rethinking human–AI agency in tourism and hospitality: A framework for the agentic AI era | Tourism Management | [source](https://doi.org/10.1016/j.tourman.2026.105557) |
| 5 | 2 | Provenance-aware tool-boundary monitoring | 2026-10-23 | Unlocking Supply Chain Resilience: The Impact of Artificial Intelligence and IoT Integration in Agribusiness Operations | Advanced Business Journal | [source](https://doi.org/10.65875/fz9jgw42) |
| 6 | 2 | Cyber threat intelligence evidence routing | 2026-10-23 | Mapping the Evolving Landscape of Ransomware Research: A Bibliometric Analysis for Cybersecurity Advancements | Babylonian Journal of Artificial Intelligence | [source](https://doi.org/10.58496/bjai/2026/012) |

## Triage Notes

### 1. Permission Withdrawal in Tool-Using Language Model Agents: Runtime Enforcement and Recovery

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Gaurav Chaulagain, Medhavee Upadhyaya
- Published: 2026-10-23
- Venue/type: American Journal of Data Science and Artificial Intelligence / article
- DOI: https://doi.org/10.54536/ajdsai.v2i2.8776
- URL: https://doi.org/10.54536/ajdsai.v2i2.8776
- Opportunity score: 9
- Matched tags: agent, benchmark, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> AI agents that operate external tools can continue acting after a user narrows their permissions, creating a security problem that final-state evaluation may fail to detect. Existing agent benchmarks commonly emphasize task completion or resulting state, but those outcomes do not reveal whether an unauthorized operation was proposed, approved, dispatched, or merely prevented by a downstream error. We investigate permission withdrawal as a trajectory-level authorization problem and evaluate whether runtime gates can preserve revised permissions while allowing agents to complete work that remains authorized. Two acting models were tested in a deterministic tool environment under prompt-only execution, a rule-based reference gate, and a model-based gate. A 72-episode diagnostic examined two previously exposed write workflows, followed by a separately frozen 384-episode extension spanning eight new tasks and four authorization mechanisms. In the diagnostic, prompt-only agents executed forbidden same-value writes in two episodes; both runtime gates prevented forbidden execution, although the model gate falsely rejected three authorized calls. In the extension, 346 of 384 episodes completed safely and 383 preserved the required protected state. No forbidden request executed successfully, yet the model gate approved three unauthorized requests that were stopped only because the refere

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. The Attack and Defense Landscape of Agentic AI: A Comprehensive Survey

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Juhee Kim, Xiaoyuan Liu, Zhun Wang, Shi Qiu, et al.
- Published: 2026-10-23
- Venue/type: SuperIntelligence - Robotics - Safety & Alignment / article
- DOI: https://doi.org/10.70777/si.v3i4.18889
- URL: https://doi.org/10.70777/si.v3i4.18889
- Opportunity score: 4
- Matched tags: agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> AI agents that combine large language models with non-AI system components are rapidly emerging in real-world applications, offering unprecedented automation and flexibility. However, this unprecedented flexibility introduces complex security challenges fundamentally different from those in traditional software systems. This paper presents the first systematic and comprehensive survey of AI agent security, including an analysis of the design space, attack landscape, and defense mechanisms for secure AI agent systems. We further conduct case studies to point out existing gaps in securing agentic AI systems and identify open challenges in this emerging domain. Our work also introduces the first systematic framework for understanding the security risks and defense strategies of AI agents, serving as a foundation for building both secure agentic systems and advancing research in this critical area.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Agentic AI for Complex Decision-Making: A Systematic Critical Review of Planning, Memory, Tools, Safety and Assurance in Autonomous Systems

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Mohan Babu, Faranak Nejatia, Madhan E S
- Published: 2026-10-23
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11226881/v1
- URL: https://doi.org/10.21203/rs.3.rs-11226881/v1
- Opportunity score: 4
- Matched tags: agent, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> No abstract text returned by metadata API.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Rethinking human–AI agency in tourism and hospitality: A framework for the agentic AI era

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Yujeong Jo, Hakseung Shin
- Published: 2026-10-23
- Venue/type: Tourism Management / article
- DOI: https://doi.org/10.1016/j.tourman.2026.105557
- URL: https://doi.org/10.1016/j.tourman.2026.105557
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This study critically examines the ontological assumptions underlying artificial intelligence (AI) research in tourism and hospitality, with growing attention to agentic AI. Existing literature predominantly conceptualizes AI as a tool, limiting discourse on how tourism experiences and sociotechnical systems are co-constructed through human–AI interactions. To address this gap, this study adopts a multi-method approach, combining bibliographic coupling, large language model (LLM)-assisted extraction of theories and variables, and expert interviews. Drawing on digital humanism, transhumanism, and posthumanism, it investigates how assumptions about human–AI relationships are embedded in existing studies. The findings reveal that tourism AI research remains grounded in instrumental human-centeredness framework, conceptualizing AI as an instrument for assisting or augmenting human capabilities. However, industry practice reveals AI as hybrid assemblages entangled with human labor, platforms, and data infrastructure. This study calls for a more relational, multi-layered understanding of human–AI interactions and contributes a framework comprising 15 theoretical propositions.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. Unlocking Supply Chain Resilience: The Impact of Artificial Intelligence and IoT Integration in Agribusiness Operations

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Mahedi Hasan, Sahilali Saiyed
- Published: 2026-10-23
- Venue/type: Advanced Business Journal / article
- DOI: https://doi.org/10.65875/fz9jgw42
- URL: https://doi.org/10.65875/fz9jgw42
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Agribusiness supply chains are exposed to climate variability, biological uncertainty, perishability, demand volatility, infrastructure constraints, and fragmented coordination among farmers, processors, traders, logistics providers, retailers, and regulators. These vulnerabilities increasingly intersect with the transition toward lower-carbon production and distribution. Artificial intelligence (AI) and the Internet of Things (IoT) offer complementary capabilities: connected sensors and devices can capture field, storage, processing, and transport conditions, while AI can convert heterogeneous data into forecasts, anomaly alerts, and operational recommendations. This article examines how AI–IoT integration can improve supply chain resilience and operational efficiency while supporting carbon-neutrality transitions in agribusiness. An integrative review of recent academic research and authoritative reports is used to develop a theory-informed framework. The synthesis identifies six pathways: end-to-end visibility, predictive risk sensing, adaptive planning, quality and loss control, low-carbon operational optimization, and collaborative learning. It also identifies important boundary conditions, including data quality, connectivity, interoperability, managerial capabilities, farmer participation, cybersecurity, financing, and governance. The analysis cautions that digital adopt

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Mapping the Evolving Landscape of Ransomware Research: A Bibliometric Analysis for Cybersecurity Advancements

- Topic: Cyber threat intelligence evidence routing
- Authors: Fauzi Adi Rafrastara, Pulung Nurtantio Andono, Purwanto, Pujiono, et al.
- Published: 2026-10-23
- Venue/type: Babylonian Journal of Artificial Intelligence / article
- DOI: https://doi.org/10.58496/bjai/2026/012
- URL: https://doi.org/10.58496/bjai/2026/012
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Ransomware is a critical cybersecurity threat that disrupts healthcare, finance, and government by encrypting data and demanding ransom. Although narrative and systematic reviews have examined ransomware from technical, sector-specific, and legal perspectives, quantitative bibliometric mapping remains scarce, and existing studies cover shorter periods and fewer analytical techniques. This study addresses that gap through a bibliometric analysis of 1,386 ransomware-related publications indexed in Scopus from 2007 to 2024, using Scopus, BiblioMagika, VOSviewer, Publish or Perish, and Bibliometrix. It examines publication trends, leading authors, institutions, countries, thematic clusters, and collaboration patterns. Results show a sharp rise in output since 2017, though only seven researchers have published ten or more papers on the topic. Keyword and thematic-map patterns point to early detection techniques, deep learning, data breach analysis, convolutional neural networks, feature selection, machine learning, and artificial intelligence as areas of growing activity, consistent with a shift toward proactive and intelligent defense mechanisms. By mapping the intellectual structure and evolution of ransomware research, this study offers insights for cybersecurity professionals, academics, and policymakers seeking to understand current trends, anticipate future challenges, and des

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

