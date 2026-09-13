# AutoDCWorkflow offline artifact audit

**Decision: HOLD_UNTRUSTWORTHY_BASELINE_ORACLE. No new model run is justified by this artifact audit.**

The released evaluator cannot yet support a trustworthy task-success baseline. This conclusion concerns the inspected code and artifacts; it is not a reanalysis of every published experiment or a claim that the research direction cannot work.

Pinned source: [LanLi2017/LLM4DC, 082dcbf5304329ef1ff08f5830e4116256b00a59](https://github.com/LanLi2017/LLM4DC/tree/082dcbf5304329ef1ff08f5830e4116256b00a59). Reviewed and executed locally on 2026-09-13. No model inference, API clients, cloud operations, or Git changes. Only reviewed evaluator functions and three short query methods were executed; the upstream pipeline and its module-level I/O were not imported or run.

## What was tested

`audit_oracles.py` exercises the original scorer using all 142 released reference answers, once against an identical answer and once against a deliberately wrong answer: 284 answer fixture evaluations. Every released answer type is covered. Eight small table fixtures probe row/null/schema behavior; three reviewed query methods establish actual return types and task-contract concerns.

| Released answer type | Count | Identical answer credited | Deliberately wrong answer rejected by exact accuracy |
|---|---:|---:|---:|
| Integer | 29 | 0 | 29 |
| Float | 11 | 11 | 11 |
| String | 24 | 22 | 24 |
| List | 65 | 65 | 65 |
| Dictionary | 13 | 13 | 13 |
| Total | 142 | 111 | 142 |

**31 correct identity fixtures receive zero credit.** All 29 integers fall through the scorer. Two strings, IDs 78/79 (numeric-looking code strings), are parsed into integers and then fall through too. These code-like strings also demonstrate why a repair must preserve task-specific types rather than convert every numeric-looking string.

All 13 dictionary fixtures with every value deliberately wrong still receive F1=1 because that metric compares keys. Exact accuracy correctly rejects them. Key agreement therefore must not become the primary answer-correctness measure.

The table comparator returns 0 after reversing the order of otherwise identical records with explicit row IDs, and returns 1 when an extra wrong record is appended. It excludes null gold cells, so replacing one with an arbitrary value remains unpenalized. Missing rows/columns raise `KeyError`; an all-null target raises `ZeroDivisionError`. These behaviors need an explicit task contract; none should be silently excluded from a future denominator.

Actual query examples: purpose 1 returns integer 22, which scores zero against itself; purpose 2 converts the mean of [1,2] to integer 1, although the purpose does not specify rounding; purpose 3 requests the number of distinct event types but returns a list of values. The latter agrees with its released gold format but does not directly answer the written question.

The released gold has one nested NaN at ID104. Source bytes were preserved. The audit uses Python's permissive JSONL parser and tags nonfinite values only when writing strict-JSON receipts. A self-comparison containing NaN is not evidence that its intended semantics are sound. The first reporter attempt rejected NaN during serialization; that failed attempt and the encoding-only correction are recorded in `RUN_HISTORY.md`.

## Artifact inventory

The inventory verified 303 downloaded files, totaling 2,487,771 bytes, against their pinned Git blob hashes and sizes, recording SHA256 for each. All 142 raw/clean pairs parse with no malformed CSV rows and equal row counts within each pair. Fourteen menu pairs have column differences requiring task-aware alignment. Raw tables range from 10 to100 rows (median20). These are purpose-specific files; this count must not be described as 142 independent source datasets.

The 142 IDs span menu30, food inspections30, PPP22, dish16, flights16 and hospital28. IDs are not contiguous within1?154. Thirteen saved-answer files are JSONL despite `.json` suffixes. All ten under `evaluation/` have142 IDs; the two additional rerun model files contain126 Gemma and105 Llama answers, plus a complete gold file. All missing IDs are recorded.

Four `CoT.response` model groups each contain142 saved CSVs. Ablation groups contain138 Gemma2,138 Gemma2base,124 Llama3.1 and36 Mistral CSVs. Source inspection shows the ablation answer-execution branch falls back to the raw table when an expected output CSV is missing. A complete answer file therefore does not certify complete model generation; missing and genuine unchanged outputs must be distinguished.

Both gold copies are byte-identical. Their question wording matches `purposes/all_purposes.csv` on all142 IDs. `purposes/all_purposes_full.csv` and root `dataset-all - all_purposes.csv` differ on33 wordings. Freeze the exact prompt file before reproduction; the oracle audit's three query fixtures use the root CSV and label that source explicitly.

Saved model CSVs were inventoried from the pinned tree; they were not all downloaded or semantically validated. No aggregate model ranking or accuracy claim is made. The repository's reuse terms remain unresolved as noted in the literature memo.

## Minimal repair needed before reconsideration

1. Freeze an authoritative purpose/query/gold manifest. Resolve count-versus-list, rounding and nonfinite-value contracts from original task evidence. Preserve upstream labels and document any revised measurement separately.
2. Implement typed answer scoring: integers and mixed numeric values with explicit tolerances; code strings preserved; nested values checked; per-task list ordering and duplicate rules. Require all valid identity fixtures to pass and deliberately wrong answers to fail. Do not use dictionary-key F1 as task success.
3. Specify row identity, allowed order changes, additions/deletions, nulls and execution failures. Add explicit failure accounting and independent purpose-answer checks.
4. Keep missing model outputs distinct from raw-table fallback. Re-score existing saved outputs offline after these repairs; demonstrate a useful specialist baseline before creating a new inference protocol.

This is a bounded **measurement repair prerequisite**, not a newly qualified primary experiment. No paid follow-up is implied.

## Reproduction and receipts

From this folder, using Python3.11.9 with pandas3.0.2, numpy2.4.4, python-dateutil2.9.0.post0:

```powershell
python fetch_sources.py
python audit_oracles.py
python inventory/inventory.py
```

The first command performs only pinned public HTTP GETs. The second is fully offline. The inventory uses its verified local cache when present; `--refresh` explicitly re-fetches pinned artifacts. Dependencies and exact workstation commands appear in `EXECUTION_RECEIPT.json`. Exit0 means the audit completed, not that its HOLD decision passed a scientific gate.

- `SOURCE_MANIFEST.json`: immutable evaluator/reference file hashes and URLs.
- `AUDIT.json`, `ANSWER_FIXTURES.json`, `audit_stdout.txt`: numerical findings and individual fixtures.
- `inventory/inventory.py`, `inventory/inventory_receipt.json`, `inventory/README.md`: complete data/output inventory and reproducible verification.
- `INVENTORY_SUMMARY.json`: compact inventory counts.
- `SHA256SUMS.json`: hashes of this audit package, excluding the checksum file itself.

For publication, use `PUBLIC_AUDIT.json` and `PUBLIC_INVENTORY.json`. These contain only derived counts, IDs, schema dimensions, paths, hashes and our findings; they omit downloaded source, rows, gold answers, and heuristic question/answer examples. See `PUBLICATION_MANIFEST.json`.
