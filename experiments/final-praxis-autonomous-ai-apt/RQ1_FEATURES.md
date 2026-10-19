# EXP-RQ1: feature identification

**Status:** draft / not run. **Tracker:** E01, with final confirmation in E04. **Development target:** Nov 6; locked evaluation Nov 7.

**RQ1:** Which target-side host and network behavioral feature families distinguish human-operated from autonomous-AI trials under matched conditions?

**H1:** At least one predeclared family improves trial-level macro-F1 over the frozen baseline. Specify that baseline and the contrast for each family before scoring; do not retrospectively pick the weakest comparator.

| Element | Method |
| --- | --- |
| Observation | One trial-level outcome; windows/events remain nested within trial |
| Independent variables | Host-only, network-only, combined representation; included/removed feature family |
| Primary response | Paired difference in trial-level macro-F1 |
| Secondary evidence | Per-class errors, family permutation importance and ranking stability |
| Matched controls | Same trial partitions, classifier settings, tuning policy and seeds for predefined contrasts |
| Development | Define families and correlated sets from training data; assess validation-fold reliance; retrain each ablation with the frozen tuning policy |
| Confirmation | Apply only frozen contrasts to locked predictions; group-aware uncertainty and multiplicity correction |
| Acceptance | Supported positive contrast under the preregistered rule; otherwise not supported or inconclusive according to precision |
| Limitation | Reliance is model-conditional and does not establish a causal marker of autonomy |

Deliver a dictionary, feature counts, full/ablated model manifests, per-trial predictions and family-level uncertainty table. Keep model choice/feature discovery within development folds. [Fillable experiment record](templates/EXPERIMENT_TEMPLATE.md) · [Results record](templates/RESULTS_TEMPLATE.md).
