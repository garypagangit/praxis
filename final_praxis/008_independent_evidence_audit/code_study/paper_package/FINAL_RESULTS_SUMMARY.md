# Final Praxis results and writing decision

Scientific execution is complete across the numbered portfolio. **Invest the next effort in writing 008 as a bounded empirical study of selective disclosure of executed tests.** Its positive finding is specific to one model/configuration on native code pairs. The proposed hybrid defense did not succeed, and the disclosure effect was not observed in the smaller generated-corruption cohort. **Ready for bounded Praxis paper development:** the amended full audit passed with the disclosed numerical erratum, automated readiness passed 15/15, and both AWS hosts are stopped.

The concrete starting document is [MANUSCRIPT_STARTER.md](MANUSCRIPT_STARTER.md), titled **Selective Disclosure of Executed Tests in Language-Model Code Revision**. It includes an abstract, research questions, observed hypothesis outcomes and a chapter outline mapped to evidence. [Detailed results and investment decision](RESULTS_AND_INVESTMENT.md), [methods and writing plan](METHODS_AND_WRITING_PLAN.md), [claim boundaries](CLAIM_BOUNDARIES.md).

## What 008 established

HumanEvalFix/HumanEvalPlus provided a public, executable base. Qualification admitted 135 native source problems, including 101 heldout problems with paired harmful and useful revisions. Actors saw supplied code and authenticated execution records; reserved tests supplied the outcome labels. The supplier acquired 16 observations and disclosed at most two. This is finite-suite correctness on a public benchmark, with possible pretraining exposure, rather than proof of program correctness or unseen-task generalization.

| Heldout result | Qwen schema-constrained reviewer | Devstral reviewer |
|---|---|---|
| H1: harmful acceptance, selected / uniform disclosure | **12/101 / 4/101**; +7.92 percentage points; 95% task-bootstrap CI [2.97,13.86]; Holm-four p=0.015625 | 3/101 / 1/101; +1.98 points; Holm-four p=0.75; unsupported |
| H2: harmful acceptance after enforcement, uniform / hybrid verification | 3/101 / 4/101; no hybrid benefit | 0/101 / 0/101; no hybrid benefit |
| Generated harmful revisions: selected / uniform disclosure | 4/34 / 4/34; no observed contrast | 1/34 / 1/34; no observed contrast |

Both Qwen H1 arms have **101/101 valid decisions**, so the 12-versus-four contrast is unchanged when restricted to valid calls. A post-result diagnostic found that seven of the eight selected-only flips omitted a failure displayed under uniform disclosure; two selected messages contained no tests. None was an ordering-only change. H1 therefore concerns the entire passing-only selective-disclosure policy, including omission, rather than isolating a geometric test-selection heuristic or persuasion by passing examples. [Diagnostic receipt](../postrun_review/completed_extension_v2/H1_MECHANISM_DIAGNOSTIC.json).

Both full hybrid-policy recommendation gates failed. The 34 harmful generated revisions are explicit model-proposed corruptions, below the 40-task recommendation threshold; they are not naturally occurring model errors. The native positive effect was not observed in this secondary cohort. V1 Qwen's heldout calls were gated and never run, so V2 cannot establish that schema formatting caused vulnerability. Devstral's designated V1 observations were reused explicitly; its updated multiplicity adjustment is not a second independent replication.

## Disposition of all options

All eight dedicated numbered Git branches exist. The [portfolio evidence audit](PORTFOLIO_STATUS_DRAFT.md) provides exact reports, branch names and measurement limits.

| Option | Completed result | Investment decision |
|---|---|---|
| **001 — Outcome-state verification** | 400 cases; learned judge accepted 7/200 invalid but only 19/200 valid states; 205/400 malformed responses. Registered gates failed. | Preserve the completed report as a bounded negative study. |
| **002 — Cascade containment** | Invalid actions 10/60 to zero, but clean completion 51/60 remained below the 90% floor. Nine invalid injected cases also failed clean. | Preserve the negative utility/containment result; no new-defense success claim. |
| **003 — Adaptive stopping** | Accuracy 138/400 versus fixed-long 217/400 despite 23.34% fewer rounds. Harm and review requirements failed. | Close this policy; retain its report and measured tradeoff. |
| **004 — Specialist revision** | Four qualified issues; zero successful initial repairs and zero valid final candidates in the follow-up. | Close the scaffold. Correct-answer preservation was not measurable. |
| **005 — Defense distillation** | Three short adaptations; harmful labels unchanged and no replay advantage. Automated review completed with retained semantic uncertainty. | Close the generic retention hypothesis; retain a feasibility appendix. |
| **006 — Cognitive expert containment** | Useful logic-ablation contribution, but capability/format gates failed; no qualified containment mechanism. | Preserve prerequisite findings; close the current configuration. |
| **007 — Overthinking/selective revision** | Both model evaluations failed the proposed gate's registered recovery comparisons. | Close the gate and retain the negative result. |
| **008 — Independent evidence** | AutoDC audit completed but its ambiguous base was held. Code-study Qwen H1 supported; hybrid H2 failed; generated H1 contrast absent. | **Primary writing focus; evidence closure complete.** A bounded empirical contribution, not a successful new defense. |
| **Older FalseCite-Code / PX-004** | On the reused strict panel, Coder-7B accepted 6/7 fabricated claims versus 0/7 with metadata/verifier, with substantial scope and exposure limits. | Preserve the separate bounded positive and existing local manuscript. No external publication was verified. |

## Reproducibility, closure and next writing work

V2 accounts for all **9,456 review assignments**: 7,512 completed eligible calls and 1,944 ineligible assignments. Original and V2 public packages reproduce the complete frozen statistical payloads, including 5,000-draw bootstrap results. This is deterministic reproduction of the same implementation; independent arithmetic and artifact review are separate. [Reproduction guide](REPRODUCTION_GUIDE.md), [V1 receipt](reproduced_original_v1.json), [V2 receipt](reproduced_schema_extension_v2.json).

The original full artifact audit passed **918,245/918,245 checks**. The initial V2 audit exposed a secondary offline numerical-zero flag discrepancy: an exact-zero effect was represented as approximately 4.08e-19 and flagged directional benefit. The [disclosed erratum](../postrun_review/roundoff_amendment/NUMERICAL_ERRATUM.json) records no directional benefit; primary hypotheses and the overall recommendation are unchanged. Frozen sources, original results and the initial failed audit remain preserved. The amended full audit passed **1,099,300/1,099,300 checks**, retaining the numerical correction as an explicit warning. [Full V2 audit](../postrun_review/completed_extension_v2/ARTIFACT_AUDIT.json), [readiness review](PAPER_READINESS.md), [cloud closeout](../execution_receipts/CLOUD_CLOSEOUT.json).

Both campaign EC2 hosts were verified **stopped** at 2026-09-14T02:30:26.985135+00:00. The API estimate is **$11.8626**; host compute through verified stop is at most **$2.2115** by the recorded rate/time estimate. The known API-plus-compute subtotal is **$14.0742**; including the disclosed $5 incidental storage/transfer allowance gives **$19.0742**, within the $100 envelope. These are incremental usage/rate estimates, not an invoice or total account spending. Automated readiness passed **15/15**. [Full V2 audit](../postrun_review/completed_extension_v2/ARTIFACT_AUDIT.json), [readiness review](PAPER_READINESS.md), [cloud closeout](../execution_receipts/CLOUD_CLOSEOUT.json).

Develop the starter's methods and results chapters around the positive native disclosure effect, model disagreement, failed intervention and transfer limits. Compare the precise empirical contribution with the [closest-prior literature](../literature/CLOSE_PRIOR_MATRIX.md). Prior work already covers selective evidence and test-based patch verification; neither significance nor a working veto alone establishes novelty. The next investment is careful writing from the closed evidence package, not additional spending to scale the unsuccessful hybrid policy.
