# Pagan Praxis Experiment Catalog — 001–034

This catalog is the canonical public-facing numbering layer. Historical PX/Praxis identifiers remain inside source artifacts for provenance.

| Experiment | What it is trying to prove — simple language | Status |
|---|---|---|
| [**Experiment 001 — Safety-Gated TTA for Streaming APT Detection**](../reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md) | Can a detector safely adapt to new data and recover rare APT stages? | 🟢 Defense-ready positive |
| [**Experiment 002 — ATT&CK TTP-Set Profile Retrieval**](../reports/gnn_attribution_ttp_graph_embeddings/px002_final_defense_package_export_20260706/PX002_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md) | Can a few observed ATT&CK techniques retrieve likely threat-group profiles? | 🟡 Bounded diagnostic |
| [**Experiment 003 — Retrieval-Conditioned CTI Compliance**](../reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md) | Does retrieving the right ATT&CK relationship evidence improve CTI answers? | 🟢 Defense-ready positive |
| [**Experiment 004 — FalseCite-Code Citation Poisoning**](../reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md) | Can source checks stop coding agents from trusting nonexistent or poisoned software references? | 🟢 Bounded defense-positive |
| [**Experiment 005 — MoE Standing-Committee Router Audit**](../reports/moe_standing_committee/README.md) | Do similar prompts repeatedly route through stable groups of experts? | 🟢 Bounded positive |
| [**Experiment 006 — OpTC Provenance Label / Host-Day Gate**](../reports/provenance_architecture/OPTC_CROSS_HOST_GATE_20260515.md) | Can we build trustworthy provenance labels that survive host/day changes? | 🟡 Evidence artifact |
| [**Experiment 007 — GWU GML APT Stage Repair**](../reports/gwu_committee_response/GML_CROSS_DATASET_REPRODUCTION_RESULT_20260518.md) | Does the earlier graph-ML APT stage claim reproduce across datasets? | 🟡 Diagnostic evidence |
| [**Experiment 008 — DAPT2020 External TTA Boundary Check**](../reports/tta_streaming_apt/DAPT2020_EXTERNAL_VALIDITY_NOTE_20260512.md) | Does the successful TTA mechanism transfer to a different APT dataset? | 🟡 Boundary evidence |
| [**Experiment 009 — LoRA Training-Trace Provenance**](../runs/ai-supply-chain-multistrength-lora-20260628/report.md) | Can training traces reveal poisoned LoRA fine-tuning? | 🔴 Failed gate |
| [**Experiment 010 — Synthetic Circuit Recovery Benchmark**](../reports/synthetic_circuit_recovery/README.md) | Can interpretability methods recover a circuit when the true circuit is known? | 🟡 Methods diagnostic |
| [**Experiment 011 — HalluHard Source-Backed Verifier Audit**](../reports/halluhard_source_verifier/) | Can deterministic source verification catch hallucinated claims reliably? | 🟢 Bounded positive |
| [**Experiment 012 — Contrastive SSL for Provenance Graphs**](../reports/contrastive_ssl_provenance_graphs/CADETS_SSL_REPRESENTATION_PILOT_20260509.md) | Can self-supervised learning create useful provenance-graph representations? | ⚪ Hold |
| [**Experiment 013 — Continuous-Time TGN for APT Streams**](../reports/continuous_time_tgn_apt_provenance/CADETS_TGN_NEXT_EVENT_PILOT_20260509.md) | Can temporal graph memory learn useful structure from continuous APT events? | ⚪ Reframe |
| [**Experiment 014 — Concept Drift on Provenance Detectors**](../reports/concept_drift_provenance_detectors/CADETS_DRIFT_GATE_20260510.md) | Can we detect when provenance detectors stop matching changing data? | ⚪ Label-blocked |
| [**Experiment 015 — TTC Transferability**](../reports/frontier_ai_ml_experiments_20260618/PX015_TTC_CI_GATE_20260630.md) | Do test-time-compute policies transfer instead of working only in one setting? | 🟡 Completed gate |
| [**Experiment 016 — Self-Jailbreak Guardrail**](../reports/frontier_ai_ml_experiments_20260618/FRONTIER_FINAL_DETERMINATION_20260621.md) | Can an early guardrail catch unsafe escalation without blocking safe answers? | 🔴 Failed utility gate |
| [**Experiment 017 — VLA Instruction Diversity**](../reports/frontier_ai_ml_experiments_20260618/FRONTIER_FINAL_DETERMINATION_20260621.md) | Does instruction diversity materially improve vision-language-action robustness? | 🔴 Stop / reframe |
| [**Experiment 018 — KG Hallucination Verification**](../reports/frontier_ai_ml_experiments_20260618/FRONTIER_FINAL_DETERMINATION_20260621.md) | Can knowledge-graph verification catch hallucinated factual relationships? | 🔴 Failed promotion |
| [**Experiment 019 — World-Model Visual Robustness**](../reports/frontier_ai_ml_experiments_20260618/FRONTIER_FINAL_DETERMINATION_20260621.md) | Does a world model remain reliable as visual conditions change? | ⚪ Environment smoke |
| [**Experiment 020 — Stage-Conditional APT Routing**](../reports/praxis04_full_run/PRAXIS04_FULL_RUN_REPORT.md) | Does stage-specific routing improve APT kill-chain classification under shift? | 🔴 Negative / reframe |
| [**Experiment 021 — Stage-Conditioned Imbalance Rescue**](../reports/plan02_stage_conditioned_imbalance/PLAN02_WEIGHTING_PILOT_RESULT.md) | Can stage-aware weighting rescue rare APT classes safely? | 🔴 Negative / parked |
| [**Experiment 022 — Routing Recovery Diagnostics**](../runs/stage1-routing-recovery-sweep-20260509-full/report.md) | Can a routing policy recover rare stages without damaging strong stages? | 🟡 Diagnostic |
| [**Experiment 023 — Sparse Autoencoder APT Interpretability**](../reports/praxis05_phase_a/PX023_WORKING_PATH_20260701.md) | Can sparse autoencoders expose understandable APT-detector features? | 🔴 Pivot failed |
| [**Experiment 024 — Domain-Seeded SEC-LoRD / DS-LoRD**](../reports/sec_lord_ds_lord/SEC_LORD_FAILURE_AUDIT_20260511.md) | Does broad cybersecurity domain seeding improve CTI extraction? | 🔴 Negative |
| [**Experiment 025 — APT Detector Watermarking**](../reports/apt_detector_watermarking/WATERMARK_OWNER_HEAD_GATE_20260514.md) | Can a detector carry an ownership watermark without hurting detection? | 🔴 Closed negative |
| [**Experiment 026 — Membership Inference Against APT Detectors**](../reports/membership_inference_apt_detectors/SHADOW_PROTOCOL_20260509.md) | Can an attacker infer whether a record trained an APT detector? | 🔴 Negative / parked |
| [**Experiment 027 — GNN TTP Embeddings for APT Attribution**](../reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_GRAPHSAGE_PILOT_20260510.md) | Can GNN embeddings beat simple ATT&CK retrieval for attribution? | 🔴 GNN claim dropped |
| [**Experiment 028 — LLM Threat Intelligence Fusion**](../reports/cti_attribution_label_sufficiency/ATTACK_ANNOCTR_LABEL_GATE_20260510.md) | Can an LLM fuse multiple CTI sources into useful early warning? | ⚪ Blocked |
| [**Experiment 029 — Stage Routing on Provenance Graphs**](../reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md) | Can graph windows be routed by kill-chain stage to improve detection? | ⚪ Hold |
| [**Experiment 030 — Cross-Detector Adversarial Robustness**](../configs/detector_zoo_registry.json) | Do different APT detector families fail under the same adversarial changes? | ⚪ Deferred |
| [**Experiment 031 — Causal GNN for Evasion-Resistant APT Detection**](../reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md) | Can causal graph rationales make APT detection harder to evade? | ⚪ Deferred |
| [**Experiment 032 — Reverse TTP Extraction**](../reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md) | Can hidden attacker techniques be inferred backward from observed behavior? | ⚪ Shelved |
| [**Experiment 033 — SWE-EVO Repo-State World Model**](../reports/swe_evo_repo_state_world_model/SWE_EVO_TRUE_EVAL_SLICE_20260628.md) | Can a model predict useful repository-state changes for software agents? | 🔴 Primary queue failed |
| [**Experiment 034 — CTI Source-Conflict Evidence Agent**](../reports/relationship_evidence_cti_compliance/) | Can a research agent recognize conflicting CTI sources and route evidence accordingly? | 🟡 Merged into 003 |
