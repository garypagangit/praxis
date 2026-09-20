# Frozen encoder anomaly scoring: prospective development comparison

## Question and scope

Does distance from known normal examples yield a more useful anomaly score than reconstruction error, using exactly the already trained encoders? The preceding negative experiment motivated this study. Its test outcomes have been inspected; neither dataset is untouched confirmation. This is a controlled scoring diagnostic, not a new architecture, a faithful MAGIC reproduction, or an established novel praxis contribution.

Use the same audited CADETS and THEIA arrays, file splits, three encoder seeds, original feature preprocessing, checkpoints, and annotations. Original source/data limitations remain: upstream filtered-benign training assumptions, incomplete negative annotations, missing timestamps/UUIDs, separately assigned type IDs and only one evaluation graph per dataset. No independent-campaign intervals, actor identification or five-stage claims.

## Frozen comparison

Use the 8-dimensional pre-decoder bottlenecks of the original MLP and GIN. Do not retrain any weights. Verify strict checkpoint loading and decoder(embedding) parity. Retain full graph context for GIN; batch independent MLP rows. Both models use graph-derived local features, so the MLP is not independent of missing relationships.

For each seed, sample up to 8192 rows uniformly without replacement from the combined train0, train1 and train2 node population, using seed+20260920. Persist graph names and original row indices. Share selected rows across the MLP embedding, GIN embedding, and original local-feature control. The feature control requires no encoder. Sample banks preserve duplicate vectors and their multiplicities.

For each representation, fit coordinate mean and population standard deviation on this training-only bank, flooring scale at 0.001. Use the mean Euclidean distance to the 10 nearest bank rows as the anomaly score. Exact float64 KDTree search runs on CPU; identical queries may be evaluated once and expanded back, without deduplicating the bank. Neural embedding extraction runs on the GPU. Do not imply that all computation runs on GPU.

Calibrate each new score against the entire separate train3 graph: p=(1+#calibration scores>=query score)/(n+1), alert iff p<=0.01. All bank fitting and calibration for all seeds finish before loading evaluation labels in this run. Preserve a fitting freeze with hashes. The study's prior test-label exposure is still explicitly acknowledged. Do not change k, reference size, scaling, thresholds, or architecture after seeing outcomes.

Compare with hash-verified saved reconstruction, Isolation Forest, rarity and fixed-selector predictions from the first pilot for precisely the same seed and graph condition. Retain original classifier names with a `prior_` prefix. Do not deserialize old forest objects; reuse their saved scores and calibrated decisions. Verify labels, degrees, mask hashes and aggregate results against the preceding audited receipts.

Evaluate clean graphs and 50% independently removed retained relationships using the prior fixed mask seed 20260920. This single stress condition is a bounded diagnostic, not a new missingness sweep. Recompute local relationship counts and embeddings from observed relationships for every new arm; banks and calibration remain clean/frozen. Full graph context is preserved before bank-row selection. Removal concerns retained pairs, not raw events.

Also report the original fixed degree checker and confidence selector applied to the new calibrated MLP/GIN scores, without tuning: degree>=2 chooses GIN; confidence chooses larger absolute log(0.01/p), with GIN ties. Score all arms offline. Measure false positives of selectors; their individual-arm calibration does not guarantee selector FPR. No learned checker or compute-saving claim.

## Outcomes and prospective development gates

Publish counts, recall, precision, F1, AP, false-positive rate, achieved calibration FPR, per-seed results and descriptive means. Compare every new arm against all fixed old controls and the new local-feature kNN control. Report corrected/introduced errors and complementary true-positive detections.

An arm is detector-ready for further development on a dataset only if every seed has clean recall >= 50% and evaluation FPR <= 2%. These are prospective engineering screens, not industry-derived deployment guarantees. A positive scoring-improvement screen additionally requires mean clean F1 at least 0.05 above the best prior fixed arm (MLP, GIN, Isolation Forest, rarity). Report exact results if these thresholds fail; no retrospective threshold rescue. Claim support on both datasets only when the same arm meets the gates on each. A learned checker remains deferred until useful, complementary detections and a separately declared training partition exist.

A successful scoring change can motivate a later architecture comparison. If embeddings remain weak, implement and qualify an explicitly documented MAGIC-style masked encoder separately. Novelty must concern a demonstrated new contribution after strong baselines; adopting kNN is existing work.

## Execution and evidence

Freeze exact committed code, config, protocol, predecessor receipts, private checkpoints/predictions and audited arrays before execution. No author checkpoints or cached author scores are used. Preserve all preceding evidence. Private arrays, weights and account/resource identifiers remain outside public Git.

Reuse the existing authorized g5.xlarge and reviewed controller with a new private directory and S3 prefix, one-hour host cap, independent automatic stop and verified shutdown. Maximum reserve is $10, including a $5 incidental allowance; record observed compute estimates separately from actual billing. Use the same isolated CUDA Torch environment and pinned numerical wheels as the successful pilot. No new cloud provisioning or IAM changes.

Require actual CPU/CUDA embedding parity (rtol 1e-4, atol 1e-5), repeated CUDA agreement, exact KDTree checks against independent brute-force Euclidean distances, and hash-bound saved-score auditing. Preserve partial status on timeout. Do not claim GPU speedup without a paired benchmark.

## Primary sources

- Jia et al. (2024), [MAGIC, USENIX Security](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian): masked graph representation learning followed by outlier scoring.
- [Pinned author evaluator](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/eval.py): embedding standardization and kNN, with different k and label-informed thresholds. This experiment uses smaller sampled banks, fixed k=10 and independent benign calibration.
- Detailed method comparison and limitations are recorded in LITERATURE_AND_DESIGN.md.
