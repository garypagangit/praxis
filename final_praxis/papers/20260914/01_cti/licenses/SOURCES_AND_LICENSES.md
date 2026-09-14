# Sources, attribution, and redistribution boundaries

This release combines distinct source materials. Their original terms continue to apply. Inclusion in this research package does not create an unrestricted blanket license over third-party data or software.

## CTIBench

Original authors: Md Tanvirul Alam, Dipkamal Bhusal, Le Nguyen, and Nidhi Rastogi. Base paper: [CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence](https://arxiv.org/abs/2406.07599). Official [dataset card](https://huggingface.co/datasets/AI4Sec/cti-bench) identifies the dataset license as [Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/). The release DOI is [10.57967/hf/2506](https://doi.org/10.57967/hf/2506).

The four `full2500_*.jsonl.gz` files contain CTIBench questions, displayed options, released labels and associated experimental prompts/output. They retain the dataset attribution and noncommercial/share-alike requirements for covered data. They are compressed copies of original experimental prediction files, not original upstream dataset exports. Gzip changes storage only; decompressed prediction bytes are exact. Added fields record model outputs, retrieval condition, and analysis metadata. The original dataset's source URLs remain in each row. No endorsement by the CTIBench authors is implied.

Primary dataset artifact used by the study: SHA-256 `42f8cb0c1d804945cbdcf890411ca6ede3a1e0222fb91966804fed7dc1a19acb`. The original paper's finer source-family subtotal discrepancy was not resolved by changing released data. All 2,500 observations remain represented.

## MITRE ATT&CK

ATT&CK is attributed to The MITRE Corporation. The [versioned STIX repository](https://github.com/mitre-attack/attack-stix-data) and its [license notice](https://github.com/mitre-attack/attack-stix-data/blob/master/LICENSE.txt) are the primary sources. An [exact notice copy](MITRE_ATTACK_LICENSE.txt) is included. The full study used a combined Enterprise/Mobile/ICS ATT&CK 19.1 source with SHA-256 `bca81a8d69218ace1f7b5c706c605d22ad77d64425375b3d7804fdaf87c2ded9`.

The package includes selected evidence text inside archived prompts, attributed to ATT&CK, rather than the complete combined STIX file. The builder applies compacting, normalization, fact selection, and prompt formatting; those are study transformations, not MITRE-authored recommendations. ATT&CK and the ATT&CK logo are trademarks of The MITRE Corporation. No affiliation or endorsement is claimed.

## AthenaBench

Original authors: M. T. Alam, D. Bhusal, S. Ahmad, N. Rastogi, and P. Worth. [Primary paper](https://arxiv.org/abs/2511.01144), [DOI](https://doi.org/10.1109/ACSACW69556.2025.00072), [pinned source repository](https://github.com/Athena-Software-Group/athenabench/tree/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf).

**This research utilized software developed by Athena Security Group.**

The pinned source contains an academic/noncommercial research license, with attribution requirements and commercial-use restrictions. Public accessibility does not establish unrestricted raw-data redistribution. This release consequently contains only question IDs and derived correctness/validity/router indicators, source hashes, aggregate analyses, and study code. It does not include Athena questions, options, sealed answer labels, raw model responses, or the full benchmark corpus. Obtain the source directly under its applicable terms for independent raw-to-label verification. The [archived license review](ATHENABENCH_LICENSE_REVIEW.md) records the precise file hashes and the conservative common terms of the two source license files.

An [exact pinned source-license notice](ATHENABENCH_SOURCE_LICENSE.md) is included. `data/px068_*_derived.jsonl.gz` is a documented projection of authenticated archived predictions, assignments, and truth. It preserves both the original analyzer's `legacy_valid` indicator and the intended A–E validity indicator. It does not replace original scoring semantics or represent a new experiment.

## Models and study software

The model sources were [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) and [Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct). No model weights are distributed. Obtain any weights directly under their source terms; this document does not grant rights over them.

Frozen study files are exact copies from the author's repository commit identified in [PROVENANCE.json](../PROVENANCE.json). New packaging code changes neither their licenses nor their scientific decisions. No secrets, model-access tokens, private service endpoints, or cloud account configuration are needed by the reproduction command. No new external publication or third-party endorsement is represented by this release.
