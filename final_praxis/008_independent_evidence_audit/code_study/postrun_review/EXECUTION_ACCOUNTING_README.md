# Reproduce execution accounting

Run the read-only tool against completed local campaign directories:

```bash
python postrun_review/summarize_execution.py \
  --v1 /campaign/study \
  --v2 /campaign/study_v2 \
  --output-dir /campaign/execution_accounting
```

It produces `EXECUTION_ACCOUNTING.json` and `SAMPLE_FLOW.md`. If V2 is absent or its process status is unfinished, the tool reports V2 as pending and does not read its incomplete result tables. All four review partitions and both proposal partitions are required for a completed version, including partitions containing only gate-blocked or ineligible placeholders.

The tool checks assignment identity sets and hashes, aggregate/per-record agreement, raw-result/ledger linkage, and the exact source/destination hashes in V2 import manifests. It rejects duplicated record IDs, unknown imported kinds, incomplete reuse identity sets, unexplained raw results, and duplicate provider request IDs across phase directories. Imported Devstral decisions and development proposals contribute source-lineage counts; they do not add another provider result or another charge. The synthetic schema warmup is counted as a control request and included in costs, outside the scientific assignment counts.

The API estimate sums each ledger entry once using its serialized decimal value. It distinguishes successful usage-based costs from other or unresolved accounted reservations. Ledger attempts, distinct logical request IDs, returned provider results, assigned records, valid reviews, and reused records are separate quantities. A successful transport response can still produce invalid model JSON. Requests prepared before a budget rejection can leave a request file without an inference attempt; raw request-file count is therefore not presented as a count of successful model calls.

The tool does not execute benchmark/model code, make provider calls, or compute scientific effects. Its combined distinct-response counts do not turn the two interface configurations into independent replications. API estimates are not invoices and exclude host, storage, transfer, and tax costs.

Run the self-authored synthetic controls with:

```bash
python postrun_review/test_summarize_execution.py
```

The controls verify reuse deduplication, budget reservation accounting, pending-version handling, and corruption rejection without accessing benchmark records or making API calls.
