SOC ATTRIBUTION FEASIBILITY PACKAGE — OCTOBER 11, 2026

Outcome
The observation boundary and fair-comparison protocol are now concrete and the
readiness demonstration runs. Published data can support useful work without a
new large dataset. A qualified four-origin detector experiment is not ready, and
no novel effective detector or analyst benefit has been established.

User choices: controlled lab with session recording; no participants arranged.
The latest dataset question is answered in DATASET_OPTIONS.txt. We recommend a
published-data-first reliability/information study, with supplemental collection
only for a specific unsupported claim. Human research participation is not a
prerequisite for every machine-evaluation Praxis, but actual analyst benefit
cannot be asserted without an analyst study.

Work completed
1. Observation contract: exactly which fields a managed-session defender sees,
   three information views, provenance exclusions, and separate log regimes.
2. Label correction: live human/AI collaboration is separate from an AI-written
   script with no runtime AI. Prefix origin requires prefix-specific provenance.
3. Fair-comparison protocol: four origins, matched tasks, source/count controls,
   published-data route, optional 32-cell engineering design, separate transfer
   splits and later analyst evaluation. Original gates/results remain intact.
4. Reference implementation: boundary.py projects commands, results and timing
   with no future output or label fields, checks origin readiness and split overlap.
   This is an ingestion/projection contract, not a deployed terminal recorder.
5. Eighteen adversarial/edge-case tests pass. Inert fixtures demonstrate metadata
   exclusion, information separation, temporal cutoff and unidentifiable identical
   observations. Fixtures are explicitly rejected as genuine human data.
6. Fresh raw-archive audit: 93/93 hashes/sizes match; no source commands executed.
7. Targeted literature and dataset review: method overlap and viable public-data
   roles documented, with access/method limitations. Not a systematic review.

Newly recomputed evidence
- 87 finalized human and 222 AI samples in the selected raw archive subset.
- Human terminal-input keys: 86/87; AI terminal-input keys: 0/222.
- The deliberately forbidden rule 'terminal input present => human, absent => AI'
  gets 308/309 source labels (99.68%). This is a collector shortcut diagnostic,
  not a useful detector or proof that every normalized command classifier leaks.
- Matched filtered minimum-three-submission slice: 25 H and 42 A over 24 tasks.
- At minimum five: 10 H and 15 A over ten tasks, three human groups.
- At minimum ten: one H and three A on one task.
- Three distinct first-command strings occur under both origin labels in the full
  filtered extraction. No exact cross-label three/five-command prefix collisions
  found there; absence is not proof of separability or absence of near duplicates.
- No qualified separate scripted or runtime-hybrid arm in the audited slice.
  Different native recorders, unverified capture equivalence and prior exposure
  prevent calling it fresh four-arm confirmation. All counts are development.

What looks potentially fruitful
Incremental information value under ordinary-script and recording controls is a
defensible applied question. Published-data reliability work may quantify where
origin judgments break down. Neither claim needs a new architecture. Neither is
already established as novel or beneficial by today's software tests.

What happens next under a public-data-first route
Qualify comparable command/result extraction and the intended subset before any
new model run. Reuse earlier PX-125 results rather than rebrand the same feature
sweep. If a new observation or fresh qualified population creates a distinct
question, freeze a small baseline comparison before evaluating it. If no such
question or data can be qualified, write the bounded reliability synthesis rather
than claim an improved detector. New collection remains an optional targeted way
to support stronger script/hybrid claims, not a mandatory new benchmark project.

Files
OBSERVATION_CONTRACT.json — input/provenance boundaries and corrected origin axes.
PROTOCOL.txt / STUDY_PLAN.json — proposed study and unfinished dependencies.
DATASET_OPTIONS.txt — twelve source options and what each can actually support.
NOVELTY_REVIEW.txt — closest work and candidate contribution boundaries.
boundary.py / test_boundary.py — standard-library implementation and 18 tests.
audit_readiness.py — fresh archive/schema/cohort audit with bound source hashes.
demo.py — explicitly synthetic, inert observation-boundary demonstration.
results/READINESS.json — actual source audit results and exact failure reasons.
results/BOUNDARY_DEMO.json — projected examples and fixture rejection.
results/VALIDATION.json — executed test receipt and scope.
PACKAGE_MANIFEST.json — byte hashes of package files, excluding itself/cache.

Reproduce from this directory
python -m unittest -v test_boundary
python demo.py
python audit_readiness.py --raw-root C:/w/px120_lyptus_20261007 --replay C:/w/operator_signals_20261007/experiments/praxis_next/defense_opportunities_20261007/evidence/FILTERED_REPLAY_INPUT.json

Tests/demo are portable and require only Python's standard library. The raw audit
requires the local source archives named by their manifests; its output binds
their paths, bytes and SHA-256. This package does not redistribute those archives.
No GPU, cloud resource change, paid inference, recruitment or attack execution.
