# Testing the proposed tabular APT research batch

This batch evaluates the user's E0–E7 proposal. A proposal is not evidence of a positive result or novelty. The registered experiments can fail, and the results must retain all registered arms and seeds.

## Frozen first experiments

- **E0:** qualify source files, labels, feature leakage, duplicates and usable splits. [Dataset decision](E0_DATASET_GATE.md).
- **E1:** compare TabICL v2 and explicitly pinned synthetic-only TabPFN 2.5 against tuned XGBoost/LightGBM and Random Forest. Use 32 fitting labels per class, ten common training subsamples, and one fixed deduplicated SCVIC development test partition. The primary candidate is fixed as TabICL; GBDT selection uses training-only cross-validation. [Protocol](protocol.json).
- **E3:** compare untreated XGBoost with two explicitly adapted gradient-history/GMM treatments under 0% and 20% injected training-label noise, with three common fitting subsamples. This is a bounded pilot, not a reproduction of the published Gradients method or the proposal's full corruption grid. [Protocol](protocol_e3.json), [method](METHODS_E3.md).
- **E4:** reuse E1's separate calibration and test probabilities to assess prediction-set coverage and size. There is no guaranteed positive outcome, no certification under arbitrary dataset shift, and no unseen-stage miss guarantee. [Implementation](conformal.py).

Only the author's SCVIC training CSV is presently qualified. Exact-feature deduplication and removal of identifiers, timestamps, ports and malformed Idle features precede partitioning. The available rare class supports 32/class, not the requested 64–1,024/class budgets. Results on this development split cannot establish independent-incident, chronological, early-warning or author-holdout performance. The 15 InitialCompromise test examples make that recall estimate especially fragile.

## Literature and remaining experiments

[Foundation-model literature check](LITERATURE_FOUNDATION.md) and [validity check](LITERATURE_VALIDITY.md) document direct prior art. Broad foundation-model IDS, the proposed hybrid screening pipeline, conformalized foundation-model IDS and GRANDE security use are already represented in primary literature. An APT-specific evaluation may still be useful; a defensible new contribution remains to be demonstrated.

E2 requires a separately frozen, measured end-to-end binary screening experiment on common hardware; timing unlike devices or reusing precomputed scores would not test the proposed speed claim. E5 as proposed requires unavailable qualified S-DAPT data and cannot guarantee a missed-unknown-stage bound merely by adding conformal prediction. E6 lacks qualified scenario sequences and a corrected downloadable data release. E7 is an optional additional model comparison, not a first security application.

## Execution and evidence

`run_e1.py` writes a pre-fit receipt before fitting, then immutable per-model/per-seed prediction artifacts and completion hashes. Separate CPU and GPU arms can be compared only when their data, protocol, code and fitting-support bindings match. `analyze_e1.py` independently verifies and recomputes E1/E4 outcomes. Incomplete primary comparisons cannot pass.

`run_e3.py --freeze-only` creates the pre-fit receipt; `--run` requires unchanged code, protocol, data and package versions. Source calibration labels are unused for E3. Its clean-label corruption mask is available only to post-hoc evaluation, never to a treatment learner.

Raw data, row-level predictions, checkpoints and private cloud configuration remain outside Git. Public evidence contains methods, source citations, aggregate scores and verification receipts. CPU-only synthetic smoke tests qualify runtime compatibility; they are not cybersecurity experiment results.
