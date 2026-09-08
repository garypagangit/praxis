# Final Praxis discovery results — 8 September 2026

All three frozen discovery experiments completed real model execution and independent verification. All three results are **Negative** under their original decision rules. The hypotheses and thresholds were not adjusted to obtain favorable results.

| Experiment | Evidence | Why the result is Negative | Report |
|---|---|---|---|
| 001: Outcome-state verification | 400 primary cases, 40 full-state diagnostics, 1,240 real generations | Learned judge accepted 7/200 invalid outcomes (3.5%); the required 10% judge-gap gate and cross-family collateral gate failed. Its 205/400 numeric-schema errors limit semantic interpretation. | [PDF](../output/doc/final_praxis_20260908/FINAL_PRAXIS_001_REPORT.pdf) |
| 002: Cascade containment | 480 workflows, 1,164 real generations | Clean completion was 51/60 (85%) in every arm, below the required 90% floor. Invalid injected-condition actions fell from 10/60 to 0/60, but nine of those ten baseline failures also occurred clean. | [PDF](../output/doc/final_praxis_20260908/FINAL_PRAXIS_002_REPORT.pdf) |
| 003: Adaptive investigation stopping | 400 cases, 3,200 real investigation rounds | Reviewed stopping accuracy was 34.5% versus 54.25% fixed-long; 34/400 early incorrect endpoints had a later correct answer, and every case required review. Utility, harm and review gates failed. | [PDF](../output/doc/final_praxis_20260908/FINAL_PRAXIS_003_REPORT.pdf) |

The 5,604 discovery generations are separate from infrastructure pilots and deterministic fixtures. The generated inert benchmarks establish bounded engineering observations. Shared oracle/label definitions, parameterized templates, one discovery agent model, judge schema noncompliance and counterfactual policy evaluation limit broader claims. No cross-model replication or real-world deployment-safety finding is established.

003's frozen verifier passed in the cloud. Strict local replay rejected three machine-precision confidence-bound differences; a separately labeled numerical replay and a second raw-response reconstruction confirmed every count and gate. The original strict failure, cloud PASS and supplemental evidence are retained separately.

Each report follows the five-chapter Praxis structure, with abstract, research questions, literature, graphical methodology, methods, results, discussion, limitations, conclusions, references and provenance. Word versions and verification summaries are linked from the [dashboard](index.html). Exact source and raw-result archives are mapped in the [evidence index](ARTIFACT_INDEX.md).

Both previously stopped GPU instances started for this task have returned to **stopped**, confirmed by the AWS API. Estimated instance compute through the stop requests is approximately **USD 1.43**, using the recorded USD 1.006 hourly rate; this excludes storage, transfer, taxes and discounts and is not an AWS invoice. See the [compute receipt](execution/20260908/COMPUTE_CLOSEOUT.json).
