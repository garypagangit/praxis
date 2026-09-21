# E3: bounded label-noise treatment pilot

## What this tests

Can a training-label treatment recover stage-classification performance after artificial training-label errors, without damaging clean performance or the rare InitialCompromise stage? This is a development screen on the acquired SCVIC **training CSV**, using its fixed feature-deduplicated split. It is not the author's test set, an independent-incident test, or a test of actual annotation repair. Original dataset labels are assumed correct solely to score the controlled corruption.

The complete executable settings and gates are frozen in [protocol_e3.json](protocol_e3.json). The runner creates a pre-fit receipt containing code, protocol, input and environment hashes. It refuses to run until that receipt exists and still matches. This document itself does not report a model outcome.

## Relation to the proposed Gradients experiment

The grounding is Eisenbürger et al., [*Training Gradient Boosted Decision Trees on Tabular Data Containing Label Noise for Classification Tasks*, arXiv 2409.08647v2](https://arxiv.org/html/2409.08647v2). An authoritative implementation and all algorithm details were not verified. Consequently, the tested methods are explicitly named **history-gradient GMM removal adaptation** and **history-gradient GMM relabeling adaptation**. Their results must not be described as a reproduction, confirmation or refutation of the original Gradients algorithm. The existing [literature review](LITERATURE_VALIDITY.md) records the paper's scope and cautions.

The following are our frozen implementation choices, not inferred claims about unspecified author code:

- Use multiclass post-update residuals `p[k] - 1[k == assigned_label]`; average their maximum absolute value over five rounds. This is a bounded historical error score; it does not establish that a difficult example is mislabeled.
- Train 15 rounds before treatment, then intervene every five rounds. Fit a two-component Gaussian mixture on the active examples' scores. Candidate examples have posterior probability greater than 0.5 of belonging to the higher-mean component. Degenerate score distributions receive no treatment.
- For removal, consider candidates in descending score order, retain at least one example of each currently assigned class, and remove at most 80% of the original fit subset. This floor uses observed training labels, never hidden correct labels.
- For relabeling, change each candidate at most once to its five-round mean-probability argmax, and only if the proposed label differs. Clear history after intervention. Final-round treatment is prohibited because it would not affect training.
- Use exactly 100 boosting rounds for every arm, depth 3 and learning rate 0.1, with no tuning or early stopping. These differ from the source paper's settings. Calibration records are unused in E3, leaving their role in the separate E4 evaluation explicit.

The 80% removal ceiling is permissive and may harm rare or difficult valid examples. A favorable result requires clean/rare-stage guards as well as recovery under injected noise. A negative result applies to this adaptation and protocol.

## Fixed data and comparisons

Three seeds select up to 256 available fitting examples per original class by a deterministic hash. InitialCompromise has only 43 fit examples; all other classes supply 256. Therefore each seed trains on 1,323 examples, and this is an unequal realized class budget. The full fixed test split contains 30,787 rows, including 15 InitialCompromise examples. Exact duplicates have been removed, but correlations between different flows can remain.

For each seed, all arms receive the same fitting subset and corrupted labels. Conditions are 0% corruption and 20% symmetric corruption. The latter changes exactly `floor(0.2 * 1323) = 264` labels to a randomly chosen different class. The three arms are no correction, removal adaptation and relabeling adaptation: **18 fits total**.

The fitting function receives only features, observed training labels, model/settings and seed. It receives no noise rate, clean labels, corruption mask, calibration data or test data. Hidden labels are supplied only after training to measure candidate/treatment precision, recall, clean-example damage and retained corrected labels. All treatment traces and predictions are saved for independent checking.

The no-correction arm uses the same XGBoost settings and fixed round count. This controls fitting duration in boosting rounds; it does not make the smaller post-removal training sets identical in total computation. No cleaner gets additional validation information.

## Frozen screening decision

For the same treatment arm, the mean of its three paired seed differences from no correction must satisfy all four conditions:

1. Under 20% corruption, macro-F1 gain is at least 0.02.
2. With 0% corruption, macro-F1 loss is no greater than 0.01.
3. With 0% corruption, InitialCompromise recall loss is no greater than 0.05.
4. Under 20% corruption, InitialCompromise recall loss is no greater than 0.05.

Both arms are reported regardless of outcome. A passing arm is a **promising development result**, not a significance claim or guaranteed praxis contribution. Seeds reuse one test population; no independent-population confidence intervals are computed. A failed guard cannot be rescued by a secondary metric or a later parameter change on this test split.

## Running

Use the isolated CPU environment with XGBoost 2.1.4. The first command validates artifacts and creates the receipt without fitting. After the receipt/protocol are saved for review, the second starts the bounded run. Paths below keep models and per-example predictions private.

```powershell
& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' -m experiments.apt_benchmark.tabular_batch.run_e3 --output 'C:/w/apt_benchmark_data_20260920/tabular_batch_v1/e3_run1' --freeze-only
& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' -m experiments.apt_benchmark.tabular_batch.run_e3 --output 'C:/w/apt_benchmark_data_20260920/tabular_batch_v1/e3_run1' --run
```

`RESULTS.json`, `SUMMARY.json` and `REPORT.md` are aggregate outcomes. Private prediction archives include held-out probabilities and post-hoc training-label audit state. A run that has started cannot be overwritten; a code/protocol/input change requires a new receipt/output and an explicit amendment.

CPU is appropriate for this small tree pilot; the user's AWS GPU request is handled by the separate foundation-model work. This module never starts AWS resources.
