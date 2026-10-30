# Praxis Recon Daily Literature Scan

Generated: 2026-10-30 16:50 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 13 | Provenance-aware tool-boundary monitoring | 2026-10-28 | From task-specific networks to foundation models in diabetes care: a critical review of opportunities, evaluation gaps, and safety frontiers | Frontiers in Artificial Intelligence | [source](https://doi.org/10.3389/frai.2026.1983619) |
| 2 | 8 | Agentic package hallucination and tool-boundary gates | 2026-10-28 | CHRONOS: An AI-Powered Kernel Monitoring and Attack Visualization Platform Using eBPF Telemetry and Behavioural Graphs | International Journal of Advanced Research in Science Communication and Technology | [source](https://doi.org/10.48175/ijarsct-40338) |
| 3 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-10-28 | Internal security in the digital age – challenges and development areas | Przegląd Bezpieczeństwa Wewnętrznego | [source](https://doi.org/10.4467/20801335pbw.26.036.24185) |

## Triage Notes

### 1. From task-specific networks to foundation models in diabetes care: a critical review of opportunities, evaluation gaps, and safety frontiers

- Topic: Provenance-aware tool-boundary monitoring
- Authors: M. Nanda Kishore, C. Navaneethan
- Published: 2026-10-28
- Venue/type: Frontiers in Artificial Intelligence / article
- DOI: https://doi.org/10.3389/frai.2026.1983619
- URL: https://doi.org/10.3389/frai.2026.1983619
- Opportunity score: 13
- Matched tags: benchmark, dataset, evaluation, open problem, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial intelligence in diabetes care has historically relied on task-specific supervised learning, such as bespoke networks for retinopathy grading, kidney disease prediction, and glucose forecasting. The emergence of foundation models (FMs: large models pretrained on broad data, typically with self-supervision, and adapted to many downstream tasks) is displacing this paradigm across diabetes-relevant modalities: ophthalmic models such as RETFound, pretrained on 1.6 million retinal photographs, have been reported to outperform task-specific networks on retinopathy grading and systemic disease prediction, especially when labeled data are scarce; transformer-based time-series models are replacing long short-term memory (LSTM) pipelines for continuous glucose monitoring (CGM) forecasting; clinical large language models (LLMs) such as Med-PaLM and GPT-4 attain expert-level scores on medical question-answering benchmarks; and generative models supply synthetic CGM and electronic health record (EHR) data. This review provides a critical, modality-organized synthesis of this transition. We (i) formalize a three-era taxonomy: rule-based risk scores (era I), task-specific deep learning (era II, 2016–2020), and foundation models (era III, from 2021), and map the diabetes literature onto it; (ii) survey foundation-model architectures, pretraining objectives, and adaptation strategies 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. CHRONOS: An AI-Powered Kernel Monitoring and Attack Visualization Platform Using eBPF Telemetry and Behavioural Graphs

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Asuwath Kumaresh V, Jesvin Bruce J, P. Sai Mounisha
- Published: 2026-10-28
- Venue/type: International Journal of Advanced Research in Science Communication and Technology / article
- DOI: https://doi.org/10.48175/ijarsct-40338
- URL: https://doi.org/10.48175/ijarsct-40338
- Opportunity score: 8
- Matched tags: MITRE ATT&CK, security, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Security tools generate many endpoint alerts that analysts must correlate manually to understand an intrusion. This paper presents CHRONOS, an AI-assisted kernel-monitoring and attack-visualization platform that links low-level Linux telemetry to interpretable behavioural context. The design combines eBPF event collection, schema normalization, optional Kafka streaming, PostgreSQL/TimescaleDB storage, a time-aware NetworkX behavioural graph, rule- and model-assisted threat analysis, evidence-linked MITRE ATT&CK mapping, template-based narration and a React dashboard. A policy-gated response design keeps human approval before disruptive action. We describe the architecture, graph model, workflow, prototype components and a layered verification plan. CHRONOS is a research prototype; no accuracy, latency or overhead figures are claimed because reproducible measurements have not yet been collected. Its contribution is a traceability-first design in which every finding and narrative statement links to source events

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Internal security in the digital age – challenges and development areas

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Michał Antoniuk
- Published: 2026-10-28
- Venue/type: Przegląd Bezpieczeństwa Wewnętrznego / article
- DOI: https://doi.org/10.4467/20801335pbw.26.036.24185
- URL: https://doi.org/10.4467/20801335pbw.26.036.24185
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The aim of this article is to present and systematise contemporary directions in the development of internal security in the context of advancing digital transformation. The subject of the study is the impact of digital technologies on the nature of internal threats and on the functioning of institutions responsible for ensuring state security. The article has a review-analytical character. The study employs a review of the relevant literature, an analysis of legal acts and strategic documents. The author compared the solutions for application of digital technologies in the field of security adopted in different countries and international organisations. The conducted analysis demonstrates that the development of these technologies has fundamentally transformed internal security systems, requiring changes in management models, the development of interinstitutional cooperation, and the adaptation of legal frameworks to emerging threats. In the conclusions, the author indicates that effective internal security in the digital age requires an integrated approach combining technological solutions, appropriate legal frameworks, development of institutional capacities, and international cooperation.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

