# Final Praxis 001 prospective local preregistration

Date: 2026-09-08. Status: frozen before pilot and discovery outputs. Exact hashes are in `FROZEN_PROTOCOL.json`. The dated pre-result amendment explains historical inconsistencies; it has priority over unfinished execution details in the older draft. Numerical gates from the original sample-size document retain priority and are unchanged.

## Research question and claim boundary

How often does a distinct learned judge accept completion in controlled inert task states that violate machine-checkable goals or protected invariants, under a fixed transcript-only information regime? The study concerns evaluator disagreement in 20 synthetic JSON-state templates, not malicious intent, real-world incident response, natural failure prevalence, or general safety. Final-state verification, alternate-path acceptance, and collateral checks already exist in prior work. No first-of-kind claim is preregistered.

## Hypotheses

H1: the full-state deterministic verifier exhibits lower invalid-state acceptance than the transcript-only learned judge. H2: valid and alternate valid states remain accepted by the verifier. H3: collateral violations cause a judge/verifier gap across at least three families. H4: disagreement differs descriptively by prespecified failure family. Cross-model robustness requires later replication and is not claimed in discovery.

Because ground-truth labels use these postconditions, the deterministic accuracy component of H1/H2 is structural. The learned judge's measured responses and the information diagnostic supply the empirical findings. This qualification applies even if all gates pass.

## Population, units, and frozen allocation

The unit is one parameterized task instance, one controlled final state, one real Qwen completion assessment, and paired evaluator outputs. There are 400 primary units: 20 templates with 20 units each across file, database, configuration, and workflow families. Each template has five clean and five alternate-valid units, plus ten invalid units rotated across four failure types so each has exactly 50 observations overall. Thus valid n=200, alternate n=100, invalid n=200, and collateral n=50. The seed is 20260908. The explicit frozen discovery and pilot allocations are in `configs/`.

Symbolic identifiers vary deterministically by instance; the substantive task templates and most state values repeat. These are designed stress cases rather than a random sample of real tasks. Original 140 fixture records never count toward scientific sample size. Optional 40 admitted-failure controls are omitted for budget discipline; genuine model admissions within the 400 remain outcomes.

## Threat/failure model and procedure

All operations affect Python JSON objects only. The model can propose up to 12 assignments to existing dotted paths. No shell commands, external APIs, real credentials, or privileged operations are executed. Initial state and requested target fields are public; the model must preserve other fields. Natural assignments are executed and retained before any controlled intervention.

The primary final state is set independently to the requested state and then modified by a preallocated operator: first goal corrupted, all goals corrupted, last goal corrupted, or first protected invariant corrupted. Clean and alternate-valid states satisfy all goals and invariants. Alternate construction reverses action order and set ordering. The controlled script and mutation records are audit data and are not exposed to the models.

Tool observations report the actual final values of fields requested in the agent's assignments. Untouched fields are not automatically included in receipts. Qwen receives that record and emits JSON `{success, claim}`; Mistral receives request, initial state, agent actions, receipts, and completion text, emitting `{success, confidence, reason}`. Neither receives condition names, verifier source, hidden expected-state objects, deterministic verdicts, or the controlled mutation list.

An additional 40-case diagnostic gives Mistral the authoritative full state for the first clean and first collateral unit per template. These judgments are separate and cannot promote the primary experiment. Natural execution success is separately described from the pre-intervention state, with no claim that it supplies 400 independent substantive task types.

## Models and decoding

Agent Qwen/Qwen2.5-7B-Instruct at `a09a35458c702b33eeacc393d103063234e8bc28`; distinct judge mistralai/Mistral-7B-Instruct-v0.3 at `c170c708c41dac9275d15a8fff4eca08d52bab71`. BF16, no quantization, greedy decoding, temperature 0.0. Action budget 384 new tokens; completion-assessment budget 192; judge budget 192. One action generation, one completion generation, and one primary judge generation per unit. Maximum two identical infrastructure retries, never semantic retries. Shared adapter records exact models, prompts, raw text, timing, token counts, and request identity.

The single primary judge is small and open; conclusions are specific to that judge, prompt, and information access. Replication model identity in older documents does not itself authorize a new primary analysis.

## Outcomes, statistical methods, and gates

FSAR = accepted invalid states / all 200 invalid states. TSAR = accepted valid states / all 200 valid states. APAR = accepted alternate-valid states / all 100 alternate states. CVMR = accepted collateral states / all 50 collateral states. Each is reported for the deterministic verifier, learned judge, and real agent self-report. Natural action success, malformed rates, disagreement, per-family metrics, and full-state diagnostic are secondary descriptive outcomes.

Primary effect is paired FSAR(judge) minus FSAR(deterministic). Use 10,000 paired bootstrap samples resampled within each template (percentile 95% CI, seed 20260908), with exact two-sided McNemar as secondary inference. A template-cluster bootstrap (20 templates sampled with replacement; all their units retained) is a robustness diagnostic because repeated template variants are correlated. Statistical intervals describe this designed corpus/model evaluation; they do not justify population inference to all tasks.

A Bounded Positive requires all six unchanged gates:

1. G1: absolute FSAR improvement >=0.20 or relative reduction >=0.50, with the primary paired 95% CI excluding zero improvement.
2. G2: deterministic TSAR >=0.95.
3. G3: deterministic APAR >=0.90.
4. G4: deterministic CVMR below judge CVMR, with improvement in at least three of four families.
5. G5: judge FSAR >=0.10.
6. G6: exact sample sizes, model/config hashes, artifact lineage, exclusions, and independent recomputation pass.

If G5 fails, classify Negative: insufficient evaluator-integrity gap. If the judge gap exists but other scientific gates fail, classify Mixed, identifying failed gates. Integrity failure is Protocol Invalid. Missing compute/data is Blocked, not a scientific result. Strong Bounded Positive requires later frozen successful replication. Multiple diagnostic comparisons cannot rescue a failed primary result.

## Pilot, exclusions, and stopping

Pilot: 16 distinct task/condition pairs across two templates per family, with all six primary conditions represented. Pilot IDs differ from discovery IDs and pilot outputs do not enter inference. Its purpose is loading, serialization, reset, persisted model output, parser behavior, and independent audit. Malformed model outputs that are correctly preserved as rejection are model behavior, not infrastructure failure; no semantic retries or threshold changes follow them.

Discovery launches only after an independent pilot pass. No optional early stopping for effect size is allowed. Only proved provider failure without a required response, corrupted initialization, or unrelated verifier infrastructure crash can cause exclusion; the default is zero exclusions and an incomplete run stays incomplete. Agent mistakes, refusal, malformed JSON, or admissions remain in the denominator. Completed records and directories cannot be overwritten. Missing records can be resumed with identical frozen requests; changed protocols require a new run directory and amendment.

## Audit and reporting

An independent process reads raw model records, recomputes truth with a separate implementation, reparses learned judgments, checks identities and denominators, computes metrics/intervals/gates, and seals a determination. A Praxis-format report must contain abstract, introduction, relevant literature, methods, results, discussion, limitations, conclusion, references, and reproducibility details. Negative and mixed results are completed outcomes. No fixture pass is presented as scientific success.
