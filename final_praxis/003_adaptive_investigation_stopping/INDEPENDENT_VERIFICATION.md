# Final Praxis 003 independent verification

**Frozen cloud verification: PASS. Supplemental local numerical replay: PASS. Strict local exact-float replay: failed.**

The unchanged frozen verifier checked all 400 cases / 3,200 rounds in the cloud, including unique identities, model revision/runtime, opaque evidence projections, protocol and raw hashes, independently recomputed policy decisions, harm/prevention/review counters, intervals and final gates. The archived cloud classification is Negative.

The immutable downloaded ZIP has SHA-256 `d0280c134ade9d0e1e0d90630386247a7da99aa755d9616653ef575961e60b44`. Its raw JSONL has SHA-256 `13a97bf948a7baf5f55fe7929e0cf4b05fea3fefb2117b08e0795702ba79871c`.

A local run of the unchanged verifier rejected an exact floating equality: A1's imported harm upper bound was `0.007461355528799602`, versus local SciPy `0.007461355528799601`. This failure is retained and is not described as a strict local PASS.

A separate supplemental audit permitted absolute floating equality differences <=1e-14 while preserving exact inequalities, gate booleans, counts, hashes and input identities. It found three beta-quantile differences, with maximum absolute delta `9.71445146547012e-17`. Every frozen threshold decision and the Negative classification remained unchanged. No source analysis value, cloud receipt, threshold or frozen code was modified.

Tracked receipts:

- [Strict local attempt](paper/evidence/STRICT_LOCAL_VERIFIER_ATTEMPT.json).
- [Supplemental numerical replay](paper/evidence/SUPPLEMENTAL_NUMERIC_REPLAY.json).

The full frozen cloud receipt remains in `artifacts/discovery/qwen_20260908_v2/INDEPENDENT_VERIFICATION.json`; the supplemental auditor is `paper/verify_portable.py` and is explicitly separate from the frozen scientific verifier.
