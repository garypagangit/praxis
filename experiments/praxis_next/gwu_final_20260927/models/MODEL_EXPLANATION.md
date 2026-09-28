# Models and decision rules actually implemented

**Implementation audit: September 24, 2026.** This material describes the frozen PX080–PX083 implementations and their saved artifacts. It does not report new fitting or attribute proposed architectures to completed experiments. The accompanying [machine-readable inventory](MODEL_INVENTORY.json) binds source hashes and records configuration details, retained estimator metadata and model counts.

## 1. What the models do, in ordinary language

The main classifier is a collection of small decision trees. Each new set of trees improves on the scores already produced. One expert sees the current flow; another can also see summaries of earlier activity. A selector learns which expert is less likely to make a stage mistake. A separate acquisition policy estimates whether asking for another evidence group is worth its simulated cost. The chronological experiment changes the training population while keeping the classifier configuration fixed.

The three main experiments fitted **141 LightGBM estimators: 111 multiclass classifiers and 30 regressors**. These are repeated model fits for cross-fitting, controls and seeds, not 141 different architectures. The supplementary T1105 study fitted **two Ridge regressors** and reused previously fitted binary logistic classifiers. Thus the batch contains **143 new fits**, while the T1105 models address a different target from the four-class flow experiments.

| Experiment | Classifier fits | Regressor fits | Derivation |
|---|---:|---:|---|
| PX080: choose whether to use history | 33 | 6 | Per seed: eight forward-fold experts, two final experts, one augmented expert and two selectors; three seeds |
| PX081: choose which evidence to request | 60 | 24 | Per seed: sixteen forward-fold subset experts, four final experts and eight transition regressors; three seeds |
| PX082: compare training composition | 18 | 0 | Three seeds × two feature views × three training/evaluation protocols |
| PX083: supplementary score-policy transfer | 0 new | 2 | One ordinary and one target-cost Ridge selector; six existing T1105 classifier controls reused across two datasets |

Counts are verified against [PX080 completion](../../px080_context_selector/results/COMPLETE.json), [PX081 receipt](../../px081_evidence_acquisition/RUN_RECEIPT.json), [PX082 completion](../../px082_temporal_audit/COMPLETE.json), and [PX083 completion](../../px083_policy_transfer/results/COMPLETE.json). The four evaluation classes in the main experiments are the prepared grouping Benign, OtherAttackStage, LateralMovement and DataExfiltration. They are **declared evaluation classes**, not a universal native taxonomy. Movement in the inspected sensor represents author Remote System Discovery progress, not independently verified successful movement.

## 2. LightGBM multiclass experts

### Simple explanation

A tree asks a sequence of questions about numeric features, such as a flow size or a count of earlier contacts. Boosting adds trees sequentially to improve the model's scores. LightGBM uses binned feature values and grows a selected leaf at a time; these are library capabilities, not algorithmic inventions in this praxis. The primary algorithm reference is Ke et al. (2017, Section 2.1); implementation details follow the versioned [LightGBM feature documentation](https://lightgbm.readthedocs.io/en/v4.6.0/Features.html#leaf-wise-best-first-tree-growth).

### Compact mathematics for Chapter 3

An additive representation of the four class scores and their softmax transformation is:

$$
F_k(x)=F_{0,k}+\eta\sum_{m=1}^{M}h_{mk}(x),\qquad
p_k(x)=\frac{\exp(F_k(x))}{\sum_{j=0}^{3}\exp(F_j(x))}.
$$

Here, x is the supplied feature vector, h is a class-specific tree contribution, M is the number of boosting iterations, and η is the learning rate.

The multiclass data-fit loss and the implemented decision rule are:

$$
\mathcal L_{\mathrm{CE}}=-\sum_{i=1}^{n}\log p_{y_i}(x_i),\qquad
\widehat y_i=\operatorname*{arg\,max}_{k\in\{0,1,2,3\}}p_k(x_i).
$$

Here, y is the declared class of fitting example i; the largest class score determines its predicted class, with NumPy argmax selecting the first class in a tie.

The equation specifies the data-fit loss; LightGBM's tree-growing procedure and L2 leaf regularization determine the fitted ensemble. The code uses the ordinary `multiclass` objective inferred by `LGBMClassifier`, not a custom warning-retention objective. The expert fitting calls do not supply the stage cost vector as class or sample weights. Class-specific sampling caps change the fitting composition; that is different from weighting the classifier's loss. The scores are `predict_proba` outputs, but the main experiments perform no probability calibration. [LightGBM classifier API, `objective`, `class_weight`, `reg_lambda`, `predict_proba`](https://lightgbm.readthedocs.io/en/v4.6.0/pythonapi/lightgbm.LGBMClassifier.html).

### Exact configured settings

| Model role | Boosting iterations | Maximum leaves/tree | Learning rate |
|---|---:|---:|---:|
| PX080 experts, including augmented comparator | 180 | 15 | 0.05 |
| PX080 selector regressors | 120 | 7 | 0.05 |
| PX081 subset experts | 150 | 15 | 0.05 |
| PX081 acquisition regressors | 100 | 9 | 0.05 |
| PX082 experts | 200 | 15 | 0.05 |

| Model role | Minimum child samples | L2 leaf regularization | CPU threads |
|---|---:|---:|---:|
| PX080 experts, including augmented comparator | 10 | 1 | 4 |
| PX080 selector regressors | 30 | 5 | 4 |
| PX081 subset experts | 10 | 1 | 2 |
| PX081 acquisition regressors | 20 | 1 | 2 |
| PX082 experts | 10 | 1 | 2 |

`n_estimators` is a boosting-iteration setting. A four-class LightGBM iteration builds class-specific trees; it is inaccurate to describe 180 multiclass iterations as 180 total trees. Saved PX080 classifiers inspected in this audit have 180 iterations and 720 trees, and the retained PX081 classifiers have 150 iterations and 600 trees. PX082 saved probabilities and receipts, not serialized estimators, so its inventory records configured iterations without asserting an independently inspected final tree count. [LightGBM parameters, `num_iterations`](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html#num_iterations).

All these fits use `boosting_type='gbdt'`. Common unchanged wrapper defaults include `max_depth=-1`, `min_child_weight=0.001`, `min_split_gain=0`, `reg_alpha=0`, `subsample=1`, `subsample_freq=0`, `colsample_bytree=1`, and `subsample_for_bin=200000`. No validation-based early stopping or hyperparameter search is invoked. PX080 and PX082 explicitly set `deterministic=True` and `force_col_wise=True`; PX081 does not set those two flags. GOSS and DART were not selected. The implementations use CPU execution. PX080, PX082 and PX083 completion receipts explicitly record no AWS use, while PX081 records local CPU compute; cloud data-acquisition activity elsewhere is not a GPU model-fitting result. Full constructor and saved-booster parameters are preserved in [MODEL_INVENTORY.json](MODEL_INVENTORY.json).

## 3. PX080: learning when history adds a mistake

### Features and honest comparison targets

The current expert sees 62 current-flow features and eight role features: 70 inputs. The context expert adds 36 history summaries, the log-transformed age of the newest available earlier event, and a history-channel availability flag: 108 inputs. The 20 selector inputs comprise the two four-class probability vectors, their four differences, each expert's maximum score/margin/entropy, and the two history-status values. These are observable prediction/status features; the true class is not supplied at inference. See [implementation](../../px080_context_selector/run.py), functions `observe`, `selector_features`, `gate_target` and `fit_experts` (lines 59–93).

Four forward folds produce selector-training predictions: fit on captures earlier than 1 and predict capture 1, then repeat for captures 2, 3 and 4. Fitting completion times must precede validation start times. Within a fold, the same clean-fitted experts score clean, half-missing and stale histories. The ordinary and stage-cost regressors learn from these held-out comparisons; final experts are then fitted on the designated earlier period. This is forward cross-fitting, not random-fold cross-validation, nested tuning, or untouched external confirmation. The held-out comparison data belong to the already exposed development campaign.

Fitting row caps are 20,000 benign and 5,000 for each other class. Per-capture selector-validation caps are 12,000 benign and 5,000 for each other class. Seeds are 20260924, 20260925 and 20260926. Capture 5 is unused by these fits; captures 6–10 supply later descriptive evaluation. See the [frozen protocol](../../px080_context_selector/PROTOCOL.md) and runner lines 133–169.

### Selector target and decision

Define weighted stage error as:

$$
\ell_w(y,p)=w_y\,\mathbf 1\{\operatorname*{arg\,max}_k p_k\ne y\},\qquad
w=(1,1,4,4).
$$

Here, w assigns a self-imposed cost to the true evaluation class; every wrong destination for that class receives the same cost.

The gate's training response and deployment choice are:

$$
t_i=\ell_w(y_i,p_i^{H})-\ell_w(y_i,p_i^{C}),\qquad
p_i^{\mathrm{gate}}=
\begin{cases}
p_i^{H},&g(z_i)<0,\\
p_i^{C},&g(z_i)\ge 0.
\end{cases}
$$

Here, C and H denote the current and context experts, z contains the selector's observable inputs, and g is the fitted regression function.

The ordinary gate uses cost one for every class. A LightGBM regressor fits the numerical response using squared-error regression; it predicts a signed incremental loss, **not a calibrated probability that history is harmful**. The weight of four multiplies the response on selected true classes; it is not passed as `sample_weight` and is not a fourfold weight on the regressor's residual loss. [LightGBM regressor API, `objective`](https://lightgbm.readthedocs.io/en/v4.6.0/pythonapi/lightgbm.LGBMRegressor.html); [source target and fitting calls](../../px080_context_selector/run.py), lines 79–86 and 149–158.

This error definition treats exfiltration called benign and exfiltration called another attack stage equally: both cost four. It therefore does not explicitly optimize the retention of an attack warning. That implementation fact helps interpret the measured tradeoff, but does not establish that a replacement loss would improve it.

### Fixed and augmentation controls

The seven arms are current-plus-roles, context, equal probability fusion, maximum-confidence gate, ordinary learned gate, stage-harm gate and context-dropout classifier. Fusion averages the two probability vectors. The confidence gate chooses context only when its largest probability exceeds the current expert's largest probability; ties choose current. Neither control is another fitted selector.

The dropout comparator is one additional LightGBM classifier trained on two copies of each fitting row: a clean-history copy and a copy with history removed for the deterministic hash-defined half-missing subset. Each copy receives sample weight 0.5, preserving the row's total training weight. Removed history and age are zeroed and the availability flag is zero. This is feature-loss data augmentation, **not neural dropout or LightGBM DART**. Five evaluation conditions are retained: clean, half missing, all missing, a five-minute-old historical snapshot, and wrong-host history. The stale condition is a simulated cached-state intervention, not a measurement of real log-delivery delay. [Source](../../px080_context_selector/run.py), lines 63–71, 107–113 and 162–177.

## 4. PX081: selecting a useful evidence request

### What is fitted

Four multiclass experts represent the evidence already delivered: current only (62 inputs), current plus roles (70), current plus history (98), and all three groups (106). The state is a two-bit code: roles contributes bit 1 and history bit 2. Four legal transitions are learned: request roles or history from the empty optional state, history after roles, and roles after history. Each transition has an entropy regressor and an error-reduction regressor. Their inputs are the features already present in that state plus its four class probabilities; they do not include the unacquired group's values. Dimensions are 66, 74 or 102 depending on the transition's initial state. See [runner](../../px081_evidence_acquisition/run.py), lines 18–19, 33–59 and 172–190.

The four subset experts are cross-fitted over the same four earlier-to-later capture folds. A capped sample of the resulting held-out rows fits the transition regressors. Fitting and selector caps are 12,000 benign and 4,000 per other class. Final experts use the designated earlier fitting captures. Seeds are 8101, 8102 and 8103. The learned responses come from clean evidence; delayed/unavailable and wrong-host conditions are later simulated evaluations, not alternative labels used to train the policy.

### Learned gains

The two responses for acquiring group a in delivered state S are:

$$
u_i^{\mathrm{harm}}(S,a)=\ell_w(y_i,p_i^{S})-\ell_w(y_i,p_i^{S\cup\{a\}}),\qquad
u_i^{\mathrm{entropy}}(S,a)=H(p_i^{S})-H(p_i^{S\cup\{a\}}).
$$

Here, positive u means a favorable before-to-after change. H is predictive entropy: the negative sum of each class probability multiplied by its natural logarithm. The code clips logarithm inputs at 10⁻¹⁵.

These signs are the reverse of the history gate's incremental-loss response: acquisition seeks positive predicted improvement, whereas the history gate chooses context for negative predicted extra loss. Each transition regressor uses ordinary squared-error fitting to predict its response. Entropy reduction measures sharper model scores; it does not certify a more accurate decision.

### Actual greedy policy and simulated constraints

For eligible groups, the policy chooses:

$$
a^*=\operatorname*{arg\,max}_{a\in\mathcal E(S)}
\frac{q_a\,\widehat u(S,a)}{c_a},\qquad
\text{request only if }\frac{q_{a^*}\,\widehat u(S,a^*)}{c_{a^*}}>0.
$$

Here, c is the simulated request cost, q is a supplied availability prior, and the hatted u is the fitted gain for that transition.

The eligibility conditions are:

$$
a\notin A_{\mathrm{attempted}},\qquad
C_{\mathrm{spent}}+c_a\le B,\qquad
T_{\mathrm{elapsed}}+d_a^{\mathrm{nominal}}\le D.
$$

Here, B is the budget, D is the decision deadline, and the elapsed time accumulates realized delays after a request. The code applies a 10⁻⁷ numerical tolerance to deadline comparisons.

Roles cost one unit and nominally take 0.25 time units; history costs two and nominally takes 0.75. Budgets are 1, 2 and 3; the deadline is one unit. The delayed/unavailable regime supplies priors 0.8 and 0.65, respectively. Other regimes supply priors of one. Delayed requests add 0, 0.5 or 1.5 time units with simulated probabilities 0.60, 0.25 and 0.15. A request consumes cost and realized delay even if unavailable or late. The delivered state changes only if the requested evidence is available and arrives by the deadline. There are at most two requests and no retry of an attempted group. [Exact replay implementation](../../px081_evidence_acquisition/run.py), lines 68–112.

This is a **greedy one-step gain-per-cost heuristic**, not a globally optimized sequential planner, learned delay model, or deadline guarantee. It knows the declared regime's availability priors; it does not know the row's hidden availability/delay outcome before requesting. Multiplying by availability does not fully model the probability of timely arrival. Offline code precomputes all state scores, but the replay selects only the score indexed by the evidence actually delivered. Cost, delay and severity values are design choices rather than industry measurements or literature-mandated thresholds.

The six policies are no request, roles first, history first, random order, predicted entropy reduction and predicted stage-error reduction. All conditions and budgets are retained. An all-evidence reference is separately marked `reference_only`; it bypasses the sequential delivery constraints and is not a deployable policy. None of these acquisition arms is a reproduced SEFA or Learning-to-Measure implementation.

## 5. PX082: holding the model fixed while changing temporal access

This experiment uses ordinary unweighted multiclass LightGBM with current features (62 inputs) or current plus the 36 history summaries (98). It does **not** use the PX080 role, age or availability additions. Eighteen fits cover three seeds (20260923–20260925), two feature views and three protocols. No selector is fitted here. All models use argmax, with no threshold or probability calibration.

Past-only and time-mixed fitting share a 104,051-row later anchor and matched class counts of 20,000 benign, 5,000 other stage, 20 movement and 1,740 exfiltration. Anchor feature fingerprints are excluded from both fitting pools. The separate random-row protocol reserves 55% for evaluation and changes the evaluation population. Consequently, the controlled past/mixed contrast concerns training composition and temporal access; the random-row difference cannot be interpreted as the same isolated contrast. These are evaluation controls, not a new LightGBM architecture. See [protocol](../../px082_temporal_audit/protocol.json), [design](../../px082_temporal_audit/DESIGN.json), and [runner](../../px082_temporal_audit/run.py), lines 85–130.

## 6. Supplementary PX083: a Ridge policy on a different recognition task

### Scope and reused experts

The target is **T1105 Ingress Tool Transfer versus other author technique labels**. The negatives are not independently verified benign flows. CasinoLimit and CAM-LDS use different annotated units. This experiment therefore does not establish movement recognition, exfiltration prediction or benign false-alarm reduction. Only the selector transfers unchanged from Casino to CAM-LDS; each dataset retains its own native experts.

The reused current, context and mixed-dropout experts are binary `LogisticRegression` models, not LightGBM, GNNs or language models. Their frozen settings are `C=1`, `class_weight='balanced'`, `solver='liblinear'`, `max_iter=2000`, and `random_state=20260920`. Stored models use L2 regularization (`l1_ratio=0` in their original scikit-learn 1.9.0 state). They use fixed hashed text features rather than learned language-model embeddings. Each input has 65,546 columns: two 32,768-column hashed blocks plus ten metadata columns. The original mixed-dropout comparator uses six views—clean, random 25% loss, random 50% loss, EXECVE absent, PROCTITLE absent and both command records absent—with sample weight 1/6 per view, multiplied by the classifier's automatic class-balancing weights. No such native model was refitted in PX083. [Original runner](../../../apt_benchmark/robustness_v2/run.py), functions `fit_lr` and `run`; [original protocol](../../../apt_benchmark/robustness_v2/protocol.json), `classifier`, `text_features` and `arms`; [official logistic-regression documentation](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.LogisticRegression.html).

### Two deterministic linear selectors

Both selectors fit the same 1,494 Casino clean-calibration rows, including 87 target-positive rows. Only 11 rows have a nonzero expert-error comparison response; the full calibration sample size is not the number of informative disagreements. The ordinary response is context error minus current error at the strict score threshold 0.5. The target-cost response multiplies this difference by four for target-positive rows and one otherwise. The 12 observable inputs are the two scores, their signed/absolute difference, both binary confidences and margins, two visibility flags, threshold-decision disagreement, and the product of the scores. No scaler is fitted.

Ridge estimates the linear selector by:

$$
(\widehat b,\widehat\beta)=\operatorname*{arg\,min}_{b,\beta}
\left[\sum_{i=1}^{n}(t_i-b-z_i^\top\beta)^2+10\lVert\beta\rVert_2^2\right].
$$

Here, t is the ordinary or target-cost error-difference response, z is the 12-feature vector, b is the fitted intercept, and the coefficient penalty is `alpha=10`.

The solver is SVD, with `fit_intercept=True`; there is no random fitting seed or tuning search. A negative fitted linear score chooses context, otherwise current. The chosen expert's score is retained, and an alarm requires **strictly greater than 0.5**. The Ridge output is an unbounded regression score, not a probability. If neither expert observes a target, all arms force its final score to zero while retaining the row in the denominator. Original calibrated native-control thresholds remain separate descriptive controls and were not selected anew for these policies. [Ridge objective and solver documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.Ridge.html); [PX083 source](../../px083_policy_transfer/run.py), lines 74–129.

Two fits generate evaluations of seven arms across 21 perturbation views per dataset: 294 tables in total. The 21 views comprise 15 conditions, with repeated random-loss seeds; these are not 21 datasets or three new Ridge fitting seeds. Original native models were fitted with scikit-learn 1.9.0; the new Ridge selectors use 1.7.2. PX083 consumes previously saved probabilities and does not reload those older classifiers for new inference. This implementation audit likewise used their stored attributes only; it did not recompute cross-version predictions.

## 7. Implemented versus proposed approaches

| Approach | Status in PX080–PX083 |
|---|---|
| LightGBM four-class experts and regression selectors | Fitted in the main experiments |
| Fixed averaging, confidence gates and fixed acquisition order | Evaluated decision rules; no extra model fit |
| Missing-history and record-loss augmentation | Implemented comparator training, as specified above |
| Ridge score-policy transfer | Two supplementary fits on T1105 |
| TabM, GNN/graph-machine-learning architecture, Qwen or another LLM | Not fitted or evaluated in this batch |
| New warning-destination loss or a guard against attack-to-benign changes | Possible future work; no performance result claimed |
| SEFA, Learning-to-Measure, reinforcement-learning planner | Literature context or proposed direction; not reproduced algorithms in these runs |

## 8. Corrections and qualifications for the final manuscript

1. Replace “classifier trees” with **boosting iterations** in configuration tables. Do not equate multiclass iteration counts with total trees.
2. Describe **stage-cost regression responses** and unweighted base experts. “Class-weighted LightGBM classifier” would misstate the implementation. The only main classifier sample weights are 0.5 per augmentation copy in the PX080 comparator.
3. Keep the two response signs straight: history uses context-minus-current loss and chooses negative; acquisition uses before-minus-after loss and requests positive gain.
4. Describe availability priors as supplied by the simulated regime. No learned deadline-success model, hard statistical protection, calibrated risk estimator, or optimal sequential planner was implemented.
5. Distinguish feature-loss augmentation from neural/tree dropout and distinguish forward-held-out fitting from independent confirmation.
6. Report T1105 transfer separately: two Ridge fits, reused balanced logistic experts, different negatives and annotation units, no native-classifier transfer.
7. Retain exact software provenance: LightGBM 4.6.0, main/new-selector scikit-learn 1.7.2, earlier cached native logistic models scikit-learn 1.9.0. The original source and saved probability receipts remain authoritative for reproducing the different stages.

## 9. Verified primary references and locators

The following APA-style entries support model descriptions, not claims of praxis novelty. Versioned documentation has no asserted publication date; retrieval was September 24, 2026. The LightGBM paper is foundational even though the praxis literature-gap review emphasizes newer application studies.

**Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017).** LightGBM: A highly efficient gradient boosting decision tree. In *Advances in Neural Information Processing Systems* (Vol. 30). Curran Associates. [Official proceedings](https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html). Locator: paper Section 2.1, PDF page 2, for sequential gradient-boosted trees and histogram representation. Sections 3–4 describe GOSS/EFB; citing the paper does not mean this experiment selected GOSS.

**LightGBM developers. (n.d.-a).** *Features* (Version 4.6.0 documentation). Retrieved September 24, 2026, from [official documentation](https://lightgbm.readthedocs.io/en/v4.6.0/Features.html). Locators: “Optimization in Speed and Memory Usage” and “Leaf-wise (Best-first) Tree Growth.”

**LightGBM developers. (n.d.-b).** *lightgbm.LGBMClassifier* (Version 4.6.0 documentation). Retrieved September 24, 2026, from [official API](https://lightgbm.readthedocs.io/en/v4.6.0/pythonapi/lightgbm.LGBMClassifier.html). Locators: constructor parameters `objective`, `class_weight`, `reg_lambda`; properties `n_estimators_` and `objective_`; `predict_proba`.

**LightGBM developers. (n.d.-c).** *lightgbm.LGBMRegressor* (Version 4.6.0 documentation). Retrieved September 24, 2026, from [official API](https://lightgbm.readthedocs.io/en/v4.6.0/pythonapi/lightgbm.LGBMRegressor.html). Locator: `objective` default and constructor settings. The regression objective's L2 meaning is also explicit in *Parameters*, `objective`.

**LightGBM developers. (n.d.-d).** *Parameters* (Version 4.6.0 documentation). Retrieved September 24, 2026, from [official parameter reference](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html). Locators: `objective`, `num_iterations`, `boosting`, `data_sample_strategy`, `deterministic`, `force_col_wise`, `device_type` and `early_stopping_round`.

**Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011).** Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*(85), 2825–2830. [Official JMLR record](https://jmlr.org/papers/v12/pedregosa11a.html). Locator: official article metadata for authors, year and pages; this is the software citation, not the source of experiment-specific settings.

**Scikit-learn developers. (n.d.-a).** *LogisticRegression* (Version 1.9 documentation, displayed as 1.9.1 at retrieval). Retrieved September 24, 2026, from [official API](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.LogisticRegression.html). Locators: `C`, `l1_ratio`, `class_weight`, `solver`, and the `penalty` deprecation note. The archived models' receipts specify 1.9.0; the online documentation's patch version is not substituted for that recorded version.

**Scikit-learn developers. (n.d.-b).** *Ridge* (Version 1.7.2 documentation). Retrieved September 24, 2026, from [official API](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.Ridge.html). Locators: objective directly below class definition; `alpha`, `fit_intercept` and `solver='svd'`.
