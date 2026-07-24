# Praxis Experiment Dashboard

Updated: 2026-07-24

## Portfolio snapshot

- Lead new positive: **PX-057 adaptive stopping**.
- Mixed result: **PX-058 explanation stability passed; drift warning failed**.
- Closed or negative: **PX-059, PX-060, PX-061**.
- Active: **PX-062 skill-name hallucination Gate 2**.
- Queued or blocked: **PX-063 through PX-065**.
- Related mature defense: **PX-050 independently confirmed one-million-command robustness within its frozen grammar**.

## Active cloud work

- Job: `px062-skill-hallucination-2026-07-24-22-21-01`
- Status: `InProgress` / `Pending`
- Workload: two models x three conditions x 300 tasks = 1,800 outputs.

## PX-057 through PX-065

| ID | Experiment | Classification | Best current result | Next action |
|---|---|---|---|---|
| [PX-057](adaptive_stopping_overthinking/PX057_FINAL_DETERMINATION_20260724.md) | Adaptive Stopping to Prevent LLM Overthinking | Strong bounded positive | Adaptive accuracy 91.0% vs. 61.5% fixed-long; token saving 66.5%; prevention 89.6%; harm 0.5%. | Run H4 cross-model and non-math transfer without changing the completed discovery result. |
| [PX-058](xai_explanation_drift_intrusion/PX058_FINAL_DETERMINATION_20260724.md) | Explanation Stability and Drift for Network Intrusion Detection | Mixed | H1 stability passed for permutation, TreeSHAP, and LIME; H2 drift-warning failed for all methods. | Retain stability as a subfinding; redesign drift warning only as a new preregistered experiment. |
| [PX-059](uncertainty_adaptive_speculative_decoding/PX059_SOURCE_GATE_20260724.md) | Uncertainty-Adaptive Speculative Decoding | Closed at novelty gate | Not novel enough to advance as a separate Praxis contribution. | Archive unless a distinctly new mechanism appears. |
| [PX-060](coed_direction_robustness/PX060_FINAL_DETERMINATION_20260724.md) | Robustness and Meaning of Learned Continuous Edge Directions | Final negative | Prediction improved and reversal was tolerated, but direction identifiability and deletion robustness failed. | Any equivalence-class identifiability test must be a new hypothesis. |
| [PX-061](wavelet_dp_federated_learning/PX061_FINAL_DETERMINATION_20260724.md) | Unequal Wavelet Noise and Adaptive Clipping for Private Federated Learning | Final negative | Adaptive unequal noise gained 1.42 points vs. a required 2.0; static unequal allocation did not help. | Do not advance to Fashion-MNIST confirmation. |
| [PX-062](coding_agent_skill_provenance/PX062_CURRENT_DETERMINATION_20260724.md) | Provenance and Existence Gate for Coding-Agent Skills | Gate 1 negative; Gate 2 active | Provenance blocked tampering and nonexistent names but admitted 100% of authentic signed poisoned skills. | Complete the two-model, three-condition live skill-name hallucination run and adjudicate 1,800 outputs. |
| [PX-063](new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Deterministic Reward-Hack Verification on TRACE | Blocked | Dataset fetch remains unresolved. | Verify and freeze the public dataset before implementation. |
| [PX-064](new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Registry Verification as Environment Hardening in Tool-Use RL | Blocked | Benchmark artifact verification remains unresolved. | Establish a reproducible benchmark environment before execution. |
| [PX-065](new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Provenance-Admission Gate for Agent Memory | Simulation ready | No scientific result yet. | Run the frozen inert simulation after PX-062 adjudication. |

## Related completed defense

PX-050 independently confirmed its repaired deterministic install gate on one million commands: zero invalid allows across 500,000 absent-package cases, 100% allow rate on 416,668 supported safe-valid commands, and 100% block rate on 166,664 shell-chain cases.

- [PX-050 large-scale robustness determination](agentic_deployment_defense/PX050_LARGE_SCALE_ROBUSTNESS_DETERMINATION_20260724.md)
- [PX-057-PX-061 portfolio audit](PX057_PX061_PORTFOLIO_AUDIT_20260724.md)
- [PX-062 working Praxis report](../output/doc/px062_working_praxis_20260724/PX-062_Working_Praxis_Report.pdf)
