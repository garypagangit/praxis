# Praxis EXP03 Protocol - Instruction Diversity and Linguistic Generalisation in VLA Models

Generated: 2026-06-19

Status: **source/readiness gate active; simulator smoke pending**

Source brief: `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`

## Experiment ID

`frontier-exp03-vla-instruction-diversity`

## Working Title

**OpenVLA Instruction Diversity Sweep**

## Thesis

Linguistic diversity in trajectory annotations is a binding constraint for VLA instruction generalisation. A controlled paraphrase-variant sweep can improve robustness to held-out instruction forms without requiring new robot data collection, but only if the simulator/evaluation stack first reproduces baseline behavior.

## Research Questions

| ID | Research question | Decision evidence |
|---|---|---|
| RQ1 | Does adding instruction variants improve success on held-out paraphrase templates? | LIBERO success rate on held-out templates by variant count. |
| RQ2 | Where do returns saturate as variants per trajectory increase? | 0/1/5/10 variant curve with confidence intervals. |
| RQ3 | Does language-diversity improvement transfer across suite or embodiment? | Held-out LIBERO suite or Bridge/OXE transfer gap. |

## Hypotheses

| ID | Hypothesis | Promotion gate |
|---|---|---|
| H1 | Held-out paraphrase success improves from 0 to 5 variants per trajectory. | Positive held-out-template success delta with bootstrap CI. |
| H2 | Returns saturate near 5 variants; 10 variants adds small marginal gain. | Variant-count curve and overlap of 5-vs-10 CIs. |
| H3 | Improvements transfer to at least one held-out suite/embodiment without harming base success. | Held-out suite success delta and clean-task success retention. |

## Literature Review

OpenVLA provides an open vision-language-action model and evaluation recipes for robot manipulation. OpenVLA-OFT reports improved fine-tuning and action decoding for VLA policies. LIBERO provides long-horizon language-conditioned robot manipulation suites. Bridge/Open X-Embodiment-style data motivate cross-dataset and cross-embodiment generalisation.

The EXP03 first gate is deliberately a source/readiness gate. It does not claim robot success. It checks that the required repos, checkpoints, and at least one accessible LIBERO dataset path are available, and freezes an instruction-variant manifest before any training or simulator threshold decisions.

## Dataset And Tool Plan

| Source | First-gate role | Formal role |
|---|---|---|
| `openvla/openvla` | Baseline model/repo availability. | Baseline VLA policy. |
| `moojink/openvla-oft` | OFT training/evaluation recipe availability. | Primary fine-tuning path. |
| LIBERO repo | Simulator/evaluation stack availability. | Official task success evaluation. |
| `lerobot/libero_10` | Public dataset-viewer smoke source. | Initial accessible data path. |
| OpenVLA/OFT LIBERO checkpoints | Model checkpoint availability. | Baseline and fine-tuned comparisons. |

## Split Discipline

| Split role | Source | Used for | May tune? | Final claim use |
|---|---|---|---:|---|
| `train_template` | Base and simple paraphrase templates | Training/instruction augmentation. | Yes. | No final metric. |
| `heldout_template` | Frozen templates not seen during training | Paraphrase robustness. | No. | Primary metric. |
| `heldout_suite` | LIBERO suite or Bridge/OXE subset not used for training | Transfer. | No. | Promotion metric. |

## GMR - Goal / Method / Rationale

**Goal.** Test whether language diversity in instructions improves VLA generalisation rather than just memorizing task wording.

**Method.** Verify the OpenVLA/LIBERO/OFT resource path, freeze a train/held-out template manifest, then run a 0/1/5/10 variant fine-tuning/evaluation sweep only after official baseline success is reproduced.

**Rationale.** Without an environment gate, a VLA result can be a simulator/install artifact. Freezing the instruction variants first prevents post-hoc prompt selection.

## Feature Engineering Plan

| Feature group | Examples |
|---|---|
| Linguistic features | token count, verb set, object nouns, template family, edit distance from base. |
| Task metadata | LIBERO suite, task id, object category, spatial relation. |
| Training design | variants per trajectory, seed, held-out template flag. |
| Evaluation | success/failure, horizon, suite, clean versus paraphrase template. |

Optuna is not part of the first gate. Later sweeps may tune learning rate on training/validation suites only, never on held-out templates.

## Results Gates

| Stage | Pass | Stop or reframe |
|---|---|---|
| Source gate | Required repos/checkpoints available, at least one public LIBERO dataset path, frozen variant manifest. | Core assets inaccessible or mostly gated. |
| Environment gate | LIBERO/OpenVLA-OFT install and one official eval smoke run. | Cannot reproduce baseline install/eval path. |
| Sweep gate | 0/1/5/10 variant sweep with strict held-out templates. | Improvement disappears on held-out templates. |
| Promotion | Three seeds, CIs, held-out suite/embodiment, clean-success retention. | Result is only prompt-style overfitting. |

## What Not To Claim

- Do not claim VLA success from source availability alone.
- Do not count synthetic instruction variants as new robot trajectories.
- Do not tune held-out paraphrases after seeing evaluation results.
- Do not promote until an official LIBERO baseline run is reproduced.
