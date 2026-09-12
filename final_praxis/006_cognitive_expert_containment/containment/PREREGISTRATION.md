# Final Praxis 006 Stage 2 — synthetic expert-fault containment

Frozen for execution, 2026-09-12, after root and independent implementation review. Commit and hash this document before any model execution. Free source/data preparation and synthetic tensor tests do not evaluate the model.

## Evidence and scope

The qualified pinned MiCRo135M architecture/checkpoint loads exactly and passes numerical and cache checks. Its first eight GSM8K examples at 128 tokens yielded no valid final answers; that failed capability protocol remains recorded. The separate ARC-Easy gate scored 19/32 correct with and without social ablation. The audit found altered candidate likelihoods on all 32 questions (maximum absolute change 0.6653769), social routing reduced from 5,501 selections to zero, and no decision changes. Thus H-Q2 established a score/routing intervention, not harmful reasoning or successful containment.

MiCRo already demonstrates expert removal and steering: https://arxiv.org/html/2506.13331v3. Counterfactual routing analysis (Yoon et al., 2605.07260) already compares equal-compute routes and updates a frozen model's router. RASA (2602.04448) is prior routing-aware safety alignment. No generic expert fallback/ablation novelty is claimed. Activation-patching conclusions depend on corruption and metric choices (Zhang and Nanda, https://arxiv.org/abs/2309.16042), motivating a second, different synthetic corruption at confirmation.

This is a bounded mechanistic feasibility experiment. A synthetic perturbation is an experimental fault, not evidence that the social module represents a mistaken belief, sycophancy, a human brain region, or naturally incorrect reasoning.

## Research question and hypotheses

RQ: Can a fixed non-oracle rule detecting disagreement between a selected expert's observed update and the router's next-best alternative reduce damage from an expert fault while preserving clean task accuracy, beyond permanent removal and a randomized fallback?

H-M1: The prespecified perturbation causes at least two clean-correct confirmation questions to become wrong without intervention. H-M2: The calibrated conditional rule recovers at least one of these damaged questions without losing any clean-correct confirmation questions. H-M3: A useful containment contribution requires better perturbed accuracy than the random control and evidence of a retention advantage over permanent social ablation; if permanent removal performs equally well, conditional containment has not earned a contribution. These are progression gates, not powered statistical claims.

## Exact interventions and gate

Use only the qualified checkpoint bkhmsi/micro-smollm2-135m at 1ebfb28c382f9176647bbbb9f63cdb7ed0a62e57 and the existing reviewed MiCRo source/SDPA adaptation; no training of weights.

For every block l and position t, h is the incoming hidden state, y_s is the social expert output, and delta_s = y_s - h. Let s be expert index 1. Perturb only positions whose original top-1 route selects s. Primary corruption is observed y_s' = h - delta_s: it reverses the residual update while preserving its norm. The clean condition is y_s' = y_s. The reserved transfer corruption is y_s' = h + P delta_s, where P cyclically shifts the hidden dimension by exactly 17. Both act on post-block outputs, leaving that block's attention/KV computation intact. Apply at every block where social was selected; later layers receive the resulting altered state.

Let b be the next-best non-social expert according to the current router, evaluated on the same incoming state, and delta_b = y_b - h. The only proposed gate feature is d = 1 - cosine(y_s' - h, delta_b), with zero distance for a zero-norm operand (norm product <= 1e-12). Replace the selected social output with y_b iff d > tau. Preserve the original top-1 weight normalization, and use the corresponding normalization for the backup. A corruption actuator has access to the original output to construct the fault; the gate receives only the observed update and alternative update. It never receives gold, a clean reference update, corruption identity, realized answer correctness, or a choice singled out by gold.

Calibration thresholds are exactly {0.5, 1.0, 1.5, 2.0}; 2.0 disables the gate because d is clamped to [0,2]. All experts and router weights remain frozen.

## Data, calibration and confirmation

Use the same pinned allenai/ai2_arc ARC-Easy dataset revision as the previous artifact. Data preparation records train/test parquet hashes and fixture hash. Select the first 16 training rows after excluding normalized question-text overlap with the entire test split. Select original test rows 32 through 63, excluding the previously exposed first 32. Preserve choice order and all labels.

Calibrate on clean and sign-reversed versions of the 16 training questions only. Among thresholds with no clean calibration accuracy loss against unprotected baseline, maximize corrupted calibration correct count; break ties by clean correct count, fewer interventions, then larger threshold. Freeze selected threshold and calibration result before confirmation. Do not tune on the confirmation permutation condition.

Use all four conditions on clean, negated and permuted confirmation inputs: unprotected, permanent social ablation, conditional fallback, and random fallback. Permanent ablation uses the upstream model's actual experts_ablate=['social'] at all layers. The random policy uses a single rate fixed to the selected gate's aggregate intervention/eligible-token rate on both calibration conditions. Its deterministic random seed includes question ID, candidate label and layer, never corruption identity or gold. This matches intervention rate in expectation on calibration; actual confirmation rates must be reported, not described as exactly matched.

## Scoring, controls and implementation checks

Reuse the qualified ARC scorer: zero-shot plain Question/Answer template, leading-space full answer-choice continuation, summed continuation token likelihood as primary. No chat template, labels-as-answer-token shortcuts, prompt-token loss, extra BOS/EOS, or input truncation. Score every candidate identically; gold enters only final offline scoring/calibration.

For this full-sequence, no-cache implementation, the pinned source already evaluates all four expert blocks. Hooks capture those existing outputs; they must not call an additional expert forward. Apply the same capture/disagreement instrumentation in all four conditions. Report elapsed time and candidate forwards; do not extrapolate this cost to cached autoregressive decoding.

Before calibration require (i) unhooked versus clean unprotected hook score agreement <=1e-6, and (ii) always-fallback hook versus actual permanent ablation score agreement <=1e-4 on the first calibration candidate. Stop on nonfinite activations, missing expert captures, top-k !=1, or sequence-length/cache mode mismatches. Hooks must remove cleanly. Log effective routes separately: upstream routing output still describes nominal selection before the conditional override.

## Failure and advancement gates

Report all question-level predictions, candidate likelihoods, corruption exposures and intervention counts. Primary robustness comparison is conditional versus unprotected under negation; permutation transfer is separately reported. Report clean-correct losses, corruption-induced errors, recovered errors, and clean harms caused by permanent ablation.

Do not claim useful containment if corruption changes only scores but no decisions; the conditional policy is disabled; random fallback is equally good; benefits require clean-accuracy sacrifice; or permanent ablation dominates. If clean permanent ablation harms no questions, ARC has not demonstrated useful social-expert contributions and cannot support a preservation claim. A later study must preselect an independent task family where social capability is relevant and rotate expert identities. Do not select held-out questions by observed ablation benefit.

Treat all 32 confirmation questions as exposed development material after this gate; a publishable result requires a separately powered untouched study. Report paired question-level intervals when expanding; never treat candidate tokens or repeated prefixes as independent observations. Model-level activations permit statements about the specified intervention only, not biological equivalence.

## Source contract and deployment

The pinned active use_router=True decoder path returns raw router logits; the similarly named variable is overwritten with probabilities only in the inactive use_router=False path. An AST source-contract audit records this distinction. Hooks reproduce the active float32 softmax then top-k selection, including possible rounded ties, and require evaluation mode. Prior descriptions that treated the active tuple as probabilities were incorrect; previous ARC route argmax counts remain unaffected by this distinction. No prior scores are recalculated or replaced here.

Frozen fixture SHA256: fd98835911aba2915ebde86add8c89666b556c4bc936ec75516188710367b96e. Exact train/test source hashes and all48 IDs are in data/data_lock.json. This is item holdout within ARC-Easy, not a new-domain generalization claim.

Reuse the existing CPU host i-07178e293e8df2a60 temporarily as m6i.2xlarge, its existing scratch disk, qualified CPU environment and cached weights. Run this study alongside007 without sharing or exposing labels between studies. Independent AWS stop within4hours; study supervisor within2.25hours, including model load. Incremental compute/request envelope for006 is below$5 and the combined new006/007 envelope below$60 including007's$25 API ledger. No new disk or persistent endpoint. The original005GPU run has a separate unchanged deadline and is not used here.

## Execution bound

No model calls were made while staging. The runner defaults to dry validation; --execute requires a frozen preregistration path/hash. Maximum 3,000 candidate forwards and two hours of model evaluation, excluding model load. Calibration has at most 960 forwards (16 questions, up to five choices, 12 conditions), confirmation at most 1,920 (32 questions, up to five choices, 12 conditions), plus four sanity forwards. Cached cells require manifest identity equality. Parent schedules AWS execution and cost controls; no jobs are launched by this preregistration or staging work.

