# Praxis Recon Daily Literature Scan

Generated: 2026-11-06 17:43 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 4

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 22 | Cyber threat intelligence evidence routing | 2026-11-05 | NeuroGraph: an AI graph-driven neuro-symbolic framework for explainable threat reasoning in advanced manufacturing | International Journal of Information Security | [source](https://doi.org/10.1007/s10207-026-01345-8) |
| 2 | 5 | Agentic package hallucination and tool-boundary gates | 2026-11-05 | The Impact of AI Coding Assistants on Software Engineering: A Longitudinal Study | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3861343) |
| 3 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-11-05 | Beyond Signatures and IP Blocking: A Critical Survey of WAF Evaluation under Source-Path Diversity, Payload Mutation, and Parser Discrepancy | Technological Pathways and Development | [source](https://doi.org/10.70693/rptjzk54) |
| 4 | 2 | Agentic package hallucination and tool-boundary gates | 2026-11-04 | An expert-AI co-creation framework for robust health economic simulations | Expert Review of Pharmacoeconomics & Outcomes Research | [source](https://doi.org/10.1080/14737167.2026.2755647) |

## Triage Notes

### 1. NeuroGraph: an AI graph-driven neuro-symbolic framework for explainable threat reasoning in advanced manufacturing

- Topic: Cyber threat intelligence evidence routing
- Authors: Padmeswari Nandiya, Ahmad Mohsin, Iqbal Hasan Sarker, Ahmed Ibrahim, et al.
- Published: 2026-11-05
- Venue/type: International Journal of Information Security / article
- DOI: https://doi.org/10.1007/s10207-026-01345-8
- URL: https://doi.org/10.1007/s10207-026-01345-8
- Opportunity score: 22
- Matched tags: benchmark, cyber threat intelligence, evaluation, hallucination, limitation, retrieval, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract The growing complexity of cyber-physical attack surfaces in advanced manufacturing environments has made reliable cyber threat intelligence analysis increasingly challenging. While large language models and retrieval-augmented generation have enhanced cyber threat intelligence capabilities, text-based approaches remain prone to hallucinations and lack structured reasoning over interconnected threats. Graph-based retrieval-augmented generation partially addresses this limitation but often fails to support ontology-consistent multi-hop reasoning and transparent evidence tracing across heterogeneous cybersecurity knowledge. This paper proposes a graph-grounded neuro-symbolic framework that integrates ontology-aware symbolic query generation, knowledge graph retrieval, and neural language generation to enable accurate and explainable threat analysis across information technology and operational technology domains. The proposed framework employs a dual-large language model architecture in which the first model translates natural-language queries into executable Cypher statements for symbolic graph retrieval, while the second generates responses exclusively from the retrieved graph evidence. Experimental evaluation on publicly available cyber threat intelligence benchmarks demonstrates consistent improvements over the published baseline in reasoning accuracy while reducing h

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. The Impact of AI Coding Assistants on Software Engineering: A Longitudinal Study

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Annie Vella, Kelly Blincoe
- Published: 2026-11-05
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3861343
- URL: https://doi.org/10.1145/3861343
- Opportunity score: 5
- Matched tags: evaluation, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> AI coding assistants have become prolific in recent years. Through a longitudinal mixed-methods investigation, we examined how professional software engineers perceive the effects of AI coding assistants in regard to task focus, developer experience, and productivity. Two questionnaires were administered six months apart, yielding 158 eligible participants at the first time point, 101 at the second, and a matched longitudinal cohort of 95. Participants reported spending less time on most development tasks, with 82% reporting less on writing code. We found a broader shift in focus from creation to verification activities. We propose a new category of work we term supervisory engineering work , encompassing the direction, evaluation, and correction of AI output. This construct is broader than the extra review overhead that has been previously reported in literature since it encompasses directing and shaping AI output both before and during creation. We also identified a productivity-experience paradox: consistently positive productivity perceptions alongside eroding developer experience. These findings suggest that AI coding assistants may be reshaping both the nature of software engineering work and how engineers experience it.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Beyond Signatures and IP Blocking: A Critical Survey of WAF Evaluation under Source-Path Diversity, Payload Mutation, and Parser Discrepancy

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: HaoLan Su
- Published: 2026-11-05
- Venue/type: Technological Pathways and Development / article
- DOI: https://doi.org/10.70693/rptjzk54
- URL: https://doi.org/10.70693/rptjzk54
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Web application firewall research is often organized by the signal available to a decision or enforcement layer: request content, client identity, browser behavior, or traffic history. That organization is useful for isolated experiments, but it leaves open how a WAF should be evaluated when these pressures occur together. A malicious request may arrive through a changing or shared source path, use a different surface form, and pass through parsers that do not agree on its meaning. This survey reviews signature and rule filtering, transport and client fingerprinting, challenge-based enforcement, surface-form machine learning, intent-oriented language models, behavioral linkage, and protocol normalization. It separates direct WAF measurements from adjacent evidence on proxy identification, encrypted-traffic classification, and general intrusion detection, and treats parser discrepancy as a distinct failure mode rather than another payload mutation. The reviewed corpus shows clear one-axis evidence: payload mutation and parser-level differences can change WAF outcomes, while source-path studies show that identity and transport signals can rotate, overlap, or be manipulated. We did not identify a direct focal-WAF experiment that varies source-path conditions and payload realization together while verifying the intended application-level effect. The survey therefore proposes compos

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. An expert-AI co-creation framework for robust health economic simulations

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Anna Machens, Hendrik Koffijberg, Shiva Faeghi
- Published: 2026-11-04
- Venue/type: Expert Review of Pharmacoeconomics & Outcomes Research / article
- DOI: https://doi.org/10.1080/14737167.2026.2755647
- URL: https://doi.org/10.1080/14737167.2026.2755647
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> BACKGROUND: Health economic (HE) evaluations are essential for healthcare decision-making, yet the rapid pace of innovation demands accelerated HE evaluations. Integrating Generative AI (GenAI), particularly Large Language Models (LLMs), into HE simulation modeling offers a promising opportunity to enhance model development efficiency and speed. RESEARCH DESIGN AND METHODS: We propose a framework for automating HE model development through expert-AI co-creation. This framework enables GenAI to generate simulation models in a structured and transparent manner. The proposed approach is expert-led and incorporates iterative prompt-response cycles. GPT5-mini and GPT-5.2-codex are employed using zero-shot prompting. As LLM results are non-deterministic, we introduced a Prompt Robustness Test (PRT) to assess the stability of LLM-generated outputs, indicating whether a prompt is sufficiently reliable to support automated model development. The methodology is applied to replicate a published discrete-event simulation comparing two post-surgery treatment strategies for colon cancer. The original model is complex and representative of real-world HE practice. RESULTS: Using our framework, we replicated the model in Python, achieving cost and QALY estimates within 2% of the original. While the overall pathway structure was successfully reconstructed, several logic discrepancies remained co

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

