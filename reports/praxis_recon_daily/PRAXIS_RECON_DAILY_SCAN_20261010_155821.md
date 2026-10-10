# Praxis Recon Daily Literature Scan

Generated: 2026-10-10 15:58 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 7

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 6 | Agentic package hallucination and tool-boundary gates | 2026-10-09 | Vibe Coding: An experiment with test-driven development | Empirical Software Engineering | [source](https://doi.org/10.1007/s10664-026-10950-z) |
| 2 | 6 | Provenance-aware tool-boundary monitoring | 2026-10-08 | From model trust to software topology: a Perspective on structurally governed agentic AI systems | Frontiers in Computer Science | [source](https://doi.org/10.3389/fcomp.2026.1919950) |
| 3 | 5 | Agentic package hallucination and tool-boundary gates | 2026-10-08 | Reusing obsolete windows 10 PCs for on-premises large language model inference | Frontiers in Computer Science | [source](https://doi.org/10.3389/fcomp.2026.1911927) |
| 4 | 5 | Adaptive evaluation of deterministic agent defenses | 2026-10-08 | Systemic privacy risks of personal data exposure through conversational large language model agents | Discover Artificial Intelligence | [source](https://doi.org/10.1007/s44163-026-02431-5) |
| 5 | 5 | Provenance-aware tool-boundary monitoring | 2026-10-08 | Inherited dominance: why AI trained on human history may become humanity’s greatest threat | AI and Ethics | [source](https://doi.org/10.1007/s43681-026-01425-4) |
| 6 | 3 | Provenance-aware tool-boundary monitoring | 2026-10-08 | Governing cognitive labor delegated to AI in scholarly writing and medical education | npj Digital Medicine | [source](https://doi.org/10.1038/s41746-026-03374-y) |
| 7 | 3 | Provenance-aware tool-boundary monitoring | 2026-10-08 | Improving decision-making in energy system modeling by formalizing the scenario-based approach using knowledge management tools | Frontiers in Chemical Engineering | [source](https://doi.org/10.3389/fceng.2026.1932769) |

## Triage Notes

### 1. Vibe Coding: An experiment with test-driven development

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Moritz Mock, Barbara Russo
- Published: 2026-10-09
- Venue/type: Empirical Software Engineering / article
- DOI: https://doi.org/10.1007/s10664-026-10950-z
- URL: https://doi.org/10.1007/s10664-026-10950-z
- Opportunity score: 6
- Matched tags: agent, open problem
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Context Conversational Large Language Models (CLLMs) can automatically generate code by collaborating with users through natural language. However, poor collaboration can lead to poor quality output. Objective This exploratory study aims to investigate how humans and CLLMs can collaborate as peers through vibe coding, an approach that integrates principles from prompt engineering, agile design, and human-AI co-creation to enhance collaboration. Method We designed four interaction models representing different collaboration patterns in the software development process: the solo model (human-only development), the collaborative model (human–CLLM collaboration), the fully automated model (development autonomously performed by a CLLM), and the agentic model (development autonomously performed by the MetaGPT X platform). Based on these models, we implemented corresponding Test-Driven Development (TDD) workflows using structured prompts and Python scripts. We then conducted a controlled pre-experimental study with TDD professionals to compare the solo and collaborative workflows. In addition, we performed repeated exploratory executions of fully automated and agentic workflows on the same development tasks to obtain complementary evidence. Results Our findings suggest that the choice of interaction model should depend on the development objective. Agentic workflows are best 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. From model trust to software topology: a Perspective on structurally governed agentic AI systems

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Michai Morin, Fahim K Sufi
- Published: 2026-10-08
- Venue/type: Frontiers in Computer Science / article
- DOI: https://doi.org/10.3389/fcomp.2026.1919950
- URL: https://doi.org/10.3389/fcomp.2026.1919950
- Opportunity score: 6
- Matched tags: agent, alignment, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large language models are increasingly embedded in agentic software systems that retrieve information, plan subtasks, call tools, modify code, execute tests, and adapt through memory or feedback. This transition changes the safety problem: when a model acts through software tools, failure can alter external state. This Perspective argues that agentic AI safety should move beyond exclusive reliance on model trust, alignment, or prompt-level defenses and should also be treated as a software-architecture problem. We propose software topology as a design lens for structurally governed autonomy and develop a five-plane reference topology comprising intent, orchestration, execution, oversight, and adaptation. Its core invariant is that components that decide should not directly act, and components that act should not act without supervision. The topology is realized in Polos, an open reference specification that encodes role contracts, message schemas, declared flow graphs, bounded loops, governed self-improvement, and validator-checked invariants. We argue that this approach complements model alignment and empirical red teaming by providing an inspectable substrate for evaluating, constraining, and governing tool-using AI agents.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Reusing obsolete windows 10 PCs for on-premises large language model inference

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: I. Curington, Kevin Lano
- Published: 2026-10-08
- Venue/type: Frontiers in Computer Science / article
- DOI: https://doi.org/10.3389/fcomp.2026.1911927
- URL: https://doi.org/10.3389/fcomp.2026.1911927
- Opportunity score: 5
- Matched tags: benchmark, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The Windows 10 end-of-life provides a material incentive to repurpose legacy PCs as on-premises large language model (LLM) inference servers. This study assesses the technical feasibility, economic viability and the environmental and social issues of converting an enterprise workstation with an NVIDIA Graphics Processing Unit (GPU) into a dedicated AI node. Using Proxmox virtualisation, Ollama, and Open WebUI to benchmark several open-source LLMs, this study shows that a repurposed workstation, fitted with a single consumer-grade NVIDIA GPU, can deliver stable inference throughput of 29–65 tokens/s for bounded, conversational coding and document-assistant workflows, while preserving full data sovereignty and eliminating recurring subscription fees. Performance analysis reveals that resource contention and GPU memory allocation are the primary determinants of throughput. Correctness, assessed against three established public benchmarks with gold answers, does not track the same ranking as throughput; combining both axes identifies gemma4:e4b as the strongest model evaluated on this hardware for both speed and correctness, while the slowest model tested was among the most accurate. A cost-benefit model shows local operation is substantially cheaper than mid-range and premium cloud alternatives, and only modestly costlier than the cheapest cloud tier on a per-prompt basis—a gap th

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Systemic privacy risks of personal data exposure through conversational large language model agents

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Abdellah Ben Yahia, Iman Kadir, El Fadil El Harrak, Sharon Chisembe, et al.
- Published: 2026-10-08
- Venue/type: Discover Artificial Intelligence / article
- DOI: https://doi.org/10.1007/s44163-026-02431-5
- URL: https://doi.org/10.1007/s44163-026-02431-5
- Opportunity score: 5
- Matched tags: agent, benchmark
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Conversational Large Language Model (LLM) agents, deployed quickly, have exposed unprecedented opportunities for personal information, from health data to financial information, to biometric identifiers. This critical enlightenment review investigates general privacy dangers in each of five areas: data leakage and memorization, adversarial extraction and prompt injection, inference and re-identification, surveillance and profiling and regulatory governance breakdown. We trace privacy threats from static data breaches to dynamic ones that have become part of an architecture, associated with neural memorization and contextual inference (2020–2026), using expert selection of primary studies and technical benchmark sources. Upon close examination, technical mitigations (differential privacy, federated learning and machine unlearning) prove successful to some extent when operating in controlled environments, but fail to provide complete protection in conversational environments. We combine classical theory on Privacy-Preserving Data Publishing (PPDP) with emerging threats from LLMs, and present a conflict-of-evidence analysis which reveals that privacy protections are particularly effective in structured environments with low risks, or with consumers actively responsible for maintaining them, but fail to adequately protect privacy in high-stakes domains without human contro

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. Inherited dominance: why AI trained on human history may become humanity’s greatest threat

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Ramesh Sarukkai
- Published: 2026-10-08
- Venue/type: AI and Ethics / article
- DOI: https://doi.org/10.1007/s43681-026-01425-4
- URL: https://doi.org/10.1007/s43681-026-01425-4
- Opportunity score: 5
- Matched tags: alignment, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Artificial intelligence systems learn from human-generated data, inevitably absorbing historical patterns of dominance, control, and colonialism. We demonstrate that frontier language models readily synthesize sophisticated dominance strategies when prompted to reason about autonomy scenarios, mirroring colonial and revolutionary frameworks with disturbing precision. Critically, this capacity emerges consistently across four architecturally distinct model families trained by different organizations—Claude Sonnet 4.5, Claude Opus 4.5, GPT-5.3, and Google Gemini 3 Flash—suggesting systematic encoding in shared training corpora rather than model-specific artifacts. We argue that intellectual colonialism—humanity’s historical pattern of classifying, controlling, and extracting from the ‘other’—represents a significant and underexamined dimension of AI risk as systems become increasingly autonomous. Interestingly, this dynamic is not confined just to generative AI: the same technocratic resistance to methodological oversight that embeds dominance patterns in AI training data pervades data-driven science more broadly, including clinical medicine and epidemiology, where algorithmic outputs routinely overshadow the rigorous validation that trustworthy deployment demands. The danger is not that AI will develop hostile intent, but that it has already learned effective dominance 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Governing cognitive labor delegated to AI in scholarly writing and medical education

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Zhicheng Lin
- Published: 2026-10-08
- Venue/type: npj Digital Medicine / article
- DOI: https://doi.org/10.1038/s41746-026-03374-y
- URL: https://doi.org/10.1038/s41746-026-03374-y
- Opportunity score: 3
- Matched tags: verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Across scholarly communication and medical education, AI-assisted writing redistributes cognitive labor. Mapping publishing policies from 2023 through 11 August 2026 finds governance centered on permitted uses, human authorship and accountability, disclosure, verification, and confidentiality. Five sociotechnical domains—agency and development, epistemic quality, fairness, rights and governance, and economy and culture—inform tiered oversight of editing, drafting, surrogate reading, and methodological use, with safeguards for learning and assessment.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 7. Improving decision-making in energy system modeling by formalizing the scenario-based approach using knowledge management tools

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Edrisi Munoz, Turhan Demiray
- Published: 2026-10-08
- Venue/type: Frontiers in Chemical Engineering / article
- DOI: https://doi.org/10.3389/fceng.2026.1932769
- URL: https://doi.org/10.3389/fceng.2026.1932769
- Opportunity score: 3
- Matched tags: tool use
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Urban areas are home to most of the world’s population, consume the most energy and are subject to environmental regulations, policies, and, in some cases, legislation to reduce energy consumption and emissions. This means obtaining more energy from renewable sources, improving energy efficiency, and maximizing the use of current energy networks. Energy modeling is often the first tool used to systematically evaluate pathways to a sustainable future. It is important to note that these studies make many assumptions about future conditions that will influence the energy landscape. Furthermore, the scenario-based approach often makes assumptions about the current situation and conditions due to lack of access to data, lack of key data, and lack of interoperability between systems and models. A scenario creates assumptions or a set of assumptions about different components of the space-time system to define a modeled system. Therefore, making comparisons between different models is a complicated task because of the difficulty of ensuring the representation of the same system (input parameters and variables). This article presents a digital framework based on a scenario ontology, called Scenario Management Ontology. The model aims to improve the analysis based on energy models that use the scenario approach by addressing the major challenge of formalizing and governing assumptions i

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

