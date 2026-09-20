# Runtime-only continuation of the registered normal-stability experiment

## Purpose and scientific invariants

This wrapper continues the same fixed experiment if its bounded worker stops before completion. It is not a new scientific comparison, a new seed search, or reuse of checkpoints from a different experiment. The original `normal_stability` source files, configuration, protocol, pinned baselines, and registration remain byte-identical.

The four folds, three encoder seeds, three independent bank seeds, three representations, three strategies, graph masks, all numerical settings, and all decision gates remain exactly those in the original registration. Prior outcomes cannot select checkpoints or alter settings. An incomplete attempt cannot be classified as scientific no-go.

## Eligible reusable state

Only complete encoder-and-normal-cache checkpoints produced by this same registered run are eligible. Each checkpoint contains exactly the two encoder weights, preprocessing arrays, `FIT_FREEZE.json`, `MANIFEST.json`, and the eight clean/masked normal graph caches with their receipts: 21 files. Verify role identities, encoder seed, dimensions, training settings, graph/source hashes, feature scaler, checkpoint hashes, cache hashes, and masks against the unchanged original inputs.

Checkpoint eligibility depends on complete valid artifacts, not normal scores or detector performance. A completed cache manifest may qualify even if the original worker did not finish its banks. A missing completion manifest identifies an incomplete encoder/cache set; record it as skipped and retrain under the original deterministic procedure. If a completion manifest exists but its hashes, roles, or artifacts fail verification, abort preparation and investigate the inconsistency; do not silently replace corrupt completed evidence with retraining. Reuse does not rely on the partial-report completed-fold counter.

Create a separate private staging tree containing only `REUSE_MANIFEST.json` and the verified checkpoint files under `checkpoints/`. Verify the original collected result archive against its transport checksum and compare each selected checkpoint and source-output receipt with the corresponding archive member bytes. Bind that chain, all selected bytes, and the original registration/config/data to a new continuation registration before launch. Preserve the prior attempt and its transport and execution receipts. Do not modify its evidence in place.

## Execution order

The wrapper verifies both registrations and the exact staged checkpoint inventory, qualifies the current numerical runtime, and invokes the unchanged original runner in a fresh output tree. It replaces only that runner's `train_and_cache` callback. For an eligible role/seed case, the callback copies its 21 verified files into the corresponding new fold directory and returns its original manifest; every other case runs the original training/cache function.

Do not copy old bank directories, calibration scores, normal result records, attack caches, attack scores, or final decisions into the new scientific tree. The original runner rebuilds **every** reference bank, calibration, and normal-validation result. It writes a new global normal-phase freeze before accessing test0 labels in the continuation and then repeats the **entire** attack evaluation. Previously viewed outcomes remain acknowledged; a repeated evaluation is not independent evidence.

The continuation must record which encoder/cache sets were reused or newly generated and link the original and continuation source/registration hashes. The original runner's source identity remains meaningful for the unchanged science; the continuation receipt separately records the added scheduling/copy mechanism. All gates and expected inventory checks remain the original ones. Independent audit must verify the combined provenance chain and recompute outcomes.

## Integrity and bounded cloud use

The new freeze binds original registered source, the original registration, all continuation operative modules/config/protocol, the reuse-manifest hash, every reused checkpoint file, and the original data inventory. No additional top-level file is added to the frozen original module directory.

Use a new private AWS attempt directory and S3 prefix, with the unchanged reviewed controller: existing authorized host, one-hour host cap, $10 reserve including the $5 incidental allowance, independent stop schedule, and verified shutdown. No new cloud provisioning or permission changes occur here. Input collection now permits at most 2,000 members and 4 GB to accommodate up to 504 reusable checkpoint files; output limits remain 2,000 members and 4 GB. Reuse always occurs in a fresh scientific output tree.

Retain partial status and all prior attempts on interruption. Final elapsed time and compute estimates must account for every attempt; do not present saved training as new training or a hardware speedup. Complete and audit the fixed family before publishing a scientific go/no-go conclusion.
