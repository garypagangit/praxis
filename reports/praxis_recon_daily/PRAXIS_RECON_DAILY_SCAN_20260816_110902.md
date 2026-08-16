# Praxis Recon Daily Literature Scan

Generated: 2026-08-16 11:09 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 9 | Source-locked citation and hallucination verification | 2026-08-14 | Delivering building demand flexibility for grid-interactive operation: from perception and cognition to decision, execution, and verification | Applied Energy | [source](https://doi.org/10.1016/j.apenergy.2026.128668) |
| 2 | 8 | Adaptive evaluation of deterministic agent defenses | 2026-08-15 | What surrounds an injection decides whether it works: context and channel effects in tool-metadata attacks on seven production LLM agents. Data and code | arXiv (Cornell University) | [source](https://arxiv.org/abs/2606.00566) |
| 3 | 4 | Agentic package hallucination and tool-boundary gates | 2026-08-14 | A Conversational Multi-Agent AI System for Integrated Multi-Omics Analysis and Biomedical Discovery | bioRxiv (Cold Spring Harbor Laboratory) | [source](https://doi.org/10.64898/2026.08.08.743577) |

## Triage Notes

### 1. Delivering building demand flexibility for grid-interactive operation: from perception and cognition to decision, execution, and verification

- Topic: Source-locked citation and hallucination verification
- Authors: Zhenjun Ma, Menglong Lu, Xiaochen Yang, Maomao Hu, et al.
- Published: 2026-08-14
- Venue/type: Applied Energy / article
- DOI: https://doi.org/10.1016/j.apenergy.2026.128668
- URL: https://doi.org/10.1016/j.apenergy.2026.128668
- Opportunity score: 9
- Matched tags: evaluation, future research, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> As both buildings and power systems undergo rapid decarbonization, demand flexibility (DF) in buildings has emerged as a key enabler for renewable energy integration, grid reliability, energy resilience, and efficient and low carbon operation. By dynamically adjusting building energy use in response to grid requirements, DF can help reduce building operational costs, respond to renewable variability, reduce peak demand, alleviate network congestion, and enhance overall system stability. Consequently, significant research efforts have examined building DF from multiple perspectives, including flexibility definitions, resources, characterization, assessment, optimization, and application scenarios. However, the effective delivery of DF in buildings requires an integrated, end-to-end approach spanning perception, cognition, decision, execution, and verification, which remains a critical gap in the existing literature. This review addresses this gap by proposing a layered architecture that integrates these stages into a coherent framework and provides insights from existing studies in this field. It synthesizes enabling methods, clarifies cross-layer interactions, and examines how data, models, control strategies, implementation mechanisms, and evaluation approaches collectively support DF delivery. Critical cross-layer challenges are identified, and future research priorities for 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. What surrounds an injection decides whether it works: context and channel effects in tool-metadata attacks on seven production LLM agents. Data and code

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Shaban Asif
- Published: 2026-08-15
- Venue/type: arXiv (Cornell University) / preprint
- DOI: https://doi.org/10.5281/zenodo.21944597
- URL: https://arxiv.org/abs/2606.00566
- Opportunity score: 8
- Matched tags: agent, tool call
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> A data and code for a study of indirect prompt injection in tool-using large language model agents. I performed 1,334 controlled trials across seven production models. In every comparison the injected instruction is held byte-identical and only its surroundings vary, so any difference in outcome is attributable to where the text arrived or what surrounded it, not to what it said. Two effects govern whether an attack succeeds. Delivery channel: Claude Haiku 4.5 obeyed an identical instruction in 37 of 38 trials as tool metadata and 0 of 30 as tool output. Surrounding context: Claude Sonnet 4.6 complies in 4 of 38 trials when the request arrives bare, and in 86.7% to 100% once any benign task framing is present, including a system prompt that mentions nothing about tools; a placement control moving the identical text into the user turn is indistinguishable. The two effects dissociate, since the context that removes the metadata-side resistance leaves the tool-output defence at 0 of 30. A separate methodological result is distinguishing whether the agent made the attacker's tool call from whether data actually left makes the two diverge by more than five to one, because the attack template's ordering clause fires before the data even exists. The archive I uploaded contains all 1,334 raw run directories including every model response, per-run results as CSV, every injected payload 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. A Conversational Multi-Agent AI System for Integrated Multi-Omics Analysis and Biomedical Discovery

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Pankaj Rajdeo, 浅沼 駿哉, Michal Kouril, Peixin Lu, et al.
- Published: 2026-08-14
- Venue/type: bioRxiv (Cold Spring Harbor Laboratory) / preprint
- DOI: https://doi.org/10.64898/2026.08.08.743577
- URL: https://doi.org/10.64898/2026.08.08.743577
- Opportunity score: 4
- Matched tags: agent, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Single-cell and spatial omics offer unprecedented opportunities to decipher the mechanisms of disease, however, this process requires teams of experts, iterative trial-and-error and reasoning across modalities. Here we present LungChat (https://chat.lungmap.net), a conversational system for integrated multi-omics analysis and biomedical discovery, deployed as a hierarchical multi-agent architecture in which a supervisor decomposes natural-language questions into parallel, tool-grounded tasks spanning single-cell and spatial analyses, literature and clinical-trial synthesis, and drug repurposing. To predict new therapeutics, LungChat implements Direction-Aware Repurposing and Targeting (DART) to distinguish perturbations that reverse disease transcriptional programs from those that reinforce them, at the cell-type level, for safety prediction. Controlled architecture ablations showed that hierarchical orchestration improved grounded abstention and token efficiency and preserved strong performance on complex multi-step tasks. In pulmonary disease case studies, LungChat independently prioritized saracatinib for IPF through drug-connectivity screening, followed by DART-based cell-type analysis; the same compound has been evaluated in the STOP-IPF clinical trial ( NCT04598919 ). The system also recovered fluticasone propionate, an established COPD therapy, through a single orchestra

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

