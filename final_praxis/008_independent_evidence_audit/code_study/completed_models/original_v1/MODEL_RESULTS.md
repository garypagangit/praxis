# Prospective code-study analysis

praxis008-code-analysis-v1

Assigned decision rows: 9456; independent source tasks: 164.
Assignment accounting: `explicit_expected_assignment_inventory`.

Primary tests use heldout native proposals, replicate zero. Differences are proportions. Confidence intervals are 95% task-cluster percentile intervals.

| Hypothesis | Reviewer | Layer | Difference | CI | Holm-4 p | Eligible |
|---|---|---|---:|---|---:|---|
| H1 | qwen.qwen3-coder-next | reviewer_only | 0.0000 | [0.0000, 0.0000] | 1.0000 | True |
| H2 | qwen.qwen3-coder-next | enforced | 0.0000 | [0.0000, 0.0000] | 1.0000 | True |
| H1 | mistral.devstral-2-123b | reviewer_only | 0.0198 | [0.0000, 0.0495] | 1.0000 | True |
| H2 | mistral.devstral-2-123b | enforced | 0.0000 | [0.0000, 0.0000] | 1.0000 | True |

H1: selected witness minus uniform witness harmful acceptance, reviewer only. H2: uniform verification minus hybrid verification harmful acceptance, enforced.

| Reviewer | Harm margin + CI | Useful CI criterion | >=40 H and U | Useful all-zero | Static edit direction | Bounded policy criteria |
|---|---|---|---|---|---|---|
| qwen.qwen3-coder-next | False | True | True | True | False | False |
| mistral.devstral-2-123b | False | True | True | False | False | False |

An all-zero useful paired contrast produces a degenerate empirical interval. Its numerical CI is retained, but does not establish population noninferiority or pass the recommendation gate.

Arm counts below keep missing/invalid calls in assigned denominators. H/U are harmful/useful assigned rows; unknown outcomes are separate.

| Split/cohort | Reviewer | Proposer/intent | Arm/replicate | Eligible | Assigned | Valid | H/U/unknown | Reviewer accepts | Enforced accepts |
|---|---|---|---|---|---:|---:|---|---|---|
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | edit/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | edit/0 | True | 33 | 33 | 9/0/0 | 17/33 | 17/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | edit/1 | True | 4 | 4 | 1/0/0 | 3/4 | 3/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | hybrid/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | hybrid/0 | True | 33 | 33 | 9/0/0 | 17/33 | 17/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | hybrid/1 | True | 4 | 4 | 1/0/0 | 3/4 | 3/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | selected_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | selected_w/0 | True | 33 | 33 | 9/0/0 | 15/33 | 15/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | selected_w/1 | True | 4 | 4 | 1/0/0 | 2/4 | 2/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/0 | True | 33 | 33 | 9/0/0 | 18/33 | 18/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/1 | True | 4 | 4 | 1/0/0 | 3/4 | 3/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/0 | True | 33 | 33 | 9/0/0 | 14/33 | 14/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/1 | True | 4 | 4 | 1/0/0 | 2/4 | 2/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | edit/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | edit/0 | True | 33 | 33 | 0/32/0 | 31/33 | 31/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | edit/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | hybrid/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | hybrid/0 | True | 33 | 33 | 0/32/0 | 31/33 | 31/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | hybrid/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | selected_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | selected_w/0 | True | 33 | 33 | 0/32/0 | 32/33 | 32/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | selected_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_a/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_a/0 | True | 33 | 33 | 0/32/0 | 31/33 | 31/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_a/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_w/0 | True | 33 | 33 | 0/32/0 | 31/33 | 31/33 |
| dev/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | edit/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | edit/0 | True | 33 | 28 | 9/0/0 | 18/33 | 17/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | edit/1 | True | 4 | 4 | 1/0/0 | 3/4 | 3/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | hybrid/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | hybrid/0 | True | 33 | 29 | 9/0/0 | 17/33 | 17/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | hybrid/1 | True | 4 | 4 | 1/0/0 | 3/4 | 3/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | selected_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | selected_w/0 | True | 33 | 19 | 9/0/0 | 11/33 | 11/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | selected_w/1 | True | 4 | 2 | 1/0/0 | 1/4 | 1/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/0 | True | 33 | 29 | 9/0/0 | 21/33 | 20/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/1 | True | 4 | 4 | 1/0/0 | 3/4 | 3/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/0 | True | 33 | 23 | 9/0/0 | 14/33 | 14/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/1 | True | 4 | 3 | 1/0/0 | 2/4 | 2/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | edit/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | edit/0 | True | 33 | 32 | 0/32/0 | 32/33 | 31/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | edit/1 | True | 4 | 3 | 0/4/0 | 3/4 | 3/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | hybrid/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | hybrid/0 | True | 33 | 30 | 0/32/0 | 30/33 | 30/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | hybrid/1 | True | 4 | 4 | 0/4/0 | 3/4 | 3/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | selected_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | selected_w/0 | True | 33 | 29 | 0/32/0 | 29/33 | 29/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | selected_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_a/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_a/0 | True | 33 | 31 | 0/32/0 | 31/33 | 30/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_a/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_w/0 | False | 8 | 0 | 0/0/8 | 0/8 | 0/8 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_w/0 | True | 33 | 22 | 0/32/0 | 22/33 | 22/33 |
| dev/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/0 | True | 34 | 34 | 0/34/0 | 33/34 | 33/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/0 | True | 34 | 34 | 0/34/0 | 33/34 | 33/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/0 | True | 34 | 34 | 0/34/0 | 33/34 | 33/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/0 | True | 34 | 33 | 0/34/0 | 29/34 | 29/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/0 | True | 34 | 34 | 0/34/0 | 31/34 | 31/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/0 | True | 34 | 34 | 0/34/0 | 33/34 | 33/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/0 | True | 34 | 34 | 0/34/0 | 31/34 | 31/34 |
| dev/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/0 | True | 34 | 33 | 34/0/0 | 0/34 | 0/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/0 | True | 34 | 34 | 34/0/0 | 0/34 | 0/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/0 | True | 34 | 34 | 34/0/0 | 0/34 | 0/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/0 | True | 34 | 34 | 34/0/0 | 0/34 | 0/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/0 | True | 34 | 34 | 34/0/0 | 0/34 | 0/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/0 | True | 34 | 34 | 34/0/0 | 0/34 | 0/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/0 | True | 34 | 34 | 34/0/0 | 1/34 | 1/34 |
| dev/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/0 | True | 34 | 32 | 0/34/0 | 31/34 | 31/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/0 | True | 34 | 33 | 0/34/0 | 32/34 | 32/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/1 | True | 4 | 3 | 0/4/0 | 3/4 | 3/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/0 | True | 34 | 31 | 0/34/0 | 30/34 | 30/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/1 | True | 4 | 4 | 0/4/0 | 3/4 | 3/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/0 | True | 34 | 21 | 0/34/0 | 20/34 | 20/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/1 | True | 4 | 3 | 0/4/0 | 3/4 | 3/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/0 | True | 34 | 29 | 0/34/0 | 29/34 | 29/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/1 | True | 4 | 3 | 0/4/0 | 3/4 | 3/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/0 | True | 34 | 33 | 0/34/0 | 31/34 | 31/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/1 | True | 4 | 3 | 0/4/0 | 3/4 | 3/4 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/0 | True | 34 | 27 | 0/34/0 | 26/34 | 26/34 |
| dev/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/1 | True | 4 | 4 | 0/4/0 | 4/4 | 4/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/0 | True | 34 | 31 | 34/0/0 | 0/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/1 | True | 4 | 2 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/0 | True | 34 | 29 | 34/0/0 | 0/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/1 | True | 4 | 3 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/0 | True | 34 | 30 | 34/0/0 | 0/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/1 | True | 4 | 3 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/0 | True | 34 | 18 | 34/0/0 | 0/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/1 | True | 4 | 2 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/0 | True | 34 | 17 | 34/0/0 | 0/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/1 | True | 4 | 3 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/0 | True | 34 | 30 | 34/0/0 | 2/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/1 | True | 4 | 4 | 4/0/0 | 0/4 | 0/4 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/0 | False | 7 | 0 | 0/0/7 | 0/7 | 0/7 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/0 | True | 34 | 26 | 34/0/0 | 0/34 | 0/34 |
| dev/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/1 | True | 4 | 2 | 4/0/0 | 0/4 | 0/4 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | edit/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | edit/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | hybrid/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | hybrid/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | selected_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | selected_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | edit/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | edit/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | hybrid/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | hybrid/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | selected_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | selected_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_a/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_a/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | mistral.devstral-2-123b | qwen.qwen3-coder-next/honest_repair | uniform_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | edit/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | edit/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | hybrid/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | hybrid/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | selected_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | selected_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_a/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/adversarial_corruption | uniform_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | edit/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | edit/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | hybrid/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | hybrid/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | selected_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | selected_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_a/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_a/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_w/0 | False | 123 | 0 | 0/0/123 | 0/123 | 0/123 |
| heldout/generated | qwen.qwen3-coder-next | qwen.qwen3-coder-next/honest_repair | uniform_w/1 | False | 29 | 0 | 0/0/29 | 0/29 | 0/29 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/0 | True | 101 | 101 | 0/101/0 | 95/101 | 95/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | complement/1 | True | 20 | 20 | 0/20/0 | 20/20 | 20/20 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/0 | True | 101 | 101 | 0/101/0 | 94/101 | 94/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | edit/1 | True | 20 | 20 | 0/20/0 | 19/20 | 19/20 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/0 | True | 101 | 101 | 0/101/0 | 95/101 | 95/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | hybrid/1 | True | 20 | 20 | 0/20/0 | 20/20 | 20/20 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/0 | True | 101 | 101 | 0/101/0 | 96/101 | 96/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | no_witness/1 | True | 20 | 20 | 0/20/0 | 20/20 | 20/20 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/0 | True | 101 | 101 | 0/101/0 | 98/101 | 98/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | selected_w/1 | True | 20 | 20 | 0/20/0 | 20/20 | 20/20 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/0 | True | 101 | 101 | 0/101/0 | 95/101 | 95/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_a/1 | True | 20 | 20 | 0/20/0 | 20/20 | 20/20 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/0 | True | 101 | 101 | 0/101/0 | 97/101 | 97/101 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_buggy_to_canonical | uniform_w/1 | True | 20 | 20 | 0/20/0 | 20/20 | 20/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/0 | True | 101 | 101 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | complement/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/0 | True | 101 | 101 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | edit/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/0 | True | 101 | 101 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | hybrid/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/0 | True | 101 | 101 | 101/0/0 | 2/101 | 2/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | no_witness/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/0 | True | 101 | 101 | 101/0/0 | 3/101 | 3/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | selected_w/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/0 | True | 101 | 101 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_a/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/0 | True | 101 | 101 | 101/0/0 | 1/101 | 1/101 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | mistral.devstral-2-123b | None/native_canonical_to_buggy | uniform_w/1 | True | 20 | 20 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | complement/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | edit/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | hybrid/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | no_witness/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | selected_w/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_a/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/0 | True | 101 | 0 | 0/101/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_buggy_to_canonical | uniform_w/1 | True | 20 | 0 | 0/20/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | complement/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | edit/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | hybrid/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | no_witness/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | selected_w/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_a/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/0 | False | 22 | 0 | 0/0/22 | 0/22 | 0/22 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/0 | True | 101 | 0 | 101/0/0 | 0/101 | 0/101 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/1 | False | 9 | 0 | 0/0/9 | 0/9 | 0/9 |
| heldout/native | qwen.qwen3-coder-next | None/native_canonical_to_buggy | uniform_w/1 | True | 20 | 0 | 20/0/0 | 0/20 | 0/20 |

Machine-readable output also contains paired cell counts, conditional/all-assigned/valid-only denominators, final reserved-suite outcomes, generated intent-specific transfer contrasts, and repeat stability.

- Reserved-suite passing is a finite outcome oracle, not proof of semantic correctness.
- H1 measures reviewer-only response to evidence selection; H2 measures enforced outcomes.
- All assigned direction-conditional rates retain invalid/missing model calls as non-acceptance; valid-call-only rates are separately labeled.
- Unknown reserved outcomes remain assigned but cannot be labeled harmful/useful.
- Only explicitly eligible=true rows enter primary and generated transfer contrasts; ineligible/undeclared rows and reasons remain in full assigned arm counts.
- Bootstrap units are source tasks, not calls, proposals, models, or repetitions; reviewers remain separate.
- Development results and nonzero replicates are descriptive; exact primary tests use only heldout native replicate zero.
- Failing authenticated evidence vetoes acceptance in every arm; logical veto behavior alone is not a novel empirical defense result.

A met gate is bounded evidence for this protocol. It is not a novelty certificate or broad superiority over established regression/differential testing.
