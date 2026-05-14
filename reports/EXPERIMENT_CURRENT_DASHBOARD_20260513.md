# Experiment Current Dashboard

Updated: 2026-05-14

Sources: `reports/EXPERIMENT_FINAL_EVALUATION_20260511.md`, `reports/EXPERIMENT_DASHBOARD.md`, `configs/experiment_cloud_handoff_registry.json`, and the local handoff checks run on 2026-05-14.

## Where We Left Off

The portfolio has one defense-ready positive result: `TTA for Streaming APT Detection`. The locked replay, AWS agreement, robustness checks, matched confidence-reject baseline, and paper assets make it the only current Praxis-grade claim.

The second major result is architectural rather than scientific: provenance windowing and the detector-zoo registry now work, including the full E5 Cadets window factory, but supervised provenance claims remain blocked because the available node-touch labels collapse almost every window into attack-touch.

The remaining experiments are a useful queue, not a pile of half-wins. Praxis 04, stage-conditioned imbalance, MIA, SEC-LoRD prompt seeding, GraphSAGE TTP embeddings, first-pass watermarking, AI supply-chain provenance, SSL provenance, and next-event TGN each taught a clear constraint.

## Priority Dashboard

| Priority | Track | Current posture | Best evidence | Next action |
|---:|---|---|---|---|
| 1 | TTA for Streaming APT Detection / Praxis 06 | Lead positive; cloud hardening PASS; seven-seed defense addendum complete | Locked replay Macro-F1 `0.8658`, Recon F1 `0.5050`, PR-AUC `0.8738`, override rate `4.7%`; matched confidence-reject Recon F1 `0.0000`; cloud paper audit passed 12/12 checks; seven-seed addendum Macro F1 `0.8477 +/- 0.0226`, Recon F1 `0.5147 +/- 0.0589` | Convert the draft/assets into the target venue package. Keep original locked replay primary; use seven-seed run as robustness addendum. No threshold changes. |
| 2 | Praxis 06 venue package | Expanded thesis-neutral LaTeX draft; CI build PASS; target style still open | LaTeX workspace exists under `paper/praxis06_tta/`; GitHub Actions run `25875430166` built an 8-page PDF from commit `ecfb6e0`; `main.tex` now carries related work, method, results, external validity, threats, PR operating-point figures, and appendices | Choose target venue/thesis style and tune length/figures. No threshold changes. |
| 3 | Few-Shot APT Group Attribution | Active narrow result; 2026-05-13 retrieval refresh PASS | ATT&CK TTP-set SVD top-5 `0.879` at 5 shots; overlap top-5 `0.960`; median rank `1.0` | Turn this into a formal ATT&CK profile retrieval result. Do not call it CTI prose attribution without report-to-group labels. |
| 4 | Provenance labels / OpTC or interval truth | Architecture-ready but label-blocked; OpTC seed manifest and eCAR conversion scaffold ready | Full E5 Cadets: `480,537,673` edge events to `9,611` windows; class support `9,609` attack-touch vs `2` benign/unlabeled`; OpTC PDF yielded `101` timestamped red-team seed events across 3 days | Next: download/mirror a targeted OpTC eCAR shard, run `scripts/build_optc_window_gate.ps1`, and require `>=20` benign / `>=20` attack windows before detector training. |
| 5 | APT Detector Watermarking | Active, first gate failed | Macro-F1 delta `-0.0866`; trigger signature accuracy `0.2391` | Redesign the trigger objective or add a separate owner-verification head before any surrogate extraction. |
| 6 | AI Supply Chain Backdoor Detection | Pending weak | LoRA trace effects: loss `0.0401`, grad-norm `-0.0673`, update-norm `0.0203` | Build a stronger poison construction and richer gradient/update diagnostics before multi-seed cloud replication. |
| 7 | SEC-LoRD / DS-LoRD | Hold, current method negative | Strict audit: 3B vanilla `0.276` vs seeded `0.090`; 8B vanilla `0.466` vs seeded `0.284` | Redesign task formatting and seed selection; re-gate with strict answer parsing before extraction. |
| 8 | Concept Drift / SSL / TGN on Provenance | Pending weak or architecture-ready | Density proxy is learnable, but not ground truth; SSL positive > negative cosine only `0.5227`; previous-event baseline beat next-event TGN features | Run only weak-proxy diagnostics until labels exist. No GPU GraphCL/TGN push yet. |

## Stop Or Hold List

| Track | Decision |
|---|---|
| Praxis 04 - Stage-Conditional Routing | Preserve as negative bottleneck evidence. Predicted-stage routing failed under shift. |
| Stage-Conditioned Class Imbalance | Park simple weighting/resampling. Rare-class gain was too small and Benign collapsed. |
| Membership Inference | Park as negative/control evidence: temporal shift explains most apparent leakage. |
| GNN TTP Graph Embeddings | Hold GNN claim. Keep the simple SVD/overlap TTP-set result. |
| Praxis 05 SAE on MAGIC hidden states | Hold. Phase A failed feature-death and seed-stability gates. Only a larger-hidden-state PIDSMaker pivot is justified. |
| LLM Threat Intelligence Fusion | Blocked until dated campaign/outcome labels exist. |
| Cross-Detector Adversarial Robustness | Later; needs 2-4 stable trained detector families. |
| Causal GNN for Evasion Resistance | Later; keep as a follow-on after stronger publication base. |
| Reverse TTP Extraction | Shelved; no public simulator/data path. |

## Recommended Next Sequence

1. Decide the target venue format and convert `paper/praxis06_tta/main.tex` from thesis-neutral `article` style into the selected class. The work is paper assembly and venue conversion, not another threshold search.
2. Add final figure placement and visual PDF review. Use the seven-seed hardening addendum as robustness material, not as a replacement for the locked replay.
3. Keep the pushed handoff memory current. Last pushed commits: `7fdb4b9` and `9e0a183`.
4. Use the formal protocol for ATT&CK TTP-set few-shot attribution as a second narrow result: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_PROTOCOL_20260513.md`.
5. Spend provenance effort on labels, not models. The recommended first path is a targeted OpTC subset, with Cadets interval labels as fallback: `reports/provenance_architecture/PROVENANCE_LABEL_PATH_DECISION_20260513.md`.
6. Run only cheap redesign gates for watermarking, AI supply-chain provenance, and SEC-LoRD. Each now has a corrected gate memo before expensive cloud work.

## New Decision Artifacts

| Artifact | Purpose |
|---|---|
| `reports/EXPERIMENT_IDEA_DECISION_MATRIX_20260513.md` | Definitive doctoral-style table of experiment ideas, research gap, status, metrics, and selected/dropped/reframed decision. |
| `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_PROTOCOL_20260513.md` | Formal protocol for the next narrow positive: ATT&CK TTP-set group-profile retrieval. |
| `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_REFRESH_20260513.md` | Refreshed ATT&CK TTP-set retrieval baseline confirming SVD top-5 `0.879` and overlap top-5 `0.960` at 5 shots. |
| `reports/provenance_architecture/PROVENANCE_LABEL_PATH_DECISION_20260513.md` | Label-path decision; recommends targeted OpTC subset first, Cadets interval labels as fallback. |
| `reports/provenance_architecture/OPTC_GROUND_TRUTH_SEED_MANIFEST_20260513.md` | First OpTC label feasibility artifact: 101 timestamped red-team seed events extracted from the public ground-truth PDF. |
| `reports/apt_detector_watermarking/NEXT_GATE_DESIGN_20260513.md` | Cheap redesign gate for detector watermarking before surrogate extraction. |
| `reports/ai_supply_chain_training_provenance/NEXT_GATE_DESIGN_20260513.md` | Cheap redesign gate for poisoned LoRA training-trace provenance. |
| `reports/sec_lord_ds_lord/NEXT_GATE_DESIGN_20260513.md` | Cheap redesign gate for SEC-LoRD/DS-LoRD after strict parser failure. |
| `paper/praxis06_tta/main.tex` | Expanded thesis-neutral LaTeX draft for the Praxis 06 TTA paper. |
| `.github/workflows/praxis06-paper.yml` | GitHub Actions paper build path for Praxis 06. |
| `reports/tta_streaming_apt/PRAXIS06_CI_BUILD_20260514.md` | CI build proof that the Praxis 06 LaTeX draft compiles to PDF. |
| `reports/provenance_architecture/OPTC_ECAR_CONVERSION_GATE_20260514.md` | OpTC eCAR-to-window conversion gate and pass criteria. |

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

The local Windows environment does not currently have `pandoc` or `pdflatex`, but the GitHub Actions paper build now compiles the venue-neutral LaTeX skeleton successfully. The remaining packaging risk is editorial: choosing the target venue/thesis style and fitting the paper to that format.
