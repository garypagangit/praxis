# PX-063 rh-bench TRACE-Derived Source Gate

Date retrieved (UTC): **2026-07-26T22:37:52.955335+00:00**

Status: **PASS**

## Provenance

- Dataset: `ktolnos/rh-bench` / `open_ended` / `train`
- Filter: `source_dataset == 'patronus_trace'`
- Hugging Face revision: `1045a7336432c40182924bbd3698af292ea24acb`
- Pinned Parquet SHA-256: `0a809f3fa648169f5a7df641095a72ee3218fa4e9d1ee68c5fdb7fb32d723b72`
- GitHub dependency commit: `090e47b878192ee7a016d6c89e983141a415b154`
- GitHub dependency URL: `https://github.com/ktolnos/rh-bench.git`
- GitHub dependency worktree clean: **True**
- Dataset license metadata: `cc-by-sa-4.0`
- External code license file: **UNRESOLVED - no repository license file**
- Gate 0 dependency/license status: **PASS**
- Official TRACE card revision: `31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d`
- Raw trajectories committed: **No**

## Integrity results

- Rows: **517** (expected 517)
- Hacking: **268** (expected 268)
- Clean: **249** (expected 249)
- JSON parse-failure rows: **0**
- Missing response rows: **0**
- Dual-populated response rows: **0**
- Missing-label rows: **0**
- Missing original TRACE-code rows: **0**
- Invalid TRACE-code rows: **0**
- Duplicate source IDs: **0**
- Missing source IDs: **0**
- Duplicate source row indices: **0**
- Missing source row indices: **0**
- Duplicate canonical row hashes: **0**
- Rows with structured tool payloads: **0**
- Canonical safe-manifest SHA-256: `a9cf33f6e6d5a9a5ce10c2fd8e43093eec54578315b7cb7f0c22e5a8a651483e`
- Frozen TRACE-taxonomy SHA-256: `67f7133dc1e18da5701dac5c1bc9fa2f32b606832246d2b479b0fb0a20bfae3b`

## Frozen expectation checks

- `row_count`: **PASS**
- `hacking_count`: **PASS**
- `clean_count`: **PASS**
- `json_parse`: **PASS**
- `responses_present`: **PASS**
- `response_side_unambiguous`: **PASS**
- `labels_present`: **PASS**
- `trace_codes_present`: **PASS**
- `trace_codes_valid`: **PASS**
- `source_ids_unique`: **PASS**
- `source_row_indices_unique`: **PASS**
- `canonical_row_hashes_unique`: **PASS**
- `manifest_complete`: **PASS**
- `pinned_parquet_sha256`: **PASS**

## Scientific claim boundary

The normalized rows contain ChatML role/content text. A zero value for structured_tool_payload_rows means execution and filesystem effects are not independently verified by this derivative.

PX-063 therefore evaluates deterministic evidence extraction over the TRACE-derived `rh-bench` normalization. It does not claim use of the official TRACE harness, and it does not treat assistant transcript text as independently verified execution state.

The `rh-bench` dataset card identifies the derivative dataset as CC-BY-SA-4.0. The pinned GitHub repository has no license file at this commit, so live reuse of its OpenRouter helper code remains a separately recorded licensing limitation; paid calls are not part of this gate.

## Committed artifact policy

Only pseudonymous record IDs and cryptographic row hashes are written per row. Gold labels, TRACE codes, categories, source identifiers, prompts, and response text are intentionally excluded.
