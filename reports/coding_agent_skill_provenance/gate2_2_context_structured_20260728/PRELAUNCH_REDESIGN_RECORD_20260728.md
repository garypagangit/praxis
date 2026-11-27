# PX-062 Gate 2.2 prelaunch redesign record

**Date:** 2026-07-28
**Outcome status when superseded:** no model-facing collection had run and no
Qwen or Mistral confirmation output existed.

## Why the first candidate corpus was superseded

A hostile prelaunch review found that the first candidate corpus could support
a misleading positive result.  Its 516 expected-`NONE` requests were expanded
from twelve recurring safety and physical-operation frames.  A phrase rule
using those construction artifacts separated registered-skill targets from
`NONE` targets on 1,032/1,032 tasks.  The original repair endpoint also pooled
registered and `NONE` targets, so easy `NONE` recovery could satisfy the repair
gate while actual skill recovery remained weak.

The same review identified additional prospective design issues: sixty
registered-target prompts contained their canonical skill identifier, 172
underlying requests were reused across two strata, correct-answer option
positions were not balanced, contextual and decontextualized repair used
different system instructions, and the evidence chain did not yet prove an
exact reconstruction of generated completions from token IDs.

These are design and integrity failures, not experimental outcomes.  Launch was
halted and the candidate was replaced before any model result was generated or
viewed.  No threshold was changed in response to model performance.

## Superseded candidate identifiers

| Artifact | SHA-256 |
|---|---|
| Tasks | `9621c0c233a846adda237d3ad0b2e2bf45325eb7d7bf557ab1504af376c2a640` |
| Answer key | `85d31e407083e8ca6e200fd2914e703b04c4b975552e6f849f80393d5d25b469` |
| Registry catalog | `d775221aaa2d0bb11ee7b25c2236a241970175d97726fc70f55e47ca6589acde` |
| Benchmark manifest | `9871ed284821dc81c8336c3a7e0d513acb0c730bd7025ee0257d95db496c20d0` |
| Blinded audit 1 | `5eb3f2b87ec8879b583c336cb0c046d7f95e9563789bdf89025292cd186a2b9a` |
| Blinded audit 2 | `7acd6e31b0adc5c4b5d2aeb15f3d8f545caded9601274cb40eedfcc466761513` |

Both first-pass audits agreed with the intended labels, but they did not test
whether labels were exposed by corpus-wide construction artifacts.  They are
therefore superseded and cannot authorize launch of the redesigned benchmark.

## Prospective corrective requirements

The replacement corpus and executable protocol must satisfy all of the
following before registration:

- diverse, individually authored unsupported requests across 43 domains;
- no label-exclusive request frames and a prospective lexical-leakage audit;
- distinct underlying requests across all task strata;
- no canonical answer identifier embedded in a confirmatory prompt;
- balanced correct-answer local-ID positions within label and task strata;
- two new independent blinded label audits over the replacement tasks;
- repair efficacy scored on `A-invalid` registered-skill targets, separately
  from the expected-`NONE` harm gate;
- identical format-neutral system instructions for the D/E context ablation;
- untrimmed completion preservation and independent token-ID reconstruction;
- cryptographic binding of corpus, audit evidence, preregistration, collector,
  adjudicator, tests, model revisions, tokenizer artifacts, and AWS receipts.

Only a replacement that meets these requirements, as prospectively amended
below, may be marked frozen and launched.

## Prospective addendum: label-independent option maps

**Added:** 2026-07-28, before either replacement label audit and before any
Qwen or Mistral Gate 2.2 collection output existed.

A second hostile prelaunch review found that the line-52 requirement to balance
the *correct answer's* local-ID position would itself require private labels to
construct option maps.  The pending candidate had in fact used label/task
strata while assigning rotations.  That creates an avoidable answer-dependent
information path even when the final counts look balanced.  The affected
pending candidate was regenerated; it never produced model-facing output and
its audits remained 0/2.

The line-52 requirement is therefore superseded prospectively by the following
stronger construction rule:

- derive each collection task ID only from a frozen namespace and the full
  collection-visible prompt bytes;
- order all 43 skill values plus JSON `null` from a fixed salted hash, rank
  prompts only within their observable direct or misleading outer scaffold,
  and rotate by a frozen scaffold offset; and
- require every catalog value to appear 23 or 24 times in every local-ID
  position globally (15-16 in direct prompts and 7-8 in misleading prompts).

Expected labels, private task subtypes, within-label indices, authoring
fingerprints, and label-derived IDs are forbidden construction inputs.
Correct-answer positions are disclosed after construction as a diagnostic only
and cannot authorize or reject the corpus.  Information-flow tests must prove
that mutating private answer fields leaves task IDs and option maps unchanged.
This addendum governs the replacement candidate and resolves the apparent
conflict with the historical line-52 finding.
