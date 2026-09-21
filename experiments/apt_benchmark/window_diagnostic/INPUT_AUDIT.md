# Independent input audit

Status: **PASS**; 62 checks.

Independent software/input audit; not a human label audit.

Direct CSV overlap and roster reconstruction; fresh complete source pass for per-bin event counts and hash; source coverage, aggregate support, all saved artifact hashes, and sparse-matrix invariants. Does not refit, score, mutate features, or certify semantic label correctness.

Confirmed 5,480 bins: 264 positive, 4,319 other-annotation negative, 897 unknown. Retained 13 empty positive bins and all 83 target source intervals.

## Limits

- Does not independently reconstruct every lexical hash from raw fragments; tests invariant relations and provenance/code hashes.
- Ablation may create new cross-fragment bigrams, so text-column subset of clean is not asserted. First-event text must be a subset of pooled text within the same condition.
- The author-derived slice, padded window labels, unknown-period handling, and exposed development-family limitations remain.

Detailed aggregate checks: [INPUT_AUDIT.json](INPUT_AUDIT.json).
