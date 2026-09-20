# S-DAPT-2026: candidate intake and evaluation plan

Checked September 20, 2026. **Added to the experiment registry; data are not yet evaluation-ready and no model has been run on this dataset.** The complete machine-readable plan is [EVALUATION_PLAN.json](EVALUATION_PLAN.json).

## Source status

Tijjani, Ghita, Clarke and Craven submitted the January 10 preprint. The [current arXiv record](https://arxiv.org/abs/2601.06690) marks it withdrawn on April 1, 2026 because analysis errors affected the conclusions. The [companion E-HiDNet paper](https://arxiv.org/abs/2601.06734) was also withdrawn. A [later SSRN posting dated April 18](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942), DOI 10.2139/ssrn.6603942, exists; its correction status and peer review were not verified. Full SSRN retrieval returned HTTP 403.

The [historical January manuscript](https://arxiv.org/html/2601.06690v1) describes 120,000 synthetic alerts and names raw and preprocessed CSVs. **These are paper-reported properties, not counts from acquired files.** A downloadable author-controlled artifact and dataset license were not located in the checked primary pages or exact-name/file-name searches. The paper's publication license must not be substituted for a dataset license. No claim is made that the data do not exist elsewhere.

## Where it could help our ideas

These are proposed uses conditional on acquiring and qualifying the source, not demonstrated capabilities or novelty claims.

| Idea | Fit | Useful experiment |
|---|---|---|
| Current missing/delayed-evidence question | Good controlled alert-level test | Remove or delay whole alerts or named alert classes and measure stage recognition at fixed deadlines. This models loss after detection, not missing raw Linux records. |
| Earlier warning and stage progression | Good if campaign membership and times are valid | Predict a later, not-yet-observed stage from an observed prefix; count missed campaigns and warnings before source-defined exfiltration. Test against simple transition/HMM controls. |
| Original graph-ML direction | Conditional | Construct edges from visible host relationships and time, then compare a simple mutual-kNN graph with incremental graph/state models under missing evidence. Ground-truth campaign IDs cannot construct the input graph. |
| CTI factuality/checker experiments | Weak direct fit | It does not establish claim-to-document evidence, source reliability, or factual contradictions needed by the CTI checker. |
| Qwen/LLM substitution | Optional baseline, weak novelty by itself | Compare on the same observed alerts and context budget only after type lookup, linear and probabilistic controls. A model name is not a contribution. |

## First qualification checks

1. Obtain the authoritative raw CSV and generator/configuration, a version or checksum, terms of use, and clarification of which release corrects the withdrawn analysis. Use the [prepared request](DATA_REQUEST.md); it has **not been sent**.
2. Verify actual headers, row counts, alert types, stage meanings, timestamps, campaign groups and generator seeds against the source. The historical text has inconsistent alert names/stage descriptions; do not silently invent a mapping to reconcile them.
3. Test whether current stage is determined by alert type alone. Such a lookup is a mandatory control. High accuracy reproducing that mapping would not show that a model understands hidden campaign progression.
4. Keep labels, campaign IDs, correlation indices, full-sequence summaries and future stages out of predictor inputs. Check whether `infected_host` is observed alert metadata or generator-only ground truth before using it even for joins. Missing campaign identifiers may themselves reveal class membership.
5. Split whole generator campaigns/realizations and templates, not random rows. Shared hosts, templates and duplicate sequences must be grouped or explicitly disclosed. Missing IDs for background records do not supply independent grouping automatically.
6. Recompute any legitimate time/context features using only records available at the decision deadline. Fit preprocessing on training data only. Keep hidden targets in denominators; do not relabel a campaign after deleting its evidence.

## Proposed evaluation sequence

| Gate | What to run | What it can establish |
|---|---|---|
| S0: Shortcut audit | Majority/type lookup, source-identity and forbidden-field diagnostics, then a clean prefix-only linear model | Whether there is a nontrivial inference task rather than recovery of generator rules or labels embedded in inputs. |
| S1: Missing alerts | Event/history controls, random dropout and alert-type dropout; test 25%, 50%, 75% random loss and whole-type absence | Sensitivity to different information-loss mechanisms. Pair corruption seeds and keep clean-calibrated thresholds fixed. |
| S2: Delayed progression | Immediate predictions, bounded buffering and past-only HMM filtering at matched deadlines | Whether partial observations support useful progression estimates without future-aware smoothing. Derive delay scales from training timelines before freezing them. |
| S3: Graph contribution | Observed-edge mutual-kNN baseline, an equal-history sequence model and the proposed graph modification | Whether the graph mechanism adds value beyond matching evidence, parameter budget and observability. |

Report macro/per-stage F1, precision, recall, one-vs-rest ROC-AUC and average precision where classes are supported, coverage/abstention, false-stage claims, campaign-level warning delay and missed/censored campaigns where onset and impact are qualified. Keep synthetic alert results separate from AIT/Casino audit-event results. Recheck on qualified CAM-LDS or another independent source before claiming operational benefit.

## Praxis recommendation

Use S-DAPT, if qualified, as a controlled stress-test supplement. The immediate strong question comes from our real Casino measurements: random-dropout training helps random loss but can fail when a particular record type disappears. Stage-aware handling of incomplete evidence is a plausible research direction; ordinary HMMs, missing-input training, buffering and kNN alert correlation are existing ideas. The withdrawn E-HiDNet manuscript also proposed inference with incomplete observations, so this territory cannot be called unexamined. Its withdrawn performance claims are not validated baselines.

Until corrected provenance and raw files are available, keep CasinoLimit/AIT as completed evidence and CAM-LDS as the primary recent-data confirmation candidate. No synthetic replacement has been generated and labeled as the authors' S-DAPT-2026.
