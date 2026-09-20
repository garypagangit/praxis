# E0: Unraveled data verification

**Result: HOLD_DATA_CONTRACT.** The audit completed; E1–E4 cannot claim validated real-data results yet.

## What was actually examined

- 173 network-flow files and 59 host-log files, each using at most 128 records from a 2,097,152-byte prefix.
- All 435,488 rows in the existing processed cache were recounted; metadata totals and stages agree: True.
- Samples are the beginning of files, not probability samples. Raw row totals and population join rates cannot be inferred from them.
- No raw events, event text, credentials, downloaded datasets, or model outputs were copied into this result folder.

## Required three numbers

1. **Validated join rate: unavailable.** The deterministic interval search found 0 candidate pairs among 22,144 timestamp-valid sampled flows and 1,401 sampled host events. Host/time coincidence is not proof that the records describe the same action. Zero candidates would not demonstrate an unjoinable dataset.
2. **Lifecycle label coverage:** all cached rows have StageClean labels; the full-cache counts are below. This cache retained about 5% of benign traffic (with a per-file minimum) and omitted cover-up; it is not the raw population or evidence of host-label completeness.
3. **Minimum positive test support per independent stage/campaign: unavailable.** Old split row counts exist, but no evidence-backed independent campaign mapping exists. No stage is yet included in a new hypothesis test.

| Cached stage | Rows |
|---|---:|
| benign | 338,609 |
| data exfiltration | 7,522 |
| establish foothold | 27,118 |
| lateral movement | 27,445 |
| reconnaissance | 34,794 |

## Why the hold is necessary

Flow timestamps have explicit millisecond units. Audit records use epoch seconds; some syslog records contain timezone-qualified timestamps. Other host records lack a timezone or year, or have mismatched CSV field counts. Those records were not silently assigned a timezone or extra labels. Clock skew needs manually or programmatically verified same-event pairs; a nearest timestamp distribution is not clock skew.

The source README describes one APT group operating across multiple weeks, plus amateur and skilled attacker groups. Signature identifies an attacker group, not independently repeated campaigns. Capture-day and file boundaries do not create new campaigns. All old train/validation/test partitions share six sensors; the old days are interleaved rather than a clean prospective timeline. Shared sensors alone do not invalidate campaign evaluation, but they do not demonstrate cross-environment generalization either.

The source data README also documents duplicate observations at subnet and gateway sensors, missing intra-subnet flow visibility, partial host logging, and host labeling described as unfinished in that README. These need explicit handling; the current on-disk files, not an old README claim, determine actual availability.

## Concrete next work

Use [DATA_CONTRACT.md](../../data/DATA_CONTRACT.md) and the [human handoff](../../data/HUMAN_HANDOFF.md). Establish event matching and clock provenance, independently review a stratified set of candidate/noncandidate pairs, resolve raw host schemas and labels, and supply evidence-backed campaign/group assignments. Deduplicate cross-sensor observations before splitting. If the dataset supplies only one complete APT realization, retain it for development and obtain separately documented DARPA TC/OpTC engagements for confirmation; changing a file name cannot fix independence.

The proposed 30 positive test rows per stage is only a minimum support screen. Repeated flows from one attack are not 30 independent attacks; report row counts and independent groups separately and plan uncertainty at the campaign level.

## Reproduce

`python experiments/apt_final/data_audit.py --workspace PATH_TO_EXISTING_WORKSPACE --output NEW_EMPTY_OUTPUT_FOLDER`

This is a local CPU audit and uses no network, AWS, API, or model. Full file and sampled-prefix hashes are in SOURCE_MANIFEST.json. The command returns success when the audit completes, including a scientific HOLD; downstream code must inspect E0_RESULT.json.status.
