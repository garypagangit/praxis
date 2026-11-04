# Praxis Recon Daily Literature Scan

Generated: 2026-11-04 18:16 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 7 | Adaptive evaluation of deterministic agent defenses | 2026-11-03 | Fully homomorphic encryption on LlaMA 3 model for partial privacy preserving LLM inference | Journal of Systems Architecture | [source](https://doi.org/10.1016/j.sysarc.2026.104040) |
| 2 | 4 | Agentic package hallucination and tool-boundary gates | 2026-11-03 | Developing LLM-based multi-agent systems in software engineering: a mixed-method experience report | Empirical Software Engineering | [source](https://doi.org/10.1007/s10664-026-10955-8) |
| 3 | 4 | Provenance-aware tool-boundary monitoring | 2026-11-02 | Generative AI in L2 English Academic Writing: University Students’ Perspectives on Autonomy and Human–AI Interaction | International Journal of TESOL Studies | [source](https://doi.org/10.58304/ijts.261120) |

## Triage Notes

### 1. Fully homomorphic encryption on LlaMA 3 model for partial privacy preserving LLM inference

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Anes Abdennebi, Nadjia Kara, Laaziz Lahlou
- Published: 2026-11-03
- Venue/type: Journal of Systems Architecture / article
- DOI: https://doi.org/10.1016/j.sysarc.2026.104040
- URL: https://doi.org/10.1016/j.sysarc.2026.104040
- Opportunity score: 7
- Matched tags: benchmark, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative Artificial Intelligence applications have delivered significant improvements in service efficiency and language understanding. However, the surge in Large Language Model deployment raises critical security and privacy concerns regarding data exposure and unauthorized access to sensitive information. Quantum computing attacks pose an imminent threat to existing cryptographic protections, necessitating post-quantum cryptographic approaches. We present a partially privacy-preserving inference pipeline for LLaMA-3 by integrating fully homomorphic encryption into the transformer’s Multi-Query Attention mechanism. Our approach encrypts attention weights and computations across all 32 decoder layers of LLaMA-3.2-3B using lattice-based cryptography via the concrete-ml library, while feed-forward sublayers, layer normalization, and output projections remain in plaintext, a deliberate trade-off achieving practical feasibility on commodity CPUs. Evaluation on the instruction-tuned LLaMA-3.2-3B model yields: (i) strong semantic preservation (BERTScore-F1 ∼ 84.4%), (ii) controlled perplexity degradation (1.18 FP16 vs. 2.09 FHE), (iii) competitive BLEU-4 and ROUGE-L scores ( ∼ 35.6% and ∼ 51.8%), (iv) downstream GLUE benchmark accuracy, and (v) 825 ms latency at 17 tokens/second on AMD EPYC CPUs. We further present quantization-aware FHE and quantization bit-width ablation studies

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Developing LLM-based multi-agent systems in software engineering: a mixed-method experience report

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Mariama Celi Serafim De Oliveira, Motunrayo Osatohanmen Ibiyo, Marco Gianrusso, Claudio Di Sipio, et al.
- Published: 2026-11-03
- Venue/type: Empirical Software Engineering / article
- DOI: https://doi.org/10.1007/s10664-026-10955-8
- URL: https://doi.org/10.1007/s10664-026-10955-8
- Opportunity score: 4
- Matched tags: agent, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract The proliferation of Generative Artificial Intelligence (Gen AI) powered by large language models (LLMs) has transformed the software development process, introducing new paradigms for code generation, debugging, testing, and maintenance. While early applications focused on leveraging single, independent LLMs to assist developers with isolated tasks, recent advances have shifted toward multi-agent systems (MAS) that orchestrate multiple LLM-based agents working collaboratively toward common objectives. Despite their promising potential, using MAS encompasses a set of challenges for developers who have to carefully select the right technology, devise proper coordination rules, and design specific roles for the involved agents. In this paper, by means of a mixed-method study, we provide a comprehensive overview of the existing tools and frameworks for implementing MAS in software engineering. We qualitatively analyzed eight representative LLM-based multi-agent frameworks selected from an initial pool of 20 publicly available frameworks, and quantitatively evaluated them using the software engineering scenario. The qualitative analysis reveals a trade-off between low-code frameworks, which emphasize ease of use through integrated agent creation, orchestration, and monitoring capabilities, and high-code frameworks, which provide greater flexibility and extensibility for ad

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Generative AI in L2 English Academic Writing: University Students’ Perspectives on Autonomy and Human–AI Interaction

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Liubov Darzhinova
- Published: 2026-11-02
- Venue/type: International Journal of TESOL Studies / article
- DOI: https://doi.org/10.58304/ijts.261120
- URL: https://doi.org/10.58304/ijts.261120
- Opportunity score: 4
- Matched tags: agent, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative Artificial Intelligence (GenAI) tools are widely reported to improve writing quality and efficiency, yet their implications for autonomy, defined here as volitional, informed, and self-endorsed decision-making, remain underexplored. Drawing on an integrated Self-Determination Theory (SDT) and Sociocultural Theory (SCT) framework, this study interviewed twenty second-language (L2) English learners in Hong Kong universities about how they perceive and report their interaction practices when using GenAI in L2 academic writing. Hybrid inductive/deductive thematic analysis of the interview data yielded six themes: selective and strategic deployment of GenAI; concerns about dependency; preservation of authorial voice; perceived benefits; critical evaluation of outputs; and awareness of institutional expectations. Learners described balancing efficiency against authentic authorship, editing or reframing AI-generated text to protect their voice, and treating GenAI as a peripheral rather than primary agent. From these reported practices we derived a heuristic of seven roles that learners ascribed to GenAI: text analyst, consultant, literature search/review instrument, tutor, creative aid, adversary, and conversational partner. Implications are drawn for pedagogy that treats GenAI as a mediational tool whose contributions must be subordinated to the writer’s own intellectual a

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

