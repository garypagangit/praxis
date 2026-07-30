# Praxis Experiment Dashboard

Updated: 2026-07-29

## Portfolio snapshot

- Lead new positive: **PX-057 adaptive stopping**.
- Mixed result: **PX-058 explanation stability passed; drift warning failed**.
- Closed or negative: **PX-059, PX-060, PX-061**.
- Latest PX-062 extension: **Gate 2.2 v1.3 stopped at its preregistered label-quality gate; no target-model or AWS run occurred**.
- PX-063: **Protocol 1.5 development result is not evaluable**; PX-064 remains blocked and PX-065 remains ready but unrun.
- Related mature defense: **PX-050 independently confirmed one-million-command robustness within its frozen grammar**.

## Latest execution status

- PX-062 Gate 2.1 finished with a cross-model **FAIL / NOT SUPPORTED** result.
- PX-062 Gate 2.2 v1.3 completed four full blinded label audits over 1,032 rows.
- Mechanical evidence passed: 172 unique sessions, 873 hash-bound artifacts, and zero retries.
- Semantic governance failed: 1,031 rows passed, but one row split 2-2 by model family.
- The preregistered lock worked: no Qwen/Mistral collection and no SageMaker experiment was launched for Gate 2.2 v1.3.

## PX-057 through PX-065

| ID | Experiment | Classification | Best current result | Next action |
|---|---|---|---|---|
| [PX-057](adaptive_stopping_overthinking/PX057_FINAL_DETERMINATION_20260724.md) | Adaptive Stopping to Prevent LLM Overthinking | Strong bounded positive | Adaptive accuracy 91.0% vs. 61.5% fixed-long; token saving 66.5%; prevention 89.6%; harm 0.5%. | Run H4 cross-model and non-math transfer without changing the completed discovery result. |
| [PX-058](xai_explanation_drift_intrusion/PX058_FINAL_DETERMINATION_20260724.md) | Explanation Stability and Drift for Network Intrusion Detection | Mixed | H1 stability passed for permutation, TreeSHAP, and LIME; H2 drift-warning failed for all methods. | Retain stability as a subfinding; redesign drift warning only as a new preregistered experiment. |
| [PX-059](uncertainty_adaptive_speculative_decoding/PX059_SOURCE_GATE_20260724.md) | Uncertainty-Adaptive Speculative Decoding | Closed at novelty gate | Not novel enough to advance as a separate Praxis contribution. | Archive unless a distinctly new mechanism appears. |
| [PX-060](coed_direction_robustness/PX060_FINAL_DETERMINATION_20260724.md) | Robustness and Meaning of Learned Continuous Edge Directions | Final negative | Prediction improved and reversal was tolerated, but direction identifiability and deletion robustness failed. | Any equivalence-class identifiability test must be a new hypothesis. |
| [PX-061](wavelet_dp_federated_learning/PX061_FINAL_DETERMINATION_20260724.md) | Unequal Wavelet Noise and Adaptive Clipping for Private Federated Learning | Final negative | Adaptive unequal noise gained 1.42 points vs. a required 2.0; static unequal allocation did not help. | Do not advance to Fashion-MNIST confirmation. |
| [PX-062](coding_agent_skill_provenance/gate2_2_context_structured_v1_3_20260728/LABEL_AUDIT_INVALIDATION_V1_3_20260729.md) | Provenance and Existence Gate for Coding-Agent Skills | Gate 1 negative; Gate 2.1 cross-model fail; Gate 2.2 v1.3 label gate invalidated | Gate 2.2 evidence was mechanically complete, but one frozen row received only 2/4 answer-key votes: both Sol passes chose `NONE`, while both Terra passes chose `linear`. | Preserve the sealed v1.3 invalidation and retire in-place prompt repair; any continuation needs new deterministic or expert label governance. |
| [PX-063](https://github.com/garypagangit/praxis/pull/14) | Deterministic Reward-Hack Verification on TRACE | Protocol 1.5 not evaluable | The pinned 517-row development run produced zero blocks: clean FPR passed, hacked-row recall was 0/241, and block precision was undefined. | Do not tune the sealed run; a structured tool-event experiment requires a new preregistration. |
| [PX-064](new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Registry Verification as Environment Hardening in Tool-Use RL | Blocked | Benchmark artifact verification remains unresolved. | Establish a reproducible benchmark environment before execution. |
| [PX-065](new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Provenance-Admission Gate for Agent Memory | Simulation ready | No scientific result yet. | Run the frozen inert simulation as the next unblocked experiment. |

## Related completed defense

PX-050 independently confirmed its repaired deterministic install gate on one million commands: zero invalid allows across 500,000 absent-package cases, 100% allow rate on 416,668 supported safe-valid commands, and 100% block rate on 166,664 shell-chain cases.

- [PX-050 large-scale robustness determination](agentic_deployment_defense/PX050_LARGE_SCALE_ROBUSTNESS_DETERMINATION_20260724.md)
- [PX-057-PX-061 portfolio audit](PX057_PX061_PORTFOLIO_AUDIT_20260724.md)
- [PX-062 working Praxis report](../output/doc/px062_working_praxis_20260724/PX-062_Working_Praxis_Report.pdf)
