# PX-002 TTP Retrieval Defense Audit

Generated: 2026-07-01T00:04:56.179883+00:00

Status: **BOUNDED LOOKUP-STYLE POSITIVE ONLY**

## Purpose

This audit tests whether the ATT&CK group-profile retrieval positive survives harsher defense conditions. The original positive samples observed TTPs from the target group's profile and ranks candidate profiles. That is useful as profile lookup, but it can overstate defense readiness because exact self-overlap is available.

## Stress Settings

- `standard`: original five-shot profile retrieval.
- `leave_query_out`: remove the observed query techniques from the true group's candidate profile before scoring.
- `noisy_query`: replace 40% of observed techniques with techniques not in the target profile.

## Results

| setting | method | shot | top1 | top5 | top10 | mrr | median_rank | queries |
|---|---|---|---|---|---|---|---|---|
| leave_query_out | frequency_prior | 5 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| leave_query_out | overlap_cosine | 5 | 0.000 | 0.000 | 0.000 | 0.008 | 134.0 | 605 |
| leave_query_out | random_uniform | 5 | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 |
| leave_query_out | svd32_graph_embedding | 5 | 0.116 | 0.299 | 0.413 | 0.215 | 16.0 | 605 |
| noisy_query | frequency_prior | 5 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| noisy_query | overlap_cosine | 5 | 0.412 | 0.788 | 0.914 | 0.567 | 2.0 | 605 |
| noisy_query | random_uniform | 5 | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 |
| noisy_query | svd32_graph_embedding | 5 | 0.225 | 0.577 | 0.767 | 0.389 | 4.0 | 605 |
| standard | frequency_prior | 5 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| standard | overlap_cosine | 5 | 0.721 | 0.960 | 0.992 | 0.824 | 1.0 | 605 |
| standard | random_uniform | 5 | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 |
| standard | svd32_graph_embedding | 5 | 0.623 | 0.879 | 0.949 | 0.732 | 1.0 | 605 |

## Decision

Keep PX-002 only as a bounded profile-lookup artifact. Do not use it as a major Praxis defense pillar because anti-tautology/noisy-query stress is too weak.

## Artifacts

- Raw records: `runs/px002-ttp-retrieval-defense-audit-20260630/records.csv`
- Summary: `runs/px002-ttp-retrieval-defense-audit-20260630/summary.csv`
- JSON payload: `runs/px002-ttp-retrieval-defense-audit-20260630/payload.json`
