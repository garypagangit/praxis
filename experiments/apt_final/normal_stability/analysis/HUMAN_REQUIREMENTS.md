# Human and external evidence requirements

**Status:** requirements documented; no human review or new source evidence is claimed. This document does not block completion of the registered experiment or require reopening the Unraveled dataset work.

## Completed development work

Every registered candidate ran, numerical evidence passed independent checks, AWS shutdown was verified, and the [fixed-family no-go result](../results/gpu_stability_20260920/REPORT.md) is complete. No new human labels were required for that development comparison. Results must say **annotated malicious entities**, retain the upstream filtered-benign assumption, and acknowledge previous test exposure.

## What requires outside evidence for broader claims

| Broader claim | Needed evidence and a concrete way to obtain it | Current status |
| --- | --- | --- |
| Detected entities are correctly labeled and ambiguities are understood | Ask the dataset maintainer for the source-to-prepared-row mapping and annotation/exclusion notes. A security reviewer can then check source records for a predeclared sample of false alerts, misses, and correct detections, recording confirmed benign, confirmed malicious, or uncertain. | Not performed; the prepared arrays lack source UUIDs and timestamps. |
| The method transfers to a new host, campaign, or time period | Obtain a separately documented evaluation partition with source IDs, collection times, host/campaign boundaries, and exposure history. A data owner confirms permitted access and those boundaries. Freeze the method before evaluating it. | Not established by the current graph-file splits or repeated seeds. |
| Relationship loss reflects real telemetry failures | Obtain collection-health records, such as sensor coverage and dropped-event counters, aligned to the source events. A system owner confirms how those records were produced. | Current masks simulate loss of retained relationships; the arrays cannot identify actual missing logs. |
| The method reduces real analyst burden | A participating security team supplies an observation interval and alert-review outcomes, allowing false alerts per host/day and review effort to be measured. | Entity-level benchmark FPR has no operational time denominator. |
| This is a defensible novel praxis | Give an adviser the completed protocol, audited results, and checked prior-art comparison. Record the exact proposed contribution and which existing method it exceeds or differs from. | No novelty claim; practical improvement alone is insufficient. |

These are requirements for broader claims, not promises that those claims will pass. Existing augmentation and calibration work is linked in the [literature assessment](../../embedding_baseline/results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md).

## Ready-to-use evidence record

Create one record per outside review or evidence delivery:

```text
Reviewer / data owner and date:
Dataset version and file hash:
Evidence delivered or source records inspected:
Prepared graph + row ID and source mapping, if available:
Finding: confirmed benign / confirmed malicious / uncertain / not applicable
Host, time, or campaign independence: supported / unsupported / unknown
Reason and evidence location:
Unresolved limitations:
```

**Documented result today:** the access/review steps and recording form are ready; none of the external findings above has been supplied or verified through this document. The current experiment has closed with its independently audited development no-go result.
