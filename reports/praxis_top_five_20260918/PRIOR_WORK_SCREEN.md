# Prior-work screen for the positive Praxis shortlist

Reviewed September 18, 2026. This is a targeted primary-source overlap check, not a systematic review, novelty certification, or academic approval. Existing positive observations, successful interventions, and promising follow-up ideas are different categories. A failed external test remains part of the evidence even when an earlier pilot was positive.

## Recommendation from the literature check

The portfolio does not currently establish five distinct, novel, effective solutions. The most credible directions retain their measured results and narrow their claims. Selective test disclosure and CTI applicability support bounded empirical studies. Software-artifact verification offers a practical intervention with substantial prior art and a small holdout. Model/dataset registry checking is an early extension of that same family. Refusal geometry and MoE committees are replication reserves. Source-locked citation extraction needs stronger controls before promotion.

Ranking should combine this assessment with the independent evidence audit in this directory. The order below is thematic; it does not override the final portfolio ranking.

## 1. CTI: deciding whether a security fact applies to the question

**Local evidence.** The completed CTIBench paper documents benefits from compatible evidence and substantial harm from mismatched evidence. Its source-known condition receives a published technique pointer. Query-only retrieval uses the question and all displayed choices. The September 18 external SecEval test did not confirm this checker as an accuracy improvement: Llama 86.53% to 86.21%; Qwen 87.09% to 87.25%. The mean change was -0.08 percentage points, with a 95% interval of [-0.52, +0.36]. The original positive result and the external failure must both appear in any proposal.

**Closest overlap.** [CoRM-RAG, May 2026, Sections 3.3–3.4](https://arxiv.org/html/2605.01302v1) already trains an evidence critic to predict robustness utility and gates evidence with an abstention mechanism. Predicting whether facts help is therefore not a new general method. [Ahlert, September 2026, Sections II-D and IV](https://arxiv.org/html/2609.08790v1) already combines CTI evidence retrieval with environment grounding; its discussion identifies incomplete inventories and a fallback to unfiltered leads as limitations. These are different tasks from multiple-choice accuracy, so their published scores cannot be imported as direct baselines.

**Defensible candidate gap, not an established contribution.** Test whether facts support the particular answer change and apply to the same asset, version, time, and required conditions. Evaluate missing information separately from contradicted information. Compare against a strong published evidence critic and simple rules with the same evidence access, while measuring useful corrections, induced errors, and cost. The research question is whether this distinction improves a security workflow under distribution shift; “a better checker” by itself does not define novelty.

**Next decision.** Finish the prepared independent question/evidence review, then preregister a specific revised comparison on untouched questions. SecEval is now development evidence for a revised method. The bounded empirical CTI paper can still be reviewed on its own merits without representing the new checker as successful.

Local sources: `C:/w/px_final_20260917/final_praxis/final_three_20260917/01_cti/PAPER.md`; `reports/cti_external_validation_20260918/DECISION.md`; `reports/cti_checker_gap_review_20260918/RESEARCH_GAP.md`.

## 2. Code review: real tests can be selectively shown

**Local evidence.** On 101 heldout source problems, Qwen accepted harmful revisions in 12 selected-disclosure cases versus 4 uniform-disclosure cases: +7.92 percentage points, 95% task-bootstrap interval [2.97, 13.86], Holm-adjusted p=.015625. The other reviewer did not establish the same effect. The hybrid independent-test policy failed its recommendation gates, and the generated harmful-revision cohort showed no disclosure contrast.

**Closest overlap.** [Preregistered Belief Revision Contracts, April 2026, Section 9.2](https://arxiv.org/html/2604.15558v1#S9.SS2) explicitly discusses steering evidence acquisition, cherry-picking, withholding, and query-policy compliance. The threat and the idea of authenticating tool inputs are already known. The local study does not instantiate the complete PBRC enforcement system, so it cannot refute that system's guarantees.

**Defensible candidate gap.** A controlled implementation showing how selective disclosure affects code replacement decisions, with fixed acquisition, both harmful changes and useful repairs, and heldout executable outcomes. Further work could separate omission, number of records, and selection among passing tests, which the present compound intervention does not isolate. Any new defense must beat equal-budget independent testing while retaining valid repairs.

**Priority caution.** This is a positive vulnerability measurement, not a positive new defense. It is one of the clearest bounded empirical contributions in this shortlist.

Local source: `C:/w/px_final_20260917/final_praxis/final_three_20260917/02_008/PAPER.md`.

## 3. Software citations: verify that the claimed package version or repository exists

**Local evidence.** FalseCite-Code's deterministic verifier reduced fabricated-citation trust to zero on the tested locked benchmark. The benchmark has 80 claims and only 15 strict-holdout claims; the audit and generation measurements are separate endpoints. These results establish narrow metadata checking, not safe installation or absence of malicious code.

**Closest overlap.** [Spracklen et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/spracklen) already measures package hallucinations extensively and tests mitigation. [Djire et al., August 23, 2026, Sections 4–5](https://arxiv.org/html/2608.22652v1) compares seven inference-time defenses across four languages, adversarial fabricated-name prompts, and recommendation usefulness. It also shows that registry-only validation can misclassify legitimate standard-library imports. Registry checking, external grounding, and fabricated dependency prompts are established territory.

**Defensible candidate gap.** A deployment evaluation of precise artifact claims spanning package name, version, repository, and tag, with time-stamped ground truth and correct treatment of inaccessible or indeterminate records. Demonstrate reduced invalid actions while preserving valid task completion against a direct API checker and strong existing defenses. The same API used to create labels should not be the sole independent validation of the checker.

**Priority caution.** The small current result is useful engineering evidence. A larger heldout task and a specific failure mode beyond straightforward lookup are needed for a stronger original contribution. Existing metadata does not prove an artifact is trustworthy, compatible, or benign.

Local source: `reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md`.

## 4. Model and dataset identifiers: decide what to load when registry evidence is incomplete

**Local evidence.** The live pilot produced 378 outputs from three code models. Among 33 verified physical-model registry identifier occurrences, two were missing. There were 116 ambiguous verifications and five null-control extraction events. Zero known-missing escapes is a pilot observation, not a complete false-positive or security guarantee.

**Closest overlap.** Package-hallucination work already covers the generic lookup pattern. [Yuan et al., July 2026](https://arxiv.org/abs/2607.12340) extends hallucinated identifiers to agent skills and finds a security/usefulness tradeoff, so “extend from packages to another registry” is weak as a novelty claim. [Stalnaker et al., revised September 2025](https://arxiv.org/abs/2502.04484v2) studies model/dataset documentation and supply-chain validation on Hugging Face.

**Concrete unresolved operational distinction.** An unavailable identifier is not necessarily nonexistent. [Hugging Face's official error documentation](https://huggingface.co/docs/huggingface_hub/package_reference/utilities#http-errors) distinguishes missing repository, private access, gated access, wrong revision, missing file, and network/lookup failure; RepositoryNotFoundError can conceal more than one of these states. A useful experiment would test whether a checker selects the correct next action across these states while retaining legitimate loading and task completion. Those distinctions are existing API semantics; the contribution would be measured operational benefit, not inventing the states.

**Priority caution.** This is an early pilot and a close relative of software-artifact verification. Do not sell them as two independent methodological breakthroughs. Resolve extraction errors and independently adjudicate ambiguous cases before estimating prevalence or protection.

Local source: `reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/PX056_GATE2A_DETERMINATION_20260721.md`.

## Replication reserves and candidates not promoted

### Refusal geometry under quantization

The local study retains a positive bounded geometry result across nine cells but has a nonpositive restoration proxy and no retained decoded responses for independent semantic re-scoring. [Chhabra and Khalili, 2025](https://arxiv.org/html/2504.04215v1) already studies refusal directions under compression and an intervention to restore refusal. [Quality Is Not a Safety Proxy Under Quantization, June 2026](https://arxiv.org/html/2606.10154v1) directly overlaps the distinction between stable geometry and behavioral safety. Keep the completed result as a replication/measurement reserve. A fifth portfolio position must be labeled conditional, not a validated new safety method. Local disposition: `reports/praxis_top_three_decision_20260915/04_PX055_DISPOSITION.md`.

### MoE standing committees

The three-model local routing audit is a positive observation. However, [Wang et al., January 2026, revised May 2026](https://arxiv.org/abs/2601.03425) already introduces COMMITTEEAUDIT and the domain-invariant standing-committee framing across models. Replicating overlap under new prompt styles can be useful, but does not establish first discovery, causal specialization, or a performance improvement. Local source: `reports/praxis_final_positive_reports_20260701/PX005_FINAL_REPORT_MOE_STANDING_COMMITTEE.md`.

### Source-locked research citations

The local HalluHard slice reported 90.4% verifier accuracy over 500 constructed pairs and 80.8% supported-claim pass rate. This is source-known, extractive generation. [HalluHard](https://arxiv.org/abs/2602.01031) evaluates a substantially broader multi-turn problem. [CAGE, July 2026](https://arxiv.org/html/2607.24236v1) already makes claim-to-source assignments explicit before generation. [The Attribution-Compression Frontier, September 13, 2026](https://arxiv.org/abs/2609.14245) further shows why citation appearance and support from original source spans should be measured separately; its results remain evaluator-dependent.

The concurrent independent portfolio audit found that a simple metadata-only diagnostic separates all 500 local constructed pairs, exceeding the original verifier. This is a post-hoc diagnostic, not a new confirmatory result, but it prevents promoting the current slice as evidence of a superior semantic checker. Use independently reviewed same-source unsupported claims and stronger simple baselines before reconsidering. Local source: `reports/praxis_final_positive_reports_20260701/PX011_FINAL_REPORT_HALLUHARD_SOURCE_LOCKED.md`; see the companion portfolio audit for diagnostic details.

### Earlier positive pilots superseded by larger failed gates

The evidence audit found that full adaptive-stopping, independent streaming-intrusion adaptation, and forecasting-corruption follow-ups failed their primary criteria. Earlier positive pilot headlines should not displace these later results. This literature screen did not spend further search effort trying to rehabilitate those failed current methods.

## Screen boundary

Primary research pages and official API documentation above were opened on September 18, 2026. Search targeted the exact shortlist claims and recent direct overlaps. Several sources are preprints; being on arXiv is not independent validation. No source's reported efficacy was independently reproduced in this screen. Absence of an exact match in this limited search does not establish novelty. The specific proposed gaps are reasoned interpretations that require a successful, controlled experiment and advisor assessment.
