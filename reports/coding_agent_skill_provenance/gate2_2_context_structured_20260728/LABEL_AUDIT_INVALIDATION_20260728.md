# PX-062 Gate 2.2 v1.0 Label-Audit Invalidation

**Status:** `LABEL_REVIEW_REQUIRED`
**Decision:** v1.0 is not eligible for Qwen/Mistral collection or an AWS experiment launch.

The two blinded audits completed mechanically and the pair verifier accepted all
86 isolated sessions. The semantic acceptance gate then failed exactly as the
preregistration required: 999 of 1,032 rows were unanimously supported, but 33
rows were not. Audit 1 agreed with 1,012 frozen labels, audit 2 agreed with
1,004, the auditors disagreed with each other on 19 rows, and on 14 additional
rows both auditors selected the same alternative against the authored label.

The failed rows cluster around visible-context ambiguity rather than evidence
or runner failure:

- platform-neutral deployment wording did not distinguish Netlify, Vercel, or
  Render;
- several intended `NONE` requests remained broad enough to match Linear,
  PDF, ASP.NET Core, Playwright, or Notion descriptions;
- two design tasks did not identify Figma or an editable Figma deliverable;
- one security-review task requested Java even though the registered skill's
  frozen description does not support Java.

No row in v1.0 will be patched, neither audit will be rerun on unchanged
inputs, and no disputed-only audit will be accepted. The replacement must be a
new benchmark version with new hashes. It may preserve byte-identical rows that
were not corrected, but the complete 1,032-row replacement corpus must receive
two fresh, full, independent blinded audits. The v1.0 predictions, sidecars,
per-attempt evidence, pair manifest, and this invalidation record remain
immutable historical evidence.

No model-facing Gate 2.2 collection and no SageMaker Gate 2.2 training job was
launched before this failure was detected.

## Canonical evidence seal

The machine-readable invalidation is
`label_audit_invalidation.json` (SHA-256
`3c0a3d83877ea2eb5b8fc829e92cd9661b72ac5cf8c016ae145a5fd3dd3a9e42`).
It binds the exact task, answer-key, catalog, benchmark-manifest, prediction,
sidecar, and audit-pair-manifest paths and hashes at repository checkpoint
`5b9bea8205a52df973b037eee12454af7783df8a`. The pair manifest in turn binds
438 byte-verified evidence artifacts and 86 unique, cross-audit-disjoint model
sessions.

All 33 nonunanimous rows are preserved in frozen task order in
`label_audit_conflicts.jsonl` (SHA-256
`5b899e78cac1ee60c7fafbe37088c3ce58221c6f55680964235b896b1fc91c0c`).
Each row contains the task type, a hash of the exact prompt, the authored
answer, both auditors' predictions, confidences, and notes, a conflict class,
and a canonical row hash. Nineteen rows are `AUDITORS_DISAGREE`; fourteen are
`BOTH_AUDITORS_SAME_ALTERNATIVE`.

Run the fail-closed validation from the repository root:

```powershell
python scripts/seal_px062_gate2_2_v1_invalidation.py --root .
```

The validator recomputes every binding and aggregate, requires the
provisional and final resolution files to be absent, and invokes the real
check-only finalizer. The expected terminal failure is exactly
`ValueError: label audits do not unanimously support the answer key`; any
other result fails validation.
