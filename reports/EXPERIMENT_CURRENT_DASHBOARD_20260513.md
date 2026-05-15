# Experiment Current Dashboard

Updated: 2026-05-15

Sources: `reports/EXPERIMENT_FINAL_EVALUATION_20260511.md`, `reports/EXPERIMENT_DASHBOARD.md`, `configs/experiment_cloud_handoff_registry.json`, the local handoff checks run on 2026-05-14, and the expanded OpTC cross-host gate run on 2026-05-15.

## Where We Left Off

The portfolio has one defense-ready positive result: `TTA for Streaming APT Detection`. The locked replay, AWS agreement, robustness checks, matched confidence-reject baseline, and paper assets make it the only current Praxis-grade claim.

The second major result is architectural rather than scientific: provenance windowing and the detector-zoo registry now work, including the full E5 Cadets window factory. Cadets supervised claims remain blocked because node-touch labels collapse almost every window into attack-touch. OpTC now clears the label/data gate across three red-team host/day slices plus three benign host baselines, but detector promotion remains blocked by host/day shift.

The remaining experiments are a useful queue, not a pile of half-wins. Praxis 04, stage-conditioned imbalance, MIA, SEC-LoRD prompt seeding, GraphSAGE TTP embeddings, first-pass watermarking, AI supply-chain provenance, SSL provenance, and next-event TGN each taught a clear constraint.

## Priority Dashboard

| Priority | Track | Current posture | Best evidence | Next action |
|---:|---|---|---|---|
| 1 | TTA for Streaming APT Detection / Praxis 06 | Lead positive; cloud hardening PASS; seven-seed defense addendum complete | Locked replay Macro-F1 `0.8658`, Recon F1 `0.5050`, PR-AUC `0.8738`, override rate `4.7%`; matched confidence-reject Recon F1 `0.0000`; cloud paper audit passed 12/12 checks; seven-seed addendum Macro F1 `0.8477 +/- 0.0226`, Recon F1 `0.5147 +/- 0.0589` | Convert the draft/assets into the target venue package. Keep original locked replay primary; use seven-seed run as robustness addendum. No threshold changes. |
| 2 | Praxis 06 venue package | Expanded thesis-neutral LaTeX draft; thesis wrapper added; CI/layout sanity PASS; defense deck scaffold complete; first claim-alignment editorial pass complete | LaTeX workspace exists under `paper/praxis06_tta/`; GitHub Actions run `25881761738` built both PDFs from commit `37a64c5`: article `8` pages, thesis chapter `14` pages; contact-sheet reviews passed for both; 12-slide defense PPTX generated; 2026-05-15 edits align the provenance boundary with the expanded OpTC result | Trigger/inspect the next CI PDFs, then tune table/figure placement and polish slide visuals. No threshold changes. |
| 3 | Few-Shot APT Group Attribution | Selected second narrow result; retrieval closeout PASS | ATT&CK TTP-set 5-shot top-5: overlap `0.960`, SVD `0.879`, random `0.028`, frequency prior `0.041`; median rank `1.0`; degree-bucket analysis complete; GraphSAGE pilot remains negative | Convert this into a compact thesis/paper section. Keep scope as ATT&CK TTP-set profile retrieval, not CTI prose attribution and not a GNN claim. |
| 4 | Provenance labels / OpTC or interval truth | Expanded OpTC label/data gate PASS; detector claim not promoted | Full E5 Cadets remains label-blocked (`9,609` attack-touch vs `2` benign/unlabeled). OpTC now has three red-team host/day slices plus three benign baselines: `717` usable non-gray windows and `108` gray-buffer windows excluded. Red support: `sysclient0501` day 2 `82/21` attack/background, `sysclient0201` day 1 `112/54`, `sysclient0051` day 3 `41/107`; each matched benign baseline adds `100` background windows. Pooled sanity is strong (`all_behavior` RF/ET Macro-F1 `0.8750`), but host-baselined and strict host holdout both fail. | Treat OpTC as a Praxis-ready label/data artifact, not a detector result. Next detector work must solve host/day generalization or be framed explicitly as label-acquisition/protocol feasibility. |
| 5 | APT Detector Watermarking | Closed negative for current detector lineage; direct trigger and owner-head redesign both failed | Direct watermark fine-tune: Macro-F1 delta `-0.0866`, trigger signature accuracy `0.2391`; sidecar owner-head: utility delta `+0.0000`, eval trigger detection `0.5217` vs required `>=0.9500`, eval false watermark rate `0.0435` | Archive for now. Do not run surrogate extraction. Reopen only after a stronger detector suite exists or the ownership claim is reframed away from transferable watermarking. |
| 6 | AI Supply Chain Backdoor Detection | Weak first LoRA result; multi-strength redesign gate ready | First LoRA trace effects: loss `0.0401`, grad-norm `-0.0673`, update-norm `0.0203`; new gate defines `9` paired clean/poison runs across `1%`, `5%`, `10%` poison and seeds `41/42/43` with richer trace logging | Run the cheap multi-strength cloud gate only if resources allow. Promote only if 5% poison clears ROC-AUC/AP `>=0.7000` with stable signs on `>=2/3` seeds; otherwise archive for this cycle. |
| 7 | SEC-LoRD / DS-LoRD | Hold; current method negative; retrieved-evidence prompt gate ready | Strict audit: 3B vanilla `0.276` vs seeded `0.090`; 8B vanilla `0.466` vs seeded `0.284`; new prompt gate has `500` CTI-MCQ rows with `1.000` ATT&CK evidence coverage | Run one cheap strict model gate: vanilla vs retrieved evidence vs broad-seed negative control. No extraction unless retrieved evidence beats vanilla by `>= +0.030`. |
| 8 | Concept Drift / SSL / TGN on Provenance | Pending weak or architecture-ready | Density proxy is learnable, but not ground truth; SSL positive > negative cosine only `0.5227`; previous-event baseline beat next-event TGN features | Run only weak-proxy diagnostics until labels exist. No GPU GraphCL/TGN push yet. |

## Paper Anchors Behind The Dashboard

| Priority | Track | Research paper / source anchor | Gap this experiment fills | Current decision |
|---:|---|---|---|---|
| 1 | TTA for Streaming APT Detection / Praxis 06 | Wang et al. (2021), *Tent: Fully Test-Time Adaptation by Entropy Minimization* | Applies no-label adaptation to high-consequence cybersecurity streams with validation-selected safety gates rather than unconstrained adaptation | Selected lead positive |
| 2 | Praxis 06 venue package | Same Praxis 06 anchor: Wang et al. (2021), plus the local DAPT2020 external-validity check | Converts the bounded TTA finding into a defensible thesis/venue package without expanding the claim | Packaging in progress |
| 3 | Few-Shot APT Group Attribution | Strom et al. (2020), *MITRE ATT&CK: Design and Philosophy*; Hamilton et al. (2017), GraphSAGE as the failed learned-embedding comparison | Formalizes few-shot ATT&CK group-profile retrieval from observed TTP sets; separates profile retrieval from CTI prose attribution | Selected second narrow result |
| 4 | Provenance labels / OpTC or interval truth | Han et al. (2020), UNICORN; Gama et al. (2014), concept drift adaptation; OpTC red-team ground-truth artifact | Provides label-faithful provenance windows before drift, TGN, SSL, MIA, watermarking, or detector-zoo claims | Expanded label/data artifact ready; detector claim blocked by host/day shift |
| 5 | APT Detector Watermarking | Adi et al. (2018), DNN watermarking by backdooring | Tests whether APT detectors can carry owner-verifiable signatures without losing normal detection utility | Closed negative for this detector lineage |
| 6 | AI Supply Chain Backdoor Detection | Gu et al. (2017), BadNets / ML supply-chain backdoor risk | Moves from final-model behavior to training-trace provenance diagnostics for poisoned fine-tuning runs | Weak first result; falsifiable multi-strength gate ready |
| 7 | SEC-LoRD / DS-LoRD | Carlini et al. (2021), extracting training data from LLMs; Lewis et al. (2020), retrieval-augmented generation | Tests whether question-specific CTI evidence can improve strict task compliance before any LoRD-style extraction claim | Current method negative; redesign gate only |
| 8 | Concept Drift / SSL / TGN on Provenance | Gama et al. (2014), drift; You et al. (2020), GraphCL; Rossi et al. (2020), TGN; Han et al. (2020), UNICORN | Reopens dynamic/representation provenance modeling only after honest labels exist | Hold weak-proxy diagnostics only |

## Reference Details For Paper Anchors

| Anchor | APA reference |
|---|---|
| TTA / Praxis 06 | Wang, D., Shelhamer, E., Liu, S., Olshausen, B., & Darrell, T. (2021). *Tent: Fully test-time adaptation by entropy minimization*. International Conference on Learning Representations. https://openreview.net/forum?id=uXl3bZLkr3c |
| ATT&CK profile retrieval | Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). *MITRE ATT&CK: Design and philosophy*. MITRE. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy |
| Graph embedding comparison | Hamilton, W. L., Ying, Z., & Leskovec, J. (2017). Inductive representation learning on large graphs. In *Advances in Neural Information Processing Systems 30*. https://papers.nips.cc/paper/6703-inductive-representation-learning-on-large-graphs |
| Provenance APT detection | Han, X., Pasquier, T., Bates, A., Mickens, J., & Seltzer, M. (2020). UNICORN: Runtime provenance-based detector for advanced persistent threats. In *Network and Distributed System Security Symposium*. https://tfjmp.org/publication/2020-ndss/ |
| Concept drift | Gama, J., Zliobaite, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014). A survey on concept drift adaptation. *ACM Computing Surveys, 46*(4), 1-37. https://doi.org/10.1145/2523813 |
| Detector watermarking | Adi, Y., Baum, C., Cisse, M., Pinkas, B., & Keshet, J. (2018). Turning your weakness into a strength: Watermarking deep neural networks by backdooring. In *27th USENIX Security Symposium* (pp. 1615-1631). https://www.usenix.org/conference/usenixsecurity18/presentation/adi |
| Supply-chain backdoors | Gu, T., Dolan-Gavitt, B., & Garg, S. (2017). BadNets: Identifying vulnerabilities in the machine learning model supply chain. *arXiv:1708.06733*. https://arxiv.org/abs/1708.06733 |
| LLM extraction / SEC-LoRD | Carlini, N., Tramer, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, U., Oprea, A., & Raffel, C. (2021). Extracting training data from large language models. In *30th USENIX Security Symposium* (pp. 2633-2650). https://www.usenix.org/conference/usenixsecurity21/presentation/carlini-extracting |
| Retrieval-conditioned CTI prompts | Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems 33*. https://papers.nips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html |
| Graph contrastive learning | You, Y., Chen, T., Sui, Y., Chen, T., Wang, Z., & Shen, Y. (2020). Graph contrastive learning with augmentations. In *Advances in Neural Information Processing Systems 33*. https://arxiv.org/abs/2010.13902 |
| Temporal graph networks | Rossi, E., Chamberlain, B., Frasca, F., Eynard, D., Monti, F., & Bronstein, M. (2020). Temporal graph networks for deep learning on dynamic graphs. *arXiv:2006.10637*. https://arxiv.org/abs/2006.10637 |
| OpTC label path note | `external/datasets/optc/OpTCRedTeamGroundTruth.pdf` is treated as a release ground-truth artifact rather than a peer-reviewed paper; it supports the label path, not a detector claim. |

## Stop Or Hold List

| Track | Decision |
|---|---|
| Praxis 04 - Stage-Conditional Routing | Preserve as negative bottleneck evidence. Predicted-stage routing failed under shift. |
| Stage-Conditioned Class Imbalance | Park simple weighting/resampling. Rare-class gain was too small and Benign collapsed. |
| Membership Inference | Park as negative/control evidence: temporal shift explains most apparent leakage. |
| GNN TTP Graph Embeddings | Hold GNN claim. Keep the simple SVD/overlap TTP-set result. |
| Praxis 05 SAE on MAGIC hidden states | Hold. Phase A failed feature-death and seed-stability gates. Only a larger-hidden-state PIDSMaker pivot is justified. |
| APT Detector Watermarking | Archive current detector lineage. Direct watermarking harmed utility and failed signature learning; the owner-verification sidecar preserved utility but missed the trigger-detection gate. |
| LLM Threat Intelligence Fusion | Blocked until dated campaign/outcome labels exist. |
| Cross-Detector Adversarial Robustness | Later; needs 2-4 stable trained detector families. |
| Causal GNN for Evasion Resistance | Later; keep as a follow-on after stronger publication base. |
| Reverse TTP Extraction | Shelved; no public simulator/data path. |

## Recommended Next Sequence

1. Trigger/inspect the next Praxis 06 CI PDFs after the 2026-05-15 editorial pass, then tune table/figure placement. The work is paper assembly and venue conversion, not another threshold search.
2. Polish the Praxis 06 defense deck from `paper/praxis06_tta/defense_slides/PRAXIS06_DEFENSE_SLIDES_20260514.pptx`, then tune thesis/venue formatting. Use the seven-seed hardening addendum as robustness material, not as a replacement for the locked replay.
3. Keep the pushed handoff memory current. Latest pushed experiment commits include `ed45763` for the expanded OpTC provenance label gate.
4. Convert the second selected result into a thesis/paper section using `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`, `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`, and `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_PAPER_OUTLINE_20260514.md`.
5. Keep provenance as label/data readiness until detector generalization is solved. The expanded OpTC subset is now enough for honest host/day holdout tests, and those tests block a detector claim.
6. Watermarking is archived for now. AI supply-chain provenance and SEC-LoRD are both gate-ready; run them only as cheap strict gates before any expensive extraction or replication work.

## New Decision Artifacts

| Artifact | Purpose |
|---|---|
| `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md` | Definitive doctoral-style table of experiment ideas, research gap, status, metrics, and selected/dropped/reframed decision. |
| `reports/EXPERIMENT_PORTFOLIO_CLOSEOUT_20260514.md` | Compact closeout: selected positives, archived negatives, gate-ready items, and label/data blockers. |
| `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_PROTOCOL_20260513.md` | Formal protocol for the next narrow positive: ATT&CK TTP-set group-profile retrieval. |
| `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_REFRESH_20260513.md` | Refreshed ATT&CK TTP-set retrieval baseline confirming SVD top-5 `0.879` and overlap top-5 `0.960` at 5 shots. |
| `reports/provenance_architecture/PROVENANCE_LABEL_PATH_DECISION_20260513.md` | Label-path decision; recommends targeted OpTC subset first, Cadets interval labels as fallback. |
| `reports/provenance_architecture/OPTC_GROUND_TRUTH_SEED_MANIFEST_20260513.md` | First OpTC label feasibility artifact: 101 timestamped red-team seed events extracted from the public ground-truth PDF. |
| `reports/provenance_architecture/OPTC_LABEL_ACQUISITION_PLAN_20260514.md` | Concrete answer for how provenance labels are obtained from OpTC red-team seeds plus targeted eCAR host/day shards. |
| `reports/provenance_architecture/OPTC_WINDOW_LABEL_GATE_RESULT_20260514.md` | First OpTC targeted host/day label-support gate: `82` attack, `21` background, `22` gray-buffer windows from `625,000` converted eCAR edges. |
| `reports/provenance_architecture/OPTC_SUPERVISED_SMOKE_GATE_20260514.md` | Strict targeted OpTC supervised smoke: detector registry consumes `103` non-gray windows, with chronological-generalization caveat. |
| `reports/provenance_architecture/OPTC_CROSS_HOST_GATE_20260515.md` | Expanded OpTC label/data gate across three red-team host/day slices plus three benign baselines; label support passes, detector promotion fails under host/day holdout. |
| `reports/apt_detector_watermarking/NEXT_GATE_DESIGN_20260513.md` | Cheap redesign gate for detector watermarking before surrogate extraction. |
| `reports/apt_detector_watermarking/WATERMARK_OWNER_HEAD_GATE_20260514.md` | Redesign closeout for detector watermarking; owner-verification head failed held-out trigger detection. |
| `reports/ai_supply_chain_training_provenance/NEXT_GATE_DESIGN_20260513.md` | Cheap redesign gate for poisoned LoRA training-trace provenance. |
| `reports/ai_supply_chain_training_provenance/AI_SUPPLY_CHAIN_MULTISTRENGTH_GATE_READY_20260514.md` | Concrete 9-run multi-strength LoRA provenance gate for AI supply-chain backdoor detection. |
| `reports/sec_lord_ds_lord/NEXT_GATE_DESIGN_20260513.md` | Cheap redesign gate for SEC-LoRD/DS-LoRD after strict parser failure. |
| `reports/sec_lord_ds_lord/SEC_LORD_RETRIEVED_EVIDENCE_GATE_READY_20260514.md` | Concrete SEC-LoRD retrieved-evidence prompt gate; 500 CTI-MCQ rows with exact ATT&CK evidence coverage. |
| `paper/praxis06_tta/main.tex` | Expanded thesis-neutral LaTeX draft for the Praxis 06 TTA paper. |
| `paper/praxis06_tta/thesis_chapter.tex` | Thesis/Praxis chapter wrapper that reuses the article body. |
| `paper/praxis06_tta/TARGET_STYLE_DECISION_20260514.md` | Records the thesis-chapter-first packaging decision and venue conversion notes. |
| `paper/praxis06_tta/VISUAL_LAYOUT_REVIEW_20260514.md` | Contact-sheet visual sanity review for the latest 8-page CI PDF. |
| `paper/praxis06_tta/THESIS_CHAPTER_LAYOUT_REVIEW_20260514.md` | Contact-sheet visual sanity review for the 14-page thesis-chapter PDF. |
| `paper/praxis06_tta/defense_slides/README.md` | Defense-deck handoff index with the open-first files and rebuild command. |
| `paper/praxis06_tta/defense_slides/PRAXIS06_DEFENSE_SLIDE_OUTLINE_20260514.md` | Slide-by-slide Praxis 06 defense outline with speaker intent and backup-slide plan. |
| `paper/praxis06_tta/defense_slides/PRAXIS06_DEFENSE_SLIDES_20260514.pptx` | Usable 12-slide PowerPoint defense deck generated from the outline. |
| `scripts/build_praxis06_defense_deck.py` | Rebuild script for the Praxis 06 PowerPoint deck. |
| `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md` | Formal result #2 write-up for ATT&CK TTP-set profile retrieval. |
| `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md` | Result #2 closeout with random/frequency floors, degree buckets, and example five-shot retrievals. |
| `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_PAPER_OUTLINE_20260514.md` | Paper/chapter outline for turning the ATT&CK retrieval result into a manuscript section. |
| `.github/workflows/praxis06-paper.yml` | GitHub Actions paper build path for Praxis 06. |
| `reports/tta_streaming_apt/PRAXIS06_CI_BUILD_20260514.md` | CI build proof that the Praxis 06 LaTeX draft compiles to PDF. |
| `reports/provenance_architecture/OPTC_ECAR_CONVERSION_GATE_20260514.md` | OpTC eCAR-to-window conversion gate and pass criteria. |
| `paper/portfolio_experiment_decks/README.md` | Handoff index for PowerPoint decks covering dashboard items 3, 4, and 7. |
| `paper/portfolio_experiment_decks/EXPERIMENT_03_ATTACK_TTP_RETRIEVAL_DECK_20260514.pptx` | PowerPoint deck for the selected ATT&CK TTP-set profile retrieval result. |
| `paper/portfolio_experiment_decks/EXPERIMENT_04_PROVENANCE_LABEL_PATH_DECK_20260514.pptx` | PowerPoint deck for the provenance label path and OpTC gate. |
| `paper/portfolio_experiment_decks/EXPERIMENT_07_SEC_LORD_REDESIGN_GATE_DECK_20260514.pptx` | PowerPoint deck for the SEC-LoRD / DS-LoRD redesign gate. |
| `scripts/build_portfolio_experiment_decks.py` | Rebuild script for the portfolio experiment decks. |
| `scripts/run_attack_ttp_retrieval_closeout.py` | Reproducible closeout analysis for ATT&CK retrieval floors, buckets, and examples. |
| `scripts/run_watermark_owner_head_gate.py` | Reproducible owner-verification-head gate for the watermarking redesign. |
| `scripts/build_ai_supply_chain_multistrength_gate.py` | Builds paired clean/poison LoRA gate files for the AI supply-chain provenance redesign. |
| `scripts/build_optc_interval_labels.py` | Builds padded OpTC attack intervals and target host/day shortlist from the red-team seed manifest. |
| `scripts/download_optc_target_ecar.py` | Resolves and downloads one targeted OpTC eCAR host/day Google Drive folder from the local PIDSMaker URL map. |
| `scripts/run_optc_supervised_smoke_gate.py` | Runs the targeted OpTC `attack` vs `background` detector-registry smoke while excluding gray-buffer and label-derived columns. |
| `scripts/run_optc_cross_host_gate.py` | Runs the expanded OpTC label/data and host/day holdout detector gate. |
| `scripts/export_experiment_dashboard_html.py` | Rebuild script for the browser-viewable dashboard export. |
| `scripts/build_sec_lord_retrieved_evidence_gate.py` | Builds the SEC-LoRD vanilla / broad-seed / retrieved-evidence strict prompt gate. |
| `reports/EXPERIMENT_CURRENT_DASHBOARD_20260514.html` | Browser-viewable dashboard export with the paper-anchor table. |

## Immediate Commands

Use the diagnostic environment for checks:

```powershell
.\.venv-diag\Scripts\python.exe -m pytest tests/test_detector_registry.py tests/test_provenance_window_factory.py
powershell -ExecutionPolicy Bypass -File .\scripts\check_cloud_handoff_state.ps1
```

Before cloud runs, paste the startup prompt from `templates/experiment_cloud_prompt.template.md` and name a single experiment id from `configs/experiment_cloud_handoff_registry.json`.

Primary TTA capability report: `reports/tta_streaming_apt/TTA_FUNCTIONING_CAPABILITY_REPORT_20260513.md`.

Paper-ready TTA final report: `reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md`.

Cloud TTA paper-hardening audit: `reports/tta_streaming_apt/cloud_paper_hardening_20260513/PRAXIS06_FINAL_CLOUD_PAPER_AUDIT_20260513.md`.

TTA defense-hardening addendum: `reports/tta_streaming_apt/PRAXIS06_DEFENSE_HARDENING_ADDENDUM_20260513.md`.

## Current Risk

The main repository-state risk has been reduced: standard lightweight handoff files are committed and pushed. Remaining local noise is outside the standard lightweight prefixes: `.vscode/settings.json`, standalone planning documents, and `codex_mobile_project_20260429/`.

The local Windows environment does not currently have `pandoc` or `pdflatex`, but the GitHub Actions paper build now compiles the expanded LaTeX draft successfully. The latest CI PDF also renders locally with PyMuPDF, so the remaining packaging risk is editorial: choosing the target venue/thesis style, visually reviewing page layout, and fitting the paper to that format.
