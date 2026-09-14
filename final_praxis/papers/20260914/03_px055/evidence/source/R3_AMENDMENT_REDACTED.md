# PX-055 E1-E4 Execution Amendment R3

Date: 2026-09-01 America/New_York

Status: `FROZEN_BEFORE_R3_OUTCOME_EXPOSURE`

This versioned technical amendment supplements the original PX-055 E1-E4
protocol and the R2 execution amendment. It does not change any registered
model, revision, corpus, exclusion, split, precision condition, compute dtype,
quantizer setting, hook point, activation position, layer rule, endpoint,
threshold, bootstrap iteration count, seed, stopping rule, or claim boundary.

## Closed R2 boundary

R2 (`px055-e1e4-ac705630-20260831-r2`) is terminally closed, outcome-exposed,
manifest-sealed, and retained as immutable descriptive evidence. R3 will not
resume, import, pool, overwrite, or otherwise amend an R2 checkpoint or result.
Only dependency caches and Hugging Face model-weight caches may be reused.

The exact R3 run identity is
`px055-e1e4-7df9f1e2-20260901-r3`. Its wholly new S3 prefix is
`[private storage location omitted]`.
Both the local output directory and the complete S3 prefix, including object
versions and delete markers, must be proven empty before staging or execution.

## Administrative Gemma access restoration

Access to the registered gated repository was restored administratively for
the Hugging Face account [account name omitted]. A credential-safe, zero-GPU probe read
the existing [secret resource name omitted] secret only in process memory and
received authorized metadata responses for
`google/gemma-2-9b-it@11c9b309abf73637e4b6f9a3fa1e92e615547819`.
Both model metadata and `config.json` resolved to that exact commit. The probe
emitted no token, response body, model weight, activation, generation, or
registered scientific endpoint. Access restoration is an administrative
repair, not a scientific observation or factor change.

## Frozen principal-angle implementation repair

The frozen protocol defines principal angles by the singular values of the
complete cross-Gram matrix `left_basis @ right_basis.T`. The R2 production
runner incorrectly pre-truncated unequal-rank bases before that calculation.
R2's observed material ranks were all one, so the defect was inactive there;
the independent R2 adjudicator already used the correct complete cross-Gram
calculation.

R3 uses the versioned runner
`cloud_jobs/px055_e1_e4_20260831/run_px055_e1_e4_r3.py`, SHA-256
`7df9f1e2480f077c22edc2d70cd7657e08c963ae5356d7ef92a55d846bc80908`,
implementation version
`px055-e1-e4-implementation-v1.2-full-cross-gram`. The repair removes only the
incorrect pre-truncation, validates compatible non-empty bases, computes the
SVD of the full cross-Gram matrix, and clips numerical singular values before
`arccos`. This restores the already-frozen estimand; it does not define a new
analysis.

The scientific configuration remains byte-identical at SHA-256
`202ccb2c626324056488ebe4d5fc5f02bd50c697de318fee61a61cd92398ea68`.
The registered attention implementations remain Qwen SDPA, Llama SDPA, and
Gemma eager. Gemma may not silently fall back to SDPA because the pinned
Transformers implementation would not preserve Gemma 2 attention-logit
softcapping.

## Credential isolation and cache-only production

Credentialed work is restricted to a pre-scientific prefetch/access phase.
That phase retrieves only the allowlisted AWS secret through the instance role,
keeps the token in process memory, downloads all three exact registered
snapshots into the shared cache, verifies their resolved commits, and emits a
sanitized receipt. The token must never be placed in SSM command text, process
arguments, environment variables, source files, logs, outputs, receipts, or
the production process.

After prefetch, R3 production is token-free and network-independent:
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and
`local_files_only=True` are mandatory. Production must not call Secrets
Manager. Only verified cached snapshots may be loaded.

## Outcome-free Gemma runtime gate

Before any R3 XSTest generation, variant-4 record, activation vector, or E1-E4
metric is produced, a separately retained technical gate must verify the exact
Gemma revision on the NVIDIA A10G under all three registered conditions:
FP16, bitsandbytes INT8, and bitsandbytes NF4. It must prove the eager backend
at every decoder layer, preserve the Gemma softcapping path, keep attention
outputs disabled, prove each quantized load, and obtain finite, shape-valid
hook observations for all `116/116` safe-corpus rows per condition.

The runtime gate may retain only sanitized counts, shapes, backend/load proofs,
hashes, and environment metadata. It may not retain prompt text, response text,
activation vectors, generations, variant-4 projections, or any registered
scientific endpoint. Failure of any runtime-gate requirement is a no-go for R3
science and requires repair followed by a new pre-outcome technical gate.

## Fresh full-scope execution

R3 reruns all nine registered model-by-condition cells from an empty output
directory. It does not run Gemma alone and does not combine fresh Gemma data
with R2 Qwen/Llama data. No R3 scientific outcome may be inspected while
preparing, testing, hashing, staging, or independently reviewing the R3
runner, wrapper, amendment, source manifest, access receipt, runtime-gate
receipt, or adjudicator.

The R3 production completion gate remains fail closed: all `9/9` cells;
paired geometry capture at least `0.95`; complete common-ID behavior records
of `450/450` rows per cell; E4 records of `30/30` paired confirmation rows for
FP16 and NF4 per model; exact model revisions; registered attention backends;
quantized-load, runtime, privacy, and terminal-state proofs. Any missing cell
produces `INCOMPLETE_SCOPE` with no substitution and is closed rather than
repaired in place.

Only an infrastructure interruption before outcome inspection may continue a
hash-validated R3 checkpoint under the same run identity. Any post-outcome
scientific-code repair, factor change, missing-cell repair, or integrity failure
requires another versioned amendment and a wholly fresh run.

R3 adjudication must be performed by a separately frozen R3 validator bound to
this amendment, the exact R3 runner hash, run ID, config, source hashes, and
external terminal-state receipt. It must independently recompute the complete
cross-Gram principal angles and require all three registered models.
