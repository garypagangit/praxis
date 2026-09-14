# Independent post-run audit code

These scripts preserve the coordinator's independent reviews of saved 009 and 010 artifacts. They require Python and NumPy. They make no cloud or model calls and do not import the experiment workers or their comparison functions.

**These audit sources were archived after the model runs and initial reviews.** They are not prospectively frozen experiment code. [Archive provenance](AUDIT_SOURCE_ARCHIVE.json) records their hashes, archival time and the earlier review-receipt hashes. Model/protocol provenance remains in the original frozen bundles.

Run from any directory, replacing the uppercase path arguments with local paths:

```text
python audit_009_independent.py --source SOUP_SOURCE_DIRECTORY --results SAVED_GPU_RESULTS_DIRECTORY --output REVIEW_OUTPUT.json
```

The source directory contains `QUALIFICATION_PROTOCOL.md`, `BUNDLE_MANIFEST.json`, the worker files, `RESULTS.md` and `results/GPU_SUMMARY.json`. Use `--canonical-summary` and `--canonical-results` if the last two files are stored elsewhere. The script reads all 20 saved safetensor files through its own binary parser. It checks exact output/gradient/final-state equality, finite nonzero gradients, assignments, owned staging, timing and both timing aggregations. It cannot regenerate missing model outputs or establish a useful speedup.

```text
python audit_010_results_independent.py --source FORECASTING_SOURCE_DIRECTORY --cloud-results SAVED_CLOUD_RESULTS_DIRECTORY --source-review INDEPENDENT_010_REVIEW.json --output REVIEW_OUTPUT.json
```

The cloud-results directory contains `new3/` and the setup/control/environment receipts. This archived version reconstructs the fixed numeric stream and checks every saved residual and alarm, source/asset identities, count metrics and reported operational-gate arithmetic. Original25 and calibration deliberately remain pending in this version. Individual repeat forecasts, quantile arrays and latency samples were not archived, so the script does not claim to independently reproduce those measurements.

Use a new output filename to retain earlier receipts. Errors or missing inputs produce a failure receipt and a nonzero exit status. A partial 010 result returns zero only to indicate that its released new3 audit completed; its `overall_010_qualification` field remains `PENDING`.

`AUDIT_ARCHIVE_VALIDATION.json` records one local replay of these audits against the same stored artifacts, comparing the documented check identities/verdicts and numerical fields. This validation involves no model inference and no new scientific experiment.
