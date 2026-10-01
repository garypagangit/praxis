# PX-094: exfiltration episode coverage and SOC workload

**Scope:** source/client-host episodes inferred from flow labels and timing, plus simulated review cases. These are not independently confirmed SOC incidents or measured analyst outcomes. Zero new fits and no cloud/API use.

## Primary grouping: source–destination, 15-minute windows; 60-minute episode gap

| Source | Policy | Exfil episodes warned / total | Raw warning flows | Grouped cases | Benign-only-warning cases | New episodes vs base OR | Earlier episodes vs base OR |
|---|---|---:|---:|---:|---:|---:|---:|
| UNRAVELED | base_mean | 4 / 18 | 14941 | 725 | 128 | 0 | 0 |
| UNRAVELED | base_OR | 6 / 18 | 16022 | 1057 | 142 | 0 | 0 |
| UNRAVELED | plus_current_OR | 6 / 18 | 16022 | 1057 | 142 | 0 | 0 |
| UNRAVELED | full_OR | 6 / 18 | 17843 | 2607 | 1691 | 0 | 0 |
| wilson | base_mean | 1 / 1 | 60510 | 4457 | 15 | 0 | 0 |
| wilson | base_OR | 1 / 1 | 60535 | 4460 | 16 | 0 | 0 |
| wilson | plus_current_OR | 1 / 1 | 60636 | 4509 | 62 | 0 | 0 |
| wilson | full_OR | 1 / 1 | 62851 | 4611 | 161 | 0 | 0 |
| harrison | base_mean | 1 / 1 | 100668 | 18795 | 222 | 0 | 0 |
| harrison | base_OR | 1 / 1 | 101222 | 18828 | 255 | 0 | 0 |
| harrison | plus_current_OR | 1 / 1 | 113799 | 19443 | 867 | 0 | 1 |
| harrison | full_OR | 1 / 1 | 115395 | 19586 | 1007 | 0 | 1 |

A case is released at its fixed window end. Benign-only-warning means all warned flows in that case are labeled benign; an unflagged attack sharing the group is not credited as detected. Episode boundaries are evaluation proxies; captures/executions are never silently pooled into one campaign.

## Reference scenario: one analyst, 15 minutes per case, 09:00–17:00 UTC daily

| Source | Policy | Analyst-hours of service | Cases unfinished at observation end | Median wait (hours) | P95 wait (hours) | Episodes with a review slot completed within 60 minutes | Within 240 minutes |
|---|---|---:|---:|---:|---:|---:|---:|
| UNRAVELED | base_mean | 181.25 | 469 | 226.25 | 399.95 | 0 / 18 | 1 / 18 |
| UNRAVELED | base_OR | 264.25 | 801 | 321.75 | 570.25 | 0 / 18 | 1 / 18 |
| UNRAVELED | plus_current_OR | 264.25 | 801 | 321.75 | 570.25 | 0 / 18 | 1 / 18 |
| UNRAVELED | full_OR | 651.75 | 2351 | 889.75 | 1674.67 | 0 / 18 | 1 / 18 |
| wilson | base_mean | 1114.25 | 4265 | 1563.00 | 3072.30 | 0 / 1 | 0 / 1 |
| wilson | base_OR | 1115.00 | 4268 | 1563.38 | 3073.01 | 0 / 1 | 0 / 1 |
| wilson | plus_current_OR | 1127.25 | 4317 | 1585.50 | 3100.65 | 0 / 1 | 0 / 1 |
| wilson | full_OR | 1152.75 | 4419 | 1630.25 | 3172.88 | 0 / 1 | 0 / 1 |
| harrison | base_mean | 4698.75 | 18635 | 6943.00 | 13281.08 | 0 / 1 | 0 / 1 |
| harrison | base_OR | 4707.00 | 18668 | 6963.12 | 13304.91 | 0 / 1 | 0 / 1 |
| harrison | plus_current_OR | 4860.75 | 19283 | 7184.00 | 13754.98 | 0 / 1 | 0 / 1 |
| harrison | full_OR | 4896.50 | 19426 | 7249.88 | 13852.94 | 0 / 1 | 0 / 1 |

Service hours sum analyst effort, not elapsed calendar hours. A completed slot does not establish a correct analyst verdict. Delays include batch-window release and staffing shifts; real SOC schedules, priority triage and case complexity are not measured.

## Marginal heterogeneous-gate workload

| Source | Added grouped cases vs base OR | Added service hours at 5 min | At 15 min | At 30 min | Additional primary episodes |
|---|---:|---:|---:|---:|---:|
| UNRAVELED | 1550 | 129.17 | 387.50 | 775.00 | 0 |
| wilson | 151 | 12.58 | 37.75 | 75.50 | 0 |
| harrison | 758 | 63.17 | 189.50 | 379.00 | 0 |

## Sensitivity, all retained

| Source | Full-OR new episodes: minimum–maximum | Additional grouped cases: minimum–maximum |
|---|---:|---:|
| UNRAVELED | 0–0 | 138–1626 |
| wilson | 0–0 | 67–234 |
| harrison | 0–0 | 145–1657 |

Ranges span all declared 5/15/60-minute windows, source or pair grouping, and 30/60/120-minute episode gaps. Repeated views are dependent. Staff and service-time grids are in QUEUE_RESULTS.csv; no favorable scenario is promoted after inspection.

## Evidence and interpretation limits

Independent audit: 15,496 checks across 72 case cells, 216 episode-result rows and 648 queue scenarios. Frozen source hashes, native endpoint mapping, all group/episode counts and every simulated queue were checked. No actual staffing record or confirmed incident ID was available.

This experiment tests whether flow-level gains become new episode coverage under stated definitions, and what case/queue burden follows. It cannot determine the number of real incidents rescued or the probability of an analyst reaching a correct conclusion. Evidence needed for that next claim is a case-linked incident ground truth and timed analyst review; additional replay or model tuning cannot substitute for those observations.

[Frozen protocol](PROTOCOL.md) | [Episode results CSV](RESULTS.csv) | [Queue scenarios CSV](QUEUE_RESULTS.csv) | [Audit](AUDIT.json)
