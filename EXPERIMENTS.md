# Praxis Experiment Publication Index

Generated: 2026-06-18

Canonical dashboard: [Praxis Research Experiment Tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html).

Purpose: a GitHub-readable index of the Praxis research portfolio, numbered from Experiment 01 to Experiment N with clear titles, status, evidence, claim boundaries, and source artifacts.

This index intentionally publishes both positive and negative results. The rule is simple: a positive result can be pitched as a claim only when the gate was cleared; a negative result is preserved as evidence about the method, data, or evaluation bottleneck.

## Publication Tiers

| Tier | Experiments | Meaning |
|---|---|---|
| Selected positives | 01-03 | Defensible thesis or paper candidates with narrow claim boundaries. |
| Evidence artifacts | 04-05 | Strong supporting artifacts, label/data readiness, or committee remediation evidence. |
| Negative, gated, blocked, or future tracks | 06-23 | Publishable as honest outcomes, appendix material, or future-work constraints. |

## Experiment 01 - Safety-Gated TTA for Streaming APT Detection

**Status:** selected lead positive / Praxis 06.

**Title to use:** Safety-Gated Test-Time Adaptation for Streaming APT Detection.

**Core claim:** no-label test-time adaptation can recover rare APT-stage performance under held-out source-file shift when guarded by validation-selected safety gates and bounded override rates.

**Best evidence:** locked replay Macro-F1 `0.8658`, Recon F1 `0.5050`, PR-AUC `0.8738`, override rate `4.7%`; matched confidence-reject baseline Recon F1 `0.0000`; seven-seed robustness addendum Macro-F1 `0.8477 +/- 0.0226`, Recon F1 `0.5147 +/- 0.0589`.

**Decision:** lead publication result. Keep the locked replay primary; use robustness runs as addenda. Do not re-search thresholds.

**Primary artifacts:** `paper/praxis06_tta/`, `reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md`, `reports/tta_streaming_apt/PRAXIS06_DEFENSE_HARDENING_ADDENDUM_20260513.md`.

## Experiment 02 - ATT&CK TTP-Set Profile Retrieval for Few-Shot APT Attribution

**Status:** selected narrow positive.

**Title to use:** Few-Shot APT Group Profile Retrieval from ATT&CK TTP Sets.

**Core claim:** small observed ATT&CK technique sets can retrieve likely group profiles under a formal TTP-set retrieval protocol.

**Best evidence:** five-shot top-5 overlap `0.960`, SVD `0.879`, random `0.028`, frequency prior `0.041`; median rank `1.0`; degree-bucket analysis complete.

**Decision:** publish as profile retrieval, not CTI prose attribution and not a GNN claim.

**Primary artifacts:** `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`, `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`, `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_PAPER_OUTLINE_20260514.md`.

## Experiment 03 - Retrieval-Conditioned CTI Compliance with Relationship Evidence

**Status:** defensible narrow positive / Praxis 07.

**Title to use:** Relationship-Evidence Retrieval for CTI Task Compliance.

**Core claim:** question-specific ATT&CK relationship evidence improves strict CTI multiple-choice task compliance beyond vanilla prompting and broad seed prompting.

**Best evidence:** on the locked 106-row no-label evidence-addressable slice, 8B vanilla `68/106 = 0.642`, relationship evidence `97/106 = 0.915`, broad seed `68/106 = 0.642`, lift `+0.274`; 3B cross-model gate passed with vanilla `0.547`, relationship `0.887`, broad seed `0.575`; 8B ablation kept relationship evidence strongest but mechanism remained mixed.

**Decision:** publish as CTI task-compliance improvement, not model extraction. Add figure/example row and compile the paper package.

**Primary artifacts:** `paper/relationship_evidence_cti/`, `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`, `reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md`.

## Experiment 04 - Provenance Label Acquisition and OpTC Host/Day Gate

**Status:** label/data artifact; detector claim blocked.

**Title to use:** Label-Faithful OpTC Provenance Windowing Under Host/Day Shift.

**Core claim:** targeted OpTC host/day slices can support honest provenance-window label acquisition, while detector promotion remains blocked by host/day generalization.

**Best evidence:** expanded OpTC gate has three red-team host/day slices plus three benign host baselines, `717` usable non-gray windows, `108` gray-buffer windows excluded; red support `82/21`, `112/54`, and `41/107` attack/background by slice; pooled RF/ET Macro-F1 `0.8750`, but host-baselined and strict host holdout fail.

**Decision:** publish as label/data readiness and generalization-blocker evidence, not as a detector result.

**Primary artifacts:** `reports/provenance_architecture/OPTC_CROSS_HOST_GATE_20260515.md`, `reports/provenance_architecture/OPTC_LABEL_ACQUISITION_PLAN_20260514.md`, `scripts/run_optc_cross_host_gate.py`.

## Experiment 05 - GWU GML APT Stage-Classification Reproduction and Repair

**Status:** committee remediation evidence; diagnostic/negative support.

**Title to use:** Cross-Dataset GML Reproduction for Flow-Node APT Stage Classification.

**Core claim:** the old GML claim must be reframed around flow-node stage classification; ST-GCN superiority and Data Exfiltration detection are not supported by the repair runs.

**Best evidence:** DAPT2020 best GML Macro-F1 `0.5995`; Unraveled best GML Macro-F1 `0.2859`; ST-GCN weak on both (`0.2956` DAPT, `0.1853` Unraveled); all GML Data Exfiltration F1 values `0.0000`. DAPT apples-to-apples rerun: MLP Macro-F1 `0.6386`, KNN `0.6081`, best GML GIN `0.5895`, ST-GCN `0.1739`.

**Decision:** use as advisor-facing remediation and correction evidence, not as a new lead positive.

**Primary artifacts:** `reports/gwu_committee_response/GML_COMMITTEE_PROGRESS_RESPONSE_20260518.md`, `reports/gwu_committee_response/GML_CROSS_DATASET_REPRODUCTION_RESULT_20260518.md`, `reports/gwu_committee_response/DAPT_SOH_GML_APPLES_TO_APPLES_RESULT_20260519.md`.

## Experiment 06 - DAPT2020 External TTA Boundary Check

**Status:** negative appendix for Experiment 01.

**Title to use:** External-Validity Boundary Check for TTA on DAPT2020.

**Core claim:** the detector recipe transfers better than the TTA mechanism; the TTA result should not be generalized without qualification.

**Best evidence:** DAPT MLP recipe reached Macro-F1 `0.6353 +/- 0.0043`, Recon F1 `0.8932 +/- 0.0089`; selected TTA on DAPT had Macro-F1 delta `-0.2874`, Recon delta `-0.6589`, and only `2` Data Exfiltration test examples.

**Decision:** include as honest external-validity boundary.

**Primary artifacts:** `reports/tta_streaming_apt/DAPT2020_EXTERNAL_VALIDITY_NOTE_20260512.md`, `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md`.

## Experiment 07 - Stage-Conditional Routing for APT Kill-Chain Classification

**Status:** negative current method; reframe possible.

**Title to use:** Stage-Conditional Routing Under Temporal Shift.

**Core claim:** predicted-stage routing failed under shift, but oracle-stage routing shows the bottleneck is stage prediction rather than the routing idea alone.

**Best evidence:** five-seed Treatment-Stage Macro-F1 `0.5981` vs Baseline-TSE `0.6313`, p-value `1.0000`; rare-day oracle-stage pivot reached supported Macro-F1 `0.7173`, Infilteration F1 `0.5157`.

**Decision:** do not publish as a positive routing result. Reframe only as stage prediction under day shift.

**Primary artifacts:** `reports/praxis04_full_run/PRAXIS04_FULL_RUN_REPORT.md`, `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md`.

## Experiment 08 - Stage-Conditioned Class-Imbalance Rescue

**Status:** negative / parked.

**Title to use:** Stage-Aware Reweighting for Rare APT Classes.

**Core claim:** simple weighting/resampling did not rescue rare classes safely.

**Best evidence:** best Infilteration F1 gain only `+0.0049`; Benign F1 collapsed to `0.5481`; Bot strict smoke had zero train support.

**Decision:** park simple weighting and resampling. A future claim needs a calibrated rare-class method, not parameter tuning.

**Primary artifacts:** `reports/plan02_stage_conditioned_imbalance/PLAN02_WEIGHTING_PILOT_RESULT.md`.

## Experiment 09 - Stage-1 Routing Recovery Policy Diagnostics

**Status:** diagnostic only.

**Title to use:** Rare-Stage Routing Recovery and Safety Diagnostics.

**Core claim:** a macro-policy router can recover some rare-stage behavior, but the gain is not clean because Data Exfiltration protection degrades.

**Best evidence:** best macro policy Macro-F1 `0.7723 +/- 0.0894`; Recon improved, but Data Exfiltration fell versus the single-stage baseline.

**Decision:** preserve as diagnostic evidence feeding Experiment 01's safety-gated policy design.

**Primary artifacts:** `runs/stage1-routing-recovery-sweep-20260509-full/report.md`.

## Experiment 10 - Sparse Autoencoder Interpretability for APT Detectors

**Status:** hold; current MAGIC hidden-state result negative.

**Title to use:** Sparse Autoencoder Interpretability for Provenance APT Detector Hidden States.

**Core claim:** the current MAGIC hidden-state representation is too compressed or unstable for a publishable TopK SAE interpretability claim.

**Best evidence:** full AWS Phase A passed reconstruction with MSE ratio `0.0000224`, but failed feature death `0.9119` against threshold `<0.50` and seed stability `0.2815` against threshold `>=0.30`.

**Decision:** do not proceed to Phase B. Only a larger-hidden-state PIDSMaker pivot is justified.

**Primary artifacts:** `reports/praxis05_phase_a/FULL_GPU_PHASE_A_20260510.md`, `reports/praxis05_phase_a/PHASE_A_STATUS.md`.

## Experiment 11 - Domain-Seeded SEC-LoRD / DS-LoRD Prompting

**Status:** negative method; replaced by the narrower Experiment 03 path.

**Title to use:** Domain-Seeded CTI Prompting for LoRD-Style Extraction Gates.

**Core claim:** broad CTI domain seeding made strict answer behavior worse and cannot support an extraction claim.

**Best evidence:** strict audit 3B vanilla `0.276` vs seeded `0.090`; 8B vanilla `0.466` vs seeded `0.284`; seeded prompts increased invalid/meta outputs.

**Decision:** stop broad seed prompting. Do not run extraction from this gate.

**Primary artifacts:** `reports/sec_lord_ds_lord/SEC_LORD_FAILURE_AUDIT_20260511.md`, `reports/sec_lord_ds_lord/NEXT_GATE_DESIGN_20260513.md`.

## Experiment 12 - AI Supply-Chain Backdoor Detection from LoRA Training Provenance

**Status:** weak first result; falsifiable gate ready.

**Title to use:** Training-Trace Provenance for Poisoned LoRA Fine-Tuning.

**Core claim:** final-model behavior alone is not enough; training traces may expose poisoned fine-tuning, but the first real trace signal is weak.

**Best evidence:** first LoRA trace effects: loss `0.0401`, grad-norm `-0.0673`, update-norm `0.0203`; 9 paired clean/poison runs are defined across `1%`, `5%`, `10%` poison and seeds `41/42/43`.

**Decision:** run the multi-strength gate only if cloud resources allow. Promote only if 5% poison clears ROC-AUC/AP `>=0.7000` with stable signs on `>=2/3` seeds.

**Primary artifacts:** `reports/ai_supply_chain_training_provenance/AI_SUPPLY_CHAIN_MULTISTRENGTH_GATE_READY_20260514.md`, `scripts/build_ai_supply_chain_multistrength_gate.py`.

## Experiment 13 - Contrastive SSL for Provenance Graph Windows

**Status:** pending weak / hold GPU.

**Title to use:** Self-Supervised Provenance Graph Representation Learning.

**Core claim:** graph augmentations and windowing work, but the representation signal is not strong enough yet.

**Best evidence:** positive cosine `0.9239`, negative cosine `0.6633`, but positive-greater-than-negative rate only `0.5227`.

**Decision:** improve node features, augmentations, and hard negatives before GPU GraphCL.

**Primary artifacts:** `reports/contrastive_ssl_provenance_graphs/CADETS_SSL_REPRESENTATION_PILOT_20260509.md`.

## Experiment 14 - Continuous-Time TGN for APT Provenance Streams

**Status:** pending weak; reframe needed.

**Title to use:** Temporal Graph Memory for APT Provenance Event Streams.

**Core claim:** next-event prediction is not the right target yet; simple temporal baselines match or beat the current feature path.

**Best evidence:** previous-event transition baseline Macro-F1 `0.6044`; logistic temporal/hash features `0.5972`; no TGN detector gain established.

**Decision:** reframe toward anomaly/window detection once labels exist.

**Primary artifacts:** `reports/continuous_time_tgn_apt_provenance/CADETS_TGN_NEXT_EVENT_PILOT_20260509.md`.

## Experiment 15 - APT Detector Watermarking and Owner Verification

**Status:** closed negative for current detector lineage.

**Title to use:** Owner-Verifiable Watermarking for APT Detectors.

**Core claim:** current detector watermarking methods failed either utility or signature-detection gates.

**Best evidence:** direct watermark fine-tune Macro-F1 delta `-0.0866`, trigger signature accuracy `0.2391`; sidecar owner-head utility delta `+0.0000`, eval trigger detection `0.5217` vs required `>=0.9500`, eval false watermark rate `0.0435`.

**Decision:** archive for now. Do not run surrogate extraction.

**Primary artifacts:** `reports/apt_detector_watermarking/WATERMARK_OWNER_HEAD_GATE_20260514.md`, `scripts/run_watermark_owner_head_gate.py`.

## Experiment 16 - Membership Inference Against APT Detectors

**Status:** negative / parked.

**Title to use:** Membership-Inference Risk Under Temporal Shift in APT Detectors.

**Core claim:** apparent membership leakage is largely explained by temporal/source shift.

**Best evidence:** RF smoke looked positive with ROC-AUC `0.6864`, AP `0.8791`; stricter same-distribution shadow protocol weakened to ROC-AUC `0.5599`, AP `0.5351`, while temporal nonmembers stayed high at `0.7256`.

**Decision:** keep as negative/control evidence.

**Primary artifacts:** `reports/membership_inference_apt_detectors/SHADOW_PROTOCOL_20260509.md`.

## Experiment 17 - GNN TTP Graph Embeddings for APT Attribution

**Status:** GNN claim dropped; simple retrieval retained in Experiment 02.

**Title to use:** Graph Neural TTP Embeddings for ATT&CK-Based APT Attribution.

**Core claim:** GraphSAGE did not beat cheap ATT&CK profile-retrieval baselines.

**Best evidence:** known-profile 5-shot GraphSAGE top-5 `0.060` vs SVD `0.926` and overlap `0.985`; held-edge GraphSAGE 5-shot top-5 `0.073`.

**Decision:** do not pitch as a GNN result. Use the simple TTP-set retrieval result instead.

**Primary artifacts:** `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_GRAPHSAGE_PILOT_20260510.md`.

## Experiment 18 - LLM Threat Intelligence Fusion

**Status:** blocked.

**Title to use:** Outcome-Labeled LLM Fusion for Threat Intelligence.

**Core claim:** the data supports retrieval and extraction, but not early-warning evaluation until dated campaign/outcome labels exist.

**Best evidence:** local NVD, APTNotes, AnnoCTR, ATT&CK, and CTIBench sources are staged, but no suitable outcome-label target exists.

**Decision:** do not model first. Build outcome labels or drop.

**Primary artifacts:** `reports/cti_attribution_label_sufficiency/ATTACK_ANNOCTR_LABEL_GATE_20260510.md`.

## Experiment 19 - Concept Drift on Provenance Detectors

**Status:** architecture-ready; label-blocked.

**Title to use:** Concept Drift Diagnostics for Provenance-Based APT Detection.

**Core claim:** provenance windowing scales, but supervised drift claims need honest interval labels.

**Best evidence:** full E5 Cadets window factory converted `480,537,673` events into `9,611` windows; node-touch labels collapse to `9,609` attack-touch vs `2` benign/unlabeled. Density proxy is learnable, with chronological Macro-F1 up to `0.9788`, but it is not ground truth.

**Decision:** use density only for weak-proxy diagnostics and sample prioritization until labels exist.

**Primary artifacts:** `reports/provenance_architecture/FULL_CADETS_WINDOW_FACTORY_20260511.md`, `reports/concept_drift_provenance_detectors/CADETS_DRIFT_GATE_20260510.md`.

## Experiment 20 - Stage Routing on Provenance Graphs

**Status:** hold.

**Title to use:** Kill-Chain Stage Routing on Provenance Graph Windows.

**Core claim:** graph-stage routing is premature because graph labels and robust stage prediction are not yet available.

**Best evidence:** current evidence only shows the CIC-IDS2018 predicted-stage routing bottleneck and the provenance label gap.

**Decision:** reopen only after a graph stage predictor clears a separate temporal/host-shift gate.

**Primary artifacts:** `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md`.

## Experiment 21 - Cross-Detector Adversarial Robustness

**Status:** later.

**Title to use:** Cross-Detector Adversarial Robustness for APT Models.

**Core claim:** robustness comparisons require 2-4 stable trained detector families; the detector suite is not ready yet.

**Best evidence:** detector-zoo registry exists, but full Cadets detector claims are still label-blocked.

**Decision:** defer until there are stable detectors with honest labels.

**Primary artifacts:** `configs/detector_zoo_registry.json`, `reports/provenance_architecture/DETECTOR_ZOO_REGISTRY_20260511.md`.

## Experiment 22 - Causal GNN for Evasion-Resistant APT Detection

**Status:** later.

**Title to use:** Causal Graph Rationales for Evasion-Resistant APT Detection.

**Core claim:** invariant-rationale or causal-GNN claims require a stronger labeled detector base first.

**Best evidence:** no local gate yet; the prerequisite labels and detector suite are not available.

**Decision:** keep as a high-ceiling follow-on after the selected positives are packaged.

**Primary artifacts:** `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md`.

## Experiment 23 - Reverse TTP Extraction

**Status:** shelved.

**Title to use:** Reverse TTP Extraction from Attacker Query or Simulator Evidence.

**Core claim:** inferring unknown attacker TTPs needs realistic attacker-query traces or a validated simulator; the public data path is missing.

**Best evidence:** no public simulator or query-trace path is available in the current portfolio.

**Decision:** shelve until a real data source exists.

**Primary artifacts:** `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md`.

## Source Dashboards

- `reports/EXPERIMENT_CURRENT_DASHBOARD_20260513.md`
- `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md`
- `reports/EXPERIMENT_PORTFOLIO_CLOSEOUT_20260514.md`
- `reports/EXPERIMENT_DASHBOARD.md`
