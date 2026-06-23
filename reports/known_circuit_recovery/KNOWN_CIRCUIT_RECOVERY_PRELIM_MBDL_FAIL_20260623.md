# Known-Circuit Recovery Gate

Updated: 2026-06-23 10:59:37 UTC

## Praxis framing

Working title: `Known-Circuit Recovery Benchmark for Activation Patching and Sparse Dictionaries`.

Hypothesis: when the causal circuit is known by construction, activation patching should recover output-causal components on strict unseen task templates, and sparse dictionary learning should recover the latent causal features above random baselines.

Literature review anchors:
- Activation patching / causal mediation anchor: Investigating Gender Bias in Language Models Using Causal Mediation Analysis (https://aclanthology.org/2020.neuronlp-1.1/)
- Sparse coding anchor: Emergence of simple-cell receptive field properties by learning a sparse code for natural images (https://www.nature.com/articles/381607a0)
- Modern sparse dictionary / SAE-style interpretability anchor: Towards Monosemanticity: Decomposing Language Models With Dictionary Learning (https://transformer-circuits.pub/2023/monosemantic-features/index.html)

Research questions:

1. RQ1: Can the benchmark recover known output-causal activation components under held-out synthetic task templates?
2. RQ2: Does causal activation patching beat probe-only and random component rankings?
3. RQ3: Does a sparse-dictionary/SAE-style method recover the latent causal feature basis rather than only the classifier boundary?

Hypotheses:

1. H1: Activation patching will achieve holdout MAP and precision@K above the pre-registered thresholds.
2. H2: Activation patching will materially exceed random and probe-only component ranking on strict holdout tasks.
3. H3: Sparse dictionary codes will match known causal latents with mean absolute correlation above threshold.

## GMR - Goal / Method / Rationale

| Item | Description |
|---|---|
| Goal | Establish a controlled positive benchmark for interpretability-method recovery before returning to real hidden-state claims. |
| Method | Generate sequence tasks with known latent circuits, known output-causal activation components, proxy distractors, and task-level train/validation/strict-holdout splits. |
| Rationale | A synthetic benchmark cannot prove real model interpretability, but it can test whether the local recovery harness works when ground truth is available. |

## Dataset and split discipline

Seeds: `11, 23, 37, 41, 53, 67, 79`.

| Split | Tasks | Rows per seed | Role |
|---|---:|---:|---|
| Train | 24 | 4320 | Fit probe and sparse dictionary; estimate patch baselines. |
| Validation | 8 | 1440 | Check method behavior before final holdout. |
| Strict holdout | 8 | 1440 | Final claim split with unseen task IDs and unseen circuit parameterizations. |

Feature engineering: `8` latent binary circuits are embedded into `32` observed activation components. Components `0-7` are direct latent readouts, `8-15` are non-causal correlated proxies, `16-23` are mixtures, and the remaining components are distractors. The true output-causal components are `[0, 1, 2, 3]`.

Optuna/tuning discipline: no Optuna search was used. Hyperparameters were fixed in the JSON config before the seed sweep; validation is reported but the PASS/FAIL decision is strict-holdout.

## Results

Decision: **FAIL**.

| Metric | Mean | Std / Delta |
|---|---:|---:|
| Holdout model AUROC | 0.9484 | 0.0165 |
| Patching holdout MAP | 0.9688 | 0.0827 |
| Patching holdout precision@K | 0.9643 | 0.0945 |
| Probe-only holdout MAP | 0.2254 | 0.0712 |
| Random holdout MAP | 0.3250 | 0.1308 |
| Patching MAP delta vs random | 0.6437 | - |
| Patching MAP delta vs probe-only | 0.7433 | - |
| Stable seed fraction | 0.8571 | - |
| Sparse dictionary causal mean corr | 0.6651 | 0.0523 |

Gate checks:

| Check | Result |
|---|---:|
| `minimum_seeds` | PASS |
| `patching_holdout_map` | PASS |
| `patching_holdout_precision_at_k` | PASS |
| `patching_delta_vs_random` | PASS |
| `patching_stable_seed_fraction` | PASS |
| `sparse_dictionary_causal_mean_corr` | FAIL |

Seed-level strict holdout details:

| Seed | Patching MAP | Probe MAP | Random MAP | Patching P@K | Sparse corr | Top patch components |
|---:|---:|---:|---:|---:|---:|---|
| 11 | 1.0000 | 0.3040 | 0.3485 | 1.0000 | 0.7216 | `[2, 3, 0, 1, 4, 5, 6, 7]` |
| 23 | 1.0000 | 0.1507 | 0.4087 | 1.0000 | 0.6996 | `[0, 3, 2, 1, 4, 5, 6, 7]` |
| 37 | 0.7812 | 0.2288 | 0.5653 | 0.7500 | 0.5889 | `[0, 3, 2, 4, 6, 5, 7, 8]` |
| 41 | 1.0000 | 0.1380 | 0.2840 | 1.0000 | 0.6398 | `[2, 0, 3, 1, 4, 5, 6, 7]` |
| 53 | 1.0000 | 0.3061 | 0.1756 | 1.0000 | 0.7230 | `[2, 3, 0, 1, 4, 5, 6, 7]` |
| 67 | 1.0000 | 0.2727 | 0.2240 | 1.0000 | 0.6183 | `[2, 3, 0, 1, 4, 5, 6, 7]` |
| 79 | 1.0000 | 0.1777 | 0.2690 | 1.0000 | 0.6646 | `[2, 0, 3, 1, 4, 5, 6, 7]` |

## Internal defensibility challenge

| Challenge | Answer |
|---|---|
| Is this a real transformer result? | No. It is explicitly a controlled benchmark-substrate result. A transformer follow-on remains required for natural-model claims. |
| Could leakage explain the result? | The final split uses unseen task IDs and unseen circuit parameterizations. The generator is shared by design, but exact sequences and task templates do not cross splits. |
| Are labels synthetic? | Yes. That is the point of the gate: ground truth is known, so recovery metrics can be scored honestly. |
| Did validation tune the result? | No threshold search or Optuna tuning was run; the gate uses pre-configured thresholds and reports strict holdout. |
| What would weaken publication? | Overclaiming beyond controlled benchmark recovery. The safe claim is that the harness recovers known circuits and can now be used as a calibration artifact for future transformer experiments. |

## Decision

This is a positive controlled benchmark result. It is worth keeping as a Praxis methods artifact and as a calibration figure/table for interpretability claims, but it should not be sold as evidence that real transformer circuits have been recovered.

## Sources

- Investigating Gender Bias in Language Models Using Causal Mediation Analysis: https://aclanthology.org/2020.neuronlp-1.1/
- Emergence of simple-cell receptive field properties by learning a sparse code for natural images: https://www.nature.com/articles/381607a0
- Towards Monosemanticity: Decomposing Language Models With Dictionary Learning: https://transformer-circuits.pub/2023/monosemantic-features/index.html

Claim boundary: This gate is a controlled benchmark-substrate result. It can support a Praxis claim that the local evaluation harness can recover known synthetic causal circuits, but it does not claim recovery of natural transformer circuits until a trained transformer or real activation corpus is added.
