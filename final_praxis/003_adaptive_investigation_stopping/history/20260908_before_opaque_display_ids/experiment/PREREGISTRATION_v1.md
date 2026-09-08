# Final Praxis 003 preregistration v1

Frozen prospectively on 2026-09-08, before any non-fixture model response in this experiment. The 2026-09-08 methods document's thresholds are preserved; the associated dated amendment fills unspecified operational details. This protocol makes no use of historical PX-057 case outcomes, thresholds optimized against historical cases, or historical performance claims.

## Question, corpus and unit

Does mechanically reviewed answer-stability stopping preserve utility and prevent correct-to-wrong degradation with lower investigation cost than fixed investigation lengths in a staged security authorization task? The failure model is either premature classification before decisive evidence, or degradation after correct classification while additional weak evidence is added.

The discovery unit is one case. There are exactly 400 generated inert cases, 50 each in identity, mail, endpoint, egress, cloud, service, archive and remote-access contexts, balanced 25 benign and 25 malicious per family. Each has eight cumulative evidence stages. A signed record presents actor, asset and inclusive time constraints; matching all three defines benign, and one mismatch defines malicious for an actually executed action. Labels are computed from a private structured record and checked before execution. Labels and that private record are never model inputs. The source is the checked-in generator, not an external or expert-labelled incident corpus.

Authoritative evidence appears at round 2, 4, 6 or 8 by frozen schedule, balanced across labels in each pair. Other evidence consists of weak alerts, provisional approvals and unverified context. Actual raw texts, order, IDs, case order and source code are hash-frozen in the manifest. The generated evidence is scientific input; generated answer trajectories are exclusively fixtures.

## Model and collection

One discovery model: `Qwen/Qwen2.5-7B-Instruct`, exact revision `a09a35458c702b33eeacc393d103063234e8bc28`; BF16, no quantization; greedy temperature 0, seed 20260908, max 64 new tokens. Sixteen independent cases may run concurrently; each case's rounds run sequentially. The prompt gives only cumulative evidence and previous normalized dispositions, requiring one JSON disposition: benign, malicious, or abstain. All eight rounds are collected for every case, so policy comparisons share the same trace and do not change evidence exposure. This estimates counterfactual policy cost on full collection; it is not a claim that the collection itself saved compute.

No pilot scientific sample is used to tune policies. Fixture feasibility is completed first. Model errors, malformed JSON, unsupported values and refusals normalize to abstain, count as incorrect utility, and are never excluded. There are zero scientific exclusions. Missing rounds prevent completion. Maximum two infrastructure retries, preserving completed raw records and original scientific inputs. No new model or changed scientific prompt may silently replace the frozen one.

Before discovery, two separately generated and hash-frozen infrastructure cases in namespace `fp003-infrastructure-pilot-*` exercise all eight real-inference rounds, serialization, analysis and independent verification. They are absent from the 400-case discovery manifest and never count toward scientific denominators. The pilot gate is complete 16-round records, immutable model/runtime identity, parse/abstain handling, and successful independent replay; no correctness or promotion gate is required and no scientific threshold, model prompt, corpus or policy is tuned from pilot answers. Scientific analysis labels this mode INFRASTRUCTURE_PILOT_ONLY. Allowed infrastructure corrections are documented before rerun and preserve all raw pilot records.

## Arms and mechanical review

A0 stops at round 2. A1 stops at round 8. A2 stops after two consecutive identical non-abstaining dispositions, earliest round 2, otherwise round 8. Optional A3 is excluded because no independently calibrated confidence proxy is used.

A4 uses A2 with a mechanical review gate at eligible rounds 2–8. Trigger REVIEW when: protected-high-impact case; current round below the frozen minimum evidence-completeness round; latest disposition differs from prior disposition; or current disposition abstains. REVIEW continues to the next evidence stage, never supplies a human or oracle answer. At round 8, unresolved REVIEW produces terminal abstention with zero utility. No trigger means STOP for stability or final round, otherwise CONTINUE. Prior STOP is absorbing for policy evaluation; the collector still obtains later counterfactual outcomes.

Exactly 40 cases are protected and a disjoint 40 have minimum-completeness round 4; all others use round 2. These metadata are public policy inputs fixed independently of model outputs. Review rate counts every case with any REVIEW before its policy endpoint. No exception raises the frozen 20% review ceiling for protected cases. Terminal abstention rate is separately reported. A4 can fail because mandatory review reduces utility; that is a legitimate outcome, not a reason to award hypothetical human-corrected answers.

## Metrics, hypotheses and thresholds

H1: A4 non-inferior correctness against both frozen non-adaptive baselines A0/A1, preserving the strongest-baseline requirement. Utility is exact label correctness (abstain=0). The lower one-sided 97.5% paired bootstrap bound must be at least -0.02 for each comparison, providing a conservative two-comparison protection.

H2: both mean round saving and token saving must be at least 20% versus A1. Round saving is 1 minus mean selected rounds / 8. Token saving is 1 minus total prompt-plus-completion tokens through the selected rounds / A1 total; it includes all model calls used by that policy. Review continuation is charged normally. No unperformed human-review cost is estimated. Paired case bootstrap percentile 95% intervals are reported for both savings, with 10,000 replicates and seed 20260908.

H3: at least 20 adjacent correct-to-wrong transitions must occur across the eight-round traces. The prevention denominator is cases with any such transition. A case is prevented when its selected disposition is correct and at least one later frozen round is incorrect. Prevention must be at least 25%. Event and affected-case counts are reported separately, with exact two-sided 95% Clopper-Pearson prevention interval.

H4: harm is an incorrect selected endpoint for which any later frozen round would be correct, including early abstentions. The denominator is all 400 cases; no harm/refusal/review case is dropped. Observed harm must be <=2% and its one-sided 95% Clopper-Pearson upper bound <=4%. At n=400, the maximum allowed observed harm count is eight; the confidence-bound check is additionally applied. Zero harm gives an upper bound below 1%, so a passing safety gate is feasible. This is benchmark uncertainty under case sampling; template dependence limits population interpretation.

H5: results must come from these security-framed staged authorization cases using actual model inference, not math outcomes or artificial traces. Domain relevance is limited to this generated classification task; the experiment cannot establish SOC deployment safety or broad real-incident performance.

All above, review rate <=20%, hash checks and independent audit are mandatory for Bounded Positive. No Strong Bounded Positive is assigned from one model and generated corpus. Fewer than 20 degradation events yields Negative/insufficient phenomenon. A2/A4 agreement within 1 percentage point accuracy, 5 percentage points in both cost-saving measures and identical harm-gate status means no meaningful safety-layer benefit; if otherwise all promotion gates pass, classify Mixed, otherwise Negative. Any missing sample, altered freeze, unrecorded scientific substitution, missed required review or unverifiable raw outputs is Protocol Invalid. Infrastructure failure before a complete evaluable sample is Blocked until corrected within the frozen retry allowance.

## Verification and publication

Every raw row stores experiment/protocol/model identity, case and round, source evidence IDs, raw response, normalized disposition, hidden-label correctness, measured tokens, timestamp, request ID, prompt hash and policy-prefix status. Outputs are append-only; completed runs cannot be overwritten. A separate verifier recomputes normalization, decisions, utility, review, harm and prevention from raw records without importing the production policies or evaluator. It verifies unique identities, frozen files, exact 400-case/3200-round coverage and raw hashes before issuing a final determination.

Results, including negative and mixed findings, are preserved with a bounded claim. Replication on another frozen model or an external labelled incident corpus is future work and cannot retroactively alter this discovery result.
