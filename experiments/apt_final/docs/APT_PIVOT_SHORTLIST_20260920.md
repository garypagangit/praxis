# Executable APT praxis opportunities after the negative detector studies

> Execution update, September 20: option 1's [registered baseline screen](../investigation_pilot/results/otrf_baseline_20260920/REPORT.md) is complete and closed. Ordinary GUID joins solved all 38 available answers and correctly abstained on 22 unavailable cases, leaving no correctness gap for a novel selector in this task. The ranking below is the original prospective shortlist, not three validated successes. The next candidate's [data-readiness audit](CTI_FALLBACK_READINESS_20260920.md) is complete; no CTI efficacy claim is made.

Research completed September 20, 2026. User accepts either direct detection or improvements to APT investigation and explanation.

## Decision

**Pivot the next development effort toward investigation, with behavior extraction as the alternative.** The completed normal-only MAGIC experiment passed zero of six cases. Another threshold, confidence checker, or local-model substitution has neither demonstrated a useful repair nor established a contribution. This does not rule out graph learning as a field.

There is **no newly validated positive experiment and no established novel algorithm** in this shortlist. The evidence supports small, executable tests of specific gaps. We should establish room to improve on simple methods before spending on training. A positive development result would justify further study; it would not alone establish a final praxis.

| Priority | Research question in everyday language | Data readiness | Contribution risk | Decision |
|---|---|---|---|---|
| 1 | Can we select the evidence that prevents an investigator from connecting the wrong events? | Public APT29 log archive downloaded, hash-checked and parsed | Medium-high: joins, compact IDs, verification and active queries already exist | First inexpensive failure audit; build a model comparison only if simpler methods leave room |
| 2 | Can a report reader identify what actually happened without guessing from the attacker name? | AnnoCTR public annotation file downloaded and parsed; report-level splits documented | Medium-high: masking, consistency training and counterfactual filtering already exist | Best alternative small supervised experiment |
| 3 | Can a graph model ignore harmless name changes while retaining meaningful behavior changes? | Rich public logs available; benign/attack labels and transformation rules need qualification | High: FLASH and MirGuard closely overlap | Reserve; do not start a GPU sweep |

These ratings are judgments from a bounded literature screen, not numerical probabilities of success. No candidate receives a novelty clearance based on an unsuccessful search.

## 1. Select evidence that distinguishes competing attack explanations

**Possible title:** *Question-Directed Evidence Selection for Reliable APT Reconstruction.*

**Problem:** Two PowerShell instances may have similar names and commands. If an investigator combines the download performed by one with the execution performed by the other, it can produce a convincing but wrong account of the incident.

**Proposed change:** Preserve complete identities outside the prompt. For each investigation question, track the competing event matches and select the smallest available set of parent, host, time and event references that separates them. Include compact identifiers in the evidence presented to the model. Report unresolved relationships when the available evidence cannot distinguish them. This cannot recover telemetry that was never recorded.

**Literature boundary:** [OCR-APT, CCS 2025](https://doi.org/10.1145/3719027.3765219) already builds LLM investigation narratives. Its pinned author code simplifies some paths/ports and omits source UUIDs from displayed descriptions. That is an inspected implementation property, not a measured error rate. [PROVSEEK](https://arxiv.org/abs/2508.21323) already performs evidence lookup and verification; [HunterAgent, May 2026 preprint](https://arxiv.org/abs/2605.29269) already combines deterministic identity constraints and uncertainty-aware search. [Improv, PRISM 2026](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf) repairs identity and ordering with live operating-system context. Stable IDs, abstention and set-cover-style evidence selection are not new inventions. The conditional contribution is a question-specific selection method with measured benefit at a fixed context budget, beyond these ordinary components.

**Actual data qualification:** We acquired the pinned [OTRF APT29 day-one host logs](https://github.com/OTRF/Security-Datasets/tree/d9d40ef123d2c87d5d3df28c96bcab4f0faccc87/datasets/compound/apt29), checked the archive against its Git blob hash, and parsed it without extraction or execution:

- 196,081 JSON records across four hosts; 143,884 Sysmon records.
- 447 process-creation records: 446 expose the identity fields directly; one stores them in its Sysmon Message. A validated fallback recovers all 447 process identities.
- 61 same-host program-name groups contain multiple process identities; 55 same-host/name/minute groups do so.
- Only **one** same-host program-name group contains multiple full paths. The evidence is mainly repeated process instances, not widespread different-directory collisions.
- Exact host/GUID joins link 329 child creation records to a recorded parent creation, with no parent-image disagreement. Another 118 parent creations are absent from this capture. Absence does not establish corruption or malicious activity.

These are **data-readiness and ambiguity counts**, not model errors, malicious links, or a positive algorithm result. This is one APT29 emulation recording, not four independent campaigns. Neither attack-stage labels nor complete attack-story gold answers were qualified.

**First experiment:** Freeze eligible question types, sampling and scoring before evaluating a method. Build 40-60 source-grounded relationship cases if enough exist, separating a random natural sample from a difficult ambiguity subset. Use exact event references for factual scoring. Compare names-only lookup, host/time joins, full ProcessGuid joins, compact-ID serialization, identity-aware graph retrieval and standard greedy evidence selection. Record answered coverage, wrong links, exact relationship recovery and total retrieved tokens/events.

**Gate:** If full-ID joins or compact-ID retrieval solve the task just as well, close the novel-method proposal. Only if a natural failure remains, compare the proposed selector with one fixed model at two frozen context budgets. Proposed development targets are at least 30% fewer wrong links at matched coverage with no more than two percentage points lost in correct recovery, or at least 20% less evidence at matched recovery/coverage against the strongest comparator. Freeze one primary target before scoring; disclose both outcomes. Synthetic identity loss is a separate stress test and cannot supply the primary success claim. A second capture is required for replication; related hosts are not independent campaign evidence.

**Industry benefit to test:** fewer incorrect investigative conclusions and less evidence to inspect. Analyst time savings require a subsequent human study; token reductions alone do not establish them.

## 2. Extract behavior without shortcuts from actor names

**Possible title:** *Actor-Invariant Extraction of Attack Techniques from Threat Reports.*

**Problem:** Seeing a familiar attacker name may lead a model to assign techniques associated with that attacker even when the report does not describe them.

**Proposed change:** Train a small text model on paired passages: the original and a version in which only the actor name is replaced by a neutral placeholder. Require consistent technique predictions while preserving the words that describe actual behavior. Evaluate untouched reports first; actor-name swaps are a diagnostic.

**Literature boundary:** The [USENIX Security 2025 TTP extraction study](https://www.usenix.org/conference/usenixsecurity25/presentation/buechel) supplies realistic evaluation and strong simpler baselines. [AnnoCTR, LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.103/) supplies annotated report evidence. Masking and consistency learning are established, and newer CTI work already uses counterfactual filtering and contrastive evidence objectives. The hypothesis is specifically whether actor-name dependence causes natural technique errors and whether consistency training improves on masking alone; the loss function itself is not a novelty claim. See the [CTI review](PIVOT_CTI_RESEARCH_20260920.md) for closest 2025-2026 overlaps and version distinctions.

**Data:** AnnoCTR has 400 reports overall, but the cybersecurity annotation layer covers **120**, split 70 train / 16 development / 34 test. The public development linking file was actually downloaded and parsed: 3,510,715 bytes and 1,542 records across entity categories. These are not 1,542 independent reports or exclusively technique labels. The final test remains reserved for the frozen comparison; published use of the benchmark limits claims of unseen-domain validation.

**First experiment:** Measure actor-sensitive errors with one baseline. Then compare ordinary training, name masking, paired augmentation without consistency, and the proposed consistency loss using the same encoder, data and training budget. Keep reports and related passages together. Use three seeds and document-level uncertainty estimates; preserve true behavioral entities such as PowerShell.

**Gate:** Require a natural baseline failure and improvement over masking-only. A proposed target is at least 10% fewer incorrect technique assignments at matched recall, with no more than one percentage point lost in macro-F1, and a document-level confidence interval supporting improvement. Thirty-four test reports may leave this inconclusive. Stop if the gain appears only on manufactured name swaps. Confirm on a second source before broad claims.

**Industry benefit to test:** fewer incorrect ATT&CK mappings entering an analyst's investigation. This is behavior extraction, not proof of the responsible attacker group.

## 3. Make harmless changes matter less than behavioral changes

**Possible title:** *Separating Naming Variation from Behavioral Change in APT Graph Detection.*

**Problem:** A detector should tolerate an irrelevant temporary-name change while still recognizing a meaningful change in actions or their dependencies.

**Proposed change:** Pair identity-consistent harmless renamings with separately defined behavior/order changes, and train a fixed encoder to distinguish the two. Do not label arbitrary reordered traces as real attacks.

**Literature boundary:** [FLASH, IEEE S&P 2024](https://mati607.github.io/assets/Flash.pdf) already abstracts execution-specific identifiers; [MirGuard, August 2025 preprint](https://arxiv.org/abs/2508.10639) already learns invariance to semantics-preserving graph views and sensitivity to adversarial inconsistencies. This is a crowded area. The paired objective needs a specifically demonstrated limitation of those controls; combining familiar losses is insufficient. The [algorithm review](PIVOT_ALGORITHM_RESEARCH_20260920.md) also screens 2026 temporal and compression approaches.

**Executable pilot:** Audit a frozen temporal baseline against canonicalization and augmentation-only controls before training a new objective. OTRF provides names and times, but benign periods and attack-event mappings still require qualification. The existing MAGIC arrays lack those fields and cannot answer this question.

**Gate:** Continue only if the base model changes alerts under a defensible harmless transformation and simple canonicalization does not solve it. Any positive claim must retain clean detection quality, reduce nuisance-induced changes, and preserve sensitivity to meaningful behavior on held-out real evidence. Highest build cost and overlap risk of the three; reserve rather than the first investment.

## Access findings and reproducibility

- [OTRF qualification receipt](../pivot_research/OTRF_APT29_DAY1_QUALIFICATION.json) and [replay script](../pivot_research/qualify_otrf.py) contain hashes and exact counts. An [independent audit](../pivot_research/INDEPENDENT_AUDIT.md) surfaced and verified the correction for the one Message-only process record. Raw logs are kept outside Git. The pinned repository LICENSE is MIT; its README has a conflicting GPL footer. Record both notices before any dataset redistribution; none is included here.
- The 2.94 GB OCR-APT archive was attempted but the connection failed. Metadata were verified; the full archive was not acquired or checksum-validated. The [receipt](../pivot_research/OCR_ACQUISITION.json) preserves the failed attempt. Do not wait for it to start the OTRF development audit.
- PIDSMaker documents rich ATLASv2 data, but its inspected download script requests a Google Drive access token. Full access was not established here; it is a secondary acquisition route, not a promised zero-setup download.
- AthenaBench's 100 attribution cases were parsed, but independent-source accounting and actor labels are a weaker basis for the first study. Dependence-aware attribution remains a reserve in the CTI memo.
- No new model was trained, no inference efficacy experiment ran, and no GPU was started for this research.

## Next action and completion boundary

The research and first data-qualification task are complete. **Next: run the small natural-error and strong-baseline screen for option 1.** If it leaves no meaningful room to improve, close it and move to option 2 rather than adding complexity to manufacture a win. Freeze the new experiment before outcome evaluation. Do not relabel the completed negative MAGIC studies.

For later claims of attack intent, storyline quality or analyst time saved, prepare a blinded review packet and a short rubric for an adviser/security analyst. Objective relationship questions can be scored from recorded IDs first; an AI-generated review is not a substitute for that later human evaluation. No adviser approval, independent human review or positive outcome is asserted.

Supporting reviews: [investigation](PIVOT_INVESTIGATION_RESEARCH_20260920.md), [CTI](PIVOT_CTI_RESEARCH_20260920.md), [graph algorithms](PIVOT_ALGORITHM_RESEARCH_20260920.md). Primary-source searches covered investigation verification, entity ambiguity, evidence selection, CTI extraction/name bias, attribution fusion, graph invariance, temporal modeling and compression through September 20, 2026. This is a focused screening review, not an exhaustive systematic review.
