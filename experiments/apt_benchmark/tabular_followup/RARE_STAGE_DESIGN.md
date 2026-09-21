# Protecting rare attack stages at a fixed review budget

Design review: September 21, 2026. This follow-up was designed after the earlier development results were known, before evaluating this routing policy. No prediction outcomes were inspected to choose its scores or thresholds during this review. It is an empirical adaptation of established methods; algorithmic novelty is not established.

## Recommendation

Test one fixed, two-channel review gate. A general attack channel catches strongly suspicious flows; a second channel lets either a foundation model or a tree model request review when it sees evidence for InitialCompromise or DataExfiltration. Allocate half of a nominal 1% benign-routing budget to each channel. Calibrate the channels using existing benign examples, avoiding threshold tuning on only 14 initial-compromise examples.

The question is whether complementary predictions recover rare dangerous cases at a useful workload. Being sent to review is **not** correct stage identification, successful human adjudication, actor attribution, or early attack detection.

## Literature and the novelty boundary

| Primary source | Verified finding and implication |
|---|---|
| Zöller & Lawall (2026), *Reliable Intrusion Detection via Conformalized Tabular Foundation Models*, [official IEEE CSR program](https://www.ieee-csr.org/2026-conference-program/). | The accepted paper establishes direct topic overlap. Full paper not obtained; exact protocol and results remain unverified. Its author's [presentation account](https://www.linkedin.com/pulse/at%C3%A9-%C3%A0-pr%C3%B3xima-lisboa-dr-thomas-z%C3%B6ller-bccte) describes TabPFN with conformal prediction. Do not claim first conformalized TFM intrusion detector. |
| De Melo Costa, Popineau, Rimmel, & Doan (2026), *High Performance, Low Reliability: Uncertainty Benchmarking for Tabular Foundation Models*, [ESANN proceedings](https://www.esann.org/sites/default/files/proceedings/2026/ES2026-261.pdf), doi:10.14428/esann/2026.ES2026-261. | Across 112 tabular datasets, the authors compare prediction performance and LAC uncertainty, finding weaker size-stratified coverage for TFMs than boosted trees. Their conditional diagnostic is **set-size conditional**, not a demonstrated APT-stage guarantee. This motivates testing complementary families but does not predict a positive result here. |
| Ding, Angelopoulos, Bates, Jordan, & Tibshirani (2023), *Class-Conditional Conformal Prediction with Many Classes*, [NeurIPS paper](https://papers.neurips.cc/paper_files/paper/2023/file/cb931eddd563f8d473c355518ce8601c-Paper-Conference.pdf). | Clustered calibration already addresses scarce per-class labels. Pooling similar classes is not a new idea, and with six stages it requires evidence that pooling is sensible. We do not spend scarce labels learning clusters in this pilot. |
| Ding, Fermanian, & Salmon (2025), *Conformal Prediction for Long-Tailed Classification*, [author preprint](https://arxiv.org/abs/2507.06867). | Prevalence-adjusted scores and interpolation between marginal and classwise calibration already target rare-class coverage versus set size. Reweighting rare stages or shrinking thresholds alone is not a defensible novelty claim. |
| Singh, Srikantha, & Lakhanpal (2026), *Cost-Sensitive Conformal Prediction and Human-in-the-Loop Abstention for Imbalanced High-Stakes Decision Support*, [July preprint](https://arxiv.org/abs/2607.27143). | This preprint combines class-conditional sets and cost-based deferral across imbalanced tabular tasks. Its peer-review status is unverified; the overlap still rules out presenting Mondrian-plus-review as an unexplored general mechanism. We do not adopt its claimed effect sizes or human-oracle assumptions. |
| Tong, Feng, & Li (2018), *Neyman-Pearson classification algorithms and NP receiver operating characteristics*, [author manuscript](https://jsb-lab.org/wp-content/uploads/2018/02/ScienceAdvances_eaao1659.full_.pdf), doi:10.1126/sciadv.aao1659. | Prioritized error control and calibrated score thresholds are established. The present simple upper-tail rule is not claimed to implement their high-probability NP certificate. An empirical false-alarm target alone is not such a certificate. |

**Potential applied contribution, conditional on results:** an explicit measurement of the rare-stage protection/workload trade-off from complementary model families under severe stage-label scarcity. A stronger praxis still needs independent incident/temporal or author-holdout validation and a fuller prior-art comparison. This development dataset cannot establish those claims.

## Frozen policy specification

Use the existing six-class E1 probability arrays, identical 192-row fitting supports, all ten seeds, full calibration and development-test partitions. For each seed, select XGBoost versus LightGBM using the original fitting-only inner-CV score, ties to XGBoost. Do not choose TabICL versus TabPFN using outcomes: TabICL is fixed. Missing full TabICL calibration/test probabilities make the run incomplete; the enriched CPU prescreen is not a substitute.

For model m and rare stage k, define `r_mk = p_m(k)/(p_m(k)+p_m(NormalTraffic)+1e-12)`.

- Common score: `1-p_TabICL(NormalTraffic)`.
- Rescue score: maximum `r_mk` over the two fixed rare stages and the two selected model families.
- For each score, compute its threshold on benign calibration rows only, using ascending order statistic `ceil((n+1)*(1-alpha))`, with alpha=.005. Use positive infinity when the rank exceeds n. Route if score is **strictly greater** than threshold; ties are not routed.
- Candidate review flag: common-channel OR rescue-channel. The joint maximum is calibrated once; do not mistakenly treat its four components as separately calibrated tests.
- Both component thresholds and the 50/50 allocation are fixed. No calibration-label search for better rare-stage thresholds, no test tuning, and no post-result budget search.

Under ideal within-benign exchangeability, the finite-sample tail construction has a marginal interpretation and the union bound explains allocating .005+.005. The present flow split does not establish those assumptions. Report **nominal budget and empirical test burden**, never guaranteed future false-positive or attack-miss ceilings.

## Mandatory controls and diagnostics

1. TabICL `1-p(NormalTraffic)` with nominal benign upper tail .01.
2. Inner-CV-selected GBDT `1-p(NormalTraffic)` with the same .01 rule. The candidate must beat **both fixed controls**, avoiding selection of a conveniently weak comparator.
3. The identical two-channel gate with TabICL alone in the rescue maximum. This separates the value of the second model from score engineering; diagnostic, not an extra winning opportunity.
4. Established class-conditional LAC at nominal 90% and 95% for each model. Publish per-class coverage and set size. For routing, automatically clear only the exact singleton `{NormalTraffic}`; send every other set, including an empty set, to review. This mapping is deliberately explicit: informative coverage and low workload are separate outcomes. These set methods do not share the 1% false-alarm operating point; report that cost rather than treating unequal burden as a fair detection victory.

## Success criteria, costs, and interpretation

Primary result is the mean over ten seeds of `min(InitialCompromise routing recall, DataExfiltration routing recall)`. Require a gain of at least .05 against **each** fixed single-model control, mean routing-recall loss no greater than .05 for **any of the five attack stages** against either control, and candidate benign routing FPR at most .015 in **every seed**. Report every seed, absolute counts, all stage recall, precision of the review queue, total review fraction, and additional common-only/rescue-only/overlap routing. All gates are needed; missing pairs remain incomplete. Seeds reuse examples and are not independent incidents. No significance claim or oracle-corrected F1.

The input manifest records 29,929 benign calibration labels, 14 InitialCompromise and 105 DataExfiltration calibration labels; the full calibration pool has 30,782 labels. Gate thresholds use only benign membership, whereas the conformal controls use all calibration stage labels. The 192 model-fitting labels are shared between the two models, not 384 unique examples per seed. Existing fitting-only CV consumes no additional labels. Report calibration and fitting labels separately; this is not a 192-total-label operational system. No new human labeling or model fit is needed, but future real review effort has not been measured.

With 14 InitialCompromise calibration examples, nominal 90% classwise LAC uses rank14, the maximum observed score. At 95%, rank15 is unavailable: its threshold is infinity and InitialCompromise is included for **every** input. This does not necessarily make the entire set full, but the stated protective routing rule reviews every input. Do not clip the infinite threshold or force singleton sets. Even zero misses among 14 independent positives would leave a one-sided 95% binomial upper miss bound of about19.3%; at least59 independent positives with zero misses would be needed to put that bound below5%. These illustrative counts do not establish independence here.

InitialCompromise test support is15, DataExfiltration106; one initial-compromise case changes recall by6.67 percentage points in a seed. The full test has30,787 rows. At the empirical1.5% benign-FPR ceiling, even routing every attack would imply at most approximately4.25% total review on this particular class mix. Deployment prevalence and analyst time can differ.

## Execution discipline

Freeze the JSON protocol and runner before any policy outcomes. Bind full E1 prediction artifacts through the independent E1 analyzer; verify class order, labels, splits, fitting supports, CV and hashes. Save calibration thresholds, source receipts and per-example routing flags privately. Run the policy without refitting or prediction inference. Prior E1 and CPU prescreen outcomes are already known, so this remains a prospective **development follow-up policy test**, not an untouched confirmation dataset.
