# Released-output provenance before answer replay

**The intended model/CSV labels are recoverable, but the historical saved-answer-to-CSV binding is unverified.** A new offline replay should execute a frozen query/scoring contract against explicitly selected, hash-pinned CSVs and record each source hash. This audit does not score answers or establish a model ranking.

Source: [LanLi2017/LLM4DC at 082dcbf5304329ef1ff08f5830e4116256b00a59](https://github.com/LanLi2017/LLM4DC/tree/082dcbf5304329ef1ff08f5830e4116256b00a59). Only public GETs, file hashes, CSV structure, JSONL IDs, and source inspection are used. No upstream module or query is executed; notebook outputs are not inspected.

## Mapping and its limits

| Saved-answer label | Intended input | Evidence and limitation |
|---|---|---|
| `evaluation/answer_1-154_{model}.json` | `CoT.response/{model}/datasets_llm/{model}_{domain}_test_p{id}.csv` | Consumer notebooks and the non-base query branch support this label. The active writer configuration is ambiguous. |
| `evaluation/answer_1-154_base_{model}.json` | `ablation/{model}/datasets_llm/base_{model}_{domain}_test_p{id}.csv` | The ablation notebook reads these answer filenames. The query writer would need its output filename changed or the result renamed. Missing CSVs trigger raw-table fallback in the reviewed base branch. |
| `CoT.rerun/answer_1-154_{model}.json` | Corresponding model and purpose ID under `CoT.rerun/{model}/datasets_llm` | Directory, model, and ID agree. Filename variants occur, and no per-answer source receipt binds these historical outputs. |
| `answer_1-154_gt.json` | Released clean table for the purpose | The ground-truth query branch defines the intended source; no execution is performed here. |
| `evaluation/answer_1-154_dirty.json` | Released raw table for the purpose | The dirty-data query branch defines the intended source; no execution is performed here. |

At the pinned revision, `evaluation/q_execution.py` sets `base_tag=True`, selects an ablation input directory, and writes an **unprefixed** model answer filename. The same answer filename can therefore be written from different configurations. Filenames and consumer code are evidence of intended labels, not proof of the exact historical producer run. No released per-answer source hash, configuration receipt, or execution receipt was found in the inspected artifacts.

The machine-readable map contains every combination of 13 answer files and 142 purpose IDs, including missing answers. Each candidate is classified separately as a released CSV, a released CSV with unchanged raw cells, or a missing CSV with conditional raw fallback. The fallback label states what the pinned base branch would read; it does not assert that a historical answer used that path. A saved CSV identical to raw remains distinct from a missing CSV and does not itself certify model execution.

The identity diagnostic compares bytes, parsed CSV cells, and parsed cells after removing an optional exported range-index column. That last normalization applies only when the first header is empty and its values are exactly `0,1,...,n-1`; it changes no other fields. Under this limited comparison, 36 of the 568 `CoT.response` files have unchanged raw cells (Gemma2 5, Gemma2base 12, Llama3.1 10, Mistral 9). This is an artifact property, not a correctness score or proof of successful generation.

All four `CoT.response` groups have 142 CSVs. The ablation groups have 138 Gemma2, 138 Gemma2base, 124 Llama3.1, and 36 Mistral CSVs. The two rerun groups associated with saved model answers have 126 Gemma2 and 105 Llama3.1 CSVs. Every selected CSV is downloaded and checked against its pinned Git blob hash and size. Exact counts, IDs, shape observations, and SHA256 hashes are in the JSON artifacts. No table is compared against a clean reference for correctness.

The verifier checked 1,543 files totaling 15,932,184 bytes, including 1,235 selected generated CSVs. Llama3.1 `CoT.response` purpose IDs 150 and 154 have a nonrectangular record at row 22. These require explicit parser-failure accounting in a replay; the provenance audit does not silently repair them.

## Artifacts

- `PROVENANCE_SUMMARY.json`: coverage, limitations, source-code locations, and verification metadata.
- `ANSWER_SOURCE_MAP.json`: per answer-file/purpose-ID candidates, missingness, and binding uncertainty; no answer values.
- `CSV_MANIFEST.json`: verified generated CSV paths/hashes, dimensions, malformed row locations, and raw-byte identity.
- `VERIFIED_SOURCE_MANIFEST.json`: all source, answer, raw/clean, and generated CSV hashes checked by the verifier.
- `verify_provenance.py`: standard-library reproduction; downloads stay outside this publication directory.
- `reexecute_tables.py`: separate runner for a subsequent frozen offline query replay. Writing this runner does not execute it.

## Reproduction

From the workspace root, with the prior artifact audit available:

```powershell
.venv/Scripts/python.exe C:/w/fp008/final_praxis/008_independent_evidence_audit/oracle_repair/provenance/verify_provenance.py --artifact-audit reports/praxis_20260913_closeout_and_pivot/artifact_audit --private-dir reports/praxis_20260913_closeout_and_pivot/oracle_repair_provenance --fetch
```

Omit `--fetch` to require existing local caches and make the run fully offline. All cached files are hash-verified again. The private execution receipt records exact local paths; private caches retain third-party source, notebook files, CSV rows, and answer payloads. Only derived metadata and our verifier/report are intended for Git publication. Reuse terms remain unresolved as recorded in the parent artifact audit.

## Separate archived-table replay

`reexecute_tables.py` requires `--frozen-commit` and refuses execution unless its code, the repaired scorer, task contract, and input manifests match that Git commit. It uses all 142 raw and 142 clean tables as fresh controls first. Model-table execution is permitted only if every finite clean-reference comparison passes and the previously frozen raw/clean return values are reproduced. The nonfinite reference remains explicit in the control accounting.

If those checks pass, all 142 purpose IDs in each of four `CoT.response` groups are assigned to the replay, including purpose-ineligible IDs, missing files, malformed CSVs, exceptions, nulls, and nonfinite returns. There is no raw fallback. Input preprocessing is exactly default `pandas.read_csv`; the range-index removal used by the provenance identity diagnostic is **not** applied to query inputs.

Only the reviewed query class, datetime helper, and regex assignment are extracted from the source AST. An amended runner records every exception handler entry without changing successful-path query operations. Any caught exception prevents task-success credit, even if the source method returns an empty/default result or recovers through a fallback branch. JSON serialization adds an explicitly recorded conversion for numpy scalar values; unsupported types fail instead of becoming strings. Saved-answer agreement is a separate provenance diagnostic and never proves historical source identity.

The invocation, after the root agent commits the freeze, is:

```powershell
.venv/Scripts/python.exe C:/w/fp008/final_praxis/008_independent_evidence_audit/oracle_repair/provenance/reexecute_tables.py --audit-root reports/praxis_20260913_closeout_and_pivot/artifact_audit --model-cache reports/praxis_20260913_closeout_and_pivot/oracle_repair_provenance/cache --private-controls reports/praxis_20260913_closeout_and_pivot/oracle_repair_contract/PRIVATE_RAW_CLEAN_CONTROLS.json --output-dir PUBLIC_RESULT_DIRECTORY --private-output-dir PRIVATE_ANSWER_DIRECTORY --frozen-commit FROZEN_40_CHARACTER_COMMIT
```

The outputs are `TABLE_REPLAY_SUMMARY.json`, `TABLE_REPLAY_CELLS.json`, `TABLE_REPLAY_CONTROLS.json`, and `TABLE_REPLAY_RECEIPT.json`. Private recomputed answers remain outside Git. Add `--controls-only` to stop after raw/clean checks. No ablation or rerun tables are reexecuted by this runner.
