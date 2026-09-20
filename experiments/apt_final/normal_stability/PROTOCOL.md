# Normal-reference stability and a finite repair comparison

## Scope and completion rule

Complete the three strategies specified below on both audited datasets, all four graph-role folds, three encoder seeds crossed with three independent bank seeds, and clean/50%-removed conditions. Then issue a final go/no-go decision for this fixed candidate family. Do not add an optional checker, change thresholds, select a winning seed, or tune an architecture after viewing outcomes. A completed negative comparison closes this version of the idea; it does not establish that all provenance detectors are impossible. An interrupted run is incomplete, not scientific no-go.

The previous scoring comparison showed strong THEIA recovery but unstable normal scores and a failed degree checker. This study asks whether representing normal behavior with missing relationships can control false alerts while retaining malicious-entity detection. It is previously exposed development data, not confirmation or an established novel method. The [prior literature assessment](../embedding_baseline/results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md) identifies close existing augmentation and conditional-calibration methods.

## Data roles and training

Use the exact audited CADETS/THEIA NPZ arrays. For each dataset separately, rotate the four supplied filtered-benign graph files according to config.json: two fit graphs, one calibration graph, one normal-validation graph. Train fresh native-pilot MLP and GIN models and fit the original input scaler using only the two fit graphs for that fold. Use the original ten-epoch,32-hidden,8-bottleneck training procedure and three fixed encoder seeds. Do not reuse the previous fit-three-graph checkpoints.

Reserve graph roles explicitly. Held-out files do not establish disjoint entity identities or independent campaigns because source UUIDs/times are absent. Folds overlap and are not independent replications. The source's filtered-benign designation remains an assumption; normal-validation false-positive rates are conditional on it. Test negatives are absent from supplied malicious annotations, not exhaustively verified benign entities. Type vocabularies differ across datasets and include a source label-free transductive vocabulary assumption.

Cross each encoder seed with all three independent bank seeds. Local-feature representations do not depend on encoder seed: repeated copies are marked duplicates and verified identical, not counted as additional independent evidence. Model and bank variability is descriptive.

## Equal-budget strategies

For each fold/bank seed, uniformly sample 8192 distinct original entity rows from the union of the two fit graphs (or all rows if fewer). Every representation and strategy uses this same base row set. Preserve reference-vector multiplicity.

1. **clean:** all selected rows use their clean representations; calibrate against the clean calibration graph.
2. **pooled_calibration:** use the same clean reference bank and its exact scores; calibrate against concatenated clean and masked calibration scores.
3. **pooled_reference_calibration:** independently shuffle the selected row positions using a fixed bank-seed-derived allocation; half use clean views and half use masked views, with no repeated source row and the same total8192-row budget. Calibrate against concatenated clean and masked calibration scores.

The pooled calibration views have equal node counts and therefore equal mass. They are dependent views, not independent samples. Mixture calibration does not guarantee the desired FPR in either subgroup; measure clean and masked groups separately. Fit each representation's coordinate mean/std on its own reference bank, with scale floor0.001. Use exact mean Euclidean distance to10 nearest bank rows. New methods are compared at equal reference size; changes in reference composition and bank scaling are jointly part of the pooled-reference strategy.

Use local observed features, frozen-after-training MLP bottlenecks, and GIN bottlenecks. MLP inputs contain graph-derived counts, so it is not independent of relationship loss. GIN embedding extraction retains the entire observed context. GPU extraction and CPU exact kNN are timed separately; no hardware speedup claim.

Use conservative empirical-tail probabilities p=(1+#calibration>=query)/(n+1), alert when p<=0.01. Keep ties intact. No validation or attack labels select banks, features, thresholds, hyperparameters, candidate arms or stopping epochs.

## Interventions and order

Drop50% of retained relationships with a fixed seed per graph, shared by all folds/models/strategies, while retaining every node. Clean and masked are the only conditions. Both incoming/outgoing count features and embeddings must reflect observed relationships. The simulator mask, intact query degree and true removal rate are never classifier inputs. Actual missing-log identification is not claimed.

Finish all encoder fitting, reference construction and calibration across both datasets before loading any test0 labels in this execution. Write a global normal-phase freeze binding every fitted artifact and normal result. Then evaluate all fixed arms on both conditions of the already inspected test0 graph using unchanged weights, reference banks, scaling and calibration. Do not discard failed normal arms from the attack replay: their detection tradeoffs are part of the final result.

## Outcomes and fixed decision gates

For every dataset/fold/encoder seed/bank seed/strategy/representation/condition, report normal-validation alert counts/FPR and per-node-type FPR; attack-evaluation TP/FP/TN/FN, recall, precision,F1,AP and benchmark-negative FPR. Report descriptive mean/range and sample counts, with local-feature duplicate accounting. Save compressed numeric evidence, reference row/view identities, unique query vectors and inverse mappings sufficient for independent recalculation.

**Normal-stability gate:** the same candidate must have normal-validation FPR<=2% in every fold/encoder-bank repeat and both conditions.

**Detector-readiness gate:** that same candidate must achieve test0 malicious-entity recall>=50% and benchmark-negative FPR<=2% in every fold/repeat and both conditions. A general go requires the same strategy/representation to pass on both datasets. Dataset-specific passes are reported separately without relabeling the general gate.

Carry forward the previous mean clean F1 improvement screen of+0.05 over the pinned original native-pilot best fixed mean F1, using unchanged published baseline values. This historical comparison changes training from three graphs to two and is descriptive, not a pure causal scoring contrast. Also report paired repair deltas against all clean-strategy representations with the same new fold/seeds, including the strongest clean-strategy comparator. A positive repair claim requires readiness plus mean F1 improvement>=0.05 under missing relationships over the strongest clean-strategy fixed representation on each dataset. Report any clean-data loss and all individual runs; no significant-generalization or production claim.

The gates are engineering development screens, not industry-derived alert budgets. Normal stability alone cannot establish attack detection. If no fixed candidate passes the gates, close this repair family as unsupported for the declared scope and document why. Do not retrospectively weaken the2% ceiling or50% recall floor. Preserve all earlier results.

## Integrity, runtime and limits

Freeze exact committed source/config/protocol, imported operative modules, pinned baseline receipts and all10 normalized arrays before execution. No author saved models/scores are used. Require CPU/CUDA numerical and deterministic qualification and exact kNN checks against direct Euclidean calculations. Independent audit must verify role exclusion, row/view budgets, source/data/model/cache hashes, calibration, all decision counts, duplicate accounting and gates; document any sampled checks.

Use a new private AWS directory/prefix with the existing authorized g5.xlarge, reviewed controller, one-hour host cap, independent automatic stop and verified shutdown. Reserve at most$10 including a$5 incidental allowance; record observed compute estimates separately from billing. The run must preserve partial phase status if the limit is reached. A runtime-only resumption may reuse verified completed fold artifacts under a separately frozen continuation, without changing scientific settings or omitting failed arms.

No timestamps/UUID maps, independent campaign confirmation, operational exposure denominator or human label audit is created by this experiment. Public Git contains code, aggregate outcomes, hashes and audit receipts only. No raw arrays, trained weights, credentials or account/resource identifiers are published.
