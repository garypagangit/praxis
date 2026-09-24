# PX-062 Gate 2.2 v1.2 Label-Audit Invalidation

**Status:** `LABEL_REVIEW_REQUIRED`
**Decision:** v1.2 is not eligible for Qwen/Mistral collection or an AWS
experiment launch.

Both fresh blinded audits completed mechanically. Historical verification
accepted all 438 byte-bound evidence artifacts and all 86 unique,
cross-audit-disjoint sessions at preregistered repository checkpoint
`08a5efc723959132c1bc4e03988fe3f2753e176a`.

The semantic gate failed exactly as preregistered. Of 1,032 rows, 1,023 had
three-way agreement between the authored answer and both auditors. The exact
nine-row nonunanimous union consists entirely of cross-auditor disagreements:

- audit 1 disagreed with 2 authored labels;
- audit 2 disagreed with 7 authored labels;
- the auditors disagreed with each other on all 9 rows; and
- there were no rows where both auditors selected the same alternative
  against the authored answer.

The nine rows include 1 available-skill task, 2 misleading-name real-skill
tasks, 3 misleading-name `NONE` tasks, and 3 unavailable-capability tasks.
They expose persistent boundary ambiguity around cache-busted plugin work,
official API guidance, generic incident automation and knowledge curation,
Word-native forms/styles/templates versus the registered PDF skill, and a
generic requirements-to-plan request. This is a label-design failure, not an
audit-runner or evidence-integrity failure.

The pinned verifier and the real check-only finalizer, imported from the
repository root, both terminate with the required semantic error:

```text
ValueError: label audits do not unanimously support the answer key
```

Neither wrote a provisional or final resolution. Canonical local collection,
launch, completion, and adjudication paths are absent. No target Qwen/Mistral
Gate 2.2 collection and no Gate 2.2 SageMaker job was launched.

No v1.2 row may be patched in place, no disputed-only audit is acceptable,
and neither audit may be rerun on unchanged v1.2 inputs to seek a pass. Any
continuation requires a new benchmark version with new corpus hashes and two
fresh full blinded audits. All v1.0, v1.1, and v1.2 corpus and audit evidence
remains immutable historical evidence.

## Canonical evidence seal

The write-once machine-readable invalidation is
`label_audit_invalidation.json` (SHA-256
`dc9a66283ad4a0a7cd7e5fd384f4d369232018aef1e4431bc2073cf8e23728fa`).
It binds the exact v1.2 tasks, answer key, registry catalog, benchmark
manifest, predictions, sidecars, pair manifest, verifier, and finalizer.

The nine nonunanimous rows are preserved in frozen task order in
`label_audit_conflicts.jsonl` (SHA-256
`76188a8817ef236ef0a9afe7859d4e28546e08df388a5a553a337c6143780693`).
Each row binds its exact prompt hash, authored answer, both predictions,
confidence values, notes, conflict class, and a canonical row hash.

Run the fail-closed validator from the repository root:

```powershell
python scripts/seal_px062_gate2_2_v12_invalidation.py --root .
```

The validator authenticates the audit pair in historical mode, recomputes all
bindings and aggregates, invokes both semantic rejection paths, and requires
every resolution and target-execution path to remain absent.

## Recorded direct-entrypoint defect

The frozen command `python scripts/finalize_px062_gate2_2_v12_labels.py`
resolves `scripts` incorrectly and stops at
`ValueError: canonical blinded audit-pair verification failed`, whose cause is
an import failure for the v1.2 audit runner. Running the same frozen finalizer
as `python -m scripts.finalize_px062_gate2_2_v12_labels`, or importing and
calling `prepare_finalization`, reaches the semantic rejection above.

This tooling defect does not change the sealed label-gate result and must not
be repaired inside the audited v1.2 checkpoint. A new benchmark version must
fix and test the direct entrypoint before its own checkpoint.
