# PX-081 — Choosing additional evidence for attack-stage decisions

Frozen development protocol, 23 September 2026. No results existed when this protocol was written.

## Question and scope

Can a policy that estimates the reduction in stage-weighted classification error choose optional evidence more usefully than an uncertainty-reduction policy at the same acquisition budget and deadline?

This is **offline feature-group acquisition replay**, not live log collection, a reproduced SEFA/L2M system, or a claim to invent active feature acquisition. UNRAVELED is an already-examined, single-campaign development dataset. Current inputs describe completed flows; no early-warning or exfiltration forecast is measured. Author movement labels in this sensor concern remote-system discovery. The 35 evaluation movement examples are not independent campaigns.

## Input and split

Use the previously qualified `host_history_exfil_v1/prepared/DATA.npz` without changing it. Preserve its 11 captures and chronological split: captures 0–4 fit, 5 calibration, 6–10 evaluation. The calibration partition is not needed by this fixed policy and remains unused. Input SHA256 is recorded in the freeze manifest. Current features exclude labels, literal host identifiers, source/capture identifiers and absolute timestamps. Optional groups are static coarse host roles and earlier completed-flow history. They are precomputed features whose hypothetical retrieval is simulated; roles in particular may be inexpensive to cache in real deployments.

The script checks all histories precede the current flow and that fitting ends before calibration, which ends before evaluation. Roles/history are not known by a policy until that group is delivered. Classifiers for all four subsets share the same sampled fitting rows. Fit caps per class are 12,000 benign and 4,000 each other class, retaining all rare movement cases. Seeds: 8101, 8102, 8103.

## Models and policy training

Four fixed LightGBM classifiers use current, current+roles, current+history, and current+roles+history inputs. Each has 150 trees, 15 leaves, learning rate .05, minimum child count 10, L2=1, two CPU threads, no class weighting, no tuning and no early stopping.

Generate forward out-of-fold predictions: fit captures <1 and predict capture1, then <2→2, <3→3, <4→4. No evaluated row is used to fit its generating model. Fit selectors from only these OOF rows, with the same per-class caps. Each transition from an observed subset to a one-group-larger subset has one harm regressor and one entropy regressor (four transitions per objective). Regressors use 100 trees, 9 leaves, minimum child count20, learning rate .05, L2=1. Their inputs are current observations, already acquired optional features and the current subset's four predicted probabilities. They never inspect the unacquired group's values or probabilities.

Harm target = weighted hard-classification error before acquisition minus error after acquisition. Correct classification costs0; incorrect classification costs1 for a true benign/other-stage row and4 for a true movement/exfiltration row. These are **self-imposed illustrative priorities**, not literature standards or estimates of monetary harm. Also report ordinary unweighted errors and all per-stage outcomes so this choice cannot manufacture an overall-positive conclusion.

Entropy target = Shannon entropy of the pre-acquisition probability vector minus entropy after acquisition. This is a practical learned expected-information proxy, not a faithful reproduction of a published algorithm. Both regressors use identical permitted state and fitting rows. Policies greedily maximize estimated benefit × configured channel-success prior / cost, stop when the best estimate is nonpositive, and never query an unaffordable channel. Metadata contains quoted nominal delay/cost, not actual success or actual arrival. A channel whose quoted arrival exceeds the remaining deadline is not attempted. Realized delay/unavailability is revealed only after an attempted query, which is charged even if it fails or arrives late.

## Frozen comparisons and simulated conditions

Policies: no acquisition; fixed roles-first; fixed history-first; deterministic random order; learned expected entropy reduction; learned expected stage-error reduction. A seventh **full-context reference** uses both groups without cost/deadline restrictions; it is explicitly excluded from same-budget superiority comparisons.

Budgets1,2,3 simulated cost units. Role cost1 and history cost2; nominal delays .25 and .75 simulated time units. Deadline1.0. Sequential acquisition; actual delays accumulate. All policies share the same row-specific schedule. No automatic abstentions or correct labels for unresolved cases: the model using the last delivered subset makes every prediction.

Conditions:

1. Clean: all queried groups available at nominal delays.
2. Delayed/unavailable: role/history success probabilities .8/.65; additional delay0/.5/1.5 with probabilities .6/.25/.15. Values are deterministic pseudorandom functions of seed, observable event hash and channel. Draws use no labels or source/capture identities. Selection knows configured success priors, but no realized draw. Late/failed queries are charged.
3. Wrong-host history: use the existing qualified `wrong_history` values whenever history is delivered; clean arrival schedule. This is a deliberate correspondence-corruption sensitivity test, not a measured field failure or a new independent workflow. Selector training remains clean.

## Outcomes and interpretation

Publish every seed, budget, condition and policy, and by-capture breakdowns. Metrics: macro-F1, per-class precision/recall/F1/AP/ROC AUC, movement/exfiltration missed counts, movement-as-exfiltration confusion, benign false alerts, weighted/unweighted error, query count, delivered-group count, spend and elapsed time. No invented 90% gate or tuned operating point. Null and harmful results are retained. Seed spread measures fitting sensitivity, not population uncertainty; no row bootstrap or claim of independent campaigns.

Write exact per-row probabilities, actions, deliveries, cost and elapsed time to private results for independent recomputation. Public tables contain no raw host identities. The independent audit recomputes confusion-based metrics, budget/deadline/delivery consistency and input/output hashes. Unit tests verify failed/late queries cost budget, hidden evidence does not enter the first decision, unavailable groups cannot change model state, and synthetic correct/error reductions give the expected harm target.

## Literature and contribution boundary

- [Guney et al., ICML 2025, explainability-driven acquisition](https://proceedings.mlr.press/v267/guney25a.html): adaptive acquisition already exists.
- [Norcliffe et al., ICML 2025, SEFA](https://proceedings.mlr.press/v267/norcliffe25a.html): complementary evidence can defeat simple greedy acquisition.
- [Learning-To-Measure, 2025/2026](https://arxiv.org/html/2510.12624v2): fixed feature and cost assumptions motivate operational extensions; this pilot is not its implementation.
- [Basak and Shin, Sim-CTKG, 2025/2026](https://www.mdpi.com/1424-8220/26/1/21): budgeted logging with latency already has cybersecurity precedent.

Any promising result here justifies implementing stronger published comparators and measuring real acquisition on independent executions. It does not establish novelty, real collection savings, enterprise generalization or successful attack prediction.
