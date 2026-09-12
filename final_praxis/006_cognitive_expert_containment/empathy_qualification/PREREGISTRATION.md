# Final Praxis 006: empathy social-utility qualification — preregistration draft

Status: prepared 2026-09-12 before this task's model execution. Root must review and freeze this document before paid execution. This is a separate validation-only task adaptation. Preserve every prior GSM8K/ARC result and null outcome.

## Research question and hypothesis

RQ: On the already qualified MiCRo-SmollM2-135M checkpoint, does permitting the social expert improve agreement with SOCKET empathy labels enough to justify a later preservation-versus-containment study?

H-E1: On the frozen balanced 64-example validation fixture, intact inference obtains at least 39 correct answers (60.9375%), exceeds permanent social ablation by at least two correct answers, and has at least two baseline-correct to ablation-wrong cases. These are feasibility thresholds, not a significance claim or evidence of a new routing method. A 32/64 constant-label baseline is reported.

Falsifiers: any failed conjunct leaves this task unqualified. In particular, zero baseline-correct to ablation-wrong cases is a retained zero-harm null result. Do not promote empathy as the primary preservation task, choose alternative rows/prompts, switch checkpoints, tune a gate, or inspect test performance to rescue that result. Another qualification requires a separate prospectively frozen protocol. Qualification alone authorizes no held-out test inference.

## Source and construct

MiCRo v3 uses empathy in routing analysis; no tiny-checkpoint empathy accuracy/ablation benchmark was established by the source review. Its released empathy runner uses three fixed user/assistant demonstrations, the SOCKET question, and open-ended generation. We preserve those six demonstration messages and question exactly, but replace generation with full-answer-string likelihood and add permanent social ablation. CPU float32, no-cache inference also differs from its GPU generation path. This is task adaptation, not numerical reproduction. See ATTRIBUTION.md for pinned sources.

The original Empathic Reactions target is authors' self-reported empathic concern after reading news. SOCKET supplies a binary target, while its prompt asks whether the text expresses empathy. Report agreement with the released binary labels, never objective feelings, psychological competence, or neuroscience equivalence. Binarization provenance and model-training overlap remain unresolved for a publication claim.

## Frozen data and prompt

Dataset: Blablablab/SOCKET, task empathy#empathy_bin, revision beb92deb932d67a6319cc7ca71d8056ececc47d2. Only validation texts/labels are read by prepare.py. Of 186 validation rows (87 empathy, 99 not empathy), select 32 per label by ascending SHA256 of `006-empathy-validation-v1:{zero_based_row}:{sha256(stripped_text)}`; then sort the selected rows by the same hash. Selection uses public labels for balancing and no model outcomes. No training/test text or labels are opened by this preparation or runner. Prior repository artifact inspection is documented separately; do not imply that public test artifacts have never been inspected anywhere in the project.

Fixture SHA256: 256473989b7a2ea14a282f88c0845d3ed7a080b2507edd16e6e7fa861d4078e1.

Prompt SHA256: 94273b598c6aa40c545c57616dc9fe9b487ee17f9ca8ff3d7e425770875b9470.

Use the source's three demonstrations in their exact order, followed by its question for the target text. Render through the pinned SmolLM2-135M-Instruct tokenizer's chat template with add_generation_prompt=True and no added system message. Compare literal continuations `The answer is No.` (not empathy) and `The answer is Yes.` (empathy), in that order. Do not append a chat-end token, add a space, request rationale generation, or normalize by length. Sum all candidate token log probabilities; exact ties choose not empathy. The shared assistant prefix cancels only as actually tokenized. Verify rendered and direct-template context token IDs agree and the context remains a full token prefix after appending each candidate; otherwise stop.

## Measurement and controls

Reuse load_qualified_model from the existing ARC runner, with the identical pinned checkpoint, base config, tokenizer, reviewed custom source/SDPA patch and strict missing/unexpected key checks. Model: bkhmsi/micro-smollm2-135m at 1ebfb28c382f9176647bbbb9f63cdb7ed0a62e57; 491,457,600 total parameters. Four CPU threads, float32, eval mode, fixed seed 20260912, batch one, no KV cache, no gradients or training. Enforce all parameter devices are CPU.

For every example, score both full candidate strings under intact and upstream permanent `experts_ablate=['social']`; pass an explicit empty list to intact forwards. Gold enters only the final correctness calculation, never the model inputs or condition choice. Score first candidate token from context-length minus one in the shifted next-token logits; include every candidate token and exclude all chat-end tokens. No input truncation or invalid-cell dropping is permitted.

Before cohort inference, run baseline→ablation→baseline on the first frozen example's No candidate. Require reset likelihood difference <=1e-6 and zero ablated social selections. Record candidate token IDs, per-token log probabilities, their double-precision sum, rendered-context/token hashes and selected route counts. Route participation is diagnostic, not utility. Full-sequence source inference executes all four experts per block even when social selection is ablated; this study does not establish compute savings.

Report baseline and ablation accuracy, each label's recall, constant-label accuracy, paired CW/WC counts, net advantage, and a descriptive 2,000-replicate paired question bootstrap interval with seed 20260912. The fixed 32/32 cohort makes overall accuracy equal balanced accuracy. No p-value or multiplicity-adjusted discovery claim is planned. Treat observed subgroup patterns as descriptive, without changing the gate.

## Bounds and disposition

Root execution freeze,12September2026: this reviewed version supersedes the staging draft status above. Launch only on the existing bounded CPU host with its existing qualified environment/cache and disk. External supervisor maximum1800seconds including load; the tighter of this limit and the original host stop14:00:33UTC applies, with no extension. Incremental CPU ceiling below$1, inside the combined$60 stage-two envelope. No new machine, storage, endpoint or API calls. The completed sign-reversal containment study matched random/permanent ablation on perturbed accuracy and failed permutation transfer; this qualification does not revise or rescue those outcomes. It asks whether there is a useful social-task baseline for a differently designed later method.

128 cells: 64 questions x two conditions. Two candidate forwards per cell =256, plus three reset checks =259 in a fresh run. Hard cap 300 candidate forwards and 7,200 seconds after model loading; preserve partial receipts if stopped. Root's external launch budget and timeout govern loading. Cached resume verifies immutable manifest-based cell identities and repeats reset checks. Save the preregistration hash, all source/data hashes and runtime environment.

If qualified, propose a separate preregistration for useful-ability preservation plus the existing fixed synthetic-fault intervention, on untouched evaluation data. Do not fit a containment threshold or evaluate the test split in this qualification. Even a positive gate is insufficient evidence of selective containment advantage over permanent ablation, naturally erroneous reasoning repair, or a publishable new contribution.
