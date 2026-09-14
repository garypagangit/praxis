# Version-two adapter source review

Reviewed `technical_extension/adapter.py` at SHA256
`6ae612a87441d50100827417e8ed36abee7ea01872562460843b06964f9cd9b4`.
The source matches its declared narrow routing: only Qwen review requests receive
the exact copied JSON schema, unchanged 1,024-token limit and temperature, and a
version-two request namespace. The supplied message objects and seed pass through;
proposal calls and other models delegate without that schema. Importing the
adapter does not call a model. The inherited ledger remains in force.

This is a source review, not verification that the hosted endpoint accepts the
schema. The separate protocol requires a logged synthetic warmup and a complete
development gate before heldout inference. Provider-constrained decoding can alter
substantive accept/keep decisions as well as formatting, so version-two scientific
effects must remain separately identified.

The accompanying runner review identified a required correction before freeze:
Qwen heldout permissions must use the conjunction of both development cohort gates,
as the version-two protocol specifies. Actual measured development gate files must
remain intact; an effective heldout permission artifact can record the conjunction.
Warmup cache reuse should also verify schema, protocol and raw-result hashes.
These findings were sent to the coordinator for the separately owned extension;
this note does not assert that a version-two gate has passed or that its scientific
results were inspected.
