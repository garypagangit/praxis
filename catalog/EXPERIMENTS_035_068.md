# Pagan Praxis Experiment Catalog — 035–068

This continues the canonical public-facing numbering layer. Historical PX and Final Praxis IDs remain in linked source artifacts for provenance.

| Experiment | What it is trying to prove — simple language | Status |
|---|---|---|
| [**Experiment 035 — Long CoT Thought-Budget Oracle**](../reports/frontier_ai_ml_experiments_20260618/PX035_THOUGHT_BUDGET_ORACLE_20260630.md) | Can we predict when extra reasoning helps versus wastes compute or hurts answers? | 🟡 Diagnostic |
| [**Experiment 036 — RWML for Agent World Models**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can reward-weighted modeling improve an agent's model of a changing environment? | ⚪ Deferred |
| [**Experiment 037 — Ouro Latent Loop Exit Gating**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can a model learn when to exit repeated latent reasoning loops? | ⚪ Deferred |
| [**Experiment 038 — Circuit-Aware Reward Training**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can circuit-aware rewards improve robustness on rare cases? | ⚪ Deferred |
| [**Experiment 039 — FLAME-MoE Routing Transfer**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Do MoE routing behaviors transfer across architectures and tasks? | ⚪ Deferred |
| [**Experiment 040 — DP-FedLoRA CoT Degradation**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Does privacy-preserving federated LoRA degrade reasoning quality? | ⚪ Deferred |
| [**Experiment 041 — SPEED-Q Robotics VLM Quantization**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | How far can robotics VLMs be quantized before useful behavior breaks? | ⚪ Deferred |
| [**Experiment 042 — TernaryCLIP Federated Hospital Compression**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can heavily compressed federated VLMs remain useful across hospitals? | ⚪ Deferred / kill |
| [**Experiment 043 — MAGRPO Multi-Agent RL Collaboration**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can multi-agent RL improve collaboration without unstable coordination? | ⚪ Deferred |
| [**Experiment 044 — Agentic RL Scientific Discovery Benchmark**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can agentic RL be benchmarked meaningfully on scientific-discovery tasks? | ⚪ Hold |
| [**Experiment 045 — SLAM-LLM Multimodal Speech/Audio**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can one LLM framework reason robustly over speech and audio? | ⚪ Hold |
| [**Experiment 046 — Controllable Video Generation Benchmark**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can video generators reliably follow structured controls? | ⚪ Hold |
| [**Experiment 047 — Gaussian Splatting 3D Scene Generation**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can generative Gaussian splatting produce defensible controllable 3D scenes? | 🔴 Kill current cycle |
| [**Experiment 048 — HuGeDiff 3D Human Generation**](../reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html) | Can diffusion-based 3D human generation clear a defensible experiment gate? | 🔴 Kill current cycle |
| [**Experiment 049 — Agentic Slopsquatting Verifier**](../reports/agentic_deployment_defense/px049_live_gate_20260705/PX049_AGENTIC_SLOPSQUATTING_LIVE_GATE_20260705.md) | Will coding agents try to install hallucinated packages, and can verification stop them? | 🔴 Live gate failed |
| [**Experiment 050 — Deterministic Agent Defenses**](../reports/agentic_deployment_defense/px050_final_manuscript_20260705/PX050_FINAL_MANUSCRIPT_20260705.md) | Can deterministic verification stop unsafe package actions while preserving legitimate work? | 🟢 Lead bounded positive |
| [**Experiment 051 — Security-Utility Pareto for Agent Gates**](../reports/agentic_deployment_defense/px051v_live_agent_policy_refresh_20260705/PX051V_LIVE_AGENT_POLICY_REFRESH_20260705.md) | Can a gate block bad actions without reviewing or blocking everything? | 🟢 Live-agent policy pass |
| [**Experiment 052 — Provenance-Aware Tool-Boundary Monitoring**](../reports/agentic_deployment_defense/px052v_live_agent_provenance_refresh_20260705/PX052V_LIVE_AGENT_PROVENANCE_REFRESH_20260705.md) | Can tool-call provenance expose untrusted agent arguments without clean false alarms? | 🟢 Live-agent provenance pass |
| [**Experiment 053 — Approval Fatigue vs. Agent Security**](../reports/agentic_deployment_defense/px053_approval_fatigue_sim_20260705/PX053_APPROVAL_FATIGUE_SIMULATION_GATE_20260705.md) | Can selective human approval improve security without overwhelming reviewers? | 🔴 Simulation failed |
| [**Experiment 054 — Refusal Geometry Across Recurrent Depth**](../reports/refusal_geometry_recurrent_depth/px054_final_manuscript_20260706/PX054_FINAL_MANUSCRIPT_20260706.md) | Do refusal-related internal directions remain stable as recurrent depth changes? | 🟢 Defense-ready bounded positive |
| [**Experiment 055 — Refusal Geometry Under Quantization**](../reports/refusal_direction_quantization/PX055_REFUSAL_DIRECTION_QUANTIZATION_PREREG_20260711.md) | Does quantization change refusal-related internal geometry in a measurable way? | ⚪ Rescoped / cloud gate |
| [**Experiment 056 — Model-Registry Identifier Hallucination**](../reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/PX056_GATE2A_DETERMINATION_20260721.md) | Do coding models invent model/dataset IDs, and can registry checks stop them? | 🔵 Live pilot positive; full study pending |
| [**Experiment 057 — Adaptive Stopping for LLM Overthinking**](../reports/adaptive_stopping_overthinking/PX057_FINAL_DETERMINATION_20260724.md) | Can stopping reasoning at the right time avoid correct-to-wrong flips and save compute? | 🟢 Repository determination: bounded positive |
| [**Experiment 058 — Explanation Stability and Drift**](../reports/xai_explanation_drift_intrusion/PX058_FINAL_DETERMINATION_20260724.md) | Are intrusion-detector explanations stable, and can explanation drift warn about data drift? | 🟡 Mixed |
| [**Experiment 059 — Uncertainty-Adaptive Speculative Decoding**](../reports/uncertainty_adaptive_speculative_decoding/PX059_SOURCE_GATE_20260724.md) | Can uncertainty choose speculative-decoding depth better than fixed settings? | 🔴 Closed at novelty gate |
| [**Experiment 060 — Continuous Edge-Direction Robustness**](../reports/coed_direction_robustness/PX060_FINAL_DETERMINATION_20260724.md) | Are learned continuous graph-edge directions meaningful and robust? | 🔴 Final negative |
| [**Experiment 061 — Wavelet DP Federated Learning**](../reports/wavelet_dp_federated_learning/PX061_FINAL_DETERMINATION_20260724.md) | Can unequal wavelet noise improve private federated learning at the same privacy budget? | 🔴 Final negative |
| [**Experiment 062 — Coding-Agent Skill Provenance / Existence**](../reports/coding_agent_skill_provenance/PX062_CURRENT_DETERMINATION_20260724.md) | Can provenance and existence checks stop coding agents from using nonexistent or tampered skills? | 🔵 Gate 2 active in legacy record |
| [**Experiment 063 — Deterministic Reward-Hack Verification on TRACE**](../reports/new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Can deterministic checks identify reward hacking more reliably than judge-based evaluation? | ⚪ Blocked on external artifact |
| [**Experiment 064 — Registry Hardening for Tool-Use RL**](../reports/new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Can registry verification harden a tool-use RL environment without destroying task success? | ⚪ Blocked on benchmark |
| [**Experiment 065 — Provenance Admission for Agent Memory**](../reports/new_praxis_experiments_20260723/NEW_EXPERIMENT_BUILD_ORDER_20260723.md) | Can memory admission rules stop untrusted memories from influencing later agent actions? | ⚪ Deprioritized / legacy simulation-ready |
| [**Experiment 066 — Outcome-State Verification**](../final_praxis/001_outcome_state_verification/) | Can we verify what an AI actually changed instead of trusting another AI that says it succeeded? | 🔴 Negative — verified complete |
| [**Experiment 067 — Multi-Agent Cascade Containment**](../final_praxis/002_cascade_containment/) | Can deterministic checkpoints stop one AI agent's mistake from spreading through a team of agents? | 🔴 Negative — verified complete |
| [**Experiment 068 — Adaptive Cyber Investigation Stopping**](../final_praxis/003_adaptive_investigation_stopping/) | Can a security AI stop before extra investigation turns a correct answer into a wrong one? | 🔴 Negative — verified complete |

## Final-series verified outcomes

- **Experiment 066:** 400 cases independently verified. Judge false-success acceptance was 7/200 (3.5%) versus 0/200 for the state verifier; the preregistered required gap and collateral gates failed.
- **Experiment 067:** 480 workflows independently verified. Full containment reduced invalid-action escapes from 10/60 ungated to 0/60, but clean success was 51/60 (85%), below the frozen 90% utility floor.
- **Experiment 068:** 400 cases / 3,200 rounds verified. Reviewed stopping accuracy was 34.5% versus 54.25% fixed-long; 34/400 cases had incorrect early endpoints that were later corrected, and all cases required review.

Negative results remain part of the permanent Pagan Praxis record.
