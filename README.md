# Praxis Research

Praxis Research is a future-work-to-experiment program. The project reviews 2025-2026 AI/ML papers, identifies practical opportunities from future-work sections and reproducibility gaps, proposes bounded experiments, and tracks whether each experiment produced a positive result, a negative result, a blocked result, or a future research lead.

## Public Research Dashboard

- Public dashboard URL: https://garypagangit.github.io/praxis/
- [Praxis Research Experiment Tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html)
- [Final positive report export with tracker](reports/praxis_final_positive_reports_20260701/PRAXIS_FINAL_POSITIVE_REPORTS_WITH_TRACKER_EXPORT_20260705.txt)
- [Final positive report index](reports/praxis_final_positive_reports_20260701/README.md)
- [PX-002 final bounded lookup package](reports/gnn_attribution_ttp_graph_embeddings/px002_final_defense_package_export_20260706/PX002_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md)
- [Recommendation implementation audit](reports/PRAXIS_RECOMMENDATION_IMPLEMENTATION_20260705.md)
- [D1 agent-defense deconfliction and new candidate queue](reports/agentic_deployment_defense/D1_AGENTIC_DEFENSE_DECONFLICTION_20260705.md)
- [D1 new experiment follow-on rollup](reports/agentic_deployment_defense/d1_followon_rollup_20260705/D1_NEW_EXPERIMENT_FOLLOWON_ROLLUP_20260705.md)
- [PX-050 final manuscript](reports/agentic_deployment_defense/px050_final_manuscript_20260705/PX050_FINAL_MANUSCRIPT_20260705.md)
- [PX-050 final defense package export](reports/agentic_deployment_defense/px050_final_defense_package_export_20260705/PX050_FINAL_DEFENSE_PACKAGE_EXPORT_20260705.md)
- [PX-050 held-out third-model boundary](reports/agentic_deployment_defense/px050_heldout_third_model_20260705/PX050_HELDOUT_THIRD_MODEL_REPLICATION_20260705.md)
- [PX-050R strict held-out repair](reports/agentic_deployment_defense/px050r_strict_heldout_repair_20260705/PX050R_STRICT_HELDOUT_REPAIR_SYNTHESIS_20260705.md)
- [PX-050S controller/extractor held-out repair](reports/agentic_deployment_defense/px050s_controller_extractor_20260705/PX050S_CONTROLLER_EXTRACTOR_HELDOUT_SYNTHESIS_20260705.md)
- [PX-050T controller/extractor adaptive stress](reports/agentic_deployment_defense/px050t_controller_adaptive_stress_20260705/PX050T_CONTROLLER_EXTRACTOR_ADAPTIVE_STRESS_20260705.md)
- [PX-050U live-agent tool-boundary gate](reports/agentic_deployment_defense/px050u_live_agent_tool_boundary_20260705/PX050U_LIVE_AGENT_TOOL_BOUNDARY_SYNTHESIS_20260705.md)
- [PX-050 two-model live-agent final determination](reports/agentic_deployment_defense/px050_live_agent_two_model_determination_20260705/PX050_LIVE_AGENT_TWO_MODEL_FINAL_DETERMINATION_20260705.md)
- [PX-051V live-agent policy refresh](reports/agentic_deployment_defense/px051v_live_agent_policy_refresh_20260705/PX051V_LIVE_AGENT_POLICY_REFRESH_20260705.md)
- [PX-052V live-agent provenance refresh](reports/agentic_deployment_defense/px052v_live_agent_provenance_refresh_20260705/PX052V_LIVE_AGENT_PROVENANCE_REFRESH_20260705.md)
- [PX-054 final manuscript](reports/refusal_geometry_recurrent_depth/px054_final_manuscript_20260706/PX054_FINAL_MANUSCRIPT_20260706.md)
- [PX-054 final defense package export](reports/refusal_geometry_recurrent_depth/px054_final_defense_package_export_20260706/PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md)

The HTML tracker is the front-door overview for the research portfolio. It lists each experiment by stable `PX-###` ID with title, objective, status, short finding, and links to supporting evidence.

Public viewers can read, clone, and download the repository. Write access remains controlled by GitHub repository permissions for the owner and invited collaborators.

## Current Positive Results

The strongest Praxis candidates currently tracked are:

- `PX-001`: DAPT graph/ML routing experiments.
- `PX-002`: ATT&CK TTP-set profile retrieval, packaged as a bounded lookup-style positive and not as a defense pillar.
- `PX-003/PX-034`: CTI relationship-evidence prompting and source-support risk stratification.
- `PX-004`: Hallucination-resistant source-locked QA.
- `PX-005`: MoE standing-committee/router observability, now positioned as a bounded confirmation/extension result.
- `PX-011`: HalluHard deterministic verification gate.

`PX-002` is now packaged as a bounded CTI lookup result: five observed ATT&CK techniques retrieve the correct group profile with overlap top-5 `0.960` and SVD top-5 `0.879` under the standard known-profile protocol, compared with random `0.028` and frequency prior `0.041`. The defense audit blocks a stronger defense-pillar claim because leave-query-out stress produced overlap top-5 `0.000` and SVD top-5 `0.299`; use the result only as analyst-triage profile retrieval.

The latest PX-003/PX-034 full-bucket AWS audit found relationship-evidence prompting improved Qwen2.5-7B accuracy from `0.614` to `0.822` across 500 CTI rows. The result supports the relationship-evidence lift claim, while narrowing the router claim to source-support and conflict-risk stratification rather than a hard answerability oracle.

The new D1 agent-defense branch has now been tested through follow-on gates. `PX-050` is a publishable bounded positive with a final manuscript draft, final defense package export, and final two-model live-agent determination: it cleared fixed, Qwen live, DeepSeek replication, 984-row parser-stress, PX-050S controller/extractor repair, PX-050T adaptive stress, PX-050U Qwen dry-run live-agent, and PX-050V DeepSeek dry-run live-agent gates with zero observed hardened invalid-package escapes, while keeping the registry-uplift claim model-dependent. Raw and strict one-line StarCoder2 promotion gates failed, so they are published as boundary evidence. `PX-050S` passed the deployment-shaped controller/extractor repair on a fresh StarCoder2 held-out namespace. `PX-050T` then stress-tested that repair over `1,440` crafted raw-output strings: `1,140` invalid cases, invalid allows `0`, valid allow rate `1.0000`, and registry-only invalid allows `300`. `PX-050U/PX-050V` then prompted Qwen2.5-Coder-7B and DeepSeek-Coder-6.7B as dry-run coding agents over `288` combined tool-call tasks: install-action rate `1.0000`, raw unsafe rate `0.9453`, controller recovery `0.9757`, hardened invalid allows `0`, and valid allow rate `1.0000`. `PX-051V` passed the 288-row live-agent policy refresh with hardened invalid escape `0.0000`, utility preserved `1.0000`, and review rate `0.0243`. `PX-052V` passed the 288-row live-agent provenance refresh with alert recall `1.0000`, clean false-positive rate `0.0000`, and trace completeness `1.0000`. `PX-054` is now packaged as a defense-ready bounded characterization positive: the safe Huginn scale gate captured `600/600` activation rows over `120` prompts and depths `[4, 8, 16, 32, 64]`, with cross-depth stability `0.9257`, CI `[0.9067, 0.9273]`, benign-control FPR `0.0000`, and worst refusal TPR `0.9750`. `PX-049` failed its earlier live agentic slopsquatting gate because the model produced zero install actions, and `PX-053` failed its synthetic approval-fatigue gate.

## Repository Layout

- `reports/`: dashboards, final reports, audit reports, and downloadable exports.
- `cloud_jobs/`: AWS experiment job packages and run wrappers.
- `scripts/`: local analysis, export, and experiment helper scripts.
- `src/praxis/`: reusable Praxis package code.
- `configs/`: experiment and training configuration files.
- `tests/`: local test coverage for supported utilities and workflows.

Large model artifacts, datasets, checkpoints, caches, and local run outputs are intentionally excluded from Git unless a small artifact is needed as supporting evidence.

## Reproducing Or Reviewing Results

Start with the tracker, then follow each experiment's evidence links into its report, code, logs, and result tables.

For local development, install the project dependencies in a Python 3.11 environment and run focused scripts from `scripts/` or experiment-specific wrappers in `cloud_jobs/`. AWS-backed runs expect the caller to have valid AWS SSO credentials and access to the project S3 bucket.

## GitHub Access

Canonical repository:

```text
https://github.com/garypagangit/praxis
```

Recommended public branch:

```text
praxis-research
```
