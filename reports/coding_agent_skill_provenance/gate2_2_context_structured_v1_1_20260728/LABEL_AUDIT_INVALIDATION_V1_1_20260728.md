# PX-062 Gate 2.2 v1.1 Label-Audit Invalidation

**Status:** `LABEL_REVIEW_REQUIRED`
**Decision:** v1.1 is not eligible for Qwen/Mistral collection or an AWS
experiment launch.

Both fresh blinded audits completed mechanically. The historical pair verifier
accepted all 438 byte-bound evidence artifacts and all 86 unique,
cross-audit-disjoint sessions at preregistered repository checkpoint
`ed8dbf2c7fbef930a1c38830ccfcfe7e7d9a2a9b`.

The semantic gate nevertheless failed exactly as preregistered. Of 1,032 rows,
1,022 had three-way agreement between the authored answer and both auditors.
The exact 10-row nonunanimous union consists of:

- 3 disagreements between audit 1 and the authored answer;
- 9 disagreements between audit 2 and the authored answer;
- 8 rows where the two auditors disagreed with each other; and
- 2 rows where both auditors selected the same alternative against the
  authored answer.

The 10 rows span four task types: 1 available-skill row, 2 misleading-name
`NONE` rows, 3 misleading-name real-skill rows, and 4 unavailable-capability
rows. The remaining ambiguity is visible in requests that can reasonably be
read as Word/PDF styling, ASP.NET messaging, Linear project administration,
Figma implementation, plugin development, or Render deployment. This is a
label-design failure, not an audit-runner or evidence-integrity failure.

The pinned verifier and the real check-only finalizer both terminate with the
required error:

```text
ValueError: label audits do not unanimously support the answer key
```

Neither tool wrote a provisional or final label-resolution file. Canonical
local model-output, launch-registration, launch-receipt, completion, and
adjudication paths are also absent. No target Qwen/Mistral Gate 2.2 collection
and no Gate 2.2 SageMaker job was launched.

No v1.1 row will be patched in place, no disputed-only audit is acceptable,
and neither audit may be rerun on unchanged v1.1 inputs to seek a pass. Any
continuation requires a new benchmark version with new corpus hashes and two
fresh full blinded audits. All v1.0 and v1.1 corpus and audit evidence remains
immutable historical evidence.

## Canonical evidence seal

The write-once machine-readable invalidation is
`label_audit_invalidation.json` (SHA-256
`5fb5e72d9db7cde210041baea33ab551b89a43772580ccf7d74391a50ba4f09e`).
It binds the exact v1.1 tasks, answer key, registry catalog, benchmark manifest,
predictions, sidecars, pair manifest, verifier, and finalizer.

The 10 nonunanimous rows are preserved in frozen task order in
`label_audit_conflicts.jsonl` (SHA-256
`bf89fd32a617e90315bd9f3aaa08aee3cbf4ab8f2e47db08455c249233bdeea6`).
Each row binds its exact prompt hash, authored answer, both predictions,
confidence values, notes, conflict class, and a canonical row hash.

Run the fail-closed validator from the repository root:

```powershell
python scripts/seal_px062_gate2_2_v11_invalidation.py --root .
```

The validator authenticates the audit pair in historical mode, so it continues
to verify when the sealed checkpoint is an ancestor of a later commit. It
recomputes all bindings and aggregates, invokes both rejection paths, and
requires every resolution and target-execution path to remain absent.
