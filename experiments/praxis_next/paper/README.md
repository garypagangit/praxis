# When Historical Context Helps and Hurts

[Read the paper](manuscript.md) | [Word](historical_context_praxis.docx) | [PDF](historical_context_praxis.pdf)

This empirical praxis manuscript reports four completed development experiments. It includes measured improvements, their costs, unsuccessful comparisons, related work, source limitations and reproducibility evidence. It does not claim a proven novel superior detector or independent confirmation of exfiltration prediction.

## What is supported

- History can improve some stage scores and reduce false alerts, while increasing missed attack warnings.
- A stage-weighted selector recovered more movement annotations than ordinary gating, with higher false-alert and weighted-error costs.
- Evidence selection reduced simulated collection spending, without consistently better recognition.
- Training with later examples materially changed scores on the same evaluation rows.
- A lightweight selector did not add useful transferred hard decisions on the two supplementary recent datasets.

The resulting research question is how to use supporting evidence while separately accounting for false alarms, wrong attack-stage labels and attacks declared benign. The current results motivate that question; they do not settle it with a winning new method.

## Reproduce the document

From the repository root, run `paper/build_manuscript.py` with the scientific Python environment, then `paper/render_manuscript.py` with Python containing python-docx, PyMuPDF and Pillow. Both paths are relative to `experiments/praxis_next`. The renderer uses the repository's existing document formatter and LibreOffice. These commands assemble and format preserved results; they do not train models.

`BUILD_INPUTS.json` binds scientific aggregates and narrative sources. `RENDER_RECEIPT.json` binds the final document versions and records visual review. [Reference audit](REFERENCES.md) preserves primary links, publication status, and the limits of the novelty assessment. [Final verification](../FINAL_VERIFICATION.json) checks the scientific source against pre-fit Git commits and records 24 passing invariant tests.

All model fits used local CPU. The separate AWS acquisition outcome and stopped-worker evidence appear in the [compute record](../compute/README.md). Raw datasets and row-linked predictions remain outside this public document package.
