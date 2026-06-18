# GML Committee Feedback Progress Response

Date: 2026-05-18

## Sources Reviewed

- `C:\Users\garyp\Downloads\Gary Pagan GWU DEng GML to Detect APT Final 04012026 AIRv02.docx`
- `imports/gml_to_detect_apt_final/gml_to_detect_apt_final.py`
- `imports/gml_to_detect_apt_final/README.md`
- `PRAXIS_PREWRITE_GAP_CLOSURE_REPORT.md`
- `PREWRITE_GAP_CLOSURE_PLAN.md`
- `runs/dapt-cross-dataset-mlp-20260429/report.md`
- `runs/stage2-graph-head-suite-20260428/report.md`
- `runs/final-praxis-unraveled-graph-head-followup-20260428.md`
- `runs/mlp-optuna-support-floor-20260429/report.md`
- `runs/tabular-baseline-suite-20260429/report.md`
- `runs/gml-cross-dataset-comparison-20260518/GML_CROSS_DATASET_COMPARISON_REPORT.md`
- `reports/gwu_committee_response/GML_CROSS_DATASET_REPRODUCTION_RESULT_20260518.md`
- `runs/dapt-soh-gml-apples-to-apples-20260519/SOH_GML_APPLES_TO_APPLES_REPORT.md`
- `reports/gwu_committee_response/DAPT_SOH_GML_APPLES_TO_APPLES_RESULT_20260519.md`
- `reports/tta_streaming_apt/DAPT2020_EXTERNAL_VALIDITY_NOTE_20260512.md`
- `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md`
- `reports/EXPERIMENT_FINAL_EVALUATION_20260511.md`

## Executive Status

Material progress has been made, but the original GML praxis should not be defended in its old form.

The later experiment work answers several committee concerns with evidence: fairer tabular baselines were run, DAPT-2020 class-support limitations were quantified, cross-dataset attempts were performed, graph-head substitutions were tested and mostly failed, a fresh AWS GML cross-dataset reproduction compared all five GML families on DAPT2020 and Unraveled, a DAPT2020 Soh-style apples-to-apples rerun compared traditional baselines and GML heads under the same split/preprocessing surface, and the research portfolio was reframed around narrower, better-supported claims.

The most important finding is that the original ST-GCN-centered thesis is not supportable. The paper itself reports R-GCN as the best GML model and ST-GCN as the weakest GML model. The revised position should be either:

1. Use the GML work as a negative/diagnostic study showing that simple graph construction on DAPT-2020 is not enough for a strong APT detection claim, or
2. Rewrite the GML study as a bounded architecture comparison in which typed relational edges appear more useful than temporal windows on DAPT-2020, while explicitly avoiding operational/generalization claims.

The stronger current Praxis path is not the original GML paper. It is the later bounded TTA result, with DAPT-2020 retained only as external-validity/limitation evidence.

## Committee Issue Progress Matrix

| Committee issue | Current progress | Evidence already available | Work left |
|---|---|---|---|
| Academic rigor: ground methods, model choices, graph construction, tuning, and interpretation in prior research | Partial progress. The GML draft has more citations than before, but many method decisions are still explained as intuitive rather than experimentally or literature-grounded. Later Praxis 06 and Praxis 07 drafts are much stronger examples of bounded literature framing. | GML draft includes GIN, GATv2, R-GCN, ST-GCN, DGI citations and taxonomy table. Later reports use explicit anchors such as Wang et al. for TTA, MITRE ATT&CK, Lewis et al. for retrieval, and graph/provenance papers. | Rewrite the GML methodology so every model choice maps to a specific graph-learning capability and prior paper. Add a short "why this graph construction" subsection. Remove broad claims that GML generally "outperforms" without same-pipeline baselines. |
| Realign thesis/H3 with findings | Substantial progress in understanding, but not fully fixed in the original paper. The paper still states ST-GCN as the expected best model in the thesis/H3, while later results and the paper's own discussion reject H3. | GML draft Table 4-3: R-GCN F1 `94.7%`, GATv2 `94.6%`, DGI `93.7%`, GIN `87.8%`, ST-GCN `82.6%`. Paragraphs 0636-0644 reject H3 and say R-GCN outperformed ST-GCN. | Rewrite thesis, RQ3, H3, abstract, conclusion, and contribution language. New H3 should be evidence-neutral, e.g. "typed relational models will outperform untyped or temporal-only graph variants when DAPT-2020 stage labels are flow-level." |
| Recreate GML architecture comparison on two datasets | New substantial progress. A fresh AWS GPU reproduction compared `GCN-DGI`, `GATv2`, `RGCN`, `GIN`, and `ST-GCN` on both DAPT2020 and Unraveled under an explicit flow-node classification framing. | `runs/gml-cross-dataset-comparison-20260518/`: DAPT2020 best Macro F1 was `GCN-DGI = 0.5995`; Unraveled best Macro F1 was `GCN-DGI = 0.2859`; ST-GCN was weak on both (`0.2956` DAPT, `0.1853` Unraveled); Data Exfiltration F1 was `0.0000` for every GML model on both datasets. | Use this as a transparent architecture-comparison and limitation study. Do not claim ST-GCN superiority or operational usefulness. Traditional baselines still need same-pipeline rerun if the old GML paper remains the main praxis. |
| Define what is being classified and make graph method consistent | Major remaining issue for the old GML paper. The code classifies flow records as graph nodes, but the paper often describes IPs/hosts as nodes and flows as edges. That mismatch is exactly what the committee flagged. | In `gml_to_detect_apt_final.py`, `build_graph_with_custom_k*` sets each dataframe row/flow as a node with `y = MultiLabel`; edges connect flow-nodes via same source IP, same destination IP, or KNN feature similarity. GML paper paragraphs 0335, 0338, 0595 describe IP/host nodes, which conflicts with the implemented code. | Pick one target. Recommended: "flow-node classification." Define nodes as flow records, labels as DAPT stage per flow, and edges as relationships between flows. Do not call it host-node classification unless the experiment is rebuilt. |
| Redesign and explain evaluation protocol; reconcile temporal overlap, ST-GCN windows, stratified splits, cross-validation | Partial progress. The imported code now uses split-aware temporal features and train-only scaling, but the original description still invites leakage objections because it mixes temporal blocks, stratification, Optuna validation, and overlapping graph windows. | Script uses network-aware 70/15/15 hybrid block split, train-only `StandardScaler`, derived temporal features, and separate train/val/test graph construction. Later Unraveled/TTA work uses stricter held-out source-file splits and explicit leakage checks. | For GML, either rerun a single clean protocol or narrow the claim. Best salvage rerun: fixed train/val/test by day or host/day, no cross-validation language, no overlapping ST-GCN windows across splits, and one sealed test set. |
| Fair comparison with traditional baselines | Substantially addressed for DAPT2020. A new AWS run reran KNN, MLP, and a transparent Soh Bayesian-network proxy, then ran the five GML heads on the same DAPT2020 rows, same stratified 80/20 split, same train-only scaling, and same stage labels. | `runs/dapt-soh-gml-apples-to-apples-20260519/`: same-pipeline results show MLP Macro F1 `0.6386`, KNN `0.6081`, GIN `0.5895`, R-GCN `0.3190`, GCN-DGI `0.3097`, ST-GCN `0.1739`, GATv2 `0.1694`; all models had Data Exfiltration F1 `0.0000` with only `3` DE test rows. | Exact Soh Bayesian-network reproduction still requires Soh's original executable code or a separately validated Bayesian-network implementation. The GML paper can now remove the copied-table comparison and use this same-pipeline DAPT comparison instead. |
| Dataset and overclaiming problem | Strong progress. This is now clearly quantified and reflected in later reports. DAPT-2020 cannot support strong Data Exfiltration or operational generalization claims. | DAPT class support: train DE `10`, validation DE `2`, test DE `2`; full measured DAPT DE support is only `14` after preprocessing. DAPT TTA gate is negative: selected TENT test Macro F1 delta `-0.2874`, Recon delta `-0.6589`, DE support only `2`. Later dashboard says DAPT is appendix evidence only. | The GML paper must soften claims: no operational usefulness claim, no strong DE claim, no general APT detector claim from DAPT alone. Add larger/more recent datasets only if this GML line remains the main praxis. Otherwise use DAPT as a limitation and pivot. |

## Experiments Already Done That Help Answer The Committee

1. Original GML import and local patch.
   - The GML notebook/script was imported under `imports/gml_to_detect_apt_final/`.
   - The original zip included credentials and was sanitized.
   - The code was patched to use local DAPT CSVs.

2. DAPT-2020 cross-dataset MLP attempt.
   - Artifact: `runs/dapt-cross-dataset-mlp-20260429/report.md`.
   - Result: Macro F1 `0.6353`, ROC-AUC `0.9723`, Recon F1 `0.8932`, DE F1 `0.0387`.
   - Value: shows a same-repo tabular run on DAPT and quantifies DAPT DE weakness.

3. DAPT TTA feasibility gate.
   - Artifact: `reports/tta_streaming_apt/DAPT2020_TTA_FEASIBILITY_GATE_20260512.md`.
   - Result: no support for DAPT TTA. Macro F1 delta `-0.2874`; Recon delta `-0.6589`.
   - Value: directly addresses overclaiming; DAPT is a boundary, not proof of generality.

4. Unraveled graph-head follow-up.
   - Artifact: `runs/stage2-graph-head-suite-20260428/report.md`.
   - Result: R-GCN was best of the graph heads, but still much worse than the MLP cascade and official MLP baseline.
   - Value: supports a sober conclusion: simple graph-head substitution does not solve APT stage detection.

5. Fresh AWS cross-dataset GML reproduction.
   - Artifacts: `runs/gml-cross-dataset-comparison-20260518/GML_CROSS_DATASET_COMPARISON_REPORT.md` and `reports/gwu_committee_response/GML_CROSS_DATASET_REPRODUCTION_RESULT_20260518.md`.
   - Result: Compared `GCN-DGI`, `GATv2`, `RGCN`, `GIN`, and `ST-GCN` on DAPT2020 and Unraveled as flow-node APT stage classification.
   - DAPT2020 test Macro F1: GCN-DGI `0.5995`, RGCN `0.5480`, GIN `0.5408`, GATv2 `0.5354`, ST-GCN `0.2956`.
   - Unraveled test Macro F1: GCN-DGI `0.2859`, RGCN `0.2692`, GIN `0.2563`, ST-GCN `0.1853`, GATv2 `0.1749`.
   - Value: directly addresses model-family comparison, stage-level metrics, and two-dataset evidence. It also confirms that the ST-GCN-centered hypothesis should be removed.

6. DAPT2020 Soh-style apples-to-apples baseline and GML rerun.
   - Artifacts: `runs/dapt-soh-gml-apples-to-apples-20260519/SOH_GML_APPLES_TO_APPLES_REPORT.md` and `reports/gwu_committee_response/DAPT_SOH_GML_APPLES_TO_APPLES_RESULT_20260519.md`.
   - Result: Reran KNN, MLP, and a transparent Soh Bayesian-network proxy, then reran `GCN-DGI`, `GATv2`, `RGCN`, `GIN`, and `ST-GCN` on the same DAPT2020 rows, same stratified 80/20 split, same train-only scaling, and same stage labels.
   - Test Macro F1: MLP `0.6386`, KNN `0.6081`, GIN `0.5895`, R-GCN `0.3190`, GCN-DGI `0.3097`, ST-GCN `0.1739`, GATv2 `0.1694`, Soh BN proxy `0.1798`.
   - Value: directly addresses the fair-baseline objection. It shows the old copied Soh comparison should be replaced by a same-pipeline comparison, and it does not support ST-GCN superiority.

7. Fairer tabular baseline work.
   - Artifact: `runs/tabular-baseline-suite-20260429/report.md`.
   - Result: LightGBM and TabNet were tested under the later trusted Unraveled split; neither beat the official MLP.
   - Value: demonstrates that the missing-baselines issue was taken seriously beyond DAPT2020.

8. MLP optimization and ADASYN weighting diagnostic.
   - Artifact: `runs/mlp-optuna-support-floor-20260429/report.md`.
   - Result: 50-trial Optuna search did not replace the official baseline; class weights were shown to be computed after ADASYN.
   - Value: improves methodological rigor around tuning and imbalance handling.

## Recommended Reply To Advisor

Dear [Advisor/Committee],

Since the failed defense I have made material progress on the committee's concerns, but I also want to be clear that the original GML praxis cannot simply be defended unchanged.

I reviewed the original GML paper and the executable experiment lineage. The committee's concerns are valid: the original thesis and H3 were still framed around ST-GCN as the expected best model, even though the reported results show R-GCN performed best and ST-GCN performed worst. I have therefore realigned the research posture. The GML result should no longer be framed as "ST-GCN is best for APT detection." At most, it supports a narrower diagnostic claim: on DAPT-2020, typed relational edge structure appears more useful than the particular temporal-window ST-GCN construction that was tested.

I have also completed several follow-up experiments and reports that directly address the committee's issues:

- I imported and sanitized the original GML codebase, removed unsafe credential handling, and made it runnable locally against DAPT-2020.
- I quantified the DAPT-2020 limitation: after preprocessing, Data Exfiltration support is only `10` train, `2` validation, and `2` test examples. This means no strong Data Exfiltration or operational-generalization claim is defensible from DAPT alone.
- I ran a same-repo DAPT tabular MLP baseline using the later trusted recipe. It reached Macro F1 `0.6353` and Recon F1 `0.8932`, but Data Exfiltration F1 remained only `0.0387`, confirming the dataset limitation.
- I ran a DAPT test-time-adaptation feasibility gate, and it was negative. This is now documented as a boundary on generality rather than hidden.
- I ran graph-head follow-up experiments on the later Unraveled benchmark. R-GCN was again the best graph head, but graph heads did not beat the stronger MLP/cascade baselines. This prevents overclaiming and supports a more rigorous interpretation.
- I added fairer baseline work in the later pipeline, including LightGBM and TabNet, and added Optuna/ADASYN diagnostics to document tuning and imbalance decisions.
- I reran the DAPT2020 traditional baselines and GML heads under the same split and preprocessing surface. The same-pipeline DAPT result does not support the original ST-GCN claim: MLP Macro F1 was `0.6386`, KNN `0.6081`, best GML was GIN `0.5895`, and ST-GCN was `0.1739`.

Remaining work depends on whether the committee wants the original GML study repaired or whether I should proceed with the newer, stronger Praxis direction.

If repairing the GML study, the remaining work is substantial but bounded:

1. Rewrite the thesis, H3, abstract, and conclusion around the actual finding that R-GCN, not ST-GCN, performed best.
2. Redefine the classification target explicitly as flow-node classification, unless the graph is rebuilt as a true host-node/edge-classification experiment.
3. Use the new same-pipeline DAPT baseline/GML rerun instead of comparing directly to Soh (2023). If the exact Bayesian-network result is still required, obtain Soh's code or implement and validate a true Bayesian-network classifier separately.
4. Replace the ambiguous split language with one clean evaluation protocol and remove any plausible temporal leakage objection.
5. Substantially soften claims about operational usefulness because DAPT-2020 is small, synthetic, imbalanced, and has only a handful of Data Exfiltration samples.

My honest assessment is that the original GML paper is approximately halfway repaired as an evidence record, but not yet committee-ready as a revised praxis. The strongest path is to use the GML work as negative/diagnostic evidence and proceed with the newer bounded experiment, where the methodology, baselines, split protocol, robustness checks, and claim boundaries are much stronger.

Respectfully,
Gary Pagan

## Estimated Work Left

| Path | Work left | Recommendation |
|---|---:|---|
| Minimal committee response memo showing progress | 1-2 days | Do this immediately. |
| Repair old GML paper as a bounded diagnostic study | 1-2 weeks | Possible, but must remove ST-GCN-centered thesis and rerun same-pipeline baselines. |
| Make old GML paper a strong main praxis | 3-5+ weeks | Not recommended unless required; DAPT class support remains a structural blocker. |
| Use later Praxis 06 / Praxis 07 results as replacement direction | Already much stronger; packaging remains | Recommended path. |
