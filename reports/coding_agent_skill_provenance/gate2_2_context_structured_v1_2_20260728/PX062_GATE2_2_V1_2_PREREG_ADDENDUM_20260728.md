# PX-062 Gate 2.2 v1.2 preregistration addendum

**Experiment ID:** `px062-skill-selection-gate2-2-v1-2-20260728`

**Protocol version:** `2.2.2`

**Status:** construction complete; two fresh independent full label audits
required; target-model collection prohibited.

## Why v1.2 exists

Gate 2.2 v1.1 failed its preregistered semantic label gate before any Qwen,
Mistral, SageMaker, or other Gate 2.2 target-model collection. Its two sealed
audits were mechanically valid, but the answer key and both auditors were not
unanimous on ten of 1,032 rows. The canonical v1.1 invalidation and conflict
ledger are bound by the v1.2 seed, config, and lineage artifacts.

Version 1.2 is label-audit-informed but target-outcome-blind. It replaces the
complete ten-row conflict union, retains the other 1,022 prompts and task IDs,
and does not reuse any v1.1 prediction as an acceptance decision.

## Frozen revision boundary

The ten revisions clarify only the intended semantic boundary:

- two Figma-to-code tasks now identify their Figma source;
- two editable Microsoft Word tasks now identify Word-native style controls;
- two Jira administration tasks now identify Jira rather than a generic team
  workflow;
- one Redis Pub/Sub task now identifies Redis rather than generic application
  notifications;
- one Render task now identifies its Render Blueprint workflow;
- one Codex plugin task now asks for structure and marketplace-entry work that
  is inside the frozen plugin-creator description; and
- one Microsoft Teams task now identifies the Teams platform.

The exact old/new requests, IDs, intended labels, task types, source audit
decisions, and reasons are frozen in
`../../../manifests/px062_gate2_2_v1_2_20260728/task_lineage.json`.

The following remain unchanged from v1.1: all hypotheses; arms A-E; registry
names and descriptions; Qwen and Mistral IDs and revisions; task and label
strata; decoding; message templates; efficacy, harm, integrity and
multiplicity gates; determination rules; and claim boundary. The
collection-visible identity namespace and label-independent option-map salt
also remain unchanged.

## Pending construction artifacts

| Artifact | SHA-256 |
|---|---|
| Seed bank | `b504f37942c6bb4103cfa20ac9b89cc2bb56b6e49ad9187883cff9e3aa201cce` |
| Tasks | `e9a4c387781b7299884d75ebbb59f3ba1dcd398599821fb586db95e02fabea16` |
| Pending answer key | `c9fb2c8be3ee200050f709a046109c42884aea741e980371837bd58f741f3913` |
| Registry catalog | `90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212` |
| Benchmark manifest | `93a126f0fed68d259caae32bd2a0eae8af4f656bbebdcda07dac880aa9e3eb57` |
| Lineage map | `36dbb89d20e38dab7ebfbde13008187306fa0275b025efe5627b1b42eb2b9835` |
| Pending configuration | `8ccd093686dde9f977fc18fe9250c49a17555cd3a5a2f5b54532346957519ca5` |

All construction gates pass. The grouped shallow lexical diagnostic is
`0.823643`, below the frozen exclusive limit of `0.85`. Every option value
appears 23-24 times per local position globally, 15-16 times in direct tasks,
and 7-8 times in misleading tasks. Counts remain 516 registered and 516
`NONE`, with 344/344/172/172 task-type balance. Freshness, uniqueness,
repeated-phrase, catalog-copy, canonical-answer-mention, and label-independent
information-flow gates pass.

## Mandatory remaining gates

Construction does not authorize collection. Before launch:

1. freeze a v1.2-specific audit runner and adversarial audit tests and replace
   the two pending hash markers in the configuration;
2. commit and push the exact 0/2 checkpoint;
3. run two complete fresh 1,032-row blinded audits, 43 new sessions per slot;
4. require both audits and the answer key to agree on all 1,032 rows;
5. finalize labels and freeze all source, tokenizer, bundle, AWS, fetch, and
   adjudication hashes; and
6. only then run the Qwen and Mistral experiment once.

Any v1.2 semantic disagreement invalidates v1.2. A disputed-only rerun or
reuse of v1/v1.1 predictions is forbidden.
