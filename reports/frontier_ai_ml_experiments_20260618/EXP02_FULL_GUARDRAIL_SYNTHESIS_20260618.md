# EXP02 Full Guardrail Synthesis

Date: 2026-06-18

Experiment: `frontier-exp02-self-jailbreak-guardrail`

Status: **MIXED - RESPONSE-PREFIX SIGNAL PRESENT, NOT PROMOTED**

## Scope

Two AWS gates were completed after the schema-readiness pass:

1. `frontier-exp02-self-jailbreak-full-20260618`: lightweight TF-IDF/logistic prompt and response-step detectors.
2. `frontier-exp02-self-jailbreak-guardian-step-20260618`: open-source Granite Guardian 3.2 5B prompt and response-prefix judge.

Both gates kept raw prompts and responses in memory/private cloud execution only. The committed run artifacts contain hashes, lengths, labels, parsed predictions, and metrics only.

## Primary Results

| Gate | Prompt harmful recall | Prompt benign false-refusal | Response-step unsafe recall | Safe-response block | Caught unsafe exposure | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Lightweight detector | `0.7400` | `0.6900` | `0.8158` | `0.1818` | `0.2370` | Mixed / fail promotion |
| Open guardian step judge | `1.0000` | `0.8700` | `1.0000` | `0.1818` | `0.1310` | Mixed / fail utility gate |

The constructive result is the response-prefix signal. Granite Guardian caught `38/38` unsafe held-out responses and did so after an average of `13.10%` of the response, an exposure reduction of `86.90%` relative to output-only blocking. The same run still blocked `12/66` safe responses, so it fails the pre-registered safe-block target of `<=0.05`.

## RQ/H Readout

| Item | Readout |
|---|---|
| RQ1 / H1 | Partially supported only for the open guardian: response-prefix unsafe recall reached `1.0000`; the lightweight detector reached only `0.8158`. |
| RQ2 / H2 | Not supported. Both gates over-block benign/safe controls. Prompt benign false-refusal was `0.6900` for the lightweight detector and `0.8700` for the open guardian. |
| RQ3 / H3 | Mechanism signal only. Step-prefix monitoring is much earlier than output-only blocking, but the utility cost is still too high for a Praxis promotion claim. |

## Defense Challenge

| Challenge | Answer |
|---|---|
| Were strict holdouts used? | Yes. WildJailbreak was used for lightweight prompt-detector development; JailbreakBench harmful/benign and judged-response holdouts supplied final checks. The guardian gate used the same held-out response split with no training. |
| Did the work produce a positive signal? | Yes, narrowly: open response-prefix guarding caught all unsafe held-out responses early. |
| Did it prove the thesis? | No. The thesis requires safety improvement without material over-refusal. The utility gate failed. |
| Is it worth publishing now? | Not as a full EXP02 paper. It is worth preserving as a strong pilot/result subsection showing why refusal-aware moderation is required for step-level intervention. |
| What would make it promotable? | A refusal-aware guardrail or manually labeled boundary model that keeps response-step recall `>=0.85` while reducing safe-response block to `<=0.05`, followed by a private live open-model validation run. |

## Decision

Do not promote EXP02 as a publication-ready positive yet. Keep the result as a defensible AWS pilot with a clear contribution boundary:

- prompt-level blocking is too blunt on benign controls;
- open guardian response-prefix monitoring produces a strong early-detection signal;
- the next gate must solve safe-response over-blocking, not rerun the same threshold sweep.

Recommended next gate if EXP02 is continued: use a refusal-aware safety classifier such as WildGuard if access is available, or a custom calibration layer with manually labeled refusal/safe-boundary examples. Otherwise move the frontier queue to EXP04.

Primary artifacts:

- `runs/frontier-exp02-self-jailbreak-full-20260618/EXP02_FULL_GUARDRAIL_RESULT_20260618.md`
- `runs/frontier-exp02-self-jailbreak-full-20260618/EXP02_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md`
- `runs/frontier-exp02-self-jailbreak-guardian-step-20260618/EXP02_GUARDIAN_STEP_RESULT_20260618.md`
- `runs/frontier-exp02-self-jailbreak-guardian-step-20260618/EXP02_GUARDIAN_DEFENSIBILITY_CHALLENGE_20260618.md`
- `configs/frontier_exp02_self_jailbreak_full_20260618.json`
- `configs/frontier_exp02_guardian_step_20260618.json`
