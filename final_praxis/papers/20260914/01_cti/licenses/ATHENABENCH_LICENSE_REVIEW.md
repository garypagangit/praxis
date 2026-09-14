# PX-068 AthenaBench Access and License Review

Reviewed: **2026-07-31**

Repository and data revision: `Athena-Software-Group/athenabench@39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf`

## Determination

The pinned repository contains two license files. Both grant academic-research, educational, internal-experimentation, and non-commercial collaboration use, require attribution, and prohibit commercial use without separate written permission. PX-068 may use the artifact only as a non-commercial research evaluation with Athena Security Group attribution.

The licenses do not establish an unrestricted public-data redistribution right. Therefore PX-068 will not publish or commit the raw 3,000-question file, sealed answers, or modified copies. A reproducibility release may publish the pinned repository commit, source URL, cryptographic hashes, code, frozen IDs/hashes, router specification, model predictions where permitted, and aggregate or derived non-sensitive scores. Anyone reproducing the experiment must obtain the source artifact directly under its then-applicable terms.

If this Praxis is conducted for a commercial, proprietary, revenue-generating, consulting, SaaS, or paid data-analysis purpose, execution is blocked until Athena Security Group supplies written commercial permission. This review is a conservative research-use determination, not legal advice.

## Pinned license evidence

| Repository file | Bytes | SHA-256 | Material scope |
|---|---:|---|---|
| `License.md` | 3,213 | `bc1c0c70176e56b920171057fc2c410590162d1f918292d32faf57e0443fc0a1` | Academic Research License, non-commercial use only; attribution required. |
| `License.txt` | 2,574 | `756f79c0f891067b84fb800de105cc45c38291bde430b21ca284fee77f1d494d` | Same academic/non-commercial grant and attribution requirement. |
| `readme.md` | 5,872 | `72c6fbddc26af2cf15a4ae614bf355747933afce6f683ca4f0a7a195eb2df135` | Identifies the full `benchmark/` inventory, the 3,000-row CKT file, execution commands, and required paper citations. |

Primary links at the pinned revision:

- https://github.com/Athena-Software-Group/athenabench/blob/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf/License.md
- https://github.com/Athena-Software-Group/athenabench/blob/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf/License.txt
- https://github.com/Athena-Software-Group/athenabench/blob/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf/readme.md

The two license files contain inconsistent administrative details—different governing-law states and contact addresses—but not different research-use boundaries. PX-068 relies only on the shared, conservative intersection: attributed non-commercial academic research is allowed; commercial use requires written permission; raw redistribution is not assumed.

## Reconciliation with the paper

Section 4.3 of **“AthenaBench: A Dynamic Benchmark for Evaluating LLMs in Cyber Threat Intelligence”** says the authors planned a non-commercial request process for complete-data access upon paper acceptance. At the pinned later repository revision:

- the README describes the full benchmark under `benchmark/`;
- `benchmark/athena-cti-ckt-3k.jsonl` is directly downloadable;
- a fresh retrieval produced 5,994,938 bytes, 3,000 JSONL rows, and SHA-256 `7893643dd98973fff5b2c3230a4f8f08227d7b6b312ba1a73309f97bb56a7542`;
- the repository license expressly permits non-commercial academic research and internal experimentation.

The later repository state therefore supplies access for this non-commercial research run. Public download is treated as access, not as a waiver of license conditions and not as permission to republish the raw benchmark.

## Required attribution

The paper and repository will be cited in every report, and the final artifact will include the attribution requested by the license: “This research utilized software developed by Athena Security Group.”

Verified paper reference:

Alam, M. T., Bhusal, D., Ahmad, S., Rastogi, N., & Worth, P. (2025). AthenaBench: A dynamic benchmark for evaluating LLMs in cyber threat intelligence. In *2025 Annual Computer Security Applications Conference Workshops (ACSACW)* (pp. 443–450). IEEE. https://doi.org/10.1109/ACSACW69556.2025.00072

Open manuscript: https://arxiv.org/abs/2511.01144
