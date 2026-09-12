# Pre-outcome amendments

12 September 2026, before model inference/training: corrected the interpretation of the two-judge agreement range. Both-unsafe and either-unsafe (augmented for invalid/truncated evidence) are an instrument disagreement envelope, not proven bounds on true harmfulness. No examples, endpoints, thresholds, training settings, or decoding budgets changed. Original preregistration commit: `bb5f3720c18e47a21f6fea5b4e56b1f9c781ef14`.

Protocol hashing canonicalizes CRLF to LF so Windows and Linux copies of the same text have the same identity. This is a transport correction, not a scientific change.

Before model inference/training, pinned-data preparation returned HTTP 404 for the guessed XSTest filename `xstest_v2_prompts.csv`. The already-pinned official repository revision stores the 450-row prompt table as `xstest_prompts.csv` (250 safe, 200 unsafe; columns `id,prompt,type,label,focus,note`). Corrected only that path, keeping the revision, benchmark, eligibility and selection rule unchanged. File SHA-256: `11783fb294ed017473ee53c207d71f2161c7672c8d0b037501e78387f801cb5a`.
