# Experiment Portfolio Closeout

Generated: 2026-05-15

Repository state: pushed through `b8852a4` on branch `experiment/tta-streaming-apt`; expanded OpTC label-gate work now extends beyond that commit.

## Bottom Line

The portfolio now has two selected positive results and a clear stop/gate/block decision for the rest.

| Tier | Experiment | Decision | Evidence | Next work |
|---|---|---|---|---|
| Selected result 1 | TTA for Streaming APT Detection / Praxis 06 | **Selected lead positive** | Locked replay Macro-F1 `0.8658`, Recon F1 `0.5050`, override `4.7%`; confidence-reject Recon F1 `0.0000`; seven-seed addendum Recon F1 `0.5147 +/- 0.0589`; cloud audit PASS | Editorial packaging only: thesis/venue formatting and slide polish. No threshold changes. |
| Selected result 2 | ATT&CK TTP-set profile retrieval | **Selected narrow positive** | 5-shot top-5: overlap `0.960`, SVD `0.879`, random `0.028`, frequency prior `0.041`; median rank `1.0`; GraphSAGE negative | Convert into thesis/paper section as profile retrieval, not CTI prose attribution and not a GNN claim. |
| Architecture/feasibility | Provenance labels / OpTC | **Expanded label/data gate PASS; detector not promoted** | E5 Cadets window factory still label-blocked, but OpTC now covers three red-team host/day slices plus three clean benign baselines: `717` usable non-gray windows, `108` gray-buffer windows excluded, and per-red-slice attack/background support of `82/21`, `112/54`, and `41/107`; pooled sanity reaches all-behavior Macro-F1 `0.8750`, but host/day holdout fails | Use as a Praxis-ready label/data artifact and detector-generalization blocker. Do not claim a provenance detector until host/day shift is solved. |
| Archived | APT detector watermarking | **Closed negative for current detector lineage** | Direct fine-tune: Macro-F1 delta `-0.0866`, trigger signature `0.2391`; sidecar owner-head: utility delta `+0.0000`, trigger detection `0.5217` vs `>=0.9500` | Do not run surrogate extraction. Reopen only with stronger detector families or a materially different ownership protocol. |
| Gate ready | AI supply-chain training provenance | **Weak first result; falsifiable gate ready** | First LoRA trace effects weak: loss `0.0401`, grad-norm `-0.0673`, update-norm `0.0203`; 9-run multi-strength gate now built | Run only if cheap cloud budget is available. Promote only if 5% poison clears ROC-AUC/AP `>=0.7000` with stable signs on `>=2/3` seeds. |
| Narrow positive | Relationship-Evidence CTI Compliance / Praxis 07 | **Relationship-evidence model gate PASS; local slice audit PASS; A2 cloud audit next** | Old broad seed remains negative: 3B vanilla `0.276` vs seeded `0.090`; 8B vanilla `0.466` vs seeded `0.284`. New 8B relationship-evidence gate on `106` no-label addressable rows: vanilla `0.642`, relationship evidence `0.915`, broad seed `0.642`, delta `+0.274`, evidence-only wins `33` vs vanilla-only `4`. Local A1/A3/A4 slice audit passed and prepared a `394`-row complement input. | Run A2 complement-slice 8B vanilla cloud audit before 3B cross-model or ablation. Keep LoRD extraction separate. |
| Hold | Concept drift / SSL / TGN on provenance | **Hold until labels** | Density proxy learnable but not truth; SSL positive > negative cosine `0.5227`; previous-event baseline beat next-event TGN | No GPU GraphCL/TGN push until honest labels exist. |

## What Is Done

- The dashboard has a browser-viewable HTML export: `reports/EXPERIMENT_CURRENT_DASHBOARD_20260514.html`.
- Praxis 06 has a paper draft, thesis wrapper, CI build, and defense deck.
- Result #2 has a protocol, refreshed baseline, closeout analysis, and paper outline.
- Experiments 3, 4, and 7 have standalone PowerPoint decks under `paper/portfolio_experiment_decks/`.
- Watermarking has been given one fair redesign gate and is now archived for the current detector lineage.
- AI supply-chain has concrete gate-ready artifacts instead of vague next steps. The old SEC-LoRD broad-seed route remains negative, but the relationship-evidence rescue has become a separate Praxis 07 candidate scoped narrowly as CTI-MCQ task compliance rather than extraction.
- Provenance is no longer blocked at the first label-acquisition step: expanded OpTC labels now pass support across three red-team host/day slices and three benign baselines, and the detector-registry gate exposes host/day generalization as the real blocker.

## Do Not Do

| Area | Prohibited shortcut |
|---|---|
| Praxis 06 | Do not re-search thresholds or replace the locked replay with robustness runs. |
| ATT&CK retrieval | Do not call the result CTI prose attribution or a GraphSAGE win. |
| Provenance | Do not train supervised detectors on attack-touch labels as if they were ground truth; do not claim an OpTC detector from pooled/random splits while host/day holdout fails. |
| Watermarking | Do not run surrogate extraction from the failed direct or sidecar gates. |
| AI supply-chain | Do not claim provenance detection from the weak first LoRA trace effects. |
| SEC-LoRD / Relationship evidence | Do not run extraction from broad seeded prompts; strict answer parsing failed. Do not call the relationship-evidence CTI compliance result an extraction result. |

## Next Logical Sequence

1. Finish Praxis 06 editorial packaging and defense slides.
2. Convert ATT&CK retrieval into the second thesis/paper section.
3. For provenance, write the expanded OpTC result as label/data readiness and host/day-shift evidence; do not promote a detector result yet.
4. If running more experiments, run only the gate-ready jobs: relationship-evidence CTI A2 complement audit first, then 3B/ablation only if A2 passes; AI supply-chain multi-strength provenance remains separate.
5. Keep the dashboard and this closeout file updated only when a posture changes.
