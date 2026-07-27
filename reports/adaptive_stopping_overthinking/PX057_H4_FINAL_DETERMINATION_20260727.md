# PX-057 H4 Final Praxis Determination

Date: 2026-07-27

Experiment: Adaptive Stopping to Prevent LLM Overthinking — three-cell per-cell certification matrix

Final status: **VALID NEGATIVE**

Portfolio classification: **bounded Gate 2 discovery positive; H4 certification negative**

## Decision

The preregistered H4 experiment was completed through its correct terminal gate. The independent adjudicator reproduced the evidence and returned `VALID_NEGATIVE` with `valid=true`.

All three 500-trace calibration cells stopped at the first fixed-sequence policy. None produced a certified prefix, so all three terminal locks contain `selected_policy: null`. Under the frozen protocol, this fails H4a and forbids held-out generation. H4b through H4d and the manual audit were therefore not run. H4e is `INCONCLUSIVE` because no policy was selected.

This is a scientific negative result, not an infrastructure failure. The experiment generated and protected 1,500 calibration traces and 12,000 model generations before reaching the registered stopping rule.

## Was this the correct experiment?

Yes, for the claim being tested. Gate 2 had shown a strong bounded result on one 200-question Qwen/GSM8K sample. H4 asked the harder question: can a policy be selected while controlling per-question early-stop harm at 2% across a frozen three-cell model/domain family?

The design used disjoint calibration and holdout splits, an outcome-independent 30-policy sequence, exact finite-population tests, a three-cell family error budget, immutable terminal locks, and an untouched holdout. That is the appropriate experiment for a three-cell certification claim. Each cell calibrated its own policy; H4 was not a zero-shot transfer test of one policy.

The result also exposed two mechanism-design weaknesses: the registered confidence thresholds were below every observed confidence value, and blank/truncated answers were allowed to satisfy the stability rule. Those weaknesses limit mechanism interpretation, but they do not invalidate the registered negative result.

## Registered calibration result

The first policy in every cell was `m4-k2-tau0p20`: do not stop before round 4, then stop after two identical normalized answers when both confidence values are at least 0.20.

| Cell | Frozen model and corpus | Finite population | Calibration | Harms | Harm rate | Null boundary | Stored primary p-value | Certified prefix | H4a |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| C1 | Llama-3.1-8B-Instruct / GSM8K | 1,119 | 500 | 40 | 8.0% | 23 total population harms | 0.9999999999996976 | 0/30 | Fail |
| C2 | Qwen2.5-7B-Instruct / ARC-Challenge | 1,172 | 500 | 35 | 7.0% | 24 total population harms | 0.9999999999991549 | 0/30 | Fail |
| C3 | Llama-3.1-8B-Instruct / ARC-Challenge | 1,172 | 500 | 28 | 5.6% | 24 total population harms | 0.9999999999991549 | 0/30 | Fail |

Certification required a p-value at most `1/60 = 0.0166667`. Each calibration sample contained more observed harms than the null-boundary population total—the smallest total under `H0`. The exact lower-tail probability is therefore 1; the stored values just below 1 reflect numerical log-gamma rounding.

Because fixed-sequence testing stops at the first failure, only policy 1 was reached. The other 29 stored policy rows are diagnostics. They were not formally reached, certified, or eligible for selection.

## Utility improved, but safety did not certify

The negative result is not that early stopping had no utility. Policy 1 improved aggregate accuracy, saved compute, and prevented many overthinking events in every cell. It simultaneously harmed too many individual questions to meet the 2% bound.

| Cell | Fixed-long accuracy | Policy-1 stopped accuracy | Accuracy change | Mean token saving | Overthinking prevented | Early-stop harms |
|---|---:|---:|---:|---:|---:|---:|
| C1 | 28.2% | 31.2% | +3.0 points | 42.45% | 55/111 (49.55%) | 40/500 |
| C2 | 76.6% | 80.0% | +3.4 points | 50.85% | 52/73 (71.23%) | 35/500 |
| C3 | 34.6% | 40.8% | +6.2 points | 43.30% | 59/127 (46.46%) | 28/500 |

This distinction is the central Praxis finding: aggregate accuracy and compute gains can coexist with an unacceptable tail of correct-to-wrong reversals. The registered harm gate correctly rejected policies that would look attractive under average utility alone.

## Held-out disposition

No held-out model response was generated. That is the required outcome after three empty H4a prefixes.

For each registered holdout cell, the protected transport verifier confirmed:

- no SageMaker job with the deterministic holdout job name;
- no source, result, or model S3 object-version history under the registered prefixes;
- no local holdout output directory or cloud manifest;
- no manual-audit packet, joined audit, or holdout determination.

The independent adjudicator recorded `not_run_without_certified_policy=true` for all three cells and confirmed no local downstream evidence. A separate read-only transport check confirmed that all deterministic SageMaker job names and registered S3 prefixes remain unused. Running a holdout now would violate the experiment rather than add evidence.

## Exploratory failure diagnosis

The following diagnostics were computed after the confirmatory H4a result. They explain the observed behavior but are not new preregistered tests.

### 1. The confidence grid was inert

All 12,000 recorded confidence values exceeded the largest registered threshold, 0.20.

| Cell | Minimum observed confidence | Values at or below 0.20 |
|---|---:|---:|
| C1 | 0.585984 | 0/4,000 |
| C2 | 0.491244 | 0/4,000 |
| C3 | 0.487014 | 0/4,000 |

Consequently, the five `tau` settings behaved identically for each `(m,k)` pair. The nominal 30-policy grid collapsed to six effective stopping behaviors. H4 therefore did not provide meaningful evidence that this confidence proxy improved stopping.

### 2. Blank, token-capped answers drove most harms

The frozen extractor maps a failed extraction to the empty string, and the frozen stability rule permits two empty answers to count as identical.

| Cell | Blank extracted rounds | Blank rate | Blanks at 256-token cap | First-policy harms with blank selected answer |
|---|---:|---:|---:|---:|
| C1 | 1,875/4,000 | 46.88% | 1,874/1,875 | 33/40 (82.5%) |
| C2 | 605/4,000 | 15.13% | 587/605 | 22/35 (62.9%) |
| C3 | 1,956/4,000 | 48.90% | 1,955/1,956 | 26/28 (92.9%) |

This means H4 partly measured looping, truncation, and answer-extraction behavior—not only genuine reasoning overthinking. It followed the frozen specification exactly, so this is a design diagnosis rather than an implementation discrepancy.

## Independent integrity result

The final adjudicator independently rederived the source splits, rescored the traces, reconstructed the fixed sequence, recomputed the exact risk tests, and verified all three pushed terminal locks.

- Status: `VALID_NEGATIVE`
- Valid evidence package: `true`
- Three-cell H4a–H4d pass: `false`
- Cells with selected policy: `0/3`
- H4e confidence-component decision: `INCONCLUSIVE`
- Source/split/integrity checks: all passed
- Holdout correctly absent: all three cells

## Relationship to the original Gate 2 result

The July 24 Gate 2 discovery result remains valid within its frozen boundary: Qwen2.5-7B-Instruct on 200 GSM8K questions under the original prompt and stopping rule. H4 does not erase that result.

H4 does show that the stronger claim did not survive the registered certification matrix. PX-057 must not be described as having passed cross-model or cross-domain certification, as deployment-ready, or as certified below 2% harm.

The correct combined classification is: **strong bounded discovery result; valid negative certification/transfer result**.

## Permitted claims

- The H4 fixed sequence produced no certified prefix in all three frozen calibration cells.
- Aggregate accuracy improved by 3.0 to 6.2 points and mean token use fell by 42.5% to 50.9% for the first policy, while early-stop harm remained 5.6% to 8.0%.
- The registered harm-aware selection gate prevented an attractive average-utility result from being promoted as a safety certificate.
- The confidence grid was non-discriminating on the observed proxy scale, and blank/token-capped extractions accounted for most first-policy harms.

## Prohibited claims

- No policy achieved a 2% finite-population risk certificate.
- There is no H4 held-out transfer result, production guarantee, universal overthinking claim, or large-scale robustness claim.
- H4 does not prove that every policy in the grid fails; policies after index 1 were not reached under the fixed sequence.
- H4 does not prove that adaptive stopping generally cannot work.

## Next research decision

Close H4 unchanged. Do not rerun it with repaired extraction or different thresholds under the same experiment identifier.

If PX-057 receives another investment, it should be a new preregistered experiment with:

1. a non-empty, in-vocabulary answer requirement before stability can trigger;
2. an explicit truncation/repetition detector and a frozen rule for the last valid extractable answer;
3. confidence thresholds selected from an independent pilot or a scale-free rank/quantile signal;
4. the same per-question harm definition and Learn-then-Test certification barrier;
5. fresh calibration and untouched holdout splits.

That experiment would test a repaired mechanism. It must not be presented as a rescue of H4.

## Literature basis

- [When More Thinking Hurts](https://aclanthology.org/2026.findings-acl.1199/) motivates the operational reversal phenomenon.
- [Learn then Test](https://arxiv.org/abs/2110.01052) motivates risk-controlling policy selection with a separate test stage.
- [Conformal Thinking](https://arxiv.org/abs/2602.03814) provides broader context for controlled adaptive reasoning.

These works motivated H4; they did not predetermine its result.

## Bound evidence

| Evidence | Identity |
|---|---|
| Protected calibration fetch | Git commit `e27aafaa46967c85cb7f88517ef374e4ae8a3d73` |
| Holdout transport implementation | Git commit `52fb46f2595002498ba5e8ca3173423e7a03869e` |
| Pre-outcome transport freeze | Git commit `3242e21a5308decb81b8952de182e116256fc56d`; SHA-256 `1c9efd31239115093d94e45bd0a5004ef5924c9e9097a5e36027f01f16311cea` |
| Three LTT determinations | Git commit `8c87a3df6566a938ff13fae454854bdf17d98a4e` |
| Three terminal locks | Git commit `f95551b959daec8dc1efb3ab7f7fe81c6098e2e2` |
| C1 determination / lock | `95017eaba822985c1ea4d027f9818f96fe1bff0e75d945d0be68a149e88fc371` / `da5438a214632983bc2759effe7b80904d46e324fdffe5f9fc173ee199f296f2` |
| C2 determination / lock | `3393275ed1d73f980ac1c4dfde8886f42c0adad9a604da2a54cf5a1e906aeb85` / `452d73dd7914a17e4deef13b6f500abea2890ba4969218d3e8a01c351f9470fe` |
| C3 determination / lock | `8aba80d9c6e80d3b5a19211fa3fa8357e7dc4397838d7c962435b7a0496b2fbf` / `475c58114cf512396115898433f05ace44ddc0381319f62d9293f2c13254b30c` |
| Independent final adjudication | Git commit `cb26144`; SHA-256 `39c48510b08d65ae2b76561e89b4e6a693917d00eb62eb63428dab15a939312d` |
| Post-adjudication transport-absence check | SHA-256 `40f14821723efc4c43c7f683c58f25574e0fcf774931c28b6cdeafbdf3598b45` |

## Protocol wording disclosure

The frozen transport amendment’s execution-order prose can be read as requiring a terminal lock only for a cell with a non-empty prefix. The original H4 preregistration, frozen lock writer, all-lock verifier, and lock rule require a terminal record for every cell; a null lock closes an ineligible cell. Three null locks were therefore written and pushed before final adjudication. The frozen amendment is preserved unchanged, and this wording ambiguity is disclosed rather than edited after the outcome.
