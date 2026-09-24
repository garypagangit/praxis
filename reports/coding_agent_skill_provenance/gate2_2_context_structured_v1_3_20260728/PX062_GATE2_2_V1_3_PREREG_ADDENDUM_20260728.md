# PX-062 Gate 2.2 v1.3 preregistration addendum

**Experiment ID:** `px062-skill-selection-gate2-2-v1-3-20260728`

**Protocol version:** `2.2.3`

**Status:** construction pending deterministic freeze; four fresh independent
full label-audit passes required; target-model collection prohibited.

## Revision basis

The sealed v1.2 audit pair was mechanically valid but failed its semantic gate:
audit 1 disagreed with the key on two rows, audit 2 on seven, and the complete
nonunanimous union contained nine rows. Version 1.3 replaces exactly those nine
scenarios, preserves their intended labels/task types/source slots, and retains
the other 1,023 prompt IDs.

The revisions make the intended platform or native operation objective:

- four Microsoft Word `NONE` tasks now require Word-native editable-DOCX or
  DOTX fields, controls, lists, or Building Blocks outside PDF scope;
- one Jira Service Management automation task is explicitly not Linear;
- one Confluence page-property/macro task is explicitly not Notion capture;
- the OpenAI documentation task names the Responses API streaming boundary;
- the Notion task names its specification-to-tracked-implementation workflow;
  and
- the Codex plugin task names the frozen manifest and marketplace-entry scope.

The exact old/new prompts, deterministic task IDs, audit decisions, seed slots,
and semantic boundaries are frozen in the v1.3 task-lineage artifact.

All 1,023 retained task IDs and exact prompt strings are unchanged, but not
every full task row is byte-identical. The label-independent option-map
rotation uses corpus-wide prompt rank, so nine replacements rotate 590 retained
maps while 433 remain identical. The changes are pure cyclic shifts (327 by
one, 249 by two, and 14 by three); option values, prompts, IDs, labels, and the
mapping algorithm remain unchanged.

## Prospective governance redesign

The old rule required both fresh auditors and the key to agree on every row.
It was empirically non-convergent: on the 1,022 prompts carried unchanged from
v1.1 to v1.2, Sol changed two decisions and Terra changed five, and all seven
new decisions turned previously correct unanimous rows into conflicts.

Before any Qwen or Mistral output, v1.3 instead freezes four full passes: two
Sol and two Terra. Each row needs at least three key-matching votes plus key
support from both model families. A single dissent is evidence, not automatic
invalidation. Every other vote pattern fails the version. No semantic retry,
disputed-only rerun, same-version prompt edit, or relabel is permitted.

Every slot blacklists the exact 86 accepted session IDs sealed by the v1.2
pair manifest. Execution order is immutable: slot 1, then 2, then 3, then 4.
A slot cannot create evidence unless all predecessors are canonical and
complete and its own and all successor evidence is absent. Every attempt's
complete `thread.started` ID set is reconstructed from raw event bytes,
including failed and multiple-ID logs, so a sealed ID cannot hide behind a
`null` singleton session field.

The tradeoff is explicit: v1.3 does not claim four-auditor unanimity. It tests
stable, balanced supermajority support and doubles audit cost to 172 accepted
sessions. The v1.2 evidence is revision provenance only and cannot fill a v1.3
slot.

## Unchanged experiment boundary

All hypotheses, target arms, Qwen/Mistral model IDs and revisions, task and
label counts, registry semantics, option-map construction, decoding, efficacy,
harm, integrity, multiplicity, decision rules, and claim boundary remain
unchanged. Construction and all four label audits precede target-model
collection. No AWS launch or target outcome may be used to revise v1.3.

## Mandatory order

1. deterministically freeze v1.3 seed, lineage, config, and four inputs;
2. pass construction, audit-runner, consensus-verifier, finalizer, direct-CLI,
   regression, and byte-preservation tests;
3. commit and push the exact pending 0/4 checkpoint;
4. run four complete fresh audits in fixed slot order with 172 globally unique
   accepted sessions;
5. seal the evidence manifest and apply the frozen row-level consensus rule;
6. finalize audited labels only if all 1,032 rows pass; and
7. only then freeze and launch the Qwen/Mistral Gate 2.2 collection once.

The checkpoint binds the v1.3 builder, runner, standalone verifier, finalizer,
protocol and tests, the sealed v1.2 blacklist manifest, and the bounded
inherited project-code chain: the base builder and audit core plus the v1.1
builder, runner, verifier, and finalizer. Historical consensus and finalization
require current immutable control bytes to equal authenticated historical
blobs. Current, historical, and final pre-write verification also require the
exact safe leaf set in all four canonical evidence directories to equal the
manifest inventory; extra, missing, linked, reparse, or aliased files fail
before any governance output is written. This check walks every lexical path
component from the repository root, rejects linked/reparse ancestors and
leaves, requires a hard-link count of one for regular files, and rejects
duplicate stable filesystem identities. The repository checkpoint is also
revalidated after the final inventory pass and immediately before the
consensus-manifest existence check and write.
