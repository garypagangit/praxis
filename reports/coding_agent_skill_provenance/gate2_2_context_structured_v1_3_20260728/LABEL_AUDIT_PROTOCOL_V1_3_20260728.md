# PX-062 Gate 2.2 v1.3 blinded label-audit protocol

**Experiment:** `px062-skill-selection-gate2-2-v1-3-20260728`

**Construction status:** prospective, target-outcome-blind, and prohibited from
Qwen, Mistral, or AWS collection until this gate is completed.

## Why the label gate changed

The v1.2 two-pass all-row unanimity gate failed on nine rows. Seven failures
were prompts retained byte-for-byte from v1.1 that both prior auditors had
classified correctly and unanimously. Across all 1,022 retained rows, the new
Sol pass changed two decisions and the new Terra pass changed five; every
changed decision created a new conflict. This is direct evidence that requiring
two stochastic passes to make zero isolated errors over 1,032 rows is a brittle
run-perfection test rather than a stable semantic-label test.

Version 1.3 therefore preregisters a governance redesign before any target
model output exists. This is not a relaxation or reanalysis of v1.2. The v1.2
result remains invalid, and none of its predictions can count toward v1.3.

## Required fresh four-pass audit

Four complete blinded audits must be run over all 1,032 rows:

- slot 1: `gpt-5.6-sol`
- slot 2: `gpt-5.6-terra`
- slot 3: `gpt-5.6-sol`
- slot 4: `gpt-5.6-terra`

Each slot uses 43 new stateless ephemeral sessions of 24 tasks, high reasoning,
model-default sampling, the frozen strict JSON schema, an 1,800-second attempt
timeout, and the same disabled-tool boundary as the qualified v1 runner. The
172 accepted session IDs must be globally unique. Every attempt uses a unique
empty working directory. Slots 3 and 4 are independent fresh passes, not
resumes or semantic retries of slots 1 and 2.

The sealed v1.2 evidence manifest is also an authenticated session blacklist.
Before every slot, the runner loads its exact bytes at SHA-256
`f34151882216c35196bd0c26d80f7603bb371187efe3862fa6eacc96ef4b90c0`,
recovers exactly 86 unique accepted session IDs (identity-set SHA-256
`893d9aba0182f9bf5ba5a612d59eb826e9878c5d45d321805c09e5c1c9f6e632`),
and rejects any v1.3 attempt or predecessor sidecar that reuses one. The sealed
v1.2 manifest is included in the v1.3 evidence artifact inventory. Every
`thread.started` ID is recovered from every attempt event log, including
failed, partial, malformed, and multiple-ID attempts. The canonical sidecar
records that complete sorted set, and any intersection with the sealed 86-ID
set or another v1.3 attempt fails even when the legacy singleton projection is
`null`.

Slots execute only in the fixed order 1, 2, 3, 4. Before any evidence write,
the requested slot and every successor must be absent, every predecessor must
have a canonical complete 1,032-row payload, sidecar, 43-batch evidence tree,
and 43 unique accepted sessions bound to the same pending checkpoint, and the
consensus manifest must be absent. The runner repeats this check after
collecting the checkpoint and before creating its evidence directory.
Predecessor validation reconstructs every batch partition, rendered prompt,
dynamic schema, exact command, event/session summary, captured response, and
canonical prediction binding; self-consistent edits to sidecar-declared hashes
are insufficient.

Auditors receive only the frozen 43-entry semantic registry projection and
`task_id`/`prompt`. Option maps, answer labels, seed scenarios, all v1-v1.2
predictions, conflict ledgers, invalidation records, and other v1.3 auditor
outputs are withheld.

## Frozen row-level acceptance rule

A row is accepted only if all of the following hold:

1. at least three of four predictions equal the frozen answer;
2. at least one matching vote comes from a Sol slot (1 or 3); and
3. at least one matching vote comes from a Terra slot (2 or 4).

One dissent is permitted and retained in the resolution evidence. Any 2-2
split, majority against the key, fewer than three key votes, lack of supporting
votes from either model family, missing or mechanically invalid row, or any
other failure invalidates v1.3 before collection. There is no semantic retry,
disputed-only rerun, same-version prompt edit, or same-version relabel. A
mechanically invalid attempt may receive at most one byte-identical retry under
the already qualified transport/schema rule.

This policy does not claim four-way unanimity. It claims that every frozen
label has a model-family-balanced supermajority under four fresh full passes.

## Frozen scientific boundary

Version 1.3 replaces exactly the complete nine-row v1.2 conflict union and
retains the other 1,023 task IDs. Counts remain 1,032 tasks, 516 registered
labels, 516 `NONE`, and 344/344/172/172 task-type balance. Registry names and
descriptions, hypotheses, arms, target model revisions, decoding, efficacy and
harm thresholds, multiplicity, determination logic, and claim boundary are
unchanged. No Qwen or Mistral Gate 2.2 target outcome existed during this
construction or governance decision.

“Retained” refers to prompt IDs and exact prompt text, not byte-identical full
task rows. All 1,023 retained IDs/texts are unchanged. Because the unchanged
label-independent option-map algorithm assigns rotations from corpus-wide
sorted prompt rank, replacing nine prompts rotates `option_map` on 590
retained rows; 433 full task rows remain byte-identical. Every change is a pure
cyclic rotation (327 by one position, 249 by two, and 14 by three). No label,
prompt, ID, map contents, or construction algorithm changed.

The sealed v1.2 sources are bound by SHA-256:

- pair manifest: `f34151882216c35196bd0c26d80f7603bb371187efe3862fa6eacc96ef4b90c0`
- invalidation: `dc9a66283ad4a0a7cd7e5fd384f4d369232018aef1e4431bc2073cf8e23728fa`
- nine-row conflicts: `76188a8817ef236ef0a9afe7859d4e28546e08df388a5a553a337c6143780693`

## Implementation bindings

The clean pushed pending checkpoint must track and hash the v1.3 task,
catalog, answer, manifest, seed, configuration, this protocol, audit runner,
qualified mechanical core, v1.3 builder, standalone consensus verifier,
finalizer, v1.3 audit tests, and the sealed v1.2 blacklist manifest. It also
binds every project-code dependency executed through the inherited engines:
the base builder, v1.1 builder and audit runner, v1.1 verifier, and v1.1
finalizer. The configuration binds the exact path and SHA-256 of every
governance-critical code file. Historical verification authenticates the
recorded Git blobs and then requires every currently executing immutable
control to equal its authenticated historical bytes. Mutable pending/finalized
input artifacts are not subjected to that current-byte equality rule. The
fixed pre-audit corpus is:

- tasks: `79becaa213147f98146777bdf1e0cee7baf0afd2cdbfb4226daae6a961d58b0c`
- registry catalog: `97b751849bd26e6bd9f347d5153f4237d995e4e0f8eda289faaa18d75523b905`
- pending answer key: `e7de909cce9b8e10a8d148cac4a60012dfe4ac6e61d6034bdc7919dfbb0e44e1`
- pending benchmark manifest: `31d2c24f916b805bc9f70d9a582aead26468ae67788bf1e4bba6a11e94c06c30`

The runner refuses hash, path, Git checkpoint, session, or evidence drift. The
finalizer remains check-only by default. Its direct-script entrypoint must be
tested before checkpoint so `python scripts/finalize_px062_gate2_2_v13_labels.py`
reaches the intended evidence failure/success path rather than an import-path
failure.

Current, check-only, and historical consensus verification re-read and re-hash
every artifact in the reconstructed inventory. For each of the four canonical
evidence directories, the exact safe leaf-file set must equal the manifest
inventory; extra or missing leaves and symlink, junction, reparse-point, or
unsafe path aliases fail. Every lexical component from the repository root
through each evidence/control leaf is checked without following links. Regular
file leaves must have exactly one hard link, and duplicate stable filesystem
identities are forbidden even when roles and path strings differ. Before
writing the consensus manifest, the verifier rechecks the repository checkpoint
both before and after its final raw-inventory pass. Before the finalizer's first write,
it historically reconstructs the complete manifest, compares it with the
sealed bytes, revalidates the exact directory inventories, and rechecks that
all current immutable governance controls equal their historical blobs. Any
mutation leaves all finalization outputs unwritten.
