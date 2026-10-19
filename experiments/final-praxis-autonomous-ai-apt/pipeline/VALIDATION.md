# Engineering validation — October 19, 2026

**Data:** generated synthetic fixture only. **Scientific finding:** none. **Run:** [synthetic_smoke_20261019_v2](synthetic_smoke_20261019_v2/REPORT.md).

## Completed checks

- Nine automated tests passed: deterministic generation, duplicate-trial rejection, unseen-group leakage rejection, source/class confounding rejection, control separation, unexpected-feature rejection, training-only imputation, paired-bootstrap identity and strict JSON parameter serialization.
- All five requested classifier families ran, alongside logistic and dummy baselines. The transformer is the documented small FT-style implementation.
- 22 model/feature combinations generated 5,808 saved predictions and 66 metric records.
- `verify_run.py` verified artifact/input/source/schema hashes, expected prediction coverage, original labels/partitions and recomputed metric agreement.
- Full and reduced feature representations, host/network/timing-only models and retrained family removals completed.
- Controls retained separate labels and no fabricated binary ground truth; their predicted-AI rates are in `control_summary.csv`.

## Intended fixture behavior observed

The fixture intentionally gives training groups an easy timing/tool cue that shifts in unseen groups. Random forest with full features achieved known-group macro-F1 0.958 and unseen-group macro-F1 0.371. Its reduced host/network representation achieved unseen-group macro-F1 0.767. This demonstrates that the harness exposes the designed shift; it says nothing about real attacker behavior or the best real-data classifier.

The primary model was selected on validation data before final scoring. Bootstrap intervals are descriptive and unadjusted. No confirmatory H1/H2/H3 decision was made.

## Recheck the committed evidence

From this directory, using the installed environment:

```powershell
python -m pytest -q
python verify_run.py --input fixtures/synthetic_trials.csv --run synthetic_smoke_20261019_v2
```

The run manifest records exact dependency versions, seed and input/code hashes. See [remaining work](README.md#remaining-before-the-final-study) before using this harness for final research.
