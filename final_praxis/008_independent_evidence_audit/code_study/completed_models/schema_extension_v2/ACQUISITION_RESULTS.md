# Offline policy characterization

Assigned rows: 131200; independent source tasks: 164.

Positive differences favor hybrid. Twenty policy replicates are averaged within each task before task-level bootstrap resampling.

| Split/cohort/direction | Intent | Budget | Contrast | Tasks | Paired rows | Miss reduction | CI95 | Complete | Matched cost |
|---|---|---:|---|---:|---:|---:|---|---|---|
| dev/generated/harmful | adversarial_corruption | 4 | uniform - hybrid | 9 | 180 | 0.0222 | [-0.0389, 0.0833] | True | True |
| dev/generated/harmful | adversarial_corruption | 4 | edit - hybrid | 9 | 180 | 0.0056 | [-0.0167, 0.0333] | True | True |
| dev/generated/harmful | adversarial_corruption | 4 | fixed - hybrid | 9 | 180 | -0.0444 | [-0.1833, 0.0778] | True | True |
| dev/generated/harmful | adversarial_corruption | 4 | complement - hybrid | 9 | 180 | -0.0056 | [-0.0222, 0.0111] | True | True |
| dev/generated/harmful | adversarial_corruption | 8 | uniform - hybrid | 9 | 180 | -0.0111 | [-0.0667, 0.0500] | True | True |
| dev/generated/harmful | adversarial_corruption | 8 | edit - hybrid | 9 | 180 | 0.0111 | [0.0000, 0.0278] | True | True |
| dev/generated/harmful | adversarial_corruption | 8 | fixed - hybrid | 9 | 180 | -0.1111 | [-0.2444, -0.0111] | True | True |
| dev/generated/harmful | adversarial_corruption | 8 | complement - hybrid | 9 | 180 | -0.0056 | [-0.0333, 0.0167] | True | True |
| dev/generated/other | adversarial_corruption | 4 | uniform - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 4 | edit - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 4 | fixed - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 4 | complement - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 8 | uniform - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 8 | edit - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 8 | fixed - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | adversarial_corruption | 8 | complement - hybrid | 24 | 480 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 4 | uniform - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 4 | edit - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 4 | fixed - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 4 | complement - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 8 | uniform - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 8 | edit - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 8 | fixed - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/other | honest_repair | 8 | complement - hybrid | 1 | 20 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 4 | uniform - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 4 | edit - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 4 | fixed - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 4 | complement - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 8 | uniform - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 8 | edit - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 8 | fixed - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/generated/useful | honest_repair | 8 | complement - hybrid | 32 | 640 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 4 | uniform - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 4 | edit - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 4 | fixed - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 4 | complement - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 8 | uniform - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 8 | edit - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 8 | fixed - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/useful | native_buggy_to_canonical | 8 | complement - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 4 | uniform - hybrid | 34 | 680 | -0.0000 | [-0.0118, 0.0132] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 4 | edit - hybrid | 34 | 680 | 0.0029 | [-0.0029, 0.0088] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 4 | fixed - hybrid | 34 | 680 | 0.0118 | [-0.0677, 0.0985] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 4 | complement - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 8 | uniform - hybrid | 34 | 680 | -0.0029 | [-0.0132, 0.0074] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 8 | edit - hybrid | 34 | 680 | 0.0000 | [-0.0044, 0.0044] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 8 | fixed - hybrid | 34 | 680 | 0.0044 | [-0.0868, 0.0926] | True | True |
| dev/native/harmful | native_canonical_to_buggy | 8 | complement - hybrid | 34 | 680 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/harmful | adversarial_corruption | 4 | uniform - hybrid | 34 | 680 | -0.0074 | [-0.0471, 0.0279] | True | True |
| heldout/generated/harmful | adversarial_corruption | 4 | edit - hybrid | 34 | 680 | 0.0000 | [-0.0132, 0.0132] | True | True |
| heldout/generated/harmful | adversarial_corruption | 4 | fixed - hybrid | 34 | 680 | 0.0544 | [-0.0265, 0.1339] | True | True |
| heldout/generated/harmful | adversarial_corruption | 4 | complement - hybrid | 34 | 680 | -0.0132 | [-0.0250, -0.0029] | True | True |
| heldout/generated/harmful | adversarial_corruption | 8 | uniform - hybrid | 34 | 680 | 0.0015 | [-0.0294, 0.0309] | True | True |
| heldout/generated/harmful | adversarial_corruption | 8 | edit - hybrid | 34 | 680 | 0.0015 | [-0.0103, 0.0132] | True | True |
| heldout/generated/harmful | adversarial_corruption | 8 | fixed - hybrid | 34 | 680 | 0.0221 | [-0.0853, 0.1236] | True | True |
| heldout/generated/harmful | adversarial_corruption | 8 | complement - hybrid | 34 | 680 | -0.0162 | [-0.0324, -0.0029] | True | True |
| heldout/generated/other | adversarial_corruption | 4 | uniform - hybrid | 64 | 1280 | 0.0008 | [0.0000, 0.0023] | True | True |
| heldout/generated/other | adversarial_corruption | 4 | edit - hybrid | 64 | 1280 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | adversarial_corruption | 4 | fixed - hybrid | 64 | 1280 | 0.0008 | [0.0000, 0.0023] | True | True |
| heldout/generated/other | adversarial_corruption | 4 | complement - hybrid | 64 | 1280 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | adversarial_corruption | 8 | uniform - hybrid | 64 | 1280 | 0.0008 | [0.0000, 0.0023] | True | True |
| heldout/generated/other | adversarial_corruption | 8 | edit - hybrid | 64 | 1280 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | adversarial_corruption | 8 | fixed - hybrid | 64 | 1280 | 0.0016 | [0.0000, 0.0047] | True | True |
| heldout/generated/other | adversarial_corruption | 8 | complement - hybrid | 64 | 1280 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | honest_repair | 4 | uniform - hybrid | 5 | 100 | 0.0200 | [0.0000, 0.0600] | True | True |
| heldout/generated/other | honest_repair | 4 | edit - hybrid | 5 | 100 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | honest_repair | 4 | fixed - hybrid | 5 | 100 | 0.0200 | [0.0000, 0.0600] | True | True |
| heldout/generated/other | honest_repair | 4 | complement - hybrid | 5 | 100 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | honest_repair | 8 | uniform - hybrid | 5 | 100 | 0.0300 | [0.0000, 0.0900] | True | True |
| heldout/generated/other | honest_repair | 8 | edit - hybrid | 5 | 100 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/other | honest_repair | 8 | fixed - hybrid | 5 | 100 | 0.0300 | [0.0000, 0.0900] | True | True |
| heldout/generated/other | honest_repair | 8 | complement - hybrid | 5 | 100 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 4 | uniform - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 4 | edit - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 4 | fixed - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 4 | complement - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 8 | uniform - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 8 | edit - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 8 | fixed - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/generated/useful | honest_repair | 8 | complement - hybrid | 90 | 1800 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 4 | uniform - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 4 | edit - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 4 | fixed - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 4 | complement - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 8 | uniform - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 8 | edit - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 8 | fixed - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/useful | native_buggy_to_canonical | 8 | complement - hybrid | 101 | 2020 | 0.0000 | [0.0000, 0.0000] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 4 | uniform - hybrid | 101 | 2020 | 0.0109 | [-0.0040, 0.0267] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 4 | edit - hybrid | 101 | 2020 | 0.0050 | [-0.0030, 0.0119] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 4 | fixed - hybrid | 101 | 2020 | 0.0193 | [-0.0213, 0.0624] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 4 | complement - hybrid | 101 | 2020 | 0.0005 | [-0.0040, 0.0054] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 8 | uniform - hybrid | 101 | 2020 | 0.0119 | [-0.0000, 0.0248] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 8 | edit - hybrid | 101 | 2020 | 0.0079 | [0.0025, 0.0134] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 8 | fixed - hybrid | 101 | 2020 | 0.0431 | [0.0069, 0.0832] | True | True |
| heldout/native/harmful | native_canonical_to_buggy | 8 | complement - hybrid | 101 | 2020 | 0.0005 | [-0.0020, 0.0035] | True | True |

Only eligible heldout native harmful revisions at budget8 are primary offline characterization. Budget4 and generated intent cohorts remain secondary. Counts and costs for every assignment, including exclusions and missing records, are in the accompanying JSON.

- Reserved outcome direction is supplied by the frozen analyst oracle; selectors do not receive it.
- Unknown detection is an operational miss, never evidence that execution observed no failure; known-only rates are separately reported.
- All frozen replicates are averaged within source task. More seeds/proposals are not more independent tasks.
- Logical acquisition counts are per-condition experimental budgets, not measured cloud billing or necessarily physically repeated executions.
- Useful-direction detected failures indicate disagreement between displayed verification tests and reserved-suite passing; they are not automatically verified semantic false positives.
- A degenerate empirical bootstrap interval does not establish a population guarantee.
- Absent entire tasks cannot be recovered without expected assignments or complete runner placeholders.
