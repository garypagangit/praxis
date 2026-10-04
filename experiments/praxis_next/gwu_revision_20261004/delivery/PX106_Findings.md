# PX-106 — Warning Loss Versus Exact-Class Negative Flips

## Result

Stage-only regression accounting omits warnings that had the wrong attack-stage name before becoming benign. Ordinary binary attack-versus-benign negative-flip counting captures these changes. This experiment supports using both levels in the audit; it does not introduce a new metric or outperform binary regression accounting.

### Existing primary example: clean evidence, budget three

The reference is entropy acquisition; the candidate is error-focused acquisition. Each row evaluates the same 3,442 exfiltration-labeled flows. Fitting seeds are not independent campaigns.

| Seed | Warnings lost | Correct stage to benign | Wrong attack stage to benign | Warnings gained | Net change |
|---|---:|---:|---:|---:|---:|
| 8101 | 901 | 8 | 893 | 4 | -897 |
| 8102 | 4 | 2 | 2 | 1 | -3 |
| 8103 | 25 | 4 | 21 | 3 | -22 |

The largest loss depends strongly on the fitting seed. For seed 8101, the 893 wrong-stage-to-benign changes were specifically movement predictions on exfiltration-labeled records. They were not correctly recognized movement attacks. This distinction matters when interpreting the mechanism.

All 27 policy pairs and 81 stage-specific transition tables are saved, including zero and opposite changes. The new calculation does not refit models, choose thresholds or search for a favorable test subset. Its independent reconstruction passes 945 checks.

Two of 27 pairs meet the previously stated illustrative tolerances when applied descriptively to test outcomes. This is not an evaluation of prospective calibration-only gate decisions. A tolerance on net recall can also permit individual warning losses offset by gains elsewhere.

## Relation to prior work

Correct-to-incorrect negative flips are established by Yan et al. (CVPR 2021), and regression-aware learning has already been studied in Android malware detection by Ghiani et al. (2026). AlertPro already reports F1 rising while attack recall falls. Our added measurement is a paired stage-specific transition table on the existing APT evidence-policy experiment. Applying established binary regression accounting to these labels does not establish first-of-kind novelty.

See the October 4 manuscript Section 2.6 and [review assessment](Review_Readiness.md) for links and claim boundaries.

## Reproduce

Use the existing Praxis Python environment with NumPy and scikit-learn. `run.py run` verifies FREEZE.json and refuses to overwrite RESULTS.json. To repeat the original calculation, use a separate copy without RESULTS.json and keep the original freeze and source files unchanged. The frozen private prediction inputs are required. `audit.py` independently reconstructs the published count tables and metrics from those inputs.

No paid compute, new model fits, human participants or production deployment. The protocol precedes this calculation but the source data were already exposed; this is an exploratory reanalysis.
