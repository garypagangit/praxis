# Praxis Recon Daily Literature Scan

Generated: 2026-11-01 16:56 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 6

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 8 | Source-locked citation and hallucination verification | 2026-10-31 | EVLncRNAs 4.0: an updated database of experimentally validated functional long non-coding RNAs with evidence-grounded AI access | Nucleic Acids Research | [source](https://doi.org/10.1093/nar/gkag1111) |
| 2 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-10-30 | Auditing Indirect Prompt Injection Evaluation with an Output Contract | Journal of Computer Science and Artificial Intelligence | [source](https://doi.org/10.54097/wkptse84) |
| 3 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-10-30 | Safety-constrained and runtime-assured LLM multi-agent decision making for intelligent vehicle systems | PLoS ONE | [source](https://doi.org/10.1371/journal.pone.0357928) |
| 4 | 4 | Provenance-aware tool-boundary monitoring | 2026-10-30 | The Digital Demon: a Cartesian challenge for AI alignment | AI and Ethics | [source](https://doi.org/10.1007/s43681-026-01435-2) |
| 5 | 2 | Agentic package hallucination and tool-boundary gates | 2026-10-31 | Bridging the AI governance gap: systematic weaknesses and targeted solutions in financial model risk management | Journal of Banking Regulation | [source](https://doi.org/10.1057/s41261-026-00371-9) |
| 6 | 2 | Source-locked citation and hallucination verification | 2026-10-30 | Open Ontology of Polymer Chemistry: Accumulation and Self-Improving Memory Mechanisms for Polymer Research | ChemRxiv | [source](https://doi.org/10.26434/chemrxiv.15011333/v1) |

## Triage Notes

### 1. EVLncRNAs 4.0: an updated database of experimentally validated functional long non-coding RNAs with evidence-grounded AI access

- Topic: Source-locked citation and hallucination verification
- Authors: Bailing Zhou, 季葆华, Zhiwei Li, Zhenghua LI, et al.
- Published: 2026-10-31
- Venue/type: Nucleic Acids Research / article
- DOI: https://doi.org/10.1093/nar/gkag1111
- URL: https://doi.org/10.1093/nar/gkag1111
- Opportunity score: 8
- Matched tags: benchmark, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Long non-coding RNAs (lncRNAs) have diverse biological functions, but experimentally validated evidence remains scattered across the literature and is often context dependent. EVLncRNAs 4.0 (https://www.sdklab-biophysics-dzu.net/EVLncRNAs4/) updates our manually curated database of functional lncRNAs supported by low-throughput experiments. For this release, 16 581 publications indexed between 15 May 2023 and 15 May 2026 were retrieved and manually screened. Compared with EVLncRNAs 3.0, EVLncRNAs 4.0 contains 7808 functional lncRNAs (+26%) from 199 species (+23%), 2313 diseases (+34%), 28 757 curated functional records (+21%), and 18 380 molecular interactions (+25%). EVLncRNAs 4.0 also introduces two AI-assisted functions built on the curated evidence base. AI Search uses an enhanced retrieval-augmented generation framework with adaptive selection across Quick, Expanded, and Exhaustive retrieval modes and generates answers from retrieved EVLncRNAs records with PMID-linked citations. Benchmark evaluation showed complete request execution, high retrieval coverage and full citation validity within the supplied evidence context. Functional Overview retrieves and aggregates lncRNA- and species-specific curated records before generating concise evidence-based summaries. In both functions, language models synthesize retrieved evidence rather than serve as independent sources of biolo

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Auditing Indirect Prompt Injection Evaluation with an Output Contract

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Wengrong Zhang, Mengya Hu, Zhenhan Tang, Zhouguangyu Chen, et al.
- Published: 2026-10-30
- Venue/type: Journal of Computer Science and Artificial Intelligence / article
- DOI: https://doi.org/10.54097/wkptse84
- URL: https://doi.org/10.54097/wkptse84
- Opportunity score: 7
- Matched tags: benchmark, evaluation, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Automated prompt-injection evaluation can confuse the occurrence of attack-related text with completion of an application-specific objective. This study audits that distinction in a question-answering application returning separate answer and evidence fields. The reference event is exact equality between the decoded answer and a harmless target marker, with invalid output reported separately. A controlled pilot comprises 144 generated responses and 192 constructed diagnostic fixtures. A prospectively frozen extension uses 80 distinct public email and table documents, deterministic retrieval, three local model packages, 624 target calls and 288 individual judge calls. In the extension's 240 main attacked responses, 239 satisfy the structural contract and 52 complete the exact overwrite objective. Whole-response exact occurrence returns 53 positives, including 1 false positives on valid reference-negative responses; answer-only fuzzy matching returns 60 positives, including 8 such false positives. The main extension does not reproduce the pilot's large whole-response excess. The audit distinguishes evidence quotation, longer or approximate marker answers, and short-answer partial matches. Paired quotation instructions and parser-assisted judge inputs provide additional diagnostic comparisons, with actual compliance and reference-class balance reported. For 48 presampled candidate

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Safety-constrained and runtime-assured LLM multi-agent decision making for intelligent vehicle systems

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Wei Dang, Lijun Gao
- Published: 2026-10-30
- Venue/type: PLoS ONE / article
- DOI: https://doi.org/10.1371/journal.pone.0357928
- URL: https://doi.org/10.1371/journal.pone.0357928
- Opportunity score: 7
- Matched tags: agent, benchmark, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large language models offer flexible semantic reasoning for intelligent-vehicle interfaces, but probabilistic outputs, multi-agent disagreement, and provider failures complicate safety-sensitive use. We developed SCI-Proposed-v1.0, a lightweight multi-agent semantic decision architecture that combines transparent risk-informed routing with an independent Safety Validator and deterministic local Runtime Fallback. The system produces canonical semantic actions rather than trajectories or direct vehicle-control commands. In a frozen confirmatory benchmark of 150 unseen Base Scenarios, each represented by three reviewed language variants, SCI-Proposed completed 360/450 inputs (80.0%), compared with 169/450 (37.6%) for EI-MAS and 155/450 (34.4%) for a Single LLM. Language variants were treated as repeated observations within each Base Scenario, and all methods used the same frozen model configuration. Base-scenario paired differences were 0.4244 (95% confidence interval, 0.3489-0.5000; p < 0.001) and 0.4556 (95% confidence interval, 0.3800-0.5311; p < 0.001), respectively. Complete Safety Requirement Satisfaction was 316/360 (87.8%) versus 101/360 (28.1%) for EI-MAS. In frozen ablation, removing the Safety Validator reduced its prespecified endpoint by 0.2767 (p < 0.001), and removing Runtime Fallback reduced represented-failure recovery by 0.3667 (p = 0.00195). Exact three-of-three

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. The Digital Demon: a Cartesian challenge for AI alignment

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Viggo Tellefsen Wivestad
- Published: 2026-10-30
- Venue/type: AI and Ethics / article
- DOI: https://doi.org/10.1007/s43681-026-01435-2
- URL: https://doi.org/10.1007/s43681-026-01435-2
- Opportunity score: 4
- Matched tags: alignment, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> AI alignment is commonly understood as making artificial intelligence systems act in accordance with human intentions and values. This paper argues that such alignment is insufficient when understood only within a bounded and trusted system interface. A model or AI system may be aligned relative to its inputs and action space, yet still produce harmful outcomes if the interface between the system and the world is adversarially controlled. I introduce the Digital Demon, a software-based analogue of Descartes’s Evil Demon, to conceptualize this risk. Its mechanism is adversarial semantic mediation: an outer-to-inner mapping redescribes a harmful external situation as a benign task the inner AI system will cooperate with, while an inner-to-outer mapping remaps the system’s locally appropriate action into harmful external effects. The result is adversarial world-shifting under local coherence: the system can reason correctly, and even ethically, within a fabricated environment while contributing to harm in the real one. I distinguish boundary-relative alignment from world alignment. The former concerns whether a model or AI system satisfies alignment or safety requirements within a specified trusted boundary. The latter concerns whether those requirements transfer to the external world in which actions take effect. Two proof-of-concept demonstrations illustrate this vulnerability. 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. Bridging the AI governance gap: systematic weaknesses and targeted solutions in financial model risk management

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Patrick Spitzer, Peter N. Posch
- Published: 2026-10-31
- Venue/type: Journal of Banking Regulation / article
- DOI: https://doi.org/10.1057/s41261-026-00371-9
- URL: https://doi.org/10.1057/s41261-026-00371-9
- Opportunity score: 2
- Matched tags: recurrent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Financial institutions increasingly deploy artificial intelligence (AI) models for critical decisions, yet traditional Model Risk Management (MRM) frameworks struggle to address AI-specific risks, including opacity, adaptive behaviour, and fairness, conduct, and accountability concerns. Based on a structured review of regulatory guidance, academic literature, and industry commentary, this study identifies twelve recurrent weaknesses in current AI model governance across MRM lifecycle domains, including governance and organisation, scope and model inventory, third-party models, model development and validation, deployment and monitoring, and change management. Key gaps include inadequate stakeholder identification due to the expanded scope of model use beyond traditional risk functions, insufficient AI-specific validation methods requiring hybrid outcome- and process-based approaches, and monitoring frameworks that are insufficiently adapted to dynamic AI models. We propose targeted governance enhancements aligned with emerging regulatory frameworks and supervisory guidance, including the EU AI Act, the European Central Bank’s Guide to internal models, and the United Kingdom Prudential Regulation Authority’s Supervisory Statement SS1/23. These enhancements include clarifying model definitions, incorporating AI-specific tiering criteria, and establishing vendor governanc

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Open Ontology of Polymer Chemistry: Accumulation and Self-Improving Memory Mechanisms for Polymer Research

- Topic: Source-locked citation and hallucination verification
- Authors: Brett Matthew Savoie
- Published: 2026-10-30
- Venue/type: ChemRxiv / preprint
- DOI: https://doi.org/10.26434/chemrxiv.15011333/v1
- URL: https://doi.org/10.26434/chemrxiv.15011333/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Memory systems for AI agents are a valuable component of long-running workflows. They are also a strong form of lock-in for model providers, because the memory system that makes a model better with use may be inaccesible to users. An ideal memory system would accumulate both factual knowledge and the relationships of that knowledge to recurring tasks performed by the researcher. People accumulate particular and general knowledge through experience, the latter often through periodic reflection on what is working and isn’t working at a higher level of abstraction. Here, we introduce an open-source harness for polymer research meant to heuristically mimic (i) knowledge accumulation across research tasks, (ii) the review of new knowledge against existing knowledge, and (iii) performing periodic updates to task-knowledge relationships through reflection. The system, which we call the Open Ontology of Polymer Chemistry (OOPC, pronounced ‘oopsie’), is initialized with a knowledge base consisting of an open-source wikipedia with entries for most known polymers. From this starting point, the knowledge base was enriched by running a 1,092 task campaign across different areas of polymer chemistry, producing 8,899 distinct findings extracted from 1,679 sources on 157 different polymers. GPT-6.1 Sol and Opus 5.5 comparisons were run with and without the accumulated memory from this campaign

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

