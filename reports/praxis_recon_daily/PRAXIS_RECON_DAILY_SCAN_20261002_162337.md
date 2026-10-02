# Praxis Recon Daily Literature Scan

Generated: 2026-10-02 16:23 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 4

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 11 | Provenance-aware tool-boundary monitoring | 2026-10-01 | Large language models for agentic NetOps and AIOps: Architectures, evaluation, and safety | Computer Science Review | [source](https://doi.org/10.1016/j.cosrev.2026.101075) |
| 2 | 4 | Agentic package hallucination and tool-boundary gates | 2026-10-01 | MalTotal: Cost-Effective and Language-Agnostic Malicious Code Poisoning Detection for Millions of Repositories | Proceedings of the ACM on software engineering. | [source](https://doi.org/10.1145/3832228) |
| 3 | 2 | Agentic package hallucination and tool-boundary gates | 2026-10-01 | LogicHunter: Testing LLM Agent Frameworks with an Agentic Oracle | Proceedings of the ACM on software engineering. | [source](https://doi.org/10.1145/3832142) |
| 4 | 2 | Agentic package hallucination and tool-boundary gates | 2026-10-01 | TrapHunter: Exposing Covert Pathways in Trap Token Contracts | Proceedings of the ACM on software engineering. | [source](https://doi.org/10.1145/3832106) |

## Triage Notes

### 1. Large language models for agentic NetOps and AIOps: Architectures, evaluation, and safety

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Muhammad Bilal, Jon Crowcroft, Ruizhi Wang, Xiaolong Xu, et al.
- Published: 2026-10-01
- Venue/type: Computer Science Review / article
- DOI: https://doi.org/10.1016/j.cosrev.2026.101075
- URL: https://doi.org/10.1016/j.cosrev.2026.101075
- Opportunity score: 11
- Matched tags: agent, evaluation, safety, security, tool use
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large language models (LLMs) are increasingly being used in network operations (NetOps) and artificial intelligence for IT operations (AIOps) for tasks ranging from telemetry retrieval and incident diagnosis to configuration planning and bounded remediation. As these systems acquire greater access to operational tools, the central question is no longer only what an LLM can do, but whether operational assurance increases commensurately with the authority granted to it. This survey examines that question through a structured, evidence-stratified review of agentic NetOps and AIOps. We organise the field around autonomy, tool scope, evidence traces, assurance controls, evaluation, security, and governance, and introduce an operational assurance contract that links each autonomy level to permitted tools, required evidence, independent gates, execution budgets, rollout and rollback duties, and audit requirements. The synthesis reveals a capability--assurance gap: evidence is comparatively strong for read-oriented assistance and tool-grounded diagnosis, but becomes substantially less complete as systems approach configuration change, bounded execution, and closed-loop operation. We therefore argue that evaluation should move beyond static question answering and model accuracy towards workflow-level assessment of evidence quality, tool use, policy and invariant compliance, staged execu

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. MalTotal: Cost-Effective and Language-Agnostic Malicious Code Poisoning Detection for Millions of Repositories

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Jian Zhao, Shenao Wang, Qingyang Wu, Yanjie Zhao, et al.
- Published: 2026-10-01
- Venue/type: Proceedings of the ACM on software engineering. / article
- DOI: https://doi.org/10.1145/3832228
- URL: https://doi.org/10.1145/3832228
- Opportunity score: 4
- Matched tags: evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The widespread adoption of open source software (OSS) has introduced significant security risks, with malicious code poisoning attacks increasingly targeting public package registries and open-source platforms. Existing detection approaches, including heuristic-, learning-, and LLM-based methods, suffer from language-specific designs, limited generalization, and high analysis costs, making them unsuitable for large-scale multi-language analysis. To address these challenges, we propose MalTotal, a scalable and cost-effective framework for language-agnostic malicious code detection. MalTotal leverages LLM-assisted semantic reasoning to identify sensitive APIs, perform hybrid semantic slicing, and reconstruct malicious behavior contexts while reducing analysis overhead. Our evaluations show that MalTotal outperforms 8 state-of-the-art baselines, achieving an average F1-score of 93.1

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. LogicHunter: Testing LLM Agent Frameworks with an Agentic Oracle

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Minghui Long, Yanjie Zhao, Haoyu Wang
- Published: 2026-10-01
- Venue/type: Proceedings of the ACM on software engineering. / article
- DOI: https://doi.org/10.1145/3832142
- URL: https://doi.org/10.1145/3832142
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large Language Model (LLM) agent frameworks such as LangChain, LlamaIndex, and CrewAI have become critical infrastructure powering production AI systems, yet they remain severely under-tested due to fundamental challenges in automated testing. Unlike traditional software, where crashes serve as reliable oracles, defects in these pure Python frameworks manifest as ordinary exceptions or silent semantic failures, creating profound oracle ambiguity. This problem is exacerbated by strict type governance through Pydantic schemas and complex protocol requirements that cause existing fuzzers to generate overwhelming invalid inputs, while traditional test generators produce only trivial cases with weak regression assertions. We present LogicHunter, a fuzzing framework that addresses both the generation and oracle challenges through active specification-aware testing. LogicHunter employs specification-driven generation that systematically fuses formal type constraints with authentic usage patterns from real-world repositories, synthesizing inputs that are valid by construction yet semantically extreme, equipped with behavioral probes to expose silent failures. To resolve oracle ambiguity, we introduce the Agentic Oracle, which transcends passive classification by actively retrieving documentation, navigating source code, and inspecting runtime states through a ReAct-based architecture w

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. TrapHunter: Exposing Covert Pathways in Trap Token Contracts

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Yin Wu, Yixuan Liu, Yi Li, Chenyang Peng, et al.
- Published: 2026-10-01
- Venue/type: Proceedings of the ACM on software engineering. / article
- DOI: https://doi.org/10.1145/3832106
- URL: https://doi.org/10.1145/3832106
- Opportunity score: 2
- Matched tags: evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Standardized token contracts (e.g., ERC-20) form the foundation of digital assets. However, attackers increasingly abuse this standardization to disguise malicious trap tokens. Unlike obvious violations, these contracts employ a strategy of "deceptive adherence": they strictly adhere to standard protocols to evade detection while embedding covert logic to defraud users. To address this, we first systematize the trap landscape by proposing a novel taxonomy derived from the intrinsic functional lifecycle of tokens (Generation, Circulation, Persistence, and Observation). We then propose TrapHunter, a framework designed to identify these traps and expose covert pathways within these deceptive contracts via intent deviation analysis. Specifically, TrapHunter introduces a unified semantic representation combining Abstract Behavior Trees (ABTs) and Augmented Path Graphs (APGs) to normalize intra-procedural syntax and reveal hidden execution paths driven by inter-procedural state dependencies. Crucially, it bridges the semantic gap by leveraging LLMs to reason about the behavioral intent of deviations from reference implementations, followed by fork-based dynamic validation to confirm exploitability. Experimental evaluation on 269 real-world contracts with three LLMs (DeepSeek, GPT, and Gemini) demonstrates that TrapHunter effectively detects all six categories of traps, achieving an a

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

