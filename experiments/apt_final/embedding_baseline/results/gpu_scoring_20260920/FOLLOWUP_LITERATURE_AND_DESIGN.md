# Follow-up: normal-reference stability under missing relationships

**Status:** proposed development diagnostic; literature checked September 20, 2026. No new execution, threshold changes, or novelty claim. This note does not alter the completed scoring experiment or its failed prospective gates.

## Question in plain language

Can we teach the detector what ordinary activity looks like with fewer recorded relationships, so missing information does not make ordinary entities look malicious? First establish whether the instability comes from the learned representation, the sampled normal examples, or calibration on a different normal graph. The scoring experiment and [post-hoc diagnostic](POSTHOC_DIAGNOSTIC.json) motivate this question; they do not establish its cause.

## Closest primary literature and limits

| Primary source | Existing contribution and relevant distinction |
| --- | --- |
| Zargarbashi & Bojchevski, [Conformal Inductive Graph Neural Networks, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/file/f3024ea88cec9f45a411cf4d51ab649c-Paper-Conference.pdf) | Recomputes calibration scores as graph structure changes. Guarantees assume node- or edge-exchangeable graph sequences; the main setting adds nodes/edges for supervised node classification. Arbitrary deletion and shifts between provenance graphs do not inherit these guarantees. |
| Bai et al., [CRC-SGAD, 2025 preprint](https://arxiv.org/abs/2504.02248) | Graph-aware calibration and conformal control of false positives/negatives already exist. This method trains with class labels and calibrates normal and anomalous classes separately under exchangeability assumptions; our benign-only preparation cannot supply that anomalous calibration set. |
| Lin et al., [CGOD, WWW 2025](https://doi.org/10.1145/3696410.3714879) ([author institution record](https://researchers.mq.edu.au/en/publications/conformal-graph-level-out-of-distribution-detection-with-adaptive/)) | Adaptive graph augmentation and aggregated conformal anomaly scores are established. Its prediction unit is a whole graph, whereas our dependent entities lie within a few provenance graphs. Augmentation plus calibration is therefore not itself a new contribution. |
| Fan et al., [Mask-Conditional Conformal Prediction, AISTATS 2026](https://proceedings.mlr.press/v300/fan26a.html) | Conditions uncertainty on missing-covariate patterns using imputation and reweighting. Our retained graph does not identify which absent relationships were lost versus never existed; simulator masks cannot become deployment inputs. |
| Kong et al., [Mixture-of-Experts Conformal Prediction, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/97c8a8eb0e5231d107d0da51b79e09cb-Abstract-Conference.html) | Weights calibration residuals by similarity between expert-gating vectors, adapting to latent populations without domain labels. Conditional calibration through a learned gate is already represented in the literature; its coverage results cannot be assumed for our dependent graph entities. |

**Assessment:** a benign-only provenance adaptation remains worth testing for practical value. This bounded search does not verify a novel method or an unfilled literature gap. Call results empirical false-positive control, not a distribution-free guarantee.

An additional benchmark review is [Guerra et al. (2026), How Benchmarks and Evaluation Protocols Shape Conclusions in Provenance-Based Intrusion Detection](https://arxiv.org/abs/2608.01454v3), revised September 9, 2026. It reports that benchmark semantics and calibration protocols strongly affect architectural comparisons, including stronger semantic signal on THEIA under its own protocol. Our prepared arrays lack the source identifiers and times needed to reconcile those evaluation choices. Its findings are a reason to check provenance and simple controls, not proof that our score ties have the same cause.

## Smallest rigorous next diagnostic

1. **Hold out whole normal graph files.** Treat the upstream filtered-benign designation as an assumption. Retrain the same encoder procedure on two graphs, calibrate on one, and validate on the remaining graph:

   | Fold | Fit encoder/reference bank | Calibrate | Validate normal behavior |
   | --- | --- | --- | --- |
   | A | train0, train1 | train2 | train3 |
   | B | train1, train2 | train3 | train0 |
   | C | train2, train3 | train0 | train1 |
   | D | train3, train0 | train1 | train2 |

   The current encoders already saw train0–2. Reusing them while rotating these files is only a reference/calibration diagnostic conditional on that exposure. Source UUIDs and times are absent: separate files do not establish disjoint entities, hosts, or independent campaigns. Overlapping folds are not independent replications.

2. **Separate sources of randomness.** Cross the three encoder seeds with three independently fixed bank-sampling seeds; retain the full matrix. The completed experiment coupled those seeds, so its variability cannot be attributed solely to encoder training. Keep bank size, k, scaling, tie handling, and the nominal 1% calibration rule fixed.

3. **Test controls in order.** Compare clean reference/clean calibration; clean reference with pooled clean-and-masked normal calibration; then pooled masked reference and calibration. Only then add conditioning on predeclared observable quality descriptors. Use identical masks and reference budgets across arms, recomputing all observed features. This separates recalibration from added reference coverage and tests whether conditioning adds value beyond simple augmentation.

4. **Keep quality observable.** Fit descriptors and partitions from fit graphs only; use calibration solely for fixed tail cutoffs. Never use true drop rates, intact query counts, labels, or simulator mask identities. Node-type-relative degree and retained relation diversity are candidate proxies, not measurements of actual collection loss. The failed degree selector demonstrates why low degree alone is insufficient.

5. **Freeze before running.** Prespecify graph roles, masks, procedures, and comparisons. Report normal false-positive rates by fold, seed, node type, and corruption condition; also report reference-distance quantiles, dominant score ties, and alarm counts. Use the existing 2% false-positive ceiling as a diagnostic target without changing the completed gates. Normal stability alone is insufficient: any later detector evaluation must also preserve malicious-entity recall and pass the unchanged readiness criteria. Previously examined attack-bearing graphs remain development evidence.

**Decision:** if simple pooled augmentation restores normal stability, measure its detection tradeoff before inventing a checker. If instability remains across encoder seeds with fixed reference sampling, investigate representation changes, including a faithful MAGIC-style encoder. Neither outcome retrospectively rescues the completed experiment.
