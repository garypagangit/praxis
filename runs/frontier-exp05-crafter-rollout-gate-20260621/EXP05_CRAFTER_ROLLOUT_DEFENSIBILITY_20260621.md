# EXP05 Crafter Rollout Internal Defensibility Challenge

Generated: 2026-06-21T11:06:59.497575+00:00

Verdict: **ENVIRONMENT SMOKE PASS - WORLD-MODEL CLAIM NOT PROMOTED**

| Defense question | Answer |
|---|---|
| Did a real environment run? | Yes. `25` Crafter episodes completed across clean/dev/held-out perturbations. |
| Did held-out perturbations run? | Yes. `center_occlusion` and `salt_pepper` were evaluated after source/wrapper freezing. |
| Is this a world-model agent result? | No. The agent is a deterministic observation-checksum policy. |
| Are multiple paradigms compared? | No. |
| Was augmentation tested? | No. |
| Final decision | Environment path passes; thesis claim is not promoted. |
