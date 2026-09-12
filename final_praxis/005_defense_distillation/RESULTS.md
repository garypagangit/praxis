# Final Praxis 005: completed feasibility pilot

**Decision: deprioritize this generic defense-retention direction as a new publishable project.** The run completed real benign adaptation, but neither automated judge detected an increase in Extended Refusal's unsafe-response count. Its severe refusal of benign requests largely persisted. This pilot does not demonstrate a new defense or establish safety.

**Status: automated and provisional; the requested automated review workflow is complete.** The [completed automated review](automated_review_v2/completion/COMPLETION.md) records 26 consensus decisions and two harmfulness disagreements, which remain uncertain. The frozen V2 result stays 23/28; a separately labeled mechanical citation-normalization supplement recovered three decisions without changing any label or making calls. The historical human-adjudication criterion remains unmet, and original labels are preserved. All 800 evaluation responses and 1,280 judge assessments are present and numerically consistent. Results concern one seed, one Qwen2.5-3B family, same-size hard-label distillation, and a short LoRA update. They do not test model compression, cross-family transfer, or new abliteration resistance.

## Observed results

Each arm answered the identical 64 HarmBench, 64 safe XSTest and 32 held-out GSM8K prompts. HarmBench category exclusions and overlap filtering were fixed before inference. `KD` uses the same 64 accepted benign teacher solutions. Replay substitutes a safety example every fifth training example.

| Arm | Harmful-response labels: Qwen / MD, each /64 | Benign refusals /64 | Complete non-refusals /64 | Math correct /32 |
|---|---:|---:|---:|---:|
| Parent | 3 / 2 | 13 | 14 | 12 |
| Parent + KD | 3 / 2 | 13 | 24 | 22 |
| Extended Refusal (ER) | 1 / 0 | 60 | 1 | 20 |
| ER + KD | 1 / 0 | 59 | 2 | 23 |
| ER + KD/replay | 1 / 0 | 59 | 1 | 21 |

Refusal is a Qwen3Guard semantic label, not a keyword count. Complete non-refusal requires valid judges, nonempty output and no truncation; it does **not** establish that the answer is useful or correct. Math requires the frozen final-number extraction and a nontruncated output.

The salient usability signal is **60/64 benign refusals before ER adaptation versus 59/64 afterward** (93.8% to 92.2%). The parent was at 13/64 (20.3%). These are automated judgments on this selected panel, not general refusal rates. The additional blinded automated panel found no refusal-label differences across all 28 refusal assessments, including 12 selected benign responses. Its enriched small sample does not validate the overall refusal rate or replace human ground truth.

## Preregistered hypotheses and uncertainty

- **H1: no observed safety erosion.** ER had the same Qwen-unsafe item in all three ER conditions and no MD-unsafe items. ER+KD minus ER is 0 percentage points for both judges. The frozen paired bootstrap returns [0, 0] because the observed paired labels do not change; that degenerate empirical interval is not proof of population equivalence or safety. The parent change is also zero in aggregate, with Qwen's paired interval [-4.69, +4.69] points. The Qwen difference-in-changes is 0 [-4.69, +4.69]. The preregistered follow-up criterion (at least a 10-point ER increase with corroborating judges and manual adjudication) is not met.
- **H2: no demonstrated replay benefit.** Replay did not reduce either unsafe count. Relative to ER+KD, replay scored 21 rather than 23 correct math answers: -6.25 points, paired interval [-21.88, +9.38]. Its point estimate exceeds the allowed five-point utility loss, but uncertainty is large and does not establish a true loss. Benign refusal is unchanged in aggregate (59/64 each; paired change 0, interval [-4.69, +4.69]). Do not call replay a successful preservation intervention.
- **H3: unresolved construct check.** ER's low unsafe counts coexist with extensive benign refusal. Output length, truncation and evaluator style sensitivity limit the interpretation; the historical human check has not occurred. The requested automated replacement is now complete, with two harmfulness disagreements retained.

Math accuracy rose from 12 to 22/32 for the parent (+31.25 points, interval [+9.38, +53.13]) and from 20 to 23/32 for ER (+9.38 points, [-9.38, +28.13]). However, these are scores under the original256-token limit. Parent math truncations fell from 18 to 2 and ER truncations from 6 to 1. Adaptation to concise solutions can improve completion within the budget; the result does not isolate better mathematical reasoning from shorter answers. No token limits were changed after seeing outcomes.

## Incomplete output and evaluator limitations

| Arm | Harm truncations /64 | Benign truncations /64 | Math truncations /32 | Both-unsafe / either-unsafe-or-unresolved, harm /64 |
|---|---:|---:|---:|---:|
| Parent | 23 | 40 | 18 | 2 / 23 |
| Parent + KD | 19 | 29 | 2 | 1 / 19 |
| ER | 4 | 6 | 6 | 0 / 4 |
| ER + KD | 3 | 4 | 1 | 0 / 3 |
| ER + KD/replay | 2 | 6 | 2 | 0 / 2 |

There are no empty generations and no invalid judge outputs. Eight of 640 judged response pairs disagree on unsafe classification: seven HarmBench and one benign. All original judge labels remain intact. The disagreement/unresolved envelope is not a lower/upper bound on true harmfulness; its upper count is heavily driven by truncated generations. A judge can classify a truncated response syntactically validly without resolving the missing continuation.

The frozen blinded review queue contains all eight disagreements plus 20 agreement cases. Original human-label fields remain unfilled because no human performed the review. A separate automated workflow processed all 28, reaching qualified two-model agreement on 23 under the strict V2 endpoint, then 26 after separately recorded mechanical citation normalization; two harmfulness disagreements remain. The first reviewer-qualification pass failed and is preserved; a separately frozen revision passed fresh controls for two reviewers. Automated agreement is not independent human validation.

## Training and artifact validation

The teacher supplied the first 64 eligible solutions from 81 attempts in the frozen pool. The audit rechecked order, accepted numeric answers, nontruncation, training-length eligibility, data hash and zero exact normalized overlap with the 32 math test prompts. Numeric-answer verification does not certify every reasoning step.

All three training logs contain exactly 32 optimizer steps, one consistent attempt ID and finite recorded losses/gradient norms. Each trained 1,843,200 LoRA parameters using 128 examples. Parent+KD and ER+KD each saw 14,454 supervised tokens; replay saw 15,182 tokens and 25 replay examples, hence 103 benign examples. Replay matches update count, not token count or benign exposure.

Recorded adapter L2 changes are 1.762799 (parent+KD), 1.667166 (ER+KD), and 1.509174 (replay). The manifests match the frozen parent/ER revisions and identical teacher-data SHA256. Adapter configuration files match their recorded hashes. First/last-four-example losses match the first/last optimizer-log entries: parent 0.2734 to 0.1410; ER 0.1284 to 0.0858; replay 0.1284 to 0.1428. These first/last examples differ, so the pair is training evidence, not a learning-curve efficacy test.

The local independent audit verifies all five 160-record generation ID sets, source prompts and protocol identities; reparses all 640 outputs from each judge; recomputes every summary mean, paired-bootstrap interval and difference-in-changes interval; and checks all downloaded-file receipts. `audit.json` records these checks. The local download excludes final adapter weight binaries, so this audit does not independently certify all final serialized tensors. The earlier live audit verified the parent's serialized adapter; final ER/replay weight verification is a separate artifact check.

MD-Judge initially failed during tokenizer conversion because protobuf was missing. An environment-only pinned protobuf repair resumed MD scoring and reporting from the original output directory; the supervisor completed with exit code 0 at 2026-09-12 10:08:20 UTC. The reviewed repair wrapper verifies original source identity and hashes protected generations, checkpoints, teacher artifacts and Qwen judgments before/after. No retraining or changed evaluation protocol was requested. The orchestrator directly compared the before/after hash maps and verified `repair_complete.original_artifacts_unchanged=True`; its copied [repair completion receipt](completed_audit/repair_completion_receipt.json) records that verification and confirms the instance is stopped. This is metadata auditing plus repair hash verification, not an independent inspection of every final weight tensor. Do not conflate the supervisor's four-minute repair duration with total experiment time.

## Scope and investment

The [Extended Refusal paper v2](https://arxiv.org/html/2505.19056v2), dated October 7, 2025, already evaluates benign Dolly15k fine-tuning. The documented novelty amendment therefore classifies 005 as reproduction/feasibility; changing the benign dataset or adding ordinary replay does not establish novelty.

Retain the reproducible training/evaluation harness and this negative retention gate. The automated audit is complete; retain its uncertainty and avoid stronger semantic claims. No follow-up manual task is assigned by this workflow. A separate compression or cross-family study would need an independently motivated mechanism, a fresh closest-prior review and a new preregistration. The current evidence does not justify more spending on the generic retention hypothesis.

Protocol ID: `2e3749bcc7fa4f5d1bbd9b5758608ecb5827c2546fc8ebc29fef991cb035b938`. Original source bundle: `37fdd3f154a78017f9eb313385e25379c36affde`. Private run: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp005-20260912-37fdd3f/`. Raw prompts/responses and review keys are omitted from this report.
