# EXP-RQ1: feature identification

**Status:** prospective matched-study experiment not run; wording approved October 24, 2026. Earlier archive/synthetic screens are exploratory only. **Tracker:** E01, with final confirmation in E04. **Development target:** Nov 6; locked evaluation Nov 7.

**RQ1:** Which target-side host and network behavioral feature families distinguish human-operated from autonomous-AI APT-like trials under matched conditions?

**H1:** Command diversity and command-sequence transition entropy improve classification of human-operated versus autonomous-AI APT-like activity compared with a predefined baseline.

| Element | Method |
| --- | --- |
| Observation | One trial-level outcome; windows/events remain nested within trial |
| Independent variables | Command diversity and transition entropy included/removed individually and jointly; host/network family ablations as supporting analyses |
| Primary response | Paired difference in trial-level macro-F1 |
| Secondary evidence | Per-class errors, family permutation importance and ranking stability |
| Matched controls | Same trial partitions, classifier settings, tuning policy and seeds for predefined contrasts |
| Development | Define families and correlated sets from training data; assess validation-fold reliance; retrain each ablation with the frozen tuning policy |
| Confirmation | Apply only frozen contrasts to locked predictions; group-aware uncertainty and multiplicity correction |
| Acceptance | Supported improvement for the frozen individual/joint feature contrasts; exact baseline and decision rule unresolved until freeze |
| Limitation | Reliance is model-conditional and does not establish a causal marker of autonomy |

Deliver a dictionary, feature counts, full/ablated model manifests, per-trial predictions and family-level uncertainty table. Keep model choice/feature discovery within development folds. [Fillable experiment record](templates/EXPERIMENT_TEMPLATE.md) · [Results record](templates/RESULTS_TEMPLATE.md).

[October 24 hypothesis rationale and revision history](../../PRAXIS_RESEARCH_DESIGN.md#october-24-revision-and-evidentiary-basis). Freeze exact contrasts, baselines and practical margins before final evaluation.
