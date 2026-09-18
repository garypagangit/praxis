# Data and model attribution

This is a derivative research pilot over the project's frozen CTIBench and MITRE ATT&CK evidence. Original source terms remain applicable; no third-party endorsement is claimed.

CTIBench authors: Md Tanvirul Alam, Dipkamal Bhusal, Le Nguyen, and Nidhi Rastogi. [Paper](https://arxiv.org/abs/2406.07599), [official dataset](https://huggingface.co/datasets/AI4Sec/cti-bench), [release DOI](https://doi.org/10.57967/hf/2506). The frozen source package records Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International for the covered dataset. This pilot projects the question/option/evidence fields, records source-group assignments and adds checker predictions and derived outcomes. It is not a new benchmark authored by this project.

ATT&CK evidence is attributed to The MITRE Corporation. [Versioned STIX source](https://github.com/mitre-attack/attack-stix-data). The exact notice from the frozen source package is preserved in MITRE_ATTACK_LICENSE.txt. The selected text was normalized and formatted by the original experiment's evidence builder.

Neural checker: [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2), pinned revision and file hashes in relevance_metadata.json. Weights are cached separately and are not distributed in this result folder. Original generator responses were produced by Llama-3.1-8B-Instruct and Qwen2.5-7B-Instruct; their frozen revisions and inference conditions are documented in the canonical source paper.

Original data/source hashes and paths are in DATA_AUDIT.json. The original package's detailed attribution record is C:/w/px_final_20260917/final_praxis/papers/20260914/01_cti/licenses/SOURCES_AND_LICENSES.md. No AthenaBench question data is included here.
