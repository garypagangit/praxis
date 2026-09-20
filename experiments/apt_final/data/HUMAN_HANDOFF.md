# Resolve the E0 data contract

No reviewer has completed this work. This is a concrete handoff, not an approval form that can unlock modeling through self-attestation.

For Gary's personal actions and copy-ready messages, use [NEXT_ACTIONS.md](../NEXT_ACTIONS.md). The technical work below is primarily assigned to the assistant. Gary's role is to obtain missing source facts and identify an independent reviewer; he does not need to build parsers or manually populate all manifest fields.

## Source entry points

- Local author overview: `imports/unraveled/README.md` in the existing workspace.
- Local author data schema and caveats: `imports/unraveled/data/README.md`.
- [Author repository](https://gitlab.com/asu22/unraveled) and [data documentation](https://gitlab.com/asu22/unraveled/-/blob/master/data/README.md).
- [Author issue tracker](https://gitlab.com/asu22/unraveled/-/issues) for unresolved release/schema questions.
- Myneni et al. (2023), *Unraveled — A semi-synthetic dataset for Advanced Persistent Threats*, [Computer Networks article](https://www.sciencedirect.com/science/article/pii/S1389128623001330).
- The root README's Contact section lists the authors. No message has been sent. Repository links are author-provided references from the local documentation; this audit does not certify live website availability.

## Technical preparation and independent review

1. Read E0_REPORT.md and RAW_SAMPLE_SCHEMAS.json. Resolve Windows field/header mismatches and naive/yearless timestamps from collection documentation. Record the evidence source and exact transformation; do not guess timezone, year, or missing labels.
2. Populate `campaign_manifest.csv` with actual independent collection/campaign assignments, source row/range selectors, time bounds, and evidence references. Mark uncertainty explicitly. Seek author clarification if Signature AA/SH/APT cannot distinguish independently repeated campaigns. One APT group spanning weeks cannot be divided into independent campaigns solely by date.
3. Build a blinded linkage review packet from a pre-specified stratified sample of proposed matches, nonmatches, ambiguous matches, sources and stages. Keep raw event pairs in a controlled local location. Populate `link_review.csv` with source event IDs, match verdicts and reason/source references. Require another reviewer for uncertain cases and preserve disagreement. A review restricted to proposed positives cannot estimate missed matches.
4. Freeze the joining policy and clock correction using development data. Then apply it to a separately selected verification sample and report numerator, denominator, sampling scheme, precision/recall uncertainty, duplicate handling and missingness. This creates the join/skew numbers E0 lacks.
5. The assistant must first implement and qualify the normalizer and release validator; these are not completed tools in the current release. Then create immutable row/edge manifests, audit leakage and campaign membership, and recount row and group support by stage/split. Get a reviewer to verify the supporting artifacts rather than approve a naked PASS flag.

## Additional clock evidence found after the initial audit

The source repository contains `tools/employee_behavior_generation/scheduler.py`, whose `synchronize_worker` method runs NTP setup and a synchronization-verification playbook, and `configs/ntp.j2`, which configures Ubuntu NTP pools. This documents intended clock synchronization. Collection-time verification results and the unresolved Windows timezone/year conventions have not been established. Source code alone does not measure actual clock offset. The original E0 receipt is unchanged.

## Questions ready for source authors (draft only)

“We are evaluating graph-based APT identification using the public Unraveled data. Does the release contain multiple independently initiated APT campaigns, or one campaign over weeks 2–6? Is there a source-record mapping to campaign/session IDs beyond Signature? Which host timestamps use which timezone/year? The repository includes NTP synchronization code; are its collection-time verification results available? Are there stable flow-to-host session identifiers or verified event links? Where are the current Windows label schemas and final host-label annotations?”

## Human deliverables

Completed evidence-linked campaign and linkage CSVs, source clarification/annotation references, clock/schema mapping, reviewer disagreements and resolutions, and a support/leakage report. Store private/raw evidence locally; publish only permitted aggregate receipts and pseudonymous IDs. No completed review or response is represented by the blank templates.
