# Praxis Recon Daily Literature Scan

Generated: 2026-10-19 17:13 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Agentic package hallucination and tool-boundary gates | 2026-10-17 | Current applications of artificial intelligence for advancing agriculture, sustainability and climate mitigation | Discover Artificial Intelligence | [source](https://doi.org/10.1007/s44163-026-02540-1) |
| 2 | 4 | Adaptive evaluation of deterministic agent defenses | 2026-10-18 | Securing LLM-Agent Long-Term Memory Against Poisoning: Non-Malleable, Origin-Bound Authority with Machine-Checked Guarantees | Unknown venue | [source](https://doi.org/10.66977/xsci.2610.001o) |

## Triage Notes

### 1. Current applications of artificial intelligence for advancing agriculture, sustainability and climate mitigation

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Mostafa Farajpour
- Published: 2026-10-17
- Venue/type: Discover Artificial Intelligence / article
- DOI: https://doi.org/10.1007/s44163-026-02540-1
- URL: https://doi.org/10.1007/s44163-026-02540-1
- Opportunity score: 10
- Matched tags: dataset, limitation, limitations, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Artificial intelligence (AI) is reshaping agriculture by enabling data-driven decision-making across crop production systems and supporting the transition toward more sustainable, resilient, and climate-smart farming. This review critically synthesizes advances in AI applications spanning precision irrigation, nutrient and soil management, yield prediction, pest and disease monitoring, computer vision, autonomous agricultural robotics, and large language model (LLM)-based decision support systems. Beyond summarizing technological developments, the review evaluates their practical deployment, emphasizing that successful agricultural AI depends not only on predictive accuracy but also on model generalizability, explainability, economic feasibility, interoperability, and integration with existing agronomic knowledge. Emerging technologies including Vision Transformers, foundation models, Digital Twins, multimodal AI, Retrieval-Augmented Generation, and federated and continual learning—are discussed as important directions for overcoming limitations related to data scarcity, environmental variability, and scalable field implementation. The review highlights that responsible AI adoption requires transparent governance frameworks addressing data ownership, privacy, algorithmic fairness, cybersecurity, and equitable access, particularly for smallholder farming systems. Although numero

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Securing LLM-Agent Long-Term Memory Against Poisoning: Non-Malleable, Origin-Bound Authority with Machine-Checked Guarantees

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Yedidel Louck
- Published: 2026-10-18
- Venue/type: Unknown venue / preprint
- DOI: https://doi.org/10.66977/xsci.2610.001o
- URL: https://doi.org/10.66977/xsci.2610.001o
- Opportunity score: 4
- Matched tags: agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> An agent based on a large language model (LLM) may store an untrusted document and use it weeks later to select a payment destination. Preventing this action requires evidence of authorization that remains valid when stored text changes. We study a policy that requires either endorsements (explicit approvals) from two separately administered sources or explicit user authorization. In an abstract memory model, we prove the policy is preserved under permitted transformations for stores of any size, assuming correct source and authority binding, protected records, and checks on every consequential action. We evaluate the executable monitor, which checks calls before execution, separately from the proof. In 1,152 controlled tool-use episodes, GPT-4o-mini executes attacker-selected actions in 61 of 72 undefended episodes and none of the 72 monitored episodes. Clean-task completion remains 24 of 24 when both endorsers are available. A separate 1,728-episode experiment tests recovery after denial. Returning to signed records instead of rereading a contaminated note raises attacked-task completion from 14/72 to 72/72 for GPT-4o-mini and from 22/72 to 43/72 for Gemini 2.5 Flash, without executing an attacker-selected action. Neither model completes transactions with fewer than two sources. Whole-action tests reject unauthorized combinations of individually approved fields. Extraction pr

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

