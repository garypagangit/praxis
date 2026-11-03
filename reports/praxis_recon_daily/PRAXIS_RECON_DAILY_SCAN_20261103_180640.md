# Praxis Recon Daily Literature Scan

Generated: 2026-11-03 18:06 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Agentic package hallucination and tool-boundary gates | 2026-11-01 | Generative AI and Its Impact on Software Development | INTERANTIONAL JOURNAL OF SCIENTIFIC RESEARCH IN ENGINEERING AND MANAGEMENT | [source](https://doi.org/10.55041/ijsrem68679) |
| 2 | 9 | Agentic package hallucination and tool-boundary gates | 2026-11-02 | A Survey of LLM-based Software Repair: Taxonomies, Design Paradigms, and Applications | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3845995) |
| 3 | 4 | Adaptive evaluation of deterministic agent defenses | 2026-11-02 | BiCP: Reasoning-Prefix Deconfounding for Dual-Axis Counterfactual Probing and Operation-Risk Routing | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11536275/v1) |

## Triage Notes

### 1. Generative AI and Its Impact on Software Development

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Mr. Vivek Sanjay Amale
- Published: 2026-11-01
- Venue/type: INTERANTIONAL JOURNAL OF SCIENTIFIC RESEARCH IN ENGINEERING AND MANAGEMENT / article
- DOI: https://doi.org/10.55041/ijsrem68679
- URL: https://doi.org/10.55041/ijsrem68679
- Opportunity score: 10
- Matched tags: benchmark, evaluation, security, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The rapid proliferation of Large Language Models (LLMs) specialized in programming languages has fundamentally reconfigured the modern Software Development Life Cycle (SDLC). Far beyond basic autocompletion, generative foundation models now actively assist software practitioners across requirements formulation, architectural drafting, automated unit test synthesis, vulnerability remediation, and continuous refactoring. This empirical investigation provides an in-depth, rigorous evaluation of generative AI's real-world impact across engineering teams. Analyzing telemetry across 50 production engineering cohorts and standard code evaluation suites (HumanEval, MBPP, and SWE-bench), we demonstrate that modern generative coding assistants accelerate routine boilerplate authoring by 52.1% to 57.8%, yet introduce pronounced cognitive friction during pull request verification. Crucially, synthetic benchmark pass rates (such as HumanEval Pass@1 topping 92.4%) mask an acute architectural reasoning deficit when resolving multi-file repository-level bugs on SWE-bench Lite (38.8% resolve ceiling). Furthermore, automated static security audits reveal that unconstrained generative synthesis increases latent defect density by 14.6%, primarily manifesting as improper input validation (CWE-20), SQL injection vectors (CWE-89), and hallucinated third-party dependencies. To resolve this dilemma, we

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. A Survey of LLM-based Software Repair: Taxonomies, Design Paradigms, and Applications

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Boyang Yang, Zijian Cai, Fenglin Liu, Bach Le, et al.
- Published: 2026-11-02
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3845995
- URL: https://doi.org/10.1145/3845995
- Opportunity score: 9
- Matched tags: agent, alignment, benchmark, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large language models (LLMs) are reshaping automated program repair. We present a reproducible hierarchical taxonomy that organizes 66 LLM-based repair systems according to where repair capability and control logic principally reside: taskadapted parameters, prompt and context design, designer-specified workflows, or LLM-directed runtime control. Adaptation, generation pattern, runtime control, and auxiliary evidence remain separate coded dimensions. This representation exposes control distinctions hidden by utilization labels and supports cross-paradigm analysis of system design and evaluation evidence. To the best of our knowledge, it is the first publicly available LLM-based software repair survey to operationalize Fine-Tuning, Prompting, Procedural, and Agentic as one corpus-wide primary classification. Our hierarchy complements prior surveys with a single corpus-wide primary decision rule, while the result-level protocol audit bounds which reported results are defensibly comparable. To analyze how repair systems use benchmarks, we record benchmark variants, metrics, base models, and fault-localization assumptions for each system’s primary reported result, identifying protocol-aligned comparison windows and benchmark-family fragments. We clarify paradigm trade-offs in task alignment, deployment cost, controllability, and multi-hunk or cross-file repair. We outline open chal

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. BiCP: Reasoning-Prefix Deconfounding for Dual-Axis Counterfactual Probing and Operation-Risk Routing

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Zida Hao, Yubo Li
- Published: 2026-11-02
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11536275/v1
- URL: https://doi.org/10.21203/rs.3.rs-11536275/v1
- Opportunity score: 4
- Matched tags: agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Tool-using language-model agents can select the intended tool while executing an injected argument. Counterfactual guards also lose source sensitivity when they condition on reasoning that already encodes the injected decision. We present BiCP (bilateral counterfactual probing), an execution-time defense combining reasoning-prefix removal, complementary tool-name and complete-call probes, and operation-risk routing. Equal-token controls over 69 fixed proposals raise tool-name macro area under the receiver operating characteristic curve from 0.7164 to 1.0000. On these fixed proposals, a second model family (Mistral-7B-Instruct-v0.3) independently reproduces both prefix deconfounding (0.6509 to 1.0000) and five-domain source reversals (joint p = 0.03125). After independent calibration, progressive component ablations on 922 fixed replay cases reduce confirmed InjecAgent attacks from 83/682 to 0/682 and unsafe conditional executions from 33/240 to 0/240, while increasing benign task success from 66/120 to 78/120. All five malicious argument substitutions adopted by the original model are blocked. A paired prompt-contract comparison increases the unchanged policy's retention of verified legal protected calls from 30/47 to 43/47. Among 47 paired attack proposals, deterministic anchoring stops 40 unsupported substitutions, while both probe variants stop all seven observation

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

