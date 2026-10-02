# Syntax-only replay amendment

Added during the first successful inference allocation, after observing that Qwen wrapped a response in a Markdown JSON code fence. The original frozen parser accepts bare JSON only and its results remain the primary operational record.

A separately labeled replay removes exactly one complete outer Markdown fence (` ```json ` or ` ``` `, with a closing ` ``` `), then applies the original PX-098 JSON schema. It does not change the answer, reason, prompt, model, input, sample membership, alert threshold or labels. Incomplete output, extra surrounding text, unsupported answers and malformed JSON remain invalid. No response is regenerated.

Report both strict and syntax-normalized counts. The normalized replay is posthoc and must not be described as preregistered. This diagnoses and fixes output formatting; it does not create evidence of model accuracy. PX-099 schema and host/time validation remain separate, and a bare interval list does not satisfy its frozen object schema.
