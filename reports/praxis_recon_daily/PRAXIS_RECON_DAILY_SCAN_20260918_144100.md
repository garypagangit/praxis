# Praxis Recon Daily Literature Scan

Generated: 2026-09-18 14:41 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 9 | Agentic package hallucination and tool-boundary gates | 2026-09-17 | HydroSuite-AI: a web-based LLM environment for hydrological code generation and execution for the hydrosuite open-source ecosystem | Earth Science Informatics | [source](https://doi.org/10.1007/s12145-026-02222-7) |
| 2 | 6 | Agentic package hallucination and tool-boundary gates | 2026-09-17 | TRAFFICGEN: a multi-agent LLM orchestration for smart mobility and emergency corridor pre-emption | Frontiers in Artificial Intelligence | [source](https://doi.org/10.3389/frai.2026.1894645) |
| 3 | 4 | Provenance-aware tool-boundary monitoring | 2026-09-17 | Interaction-induced knowledge narrowing risk in LLM systems | Discover Artificial Intelligence | [source](https://doi.org/10.1007/s44163-026-02101-6) |

## Triage Notes

### 1. HydroSuite-AI: a web-based LLM environment for hydrological code generation and execution for the hydrosuite open-source ecosystem

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Vinay Pursnani, Carlos Erazo Ramirez, Yusuf Sermet, İbrahim Demir
- Published: 2026-09-17
- Venue/type: Earth Science Informatics / article
- DOI: https://doi.org/10.1007/s12145-026-02222-7
- URL: https://doi.org/10.1007/s12145-026-02222-7
- Opportunity score: 9
- Matched tags: benchmark, limitation, limitations
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Researchers in hydrology face technical barriers from complex models, evolving libraries, and fragmented documentation. We present HydroSuite-AI, an LLM-based assistant that integrates the open-source web hydrologic libraries HydroLang, HydroCompute, and HydroRTC for code generation, factual guidance, and in-browser execution of hydrological workflows. The system uses a Planner-Worker-Synthesizer architecture with retrieval-augmented generation (RAG) over library documentation and validates outputs in a client-side virtualized execution environment. We evaluate HydroSuite-AI through (i) a cross-library case study, (ii) a controlled benchmark measuring the assistant’s ability to retrieve and execute library functions across 60 domain-specific tasks under different LLM backends, and (iii) deployment as a code assistant in the WaterSoftHack 2024 workshop. Across the benchmark tasks, HydroSuite-AI achieves 95.0% function retrieval accuracy with 23.1 s mean latency when powered by o3-mini, while the same system reaches 71.7% under 10s with GPT-4.1-nano, showing an accuracy–speed tradeoff across model configurations. The case study demonstrates end-to-end interoperability and exposes limitations in advanced statistical workflows, and the workshop deployment confirms the system’s utility in collaborative, time-constrained settings. Documentation-grounded LLM orchestration red

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. TRAFFICGEN: a multi-agent LLM orchestration for smart mobility and emergency corridor pre-emption

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Gaurav Soni, Ganesh Khekare, Yash Kumar, Rupaak S.
- Published: 2026-09-17
- Venue/type: Frontiers in Artificial Intelligence / article
- DOI: https://doi.org/10.3389/frai.2026.1894645
- URL: https://doi.org/10.3389/frai.2026.1894645
- Opportunity score: 6
- Matched tags: agent, evaluation, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This research work introduces TrafficGen, a proof-of-concept software prototype that explores the possibility of adaptive traffic signal management using LLM-based agentic orchestration. The framework is evaluated in a single-intersection, deterministic simulation environment that uses text to represent the various intersections and can operate with Gemini 2.5 Flash and LangGraph to implement a “Council of Agents” control architecture. TrafficGen uses a semantic translation layer to generate human-readable chain-of-thought reasoning logs for each signal decision, enabling it to manage complex traffic patterns. In empirical stochastic evaluations, TrafficGen was tested using four custom stress scenarios and 30 independent runs, yielding a mean reduction of 46.9% ± 2.8% in Wait Burden Score across all scenarios and runs (from 6,370 points to 3,380 points per run, compared to standard fixed-time signal controllers). Additionally, 100% of the Green Corridor maintained a success rate for dynamic emergency vehicle pre-emption. Architecturally, the system achieved a 100% decision override latency of 1,556 ms and a Green Corridor success rate of 100% for life safety evaluations. The quantitative results show the effectiveness of zero-shot semantic LLM orchestration compared to other LLM controllers with heuristic rules. These results come from a controlled single intersection environme

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Interaction-induced knowledge narrowing risk in LLM systems

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Dale Rutherford, Ningning Wu
- Published: 2026-09-17
- Venue/type: Discover Artificial Intelligence / article
- DOI: https://doi.org/10.1007/s44163-026-02101-6
- URL: https://doi.org/10.1007/s44163-026-02101-6
- Opportunity score: 4
- Matched tags: agent, alignment
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> AI governance frameworks address well-documented risks through controls on data, models, and post-deployment performance. This paper identifies a distinct, under-governed lifecycle risk arising not from model error or degradation, but from interaction itself. Termed Interaction-Induced Knowledge Narrowing (IIKN), this risk occurs when bounded context windows, ranked probabilistic synthesis, and iterative interaction dynamics systematically constrain the epistemic scope surfaced during AI system use. IIKN manifests as unobserved exclusion rather than incorrectness: AI systems may produce fluent, accurate, and aligned outputs while silently omitting plausible, defensible, and consequential alternatives. Because IIKN leaves no error signal, it routinely passes undetected by conventional assurance mechanisms. This paper provides a formal definition, differentiates IIKN from adjacent risk categories, and explains its emergence through inference-time selection and interaction path dependence. Mapping IIKN across the AI lifecycle demonstrates why late-stage review is insufficient and early controls are necessary. The paper proposes proportionate governance controls, including epistemic scope declaration, breadth-before-depth interaction patterns, coverage confirmation checkpoints, and lifecycle-aligned trigger gates, that render exclusion explicit and accountable without requiring exh

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

