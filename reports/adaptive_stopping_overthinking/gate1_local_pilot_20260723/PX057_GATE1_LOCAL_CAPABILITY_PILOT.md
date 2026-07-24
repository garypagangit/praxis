# PX-057 Gate 1 Local Capability Pilot

Status: **PIPELINE PASS / MODEL CAPABILITY FAIL / GPU PILOT REQUIRED**

This run used `google/flan-t5-small` on 12 deterministically sampled GSM8K test questions with five iterative reconsideration rounds per question.

## Reproducibility

- Dataset SHA-256: `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`
- Sample seed: `57`
- Questions: `12`
- Generated trace steps: `60`
- Decoding: deterministic

## Results

| Metric | Value |
|---|---:|
| Fixed-long accuracy | 0.0000 |
| Adaptive accuracy | 0.0000 |
| Observable overthinking events | 0 |
| Mean simulated compute saving | 0.6006 |
| Early-stop harms | 0 |

## Determination

The data download, hash lock, deterministic sampling, iterative prompting, intermediate-answer extraction, correctness scoring, confidence calculation, trace serialization, and adaptive replay all completed.

The model produced no correct final answers and no observable correct-to-wrong events. Therefore this run cannot evaluate the adaptive-stopping hypothesis. The reported compute saving is mechanically defined but scientifically meaningless when all candidate answers are wrong.

Proceed to the frozen Qwen2.5-7B-Instruct GPU capability pilot. Do not tune the stopping policy from this FLAN result.

## Next artifact

`configs/px057_adaptive_stopping_gate1_gpu_pilot_20260723.json`
