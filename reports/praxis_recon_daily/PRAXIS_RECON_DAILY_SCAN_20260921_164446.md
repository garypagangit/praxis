# Praxis Recon Daily Literature Scan

Generated: 2026-09-21 16:44 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 6 | Provenance-aware tool-boundary monitoring | 2026-09-19 | Human-AI collaboration for ethical, transparent, and equitable educational practices | Journal of Digital Educational Technology | [source](https://doi.org/10.29333/jdet/19286) |
| 2 | 2 | Provenance-aware tool-boundary monitoring | 2026-09-19 | Token-level defect feedback and alternating optimization for coupled code generation and defect detection with large language models | Scientific Reports | [source](https://doi.org/10.1038/s41598-026-71524-z) |
| 3 | 2 | Provenance-aware tool-boundary monitoring | 2026-09-19 | From Model Risk Management to AI Assurance: Integrating AI Risk Management, Independent Validation, and AI Auditing for Generative and Agentic AI | Transactions on Engineering and Computing Sciences | [source](https://doi.org/10.14738/tecs.1405.12205) |

## Triage Notes

### 1. Human-AI collaboration for ethical, transparent, and equitable educational practices

- Topic: Provenance-aware tool-boundary monitoring
- Authors: D. Singh
- Published: 2026-09-19
- Venue/type: Journal of Digital Educational Technology / article
- DOI: https://doi.org/10.29333/jdet/19286
- URL: https://doi.org/10.29333/jdet/19286
- Opportunity score: 6
- Matched tags: agent, alignment, interpretability
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial intelligence (AI) and immersive technologies are reshaping education by enabling adaptive, personalized, and experiential learning environments that enhance engagement, instructional effectiveness, and administrative efficiency. This review explores Human-in-the-loop (HITL) frameworks that integrate human expertise with AI to enhance trust, interpretability, collaborative decision-making, and continuous feedback. AI applications in teacher professional development facilitate personalized training, competency growth, and ethical governance, emphasizing human-centered frameworks and structured professional learning. HITL approaches extend to reality training, knowledge graph validation, emotion recognition, and large language model integration, combining automated outputs with human oversight to ensure contextual appropriateness, fairness, and ethical compliance. Reinforcement learning augmented with human guidance enhances performance, robustness, and reliability, demonstrating scalable, interpretable, and human-aligned solutions. Challenges persist in explainability, bias mitigation, interface design, and the underexplored role of agentic AI, highlighting the need for continuous human involvement in AI-assisted educational systems. Empirical and conceptual evidence underscores that human-AI collaboration improves engagement and ethical alignment while enabling scalab

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Token-level defect feedback and alternating optimization for coupled code generation and defect detection with large language models

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Wenzeng Shan
- Published: 2026-09-19
- Venue/type: Scientific Reports / article
- DOI: https://doi.org/10.1038/s41598-026-71524-z
- URL: https://doi.org/10.1038/s41598-026-71524-z
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Large language models write code fluently, yet the programs they produce carry defect rates that ordinary functional evaluation seldom exposes, and detection systems that could catch these faults act too late to shape the generation that created them. This paper argues that generation and detection should be optimized together rather than in sequence, and it makes that argument concrete through one specific coupling: the detector’s node-level risk estimates are mapped back onto decoder positions and used to reweight the generation loss token by token, while a composite reward built from test outcomes and defect probability supplies a second, sampled gradient. Generator and detector are updated in alternation under a bounded schedule; failed candidates re-enter the detector’s training stream, and twelve mutation operators widen its exposure to underrepresented fault families. Using Qwen2.5-Coder-7B-Instruct as the generator and a gated graph neural network as the detector, and averaging five independent seeds, the coupled method lowered the defect rate of test-passing code from 0.216 ± 0.008 to 0.128 ± 0.008 while raising pass@10 from 0.724 ± 0.008 to 0.761 ± 0.008. Every defect rate reported here is scored by a reference detector frozen outside the loop, so the improvement cannot be an artefact of a critic grading its own pupil. Detection F1 rose from 0.627 ± 0.011 to 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. From Model Risk Management to AI Assurance: Integrating AI Risk Management, Independent Validation, and AI Auditing for Generative and Agentic AI

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Timothy Godlove, John Buchanan
- Published: 2026-09-19
- Venue/type: Transactions on Engineering and Computing Sciences / article
- DOI: https://doi.org/10.14738/tecs.1405.12205
- URL: https://doi.org/10.14738/tecs.1405.12205
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative and agentic artificial intelligence challenge assumptions embedded in traditional model risk management (MRM), including stable system boundaries, direct observability, controllable change, and access to model-development evidence. Yet the enduring purposes of MRM—inventory, materiality assessment, independent validation, monitoring, documentation, effective challenge, and accountable governance—remain necessary. This conceptual and applied article develops a socio-technical assurance architecture for contemporary AI systems by integrating governmental and regulatory guidance, international standards, professional assurance practices, and scholarly literature. The proposed Integrated AI Assurance Framework connects four distinct but interdependent functions: AI governance; AI risk management and MRM; independent AI/model validation; and AI auditing. The article also introduces the AI Assurance Boundary, which defines the technical and organizational components whose evidence is material to justified reliance on an AI-enabled capability, and the Assurance Sufficiency Principle, which addresses circumstances in which complete transparency, traceability, or explainability is unattainable. The resulting architecture is risk-based, with assurance intensity varying according to materiality, consequentiality, autonomy, data sensitivity, regulatory exposure, observability, t

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

## API Errors

- agentic-package-gates: HTTP Error 429: Too Many Requests
- adaptive-agent-defenses: HTTP Error 429: Too Many Requests
- refusal-geometry: HTTP Error 429: Too Many Requests

