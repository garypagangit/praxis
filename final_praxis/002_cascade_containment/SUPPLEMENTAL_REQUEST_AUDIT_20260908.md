# Additional request-integrity audit

Date: 2026-09-08. Added after the original source freeze and before experiment outcomes were inspected by this agent. The scientific harness, corpus, model, metrics and thresholds are unchanged.

Independent review identified an opportunity to strengthen request provenance: the frozen verifier compares public case data and the previous handoff but does not independently compare the complete system prompt and policy payload. `supplemental_audit/verify_exact_requests.py` supplies that additional read-only check, using a separately transcribed prompt and separately constructed payload rather than importing the production prompt constructor.

The supplement verifies all frozen hashes; exact role/system/user messages; the complete frozen policy; absence of unexpected hidden fields; both completed records and their raw pointers; and unique model-generation request IDs. When `--verify-tokenizer` is supplied in the cached model environment, it also checks that the actual prompt hash recorded by the model adapter equals the pinned tokenizer's chat-template rendering of the independently reconstructed request.

```text
python final_praxis/002_cascade_containment/supplemental_audit/verify_exact_requests.py <run-directory> --verify-tokenizer
```

The audit writes an additional verification receipt. It never changes model outputs or a scientific denominator. A failure is an integrity issue requiring explanation; it is not repaired by relabeling outcomes or changing scientific thresholds.
