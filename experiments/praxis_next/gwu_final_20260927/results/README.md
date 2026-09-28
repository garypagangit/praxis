# Results and dataset publication supplement

This folder assembles completed evidence for the final praxis. It introduces **zero model fits, inference runs, downloads, or threshold changes**. Original experiment files remain unchanged.

## Assembly materials

- [Dataset chapter](DATASET_CHAPTER.md): source lineage, labels, feature groups, actual denominators, qualification decisions, and a real published aggregate example.
- [Results chapter](RESULTS_CHAPTER.md): complete coverage, method tradeoffs, seed sensitivity, secondary-policy scope, and measurement-versus-practice interpretation.
- [Complete group tables](COMPLETE_GROUP_TABLES.md): all 308 means in six-column printable tables.
- [Dataset references](REFERENCES.json): eight source references with publication status; CasinoLimit and CAM-LDS supplement the main paper's existing references.
- [Figure inventory and captions](FIGURES.json): five new figures, each as high-resolution PNG and vector PDF.
- [Coverage](COVERAGE.json), [arithmetic checks](ASSEMBLY_AUDIT.json), and [input hashes](SOURCE_MANIFEST.json).

## Tables and their units

| File | Scope | Interpretation |
|---|---|---|
| tables/all_configuration_metrics.csv | 588 saved evaluation records | One arm/condition/seed; not one independent experiment |
| tables/all_class_metrics.csv | 1,764 class records | Source precision, recall, F1, AP, ROC-AUC plus confusion-derived counts |
| tables/all_confusion_counts.csv | 5,880 cells | Integer counts; true rows and predicted columns |
| tables/all_group_means.csv | 308 means | Three same-event fits for primary studies; perturbation means or one deterministic view for PX083 |
| tables/all_class_group_means.csv | Per-class group means | Availability counts accompany fields; a missing ranking value is not imputed |
| tables/all_subgroup_metrics.csv | 6,732 existing subgroup records | Original capture, role-stratum, or run detail where available |
| tables/all_subgroup_class_metrics.csv | 16,344 subgroup-class records | Absent-stage support is explicit |
| tables/paired_stage_metrics.csv | Original complete paired reanalysis | Byte-identical source copy, including all stages and conditional intervals |
| tables/capture_omissions.csv and seed_omissions.csv | Complete sensitivity inventory | Fixed predictions; finite sensitivity, not new fits |
| tables/native_class_counts.csv | D1 native-label counts | No made-up S-DAPT row count |

`source_snapshots/` retains the original full JSON, including fields that are not in a normalized CSV and the original-threshold PX083 supplement. Its metadata remains part of the scientific interpretation.

All normalized rates and F1 values use the zero-to-one scale; plots explicitly identify percentage-point differences or F1 differences multiplied by 100. `negative_flags` means benign false alerts for UNRAVELED but **other-technique flags for PX083**. The `negative_definition` column preserves that distinction. Attack warning metrics are deliberately blank for PX083: a T1105 false negative is not proof that an event was called benign. Its binary false-negative count has a separate field.

ROC-AUC and average precision are copied only where saved in the original score-based results. They cannot be reconstructed from a confusion matrix. An absent value remains blank/null. Existing zero-division conventions for precision, recall and F1 are retained; `recall_supported` identifies whether the true class was present. Stage warning recall is blank when the true-stage denominator is zero. Neither an absent stage nor an inaccessible dataset is silently treated as successful detection.

## Reproduction

From the repository root, run:

```powershell
& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' 'experiments/praxis_next/gwu_final_20260924/results/build_results.py'
```

The builder reads existing public aggregate inputs, checks confusion-derived arithmetic, exports the complete tables and renders all five figures with Matplotlib. It does not access private raw traces or private model predictions. The two narrative chapters are authored assembly material. Public arithmetic reproduction is narrower than refitting models or independently verifying source annotations.

The publisher should read the main paper's limits together with this supplement: one previously examined primary campaign, author discovery/exfiltration semantics, 35 movement evaluation labels (18 in the temporal anchor), retrospective warning analysis, dependent fitting comparisons, simulated telemetry interventions, and a different target/negative definition in the secondary technique study.
