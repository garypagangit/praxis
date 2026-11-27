# PX-062 Gate 2.2 v1.3 Label-Audit Invalidation

Status: INVALIDATED_LABEL_AUDIT_SEMANTIC_GATE_FAILED

Decision: v1.3 is not eligible for Qwen/Mistral target collection or an AWS
experiment launch.

All four fresh blinded passes completed mechanically. Historical
authentication reconstructed all 873 byte-bound artifacts, re-read the 860
per-attempt raw evidence files, and accepted all 172 unique sessions at the
preregistered Git checkpoint 0291f2052b312a740cfb9779e2895bd4942330eb. There were zero retries.

The prospectively frozen semantic rule required every answer-key row to
receive at least three of four votes, including support from both model
families. Of 1,032 rows:

- 1,023 were unanimous with the frozen answer;
- 8 had one dissent and were accepted by the preregistered rule;
- 1,031 total rows were accepted; and
- 1 row failed the rule, invalidating the complete v1.3 benchmark.

The rejected row is g22-ba732261f65ca75f9d2e. Its frozen answer is Linear.
Both Sol passes selected NONE, while both Terra passes selected Linear. The
frozen answer therefore received only two votes and no Sol-family support.
This is an observed model-family boundary disagreement, not a mechanical
runner or evidence-integrity failure.

The pinned verifier and real check-only finalizer both terminate with:

    ValueError: label audits do not satisfy balanced 3-of-4 consensus on all 1032 rows

Neither wrote a provisional or final label resolution. Canonical collection,
launch, completion, and adjudication paths are absent. No target-model
collection and no SageMaker job was launched.

No v1.3 row may be patched in place, no disputed-only rerun is acceptable,
and the unchanged inputs may not be rerun to seek a pass. The four v1.3
audits remain immutable historical evidence and cannot be reused as
acceptance evidence for a successor version.

## Canonical evidence seal

The write-once invalidation record is label_audit_invalidation.json with
SHA-256 8878a20c6fedda90f28721f26f7f370576a018f2892c4309ae1fb43a3f498e43.

The nine nonunanimous rows are preserved in frozen task order in
label_audit_conflicts.jsonl with SHA-256 c2f8de446ca40552106116ea3875313b352864242a65e0ede99bef30832b439b. The ledger
distinguishes the eight accepted single-dissent rows from the one rejected
balanced-consensus row and binds every prompt, answer, four predictions,
confidence values, notes, outcome, and canonical row hash.

Run the fail-closed validator from the repository root:

    python scripts/seal_px062_gate2_2_v13_invalidation.py --root .

The validator authenticates the historical preregistration checkpoint,
reconstructs the exact evidence inventory, re-hashes every raw artifact,
re-evaluates balanced consensus, invokes both semantic rejection paths, and
requires all resolution and target-execution paths to remain absent.
