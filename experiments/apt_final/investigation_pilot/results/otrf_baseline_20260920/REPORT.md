# Ordinary process identifiers already solve this investigation task

**Decision: NO-GO for a novel evidence selector on these questions.** The registered baseline screen is complete. Ordinary host/process-ID lookup recovered every available recorded answer without a wrong connection. Following the frozen rule, no new selector or LLM experiment was started.

## What we tested

From one public OTRF APT29 emulation recording, we froze 60 factual questions: 20 about a process's parent creation, 20 about a network connection's owning process creation, and 20 parent questions with repeated program names. Each answer required the actual creation record, image and UTC creation time. A process identifier mentioned elsewhere does not supply a missing creation timestamp.

An independent source parser verified all questions and reference answers before scoring. **38 questions had an answer in the qualified Sysmon creation table; 22 lacked a matching creation record in that table.** The questions involved 38 distinct target identities. They are related observations from one recording, not 60 independent attacks.

**Scope of unavailable evidence:** this screen uses Sysmon process-creation and network events. Other channels in the archive, including Windows Security logs, were not joined for alternative creation evidence. An insufficient result here does not establish that no other log source contains useful information. Cross-source identity reconstruction would be a different task requiring a new protocol and strong ordinary join baselines.

## Measured results

Both evidence limits (two or four source records including the question's anchor) produced the same answers.

| Method | Correct supported answers, out of 38 available | Wrong or unsupported answers | Appropriate abstentions on 22 unavailable cases | Unnecessary abstentions on answerable cases |
|---|---:|---:|---:|---:|
| Match program name and nearest earlier time | 30 | 16 | 14 | 0 |
| Match name/time, abstain when several processes fit | 12 | 0 | 22 | 26 |
| **Exact host and process GUID lookup** | **38** | **0** | **22** | **0** |
| Exact lookup with compact serialized identifiers | 38 | 0 | 22 | 0 |

The nearest-time method's 16 errors comprise eight incorrect identities where the proper creation record existed, and eight unsupported answers where it did not. The name/time abstention method avoided false answers by declining many questions that had a valid answer. Its low error count is therefore not equivalent to the exact method's performance.

For the name/time abstention method, the 22 safe non-answers include 14 correct insufficient-evidence responses and eight ambiguity responses. Thus the table's appropriate-abstention count does not imply that every explanation for abstaining was correct. Both exact methods gave the correct insufficient-evidence status for all 22 unavailable cases.

The exact method found all 14 available natural-parent answers, all eight available network-owner answers, and all 16 available difficult-parent answers. It required one index lookup per question and at most one additional creation record. Its answers were already achievable at the smaller evidence limit.

The difficult cohort is deliberately enriched. The pooled 16-error count describes these 60 selected questions; it does not estimate the natural population rate of investigator or LLM errors.

## Cost observations

Building the shared index over 447 creation records took about 2.36 ms in this run. Median latency over 31 repeated 60-question batches at the two-record limit was approximately 0.64 ms for exact lookup. These local timings are descriptive, include response serialization, exclude archive parsing, and are not deployment benchmarks. Timing repetitions are not additional scientific cases.

The exact representation averaged 906.23 serialized UTF-8 bytes per question; compact GUID aliases averaged 924.70 bytes after charging the reversible alias map. Thus this particular compact representation was about 2.0% larger. This is a byte count, not a token count, model-cost measurement or general conclusion about compression.

## Interpretation in plain language

Keeping the original process identifiers prevents the mistakes that arise from matching names and times. However, ordinary database lookup already provides that benefit. There is no remaining correctness gap in this task for a new selector to close, and the standard lookup already returns only the relevant record.

**This is useful engineering evidence, not a novel positive praxis result.** It does not show that LLM investigation is solved, that the proposed selector fails on every investigation task, or that missing telemetry can be reconstructed. No LLM was run. The endpoint is deterministic recorded-fact retrieval, not attack detection, malicious intent, attribution, full attack-story reconstruction or analyst time saved.

The known GUIDs make this an intentionally inexpensive screening task. Exact lookup's ceiling is expected from the information available. Independent source parsing validates the execution and prevents a parser/scorer mistake; it does not turn this lookup comparison into evidence of new intelligence.

## Frozen protocol, validation and evidence

- [Protocol](../../PROTOCOL.json) frozen in commit `c676234`, before question preparation or method scoring.
- [Question/hash manifest](../../CASE_MANIFEST.json) and source preparation frozen in `1360c6f`.
- Methods, scorer and [independent source audit](../../REFERENCE_AUDIT.json) committed in `fa23a6f`; the audit verified all 1,676 relevant source records and all 60 reference answers.
- Seventeen focused synthetic tests passed before execution; tests committed in `f114185`. Nine independent parser/identity checks also passed during source-audit qualification.
- [Full results](RESULTS.json), [480 individual method/budget predictions](PREDICTIONS.jsonl), and [execution/hash receipt](RUN_RECEIPT.json). The 480 rows are four methods times two budgets times 60 questions, not 480 independent cases.
- [Independent results audit: PASS](RESULTS_AUDIT.json). All 480 predictions, pooled/stratified metrics, record budgets, evidence bytes and the stopping decision were independently checked without importing or rerunning the evaluated methods. Eleven deliberate corruption checks plus a valid-prediction check passed. Raw timing samples were not retained, so the audit verifies timing-summary consistency only.
- The `correct_reason` metric in the JSON means status-label agreement only; identity correctness is separately measured by `correct_supported_answer`. It must not be interpreted as overall answer accuracy.
- No AWS instance was started; no model trained; no telemetry executed. Original logs and normalized source excerpts remain outside Git.

## What follows

Close the novel-selector proposal for this dataset and these direct-identity questions. Do not remove identifiers, make the baseline return irrelevant events, or redefine the task after seeing the result to manufacture an improvement.

The next candidate in the [shortlist](../../../docs/APT_PIVOT_SHORTLIST_20260920.md) is actor-invariant technique extraction from threat reports. Its own natural failure, annotation alignment and improvement beyond name masking must be established before calling it promising. The new CTI readiness audit is preparation, not another positive experiment.

No human action is required to finish this screen. A later study of attack intent or analyst usefulness would need a separate reviewed evaluation. Prior MAGIC studies remain unchanged and closed.
