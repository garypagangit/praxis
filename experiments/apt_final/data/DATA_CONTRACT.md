# Data contract for APT final

**Current state: HOLD_DATA_CONTRACT.** The E0 audit inventories existing data; it cannot turn author claims or a checked box into validated campaign independence. No real-data PASS receipt is supplied.

## Normalized model input

Rows are UTF-8 JSONL with fields:

| Field | Required meaning |
|---|---|
| `id` | Unique immutable event/window ID; never just an ID reused within each CSV. |
| `group_id` | Evidence-backed independent campaign or collection unit. Source files/days are not automatically campaigns. |
| `split` | `train`, `gate_train`, `calibration`, `development`, or `confirmation`. Each group belongs to exactly one split. |
| `host_id` | Stable pseudonymous host ID mapped using documented source metadata. |
| `time` | Finite UNIX seconds, timezone resolved; event-time and arrival-time semantics documented. |
| `features` | Fixed-length finite numeric list produced without outcome labels, future events, source identity shortcuts, or held-out fitting. |
| `label` | Integer target with versioned source-to-stage mapping. Unknown and ambiguous labels remain unresolved or explicitly excluded. |

Edges are JSONL `{source, target, relation, available_at}`; endpoints reference row IDs and `available_at` uses UNIX seconds. Endpoint/group/split integrity and when an edge was observable must be checked before training. Cross-split edges are prohibited in this initial experiment contract. Edge construction cannot use labels, campaign IDs, withheld host mappings, or future arrival information. Graph, feature, preprocessing, and split manifests need exact hashes.

The concrete E1 engine validates its supported schema. This document does not override engine checks or authorize unsupported inputs.

## Required evidence bundle before E0 can pass

1. **Source receipt:** release/commit, license, author documentation, acquisition date, full local file hashes. Prefix sample receipts authenticate only sampled bytes.
2. **Parser and clock evidence:** exact schemas, malformed/multiline handling, timezone/year provenance, timestamp units, missingness counts, and verified same-event pairs for clock skew. Never infer skew from unmatched nearest events.
3. **Link evidence:** define eligible flows and host events, session/entity relation, interval tolerance, multiplicity policy, and verified-positive/negative adjudications. Keep unmatched, unobservable, ambiguous, and invalid records separate. Duplicated gateway/subnet observations require deduplication or shared grouping before splitting.
4. **Campaign manifest:** `campaign_manifest.csv` entries tied to stable source IDs or documented ranges and supporting author/annotation references. A reviewer verifies references. Attacker group Signature and filename are inadequate by themselves. If only one APT campaign exists, it cannot supply independent train and confirmation APT campaigns.
5. **Labels and support:** provide per-stage row counts, distinct independent groups and collection units per split. Minimum 30 positive confirmation rows is a screening floor, not evidence of statistical power or independence. Include stages only after this audit; keep excluded stages excluded everywhere.
6. **Split freeze:** train for model fitting, gate_train for routing development, calibration for thresholds, development for diagnostic evaluation, confirmation untouched until freeze. Transform fitting uses authorized training data only. Temporal ordering and campaign grouping both documented; old interleaved stage-balanced days do not satisfy prospective confirmation.
7. **Operational denominator:** unsampled monitored duration and coverage are required for alerts/day. A cache retaining roughly 5% of benign traffic cannot directly supply a natural alert burden.

## Future receipt fields (specification only)

A future validated receipt must contain `status: "PASS"`, `rows_sha256`, `edges_sha256`, `included_labels`, `confirmation_ready` (false unless separately supported), evidence references for campaign mapping, parser and join audits, review receipts, excluded stages/reasons, and validator version/hash. Setting these fields is not validation. The current audit emits HOLD and must not be edited into PASS; a future validator must inspect the supporting evidence.

If independent campaigns or trustworthy links cannot be supplied, preserve Unraveled as explicitly bounded development data and evaluate the official DARPA TC/OpTC/PIDSMAKER route. A fallback name is not a dataset: verify actual access, labels, license, schemas, per-stage coverage and independent engagements before adoption.
