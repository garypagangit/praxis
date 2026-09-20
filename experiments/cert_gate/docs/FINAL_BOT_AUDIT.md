# Final automated review audit

Date: 20 September 2026. Status: **completed, negative label-agreement result**. This was a blinded bot review, not human review or independent adjudication of attack truth.

## Result

The fixed Qwen reviewer processed all 50 reserved cases. **Ten of 50 answers agreed with the existing dataset labels: 20.0%.** Thirty-four responses passed the response validator, and every one of those said `Attack`. Sixteen were converted to `Unable to verify` by the validator. None was accepted as `Non-Attack`.

| Existing dataset label | Bot: Attack | Bot: Non-Attack | Validator: Unable to verify | Total |
|---|---:|---:|---:|---:|
| Attack | 10 | 0 | 1 | 11 |
| Non-Attack | 24 | 0 | 15 | 39 |
| Total | 34 | 0 | 16 | 50 |

Agreement among the 34 decided cases was **29.4%**, which must not replace the primary 50-case denominator. The automatic 45-of-50 agreement benchmark was not met. The 24 `Attack` decisions on dataset-negative cases are disagreements with those labels, not independently proven false accusations or proof that the dataset is wrong. [Graded aggregate](../results/automated_review_20260920/RESULTS.json), [independent recount](../results/automated_review_20260920/RECOUNT.json)

The automated reviewer produced **zero accepted benign decisions**, so it offers no demonstrated automatic-closure utility on this sample. Runtime completion is not a positive scientific result.

## Why 16 responses were rejected

| Validation outcome | Cases | Interpretation |
|---|---:|---|
| Valid response with required exact citations | 34 | Output format and citation presence passed; semantic reasoning was not independently verified. |
| Reached the frozen 512-output-token limit | 14 | The validator rejected potentially incomplete responses. Raw-output parsing also found 14 invalid JSON responses. |
| Citation was not an exact substring of its named visible field | 2 | Two otherwise JSON-parseable responses contained three invalid quotations in total. |
| Input exceeded 16,384 tokens | 0 | No input-limit failure. |
| Input truncated | 0 | No truncation. |
| Model/worker runtime exception | 0 | No recorded inference exception. |
| Missing, unknown or malformed worker record | 0 | All 50 worker records were present and matched known cases. |

All 16 unable outcomes were **validation failures**, not accepted model judgments that evidence was insufficient. The two citation failures concerned response-body text in one case and request/response headers in another. Basic URL decoding, HTML unescaping and whitespace normalization did not make those quotations match. This diagnostic did not repair or regrade them.

The valid responses contained 94 citations. All 34 cited `rule_name`, and all also cited at least one other field; therefore this was not literally rule-name-only citation. Only two cited response-body evidence. A simple, nonexclusive keyword diagnostic found attempt/probe/scan terms in 32 of the 34 valid reasons. These observations suggest an emphasis on attack-looking request evidence, but they do not prove a causal shortcut or establish the correct interpretation of any case.

The output cap is a real implementation limitation, but it cannot explain the entire negative result. Holding the 34 accepted decisions fixed, even a hypothetical perfect replacement of all 16 rejected responses would yield at most **26/50 = 52%** agreement. This is an arithmetic bound for that hypothetical, not a result from a rerun.

## Target-definition check

We investigated the hypothesis that the source benchmark labels unsuccessful attempts `Non-Attack`, while our prompt labels attempts `Attack`. **That mismatch was not established.** The author's pinned RQ1 evaluation prompt explicitly includes **“an attack attempt”** in its `Attack` definition. Its `Non-Attack` description covers benign activity, normal operations, false positives and informational events. [Primary RQ1 prompt, lines 237–245](https://github.com/Dxsssu/SecAlertBench/blob/42a84889fda912ca432c994924a1ccd4b9df6274/0x03.%20Evaluation%20Scripts/RQ1/run_rq1_transformers_test_eval.py#L237)

The pinned README also shows an `Attack` example with an HTTP 400 response. An error response therefore cannot be treated as evidence that the benchmark universally labels failed attempts negative. The complete annotation/adjudication policy and complete enterprise context were not verified here. [Primary author README](https://github.com/Dxsssu/SecAlertBench/blob/42a84889fda912ca432c994924a1ccd4b9df6274/README.md)

Our prompt's attempt-inclusive definition is broadly consistent with that published prompt fragment. The tasks still differ in other respects: our reviewer must provide reasons and exact citations, may return `Unable to verify`, uses a fixed output cap, and sees a cleaned blinded case representation. Consequently, the 20% result is **agreement for this fixed reviewer on these 50 cases**, not a matched reproduction of the author's model metrics or a general Qwen accuracy estimate.

Do not explain the disagreement away as a proven definition mismatch, declare the dataset wrong from bot opinions, overwrite labels with these decisions, or retry the exposed 50 until agreement reaches 90%. The result preserves unresolved label validity rather than resolving it.

## Frozen model and observed execution

| Item | Verified value |
|---|---|
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Immutable revision | `cdbee75f17c01a7cc42f958dc650907174af0554` |
| Decoding | Greedy; no sampling; one beam |
| Input/output caps | 16,384 / 512 tokens |
| GPU and precision | NVIDIA A10G; bfloat16 |
| Runtime | Python 3.10.12; Torch 2.5.1+cu121; Transformers 4.57.6; tokenizers 0.22.2; safetensors 0.7.0 |
| Total input / output tokens | 66,906 / 18,997 |
| Maximum observed input | 2,479 tokens |
| Summed per-case measured time | 751.84 seconds; excludes model loading and cloud setup |
| Median per-case measured time | 15.00 seconds |
| Answers frozen | 2026-09-20 16:54:48 UTC |
| Graded after freeze | 2026-09-20 16:58:13 UTC |
| Host verified stopped | 2026-09-20 16:59:09 UTC |
| Start request to observed stop | 1,127.20 seconds; within the one-hour bound |

The input bundle contained only the standalone reviewer, allowlisted blinded prepared files, and protocol/runtime records. No answer key was uploaded. The fixed answers were collected and verified before the root process graded them. This independent audit read frozen answers, limited raw responses, blinded source fields for citation checks, public aggregate grading results and operational receipts; it did not read the private answer key.

The primary cloud collection and earlier grading copy had identical `FROZEN.json`, `ANSWERS.json` and `RAW_OUTPUTS.jsonl` bytes. Observed final status was `COMPLETED_AND_STOPPED`; the controller removed only its own watchdog after verifying that the host had stopped. No reviewer prompt, model revision, token cap or answer was changed during this run, and no case was retried.

Integrity identifiers:

- Frozen answers SHA256: `d49c4949093f4769945836dce33cf6283adb4f444acbe86add44efbda20e708c`
- Raw outputs SHA256: `02444f7c660fb5484ff76be3f2755e00a22226e63c556a82ef7a9ef830c5ba23`
- Private transport archive SHA256: `cc22f5905b54fd6fe05f5f8681bbb1c2e7bc929cfe42ac2be415ae4143aeae77`

Raw cases, response text, quotations and account details remain private. The human-review requirement remains unsatisfied. The appropriate conclusion is that the automated review was completed transparently and **did not validate the dataset labels or supply a reliable replacement checker**.
