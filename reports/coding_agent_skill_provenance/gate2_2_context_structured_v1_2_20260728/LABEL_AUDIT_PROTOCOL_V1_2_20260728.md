# PX-062 Gate 2.2 v1.2 blinded label-audit protocol

**Experiment:** `px062-skill-selection-gate2-2-v1-2-20260728`

**Construction status:** pending corpus is target-outcome-blind and cannot
authorize Qwen, Mistral, or AWS collection.

## Required fresh audit pair

Version 1.2 requires two new complete blinded audits over all 1,032 rows.
Slot 1 uses `gpt-5.6-sol`; slot 2 uses `gpt-5.6-terra`. Each slot must use 43
fresh stateless ephemeral sessions containing 24 tasks apiece, high reasoning,
model-default sampling, the frozen strict JSON schema, a 1,800-second attempt
timeout, and the same disabled-tool command boundary as v1.1.

Each auditor receives only the frozen 43-entry semantic registry projection
and the `task_id` and `prompt` fields. Option maps, answer labels, seed
scenarios, v1/v1.1 predictions, conflict ledgers, invalidation records, and
the other auditor's output are withheld.

Acceptance requires both sealed audits and the pending answer key to agree on
all 1,032 tasks. A mechanically invalid attempt may receive at most one
byte-identical retry. There is no semantic retry. Any semantic disagreement
sets `LABEL_REVIEW_REQUIRED`, invalidates v1.2 for collection, and requires a
new benchmark version plus two further full fresh audits.

The v1 and v1.1 predictions are revision evidence only. They are forbidden as
v1.2 acceptance decisions, warm starts, examples, prompt material, or partial
substitutes. Disputed-only reaudit is forbidden.

## Frozen scientific boundary

The registry names and descriptions, task counts and strata, hypotheses,
arms, model revisions, decoding, efficacy and harm thresholds, multiplicity
rule, and determination logic remain unchanged. Only the ten v1.1
nonunanimous prompt scenarios are prospectively replaced. No Qwen or Mistral
Gate 2.2 target outcome existed when v1.2 was constructed.

The v1.2 audit runner and adversarial audit tests remain a pre-checkpoint
implementation gate. Until their exact hashes replace the pending markers in
the v1.2 configuration, the corpus is not audit-eligible or launch-eligible.

## Versioned implementation bindings

The pending audit checkpoint must hash and track all of the following inputs:

- `scripts/run_px062_gate2_2_v12_blind_audit.py`
- `scripts/run_px062_gate2_2_blind_audit.py` (the qualified mechanical core)
- `tests/test_px062_gate2_2_v12_blind_audit.py`
- this protocol, the v1.2 configuration and seed bank, and all four v1.2
  frozen-input files

Post-audit verification and finalization use the new-only v1.2 wrappers
`scripts/verify_px062_gate2_2_v12_label_audits.py` and
`scripts/finalize_px062_gate2_2_v12_labels.py`. Their explicitly declared
dependencies are the v1.1 verifier/finalizer engines and the v1.2 benchmark
builder. They cannot substitute v1.1 prediction evidence for either fresh
v1.2 slot.

The pre-audit corpus bindings are:

- tasks: `e9a4c387781b7299884d75ebbb59f3ba1dcd398599821fb586db95e02fabea16`
- registry catalog: `90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212`
- pending answer key: `c9fb2c8be3ee200050f709a046109c42884aea741e980371837bd58f741f3913`
- pending benchmark manifest: `93a126f0fed68d259caae32bd2a0eae8af4f656bbebdcda07dac880aa9e3eb57`

The runner must refuse any hash or path drift before starting the first
ephemeral session. Pair verification must require 86 accepted, globally
unique session IDs (43 per slot), two distinct full prediction files in exact
task order, and no overlap between slots. Finalization remains check-only by
default and may write only after three-way unanimity on every row.
