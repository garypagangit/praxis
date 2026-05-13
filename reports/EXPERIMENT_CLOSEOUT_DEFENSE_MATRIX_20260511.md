# Experiment Closeout Defense Matrix

Generated: 2026-05-11

## Bottom Line

The defensible Praxis candidate is still `TTA for Streaming APT Detection`. It has the cleanest positive evidence: locked final replay, AWS rerun agreement, robustness audit, confidence-reject comparator, and paper assets.

The main architecture unlock is now started: a provenance window factory and detector-zoo registry exist, with smoke artifacts under `runs/provenance-window-factory-20260511/` and reports under `reports/provenance_architecture/`. This reopens blocked graph/drift/watermark/privacy work only at the plumbing level. It does not prove any new scientific claim until longer streams and labels are attached.

Several other ideas produced useful negative or narrowing results. That is not wasted work. It tells us what not to claim in a defense:

- Do not claim SEC-LoRD domain-seeded prompting works yet.
- Do not claim GraphSAGE TTP attribution beats cheap ATT&CK profile baselines.
- Do not claim MAGIC hidden-state SAEs are interpretable after the full Phase A feature-death failure.
- Do not claim AI supply-chain backdoor provenance detection from the current weak LoRA traces.

## Defense-Ready Status

| # | Experiment | Closeout state | What is proven | What is not proven | Honest next move |
|---:|---|---|---|---|---|
| 01 | TTA for Streaming APT Detection | Lead positive | Hybrid TTA recovers major Macro-F1 and Recon signal under the locked Unraveled split; reject baseline does not explain it. | Cross-dataset generality is not yet proven. | Refine the Praxis 06 draft and optionally run DAPT2020/CIC replication as external validity. |
| 02 | Stage-Conditioned Class Imbalance | Negative | Simple stage-aware weighting does not rescue rare classes safely. | No claim about representation learning or calibrated rare-class rescue. | Park unless tied to TTA/representation work. |
| 03 | Contrastive SSL on Provenance Graphs | Pending, weak pilot | Cadets graph parsing and augmentation work; first representation signal is weak. | No publishable GraphCL/SSL claim. | Improve node features and hard negatives before GPU. |
| 04 | MIA Against APT Detectors | Negative/control | Apparent MIA signal is largely temporal-shift confounding under stricter shadow protocol. | No strong same-distribution privacy leakage result. | Park as diagnostic control. |
| 05 | SEC-LoRD / DS-LoRD | Hold after strict audit | Current domain-seeded prompting hurts Llama CTI-MCQ performance; strict parser confirms failure. | No SEC-LoRD extraction advantage; no DS-LoRD benefit. | Redesign seeding with retrieved facts, constrained answer format, or switch to AnnoCTR TTP linking. |
| 06 | Continuous-Time TGN for APT Provenance | Pending, reframing needed | Temporal parsing/windowing works; next-event target is not strong enough. | No TGN detector improvement. | Reframe to anomaly/window detection with longer streams and labels. |
| 07 | APT Detector Watermarking | Active but failed first gate | Trigger candidates exist; first watermark objective damaged utility and did not improve signature. | No ownership or surrogate-retention claim. | Add owner-verification head or less destructive trigger objective. |
| 08 | Few-Shot APT Group Attribution | Scoped positive | ATT&CK TTP-set few-shot retrieval is promising. | Document-level APTNotes attribution is not supported because explicit group labels are missing. | Keep as TTP-set simulation unless labels are added. |
| 09 | GNN Attribution - TTP Graph Embeddings | Hold after GNN pilot | Cheap SVD/overlap ATT&CK profile retrieval is strong. | GraphSAGE does not beat cheap baselines. | Add text/metadata features or abandon GNN framing. |
| 10 | SAE for APT Interpretability | Negative for MAGIC, pivot possible | Full 5-seed GPU Phase A fails feature-death and stability gates on MAGIC CADETS hidden states. | No interpretable SAE feature claim; no Phase B. | One PIDSMaker larger-hidden-state pivot via activation-export scaffold. |
| 11 | Stage Routing on Provenance Graphs | Hold | Praxis 04 identified stage prediction as the bottleneck. | No graph-stage routing result yet. | Only proceed if a graph-stage predictor clears temporal split. |
| 12 | AI Supply Chain - Backdoor Detection | Pending, weak real run | Clean-vs-poison LoRA traces exist; current separation is weak. | No reliable backdoor provenance detector. | Strengthen poison construction, add richer gradient diagnostics, multi-seed. |
| 13 | LLM Threat Intelligence Fusion | Blocked | Data sources support retrieval/extraction. | Early-warning success/failure labels are missing. | Define outcome labels before model work. |
| 14 | Concept Drift on Provenance Detectors | Pending, data-limited | Cadets drift parser/windowing works. | Current 245-second sample cannot support publishable drift claims. | Process longer Cadets/OpTC streams with labels/anomaly windows. |
| 15 | Cross-Detector Adversarial Robustness | Later | Motivation remains valid. | No detector suite exists. | Build 2-4 stable detectors first. |
| 16 | Causal GNN for Evasion-Resistant APT | Later | High-ceiling idea remains. | No local evidence yet. | Save until after 2+ publishable wins. |
| 17 | Reverse TTP Extraction | Shelved | High-novelty concept remains. | No simulator/dataset exists. | Revisit only after publishable wins and simulator design. |

## SEC-LoRD Audit Correction

The 2026-05-10 cloud reports were directionally right but numerically too generous. The old parser accepted any `A/B/C/D` character anywhere in the generated text, so malformed outputs like `assistant\n\nI'm ready` were parsed as `A`. The 2026-05-11 strict audit fixes that and confirms the failure:

| Model | Vanilla strict acc | Seeded strict acc | Delta | Seeded invalid/meta outputs |
|---|---:|---:|---:|---:|
| Llama-3.2-3B-Instruct | `0.276` | `0.090` | `-0.186` | `432 / 500` |
| Llama-3.1-8B-Instruct | `0.466` | `0.284` | `-0.182` | `239 / 500` |

This makes the conclusion stronger, not weaker: current domain seeding is not just unhelpful; it breaks answer compliance.

## Remaining Closeout Queue

1. Refine the Praxis 06/TTA Introduction and Methods draft at `reports/tta_streaming_apt/PRAXIS06_INTRO_METHODS_DRAFT_20260511.md`.
2. Run optional DAPT2020 or CIC replication only if it will strengthen external validity before drafting.
3. Run the provenance window factory on longer Cadets/OpTC streams and attach attack/anomaly labels before more graph/drift modeling.
4. Build PIDSMaker activation-export scaffold for the one allowed SAE pivot.
5. Redesign SEC-LoRD seeding around retrieved facts plus strict constrained answers before any extraction.
6. For AI supply chain, improve poison construction and gradient diagnostics before another cloud batch.

## Praxis Defense Rule

Claim only what cleared a gate. Preserve negative results when they isolate a bottleneck. Do not round weak pilots into positive evidence.
