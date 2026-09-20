# Runtime amendment: preserve exact reference multiplicities while removing duplicate storage

This follows the frozen [MAGIC development reproduction](../magic_reproduction/PROTOCOL.md), not a new scientific model. The original THEIA qualification completed one training epoch and measured 64 training-only queries against 1,279,199 reference rows. Its projected remaining cost (6,161 seconds with safety) exceeded the remaining 2,390-second science budget. No test graph was loaded or scored. Preserve that attempt and its resource hold.

## Unchanged science

All original datasets, prepared rows, features, original author source, model/objective behavior, seed, 50 epochs, graph order, mean/std arithmetic, k, normalizer query selection, test-label-selected threshold rules, metrics and caveats remain unchanged. Training starts fresh; the one-epoch checkpoint is not reused. Full original training embeddings are still saved. The normalizer still samples original rows, with their original multiplicities. Existing registrations and operative files remain byte-for-byte unchanged.

## Exact execution change

Only nearest-neighbor reference storage/search changes. Deduplicate numerically identical standardized embedding rows without rounding, quantization or near-duplicate merging, retaining an integer count for every row. Search every retained unique vector using float64 direct Euclidean distances. Consume the nearest distances with their counts until exactly k original neighbors have been represented. Repeated distances, including self matches, retain their original weight. If k exceeds the number of unique vectors, multiplicities still supply k original neighbors. No training-reference row is dropped from the mathematical distribution and no approximate neighbor search is used.

This is exact in real arithmetic. Different addition order can produce tiny floating-point differences; verify distances against independent expanded-bank direct calculations at the original tolerances (rtol 1e-6, atol 1e-8), and disclose observed errors. Ties across identical distances cannot change their mean. Generic duplicate-vector compression is established engineering; [Faiss v1.7.4 IndexIVFFlatDedup](https://github.com/facebookresearch/faiss/blob/v1.7.4/faiss/IndexIVFFlat.cpp#L336) already preserves duplicate neighbors. No novelty or retraining-stability improvement is claimed from exact compression.

## Gates and evidence

Qualify synthetic chunk boundaries, counts, ties, k greater than unique count, an all-identical bank, near-but-not-equal vectors, and bad inputs. Independently compare fixed original THEIA qualification queries where available. The same original worker runs its CUDA and per-dataset training-only qualification, with the compact scorer substituted at an explicitly recorded runtime entry point. Original resource estimation now includes unique-bank construction/transfer in its measured index time and actual compact query times. Every original row still contributes to standardization, resource query counts, normalization and evaluation.

Save a runtime amendment receipt binding this source/config registration to the original registration, upstream/source/data hashes, bundle hash and exact substitution. Keep original worker result bindings as well as this separate chain. Recompute all reported metrics from saved full row-aligned outputs and independently verify full original-bank distances on sampled queries. A compact run's numerical/scientific audit and amendment-chain audit must both pass.

## Operations and completion

Permit at most two additional primary attempts, THEIA then CADETS (or both if time permits), using the same existing g5.xlarge and one-hour/watchdog protections. The two original qualification attempts and two additional attempts together have a maximum four-hour compute envelope, approximately $4.024 at the recorded $1.006/hour rate, plus the $5 incidental reserve, within $10. Price estimates are not invoices. No new resources or paid model APIs. Retain all evidence and verify stopped after each attempt.

Resource or numerical holds remain incomplete scientific evaluation. Full 50-epoch, both-dataset results plus independent audits are required to claim the reproduction completed. Even favorable results remain exposed-data, single-seed, oracle-threshold development evidence; a separately designed normal-only calibration study is needed to assess operational alert thresholds.
