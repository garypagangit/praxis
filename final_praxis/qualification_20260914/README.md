# Praxis development and new-experiment qualification

September 14, 2026. The new protocols were committed before GPU execution. This campaign qualifies reproducibility and measurement; it does not establish a new algorithm's efficacy or academic acceptance.

**Final research decision:** Prioritize CTI's completed cybersecurity evidence and keep 008 as the completed alternative. Both new qualification runs are complete: 009 preserves the checked calculations but provides no speedup on its small workload; 010 qualifies for a new, limited development study. Neither new track has established a novel, effective defense. See the [investment decision, next research question and stopping rules](INVESTMENT_DECISION.md).

| Workstream | Purpose | Evidence |
|---|---|---|
| CTI development | Navigate the completed CTI evidence, understand its limits and prepare for independent authorship. | [Internal guide, Word/PDF, evidence index and automated checks](https://github.com/garypagangit/praxis/tree/Final-Praxis-CTI-Development-20260914/final_praxis/cti_development_20260914) |
| Final-Praxis-009 | Check whether a bounded CPU staging modification preserves SOUP's actual model outputs, gradients and updates before considering a larger training experiment. | [Protocol and qualification package](https://github.com/garypagangit/praxis/tree/Final-Praxis-009-SOUP-Streaming/final_praxis/009_soup_streaming) |
| Final-Praxis-010 | Reproduce attack-detection and conformal-score implementations, separate an oracle baseline from deployable policies, and test current forecasting-model feasibility. | [Protocol and qualification package](https://github.com/garypagangit/praxis/tree/Final-Praxis-010-Attack-Aware-Forecasting/final_praxis/010_attack_aware_forecasting) |

The [three existing research drafts and evidence packages](https://github.com/garypagangit/praxis/tree/Final-Praxis-Top-Three-Papers-20260914/final_praxis/papers/20260914) remain available. CTI has the strongest completed cybersecurity evidence, 008 is the decision-manipulation alternative, and PX055 supports a narrower geometric measurement claim.

## What the experiments found

**009 / SOUP:** All 16 tiny-model comparisons preserved saved outputs, loss, gradients and final adapter weights exactly. Four altered-gradient controls were rejected. Prefetch nevertheless took **6.32% longer** than stock disk, using the frozen mean-of-block-medians statistic. The workload was warm-cache and all measured physical-read deltas were zero. This is no evidence of an 8B laptop training result, pretrained model quality, useful speedup or new mathematical contribution. [Results and retained failed attempt](https://github.com/garypagangit/praxis/blob/Final-Praxis-009-SOUP-Streaming/final_praxis/009_soup_streaming/RESULTS.md).

**010 / forecasting:** The original TimesFM 2.5 comparison completed all 20 scenarios for each of four policies. Every policy caught at least one point in every attack episode, but persistence and false alarms differed:

| Existing policy | Attack points flagged / 600 | Clean points flagged / 600 |
|---|---:|---:|
| Historical blend using known attack onset | 200 | 3 |
| Rolling context | 138 | 3 |
| Deployable alarm-only blend | 200 | 3 |
| Literal context freeze | 246 | 64 |

Freezing caught more attack points while producing substantially more clean alarms. Matching totals for the two blending policies do not prove equivalence. The historical implementation's known-onset advantage is explicitly separated from deployable policies.

Native TimesFM 3 ran on the A10G with a **0.12847-second median batch time and 2.464 GiB peak allocated GPU memory**. On one predetermined synthetic shift, only 3/256 shifted points alarmed and none did after the first 32 shifted points. This illustrates adaptation to the shift; it does not distinguish an attack from identical benign data. The public NAB/Chronos/W1ACAS example also ran successfully: at fixed alpha 0.01, **21/343 anomalous points and 39/2,681 normal points** alarmed. This is a reproducible development baseline with low pointwise sensitivity, not a strong detector or a held-out cyber result. [Complete 010 summary and raw evidence](https://github.com/garypagangit/praxis/blob/Final-Praxis-010-Attack-Aware-Forecasting/final_praxis/010_attack_aware_forecasting/completed_qualification/QUALIFICATION_SUMMARY.md).

## Review and reproducibility

CTI's handoff passed 154 consistency checks and six adversarial controls. 009 passed 107 owner artifact checks and 174 independent review checks. 010 passed 222 CPU checks, 22 runtime controls, 51 owner artifact checks and **20,026 independent saved-result checks**. These counts describe different check units; they are not independent scientific observations or measures of statistical confidence. Reviews verify saved assignments, arithmetic, source identity and specified operational criteria, not academic acceptance.

The independent [009 review](INDEPENDENT_009_REVIEW.json), [010 source review](INDEPENDENT_010_REVIEW.json), [010 result review](INDEPENDENT_010_RESULTS_REVIEW.json) and [runnable review code](review/README.md) preserve their scope. Individual repeat forecasts, quantile arrays and latency samples were not all saved. The independent auditor did not rerun model inference or the calibration optimizer. [The audit index](AUDIT_INDEX.json) binds sealed evidence to exact Git commits.

The source parameter mismatch (requested one epoch, effective two) was preserved and documented before inference. A later reviewer arithmetic correction preserves the worker's float32 operation order at the original tolerance. An **unpreregistered expansion of HAI timestamp/header inspection** occurred after model execution began; it is recorded as Q1-D1. It did not inspect additional sensor/label values or score HAI outcomes, but future chronological splits must cite that access and be frozen before further analysis. The complete amendments and data license notices accompany 010. Original frozen protocols and workers remain unchanged.

The [independent next-design novelty challenge](NEXT_DESIGN_NOVELTY_CHALLENGE.md) identifies close prior methods, required baselines and specific tests that could falsify the proposed contribution. A generic fixed-reference/adaptive-reference combination is insufficient novelty, and an admission-weight cap alone does not bound a neural forecast's sensitivity. A byte-integrity check does not establish method efficacy or novelty.

## Academic authorship status

The current [GW doctoral policy page](https://online.engineering.gwu.edu/policies-procedures-doctoral) links an [AI policy](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v) that restricts AI-written submitted Praxis work. These AI-assisted documents are internal research materials. No applicable written exception has been verified, and human editing alone does not establish compliance. Source identification and coding are permitted under the policy's conditions, including attribution and the author's ability to explain the code. This package preserves provenance and makes no submission or approval claim.

## Compute controls

One existing AWS g5.xlarge was authorized for at most two hours under a $25 combined reserve, with an external stop schedule installed before startup. The verified Linux instance rate was $1.006/hour. This reserve is not a billing invoice. No paid model API calls, additional GPU instances, held-out HAI scoring or full efficacy campaign are part of this qualification.

**Closed:** the selected host was confirmed stopped at **15:07:25 UTC on September 14, 2026**. From the start request to that observation, the approximate instance-compute charge is **$1.01**. This estimate excludes storage, transfer, taxes and unrelated resources; it is not a billing invoice. All six result archives were downloaded and their hashes verified before closeout. The committed-evidence index verifies **153 sealed files** across CTI, 009 and 010.

`cloud_ops.py` implements profile-based control and keeps account/resource identifiers and operational logs in a separate private settings directory. It accepts no embedded credentials. [Cloud closure](CLOUD_CLOSURE.json) records the observed stopped state, elapsed-window compute estimate, downloaded archive hashes and operational corrections. No further model job is running for this qualification.

The coordinator's [release inventory](RELEASE_MANIFEST.json) can be checked offline with `python verify_release.py`. The [audit-index builder](build_audit_index.py) additionally verifies the three child packages against their exact committed bytes when their worktrees are available. These checks make no model or cloud calls.
