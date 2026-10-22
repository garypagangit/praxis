# Praxis Recon Daily Literature Scan

Generated: 2026-10-22 15:42 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 5

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 4 | Adaptive evaluation of deterministic agent defenses | 2026-10-20 | LLM-Attack Suite: A Unified Red-Team Framework for Privacy Evaluation of Split and Distributed LLM Systems | Unknown venue | [source](https://doi.org/10.66977/xsci.2610.0021) |
| 2 | 2 | Provenance-aware tool-boundary monitoring | 2026-10-21 | Agency as a New Organizing Abstraction for Computer Science | Communications of the ACM | [source](https://doi.org/10.1145/3806060) |
| 3 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-10-20 | Verifiable Delegated Authority for LLM Agents in Banking: A Formal Architecture, Capability Protocol, and Audit Guarantees | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11415811/v1) |
| 4 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-10-20 | Residual Privacy Leakage after Output Scrubbing in Tool-Using LLM Agents under Indirect Prompt Injection | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11428254/v1) |
| 5 | 2 | Source-locked citation and hallucination verification | 2026-10-20 | Guideline Adherence, Clinical Safety, and Source Accuracy of Commercial Large Language Models in Perioperative GLP-1 and GLP-1/GIP Receptor Agonist Management: A Scenario-Based Comparative Study | Acta Medica Alanya | [source](https://doi.org/10.30565/medalanya.1979219) |

## Triage Notes

### 1. LLM-Attack Suite: A Unified Red-Team Framework for Privacy Evaluation of Split and Distributed LLM Systems

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Georgios Politis, Evangelos Pappas
- Published: 2026-10-20
- Venue/type: Unknown venue / preprint
- DOI: https://doi.org/10.66977/xsci.2610.0021
- URL: https://doi.org/10.66977/xsci.2610.0021
- Opportunity score: 4
- Matched tags: dataset, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Split language models keep input text on a client but send intermediate representations to a server. Attacks can reconstruct text from these messages. Comparing privacy evaluations is difficult when attackers see different messages, know different model weights or use different datasets and recovery measures. We present LLM-Attack Suite, a framework that records these choices and lets researchers check, compare and extend an evaluation. Compatible attacks reuse recorded messages, and their predictions are saved for independent scoring. The scoring rule requires a linked undefended reference before a defence can pass. Reports also identify attacks that remain untested. In a controlled GPT-2 experiment, adding gradients returned during training increased token recovery from 94.20% to 97.38% and exact-document recovery from 13.71% to 37.77%. The 95% interval for the token gain lay above the two-percentage-point threshold fixed before testing. This experiment is shared with a companion study; here it tests how the evaluation responds to a change in attacker access. Further studies measure how corpus choice and compression defences affect recovery, compare an adapted published attack with its reference implementation, and test the measurement code. The framework reports implementation checks separately from measured attack effectiveness. Each privacy claim should state the attacker,

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Agency as a New Organizing Abstraction for Computer Science

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Ian T Foster
- Published: 2026-10-21
- Venue/type: Communications of the ACM / article
- DOI: https://doi.org/10.1145/3806060
- URL: https://doi.org/10.1145/3806060
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Addressing the challenges of agentic AI will require targeted advances in systems, programming languages, theory, and human–computer interaction.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Verifiable Delegated Authority for LLM Agents in Banking: A Formal Architecture, Capability Protocol, and Audit Guarantees

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Neeraj Aggarwal
- Published: 2026-10-20
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11415811/v1
- URL: https://doi.org/10.21203/rs.3.rs-11415811/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> No abstract text returned by metadata API.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Residual Privacy Leakage after Output Scrubbing in Tool-Using LLM Agents under Indirect Prompt Injection

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Kashvi Gupta
- Published: 2026-10-20
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11428254/v1
- URL: https://doi.org/10.21203/rs.3.rs-11428254/v1
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> No abstract text returned by metadata API.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. Guideline Adherence, Clinical Safety, and Source Accuracy of Commercial Large Language Models in Perioperative GLP-1 and GLP-1/GIP Receptor Agonist Management: A Scenario-Based Comparative Study

- Topic: Source-locked citation and hallucination verification
- Authors: Ebru Aladağ
- Published: 2026-10-20
- Venue/type: Acta Medica Alanya / article
- DOI: https://doi.org/10.30565/medalanya.1979219
- URL: https://doi.org/10.30565/medalanya.1979219
- Opportunity score: 2
- Matched tags: safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Aim: This study compared the guideline adherence, clinical safety, risk stratification, source accuracy, and practical applicability of three commercial large language models in perioperative GLP-1 receptor agonist (GLP-1 RA) and dual GLP-1/glucose-dependent insulinotropic polypeptide receptor agonist (GLP-1/GIP RA) management scenarios.Methods: In this non-interventional scenario-based comparative study, 20 English-language perioperative clinical scenarios were submitted once to ChatGPT Plus, Claude Pro, and Gemini Advanced/Google AI Pro. A total of 60 first complete responses were evaluated. Responses were scored using a predefined 10-point composite scale across five domains and predefined binary quality and safety outcomes. Paired non-parametric analyses were used for model comparisons.Results: ChatGPT achieved uniformly maximal total scores (mean 10.00), followed by Gemini (mean 8.00) and Claude (mean 5.85). Total scores differed significantly across models (χ²(2)=37.333, p

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

