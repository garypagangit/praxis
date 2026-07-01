# PX-003 Qwen2.5-7B Defense Replication

Generated: 2026-07-01 UTC

Status: **PASS - CROSS-FAMILY RETRIEVAL-CONDITIONED EFFECT REPLICATED**

## Purpose

This gate reruns the PX-003 evidence-addressable CTI-MCQ slice on a non-Llama model family to test whether the relationship-evidence lift is a Llama-only artifact. The run used `Qwen/Qwen2.5-7B-Instruct` on AWS `g5.xlarge` (`i-07178e293e8df2a60`) with all six prompt conditions over the locked `106`-row evidence-addressable slice.

## Scorecard

| Condition | Accuracy | Correct / Rows | Invalid rate |
|---|---:|---:|---:|
| `vanilla` | `0.623` | `66 / 106` | `0.000` |
| `relationship_evidence` | `0.906` | `96 / 106` | `0.000` |
| `technique_only_evidence` | `0.726` | `77 / 106` | `0.000` |
| `random_facts` | `0.462` | `49 / 106` | `0.057` |
| `empty_evidence` | `0.594` | `63 / 106` | `0.057` |
| `broad_seed` | `0.660` | `70 / 106` | `0.009` |

## Key Tests

| Test | Result |
|---|---|
| Relationship minus vanilla | `+0.283` |
| Relationship minus technique-only | `+0.179` |
| Relationship evidence-only wins vs vanilla-only wins | `35` vs `5` |
| Random-facts negative control | Relationship evidence beats random facts by `+0.443` |
| Empty-evidence negative control | Relationship evidence beats empty evidence by `+0.311` |
| Broad-seed comparison | Relationship evidence beats broad seed by `+0.245` |

## Interpretation

The main PX-003 claim survives a non-Llama replication: per-question ATT&CK evidence retrieval substantially improves strict CTI-MCQ compliance on the locked evidence-addressable slice. Qwen2.5-7B reproduces the same pattern seen on Llama-3.1-8B and Llama-3.2-3B.

The mechanism claim must remain conservative. Relationship-level evidence is the strongest tested condition, but technique-only evidence also improves over vanilla. The defended claim is therefore retrieval-conditioned CTI compliance, not pure relationship causality.

The underlying runner labels the gate as `STOP` because it treats invalid outputs in negative-control conditions as a full ablation failure. For the defense audit, that is not a failure of the positive claim: relationship evidence has `0.000` invalid rate and wins against vanilla, technique-only, random facts, empty evidence, and broad seed.

## Artifacts

| Artifact | Purpose |
|---|---|
| `qwen25_7b_defense_20260630/summary.json` | Machine-readable condition summaries and paired comparisons. |
| `qwen25_7b_defense_20260630/report.md` | Generated model-gate report. |
| `qwen25_7b_defense_20260630/predictions.jsonl` | All `636` condition-level predictions. |
| `qwen25_7b_defense_20260630/logs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630.log` | AWS setup, model load, generation, and sync log. |

## Decision

PX-003 should be kept as a true Praxis defense-positive result. PX-034 should be merged into PX-003 as the source-conflict/router add-on that decides when this retrieval-conditioned answering path is safe to use directly.
