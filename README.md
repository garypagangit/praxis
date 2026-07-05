# Praxis Research

Praxis Research is a future-work-to-experiment program. The project reviews 2025-2026 AI/ML papers, identifies practical opportunities from future-work sections and reproducibility gaps, proposes bounded experiments, and tracks whether each experiment produced a positive result, a negative result, a blocked result, or a future research lead.

## Public Research Dashboard

- Public dashboard URL: https://garypagangit.github.io/praxis/
- [Praxis Research Experiment Tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html)
- [Final positive report export with tracker](reports/praxis_final_positive_reports_20260701/PRAXIS_FINAL_POSITIVE_REPORTS_WITH_TRACKER_EXPORT_20260705.txt)
- [Final positive report index](reports/praxis_final_positive_reports_20260701/README.md)
- [Recommendation implementation audit](reports/PRAXIS_RECOMMENDATION_IMPLEMENTATION_20260705.md)
- [D1 agent-defense deconfliction and new candidate queue](reports/agentic_deployment_defense/D1_AGENTIC_DEFENSE_DECONFLICTION_20260705.md)
- [D1 new experiment follow-on rollup](reports/agentic_deployment_defense/d1_followon_rollup_20260705/D1_NEW_EXPERIMENT_FOLLOWON_ROLLUP_20260705.md)

The HTML tracker is the front-door overview for the research portfolio. It lists each experiment by stable `PX-###` ID with title, objective, status, short finding, and links to supporting evidence.

Public viewers can read, clone, and download the repository. Write access remains controlled by GitHub repository permissions for the owner and invited collaborators.

## Current Positive Results

The strongest Praxis candidates currently tracked are:

- `PX-001`: DAPT graph/ML routing experiments.
- `PX-003/PX-034`: CTI relationship-evidence prompting and source-support risk stratification.
- `PX-004`: Hallucination-resistant source-locked QA.
- `PX-005`: MoE standing-committee/router observability, now positioned as a bounded confirmation/extension result.
- `PX-011`: HalluHard deterministic verification gate.

The latest PX-003/PX-034 full-bucket AWS audit found relationship-evidence prompting improved Qwen2.5-7B accuracy from `0.614` to `0.822` across 500 CTI rows. The result supports the relationship-evidence lift claim, while narrowing the router claim to source-support and conflict-risk stratification rather than a hard answerability oracle.

The new D1 agent-defense branch has now been tested through first follow-on gates. `PX-050`, `PX-051`, and `PX-052` cleared positive prototype/framework gates; `PX-054` cleared a safe Huginn activation-characterization gate; `PX-049` failed its live agentic slopsquatting gate because the model produced zero install actions; and `PX-053` failed its synthetic approval-fatigue gate. These D1 results are tracked separately from the five core Praxis positives until scaled or replicated.

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
