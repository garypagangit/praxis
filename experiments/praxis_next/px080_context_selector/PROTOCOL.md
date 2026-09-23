# PX-080 — Learn when historical context harms an attack-stage decision

## Frozen development pilot

This is a new method-development experiment on the previously exposed UNRAVELED single-campaign preparation, **not independent confirmation**. It uses 382,229 qualified author-labeled rows. The later-period evaluation contains 35 lateral-movement and 3,442 exfiltration labels; movement here means the author's progress annotation (Remote System Discovery), not independently verified successful movement. No forecast or pre-exfiltration warning is measured: current predictors summarize completed flows.

The narrower research question is whether a selector trained on the incremental stage error from using context outperforms fixed fusion and ordinary learned gating when context is absent, stale, or incorrectly linked. Generic expert fusion is not a novelty claim.

## Inputs and chronology

The read-only input is `C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz`, SHA256 `b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14`. Its upstream parser, label and split limitations remain binding. All stage labels are preserved.

Original captures 0–4 are fitting data, capture 5 is unused calibration data, and captures 6–10 are final descriptive evaluation. Selector targets come exclusively from four forward folds: train on captures earlier than 1 and score capture 1, then earlier than 2/score 2, earlier than 3/score 3, and earlier than 4/score 4. Require every fitting end time to precede the earliest validation start. Fit/cross-fit caps per class are 20,000 benign and 5,000 each other class, chosen using observable-event hashes and seed. Selector fitting takes at most 12,000 benign and 5,000 each other class per validation capture, also hash-selected. Model selection never examines capture 5 or later labels.

## Models, selectors, fixed comparisons

Seeds are 20260924, 20260925 and 20260926; no hyperparameter search. Base learners are LightGBM classifiers: 180 trees, 15 leaves, learning rate .05, minimum child count 10, L2=1, four threads. They receive current numeric flow summaries and coarse source/destination roles equally. The context expert additionally receives 36 history summaries, age of the newest historical event, and an explicit history-channel availability indicator. Literal endpoints, timestamps, capture IDs, target labels and future evidence are never predictors. Age is a relative observable duration, not a date.

Selector regressors use 120 trees, 7 leaves, learning rate .05, minimum child count 30, L2=5. Inputs are the two experts' four-class probability vectors, differences, confidence/margin/entropy, the relative history age and channel availability. They do not receive scenario/condition identity. The ordinary selector predicts the difference between context and current 0/1 errors. The proposed selector predicts that difference multiplied by a true-class training cost: benign=1, other=1, movement=4, exfiltration=4. These costs are design choices, not literature requirements. At inference, both selectors choose context only for a strictly negative predicted difference; labels are unavailable. The costs shape training rather than granting any protection guarantee.

Seven arms: current+roles; context expert; 50/50 probability fusion; choose the more confident expert (ties current); ordinary learned selector; stage-harm selector; and a context classifier trained with missingness/dropout (clean and deterministically half-missing copies, half weight each). This last classifier uses the same availability and age inputs. All are evaluated and retained regardless of direction.

## Conditions

1. Clean historical evidence.
2. Deterministically 50% of history channels absent, zeroed with explicit unavailable flag.
3. All history absent, zeroed with explicit unavailable flag.
4. Five-minute stale snapshot, rebuilt from observable flows with query time `current_start - 300000`; no event finishing at or after that cutoff contributes. Age remains measured relative to the current start.
5. Hidden wrong-host history from the upstream past-only deterministic donor; availability remains present, and no explicit corruption flag is supplied.

Selector supervision includes clean, half-missing and stale versions of forward-fold rows; the same supervised examples are used for the ordinary and proposed selector. Wrong-host linkage and all-missing are evaluation conditions. Interventions are simulated replay, not measured production outages or verified dataset label changes. The clean later period also contains the already-known department-to-private-service role change; report it separately without adapting to it.

## Outcomes and interpretation

Retain row-linked private probabilities for every seed, arm and condition. Public outputs contain confusion matrices, four-class macro F1, each stage's precision/recall/F1/AP/ROC AUC, movement any-attack recall, normal false-attack counts, descriptive stage-weighted error, selector-use fractions and context-harm/help counts. Also publish capture and role-shift strata. No threshold optimization, selective reporting, row-independent confidence intervals or seed-based population confidence intervals. The three seeds measure fitting variability on the same events.

A useful candidate should improve stage-sensitive decisions against ordinary gating and dropout while displaying its false-alarm costs. Mixed or negative outcomes will be published. This pilot cannot certify missing-information recovery, causal prevention, independent-campaign generalization, successful theft recognition, or algorithm novelty. Source/protocol/dependency hashes must be recorded before fitting and checked at run start. The root agent records the Git freeze before the run.
