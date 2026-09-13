# Source-only task contract freeze

This package separates **agreement with the released executable observable** from **agreement with the written purpose**. Repairing the answer comparator cannot make a query that calculates the wrong statistic valid. No gold answers have been replaced. No saved model answers were scored or used to choose eligibility, tolerances, or exclusions during this review.

The source is [LLM4DC at commit 082dcbf5304329ef1ff08f5830e4116256b00a59](https://github.com/LanLi2017/LLM4DC/tree/082dcbf5304329ef1ff08f5830e4116256b00a59). `purposes/all_purposes.csv` is authoritative for this replay because its 142 purpose strings match the released gold records. The alternate full/root purpose CSVs are not substituted. `TASK_CONTRACTS.json` identifies each purpose row, query method, reference record and raw/clean table by pinned path and SHA256. It publishes our semantic summaries and hashes, not copied task text, source tables, or gold answers.

## Denominators and interpretation

All 142 query methods and authoritative purposes were reviewed. The frozen classification is:

| Classification | Tasks | Permitted interpretation |
|---|---:|---|
| Provisionally purpose aligned | 40 | Filtered agreement under the disclosed query conventions; independent certification is not claimed |
| Observable conflicts with purpose | 61 | Released-query agreement is diagnostic only |
| Purpose or required representation ambiguous | 41 | Released-query agreement is diagnostic only |

Each excluded ID has an explicit reason in the manifest. The102 exclusions were determined from source semantics, before repaired model-output metrics were viewed. They must not be silently removed from the report: publish the full142-task accounting and the40-task filtered diagnostic side by side. This is an artifact repair and selected-task analysis, not reproduction of the paper's headline score. Do not call the filtered diagnostic a fully qualified specialist baseline.

An independent source-only review tightened an initial56-task provisional set before freezing it. IDs40,42,48,68,87,93,109 and130 have modal or ranking ties, entity/inspection units, name multiplicity, or semantic-JSON issues. The same conservative name/address multiplicity rule excludes IDs52,94,101,102 and103. The retained diagnostic comparator is unchanged; exclusions do not manufacture alternate gold answers.

The final source-only review also excludes ID133, which counts19 qualifying hospital rows but only15 distinct provider identifiers, and IDs16/17, whose exact event filters omit compound meal-offering labels actually present in their clean tables. ID15 has no corresponding compound breakfast labels in its clean table and remains provisional. Clean-table ranking or maximum ties were separately ruled out for IDs23,47 and89. Eligibility must not be revised after viewing model metrics without a separately labeled version and fresh analysis plan.

`purpose_eligible` and `purpose_valid_eligible` are identical aliases. Their true value means `purpose_status == eligible_provisional`; it does not assert a proof of correctness. Negative cases include count requests answered by label lists, omitted required amounts or entity identities, reversed comparisons, incorrect denominators, and missing temporal or dominance tests. Ambiguous cases are excluded rather than resolved by guessing an author intention.

ID104 contains a nested nonfinite released reference. Its upstream diagnostic is also ineligible. The remaining 141 finite references can support typed executable-observable agreement, with all ineligible and execution-failure counts reported. A null, NaN, infinity, exception or missing output must not be converted into a correct answer. An empty list/dictionary can be a legitimate query result, but many upstream methods also swallow exceptions into empty containers. Saved answers alone cannot distinguish those cases; reexecution requires explicit provenance and failure reporting. Catching only uncaught exceptions does not establish successful query execution.

## Typed comparison decisions

- Counts and identifiers use exact finite numeric comparison, allowing mathematically equal integer/float representations while rejecting booleans as numbers. Numeric-looking strings remain literal strings. In particular, ZIP strings at IDs78/79 and the ZIP component of ID89 must not be parsed into numbers or have leading zeros removed.
- The measured real-valued observables at IDs9, 11, 19, 32, 44, 45, 62, 63, 64, 66, 92, 112, 123 and140 use absolute tolerance `1e-8` plus relative tolerance `1e-9`. This is an explicit diagnostic numerical convention, not an inferred task tolerance. It is much smaller than a count or monetary cent; differences in required precision still need a future task contract. All other numbers compare exactly.
- Lists explicitly produced as unique-label collections compare as sets: order and repeated identical labels do not convey information. Lists of returned records compare as multisets at IDs36, 52, 93, 94, 98, 99, 100, 101, 102, 103, 116, 119 and121, preserving multiplicity while ignoring incidental row order.
- Ordered answers are retained at IDs23, 68 and109 (ranked selections) and IDs74, 75, 89 and134 (positional tuples). Equal-score boundary ties follow the pinned query/runtime's convention for this diagnostic; they are not a general semantic tie rule. No alternate tied winner is invented as a new gold.
- Dictionary keys and values must both match. Key-only F1 is not answer correctness. Parallel arrays at IDs104/105 form ordered paired rows; independently sorting their columns would destroy associations. The nested lists in ID141 use set semantics.
- IDs40, 43, 72, 73, 87 and110 return literal JSON-encoded strings. This bounded repair keeps those strings literal rather than adding another undocumented decoder. Equivalent mappings with different JSON/index formatting can therefore be false negatives. Their diagnostic is representation-sensitive and must be described as such.
- String case, whitespace, Unicode and null conventions are not silently rewritten by the comparator. Normalizations explicitly performed inside a query remain part of that executable observable.

The top-level `scorer_spec` fields are directly consumable by the shared scorer. They do not change the source queries, dataset rows, labels, or purpose wording.

## Source controls and independent probes

Every raw and clean table was read locally using the pinned pipeline's `pd.read_csv` defaults and its reviewed query function. Only the `QExecute` class, the datetime helper and its regex assignment were compiled from the AST; no upstream module I/O, model client, process launcher or pipeline entry point ran. Each query receives a fresh deep copy because several methods mutate their input. Warnings and prints were captured. No model predictions were read by this execution.

The 142 clean-query controls give 140 exact agreements, one permutation of tied names at ID55, and one unresolved nonfinite reference at ID104. The ID55 difference supports order-insensitive tie-set comparison rather than modifying the gold. This demonstrates executable/reference consistency, not purpose correctness. The private raw/clean control file is hashed in the manifest; it contains source-derived answers and is not published.

`semantic_controls.py` independently specifies expected outcomes for 53 artificial tables: 28 matching-observable controls and25 purpose-discrepancy controls. All53 passed their declared relationship checks. The negative controls are expected to disagree with upstream output; their pass means the discrepancy was reproduced. These include fractional means, count-versus-list errors, risk direction, all-before-date versus earliest-before-date, average delay versus timestamps, on-time early arrivals, morning boundaries, reversed arrival comparisons, the critical-access/acute-care substitution, per-city ratio denominators, government dominance and multi-owner-city filtering. Synthetic controls do not replace any released reference and do not certify the untested portions of an eligible query.

## Unit of analysis and unresolved work

The six source-corpus groups are menu, food inspections (`chi`), PPP, dish, flights and hospital (`hos`), containing30, 30, 22, 16, 16 and28 tasks respectively. The142 task-specific table pairs are not142 independent source datasets. `source_table_group` is the domain/corpus grouping, the strongest grouping justified by this release; it is not an asserted unique source-table identity. Future splits must prevent related source rows/tables and transformations from crossing train/development/test boundaries. An ID-random split would not establish that independence.

This contract qualifies a bounded offline replay only. It leaves purpose-valid gold correction, broader oracle edge-case coverage, row/entity identity, alternate tied answers, JSON formatting invariance and benchmark reuse terms unresolved. Any future purpose-corrected benchmark needs its own version, independently checked labels and a new pre-outcome freeze. Do not use these exclusions or semantic probes as a claimed novel defense contribution.

Reproduction (offline, Python3.11.9, pandas3.0.2, numpy2.4.4):

```powershell
python collect_source_controls.py --audit-cache <artifact_audit> --output <private>/PRIVATE_RAW_CLEAN_CONTROLS.json
python semantic_controls.py --query-source <artifact_audit>/source/evaluation/q_execution.py
python build_contract.py --audit-cache <artifact_audit> --private-controls <private>/PRIVATE_RAW_CLEAN_CONTROLS.json
```

The initial raw/clean control execution is documented in the private report directory. `FREEZE_RECEIPT.json` hashes this package after the53 synthetic controls and before model-output replay. The Git commit made by the coordinating agent provides the final immutable pre-replay boundary.
