# PX-057 H4 Holdout Cloud-Transport Amendment

**Experiment:** PX-057 - Adaptive Stopping to Prevent LLM Overthinking

**Transport ID:** `px057-h4-holdout-cloud-transport-20260727`

**Date:** July 27, 2026

**Status:** `PRE-OUTCOME TRANSPORT FREEZE PENDING`
**Scientific protocol:** H4 Revision 2.2, unchanged

## Determination

This amendment supplies the missing hardened cloud transport for the H4
held-out phase. It does not alter a model, dataset, split, prompt, decoding
setting, policy grid, fixed sequence, risk threshold, sample size, manual-audit
rule, success gate, or claim boundary.

The three calibration bundles were protected-fetched and committed at Git
commit `e27aafaa46967c85cb7f88517ef374e4ae8a3d73` before this holdout-transport
freeze. During preparation of this amendment and its freeze gate, no
calibration payload was opened or parsed and no calibration outcome, loss,
p-value, certified prefix, or selected policy was calculated or inspected.
Only paths, byte lengths, SHA-256 values, and transport metadata were checked.

Consequently, this is an outcome-blind implementation amendment. It cannot be
used as evidence that H4 passes, that any cell is eligible for held-out
collection, or that a useful policy will be selected.

## Frozen scientific bindings

| Artifact | SHA-256 |
|---|---|
| H4 Revision 2.2 config | `0df81f0bb86d60869424ba12156ccc306ce3df280d6cecd25857f98785d03317` |
| Phase A freeze v2 | `e54e6aa573e42f4415d9a03bc129e25a96ba71d555ed631586364eca6aeaceff` |
| H4 trace collector | `e2472bc913114ab23e1ff2c70dc13d72a3b70c305c294951e4aada6045d9c64a` |
| H4 common/scoring library | `5e931441fada32e9e94a5eb6167597bc8def825796566190aab03257034df60f` |
| H4 holdout gate | `dbd85331717e4b99f485aa8a604d9fa15782a7670e726a19cc4c08845bc7ec70` |
| H4 requirements lock | `5aa1adf7ce4187838a9f2867c9e6919bb5b06e11f90d70194ab48fc09984d163` |

The holdout transport refuses to freeze if any of these exact bytes change.
The already frozen model revisions, source revisions, prompt hash, split hashes,
and runtime identity remain governed by the Revision 2.2 config and Phase A
freeze.

## Protected calibration evidence, not outcomes

The freeze binds the exact committed calibration retrieval manifests:

| Cell | Cloud manifest SHA-256 |
|---|---|
| C1: Llama / GSM8K | `c0b0793705c31cd64ead0f2a6235ab7e872a3e9231d95e3791590053b7ead989` |
| C2: Qwen / ARC | `00ee964b725523a74ff18b243769ed1b92af03c41c4f674f77134e38bc734ea7` |
| C3: Llama / ARC | `0c28a2e9c7bc30d4b4616da1d5972680aead6e3315b88f66e45cc20fc9723f22` |

It also binds all twelve exact downloaded files without parsing the scientific
payloads:

| Cell | File | Bytes | SHA-256 |
|---|---|---:|---|
| C1 | `collection_summary.json` | 4,561 | `a73a3ce45517c71f50aadaeb1c6fea51ab4dd03cd26ceca6ee97d1af9c63c5d4` |
| C1 | `raw_generations.jsonl` | 9,156,495 | `6acee8c6fe662b478164ed7a305571228300e3c1fad53e8c893e08544bd5c772` |
| C1 | `reasoning_traces.jsonl` | 574,512 | `08cf9d0df9d9f73ef793a10c3d65c06018a09b2bfb7e3f685cb272794d7ec4fa` |
| C1 | `selected_rows.jsonl` | 185,117 | `a48ef2c73edc6eec80428358feee3f38e1c5182dac441ca39c339fb9b54f00ef` |
| C2 | `collection_summary.json` | 4,569 | `3311bd814730b811d66721ef34c1650e4669b58120a921675a45006e5824e995` |
| C2 | `raw_generations.jsonl` | 10,941,795 | `a2fb2084fcc25b84fa6698c1a1527550f0b35a7ddbadf37724cb71cd25e775c4` |
| C2 | `reasoning_traces.jsonl` | 580,081 | `966295c0b9b0f51bc1c34ff6f7029d95eb54f066b89d7342bf0aa3a40664740b` |
| C2 | `selected_rows.jsonl` | 283,503 | `90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224` |
| C3 | `collection_summary.json` | 4,583 | `93724c4e7002d06a11da8389ad30eb4db0238f519c928eb8426fa42535afd8b1` |
| C3 | `raw_generations.jsonl` | 10,650,544 | `9e5224adfba63257f60f00b34e54157310613504e09db5376959da6ed1e530d3` |
| C3 | `reasoning_traces.jsonl` | 585,653 | `5a43ea763555bd442f467276ca6326fae61214d08c9c5fbecbc7d65e733a8a99` |
| C3 | `selected_rows.jsonl` | 283,503 | `90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224` |

The freeze requires every file above to remain committed with
`e27aafaa46967c85cb7f88517ef374e4ae8a3d73` as its last-change commit. It also
checks each retrieval manifest's collection-object hashes and S3 VersionIds.
That is a transport-integrity check, not outcome adjudication.

## Frozen held-out transport

Each eligible cell receives exactly one deterministic SageMaker job:

| Cell | Registered job name | Frozen holdout rows | Expected generations |
|---|---|---:|---:|
| C1 | `px057-h4-hold-c1-r1-20260727` | 300 | 2,400 |
| C2 | `px057-h4-hold-c2-r1-20260727` | 300 | 2,400 |
| C3 | `px057-h4-hold-c3-r1-20260727` | 300 | 2,400 |

The transport uses the already registered `ml.g5.2xlarge` instance class,
200-GB volume, pinned PyTorch container digest, SageMaker execution role,
Hugging Face secret, AWS region, and S3 experiment prefix. Maximum runtime is
86,400 seconds per cell. `EnableManagedSpotTraining` is frozen to `false`, and
the SageMaker `RetryStrategy` field is frozen as omitted. SageMaker requires a
minimum value of one when `MaximumRetryAttempts` is supplied, so omission is
the valid API representation of no configured automatic retry. The submitted
request must omit the field, and the returned job description must report it
as absent or null. Source is fetched by exact S3 object VersionId and SHA-256
and is verified before extraction.

The authenticated bootstrap archive contains the holdout entrypoint and the
calibration and Phase A helper entrypoints that it must execute before cloning.
Those bootstrap bytes are verified by exact S3 VersionId and SHA-256 before
extraction. The bootstrap then clones the exact pinned Git commit; that commit
supplies the scientific config, frozen holdout split, prompt, requirements,
collector, common/scoring code, holdout gate, committed LTT determination, and
terminal lock. Both the bootstrap members and cloned scientific inputs are
bound by exact committed-byte hashes.

The bootstrap directory has its own committed `.gitattributes` containing
`* text eol=lf`. This prevents Windows `core.autocrlf` behavior from changing
the staged entrypoint bytes relative to their Git and S3 hashes. The protected
root `.gitattributes` is unchanged.

The cloud collector must produce exactly:

- 300 selected holdout rows;
- 300 reasoning traces with eight ordered rounds each;
- 2,400 unique question-round generations;
- one collection summary;
- cloud evidence and a SageMaker model artifact with immutable object versions.

## Outcome-blind freeze and execution order

The required order is:

1. Commit and push the new transport config, amendment, cloud entrypoint,
   submitter, fetcher, freeze gate, and tests.
2. Run `freeze_px057_h4_holdout_transport.py` from a clean pushed HEAD.
3. The gate verifies all original scientific hashes, the exact protected
   calibration evidence, all new transport files, and absence of every LTT
   determination, LTT lock, holdout launch, holdout cloud manifest, holdout
   output, manual-audit artifact, and holdout determination.
4. Commit and push
   `manifests/px057_h4_20260725/holdout_transport_freeze.json`.
5. Only then run the three registered LTT determinations against the already
   committed calibration evidence.
6. For each cell with a non-empty certified prefix, write and commit the
   terminal LTT lock. A cell with an empty prefix is scientifically negative
   for H4a and receives no held-out generation.
7. The submitter dynamically binds the exact committed-and-pushed LTT
   determination and terminal-lock SHA-256 values. These hashes do not exist
   at this transport freeze and therefore cannot be guessed or backfilled.
8. Register and submit the cell's sole deterministic job. Its ARN, request
   hash, source VersionId, and source SHA-256 must be committed and pushed
   before its outputs may be fetched.
9. Fetch only the exact registered object versions and hashes. Commit and push
   the retrieved evidence before manual audit or final held-out adjudication.

The first-attempt rule is strict: no replacement job, silent retry, alternate
model, alternate split, altered code, or post-outcome transport amendment is
permitted under this transport ID.

## Freeze gate

The executable gate is
`scripts/freeze_px057_h4_holdout_transport.py`. It refuses to write the freeze
manifest unless:

- the worktree is clean;
- local HEAD, its upstream ref, and the live remote branch are identical;
- the current branch and origin repository match the registration;
- every frozen scientific and calibration evidence hash matches;
- all calibration evidence files remain last changed at the protected-fetch
  commit;
- every new transport implementation file is committed and unchanged;
- focused transport tests pass; and
- no calibration determination, LTT lock, or held-out evidence exists.

The manifest uses the closed schema
`px057-h4-holdout-transport-freeze-v1`. A `PASS` label is insufficient: every
consumer must validate the exact inventory contract. The frozen record contains
exactly six original science bindings, three calibration cloud manifests,
twelve calibration bundle files, eleven required transport files, eleven
authenticated archive members, and thirty-three unique protected paths. It
also records exactly two successfully executed focused tests and the exact
pre-outcome absence inventory of twenty-one files plus three output
directories. Missing paths, extra paths, duplicate aliases, key/path mismatch,
failed or skipped tests, inconsistent Git heads, or incomplete absence lists
invalidate the freeze.

Every protected record is also recomputed from the historical
`freeze_base_commit`, not merely compared with the consumer's current checkout.
For each of the thirty-three paths, the validator requires the path to exist at
`freeze_base_commit`, obtains its exact Git blob and bytes with
`git show <freeze_base>:<path>`, recomputes byte length and SHA-256, and verifies
that the recorded last-change commit is both the exact path history at that
base and an ancestor of the base. A transport file added or changed after a
forged older freeze base therefore invalidates the manifest even when current
HEAD contains matching bytes.

The freeze manifest itself must then be committed and pushed before
calibration adjudication. The gate is intentionally not invoked by this draft
commit because the complete transport implementation must first be committed,
tested, and pushed.

## Claim boundary

This amendment supports only a claim that the held-out cloud transport was
specified and frozen without inspecting calibration outcomes. It does not
provide a certificate, H4 result, transfer result, robustness result, or
deployment claim. All Revision 2.2 negative-result handling and final claim
boundaries remain unchanged.
