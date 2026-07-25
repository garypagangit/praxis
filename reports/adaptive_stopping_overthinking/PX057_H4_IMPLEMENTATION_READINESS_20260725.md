# PX-057 H4 Implementation Readiness

**Protocol:** PX-057 H4 Revision 2.1
**Date:** July 25, 2026
**Current decision:** `NO-GO — PRE-DATA LOCKS NOT YET COMMITTED`

> **No H4 scientific data have been collected.** No H4 model output,
> calibration loss, p-value, policy selection, held-out score, or manual-audit
> label existed when this readiness record was drafted. Synthetic fixtures and
> code-only unit tests do not count as scientific data.

This document is an execution checklist, not a result report. The scientific
specification is
`reports/adaptive_stopping_overthinking/PX057_H4_LTT_PREREG_20260725.md`.
Nothing in this checklist may weaken that preregistration.

## 1. Readiness decision rule

H4 may enter calibration collection only when every **Phase A** item is `PASS`
in a committed freeze determination. H4 may enter held-out collection only when
every **Phase B** item is `PASS` for all three cells and the holdout runner
verifies the committed locks mechanically.

An operator's verbal confirmation is not a lock. File timestamps are not lock
evidence. Git commit IDs, exact file SHA-256 values, immutable model/data
revisions, and S3 version IDs where applicable are lock evidence.

## 2. Frozen identities

| Item | Required identity |
|---|---|
| Qwen model/tokenizer | `Qwen/Qwen2.5-7B-Instruct@a09a35458c702b33eeacc393d103063234e8bc28` |
| Llama model/tokenizer | `meta-llama/Llama-3.1-8B-Instruct@0e9e39f249a16976918f6564b8830bc894c89659` |
| GSM8K repository | `openai/grade-school-math@3101c7d5072418e28b9008a6636bde82a006892c` |
| GSM8K test SHA-256 | `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14` |
| ARC dataset | `allenai/ai2_arc@210d026faf9955653af8916fad021475a3f00453`, `ARC-Challenge/test` |
| ARC parquet SHA-256 | `62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9` |
| Policy grid | `m={2,3,4}`, `k={1,2}`, `tau={0,.02,.05,.10,.20}` |
| Risk target | finite-population harm `< .02` |
| Error budget | family `delta=.05`; per cell `.05/3=1/60` |
| Splits | calibration 500; held out 300 |
| Generation | greedy; 8 rounds; max 256 new tokens/round |

There is no OpenBookQA fallback and no model fallback. Failed access means
`BLOCKED`, not substitution.

## 3. Required implementation inventory

The planned implementation consists of:

| Artifact | Responsibility |
|---|---|
| `configs/px057_h4_ltt_transfer_20260725.json` | All frozen identities, cells, grids, thresholds, paths, and environment expectations |
| `scripts/px057_h4_common.py` | Canonical hashes, policy semantics, exact hypergeometric risk test, fixed order, and point-gate mechanics |
| `scripts/run_px057_h4_trace_collection.py` | Source verification, split construction, prompt construction, and trace collection |
| `scripts/run_px057_ltt_calibration.py` | Per-cell calibration, fixed-sequence certification, selection, and lock-manifest creation |
| `scripts/run_px057_h4_holdout_gate.py` | Three-lock verification and one-time held-out point gates |
| `scripts/freeze_px057_h4_phase_a.py` | GPU/runtime capture and the pushed pre-data Phase A freeze determination |
| `scripts/submit_px057_h4_phase_a.py` | Digest-pinned SageMaker Phase A submission from an exact pushed Git commit |
| `scripts/fetch_px057_h4_phase_a.py` | Version-specific runtime retrieval and cloud-job evidence binding |
| `cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py` | Full-Git-clone runtime capture with least-privilege secret retrieval |
| `cloud_jobs/px057_h4_phase_a_20260725/sagemaker_role_policy.json` | H4-prefix S3 and exact-secret least-privilege execution-role policy |
| `scripts/prepare_px057_h4_manual_audit.py` | Gold-free blinded audit-packet export and committed-judgment join |
| `scripts/adjudicate_px057_h4.py` | Independent source/split/gold/policy/statistical/gate replay plus replicated canonical Git-lock and manual-audit schema checks |
| `tests/test_px057_h4_common.py` | Policy-order, exact-risk, sensitivity, and held-out count-gate tests |
| `tests/test_px057_h4_trace_collection.py` | Split, prompt, and extraction tests |
| `tests/test_px057_h4_integrity.py` | Gold recomputation, blinded-audit, Git-lock, and independent-tail tests |

Names may not be silently changed after the freeze. If a final implementation
uses a different path, the preregistration and config must be amended and
committed before scientific collection.

### Build-branch validation completed

The implementation branch completed the following non-scientific checks before
publication:

- all ten H4 scripts/entry points pass Python bytecode compilation;
- the two JSON configs parse successfully;
- 39 focused PX-057 tests pass;
- an independent integer-combination implementation matches the primary exact
  hypergeometric tails;
- both upstream source byte hashes and row counts reproduce;
- the four explicit split files independently rederive from the pinned sources,
  seeds, Gate 2 exclusions, and hash-ranking algorithm;
- no H4 model response, trace, policy result, held-out score, or audit judgment
  was generated.

These checks establish implementation readiness only. The GPU runtime capture
and committed/pushed Phase A freeze remain intentionally pending.

## 4. Phase A — pre-calibration locks

Every row must be evidenced in one external freeze manifest.

| Check | Required evidence | Draft status |
|---|---|---|
| Revision 2.1 preregistration | Exact file SHA-256 and Git commit | PENDING |
| Configuration | Committed, clean file; schema validation PASS | PENDING |
| Model identities | Exact Qwen/Llama model and tokenizer revisions in config | PENDING |
| Model access | Synthetic-only load/generation smoke; no benchmark prompt | PENDING |
| Dataset identities | Pinned revisions and source-byte hashes match Section 2 | PENDING |
| No fallback | Config rejects unregistered model/corpus identifiers | PENDING |
| Environment | Expected-image digest assertion plus Python, full package inventory, Transformers, PyTorch, CUDA/cuDNN, dtype, and GPU fingerprint | PENDING |
| Prompts | Exact numeric/choice templates and SHA-256 values | PENDING |
| Scoring | Numeric/choice normalizers, invalid-output rule, option order frozen | PENDING |
| Confidence | Generated-token inclusion/exclusion and clipping rule frozen/tested | PENDING |
| Policy semantics | `k=1` no-repeat control and `k=2` repeat rule unit-tested | PENDING |
| Policy order | Exact 1–30 preregistered sequence reproduced by test | PENDING |
| Hypergeometric p-value | Compared with an independent trusted calculation | PENDING |
| Family control | Fixed sequence at `1/60` per cell; no data-dependent order | PENDING |
| GSM8K population | 1,319 source rows; exactly 200 Gate 2 IDs excluded; 1,119 eligible | PENDING |
| ARC population | Exactly 1,172 `ARC-Challenge/test` rows | PENDING |
| Split algorithm | Hash rank, seeds 5701/5702, deterministic tie-break tested | PENDING |
| GSM8K split | 500/300/319; unique and disjoint; explicit IDs and hashes | PENDING |
| ARC shared split | 500/300/372; same IDs referenced by C2/C3 | PENDING |
| Manual-audit selection | Seed 5703 and hash-ranking rule frozen; C2/C3 must select the same ARC IDs | PENDING |
| Code quality | Syntax checks, targeted tests, and independent review PASS | PENDING |
| Freeze manifest | External byte hashes; no self-hashing JSON claim | PENDING |
| Repository lock | All above committed and clean; remote commit SHA recorded | PENDING |

### Phase A hard-stop tests

The trace collector must refuse calibration when any of these is true:

- protocol status is not `PRE_DATA_FROZEN`;
- config, preregistration, split, prompt, or code is uncommitted or dirty;
- a source or model revision differs;
- an expected byte hash differs;
- the Gate 2 GSM8K exclusion count is not exactly 200;
- corpus row counts or split counts differ;
- any calibration/held-out ID overlaps within a corpus;
- C2 and C3 do not reference the same ARC split hashes;
- the runtime capture or Phase A freeze determination is missing, dirty,
  unpushed, hash-mismatched, or from a different GPU/container/package stack;
- an output directory already contains scientific rows without an authorized
  resume manifest.

Passing Phase A authorizes calibration only. It does not authorize held-out
generation.

### Phase A commit sequence

The runtime and freeze files cannot be honestly created in the initial
implementation commit. Use this sequence:

1. Commit and push the protocol, config, prompt file, requirements, code,
   tests, and explicit split manifests.
2. Apply the checked-in least-privilege SageMaker role policy, require bucket
   versioning, and run `submit_px057_h4_phase_a.py`. The submitter resolves the
   frozen ECR tag, requires the expected digest, requires a clean pushed branch,
   and launches the image by digest. The job clones that exact commit, reads the
   gated-model token from Secrets Manager without logging it, and invokes
   `freeze_px057_h4_phase_a.py --capture-runtime` on synthetic prompts only.
3. After the job completes, run `fetch_px057_h4_phase_a.py --job-name <name>`.
   It downloads the exact S3 object versions, verifies their hashes, and writes
   `runtime_environment.json` plus `phase_a_cloud_job.json`.
4. Commit and push both retrieved Phase A evidence files.
5. Run `freeze_px057_h4_phase_a.py --freeze`. It verifies the pushed base
   commit, all protected hashes, the empty scientific-output state, and the
   focused PX-057 test suite.
6. Commit and push `phase_a_freeze.json`.
7. Only then may the calibration collector run. It rechecks the Phase A
   hashes, remote commit, container digest, package versions, CUDA runtime,
   GPU identities, model revisions, dtype, and tokenizer chat-template hash.

The digest equality check is not independent runtime attestation: the capture
script checks the supplied CLI value against the supplied environment value.
The final report must describe it as an expected-image assertion and rely on
the richer captured runtime fingerprint as corroborating reproducibility
evidence.

## 5. Phase B — calibration and global holdout lock

Calibration is one global phase across all cells.

| Check | Exact acceptance condition | Status |
|---|---|---|
| C1 calibration completeness | 500 unique traces × 8 rounds = 4,000 generations | NOT STARTED |
| C2 calibration completeness | 500 unique traces × 8 rounds = 4,000 generations | NOT STARTED |
| C3 calibration completeness | 500 unique traces × 8 rounds = 4,000 generations | NOT STARTED |
| Total calibration completeness | 1,500 traces; 12,000 generations | NOT STARTED |
| C1 determination | All 30 policies, exact p-values, reached flags, selected policy or empty prefix | NOT STARTED |
| C2 determination | Same required fields | NOT STARTED |
| C3 determination | Same required fields | NOT STARTED |
| Fixed-sequence verification | No ordering value derived from calibration metrics | NOT STARTED |
| Independent recalculation | Exact match for p-values, prefix, and tie-break selection | NOT STARTED |
| C1 lock manifest | Inputs, outputs, environment, config, code, split, hashes | NOT STARTED |
| C2 lock manifest | Same | NOT STARTED |
| C3 lock manifest | Same | NOT STARTED |
| Global commit | All three determinations and locks committed together or referenced by one global lock commit | NOT STARTED |
| Cloud immutability | S3 version IDs plus downloaded-byte SHA-256 values recorded | NOT STARTED |
| Clean-worktree verification | No protected file differs from the lock commit | NOT STARTED |

The holdout runner must verify all three committed lock manifests before loading
either model. A missing or empty certified prefix in any cell is a registered
negative H4a outcome; held-out generation for that cell is skipped. No other
cell's held-out result may influence calibration, code, or policy selection.

The current branch verifies that every calibration lock commit is present on a
remote Git ref before holdout generation. S3 version lookup is not automated;
when AWS/S3 is used, the cloud-immutability row must remain `NOT STARTED` until
an external retrieval manifest is captured and checked. This limitation must
be carried into the final report.

## 6. Phase C — held-out execution and audit

When Phase B passes, apply each committed selected policy once to its held-out
cell.

| Check | Exact acceptance condition |
|---|---|
| Holdout completeness | 300 unique traces × 8 rounds = 2,400 generations per eligible cell |
| Full planned total | 900 held-out traces; 7,200 generations if all cells have policies |
| No overlap | Calibration and held-out IDs disjoint within each corpus |
| ARC pairing | C2/C3 use the same 300 ARC IDs |
| Policy identity | Loaded only from committed cell determination |
| H4b | Harm count `<=6/300` |
| H4c | Selected-correct minus fixed-long-correct `>=-3/300` |
| H4d | Unrounded mean generated-token saving `>=.20` |
| Manual sample | 50 committed trace IDs per cell |
| Manual units | All eight rounds; exactly 400 comparisons per cell |
| Manual blinding | No gold, automated extraction/labels, policy/gate result, or certificate status shown |
| Audit chronology | Blinded judgments committed before automated-answer join and before point-gate calculation |
| Manual pass | `<=8/400` automated/manual disagreements per cell |
| Independent adjudication | Recomputes all gates and integrity checks without importing decisions |

H4b–H4d are point gates. H4b must never be labeled a formal validation or
violation of the calibration certificate.

If the manual audit produces 9 or more disagreements in a cell, that cell is
invalid. Do not repair the scorer and reuse the same held-out outcomes.

## 7. H4e reporting readiness

H4e is computed only after all cell determinations exist:

- `RETAIN_FOR_FUTURE_PX057_CANDIDATE` if `tau>0` in at least two of three
  selected certified policies;
- `RETIRE_FROM_FUTURE_PX057_CANDIDATE` otherwise;
- `INCONCLUSIVE` if any cell has no selected certified policy.

H4e is not part of overall H4 scientific pass/fail and does not authorize a
production policy.

## 8. Compute and operational envelope

| Phase | Questions | Rounds | Generations | Maximum output tokens |
|---|---:|---:|---:|---:|
| Calibration | 1,500 | 8 | 12,000 | 3,072,000 |
| Held out | 900 | 8 | 7,200 | 1,843,200 |
| Total | 2,400 | 8 | **19,200** | **4,915,200** |

This is approximately 12 times the 200-question Gate 2 maximum generation
count/token budget. Actual output tokens can be lower because generation may
end before 256 tokens.

Before cloud submission, verify:

- GPU quota and model license access;
- encrypted, versioned S3 output location;
- sufficient local and cloud storage for raw prompts/responses;
- container digest and package lock;
- job names encode cell and phase;
- no job combines calibration and held-out phases;
- held-out jobs cannot start without the three-lock verification step.

Cost approval does not relax any scientific lock.

## 9. Required artifact manifest

The final evidence package must include, at minimum:

- Revision 2.1 preregistration and readiness record;
- frozen config and exact environment manifest;
- source and model identity manifest;
- prompt files and hashes;
- explicit GSM8K and ARC calibration/held-out split files;
- Gate 2 exclusion manifest;
- frozen manual-audit selection rule and committed blinded extraction-judgment
  files;
- per-cell selected rows, reasoning traces, raw generations, and collection
  summaries;
- per-cell 30-policy calibration determinations;
- three calibration lock manifests and the global lock commit;
- held-out point-gate determinations;
- outcome-independent adjudication, with shared provenance/schema validators
  disclosed and a fully external reproduction still required for an
  independently implemented provenance claim;
- external SHA-256 manifest;
- Git commit SHAs and immutable S3 object version IDs.

The Gate 2 report says four core evidence files were hashed while one summary
lists only three hashes. H4 must not repeat that ambiguity: every claimed file
count must match the external manifest exactly.

## 10. Go/no-go sign-off template

This table remains empty until a machine-generated readiness determination
populates it.

| Decision item | Evidence path/hash | Result |
|---|---|---|
| Phase A all pre-data locks | — | — |
| Synthetic model access only | — | — |
| Dataset/source byte verification | — | — |
| Split and audit-selection freeze | — | — |
| Exact statistical implementation tests | — | — |
| Independent code review | — | — |
| Freeze Git commit and remote SHA | — | — |
| Calibration authorization | — | — |

Until every row has verifiable evidence and `PASS`, the only authorized status
is:

> **NO-GO. H4 remains a preregistered plan with no scientific data and no
> certificate.**
