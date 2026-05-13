# Experiment Final Evaluation

Generated: 2026-05-11; updated: 2026-05-12

## Bottom Line

The defense-ready answer is narrow but strong: `TTA for Streaming APT Detection` is the only current Praxis-grade positive result. It has the best combination of locked evaluation, AWS agreement, robustness checks, paper assets, a cloud paper-hardening audit, and a clear scientific claim.

Cloud handoff note: this report is paired with `CLOUD_HANDOFF.md` and `configs/experiment_cloud_handoff_registry.json`. Fresh cloud runs should treat those files as the lightweight memory layer for past experiments and should fetch heavy `data/`, `runs/`, `outputs/`, `artifacts/`, and checkpoints from the registered remote locations rather than assuming local state exists.

The rest of the portfolio is still valuable, but mostly as honest triage:

- Several ideas are real negatives and should be preserved as evidence, not rescued by threshold moving.
- Several graph/provenance ideas were blocked less by modeling than by missing long-window labels.
- SEC-LoRD is confirmed negative for the current domain-seeded prompt strategy after a stricter parser audit.
- The new provenance window factory plus detector-zoo registry is the right architecture to reopen graph/drift/privacy/watermarking work, but it does not itself create a publishable result.

## Final Status Table

| Experiment | Final posture | Best evidence | Defense decision |
|---|---|---|---|
| TTA for Streaming APT Detection | **Lead positive** | Locked replay Macro-F1 `0.8658`, Recon F1 `0.5050`, PR-AUC `0.8738`, override rate `4.7%`; matched confidence-reject baseline kept Recon F1 at `0.0000`; full draft and defense checklist built | Move to Praxis 06 paper packaging; DAPT2020 is appendix recipe evidence plus a negative TTA feasibility check |
| Praxis 04 - Stage-Conditional Routing | Negative | Treatment-Stage Macro-F1 `0.5981` vs Baseline-TSE `0.6313`, p-value `1.0000` | Keep as bottleneck evidence: stage prediction under shift failed |
| Stage-Conditioned Class Imbalance | Negative | Best Infilteration F1 gain only `+0.0049`; Benign F1 collapsed to `0.5481` | Park simple weighting/resampling path |
| Stage 1 Routing Recovery | Diagnostic only | Best macro policy `0.7723 +/- 0.0894`; Recon improved but DE fell | Not clean enough for a standalone claim |
| Praxis 05 SAE for APT Interpretability | Hold | Full AWS Phase A failed feature-death `0.9119` and seed-stability `0.2815` gates | Do not proceed to Phase B; only one PIDSMaker/larger-hidden-state pivot is justified |
| SEC-LoRD / DS-LoRD | Hold / negative current method | Strict audit: 3B vanilla `0.276` vs seeded `0.090`; 8B vanilla `0.466` vs seeded `0.284` | Stop current prompt seeding; no extraction until redesign passes strict gate |
| AI Supply Chain Backdoor Detection | Pending weak | Real LoRA traces: loss effect `0.0401`, grad-norm `-0.0673`, update-norm `0.0203` | Needs stronger poison construction and richer gradient diagnostics |
| Contrastive SSL on Provenance Graphs | Pending weak | Positive > negative cosine rate only `0.5227` | Do not spend GPU on GraphCL until node features/negatives improve |
| Continuous-Time TGN | Pending weak | Previous-event baseline Macro F1 `0.6044` beat logistic temporal/hash features `0.5972` | Reframe from next-event prediction to anomaly/window detection |
| APT Detector Watermarking | Active but failed first gate | Macro-F1 dropped `-0.0866`; trigger signature accuracy stayed `0.2391` | Redesign trigger objective or add owner-verification head before surrogate testing |
| Membership Inference | Negative | Same-distribution shadow ROC-AUC `0.5599`; temporal nonmembers `0.7256` | Park as evidence that temporal shift drives apparent leakage |
| GNN TTP Graph Embeddings | Hold | SVD retrieval strong, but GraphSAGE top-5 `0.060` vs SVD `0.926` | Keep simple TTP-set result; do not pitch GNN yet |
| Few-Shot APT Group Attribution | Active narrow result | ATT&CK TTP-set SVD top-5 `0.879` at 5 shots | Viable as ATT&CK profile retrieval, not CTI prose attribution without labels |
| LLM Threat Intelligence Fusion | Blocked | Sources support retrieval/extraction, not early-warning outcome labels | Define outcome labels before model work |
| Concept Drift on Provenance Detectors | Pending architecture-ready | Full Cadets windows exist; weak density proxy is learnable from event/exec rates with chronological Macro-F1 up to `0.9788` | Needs interval labels, confirmed benign windows, or another labeled stream for publishable drift claims |
| Stage Routing on Provenance Graphs | Hold | Praxis 04 shows stage prediction bottleneck | Only reopen if graph stage labels/predictor beat temporal split bottleneck |
| Cross-Detector Adversarial Robustness | Later | No stable detector suite yet | Wait for 2-4 trained detector families |
| Causal GNN for Evasion Resistance | Later | High-ceiling, no local gate yet | Keep as follow-on after 2+ publishable wins |
| Reverse TTP Extraction | Shelved | No public simulator/data | Revisit only after stronger publication base |

## Architecture Added To Reopen Work

| Component | Current result | What it opens | What it does not solve |
|---|---|---|---|
| Provenance window factory | Local smoke: `98,862` Cadets edges to `20` windows | Common inputs for drift, TGN, SSL, graph routing, watermarking, MIA | Does not invent labels |
| PIDSMaker node-label attachment | `126` E5-CADETS node labels attached; `19/20` local windows touched attack nodes | Lets us test attack-touch windows honestly | Node labels are not stage labels or full interval truth |
| Detector-zoo registry | Four baseline families instantiate cleanly | Shared detector suite foundation | No detector claim until class support is adequate |
| Detector-zoo gate | Correctly blocked full Cadets: `9,609` attack-touch vs `2` benign/unlabeled | Prevents bogus supervised claims | Needs interval labels or confirmed benign support |
| Full E5 Cadets cloud job | Complete: `480,537,673` edge events, `9,611` windows, `371,328.882` seconds | Scaled the architecture, but class support is `9,609` attack-touch / `2` benign-or-unlabeled | Detector claim remains blocked; use density only as weak proxy |
| Cadets density proxy gate | Weak-proxy available | Low-touch/high-touch threshold `5,000`; event/exec-only chronological Macro-F1 `0.9704` to `0.9788` | Useful for sample prioritization and representation stress tests, not attack detection |
| DAPT2020 external-validity note | Appendix evidence / negative TTA check | MLP recipe Macro F1 `0.6353 +/- 0.0043`, Recon F1 `0.8932 +/- 0.0089`; DAPT TTA selected TENT test Macro F1 delta `-0.2874`, Recon delta `-0.6589`; test DE support is only `2` | Use only as detector-recipe transfer evidence and as a negative cross-dataset TTA feasibility check |

## What Could Still Open Experiments

| Missing piece | Experiments it would reopen | Practical path |
|---|---|---|
| Full-stream Cadets/OpTC windows with enough benign and attack support | Concept drift, TGN, graph SSL, graph routing, MIA, watermarking | Full Cadets finished but did not provide enough benign support; next path is confirmed benign intervals, another labeled stream, or OpTC subset |
| Attack intervals, anomaly spans, or stage labels | Stage routing, supervised provenance detectors, drift evaluation | Use PIDSMaker labels where valid, add interval labels manually only when source truth supports them |
| Stable detector suite | Watermarking, MIA, adversarial robustness | Train detector zoo only after class support passes |
| CTI early-warning outcome labels | LLM Threat Intelligence Fusion | Build a dated campaign/outcome evaluation set before modeling |
| SEC-LoRD redesign with strict answer formatting | SEC-LoRD / DS-LoRD | Replace prompt stuffing with retrieval-constrained evidence or task-specific seed selection; re-gate before extraction |

## Recommendation

Write Praxis 06 around TTA. Keep the architecture work as a second track, not a competing claim. The full Cadets cloud result scaled successfully but remained label-blocked: PIDSMaker node-touch labels are too broad for supervised benign-vs-attack detection. The provenance line should now move only through confirmed interval labels, another labeled host stream, or weak-proxy diagnostics clearly marked as non-ground-truth.
