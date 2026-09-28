> **Integrated edition available:** These results are now incorporated in the [full paper and defense](../gwu_final_20260928/README.md). Download the full evidence archive from the [dated release](https://github.com/garypagangit/praxis/releases/tag/praxis-integrated-20260928).

# Campaign validation delivery

AWS reconnection succeeded with profile `praxis-build`; STS identity was verified on 28 September 2026. Experiments ran locally and did not require cloud compute.

## Read first

- `Gary_Pagan_Campaign_Validation_Addendum.pdf` / `.docx`: paper companion.
- `Gary_Pagan_Campaign_Validation_Defense_Addendum.pptx` / `.pdf`: five GWU defense appendix slides.
- `Validation_Defense_Notes.txt`: complete speaker notes.
- `CAMPAIGN_VALIDATION_REPORT.md`: full readable report with every comparison.
- `RESULTS.csv` / `.json`: all held-out results, including all three seeds and both executions.
- `Campaign_Validation_Full_Evidence.zip`: all eight complete source archives, prepared arrays, 42 fitted models, every saved prediction and development OOF output, protocol, source rules, code and audits.

## Interpretation

Completed an adapted validation on a different public source, using six development executions and two later held-out executions. This is not an exact replication of the original four-class, two-evidence-group experiment.

The original direction (higher macro-F1 together with lower exfiltration warning recall under error-focused selection) appeared in 0 of the 6 execution-by-seed comparisons and 0 of the 3 pooled seed comparisons. The adapted experiment did not reproduce that direction on either held-out execution.

Wilson shows a small score/warning tradeoff in the opposite policy order: entropy has higher F1 but misses 1, 3 and 8 more exfiltration warnings across seeds (4 of 21,219 on average, or 0.018851 percentage points). On Harrison, entropy improves both F1 and warning recall. This secondary descriptive finding is small and execution-specific; the frozen primary direction remains unreplicated.

This addendum accompanies the previously delivered final praxis and defense. The September 27 originals are preserved in `../praxis_final_20260927`. The older statement that there are no external fitted replications should now be read with this added, explicitly adapted AIT experiment. The old four-class/two-group results are not replaced by three-class/one-group scores.

All 3,465,342 source rows were examined; 2,397,158 training and 1,067,211 evaluation rows are eligible. The audit passed 1,245 checks. The five-slide addendum can follow the external-qualification discussion or be used as defense backup material.

## Reproduction

The evidence archive contains `reports/`, `data/`, `documents/` and `slide_source/`. On this workstation the data root is `C:/w/campaign_validation_20260928` and the Python environment is `C:/w/praxis_full_release_20260927_env/Scripts/python.exe`. Extract `data/` into that root or adjust the documented absolute paths for another machine, recording any change. Run the scripts as described in the report. Rebuilding the slide deck also requires the bundled artifact-tool and original GWU template (included under slide_source).

`FINAL_MANIFEST.json` records output hashes and archive integrity. Source and model inventories are independently hashed inside the evidence. Publisher metadata, licensing information and original notebooks remain included. No publisher notebook was executed.

Final documents: C:\Users\garyp\OneDrive\Documents\codex\output\campaign_validation_20260928
