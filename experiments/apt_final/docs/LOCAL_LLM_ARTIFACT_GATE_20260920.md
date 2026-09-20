# Local LLM track: artifact feasibility gate

Reviewed September 20, 2026. **Proceed with artifact verification; hold novelty and effectiveness claims.** This is a bounded literature and access audit, not a new model experiment. The immediate research priority remains the faithful MAGIC baseline; this memo preserves a feasible later local-LLM prerequisite.

## Existing work changes the proposed contribution

[OCR-APT](https://arxiv.org/html/2510.15188v1) already compares local language models and embeddings. Its [author workbook](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/Experiments_with_locally_deployed_LLMs.xlsx) includes Llama3-8B, Gemma7B, Mistral7B, DeepSeek-LLM7B, DeepSeek-R1-7B and Llama3.2-1B; its selected local combination uses Llama3-8B and Granite125M embeddings. The principal local/cloud rows change both components and score recovered indicators and attack stages. They do not isolate the language-model effect or establish detection-F1 noninferiority.

The [pinned investigator source](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/src/ocrapt_llm_investigator.py) implements Ollama language models and Ollama/Hugging Face embeddings. That support does not itself verify operation with networking disabled. [SHIELD](https://arxiv.org/html/2502.02342v1) already evaluates local Qwen2.5-32B against GPT-4o and other models; [CAPTAIN](https://arxiv.org/html/2607.20832v1) uses Qwen3-0.6B. A local deployment or Qwen substitution alone is insufficient novelty.

[PROV-LLM's publication](https://doi.org/10.1109/TrustCom66490.2025.00113) was verified through publisher/Crossref metadata. This bounded search did not obtain accessible primary full text, author code or data. Its exact models and cloud dependence remain unverified; failure to locate artifacts is not proof that none exist.

## What is accessible now

The [OCR-APT dataset release](https://zenodo.org/records/17254415) lists `dataset.tar.xz` (2,940,005,988 bytes; published MD5 `bd6aa111af451e9bee44bc69dcab710b`), GraphDB repositories (1,606,268,656 bytes), and RDF loading files (911,703,296 bytes). An actual HTTP range request returned status 206, bytes 0–63 of the dataset archive and the XZ signature. **The full archive was not acquired, checksum-verified or inspected in this audit.** Metadata reports open access; dataset redistribution licensing was not established separately from the repository's Apache code license.

The [author schema](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/datasets_Documentation.md) describes source/destination IDs, node and edge types, timestamps, node attributes and malicious UUID annotations. Those fields could support a richer investigation experiment than our normalized MAGIC arrays. Their actual availability, joins and independent campaign coverage still require inspection.

Pinned author commit: `d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3`. The workbook was read from 76,114 downloaded bytes in memory (SHA-256 `6d79cf865caf361e5591284edba4cd3d1162be17af2cfa2cb3cc4f06acc8cf65`). No author code, model or cached checkpoint was executed.

## Smallest useful prerequisite

1. Download and checksum the preprocessed dataset; inventory archive members safely before extraction or loading executable serialization formats.
2. Audit one host's evidence fields, annotation joins, benign coverage and grouping metadata. Prepared rows are not automatically independent campaigns.
3. Reconcile published reports with model/configuration identities and the workbook's scoring endpoint. Freeze detection, indicator recovery and evidence-supported reconstruction as separate outcomes.

There is a concrete endpoint reconciliation issue: the published [CADETS final report](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/recovered_reports/darpa_tc3/cadets/final_comprehensive_report.md) has no model identity metadata. A simple case-sensitive substring check finds 7 of the 16 strings in the [published IOC annotation](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/groundtruth/recovered_reports_IOCs/cadets_groundTruth_IOCs.json); the workbook's cloud row reports 11/16. **This exploratory text check is not a reproduction score or evidence that the reported result is wrong:** report versions, aggregation and scoring rules have not been reconciled. Missing annotations also cannot establish that other report claims are false. The paper's local-model paragraph names OpTC501 for a stage loss where its table and workbook place that loss on OpTC201; resolve this discrepancy before adopting the comparison.

**Go/hold:** GO for the CPU-only artifact gate, which needs no dataset-owner response. HOLD new inference and novelty claims until the endpoint is reproducible. A later study could assess independently verified offline operation and evidence-grounded reporting at a fixed resource budget, with language model and embedding effects separated. Its practical value and research novelty would require distinct evidence.
