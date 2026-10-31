# Praxis Recon Daily Literature Scan

Generated: 2026-10-31 15:54 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 6

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 12 | Provenance-aware tool-boundary monitoring | 2026-10-29 | Artificial intelligence-assisted art therapy in digital psychiatry: Clinical applications, mechanisms, and ethics | World Journal of Psychiatry | [source](https://doi.org/10.5498/wjp.125040) |
| 2 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-10-29 | MutQA: A Cross-Validated Q&A Dataset for Genetic Mutations | bioRxiv (Cold Spring Harbor Laboratory) | [source](https://doi.org/10.64898/2026.10.27.762236) |
| 3 | 6 | Source-locked citation and hallucination verification | 2026-10-30 | Narrative theory-driven LLM methods for automatic story generation and understanding: a survey | Artificial Intelligence Review | [source](https://doi.org/10.1007/s10462-026-11717-0) |
| 4 | 5 | Adaptive evaluation of deterministic agent defenses | 2026-10-30 | BAg-IDS: A Blockchain-Enabled Agentic AI Architecture for Trustworthy Intrusion Detection | Research Square | [source](https://doi.org/10.21203/rs.3.rs-10843028/v1) |
| 5 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-10-29 | Sources of Risk in AI Systems Revisited: FCAIR-O, a Faceted Causal Framework and Lightweight Ontology for Risk Management and Assurance | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11331305/v1) |
| 6 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-10-29 | The MAL Simulator: Cyber Operations Simulation based on Attack & Defense Graphs | Research Square | [source](https://doi.org/10.21203/rs.3.rs-10888395/v1) |

## Triage Notes

### 1. Artificial intelligence-assisted art therapy in digital psychiatry: Clinical applications, mechanisms, and ethics

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Ke Meng, Mingzhi Hou, Heeju Chae
- Published: 2026-10-29
- Venue/type: World Journal of Psychiatry / article
- DOI: https://doi.org/10.5498/wjp.125040
- URL: https://doi.org/10.5498/wjp.125040
- Opportunity score: 12
- Matched tags: future research, provenance, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial intelligence-assisted art therapy should be understood as a therapistmediated extension of creative practice rather than an autonomous treatment.This structured narrative review synthesizes eleven directly relevant publications, including preliminary patient studies and adjacent creative-activity research, alongside transferable evidence from art therapy, conversational artificial intelligence, digital psychiatry, immersive technologies, affective computing, social robotics, and health-care artificial intelligence ethics.Direct patient-level evidence remains limited and heterogeneous, with mixed, domain-specific findings that do not establish general efficacy, comparative effectiveness, or safety; clinicianperspective evidence is limited, and most proposed applications and mechanisms derive from conceptual or transferable evidence.We therefore distinguish artificial intelligence used in visual creation, therapeutic dialogue or documentation, behavioral or emotional inference, and immersive or embodied interaction, and separate professional art therapy from broader digital creative activity.Supervised image-making, reflective preparation, patient-selected monitoring, and recoveryoriented follow-up are candidate uses for prospective research.The proposed taxonomy, pathway, risk framework, mechanisms, and safeguards are conceptual, research-oriented, provisional, and no

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. MutQA: A Cross-Validated Q&A Dataset for Genetic Mutations

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Robert McCourt, David Arredondo, Oladimeji Macaulay, Shrey Poshiya, et al.
- Published: 2026-10-29
- Venue/type: bioRxiv (Cold Spring Harbor Laboratory) / preprint
- DOI: https://doi.org/10.64898/2026.10.27.762236
- URL: https://doi.org/10.64898/2026.10.27.762236
- Opportunity score: 7
- Matched tags: benchmark, dataset, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> We introduce MutQA, a dataset of 330,387 citation-grounded question-answer (QA) pairs linking genetic mutations to their functional consequences as described in the biomedical literature. Each record pairs a protein-coding mutation with a natural-language question and an evidence-backed answer anchored to sentences in one of 27,442 open-access PubMed Central articles, spanning 6,620 genes and 125,593 gene-variant pairs. The dataset is constructed using CrossValQA, a framework that enforces information isolation between independent LLMs: one model generates QA pairs from an article, a second model answers the same question without access to the first model's response, and a third model judges whether each model's rationale supports the other's answer, so that retained QA pairs are reproducible from the source text rather than hallucinated. Of 401,406 audited QA pairs, 82.7% pass both directions of this cross-validation; those with a recoverable reference protein sequence form the released benchmark. In a 999-pair stratified audit, two expert annotators agree exactly on 86.4% of cross-validated QA pairs (95% CI 83.7-89.0; n = 638), a tier in which about 90% of ratings are "correct". Individual LLM judges agree with individual annotators at a comparable 87.0% on this tier but far less on QA pairs that fail cross-validation. Fine-tuning MutaPLM on MutQA nearly doubles its mean LLM-

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Narrative theory-driven LLM methods for automatic story generation and understanding: a survey

- Topic: Source-locked citation and hallucination verification
- Authors: David Y. Liu, Aditya Joshi, Paul A. Dawson
- Published: 2026-10-30
- Venue/type: Artificial Intelligence Review / article
- DOI: https://doi.org/10.1007/s10462-026-11717-0
- URL: https://doi.org/10.1007/s10462-026-11717-0
- Opportunity score: 6
- Matched tags: benchmark
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Applications of narrative theories using large language models (LLMs) deliver promising methods in automatic story generation and understanding tasks. Our survey examines how natural language processing (NLP) research uses LLM methods to engage with diverse concepts from narrative studies. We use established distinctions from narratology to categorise ongoing efforts and discover the following: (a) narrative texts come from diverse sources beyond just literature, (b) theoretical synthesis and validation are potential outcomes, (c) generation tasks lag behind understanding in several ways: theoretical application, post-training methods, exploring non-fiction narratives and addressing narrative levels beyond fabula and discourse. For future directions, instead of the pursuit of a single, generalised benchmark for ‘narrative quality’, we believe that progress can benefit from efforts that focus on the following: defining and improving theory-based metrics for individual narrative attributes; continue conducting large-scale, theory-driven literary/social/cultural analysis; generating narratives in situated contexts; and continuing experiments where outputs can be used to validate or refine narrative theories. This work provides a contextual foundation for more systematic and theoretically informed narrative research in NLP by providing an overview to ongoing research effor

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. BAg-IDS: A Blockchain-Enabled Agentic AI Architecture for Trustworthy Intrusion Detection

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mohamed Ala Eddine BAHRI, Farah Jemili, Mohamed MOSBAH
- Published: 2026-10-30
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-10843028/v1
- URL: https://doi.org/10.21203/rs.3.rs-10843028/v1
- Opportunity score: 5
- Matched tags: agent, benchmark
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Learning-based intrusion detection produces verdicts operators must simply trust: the audit record is mutable and no independent party endorses the decision. We present BAg-IDS, a distributed detection architecture in which autonomous agents detect, independently re-check, and co-sign every remediation-triggering verdict on a Hyperledger Fabric ledger before it is acted upon, placing certification on the decision path rather than in an after-the-fact log. A calibrated, reliability-weighted ensemble with a reject option feeds the quorum; language-model and governed human-in-the-loop tiers handle escalation. The full stack is implemented and every number measured. Selective certification raises accuracy from 96.6% to 99.7% (0.04% false-positive rate) at 87.3% coverage on CICIDS2017, and reaches 99.98% on the independent GeNIS 2025 corpus while deferring 0.14% of flows. A 360-alert benchmark shows the ~ 2 s consensus latency is structural: one write per key per block forces K votes across at least K blocks, a bound no submission strategy removes.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. Sources of Risk in AI Systems Revisited: FCAIR-O, a Faceted Causal Framework and Lightweight Ontology for Risk Management and Assurance

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Moritz Schneider, André Steimers
- Published: 2026-10-29
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11331305/v1
- URL: https://doi.org/10.21203/rs.3.rs-11331305/v1
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Artificial-intelligence risk frameworks often combine causal sources, vulnerabilities, failure modes, harms, desired properties, controls, evidence, and legal classifications within the same lists. This role conflation obscures mechanisms, intervention points, and responsibility. As the conceptual successor to Steimers and Schneider (2022), this article retains intended purpose, reasonably foreseeable misuse, the protective-measure hierarchy, residual risk including control-induced risk, and post-market observation. It reassesses their eight-category taxonomy through a critical integrative conceptual synthesis supported by an access-limited evidence map, best-fit framework synthesis, legal and standards analysis, and an explicit design audit trail covering material available through 25 July 2026. The resulting Faceted Causal AI Risk and Assurance Ontology (FCAIR-O v1.2.1) is a conceptual framework implemented as a lightweight ontology and controlled concept scheme. It comprises a twelve-node causal and assurance backbone, eight orthogonal facets, twelve parent causal-source classes, and 74 operational causal leaves within 221 versioned concept identifiers. Five design-oriented theoretical propositions require ontological role separation, mechanistic traceability, multi-level causality, control-evidence coupling, and distinct normative and epistemic boundaries. Fairness

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. The MAL Simulator: Cyber Operations Simulation based on Attack & Defense Graphs

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Jakob Nyberg, Sandor Berglund, Andrei Buhaiu, Joakim Loxdal, et al.
- Published: 2026-10-29
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-10888395/v1
- URL: https://doi.org/10.21203/rs.3.rs-10888395/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract We have developed the MAL Simulator, a cyber operation simulator based on the Meta Attack Language (MAL). The MAL Simulator is intended for decision-driven cyber attack and defense simulations, for system analysis and the development of automated agents. By building the simulator around an attack modeling language, it can be adapted to different target domains without modifying the source code. We used the simulator for two case studies where we trained two types of agents for automated cyber operations: a defensive agent and an offensive agent. To ground the experiments, we base the models in data collected from an emulated network implemented in the cyber range CRATE. We found that the trained attacker policy could reach the designated targets more efficiently than the compared search methods, and that the trained defender agent induced lower costs than a naive heuristic agent under noisy alert conditions. When testing the RL attacker against the RL defender, we found that the performance of the defenders dropped significantly. This emphasizes the importance of cyber attack simulators to facilitate training both offensive and defensive agents. The MAL Simulator and associated tooling is publicly available and provides common interfaces for compatibility with existing machine learning frameworks.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

