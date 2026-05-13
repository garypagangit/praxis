# Experiment Portfolio Next Steps And Results

Generated: 2026-05-10

## Cloud Status

AWS profile `praxis-build` is live again as `paganpraxis` in account `272615233626`. Current `us-east-1` GPU quotas are usable for the next batch: G/VT `256` vCPUs and P `8` vCPUs. A `g5.xlarge` runner completed the SEC-LoRD Llama confirmation, AI Supply Chain LoRA provenance, and Praxis 05 full Phase A jobs, then was stopped to avoid idle GPU spend.

Architecture update, 2026-05-11: a shared provenance window factory and detector-zoo registry now exist. The factory converted `98,862` Cadets edges into `20` reusable windows, and the registry exposes four baseline detector families. This is an unblocker for future graph/drift/watermark/privacy work, not a new scientific claim.

## Results Table

| # | Experiment | Latest result | Logical conclusion | Praxis signal |
|---:|---|---|---|---|
| 01 | TTA for Streaming APT Detection | Locked final replay: Macro-F1 `0.8658`, Recon F1 `0.5050`, PR-AUC `0.8738`, override rate `4.7%`; paper tables/figures built. | Proceed to Praxis 06 paper drafting; optional DAPT2020/CIC replication next. | **Strong lead** |
| 02 | Stage-Conditioned Class Imbalance | Stage-aware weighting barely moved Infilteration F1 (`+0.0049`) and damaged Benign. | Park as negative; simple weighting is not the answer. | No |
| 03 | Contrastive SSL on Provenance Graphs | Cadets augmentation passed, but representation pilot is weak: positive > negative rate `0.5227`. | Do not spend GPU yet; improve node features and hard negatives first. | Possible, not ready |
| 04 | MIA Against APT Detectors | Shadow protocol weakened same-distribution signal to ROC-AUC `0.5599`; temporal nonmembers stayed high at `0.7256`. | Park as negative/control; temporal shift explains most apparent privacy leakage. | No |
| 05 | SEC-LoRD / DS-LoRD | Strict audit confirms the cloud Llama prompt gate is negative. 3B: vanilla `0.276`, seeded `0.090`, delta `-0.186`. 8B: vanilla `0.466`, seeded `0.284`, delta `-0.182`. | Hold extraction. Redesign seed injection/task selection and enforce strict answer-format checks before the next gate. | Not with current prompt strategy |
| 06 | Continuous-Time TGN for APT Provenance | Temporal gate passed, but previous-event baseline Macro-F1 `0.6044` beat temporal/hash logistic `0.5972`. | Do not run next-event TGN; reframe to anomaly/window detection. | Possible after reframing |
| 07 | APT Detector Watermarking | Trigger candidates built, but cheap validation-only watermark fine-tuning failed: Macro-F1 delta `-0.0866`, trigger signature accuracy unchanged at `0.2391`. | Do not run surrogate yet; redesign trigger objective or add an owner-verification head. | Possible, needs redesign |
| 08 | Few-Shot APT Group Attribution | ATT&CK TTP-set baseline is positive: SVD top-5 retrieval `0.684` at 3 shots and `0.879` at 5 shots; APTNotes lacks explicit group labels. | Continue as ATT&CK TTP-set few-shot attribution; keep CTI prose attribution separate until labels exist. | Promising but scoped |
| 09 | GNN Attribution - TTP Graph Embeddings | Cheap ATT&CK profile retrieval is positive, but the first GraphSAGE pilot is weak: known-profile 5-shot top-5 `0.060` vs SVD `0.926`; held-edge 5-shot top-5 `0.073`. | Hold GNN framing. Continue only with richer text/metadata features or a better graph objective. | Simple profile signal only |
| 10 | SAE for APT Interpretability | Full AWS GPU MAGIC Phase A completed all 5 frozen seeds and failed: MSE ratio `0.0000224` passed, feature death `0.9119` failed, seed stability `0.2815` failed. | Do not proceed to Phase B. Next legitimate step is a single PIDSMaker pivot with an activation-export scaffold. | MAGIC negative; pivot possible |
| 11 | Stage Routing on Provenance Graphs | Praxis 04 says predicted stage is the bottleneck; no graph stage predictor yet. | Hold until a graph-stage predictor clears temporal split. | Not yet |
| 12 | AI Supply Chain - Backdoor Detection | Real Llama 3.2 3B LoRA provenance run completed. Clean-vs-poison separation is weak: loss effect size `0.0401`, grad-norm `-0.0673`, update-norm `0.0203`; poison validation loss higher by `0.0774`. | Do not claim detection yet. Improve poison construction and gradient diagnostics before multi-seed replication. | Possible but weak |
| 13 | LLM Threat Intelligence Fusion | Local NVD/APTNotes/AnnoCTR support retrieval/extraction, but no early-warning success/failure labels. | Blocked on evaluation ground truth; do not build model first. | Not yet |
| 14 | Concept Drift on Provenance Detectors | Cadets drift parser/windowing works, but sample is only 245.329 seconds from one source file. | Pipeline ready; needs longer host streams and labels/anomaly windows. | Support experiment |
| 15 | Cross-Detector Adversarial Robustness | No stable detector suite yet. | Later; needs 2-4 detector families first. | Later |
| 16 | Causal GNN for Evasion-Resistant APT | No local work; highest execution risk. | Later after 2+ publishable wins. | Later |
| 17 | Reverse TTP Extraction | No public data/simulator. | Shelved until a simulator/threat-actor environment exists. | Shelved |

## New Gates Completed

| Gate | Report | Outcome |
|---|---|---|
| CTI attribution label sufficiency | `reports/cti_attribution_label_sufficiency/ATTACK_ANNOCTR_LABEL_GATE_20260510.md` | GNN attribution is data-ready; few-shot attribution is partial; LLM fusion is ground-truth blocked. |
| Cadets concept drift gate | `reports/concept_drift_provenance_detectors/CADETS_DRIFT_GATE_20260510.md` | Parser/windowing works, but the local sample is too short for a drift claim. |
| ATT&CK TTP graph attribution baseline | `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_20260510.md` | Positive TTP-set attribution signal; proceed to real graph baseline. |
| APT detector watermark utility gate | `reports/apt_detector_watermarking/WATERMARK_TRAINING_UTILITY_GATE_20260510.md` | Weak/failed first watermark training gate; utility fell and signature did not improve. |
| SEC-LoRD Llama strict failure audit | `reports/sec_lord_ds_lord/SEC_LORD_FAILURE_AUDIT_20260511.md` | Confirmed negative after parser repair: 3B seeded fell from `0.276` to `0.090`; 8B seeded fell from `0.466` to `0.284`. |
| AI Supply Chain LoRA provenance cloud run | `reports/ai_supply_chain_training_provenance/LORA_PROVENANCE_CLOUD_RUN_20260510.md` | Real traces generated, but separation is weak; not publishable yet. |
| ATT&CK GraphSAGE pilot | `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_GRAPHSAGE_PILOT_20260510.md` | Weak: learned graph encoder did not beat cheap SVD/overlap baselines. |
| Praxis 05 full GPU Phase A | `reports/praxis05_phase_a/FULL_GPU_PHASE_A_20260510.md` | Full MAGIC/CADETS SAE gate failed the preregistered kill switch. |
| Provenance architecture unlock | `reports/provenance_architecture/ARCHITECTURE_UNLOCK_STATUS_20260511.md` | Window factory and detector registry are smoke-tested; longer streams and labels are still required for claims. |

## Immediate Queue

1. Refine the Praxis 06 Introduction and Methods draft at `reports/tta_streaming_apt/PRAXIS06_INTRO_METHODS_DRAFT_20260511.md` while the TTA result is fresh.
2. Keep ATT&CK attribution scoped to simple TTP-profile retrieval unless richer node text/metadata features are added.
3. Redesign SEC-LoRD domain seeding before extraction; current Llama gates failed under strict parsing.
4. Improve AI Supply Chain poison construction and gradient diagnostics before another LoRA cloud batch.
5. Build a PIDSMaker activation-export scaffold for one larger-hidden-state detector before spending more Praxis 05 GPU time.
6. Run the provenance window factory on a longer Cadets/OpTC stream and attach labels/anomaly spans before provenance drift and graph-stage modeling.
7. Redesign detector watermarking around a separate owner-verification head or less destructive trigger objective before rerunning surrogate-retention tests.
