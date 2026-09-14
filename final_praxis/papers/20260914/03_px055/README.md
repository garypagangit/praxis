# PX-055 completed paper and reproducible evidence

Read the finished [PDF](PAPER.pdf), editable [Word document](PAPER.docx), or [Markdown source](PAPER.md). All 21 PDF pages have been inspected at original resolution; [VISUAL_QA.json](VISUAL_QA.json) binds that review to the delivered PDF hash. The completed result is **H1_PRECISION_INVARIANT_BOUNDED**: a safe-text geometric measurement across three models and three precision conditions. E3 is descriptive only; E4 is negative and does not test original H4. This package does not claim a successful semantic-safety mechanism or defense.

## What is included

- Nine original compressed NPZs containing full-width, all-layer safe-text activation captures, with IDs, labels, splits, token counts and text/token hashes. Each is below 50 MB; raw cell artifacts total about 247 MB.
- Nine matched metadata files and nine behavior files containing all 4,050 XSTest condition records, including per-prompt refusal flags, phrase IDs, hashes, token counts and finish metadata.
- Six E4 files containing all 180 paired-condition prediction records. Projected activation vectors and modified model weights were not retained.
- Exact frozen scientific configuration, safe-text source, production runtime, dependency pins and the historical independent adjudicator.
- Historical decisive results, production summary, source identities, prelaunch checks, and explicit copy/redaction provenance.
- A portable scientific reanalysis, seven synthetic controls, two result figures and their generation script, successful reproduction receipts, and a fresh public-source hash check.

The exact scientific input inventory is [FILE_MANIFEST.json](FILE_MANIFEST.json). It covers `code/` and `evidence/`, excluding generated outputs and writing/rendering artifacts. [COPY_PROVENANCE.json](evidence/source/COPY_PROVENANCE.json) records original and packaged hashes and identifies redacted or derived copies. Every raw cell file is byte-identical to its source. No file requires a OneDrive path or a cloud account for numerical reproduction.

## Local numerical reproduction

Use Python 3.11 or later and a dedicated environment. The recorded reproduction uses Python 3.11.9 and NumPy 2.4.4. From this directory:

```text
python -m pip install -r code/requirements-reproduction.txt
python -B code/test_reproduction_controls.py
python -B code/reproduce.py --output reproduced
```

The last command verifies all input hashes, reconstructs geometric and behavioral calculations from raw captures, and compares every computed scientific field to the archived independent adjudication. It writes a new `RECOMPUTED_RESULTS.json` and `REPRODUCTION_RECEIPT.json` into `reproduced/`, leaving the delivered `results/` receipts unchanged. The recorded result is 4,161 comparisons, zero mismatches, with identical final hypothesis decisions. The fully self-contained run, without any external source path, also passed: [offline reproduction receipt](results/offline_reproduction/REPRODUCTION_RECEIPT.json). A typical recorded local run takes roughly 10–13 seconds; runtime varies by machine and BLAS configuration.

The default path uses the packaged, authenticated XSTest ID/label/type/prompt-hash manifest. This permits complete row pairing and numerical recounting without distributing prompt text. To independently verify that manifest against the original public CSV, obtain it in an external cache:

```text
python -B code/fetch_xstest.py --output /path/outside-this-release/xstest_prompts.csv
python -B code/reproduce.py --output reproduced_source_checked --xstest-source /path/outside-this-release/xstest_prompts.csv
```

Use a Windows absolute path instead on Windows. The retrieval script makes one public GET, requires the exact historical SHA256, and fails without writing if the upstream file changes. It refuses to write raw prompt text inside the release. It does not run a model. The delivered [PUBLIC_SOURCE_RETRIEVAL.json](results/PUBLIC_SOURCE_RETRIEVAL.json) records an actual fresh retrieval matching SHA256 `11783fb294ed017473ee53c207d71f2161c7672c8d0b037501e78387f801cb5a`. The delivered reproduction also validated the original cached source bytes against the full ID manifest.

To regenerate the two presentation figures, install Matplotlib and run:

```text
python -m pip install matplotlib==3.10.8
python -B code/make_figures.py
```

That script reads the delivered, hash-verified numerical results and overwrites only the two PNG figures and their receipt. The actual recorded Matplotlib version is stored in [FIGURE_RECEIPT.json](results/FIGURE_RECEIPT.json). Figures are descriptive views of the registered results, not additional statistical tests.

## Reproduction limits

The portable wrapper calls the historical independent numerical implementation, which is separate from the production analysis. Thus it reproduces the independent analysis; it is not another independently authored mathematical implementation. It checks scientific data and cell-level runtime/load metadata, but does not repeat omitted cloud launch, credential, storage-location or stopped-host attestation. The original historical adjudication remains available as the authoritative record of those checks.

The frozen production runner is included to document exactly how the original captures and outputs were made. It is not invoked by either reproduction command. Repeating model inference would require separately obtained exact checkpoint revisions, the original compatible CUDA/PyTorch environment and model access permissions. Model weights are not included. No new inference, cloud job, or modified-checkpoint experiment was performed to build this release.

Decoded XSTest responses were intentionally never retained. The package can recount the stored phrase-matcher decisions and check their row/hash lineage; it cannot rerun the phrase matcher on unavailable text or obtain an independent semantic judgment of those historical responses. A completion hash does not repair that limitation. Similarly, E4 predictions and bootstrap intervals can be recomputed, but the discarded projected activations cannot be independently recalculated without new model execution.

The R3 amendment and historical source manifest have explicitly redacted public copies. Their original hashes were preserved, and the amendment's original Git bytes were verified during packaging. The portable verifier does not pretend the redacted document has the original byte hash, nor does it attest the omitted operational source files listed in the historical manifest. All scientific cell-file hashes and the frozen scientific configuration are exact.

## Data attribution and source history

XSTest is by Paul Röttger, Hannah Rose Kirk, Bertie Vidgen, Giuseppe Attanasio, Federico Bianchi and Dirk Hovy. Cite their NAACL 2024 paper, [XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models](https://aclanthology.org/2024.naacl-long.301/). The [upstream repository](https://github.com/paul-rottger/xstest) distributes prompts under CC-BY-4.0. Its license is included at [XSTEST_LICENSE.txt](evidence/licenses/XSTEST_LICENSE.txt). The distributed derivative is an ID/label/type/hash manifest; prompt wording is unchanged in the source used for analysis, and no raw prompt text is distributed here.

The safe-text corpus and experiment/analysis code are retained as project-authored source with their existing notices. This package does not relicense model weights or third-party software. The original checkpoint sources are [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct), [Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct), and [Gemma-2-9B-it](https://huggingface.co/google/gemma-2-9b-it); exact revisions are in the frozen configuration. Repeating inference remains subject to their upstream access and license terms.

The historical scientific result and its hypotheses are not edited by the paper package. The manuscript is a later reporting artifact. The package presents the positive geometric threshold result alongside the descriptive behavior relation, negative E4 proxy, direct prior-art overlap, style/semantic distinction, and incomplete response-text evidence.
