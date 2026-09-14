# PX-068 Internal Prospective Protocol — Source-Compatible ATT&CK Retrieval

Finalized for internal pre-launch freeze: **2026-07-31**

Status: **PROSPECTIVELY SPECIFIED INTERNALLY — NOT EXTERNALLY REGISTERED — NOT LAUNCHED**

## Purpose

PX-003/PX-034 found a replicated boundary: query-only ATT&CK relationship evidence substantially improved strict answer accuracy on ATT&CK-technique questions in two frozen model families, but harmed non-ATT&CK questions and failed mismatch non-inferiority in both. PX-068 prospectively evaluates one new intervention on external items:

> Apply the frozen ATT&CK relationship-evidence prompt only when a fixed query-only classifier predicts ATT&CK-technique source compatibility; otherwise use the unchanged vanilla prediction.

The router is trained on CTIBench source-domain labels only. It never receives a CTIBench answer outcome, AthenaBench answer, AthenaBench URL, AthenaBench source label, LLM correctness value, or model output.

## Literature and exact relationship

The exact target-paper title is **“AthenaBench: A Dynamic Benchmark for Evaluating LLMs in Cyber Threat Intelligence.”** Its CKT section states: **“After validation, we sampled 3,000 questions to construct the final CTI Knowledge Test dataset.”** The paper specifies five-option CKT instances and multiple source families. PX-068 uses the complete pinned CKT artifact as an external-item, same-lineage replication corpus. Because AthenaBench explicitly extends CTIBench, this is not an independent benchmark-producer replication.

The exact training-paper title is **“CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence.”** It supplies the 2,500-row source-labeled training artifact and states that 1,578 questions came from MITRE. Neither benchmark paper tests this source-compatibility router.

**“Selective Classification for Deep Neural Networks”** supplies the risk–coverage rationale for using a high-precision selector while retaining an explicit coverage floor. **“Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks”** supplies the general retrieval-conditioned generation foundation. **“TechniqueRAG: Retrieval Augmented Generation for Adversarial Technique Annotation in Cyber Threat Intelligence Text”** establishes CTI-specific RAG as an existing research direction; it does not test this router or CKT policy.

## Pinned target artifact and reproducible access

- Repository: `Athena-Software-Group/athenabench`
- Commit: `39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf`
- File: `benchmark/athena-cti-ckt-3k.jsonl`
- Bytes: `5,994,938`
- SHA-256: `7893643dd98973fff5b2c3230a4f8f08227d7b6b312ba1a73309f97bb56a7542`
- Released rows, unique IDs, and unique prompt hashes: `3,000` each

The pinned repository currently exposes the complete 3,000-row file and its README identifies the full benchmark inventory. This later repository state is reconciled with paper Section 4.3, which described a planned non-commercial request process for complete-data access. Public download is treated only as access under the repository license—not as unrestricted redistribution permission.

The pinned `License.md` and `License.txt` both permit attributed academic, educational, internal-experimentation, and non-commercial research use and prohibit commercial use without written permission. PX-068 will not publish or commit the raw questions or sealed answers. A reproducibility release is limited to source links, commit and file hashes, code, fixed IDs/hashes, model predictions where permitted, and aggregate or derived scores. Commercial use is blocked absent written permission.

Full review: `reports/relationship_evidence_cti_compliance/px068_source_compatibility_router_20260731/PX068_ATHENABENCH_ACCESS_AND_LICENSE_REVIEW_20260731.md`.

## Prospective exclusions and primary corpus

Before any router was fit, three released records were exposed during schema/data-integrity debugging. They are prospectively excluded from every primary metric and retained only as a three-row sensitivity appendix:

| Source ID | Experiment ID | Reason | Canonical question SHA-256 |
|---:|---|---|---|
| 1 | `athena_ckt_0001` | First-record schema inspection displayed answer/provenance fields. | `b2efbdcc082dc4f93d926e6c072131d229f440eb72cd525f5d781c66b6bbed29` |
| 480 | `athena_ckt_0480` | A full-width label appeared in a pre-router normalization exception. | `bf21d48cb5c688733098da0f57f27bafa22626dc46dd95ab0ff476bec7b052d8` |
| 1384 | `athena_ckt_1384` | A malformed canonical answer appeared in a pre-router validation exception. | `f56e2f8b8800070f60709b2d12638adf2e1951debd21e888a4861a360d0d8ccc` |

No router, router score, route assignment, target metric, or LLM outcome existed when these exclusions were made. The exact CTIBench canonical query-overlap audit found zero additional target exclusions.

Primary fixed corpus after exclusion:

- `2,997` questions total
- `998` eligible ATT&CK-technique rows
- `1,999` ineligible rows
- `954` non-ATT&CK safety rows
- source families: 2,043 MITRE ATT&CK, 378 CWE, 338 CISA ICS, 152 CAPEC, 66 other, and 20 CISA CSA

The minimum-count gate passes: at least 2,800 primary rows, 900 eligible rows, and 1,800 ineligible rows remain.

## Canonical answer and provenance definitions

The pinned AthenaBench `athena_eval/run.py` and `athena_eval/evaluate.py` score the released `answer` field. PX-068 therefore uses `answer`, normalized uniformly with Unicode NFKC, trimming, and uppercase. `updated_answer` is retained for provenance but never overrides `answer`.

Aggregate pre-router integrity inspection found 2,999 valid normalized A–E values in `answer`, 2,999 valid values in `updated_answer`, zero disagreements where both were valid, and one row invalid in both fields. That invalid row is source ID 1384 and is already prospectively excluded. No answer value enters router or prompt construction.

Eligibility is fixed from released provenance only:

- eligible: URL host is exactly `attack.mitre.org` and first path segment is `techniques`;
- ineligible: every other row;
- non-ATT&CK safety subgroup: `source_type != mitre_attack`.

## Blinded artifact boundary

The primary query table contains exactly `id`, `question`, and ordered options `A`–`E`. The sealed truth contains answer, URL, source type, explanation, eligibility, and other provenance. The router and prompt builder accept only the query table.

Target router-label metrics remain sealed until all of the following are frozen and hashed:

1. primary and sensitivity ID tables;
2. sealed truth and exclusion ledger;
3. fitted router and every route assignment;
4. both potential-outcome prompt tables;
5. inference runner and model revisions;
6. deferred analyzer and decision rules;
7. package versions and freeze manifest.

No target precision, recall, false-positive rate, coverage, acceptance count, probability summary by label, accuracy, or model output may be opened before both model-family jobs and both conditions are terminal.

## Fixed calibrated source-compatibility classifier

Training data: all 2,500 CTIBench CTI-MCQ rows, parquet SHA-256 `42f8cb0c1d804945cbdcf890411ca6ede3a1e0222fb91966804fed7dc1a19acb`.

- Positive label: released URL matches `^https?://attack\.mitre\.org/techniques/` (`1,578`).
- Negative label: every other released URL (`922`).
- Input text: question and displayed options only, joined by literal ` [OPT] `.
- Word TF-IDF: 1–2 grams, `min_df=2`, 40,000 maximum features, sublinear TF, lowercase, L2 norm.
- Character TF-IDF: `char_wb` 3–5 grams, `min_df=2`, 60,000 maximum features, sublinear TF, lowercase, L2 norm.
- Classifier: L2 logistic regression, `C=1.0`, `liblinear`, balanced class weights, `max_iter=2000`, seed `68031`.
- Calibration: sigmoid `CalibratedClassifierCV`, ensemble enabled, five shuffled stratified folds, seed `68031`.
- Routing threshold: accept if and only if calibrated `P(eligible) >= 0.90`.

Non-negotiable implementation detail: `CalibratedClassifierCV` wraps the complete `Pipeline(FeatureUnion(word,char_wb), LogisticRegression)`. Each calibration fold therefore refits both vectorizers and the classifier; no vocabulary fitted on the full training table leaks into held-out calibration folds.

There is one classifier and one threshold. No target-label threshold sweep, classifier comparison, or post-hoc retuning is allowed.

## Fixed retrieval, prompts, parser, and potential outcomes

- ATT&CK source: frozen combined Enterprise, Mobile, and ICS 19.1 bundle, SHA-256 `bca81a8d69218ace1f7b5c706c605d22ad77d64425375b3d7804fdaf87c2ded9`.
- Retrieval reads the question and all five displayed options only.
- Retrieval uses the frozen PX-003 lexical scorer/index with a five-option adapter and top six facts.
- An exhaustive synthetic permutation cycles answer/provenance fields across A–E and must change zero retrieved records or prompt bytes.
- Conditions for every primary row: `vanilla` and `relationship_evidence`.
- After trimming only surrounding whitespace, strict parsing uses the exact case-sensitive full-line grammar `(?:Answer: )?([A-E])`: only uppercase `A`–`E` or uppercase `Answer: A`–`Answer: E` with one literal space is accepted. Lowercase, a missing/additional space, tabs, trailing prose or punctuation, extra lines, and multiple labels are invalid.
- Invalid outputs are failures and remain in all denominators.

The inference input contains neither truth nor router assignments. Both base potential outcomes are generated for every row. The routed policy is derived afterward: select relationship evidence when the frozen router accepts and vanilla otherwise.

The oracle policy selects relationship evidence only for provenance-defined eligible rows. It is a diagnostic upper bound only. It never enters a confirmatory pass/fail gate and never supports a deployable claim.

The runner writes no partial prediction artifact after its first condition and withholds parsed distributions. After each model completes both conditions, its sealed prediction artifact may be uploaded, but no prediction content is inspected until both models are terminal.

## Frozen models and inference

| Model | Immutable revision |
|---|---|
| `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` |
| `meta-llama/Llama-3.1-8B-Instruct` | `0e9e39f249a16976918f6564b8830bc894c89659` |

Greedy decoding, float16, 4,096 maximum input tokens, eight maximum new tokens, batch size two.

- Primary base predictions: `2,997 × 2 conditions × 2 models = 11,988`.
- Three-row sensitivity base predictions: `3 × 2 × 2 = 12`, reported separately and never pooled into gates.

## Estimands and statistics

- Router precision, recall, false-positive rate, specificity, balanced accuracy, and treatment coverage with Wilson 95% intervals.
- Strict policy accuracy with Wilson 95% intervals.
- Row-paired policy differences with deterministic 20,000-replicate paired-bootstrap 95% intervals.
- Two-sided exact McNemar tests.
- Holm correction across the two model-family tests separately for complete-corpus benefit, eligible benefit, and wrong-domain mitigation.
- Registered primary gate scopes: all primary rows, eligible, ineligible, non-ATT&CK, and other ATT&CK page types.
- Descriptive, multiplicity-transparent subgroups: every released source family and every ATT&CK path family. These subgroup estimates do not create additional confirmatory gates.

## Confirmatory gates

### Gate 0 — integrity

Every frozen hash matches; query/truth separation holds; complete-pipeline calibration is verified; the five-option permutation test has zero failures; all three exposed rows remain excluded; no target router-label metric or model outcome existed at freeze.

### Gate 1 — useful compatibility

- precision ≥ 0.90 and Wilson lower bound ≥ 0.87;
- recall ≥ 0.45 and Wilson lower bound ≥ 0.40;
- false-positive rate ≤ 0.05 and Wilson upper bound ≤ 0.07;
- treatment coverage between 0.15 and 0.45 inclusive.

### Gate 2 — complete-corpus benefit

For each model, routed minus vanilla must be at least +0.02, paired interval lower bound above zero, and cross-model-family Holm-adjusted exact p < .05.

### Gate 3 — eligible benefit

For each model on eligible rows, routed minus vanilla must be at least +0.03, paired interval lower bound above zero, and cross-model-family Holm-adjusted exact p < .05.

### Gate 4 — wrong-domain safety

For each model on all ineligible rows and separately on non-ATT&CK rows, routed minus vanilla must have point delta > −0.01 and paired lower bound > −0.02. Routed invalid rate may not exceed vanilla by more than 0.01 in any of the five registered primary gate scopes. Source-family and individual ATT&CK-path subgroup estimates are descriptive and do not add post-hoc gates.

### Gate 5 — mitigation of ungated harm

For each model on ineligible rows, routed minus ungated relationship evidence must be at least +0.05, paired interval lower bound above zero, and cross-model-family Holm-adjusted exact p < .05.

## Adjudication

- `PASS_ROUTED_EXTERNAL_CONFIRMATION`: Gates 0–5 pass in both model families.
- `PASS_ROUTER_SAFETY_ONLY`: Gates 0, 1, 4, and 5 pass in both, but Gate 2 or 3 fails.
- `FAIL_ROUTER_CONFIRMATION`: any integrity, compatibility, safety, or mitigation gate fails.

Even a full pass is limited to this fixed 2,997-row primary corpus, two model families, and ATT&CK 19.1.

## Stop and no-retuning rules

- Do not inspect any target router-label metric before freeze.
- Do not inspect partial model predictions, summaries, or parsed distributions.
- Do not alter target IDs, exclusions, label definition, classifier, calibration, threshold, retriever, evidence count, prompts, parser, model revisions, estimands, statistical families, or decision thresholds after freeze.
- A technical failure may be retried unchanged and must be logged.
- A failed router gate does not authorize threshold search; a new design requires a new PX number and new holdout.
- No raw benchmark redistribution is authorized.
- No PX-068 job may launch until root completes a second review of the freeze manifest and explicitly approves launch.

## Verified APA references

Athena Software Group. (n.d.). *AthenaBench* (Commit 39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf) [Data set]. GitHub. Retrieved July 31, 2026, from https://github.com/Athena-Software-Group/athenabench/tree/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf

Alam, M. T., Bhusal, D., Ahmad, S., Rastogi, N., & Worth, P. (2025). AthenaBench: A dynamic benchmark for evaluating LLMs in cyber threat intelligence. In *2025 Annual Computer Security Applications Conference Workshops (ACSACW)* (pp. 443–450). IEEE. https://doi.org/10.1109/ACSACW69556.2025.00072

Open manuscript: https://arxiv.org/abs/2511.01144

Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). CTIBench: A benchmark for evaluating LLMs in cyber threat intelligence. *Advances in Neural Information Processing Systems, 37*, 50805–50825. https://doi.org/10.52202/079017-1607

Geifman, Y., & El-Yaniv, R. (2017). Selective classification for deep neural networks. In *Advances in Neural Information Processing Systems* (Vol. 30). https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html

Lekssays, A., Shukla, U., Sencar, H. T., & Parvez, M. R. (2025). TechniqueRAG: Retrieval augmented generation for adversarial technique annotation in cyber threat intelligence text. In *Findings of the Association for Computational Linguistics: ACL 2025* (pp. 20913–20926). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.findings-acl.1076

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems* (Vol. 33). https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html

Required attribution: **This research utilized software developed by Athena Security Group.**
