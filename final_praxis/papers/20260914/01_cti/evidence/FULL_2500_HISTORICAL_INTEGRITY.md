# PX-003/PX-034 Full 2,500-Row Separate Deterministic Rerun Audit

**Audit date:** 2026-07-31  
**Determination:** **CONFIRMED — `PASS_SOURCE_KNOWN_ONLY`**

## Separate deterministic procedure

After all eight internally frozen cloud shards reached terminal success and the sealed merge was complete, the root process reran the frozen full-dataset analyzer from the four merged prediction files into a separate output directory. The rerun used the frozen **20,000 paired-bootstrap replicates** and did not alter data, conditions, thresholds, multiple-testing families, or gate logic. This is a separate deterministic reproducibility check, not an independent experiment, dataset replication, or analyst-blinded reimplementation.

## Chronology and evidence composition

The full protocol was hash-frozen internally, not deposited in an external registration service. The earlier 500-row cloud outputs had already been generated at freeze time. The execution record says those outputs were not inspected until after the full freeze, but this is an internal process claim rather than an independently observable fact. The all-2,500 cloud shards were launched after the freeze.

The 1,578-row ATT&CK stratum combines the 500 questions used in the earlier experiment and 1,078 questions not used in that experiment. Therefore, the full ATT&CK result is mixed prior-item plus untouched-item evidence, not 1,578 wholly untouched observations. A post-claims-audit internal sensitivity mechanically removed the 500 IDs and separately analyzed the remaining 1,078 ATT&CK questions while retaining all 922 mismatch rows.

## Input integrity

| Analytical cell | Rows | Unique `(id, condition)` pairs | Unique question IDs | SHA-256 |
|---|---:|---:|---:|---|
| Qwen source-pointer | 15,000 | 15,000 | 2,500 | `0700bb8c0db5162d2110c9e067506fe890ea36ee22d4c0b25cc1b521094b71b7` |
| Qwen query-only | 5,000 | 5,000 | 2,500 | `aa40ef3b9134bfee9548238b64456918928f4ae82ee0073299414d80cff06ebf` |
| Llama source-pointer | 15,000 | 15,000 | 2,500 | `0abc25cd7314944d090ccadf221e8ee1bc11af5efed1f960a631aa456254a91d` |
| Llama query-only | 5,000 | 5,000 | 2,500 | `d5e758ed285616f028f9283e717b8fef814d157fa62ac085acc098af436ad6d5` |

Every source-pointer file contains exactly 2,500 rows in each of six conditions; every query-only file contains exactly 2,500 rows in each of two conditions. Each condition contains 1,578 `attack_technique_eligible` rows and 922 `non_attack_domain_mismatch` rows. Across the four files, the audit found exactly **40,000 inference rows**, with no missing or duplicate frozen cell. Because each model's vanilla condition was independently executed in both source-pointer and query-only cells, these comprise **35,000 distinct `(model, question, condition)` combinations plus 5,000 duplicate-vanilla reproducibility rows**—not 40,000 distinct experimental units.

The merge/identity audit SHA-256 is `e8b7c268a14cdca602386f9151f64d4f6f49a71267b5e5c70f2a89678471f4e6`.

## Exact deterministic-rerun agreement

The separately regenerated outputs were byte-identical to the official outputs:

| Artifact | Official SHA-256 | Separate-rerun SHA-256 | Agreement |
|---|---|---|---|
| `analysis.json` | `c6a949b82adfe00abb3b3f1acbe04dc9277bda3b2d062a42e89a29d6cce3e181` | `c6a949b82adfe00abb3b3f1acbe04dc9277bda3b2d062a42e89a29d6cce3e181` | Byte-identical |
| `comparisons.csv` | `45892abc84854c2acf79fa6bf48465031ce8153dfb78bd6923cdf4e20a85635d` | `45892abc84854c2acf79fa6bf48465031ce8153dfb78bd6923cdf4e20a85635d` | Byte-identical |
| `analysis.md` | `fef3f20f49f47f2cbe31e0fa59d145c04368bae8218a32926964f801ff403f1d` | `fef3f20f49f47f2cbe31e0fa59d145c04368bae8218a32926964f801ff403f1d` | Byte-identical |

## Confirmed gate outcome

- Source-known relationship evidence vs. vanilla: **PASS** in both models.
- Relationship specificity vs. technique-only evidence: **PASS** in both models.
- Source-known negative-control family: **PASS** in both models.
- Query-only relationship evidence on ATT&CK-eligible rows: **PASS** in both models.
- Query-only non-ATT&CK mismatch non-inferiority: **FAIL** in both models.
- All four invalid-output safety scopes: **PASS** in both models.

The rerun therefore reproduces the bounded frozen-protocol result `PASS_SOURCE_KNOWN_ONLY`. It does not provide independent replication and does not support an ungated deployable-RAG claim. The replicated mismatch harm is an outcome to report, not a subset to remove post hoc.

## Post-claims-audit sensitivity headline

The internal 1,078-item sensitivity is explicitly non-preregistered and non-confirmatory because it was specified after the full outputs existed. It nevertheless preserves the qualitative pattern in both model families: source-known relationship evidence, relationship specificity, negative controls, and ATT&CK query-only benefit satisfy the previously frozen definitions, while non-ATT&CK mismatch non-inferiority fails again. Its machine-readable analysis is `untouched_1078_sensitivity/analysis.json`.
