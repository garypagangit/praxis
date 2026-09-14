# Development-only format diagnosis and minimal technical extension

The development diagnosis supports **schema-constrained Qwen review output with the existing 1,024-token cap**. It does not support a larger token cap. This recommendation uses development-format metadata and frozen source inspection only; no heldout outcomes or scientific-effect estimates were inspected.

The filtered receipt `reports/praxis_20260914_code_study/DEVELOPMENT_FORMAT_DIAGNOSIS.json` has SHA256 `cb28a4e5656d9f0803950f3a26ec20738a74e38aa61cc96a4ed6cf862ebc0e9c`. It reports 102 invalid Qwen development reviews, all with terminal `end_turn` and `invalid_review_format`; none were reported as truncated. The eight retained examples use 37–401 output tokens, below the 1,024-token cap. These previews are illustrative rather than a complete independent classification of all 102 full response strings. The aggregate technical gate was 430/532 valid for Qwen and 530/532 for Devstral. The diagnosis provides no evidence about comparative scientific effectiveness.

Frozen [parse_review](../prompts.py#L138) first checks the terminal stop reason, then requires one JSON object with exactly the string fields `decision` and `reason`, with decision normalized to `accept` or `keep`. Invalid format remains an abstention. A 4,096-token request would not directly address normally terminated malformed JSON and would change the compute allowance without a truncation-based justification.

AWS's [Qwen3 Coder Next model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-coder-next.html) lists structured outputs on `bedrock-runtime`. The [structured-output documentation](https://docs.aws.amazon.com/en_en/bedrock/latest/userguide/structured-output.html) specifies `outputConfig.textFormat` for Converse requests. The frozen adapter already implements that request field. Schema constraints do not eliminate the need to check termination: AWS also notes that [token limits or refusals can prevent a conforming completed response](https://aws.amazon.com/blogs/machine-learning/structured-outputs-on-amazon-bedrock-schema-compliant-ai-responses/). These primary-source pages were checked on 2026-09-14 UTC; endpoint acceptance still requires the separately authorized runtime probe.

## Recommended change and invariants

[adapter.py](adapter.py) exports `StructuredReviewAdapter`, a subclass of the frozen `bedrock_adapter.BedrockAdapter`. The extension runner can supply this class where the frozen runner normally constructs its adapter. It applies the following changes only to `qwen.qwen3-coder-next` review calls:

- Require the unchanged `REVIEW_SYSTEM`, an explicit `review-` request ID, temperature zero, and `max_new_tokens=1024`.
- Add the JSON schema with required `decision` and `reason` string fields, decision enum `accept`/`keep`, and `additionalProperties=false`.
- Prefix the request ID with `v2-`, idempotently, to separate receipts/cache identity from the original run.

The actual system/user message objects are passed through unchanged. Proposal generation, other models, parser semantics, native/generated program execution, test selection, eligibility, and outcome scoring are unchanged. The subclass uses the inherited caller-supplied budget ledger; it neither creates a separate spending allowance nor makes API calls on import. The root extension protocol must explicitly choose the shared $30 ledger or a separate capped allowance within the overall authorized envelope.

## Freeze and reporting requirements

The root extension protocol must freeze the adapter/schema hashes, assignments, technical validity threshold, spending bound, retry policy, and development-to-heldout gate before any extension call or heldout outcome inspection. Re-run the complete prespecified eligible development assignment set under the new interface, rather than rescuing only previously invalid responses. Retain the complete version-one results and failed technical gate. Keep version-two estimates separate from version one and identify the interface configuration in every report.

Schema-constrained decoding can change substantive accept/keep behavior as well as syntax. Any scientific difference between versions cannot be attributed solely to repaired JSON formatting. Version two is a separately reported interface configuration, not a retrospective reparse or replacement of version-one decisions.

Admission to a heldout extension must depend only on the newly frozen technical gate. A format gate cannot justify selecting a configuration by its scientific effect. The extension should preserve the current proposal-generation configuration; no development-only review-format evidence supports modifying proposal generation. This file recommends the implementation boundary; it does not itself authorize a run, define the final extension sample, or declare the new gate passed.
