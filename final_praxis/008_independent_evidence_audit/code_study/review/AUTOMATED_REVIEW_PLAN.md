# Automated review plan

No human semantic judge is required for the proposed executable code study. The primary oracle is the independently reserved test suite; automated checks qualify the artifacts and arithmetic. Automation cannot certify novelty, arbitrary-program correctness or absence of all data contamination. Those remain explicitly bounded claims rather than manual tasks silently marked complete.

The study runner should emit a frozen assignment manifest, a source/test manifest, a sandbox receipt, per-test execution records, per-problem/policy decisions, budget traces and an aggregate summary. The independent reviewer must consume those records without calling a model or changing results. Agree the schema with the runner before execution; adapter code may translate field names but must not redefine outcomes or drop records.

## Required automatic gates

1. **Custody:** verify source/model/test revisions, every artifact hash, frozen protocol commit and environment. Reject duplicate cell IDs and unknown source variants. Keep retries and original failures distinguishable.
2. **Coverage:** compare the full expected problem × direction × policy × seed manifest with observed records. Every assigned cell must resolve to pass, fail, timeout, invalid output, execution error or unavailable reference; missing cells never vanish from denominators.
3. **Split isolation:** assert no underlying problem ID appears in both development and evaluation. Verify each query-pool and final-outcome test ID belongs to its declared partition. Test-family overlap receives an explicit audit rather than relying solely on different hashes.
4. **Access controls:** validate denied-network, denied-secret-file and resource-limit probes. Validate selector-input schemas against allowed fields. Verify query commitments precede corresponding results. This audits the declared interface; it must not be described as a proof against all side channels.
5. **Qualification:** recompute canonical/buggy outcomes, deterministic repeats and per-pair transition categories. Record every canonical failure and test incompatibility. Check the minimum informative-problem gate from the frozen protocol.
6. **Witness validity:** independently execute every disclosed witness and verify it truly passes. Recompute whether evidence was selected from the permitted pool and whether search/disclosure budgets are respected. A valid witness is not proof of global correctness.
7. **Policy integrity:** replay the decision logic from the actual ordered query trace. Validate candidate identity is identical across compared policies. Failed checks and abstentions must follow the frozen rule; no after-the-fact candidate or threshold substitution.
8. **Budget equivalence:** recompute unique execution counts, allocated test budget, screening costs, policy costs, cached/shared calls and model token counts. Record unequal realized costs even when call counts match.
9. **Outcomes:** recompute final retained/accepted program identity and reserved-suite outcomes. Independently derive all four correct/wrong transitions and each error state. Recompute preservation, recovery, selection coverage and source-problem denominators.
10. **Uncertainty and decision:** rerun the prospectively fixed paired cluster resampling with its seed, replicate count and eligible-ID set. Recompute primary superiority/noninferiority gates and minimum-information gates. Exploratory slices cannot override a failed primary gate.
11. **Report consistency:** compare every reported count/effect to per-cell results, retain failure/uncertainty receipts, and generate a machine-readable readiness state. Publish source hashes and permissible metadata without exposing private evaluation answers to policy inputs.

## Readiness states

- `ARTIFACT_OR_ORACLE_FAILURE`: source, sandbox, coverage, determinism or reference qualification failed; no efficacy conclusion.
- `FEASIBILITY_COMPLETE_ONLY`: the selective-evidence fixture works but no novel policy or useful generated repair baseline is established.
- `MINIMUM_INFORMATION_FAILURE`: execution completed but informative corruption/repair cohorts are too small for the frozen inference gate.
- `PRIMARY_HYPOTHESIS_NOT_SUPPORTED`: an informative, valid experiment failed its registered effect/tradeoff criteria. Preserve it as negative evidence.
- `PAPER_DEVELOPMENT_READY`: all required gates pass and the scoped contribution is supported. This does not mean acceptance is assured.

Every state must include completed/expected counts, hash verification, remaining limitations and whether any model inference remains authorized by the study protocol. Process exit zero is not an investment decision. Any failing gate should automatically produce a concrete closeout or diagnostic action, with no invented request for human adjudication.
