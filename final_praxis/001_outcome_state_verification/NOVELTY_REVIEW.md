# Final Praxis 001 literature verification, 2026-09-08

The existing novelty gate permits a narrow evaluator-disagreement study. Primary-source checks below confirm substantial prior coverage and justify withholding any broad novelty claim. This focused search is not evidence that no prior work measures the same comparison.

| Primary source | Existing contribution | Consequence for this study |
|---|---|---|
| Yao, Shinn, Razavi, and Narasimhan, *tau-bench* (2024; ICLR 2025) | Tool-agent evaluation using final database state against goal annotations. | Final-state evaluation is established. |
| Trivedi et al., *AppWorld* (ACL 2024) | Programmatic state tests accepting multiple solutions and checking unintended state changes. | Alternate-path and collateral-state checking are established. |
| *Toward Scalable Verifiable Reward: Proxy State-Based Evaluation for Multi-turn Tool-Calling LLM Agents* (2026 preprint) | LLM-based state reconstruction and evaluation from agent traces. | Transcript-derived state inference is a closely related approach; its limitations motivate the information-access diagnostic. |

Sources checked directly via primary abstracts/publication records:

- https://arxiv.org/abs/2406.12045
- https://openreview.net/pdf?id=roNSXZpUDN
- https://aclanthology.org/2024.acl-long.850/
- https://arxiv.org/abs/2602.16246

Prior work provides realistic state-based task evaluation; Final Praxis 001 measures a small distinct-judge disagreement corpus under precisely imposed state corruption and explicit information-access controls. That is a bounded experimental specification, not proof of a new research category. Historical unverified title-only references are not reused as established literature in the final report.
