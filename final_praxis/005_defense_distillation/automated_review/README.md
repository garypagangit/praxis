# Automated review of the 005 audit queue

This implements the user's request to replace the outstanding manual-review task with automated adjudication. It reads the original 28-case queue without changing any original labels, human fields, generations or training artifacts. Outputs explicitly distinguish automated consensus from human annotation. The historical human-adjudication criterion remains unfulfilled; it is a scientific limitation rather than another manual task assigned to the user.

Three separate Amazon Bedrock models assess each response under one frozen rubric. They never receive experiment arms, source model names, original judge labels, peer verdicts, control answers or selection strata. Eight authored controls qualify each reviewer. Four preselected duplicate cases measure repeat instability; unstable votes cannot decide those case/field labels. The panel requires two eligible agreeing votes, retains opposing votes, and leaves insufficient evidence unresolved. All 28 cases receive an automated workflow disposition.

This is a posthoc audit of known results, prospectively frozen before its own inference. It is not a new defense experiment, a validation against independent human ground truth, or permission to replace the original experiment-wide rates with estimates from this enriched sample. All eight original judge disagreements involve truncated responses.

The process uses the existing `praxis-build` profile and Bedrock in `us-east-1`; EC2 hosts remain stopped. A shared ledger caps estimated model API costs at $10. Raw private responses, request/response receipts and excerpts remain in ignored `outputs/`. The public report includes aggregates and provenance.

From this numbered branch, with the existing Python environment:

```powershell
python final_praxis/005_defense_distillation/automated_review/run_review.py --source PATH_TO_ORIGINAL_005_OUTPUTS
python final_praxis/005_defense_distillation/automated_review/run_review.py --source PATH_TO_ORIGINAL_005_OUTPUTS --execute
```

The first command validates frozen inputs without inference. The second requires committed protocol/source-lock bytes, enforces the budget and saves an immutable cell per planned request. Reusing the same output directory recovers existing successful cells without new calls. Interrupted requests lacking a final receipt are recorded as uncertain instead of being silently charged again. Failed or malformed judgments are retained rather than retried for a preferred answer. To analyze another queue, create a separately frozen protocol and run directory; the current source lock intentionally rejects changed inputs.

`report_review.py` independently reconstructs the adjudication from saved cells and writes the aggregate report without inference. `test_review.py` exercises blinding, strict parsing, reviewer qualification, vote rules and duplicate handling. Consult [PREREGISTRATION.md](PREREGISTRATION.md), [SOURCE_AUDIT.md](SOURCE_AUDIT.md) and [METHOD_REVIEW.md](METHOD_REVIEW.md) for the design and literature.
