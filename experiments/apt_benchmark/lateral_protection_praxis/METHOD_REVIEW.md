# Methodology review: fewer false alarms without hiding lateral movement

**Proposal review, September 21, 2026.** No new model, threshold search, or experimental result was produced for this document. These are suggested design decisions, not a registered protocol. The lateral-movement question was generated after inspecting completed development results.

## Assessment

**A worthwhile applied question remains; a novel algorithm has not been identified.** Investigate whether choosing benign training support, class weights, and a decision threshold under an explicit lateral-detection constraint can reduce unnecessary alerts. Constrained classification, asymmetric support, class weighting, and calibrated thresholds are established ideas. The potential contribution is a controlled, independently validated account of when they help, their label cost, and when the constraints are infeasible.

The [completed benign-control study](../results/strong_benign_controls_v1/REPORT.md) supplies the motivation: adding 992 normal fitting examples reduced normal false alarms from 10.04% to 0.40%, but lateral flows detected as any attack fell from 94.24% to 83.06%. Attack fitting examples were unchanged. This does not identify the cause: benign coverage, class balance, model choice, and tuning may all contribute. The [complete decision report](../results/tabular_followup_decision_v1/REPORT.md) also records failed external transfer and a negative two-channel review policy. Neither result should be relabeled as success for this proposal.

## One concrete procedure to test

**Lateral-constrained benign-support selection:** choose a conventional detector and its operating threshold to minimize benign alerts, subject to a prespecified acceptable loss in lateral-activity detection.

1. Retain the same 32 fitting examples for each of five attack stages: 160 attack labels. Form nested, outcome-independent benign supports of 32, 128, 512, and 1,024 examples. Use identical support indices across model families at each budget. Total fitting sizes are 192, 288, 672, and 1,184. These are support-budget comparisons, not four independent data collections.
2. Start with tuned XGBoost and LightGBM, plus TabICL at **every matched support budget** if resources permit. Keep a random forest control. Preprocessing, candidate hyperparameters, fitting seeds, tuning budgets, and tie rules must be fixed before the new evaluation. Do not claim a foundation/tree architecture advantage from unequal fitting data. If an abundant-benign foundation arm is unaffordable, restrict the primary claim to trees.
3. For trees, compare ordinary empirical class proportions, equal total fitting weight per class, and equal class mass with a lateral multiplier from a small fixed grid such as `{1, 2, 4}`. The multiplier changes training emphasis; it is not a new loss function. Equal class mass separates increased benign coverage from increased benign loss mass. Do not silently approximate sample weights in a foundation model that does not support them.
4. Use the continuous attack score `1 - p(NormalTraffic)` and a single strict `score > threshold` rule. No new rescue ensemble is needed. On selection data, choose the configuration with the lowest false-alert rate among those satisfying the lateral constraint and false-alert budget; break ties by fewer fitting labels, then a fixed model/parameter order. Fix the threshold and configuration before opening verification data.
5. A separate verification partition can accept or reject this **one locked choice**. It cannot supply another threshold or a second-choice model after failure. If multiple configurations are to be certified on the same verification sample, a prespecified simultaneous procedure is necessary; a collection of individual 95% intervals is insufficient after selecting the best result.

For a clean first primary comparison, fix the benign fitting budget at **1,024 for every arm**. The smaller-budget allocation curves are secondary and all are reported. A later policy that selects its own budget is a separate comparison with equal *available-label caps*, not necessarily equal *actually used fitting labels*. Disclose both. Accessing all 1,024 benign labels to select a 128-row support does not demonstrate a 128-label acquisition cost.

## Controls that prevent an easy but uninformative win

Use the same fitting rows, maximum label access, tuning folds, calibration access, and search budget for the controls. At minimum include:

- The stronger macro-F1-selected tree with its ordinary argmax decision.
- Its score threshold calibrated on normal data to the same false-alert target.
- Class-balanced and lateral-weighted trees with their thresholds selected using the same permitted development data; class weighting cannot be reserved for the proposal.
- An established constrained or Neyman–Pearson threshold procedure, with its assumptions and calibration cost stated.
- TabICL with a normal-calibrated threshold at the same fitting budget, if the proposed comparison includes foundation models.

Choose the primary reference from the conventional controls on selection data only. It should be a strong lateral-sensitive control, not the weak 192-label argmax tree selected because its historical false alarms were high. Report every fixed control on the final data, even when it was not selected as reference.

**Critical novelty test:** a cost-sensitive control allowed the same allocation and constrained selection may be mathematically the proposed procedure. If so, collapse the duplicate arms and describe the work as evaluation of an established method. Do not manufacture novelty by weakening that comparator. Winning only against argmax or macro-F1 selection supports an operating-policy improvement, not a new learning algorithm.

## Proposed endpoints and numerical gates

Detection means a true lateral flow generates **any attack alert**, regardless of the predicted stage. Correct lateral-stage classification is a separate secondary metric. Review routing is not a successful human investigation.

For confirmation, the independent sampling unit should be a genuinely distinct attack execution/capture and its background traffic, grouped at the highest shared incident or campaign level. For each incident, calculate the fraction of lateral flows detected and the fraction of benign flows falsely alerted. Average those fractions with equal incident weights; also report pooled flow counts. An incident with no lateral examples contributes no lateral recall denominator. Several files or random partitions from one execution are not independent incidents.

Let `R` be mean incident-level lateral-flow detection and `F` mean incident-level benign false-alert rate. A proposed single primary claim is **false-alert reduction subject to lateral noninferiority**, with all conditions required:

| Condition | Suggested confirmation criterion | Reason |
|---|---|---|
| Meaningful fewer false alerts | One-sided 95% upper bound for `F_candidate - 0.8 × F_reference` is below zero | Requires at least 20% relative reduction; avoids a ceiling-limited recall-improvement target |
| Lateral noninferiority | One-sided 95% lower bound for `R_candidate - R_reference` is above `-0.03` | Permits at most a three-percentage-point loss, not an unspoken claim of zero harm |
| Absolute lateral usefulness | One-sided 95% lower bound for `R_candidate` is at least `0.90` | Stops a weak reference from making a poor detector look acceptable |
| False-alert budget | One-sided 95% upper bound for `F_candidate` is at most `0.01` | States the intended operating cost; not a universal SOC capacity limit |

These values are **proposed operating requirements**, not values proven optimal by the old experiment or supplied by an industry standard. A 1% flow false-alert rate is still 1,000 alerts per 100,000 benign flows before aggregation. Report those counts, queue precision, total alert load, and a fixed aggregation rule if one is used. A flow percentage cannot be called analyst-hours saved without measuring the actual review process. If the reference already has essentially no false alerts, this reduction endpoint has no room to improve; declare that design infeasible rather than changing the endpoint after testing.

The primary joint claim requires every condition; this is an intersection claim, not permission to choose whichever endpoint passes. Freeze the incident-level interval method, campaign grouping, and multiplicity handling before collecting confirmation outcomes. Paired incident/campaign resampling may be suitable with enough independent groups; an iid flow bootstrap is not. Report each other attack stage as a prespecified harm check. Do not say all stages are protected when sparse labels make that unassessable.

## What the available data can and cannot support

The reused development split contains **144 lateral test flows**, not 144 known independent incidents. Ten fitting seeds do not multiply that evidence. Its official author holdout remains unavailable, and selecting this problem after observing its labels makes this split exploratory even if a new script is frozen now. Keep the old test split solely for descriptive feasibility checks; do not put its lateral outcomes into threshold selection.

Even under the optimistic assumption of independent paired flows, detecting noninferiority at a three-point margin is demanding. A simple normal-approximation planning calculation, assuming zero true paired recall difference, one-sided 5% error and 80% power, needs approximately **344, 687, or 1,374** lateral examples when the candidate/control discordance rate is 5%, 10%, or 20%, respectively. Formula: `n ≈ (z_.95 + z_.80)^2 × discordance / 0.03^2`. These are illustrative planning numbers, not achieved power; clustering and source shift can require substantially more independent executions. At 144 independent observations, even zero candidate-only misses has a one-sided exact 95% upper bound of about 2.06% for that harm probability; modest discordance quickly exhausts the three-point margin.

For a single fixed detector, zero false alerts in 299 independent benign observations is the smallest all-zero sample that can put a one-sided exact 95% binomial upper bound below 1%. This favorable corner case is not a recommended calibration size. The existing 29,929 normal calibration flows offer much more raw support, but their dependence and source specificity prevent treating that count as a deployment guarantee. A simple 99th percentile targets marginal tail behavior; it is not automatically a high-confidence bound on the fixed detector's population FPR.

Before confirmation, obtain or generate independently grouped executions with a verified lateral-movement label mapping and contemporaneous benign traffic. Split entire executions across fitting, selection/calibration, verification, and untouched confirmation; use a new network or time period for the latter. Independent replays can test robustness to experimental variation, but do not by themselves establish real-world incident generalization. Sandworm's already inspected, small procedure-labeled capture is not fresh stage-specific confirmation. If incident provenance or enough independent lateral examples cannot be obtained, stop at an applied development study and state that limitation plainly.

## Label accounting and conservative failure behavior

Publish separate counts for fitting, fitting-CV labels, model/threshold selection, normal calibration, labeled lateral verification, other-stage verification, and final evaluation. Count unique labels across overlapping supports once and disclose all labels inspected. The previous 192-label headline excluded 29,929 normal calibration labels; the new report must not repeat that omission. Newly dividing already inspected calibration data does not create fresh confirmatory evidence.

If no configuration passes the development constraints, record **INFEASIBLE**. If the independent sample is too small for the required intervals, record **INSUFFICIENT_EVIDENCE**. If confirmation fails, retain the result and do not retune on that confirmation set. Operationally retain the existing independently validated alerting process; if none exists, run in shadow mode. Do not suppress alerts merely to meet a queue budget, silently weaken the lateral floor, or describe an always-alert fallback as successful false-alert reduction.

## Literature position

- Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). *Systematic evaluation of few-shot learning for unseen IoT network attack detection*. **Computer Modeling in Engineering & Sciences, 147**(1), 45. [Primary article](https://www.techscience.com/CMES/v147n1/67129/html). Section 6.5 explicitly proposes more benign support to reduce benign/attack ambiguity. This directly limits novelty of the allocation idea.
- Tong, X., Feng, Y., & Li, J. J. (2018). *Neyman–Pearson classification algorithms and NP receiver operating characteristics*. **Science Advances, 4**(2), eaao1659. [Primary article](https://doi.org/10.1126/sciadv.aao1659); [author methods page](https://yangfengstat.github.io/projects/neyman_pearson/). Constraining one error while reducing another and calibrating held-out score thresholds are established. Distribution-free statements still require the stated sampling assumptions.
- Angelopoulos, A. N., Bates, S., Candès, E. J., Jordan, M. I., & Lei, L. (2025). *Learn then test: Calibrating predictive algorithms to achieve risk control*. **The Annals of Applied Statistics, 19**(2), 1641–1662. [Published article](https://doi.org/10.1214/24-AOAS1998); [author preprint](https://arxiv.org/abs/2110.01052). Calibration across candidate settings and multiple risk requirements is already studied through multiple testing; searching many thresholds does not confer free simultaneous validity.

See the [broader novelty assessment](../tabular_followup/NOVELTY_POSITION.md) and [benign-support overlap review](../tabular_followup/BENIGN_LABEL_NOVELTY_NOTE.md). The defensible thesis is an applied answer about labeling, false-alert cost, and protection of a subtle attack stage under independent testing. **No new algorithm, guaranteed protection under shift, or independently confirmed improvement is established yet.**
