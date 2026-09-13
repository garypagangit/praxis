# Independent review of the repaired comparator

**Comparator controls pass. The scientific baseline remains conditional on the separate contract and provenance reviews.** This validation does not establish a publishable hypothesis, useful specialist, or benchmark purpose success.

At scorer SHA256 `465a315ad2fa7ad169128520986d40a082f29c36acc189eedcc5f662619ae868`, all **103 synthetic checks pass**:

- 70 manually specified controls were frozen before the scorer implementation was available to this validator: 50 answer controls and 20 table controls. Their freeze records the exact control hash and time.
- 16 additional controls were specified following source review. They check paired column associations, nested sequence semantics, perfect matching under nontransitive numerical tolerance, isolated path rules, and type-preserving record IDs.
- 17 additional precision/configuration controls check exact counts above floating-point integer precision, mapping-key types, null/error precedence, and rejection of invalid modes and tolerances.

The first run passed 68 controls and explicitly marked two table failure states unsupported. The implementation then added separate missing-output and execution-error states. Source review also identified that unordered columnar row comparison propagated unordered semantics into nested list-valued cells. The implementation restricted that mode to the row sequence; the added regression control passes. The initial result is retained alongside the final receipts. No expected outcomes were loosened to obtain a pass.

The source-review suite's perfect-matching fixture deliberately requires rematching a previously chosen numerical pair. This guards against a greedy matcher rejecting an available valid one-to-one assignment. Its negative control requires failure when no full matching exists. Nested mappings retain both keys and values, booleans do not become counts, numeric-looking strings remain literal strings, nonfinite references remain invalid, and table identity/schema problems do not receive full credit.

## Independent semantic spot check

Before model-score review, the validator inspected provisional eligible tasks against their authoritative purpose wording, query source and clean inputs. `CONTRACT_SPOTCHECK.json` publishes only derived counts and source hashes; no table rows, task text, names or reference answers are included.

The review found material ambiguities that comparison repair cannot resolve:

- Task 42 counts three qualifying inspection records representing only two distinct store identifiers/names. Task 133 counts 19 qualifying hospital records representing 15 distinct provider identifiers. Purpose wording asks for entities, so record counts need a justified entity policy.
- Task 48 has ten equally frequent business names but returns one. Task 40 has a tied modal risk group. Task 130 has four counties tied at the top-three boundary. An exact single reference does not credit all valid tied solutions.
- Tasks 68 and 109 make arbitrary ordering inside ties part of an ordered reference. Task 93 returns 37 name records covering 31 distinct names without an explicit multiplicity requirement.
- Tasks 40 and 87 encode structured answers as literal JSON strings. A literal string comparator establishes serialization agreement, not semantic mapping agreement.
- Tasks 16 and 17 use an exact event label for a broader meal-offering purpose. Existing compound labels add one lunch sponsor and seven dinner sponsors under simple whole-word matching. This demonstrates an unresolved category scope; it does not define replacement gold.

Positive spot checks found unique maxima for tasks 47 and 89, and no within-top-three or cutoff ties for task 23. Task 92 has 50 distinct record IDs/names among 50 records, and task 7's six selected records have six distinct menu IDs. Task 1's **authoritative** purpose asks for maximum page count, which is consistent with its scalar query; an alternative purpose file uses different wording. These are bounded observations, not certification of the remaining tasks.

The contract reviewer reconciled these findings before aggregate replay. The final manifest contains **40 provisionally aligned tasks, 61 invalid contracts and 41 ambiguous contracts**. Sixteen tasks previously provisionally aligned moved to ambiguous: 16, 17, 40, 42, 48, 52, 68, 87, 93, 94, 101, 102, 103, 109, 130 and 133. This includes the contract reviewer's related name/address multiplicity exclusions beyond this validator's spot checks. No gold answers or tie policies changed. The remaining 40 are a conditional, source-reviewed subset; the validator has not independently certified every one. Ambiguities remain excluded until justified independently of model outcomes. Do not invent new gold or tie rules after observing rankings.

## Reproduction and remaining limits

From this directory, run the scripts with output paths outside tracked source if preserving the published receipts:

```powershell
python run_controls.py --output controls-result.json
python run_controls.py --controls source_review_controls.json --freeze SOURCE_REVIEW_FREEZE.json --output source-review-result.json
python configuration_controls.py --output configuration-result.json
python spotcheck_contract.py --cache PATH_TO_VERIFIED_INVENTORY_CACHE --output contract-spotcheck.json
```

The first three commands use synthetic data and the local scorer only. The last uses hashed clean tables and contract metadata, never saved model answers. All four scripts are offline and make no model or cloud calls. Published counts refer to the scorer hash above; revalidation is necessary if that code changes.

A narrow agreement baseline may still be useful for feasibility. It cannot establish task success if the query does not answer the purpose, the gold is ambiguous, generated-output provenance is incomplete, or raw-table fallback is treated as successful generation. Compare correction and harm against the same tasks' raw-table answers, preserve coverage and invalid-reference denominators, and keep evaluator-only gold inaccessible to any future specialist or controller. Shared source tables must not be split across training and held-out evaluation merely because their task IDs differ.
